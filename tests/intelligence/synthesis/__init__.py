from __future__ import annotations

from dataclasses import dataclass

import pytest

from engine.core.knowledge import Claim
from engine.intelligence.planning import ArchitecturePlan
from engine.intelligence.research import ResearchFinding, ResearchPackage
from engine.intelligence.synthesis import (
    ArchitectureProposal,
    ArtifactDraft,
    DraftPayload,
)


@dataclass(frozen=True)
class Payload:
    value: str

    def semantic_state(self):
        return (self.value,)


def test_architecture_proposal_requires_proposed_claims(
    intent, architecture_plan, context_package, proposed_claim
):
    proposal = ArchitectureProposal(
        "proposal",
        intent,
        architecture_plan,
        context_package,
        (proposed_claim,),
    )
    assert proposal.semantic_state()[0] == "proposal"


def test_architecture_proposal_validates_types_and_lineage(
    intent,
    architecture_plan,
    context_package,
    proposed_claim,
    declared_claim,
    research_plan,
):
    with pytest.raises(TypeError, match="IntentSpec"):
        ArchitectureProposal(
            "p", "intent", architecture_plan, context_package, (proposed_claim,)
        )
    with pytest.raises(TypeError, match="ArchitecturePlan"):
        ArchitectureProposal("p", intent, "plan", context_package, (proposed_claim,))
    other_intent = type(intent)("other", "x", intent.scopes)
    with pytest.raises(ValueError, match="proposal intent"):
        ArchitectureProposal(
            "p", other_intent, architecture_plan, context_package, (proposed_claim,)
        )
    with pytest.raises(TypeError, match="ContextPackage"):
        ArchitectureProposal(
            "p", intent, architecture_plan, "context", (proposed_claim,)
        )
    with pytest.raises(ValueError, match="must not be empty"):
        ArchitectureProposal("p", intent, architecture_plan, context_package, ())
    with pytest.raises(TypeError, match="Claim"):
        ArchitectureProposal(
            "p", intent, architecture_plan, context_package, ("claim",)
        )
    with pytest.raises(ValueError, match="must be PROPOSED"):
        ArchitectureProposal(
            "p", intent, architecture_plan, context_package, (declared_claim,)
        )
    with pytest.raises(ValueError, match="unique"):
        ArchitectureProposal(
            "p",
            intent,
            architecture_plan,
            context_package,
            (proposed_claim, proposed_claim),
        )

    no_lineage = Claim(
        "proposal-no-lineage",
        "Proposal without lineage",
        proposed_claim.knowledge_state,
        proposed_claim.evidence,
    )
    with pytest.raises(ValueError, match="derived_from lineage"):
        ArchitectureProposal(
            "p", intent, architecture_plan, context_package, (no_lineage,)
        )

    unknown_lineage = Claim(
        "proposal-unknown-lineage",
        "Proposal with unknown lineage",
        proposed_claim.knowledge_state,
        proposed_claim.evidence,
        derived_from=("unknown",),
    )
    with pytest.raises(ValueError, match="context/research claims"):
        ArchitectureProposal(
            "p", intent, architecture_plan, context_package, (unknown_lineage,)
        )

    other_plan = ArchitecturePlan("other-plan", intent, architecture_plan.steps)
    other_research = ResearchPackage(
        type(research_plan)("r2", other_plan.plan_id, research_plan.questions),
        (),
        ("q-1",),
    )
    with pytest.raises(ValueError, match="proposal plan"):
        ArchitectureProposal(
            "p",
            intent,
            architecture_plan,
            context_package,
            (proposed_claim,),
            other_research,
        )
    with pytest.raises(TypeError, match="ResearchPackage"):
        ArchitectureProposal(
            "p",
            intent,
            architecture_plan,
            context_package,
            (proposed_claim,),
            "research",
        )


def test_architecture_proposal_accepts_matching_research(
    intent,
    architecture_plan,
    context_package,
    proposed_claim,
    research_plan,
    declared_claim,
):
    research = ResearchPackage(
        research_plan,
        (ResearchFinding("f", "q-1", declared_claim),),
    )
    proposal = ArchitectureProposal(
        "p", intent, architecture_plan, context_package, (proposed_claim,), research
    )
    assert proposal.research is research


def test_artifact_draft_preserves_proposal_lineage(
    intent, architecture_plan, context_package, proposed_claim
):
    proposal = ArchitectureProposal(
        "p", intent, architecture_plan, context_package, (proposed_claim,)
    )
    draft = ArtifactDraft(
        "d",
        "SAD",
        proposal,
        Payload("structured"),
        (proposed_claim.claim_id,),
        "SAD-001",
    )
    assert isinstance(draft.payload, DraftPayload)
    assert draft.knowledge_state.value == "proposed"
    assert draft.semantic_state()[3] == ("structured",)


def test_artifact_draft_rejects_invalid_payload_and_lineage(
    intent, architecture_plan, context_package, proposed_claim
):
    proposal = ArchitectureProposal(
        "p", intent, architecture_plan, context_package, (proposed_claim,)
    )
    with pytest.raises(TypeError, match="ArchitectureProposal"):
        ArtifactDraft("d", "SAD", "proposal", Payload("x"), (proposed_claim.claim_id,))
    with pytest.raises(TypeError, match="DraftPayload"):
        ArtifactDraft("d", "SAD", proposal, object(), (proposed_claim.claim_id,))
    with pytest.raises(ValueError, match="must not be empty"):
        ArtifactDraft("d", "SAD", proposal, Payload("x"), ())
    with pytest.raises(ValueError, match="unique"):
        ArtifactDraft(
            "d",
            "SAD",
            proposal,
            Payload("x"),
            (proposed_claim.claim_id, proposed_claim.claim_id),
        )
    with pytest.raises(ValueError, match="proposal claims"):
        ArtifactDraft("d", "SAD", proposal, Payload("x"), ("unknown",))
    with pytest.raises(ValueError, match="target_artifact_id"):
        ArtifactDraft(
            "d", "SAD", proposal, Payload("x"), (proposed_claim.claim_id,), " "
        )

