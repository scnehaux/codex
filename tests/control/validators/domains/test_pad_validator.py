from tests.support.validators import make_validator
import os
import json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))


def _global_rules():
    with open(
        os.path.join(ROOT, "00-governance", "schemas", "base.schema.json"),
        encoding="utf-8",
    ) as f:
        return json.load(f).get("x-global-config", {})


from engine.control.validators.domains.pad_validator import PADValidator


def test_pad_invalid_fulfilled_by():
    rules = {"rules": {"metadata": {}}, "severity_levels": {}}
    v = make_validator(
        cls=PADValidator,
        doc_meta={"fulfilled_by": ["SAD-999"]},
        rules=rules,
        all_doc_ids={"SAD-001"},
        filename="PAD-001.md",
    )
    v.validate_type_specific()
    assert any("does not exist" in msg for sev, msg in v.errors)


def test_pad_bidirectional_traceability_fail():
    rules = {"rules": {"metadata": {}}, "severity_levels": {}}
    v = make_validator(
        cls=PADValidator,
        doc_meta={"id": "PAD-001", "fulfilled_by": ["SAD-001"]},
        rules=rules,
        all_doc_ids={"SAD-001"},
        all_doc_metadata={"SAD-001": {"parent_pad": "PAD-999"}},
        filename="PAD-001.md",
    )
    v.validate_type_specific()
    assert any("Bidirectional traceability is broken" in msg for sev, msg in v.errors)


def test_pad_bidirectional_traceability_pass():
    rules = {"rules": {"metadata": {}}, "severity_levels": {}}
    v = make_validator(
        cls=PADValidator,
        doc_meta={
            "id": "PAD-001",
            "fulfilled_by": ["SAD-001"],
            "realizes_capability": "EAD-001",
        },
        rules=rules,
        all_doc_ids={"SAD-001", "EAD-001"},
        all_doc_metadata={"SAD-001": {"parent_pad": "PAD-001"}, "EAD-001": {}},
        filename="PAD-001.md",
    )
    v.validate_type_specific()
    assert len(v.errors) == 0


def test_pad_empty_fulfilled_by_and_missing_ead():
    rules = {"rules": {"metadata": {}}, "severity_levels": {}}
    # fulfilled_by is empty list [] AND realizes_capability references non-existent EAD-999
    v = make_validator(
        cls=PADValidator,
        doc_meta={
            "id": "PAD-001",
            "fulfilled_by": [],
            "realizes_capability": ["EAD-999"],
        },
        rules=rules,
        all_doc_ids={"EAD-001"},
        filename="PAD-001.md",
    )
    v.validate_type_specific()
    assert any("PAD 'fulfilled_by' is empty" in msg for sev, msg in v.errors)
    assert any(
        "references EAD 'EAD-999' which does not exist" in msg for sev, msg in v.errors
    )
