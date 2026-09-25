from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from engine.control.framework.executable import (
    ExecutableFramework,
    executable_framework,
)
from engine.control.fs.source_path import repository_source_path

if TYPE_CHECKING:
    from engine.control.validation.pipeline import ArtifactCandidate, SourceDocument

from engine.core.metamodel import ArchitectureNamespace, SourceReference


_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")


class GitIngestionError(ValueError):
    """Fail-closed Git-backed ingestion failure."""


def _required(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    return normalized


def _canonical_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class GitRepositoryContext:
    repository_id: str
    namespace: ArchitectureNamespace
    revision: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "repository_id", _required(self.repository_id, "repository_id")
        )
        if not isinstance(self.namespace, ArchitectureNamespace):
            raise TypeError("namespace must be ArchitectureNamespace")
        revision = _required(self.revision, "revision").lower()
        if _COMMIT.fullmatch(revision) is None:
            raise ValueError(
                "revision must be an immutable 40-character Git commit SHA"
            )
        object.__setattr__(self, "revision", revision)

    @property
    def context_id(self) -> str:
        return _canonical_digest(
            {
                "repository_id": self.repository_id,
                "namespace": [
                    self.namespace.organization_id,
                    self.namespace.repository_id,
                ],
                "revision": self.revision,
            }
        )

    def semantic_state(self) -> tuple[str, tuple[str, str], str]:
        return (
            self.repository_id,
            (self.namespace.organization_id, self.namespace.repository_id),
            self.revision,
        )


@dataclass(frozen=True, slots=True)
class GitSourceProvenance:
    context: GitRepositoryContext
    source_path: str
    content_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.context, GitRepositoryContext):
            raise TypeError("context must be GitRepositoryContext")
        object.__setattr__(
            self, "source_path", repository_source_path(self.source_path)
        )
        digest = _required(self.content_sha256, "content_sha256").lower()
        if _DIGEST.fullmatch(digest) is None:
            raise ValueError("content_sha256 must be a 64-character lowercase SHA-256")
        object.__setattr__(self, "content_sha256", digest)

    @property
    def origin(self) -> str:
        repository = quote(self.context.repository_id, safe="")
        path = quote(self.source_path, safe="/")
        return f"git+repo://{repository}/{path}"

    @property
    def source_reference(self) -> SourceReference:
        return SourceReference(
            origin=self.origin,
            revision=self.context.revision,
            content_digest=self.content_sha256,
        )

    @property
    def provenance_id(self) -> str:
        return _canonical_digest(
            {
                "repository_id": self.context.repository_id,
                "namespace": [
                    self.context.namespace.organization_id,
                    self.context.namespace.repository_id,
                ],
                "revision": self.context.revision,
                "source_path": self.source_path,
                "content_sha256": self.content_sha256,
            }
        )

    def verify_content(self, content: str | bytes) -> None:
        raw = content.encode("utf-8") if isinstance(content, str) else content
        if not isinstance(raw, bytes):
            raise TypeError("content must be str or bytes")
        if sha256(raw).hexdigest() != self.content_sha256:
            raise ValueError("source content digest does not match recorded provenance")

    def to_record(self) -> dict[str, str]:
        return {
            "repository_id": self.context.repository_id,
            "organization_id": self.context.namespace.organization_id,
            "namespace_repository_id": self.context.namespace.repository_id,
            "revision": self.context.revision,
            "source_path": self.source_path,
            "content_sha256": self.content_sha256,
        }

    @classmethod
    def from_record(cls, record: dict[str, str]) -> "GitSourceProvenance":
        if set(record) != {
            "repository_id",
            "organization_id",
            "namespace_repository_id",
            "revision",
            "source_path",
            "content_sha256",
        }:
            raise ValueError("git provenance record fields are incomplete or ambiguous")
        context = GitRepositoryContext(
            repository_id=record["repository_id"],
            namespace=ArchitectureNamespace(
                record["organization_id"], record["namespace_repository_id"]
            ),
            revision=record["revision"],
        )
        return cls(context, record["source_path"], record["content_sha256"])


