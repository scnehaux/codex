from __future__ import annotations

from dataclasses import dataclass
import hashlib

from engine.core.knowledge import KnowledgeEdge, KnowledgeGraph

from .contracts import SimulationFinding, SimulationReport


def _required(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    return normalized


def _digest(graph: KnowledgeGraph) -> str:
    return hashlib.sha256(repr(graph.semantic_state()).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class GraphSimulationPolicy:
    """Policy knobs for graph checks without baking adopter rules into graph state."""

    cycle_relationship_types: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        values = tuple(
            _required(item, "cycle_relationship_types")
            for item in self.cycle_relationship_types
        )
        if len(values) != len(set(values)):
            raise ValueError("cycle_relationship_types must be unique")
        object.__setattr__(self, "cycle_relationship_types", tuple(sorted(values)))


def _edge_state(edge: KnowledgeEdge) -> tuple[object, ...]:
    return (
        edge.key,
        repr(edge.properties),
        edge.provenance,
    )


def _overlay(current: KnowledgeGraph, proposed: KnowledgeGraph) -> KnowledgeGraph:
    proposed_sources = {node.key for node in proposed.nodes}
    node_map = {node.key: node for node in current.nodes}
    node_map.update({node.key: node for node in proposed.nodes})

    retained_edges = [
        edge for edge in current.edges if edge.source_key not in proposed_sources
    ]
    return KnowledgeGraph(
        nodes=tuple(node_map.values()),
        edges=tuple((*retained_edges, *proposed.edges)),
    )


def _cycle_nodes(
    graph: KnowledgeGraph, relationship_types: tuple[str, ...]
) -> tuple[tuple[str, ...], ...]:
    if not relationship_types:
        return ()
    allowed = set(relationship_types)
    adjacency: dict[str, list[str]] = {node.key: [] for node in graph.nodes}
    for edge in graph.edges:
        if edge.relationship_type in allowed:
            adjacency[edge.source_key].append(edge.target_key)
    for values in adjacency.values():
        values.sort()

    cycles: set[tuple[str, ...]] = set()
    stack: list[str] = []
    on_stack: dict[str, int] = {}
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in on_stack:
            cycle = stack[on_stack[node] :]
            if cycle:
                rotations = [
                    tuple(cycle[index:] + cycle[:index]) for index in range(len(cycle))
                ]
                cycles.add(min(rotations))
            return
        if node in visited:
            return
        on_stack[node] = len(stack)
        stack.append(node)
        for target in adjacency[node]:
            visit(target)
        stack.pop()
        on_stack.pop(node, None)
        visited.add(node)

    for key in sorted(adjacency):
        visit(key)
    return tuple(sorted(cycles))


def simulate_graph(
    *,
    report_id: str,
    draft_id: str,
    current: KnowledgeGraph,
    proposed: KnowledgeGraph,
    policy: GraphSimulationPolicy = GraphSimulationPolicy(),
) -> SimulationReport:
    if not isinstance(current, KnowledgeGraph) or not isinstance(
        proposed, KnowledgeGraph
    ):
        raise TypeError("current and proposed must be KnowledgeGraph")
    if not isinstance(policy, GraphSimulationPolicy):
        raise TypeError("policy must be GraphSimulationPolicy")

    current_state = current.semantic_state()
    proposed_state = proposed.semantic_state()
    combined = _overlay(current, proposed)

    current_nodes = current.node_map
    proposed_nodes = proposed.node_map
    added = tuple(sorted(set(proposed_nodes) - set(current_nodes)))
    modified = tuple(
        sorted(
            key
            for key in set(proposed_nodes).intersection(current_nodes)
            if proposed_nodes[key] != current_nodes[key]
        )
    )
    changed = set((*added, *modified))

    current_edge_states = {_edge_state(edge) for edge in current.edges}
    proposed_edge_states = {_edge_state(edge) for edge in proposed.edges}
    for edge in proposed.edges:
        if _edge_state(edge) not in current_edge_states:
            changed.update((edge.source_key, edge.target_key))
    for edge in current.edges:
        if (
            edge.source_key in proposed_nodes
            and _edge_state(edge) not in proposed_edge_states
        ):
            changed.update((edge.source_key, edge.target_key))

    impacted = set(changed)
    for key in tuple(changed):
        impacted.update(edge.target_key for edge in combined.outgoing(key))
        impacted.update(edge.source_key for edge in combined.incoming(key))

    findings = tuple(
        SimulationFinding(
            finding_id=f"cycle-{index + 1}",
            simulation_type="cycle",
            message="Proposed graph introduces a prohibited relationship cycle.",
            impacted_keys=cycle,
            blocking=True,
        )
        for index, cycle in enumerate(
            _cycle_nodes(combined, policy.cycle_relationship_types)
        )
    )

    if (
        current.semantic_state() != current_state
        or proposed.semantic_state() != proposed_state
    ):
        raise RuntimeError("graph simulation must not mutate input graph state")

    return SimulationReport(
        report_id=report_id,
        draft_id=draft_id,
        current_graph_digest=_digest(current),
        proposed_graph_digest=_digest(proposed),
        added_node_keys=added,
        modified_node_keys=modified,
        impacted_keys=tuple(sorted(impacted)),
        findings=findings,
    )
