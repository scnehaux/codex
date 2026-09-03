import pytest

from engine.control.rendering import render_artifact, verify_round_trip
from engine.control.repository import RepositoryAssembler, RepositoryIngestionError
from engine.core.metamodel import (
    ArtifactDocumentState,
    ArtifactIdentity,
    ArtifactRelationship,
    KnowledgeState,
)
from engine.intelligence.synthesis import DraftPayload


def state():
    return ArtifactDocumentState(
        identity=ArtifactIdentity("GDC-900"),
        artifact_type="GDC",
        title="Round Trip Contract",
        lifecycle_status="draft",
        knowledge_state=KnowledgeState.PROPOSED,
        attributes={"owner": "Architecture Authority", "tags": ["roundtrip"]},
        relationships=(
            ArtifactRelationship("governed_by", ArtifactIdentity("GDC-900")),
        ),
        sections={"1. Purpose": "Prove deterministic semantic equivalence."},
    )


def test_artifact_document_state_is_valid_draft_payload_and_round_trips():
    payload = state()
    assert isinstance(payload, DraftPayload)
    rendered = render_artifact(payload, source_path="drafts/GDC-900.md")
    assert "knowledge_state: proposed" in rendered.markdown
    report = verify_round_trip(payload, source_path="drafts/GDC-900.md")
    assert report.equivalent is True
    assert report.expected_digest == report.parsed_digest


def test_renderer_is_deterministic():
    payload = state()
    first = render_artifact(payload, source_path="drafts/GDC-900.md")
    second = render_artifact(payload, source_path="drafts/GDC-900.md")
    assert first == second


def test_artifact_document_state_validates_collisions_and_sections():
    with pytest.raises(ValueError):
        ArtifactDocumentState(
            ArtifactIdentity("GDC-1"), "GDC", "T", "draft", attributes={"title": "x"}
        )
    with pytest.raises(ValueError):
        ArtifactDocumentState(
            ArtifactIdentity("GDC-1"),
            "GDC",
            "T",
            "draft",
            attributes={"governed_by": "x"},
            relationships=(
                ArtifactRelationship("governed_by", ArtifactIdentity("GDC-1")),
            ),
        )
    normalized = ArtifactDocumentState(
        ArtifactIdentity("GDC-1"), "GDC", "T", "draft", sections={" Purpose ": " body "}
    )
    assert normalized.sections["purpose"] == "body"


def test_renderer_rejects_relationship_not_allowed_for_type():
    payload = ArtifactDocumentState(
        ArtifactIdentity("GDC-1"),
        "GDC",
        "T",
        "draft",
        relationships=(ArtifactRelationship("parent_pad", ArtifactIdentity("PAD-1")),),
    )
    with pytest.raises(ValueError):
        render_artifact(payload, source_path="x.md")


def test_repository_assembler_parses_knowledge_state_and_rejects_invalid_value():
    artifact = RepositoryAssembler.artifact_from_metadata(
        metadata={
            "id": "GDC-1",
            "title": "T",
            "status": "draft",
            "knowledge_state": "proposed",
            "governed_by": ["GDC-1"],
        },
        source_path="x.md",
    ).artifact
    assert artifact.knowledge_state is KnowledgeState.PROPOSED
    assert artifact.relationships[0].knowledge_state is KnowledgeState.PROPOSED
    assert "knowledge_state" not in artifact.attributes

    with pytest.raises(RepositoryIngestionError, match="invalid knowledge_state"):
        RepositoryAssembler.artifact_from_metadata(
            metadata={
                "id": "GDC-1",
                "title": "T",
                "status": "draft",
                "knowledge_state": "future",
            },
            source_path="x.md",
        )


def test_artifact_document_state_covers_nested_freeze_and_invalid_shapes():
    payload = ArtifactDocumentState(
        ArtifactIdentity("GDC-2"),
        "GDC",
        "Nested",
        "draft",
        attributes={
            "nested": {"list": [1, {"x": 2}]},
            "tuple": (1, 2),
            "set": {"a", "b"},
        },
    )
    assert tuple(payload.attributes["nested"]["list"])[0] == 1
    assert payload.semantic_state()[0].artifact_id == "GDC-2"
    assert (
        payload.semantic_state("x.md")
        == payload.to_artifact_model("x.md").semantic_state()
    )

    with pytest.raises(TypeError):
        ArtifactDocumentState("bad", "GDC", "T", "draft")
    with pytest.raises(ValueError):
        ArtifactDocumentState(ArtifactIdentity("GDC-1"), " ", "T", "draft")
    with pytest.raises(TypeError):
        ArtifactDocumentState(
            ArtifactIdentity("GDC-1"), "GDC", "T", "draft", knowledge_state="proposed"
        )
    with pytest.raises(TypeError):
        ArtifactDocumentState(
            ArtifactIdentity("GDC-1"), "GDC", "T", "draft", attributes=[]
        )
    with pytest.raises(TypeError):
        ArtifactDocumentState(
            ArtifactIdentity("GDC-1"), "GDC", "T", "draft", attributes={1: "x"}
        )
    with pytest.raises(TypeError):
        ArtifactDocumentState(
            ArtifactIdentity("GDC-1"), "GDC", "T", "draft", relationships=(object(),)
        )
    with pytest.raises(TypeError):
        ArtifactDocumentState(
            ArtifactIdentity("GDC-1"), "GDC", "T", "draft", sections=[]
        )
    with pytest.raises(TypeError):
        ArtifactDocumentState(
            ArtifactIdentity("GDC-1"), "GDC", "T", "draft", sections={1: "body"}
        )
    with pytest.raises(ValueError):
        ArtifactDocumentState(
            ArtifactIdentity("GDC-1"),
            "GDC",
            "T",
            "draft",
            sections={" A ": "one", "a": "two"},
        )
    with pytest.raises(ValueError):
        payload.to_artifact_model(" ")


def test_rendering_support_types_and_parse_failure(monkeypatch):
    from engine.control.rendering import artifact as rendering

    payload = ArtifactDocumentState(
        ArtifactIdentity("GDC-3"),
        "GDC",
        "T",
        "draft",
        attributes={"mapping": {"x": [1]}, "set": {"a"}},
    )
    rendered = render_artifact(payload, source_path="x.md")
    assert rendered.content_digest

    with pytest.raises(TypeError):
        render_artifact(object(), source_path="x.md")
    with pytest.raises(ValueError):
        render_artifact(payload, source_path=" ")
    with pytest.raises(ValueError):
        rendering.RenderedArtifact("x", " ", "d")

    monkeypatch.setattr(rendering, "parse_frontmatter", lambda text: (None, "broken"))
    with pytest.raises(ValueError, match="cannot be parsed"):
        rendering.verify_round_trip(payload, source_path="x.md")

