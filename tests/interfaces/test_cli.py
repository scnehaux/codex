import datetime
import pytest
import os
import sys
from engine.control.config.severity import SeverityRule
import importlib.util
from engine.interfaces.cli import print_errors, lint_file, build_sarif
from engine.control.config.constants import FRAMEWORK_ROOT
from tests.support.repository import REPOSITORY_ROOT


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch, tmp_path):
    # Mock validation so tests running in temp dir don't abort immediately
    monkeypatch.setattr(
        "engine.interfaces.cli._validate_execution_root", lambda x: None
    )
    # CD into tmp_path so os.getcwd() returns tmp_path, preventing cross-drive relpath ValueErrors
    monkeypatch.chdir(tmp_path)


def _write_md(
    tmp_path,
    filename,
    frontmatter_yaml,
    body="## Context & Scope\nThis is the context.",
):
    content = f"---\n{frontmatter_yaml}\n---\n{body}"
    fpath = tmp_path / filename
    fpath.write_text(content, encoding="utf-8")
    return str(fpath)


def _global_rules():
    from engine.interfaces.cli import load_json_schema_file

    path = os.path.join(FRAMEWORK_ROOT, "schemas", "base.schema.json")
    rules = load_json_schema_file(path).get("x-global-config", {})
    if "severity_levels" in rules:
        flat_sev = {}
        for group, items in rules["severity_levels"].items():
            flat_sev.update(items)
        rules["severity_levels"] = flat_sev
    return rules


def test_print_errors():
    errors = [("ERROR", "Bad thing"), ("WARNING", "Not so bad")]
    errs, is_clean, has_blocking = print_errors(
        "file.md", errors, "text", ("CRITICAL", "ERROR")
    )
    assert not is_clean
    assert has_blocking

    errs2, is_clean2, has_blocking2 = print_errors(
        "file.md", [("WARNING", "Only warning")], "text", ("CRITICAL", "ERROR")
    )
    assert not is_clean2
    assert not has_blocking2

    errs3, is_clean3, has_blocking3 = print_errors(
        "file.md", [], "text", ("CRITICAL", "ERROR")
    )
    assert is_clean3
    assert not has_blocking3


def test_print_errors_json_format():
    """JSON format returns without printing, preserving error data."""
    errors = [("ERROR", "Bad thing")]
    errs, is_clean, has_blocking = print_errors(
        "file.md", errors, "json", ("CRITICAL", "ERROR")
    )
    assert errs == errors
    assert not is_clean
    assert has_blocking

    # No errors in JSON mode
    errs2, is_clean2, has_blocking2 = print_errors(
        "file.md", [], "json", ("CRITICAL", "ERROR")
    )
    assert is_clean2
    assert not has_blocking2


def test_lint_file_draft_skip(tmp_path):
    """A draft within max_draft_age_days must skip structural checks and yield INFO."""
    today = datetime.date.today().isoformat()
    fm = f"doc_meta:\n  id: SAD-TEST-001\n  status: draft\n  created_date: {today}"
    fpath = _write_md(tmp_path, "SAD-TEST-001.sad.md", fm)

    rules = _global_rules()
    errs, is_clean, has_blocking, di = lint_file(
        fpath,
        rules,
        rules.get("severity_levels", {}),
        tuple(rules.get("blocking_severities", ["CRITICAL", "ERROR"])),
        set(),
        {},
        "text",
    )
    assert is_clean is False
    assert errs[0][0] == "INFO"
    assert "Relaxed validation profile applied" in errs[0][1]


