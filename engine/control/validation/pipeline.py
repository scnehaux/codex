from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from types import MappingProxyType
from typing import Any, Mapping

from engine.control.config.loader import load_json_schema_file
from engine.control.config.severity import SeverityRule
from engine.control.framework.executable import (
    ExecutableFramework,
    executable_framework,
)
from engine.control.fs.source_path import repository_source_path
from engine.control.governance.relationships import relationship_contract_findings
from engine.control.parsing.markdown_ast import parse_frontmatter
from engine.control.repository.assembler import (
    RepositoryAssembler,
    RepositoryAssemblyError,
)
from engine.control.validators.metadata_rules import validate_lifecycle_age
from engine.control.validators.registry import get_validator
from engine.core.metamodel import ArchitectureNamespace, SourceReference
from engine.core.repository import RepositoryArtifact, RepositoryModel

from .contracts import ValidationFinding, ValidationReport


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class SourceDocument:
    source_path: str
    content: str
    source_reference: SourceReference | None = None
    source_namespace: ArchitectureNamespace | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "source_path", repository_source_path(self.source_path)
        )
        if self.source_namespace is not None and not isinstance(
            self.source_namespace, ArchitectureNamespace
        ):
            raise TypeError("source_namespace must be ArchitectureNamespace or None")
        if not isinstance(self.content, str):
            raise TypeError("content must be a string")
        if self.source_reference is not None and not isinstance(
            self.source_reference, SourceReference
        ):
            raise TypeError("source_reference must be SourceReference or None")
        if (
            self.source_reference is not None
            and self.source_reference.content_digest is not None
            and self.source_reference.content_digest != self.content_sha256
        ):
            raise ValueError("source_reference content_digest does not match content")

    @property
    def content_sha256(self) -> str:
        return sha256(self.content.encode("utf-8")).hexdigest()

    @property
    def source_id(self) -> str:
        reference = self.source_reference
        if reference is None and self.source_namespace is None:
            payload = f"{self.source_path}\0{self.content_sha256}".encode("utf-8")
        else:
            namespace = self.source_namespace
            payload = json.dumps(
                {
                    "source_path": self.source_path,
                    "content_sha256": self.content_sha256,
                    "reference": (
                        [
                            reference.origin,
                            reference.revision,
                            reference.line,
                            reference.content_digest,
                        ]
                        if reference
                        else None
                    ),
                    "namespace": (
                        [namespace.organization_id, namespace.repository_id]
                        if namespace
                        else None
                    ),
                },
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode("ascii")
        return sha256(payload).hexdigest()


@dataclass(frozen=True, slots=True)
class ParsedArtifact:
    source: SourceDocument
    metadata: Mapping[str, Any] | None
    parse_error: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source, SourceDocument):
            raise TypeError("source must be SourceDocument")
        if self.metadata is not None:
            if not isinstance(self.metadata, Mapping):
                raise TypeError("metadata must be a mapping")
            object.__setattr__(self, "metadata", _freeze(self.metadata))
        if self.parse_error is not None and not self.parse_error.strip():
            raise ValueError("parse_error must not be blank")


@dataclass(frozen=True, slots=True)
class ArtifactCandidate:
    parsed: ParsedArtifact
    artifact: RepositoryArtifact | None
    assembly_error: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.parsed, ParsedArtifact):
            raise TypeError("parsed must be ParsedArtifact")
        if self.artifact is not None and not isinstance(
            self.artifact, RepositoryArtifact
        ):
            raise TypeError("artifact must be RepositoryArtifact")
        if self.assembly_error is not None and not self.assembly_error.strip():
            raise ValueError("assembly_error must not be blank")

    @property
    def candidate_id(self) -> str:
        return self.parsed.source.source_id


def parse_source_document(source: SourceDocument) -> ParsedArtifact:
    metadata, error = parse_frontmatter(source.content)
    return ParsedArtifact(source=source, metadata=metadata, parse_error=error)


def build_artifact_candidate(
    parsed: ParsedArtifact,
    *,
    namespace: ArchitectureNamespace | None = None,
) -> ArtifactCandidate:
    bound_namespace = parsed.source.source_namespace
    if bound_namespace is not None:
        if namespace is not None and namespace != bound_namespace:
            raise ValueError("candidate namespace does not match source namespace")
        namespace = bound_namespace
    if parsed.parse_error or parsed.metadata is None:
        return ArtifactCandidate(
            parsed=parsed,
            artifact=None,
            assembly_error=parsed.parse_error or "missing frontmatter metadata",
        )
    try:
        artifact = RepositoryAssembler.artifact_from_metadata(
            metadata=parsed.metadata,
            source_path=parsed.source.source_path,
            content=parsed.source.content,
            namespace=namespace,
            source_reference=parsed.source.source_reference,
        )
    except RepositoryAssemblyError as exc:
        return ArtifactCandidate(parsed=parsed, artifact=None, assembly_error=str(exc))
    return ArtifactCandidate(parsed=parsed, artifact=artifact)


def _finding(
    candidate: ArtifactCandidate,
    *,
    ordinal: int,
    rule_id: str,
    message: str,
    severity: str,
    framework: ExecutableFramework,
) -> ValidationFinding:
    raw = (
        f"{candidate.candidate_id}\0{ordinal}\0{rule_id}\0{severity}\0{message}"
    ).encode("utf-8")
    return ValidationFinding(
        finding_id=sha256(raw).hexdigest(),
        rule_id=rule_id,
        message=message,
        blocking=severity in framework.blocking_severities,
        artifact_key=(
            candidate.artifact.artifact.canonical_key
            if candidate.artifact is not None
            else None
        ),
    )


