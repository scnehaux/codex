from tests.support.repository import REPOSITORY_ROOT
import json
from pathlib import Path

from jsonschema import Draft7Validator
from referencing import Registry, Resource

ROOT = REPOSITORY_ROOT
BASE_PATH = ROOT / "00-governance" / "schemas" / "base.schema.json"
GDC_PATH = ROOT / "00-governance" / "schemas" / "gdc.schema.json"


def _validator():
    base = json.loads(BASE_PATH.read_text(encoding="utf-8"))
    gdc = json.loads(GDC_PATH.read_text(encoding="utf-8"))
    registry = Registry().with_resource(base["$id"], Resource.from_contents(base))
    return Draft7Validator(gdc, registry=registry)


def _doc(status: str, include_last_reviewed: bool):
    meta = {
        "id": "GDC-999",
        "title": "Lifecycle Test",
        "owner": "Architecture Authority",
        "version": "1.0.0" if status != "draft" else "0.1.0",
        "status": status,
        "classification": "internal",
        "governed_by": ["GDC-000"],
        "review_cycle_days": 180,
        "created_date": "2026-08-28",
    }
    if include_last_reviewed:
        meta["last_reviewed"] = "2026-08-28"
    return {"filename": "GDC-999-lifecycle-test.md", "doc_meta": meta}


def test_draft_gdc_does_not_require_last_reviewed():
    errors = list(_validator().iter_errors(_doc("draft", False)))
    assert not any("last_reviewed" in error.message for error in errors)


def test_approved_gdc_requires_last_reviewed():
    errors = list(_validator().iter_errors(_doc("approved", False)))
    assert any("last_reviewed" in error.message for error in errors)


def test_deprecated_gdc_requires_last_reviewed():
    errors = list(_validator().iter_errors(_doc("deprecated", False)))
    assert any("last_reviewed" in error.message for error in errors)


def test_baseline_gdc_with_last_reviewed_is_valid_for_lifecycle_rule():
    errors = list(_validator().iter_errors(_doc("approved", True)))
    assert not any("last_reviewed" in error.message for error in errors)
