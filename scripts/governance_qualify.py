from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from engine.control.governance.genesis import assert_genesis_integrity
from engine.control.governance.mutation import (
    assert_version_mutation_integrity,
)
from engine.control.governance.readiness import (
    assert_governance_readiness,
)
from engine.control.governance.scm_trust import assert_scm_trust_boundary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Qualify the Scnehaux Codex governance control plane",
    )
    parser.add_argument(
        "--control-only",
        action="store_true",
        help="skip full pytest regression while still executing permanent controls",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path.cwd().resolve()

    try:
        readiness = assert_governance_readiness(root)
        assert_scm_trust_boundary(root)
        genesis = assert_genesis_integrity(root)
        mutation = assert_version_mutation_integrity(root)
    except RuntimeError as exc:
        print(f"[FAIL] {exc}")
        return 1

    print("[PASS] Governance control qualification")
    print(f"  controls: {len(readiness.checked_controls)}")
    print("  SCM trust boundary: DECLARED (effective enforcement separate)")
    print(f"  Genesis mode: {genesis.mode}")
    print(f"  mutation mode: {mutation.mode}")
    print("  architecture admission: CLOSED")

    if args.control_only:
        print("  full regression: skipped (--control-only)")
        return 0

    print("[RUN] full regression + per-file coverage gate")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=root,
    )
    if result.returncode != 0:
        print("[FAIL] full governance qualification regression")
        return result.returncode

    print("[PASS] full governance qualification regression")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
