from __future__ import annotations

from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from engine.control.governance.genesis_candidate import (
    assert_genesis_commit_candidate,
)


def main() -> int:
    root = Path.cwd().resolve()

    try:
        report = assert_genesis_commit_candidate(root)
    except RuntimeError as exc:
        print(f"[FAIL] {exc}")
        return 1

    print("[PASS] Genesis commit candidate")
    print(f"  staged files: {len(report.staged_files)}")
    print(f"  staged tree: {report.tree_sha}")
    print("  HEAD: <unborn>")
    print("  architecture admission: CLOSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
