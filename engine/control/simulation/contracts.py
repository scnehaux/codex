from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class SimulationOutcome(str, Enum):
    PASS = "pass"
    FAIL = "fail"


def _required(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    return normalized


@dataclass(frozen=True, slots=True)
class SimulationFinding:
    finding_id: str
    simulation_type: str
    message: str
    impacted_keys: tuple[str, ...]
    blocking: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "finding_id", _required(self.finding_id, "finding_id"))
        object.__setattr__(
            self,
            "simulation_type",
            _required(self.simulation_type, "simulation_type"),
        )
        object.__setattr__(self, "message", _required(self.message, "message"))
        impacted = tuple(_required(item, "impacted_keys") for item in self.impacted_keys)
        if not impacted:
            raise ValueError("impacted_keys must not be empty")
        if len(impacted) != len(set(impacted)):
            raise ValueError("impacted_keys must be unique")
        object.__setattr__(self, "impacted_keys", tuple(sorted(impacted)))

    def semantic_state(self) -> tuple[Any, ...]:
        return (
            self.finding_id,
            self.simulation_type,
            self.message,
            self.impacted_keys,
            self.blocking,
        )


@dataclass(frozen=True, slots=True)
class SimulationReport:
    """Non-mutating impact result over CURRENT + PROPOSED graph state."""

    report_id: str
    draft_id: str
    current_graph_digest: str
    proposed_graph_digest: str
    added_node_keys: tuple[str, ...] = ()
    modified_node_keys: tuple[str, ...] = ()
    impacted_keys: tuple[str, ...] = ()
    findings: tuple[SimulationFinding, ...] = ()

    def __post_init__(self) -> None:
        for field_name in (
            "report_id",
            "draft_id",
            "current_graph_digest",
            "proposed_graph_digest",
        ):
            object.__setattr__(self, field_name, _required(getattr(self, field_name), field_name))
        for field_name in ("added_node_keys", "modified_node_keys", "impacted_keys"):
            values = tuple(_required(item, field_name) for item in getattr(self, field_name))
            if len(values) != len(set(values)):
                raise ValueError(f"{field_name} values must be unique")
            object.__setattr__(self, field_name, tuple(sorted(values)))
        findings = tuple(self.findings)
        if not all(isinstance(item, SimulationFinding) for item in findings):
            raise TypeError("findings must contain SimulationFinding")
        ids = [item.finding_id for item in findings]
        if len(ids) != len(set(ids)):
            raise ValueError("simulation finding_id values must be unique")
        object.__setattr__(self, "findings", tuple(sorted(findings, key=lambda item: item.finding_id)))

    @property
    def outcome(self) -> SimulationOutcome:
        if any(item.blocking for item in self.findings):
            return SimulationOutcome.FAIL
        return SimulationOutcome.PASS

    def semantic_state(self) -> tuple[Any, ...]:
        return (
            self.report_id,
            self.draft_id,
            self.current_graph_digest,
            self.proposed_graph_digest,
            self.added_node_keys,
            self.modified_node_keys,
            self.impacted_keys,
            self.outcome.value,
            tuple(item.semantic_state() for item in self.findings),
        )
