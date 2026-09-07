from __future__ import annotations

from collections.abc import Iterable

from engine.core.metamodel import ArtifactModel
from engine.core.repository import RepositoryModel

from .graph import KnowledgeEdge, KnowledgeGraph, KnowledgeNode


class GraphCompilationError(ValueError):
    pass


def artifact_to_node(artifact: ArtifactModel) -> KnowledgeNode:
    if not isinstance(artifact, ArtifactModel):
        raise TypeError("artifact must be ArtifactModel")

    return KnowledgeNode(
        key=artifact.canonical_key,
        node_type="artifact",
        knowledge_state=artifact.knowledge_state,
        properties={
            "artifact_type": artifact.artifact_type,
            "title": artifact.title,
            "lifecycle_status": artifact.lifecycle_status,
            "sections": artifact.sections,
        },
        provenance=artifact.evidence,
    )


def _compile_artifacts(
    artifacts: Iterable[ArtifactModel],
    *,
    additional_nodes: Iterable[KnowledgeNode] = (),
    additional_edges: Iterable[KnowledgeEdge] = (),
) -> KnowledgeGraph:
    artifact_list = tuple(artifacts)
    extra_nodes = tuple(additional_nodes)
    extra_edges = tuple(additional_edges)

    if not all(isinstance(artifact, ArtifactModel) for artifact in artifact_list):
        raise TypeError("artifacts must contain ArtifactModel")
    if not all(isinstance(node, KnowledgeNode) for node in extra_nodes):
        raise TypeError("additional_nodes must contain KnowledgeNode")
    if not all(isinstance(edge, KnowledgeEdge) for edge in extra_edges):
        raise TypeError("additional_edges must contain KnowledgeEdge")

    by_key: dict[str, ArtifactModel] = {}
    for artifact in artifact_list:
        key = artifact.canonical_key
        if key in by_key:
            raise GraphCompilationError(f"duplicate artifact identity: {key}")
        by_key[key] = artifact

    artifact_nodes = tuple(artifact_to_node(artifact) for artifact in by_key.values())
    all_node_keys = {node.key for node in (*artifact_nodes, *extra_nodes)}

    if len(all_node_keys) != len(artifact_nodes) + len(extra_nodes):
        raise GraphCompilationError("duplicate knowledge node identity")

    edges: list[KnowledgeEdge] = list(extra_edges)
    for artifact in by_key.values():
        for relationship in artifact.relationships:
            target_key = relationship.target.canonical_key
            if target_key not in all_node_keys:
                raise GraphCompilationError(
                    "relationship target is unresolved: "
                    f"{artifact.canonical_key} "
                    f"{relationship.relation_type} "
                    f"{target_key}"
                )
            edges.append(
                KnowledgeEdge(
                    source_key=artifact.canonical_key,
                    target_key=target_key,
                    relationship_type=relationship.relation_type,
                    knowledge_state=relationship.knowledge_state,
                    provenance=relationship.provenance,
                )
            )

    try:
        return KnowledgeGraph(
            nodes=(*artifact_nodes, *extra_nodes),
            edges=tuple(edges),
        )
    except ValueError as exc:
        raise GraphCompilationError(str(exc)) from exc


def compile_repository_graph(
    repository: RepositoryModel,
    *,
    additional_nodes: Iterable[KnowledgeNode] = (),
    additional_edges: Iterable[KnowledgeEdge] = (),
) -> KnowledgeGraph:
    """Compile graph state from the canonical RepositoryModel authority."""
    if not isinstance(repository, RepositoryModel):
        raise TypeError("repository must be RepositoryModel")
    return _compile_artifacts(
        repository.artifact_models,
        additional_nodes=additional_nodes,
        additional_edges=additional_edges,
    )


def compile_knowledge_graph(
    artifacts: Iterable[ArtifactModel],
    *,
    additional_nodes: Iterable[KnowledgeNode] = (),
    additional_edges: Iterable[KnowledgeEdge] = (),
) -> KnowledgeGraph:
    """Compatibility entry point for already-canonical ArtifactModel sequences."""
    return _compile_artifacts(
        artifacts,
        additional_nodes=additional_nodes,
        additional_edges=additional_edges,
    )


def compile_architecture_graph(
    artifacts: Iterable[ArtifactModel],
) -> KnowledgeGraph:
    """Compatibility entry point for artifact-only callers."""
    return compile_knowledge_graph(artifacts)
