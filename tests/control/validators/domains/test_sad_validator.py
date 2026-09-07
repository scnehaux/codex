import json
import os

from engine.control.validators.domains.sad_validator import SADValidator
from tests.support.validators import make_validator

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))


def _global_rules():
    with open(
        os.path.join(ROOT, "schemas", "base.schema.json"),
        encoding="utf-8",
    ) as f:
        return json.load(f).get("x-global-config", {})


def _rules():
    return {"rules": {"metadata": {}}, "severity_levels": {}}


def test_sad_missing_parent_pad():
    v = make_validator(
        cls=SADValidator,
        doc_meta={"status": "draft"},
        rules=_rules(),
        filename="SAD-001.md",
    )
    v.validate_type_specific()
    assert any("missing required traceability" in msg for sev, msg in v.errors)


def test_sad_invalid_parent_pad():
    v = make_validator(
        cls=SADValidator,
        doc_meta={"parent_pad": "PAD-999"},
        rules=_rules(),
        all_doc_ids={"PAD-001"},
        filename="SAD-001.md",
    )
    v.validate_type_specific()
    assert any("does not exist" in msg for sev, msg in v.errors)


def test_sad_bidirectional_traceability_fail():
    v = make_validator(
        cls=SADValidator,
        doc_meta={"id": "SAD-001", "parent_pad": "PAD-001"},
        rules=_rules(),
        all_doc_ids={"PAD-001"},
        all_doc_metadata={"PAD-001": {"fulfilled_by": ["SAD-999"]}},
        filename="SAD-001.md",
    )
    v.validate_type_specific()
    assert any("Bidirectional traceability is broken" in msg for sev, msg in v.errors)


def test_sad_bidirectional_traceability_pass():
    v = make_validator(
        cls=SADValidator,
        doc_meta={"id": "SAD-001", "parent_pad": "PAD-001"},
        rules=_rules(),
        all_doc_ids={"PAD-001"},
        all_doc_metadata={"PAD-001": {"fulfilled_by": ["SAD-001"]}},
        filename="SAD-001.md",
    )
    v.validate_type_specific()
    assert len(v.errors) == 0


def test_chartered_sad_allowed_under_chartered_pad():
    v = make_validator(
        cls=SADValidator,
        doc_meta={
            "id": "SAD-001",
            "status": "chartered",
            "parent_pad": "PAD-001",
        },
        rules=_rules(),
        all_doc_ids={"PAD-001"},
        all_doc_metadata={
            "PAD-001": {
                "status": "chartered",
                "fulfilled_by": ["SAD-001"],
            }
        },
        filename="SAD-001.md",
    )
    v.validate_type_specific()
    assert len(v.errors) == 0


def test_draft_sad_rejected_under_chartered_pad():
    v = make_validator(
        cls=SADValidator,
        doc_meta={
            "id": "SAD-001",
            "status": "draft",
            "parent_pad": "PAD-001",
        },
        rules=_rules(),
        all_doc_ids={"PAD-001"},
        all_doc_metadata={
            "PAD-001": {
                "status": "chartered",
                "fulfilled_by": ["SAD-001"],
            }
        },
        filename="SAD-001.md",
    )
    v.validate_type_specific()
    assert any("only when its parent PAD is 'approved'" in msg for sev, msg in v.errors)


def test_draft_sad_allowed_under_approved_pad():
    v = make_validator(
        cls=SADValidator,
        doc_meta={
            "id": "SAD-001",
            "status": "draft",
            "parent_pad": "PAD-001",
        },
        rules=_rules(),
        all_doc_ids={"PAD-001"},
        all_doc_metadata={
            "PAD-001": {
                "status": "approved",
                "fulfilled_by": ["SAD-001"],
            }
        },
        filename="SAD-001.md",
    )
    v.validate_type_specific()
    assert len(v.errors) == 0
