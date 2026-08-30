from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from types import MappingProxyType
from typing import Any, Mapping

from engine.core.metamodel import ArtifactModel


def _source_path(value: str) -> str:
    normalized = value.strip().replace("\\", "/")
    if not normalized:
        raise ValueError("source_path must not be blank")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("source_path must be repository-relative")
    return path.as_posix()


@dataclass(frozen=True, slots=True)
class RepositoryArtifact:
    """One canonical ArtifactModel plus its repository-relative source projection."""

    artifact: ArtifactModel
    source_path: str

    def __post_init__(self) -> None:
        if not isinstance(self.artifact, ArtifactModel):
            raise TypeError("artifact must be ArtifactModel")
        object.__setattr__(self, "source_path", _source_path(self.source_path))

    @property
    def path(self) -> str:
        return self.source_path

    @property
    def document_id(self) -> str:
        return self.artifact.identity.artifact_id

    @property
    def artifact_type(self) -> str:
        return self.artifact.artifact_type

    @property
    def metadata(self) -> Mapping[str, Any]:
        """Deterministic compatibility projection derived from ArtifactModel state."""
        projected = dict(self.artifact.attributes)
        projected["id"] = self.document_id
        projected["title"] = self.artifact.title
        projected["status"] = self.artifact.lifecycle_status

        relations: dict[str, list[str]] = {}
        for relationship in self.artifact.relationships:
            relations.setdefault(relationship.relation_type, []).append(
                relationship.target.artifact_id
            )
        for field, targets in relations.items():
            projected[field] = tuple(targets)

        return MappingProxyType(projected)


@dataclass(frozen=True, slots=True)
class RepositoryModel:
    """Pure, immutable repository authority over canonical ArtifactModel state."""

    artifacts: tuple[RepositoryArtifact, ...] = ()

    def __post_init__(self) -> None:
        artifacts = tuple(self.artifacts)
        if not all(isinstance(item, RepositoryArtifact) for item in artifacts):
            raise TypeError("artifacts must contain RepositoryArtifact")

        ordered = tuple(sorted(artifacts, key=lambda item: item.source_path))
        keys = [item.artifact.canonical_key for item in ordered]
        if len(keys) != len(set(keys)):
            duplicates = sorted({key for key in keys if keys.count(key) > 1})
            raise ValueError(
                "duplicate canonical artifact identity: " + ", ".join(duplicates)
            )

        paths = [item.source_path for item in ordered]
        if len(paths) != len(set(paths)):
            duplicates = sorted({path for path in paths if paths.count(path) > 1})
            raise ValueError("duplicate repository source path: " + ", ".join(duplicates))

        object.__setattr__(self, "artifacts", ordered)

    @property
    def is_empty(self) -> bool:
        return not self.artifacts

    @property
    def artifact_models(self) -> tuple[ArtifactModel, ...]:
        return tuple(item.artifact for item in self.artifacts)

    @property
    def by_key(self) -> Mapping[str, RepositoryArtifact]:
        return MappingProxyType(
            {item.artifact.canonical_key: item for item in self.artifacts}
        )

    @property
    def records_by_id(self) -> Mapping[str, tuple[RepositoryArtifact, ...]]:
        index: dict[str, list[RepositoryArtifact]] = {}
        for item in self.artifacts:
            index.setdefault(item.document_id, []).append(item)
        return MappingProxyType(
            {key: tuple(values) for key, values in sorted(index.items())}
        )

    def records_for_id(self, artifact_id: str) -> tuple[RepositoryArtifact, ...]:
        return self.records_by_id.get(artifact_id, ())

    def artifacts_of_type(self, artifact_type: str) -> tuple[RepositoryArtifact, ...]:
        normalized = artifact_type.strip().upper()
        return tuple(
            item for item in self.artifacts if item.artifact_type.upper() == normalized
        )

    def require(self, canonical_key: str) -> RepositoryArtifact:
        try:
            return self.by_key[canonical_key]
        except KeyError as exc:
            raise KeyError(f"unknown artifact identity: {canonical_key}") from exc

    def semantic_state(self) -> tuple[tuple[str, str, tuple[Any, ...]], ...]:
        return tuple(
            (
                item.source_path,
                item.artifact.canonical_key,
                item.artifact.semantic_state(),
            )
            for item in self.artifacts
        )