def test_lint_file_gdc_draft_runs_full_validation(tmp_path):
    # A GDC draft is pre-baseline but MUST NOT use the relaxed draft profile.
    today = datetime.date.today().isoformat()
    fm = (
        "doc_meta:\n"
        "  id: GDC-999\n"
        "  status: draft\n"
        "  version: 0.0.1\n"
        f"  created_date: {today}"
    )
    fpath = _write_md(
        tmp_path,
        "GDC-999-control-plane-test.md",
        fm,
        body="## Context & Scope\nshort\n\n## Policy Framework\nshort",
    )

    rules = _global_rules()
    errs, is_clean, has_blocking, di = lint_file(
        fpath,
        rules,
        rules.get("severity_levels", {}),
        tuple(rules.get("blocking_severities", ["CRITICAL", "ERROR"])),
        set(),
        {},
        "text",
    )

    assert has_blocking is True
    assert not any("Relaxed validation profile applied" in msg for _, msg in errs)


def test_lint_file_draft_expired(tmp_path):
    """A draft older than max_draft_age_days must produce a blocking ERROR."""
    old_date = (datetime.date.today() - datetime.timedelta(days=999)).isoformat()
    fm = f"doc_meta:\n  id: SAD-TEST-001\n  status: draft\n  created_date: {old_date}"
    fpath = _write_md(tmp_path, "SAD-TEST-001.sad.md", fm)

    rules = _global_rules()
    errs, is_clean, has_blocking, di = lint_file(
        fpath,
        rules,
        rules.get("severity_levels", {}),
        tuple(rules.get("blocking_severities", ["CRITICAL", "ERROR"])),
        set(),
        {},
        "text",
    )
    assert has_blocking is True
    assert any("exceeding limit" in msg for _, msg in errs)
    assert any(sev == "ERROR" for sev, _ in errs)


def test_lint_file_draft_missing_created_date(tmp_path):
    """A draft without created_date must produce a blocking ERROR."""
    fm = "doc_meta:\n  id: SAD-TEST-001\n  status: draft"
    fpath = _write_md(tmp_path, "SAD-TEST-001.sad.md", fm)

    rules = _global_rules()
    errs, is_clean, has_blocking, di = lint_file(
        fpath,
        rules,
        rules.get("severity_levels", {}),
        tuple(rules.get("blocking_severities", ["CRITICAL", "ERROR"])),
        set(),
        {},
        "text",
    )
    assert has_blocking is True
    assert any("missing 'created_date'" in msg for _, msg in errs)
    assert any(sev == "ERROR" for sev, _ in errs)


# ---------- lint_file Error Path Tests ----------


def test_lint_file_unknown_doc_type(tmp_path):
    """File with an unrecognized ID prefix must produce a blocking ERROR."""
    fm = "doc_meta:\n  id: ZZZ-999"
    fpath = _write_md(tmp_path, "ZZZ-999.md", fm)

    rules = _global_rules()
    errs, is_clean, has_blocking, di = lint_file(
        fpath,
        rules,
        rules.get("severity_levels", {}),
        tuple(rules.get("blocking_severities", ["CRITICAL", "ERROR"])),
        set(),
        {},
        "text",
    )
    assert has_blocking is True
    assert any("Unknown doc type" in msg for _, msg in errs)


def test_lint_file_missing_frontmatter(tmp_path):
    """File without YAML frontmatter must produce a blocking ERROR."""
    fpath = tmp_path / "test.md"
    fpath.write_text("# No frontmatter here", encoding="utf-8")

    rules = _global_rules()
    errs, is_clean, has_blocking, di = lint_file(
        str(fpath),
        rules,
        rules.get("severity_levels", {}),
        tuple(rules.get("blocking_severities", ["CRITICAL", "ERROR"])),
        set(),
        {},
        "text",
    )
    assert has_blocking is True
    assert any("frontmatter" in msg.lower() for _, msg in errs)


def test_lint_file_read_error(tmp_path):
    """Non-existent file must produce a blocking ERROR (not crash)."""
    fpath = str(tmp_path / "nonexistent.md")

    rules = _global_rules()
    errs, is_clean, has_blocking, di = lint_file(
        fpath,
        rules,
        rules.get("severity_levels", {}),
        tuple(rules.get("blocking_severities", ["CRITICAL", "ERROR"])),
        set(),
        {},
        "text",
    )
    assert has_blocking is True
    assert any("Failed to read file" in msg for _, msg in errs)


