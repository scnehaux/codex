from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.core.knowledge import ContextScope, RetrievalRequest


def _required(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    return normalized


def _unique_strings(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    normalized = tuple(_required(item, field_name) for item in values)
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} values must be unique")
    return normalized


@dataclass(frozen=True, slots=True)
class IntentSpec:
    """Normalized user/business intent without embedding an execution topology."""

    intent_id: str
    objective: str
    scopes: tuple[ContextScope, ...]
    requested_artifact_types: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    success_criteria: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "intent_id", _required(self.intent_id, "intent_id"))
        object.__setattr__(self, "objective", _required(self.objective, "objective"))

        scopes = tuple(self.scopes)
        if not scopes:
            raise ValueError("scopes must not be empty")
        if not all(isinstance(item, ContextScope) for item in scopes):
            raise TypeError("scopes must contain ContextScope")
        if len(scopes) != len(set(scopes)):
            raise ValueError("scopes must be unique")
        object.__setattr__(self, "scopes", scopes)

        object.__setattr__(
            self,
            "requested_artifact_types",
            _unique_strings(self.requested_artifact_types, "requested_artifact_types"),
        )
        object.__setattr__(
            self,
            "constraints",
            _unique_strings(self.constraints, "constraints"),
        )
        object.__setattr__(
            self,
            "success_criteria",
            _unique_strings(self.success_criteria, "success_criteria"),
        )

    def semantic_state(self) -> tuple[Any, ...]:
        return (
            self.intent_id,
            self.objective,
            tuple(item.value for item in self.scopes),
            self.requested_artifact_types,
            self.constraints,
            self.success_criteria,
        )


@dataclass(frozen=True, slots=True)
class PlanStep:
    """One capability-oriented planning step, independent of agent/service topology."""

    step_id: str
    capability: str
    objective: str
    depends_on: tuple[str, ...] = ()
    expected_outputs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "step_id", _required(self.step_id, "step_id"))
        object.__setattr__(self, "capability", _required(self.capability, "capability"))
        object.__setattr__(self, "objective", _required(self.objective, "objective"))
        dependencies = _unique_strings(self.depends_on, "depends_on")
        if self.step_id in dependencies:
            raise ValueError("plan step cannot depend on itself")
        object.__setattr__(self, "depends_on", dependencies)
        object.__setattr__(
            self,
            "expected_outputs",
            _unique_strings(self.expected_outputs, "expected_outputs"),
        )

    def semantic_state(self) -> tuple[Any, ...]:
        return (
            self.step_id,
            self.capability,
            self.objective,
            self.depends_on,
            self.expected_outputs,
        )


def _assert_acyclic(steps: tuple[PlanStep, ...]) -> None:
    dependencies = {step.step_id: set(step.depends_on) for step in steps}
    state: dict[str, int] = {}

    def visit(step_id: str) -> None:
        marker = state.get(step_id, 0)
        if marker == 1:
            raise ValueError("plan step dependencies must be acyclic")
        if marker == 2:
            return
        state[step_id] = 1
        for dependency in dependencies[step_id]:
            visit(dependency)
        state[step_id] = 2

    for step_id in dependencies:
        visit(step_id)


@dataclass(frozen=True, slots=True)
class ArchitecturePlan:
    """Capability plan connecting intent to bounded context/research/synthesis work."""

    plan_id: str
    intent: IntentSpec
    steps: tuple[PlanStep, ...]
    context_requests: tuple[RetrievalRequest, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "plan_id", _required(self.plan_id, "plan_id"))
        if not isinstance(self.intent, IntentSpec):
            raise TypeError("intent must be IntentSpec")

        steps = tuple(self.steps)
        if not steps:
            raise ValueError("steps must not be empty")
        if not all(isinstance(item, PlanStep) for item in steps):
            raise TypeError("steps must contain PlanStep")
        step_ids = [item.step_id for item in steps]
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("plan step_id values must be unique")
        known = set(step_ids)
        unknown = sorted(
            dependency
            for step in steps
            for dependency in step.depends_on
            if dependency not in known
        )
        if unknown:
            raise ValueError(
                "plan dependencies must reference known step_id values: "
                + ", ".join(unknown)
            )
        _assert_acyclic(steps)
        object.__setattr__(self, "steps", steps)

        requests = tuple(self.context_requests)
        if not all(isinstance(item, RetrievalRequest) for item in requests):
            raise TypeError("context_requests must contain RetrievalRequest")
        object.__setattr__(self, "context_requests", requests)

    def semantic_state(self) -> tuple[Any, ...]:
        return (
            self.plan_id,
            self.intent.semantic_state(),
            tuple(item.semantic_state() for item in self.steps),
            self.context_requests,
        )
