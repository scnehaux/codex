from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _required(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    return normalized


@dataclass(frozen=True, slots=True)
class ReviewFinding:
    finding_id: str
    category: str
    challenge: str
    recommendation: str
    related_claim_ids: tuple[str, ...] = ()
    confidence: float | None = None

    def __post_init__(self) -> None:
        for field_name in ("finding_id", "category", "challenge", "recommendation"):
            object.__setattr__(self, field_name, _required(getattr(self, field_name), field_name))
        related = tuple(_required(item, "related_claim_ids") for item in self.related_claim_ids)
        if len(related) != len(set(related)):
            raise ValueError("related_claim_ids must be unique")
        object.__setattr__(self, "related_claim_ids", tuple(sorted(related)))
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

    def semantic_state(self) -> tuple[Any, ...]:
        return (
            self.finding_id,
            self.category,
            self.challenge,
            self.recommendation,
            self.related_claim_ids,
            self.confidence,
        )


@dataclass(frozen=True, slots=True)
class ArchitectureReview:
    """Advisory architecture challenge. Review never grants approval authority."""

    review_id: str
    draft_id: str
    reviewer_id: str
    summary: str
    findings: tuple[ReviewFinding, ...] = ()
    validation_report_id: str | None = None
    simulation_report_id: str | None = None
    independent_from_generation: bool = False

    def __post_init__(self) -> None:
        for field_name in ("review_id", "draft_id", "reviewer_id", "summary"):
            object.__setattr__(self, field_name, _required(getattr(self, field_name), field_name))
        for field_name in ("validation_report_id", "simulation_report_id"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(self, field_name, _required(value, field_name))
        findings = tuple(self.findings)
        if not all(isinstance(item, ReviewFinding) for item in findings):
            raise TypeError("findings must contain ReviewFinding")
        ids = [item.finding_id for item in findings]
        if len(ids) != len(set(ids)):
            raise ValueError("review finding_id values must be unique")
        object.__setattr__(self, "findings", tuple(sorted(findings, key=lambda item: item.finding_id)))

    def semantic_state(self) -> tuple[Any, ...]:
        return (
            self.review_id,
            self.draft_id,
            self.reviewer_id,
            self.summary,
            tuple(item.semantic_state() for item in self.findings),
            self.validation_report_id,
            self.simulation_report_id,
            self.independent_from_generation,
        )
