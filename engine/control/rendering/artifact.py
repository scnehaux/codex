from __future__ import annotations

from dataclasses import dataclass
import hashlib
from types import MappingProxyType
from typing import Any, Mapping

import yaml

from engine.control.governance.relationships import relationship_fields_for_source
from engine.control.parsing.markdown_ast import parse_frontmatter
from engine.control.repository import RepositoryAssembler
from engine.core.metamodel import ArtifactDocumentState, ArtifactModel


def _required(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    return normalized


def _thaw(value: Any) -> Any:
    if isinstance(value, MappingProxyType):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    if isinstance(value, frozenset):
        return sorted(_thaw(item) for item in value)
    return value


@dataclass(frozen=True, slots=True)
class RenderedArtifact:
    source_path: str
    markdown: str
    content_digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_path", _required(self.source_path, "source_path"))
        object.__setattr__(self, "markdown", _required(self.markdown, "markdown"))
        object.__setattr__(self, "content_digest", _required(self.content_digest, "content_digest"))


@dataclass(frozen=True, slots=True)
class RoundTripReport:
    source_path: str
    expected_digest: str
    parsed_digest: str
    equivalent: bool


def _semantic_digest(model: ArtifactModel) -> str:
    return hashlib.sha256(repr(model.semantic_state()).encode("utf-8")).hexdigest()


def render_artifact(state: ArtifactDocumentState, *, source_path: str) -> RenderedArtifact:
    if not isinstance(state, ArtifactDocumentState):
        raise TypeError("state must be ArtifactDocumentState")
    source_path = _required(source_path, "source_path")

    allowed_relationship_fields = relationship_fields_for_source(state.artifact_type)
    invalid = sorted(
        {item.relation_type for item in state.relationships} - set(allowed_relationship_fields)
    )
    if invalid:
        raise ValueError(
            "artifact contains relationship fields not allowed for type "
            f"{state.artifact_type}: " + ", ".join(invalid)
        )

    metadata: dict[str, Any] = {
        "id": state.identity.artifact_id,
        "title": state.title,
        "status": state.lifecycle_status,
        "knowledge_state": state.knowledge_state.value,
    }
    for key in sorted(state.attributes):
        metadata[key] = _thaw(state.attributes[key])

    grouped: dict[str, list[str]] = {}
    for relationship in sorted(
        state.relationships,
        key=lambda item: (item.relation_type, item.target.canonical_key),
    ):
        grouped.setdefault(relationship.relation_type, []).append(
            relationship.target.artifact_id
        )
    for field_name in sorted(grouped):
        metadata[field_name] = grouped[field_name]

    frontmatter = yaml.safe_dump(
        {"doc_meta": metadata},
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    ).strip()
    lines = ["---", frontmatter, "---", "", f"# {state.title}"]
    for heading in sorted(state.sections):
        lines.extend(("", f"## {heading}", "", state.sections[heading]))
    markdown = "\n".join(lines).rstrip() + "\n"
    digest = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    return RenderedArtifact(source_path, markdown, digest)


def verify_round_trip(state: ArtifactDocumentState, *, source_path: str) -> RoundTripReport:
    rendered = render_artifact(state, source_path=source_path)
    metadata, error = parse_frontmatter(rendered.markdown)
    if error or metadata is None:
        raise ValueError(f"rendered artifact cannot be parsed: {error or 'missing metadata'}")
    parsed = RepositoryAssembler.artifact_from_metadata(
        metadata=metadata,
        source_path=rendered.source_path,
        content=rendered.markdown,
        namespace=state.identity.namespace,
    ).artifact
    expected = state.to_artifact_model(rendered.source_path)
    expected_digest = _semantic_digest(expected)
    parsed_digest = _semantic_digest(parsed)
    return RoundTripReport(
        source_path=rendered.source_path,
        expected_digest=expected_digest,
        parsed_digest=parsed_digest,
        equivalent=expected.semantic_state() == parsed.semantic_state(),
    )
