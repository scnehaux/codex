import pytest
import sys

from engine.interfaces.cli import (
    _merge_reference_registry,
    _validate_execution_root,
    main,
)


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
            "SAD-001": {"_filepath": "systems/SAD-001.md"},
            "PAD-PLT-001": {"_filepath": "domains/PAD-PLT-001.md"},
        },
        {},
    )

    ids, metadata, duplicates = _merge_reference_registry(local, reference)

    assert ids == {"TDD-service-001", "SAD-001", "PAD-PLT-001"}
    assert metadata["PAD-PLT-001"]["_filepath"].startswith("domains")
    assert duplicates["SAD-001"] == [
        "systems/SAD-001.md",
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


@pytest.mark.parametrize(
    "message",
    [
        "framework unavailable",
        "blocking severity policy invalid",
        "severity mapping invalid",
    ],
)
def test_main_framework_policy_failure_is_fatal(monkeypatch, message):
    monkeypatch.setattr(sys, "argv", ["cli.py"])
    monkeypatch.setattr(
        "engine.interfaces.cli._validate_execution_root", lambda x: None
    )

    def fail():
        raise RuntimeError(message)

    monkeypatch.setattr("engine.interfaces.cli.executable_framework", fail)

    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1


def test_main_break_glass(tmp_path, monkeypatch):

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()

    monkeypatch.setattr(
        sys, "argv", ["cli.py", "--break-glass", "--target", str(tmp_path)]
    )
    monkeypatch.setattr(
        "engine.interfaces.cli.gather_markdown_paths",
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

    monkeypatch.setattr("engine.interfaces.cli.lint_file", mock_lint)

    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    assert (tmp_path / "break-glass-audit.log").exists()


def test_main_json_and_sarif_format(tmp_path, monkeypatch):

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()

    monkeypatch.setattr(
        "engine.interfaces.cli.gather_markdown_paths",
        lambda *args, **kwargs: [str(tmp_path / "doc.md")],
    )

    def mock_lint(*args, **kwargs):
        return (
            [],
            True,
            False,
            {"disabled": {}, "rejected": set()},
        )

    monkeypatch.setattr("engine.interfaces.cli.lint_file", mock_lint)

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

    local = (
        {"GDC-000"},
        {
            "GDC-000": {
                "governed_by": ["GDC-000"],
                "_filepath": "governance/GDC-000.md",
            }
        },
        {},
    )
    remote = (
        {"PAD-EXAMPLE-001"},
        {"PAD-EXAMPLE-001": {"_filepath": "domains/x.md"}},
        {},
    )
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
    schema.write_text(
        json.dumps({"type": "object", "required": ["technologies"]}), encoding="utf-8"
    )

    monkeypatch.setattr(linter, "TECH_RADAR_YAML_PATH", str(radar))
    monkeypatch.setattr(linter, "TECH_RADAR_SCHEMA_PATH", str(schema))
    monkeypatch.setattr(
        linter, "build_metadata_registry", lambda *a, **k: (set(), {}, {})
    )
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
    schema.write_text(
        json.dumps({"type": "object", "required": ["technologies"]}), encoding="utf-8"
    )

    monkeypatch.setattr(linter, "TECH_RADAR_YAML_PATH", str(radar))
    monkeypatch.setattr(linter, "TECH_RADAR_SCHEMA_PATH", str(schema))
    monkeypatch.setattr(
        linter, "build_metadata_registry", lambda *a, **k: (set(), {}, {})
    )
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
        lambda *args, **kwargs: (_ for _ in ()).throw(
            ValueError("registry boundary violation")
        ),
    )
    monkeypatch.setattr(sys, "argv", ["cli.py", "--target", str(tmp_path)])

    with pytest.raises(SystemExit) as exc:
        linter.main()

    assert exc.value.code == 1


def test_main_without_ignore_config_uses_empty_defaults(tmp_path, monkeypatch):
    from dataclasses import replace
    import engine.interfaces.cli as linter

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()

    framework = linter.executable_framework()
    repository = replace(
        framework.governance.repository,
        ignored_files=(),
        ignored_patterns=(),
    )
    governance = replace(framework.governance, repository=repository)
    runtime = replace(framework, governance=governance)

    monkeypatch.setattr(linter, "executable_framework", lambda: runtime)
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
    monkeypatch.setattr(
        linter, "build_metadata_registry", lambda *a, **k: (set(), {}, {})
    )
    monkeypatch.setattr(linter, "gather_markdown_paths", lambda *a, **k: [])
    monkeypatch.setattr(sys, "stdout", NonReconfigurableStream())
    monkeypatch.setattr(sys, "stderr", NonReconfigurableStream())
    monkeypatch.setattr(
        sys, "argv", ["cli.py", "--format", "json", "--target", str(tmp_path)]
    )

    with pytest.raises(SystemExit) as exc:
        linter.main()

    assert exc.value.code == 0
