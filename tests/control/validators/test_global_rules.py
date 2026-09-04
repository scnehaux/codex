from tests.support.validators import make_validator
import re
import os
import json
from tests.support.repository import REPOSITORY_ROOT
from engine.control.validators.global_rules import (
    _validate_content_quality,
    _validate_compliance_placement,
    _validate_temporal_integrity,
)

ROOT = str(REPOSITORY_ROOT)


def _global_rules():
    with open(
        os.path.join(ROOT, "schemas", "base.schema.json"),
        encoding="utf-8",
    ) as f:
        return json.load(f).get("x-global-config", {})


def test_validate_content_quality():
    rules = {
        "content_rules": {
            "prohibited_words": {
                "patterns": ["just", "basically"],
                "error_message": "Found prohibited word",
            }
        },
        "severity_levels": {},
    }
    v = make_validator(rules=rules, content="This is basically just too short.")
    _validate_content_quality(v)
    prohibited_errors = [e for e in v.errors if "found prohibited word" in e[1].lower()]
    assert len(prohibited_errors) == 2


def test_ambiguity_check():
    rules = {
        "content_rules": {
            "ambiguity_rules": {
                "patterns": ["\\b(very|extremely)\\s+(fast|good)\\b"],
                "error_message": "Vague claim",
            }
        },
        "severity_levels": {},
    }
    v = make_validator(rules=rules, content="It is very fast.")
    _validate_content_quality(v)
    assert len(v.errors) == 1


def test_ambiguity_no_message():
    rules = {
        "content_rules": {"prohibited_words": {"patterns": ["badword", "nono"]}},
        "severity_levels": {},
    }
    v = make_validator(rules=rules, content="This is a badword.")
    _validate_content_quality(v)
    assert len(v.errors) == 1


def test__validate_content_quality_ambiguity_regex():
    pat = _global_rules()["content_rules"]["ambiguity_rules"]["patterns"][0]
    assert "\x08" not in pat, "double-quote corrupted \\b into a backspace char"
    assert re.search(pat, "this design is highly scalable", re.IGNORECASE)
    assert re.search(pat, "it is very fast under load", re.IGNORECASE)
    assert not re.search(pat, "a perfectly ordinary sentence", re.IGNORECASE)


def test_validate_technologies_whitelist(monkeypatch):
    import engine.control.validators.global_rules as gr
    from io import StringIO

    original_exists = os.path.exists

    def mock_exists(p):
        if "tech-radar.yaml" in p:
            return True
        return original_exists(p)

    monkeypatch.setattr(os.path, "exists", mock_exists)

    mock_yaml = "technology_radar:\n  hold:\n    - React\n    - MongoDB"
    _real_open = open

    def mock_open(*args, **kwargs):
        if "tech-radar.yaml" in args[0]:
            return StringIO(mock_yaml)
        return _real_open(*args, **kwargs)

    monkeypatch.setattr("builtins.open", mock_open)

    v = make_validator(
        content="We use React for the frontend",
        doc_meta={"id": "SAD-001", "technologies": [{"name": "React"}]},
    )
    v.doc_type_name = "SAD"
    gr._validate_technologies_whitelist(v)
    assert any("React" in e[1] for e in v.errors)

    def crash_open(*args, **kwargs):
        raise ValueError("mock crash")

    monkeypatch.setattr("builtins.open", crash_open)
    v2 = make_validator(
        content="We use React for the frontend",
        doc_meta={"id": "SAD-001", "technologies": [{"name": "Crash"}]},
    )
    v2.doc_type_name = "SAD"
    gr._validate_technologies_whitelist(v2)
    assert len(v2.errors) == 1
    assert v2.errors[0][0] == "CRITICAL"
    assert "policy source is unreadable" in v2.errors[0][1]

    v3 = make_validator(
        doc_meta={"technologies": [{"name": "React"}]},
    )
    v3.doc_type_name = "GDC"
    gr._validate_technologies_whitelist(v3)
    assert len(v3.errors) == 0


def test_compliance_placement_macro_dir():
    rules = {"structure_rules": {"standard_directory": {"SAD": "systems"}}}
    v_valid = make_validator(
        rules=rules,
        file_path="/home/repo/systems/scnehaux-ui-platform/SAD-003.sad.md",
        filename="SAD-003.sad.md",
        doc_meta={"id": "SAD-003"},
    )
    v_valid.doc_type_name = "SAD"
    _validate_compliance_placement(v_valid)
    assert len(v_valid.errors) == 0

    v_invalid = make_validator(
        rules=rules,
        file_path="/home/repo/domains/scnehaux-ui-platform/SAD-003.sad.md",
        filename="SAD-003.sad.md",
        doc_meta={"id": "SAD-003"},
    )
    v_invalid.doc_type_name = "SAD"
    _validate_compliance_placement(v_invalid)
    assert len(v_invalid.errors) == 1
    assert (
        "must be located within the 'systems/' macro-directory"
        in v_invalid.errors[0][1]
    )


def test_compliance_placement_filename_match():
    v_valid = make_validator(
        file_path="/home/repo/systems/scnehaux-ui-platform/SAD-003-design-tokens.sad.md",
        filename="SAD-003-design-tokens.sad.md",
        doc_meta={"id": "SAD-003"},
    )
    v_valid.doc_type_name = "SAD"
    _validate_compliance_placement(v_valid)
    assert len(v_valid.errors) == 0

    v_invalid = make_validator(
        file_path="/home/repo/systems/scnehaux-ui-platform/design-tokens.md",
        filename="design-tokens.md",
        doc_meta={"id": "SAD-003"},
    )
    v_invalid.doc_type_name = "SAD"
    _validate_compliance_placement(v_invalid)
    assert len(v_invalid.errors) == 1
    assert "must start with the document ID 'SAD-003'" in v_invalid.errors[0][1]


def test_temporal_integrity_is_wired_into_common_validation(monkeypatch):
    v = make_validator(
        doc_meta={
            "id": "GDC-999",
            "created_date": "2030-01-01",
        }
    )
    v.doc_type_name = "GDC"
    monkeypatch.setenv("SCNEHAUX_EVALUATION_DATE", "2026-08-29")

    _validate_temporal_integrity(v)

    assert any(
        severity == "ERROR" and "future" in message for severity, message in v.errors
    )
