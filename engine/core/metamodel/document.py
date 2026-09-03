from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

from .artifact import (
    ArtifactIdentity,
    ArtifactModel,
    ArtifactRelationship,
    KnowledgeState,
    SourceReference,
)

_RESERVED_METADATA = frozenset({"id", "title", "status", "knowledge_state"})


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
class ArtifactDocumentState:
    """Structured artifact state that can be deterministically rendered and parsed."""

    identity: ArtifactIdentity
    artifact_type: str
    title: str
    lifecycle_status: str
    knowledge_state: KnowledgeState = KnowledgeState.PROPOSED
    attributes: Mapping[str, Any] = field(default_factory=dict)
    relationships: tuple[ArtifactRelationship, ...] = ()
    sections: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.identity, ArtifactIdentity):
            raise TypeError("identity must be ArtifactIdentity")
        object.__setattr__(
            self, "artifact_type", _required(self.artifact_type, "artifact_type")
        )
        object.__setattr__(self, "title", _required(self.title, "title"))
        object.__setattr__(
            self,
            "lifecycle_status",
            _required(self.lifecycle_status, "lifecycle_status"),
        )
        if not isinstance(self.knowledge_state, KnowledgeState):
            raise TypeError("knowledge_state must be KnowledgeState")
        if not isinstance(self.attributes, Mapping):
            raise TypeError("attributes must be a mapping")

        attributes: dict[str, Any] = {}
        for raw_key, value in self.attributes.items():
            if not isinstance(raw_key, str):
                raise TypeError("attribute keys must be strings")
            key = _required(raw_key, "attribute key")
            if key in _RESERVED_METADATA:
                raise ValueError(f"attribute key is reserved: {key}")
            attributes[key] = _freeze(value)

        relationships = tuple(self.relationships)
        if not all(isinstance(item, ArtifactRelationship) for item in relationships):
            raise TypeError("relationships must contain ArtifactRelationship")
        relation_fields = {item.relation_type for item in relationships}
        collision = sorted(relation_fields.intersection(attributes))
        if collision:
            raise ValueError(
                "attributes must not collide with relationship fields: "
                + ", ".join(collision)
            )

        if not isinstance(self.sections, Mapping):
            raise TypeError("sections must be a mapping")
        sections: dict[str, str] = {}
        for raw_heading, raw_body in self.sections.items():
            if not isinstance(raw_heading, str) or not isinstance(raw_body, str):
                raise TypeError("sections must map string headings to string bodies")
            heading = _required(raw_heading, "section heading").lower()
            if heading in sections:
                raise ValueError(f"duplicate normalized section heading: {heading}")
            sections[heading] = raw_body.strip()

        object.__setattr__(self, "attributes", _freeze(attributes))
        object.__setattr__(self, "relationships", relationships)
        object.__setattr__(self, "sections", _freeze(sections))

    def to_artifact_model(self, source_path: str) -> ArtifactModel:
        provenance = SourceReference(origin=_required(source_path, "source_path"))
        relationships = tuple(
            ArtifactRelationship(
                relation_type=item.relation_type,
                target=item.target,
                knowledge_state=self.knowledge_state,
                provenance=provenance,
            )
            for item in self.relationships
        )
        return ArtifactModel(
            identity=self.identity,
            artifact_type=self.artifact_type,
            title=self.title,
            lifecycle_status=self.lifecycle_status,
            knowledge_state=self.knowledge_state,
            attributes=self.attributes,
            relationships=relationships,
            sections=self.sections,
            evidence=(provenance,),
        )

    def semantic_state(self, source_path: str | None = None) -> tuple[Any, ...]:
        if source_path is None:
            return (
                self.identity,
                self.artifact_type,
                self.title,
                self.lifecycle_status,
                self.knowledge_state.value,
                tuple(
                    (
                        item.relation_type,
                        item.target.canonical_key,
                        self.knowledge_state.value,
                    )
                    for item in self.relationships
                ),
                self.sections,
                self.attributes,
            )
        return self.to_artifact_model(source_path).semantic_state()
