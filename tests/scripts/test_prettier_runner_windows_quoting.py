from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[2] / "scripts" / "prettier_runner.py"


def load():
    spec = importlib.util.spec_from_file_location(
        "prettier_runner_windows_quoting",
        SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_windows_command_has_one_executable_quote_layer():
    module = load()
    npx = r"C:\Program Files\nodejs\npx.cmd"

    command = module._windows_command_string([npx, "--version"])

    assert command == f'"{npx}" --version'
    assert r"\"" not in command


def test_empty_windows_command_fails_closed():
    module = load()

    with pytest.raises(RuntimeError, match="at least one argument"):
        module._windows_command_string([])


def test_windows_execute_uses_explicit_command_processor(
    monkeypatch,
    tmp_path,
):
    module = load()
    npx = r"C:\Program Files\nodejs\npx.cmd"
    comspec = r"C:\Windows\System32\cmd.exe"
    captured = {}

    class Result:
        returncode = 0

    monkeypatch.setenv("COMSPEC", comspec)

    def fake_run(command, cwd, check, shell, executable=None):
        captured["command"] = command
        captured["cwd"] = cwd
        captured["check"] = check
        captured["shell"] = shell
        captured["executable"] = executable
        return Result()

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    assert (
        module._execute(
            [npx, "--version"],
            cwd=tmp_path,
            platform_name="nt",
        )
        == 0
    )
    assert captured["command"] == f'"{npx}" --version'
    assert captured["cwd"] == tmp_path
    assert captured["shell"] is True
    assert captured["executable"] == comspec
    assert captured["check"] is False


def test_missing_windows_command_processor_fails_closed(
    monkeypatch,
    tmp_path,
):
    module = load()
    monkeypatch.delenv("COMSPEC", raising=False)
    monkeypatch.setattr(module.shutil, "which", lambda name: None)

    with pytest.raises(RuntimeError, match="command processor"):
        module._execute(
            [r"C:\node\npx.cmd", "--version"],
            cwd=tmp_path,
            platform_name="nt",
        )


def test_posix_execution_remains_shell_free(monkeypatch, tmp_path):
    module = load()
    captured = {}

    class Result:
        returncode = 0

    def fake_run(command, cwd, check, shell, executable=None):
        captured["command"] = command
        captured["cwd"] = cwd
        captured["check"] = check
        captured["shell"] = shell
        captured["executable"] = executable
        return Result()

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    args = ["/usr/bin/npx", "--version"]
    assert (
        module._execute(
            args,
            cwd=tmp_path,
            platform_name="posix",
        )
        == 0
    )
    assert captured["command"] == args
    assert captured["cwd"] == tmp_path
    assert captured["shell"] is False
    assert captured["check"] is False
    assert captured["executable"] is None