def test_lint_file_json_format(tmp_path):
    """JSON format should return errors without printing."""
    fm = "doc_meta:\n  id: ZZZ-999"
    fpath = _write_md(tmp_path, "ZZZ-999.md", fm)

    rules = _global_rules()
    errs, is_clean, has_blocking, di = lint_file(
        fpath,
        rules,
        rules.get("severity_levels", {}),
        tuple(rules.get("blocking_severities", ["CRITICAL", "ERROR"])),
        set(),
        {},
        "json",
    )
    assert isinstance(errs, list)
    assert has_blocking is True


# ---------- Coverage Tests for cli.py ----------


def test_load_json_schema_file_not_found():
    from engine.interfaces.cli import load_json_schema_file

    with pytest.raises(FileNotFoundError):
        load_json_schema_file("non_existent.json")


def test_lint_file_missing_specific_rules(tmp_path, monkeypatch):
    """File that resolves to a type without its corresponding specific rules YAML."""
    # We will temporarily remove the specific rules file for this test
    fm = "doc_meta:\n  id: SAD-TEST-001"
    fpath = _write_md(tmp_path, "SAD-TEST-001.sad.md", fm)

    import engine.control.linting.facade as linter

    original_loader = linter.load_json_schema_file

    def mock_loader(path):
        if "sad.schema.json" in path:
            raise FileNotFoundError()
        return original_loader(path)

    monkeypatch.setattr(linter, "load_json_schema_file", mock_loader)

    rules = _global_rules()
    with pytest.raises(SystemExit) as exc_info:
        lint_file(
            fpath,
            rules,
            rules.get("severity_levels", {}),
            tuple(rules.get("blocking_severities", ["CRITICAL", "ERROR"])),
            set(),
            {},
            "text",
        )

    assert exc_info.value.code == 1


def test_main_clean_run(tmp_path, monkeypatch):
    """main() should exit 0 when all files are clean."""
    fm = (
        "doc_meta:\n  id: SAD-TEST-001\n  parent_pad: PAD-TEST-001\n  status: draft\n  last_reviewed: "
        + datetime.date.today().isoformat()
    )
    _write_md(tmp_path, "SAD-TEST-001.sad.md", fm)

    monkeypatch.setattr(sys, "argv", ["cli.py", "--target", str(tmp_path)])

    import engine.interfaces.cli as linter

    def mock_lint_file(*args, **kwargs):
        return [], True, False, {}

    def mock_resolve(*args, **kwargs):
        return (
            {"SAD-TEST-001"},
            {
                "SAD-TEST-001": {
                    "parent_pad": "PAD-TEST-001",
                    "governed_by": ["GDC-000"],
                    "_filepath": "SAD-TEST-001.sad.md",
                }
            },
            {},
        )

    monkeypatch.setattr(linter, "lint_file", mock_lint_file)
    monkeypatch.setattr(linter, "build_metadata_registry", mock_resolve)

    with pytest.raises(SystemExit) as e:
        linter.main()
    assert e.value.code == 0


def test_main_failing_run(tmp_path, monkeypatch):
    """main() should exit 1 when there are blocking errors."""
    fm = "doc_meta:\n  id: SAD-TEST-001"  # Missing required metadata
    (tmp_path / "systems").mkdir()
    _write_md(tmp_path / "systems", "SAD-TEST-001.sad.md", fm)
    monkeypatch.setattr(sys, "argv", ["cli.py", "--target", str(tmp_path / "systems")])

    with pytest.raises(SystemExit) as e:
        import engine.interfaces.cli as linter

        linter.main()
    assert e.value.code == 1


def test_main_json_format(tmp_path, monkeypatch):
    """main() in JSON format."""
    fm = "doc_meta:\n  id: SAD-TEST-001"
    (tmp_path / "systems").mkdir(exist_ok=True)
    _write_md(tmp_path / "systems", "SAD-TEST-001.sad.md", fm)

    monkeypatch.setattr(
        sys,
        "argv",
        ["cli.py", "--target", str(tmp_path / "systems"), "--format", "json"],
    )

    with pytest.raises(SystemExit) as e:
        import engine.interfaces.cli as linter

        linter.main()
    assert e.value.code == 1


