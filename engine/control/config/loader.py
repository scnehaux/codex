import json
import logging

from .constants import (
    SCHEMA_KEY_STRUCTURE_RULES,
    SCHEMA_KEY_ARTIFACT_DIRS,
    SCHEMA_KEY_IGNORED_FILES,
    SCHEMA_KEY_MAX_DIR_DEPTH,
    SCHEMA_KEY_CONTENT_RULES,
    SCHEMA_KEY_MIN_CONTENT_LENGTH,
    SCHEMA_KEY_MAX_REVIEW_AGE,
)
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


def validate_global_config_structure(global_rules: dict) -> None:
    """
    Validates that the global governance rules configuration contains all required nested keys.
    Prevents silent failures when schema keys are accidentally deleted.

    <pre>Args:
        - global_rules (dict): The x-global-config dictionary from base.schema.json.

    Returns:
        None

    Raises:
        RuntimeError: If a required top-level or sub-level configuration key is missing.
    </pre>
    """
    required_structure = {
        SCHEMA_KEY_STRUCTURE_RULES: [
            SCHEMA_KEY_ARTIFACT_DIRS,
            SCHEMA_KEY_IGNORED_FILES,
            SCHEMA_KEY_MAX_DIR_DEPTH,
        ],
        SCHEMA_KEY_CONTENT_RULES: [
            SCHEMA_KEY_MIN_CONTENT_LENGTH,
            SCHEMA_KEY_MAX_REVIEW_AGE,
        ],
    }

    for top_key, sub_keys in required_structure.items():
        if top_key not in global_rules:
            raise RuntimeError(
                f"Missing top-level configuration '{top_key}' in x-global-config"
            )

        top_config = global_rules[top_key]
        for sub_key in sub_keys:
            if sub_key not in top_config:
                raise RuntimeError(
                    f"Missing required configuration '{sub_key}' under '{top_key}'"
                )


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


def parse_and_validate_global_config(base_schema: dict) -> tuple[dict, dict, tuple]:
    """
    Extracts and strictly validates the global configuration from the raw JSON schema.
    This centralized DRY function ensures both production (cli.py) and testing (conftest.py)
    follow identical parsing and validation paths for global governance rules.

    <pre>Args:
        - base_schema (dict): The raw, unparsed JSON schema loaded from base.schema.json.

    Returns:
        tuple: (global_rules, flattened_severity_levels, blocking_severities)

    Raises:
        RuntimeError: If the configuration is missing or structurally invalid.
    </pre>
    """
    from .constants import (
        SCHEMA_KEY_GLOBAL_CONFIG,
        SCHEMA_KEY_SEVERITY_LEVELS,
        SCHEMA_KEY_BLOCKING_SEVERITIES,
    )

    global_rules = base_schema.get(SCHEMA_KEY_GLOBAL_CONFIG)
    if not global_rules:
        raise RuntimeError(
            f"FATAL: Missing '{SCHEMA_KEY_GLOBAL_CONFIG}' in base schema."
        )

    raw_severity_levels = global_rules.get(SCHEMA_KEY_SEVERITY_LEVELS, {})
    severity_levels = {
        code: level
        for group, config in raw_severity_levels.items()
        for code, level in config.items()
    }
    if not severity_levels:
        raise RuntimeError(
            f"FATAL: Missing '{SCHEMA_KEY_SEVERITY_LEVELS}' in base schema."
        )

    # Overwrite the nested dictionary with flattened version for O(1) lookups
    global_rules[SCHEMA_KEY_SEVERITY_LEVELS] = severity_levels

    blocking_severities = global_rules.get(SCHEMA_KEY_BLOCKING_SEVERITIES)
    if not blocking_severities:
        raise RuntimeError(
            f"FATAL: Missing '{SCHEMA_KEY_BLOCKING_SEVERITIES}' in base schema."
        )

    blocking_severities_tuple = tuple(blocking_severities)

    # Perform strict architectural validations
    validate_global_config_structure(global_rules)
    validate_severity_schema(severity_levels)
    validate_blocking_severities(blocking_severities_tuple)

    return global_rules, severity_levels, blocking_severities_tuple
