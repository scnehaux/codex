from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, Protocol, TypeVar, runtime_checkable

from engine.core.knowledge import Claim, ContextPackage
from engine.core.metamodel import KnowledgeState
from engine.intelligence.planning import ArchitecturePlan, IntentSpec
from engine.intelligence.research import ResearchPackage


def _required(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    return normalized


@runtime_checkable
class DraftPayload(Protocol):
    """Structured draft payload capable of deterministic semantic comparison."""

    def semantic_state(self) -> tuple[Any, ...]: ...


DraftT = TypeVar("DraftT", bound=DraftPayload)


@dataclass(frozen=True, slots=True)
class ArchitectureProposal:
    """Evidence/context-backed proposal. It is never an approval decision."""

    proposal_id: str
    intent: IntentSpec
    plan: ArchitecturePlan
    context: ContextPackage
    claims: tuple[Claim, ...]
    research: ResearchPackage | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "proposal_id", _required(self.proposal_id, "proposal_id")
        )
        if not isinstance(self.intent, IntentSpec):
            raise TypeError("intent must be IntentSpec")
        if not isinstance(self.plan, ArchitecturePlan):
            raise TypeError("plan must be ArchitecturePlan")
        if self.plan.intent != self.intent:
            raise ValueError("proposal plan must belong to proposal intent")
        if not isinstance(self.context, ContextPackage):
            raise TypeError("context must be ContextPackage")
        if self.research is not None:
            if not isinstance(self.research, ResearchPackage):
                raise TypeError("research must be ResearchPackage or None")
            if self.research.plan.architecture_plan_id != self.plan.plan_id:
                raise ValueError("research package must belong to proposal plan")

        claims = tuple(self.claims)
        if not claims:
            raise ValueError("proposal claims must not be empty")
        if not all(isinstance(item, Claim) for item in claims):
            raise TypeError("claims must contain Claim")
        if not all(item.knowledge_state is KnowledgeState.PROPOSED for item in claims):
            raise ValueError("architecture proposal claims must be PROPOSED")
        claim_ids = [item.claim_id for item in claims]
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("proposal claim_id values must be unique")

        available_lineage = {item.claim_id for item in self.context.claims}
        if self.research is not None:
            available_lineage.update(item.claim_id for item in self.research.claims)

        for claim in claims:
            if not claim.derived_from:
                raise ValueError("proposal claims must declare derived_from lineage")
            unknown = sorted(set(claim.derived_from) - available_lineage)
            if unknown:
                raise ValueError(
                    "proposal claim lineage must reference context/research claims: "
                    + ", ".join(unknown)
                )

        object.__setattr__(self, "claims", claims)

    def semantic_state(self) -> tuple[Any, ...]:
        return (
            self.proposal_id,
            self.intent.semantic_state(),
            self.plan.semantic_state(),
            self.context.semantic_state(),
            tuple(item.semantic_state() for item in self.claims),
            self.research.semantic_state() if self.research is not None else None,
        )


@dataclass(frozen=True, slots=True)
class ArtifactDraft(Generic[DraftT]):
    """Structured pre-render artifact draft preserving proposal/claim lineage."""

    draft_id: str
    artifact_type: str
    proposal: ArchitectureProposal
    payload: DraftT
    source_claim_ids: tuple[str, ...]
    target_artifact_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "draft_id", _required(self.draft_id, "draft_id"))
        object.__setattr__(
            self, "artifact_type", _required(self.artifact_type, "artifact_type")
        )
        if not isinstance(self.proposal, ArchitectureProposal):
            raise TypeError("proposal must be ArchitectureProposal")
        if not isinstance(self.payload, DraftPayload):
            raise TypeError("payload must implement DraftPayload.semantic_state")

        source_claim_ids = tuple(
            _required(item, "source_claim_ids") for item in self.source_claim_ids
        )
        if not source_claim_ids:
            raise ValueError("source_claim_ids must not be empty")
        if len(source_claim_ids) != len(set(source_claim_ids)):
            raise ValueError("source_claim_ids must be unique")
        available = {item.claim_id for item in self.proposal.claims}
        unknown = sorted(set(source_claim_ids) - available)
        if unknown:
            raise ValueError(
                "source_claim_ids must reference proposal claims: " + ", ".join(unknown)
            )
        object.__setattr__(self, "source_claim_ids", source_claim_ids)

        if self.target_artifact_id is not None:
            object.__setattr__(
                self,
                "target_artifact_id",
                _required(self.target_artifact_id, "target_artifact_id"),
            )

    @property
    def knowledge_state(self) -> KnowledgeState:
        return KnowledgeState.PROPOSED

    def semantic_state(self) -> tuple[Any, ...]:
        return (
            self.draft_id,
            self.artifact_type,
            self.proposal.proposal_id,
            self.payload.semantic_state(),
            self.source_claim_ids,
            self.target_artifact_id,
            self.knowledge_state.value,
        )
