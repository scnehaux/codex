from tests.support.validators import make_validator
from engine.control.validators.metadata_rules import (
    _validate_review_age,
    _validate_approved_version_stability,
    _validate_cross_references,
    _validate_technologies_whitelist,
    validate_lifecycle_age,
)
from engine.control.config.severity import SeverityRule
import datetime
import engine.control.validators.metadata_rules as metadata_rules


def test_validate_review_age():
    rules = {"rules": {}, "severity_levels": {}}
    v = make_validator(
        doc_meta={"last_reviewed": "2000-01-01", "review_cycle_days": 365}, rules=rules
    )
    _validate_review_age(v)
    assert len(v.errors) == 1
    assert v.errors[0][0] == "WARNING"


def test_review_age_no_meta():
    v = make_validator(doc_meta={})
    _validate_review_age(v)
    assert len(v.errors) == 0


def test_baseline_status_at_major_version_zero_is_refused():
    """Baseline-bearing lifecycle states cannot remain on Semantic Versioning major zero."""
    rules = {"rules": {}, "severity_levels": {}}

    cases = [
        ("GDC", "approved"),
        ("GDC", "deprecated"),
        ("ADR", "accepted"),
        ("ADR", "superseded"),
    ]
    for doc_type, status in cases:
        v = make_validator(
            doc_meta={"status": status, "version": "0.4.0"},
            rules=rules,
        )
        v.doc_type_name = doc_type
        _validate_approved_version_stability(v)
        assert len(v.errors) == 1, f"{doc_type} {status} at 0.4.0 was accepted"
        assert "major version zero" in v.errors[0][1]

def test_pre_baseline_statuses_may_sit_at_major_version_zero():
    """Pre-baseline lifecycle states may correctly remain on Semantic Versioning major zero."""
    rules = {"rules": {}, "severity_levels": {}}

    cases = [
        ("PAD", "chartered"),
        ("GDC", "draft"),
        ("EAD", "draft"),
        ("ADR", "proposed"),
    ]
    for doc_type, status in cases:
        v = make_validator(
            doc_meta={"status": status, "version": "0.1.0"},
            rules=rules,
        )
        v.doc_type_name = doc_type
        _validate_approved_version_stability(v)
        assert len(v.errors) == 0, f"{doc_type} {status} at 0.1.0 was refused"

def test_stable_versions_and_unversioned_artifacts_pass():
    rules = {"rules": {}, "severity_levels": {}}

    v = make_validator(
        doc_meta={"status": "approved", "version": "1.0.0"},
        rules=rules,
    )
    v.doc_type_name = "GDC"
    _validate_approved_version_stability(v)
    assert len(v.errors) == 0

    v = make_validator(
        doc_meta={"status": "approved", "version": "10.2.3"},
        rules=rules,
    )
    v.doc_type_name = "GDC"
    _validate_approved_version_stability(v)
    assert len(v.errors) == 0

    # ADRs are immutable snapshots rather than versioned artifacts.
    v = make_validator(doc_meta={"status": "accepted"}, rules=rules)
    v.doc_type_name = "ADR"
    _validate_approved_version_stability(v)
    assert len(v.errors) == 0

def test_version_stability_no_meta():
    v = make_validator(doc_meta={})
    _validate_approved_version_stability(v)
    assert len(v.errors) == 0


def test_validate_cross_references():
    rules = {"rules": {}, "severity_levels": {}}
    # Test invalid cross reference IDs
    v2 = make_validator(
        doc_meta={
            "status": "draft",
            "parent_pad": "PAD-999",
            "governed_by": ["GDC-999"],
        },
        rules=rules,
        all_doc_ids={"PAD-001"},
    )
    _validate_cross_references(v2)
    assert any("not found in this repository" in e[1] for e in v2.errors)

    # Test valid
    v3 = make_validator(
        doc_meta={"status": "draft", "parent_pad": "PAD-001", "governed_by": "GDC-002"},
        rules=rules,
        all_doc_ids={"PAD-001", "GDC-002"},
    )
    _validate_cross_references(v3)
    assert len(v3.errors) == 0


