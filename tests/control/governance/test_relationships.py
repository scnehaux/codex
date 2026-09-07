import pytest

from engine.control.governance.relationships import (
    ALL_RELATION_FIELDS,
    APPROVED_PARENT_FOR_ACTIVE_SAD,
    RELATIONSHIP_REGISTRY,
    artifact_type_from_id,
    dag_relation_specs_for_source,
    normalize_relation_values,
    relationship_contract_findings,
    relationship_fields_for_source,
    relationship_spec_for,
    relationship_specs_for_source,
)


def test_registry_declares_required_semantics_for_every_relation():
    assert RELATIONSHIP_REGISTRY
    for spec in RELATIONSHIP_REGISTRY:
        assert spec.name
        assert spec.metadata_field
        assert spec.source_types
        assert spec.target_types
        assert spec.direction in {"up", "down"}
        assert spec.cardinality
        assert spec.authority_requirement
        assert isinstance(spec.dag_participation, bool)


def test_governed_by_is_source_specific_not_one_broad_union():
    assert relationship_spec_for("GDC", "governed_by").target_types == frozenset(
        {"GDC"}
    )
    assert relationship_spec_for("EAD", "governed_by").target_types == frozenset(
        {"GDC"}
    )
    assert relationship_spec_for("PAD", "governed_by").target_types == frozenset(
        {"GDC", "EAD", "ADR"}
    )
    assert relationship_spec_for("ADR", "governed_by").target_types == frozenset(
        {"GDC", "EAD", "PAD", "SAD"}
    )


def test_pad_fulfilled_by_declares_inverse_but_not_dag_participation():
    spec = relationship_spec_for("PAD", "fulfilled_by")
    assert spec is not None
    assert spec.inverse_relation == "parent_pad"
    assert spec.dag_participation is False
    assert spec.cardinality == "0..*"


def test_sad_parent_pad_declares_lifecycle_authority_requirement():
    spec = relationship_spec_for("SAD", "parent_pad")
    assert spec is not None
    assert spec.authority_requirement == APPROVED_PARENT_FOR_ACTIVE_SAD
    assert spec.cardinality == "1..1"
    assert spec.inverse_relation == "fulfilled_by"


def test_tdd_parent_sad_preserves_multiple_parent_support():
    spec = relationship_spec_for("TDD", "parent_sad")
    assert spec is not None
    assert spec.cardinality == "1..*"


@pytest.mark.parametrize(
    ("doc_id", "expected"),
    [
        ("GDC-000", "GDC"),
        ("EAD-001", "EAD"),
        ("STD-GLB-001", "STD"),
        ("PAD-PLT-001", "PAD"),
        ("SAD-001", "SAD"),
        ("ADR-GLB-001", "ADR"),
        ("TDD-foo-bar-001", "TDD"),
        ("EXAMPLE-EAD-001", None),
        (None, None),
    ],
)
def test_artifact_type_from_id(doc_id, expected):
    assert artifact_type_from_id(doc_id) == expected


def test_normalize_relation_values():
    assert normalize_relation_values(None) == []
    assert normalize_relation_values("EAD-001") == ["EAD-001"]
    assert normalize_relation_values(["EAD-001"]) == ["EAD-001"]


def test_relationship_fields_unknown_source_fails_safe_for_reference_scanning():
    assert relationship_fields_for_source("UNKNOWN") == ALL_RELATION_FIELDS


def test_dag_specs_exclude_downward_inverse_relation():
    fields = {spec.metadata_field for spec in dag_relation_specs_for_source("PAD")}
    assert "realizes_capability" in fields
    assert "governed_by" in fields
    assert "fulfilled_by" not in fields


def test_pad_may_be_governed_by_adr():
    findings = relationship_contract_findings(
        "PAD-PLT-005",
        {
            "status": "approved",
            "governed_by": ["ADR-GLB-017"],
            "realizes_capability": ["EAD-001"],
            "fulfilled_by": [],
        },
        {
            "ADR-GLB-017": {"status": "accepted"},
            "EAD-001": {"status": "approved"},
        },
    )
    assert findings == []


def test_adr_may_be_governed_by_sad():
    findings = relationship_contract_findings(
        "ADR-IAM-001",
        {"governed_by": ["SAD-001"]},
        {"SAD-001": {"status": "approved"}},
    )
    assert findings == []


