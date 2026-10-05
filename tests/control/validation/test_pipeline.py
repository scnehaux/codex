from __future__ import annotations

from functools import lru_cache

import pytest

from engine.control.framework.executable import executable_framework
from engine.control.fs.crawler import build_metadata_registry
from engine.control.validation import (
    ArtifactCandidate,
    ParsedArtifact,
    SourceDocument,
    ValidationFinding,
    ValidationReport,
    build_artifact_candidate,
    parse_source_document,
    promote_candidate,
    promote_candidates,
    validate_candidate,
)
from engine.core.repository import RepositoryModel
from tests.support.repository import REPOSITORY_ROOT


@lru_cache(maxsize=1)
def _registry():
    framework = executable_framework()
    policy = framework.governance.repository
    return build_metadata_registry(
        str(REPOSITORY_ROOT),
        str(REPOSITORY_ROOT),
        set(framework.repository_layout.values()),
        {item.lower() for item in policy.ignored_files},
        list(policy.ignored_patterns),
    )


def _real_candidate():
    path = REPOSITORY_ROOT / "governance/GDC-000-governance-policy.md"
    source = SourceDocument(
        "governance/GDC-000-governance-policy.md",
        path.read_text(encoding="utf-8"),
    )
    return build_artifact_candidate(parse_source_document(source))


def test_source_identity_is_deterministic_and_path_bound():
    first = SourceDocument("governance/example.md", "hello")
    second = SourceDocument("governance/example.md", "hello")
    other = SourceDocument("governance/other.md", "hello")
    assert first.source_id == second.source_id
    assert first.source_id != other.source_id
    with pytest.raises(ValueError, match="repository-relative"):
        SourceDocument("../escape.md", "hello")


def test_malformed_source_remains_diagnostic_but_cannot_promote():
    source = SourceDocument("governance/bad.md", "---\ndoc_meta: [\n---\n")
    parsed = parse_source_document(source)
    assert parsed.parse_error
    candidate = build_artifact_candidate(parsed)
    assert candidate.artifact is None
    report = validate_candidate(candidate)
    assert report.outcome.value == "fail"
    assert any(item.rule_id == "corrupt_frontmatter" for item in report.findings)
    with pytest.raises(ValueError, match="invalid candidate"):
        promote_candidate(candidate, report)


def test_unknown_artifact_identity_is_candidate_failure():
    source = SourceDocument(
        "governance/unknown.md",
        "---\ndoc_meta:\n  id: XYZ-001\n  title: Unknown\n  status: draft\n  created_date: 2026-01-01\n---\n# Unknown\n",
    )
    candidate = build_artifact_candidate(parse_source_document(source))
    assert candidate.artifact is None
    report = validate_candidate(candidate)
    assert report.outcome.value == "fail"
    assert any(item.rule_id == "unknown_document_type" for item in report.findings)


def test_real_governed_artifact_validates_before_promotion():
    ids, metadata, duplicates = _registry()
    assert not duplicates
    candidate = _real_candidate()
    report = validate_candidate(
        candidate,
        all_doc_ids=ids,
        all_doc_metadata=metadata,
    )
    assert report.outcome.value == "pass"
    assert report.findings == ()
    promoted = promote_candidate(candidate, report)
    assert promoted.document_id == "GDC-000"


def test_injected_framework_does_not_read_module_authority(monkeypatch):
    import engine.control.validators.registry as registry
    import engine.control.governance.lifecycle as lifecycle
    import engine.control.governance.relationships as relationships
    import engine.control.repository.assembler as assembler
    import engine.control.auditors.graph_auditor as graph
    import engine.control.validation.pipeline as pipeline
    import engine.control.validators.base as base
    import engine.control.framework.artifacts as artifacts

    runtime = executable_framework()
    ids, metadata, _ = _registry()
    source = _real_candidate().parsed

    def forbidden():
        raise AssertionError("module-level authority consulted")

    for module in (
        registry,
        lifecycle,
        relationships,
        assembler,
        graph,
        pipeline,
        base,
    ):
        monkeypatch.setattr(module, "executable_framework", forbidden)
    monkeypatch.setattr(artifacts, "artifact_runtime", forbidden)
    monkeypatch.setattr(registry, "VALIDATOR_REGISTRY", {})
    candidate = build_artifact_candidate(source, framework=runtime)
    report = validate_candidate(
        candidate, framework=runtime, all_doc_ids=ids, all_doc_metadata=metadata
    )
    assert report.outcome.value == "pass"
    assert promote_candidates((candidate,), (report,), framework=runtime).require(
        "GDC-000"
    )


