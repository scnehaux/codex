from tests.support.validators import make_validator
import os
import json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))


def _global_rules():
    with open(
        os.path.join(ROOT, "schemas", "base.schema.json"),
        encoding="utf-8",
    ) as f:
        return json.load(f).get("x-global-config", {})


from engine.control.validators.domains.tdd_validator import TDDValidator


def test_tdd_missing_parent_sad():
    rules = {"rules": {"metadata": {}}, "severity_levels": {}}
    v = make_validator(
        cls=TDDValidator,
        doc_meta={"status": "draft"},
        rules=rules,
        all_doc_ids={"SAD-001"},
        filename="TDD-001.md",
    )
    v.validate_type_specific()
    assert any("missing required traceability" in msg for sev, msg in v.errors)


def test_tdd_invalid_parent_sad():
    rules = {"rules": {"metadata": {}}, "severity_levels": {}}
    v = make_validator(
        cls=TDDValidator,
        doc_meta={"parent_sad": "SAD-999"},
        rules=rules,
        all_doc_ids={"SAD-001"},
        filename="TDD-001.md",
    )
    v.validate_type_specific()
    assert any("does not exist" in msg for sev, msg in v.errors)


def test_tdd_valid_parent_sad():
    rules = {"rules": {"metadata": {}}, "severity_levels": {}}
    v = make_validator(
        cls=TDDValidator,
        doc_meta={"parent_sad": "SAD-001"},
        rules=rules,
        all_doc_ids={"SAD-001"},
        filename="TDD-001.md",
    )
    v.validate_type_specific()
    assert len(v.errors) == 0


# ---------- Missing doc_meta for all validators ----------
