from __future__ import annotations

import importlib.util

from tests.support.repository import REPOSITORY_ROOT


SCRIPT = (
    REPOSITORY_ROOT
    / "06-fitness-function"
    / "scripts"
    / "prettier_runner.py"
)


def _load():
    spec = importlib.util.spec_from_file_location(
        "prettier_runner_windows_quoting",
        SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _windows_paths():
    separator = chr(92)
    npx = separator.join(("C:", "Program Files", "nodejs", "npx.cmd"))
    comspec = separator.join(("C:", "Windows", "System32", "cmd.exe"))
    return npx, comspec


def test_windows_command_has_one_executable_quote_layer():
    module = _load()
    npx, _ = _windows_paths()

    command = module._windows_command_string([npx, "--version"])

    assert command == f'"{npx}" --version'
    assert chr(92) + '"' not in command


def test_windows_execute_uses_shell_with_explicit_comspec(monkeypatch):
    module = _load()
    npx, comspec = _windows_paths()
    captured = {}

    class Result:
        returncode = 0

    monkeypatch.setenv("COMSPEC", comspec)

    def fake_run(command, cwd, check, shell, executable=None):
        captured["command"] = command
        captured["check"] = check
        captured["shell"] = shell
        captured["executable"] = executable
        return Result()

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    assert module._execute([npx, "--version"], platform_name="nt") == 0
    assert captured["command"] == f'"{npx}" --version'
    assert captured["shell"] is True
    assert captured["executable"] == comspec
    assert captured["check"] is False


def test_posix_execution_remains_shell_free(monkeypatch):
    module = _load()
    captured = {}

    class Result:
        returncode = 0

    def fake_run(command, cwd, check, shell, executable=None):
        captured["command"] = command
        captured["check"] = check
        captured["shell"] = shell
        return Result()

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    args = ["/usr/bin/npx", "--version"]

    assert module._execute(args, platform_name="posix") == 0
    assert captured["command"] == args
    assert captured["shell"] is False
    assert captured["check"] is False


def test_empty_windows_command_fails_closed():
    module = _load()

    try:
        module._windows_command_string([])
    except RuntimeError as exc:
        assert "at least one argument" in str(exc)
    else:
        raise AssertionError("empty Windows command must fail closed")