def test_injected_lifecycle_controls_age_and_baseline_semantics(monkeypatch):
    from dataclasses import replace
    from engine.control.framework.artifacts import AgePolicy, BASELINE_BEARING

    monkeypatch.setenv("SCNEHAUX_EVALUATION_DATE", "2026-10-05")
    runtime = executable_framework()
    lifecycle = dict(runtime.lifecycle)
    lifecycle["GDC"] = dict(lifecycle["GDC"])
    lifecycle["GDC"]["draft"] = replace(
        lifecycle["GDC"]["draft"],
        semantic_class=BASELINE_BEARING,
        age_policy=AgePolicy("created_date", 1, "Injected age limit {limit} exceeded"),
    )
    injected = replace(
        runtime, artifacts=replace(runtime.artifacts, lifecycle=lifecycle)
    )
    ids, metadata, _ = _registry()
    report = validate_candidate(
        _real_candidate(),
        framework=injected,
        all_doc_ids=ids,
        all_doc_metadata=metadata,
    )
    rules = {item.rule_id for item in report.findings}
    assert "lifecycle_age_violation" in rules
    assert "approved_version_not_stable" in rules


def test_injected_relationship_cardinality_is_enforced():
    from dataclasses import replace

    runtime = executable_framework()
    by_source = dict(runtime.relationships.by_source)
    by_source["GDC"] = tuple(replace(spec, min_targets=2) for spec in by_source["GDC"])
    injected = replace(
        runtime, relationships=replace(runtime.relationships, by_source=by_source)
    )
    ids, metadata, _ = _registry()
    report = validate_candidate(
        _real_candidate(),
        framework=injected,
        all_doc_ids=ids,
        all_doc_metadata=metadata,
    )
    assert any(
        item.rule_id == "structural_integrity_violation"
        and "found 1 target" in item.message
        for item in report.findings
    )


def test_injected_validator_binding_cannot_fall_back():
    from dataclasses import replace
    from engine.control.framework.artifacts import ValidatorBinding
    from engine.control.framework.contracts import FrameworkContractError

    runtime = executable_framework()
    bindings = dict(runtime.validator_bindings)
    bindings["GDC"] = ValidatorBinding(
        "engine.control.validators.domains.gdc_validator", "MissingValidator"
    )
    injected = replace(
        runtime, artifacts=replace(runtime.artifacts, validator_bindings=bindings)
    )
    with pytest.raises(FrameworkContractError, match="validator-unresolvable:GDC"):
        validate_candidate(_real_candidate(), framework=injected)


def test_injected_framework_loads_schemas_from_its_resource_root(tmp_path):
    from dataclasses import replace
    import json
    import shutil
    from engine.control.linting import lint_file

    runtime = executable_framework()
    shutil.copytree(runtime.resource_root / "schemas", tmp_path / "schemas")
    (tmp_path / "schemas/gdc.schema.json").write_text(
        json.dumps({"type": "object", "required": ["Injected schema requirement"]}),
        encoding="utf-8",
    )
    injected = replace(runtime, resource_root=tmp_path)
    ids, metadata, _ = _registry()
    report = validate_candidate(
        _real_candidate(),
        framework=injected,
        all_doc_ids=ids,
        all_doc_metadata=metadata,
    )
    assert report.outcome.value == "fail"
    assert any(
        "Injected schema requirement" in item.message for item in report.findings
    )
    errors, _, blocking, _ = lint_file(
        str(REPOSITORY_ROOT / "governance/GDC-000-governance-policy.md"),
        injected.validation_rules,
        injected.governance.severity_levels,
        injected.blocking_severities,
        ids,
        metadata,
        "json",
        framework=injected,
    )
    assert blocking
    assert any("Injected schema requirement" in message for _, message in errors)