def test_main_sarif_format(tmp_path, monkeypatch):
    """main() in SARIF format."""
    fm = "doc_meta:\n  id: SAD-TEST-001"
    (tmp_path / "systems").mkdir(exist_ok=True)
    _write_md(tmp_path / "systems", "SAD-TEST-001.sad.md", fm)

    monkeypatch.setattr(
        sys,
        "argv",
        ["cli.py", "--target", str(tmp_path / "systems"), "--format", "sarif"],
    )

    with pytest.raises(SystemExit) as e:
        import engine.interfaces.cli as linter

        linter.main()
    assert e.value.code == 1


def test_main_with_lint_disable_and_duplicates(tmp_path, monkeypatch):
    """Cover cli.py printing blocks for lint_disable, rejected disables, and duplicate IDs."""
    fm1 = (
        "doc_meta:\n  id: SAD-TEST-001\n  parent_pad: PAD-001\n  status: draft\n  last_reviewed: "
        + datetime.date.today().isoformat()
    )
    content1 = (
        "---\n"
        + fm1
        + "\n---\n<!-- lint_disable: structural_integrity_violation -->\n## Context"
    )
    fpath1 = tmp_path / "SAD-TEST-001.sad.md"
    fpath1.write_text(content1, encoding="utf-8")

    # Duplicate ID to trigger duplicate check
    fm2 = (
        "doc_meta:\n  id: SAD-TEST-001\n  parent_pad: PAD-001\n  status: draft\n  last_reviewed: "
        + datetime.date.today().isoformat()
    )
    content2 = (
        "---\n"
        + fm2
        + "\n---\n<!-- lint_disable: structural_integrity_violation (reason: ARB waiver) -->\n## Context"
    )
    fpath2 = tmp_path / "SAD-TEST-001-dupe.sad.md"
    fpath2.write_text(content2, encoding="utf-8")

    # Add --verbose to cover the verbose block too
    monkeypatch.setattr(sys, "argv", ["cli.py", "--target", str(tmp_path), "--verbose"])

    import engine.interfaces.cli as linter

    def mock_resolve(*args, **kwargs):
        # Force a duplicate ID to ensure line 278 is hit
        return (
            {"SAD-TEST-001"},
            {"SAD-TEST-001": {}},
            {"SAD-TEST-001": ["file1.md", "file2.md"]},
        )

    monkeypatch.setattr(linter, "build_metadata_registry", mock_resolve)

    with pytest.raises(SystemExit) as e:
        linter.main()

    # SAD-TEST-001 duplicate will trigger an ERROR and thus exit 1
    assert e.value.code == 1


def test_build_sarif_maps_levels():
    results = [
        {
            "file": "./a.md",
            "errors": [("CRITICAL", "c"), ("ERROR", "e"), ("WARNING", "w")],
        }
    ]
    doc = build_sarif(results, ("CRITICAL", "ERROR"))
    assert doc["version"] == "2.1.0"
    levels = [r["level"] for r in doc["runs"][0]["results"]]
    assert levels.count("error") == 2 and levels.count("warning") == 1
    assert (
        doc["runs"][0]["results"][0]["locations"][0]["physicalLocation"][
            "artifactLocation"
        ]["uri"]
        == "a.md"
    )


def test_build_sarif_empty_results():
    doc = build_sarif([], ("CRITICAL", "ERROR"))
    assert doc["version"] == "2.1.0"
    assert doc["runs"][0]["results"] == []


# ---------- FIX#4: non-destructive generator --check ----------


def _load_generator():
    gen_path = str(REPOSITORY_ROOT / "generators" / "generate_rules_doc.py")
    spec = importlib.util.spec_from_file_location("genrules", gen_path)
    assert spec is not None and spec.loader is not None, "Failed to load spec"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_cli_generator_check_non_destructive():
    gen = _load_generator()
    drift = gen.process(check=True)
    assert isinstance(drift, list)  # returns drift records, writes nothing


