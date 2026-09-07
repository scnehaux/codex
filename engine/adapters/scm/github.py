from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Mapping

import yaml

from engine.control.governance.scm_policy import SCMEnforcementPolicy


ACTION_RE = re.compile(r"^actions/(checkout|setup-python|setup-node)@([0-9a-f]{40})$")


@dataclass(frozen=True, slots=True)
class GitHubProjectionFinding:
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class GitHubProjectionReport:
    findings: tuple[GitHubProjectionFinding, ...]

    @property
    def ok(self) -> bool:
        return not self.findings


def _finding(code: str, message: str) -> GitHubProjectionFinding:
    return GitHubProjectionFinding(code=code, message=message)


def _check(
    condition: bool,
    code: str,
    message: str,
    findings: list[GitHubProjectionFinding],
) -> None:
    if not condition:
        findings.append(_finding(code, message))


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, dict) else {}


def _codeowners(text: str) -> dict[str, tuple[str, ...]]:
    result: dict[str, tuple[str, ...]] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            result[parts[0]] = tuple(parts[1:])
    return result


def _has_owner(entries: Mapping[str, tuple[str, ...]], pattern: str) -> bool:
    return bool(entries.get(pattern)) and all(
        owner.startswith("@") for owner in entries[pattern]
    )


def _job_steps(job: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    raw_steps = job.get("steps")
    if not isinstance(raw_steps, list):
        return ()
    return tuple(step for step in raw_steps if isinstance(step, dict))


def _contents_permission(permissions: object) -> str | None:
    # Job-level permissions replace the workflow defaults. Omitted scopes are none.
    if permissions == "read-all":
        return "read"
    if permissions == "write-all":
        return "write"
    if isinstance(permissions, dict):
        value = permissions.get("contents", "none")
        return value if isinstance(value, str) else None
    return None


def _required_execution(item: Mapping[str, Any]) -> bool:
    # Recognize only unconditional/default-success execution, never evaluate YAML
    # expressions. Unsupported guards cannot serve as proof of a mandatory check.
    allowed_guard = item.get("if") in (
        None,
        "true",
        "${{ true }}",
        "success()",
        "${{ success() }}",
    )
    return allowed_guard and item.get("continue-on-error", "false") == "false"


def audit_github_projection(
    repo_root: str | Path,
    policy: SCMEnforcementPolicy,
) -> GitHubProjectionReport:
    root = Path(repo_root).resolve()
    findings: list[GitHubProjectionFinding] = []

    try:
        ruleset = json.loads(
            (root / "governance/github/main-ruleset.json").read_text(encoding="utf-8")
        )
        binding = yaml.safe_load(
            (root / "governance/github/authority-binding.yaml").read_text(
                encoding="utf-8"
            )
        )
        workflow = yaml.load(
            (root / ".github/workflows/governance.yml").read_text(encoding="utf-8"),
            Loader=yaml.BaseLoader,
        )
        codeowners_text = (root / ".github/CODEOWNERS").read_text(encoding="utf-8")
    except (OSError, json.JSONDecodeError, yaml.YAMLError) as exc:
        return GitHubProjectionReport(
            (_finding("github-projection-load-failed", str(exc)),)
        )

    ruleset = _mapping(ruleset)
    binding = _mapping(binding)
    workflow = _mapping(workflow)

    _check(
        ruleset.get("name") == "main-governance",
        "ruleset-name-drift",
        "GitHub ruleset name must remain main-governance",
        findings,
    )
    _check(
        ruleset.get("target") == "branch" and ruleset.get("enforcement") == "active",
        "ruleset-activation-drift",
        "GitHub desired ruleset must target branches and be active",
        findings,
    )
    _check(
        (ruleset.get("bypass_actors") == []) == (not policy.bypass.allowed),
        "bypass-projection-mismatch",
        "GitHub bypass actors do not match SCM policy",
        findings,
    )

    ref = _mapping(_mapping(ruleset.get("conditions")).get("ref_name"))
    _check(
        policy.default_branch.selector == "default"
        and ref.get("include") == ["~DEFAULT_BRANCH"]
        and ref.get("exclude") == [],
        "default-branch-projection-mismatch",
        "GitHub ruleset must project the provider-neutral default branch selector",
        findings,
    )

    rules = {
        item.get("type"): item
        for item in ruleset.get("rules", [])
        if isinstance(item, dict) and isinstance(item.get("type"), str)
    }
    _check(
        ("deletion" in rules) == (not policy.default_branch.deletion_allowed),
        "deletion-projection-mismatch",
        "GitHub deletion rule does not match SCM policy",
        findings,
    )
    _check(
        ("non_fast_forward" in rules) == (not policy.default_branch.force_push_allowed),
        "force-push-projection-mismatch",
        "GitHub non-fast-forward rule does not match SCM policy",
        findings,
    )
    _check(
        ("required_linear_history" in rules)
        == policy.default_branch.linear_history_required,
        "linear-history-projection-mismatch",
        "GitHub linear-history rule does not match SCM policy",
        findings,
    )
    _check(
        ("pull_request" in rules) == policy.default_branch.changes_require_review,
        "review-projection-mismatch",
        "GitHub pull-request rule does not match SCM policy",
        findings,
    )

    pull = _mapping(_mapping(rules.get("pull_request")).get("parameters"))
    _check(
        pull.get("allowed_merge_methods") == list(policy.merge.allowed_methods),
        "merge-method-projection-mismatch",
        "GitHub merge methods do not match SCM policy",
        findings,
    )
    _check(
        pull.get("dismiss_stale_reviews_on_push")
        is policy.review.dismiss_stale_on_push,
        "stale-review-projection-mismatch",
        "GitHub stale-review behavior does not match SCM policy",
        findings,
    )
    _check(
        pull.get("require_code_owner_review")
        is policy.review.effective_require_qualified_owner_approval,
        "code-owner-review-projection-mismatch",
        "GitHub code-owner review behavior does not match SCM policy",
        findings,
    )
    _check(
        pull.get("require_last_push_approval")
        is policy.review.require_last_push_approval,
        "last-push-approval-projection-mismatch",
        "GitHub last-push approval behavior does not match SCM policy",
        findings,
    )
    _check(
        pull.get("required_approving_review_count")
        == policy.review.effective_required_approvals,
        "approval-count-projection-mismatch",
        "GitHub approval count does not match SCM policy",
        findings,
    )
    _check(
        pull.get("required_review_thread_resolution")
        is policy.review.require_thread_resolution,
        "thread-resolution-projection-mismatch",
        "GitHub review-thread behavior does not match SCM policy",
        findings,
    )

    status = _mapping(_mapping(rules.get("required_status_checks")).get("parameters"))
    status_checks = status.get("required_status_checks")
    expected_checks = (
        [{"context": policy.qualification.candidate.context}]
        if policy.qualification.candidate.required
        else []
    )
    _check(
        status_checks == expected_checks,
        "candidate-check-projection-mismatch",
        "GitHub required candidate check does not match SCM policy",
        findings,
    )
    _check(
        status.get("strict_required_status_checks_policy")
        is policy.qualification.candidate.strict_against_latest_base,
        "strict-check-projection-mismatch",
        "GitHub strict status-check behavior does not match SCM policy",
        findings,
    )
    _check(
        status.get("do_not_enforce_on_create") is False,
        "ruleset-create-enforcement-drift",
        "GitHub ruleset must enforce status checks on branch creation",
        findings,
    )

    on = _mapping(workflow.get("on"))
    pull_trigger = _mapping(on.get("pull_request"))
    push_trigger = _mapping(on.get("push"))
    _check(
        (pull_trigger.get("branches") == ["main"])
        == policy.workflow.pull_request_default_branch,
        "workflow-pr-trigger-projection-mismatch",
        "GitHub PR trigger does not match SCM workflow policy",
        findings,
    )
    _check(
        (push_trigger.get("branches") == ["main"])
        == policy.workflow.push_default_branch,
        "workflow-push-trigger-projection-mismatch",
        "GitHub push trigger does not match SCM workflow policy",
        findings,
    )
    permissions = _mapping(workflow.get("permissions"))
    _check(
        permissions.get("contents") == policy.workflow.repository_contents_permission,
        "workflow-permission-projection-mismatch",
        "GitHub workflow contents permission does not match SCM policy",
        findings,
    )

    jobs = _mapping(workflow.get("jobs"))
    job_names = [
        job.get("name")
        for job in jobs.values()
        if isinstance(job, dict) and isinstance(job.get("name"), str)
    ]
    _check(
        job_names.count(policy.qualification.candidate.context) == 1,
        "candidate-check-job-mismatch",
        "candidate qualification context must map to exactly one GitHub job",
        findings,
    )
    _check(
        policy.qualification.external_authority.context not in job_names,
        "candidate-workflow-emits-external-authority",
        "candidate GitHub workflow must not emit the external authority context",
        findings,
    )

    candidates = [
        job
        for job in jobs.values()
        if isinstance(job, dict)
        and job.get("name") == policy.qualification.candidate.context
    ]
    candidate = candidates[0] if len(candidates) == 1 else {}
    _check(
        _required_execution(candidate) and "needs" not in candidate,
        "candidate-check-execution-drift",
        "candidate qualification must propagate failure and run independently "
        "with an unconditional/default-success guard",
        findings,
    )

    permission_rank = {"none": 0, "read": 1, "write": 2}
    expected_permission = policy.workflow.repository_contents_permission
    required_actions = {"checkout", "setup-python", "setup-node"}
    candidate_actions: set[str] = set()
    for job_id, raw_job in jobs.items():
        job = _mapping(raw_job)
        raw_steps = job.get("steps")
        _check(
            isinstance(raw_job, dict)
            and isinstance(raw_steps, list)
            and all(isinstance(step, dict) for step in raw_steps),
            "workflow-job-structure-invalid",
            f"job {job_id} must define an inspectable list of step mappings",
            findings,
        )
        effective_permission = _contents_permission(
            job.get("permissions", workflow.get("permissions"))
        )
        _check(
            effective_permission in permission_rank
            and permission_rank[effective_permission]
            <= permission_rank.get(expected_permission, -1),
            "job-permission-projection-mismatch",
            f"job {job_id} must not exceed authored repository contents permission",
            findings,
        )
        if job is candidate:
            _check(
                effective_permission == expected_permission,
                "candidate-check-permission-mismatch",
                "candidate qualification must retain authored contents permission",
                findings,
            )
        # Check every occurrence; a safe later action must never hide an unsafe one.
        for index, step in enumerate(_job_steps(job), start=1):
            uses = step.get("uses")
            if not isinstance(uses, str):
                continue
            action = uses.split("@", 1)[0].lower()
            if action not in {f"actions/{name}" for name in required_actions}:
                continue
            match = ACTION_RE.fullmatch(uses)
            _check(
                match is not None,
                "pinned-action-projection-mismatch",
                f"job {job_id} step {index}: {action} must use a full commit SHA",
                findings,
            )
            if match and job is candidate and _required_execution(step):
                candidate_actions.add(match.group(1))
            if action == "actions/checkout":
                checkout = _mapping(step.get("with"))
                _check(
                    checkout.get("persist-credentials") == "false",
                    "checkout-credential-safety-drift",
                    f"job {job_id} step {index}: checkout must not persist credentials",
                    findings,
                )
                _check(
                    checkout.get("fetch-depth") == "0",
                    "checkout-history-safety-drift",
                    f"job {job_id} step {index}: checkout must fetch complete history",
                    findings,
                )
    _check(
        candidate_actions == required_actions,
        "pinned-action-projection-mismatch",
        "candidate job must execute pinned checkout/setup-python/setup-node steps",
        findings,
    )

    # Evidence belongs to the named qualification job, not a sibling (possibly
    # skipped) job. Ignored failures and conditional steps are not mandatory gates.
    run_commands = {
        str(step.get("run", "")).strip()
        for step in _job_steps(candidate)
        if isinstance(step.get("run"), str) and _required_execution(step)
    }
    if policy.workflow.committed_mutation_validation_required:
        _check(
            "make mutation-ci-check" in run_commands,
            "mutation-validation-step-missing",
            "candidate job must execute blocking committed mutation validation",
            findings,
        )
    if policy.workflow.full_governance_qualification_required:
        _check(
            "make governance-qualify" in run_commands,
            "governance-qualification-step-missing",
            "candidate job must execute blocking full governance qualification",
            findings,
        )

    authority = _mapping(binding.get("authority"))
    evaluator = _mapping(binding.get("evaluator"))
    activation = _mapping(binding.get("activation"))
    _check(
        binding.get("provider") == "github"
        and binding.get("desired_state_only") is True,
        "authority-binding-provider-drift",
        "GitHub authority binding must remain desired-state-only GitHub projection",
        findings,
    )
    _check(
        authority.get("type") == "github-app"
        and authority.get("check_context")
        == policy.qualification.external_authority.context
        and authority.get("expected_source_binding") == "integration_id",
        "authority-binding-projection-mismatch",
        "GitHub external authority binding does not match SCM policy",
        findings,
    )
    _check(
        evaluator.get("execution_location") == "external"
        and evaluator.get("candidate_revision_as_authority") is False
        and evaluator.get("auto_deploy_from_candidate") is False
        and evaluator.get("promotion") == "privileged-explicit",
        "authority-runtime-safety-drift",
        "GitHub external authority runtime safety contract drifted",
        findings,
    )
    _check(
        activation.get("effective_enforcement_claimed") is False,
        "preactivation-effective-claim-forbidden",
        "GitHub desired binding must not claim effective enforcement before activation",
        findings,
    )

    entries = _codeowners(codeowners_text)
    if policy.ownership.repository_default_owner_required:
        _check(
            _has_owner(entries, "*"),
            "default-owner-projection-mismatch",
            "GitHub CODEOWNERS must cover the repository default pattern",
            findings,
        )
    if policy.ownership.governance_path_owner_required:
        _check(
            _has_owner(entries, "/governance/"),
            "governance-owner-projection-mismatch",
            "GitHub CODEOWNERS must cover governance paths",
            findings,
        )
    if policy.ownership.provider_config_owner_required:
        _check(
            _has_owner(entries, "/.github/"),
            "provider-owner-projection-mismatch",
            "GitHub CODEOWNERS must cover provider configuration paths",
            findings,
        )

    _check(
        (root / ".github/pull_request_template.md").is_file(),
        "pull-request-template-missing",
        "GitHub pull request template is missing",
        findings,
    )

    return GitHubProjectionReport(tuple(findings))


def assert_github_projection(
    repo_root: str | Path,
    policy: SCMEnforcementPolicy,
) -> GitHubProjectionReport:
    report = audit_github_projection(repo_root, policy)
    if report.findings:
        raise RuntimeError(
            "GitHub SCM projection audit failed:\n  - "
            + "\n  - ".join(
                f"[{finding.code}] {finding.message}" for finding in report.findings
            )
        )
    return report
