from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.adapters.scm.github import audit_github_projection
from engine.control.governance.scm_policy import (
    SCMPolicyError,
    assert_scm_enforcement_policy,
)


def main() -> int:
    try:
        policy = assert_scm_enforcement_policy(ROOT)
    except SCMPolicyError as exc:
        print(f"[FAIL] GitHub reference-provider policy: {exc}")
        return 1

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
    raise SystemExit(main())
