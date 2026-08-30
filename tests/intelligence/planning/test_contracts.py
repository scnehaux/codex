from __future__ import annotations

import pytest

from engine.core.knowledge import ContextBudget, ContextScope, RetrievalMode, RetrievalRequest
from engine.intelligence.planning import ArchitecturePlan, IntentSpec, PlanStep


def test_intent_normalizes_and_exposes_semantic_state():
    intent = IntentSpec(
        " i-1 ",
        " objective ",
        (ContextScope.DOMAIN,),
        ("PAD",),
        ("constraint",),
        ("criterion",),
    )
    assert intent.intent_id == "i-1"
    assert intent.semantic_state()[0:2] == ("i-1", "objective")


@pytest.mark.parametrize(
    "kwargs,match",
    [
        ({"intent_id": " ", "objective": "x", "scopes": (ContextScope.DOMAIN,)}, "intent_id"),
        ({"intent_id": "i", "objective": "x", "scopes": ()}, "scopes"),
        ({"intent_id": "i", "objective": "x", "scopes": ("domain",)}, "ContextScope"),
        ({"intent_id": "i", "objective": "x", "scopes": (ContextScope.DOMAIN, ContextScope.DOMAIN)}, "unique"),
        ({"intent_id": "i", "objective": "x", "scopes": (ContextScope.DOMAIN,), "constraints": ("x", "x")}, "unique"),
    ],
)
def test_intent_rejects_invalid_shape(kwargs, match):
    with pytest.raises((TypeError, ValueError), match=match):
        IntentSpec(**kwargs)


def test_plan_step_contract():
    step = PlanStep("s2", "research", "Resolve gap", ("s1",), ("ResearchPackage",))
    assert step.semantic_state()[0] == "s2"
    with pytest.raises(ValueError, match="itself"):
        PlanStep("s", "research", "x", ("s",))
    with pytest.raises(ValueError, match="unique"):
        PlanStep("s", "research", "x", (), ("x", "x"))


def test_architecture_plan_is_capability_dag(intent):
    request = RetrievalRequest(
        "x", (ContextScope.PROJECT,), ContextBudget(2), (RetrievalMode.GRAPH,)
    )
    plan = ArchitecturePlan(
        "p",
        intent,
        (PlanStep("a", "context", "A"), PlanStep("b", "synthesis", "B", ("a",))),
        (request,),
    )
    assert plan.semantic_state()[0] == "p"


@pytest.mark.parametrize(
    "steps,match",
    [
        ((), "empty"),
        ((PlanStep("a", "x", "x"), PlanStep("a", "y", "y")), "unique"),
        ((PlanStep("a", "x", "x", ("missing",)),), "known"),
        ((PlanStep("a", "x", "x", ("b",)), PlanStep("b", "x", "x", ("a",))), "acyclic"),
    ],
)
def test_architecture_plan_rejects_invalid_dag(intent, steps, match):
    with pytest.raises(ValueError, match=match):
        ArchitecturePlan("p", intent, steps)


def test_architecture_plan_requires_typed_inputs(intent):
    with pytest.raises(TypeError, match="IntentSpec"):
        ArchitecturePlan("p", "intent", (PlanStep("a", "x", "x"),))
    with pytest.raises(TypeError, match="PlanStep"):
        ArchitecturePlan("p", intent, ("step",))
    with pytest.raises(TypeError, match="RetrievalRequest"):
        ArchitecturePlan("p", intent, (PlanStep("a", "x", "x"),), ("request",))
