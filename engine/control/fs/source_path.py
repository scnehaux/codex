from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath


def repository_source_path(value: str) -> str:
    """Normalize a portable repository file path, rejecting ambiguous components."""
    if not isinstance(value, str):
        raise TypeError("source_path must be a string")
    normalized = value.strip().replace("\\", "/")
    if not normalized:
        raise ValueError("source_path must not be blank")
    if (
        "\0" in normalized
        or PureWindowsPath(normalized).drive
        or PurePosixPath(normalized).is_absolute()
        or any(part in {"", ".", ".."} for part in normalized.split("/"))
    ):
        raise ValueError("source_path must be an unambiguous repository-relative file")
    return normalized
