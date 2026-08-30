from __future__ import annotations

import logging
import os
import sys
from typing import Any, cast

from engine.control.config.constants import GOVERNANCE_ROOT
from engine.control.config.loader import load_json_schema_file
from engine.control.config.severity import SeverityRule
from engine.control.governance.lifecycle import RELAXED, validation_profile
from engine.control.parsing.markdown_ast import parse_frontmatter
from engine.control.reporting.reporter import print_errors
from engine.control.validators.metadata_rules import validate_lifecycle_age
from engine.control.validators.registry import detect_doc_type, get_validator

logger = logging.getLogger(__name__)

def _disable_info(validator: Any) -> dict:
    """
    Capture the state of any `lint_disable` governance directives from the validator.

    This includes rules that the author successfully disabled (along with their justification)
    and CRITICAL rules that the author attempted to disable but were rejected by the engine.

    <pre>Args:
        - validator (Any): The instantiated validator object containing tracked disable directives.

    Returns:
        dict: A dictionary containing 'disabled' (a list of tuples: (rule_id, reason, start_line, end_line))
              and 'rejected' (set of rules that could not be silenced).
    </pre>
    """
    disabled_list = []
    for rule_id, blocks in validator.block_disables.items():
        for start_line, end_line, reason in blocks:
            disabled_list.append((rule_id, reason, start_line, end_line))

    return {
        "disabled": disabled_list,
        "rejected": set(getattr(validator, "rejected_disables", set())),
    }


