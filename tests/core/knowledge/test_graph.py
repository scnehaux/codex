from __future__ import annotations

import pytest

from engine.core.knowledge import (
    ExternalRef,
    GraphCompilationError,
    KnowledgeEdge,
    KnowledgeGraph,
    KnowledgeNode,
    LocalRef,
    ObservedRef,
    ReferenceKind,
    artifact_to_node,
    compile_architecture_graph,
    compile_knowledge_graph,
)
from engine.core.metamodel import (
    ArchitectureNamespace,
    ArtifactIdentity,
    ArtifactModel,
    ArtifactRelationship,
    KnowledgeState,
    SourceReference,
)


def _artifact(
    artifact_id,
    artifact_type="SAD",
    relationships=(),
    state=KnowledgeState.DECLARED,
):
    namespace = ArchitectureNamespace("acme", "architecture")
    return ArtifactModel(
        identity=ArtifactIdentity(artifact_id, namespace),
        artifact_type=artifact_type,
        title=f"Title {artifact_id}",
        lifecycle_status="approved",
        knowledge_state=state,
        relationships=relationships,
        evidence=(SourceReference(f"{artifact_id}.md", "abc", 1),),
        sections={"scope": {"value": artifact_id}},
    )


def test_artifact_compiles_to_generic_knowledge_node():
    artifact = _artifact("SAD-001")
    node = artifact_to_node(artifact)

    assert node.node_type == "artifact"
    assert node.key == "acme/architecture/SAD-001"
    assert node.properties["artifact_type"] == "SAD"
    assert node.properties["lifecycle_status"] == "approved"
    assert node.properties["sections"]["scope"]["value"] == "SAD-001"


def test_graph_supports_non_artifact_knowledge_nodes():
    artifact = _artifact("SAD-001")
    technology = KnowledgeNode(
        key="technology:kafka",
        node_type="technology",
        knowledge_state=KnowledgeState.DECLARED,
        properties={"name": "Kafka"},
    )
    uses = KnowledgeEdge(
        source_key="acme/architecture/SAD-001",
        target_key="technology:kafka",
        relationship_type="uses",
        knowledge_state=KnowledgeState.DECLARED,
    )

    graph = compile_knowledge_graph(
        [artifact],
        additional_nodes=[technology],
        additional_edges=[uses],
    )

    assert graph.node_map["technology:kafka"].node_type == "technology"
    assert graph.outgoing("acme/architecture/SAD-001") == (uses,)


def test_artifact_relationships_compile_deterministically():
    namespace = ArchitectureNamespace("acme", "architecture")
    relationship = ArtifactRelationship(
        "realizes",
        ArtifactIdentity("PAD-001", namespace),
        provenance=SourceReference("SAD-001.md", "abc", 20),
    )

    sad = _artifact("SAD-001", relationships=(relationship,))
    pad = _artifact("PAD-001", "PAD")

    first = compile_architecture_graph([sad, pad])
    second = compile_architecture_graph([pad, sad])

    assert first == second
    assert first.edges[0].relationship_type == "realizes"


def test_graph_compiler_is_fail_closed():
    duplicate = _artifact("SAD-001")
    with pytest.raises(
        GraphCompilationError,
        match="duplicate artifact identity",
    ):
        compile_knowledge_graph([duplicate, duplicate])

    namespace = ArchitectureNamespace("acme", "architecture")
    unresolved = ArtifactRelationship(
        "depends_on",
        ArtifactIdentity("SAD-404", namespace),
    )
    with pytest.raises(
        GraphCompilationError,
        match="unresolved",
    ):
        compile_knowledge_graph([_artifact("SAD-001", relationships=(unresolved,))])

    duplicate_node = KnowledgeNode(
        key="acme/architecture/SAD-001",
        node_type="technology",
        knowledge_state=KnowledgeState.DECLARED,
    )
    with pytest.raises(
        GraphCompilationError,
        match="duplicate knowledge node",
    ):
        compile_knowledge_graph(
            [_artifact("SAD-001")],
            additional_nodes=[duplicate_node],
        )

    with pytest.raises(TypeError, match="ArtifactModel"):
        compile_knowledge_graph(["bad"])
    with pytest.raises(TypeError, match="KnowledgeNode"):
        compile_knowledge_graph([], additional_nodes=["bad"])
    with pytest.raises(TypeError, match="KnowledgeEdge"):
        compile_knowledge_graph([], additional_edges=["bad"])


def test_knowledge_graph_core_validation():
    source = KnowledgeNode(
        "source",
        "system",
        KnowledgeState.DECLARED,
    )
    target = KnowledgeNode(
        "target",
        "technology",
        KnowledgeState.OBSERVED,
    )
    edge = KnowledgeEdge(
        "source",
        "target",
        "uses",
        KnowledgeState.OBSERVED,
    )

    graph = KnowledgeGraph([target, source], [edge])
    assert graph.nodes == (source, target)
    assert graph.incoming("target") == (edge,)
    assert graph.semantic_state()[0][0][0] == "source"

    with pytest.raises(ValueError, match="duplicate knowledge node"):
        KnowledgeGraph((source, source), ())
    with pytest.raises(ValueError, match="dangling edge"):
        KnowledgeGraph((source,), (edge,))
    with pytest.raises(ValueError, match="duplicate knowledge edge"):
        KnowledgeGraph((source, target), (edge, edge))
    with pytest.raises(TypeError, match="KnowledgeNode"):
        KnowledgeGraph(("bad",), ())
    with pytest.raises(TypeError, match="KnowledgeEdge"):
        KnowledgeGraph((source, target), ("bad",))


