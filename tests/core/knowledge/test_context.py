from __future__ import annotations

import pytest

from engine.core.knowledge.context import (
    ContextBudget,
    ContextEntry,
    ContextPackage,
    ContextScope,
)
from engine.core.knowledge.provenance import (
    Claim,
    Evidence,
    KnowledgeRevision,
    SourceAuthority,
)
from engine.core.metamodel import KnowledgeState, SourceReference


def _claim(claim_id: str, authority_id: str = "repo") -> Claim:
    revision = KnowledgeRevision("rev-1")
    evidence = Evidence(
        evidence_id=f"ev-{claim_id}",
        source=SourceReference(origin=f"{claim_id}.md", revision="rev-1"),
        authority=SourceAuthority(authority_id, "repository"),
        revision=revision,
    )
    return Claim(
        claim_id=claim_id,
        statement=f"statement {claim_id}",
        knowledge_state=KnowledgeState.DECLARED,
        evidence=(evidence,),
    )


def test_context_package_is_bounded_sorted_and_provenance_aware():
    package = ContextPackage(
        entries=(
            ContextEntry(_claim("b", "org"), ContextScope.PROJECT, "graph"),
            ContextEntry(_claim("a", "repo"), ContextScope.GLOBAL, "exact-id"),
        ),
        budget=ContextBudget(max_items=3, max_tokens=4096),
        knowledge_revision=KnowledgeRevision("snapshot-1"),
    )

    assert [entry.claim.claim_id for entry in package.entries] == ["a", "b"]
    assert package.claims == tuple(entry.claim for entry in package.entries)
    assert tuple(package.by_scope) == (ContextScope.GLOBAL, ContextScope.PROJECT)
    assert [item.authority_id for item in package.authorities] == ["org", "repo"]
    assert package.semantic_state()[1].max_tokens == 4096


def test_context_package_rejects_budget_and_duplicate_claim_violations():
    claim = _claim("a")

    with pytest.raises(ValueError, match="max_items"):
        ContextBudget(0)
    with pytest.raises(ValueError, match="max_tokens"):
        ContextBudget(1, 0)
    with pytest.raises(ValueError, match="exceed"):
        ContextPackage(
            entries=(
                ContextEntry(_claim("a"), ContextScope.GLOBAL, "exact-id"),
                ContextEntry(_claim("b"), ContextScope.DOMAIN, "graph"),
            ),
            budget=ContextBudget(1),
        )
    with pytest.raises(ValueError, match="duplicate claim_id"):
        ContextPackage(
            entries=(
                ContextEntry(claim, ContextScope.GLOBAL, "exact-id"),
                ContextEntry(claim, ContextScope.DOMAIN, "graph"),
            ),
            budget=ContextBudget(2),
        )


def test_context_validation_rejects_invalid_types():
    claim = _claim("a")

    with pytest.raises(TypeError):
        ContextEntry(object(), ContextScope.GLOBAL, "exact-id")
    with pytest.raises(TypeError):
        ContextEntry(claim, "global", "exact-id")
    with pytest.raises(ValueError):
        ContextEntry(claim, ContextScope.GLOBAL, " ")
    with pytest.raises(TypeError):
        ContextPackage((), object())
    with pytest.raises(TypeError):
        ContextPackage((), ContextBudget(1), knowledge_revision=object())
    with pytest.raises(TypeError):
        ContextPackage((object(),), ContextBudget(1))
