from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
from typing import Literal, Sequence


PRETTIER_VERSION = "3.9.6"
PRETTIER_PATTERNS = ("**/*.md", "**/*.json")
PrettierMode = Literal["check", "write"]


def _resolve_prettier(*, cwd: str | Path, platform_name: str | None = None) -> str:
    platform_name = os.name if platform_name is None else platform_name
    name = "prettier.cmd" if platform_name == "nt" else "prettier"
    candidate = Path(cwd) / "node_modules" / ".bin" / name
    if not candidate.is_file():
        raise RuntimeError("locked Prettier binary is not installed; run npm ci")
    return str(candidate)


def _prettier_args(mode: PrettierMode, *, executable: str) -> list[str]:
    if mode not in {"check", "write"}:
        raise ValueError("mode must be 'check' or 'write'")
    return [executable, "--check" if mode == "check" else "--write", *PRETTIER_PATTERNS]


def _windows_command_string(args: Sequence[str]) -> str:
    if not args:
        raise RuntimeError("Windows command requires at least one argument")

    return subprocess.list2cmdline([str(value) for value in args])


def _execute(
    args: Sequence[str],
    *,
    cwd: str | Path,
    platform_name: str | None = None,
) -> int:
    platform_name = os.name if platform_name is None else platform_name

    if platform_name == "nt":
        comspec = os.environ.get("COMSPEC") or shutil.which("cmd.exe")
        if not comspec:
            raise RuntimeError("Windows command processor is not available")

        return subprocess.run(
            _windows_command_string(args),
            cwd=Path(cwd),
            check=False,
            shell=True,
            executable=comspec,
        ).returncode

    return subprocess.run(
        list(args),
        cwd=Path(cwd),
        check=False,
        shell=False,
    ).returncode


def run_prettier(
    mode: PrettierMode,
    *,
    cwd: str | Path | None = None,
) -> int:
    working_directory = Path.cwd() if cwd is None else Path(cwd)
    executable = _resolve_prettier(cwd=working_directory)
    command = _prettier_args(mode, executable=executable)
    return _execute(command, cwd=working_directory)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run pinned Prettier cross-platform")
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument(
        "--check",
        dest="mode",
        action="store_const",
        const="check",
    )
    modes.add_argument(
        "--write",
        dest="mode",
        action="store_const",
        const="write",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    try:
        return run_prettier(args.mode)
    except (RuntimeError, ValueError) as exc:
        print(f"[FAIL] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
