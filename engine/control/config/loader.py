import json
import logging

from .severity import SeverityRule, BlockingSeverity

logger = logging.getLogger(__name__)


def load_json_schema_file(schema_path: str) -> dict:
    """
    Loads and parses a JSON schema file for the validation engine.
    Enforces a hard crash (exit code 1) if the mandatory schema file is missing.

    <pre>Args:
        - schema_path (str): File path to the JSON schema.

    Returns:
        dict: Parsed JSON schema.

    Raises:
        FileNotFoundError: If the schema file is not found.
    </pre>
    """
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Schema file '{schema_path}' not found.")
    except json.JSONDecodeError as e:
        raise ValueError(f"Schema file '{schema_path}' contains invalid JSON: {e}")


def validate_severity_schema(schema_levels: dict) -> None:
    """
    Validates that the provided schema severity levels comprehensively map
    every SeverityRule defined in the system. Ensures no configuration drift.

    <pre>Args:
        - schema_levels (dict): Dictionary mapping rule strings to severity strings.

    Returns:
        None

    Raises:
        RuntimeError: If a rule is missing or unrecognized.
    </pre>
    """
    defined_rules = {rule.value for rule in SeverityRule}
    schema_rules = set(schema_levels.keys())

    missing = defined_rules - schema_rules
    if missing:
        raise RuntimeError(
            f"Missing severity levels in base.schema.json for rules: {missing}"
        )

    unknown = schema_rules - defined_rules
    if unknown:
        raise RuntimeError(
            f"Unknown severity rules found in base.schema.json (typo or deprecated?): {unknown}"
        )


def validate_blocking_severities(schema_blocking: list | tuple) -> None:
    """
    Validates that the provided schema blocking severities comprehensively map
    every BlockingSeverity defined in the system. Ensures no configuration drift.

    <pre>Args:
        - schema_blocking (list): List of blocking severity strings from base.schema.json.

    Returns:
        None

    Raises:
        RuntimeError: If a severity is missing or unrecognized.
    </pre>
    """
    defined_blocking = {sev.value for sev in BlockingSeverity}
    schema_blocking_set = set(schema_blocking)

    missing = defined_blocking - schema_blocking_set
    if missing:
        raise RuntimeError(
            f"Missing blocking severities in base.schema.json: {missing}"
        )

    unknown = schema_blocking_set - defined_blocking
    if unknown:
        raise RuntimeError(
            f"Unknown blocking severities found in base.schema.json (typo or deprecated?): {unknown}"
        )
