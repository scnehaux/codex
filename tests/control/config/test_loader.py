import pytest
from unittest.mock import patch, mock_open
from engine.control.config.loader import load_json_schema_file


def test_load_json_schema_file_success():
    """
    Validates that a valid JSON schema file is successfully parsed.
    Mocks the file system read operation to return a predefined JSON structure.
    """
    mock_json = '{"type": "object", "properties": {"id": {"type": "string"}}}'
    with patch("builtins.open", mock_open(read_data=mock_json)):
        result = load_json_schema_file("fake_schema.json")

    assert result == {"type": "object", "properties": {"id": {"type": "string"}}}


@patch('engine.control.config.loader.logger.critical')
def test_load_json_schema_file_not_found(mock_logger_critical):
    """
    Validates the behavior when a schema file is missing.
    Ensures that a FileNotFoundError is properly raised.
    """
    with patch("builtins.open", side_effect=FileNotFoundError):
        with pytest.raises(FileNotFoundError):
            load_json_schema_file("missing_schema.json")


def test_validate_severity_schema_unknown_rule():
    from engine.control.config.loader import validate_severity_schema
    from engine.control.config.severity import SeverityRule

    full_levels = {r.value: "ERROR" for r in SeverityRule}
    full_levels["unknown_rule_xyz"] = "HIGH"
    with pytest.raises(RuntimeError) as exc:
        validate_severity_schema(full_levels)
    assert "Unknown severity rules found" in str(exc.value)


def test_validate_blocking_severities_missing_and_unknown():
    from engine.control.config.loader import validate_blocking_severities

    # Missing required blocking severity
    with pytest.raises(RuntimeError) as exc1:
        validate_blocking_severities(["CRITICAL"])
    assert "Missing blocking severities" in str(exc1.value)

    # Unknown blocking severity
    with pytest.raises(RuntimeError) as exc2:
        validate_blocking_severities(["CRITICAL", "ERROR", "UNKNOWN_SEV"])
    assert "Unknown blocking severities" in str(exc2.value)

def test_load_json_schema_file_invalid_json(tmp_path):
    import pytest
    from engine.control.config.loader import load_json_schema_file

    bad = tmp_path / "bad.json"
    bad.write_text("{not-json", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSON"):
        load_json_schema_file(str(bad))


def test_validate_global_config_structure_missing_top_level():
    import pytest
    from engine.control.config.loader import validate_global_config_structure

    with pytest.raises(RuntimeError, match="Missing top-level configuration"):
        validate_global_config_structure({})


def test_validate_global_config_structure_missing_subkey():
    import pytest
    from engine.control.config.loader import validate_global_config_structure
    from engine.control.config.constants import (
        SCHEMA_KEY_STRUCTURE_RULES,
        SCHEMA_KEY_CONTENT_RULES,
        SCHEMA_KEY_ARTIFACT_DIRS,
        SCHEMA_KEY_IGNORED_FILES,
        SCHEMA_KEY_MIN_CONTENT_LENGTH,
        SCHEMA_KEY_MAX_REVIEW_AGE,
    )

    cfg = {
        SCHEMA_KEY_STRUCTURE_RULES: {
            SCHEMA_KEY_ARTIFACT_DIRS: {},
            SCHEMA_KEY_IGNORED_FILES: {},
        },
        SCHEMA_KEY_CONTENT_RULES: {
            SCHEMA_KEY_MIN_CONTENT_LENGTH: {},
            SCHEMA_KEY_MAX_REVIEW_AGE: {},
        },
    }
    with pytest.raises(RuntimeError, match="Missing required configuration"):
        validate_global_config_structure(cfg)