def lint_file(
    file_path: str,
    global_rules: dict,
    severity_levels: dict,
    blocking_severities: tuple,
    all_doc_ids: set,
    all_doc_metadata: dict,
    output_format: str = "text",
) -> tuple[list[tuple[str, str]], bool, bool, dict]:
    """
    Orchestrate validation for a single markdown file.
    This executes the core lifecycle: Read -> Parse Metadata -> Identify Type -> Validate.

    <pre>Args:
        - file_path (str): The path to the markdown file being linted.
        - global_rules (dict): Global governance schema containing severity configurations.
        - severity_levels (dict): Pre-extracted and validated severity mappings.
        - blocking_severities (tuple): Pre-extracted, immutable tuple of blocking severities.
        - all_doc_ids (set): A set of all known document IDs across the repository.
        - all_doc_metadata (dict): Metadata mapping for cross-reference checks.
        - output_format (str, optional): Desired output format (text, json, sarif). Defaults to "text".

    Returns:
        tuple: (errors, is_clean, has_blocking, disable_info)
            - errors (list): Found violations.
            - is_clean (bool): True if no errors were found.
            - has_blocking (bool): True if blocking violations were detected.
            - disable_info (dict): Captured `lint_disable` directives.
    </pre>
    """
    # @flow-lint: StartLint(("2. Start Document Validation")) --> Read[2.1. Read raw markdown]
    filename = os.path.basename(file_path)

    # Step 1: Read the raw markdown content
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        # @flow-lint: Read -->|Exception| RecordErrUnreadable["<code>Record Error</code>: Unreadable Artifact"]
        # @flow-lint: RecordErrUnreadable --> Return
        file_errors, is_clean, is_blocking = print_errors(
            file_path,
            [
                (
                    severity_levels[SeverityRule.UNREADABLE_ARTIFACT],
                    f"Failed to read file: {e}",
                )
            ],
            output_format,
            blocking_severities,
        )
        return file_errors, is_clean, is_blocking, {"disabled": {}, "rejected": set()}

    # Step 2: Parse the YAML Frontmatter to extract document metadata
    # @flow-lint: Read --> ParseFM["2.2. <b>markdown_ast.py - parse_frontmatter()</b>: Extract and parse YAML metadata block"]
    doc_meta, meta_err = parse_frontmatter(content)
    if meta_err:
        # @flow-lint: ParseFM -->|Parse Error| RecordErrFM["<code>Record Error</code>: Corrupt Frontmatter"]
        # @flow-lint: RecordErrFM --> Return
        # Fatal syntax error in frontmatter means we cannot even determine doc type
        file_errors, is_clean, is_blocking = print_errors(
            file_path,
            [(severity_levels[SeverityRule.CORRUPT_FRONTMATTER], meta_err)],
            output_format,
            blocking_severities,
        )
        return file_errors, is_clean, is_blocking, {"disabled": {}, "rejected": set()}

    # @flow-lint: ParseFM -->|Yes| CheckExempt{"2.3. Is document exempt?"}
    # @flow-lint: CheckExempt -->|Yes| ValidateExemptAge["2.4. <b>metadata_rules.py - validate_lifecycle_age()</b>: Validate exempt duration"]
    # @flow-lint: CheckExempt -->|No| DetectType["2.6. <b>registry.py - detect_doc_type()</b>: Detect document type"]


    # Step 3: Detect document type before selecting a validation profile.
    # Lifecycle state, validation strictness, and admission authority are separate concerns.
    doc_meta = cast(dict, doc_meta)
    meta_id = doc_meta.get("id")
    doc_type = detect_doc_type(meta_id, global_rules)

    if not doc_type:
        file_errors, is_clean, is_blocking = print_errors(
            file_path,
            [
                (
                    severity_levels[SeverityRule.UNKNOWN_DOCUMENT_TYPE],
                    f"Unknown doc type for '{filename}'. Missing or invalid metadata ID. Hard blocking.",
                )
            ],
            output_format,
            blocking_severities,
        )
        return file_errors, is_clean, is_blocking, {"disabled": {}, "rejected": set()}

    doc_status = str(doc_meta.get("status", "")).lower()
    lifecycle_age_errors = validate_lifecycle_age(
        doc_meta,
        doc_type,
        doc_status,
        severity_levels[SeverityRule.LIFECYCLE_AGE_VIOLATION],
    )

    profile = validation_profile(doc_type, doc_status)
    if profile == RELAXED:
        if lifecycle_age_errors:
            file_errors, is_clean, is_blocking = print_errors(
                file_path,
                lifecycle_age_errors,
                output_format,
                blocking_severities,
            )
            return (
                file_errors,
                is_clean,
                is_blocking,
                {"disabled": {}, "rejected": set()},
            )

        file_errors, is_clean, is_blocking = print_errors(
            file_path,
            [
                (
                    severity_levels[SeverityRule.RELAXED_VALIDATION_APPLIED],
                    f"Relaxed validation profile applied to '{doc_type}' "
                    f"with lifecycle status '{doc_status}'.",
                )
            ],
            output_format,
            blocking_severities,
        )
        return file_errors, is_clean, is_blocking, {"disabled": {}, "rejected": set()}

    # Step 5: Retrieve the specific domain validator for this document type
    validator_cls = get_validator(doc_type)
    # @flow-lint: IsDocType -->|Yes| GetValidator["2.8. <b>registry.py - get_validator()</b>: Get specific domain validator"]
    # @flow-lint: GetValidator --> IsVal{"2.9. Validator exists?"}
    if not validator_cls:
        # @flow-lint: IsVal -->|No| RecordErrMissingVal["<code>Record Error</code>: Missing Validator"]
        # @flow-lint: RecordErrMissingVal --> Return
        file_errors, is_clean, is_blocking = print_errors(
            file_path,
            [
                (
                    severity_levels[SeverityRule.MISSING_VALIDATOR],
                    f"No validator implemented for doc type '{doc_type}'. Hard blocking.",
                )
            ],
            output_format,
            blocking_severities,
        )
        return file_errors, is_clean, is_blocking, {"disabled": {}, "rejected": set()}

    # Step 6: Load the specific JSON schema for this document type
    domain_schema_path = os.path.join(
        GOVERNANCE_ROOT, "00-governance", "schemas", f"{doc_type.lower()}.schema.json"
    )
    # @flow-lint: IsVal -->|Yes| LoadSchemaType["2.10. <b>loader.py - load_json_schema_file()</b>: Load specific domainJSON schema"]
    # @flow-lint: LoadSchemaType --> IsSchema{"2.11. Schema exists?"}

    try:
        domain_schema = load_json_schema_file(domain_schema_path)
    except (FileNotFoundError, ValueError) as e:
        # @flow-lint: IsSchema -->|No| ExitFailSchema((sys.exit 1))
        logger.error("FATAL: %s", str(e))
        sys.exit(1)

    # Step 7: Initialize the specific validator and execute validation
    # @flow-lint: IsSchema -->|Yes| Execute(("2.12. <b>base.py - validate()</b>: Initialize & Run validator engine"))
    validator = validator_cls(
        file_path,
        content,
        doc_meta or {},
        global_rules,
        domain_schema,
        all_doc_ids,
        all_doc_metadata,
        severity_levels,
        blocking_severities,
    )
    errors = lifecycle_age_errors + validator.validate()
    # @flow-lint: Execute --> Return[2.13. Return list of errors]

    file_errors, is_clean, is_blocking = print_errors(
        file_path, errors, output_format, blocking_severities
    )
    return file_errors, is_clean, is_blocking, _disable_info(validator)