def test_candidate_in_wrong_declared_root_cannot_promote():
    candidate = build_artifact_candidate(
        parse_source_document(
            SourceDocument(
                "systems/GDC-000-governance-policy.md",
                _real_candidate().parsed.source.content,
            )
        )
    )
    ids, metadata, _ = _registry()
    report = validate_candidate(candidate, all_doc_ids=ids, all_doc_metadata=metadata)
    assert report.outcome.value == "fail"
    assert any(item.rule_id == "compliance_macro_directory" for item in report.findings)


def test_report_is_deterministic_for_same_candidate_and_context():
    ids, metadata, _ = _registry()
    candidate = _real_candidate()
    first = validate_candidate(candidate, all_doc_ids=ids, all_doc_metadata=metadata)
    second = validate_candidate(candidate, all_doc_ids=ids, all_doc_metadata=metadata)
    assert first.semantic_state() == second.semantic_state()


def test_promotion_rejects_report_bound_to_other_candidate():
    candidate = _real_candidate()
    foreign = ValidationReport(report_id="report", draft_id="other", findings=())
    with pytest.raises(ValueError, match="not bound"):
        promote_candidate(candidate, foreign)


def test_blocking_report_cannot_promote_even_when_artifact_exists():
    candidate = _real_candidate()
    report = ValidationReport(
        report_id="blocked",
        draft_id=candidate.candidate_id,
        findings=(
            ValidationFinding(
                finding_id="finding",
                rule_id="schema_validation_failed",
                message="blocked",
                blocking=True,
                artifact_key=candidate.artifact.artifact.canonical_key,
            ),
        ),
    )
    with pytest.raises(ValueError, match="invalid candidate"):
        promote_candidate(candidate, report)


def test_promote_candidates_constructs_repository_only_from_pass_reports():
    ids, metadata, _ = _registry()
    candidate = _real_candidate()
    report = validate_candidate(candidate, all_doc_ids=ids, all_doc_metadata=metadata)
    repository = promote_candidates((candidate,), (report,))
    assert isinstance(repository, RepositoryModel)
    assert repository.require("GDC-000").document_id == "GDC-000"
    with pytest.raises(ValueError, match="cardinality"):
        promote_candidates((candidate,), ())


def test_candidate_set_promotion_rejects_relationship_cycle():
    from engine.control.validation.pipeline import ArtifactCandidate, ParsedArtifact
    from engine.core.metamodel import (
        ArtifactIdentity,
        ArtifactModel,
        ArtifactRelationship,
    )
    from engine.core.repository import RepositoryArtifact

    def candidate(
        artifact_id: str,
        artifact_type: str,
        relation_type: str,
        target_id: str,
    ):
        source = SourceDocument(f"systems/{artifact_id}.md", "content")
        parsed = ParsedArtifact(
            source=source,
            metadata={
                "id": artifact_id,
                "title": artifact_id,
                "status": "draft",
                relation_type: [target_id],
            },
        )
        model = ArtifactModel(
            identity=ArtifactIdentity(artifact_id),
            artifact_type=artifact_type,
            title=artifact_id,
            lifecycle_status="draft",
            relationships=(
                ArtifactRelationship(
                    relation_type=relation_type,
                    target=ArtifactIdentity(target_id),
                ),
            ),
        )
        item = ArtifactCandidate(
            parsed=parsed,
            artifact=RepositoryArtifact(model, source.source_path),
        )
        report = ValidationReport(
            report_id=f"report-{artifact_id}",
            draft_id=item.candidate_id,
            findings=(),
        )
        return item, report

    sad, sad_report = candidate("SAD-001", "SAD", "governed_by", "ADR-001")
    adr, adr_report = candidate("ADR-001", "ADR", "governed_by", "SAD-001")

    with pytest.raises(ValueError, match="relationship DAG"):
        promote_candidates((sad, adr), (sad_report, adr_report))


def test_pipeline_value_objects_fail_closed_on_invalid_shapes():
    source = SourceDocument("governance/example.md", "content")
    with pytest.raises(ValueError, match="must not be blank"):
        SourceDocument(" ", "content")
    with pytest.raises(TypeError, match="content"):
        SourceDocument("governance/example.md", b"bytes")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="source"):
        ParsedArtifact(source="bad", metadata={})  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="metadata"):
        ParsedArtifact(source=source, metadata="bad")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="parse_error"):
        ParsedArtifact(source=source, metadata={}, parse_error=" ")
    frozen = ParsedArtifact(source=source, metadata={"tuple": ("a", "b")})
    assert frozen.metadata["tuple"] == ("a", "b")


