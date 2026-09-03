from __future__ import annotations

from types import MappingProxyType

import pytest

from engine.core.metamodel import (
    ArchitectureNamespace,
    ArtifactIdentity,
    ArtifactModel,
    ArtifactRelationship,
    KnowledgeState,
    SourceReference,
)


def test_namespace_normalizes_and_builds_key():
    namespace = ArchitectureNamespace(" acme ", " architecture ")
    assert namespace.organization_id == "acme"
    assert namespace.repository_id == "architecture"
    assert namespace.key == "acme/architecture"


@pytest.mark.parametrize(
    ("field", "kwargs"),
    [
        ("organization_id", {"organization_id": " ", "repository_id": "repo"}),
        ("repository_id", {"organization_id": "org", "repository_id": ""}),
    ],
)
def test_namespace_rejects_blank_values(field, kwargs):
    with pytest.raises(ValueError, match=field):
        ArchitectureNamespace(**kwargs)


def test_identity_supports_local_and_namespaced_keys_and_uri():
    local = ArtifactIdentity(" SAD-001 ")
    assert local.artifact_id == "SAD-001"
    assert local.canonical_key == "SAD-001"
    assert local.canonical_uri == "scnehaux:///architecture/SAD-001"

    namespace = ArchitectureNamespace("acme corp", "main architecture")
    scoped = ArtifactIdentity("SAD/001", namespace)

    assert scoped.canonical_key == "acme corp/main architecture/SAD/001"
    assert (
        scoped.canonical_uri == "scnehaux://acme%20corp/main%20architecture/SAD%2F001"
    )


def test_identity_rejects_blank_artifact_id():
    with pytest.raises(ValueError, match="artifact_id"):
        ArtifactIdentity(" ")


def test_source_reference_normalizes_and_validates():
    source = SourceReference(" repo/file.md ", " abc123 ", 4)
    assert source.origin == "repo/file.md"
    assert source.revision == "abc123"
    assert source.line == 4

    assert SourceReference("repo/file.md").revision is None

    with pytest.raises(ValueError, match="revision"):
        SourceReference("repo/file.md", " ")

    with pytest.raises(ValueError, match="line"):
        SourceReference("repo/file.md", line=0)

    with pytest.raises(ValueError, match="origin"):
        SourceReference(" ")


def test_relationship_contract():
    target = ArtifactIdentity("PAD-001")
    source = SourceReference("domains/pad.md")

    relation = ArtifactRelationship(
        " realizes ",
        target,
        KnowledgeState.PROPOSED,
        source,
    )

    assert relation.relation_type == "realizes"
    assert relation.target == target
    assert relation.knowledge_state is KnowledgeState.PROPOSED
    assert relation.provenance == source

    with pytest.raises(ValueError, match="relation_type"):
        ArtifactRelationship(" ", target)

    with pytest.raises(TypeError, match="target"):
        ArtifactRelationship("realizes", "PAD-001")  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="knowledge_state"):
        ArtifactRelationship(
            "realizes",
            target,
            "declared",  # type: ignore[arg-type]
        )


def test_artifact_model_is_immutable_and_semantic():
    identity = ArtifactIdentity(
        "SAD-001",
        ArchitectureNamespace("acme", "architecture"),
    )
    target = ArtifactIdentity(
        "PAD-001",
        ArchitectureNamespace("acme", "architecture"),
    )
    source = SourceReference("systems/SAD-001.md", "abc", 1)
    relation = ArtifactRelationship("realizes", target)

    model = ArtifactModel(
        identity=identity,
        artifact_type=" SAD ",
        title=" Identity Service ",
        lifecycle_status=" draft ",
        knowledge_state=KnowledgeState.PROPOSED,
        relationships=[relation],
        sections={
            "scope": {
                "in": ["authentication", "sessions"],
                "tags": {"iam", "security"},
            }
        },
        evidence=[source],
    )

    assert model.canonical_key == "acme/architecture/SAD-001"
    assert model.artifact_type == "SAD"
    assert model.title == "Identity Service"
    assert model.lifecycle_status == "draft"
    assert model.relationships == (relation,)
    assert model.evidence == (source,)
    assert isinstance(model.sections, MappingProxyType)
    assert model.sections["scope"]["in"] == (
        "authentication",
        "sessions",
    )
    assert model.sections["scope"]["tags"] == frozenset({"iam", "security"})

    state = model.semantic_state()
    assert state[0] == identity
    assert state[1] == "SAD"
    assert state[4] == "proposed"
    assert state[5][0][:3] == (
        "realizes",
        "acme/architecture/PAD-001",
        "declared",
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("artifact_type", " "),
        ("title", ""),
        ("lifecycle_status", " "),
    ],
)
def test_artifact_model_rejects_blank_semantics(field, value):
    kwargs = {
        "identity": ArtifactIdentity("SAD-001"),
        "artifact_type": "SAD",
        "title": "System",
        "lifecycle_status": "draft",
    }
    kwargs[field] = value

    with pytest.raises(ValueError, match=field):
        ArtifactModel(**kwargs)


def test_artifact_model_rejects_invalid_structured_types():
    identity = ArtifactIdentity("SAD-001")

    with pytest.raises(TypeError, match="identity"):
        ArtifactModel(  # type: ignore[arg-type]
            identity="SAD-001",
            artifact_type="SAD",
            title="System",
            lifecycle_status="draft",
        )

    with pytest.raises(TypeError, match="knowledge_state"):
        ArtifactModel(
            identity=identity,
            artifact_type="SAD",
            title="System",
            lifecycle_status="draft",
            knowledge_state="declared",  # type: ignore[arg-type]
        )

    with pytest.raises(TypeError, match="relationships"):
        ArtifactModel(
            identity=identity,
            artifact_type="SAD",
            title="System",
            lifecycle_status="draft",
            relationships=("not-a-relationship",),  # type: ignore[arg-type]
        )

    with pytest.raises(TypeError, match="evidence"):
        ArtifactModel(
            identity=identity,
            artifact_type="SAD",
            title="System",
            lifecycle_status="draft",
            evidence=("not-a-source",),  # type: ignore[arg-type]
        )

    with pytest.raises(TypeError, match="sections"):
        ArtifactModel(
            identity=identity,
            artifact_type="SAD",
            title="System",
            lifecycle_status="draft",
            sections=["not", "mapping"],  # type: ignore[arg-type]
        )
