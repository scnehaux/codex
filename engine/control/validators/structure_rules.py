import re
import os
from urllib.parse import unquote
from .base import BaseValidator
from engine.control.parsing.markdown_ast import (
    extract_section_contents,
    clean_content_for_length,
    extract_links,
    extract_doc_id_references,
)

# Reserved example / placeholder namespace. IDs carrying one of these segments are
# illustrative citations inside guideline documents (e.g. 'ADR-EXAMPLE-001') and
# must NOT be resolved against the live registry.
_EXAMPLE_ID_PATTERN = re.compile(
    r"-(?:EXAMPLE|SAMPLE|XXX+|NNN+|YYYY|000)\b", re.IGNORECASE
)


def _is_example_id(ref: str) -> bool:
    """True if the referenced ID belongs to the reserved example/placeholder namespace."""
    return bool(_EXAMPLE_ID_PATTERN.search(ref))


def _validate_structure(v: BaseValidator) -> None:
    """Validate the document structural integrity, including checking minimum section content lengths."""
    sections_map = extract_section_contents(v.content)

    # Length checks
    rules_structure = v.global_rules.get("content_rules", {})
    rule_config = rules_structure.get("min_content_length_chars", {})
    min_length = int(rule_config.get("value", 50))

    for section_name, section_text in sections_map.items():
        clean_text = clean_content_for_length(section_text)
        if len(clean_text) < min_length:
            error_msg = rule_config.get(
                "error_message",
                "Section '{section_name}' content length ({length} chars) is below minimum of {min_length} chars.",
            ).format(
                section_name=section_name, length=len(clean_text), min_length=min_length
            )

            v.add_error(
                "stylistic_deviation",
                error_msg,
            )


def _validate_internal_links(v: BaseValidator) -> None:
    """Verify that all internal markdown links resolve to existing files in the repository to prevent link rot."""
    links = extract_links(v.content)
    base_dir = os.path.dirname(v.file_path)

    for link in links:
        # Ignore external links, mailto, and fragment-only links
        if (
            not link
            or link.startswith("http")
            or link.startswith("mailto:")
            or link.startswith("#")
        ):
            continue

        link = unquote(link)

        # Strip fragment identifier if present for file existence check
        file_part = link.split("#")[0]
        if not file_part:
            continue

        # Check if local file exists
        target_path = os.path.normpath(os.path.join(base_dir, file_part))
        if not os.path.exists(target_path):
            v.add_error(
                "broken_internal_link",
                f"Link rot detected: Internal link '{link}' points to a non-existent file.",
            )


def _validate_inline_references(v: BaseValidator) -> None:
    """
    Detect architecture document IDs cited inline in prose (e.g. '(**ADR-018**)')
    that do not resolve to any document in this repository. Reported as a
    non-blocking WARNING because a citation may legitimately point at an external
    or downstream document not present in this registry.
    """
    own_id = (v.doc_meta or {}).get("id")
    for ref in extract_doc_id_references(v.content):
        if ref == own_id:
            continue
        if _is_example_id(ref):
            # Illustrative citation in a guideline (reserved example namespace).
            continue
        if ref not in v.all_doc_ids:
            v.add_error(
                "inline_reference_missing",
                f"Inline reference to '{ref}' does not resolve to any document in this repository "
                "(possible typo, renamed ID, or an external/downstream document).",
            )


def _validate_nfr_taxonomy(v: BaseValidator) -> None:
    """
    Ensure NFRs strictly map to AWS WAF pillars (GDC-000 Section 2.4).
    """
    sections_map = extract_section_contents(v.content)
    specific_config = v.domain_schema.get("x-global-config", {})
    rules_structure = specific_config
    aws_waf_pillars = rules_structure.get("quantification_pillars", [])

    if not aws_waf_pillars:
        return

    for section_name, section_text in sections_map.items():
        if "non-functional requirements" in section_name.lower():
            # Find all ### headers in this section
            sub_headers = re.findall(r"^###\s+(.*)$", section_text, flags=re.MULTILINE)

            if not sub_headers:
                v.add_error(
                    "nfr_taxonomy_violation",
                    f"NFR taxonomy violation: Section '{section_name}' is unstructured. It must be categorized using AWS WAF Pillars as '###' sub-headers.",
                )
                continue

            for header in sub_headers:
                clean_header = header.strip()
                # Check if it matches any AWS WAF Pillar (case insensitive)
                matched = any(
                    clean_header.lower() == p.lower() for p in aws_waf_pillars
                )
                if not matched:
                    v.add_error(
                        "nfr_taxonomy_violation",
                        f"NFR taxonomy violation: Sub-header '{clean_header}' under '{section_name}' is not an approved AWS WAF Pillar.",
                    )
