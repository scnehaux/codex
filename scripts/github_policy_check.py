from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.adapters.scm.github import audit_github_projection
from engine.adapters.scm.github_activation import build_github_activation_plan
from engine.control.governance.scm_policy import (
    SCMPolicyError,
    assert_scm_enforcement_policy,
)


def main(argv: list[str] | None = None) -> int:
    args = [] if argv is None else list(argv)
    if args not in ([], ["--activation-plan"]):
        print("usage: github_policy_check.py [--activation-plan]")
        return 2

    try:
        policy = assert_scm_enforcement_policy(ROOT)
    except SCMPolicyError as exc:
        print(f"[FAIL] GitHub reference-provider policy: {exc}")
        return 1

    if args == ["--activation-plan"]:
        plan = build_github_activation_plan(ROOT, policy)
        if not plan.ready:
            print("[BLOCKED] GitHub provider activation is not ready:")
            for finding in plan.blockers:
                print(f"  - [{finding.code}] {finding.message}")
            print("  effective enforcement: NOT CLAIMED")
            return 2
        print(
            json.dumps(
                {
                    "authority_revision": plan.authority_revision,
                    "integration_id": plan.integration_id,
                    "ruleset_payload": plan.ruleset_payload,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    report = audit_github_projection(ROOT, policy)
    if report.findings:
        print("[FAIL] GitHub reference-provider projection drift:")
        for finding in report.findings:
            print(f"  - [{finding.code}] {finding.message}")
        return 1

    print("[PASS] GitHub reference-provider projection")
    print("  semantic authority: governance/scm/enforcement-policy.yaml")
    print(f"  candidate check: {policy.qualification.candidate.context}")
    print(
        "  external authority: "
        f"{policy.qualification.external_authority.context} (planned)"
    )
    print("  provider: github")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
