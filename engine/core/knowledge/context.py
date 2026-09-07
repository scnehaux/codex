from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from .provenance import Claim, KnowledgeRevision, SourceAuthority


class ContextScope(str, Enum):
    GLOBAL = "global"
    ORGANIZATION = "organization"
    DOMAIN = "domain"
    PROJECT = "project"
    WORKING = "working"
    OBSERVED = "observed"


def _required(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    return normalized


@dataclass(frozen=True, slots=True)
class ContextBudget:
    """Provider-independent bound for a context compilation operation."""

    max_items: int
    max_tokens: int | None = None

    def __post_init__(self) -> None:
        if self.max_items < 1:
            raise ValueError("max_items must be >= 1")
        if self.max_tokens is not None and self.max_tokens < 1:
            raise ValueError("max_tokens must be >= 1 when provided")


@dataclass(frozen=True, slots=True)
class ContextEntry:
    """One provenance-preserving claim selected into a bounded context."""

    claim: Claim
    scope: ContextScope
    retrieval_strategy: str

    def __post_init__(self) -> None:
        if not isinstance(self.claim, Claim):
            raise TypeError("claim must be Claim")
        if not isinstance(self.scope, ContextScope):
            raise TypeError("scope must be ContextScope")
        object.__setattr__(
            self,
            "retrieval_strategy",
            _required(self.retrieval_strategy, "retrieval_strategy"),
        )


@dataclass(frozen=True, slots=True)
class ContextPackage:
    """Immutable, bounded and provenance-aware context contract for reasoning."""

    entries: tuple[ContextEntry, ...]
    budget: ContextBudget
    knowledge_revision: KnowledgeRevision | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.budget, ContextBudget):
            raise TypeError("budget must be ContextBudget")
        if self.knowledge_revision is not None and not isinstance(
            self.knowledge_revision, KnowledgeRevision
        ):
            raise TypeError("knowledge_revision must be KnowledgeRevision or None")

        entries = tuple(self.entries)
        if not all(isinstance(item, ContextEntry) for item in entries):
            raise TypeError("entries must contain ContextEntry")
        if len(entries) > self.budget.max_items:
            raise ValueError("context entries exceed max_items budget")

        claim_ids = [item.claim.claim_id for item in entries]
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("ContextPackage cannot contain duplicate claim_id")

        object.__setattr__(
            self,
            "entries",
            tuple(
                sorted(
                    entries,
                    key=lambda item: (
                        item.scope.value,
                        item.claim.claim_id,
                        item.retrieval_strategy,
                    ),
                )
            ),
        )

    @property
    def claims(self) -> tuple[Claim, ...]:
        return tuple(item.claim for item in self.entries)

    @property
    def by_scope(self) -> Mapping[ContextScope, tuple[ContextEntry, ...]]:
        grouped: dict[ContextScope, list[ContextEntry]] = {}
        for entry in self.entries:
            grouped.setdefault(entry.scope, []).append(entry)
        return MappingProxyType(
            {
                scope: tuple(items)
                for scope, items in sorted(
                    grouped.items(), key=lambda item: item[0].value
                )
            }
        )

    @property
    def authorities(self) -> tuple[SourceAuthority, ...]:
        unique: dict[str, SourceAuthority] = {}
        for entry in self.entries:
            for authority in entry.claim.authorities:
                unique[authority.authority_id] = authority
        return tuple(unique[key] for key in sorted(unique))

    def semantic_state(self) -> tuple[Any, ...]:
        return (
            tuple(
                (
                    entry.scope.value,
                    entry.retrieval_strategy,
                    entry.claim.semantic_state(),
                )
                for entry in self.entries
            ),
            self.budget,
            self.knowledge_revision,
        )
