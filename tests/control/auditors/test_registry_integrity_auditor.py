from tests.support.repository import REPOSITORY_ROOT
import json
from pathlib import Path

import pytest

from engine.control.auditors.registry_integrity_auditor import (
    _artifact_schema_map,
    _control_findings,
    _custom_keyword_findings,
    _duplicate_validator_keys,
    _evidence_path_exists,
    _resolve_pointer,
    _schema_files,
    _schema_ref_findings,
    _severity_findings,
    _target_doc_findings,
    _validator_findings,
    assert_registry_integrity,
    audit_registry_integrity,
)
from engine.control.config.loader import parse_and_validate_global_config


ROOT = REPOSITORY_ROOT
SCHEMA_DIR = ROOT / "00-governance" / "schemas"


def _base_schema():
    return json.loads(
        (SCHEMA_DIR / "base.schema.json").read_text(encoding="utf-8")
    )


def _severity_levels():
    _, severity_levels, _ = parse_and_validate_global_config(_base_schema())
    return severity_levels


def test_structural_registry_integrity_before_severity_reconciliation():
    findings = audit_registry_integrity(ROOT, _severity_levels())
    assert not [
        finding
        for finding in findings
        if not finding.startswith("F09 ")
    ]


def test_assert_registry_integrity_raises_with_preview(monkeypatch):
    monkeypatch.setattr(
        'engine.control.auditors.registry_integrity_auditor.audit_registry_integrity',
        lambda *_: ("F01 broken", "F02 broken"),
    )
    with pytest.raises(RuntimeError, match="F01 broken"):
        assert_registry_integrity(ROOT, _severity_levels())


