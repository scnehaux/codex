from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from engine.control.framework.executable import (
    ExecutableFramework,
    executable_framework,
)
from engine.control.repository.git_ingestion import (
    GitCandidateBatch,
    GitRepositoryContext,
)
from engine.control.validation.pipeline import promote_candidates, validate_candidate
from engine.core.repository import RepositoryModel


def _canonical_digest(value: Any) -> str:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")
    return sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class ValidatedRepositorySnapshot:
    framework_id: str
    framework_version: str
    framework_semantic_sha256: str
    framework_contract_sha256: str
    framework_authority_sha256: str
    ontology_version: str
    framework_layers: tuple[tuple[str, str, str, str, str], ...]
    repository_context: GitRepositoryContext
    repository: RepositoryModel
    batch_id: str
    validation_report_ids: tuple[str, ...]
    snapshot_id: str

    def __post_init__(self) -> None:
        if not self.framework_id.strip():
            raise ValueError("framework_id must not be blank")
        if not self.framework_version.strip():
            raise ValueError("framework_version must not be blank")
        if len(self.framework_semantic_sha256) != 64:
            raise ValueError("framework_semantic_sha256 must be SHA-256")
        if len(self.framework_contract_sha256) != 64:
            raise ValueError("framework_contract_sha256 must be SHA-256")
        if len(self.framework_authority_sha256) != 64:
            raise ValueError("framework_authority_sha256 must be SHA-256")
        if not self.ontology_version.strip():
            raise ValueError("ontology_version must not be blank")
        layers = tuple(self.framework_layers)
        if not layers:
            raise ValueError("framework_layers must be non-empty")
        if any(
            len(layer) != 5
            or any(not isinstance(value, str) or not value for value in layer[:4])
            or len(layer[4]) != 64
            for layer in layers
        ):
            raise ValueError("framework_layers contains invalid authority identity")
        if len(layers) != len(set(layers)):
            raise ValueError("framework_layers must be unique")
        object.__setattr__(self, "framework_layers", layers)
        if not isinstance(self.repository_context, GitRepositoryContext):
            raise TypeError("repository_context must be GitRepositoryContext")
        if not isinstance(self.repository, RepositoryModel):
            raise TypeError("repository must be RepositoryModel")
        if len(self.batch_id) != 64:
            raise ValueError("batch_id must be SHA-256")
        reports = tuple(self.validation_report_ids)
        if not reports or any(not value.strip() for value in reports):
            raise ValueError("validation_report_ids must be non-empty")
        if len(reports) != len(set(reports)):
            raise ValueError("validation_report_ids must be unique")
        object.__setattr__(self, "validation_report_ids", tuple(sorted(reports)))
        if len(self.snapshot_id) != 64:
            raise ValueError("snapshot_id must be SHA-256")

    @property
    def revision(self) -> str:
        return self.repository_context.revision

    def semantic_state(self) -> tuple[Any, ...]:
        return (
            self.framework_id,
            self.framework_version,
            self.framework_semantic_sha256,
            self.framework_contract_sha256,
            self.framework_authority_sha256,
            self.ontology_version,
            self.framework_layers,
            self.repository_context.semantic_state(),
            self.batch_id,
            self.validation_report_ids,
            self.repository.semantic_state(),
        )


def build_validated_repository_snapshot(
    batch: GitCandidateBatch,
    *,
    framework: ExecutableFramework | None = None,
    repo_root: str | Path | None = None,
) -> ValidatedRepositorySnapshot:
    if not isinstance(batch, GitCandidateBatch):
        raise TypeError("batch must be GitCandidateBatch")

    runtime = framework or executable_framework()
    if not isinstance(runtime, ExecutableFramework):
        raise TypeError("framework must be ExecutableFramework")

    candidates = batch.candidates
    doc_ids = {
        candidate.artifact.document_id
        for candidate in candidates
        if candidate.artifact is not None
    }
    metadata = {
        candidate.artifact.document_id: dict(candidate.parsed.metadata or {})
        for candidate in candidates
        if candidate.artifact is not None
    }
    reports = tuple(
        validate_candidate(
            candidate,
            all_doc_ids=doc_ids,
            all_doc_metadata=metadata,
            framework=runtime,
            repo_root=repo_root,
        )
        for candidate in candidates
    )
    if any(report.outcome.value != "pass" for report in reports):
        rejected = "; ".join(
            f"{candidate.parsed.source.source_path}: {finding.rule_id}: {finding.message}"
            for candidate, report in zip(candidates, reports, strict=True)
            for finding in report.findings
            if finding.blocking
        )
        raise ValueError(
            "validated snapshot requires all candidates to pass validation: " + rejected
        )
    if any(candidate.artifact is None for candidate in candidates):
        raise ValueError("validated snapshot requires promotable artifacts")

    repository = promote_candidates(candidates, reports, framework=runtime)
    keys = set(repository.by_key)
    unresolved = sorted(
        (
            item.artifact.canonical_key,
            relation.relation_type,
            relation.target.canonical_key,
        )
        for item in repository.artifacts
        for relation in item.artifact.relationships
        if relation.target.canonical_key not in keys
    )
    if unresolved:
        source, relation_type, target = unresolved[0]
        raise ValueError(
            "validated snapshot contains unresolved relationship: "
            f"{source} {relation_type} {target}"
        )

    report_ids = tuple(sorted(report.report_id for report in reports))
    snapshot_id = _canonical_digest(
        {
            "framework": {
                "id": runtime.identity.framework_id,
                "version": runtime.identity.framework_version,
                "semantic_sha256": runtime.semantic_sha256,
                "contract_sha256": runtime.contract_sha256,
                "authority_sha256": runtime.authority_sha256,
                "ontology_version": runtime.relationships.ontology_version,
                "layers": [
                    [
                        layer.layer_kind,
                        layer.layer_id,
                        layer.layer_version,
                        layer.path,
                        layer.sha256,
                    ]
                    for layer in runtime.provenance
                ],
            },
            "repository_context_id": batch.context.context_id,
            "batch_id": batch.batch_id,
            "validation_report_ids": report_ids,
        }
    )
    return ValidatedRepositorySnapshot(
        framework_id=runtime.identity.framework_id,
        framework_version=runtime.identity.framework_version,
        framework_semantic_sha256=runtime.semantic_sha256,
        framework_contract_sha256=runtime.contract_sha256,
        framework_authority_sha256=runtime.authority_sha256,
        ontology_version=runtime.relationships.ontology_version,
        framework_layers=tuple(
            (
                layer.layer_kind,
                layer.layer_id,
                layer.layer_version,
                layer.path,
                layer.sha256,
            )
            for layer in runtime.provenance
        ),
        repository_context=batch.context,
        repository=repository,
        batch_id=batch.batch_id,
        validation_report_ids=report_ids,
        snapshot_id=snapshot_id,
    )