@dataclass(frozen=True, slots=True)
class GitIngestedCandidate:
    provenance: GitSourceProvenance
    candidate: ArtifactCandidate

    def __post_init__(self) -> None:
        from engine.control.validation.pipeline import ArtifactCandidate

        if not isinstance(self.provenance, GitSourceProvenance):
            raise TypeError("provenance must be GitSourceProvenance")
        if not isinstance(self.candidate, ArtifactCandidate):
            raise TypeError("candidate must be ArtifactCandidate")
        source = self.candidate.parsed.source
        self.provenance.verify_content(source.content)
        if source.source_namespace != self.provenance.context.namespace:
            raise ValueError("candidate source namespace does not match Git provenance")
        if source.source_path != self.provenance.source_path:
            raise ValueError("candidate source path does not match Git provenance")
        if source.source_reference != self.provenance.source_reference:
            raise ValueError("candidate SourceReference does not match Git provenance")
        if self.candidate.artifact is not None:
            record = self.candidate.artifact
            if record.source_path != self.provenance.source_path:
                raise ValueError(
                    "candidate artifact path does not match Git provenance"
                )
            if record.artifact.evidence != (self.provenance.source_reference,):
                raise ValueError("candidate evidence does not match Git provenance")
            if any(
                relation.provenance != self.provenance.source_reference
                for relation in record.artifact.relationships
            ):
                raise ValueError(
                    "candidate relationship provenance does not match source"
                )
            namespace = self.candidate.artifact.artifact.identity.namespace
            if namespace != self.provenance.context.namespace:
                raise ValueError("candidate namespace does not match Git provenance")

    @property
    def provenance_id(self) -> str:
        return self.provenance.provenance_id


@dataclass(frozen=True, slots=True)
class GitCandidateBatch:
    context: GitRepositoryContext
    entries: tuple[GitIngestedCandidate, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.context, GitRepositoryContext):
            raise TypeError("context must be GitRepositoryContext")
        entries = tuple(self.entries)
        if not all(isinstance(item, GitIngestedCandidate) for item in entries):
            raise TypeError("entries must contain GitIngestedCandidate")
        if any(item.provenance.context != self.context for item in entries):
            raise ValueError("batch entries must share one GitRepositoryContext")
        ordered = tuple(sorted(entries, key=lambda item: item.provenance.source_path))
        paths = [item.provenance.source_path for item in ordered]
        if len(paths) != len(set(paths)):
            raise ValueError("Git ingestion source paths must be unique")
        provenance_ids = [item.provenance_id for item in ordered]
        if len(provenance_ids) != len(set(provenance_ids)):
            raise ValueError("Git ingestion provenance identities must be unique")
        object.__setattr__(self, "entries", ordered)

    @property
    def candidates(self) -> tuple[ArtifactCandidate, ...]:
        return tuple(item.candidate for item in self.entries)

    @property
    def batch_id(self) -> str:
        return _canonical_digest(
            {
                "context_id": self.context.context_id,
                "provenance_ids": [item.provenance_id for item in self.entries],
            }
        )