def _report_id(
    candidate: ArtifactCandidate, findings: tuple[ValidationFinding, ...]
) -> str:
    payload = {
        "candidate_id": candidate.candidate_id,
        "finding_ids": [item.finding_id for item in findings],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii")
    return sha256(raw).hexdigest()


def validate_candidate(
    candidate: ArtifactCandidate,
    *,
    all_doc_ids: set[str] | None = None,
    all_doc_metadata: Mapping[str, Mapping[str, Any]] | None = None,
    framework: ExecutableFramework | None = None,
) -> ValidationReport:
    if not isinstance(candidate, ArtifactCandidate):
        raise TypeError("candidate must be ArtifactCandidate")
    runtime = framework or executable_framework()
    ids = set(all_doc_ids or ())
    metadata_registry = dict(all_doc_metadata or {})
    findings: list[ValidationFinding] = []

    def add(rule_id: str, message: str, severity: str) -> None:
        findings.append(
            _finding(
                candidate,
                ordinal=len(findings),
                rule_id=rule_id,
                message=message,
                severity=severity,
                framework=runtime,
            )
        )

    if candidate.parsed.parse_error:
        add(
            SeverityRule.CORRUPT_FRONTMATTER.value,
            candidate.parsed.parse_error,
            runtime.governance.severity_levels[SeverityRule.CORRUPT_FRONTMATTER.value],
        )
    if candidate.artifact is None:
        if not candidate.parsed.parse_error:
            rule = (
                SeverityRule.UNKNOWN_DOCUMENT_TYPE
                if isinstance(candidate.assembly_error, str)
                and "Unknown governed artifact identity" in candidate.assembly_error
                else SeverityRule.MISSING_METADATA
            )
            add(
                rule.value,
                candidate.assembly_error or "candidate assembly failed",
                runtime.governance.severity_levels[rule.value],
            )
        frozen = tuple(findings)
        return ValidationReport(
            report_id=_report_id(candidate, frozen),
            draft_id=candidate.candidate_id,
            findings=frozen,
        )

    record = candidate.artifact
    artifact = record.artifact
    doc_type = artifact.artifact_type
    doc_meta = _thaw(candidate.parsed.metadata or {})
    doc_id = artifact.identity.artifact_id
    ids.add(doc_id)
    metadata_registry.setdefault(doc_id, doc_meta)

    validator_cls = get_validator(doc_type)
    if validator_cls is None:
        add(
            SeverityRule.MISSING_VALIDATOR.value,
            f"No validator implemented for doc type '{doc_type}'.",
            runtime.governance.severity_levels[SeverityRule.MISSING_VALIDATOR.value],
        )
    else:
        schema_path = runtime.schema_bindings[doc_type]
        try:
            domain_schema = load_json_schema_file(schema_path)
        except (FileNotFoundError, ValueError) as exc:
            add(
                SeverityRule.SCHEMA_VALIDATION_FAILED.value,
                str(exc),
                runtime.governance.severity_levels[
                    SeverityRule.SCHEMA_VALIDATION_FAILED.value
                ],
            )
        else:
            validator = validator_cls(
                record.source_path,
                candidate.parsed.source.content,
                doc_meta,
                runtime.validation_rules,
                domain_schema,
                ids,
                metadata_registry,
                runtime.governance.severity_levels,
                runtime.blocking_severities,
            )
            validator.validate()
            for rule_id, severity, message in validator.finding_records:
                add(rule_id, message, severity)

    age_errors = validate_lifecycle_age(
        doc_meta,
        doc_type,
        artifact.lifecycle_status.lower(),
        runtime.governance.severity_levels[SeverityRule.LIFECYCLE_AGE_VIOLATION.value],
    )
    for severity, message in age_errors:
        add(SeverityRule.LIFECYCLE_AGE_VIOLATION.value, message, severity)

    for relation_finding in relationship_contract_findings(
        doc_id, doc_meta, metadata_registry
    ):
        add(
            SeverityRule.STRUCTURAL_INTEGRITY_VIOLATION.value,
            relation_finding.message,
            runtime.governance.severity_levels[
                SeverityRule.STRUCTURAL_INTEGRITY_VIOLATION.value
            ],
        )

    frozen = tuple(findings)
    return ValidationReport(
        report_id=_report_id(candidate, frozen),
        draft_id=candidate.candidate_id,
        findings=frozen,
    )


def promote_candidate(
    candidate: ArtifactCandidate,
    report: ValidationReport,
) -> RepositoryArtifact:
    if not isinstance(candidate, ArtifactCandidate):
        raise TypeError("candidate must be ArtifactCandidate")
    if not isinstance(report, ValidationReport):
        raise TypeError("report must be ValidationReport")
    if report.draft_id != candidate.candidate_id:
        raise ValueError("validation report is not bound to candidate")
    if report.outcome.value != "pass":
        raise ValueError("invalid candidate cannot be promoted")
    if candidate.artifact is None:
        raise ValueError("candidate has no promotable artifact")
    return candidate.artifact


def promote_candidates(
    candidates: tuple[ArtifactCandidate, ...],
    reports: tuple[ValidationReport, ...],
) -> RepositoryModel:
    if len(candidates) != len(reports):
        raise ValueError("candidate/report cardinality mismatch")
    promoted = tuple(
        promote_candidate(candidate, report)
        for candidate, report in zip(candidates, reports, strict=True)
    )
    repository = RepositoryModel(promoted)

    from engine.control.auditors.graph_auditor import audit_traceability_graph

    metadata = {item.document_id: dict(item.metadata) for item in repository.artifacts}
    graph_findings = audit_traceability_graph(metadata)
    if graph_findings:
        raise ValueError(
            "promoted candidate set violates relationship DAG: "
            + "; ".join(message for _category, message in graph_findings)
        )
    return repository
