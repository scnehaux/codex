from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[2] / "scripts" / "prettier_runner.py"


def load():
    spec = importlib.util.spec_from_file_location("prettier_runner", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("platform_name", "name"), (("posix", "prettier"), ("nt", "prettier.cmd"))
)
def test_resolve_prettier_uses_locked_local_binary(tmp_path, platform_name, name):
    module = load()
    binary = tmp_path / "node_modules" / ".bin" / name
    binary.parent.mkdir(parents=True)
    binary.write_text("stub", encoding="utf-8")
    assert module._resolve_prettier(cwd=tmp_path, platform_name=platform_name) == str(
        binary
    )


def test_missing_locked_prettier_fails_closed(tmp_path):
    module = load()
    with pytest.raises(RuntimeError, match="npm ci"):
        module._resolve_prettier(cwd=tmp_path, platform_name="posix")


@pytest.mark.parametrize(
    ("mode", "option"), (("check", "--check"), ("write", "--write"))
)
def test_prettier_args_are_local_and_mode_specific(mode, option):
    module = load()
    assert module._prettier_args(
        mode, executable="/repo/node_modules/.bin/prettier"
    ) == ["/repo/node_modules/.bin/prettier", option, "**/*.md", "**/*.json"]


def test_invalid_mode_is_rejected():
    module = load()
    with pytest.raises(ValueError, match="mode must be"):
        module._prettier_args("invalid", executable="prettier")


@pytest.mark.parametrize(
    ("mode", "option"), (("check", "--check"), ("write", "--write"))
)
def test_run_prettier_resolves_builds_and_executes(monkeypatch, tmp_path, mode, option):
    module = load()
    seen = {}
    monkeypatch.setattr(
        module, "_resolve_prettier", lambda **kwargs: "/repo/node_modules/.bin/prettier"
    )

    def execute(command, *, cwd, platform_name=None):
        seen["command"] = command
        seen["cwd"] = cwd
        return 7

    monkeypatch.setattr(module, "_execute", execute)
    assert module.run_prettier(mode, cwd=tmp_path) == 7
    assert seen["command"] == [
        "/repo/node_modules/.bin/prettier",
        option,
        "**/*.md",
        "**/*.json",
    ]
    assert seen["cwd"] == tmp_path


def test_main_supports_check_and_write(monkeypatch):
    module = load()
    seen = []
    monkeypatch.setattr(module, "run_prettier", lambda mode: seen.append(mode) or 0)
    assert module.main(["--check"]) == 0
    assert module.main(["--write"]) == 0
    assert seen == ["check", "write"]


def test_main_returns_one_for_runtime_failure(monkeypatch, capsys):
    module = load()

    def fail(mode):
        raise RuntimeError("broken")

    monkeypatch.setattr(module, "run_prettier", fail)
    assert module.main(["--check"]) == 1
    assert "[FAIL] broken" in capsys.readouterr().out


def test_cli_requires_exactly_one_mode():
    module = load()
    with pytest.raises(SystemExit) as missing:
        module.main([])
    assert missing.value.code == 2
    with pytest.raises(SystemExit) as conflicting:
        module.main(["--check", "--write"])
    assert conflicting.value.code == 2
