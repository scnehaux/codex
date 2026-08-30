import pytest

from engine.control.simulation import GraphSimulationPolicy, simulate_graph
from engine.core.knowledge import KnowledgeEdge, KnowledgeGraph, KnowledgeNode
from engine.core.metamodel import KnowledgeState


def node(key, title):
    return KnowledgeNode(key, "artifact", KnowledgeState.DECLARED, {"title": title})


def edge(source, target, relation="depends_on"):
    return KnowledgeEdge(source, target, relation, KnowledgeState.DECLARED)


def test_graph_simulation_reports_impact_without_mutating_inputs():
    current = KnowledgeGraph(
        nodes=(node("A", "old"), node("B", "b")),
        edges=(edge("A", "B"),),
    )
    proposed = KnowledgeGraph(
        nodes=(node("A", "new"), node("C", "c")),
        edges=(edge("A", "C"),),
    )
    before_current = current.semantic_state()
    before_proposed = proposed.semantic_state()

    report = simulate_graph(
        report_id="SIM-1",
        draft_id="D-1",
        current=current,
        proposed=proposed,
    )

    assert report.added_node_keys == ("C",)
    assert report.modified_node_keys == ("A",)
    assert report.impacted_keys == ("A", "B", "C")
    assert report.findings == ()
    assert current.semantic_state() == before_current
    assert proposed.semantic_state() == before_proposed


def test_graph_simulation_detects_configured_cycles():
    current = KnowledgeGraph(nodes=(node("A", "a"), node("B", "b")))
    proposed = KnowledgeGraph(
        nodes=(node("A", "a"), node("B", "b")),
        edges=(edge("A", "B"), edge("B", "A")),
    )
    report = simulate_graph(
        report_id="SIM-2",
        draft_id="D-2",
        current=current,
        proposed=proposed,
        policy=GraphSimulationPolicy(("depends_on",)),
    )
    assert report.outcome.value == "fail"
    assert report.findings[0].impacted_keys == ("A", "B")


def test_graph_simulation_policy_and_types_fail_closed():
    with pytest.raises(ValueError):
        GraphSimulationPolicy(("x", "x"))
    graph = KnowledgeGraph()
    with pytest.raises(TypeError):
        simulate_graph(report_id="S", draft_id="D", current=object(), proposed=graph)
    with pytest.raises(TypeError):
        simulate_graph(report_id="S", draft_id="D", current=graph, proposed=graph, policy=object())