def test_reference_contracts():
    identity = ArtifactIdentity(
        "SAD-001",
        ArchitectureNamespace("acme", "architecture"),
    )
    local = LocalRef(identity)
    assert local.kind is ReferenceKind.LOCAL
    assert local.key == "acme/architecture/SAD-001"

    external = ExternalRef(
        "scnehaux://other/repo/PAD-001",
        "other-architecture",
        SourceReference("catalog", "1"),
    )
    assert external.kind is ReferenceKind.EXTERNAL
    assert external.key == "scnehaux://other/repo/PAD-001"

    observed = ObservedRef(
        "aws:lambda:notification",
        "runtime-resource",
        SourceReference("aws-inventory", "2026-08-30"),
    )
    assert observed.kind is ReferenceKind.OBSERVED

    with pytest.raises(TypeError, match="ArtifactIdentity"):
        LocalRef("bad")
    with pytest.raises(ValueError, match="uri"):
        ExternalRef("", "authority")
    with pytest.raises(ValueError, match="authority"):
        ExternalRef("uri", "")
    with pytest.raises(TypeError, match="provenance"):
        ExternalRef("uri", "authority", "bad")
    with pytest.raises(ValueError, match="source_key"):
        ObservedRef("", "runtime", SourceReference("x"))
    with pytest.raises(ValueError, match="source_kind"):
        ObservedRef("x", "", SourceReference("x"))
    with pytest.raises(TypeError, match="provenance"):
        ObservedRef("x", "runtime", "bad")


# PHASE-6.6A-BEHAVIORAL-COVERAGE


def test_artifact_to_node_rejects_non_artifact():
    with pytest.raises(TypeError, match="ArtifactModel"):
        artifact_to_node("bad")


@pytest.mark.parametrize(
    ("factory", "match"),
    [
        (
            lambda: KnowledgeNode(
                "",
                "system",
                KnowledgeState.DECLARED,
            ),
            "key",
        ),
        (
            lambda: KnowledgeNode(
                "system:one",
                "",
                KnowledgeState.DECLARED,
            ),
            "node_type",
        ),
        (
            lambda: KnowledgeEdge(
                "",
                "target",
                "uses",
                KnowledgeState.DECLARED,
            ),
            "source_key",
        ),
        (
            lambda: KnowledgeEdge(
                "source",
                "",
                "uses",
                KnowledgeState.DECLARED,
            ),
            "target_key",
        ),
        (
            lambda: KnowledgeEdge(
                "source",
                "target",
                "",
                KnowledgeState.DECLARED,
            ),
            "relationship_type",
        ),
    ],
)
def test_knowledge_graph_rejects_blank_semantics(factory, match):
    with pytest.raises(ValueError, match=match):
        factory()


def test_knowledge_node_rejects_invalid_state_properties_and_provenance():
    with pytest.raises(TypeError, match="knowledge_state"):
        KnowledgeNode(
            "system:one",
            "system",
            "declared",
        )

    with pytest.raises(TypeError, match="properties"):
        KnowledgeNode(
            "system:one",
            "system",
            KnowledgeState.DECLARED,
            properties=["bad"],
        )

    with pytest.raises(TypeError, match="provenance"):
        KnowledgeNode(
            "system:one",
            "system",
            KnowledgeState.DECLARED,
            provenance=("bad",),
        )


def test_knowledge_edge_rejects_invalid_state_properties_and_provenance():
    with pytest.raises(TypeError, match="knowledge_state"):
        KnowledgeEdge(
            "source",
            "target",
            "uses",
            "declared",
        )

    with pytest.raises(TypeError, match="provenance"):
        KnowledgeEdge(
            "source",
            "target",
            "uses",
            KnowledgeState.DECLARED,
            provenance="bad",
        )

    with pytest.raises(TypeError, match="properties"):
        KnowledgeEdge(
            "source",
            "target",
            "uses",
            KnowledgeState.DECLARED,
            properties=["bad"],
        )


def test_compile_knowledge_graph_wraps_invalid_additional_edge():
    source = KnowledgeNode(
        "source",
        "system",
        KnowledgeState.DECLARED,
    )
    dangling = KnowledgeEdge(
        "source",
        "missing",
        "uses",
        KnowledgeState.DECLARED,
    )

    with pytest.raises(
        GraphCompilationError,
        match="dangling edge",
    ):
        compile_knowledge_graph(
            [],
            additional_nodes=[source],
            additional_edges=[dangling],
        )


def test_repository_graph_compiler_requires_canonical_repository_model():
    from engine.core.knowledge.compiler import compile_repository_graph
    from engine.core.repository import RepositoryArtifact, RepositoryModel

    artifact = _artifact("SAD-900")
    repository = RepositoryModel(
        (RepositoryArtifact(artifact=artifact, source_path="systems/SAD-900.md"),)
    )
    graph = compile_repository_graph(repository)
    assert tuple(node.key for node in graph.nodes) == (artifact.canonical_key,)

    with pytest.raises(TypeError, match="RepositoryModel"):
        compile_repository_graph((artifact,))  # type: ignore[arg-type]
