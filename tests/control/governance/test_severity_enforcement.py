from tests.support.repository import REPOSITORY_ROOT
from pathlib import Path

import yaml

from engine.control.config.severity import SeverityRule
from engine.control.governance.severity_enforcement import (
    load_severity_enforcement_registry,
    severity_registry_findings,
)


ROOT = REPOSITORY_ROOT
REGISTRY = ROOT / "00-governance" / "severity-enforcement-registry.yaml"


def _severity_levels():
    import json
    from engine.control.config.loader import parse_and_validate_global_config

    base = json.loads(
        (ROOT / "00-governance" / "schemas" / "base.schema.json").read_text(
            encoding="utf-8"
        )
    )
    _, severity_levels, _ = parse_and_validate_global_config(base)
    return severity_levels


def test_current_severity_registry_is_structurally_reconciled():
    assert severity_registry_findings(ROOT, _severity_levels()) == ()


def test_registry_has_exact_bijection_with_severity_rule():
    records = load_severity_enforcement_registry(REGISTRY)
    assert {record.rule_id for record in records} == {
        item.value for item in SeverityRule
    }


def test_pending_rules_are_owned_and_scheduled():
    records = load_severity_enforcement_registry(REGISTRY)
    pending = [record for record in records if record.evidence_status == "pending"]
    assert pending
    assert all(record.control_owner for record in pending)
    assert all(record.target_phase for record in pending)


def test_verified_rules_have_real_evidence_paths():
    records = load_severity_enforcement_registry(REGISTRY)
    verified = [record for record in records if record.evidence_status == "verified"]
    assert verified
    for record in verified:
        assert record.implementation
        assert record.test_evidence
        for value in (*record.implementation, *record.test_evidence):
            candidate = value.split("::", 1)[0].split("#", 1)[0]
            assert (ROOT / candidate).exists()


