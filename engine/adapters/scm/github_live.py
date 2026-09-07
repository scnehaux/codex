from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from engine.control.governance.scm_observer import (
    SCMEffectivePolicy,
    SCMLiveStateEvidence,
    compare_effective_policy,
    desired_effective_policy,
)
from engine.control.governance.scm_policy import SCMEnforcementPolicy


RULESET_NAME = "main-governance"


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, dict) else {}


def _rule_map(detail: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rules = detail.get("rules")
    if not isinstance(rules, list):
        return {}
    return {
        str(item.get("type")): item
        for item in rules
        if isinstance(item, dict) and isinstance(item.get("type"), str)
    }


def find_ruleset_summary(
    payload: object,
    *,
    name: str = RULESET_NAME,
) -> Mapping[str, Any] | None:
    if not isinstance(payload, list):
        raise ValueError("GitHub rulesets response must be a list")
    matches = [
        item for item in payload if isinstance(item, dict) and item.get("name") == name
    ]
    if len(matches) > 1:
        raise ValueError(f"multiple GitHub rulesets named {name!r}")
    return matches[0] if matches else None


def normalize_github_ruleset(
    detail: object,
    policy: SCMEnforcementPolicy,
) -> SCMEffectivePolicy:
    ruleset = _mapping(detail)
    if not ruleset:
        raise ValueError("GitHub ruleset detail must be a mapping")

    rules = _rule_map(ruleset)
    pull = _mapping(_mapping(rules.get("pull_request")).get("parameters"))
    status = _mapping(_mapping(rules.get("required_status_checks")).get("parameters"))
    checks = status.get("required_status_checks")
    check_records = (
        tuple(item for item in checks if isinstance(item, dict))
        if isinstance(checks, list)
        else ()
    )

    candidate_context = policy.qualification.candidate.context
    external_context = policy.qualification.external_authority.context
    candidate = next(
        (item for item in check_records if item.get("context") == candidate_context),
        None,
    )
    external = next(
        (item for item in check_records if item.get("context") == external_context),
        None,
    )
    external_integration_id = (
        external.get("integration_id") if isinstance(external, dict) else None
    )

    return SCMEffectivePolicy(
        changes_require_review="pull_request" in rules,
        deletion_allowed="deletion" not in rules,
        force_push_allowed="non_fast_forward" not in rules,
        linear_history_required="required_linear_history" in rules,
        allowed_merge_methods=tuple(pull.get("allowed_merge_methods") or ()),
        required_approvals=int(pull.get("required_approving_review_count", 0)),
        require_qualified_owner_approval=(
            pull.get("require_code_owner_review") is True
        ),
        dismiss_stale_on_push=(pull.get("dismiss_stale_reviews_on_push") is True),
        require_last_push_approval=(pull.get("require_last_push_approval") is True),
        require_thread_resolution=(
            pull.get("required_review_thread_resolution") is True
        ),
        candidate_check_required=candidate is not None,
        candidate_check_context=(candidate_context if candidate is not None else ""),
        candidate_check_strict=(
            status.get("strict_required_status_checks_policy") is True
        ),
        external_authority_check_required=external is not None,
        external_authority_check_context=(external_context if external is not None else ""),
        external_authority_source_bound=(
            type(external_integration_id) is int and external_integration_id > 0
        ),
        bypass_allowed=bool(ruleset.get("bypass_actors")),
    )


def observe_github_state(
    *,
    repository: str,
    observed_revision: str,
    policy: SCMEnforcementPolicy,
    rulesets_payload: object | None,
    ruleset_detail: object | None,
    rulesets_error: str | None = None,
    branch_protection_error: str | None = None,
    observation_time: str | None = None,
) -> SCMLiveStateEvidence:
    now = observation_time or datetime.now(timezone.utc).isoformat()
    notes: list[str] = []

    if branch_protection_error:
        notes.append(
            "branch-protection observation unavailable: " + branch_protection_error
        )

    if rulesets_error is not None or rulesets_payload is None:
        notes.append(
            "ruleset observation unavailable: " + (rulesets_error or "unknown")
        )
        return SCMLiveStateEvidence(
            provider="github",
            repository=repository,
            observed_revision=observed_revision or "unknown",
            observation_time=now,
            observation_state="unknown",
            installed_state="unknown",
            enforcement_state="unknown",
            effective_policy=None,
            drift=(),
            notes=tuple(notes),
        )

    summary = find_ruleset_summary(rulesets_payload)
    if summary is None:
        notes.append("desired GitHub ruleset main-governance is not installed")
        return SCMLiveStateEvidence(
            provider="github",
            repository=repository,
            observed_revision=observed_revision or "unknown",
            observation_time=now,
            observation_state="observed",
            installed_state="not-installed",
            enforcement_state=("unknown" if branch_protection_error else "inactive"),
            effective_policy=None,
            drift=("ruleset-not-installed",),
            notes=tuple(notes),
        )

    if ruleset_detail is None:
        notes.append("ruleset summary observed but ruleset detail is unavailable")
        return SCMLiveStateEvidence(
            provider="github",
            repository=repository,
            observed_revision=observed_revision or "unknown",
            observation_time=now,
            observation_state="unknown",
            installed_state="installed",
            enforcement_state="unknown",
            effective_policy=None,
            drift=(),
            notes=tuple(notes),
        )

    effective = normalize_github_ruleset(ruleset_detail, policy)
    desired = desired_effective_policy(policy)
    drift = compare_effective_policy(desired, effective)
    enforcement = (
        "active"
        if _mapping(ruleset_detail).get("enforcement") == "active"
        else "inactive"
    )

    return SCMLiveStateEvidence(
        provider="github",
        repository=repository,
        observed_revision=observed_revision or "unknown",
        observation_time=now,
        observation_state="observed",
        installed_state="installed",
        enforcement_state=enforcement,
        effective_policy=effective,
        drift=drift,
        notes=tuple(notes),
    )
