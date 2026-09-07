from __future__ import annotations

from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from engine.control.governance.genesis import assert_genesis_integrity


def main() -> int:
    root = Path.cwd().resolve()

    try:
        report = assert_genesis_integrity(root)
    except RuntimeError as exc:
        print(f"[FAIL] {exc}")
        return 1

    print("[PASS] Genesis integrity")
    print(f"  mode: {report.mode}")
    print(f"  candidate files: {len(report.candidate_files)}")
    print(f"  root commit: {report.root_commit or '<unborn>'}")
    print("  architecture admission: CLOSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
