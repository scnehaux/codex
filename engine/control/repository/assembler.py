from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from engine.control.fs.crawler import gather_markdown_paths
from engine.control.governance.relationships import (
    ALL_RELATION_FIELDS,
    artifact_type_from_id,
    normalize_relation_values,
    relationship_specs_for_source,
)
from engine.control.parsing.markdown_ast import (
    extract_section_contents,
    parse_frontmatter,
)
from engine.core.metamodel import (
    ArchitectureNamespace,
    ArtifactIdentity,
    ArtifactModel,
    ArtifactRelationship,
    KnowledgeState,
    SourceReference,
)
from engine.core.repository import RepositoryArtifact, RepositoryModel

GOVERNED_CORPUS_ROOTS = (
    "00-governance",
    "01-enterprise",
    "02-standards",
    "03-domain",
    "04-system",
    "05-decisions",
)

DERIVED_MARKDOWN_FILES = frozenset({"index.md", "readme.md", "traceability.md"})


class RepositoryAssemblyError(ValueError):
    """Base deterministic failure while constructing canonical repository state."""


class RepositoryIngestionError(RepositoryAssemblyError):
    """Source bytes or Markdown cannot be converted into canonical artifact state."""


class RepositoryIdentityError(RepositoryAssemblyError):
    """Artifact identity is absent, malformed, unknown, or ambiguous."""


# Transitional public alias for generator error handling; no model logic lives here.
RepositoryModelError = RepositoryAssemblyError


def _required_text(metadata: Mapping[str, Any], field: str, source_path: str) -> str:
    value = metadata.get(field)
    if not isinstance(value, str) or not value.strip():
        raise RepositoryIngestionError(
            f"Artifact '{source_path}' requires non-empty doc_meta.{field}."
        )
    return value.strip()


class RepositoryAssembler:
    """Control-layer authority for discovery/parsing -> pure RepositoryModel."""

    @staticmethod
    def artifact_from_metadata(
        *,
        metadata: Mapping[str, Any],
        source_path: str,
        content: str = "",
        namespace: ArchitectureNamespace | None = None,
    ) -> RepositoryArtifact:
        if not isinstance(metadata, Mapping):
            raise RepositoryIngestionError(
                f"Artifact '{source_path}' metadata must be a mapping."
            )

        document_id = _required_text(metadata, "id", source_path)
        artifact_type = artifact_type_from_id(document_id)
        if artifact_type is None:
            raise RepositoryIdentityError(
                f"Unknown governed artifact identity '{document_id}' at '{source_path}'."
            )

        title = _required_text(metadata, "title", source_path)
        lifecycle_status = _required_text(metadata, "status", source_path)
        raw_knowledge_state = metadata.get(
            "knowledge_state", KnowledgeState.DECLARED.value
        )
        try:
            knowledge_state = KnowledgeState(
                str(raw_knowledge_state).strip().lower()
            )
        except ValueError as exc:
            raise RepositoryIngestionError(
                f"Artifact '{source_path}' has invalid knowledge_state "
                f"{raw_knowledge_state!r}."
            ) from exc
        provenance = SourceReference(origin=source_path)

        relationships: list[ArtifactRelationship] = []
        relation_fields = set()
        for spec in relationship_specs_for_source(artifact_type):
            relation_fields.add(spec.metadata_field)
            for raw_target in normalize_relation_values(metadata.get(spec.metadata_field)):
                if not isinstance(raw_target, str) or not raw_target.strip():
                    raise RepositoryIngestionError(
                        f"Artifact '{source_path}' relationship '{spec.metadata_field}' "
                        "contains a non-string or blank target."
                    )
                relationships.append(
                    ArtifactRelationship(
                        relation_type=spec.metadata_field,
                        target=ArtifactIdentity(raw_target.strip(), namespace),
                        knowledge_state=knowledge_state,
                        provenance=provenance,
                    )
                )

        attributes = {
            key: value
            for key, value in metadata.items()
            if key not in {"id", "title", "status", "knowledge_state"}
            and key not in relation_fields
            and key not in ALL_RELATION_FIELDS
        }

        artifact = ArtifactModel(
            identity=ArtifactIdentity(document_id, namespace),
            artifact_type=artifact_type,
            title=title,
            lifecycle_status=lifecycle_status,
            knowledge_state=knowledge_state,
            attributes=attributes,
            relationships=tuple(relationships),
            sections=extract_section_contents(content) if content else {},
            evidence=(provenance,),
        )
        return RepositoryArtifact(artifact=artifact, source_path=source_path)

    @staticmethod
    def load(
        target_dirs: str | list[str],
        *,
        repo_root: str | Path,
        allowed_root_dirs: set[str] | None = None,
        ignored_files_lower: list[str] | None = None,
        ignored_patterns: list[str] | None = None,
        namespace: ArchitectureNamespace | None = None,
    ) -> RepositoryModel:
        root = Path(repo_root).resolve()
        try:
            discovered = gather_markdown_paths(
                target_dirs,
                repo_root=str(root),
                allowed_root_dirs=allowed_root_dirs,
                ignored_files_lower=ignored_files_lower,
                ignored_patterns=ignored_patterns,
            )
        except ValueError as exc:
            raise RepositoryAssemblyError(str(exc)) from exc

        normalized: list[tuple[str, Path]] = []
        for raw_path in discovered:
            absolute = Path(raw_path).resolve()
            try:
                relative = absolute.relative_to(root)
            except ValueError as exc:
                raise RepositoryAssemblyError(
                    f"Discovered artifact '{absolute}' escaped repository root '{root}'."
                ) from exc
            normalized.append((relative.as_posix(), absolute))
        normalized.sort(key=lambda item: item[0])

        artifacts: list[RepositoryArtifact] = []
        for relative_path, absolute_path in normalized:
            try:
                content = absolute_path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                raise RepositoryIngestionError(
                    f"Unable to read artifact '{relative_path}' as UTF-8: {exc}"
                ) from exc

            metadata, parse_error = parse_frontmatter(content)
            if parse_error or metadata is None:
                detail = parse_error or "unknown frontmatter parse failure"
                raise RepositoryIngestionError(
                    f"Malformed artifact '{relative_path}': {detail}"
                )

            artifacts.append(
                RepositoryAssembler.artifact_from_metadata(
                    metadata=metadata,
                    source_path=relative_path,
                    content=content,
                    namespace=namespace,
                )
            )

        try:
            return RepositoryModel(tuple(artifacts))
        except ValueError as exc:
            raise RepositoryIdentityError(str(exc)) from exc

    @staticmethod
    def load_governed_corpus(
        *,
        repo_root: str | Path,
        ignored_files_lower: list[str] | None = None,
        ignored_patterns: list[str] | None = None,
        namespace: ArchitectureNamespace | None = None,
    ) -> RepositoryModel:
        root = Path(repo_root).resolve()
        ignored = set(DERIVED_MARKDOWN_FILES)
        ignored.update(item.lower() for item in (ignored_files_lower or []))
        targets = [str(root / relative_root) for relative_root in GOVERNED_CORPUS_ROOTS]
        return RepositoryAssembler.load(
            targets,
            repo_root=root,
            allowed_root_dirs=set(GOVERNED_CORPUS_ROOTS),
            ignored_files_lower=sorted(ignored),
            ignored_patterns=ignored_patterns,
            namespace=namespace,
        )
