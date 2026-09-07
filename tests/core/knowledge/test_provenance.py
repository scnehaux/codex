from __future__ import annotations

import pytest

from engine.core.knowledge.provenance import (
    Claim,
    Evidence,
    KnowledgeRevision,
    SourceAuthority,
)
from engine.core.metamodel import KnowledgeState, SourceReference


def _evidence(evidence_id: str = "ev-1") -> Evidence:
    return Evidence(
        evidence_id=evidence_id,
        source=SourceReference(origin="systems/SAD-001.md", revision="abc123"),
        authority=SourceAuthority(
            authority_id="scnehaux/codex",
            authority_type="repository",
            scope="architecture",
        ),
        revision=KnowledgeRevision(
            revision_id="abc123",
            content_digest="sha256:deadbeef",
        ),
        attributes={"locator": ["section-2"]},
    )


def test_provenance_chain_is_explicit_and_immutable():
    evidence = _evidence()
    claim = Claim(
        claim_id="claim-1",
        statement="SAD-001 depends on PAD-001",
        knowledge_state=KnowledgeState.DECLARED,
        evidence=(evidence,),
        attributes={"tags": ["dependency"]},
    )

    assert claim.evidence[0].source.origin == "systems/SAD-001.md"
    assert claim.authorities == (evidence.authority,)
    assert claim.semantic_state()[0] == "claim-1"
    assert evidence.semantic_state()[0] == "ev-1"
    assert evidence.attributes["locator"] == ("section-2",)
    assert claim.attributes["tags"] == ("dependency",)

    nested = Evidence(
        evidence_id="ev-nested",
        source=SourceReference(origin="x.md", revision="r"),
        authority=SourceAuthority("repo", "repository"),
        revision=KnowledgeRevision("r"),
        attributes={"tuple": ({"x": [1]},), "set": {"a", "b"}},
    )
    assert nested.attributes["tuple"][0]["x"] == (1,)
    assert nested.attributes["set"] == frozenset({"a", "b"})

    with pytest.raises(TypeError):
        evidence.attributes["x"] = "y"


def test_revision_alignment_is_enforced():
    with pytest.raises(ValueError, match="revision must match"):
        Evidence(
            evidence_id="ev",
            source=SourceReference(origin="x.md", revision="rev-a"),
            authority=SourceAuthority("repo", "repository"),
            revision=KnowledgeRevision("rev-b"),
        )


def test_claim_requires_unique_evidence_and_lineage():
    evidence = _evidence()

    with pytest.raises(ValueError, match="must not be empty"):
        Claim(
            claim_id="claim",
            statement="statement",
            knowledge_state=KnowledgeState.INFERRED,
            evidence=(),
        )

    with pytest.raises(ValueError, match="evidence_id"):
        Claim(
            claim_id="claim",
            statement="statement",
            knowledge_state=KnowledgeState.INFERRED,
            evidence=(evidence, evidence),
        )

    with pytest.raises(ValueError, match="derive from itself"):
        Claim(
            claim_id="claim",
            statement="statement",
            knowledge_state=KnowledgeState.INFERRED,
            evidence=(evidence,),
            derived_from=("claim",),
        )

    with pytest.raises(ValueError, match="derived_from"):
        Claim(
            claim_id="claim",
            statement="statement",
            knowledge_state=KnowledgeState.INFERRED,
            evidence=(evidence,),
            derived_from=("a", "a"),
        )


def test_provenance_validation_rejects_invalid_types_and_blank_values():
    with pytest.raises(ValueError):
        SourceAuthority(" ", "repository")
    with pytest.raises(ValueError):
        SourceAuthority("repo", " ")
    with pytest.raises(ValueError):
        SourceAuthority("repo", "repository", " ")
    with pytest.raises(ValueError):
        KnowledgeRevision(" ")
    with pytest.raises(ValueError):
        KnowledgeRevision("r", " ")
    with pytest.raises(TypeError):
        Evidence(
            "ev", object(), SourceAuthority("r", "repository"), KnowledgeRevision("r")
        )
    with pytest.raises(TypeError):
        Evidence("ev", SourceReference("x"), object(), KnowledgeRevision("r"))
    with pytest.raises(TypeError):
        Evidence(
            "ev", SourceReference("x"), SourceAuthority("r", "repository"), object()
        )
    with pytest.raises(TypeError):
        Evidence(
            "ev",
            SourceReference("x"),
            SourceAuthority("r", "repository"),
            KnowledgeRevision("r"),
            attributes=[],
        )
    with pytest.raises(TypeError):
        Claim("c", "s", "declared", (_evidence(),))
    with pytest.raises(TypeError):
        Claim("c", "s", KnowledgeState.DECLARED, (object(),))
    with pytest.raises(TypeError):
        Claim("c", "s", KnowledgeState.DECLARED, (_evidence(),), attributes=[])
