from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.control.governance.scm_trust import assert_scm_trust_boundary


def main() -> int:
    try:
        assert_scm_trust_boundary(ROOT)
    except RuntimeError as exc:
        print(f"[FAIL] {exc}")
        return 1

    print("[PASS] SCM enforcement trust-boundary contract")
    print("  provider semantics: neutral")
    print("  candidate state as sole authority: forbidden")
    print("  external authority: required")
    print("  effective enforcement: NOT PROVEN by this control")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
