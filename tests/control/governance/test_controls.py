from tests.support.repository import REPOSITORY_ROOT
from pathlib import Path

import pytest

from engine.control.governance.controls import (
    ControlRecord,
    coverage_drift,
    extract_normative_statements,
    load_control_registry,
    registry_structure_errors,
)


def _repo_root() -> Path:
    return REPOSITORY_ROOT


def test_current_registry_has_one_record_per_normative_must_shall():
    root = _repo_root()
    gov = root / "00-governance"
    statements = tuple(
        statement
        for path in sorted(gov.glob("GDC-*.md"))
        for statement in extract_normative_statements(path)
    )
    records = load_control_registry(gov / "normative-control-registry.yaml")
    missing, stale = coverage_drift(statements, records)

    assert not missing
    assert not stale
    assert len(records) == len(statements)


def test_current_registry_structure_is_valid():
    root = _repo_root()
    records = load_control_registry(
        root / "00-governance" / "normative-control-registry.yaml"
    )
    assert registry_structure_errors(records) == ()


def test_extract_normative_statements_ignores_tables_code_and_should(tmp_path):
    path = tmp_path / "GDC-999-test.md"
    path.write_text(
        "# Test\n"
        "Rule MUST exist\n"
        "| table | MUST ignore |\n"
        "```text\n"
        "MUST ignore code\n"
        "```\n"
        "Rule SHOULD be advisory\n",
        encoding="utf-8",
    )
    statements = extract_normative_statements(path)
    assert len(statements) == 1
    assert statements[0].modality == "MUST"


def test_load_registry_rejects_non_mapping(tmp_path):
    path = tmp_path / "registry.yaml"
    path.write_text("- bad\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="YAML mapping"):
        load_control_registry(path)


def test_load_registry_requires_controls_list(tmp_path):
    path = tmp_path / "registry.yaml"
    path.write_text("version: 1\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="controls list"):
        load_control_registry(path)


def test_load_registry_rejects_non_mapping_control(tmp_path):
    path = tmp_path / "registry.yaml"
    path.write_text("controls:\n  - bad\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="control entry"):
        load_control_registry(path)

def _control_record(**overrides):
    values = {
        "control_id": "CTRL-GDC-000-001",
        "source_gdc": "GDC-000",
        "source_file": "GDC-000-governance-policy.md",
        "source_clause": "2. Policy Framework",
        "source_fingerprint": "abc123def456",
        "modality": "MUST",
        "statement": "A normative control MUST be enforced.",
        "scope": "governance-constitution",
        "severity": "ERROR",
        "enforcement_mode": "automated",
        "implementation": ("engine/example.py",),
        "test_evidence": ("tests/test_example.py",),
        "evidence_status": "verified",
        "evidence_expectation": "executable rule and control-specific test evidence",
    }
    values.update(overrides)
    return ControlRecord(**values)


def test_registry_structure_errors_reject_invalid_control_id():
    errors = registry_structure_errors(
        (_control_record(control_id="BAD-ID"),)
    )
    assert any("Invalid control_id" in error for error in errors)


def test_registry_structure_errors_reject_duplicate_id():
    record = _control_record()
    duplicate = _control_record(source_fingerprint="def456abc123")
    errors = registry_structure_errors((record, duplicate))
    assert any("Duplicate control_id" in error for error in errors)


def test_registry_structure_errors_reject_duplicate_source_fingerprint():
    first = _control_record()
    second = _control_record(
        control_id="CTRL-GDC-000-002",
    )
    errors = registry_structure_errors((first, second))
    assert any("Duplicate source fingerprint" in error for error in errors)


def test_registry_structure_errors_reject_invalid_enums():
    record = _control_record(
        modality="WILL",
        enforcement_mode="magic",
        evidence_status="unknown",
        severity="FATAL",
    )
    errors = registry_structure_errors((record,))
    assert any("invalid modality" in error for error in errors)
    assert any("invalid enforcement_mode" in error for error in errors)
    assert any("invalid evidence_status" in error for error in errors)
    assert any("invalid severity" in error for error in errors)


def test_registry_structure_errors_require_scope_and_evidence_expectation():
    record = _control_record(
        scope="",
        evidence_expectation="",
    )
    errors = registry_structure_errors((record,))
    assert any("missing scope" in error for error in errors)
    assert any("missing evidence_expectation" in error for error in errors)


def test_verified_automated_control_requires_implementation_mapping():
    record = _control_record(
        implementation=(),
    )
    errors = registry_structure_errors((record,))
    assert any(
        "verified automated control has no implementation mapping" in error
        for error in errors
    )


def test_verified_automated_control_requires_test_evidence():
    record = _control_record(
        test_evidence=(),
    )
    errors = registry_structure_errors((record,))
    assert any(
        "verified automated control has no test evidence" in error
        for error in errors
    )


def test_pending_or_gap_automated_control_may_expose_missing_mapping():
    pending = _control_record(
        control_id="CTRL-GDC-000-002",
        source_fingerprint="def456abc123",
        implementation=(),
        test_evidence=(),
        evidence_status="pending",
        control_owner="RepositoryModel / Topology Authority",
        target_phase="Slice 5.7 RepositoryModel + Zero-Corpus",
    )
    gap = _control_record(
        control_id="CTRL-GDC-000-003",
        source_fingerprint="456abc123def",
        implementation=(),
        test_evidence=(),
        evidence_status="gap",
        control_owner="Fitness Function Authority",
        target_phase="Slice 5.6 Registry Integrity Auditor",
    )
    assert registry_structure_errors((pending, gap)) == ()

def test_pending_or_gap_control_requires_owner_and_target_phase():
    pending = _control_record(
        control_id="CTRL-GDC-000-002",
        source_fingerprint="def456abc123",
        evidence_status="pending",
        control_owner="",
        target_phase="",
    )
    gap = _control_record(
        control_id="CTRL-GDC-000-003",
        source_fingerprint="456abc123def",
        evidence_status="gap",
        control_owner="",
        target_phase="",
    )

    errors = registry_structure_errors((pending, gap))
    assert sum(
        "pending/gap control is missing control_owner" in error
        for error in errors
    ) == 2
    assert sum(
        "pending/gap control is missing target_phase" in error
        for error in errors
    ) == 2


def test_non_automated_control_requires_enforcement_mechanism():
    record = _control_record(
        enforcement_mode="human-review",
        evidence_status="pending",
        implementation=(),
        test_evidence=(),
        control_owner="Architecture Review Authority",
        target_phase="Phase 10 Governance 1.0 Review",
    )
    errors = registry_structure_errors((record,))
    assert any(
        "non-automated control has no enforcement mechanism" in error
        for error in errors
    )


def test_verified_control_does_not_require_future_disposition():
    verified = _control_record(
        control_owner="",
        target_phase="",
        evidence_status="verified",
    )
    assert registry_structure_errors((verified,)) == ()


def test_current_pending_controls_have_explicit_disposition():
    root = _repo_root()
    records = load_control_registry(
        root / "00-governance" / "normative-control-registry.yaml"
    )

    pending_or_gap = [
        record
        for record in records
        if record.evidence_status in {"pending", "gap"}
    ]
    assert pending_or_gap
    assert all(record.control_owner for record in pending_or_gap)
    assert all(record.target_phase for record in pending_or_gap)


def test_current_registry_has_no_unowned_gap():
    root = _repo_root()
    records = load_control_registry(
        root / "00-governance" / "normative-control-registry.yaml"
    )
    assert not [record for record in records if record.evidence_status == "gap"]