def test_lint_file_no_validator(tmp_path, monkeypatch):
    import engine.control.linting.facade as linter

    fm = "doc_meta:\n  id: SAD-TEST-001"
    fpath = _write_md(tmp_path, "SAD-TEST-001.sad.md", fm)
    monkeypatch.setattr(linter, "get_validator", lambda x: None)
    rules = _global_rules()
    errs, p, b, di = linter.lint_file(
        fpath,
        rules,
        rules.get("severity_levels", {}),
        tuple(rules.get("blocking_severities", ["CRITICAL", "ERROR"])),
        set(),
        {},
        "text",
    )
    assert any("No validator implemented" in msg for _, msg in errs)


def test_main_with_file_target(tmp_path, monkeypatch):
    import sys
    from engine.interfaces.cli import main

    fm = (
        "doc_meta:\n  id: SAD-TEST-001\n  parent_pad: PAD-TEST-001\n  status: approved\n  last_reviewed: "
        + datetime.date.today().isoformat()
    )
    (tmp_path / "systems").mkdir(exist_ok=True)
    fpath = _write_md(tmp_path / "systems", "SAD-TEST-001.sad.md", fm)
    monkeypatch.setattr(sys, "argv", ["cli.py", "--target", str(fpath)])

    # Also test stream reconfigure exception coverage
    class FakeStream:
        def reconfigure(self, **kwargs):
            raise AttributeError("mocked")

        def write(self, msg):
            pass

        def flush(self):
            pass

    monkeypatch.setattr(sys, "stdout", FakeStream())

    try:
        main()
    except SystemExit as e:
        assert e.code == 1


def test_lint_file_with_disables_and_warnings(tmp_path):
    fm = "doc_meta:\n  id: SAD-TEST-001\n  parent_pad: PAD-TEST-001\n  status: active"
    body = "<!-- lint_disable: prohibited_words -->\n<!-- lint_disable: ambiguity_rules (reason: reason) -->\n<!-- lint_disable: structural_integrity_violation -->"
    fpath = _write_md(tmp_path, "SAD-TEST-001.sad.md", fm, body)
    from engine.interfaces.cli import lint_file

    rules = _global_rules()
    errs, p, b, di = lint_file(
        fpath,
        rules,
        rules.get("severity_levels", {}),
        tuple(rules.get("blocking_severities", ["CRITICAL", "ERROR"])),
        set(),
        {},
        "text",
    )
    disabled = di["disabled"]
    rule1_disable = next((d for d in disabled if d[0] == "prohibited_words"), None)
    rule2_disable = next((d for d in disabled if d[0] == "ambiguity_rules"), None)
    assert rule1_disable is not None
    assert rule1_disable[1] is None  # no reason
    assert rule2_disable is not None
    assert rule2_disable[1] == "reason"


def test_tech_radar_failure(tmp_path, monkeypatch):
    import sys
    from engine.interfaces.cli import main

    fm = "doc_meta:\n  id: SAD-TEST-001"
    _write_md(tmp_path, "SAD-TEST-001.sad.md", fm)

    # Create invalid tech-radar.yaml inside mocked directories
    (tmp_path / "enterprise").mkdir()
    (tmp_path / "schemas").mkdir(parents=True)

    radar = tmp_path / "enterprise" / "tech-radar.yaml"
    radar.write_text("invalid_radar: true")

    # We need a valid schema so it attempts to validate and fails
    schema = tmp_path / "schemas" / "tech-radar.schema.json"
    schema.write_text('{"type": "object", "required": ["version"]}')

    # Mock schemas to force failure
    monkeypatch.setattr(sys, "argv", ["cli.py", "--target", str(tmp_path)])
    monkeypatch.setattr("engine.control.linting.facade.FRAMEWORK_ROOT", str(tmp_path))
    monkeypatch.setattr(
        "engine.interfaces.cli.BASE_SCHEMA_PATH", "fake"
    )  # Just so it doesn't crash on base schema loading

    def mock_load_json(path):
        return {
            "x-global-config": {
                "severity_levels": {
                    "mock_group": {r.value: "ERROR" for r in SeverityRule}
                },
                "blocking_severities": ["CRITICAL", "ERROR"],
                "structure_rules": {
                    "artifact_directories": {},
                    "max_directory_depth": 3,
                    "ignored_files": {},
                },
                "content_rules": {
                    "lifecycle_age_rules": [],
                    "min_content_length_chars": {"value": 50},
                    "max_review_age_days": {"value": 365},
                },
            }
        }

    monkeypatch.setattr("engine.interfaces.cli.load_json_schema_file", mock_load_json)

    with pytest.raises(SystemExit) as e:
        main()

    assert e.value.code == 1


