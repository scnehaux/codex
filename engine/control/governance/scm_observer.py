from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from engine.control.governance.scm_policy import SCMEnforcementPolicy


OBSERVATION_STATES = frozenset({"observed", "unknown"})
INSTALLATION_STATES = frozenset({"installed", "not-installed", "unknown"})
ENFORCEMENT_STATES = frozenset({"active", "inactive", "unknown"})
DRIFT_STATES = frozenset({"aligned", "drifted", "unknown"})


@dataclass(frozen=True, slots=True)
class SCMEffectivePolicy:
    changes_require_review: bool
    deletion_allowed: bool
    force_push_allowed: bool
    linear_history_required: bool
    allowed_merge_methods: tuple[str, ...]
    required_approvals: int
    require_qualified_owner_approval: bool
    dismiss_stale_on_push: bool
    require_last_push_approval: bool
    require_thread_resolution: bool
    candidate_check_required: bool
    candidate_check_context: str
    candidate_check_strict: bool
    bypass_allowed: bool


@dataclass(frozen=True, slots=True)
class SCMLiveStateEvidence:
    provider: str
    repository: str
    observed_revision: str
    observation_time: str
    observation_state: str
    installed_state: str
    enforcement_state: str
    effective_policy: SCMEffectivePolicy | None
    drift: tuple[str, ...]
    notes: tuple[str, ...]

    @property
    def drift_state(self) -> str:
        if self.observation_state == "unknown" or self.installed_state == "unknown":
            return "unknown"
        return "drifted" if self.drift else "aligned"


def desired_effective_policy(policy: SCMEnforcementPolicy) -> SCMEffectivePolicy:
    return SCMEffectivePolicy(
        changes_require_review=policy.default_branch.changes_require_review,
        deletion_allowed=policy.default_branch.deletion_allowed,
        force_push_allowed=policy.default_branch.force_push_allowed,
        linear_history_required=policy.default_branch.linear_history_required,
        allowed_merge_methods=policy.merge.allowed_methods,
        required_approvals=policy.review.effective_required_approvals,
        require_qualified_owner_approval=(
            policy.review.effective_require_qualified_owner_approval
        ),
        dismiss_stale_on_push=policy.review.dismiss_stale_on_push,
        require_last_push_approval=policy.review.require_last_push_approval,
        require_thread_resolution=policy.review.require_thread_resolution,
        candidate_check_required=policy.qualification.candidate.required,
        candidate_check_context=policy.qualification.candidate.context,
        candidate_check_strict=(
            policy.qualification.candidate.strict_against_latest_base
        ),
        bypass_allowed=policy.bypass.allowed,
    )


def compare_effective_policy(
    desired: SCMEffectivePolicy,
    observed: SCMEffectivePolicy,
) -> tuple[str, ...]:
    drift: list[str] = []
    for field in desired.__dataclass_fields__:
        if getattr(desired, field) != getattr(observed, field):
            drift.append(field)
    return tuple(drift)


def validate_live_evidence(evidence: SCMLiveStateEvidence) -> None:
    if not evidence.provider.strip():
        raise ValueError("provider must be non-blank")
    if not evidence.repository.strip():
        raise ValueError("repository must be non-blank")
    if not evidence.observed_revision.strip():
        raise ValueError("observed_revision must be non-blank")
    if not evidence.observation_time.strip():
        raise ValueError("observation_time must be non-blank")
    if evidence.observation_state not in OBSERVATION_STATES:
        raise ValueError("invalid observation_state")
    if evidence.installed_state not in INSTALLATION_STATES:
        raise ValueError("invalid installed_state")
    if evidence.enforcement_state not in ENFORCEMENT_STATES:
        raise ValueError("invalid enforcement_state")
    if evidence.drift_state not in DRIFT_STATES:
        raise ValueError("invalid drift_state")
    if (
        evidence.installed_state == "installed"
        and evidence.observation_state == "observed"
        and evidence.effective_policy is None
    ):
        raise ValueError("installed state requires effective_policy")
    if (
        evidence.installed_state == "not-installed"
        and evidence.effective_policy is not None
    ):
        raise ValueError("not-installed state cannot contain effective_policy")


def evidence_dict(evidence: SCMLiveStateEvidence) -> dict[str, Any]:
    validate_live_evidence(evidence)
    result = asdict(evidence)
    result["drift_state"] = evidence.drift_state
    return result