def test_schema_files_fail_closed_on_invalid_json(tmp_path):
    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir()
    (schema_dir / "bad.schema.json").write_text("{", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        _schema_files(schema_dir)


def test_schema_ref_findings_detect_missing_document_and_pointer(tmp_path):
    base = tmp_path / "base.schema.json"
    child = tmp_path / "child.schema.json"
    schemas = {
        base: {
            "$id": "https://example/base.schema.json",
            "definitions": {"ok": {"type": "string"}},
        },
        child: {
            "$id": "https://example/child.schema.json",
            "allOf": [
                {"$ref": "https://example/missing.schema.json#/x"},
                {"$ref": "https://example/base.schema.json#/definitions/nope"},
            ],
        },
    }
    findings = _schema_ref_findings(schemas)
    assert len(findings) == 2
    assert "unresolved $ref" in findings[0]
    assert "unresolved JSON pointer" in findings[1]


def test_resolve_pointer_handles_dict_list_and_invalid_fragment():
    document = {"a": [{"b/c": {"~key": 1}}]}
    assert _resolve_pointer(document, "/a/0/b~1c/~0key")
    assert not _resolve_pointer(document, "/a/9")
    assert not _resolve_pointer(document, "anchor")
    assert _resolve_pointer(document, "")


def test_duplicate_validator_keys_detected(tmp_path):
    registry = tmp_path / "registry.py"
    registry.write_text(
        'VALIDATOR_REGISTRY = {"EAD": A, "EAD": B, "PAD": C}\n',
        encoding="utf-8",
    )
    assert _duplicate_validator_keys(registry) == ["EAD"]


def test_artifact_schema_map_finds_canonical_types():
    schemas = _schema_files(SCHEMA_DIR)
    mapped = _artifact_schema_map(schemas)
    assert set(mapped) == {"GDC", "EAD", "STD", "PAD", "SAD", "ADR", "TDD"}


def test_validator_findings_detect_missing_schema_surface():
    findings = _validator_findings(ROOT, {})
    assert any("missing artifact schema" in finding for finding in findings)
    assert any("orphan validator registration" in finding for finding in findings)


def test_target_doc_findings_cover_missing_missing_file_and_wrong_guideline(tmp_path):
    governance = tmp_path / "00-governance"
    governance.mkdir()

    missing_config = tmp_path / "ead.schema.json"
    missing_file = tmp_path / "pad.schema.json"
    wrong = tmp_path / "sad.schema.json"

    (governance / "GDC-006-ead-guideline.md").write_text("", encoding="utf-8")

    findings = _target_doc_findings(
        governance,
        {
            "EAD": (missing_config, {}),
            "PAD": (
                missing_file,
                {"config": {"target_doc": "GDC-008-missing.md"}},
            ),
            "SAD": (
                wrong,
                {"config": {"target_doc": "GDC-006-ead-guideline.md"}},
            ),
        },
    )
    assert any("missing config.target_doc" in finding for finding in findings)
    assert any("target_doc does not exist" in finding for finding in findings)
    assert any("must map to GDC-009" in finding for finding in findings)


def test_custom_keyword_findings_accept_draft7_and_registered_annotations(tmp_path):
    path = tmp_path / "x.schema.json"
    findings = _custom_keyword_findings(
        {
            path: {
                "definitions": {
                    "x": {
                        "type": "string",
                        "error_message": "authoring annotation",
                    }
                },
                "if": {"type": "string"},
                "then": {"type": "string"},
                "recommended": ["Security"],
            }
        }
    )
    assert findings == []


def test_custom_keyword_findings_detect_unsupported_keyword(tmp_path):
    path = tmp_path / "x.schema.json"
    findings = _custom_keyword_findings(
        {
            path: {
                "type": "object",
                "properties": {
                    "field": {
                        "type": "string",
                        "totally_custom_keyword": True,
                    }
                },
            }
        }
    )
    assert any("totally_custom_keyword" in finding for finding in findings)


def test_custom_keyword_findings_skip_governance_config_payload(tmp_path):
    path = tmp_path / "x.schema.json"
    findings = _custom_keyword_findings(
        {
            path: {
                "type": "object",
                "x-global-config": {
                    "arbitrary": {"nested": "configuration"},
                },
                "config": {"target_doc": "GDC-001.md"},
            }
        }
    )
    assert findings == []


def test_severity_findings_detect_missing_and_extra_mapping():
    real = _severity_levels()
    missing_key = next(iter(real))
    mutated = dict(real)
    mutated.pop(missing_key)
    mutated["not_a_real_rule"] = "ERROR"

    findings = _severity_findings(
        ROOT / 'engine' / 'control',
        mutated,
        _base_schema(),
    )
    assert any(
        missing_key in finding and "missing schema" in finding
        for finding in findings
    )
    assert any("not_a_real_rule" in finding for finding in findings)


def test_evidence_path_exists_supports_literal_glob_and_pytest_node(tmp_path):
    path = tmp_path / "00-governance" / "schemas"
    path.mkdir(parents=True)
    schema = path / "x.schema.json"
    schema.write_text("{}", encoding="utf-8")

    assert _evidence_path_exists(
        tmp_path,
        "00-governance/schemas/x.schema.json",
    )
    assert _evidence_path_exists(
        tmp_path,
        "00-governance/schemas/*.schema.json",
    )
    assert _evidence_path_exists(
        tmp_path,
        "00-governance/schemas/x.schema.json::test_example",
    )
    assert not _evidence_path_exists(
        tmp_path,
        "00-governance/schemas/missing*.schema.json",
    )


def test_control_findings_has_no_false_positive_for_current_evidence_paths():
    findings = _control_findings(ROOT)
    assert findings == []


def test_audit_fail_closed_on_schema_boot_error(tmp_path):
    schema_dir = tmp_path / "00-governance" / "schemas"
    schema_dir.mkdir(parents=True)
    (schema_dir / "bad.schema.json").write_text("{", encoding="utf-8")

    findings = audit_registry_integrity(tmp_path, {})
    assert len(findings) == 1
    assert findings[0].startswith("F01 schema boot validation failed:")

def test_validator_findings_detect_orphan_schema_and_doc_type_mismatch(
    monkeypatch,
):
    import engine.control.auditors.registry_integrity_auditor as module

    class WrongValidator:
        doc_type_name = "WRONG"

    mutated = dict(module.VALIDATOR_REGISTRY)
    mutated.pop("EAD")
    mutated["PAD"] = WrongValidator
    monkeypatch.setattr(module, "VALIDATOR_REGISTRY", mutated)

    artifact_schemas = {
        "EAD": (Path("ead.schema.json"), {}),
        "PAD": (Path("pad.schema.json"), {}),
        "FAKE": (Path("fake.schema.json"), {}),
    }

    findings = module._validator_findings(ROOT, artifact_schemas)
    assert any("F04 FAKE: orphan artifact schema" in item for item in findings)
    assert any("F06 PAD: validator doc_type_name mismatch" in item for item in findings)


def test_custom_keyword_walker_covers_items_list_dependencies_and_annotations(
    tmp_path,
):
    path = tmp_path / "complex.schema.json"
    findings = _custom_keyword_findings(
        {
            path: {
                "type": "array",
                "recommended": ["Security"],
                "items": [
                    {"type": "string"},
                    {"type": "object", "properties": {"x": {"type": "integer"}}},
                ],
                "dependencies": {
                    "x": {
                        "properties": {
                            "y": {"type": "string", "error_message": "annotation"}
                        }
                    }
                },
            }
        }
    )
    assert findings == []


def test_schema_ref_findings_detect_local_pointer_failure(tmp_path):
    schema = tmp_path / "local.schema.json"
    findings = _schema_ref_findings(
        {
            schema: {
                "$id": "https://example/local.schema.json",
                "definitions": {"ok": {"type": "string"}},
                "allOf": [{"$ref": "#/definitions/missing"}],
            }
        }
    )
    assert len(findings) == 1
    assert "unresolved JSON pointer" in findings[0]


def test_assert_registry_integrity_truncates_long_failure_preview(monkeypatch):
    monkeypatch.setattr(
        'engine.control.auditors.registry_integrity_auditor.audit_registry_integrity',
        lambda *_: tuple(f"F09 finding-{index}" for index in range(21)),
    )
    with pytest.raises(RuntimeError) as exc:
        assert_registry_integrity(ROOT, _severity_levels())

    message = str(exc.value)
    assert "finding-19" in message
    assert "finding-20" not in message
    assert "... +1 more" in message