def test_tech_radar_yaml_parse_error(tmp_path, monkeypatch):
    """Test tech radar parsing exception."""
    import sys
    from engine.interfaces.cli import main

    _write_md(tmp_path, "SAD-TEST-001.sad.md", "doc_meta:\n  id: SAD-TEST-001")
    (tmp_path / "enterprise").mkdir()
    radar = tmp_path / "enterprise" / "tech-radar.yaml"
    radar.write_text("invalid\n  yaml: : :")
    schema = tmp_path / "enterprise" / "schema.json"
    schema.write_text("{}")

    monkeypatch.setattr(sys, "argv", ["cli.py", "--target", str(tmp_path)])
    monkeypatch.setattr("engine.interfaces.cli.TECH_RADAR_YAML_PATH", str(radar))
    monkeypatch.setattr("engine.interfaces.cli.TECH_RADAR_SCHEMA_PATH", str(schema))
    monkeypatch.setattr("engine.interfaces.cli.BASE_SCHEMA_PATH", "fake")
    monkeypatch.setattr(
        "engine.interfaces.cli.load_json_schema_file",
        lambda p: {
            "x-global-config": {
                "severity_levels": {
                    "mock_group": {r.value: "ERROR" for r in SeverityRule}
                },
                "blocking_severities": ["CRITICAL", "ERROR"],
                "structure_rules": {
                    "artifact_directories": {},
                    "max_directory_depth": 3,
                    "ignored_files": {},
                },
                "content_rules": {
                    "lifecycle_age_rules": [],
                    "min_content_length_chars": {"value": 50},
                    "max_review_age_days": {"value": 365},
                },
            }
        },
    )

    with pytest.raises(SystemExit) as e:
        main()
    assert e.value.code == 1


def test_tech_radar_validation_error_json(tmp_path, monkeypatch):
    """Test tech radar jsonschema error in JSON mode."""
    import sys
    from engine.interfaces.cli import main

    _write_md(tmp_path, "SAD-TEST-001.sad.md", "doc_meta:\n  id: SAD-TEST-001")
    (tmp_path / "enterprise").mkdir()
    radar = tmp_path / "enterprise" / "tech-radar.yaml"
    radar.write_text(
        "version: 1"
    )  # valid yaml, invalid schema (assuming missing required fields)
    schema = tmp_path / "enterprise" / "schema.json"
    schema.write_text('{"type": "object", "required": ["missing_field"]}')

    monkeypatch.setattr(
        sys, "argv", ["cli.py", "--target", str(tmp_path), "--format", "json"]
    )
    monkeypatch.setattr("engine.interfaces.cli.TECH_RADAR_YAML_PATH", str(radar))
    monkeypatch.setattr("engine.interfaces.cli.TECH_RADAR_SCHEMA_PATH", str(schema))
    monkeypatch.setattr("engine.interfaces.cli.BASE_SCHEMA_PATH", "fake")
    monkeypatch.setattr(
        "engine.interfaces.cli.load_json_schema_file",
        lambda p: {
            "x-global-config": {
                "severity_levels": {
                    "mock_group": {r.value: "ERROR" for r in SeverityRule}
                },
                "blocking_severities": ["CRITICAL", "ERROR"],
                "structure_rules": {
                    "artifact_directories": {},
                    "max_directory_depth": 3,
                    "ignored_files": {},
                },
                "content_rules": {
                    "lifecycle_age_rules": [],
                    "min_content_length_chars": {"value": 50},
                    "max_review_age_days": {"value": 365},
                },
            }
        },
    )

    with pytest.raises(SystemExit) as e:
        main()
    assert e.value.code == 1


