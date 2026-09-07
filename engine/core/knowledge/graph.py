from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

from engine.core.metamodel import KnowledgeState, SourceReference


def _required(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    return normalized


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze(item) for item in value)
    return value


@dataclass(frozen=True, slots=True)
class KnowledgeNode:
    key: str
    node_type: str
    knowledge_state: KnowledgeState
    properties: Mapping[str, Any] = field(default_factory=dict)
    provenance: tuple[SourceReference, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "key", _required(self.key, "key"))
        object.__setattr__(
            self,
            "node_type",
            _required(self.node_type, "node_type"),
        )
        if not isinstance(self.knowledge_state, KnowledgeState):
            raise TypeError("knowledge_state must be KnowledgeState")
        if not isinstance(self.properties, Mapping):
            raise TypeError("properties must be a mapping")

        provenance = tuple(self.provenance)
        if not all(isinstance(item, SourceReference) for item in provenance):
            raise TypeError("provenance must contain SourceReference")

        object.__setattr__(self, "properties", _freeze(self.properties))
        object.__setattr__(self, "provenance", provenance)


@dataclass(frozen=True, slots=True)
class KnowledgeEdge:
    source_key: str
    target_key: str
    relationship_type: str
    knowledge_state: KnowledgeState
    provenance: SourceReference | None = None
    properties: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_key",
            _required(self.source_key, "source_key"),
        )
        object.__setattr__(
            self,
            "target_key",
            _required(self.target_key, "target_key"),
        )
        object.__setattr__(
            self,
            "relationship_type",
            _required(self.relationship_type, "relationship_type"),
        )
        if not isinstance(self.knowledge_state, KnowledgeState):
            raise TypeError("knowledge_state must be KnowledgeState")
        if self.provenance is not None and not isinstance(
            self.provenance, SourceReference
        ):
            raise TypeError("provenance must be SourceReference or None")
        if not isinstance(self.properties, Mapping):
            raise TypeError("properties must be a mapping")
        object.__setattr__(self, "properties", _freeze(self.properties))

    @property
    def key(self) -> tuple[str, str, str, str]:
        return (
            self.source_key,
            self.relationship_type,
            self.target_key,
            self.knowledge_state.value,
        )


@dataclass(frozen=True, slots=True)
class KnowledgeGraph:
    nodes: tuple[KnowledgeNode, ...] = ()
    edges: tuple[KnowledgeEdge, ...] = ()

    def __post_init__(self) -> None:
        nodes = tuple(self.nodes)
        edges = tuple(self.edges)

        if not all(isinstance(node, KnowledgeNode) for node in nodes):
            raise TypeError("nodes must contain KnowledgeNode")
        if not all(isinstance(edge, KnowledgeEdge) for edge in edges):
            raise TypeError("edges must contain KnowledgeEdge")

        node_keys = [node.key for node in nodes]
        if len(node_keys) != len(set(node_keys)):
            raise ValueError("duplicate knowledge node key")

        known = set(node_keys)
        for edge in edges:
            if edge.source_key not in known or edge.target_key not in known:
                raise ValueError(f"graph contains dangling edge: {edge.key}")

        edge_keys = [edge.key for edge in edges]
        if len(edge_keys) != len(set(edge_keys)):
            raise ValueError("duplicate knowledge edge")

        object.__setattr__(
            self,
            "nodes",
            tuple(sorted(nodes, key=lambda node: node.key)),
        )
        object.__setattr__(
            self,
            "edges",
            tuple(sorted(edges, key=lambda edge: edge.key)),
        )

    @property
    def node_map(self) -> Mapping[str, KnowledgeNode]:
        return MappingProxyType({node.key: node for node in self.nodes})

    def outgoing(self, source_key: str) -> tuple[KnowledgeEdge, ...]:
        return tuple(edge for edge in self.edges if edge.source_key == source_key)

    def incoming(self, target_key: str) -> tuple[KnowledgeEdge, ...]:
        return tuple(edge for edge in self.edges if edge.target_key == target_key)

    def semantic_state(self) -> tuple[Any, ...]:
        node_state = tuple(
            (
                node.key,
                node.node_type,
                node.knowledge_state.value,
                node.properties,
                node.provenance,
            )
            for node in self.nodes
        )
        edge_state = tuple(
            (
                edge.source_key,
                edge.relationship_type,
                edge.target_key,
                edge.knowledge_state.value,
                edge.properties,
                edge.provenance,
            )
            for edge in self.edges
        )
        return node_state, edge_state


ArchitectureGraph = KnowledgeGraph
ArchitectureNode = KnowledgeNode
ArchitectureEdge = KnowledgeEdge
