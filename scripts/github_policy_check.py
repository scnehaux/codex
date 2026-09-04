from __future__ import annotations

import json
from pathlib import Path
import re

import yaml

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_RULES = {
    "deletion",
    "non_fast_forward",
    "required_linear_history",
    "pull_request",
    "required_status_checks",
}
ACTION_RE = re.compile(
    r"uses:\s+actions/(checkout|setup-python|setup-node)@([0-9a-f]{40})\b"
)
AUTHORITY_CONTEXT = "Codex Governance Authority"
CANDIDATE_CONTEXT = "Governance Qualification"


def fail(message: str) -> int:
    print(f"[FAIL] {message}")
    return 1


def main() -> int:
    ruleset = ROOT / "governance/github/main-ruleset.json"
    authority_binding = ROOT / "governance/github/authority-binding.yaml"
    workflow = ROOT / ".github/workflows/governance.yml"
    codeowners = ROOT / ".github/CODEOWNERS"
    template = ROOT / ".github/pull_request_template.md"

    try:
        policy = json.loads(ruleset.read_text(encoding="utf-8"))
        binding = yaml.safe_load(authority_binding.read_text(encoding="utf-8"))
    except Exception as exc:
        return fail(f"GitHub desired state unreadable: {exc}")

    if not isinstance(binding, dict) or binding.get("provider") != "github":
        return fail("GitHub external authority binding is invalid")
    if binding.get("desired_state_only") is not True:
        return fail("repository authority binding must remain desired-state only")
    authority = binding.get("authority")
    evaluator = binding.get("evaluator")
    activation = binding.get("activation")
    if not isinstance(authority, dict) or authority.get("type") != "github-app":
        return fail("GitHub external authority must be a github-app")
    if authority.get("check_context") != AUTHORITY_CONTEXT:
        return fail("external authority check context drifted")
    if authority.get("expected_source_binding") != "integration_id":
        return fail("external authority source must bind by integration_id")
    if (
        not isinstance(evaluator, dict)
        or evaluator.get("execution_location") != "external"
    ):
        return fail("authority evaluator must execute externally")
    if evaluator.get("candidate_revision_as_authority") is not False:
        return fail("candidate revision must not execute as authority")
    if evaluator.get("auto_deploy_from_candidate") is not False:
        return fail("authority evaluator must not auto-deploy from candidate state")
    if evaluator.get("promotion") != "privileged-explicit":
        return fail("authority evaluator promotion must be privileged and explicit")
    if not isinstance(activation, dict) or activation.get("state") != "planned":
        return fail("external authority must remain planned before activation")
    if activation.get("effective_enforcement_claimed") is not False:
        return fail("pre-activation binding must not claim effective enforcement")
    if (
        authority.get("integration_id") is not None
        or evaluator.get("authority_revision") is not None
    ):
        return fail(
            "planned binding must not invent observed integration/runtime identity"
        )

    if policy.get("name") != "main-governance":
        return fail("ruleset name must be main-governance")
    if policy.get("target") != "branch" or policy.get("enforcement") != "active":
        return fail("ruleset must be an active branch ruleset")
    if policy.get("bypass_actors") != []:
        return fail("main ruleset bypass actors must be empty")
    ref = policy.get("conditions", {}).get("ref_name", {})
    if ref.get("include") != ["~DEFAULT_BRANCH"] or ref.get("exclude") != []:
        return fail("ruleset must target only the default branch")

    rules = {
        item.get("type"): item
        for item in policy.get("rules", [])
        if isinstance(item, dict)
    }
    missing = sorted(REQUIRED_RULES - set(rules))
    if missing:
        return fail(f"missing required rules: {missing}")

    pull = rules["pull_request"].get("parameters")
    if pull != {
        "allowed_merge_methods": ["squash"],
        "dismiss_stale_reviews_on_push": True,
        "require_code_owner_review": False,
        "require_last_push_approval": False,
        "required_approving_review_count": 0,
        "required_review_thread_resolution": True,
    }:
        return fail("pull request rule parameters drifted")

    status = rules["required_status_checks"].get("parameters")
    if status != {
        "do_not_enforce_on_create": False,
        "required_status_checks": [{"context": "Governance Qualification"}],
        "strict_required_status_checks_policy": True,
    }:
        return fail("required status-check rule parameters drifted")

    try:
        workflow_text = workflow.read_text(encoding="utf-8")
        codeowners_text = codeowners.read_text(encoding="utf-8")
    except OSError as exc:
        return fail(str(exc))

    if AUTHORITY_CONTEXT in workflow_text:
        return fail("candidate workflow must not emit the external authority context")

    for fragment in (
        f"name: {CANDIDATE_CONTEXT}",
        "pull_request:",
        "push:",
        "branches: [main]",
        "contents: read",
        "persist-credentials: false",
        "fetch-depth: 0",
        "make mutation-ci-check",
        "make governance-qualify",
    ):
        if fragment not in workflow_text:
            return fail(f"workflow contract missing {fragment!r}")

    pinned = {name for name, _ in ACTION_RE.findall(workflow_text)}
    if pinned != {"checkout", "setup-python", "setup-node"}:
        return fail(
            "checkout/setup-python/setup-node must be pinned by full commit SHA"
        )
    if re.search(
        r"uses:\s+actions/(checkout|setup-python|setup-node)@v\d", workflow_text
    ):
        return fail("mutable GitHub Action major tags are forbidden")

    for line in (
        "* @anshacerbia2",
        "/governance/ @anshacerbia2",
        "/.github/ @anshacerbia2",
    ):
        if line not in codeowners_text:
            return fail(f"CODEOWNERS missing {line!r}")

    if not template.is_file():
        return fail("pull request template is missing")

    print("[PASS] GitHub reference-provider enforcement desired-state policy")
    print(f"  candidate check: {CANDIDATE_CONTEXT}")
    print(f"  external authority check: {AUTHORITY_CONTEXT} (planned)")
    print("  pull request: required")
    print("  merge method: squash only")
    print("  force push: blocked")
    print("  deletion: blocked")
    print("  bypass actors: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