def test_main_filters(tmp_path, monkeypatch):
    """Test Filter 2 (README) and Filter 3 (.copy.md)."""
    import sys
    from engine.interfaces.cli import main

    (tmp_path / "README.md").write_text("# Readme")
    (tmp_path / "test.copy.md").write_text("# Copy")

    monkeypatch.setattr(sys, "argv", ["cli.py", "--target", str(tmp_path)])
    monkeypatch.setattr("engine.control.linting.facade.FRAMEWORK_ROOT", str(tmp_path))
    monkeypatch.setattr("engine.interfaces.cli.TECH_RADAR_YAML_PATH", "fake")
    monkeypatch.setattr("engine.interfaces.cli.BASE_SCHEMA_PATH", "fake")
    monkeypatch.setattr(
        "engine.interfaces.cli.load_json_schema_file",
        lambda p: {
            "x-global-config": {
                "severity_levels": {
                    "mock_group": {r.value: "ERROR" for r in SeverityRule}
                },
                "blocking_severities": ["CRITICAL", "ERROR"],
                "structure_rules": {
                    "artifact_directories": {},
                    "max_directory_depth": 3,
                    "ignored_files": {
                        "exact_matches": ["readme.md"],
                        "patterns": [r".*\.copy\.md$"],
                    },
                },
                "content_rules": {
                    "lifecycle_age_rules": [],
                    "min_content_length_chars": {"value": 50},
                    "max_review_age_days": {"value": 365},
                },
            }
        },
    )

    with pytest.raises(SystemExit) as e:
        main()
    assert e.value.code == 0


def test_main_global_auditors_json(tmp_path, monkeypatch):
    """Test global auditor errors appending to JSON format output."""
    import sys
    import engine.interfaces.cli as linter

    _write_md(tmp_path, "SAD-TEST-001.sad.md", "doc_meta:\n  id: SAD-TEST-001")

    monkeypatch.setattr(
        sys, "argv", ["cli.py", "--target", str(tmp_path), "--format", "json"]
    )
    monkeypatch.setattr(linter, "TECH_RADAR_YAML_PATH", "fake")
    monkeypatch.setattr(linter, "BASE_SCHEMA_PATH", "fake")
    monkeypatch.setattr(
        linter,
        "load_json_schema_file",
        lambda p: {
            "x-global-config": {
                "severity_levels": {
                    "mock_group": {r.value: "ERROR" for r in SeverityRule}
                },
                "blocking_severities": ["CRITICAL", "ERROR"],
                "structure_rules": {
                    "artifact_directories": {},
                    "max_directory_depth": 3,
                    "ignored_files": {},
                },
                "content_rules": {
                    "lifecycle_age_rules": [],
                    "min_content_length_chars": {"value": 50},
                    "max_review_age_days": {"value": 365},
                },
            }
        },
    )

    # Mock lint_file to pass cleanly so global auditors run
    monkeypatch.setattr(
        linter,
        "lint_file",
        lambda *args, **kwargs: ([], True, False, {"disabled": {}, "rejected": set()}),
    )

    # Mock auditors to return fake errors
    monkeypatch.setattr(
        linter,
        "audit_circular_dependencies",
        lambda m, s: [("file.md", "ERROR", "Circular dep error")],
    )
    monkeypatch.setattr(
        linter,
        "audit_version_bump",
        lambda m, s: [("ERROR", "Version bump error", "file.md")],
    )
    monkeypatch.setattr(
        linter,
        "audit_traceability_graph",
        lambda m: [("structural_integrity_violation", "Traceability error")],
    )
    monkeypatch.setattr(
        linter,
        "audit_waiver_expirations",
        lambda m, s: [("file.md", "ERROR", "Waiver error")],
    )
    monkeypatch.setattr(
        linter,
        "audit_duplicate_ids",
        lambda d, s: [("ERROR", "Duplicate error", "file.md")],
    )
    monkeypatch.setattr(
        linter, "audit_orphans", lambda m, s: [("ERROR", "Orphan error", "file.md")]
    )
    monkeypatch.setattr(
        linter,
        "audit_hierarchy_tiers",
        lambda m, s: [("ERROR", "Hierarchy error", "file.md")],
    )

    with pytest.raises(SystemExit) as e:
        linter.main()
    assert e.value.code == 1


