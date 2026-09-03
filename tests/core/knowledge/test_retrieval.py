from __future__ import annotations

import pytest

from engine.core.knowledge import (
    Claim,
    ContextBudget,
    ContextCompiler,
    ContextEntry,
    ContextPackage,
    ContextScope,
    Evidence,
    KnowledgeRevision,
    RetrievalMode,
    RetrievalRequest,
    RetrievalStrategy,
    SourceAuthority,
)
from engine.core.metamodel import KnowledgeState, SourceReference


def _entry() -> ContextEntry:
    revision = KnowledgeRevision("rev")
    evidence = Evidence(
        "ev",
        SourceReference("artifact.md", revision="rev"),
        SourceAuthority("repo", "repository"),
        revision,
    )
    claim = Claim(
        "claim",
        "statement",
        KnowledgeState.DECLARED,
        (evidence,),
    )
    return ContextEntry(claim, ContextScope.GLOBAL, "exact-id")


class ExactStrategy:
    @property
    def mode(self) -> RetrievalMode:
        return RetrievalMode.EXACT_ID

    def retrieve(self, request: RetrievalRequest) -> tuple[ContextEntry, ...]:
        return (_entry(),)


class Compiler:
    def compile(self, request: RetrievalRequest) -> ContextPackage:
        return ContextPackage(ExactStrategy().retrieve(request), request.budget)


def test_retrieval_and_compiler_protocols_are_replaceable_contracts():
    strategy = ExactStrategy()
    compiler = Compiler()
    request = RetrievalRequest(
        query="SAD-001 dependencies",
        scopes=(ContextScope.PROJECT, ContextScope.GLOBAL),
        budget=ContextBudget(5),
        modes=(RetrievalMode.GRAPH, RetrievalMode.EXACT_ID),
        exact_keys=("SAD-001",),
    )

    assert isinstance(strategy, RetrievalStrategy)
    assert isinstance(compiler, ContextCompiler)
    assert request.scopes == (ContextScope.GLOBAL, ContextScope.PROJECT)
    assert request.modes == (RetrievalMode.EXACT_ID, RetrievalMode.GRAPH)
    assert compiler.compile(request).claims[0].claim_id == "claim"


def test_retrieval_request_enforces_hybrid_contract_shape():
    budget = ContextBudget(5)

    with pytest.raises(ValueError, match="query"):
        RetrievalRequest(" ", (ContextScope.GLOBAL,), budget, (RetrievalMode.EXACT_ID,))
    with pytest.raises(ValueError, match="scopes"):
        RetrievalRequest("q", (), budget, (RetrievalMode.EXACT_ID,))
    with pytest.raises(TypeError, match="scopes"):
        RetrievalRequest("q", ("global",), budget, (RetrievalMode.EXACT_ID,))
    with pytest.raises(ValueError, match="scopes must be unique"):
        RetrievalRequest(
            "q",
            (ContextScope.GLOBAL, ContextScope.GLOBAL),
            budget,
            (RetrievalMode.EXACT_ID,),
        )
    with pytest.raises(ValueError, match="modes"):
        RetrievalRequest("q", (ContextScope.GLOBAL,), budget, ())
    with pytest.raises(TypeError, match="modes"):
        RetrievalRequest("q", (ContextScope.GLOBAL,), budget, ("graph",))
    with pytest.raises(ValueError, match="modes must be unique"):
        RetrievalRequest(
            "q",
            (ContextScope.GLOBAL,),
            budget,
            (RetrievalMode.GRAPH, RetrievalMode.GRAPH),
        )
    with pytest.raises(ValueError, match="exact-id"):
        RetrievalRequest(
            "q",
            (ContextScope.GLOBAL,),
            budget,
            (RetrievalMode.GRAPH,),
            exact_keys=("A",),
        )
    with pytest.raises(ValueError, match="exact_keys"):
        RetrievalRequest(
            "q",
            (ContextScope.GLOBAL,),
            budget,
            (RetrievalMode.EXACT_ID,),
            exact_keys=("A", "A"),
        )
    with pytest.raises(ValueError, match="allowed_states"):
        RetrievalRequest(
            "q",
            (ContextScope.GLOBAL,),
            budget,
            (RetrievalMode.GRAPH,),
            allowed_states=(),
        )
    with pytest.raises(TypeError, match="allowed_states"):
        RetrievalRequest(
            "q",
            (ContextScope.GLOBAL,),
            budget,
            (RetrievalMode.GRAPH,),
            allowed_states=("declared",),
        )
    with pytest.raises(ValueError, match="allowed_states must be unique"):
        RetrievalRequest(
            "q",
            (ContextScope.GLOBAL,),
            budget,
            (RetrievalMode.GRAPH,),
            allowed_states=(KnowledgeState.DECLARED, KnowledgeState.DECLARED),
        )
    with pytest.raises(TypeError, match="budget"):
        RetrievalRequest("q", (ContextScope.GLOBAL,), object(), (RetrievalMode.GRAPH,))
