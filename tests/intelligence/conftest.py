from __future__ import annotations

import pytest

from engine.core.knowledge import (
    Claim,
    ContextBudget,
    ContextEntry,
    ContextPackage,
    ContextScope,
    Evidence,
    KnowledgeRevision,
    RetrievalMode,
    RetrievalRequest,
    SourceAuthority,
)
from engine.core.metamodel import KnowledgeState, SourceReference
from engine.intelligence.planning import ArchitecturePlan, IntentSpec, PlanStep
from engine.intelligence.research import ResearchPlan, ResearchQuestion


@pytest.fixture
def evidence() -> Evidence:
    revision = KnowledgeRevision("rev-1")
    return Evidence(
        "ev-1",
        SourceReference("repo://architecture", revision="rev-1"),
        SourceAuthority("git", "repository"),
        revision,
    )


@pytest.fixture
def declared_claim(evidence: Evidence) -> Claim:
    return Claim(
        "claim-declared", "Declared fact", KnowledgeState.DECLARED, (evidence,)
    )


@pytest.fixture
def proposed_claim(evidence: Evidence) -> Claim:
    return Claim(
        "claim-proposed",
        "Proposed architecture",
        KnowledgeState.PROPOSED,
        (evidence,),
        derived_from=("claim-declared",),
    )


@pytest.fixture
def retrieval_request() -> RetrievalRequest:
    return RetrievalRequest(
        "architecture context",
        (ContextScope.PROJECT,),
        ContextBudget(max_items=4),
        (RetrievalMode.EXACT_ID, RetrievalMode.GRAPH),
    )


@pytest.fixture
def intent() -> IntentSpec:
    return IntentSpec(
        "intent-1",
        "Design target architecture",
        (ContextScope.PROJECT,),
        ("SAD",),
        ("preserve authority boundaries",),
        ("deterministic validation ready",),
    )


@pytest.fixture
def architecture_plan(
    intent: IntentSpec, retrieval_request: RetrievalRequest
) -> ArchitecturePlan:
    return ArchitecturePlan(
        "plan-1",
        intent,
        (
            PlanStep("context", "context-compilation", "Compile bounded context"),
            PlanStep("research", "research", "Resolve evidence gaps", ("context",)),
            PlanStep(
                "synthesis",
                "architecture-synthesis",
                "Synthesize proposal",
                ("research",),
            ),
        ),
        (retrieval_request,),
    )


@pytest.fixture
def research_plan(
    architecture_plan: ArchitecturePlan, retrieval_request: RetrievalRequest
) -> ResearchPlan:
    return ResearchPlan(
        "research-1",
        architecture_plan.plan_id,
        (ResearchQuestion("q-1", "What does evidence support?", retrieval_request),),
    )


@pytest.fixture
def context_package(declared_claim: Claim) -> ContextPackage:
    return ContextPackage(
        (ContextEntry(declared_claim, ContextScope.PROJECT, "exact-id"),),
        ContextBudget(max_items=4),
    )