def test_registry_rejects_duplicate_missing_and_unknown_rules(tmp_path):
    registry = tmp_path / "severity-enforcement-registry.yaml"
    rule = next(iter(SeverityRule)).value
    registry.write_text(
        yaml.safe_dump(
            {
                "rules": [
                    {
                        "rule_id": rule,
                        "evidence_status": "pending",
                        "enforcement_kind": "deferred",
                        "implementation": [],
                        "test_evidence": [],
                        "control_owner": "x",
                        "target_phase": "x",
                        "rationale": "x",
                    },
                    {
                        "rule_id": rule,
                        "evidence_status": "pending",
                        "enforcement_kind": "deferred",
                        "implementation": [],
                        "test_evidence": [],
                        "control_owner": "x",
                        "target_phase": "x",
                        "rationale": "x",
                    },
                    {
                        "rule_id": "not_real",
                        "evidence_status": "pending",
                        "enforcement_kind": "deferred",
                        "implementation": [],
                        "test_evidence": [],
                        "control_owner": "x",
                        "target_phase": "x",
                        "rationale": "x",
                    },
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    root = tmp_path
    governance = root / "00-governance"
    governance.mkdir()
    registry.rename(governance / registry.name)

    findings = severity_registry_findings(root, {rule: "ERROR"})
    assert any("duplicate severity enforcement record" in item for item in findings)
    assert any("registry entry has no SeverityRule" in item for item in findings)
    assert any("missing severity enforcement record" in item for item in findings)


def test_verified_rule_requires_implementation_and_test_evidence(tmp_path):
    all_rules = []
    for item in SeverityRule:
        all_rules.append(
            {
                "rule_id": item.value,
                "evidence_status": "pending",
                "enforcement_kind": "deferred",
                "implementation": [],
                "test_evidence": [],
                "control_owner": "owner",
                "target_phase": "phase",
                "rationale": "deferred",
            }
        )

    all_rules[0].update(
        {
            "evidence_status": "verified",
            "enforcement_kind": "runtime-rule",
            "implementation": [],
            "test_evidence": [],
            "control_owner": "",
            "target_phase": "",
            "rationale": "claimed verified",
        }
    )

    governance = tmp_path / "00-governance"
    governance.mkdir()
    (governance / "severity-enforcement-registry.yaml").write_text(
        yaml.safe_dump({"rules": all_rules}, sort_keys=False),
        encoding="utf-8",
    )

    severity_levels = {item.value: "ERROR" for item in SeverityRule}
    findings = severity_registry_findings(tmp_path, severity_levels)
    assert any("verified rule missing implementation" in item for item in findings)
    assert any("verified rule missing test evidence" in item for item in findings)

def _write_severity_registry(root, rules):
    governance = root / "00-governance"
    governance.mkdir(parents=True, exist_ok=True)
    path = governance / "severity-enforcement-registry.yaml"
    path.write_text(
        yaml.safe_dump({"rules": rules}, sort_keys=False),
        encoding="utf-8",
    )
    return path


def _pending_rule(rule_id):
    return {
        "rule_id": rule_id,
        "evidence_status": "pending",
        "enforcement_kind": "deferred",
        "implementation": [],
        "test_evidence": [],
        "control_owner": "Fitness Function Authority",
        "target_phase": "Future reconciliation",
        "rationale": "Explicitly unresolved",
    }


def test_loader_rejects_non_registry_shape_and_non_mapping_entry(tmp_path):
    malformed = tmp_path / "bad.yaml"
    malformed.write_text("not_rules: []\n", encoding="utf-8")
    try:
        load_severity_enforcement_registry(malformed)
    except ValueError as exc:
        assert "must contain a 'rules' list" in str(exc)
    else:
        raise AssertionError("malformed registry must fail closed")

    malformed.write_text("rules:\n  - not-a-mapping\n", encoding="utf-8")
    try:
        load_severity_enforcement_registry(malformed)
    except ValueError as exc:
        assert "entries must be mappings" in str(exc)
    else:
        raise AssertionError("non-mapping record must fail closed")


def test_findings_fail_closed_when_registry_file_is_missing(tmp_path):
    findings = severity_registry_findings(
        tmp_path,
        {item.value: "ERROR" for item in SeverityRule},
    )
    assert len(findings) == 1
    assert "severity enforcement registry invalid" in findings[0]


def test_record_validation_catches_invalid_state_kind_rationale_and_pending_ownership(
    tmp_path,
):
    rules = [_pending_rule(item.value) for item in SeverityRule]
    rules[0].update(
        {
            "evidence_status": "mystery",
            "enforcement_kind": "imaginary",
            "rationale": "",
        }
    )
    rules[1].update(
        {
            "control_owner": "",
            "target_phase": "",
        }
    )
    _write_severity_registry(tmp_path, rules)

    findings = severity_registry_findings(
        tmp_path,
        {item.value: "ERROR" for item in SeverityRule},
    )

    assert any("invalid evidence_status" in item for item in findings)
    assert any("invalid enforcement_kind" in item for item in findings)
    assert any("missing rationale" in item for item in findings)
    assert any("pending rule missing control_owner" in item for item in findings)
    assert any("pending rule missing target_phase" in item for item in findings)


def test_verified_record_rejects_deferred_and_missing_evidence_path(tmp_path):
    rules = [_pending_rule(item.value) for item in SeverityRule]
    rules[0].update(
        {
            "evidence_status": "verified",
            "enforcement_kind": "deferred",
            "implementation": ["missing/implementation.py"],
            "test_evidence": ["missing/test_rule.py"],
            "control_owner": "",
            "target_phase": "",
            "rationale": "Invalid verified claim",
        }
    )
    _write_severity_registry(tmp_path, rules)

    findings = severity_registry_findings(
        tmp_path,
        {item.value: "ERROR" for item in SeverityRule},
    )

    assert any("verified rule cannot be deferred" in item for item in findings)
    assert sum("evidence path does not exist" in item for item in findings) == 2


def test_empty_rule_id_is_rejected(tmp_path):
    rules = [_pending_rule(item.value) for item in SeverityRule]
    rules[0]["rule_id"] = ""
    _write_severity_registry(tmp_path, rules)

    findings = severity_registry_findings(
        tmp_path,
        {item.value: "ERROR" for item in SeverityRule},
    )

    assert any("record missing rule_id" in item for item in findings)

def test_slice5_6_direct_candidates_are_verified_with_evidence():
    expected = {
        "invalid_lint_disable",
        "traceability_violation",
        "missing_section",
        "structural_integrity_violation",
        "exception_expired",
        "technology_hold_violation",
        "technology_policy_unavailable",
        "unapproved_technology",
    }
    records = {
        record.rule_id: record
        for record in load_severity_enforcement_registry(REGISTRY)
    }

    for rule_id in expected:
        record = records[rule_id]
        assert record.evidence_status == "verified"
        assert record.enforcement_kind in {"runtime-rule", "auditor", "cli-fatal"}
        assert record.implementation
        assert record.test_evidence
        for value in (*record.implementation, *record.test_evidence):
            candidate = value.split("::", 1)[0].split("#", 1)[0]
            assert (ROOT / candidate).exists()

def test_slice5_6_schema_translation_and_dynamic_config_rules_are_verified():
    expected = {
        "missing_metadata",
        "missing_section_keyword",
        "prohibited_words",
        "schema_validation_failed",
        "ambiguity_rules",
    }

    records = {
        record.rule_id: record
        for record in load_severity_enforcement_registry(REGISTRY)
    }

    for rule_id in expected:
        record = records[rule_id]
        assert record.evidence_status == "verified"
        assert record.enforcement_kind in {"schema-translation", "dynamic-config"}
        assert record.implementation
        assert record.test_evidence
        for value in (*record.implementation, *record.test_evidence):
            candidate = value.split("::", 1)[0].split("#", 1)[0]
            assert (ROOT / candidate).exists()

def test_slice5_6_repository_classification_rules_are_verified():
    expected = {
        "repository_classification_violation",
        "repository_visibility_mismatch",
    }
    records = {
        record.rule_id: record
        for record in load_severity_enforcement_registry(REGISTRY)
    }

    for rule_id in expected:
        record = records[rule_id]
        assert record.evidence_status == "verified"
        assert record.enforcement_kind == "runtime-rule"
        assert record.implementation == (
            'engine/control/governance/classification.py',
        )
        assert record.test_evidence == (
            'tests/control/governance/test_classification.py',
        )

def test_slice5_6_behavioral_runtime_rules_are_verified():
    expected = {
        "approved_version_not_stable",
        "compliance_filename_match",
        "compliance_macro_directory",
        "cross_reference_missing",
        "inline_reference_missing",
        "operational_stability_violation",
        "review_age_violation",
        "stylistic_deviation",
        "temporal_integrity_violation",
        "corrupt_frontmatter",
        "lifecycle_age_violation",
        "missing_validator",
        "relaxed_validation_applied",
        "unknown_document_type",
        "unreadable_artifact",
    }

    records = {
        record.rule_id: record
        for record in load_severity_enforcement_registry(REGISTRY)
    }

    for rule_id in expected:
        record = records[rule_id]
        assert record.evidence_status == "verified"
        assert record.enforcement_kind in {"runtime-rule", "cli-fatal", "auditor"}
        assert record.implementation
        assert record.test_evidence
        for value in (*record.implementation, *record.test_evidence):
            candidate = value.split("::", 1)[0].split("#", 1)[0]
            assert (ROOT / candidate).exists()
