from __future__ import annotations

from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from engine.control.governance.mutation import (
    assert_version_mutation_integrity,
)


def main() -> int:
    root = Path.cwd().resolve()

    try:
        report = assert_version_mutation_integrity(root)
    except RuntimeError as exc:
        print(f"[FAIL] {exc}")
        return 1

    print("[PASS] Version + mutation integrity")
    print(f"  mode: {report.mode}")
    print(f"  governed documents: {report.checked_documents}")
    print("  architecture admission: unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
