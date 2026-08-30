from __future__ import annotations

from pathlib import Path


def find_repository_root(start: Path) -> Path:
    """Find the repository root by stable repository markers, not path depth."""
    current = start.resolve()
    if current.is_file():
        current = current.parent

    for candidate in (current, *current.parents):
        if (
            (candidate / "pyproject.toml").is_file()
            and (candidate / "00-governance").is_dir()
            and (candidate / "engine").is_dir()
        ):
            return candidate

    raise RuntimeError(
        f"Unable to locate repository root from {start}"
    )


REPOSITORY_ROOT = find_repository_root(Path(__file__))
