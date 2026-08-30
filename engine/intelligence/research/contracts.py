from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.core.knowledge import Claim, KnowledgeRevision, RetrievalRequest
from engine.core.metamodel import KnowledgeState


def _required(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    return normalized


@dataclass(frozen=True, slots=True)
class ResearchQuestion:
    """Evidence-seeking question with an explicit retrieval contract."""

    question_id: str
    question: str
    retrieval_request: RetrievalRequest
    rationale: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "question_id", _required(self.question_id, "question_id"))
        object.__setattr__(self, "question", _required(self.question, "question"))
        if not isinstance(self.retrieval_request, RetrievalRequest):
            raise TypeError("retrieval_request must be RetrievalRequest")
        if self.rationale is not None:
            object.__setattr__(self, "rationale", _required(self.rationale, "rationale"))

    def semantic_state(self) -> tuple[Any, ...]:
        return (
            self.question_id,
            self.question,
            self.retrieval_request,
            self.rationale,
        )


@dataclass(frozen=True, slots=True)
class ResearchPlan:
    """Research contract attached to a capability plan, not an agent execution plan."""

    research_plan_id: str
    architecture_plan_id: str
    questions: tuple[ResearchQuestion, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "research_plan_id",
            _required(self.research_plan_id, "research_plan_id"),
        )
        object.__setattr__(
            self,
            "architecture_plan_id",
            _required(self.architecture_plan_id, "architecture_plan_id"),
        )
        questions = tuple(self.questions)
        if not questions:
            raise ValueError("questions must not be empty")
        if not all(isinstance(item, ResearchQuestion) for item in questions):
            raise TypeError("questions must contain ResearchQuestion")
        ids = [item.question_id for item in questions]
        if len(ids) != len(set(ids)):
            raise ValueError("research question_id values must be unique")
        object.__setattr__(self, "questions", questions)

    def question_ids(self) -> tuple[str, ...]:
        return tuple(item.question_id for item in self.questions)

    def semantic_state(self) -> tuple[Any, ...]:
        return (
            self.research_plan_id,
            self.architecture_plan_id,
            tuple(item.semantic_state() for item in self.questions),
        )


@dataclass(frozen=True, slots=True)
class ResearchFinding:
    """Evidence-backed finding. Research findings cannot themselves be proposals."""

    finding_id: str
    question_id: str
    claim: Claim

    def __post_init__(self) -> None:
        object.__setattr__(self, "finding_id", _required(self.finding_id, "finding_id"))
        object.__setattr__(self, "question_id", _required(self.question_id, "question_id"))
        if not isinstance(self.claim, Claim):
            raise TypeError("claim must be Claim")
        if self.claim.knowledge_state is KnowledgeState.PROPOSED:
            raise ValueError("research finding claim must not be PROPOSED")

    def semantic_state(self) -> tuple[Any, ...]:
        return (
            self.finding_id,
            self.question_id,
            self.claim.semantic_state(),
        )


@dataclass(frozen=True, slots=True)
class ResearchPackage:
    """Immutable evidence package produced against an explicit ResearchPlan."""

    plan: ResearchPlan
    findings: tuple[ResearchFinding, ...]
    unresolved_question_ids: tuple[str, ...] = ()
    knowledge_revision: KnowledgeRevision | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.plan, ResearchPlan):
            raise TypeError("plan must be ResearchPlan")
        if self.knowledge_revision is not None and not isinstance(
            self.knowledge_revision, KnowledgeRevision
        ):
            raise TypeError("knowledge_revision must be KnowledgeRevision or None")

        findings = tuple(self.findings)
        if not all(isinstance(item, ResearchFinding) for item in findings):
            raise TypeError("findings must contain ResearchFinding")
        finding_ids = [item.finding_id for item in findings]
        if len(finding_ids) != len(set(finding_ids)):
            raise ValueError("research finding_id values must be unique")

        known_questions = set(self.plan.question_ids())
        unknown = sorted(
            item.question_id for item in findings if item.question_id not in known_questions
        )
        if unknown:
            raise ValueError(
                "research findings must reference known question_id values: "
                + ", ".join(unknown)
            )

        unresolved = tuple(
            _required(item, "unresolved_question_ids")
            for item in self.unresolved_question_ids
        )
        if not findings and not unresolved:
            raise ValueError(
                "research package must contain findings or unresolved questions"
            )
        if len(unresolved) != len(set(unresolved)):
            raise ValueError("unresolved_question_ids must be unique")
        unknown_unresolved = sorted(set(unresolved) - known_questions)
        if unknown_unresolved:
            raise ValueError(
                "unresolved_question_ids must reference known questions: "
                + ", ".join(unknown_unresolved)
            )

        object.__setattr__(self, "findings", findings)
        object.__setattr__(self, "unresolved_question_ids", unresolved)

    @property
    def claims(self) -> tuple[Claim, ...]:
        return tuple(item.claim for item in self.findings)

    def semantic_state(self) -> tuple[Any, ...]:
        return (
            self.plan.semantic_state(),
            tuple(item.semantic_state() for item in self.findings),
            self.unresolved_question_ids,
            self.knowledge_revision,
        )
