from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
from typing import Sequence


PRETTIER_PACKAGE = "prettier@3.9.6"
PRETTIER_PATTERNS = ("**/*.md", "**/*.json")


def _resolve_npx(*, platform_name: str | None = None) -> str:
    platform_name = os.name if platform_name is None else platform_name
    candidates = ("npx.cmd", "npx") if platform_name == "nt" else ("npx",)

    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved

    raise RuntimeError("npx executable not found on PATH")


def _prettier_args(*, write: bool, npx: str) -> list[str]:
    return [
        npx,
        "--yes",
        PRETTIER_PACKAGE,
        "--write" if write else "--check",
        *PRETTIER_PATTERNS,
    ]


def _windows_command_string(args: Sequence[str]) -> str:
    if not args:
        raise RuntimeError("Windows command requires at least one argument")

    return subprocess.list2cmdline([str(value) for value in args])


def _execute(
    args: Sequence[str],
    *,
    platform_name: str | None = None,
) -> int:
    platform_name = os.name if platform_name is None else platform_name

    if platform_name == "nt":
        comspec = os.environ.get("COMSPEC") or shutil.which("cmd.exe")
        if not comspec:
            raise RuntimeError("COMSPEC/cmd.exe not available")

        return subprocess.run(
            _windows_command_string(args),
            cwd=Path.cwd(),
            check=False,
            shell=True,
            executable=comspec,
        ).returncode

    return subprocess.run(
        list(args),
        cwd=Path.cwd(),
        check=False,
        shell=False,
    ).returncode


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run pinned Prettier cross-platform"
    )
    parser.add_argument("--write", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    try:
        npx = _resolve_npx()
        return _execute(_prettier_args(write=args.write, npx=npx))
    except RuntimeError as exc:
        print(f"[FAIL] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
