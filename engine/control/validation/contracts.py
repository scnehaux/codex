from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ValidationOutcome(str, Enum):
    PASS = "pass"
    FAIL = "fail"


def _required(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    return normalized


@dataclass(frozen=True, slots=True)
class ValidationFinding:
    finding_id: str
    rule_id: str
    message: str
    blocking: bool
    artifact_key: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "finding_id", _required(self.finding_id, "finding_id"))
        object.__setattr__(self, "rule_id", _required(self.rule_id, "rule_id"))
        object.__setattr__(self, "message", _required(self.message, "message"))
        if self.artifact_key is not None:
            object.__setattr__(
                self,
                "artifact_key",
                _required(self.artifact_key, "artifact_key"),
            )

    def semantic_state(self) -> tuple[Any, ...]:
        return (
            self.finding_id,
            self.rule_id,
            self.message,
            self.blocking,
            self.artifact_key,
        )


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Deterministic machine-verifiable validation result for one draft."""

    report_id: str
    draft_id: str
    findings: tuple[ValidationFinding, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "report_id", _required(self.report_id, "report_id"))
        object.__setattr__(self, "draft_id", _required(self.draft_id, "draft_id"))
        findings = tuple(self.findings)
        if not all(isinstance(item, ValidationFinding) for item in findings):
            raise TypeError("findings must contain ValidationFinding")
        ids = [item.finding_id for item in findings]
        if len(ids) != len(set(ids)):
            raise ValueError("validation finding_id values must be unique")
        object.__setattr__(
            self, "findings", tuple(sorted(findings, key=lambda item: item.finding_id))
        )

    @property
    def outcome(self) -> ValidationOutcome:
        if any(item.blocking for item in self.findings):
            return ValidationOutcome.FAIL
        return ValidationOutcome.PASS

    def semantic_state(self) -> tuple[Any, ...]:
        return (
            self.report_id,
            self.draft_id,
            self.outcome.value,
            tuple(item.semantic_state() for item in self.findings),
        )