def test_cross_references_no_meta():
    v = make_validator(doc_meta={})
    _validate_cross_references(v)
    assert len(v.errors) == 0






def test_validate_technologies_whitelist(monkeypatch, tmp_path):
    rules = {
        "severity_levels": {
            "technology_hold_violation": "CRITICAL",
            "technology_policy_unavailable": "CRITICAL",
            "unapproved_technology": "ERROR",
        }
    }

    radar_path = tmp_path / "tech-radar.yaml"
    radar_path.write_text(
        "technology_radar:\n"
        "  adopt:\n"
        "    - postgresql\n"
        "  trial: []\n"
        "  assess: []\n"
        "  hold:\n"
        "    - jquery\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(metadata_rules, "TECH_RADAR_YAML_PATH", str(radar_path))

    v1 = make_validator(doc_meta={}, rules=rules)
    v1.doc_type_name = "SAD"
    _validate_technologies_whitelist(v1)
    assert len(v1.errors) == 0

    v2 = make_validator(
        doc_meta={
            "technologies": [
                {"name": "UnknownTechName123"},
                "invalid_non_dict_tech",
            ]
        },
        rules=rules,
    )
    v2.doc_type_name = "SAD"
    _validate_technologies_whitelist(v2)
    assert len(v2.errors) >= 1
    assert any("not defined in the Enterprise Tech Radar" in e[1] for e in v2.errors)

    v3 = make_validator(
        doc_meta={
            "technologies": [
                {
                    "name": "postgresql",
                    "base": "jquery",
                }
            ]
        },
        rules=rules,
    )
    v3.doc_type_name = "SAD"
    _validate_technologies_whitelist(v3)
    assert any("technology on HOLD" in e[1] for e in v3.errors)

def test_validate_technologies_whitelist_missing_tech_radar(monkeypatch, tmp_path):
    rules = {
        "severity_levels": {
            "technology_hold_violation": "CRITICAL",
            "technology_policy_unavailable": "CRITICAL",
            "unapproved_technology": "ERROR",
        }
    }
    v = make_validator(
        doc_meta={"technologies": [{"name": "postgresql"}]},
        rules=rules,
    )
    v.doc_type_name = "SAD"

    monkeypatch.setattr(
        metadata_rules,
        "TECH_RADAR_YAML_PATH",
        str(tmp_path / "missing-tech-radar.yaml"),
    )
    _validate_technologies_whitelist(v)

    assert len(v.errors) == 1
    assert v.errors[0][0] == "CRITICAL"
    assert "policy source is unavailable" in v.errors[0][1]

def test_validate_lifecycle_age_is_artifact_aware():
    old_date = (datetime.date.today() - datetime.timedelta(days=35)).isoformat()
    fresh_date = (datetime.date.today() - datetime.timedelta(days=10)).isoformat()

    errs = validate_lifecycle_age(
        {"created_date": old_date},
        "SAD",
        "draft",
        "WARNING",
    )
    assert len(errs) == 1
    assert "exceeding limit of 30 days" in errs[0][1]

    assert validate_lifecycle_age(
        {"created_date": fresh_date},
        "SAD",
        "draft",
        "WARNING",
    ) == []

    assert validate_lifecycle_age(
        {"created_date": old_date},
        "GDC",
        "draft",
        "WARNING",
    ) == []

    assert validate_lifecycle_age(
        {"last_updated": old_date},
        "GDC",
        "deprecated",
        "WARNING",
    ) == []


def test_validate_lifecycle_age_requires_anchor_when_policy_exists():
    errs = validate_lifecycle_age({}, "EAD", "draft", "WARNING")
    assert len(errs) == 1
    assert "missing 'created_date'" in errs[0][1]


def test_validate_lifecycle_age_ignores_unparseable_date_until_temporal_phase():
    assert validate_lifecycle_age(
        {"created_date": "not-a-date"},
        "EAD",
        "draft",
        "WARNING",
    ) == []