def test_artifact_candidate_value_object_guards_types_and_blank_errors():
    parsed = ParsedArtifact(
        source=SourceDocument("governance/example.md", "content"),
        metadata={"id": "GDC-TEST"},
    )
    with pytest.raises(TypeError, match="parsed"):
        ArtifactCandidate(parsed="bad", artifact=None)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="artifact"):
        ArtifactCandidate(parsed=parsed, artifact="bad")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="assembly_error"):
        ArtifactCandidate(parsed=parsed, artifact=None, assembly_error=" ")


def test_validate_candidate_rejects_wrong_candidate_type():
    with pytest.raises(TypeError, match="candidate"):
        validate_candidate("bad")  # type: ignore[arg-type]


def test_validate_candidate_reports_missing_validator(monkeypatch):
    import engine.control.validation.pipeline as module

    ids, metadata, _ = _registry()
    candidate = _real_candidate()
    monkeypatch.setattr(module, "get_validator", lambda _doc_type, **_kwargs: None)
    report = module.validate_candidate(
        candidate,
        all_doc_ids=ids,
        all_doc_metadata=metadata,
    )
    assert any(item.rule_id == "missing_validator" for item in report.findings)


def test_validate_candidate_reports_schema_load_failure(monkeypatch):
    import engine.control.validation.pipeline as module

    ids, metadata, _ = _registry()
    candidate = _real_candidate()

    def fail(_path):
        raise FileNotFoundError("missing schema")

    monkeypatch.setattr(module, "load_json_schema_file", fail)
    report = module.validate_candidate(
        candidate,
        all_doc_ids=ids,
        all_doc_metadata=metadata,
    )
    assert any(item.rule_id == "schema_validation_failed" for item in report.findings)


def test_validate_candidate_surfaces_validator_age_and_relationship_findings(
    monkeypatch,
):
    import engine.control.validation.pipeline as module
    from types import SimpleNamespace

    ids, metadata, _ = _registry()
    candidate = _real_candidate()

    class FakeValidator:
        def __init__(self, *_args, **_kwargs):
            self.finding_records = [("stylistic_deviation", "WARNING", "style")]

        def validate(self):
            return []

    monkeypatch.setattr(
        module, "get_validator", lambda _doc_type, **_kwargs: FakeValidator
    )
    monkeypatch.setattr(module, "load_json_schema_file", lambda _path: {})
    monkeypatch.setattr(
        module,
        "validate_lifecycle_age",
        lambda *_args, **_kwargs: [("ERROR", "too old")],
    )
    monkeypatch.setattr(
        module,
        "relationship_contract_findings",
        lambda *_args, **_kwargs: (SimpleNamespace(message="relation bad"),),
    )
    report = module.validate_candidate(
        candidate,
        all_doc_ids=ids,
        all_doc_metadata=metadata,
    )
    rules = {item.rule_id for item in report.findings}
    assert "stylistic_deviation" in rules
    assert "lifecycle_age_violation" in rules
    assert "structural_integrity_violation" in rules
    assert report.outcome.value == "fail"


def test_promotion_type_and_empty_artifact_guards():
    candidate = _real_candidate()
    report = ValidationReport(
        report_id="pass",
        draft_id=candidate.candidate_id,
        findings=(),
    )
    with pytest.raises(TypeError, match="candidate"):
        promote_candidate("bad", report)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="report"):
        promote_candidate(candidate, "bad")  # type: ignore[arg-type]

    parsed = ParsedArtifact(
        source=SourceDocument("governance/empty.md", "content"),
        metadata=None,
    )
    empty = ArtifactCandidate(parsed=parsed, artifact=None, assembly_error="missing")
    empty_report = ValidationReport(
        report_id="empty-pass",
        draft_id=empty.candidate_id,
        findings=(),
    )
    with pytest.raises(ValueError, match="no promotable artifact"):
        promote_candidate(empty, empty_report)
