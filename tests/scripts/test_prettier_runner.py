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


def test_resolve_npx_posix(monkeypatch):
    module = load()
    monkeypatch.setattr(
        module.shutil,
        "which",
        lambda name: "/usr/bin/npx" if name == "npx" else None,
    )

    assert module._resolve_npx(platform_name="posix") == "/usr/bin/npx"


def test_resolve_npx_windows_prefers_npx_cmd(monkeypatch):
    module = load()

    def which(name):
        if name == "npx.cmd":
            return r"C:\Program Files\nodejs\npx.cmd"
        if name == "npx":
            return r"C:\Program Files\nodejs\npx"
        return None

    monkeypatch.setattr(module.shutil, "which", which)

    assert module._resolve_npx(platform_name="nt") == r"C:\Program Files\nodejs\npx.cmd"


def test_missing_npx_fails_closed(monkeypatch):
    module = load()
    monkeypatch.setattr(module.shutil, "which", lambda name: None)

    with pytest.raises(RuntimeError, match="npx is not available"):
        module._resolve_npx(platform_name="posix")


@pytest.mark.parametrize(
    ("mode", "option"),
    (("check", "--check"), ("write", "--write")),
)
def test_prettier_args_are_pinned_and_mode_specific(mode, option):
    module = load()

    command = module._prettier_args(mode, npx="/usr/bin/npx")

    assert command == [
        "/usr/bin/npx",
        "--yes",
        "prettier@3.9.6",
        option,
        "**/*.md",
        "**/*.json",
    ]


def test_invalid_mode_is_rejected():
    module = load()

    with pytest.raises(ValueError, match="mode must be"):
        module._prettier_args("invalid", npx="/usr/bin/npx")


@pytest.mark.parametrize(
    ("mode", "option"),
    (("check", "--check"), ("write", "--write")),
)
def test_run_prettier_resolves_builds_and_executes(
    monkeypatch,
    tmp_path,
    mode,
    option,
):
    module = load()
    seen = {}

    monkeypatch.setattr(module, "_resolve_npx", lambda: "/usr/bin/npx")

    def execute(command, *, cwd, platform_name=None):
        seen["command"] = command
        seen["cwd"] = cwd
        seen["platform_name"] = platform_name
        return 7

    monkeypatch.setattr(module, "_execute", execute)

    assert module.run_prettier(mode, cwd=tmp_path) == 7
    assert seen["command"] == [
        "/usr/bin/npx",
        "--yes",
        "prettier@3.9.6",
        option,
        "**/*.md",
        "**/*.json",
    ]
    assert seen["cwd"] == tmp_path
    assert seen["platform_name"] is None


def test_main_supports_check_and_write(monkeypatch):
    module = load()
    seen = []

    monkeypatch.setattr(
        module,
        "run_prettier",
        lambda mode: seen.append(mode) or 0,
    )

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
