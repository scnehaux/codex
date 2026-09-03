#!/usr/bin/env python3
"""CODEOWNERS Path Validator — Fitness Function for GDC-003 compliance.

Validates that every path rule in .github/CODEOWNERS resolves to an existing
file or directory in the repository. Stale paths mean decentralized ownership
is silently broken (GitHub falls back to the global wildcard rule).

Exit codes:
    0 — All CODEOWNERS paths are valid.
    1 — One or more stale paths detected.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CODEOWNERS_PATH = REPO_ROOT / ".github" / "CODEOWNERS"


def parse_codeowners(codeowners_file: Path) -> list[tuple[int, str]]:
    """Extract (line_number, path) tuples from CODEOWNERS, ignoring comments
    and the global wildcard (*) rule."""
    entries: list[tuple[int, str]] = []
    for line_no, line in enumerate(
        codeowners_file.read_text(encoding="utf-8").splitlines(), start=1
    ):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # First token is the path pattern, rest are owners
        tokens = stripped.split()
        path_pattern = tokens[0]
        # Skip the global wildcard
        if path_pattern == "*":
            continue
        entries.append((line_no, path_pattern))
    return entries


def resolve_path(pattern: str) -> bool:
    """Check if a CODEOWNERS path pattern resolves to an existing file or
    directory. Strips the leading slash (CODEOWNERS paths are repo-relative)."""
    # Remove leading slash for filesystem resolution
    clean = pattern.lstrip("/")
    target = REPO_ROOT / clean
    # For directory patterns (ending with /), check directory existence
    if pattern.endswith("/"):
        return target.is_dir()
    # For file patterns, check exact file
    if target.exists():
        return True
    # Check if it's a glob pattern (contains *)
    if "*" in clean:
        return bool(list(REPO_ROOT.glob(clean)))
    return False


def main() -> int:
    if not CODEOWNERS_PATH.exists():
        print(f"ERROR: CODEOWNERS file not found at {CODEOWNERS_PATH}")
        return 1

    entries = parse_codeowners(CODEOWNERS_PATH)
    stale: list[tuple[int, str]] = []

    for line_no, path_pattern in entries:
        if not resolve_path(path_pattern):
            stale.append((line_no, path_pattern))

    if stale:
        print("=" * 70)
        print("CODEOWNERS PATH VALIDATION FAILED")
        print("=" * 70)
        print()
        print(f"Found {len(stale)} stale path(s) in .github/CODEOWNERS:")
        print()
        for line_no, path in stale:
            print(f"  Line {line_no}: {path}")
            print(
                f"    → No matching file or directory found at: {REPO_ROOT / path.lstrip('/')}"
            )
            print()
        print("Fix: Update the paths to match actual directory names.")
        print("See: GDC-003 (Architecture Review Process) for ownership rules.")
        return 1

    print(
        f"SUCCESS: CODEOWNERS validation passed - all {len(entries)} path rules resolve correctly."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
