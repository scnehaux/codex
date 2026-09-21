from engine.control.validators.registry import detect_doc_type, get_validator
from engine.control.validators.domains.adr_validator import ADRValidator
from engine.control.validators.domains.sad_validator import SADValidator


def test_detect_doc_type_uses_declarative_vocabulary_not_schema_projection():
    contradictory_rules = {
        "structure_rules": {
            "artifact_directories": {
                "FAKE": "fake",
            }
        }
    }

    assert detect_doc_type("ADR-001", contradictory_rules) == "ADR"
    assert detect_doc_type("SAD-999", contradictory_rules) == "SAD"
    assert detect_doc_type("PAD-XYZ", contradictory_rules) == "PAD"
    assert detect_doc_type("GDC-002", contradictory_rules) == "GDC"
    assert detect_doc_type("FAKE-001", contradictory_rules) is None
    assert detect_doc_type(None, contradictory_rules) is None
    assert detect_doc_type("", contradictory_rules) is None


def test_detect_doc_type_keeps_compatibility_argument_optional():
    assert detect_doc_type("TDD-001") == "TDD"


def test_get_validator_is_declarative_binding_projection():
    assert get_validator("ADR") == ADRValidator
    assert get_validator("SAD") == SADValidator
    assert get_validator("adr") == ADRValidator
    assert get_validator("UNKNOWN") is None
