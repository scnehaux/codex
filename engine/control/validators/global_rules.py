import re
import logging
from .base import BaseValidator
from engine.control.governance.classification import repository_classification_findings
from engine.control.governance.temporal import temporal_integrity_findings
from engine.control.parsing.markdown_ast import (
    strip_code_fences,
)
from .metadata_rules import (
    _validate_review_age,
    _validate_approved_version_stability,
    _validate_cross_references,
    _validate_technologies_whitelist,
)
from .structure_rules import (
    _validate_structure,
    _validate_nfr_taxonomy,
    _validate_internal_links,
    _validate_inline_references,
)

logger = logging.getLogger(__name__)


def run_common_validations(validator: BaseValidator) -> None:
    """
    Execute the suite of global governance rules (e.g. naming, review age, NFR taxonomy,
    traceability) that apply universally across all architecture document types.
    """
    # @flow-validator: subgraph GlobalRulesPhase[Global Rules Validation Suite]
    # @flow-validator: direction TB

    # @flow-validator: GlobalRules --> ValCompliance["<b>_validate_compliance_placement()</b>: Check folder placement & file naming"]
    _validate_compliance_placement(validator)
    # @flow-validator: ValCompliance --> ValRevAge["<b>_validate_review_age()</b>: Check if document is expired"]
    _validate_repository_classification(validator)
    _validate_temporal_integrity(validator)
    _validate_review_age(validator)
    # @flow-validator: ValRevAge --> ValVerStab["<b>_validate_approved_version_stability()</b>: Check baseline status carries a stable version"]
    _validate_approved_version_stability(validator)
    # @flow-validator: ValVerStab --> ValContent["<b>_validate_content_quality()</b>: Check for prohibited words & vague claims"]
    _validate_content_quality(validator)
    # @flow-validator: ValContent --> ValStruct["<b>_validate_structure()</b>: Check minimum section lengths"]
    _validate_structure(validator)
    # @flow-validator: ValStruct --> ValCross["<b>_validate_cross_references()</b>: Check validity of related document IDs"]
    _validate_cross_references(validator)
    # @flow-validator: ValCross --> ValInternal["<b>_validate_internal_links()</b>: Check for broken markdown links"]
    _validate_internal_links(validator)
    # @flow-validator: ValInternal --> ValInline["<b>_validate_inline_references()</b>: Detect inline document ID mentions"]
    _validate_inline_references(validator)
    # @flow-validator: ValInline --> ValNFR["<b>_validate_nfr_taxonomy()</b>: Ensure NFRs follow AWS WAF pillars"]
    _validate_nfr_taxonomy(validator)
    # @flow-validator: ValNFR --> ValTech["<b>_validate_technologies_whitelist()</b>: Check for prohibited technologies"]
    _validate_technologies_whitelist(validator)
    # @flow-validator: end


def _validate_compliance_placement(v: BaseValidator) -> None:
    """
    Validate that the document is placed in the correct macro-directory
    and that the filename starts with the metadata ID.
    """
    doc_type = v.doc_type_name
    file_path = v.file_path.replace("\\", "/")
    filename = v.filename
    doc_id = (v.doc_meta or {}).get("id", "")

    # 1. Macro-Directory check
    macro_dir_map = v.global_rules.get("structure_rules", {}).get(
        "standard_directory", {}
    )
    expected_dir = macro_dir_map.get(doc_type)
    if expected_dir:
        # We check if the expected directory is part of the absolute path.
        # This is a simple structural enforcement (e.g. /systems/)
        if f"/{expected_dir}/" not in file_path:
            v.add_error(
                "compliance_macro_directory",
                f"Document of type '{doc_type}' must be located within the '{expected_dir}/' macro-directory.",
            )

    # 2. Filename identity check
    if doc_id:
        if (
            not filename.endswith(".sad.md")
            and not filename.endswith(".pad.md")
            and not filename.startswith(doc_id)
        ):
            v.add_error(
                "compliance_filename_match",
                f"Filename '{filename}' must start with the document ID '{doc_id}'.",
            )


def _validate_content_quality(v: BaseValidator) -> None:
    """Ensure the content avoids prohibited boilerplate words and vague claims based on the governance constraints."""
    # Strip fences and frontmatter but preserve line numbers
    text_content = strip_code_fences(v.content)

    def replacer(m):
        return "\n" * m.group(0).count("\n")

    text_content = re.sub(r"^---\s+.*?\s+---", replacer, text_content, flags=re.DOTALL)

    rules_content = v.global_rules
    content_rules = rules_content.get("content_rules", {})

    for rule_id, rule_config in content_rules.items():
        if not isinstance(rule_config, dict):
            continue
        patterns = rule_config.get("patterns")
        if not patterns:
            continue

        message = rule_config.get(
            "error_message", f"Content rule '{rule_id}' violated."
        )

        for pattern in patterns:
            for match in re.finditer(pattern, text_content, re.IGNORECASE):
                line_num = text_content.count("\n", 0, match.start()) + 1
                v.add_error(rule_id, message, line_num=line_num)


def _validate_temporal_integrity(v: BaseValidator) -> None:
    """Enforce future-date and temporal-ordering invariants."""
    for message in temporal_integrity_findings(v.doc_meta):
        v.add_error("temporal_integrity_violation", message)


def _validate_repository_classification(v: BaseValidator) -> None:
    """Enforce repository visibility as the real classification storage boundary."""
    for rule_id, message in repository_classification_findings(v.doc_meta):
        v.add_error(rule_id, message)
