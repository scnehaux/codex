import pytest
import sys

from engine.interfaces.cli import _merge_reference_registry, _validate_execution_root, main


def test_merge_reference_registry_resolves_cross_repo_ids_and_duplicates():
    local = (
        {"TDD-service-001", "SAD-001"},
        {
            "TDD-service-001": {"_filepath": "docs/designs/TDD-service-001.md"},
            "SAD-001": {"_filepath": "docs/designs/SAD-001.md"},
        },
        {},
    )
    reference = (
        {"SAD-001", "PAD-PLT-001"},
        {
            "SAD-001": {"_filepath": "04-system/SAD-001.md"},
            "PAD-PLT-001": {"_filepath": "03-domain/PAD-PLT-001.md"},
        },
        {},
    )

    ids, metadata, duplicates = _merge_reference_registry(local, reference)

    assert ids == {"TDD-service-001", "SAD-001", "PAD-PLT-001"}
    assert metadata["PAD-PLT-001"]["_filepath"].startswith("03-domain")
    assert duplicates["SAD-001"] == [
        "04-system/SAD-001.md",
        "docs/designs/SAD-001.md",
    ]


def test_validate_execution_root_fails_without_git(tmp_path, monkeypatch):
    # tmp_path does not have a .git folder
    with pytest.raises(SystemExit) as exc_info:
        _validate_execution_root(str(tmp_path))
    assert exc_info.value.code == 1


def test_validate_execution_root_passes_with_git(tmp_path):
    # Create a fake .git directory
    (tmp_path / ".git").mkdir()
    # Should not raise SystemExit
    _validate_execution_root(str(tmp_path))
    assert True


def test_main_missing_global_config(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["cli.py"])
    monkeypatch.setattr('engine.interfaces.cli._validate_execution_root', lambda x: None)
    monkeypatch.setattr('engine.interfaces.cli.load_json_schema_file', lambda p: {})

    with pytest.raises(SystemExit) as e:
        main()
    assert e.value.code == 1


def test_main_missing_blocking_severities(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["cli.py"])
    monkeypatch.setattr('engine.interfaces.cli._validate_execution_root', lambda x: None)
    monkeypatch.setattr(
        'engine.interfaces.cli.load_json_schema_file',
        lambda p: {"x-global-config": {"severity_levels": {"mock": {"rule": "ERROR"}}}},
    )

    with pytest.raises(SystemExit) as e:
        main()
    assert e.value.code == 1


def test_main_invalid_severity_schema(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["cli.py"])
    monkeypatch.setattr('engine.interfaces.cli._validate_execution_root', lambda x: None)
    monkeypatch.setattr(
        'engine.interfaces.cli.load_json_schema_file',
        lambda p: {
            "x-global-config": {
                "severity_levels": {"mock": {"rule": "INVALID_SEV"}},
                "blocking_severities": ["CRITICAL"],
            }
        },
    )

    with pytest.raises(SystemExit) as e:
        main()
    assert e.value.code == 1


def test_main_break_glass(tmp_path, monkeypatch):

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()

    monkeypatch.setattr(
        sys, "argv", ["cli.py", "--break-glass", "--target", str(tmp_path)]
    )
    monkeypatch.setattr(
        'engine.interfaces.cli.gather_markdown_paths',
        lambda *args, **kwargs: [str(tmp_path / "doc.md")],
    )

    # Mock lint_file returning a blocking error
    def mock_lint(*args, **kwargs):
        return (
            [("CRITICAL", "blocking error")],
            False,
            True,
            {
                "disabled": [("mock_rule", "reason", 10, 20)],
                "rejected": {"CRITICAL_RULE"},
            },
        )

    monkeypatch.setattr('engine.interfaces.cli.lint_file', mock_lint)

    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    assert (tmp_path / "break-glass-audit.log").exists()


def test_main_json_and_sarif_format(tmp_path, monkeypatch):

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()

    monkeypatch.setattr(
        'engine.interfaces.cli.gather_markdown_paths',
        lambda *args, **kwargs: [str(tmp_path / "doc.md")],
    )

    def mock_lint(*args, **kwargs):
        return (
            [],
            True,
            False,
            {"disabled": {}, "rejected": set()},
        )

    monkeypatch.setattr('engine.interfaces.cli.lint_file', mock_lint)

    # Test json format exit 0
    monkeypatch.setattr(
        sys, "argv", ["cli.py", "--format", "json", "--target", str(tmp_path)]
    )
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0

    # Test sarif format exit 0
    monkeypatch.setattr(
        sys, "argv", ["cli.py", "--format", "sarif", "--target", str(tmp_path)]
    )
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0

def test_main_reference_root_path(tmp_path, monkeypatch):
    import engine.interfaces.cli as linter

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()
    reference = tmp_path / "reference"
    reference.mkdir()
    (reference / ".git").mkdir()

    monkeypatch.setattr(
        sys,
        "argv",
        ["cli.py", "--target", str(tmp_path), "--reference-root", str(reference)],
    )

    local = ({"GDC-000"}, {"GDC-000": {
                "governed_by": ["GDC-000"],"_filepath": "00-governance/GDC-000.md"}}, {})
    remote = ({"PAD-EXAMPLE-001"}, {"PAD-EXAMPLE-001": {"_filepath": "03-domain/x.md"}}, {})
    calls = iter([local, remote])
    monkeypatch.setattr(linter, "build_metadata_registry", lambda *a, **k: next(calls))
    monkeypatch.setattr(linter, "gather_markdown_paths", lambda *a, **k: [])

    with pytest.raises(SystemExit) as exc:
        linter.main()
    assert exc.value.code == 0


