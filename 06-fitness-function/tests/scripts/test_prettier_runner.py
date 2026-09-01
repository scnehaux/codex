from __future__ import annotations

import pytest

from importlib import util
from tests.support.repository import REPOSITORY_ROOT


SCRIPT = (
    REPOSITORY_ROOT
    / "06-fitness-function"
    / "scripts"
    / "prettier_runner.py"
)


def load():
    spec = util.spec_from_file_location("prettier_runner", SCRIPT)
    module = util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_posix_command_uses_direct_npx(monkeypatch):
    module = load()
    monkeypatch.setattr(module.os, "name", "posix")
    monkeypatch.setattr(
        module.shutil,
        "which",
        lambda name: "/usr/bin/npx" if name == "npx" else None,
    )

    command = module._npx_command(["--check"])

    assert command == [
        "/usr/bin/npx",
        "--yes",
        "prettier@3.9.6",
        "--check",
        "**/*.md",
        "**/*.json",
    ]


def test_windows_command_uses_comspec_and_quotes_npx_path(monkeypatch):
    module = load()
    monkeypatch.setattr(module.os, "name", "nt")
    monkeypatch.setenv("COMSPEC", r"C:\Windows\System32\cmd.exe")

    def which(name):
        if name == "npx.cmd":
            return r"C:\Program Files\nodejs\npx.cmd"
        return None

    monkeypatch.setattr(module.shutil, "which", which)

    command = module._npx_command(["--write"])

    assert command[:4] == [
        r"C:\Windows\System32\cmd.exe",
        "/d",
        "/s",
        "/c",
    ]
    assert '"C:\\Program Files\\nodejs\\npx.cmd"' in command[4]
    assert "prettier@3.9.6" in command[4]
    assert "--write" in command[4]


def test_missing_npx_fails_closed(monkeypatch):
    module = load()
    monkeypatch.setattr(module.shutil, "which", lambda name: None)

    with pytest.raises(RuntimeError, match="npx is not available"):
        module._npx_command(["--check"])


def test_missing_windows_command_processor_fails_closed(monkeypatch):
    module = load()
    monkeypatch.setattr(module.os, "name", "nt")
    monkeypatch.delenv("COMSPEC", raising=False)

    def which(name):
        if name == "npx.cmd":
            return r"C:\Program Files\nodejs\npx.cmd"
        return None

    monkeypatch.setattr(module.shutil, "which", which)

    with pytest.raises(RuntimeError, match="command processor"):
        module._npx_command(["--check"])


@pytest.mark.parametrize(
    ("mode", "option"),
    (("write", "--write"), ("check", "--check")),
)
def test_run_prettier_invokes_expected_mode(monkeypatch, tmp_path, mode, option):
    module = load()
    seen = {}

    monkeypatch.setattr(
        module,
        "_npx_command",
        lambda args: ["runner", *args],
    )

    class Result:
        returncode = 7

    def fake_run(command, cwd, check):
        seen["command"] = command
        seen["cwd"] = cwd
        seen["check"] = check
        return Result()

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    assert module.run_prettier(mode, cwd=tmp_path) == 7
    assert seen["command"] == ["runner", option]
    assert seen["cwd"] == tmp_path
    assert seen["check"] is False


def test_invalid_mode_is_rejected():
    module = load()

    with pytest.raises(ValueError, match="mode must be"):
        module.run_prettier("invalid")


def test_main_success_and_failure(monkeypatch, capsys):
    module = load()
    monkeypatch.setattr(module, "run_prettier", lambda mode: 0)

    assert module.main(["--check"]) == 0

    def fail(mode):
        raise RuntimeError("broken")

    monkeypatch.setattr(module, "run_prettier", fail)

    assert module.main(["--write"]) == 1
    assert "broken" in capsys.readouterr().out