class GitRepositoryReader:
    def __init__(self, repo_root: str | Path, context: GitRepositoryContext):
        self.repo_root = Path(repo_root).resolve()
        if not isinstance(context, GitRepositoryContext):
            raise TypeError("context must be GitRepositoryContext")
        self.context = context
        top = self._git_text("rev-parse", "--show-toplevel")
        if Path(top).resolve() != self.repo_root:
            raise GitIngestionError("repo_root must be the Git repository top-level")
        resolved = self._git_text(
            "rev-parse", "--verify", f"{self.context.revision}^{{commit}}"
        ).lower()
        if resolved != self.context.revision:
            raise GitIngestionError(
                "revision does not resolve to the exact requested commit"
            )

    def _git_bytes(self, *args: str) -> bytes:
        try:
            return subprocess.check_output(
                [
                    "git",
                    "--no-replace-objects",
                    "--literal-pathspecs",
                    "-C",
                    str(self.repo_root),
                    *args,
                ],
                env={
                    key: value
                    for key, value in os.environ.items()
                    if not key.upper().startswith("GIT_")
                },
                stderr=subprocess.STDOUT,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise GitIngestionError("Git command failed: " + " ".join(args)) from exc

    def _git_text(self, *args: str) -> str:
        try:
            return self._git_bytes(*args).decode("utf-8").strip()
        except UnicodeError as exc:
            raise GitIngestionError("Git command output is not UTF-8") from exc

    def _tree_entry(self, source_path: str) -> tuple[str, str]:
        raw = self._git_bytes("ls-tree", "-z", self.context.revision, "--", source_path)
        records = [item for item in raw.split(b"\0") if item]
        if len(records) != 1:
            raise GitIngestionError(
                f"source path is absent or ambiguous at revision: {source_path}"
            )
        try:
            metadata, actual_path = records[0].split(b"\t", 1)
            mode, object_type, _object_id = metadata.decode("ascii").split(" ", 2)
            decoded_path = actual_path.decode("utf-8")
        except (ValueError, UnicodeError) as exc:
            raise GitIngestionError("invalid git ls-tree record") from exc
        if decoded_path != source_path:
            raise GitIngestionError(
                "Git tree path does not match requested source path"
            )
        if object_type != "blob" or mode not in {"100644", "100755"}:
            raise GitIngestionError("canonical Git source must be a regular file blob")
        return mode, object_type

    def read_source(
        self, source_path: str
    ) -> tuple[SourceDocument, GitSourceProvenance]:
        from engine.control.validation.pipeline import SourceDocument

        path = repository_source_path(source_path)
        self._tree_entry(path)
        raw = self._git_bytes("cat-file", "blob", f"{self.context.revision}:{path}")
        try:
            content = raw.decode("utf-8")
        except UnicodeError as exc:
            raise GitIngestionError(
                f"canonical Git source is not valid UTF-8: {path}"
            ) from exc
        provenance = GitSourceProvenance(
            context=self.context,
            source_path=path,
            content_sha256=sha256(raw).hexdigest(),
        )
        provenance.verify_content(raw)
        source = SourceDocument(
            source_path=path,
            content=content,
            source_reference=provenance.source_reference,
            source_namespace=self.context.namespace,
        )
        return source, provenance

    def list_governed_markdown_paths(
        self, framework: ExecutableFramework | None = None
    ) -> tuple[str, ...]:
        runtime = framework or executable_framework()
        roots = tuple(dict.fromkeys(runtime.repository_layout.values()))
        raw = self._git_bytes(
            "ls-tree",
            "-r",
            "-z",
            "--name-only",
            self.context.revision,
            "--",
            *roots,
        )
        ignored_files = {
            item.lower() for item in runtime.governance.repository.ignored_files
        }
        ignored_patterns = tuple(
            re.compile(pattern)
            for pattern in runtime.governance.repository.ignored_patterns
        )
        paths: list[str] = []
        for item in raw.split(b"\0"):
            if not item:
                continue
            try:
                decoded_path = item.decode("utf-8")
                path = repository_source_path(decoded_path)
                if path != decoded_path:
                    raise ValueError("noncanonical Git tree source path")
            except (UnicodeError, ValueError) as exc:
                raise GitIngestionError("invalid Git tree source path") from exc
            if not path.lower().endswith(".md"):
                continue
            if PurePosixPath(path).name.lower() in ignored_files:
                continue
            if any(pattern.search("/" + path) for pattern in ignored_patterns):
                continue
            paths.append(path)
        return tuple(sorted(dict.fromkeys(paths)))

    def ingest_governed_candidates(
        self, framework: ExecutableFramework | None = None
    ) -> GitCandidateBatch:
        from engine.control.validation.pipeline import (
            build_artifact_candidate,
            parse_source_document,
        )

        runtime = framework or executable_framework()
        entries: list[GitIngestedCandidate] = []
        for source_path in self.list_governed_markdown_paths(runtime):
            source, provenance = self.read_source(source_path)
            candidate = build_artifact_candidate(
                parse_source_document(source),
                namespace=self.context.namespace,
            )
            entries.append(GitIngestedCandidate(provenance, candidate))
        return GitCandidateBatch(self.context, tuple(entries))


def ingest_git_governed_corpus(
    *,
    repo_root: str | Path,
    context: GitRepositoryContext,
    framework: ExecutableFramework | None = None,
) -> GitCandidateBatch:
    return GitRepositoryReader(repo_root, context).ingest_governed_candidates(framework)
