from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping
from urllib.parse import quote


class KnowledgeState(str, Enum):
    DECLARED = "declared"
    OBSERVED = "observed"
    INFERRED = "inferred"
    PROPOSED = "proposed"


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
        return MappingProxyType(
            {
                key: _freeze(item)
                for key, item in value.items()
            }
        )
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze(item) for item in value)
    return value


@dataclass(frozen=True, slots=True)
class ArchitectureNamespace:
    organization_id: str
    repository_id: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "organization_id",
            _required(self.organization_id, "organization_id"),
        )
        object.__setattr__(
            self,
            "repository_id",
            _required(self.repository_id, "repository_id"),
        )

    @property
    def key(self) -> str:
        return f"{self.organization_id}/{self.repository_id}"


@dataclass(frozen=True, slots=True)
class ArtifactIdentity:
    artifact_id: str
    namespace: ArchitectureNamespace | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "artifact_id",
            _required(self.artifact_id, "artifact_id"),
        )

    @property
    def canonical_key(self) -> str:
        if self.namespace is None:
            return self.artifact_id
        return f"{self.namespace.key}/{self.artifact_id}"

    @property
    def canonical_uri(self) -> str:
        if self.namespace is None:
            return f"scnehaux:///architecture/{quote(self.artifact_id, safe='-._~')}"
        organization = quote(
            self.namespace.organization_id,
            safe="-._~",
        )
        repository = quote(
            self.namespace.repository_id,
            safe="-._~",
        )
        artifact = quote(self.artifact_id, safe="-._~")
        return f"scnehaux://{organization}/{repository}/{artifact}"


@dataclass(frozen=True, slots=True)
class SourceReference:
    origin: str
    revision: str | None = None
    line: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "origin",
            _required(self.origin, "origin"),
        )
        object.__setattr__(
            self,
            "revision",
            _optional(self.revision, "revision"),
        )
        if self.line is not None and self.line < 1:
            raise ValueError("line must be >= 1 when provided")


@dataclass(frozen=True, slots=True)
class ArtifactRelationship:
    relation_type: str
    target: ArtifactIdentity
    knowledge_state: KnowledgeState = KnowledgeState.DECLARED
    provenance: SourceReference | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "relation_type",
            _required(self.relation_type, "relation_type"),
        )
        if not isinstance(self.target, ArtifactIdentity):
            raise TypeError("target must be ArtifactIdentity")
        if not isinstance(self.knowledge_state, KnowledgeState):
            raise TypeError("knowledge_state must be KnowledgeState")


@dataclass(frozen=True, slots=True)
class ArtifactModel:
    identity: ArtifactIdentity
    artifact_type: str
    title: str
    lifecycle_status: str
    knowledge_state: KnowledgeState = KnowledgeState.DECLARED
    attributes: Mapping[str, Any] = field(default_factory=dict)
    relationships: tuple[ArtifactRelationship, ...] = ()
    sections: Mapping[str, Any] = field(default_factory=dict)
    evidence: tuple[SourceReference, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.identity, ArtifactIdentity):
            raise TypeError("identity must be ArtifactIdentity")

        object.__setattr__(
            self,
            "artifact_type",
            _required(self.artifact_type, "artifact_type"),
        )
        object.__setattr__(
            self,
            "title",
            _required(self.title, "title"),
        )
        object.__setattr__(
            self,
            "lifecycle_status",
            _required(self.lifecycle_status, "lifecycle_status"),
        )

        if not isinstance(self.knowledge_state, KnowledgeState):
            raise TypeError("knowledge_state must be KnowledgeState")

        if not isinstance(self.attributes, Mapping):
            raise TypeError("attributes must be a mapping")
        object.__setattr__(self, "attributes", _freeze(self.attributes))

        relationships = tuple(self.relationships)
        if not all(
            isinstance(item, ArtifactRelationship)
            for item in relationships
        ):
            raise TypeError(
                "relationships must contain ArtifactRelationship"
            )
        object.__setattr__(self, "relationships", relationships)

        evidence = tuple(self.evidence)
        if not all(
            isinstance(item, SourceReference)
            for item in evidence
        ):
            raise TypeError("evidence must contain SourceReference")
        object.__setattr__(self, "evidence", evidence)

        if not isinstance(self.sections, Mapping):
            raise TypeError("sections must be a mapping")
        object.__setattr__(self, "sections", _freeze(self.sections))

    @property
    def canonical_key(self) -> str:
        return self.identity.canonical_key

    def semantic_state(self) -> tuple[Any, ...]:
        relationships = tuple(
            (
                item.relation_type,
                item.target.canonical_key,
                item.knowledge_state.value,
                item.provenance,
            )
            for item in self.relationships
        )
        return (
            self.identity,
            self.artifact_type,
            self.title,
            self.lifecycle_status,
            self.knowledge_state.value,
            relationships,
            self.sections,
            self.evidence,
            self.attributes,
        )
