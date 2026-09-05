from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.control.governance.scm_policy import (
    SCMPolicyError,
    assert_scm_enforcement_policy,
)


def main() -> int:
    try:
        policy = assert_scm_enforcement_policy(ROOT)
    except SCMPolicyError as exc:
        print(f"[FAIL] SCM desired-state semantic policy: {exc}")
        return 1

    print("[PASS] SCM desired-state semantic policy")
    print("  provider semantics: neutral")
    print(f"  default branch selector: {policy.default_branch.selector}")
    print(f"  candidate qualification: {policy.qualification.candidate.context}")
    print(
        "  review target: "
        f">={policy.review.normative_target.minimum_independent_approvals} "
        "independent governed approval"
    )
    print(
        "  review effective: "
        f"{policy.review.effective_required_approvals} mandatory approvals "
        f"(bootstrap exception {'active' if policy.review.bootstrap_exception.active else 'inactive'})"
    )
    exit_condition = policy.review.bootstrap_exception.exit_condition
    print(
        "  review bootstrap exit: "
        f"{exit_condition.signal} {exit_condition.operator} {exit_condition.value}"
    )
    print(
        "  external authority: "
        f"{policy.qualification.external_authority.context} (effective state separate)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
