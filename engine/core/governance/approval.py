from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


def _required(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    return normalized


class DecisionOutcome(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes-requested"


@dataclass(frozen=True, slots=True)
class ApprovalRequirement:
    role: str
    minimum_approvals: int = 1
    segregation_group: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "role", _required(self.role, "role"))
        if self.minimum_approvals < 1:
            raise ValueError("minimum_approvals must be >= 1")
        if self.segregation_group is not None:
            object.__setattr__(
                self,
                "segregation_group",
                _required(self.segregation_group, "segregation_group"),
            )


@dataclass(frozen=True, slots=True)
class ApprovalPackage:
    """Neutral decision package assembled from validation, simulation, and review evidence."""

    package_id: str
    draft_id: str
    proposal_id: str
    validation_report_id: str
    simulation_report_id: str
    review_ids: tuple[str, ...]
    risk_classification: str
    affected_scopes: tuple[str, ...]
    requirements: tuple[ApprovalRequirement, ...]
    mechanically_eligible: bool
    auto_approval_eligible: bool = False
    policy_id: str | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "package_id",
            "draft_id",
            "proposal_id",
            "validation_report_id",
            "simulation_report_id",
            "risk_classification",
        ):
            object.__setattr__(self, field_name, _required(getattr(self, field_name), field_name))
        if self.policy_id is not None:
            object.__setattr__(self, "policy_id", _required(self.policy_id, "policy_id"))
        for field_name in ("review_ids", "affected_scopes"):
            values = tuple(_required(item, field_name) for item in getattr(self, field_name))
            if field_name == "affected_scopes" and not values:
                raise ValueError("affected_scopes must not be empty")
            if len(values) != len(set(values)):
                raise ValueError(f"{field_name} values must be unique")
            object.__setattr__(self, field_name, tuple(sorted(values)))
        requirements = tuple(self.requirements)
        if not all(isinstance(item, ApprovalRequirement) for item in requirements):
            raise TypeError("requirements must contain ApprovalRequirement")
        if not requirements:
            raise ValueError("requirements must not be empty")
        object.__setattr__(self, "requirements", requirements)
        if self.auto_approval_eligible and not self.mechanically_eligible:
            raise ValueError("auto approval requires mechanical eligibility")

    def semantic_state(self) -> tuple[Any, ...]:
        return (
            self.package_id,
            self.draft_id,
            self.proposal_id,
            self.validation_report_id,
            self.simulation_report_id,
            self.review_ids,
            self.risk_classification,
            self.affected_scopes,
            tuple(
                (item.role, item.minimum_approvals, item.segregation_group)
                for item in self.requirements
            ),
            self.mechanically_eligible,
            self.auto_approval_eligible,
            self.policy_id,
        )


@dataclass(frozen=True, slots=True)
class ApprovalDecision:
    decision_id: str
    package: ApprovalPackage
    outcome: DecisionOutcome
    authority_type: str
    actor_id: str
    rationale: str
    exception_ref: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "decision_id", _required(self.decision_id, "decision_id"))
        if not isinstance(self.package, ApprovalPackage):
            raise TypeError("package must be ApprovalPackage")
        if not isinstance(self.outcome, DecisionOutcome):
            raise TypeError("outcome must be DecisionOutcome")
        object.__setattr__(self, "authority_type", _required(self.authority_type, "authority_type"))
        object.__setattr__(self, "actor_id", _required(self.actor_id, "actor_id"))
        object.__setattr__(self, "rationale", _required(self.rationale, "rationale"))
        if self.exception_ref is not None:
            object.__setattr__(self, "exception_ref", _required(self.exception_ref, "exception_ref"))
        if self.outcome is DecisionOutcome.APPROVED:
            if not self.package.mechanically_eligible and self.exception_ref is None:
                raise ValueError("approval with mechanical blockers requires exception_ref")
            if self.authority_type == "policy" and not self.package.auto_approval_eligible:
                raise ValueError("policy approval requires auto_approval_eligible package")

    def semantic_state(self) -> tuple[Any, ...]:
        return (
            self.decision_id,
            self.package.semantic_state(),
            self.outcome.value,
            self.authority_type,
            self.actor_id,
            self.rationale,
            self.exception_ref,
        )
