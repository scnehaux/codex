from engine.control.validators.registry import detect_doc_type, get_validator
from engine.control.validators.domains.adr_validator import ADRValidator
from engine.control.validators.domains.sad_validator import SADValidator


def test_detect_doc_type():
    dummy_rules = {
        "structure_rules": {
            "artifact_directories": {
                "GDC": "governance",
                "PAD": "domains",
                "SAD": "systems",
                "ADR": "decisions",
            }
        }
    }
    # Valid metadata IDs
    assert detect_doc_type("ADR-001", dummy_rules) == "ADR"
    assert detect_doc_type("SAD-999", dummy_rules) == "SAD"
    assert detect_doc_type("PAD-XYZ", dummy_rules) == "PAD"
    assert detect_doc_type("GDC-002", dummy_rules) == "GDC"

    # Invalid or missing metadata IDs should return None
    assert detect_doc_type(None, dummy_rules) is None
    assert detect_doc_type("UNKNOWN-001", dummy_rules) is None
    assert detect_doc_type("", dummy_rules) is None


def test_get_validator():
    assert get_validator("ADR") == ADRValidator
    assert get_validator("SAD") == SADValidator
    assert get_validator("UNKNOWN") is None