def test_main_directory_depth_violation(tmp_path, monkeypatch):
    """Test max directory depth violation (CRITICAL-11) in cli.py."""
    import sys
    import engine.interfaces.cli as linter

    monkeypatch.chdir(tmp_path)

    # Create a deep directory structure (4 levels deep)
    deep_dir = tmp_path / "lvl1" / "lvl2" / "lvl3" / "lvl4"
    deep_dir.mkdir(parents=True)
    fpath = deep_dir / "SAD-TEST-001.sad.md"
    fpath.write_text("doc_meta:\n  id: SAD-TEST-001")

    # We must mock os.path.relpath so that it treats tmp_path as '.' to get 4 levels deep
    import os

    original_relpath = os.path.relpath

    def mock_relpath(path, start=None):
        if path == str(fpath):
            return "lvl1/lvl2/lvl3/lvl4/SAD-TEST-001.sad.md".replace("/", os.sep)
        return original_relpath(path, start)

    monkeypatch.setattr(os.path, "relpath", mock_relpath)
    monkeypatch.setattr(
        sys, "argv", ["cli.py", "--target", str(deep_dir), "--format", "json"]
    )
    monkeypatch.setattr(linter, "TECH_RADAR_YAML_PATH", "fake")
    monkeypatch.setattr(linter, "BASE_SCHEMA_PATH", "fake")
    monkeypatch.setattr(
        linter,
        "load_json_schema_file",
        lambda p: {
            "x-global-config": {
                "severity_levels": {
                    "mock_group": {r.value: "ERROR" for r in SeverityRule}
                },
                "blocking_severities": ["CRITICAL", "ERROR"],
                "structure_rules": {
                    "artifact_directories": {},
                    "max_directory_depth": 3,
                    "ignored_files": {},
                },
                "content_rules": {
                    "lifecycle_age_rules": [],
                    "min_content_length_chars": {"value": 50},
                    "max_review_age_days": {"value": 365},
                },
            }
        },
    )
    monkeypatch.setattr(
        linter, "build_metadata_registry", lambda *args, **kwargs: (set(), {}, {})
    )

    with pytest.raises(SystemExit) as e:
        linter.main()
    assert e.value.code == 1


def test_main_skipped_target_json(tmp_path, monkeypatch):
    """Test skipped target warning in JSON format."""
    import sys
    from engine.interfaces.cli import main

    invalid_dir = tmp_path / "invalid_dir"
    invalid_dir.mkdir()
    (tmp_path / ".git").mkdir()
    fpath = invalid_dir / "target.md"
    fpath.write_text("content")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys, "argv", ["cli.py", "--target", str(invalid_dir), "--format", "json"]
    )
    monkeypatch.setattr("engine.control.linting.facade.FRAMEWORK_ROOT", str(tmp_path))
    monkeypatch.setattr("engine.interfaces.cli.BASE_SCHEMA_PATH", "fake")

    def mock_load_json(path):
        return {
            "x-global-config": {
                "structure_rules": {"artifact_directories": {"01": "allowed_dir"}}
            }
        }

    monkeypatch.setattr("engine.interfaces.cli.load_json_schema_file", mock_load_json)

    with pytest.raises(SystemExit) as e:
        main()
    assert e.value.code == 1

