from __future__ import annotations

import pytest

from engine.core.knowledge import Claim, KnowledgeRevision
from engine.core.metamodel import KnowledgeState
from engine.intelligence.research import (
    ResearchFinding,
    ResearchPackage,
    ResearchPlan,
    ResearchQuestion,
)


def test_research_question_and_plan(retrieval_request, architecture_plan):
    question = ResearchQuestion(" q ", " evidence? ", retrieval_request, " why ")
    plan = ResearchPlan("rp", architecture_plan.plan_id, (question,))
    assert question.question_id == "q"
    assert question.rationale == "why"
    assert plan.question_ids() == ("q",)
    assert plan.semantic_state()[0] == "rp"


def test_research_question_requires_retrieval_request(retrieval_request):
    with pytest.raises(TypeError, match="RetrievalRequest"):
        ResearchQuestion("q", "x", "request")
    with pytest.raises(ValueError, match="rationale"):
        ResearchQuestion("q", "x", retrieval_request, " ")


def test_research_plan_rejects_empty_duplicate_and_untyped(architecture_plan, retrieval_request):
    question = ResearchQuestion("q", "x", retrieval_request)
    with pytest.raises(ValueError, match="empty"):
        ResearchPlan("rp", architecture_plan.plan_id, ())
    with pytest.raises(ValueError, match="unique"):
        ResearchPlan("rp", architecture_plan.plan_id, (question, question))
    with pytest.raises(TypeError, match="ResearchQuestion"):
        ResearchPlan("rp", architecture_plan.plan_id, ("q",))


def test_research_finding_preserves_non_proposed_claim(declared_claim):
    finding = ResearchFinding("f", "q-1", declared_claim)
    assert finding.semantic_state()[0] == "f"


def test_research_finding_rejects_proposal(proposed_claim):
    with pytest.raises(ValueError, match="must not be PROPOSED"):
        ResearchFinding("f", "q", proposed_claim)
    with pytest.raises(TypeError, match="Claim"):
        ResearchFinding("f", "q", "claim")


def test_research_package_validates_lineage(research_plan, declared_claim):
    finding = ResearchFinding("f", "q-1", declared_claim)
    revision = KnowledgeRevision("rev")
    package = ResearchPackage(research_plan, (finding,), (), revision)
    assert package.claims == (declared_claim,)
    assert package.semantic_state()[-1] == revision


def test_research_package_rejects_bad_lineage(research_plan, declared_claim):
    with pytest.raises(TypeError, match="ResearchPlan"):
        ResearchPackage("plan", ())
    with pytest.raises(TypeError, match="ResearchFinding"):
        ResearchPackage(research_plan, ("finding",))
    finding = ResearchFinding("f", "unknown", declared_claim)
    with pytest.raises(ValueError, match="known question"):
        ResearchPackage(research_plan, (finding,))
    with pytest.raises(ValueError, match="unique"):
        ResearchPackage(
            research_plan,
            (ResearchFinding("f", "q-1", declared_claim), ResearchFinding("f", "q-1", declared_claim)),
        )
    with pytest.raises(ValueError, match="known questions"):
        ResearchPackage(research_plan, (), ("unknown",))
    with pytest.raises(ValueError, match="unique"):
        ResearchPackage(research_plan, (), ("q-1", "q-1"))
    with pytest.raises(TypeError, match="KnowledgeRevision"):
        ResearchPackage(research_plan, (), ("q-1",), "rev")
    with pytest.raises(ValueError, match="findings or unresolved"):
        ResearchPackage(research_plan, ())