def test_wrong_source_field_is_rejected():
    findings = relationship_contract_findings(
        "TDD-foo-api-001",
        {"parent_pad": "PAD-001", "parent_sad": "SAD-001"},
        {
            "PAD-001": {"status": "approved"},
            "SAD-001": {"status": "approved"},
        },
    )
    assert any(
        f.code == "unsupported_source" and f.field == "parent_pad" for f in findings
    )


def test_wrong_target_type_is_rejected():
    findings = relationship_contract_findings(
        "TDD-foo-api-001",
        {"parent_sad": "PAD-001"},
        {"PAD-001": {"status": "approved"}},
    )
    assert any(f.code == "invalid_target_type" for f in findings)


def test_missing_required_relation_is_cardinality_violation():
    findings = relationship_contract_findings(
        "TDD-foo-api-001",
        {},
        {},
    )
    assert any(
        f.code == "missing_required" and f.field == "parent_sad" for f in findings
    )


def test_sad_parent_pad_max_cardinality_is_enforced():
    findings = relationship_contract_findings(
        "SAD-001",
        {
            "status": "chartered",
            "governed_by": ["EAD-001"],
            "parent_pad": ["PAD-001", "PAD-002"],
        },
        {
            "EAD-001": {"status": "approved"},
            "PAD-001": {"status": "approved"},
            "PAD-002": {"status": "approved"},
        },
    )
    assert any(f.code == "too_many_targets" for f in findings)


def test_duplicate_target_is_rejected():
    findings = relationship_contract_findings(
        "PAD-PLT-001",
        {
            "governed_by": ["GDC-000", "GDC-000"],
            "realizes_capability": ["EAD-001"],
            "fulfilled_by": [],
        },
        {
            "GDC-000": {"status": "approved"},
            "EAD-001": {"status": "approved"},
        },
    )
    assert any(f.code == "duplicate_target" for f in findings)


def test_non_string_target_is_rejected():
    findings = relationship_contract_findings(
        "TDD-foo-api-001",
        {"parent_sad": [123]},
        {},
    )
    assert any(f.code == "invalid_target_type" for f in findings)


def test_non_gdc_self_reference_is_rejected():
    findings = relationship_contract_findings(
        "ADR-GLB-001",
        {"governed_by": ["ADR-GLB-001"]},
        {"ADR-GLB-001": {"status": "accepted"}},
    )
    assert any(f.code == "self_reference" for f in findings)


def test_gdc_self_governance_is_explicitly_allowed():
    findings = relationship_contract_findings(
        "GDC-000",
        {"governed_by": ["GDC-000"]},
        {"GDC-000": {"status": "draft"}},
    )
    assert findings == []


def test_active_sad_requires_approved_parent_pad():
    findings = relationship_contract_findings(
        "SAD-001",
        {
            "status": "draft",
            "governed_by": ["EAD-001"],
            "parent_pad": "PAD-001",
        },
        {
            "EAD-001": {"status": "approved"},
            "PAD-001": {"status": "draft"},
        },
    )
    assert any(f.code == "authority_violation" for f in findings)


def test_chartered_sad_can_reference_nonapproved_parent_pad():
    findings = relationship_contract_findings(
        "SAD-001",
        {
            "status": "chartered",
            "governed_by": ["EAD-001"],
            "parent_pad": "PAD-001",
        },
        {
            "EAD-001": {"status": "approved"},
            "PAD-001": {"status": "draft"},
        },
    )
    assert not any(f.code == "authority_violation" for f in findings)


def test_missing_target_metadata_is_left_to_cross_reference_validator():
    findings = relationship_contract_findings(
        "TDD-foo-api-001",
        {"parent_sad": "SAD-404"},
        {},
    )
    assert findings == []


def test_non_dict_metadata_is_ignored():
    assert relationship_contract_findings("SAD-001", None, {}) == []
    assert relationship_contract_findings("SAD-001", "bad", {}) == []


def test_relationship_spec_lookup_returns_none_for_unsupported_pair():
    assert relationship_spec_for("TDD", "fulfilled_by") is None


def test_relationship_specs_for_known_source_are_nonempty():
    assert relationship_specs_for_source("PAD")