def test_main_validates_present_tech_radar(tmp_path, monkeypatch):
    import json
    import engine.interfaces.cli as linter

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()
    radar = tmp_path / "tech-radar.yaml"
    schema = tmp_path / "tech-radar.schema.json"
    radar.write_text("technologies: []\n", encoding="utf-8")
    schema.write_text(json.dumps({"type": "object", "required": ["technologies"]}), encoding="utf-8")

    monkeypatch.setattr(linter, "TECH_RADAR_YAML_PATH", str(radar))
    monkeypatch.setattr(linter, "TECH_RADAR_SCHEMA_PATH", str(schema))
    monkeypatch.setattr(linter, "build_metadata_registry", lambda *a, **k: (set(), {}, {}))
    monkeypatch.setattr(linter, "gather_markdown_paths", lambda *a, **k: [])
    monkeypatch.setattr(sys, "argv", ["cli.py", "--target", str(tmp_path)])

    with pytest.raises(SystemExit) as exc:
        linter.main()
    assert exc.value.code == 0


def test_main_invalid_tech_radar_is_blocking(tmp_path, monkeypatch):
    import json
    import engine.interfaces.cli as linter

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()
    radar = tmp_path / "tech-radar.yaml"
    schema = tmp_path / "tech-radar.schema.json"
    radar.write_text("wrong: true\n", encoding="utf-8")
    schema.write_text(json.dumps({"type": "object", "required": ["technologies"]}), encoding="utf-8")

    monkeypatch.setattr(linter, "TECH_RADAR_YAML_PATH", str(radar))
    monkeypatch.setattr(linter, "TECH_RADAR_SCHEMA_PATH", str(schema))
    monkeypatch.setattr(linter, "build_metadata_registry", lambda *a, **k: (set(), {}, {}))
    monkeypatch.setattr(linter, "gather_markdown_paths", lambda *a, **k: [])
    monkeypatch.setattr(sys, "argv", ["cli.py", "--target", str(tmp_path)])

    with pytest.raises(SystemExit) as exc:
        linter.main()
    assert exc.value.code == 1

def test_main_registry_boundary_error_is_fatal(tmp_path, monkeypatch):
    # A crawler/registry boundary violation must terminate the production CLI.
    import engine.interfaces.cli as linter

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()
    monkeypatch.setattr(
        linter,
        "build_metadata_registry",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("registry boundary violation")),
    )
    monkeypatch.setattr(sys, "argv", ["cli.py", "--target", str(tmp_path)])

    with pytest.raises(SystemExit) as exc:
        linter.main()

    assert exc.value.code == 1


def test_main_without_ignore_config_uses_empty_defaults(tmp_path, monkeypatch):
    # No ignored-files config is a supported runtime configuration.
    import copy
    import engine.interfaces.cli as linter

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()

    base_schema = linter.load_json_schema_file(linter.BASE_SCHEMA_PATH)
    global_rules, severity_levels, blocking = linter.parse_and_validate_global_config(
        copy.deepcopy(base_schema)
    )
    global_rules[linter.SCHEMA_KEY_STRUCTURE_RULES][
        linter.SCHEMA_KEY_IGNORED_FILES
    ] = {}

    monkeypatch.setattr(
        linter,
        "parse_and_validate_global_config",
        lambda schema: (global_rules, severity_levels, blocking),
    )
    monkeypatch.setattr(
        linter, "build_metadata_registry", lambda *args, **kwargs: (set(), {}, {})
    )
    monkeypatch.setattr(linter, "gather_markdown_paths", lambda *args, **kwargs: [])
    monkeypatch.setattr(sys, "argv", ["cli.py", "--target", str(tmp_path)])

    with pytest.raises(SystemExit) as exc:
        linter.main()

    assert exc.value.code == 0


def test_main_tolerates_streams_without_reconfigure(tmp_path, monkeypatch):
    # The console compatibility fallback is a reachable runtime path.
    import engine.interfaces.cli as linter

    class NonReconfigurableStream:
        def write(self, data):
            return len(data)

        def flush(self):
            return None

        def reconfigure(self, **kwargs):
            raise AttributeError("reconfigure unavailable")

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()
    monkeypatch.setattr(linter, "build_metadata_registry", lambda *a, **k: (set(), {}, {}))
    monkeypatch.setattr(linter, "gather_markdown_paths", lambda *a, **k: [])
    monkeypatch.setattr(sys, "stdout", NonReconfigurableStream())
    monkeypatch.setattr(sys, "stderr", NonReconfigurableStream())
    monkeypatch.setattr(sys, "argv", ["cli.py", "--format", "json", "--target", str(tmp_path)])

    with pytest.raises(SystemExit) as exc:
        linter.main()

    assert exc.value.code == 0
