from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable

from engine.core.metamodel import KnowledgeState

from .context import ContextBudget, ContextEntry, ContextPackage, ContextScope


class RetrievalMode(str, Enum):
    EXACT_ID = "exact-id"
    GRAPH = "graph"
    FULL_TEXT = "full-text"
    SEMANTIC = "semantic"
    OBSERVED = "observed"
    RESEARCH = "research"


def _required(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    return normalized


@dataclass(frozen=True, slots=True)
class RetrievalRequest:
    """Provider-independent retrieval request used by ContextCompiler implementations."""

    query: str
    scopes: tuple[ContextScope, ...]
    budget: ContextBudget
    modes: tuple[RetrievalMode, ...]
    exact_keys: tuple[str, ...] = ()
    allowed_states: tuple[KnowledgeState, ...] = tuple(KnowledgeState)

    def __post_init__(self) -> None:
        object.__setattr__(self, "query", _required(self.query, "query"))
        if not isinstance(self.budget, ContextBudget):
            raise TypeError("budget must be ContextBudget")

        scopes = tuple(self.scopes)
        if not scopes:
            raise ValueError("scopes must not be empty")
        if not all(isinstance(item, ContextScope) for item in scopes):
            raise TypeError("scopes must contain ContextScope")
        if len(scopes) != len(set(scopes)):
            raise ValueError("scopes must be unique")
        object.__setattr__(
            self,
            "scopes",
            tuple(sorted(scopes, key=lambda item: item.value)),
        )

        modes = tuple(self.modes)
        if not modes:
            raise ValueError("modes must not be empty")
        if not all(isinstance(item, RetrievalMode) for item in modes):
            raise TypeError("modes must contain RetrievalMode")
        if len(modes) != len(set(modes)):
            raise ValueError("modes must be unique")
        object.__setattr__(
            self,
            "modes",
            tuple(sorted(modes, key=lambda item: item.value)),
        )

        exact_keys = tuple(_required(item, "exact_keys") for item in self.exact_keys)
        if len(exact_keys) != len(set(exact_keys)):
            raise ValueError("exact_keys must be unique")
        if exact_keys and RetrievalMode.EXACT_ID not in modes:
            raise ValueError("exact_keys require exact-id retrieval mode")
        object.__setattr__(self, "exact_keys", tuple(sorted(exact_keys)))

        allowed_states = tuple(self.allowed_states)
        if not allowed_states:
            raise ValueError("allowed_states must not be empty")
        if not all(
            isinstance(item, KnowledgeState) for item in allowed_states
        ):
            raise TypeError("allowed_states must contain KnowledgeState")
        if len(allowed_states) != len(set(allowed_states)):
            raise ValueError("allowed_states must be unique")
        object.__setattr__(
            self,
            "allowed_states",
            tuple(sorted(allowed_states, key=lambda item: item.value)),
        )


@runtime_checkable
class RetrievalStrategy(Protocol):
    """Replaceable retrieval implementation; strategy topology is not authority."""

    @property
    def mode(self) -> RetrievalMode:
        ...

    def retrieve(self, request: RetrievalRequest) -> tuple[ContextEntry, ...]:
        ...


@runtime_checkable
class ContextCompiler(Protocol):
    """Contract for compiling hybrid retrieval into one bounded ContextPackage."""

    def compile(self, request: RetrievalRequest) -> ContextPackage:
        ...
