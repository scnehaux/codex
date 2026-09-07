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


def _optional(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _required(value, field_name)


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
class SourceAuthority:
    """Authority boundary that vouches for a source, independent of its location."""

    authority_id: str
    authority_type: str
    scope: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "authority_id",
            _required(self.authority_id, "authority_id"),
        )
        object.__setattr__(
            self,
            "authority_type",
            _required(self.authority_type, "authority_type"),
        )
        object.__setattr__(
            self,
            "scope",
            _optional(self.scope, "scope"),
        )


@dataclass(frozen=True, slots=True)
class KnowledgeRevision:
    """Stable source revision identity used to reconstruct knowledge state."""

    revision_id: str
    content_digest: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "revision_id",
            _required(self.revision_id, "revision_id"),
        )
        object.__setattr__(
            self,
            "content_digest",
            _optional(self.content_digest, "content_digest"),
        )


@dataclass(frozen=True, slots=True)
class Evidence:
    """First-class evidence linking a claim to source, authority, and revision."""

    evidence_id: str
    source: SourceReference
    authority: SourceAuthority
    revision: KnowledgeRevision
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "evidence_id",
            _required(self.evidence_id, "evidence_id"),
        )
        if not isinstance(self.source, SourceReference):
            raise TypeError("source must be SourceReference")
        if not isinstance(self.authority, SourceAuthority):
            raise TypeError("authority must be SourceAuthority")
        if not isinstance(self.revision, KnowledgeRevision):
            raise TypeError("revision must be KnowledgeRevision")
        if (
            self.source.revision is not None
            and self.source.revision != self.revision.revision_id
        ):
            raise ValueError("source revision must match KnowledgeRevision.revision_id")
        if not isinstance(self.attributes, Mapping):
            raise TypeError("attributes must be a mapping")
        object.__setattr__(self, "attributes", _freeze(self.attributes))

    def semantic_state(self) -> tuple[Any, ...]:
        return (
            self.evidence_id,
            self.source,
            self.authority,
            self.revision,
            self.attributes,
        )


@dataclass(frozen=True, slots=True)
class Claim:
    """Material knowledge statement with explicit evidence and knowledge state."""

    claim_id: str
    statement: str
    knowledge_state: KnowledgeState
    evidence: tuple[Evidence, ...]
    derived_from: tuple[str, ...] = ()
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "claim_id",
            _required(self.claim_id, "claim_id"),
        )
        object.__setattr__(
            self,
            "statement",
            _required(self.statement, "statement"),
        )
        if not isinstance(self.knowledge_state, KnowledgeState):
            raise TypeError("knowledge_state must be KnowledgeState")

        evidence = tuple(self.evidence)
        if not evidence:
            raise ValueError("claim evidence must not be empty")
        if not all(isinstance(item, Evidence) for item in evidence):
            raise TypeError("evidence must contain Evidence")
        evidence_ids = [item.evidence_id for item in evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("claim evidence_id values must be unique")
        object.__setattr__(
            self,
            "evidence",
            tuple(sorted(evidence, key=lambda item: item.evidence_id)),
        )

        derived_from = tuple(
            _required(item, "derived_from") for item in self.derived_from
        )
        if self.claim_id in derived_from:
            raise ValueError("claim cannot derive from itself")
        if len(derived_from) != len(set(derived_from)):
            raise ValueError("derived_from values must be unique")
        object.__setattr__(
            self,
            "derived_from",
            tuple(sorted(derived_from)),
        )

        if not isinstance(self.attributes, Mapping):
            raise TypeError("attributes must be a mapping")
        object.__setattr__(self, "attributes", _freeze(self.attributes))

    @property
    def authorities(self) -> tuple[SourceAuthority, ...]:
        unique = {
            evidence.authority.authority_id: evidence.authority
            for evidence in self.evidence
        }
        return tuple(unique[key] for key in sorted(unique))

    def semantic_state(self) -> tuple[Any, ...]:
        return (
            self.claim_id,
            self.statement,
            self.knowledge_state.value,
            tuple(item.semantic_state() for item in self.evidence),
            self.derived_from,
            self.attributes,
        )
