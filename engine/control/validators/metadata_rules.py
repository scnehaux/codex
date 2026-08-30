import os
import yaml
import logging
from .base import BaseValidator
from engine.control.config.constants import (
    SCHEMA_KEY_CONTENT_RULES,
    SCHEMA_KEY_MAX_REVIEW_AGE,
    TECH_RADAR_YAML_PATH,
)
from engine.control.parsing.markdown_ast import parse_date
from engine.control.governance.relationships import (
    normalize_relation_values,
    relationship_fields_for_source,
)
from engine.control.governance.temporal import evaluation_date
from engine.control.governance.lifecycle import (
    is_baseline_bearing,
    lifecycle_age_policy,
)

logger = logging.getLogger(__name__)

# Document types that reference deployable technology surfaces.
_TECHNOLOGY_HOLD_DOC_TYPES = frozenset({"SAD", "TDD"})



def validate_lifecycle_age(
    doc_meta: dict,
    doc_type: str,
    doc_status: str,
    violation_severity: str,
) -> list[tuple[str, str]]:
    """Validate only artifact-aware lifecycle age policies declared in the registry."""
    policy = lifecycle_age_policy(doc_type, doc_status)
    if policy is None:
        return []

    raw_date = doc_meta.get(policy.depend_on)
    if not raw_date:
        return [
            (
                violation_severity,
                f"Document with status '{doc_status}' is missing "
                f"'{policy.depend_on}', which is required for lifecycle age enforcement.",
            )
        ]

    parsed_date = parse_date(raw_date)
    if not parsed_date:
        return []

    age_days = (evaluation_date() - parsed_date).days
    if age_days <= policy.max_age_days:
        return []

    return [
        (
            violation_severity,
            policy.error_message.format(
                doc_status=doc_status,
                age_days=age_days,
                limit=policy.max_age_days,
                depend_on=policy.depend_on,
            ),
        )
    ]


def _validate_review_age(v: BaseValidator) -> None:
    """Check if a document's last review date exceeds the maximum allowed age, triggering a review requirement."""
    if not v.doc_meta:
        return
    last_reviewed_raw = v.doc_meta.get("last_reviewed")
    if last_reviewed_raw:
        last_reviewed = parse_date(last_reviewed_raw)
        if last_reviewed:
            age_days = (evaluation_date() - last_reviewed).days
            cycle_days = v.doc_meta.get("review_cycle_days")
            rules_meta = v.global_rules.get(SCHEMA_KEY_CONTENT_RULES, {})
            rule_config = rules_meta.get(SCHEMA_KEY_MAX_REVIEW_AGE, {})
            default_limit = rule_config.get("value", 365)

            limit = int(cycle_days) if cycle_days is not None else int(default_limit)
            if age_days > limit:
                error_msg = rule_config.get(
                    "error_message",
                    "Document review age of {age_days} days exceeds limit of {limit} days.",
                ).format(age_days=age_days, limit=limit, last_reviewed=last_reviewed)

                v.add_error(
                    "review_age_violation",
                    error_msg,
                )


def _validate_approved_version_stability(v: BaseValidator) -> None:
    """
    Enforce GDC-000 Section 2.6 item 6: a versioned artifact that has reached a baseline
    status MUST carry a stable Semantic Version.

    GDC-000 Section 2.6 item 4 mandates Semantic Versioning, under which major version zero
    means the artifact is in initial development and anything may change at any time. A
    document declaring `approved` -- "approved for implementation", the blueprint other teams
    build against -- while sitting at `0.y.z` therefore says two contradictory things about
    the same artifact, and a reader has no way to know which one to trust.

    The distinction matters at the point where it costs something. A design at 0.4.0 tells an
    implementer that the contract may move underneath their code; a design marked approved
    tells them it will not. Both readings were true of six TDDs in this ecosystem, all six of
    which already had code written against them.

    `chartered`, `draft`, and `proposed` are deliberately not covered: `0.y.z` is exactly the
    right version for an artifact that is recognized or under review but not yet a baseline.
    `deprecated` is covered, because an artifact can only be phased out after having been the
    baseline -- a deprecated document at `0.y.z` never was one.

    Artifacts that carry no `version` are skipped. GDC-000 Section 2.6 item 4 makes ADRs
    immutable snapshots rather than versioned artifacts, so there is nothing here to check.
    """
    if not v.doc_meta:
        return

    raw_version = str(v.doc_meta.get("version", "")).strip()
    if not raw_version:
        return

    status = str(v.doc_meta.get("status", "")).strip().lower()
    if not is_baseline_bearing(v.doc_type_name, status):
        return

    major = raw_version.split(".", 1)[0]
    if major != "0":
        return

    v.add_error(
        "approved_version_not_stable",
        f"Document is '{status}' at version '{raw_version}'. Semantic Versioning reserves "
        f"major version zero for initial development where anything may change, which "
        f"contradicts a baseline status. Promote it to '1.0.0' or move the status back to a "
        f"pre-baseline value.",
    )


def _validate_cross_references(v: BaseValidator) -> None:
    """Verify registry-declared relationship targets exist in the repository."""
    if not v.doc_meta:
        return

    for field in relationship_fields_for_source(v.doc_type_name):
        ref_ids = v.doc_meta.get(field)
        if not ref_ids:
            continue

        for ref_id in normalize_relation_values(ref_ids):
            if ref_id not in v.all_doc_ids:
                v.add_error(
                    "cross_reference_missing",
                    f"Cross-referenced document '{ref_id}' not found in this repository.",
                )


def _validate_technologies_whitelist(v: BaseValidator) -> None:
    """
    Enforce strict whitelist technology validation based on structured metadata.
    Instead of full-text scanning, this rule checks the 'technologies' array in doc_meta.
    Every technology (and its 'base') MUST exist in the Enterprise Tech Radar.
    If it exists but is on HOLD, a violation is thrown.
    """
    if v.doc_type_name not in _TECHNOLOGY_HOLD_DOC_TYPES:
        return

    if not v.doc_meta:
        return

    technologies = v.doc_meta.get("technologies")
    if not technologies:
        return

    if not os.path.exists(TECH_RADAR_YAML_PATH):
        v.add_error(
            "technology_policy_unavailable",
            f"Enterprise Tech Radar policy source is unavailable: '{TECH_RADAR_YAML_PATH}'. Technology declarations cannot be validated safely.",
        )
        return

    try:
        with open(TECH_RADAR_YAML_PATH, "r", encoding="utf-8") as f:
            radar = yaml.safe_load(f)
            tech_radar = radar.get("technology_radar", {})
    except Exception as e:
        logger.debug("Failed to load tech radar from '%s': %s", TECH_RADAR_YAML_PATH, e)
        v.add_error(
            "technology_policy_unavailable",
            f"Enterprise Tech Radar policy source is unreadable: '{TECH_RADAR_YAML_PATH}'. Technology declarations cannot be validated safely.",
        )
        return

    # Build maps of approved and hold technologies
    approved_techs = set()
    hold_techs = set()

    for category in ["adopt", "trial", "assess"]:
        for entry in tech_radar.get(category, []):
            name = entry.get("name") if isinstance(entry, dict) else entry
            if name:
                approved_techs.add(name.lower())

    for entry in tech_radar.get("hold", []):
        name = entry.get("name") if isinstance(entry, dict) else entry
        if name:
            hold_techs.add(name.lower())

    for tech in technologies:
        if not isinstance(tech, dict):
            continue

        tech_name = tech.get("name")
        tech_base = tech.get("base")

        items_to_check = []
        if tech_name:
            items_to_check.append(tech_name)
        if tech_base:
            items_to_check.append(tech_base)

        for item in items_to_check:
            item_lower = item.lower()
            if item_lower in hold_techs:
                v.add_error(
                    "technology_hold_violation",
                    f"Document implements technology on HOLD status: '{item}'.",
                )
            elif item_lower not in approved_techs:
                v.add_error(
                    "unapproved_technology",
                    f"Technology '{item}' is not defined in the Enterprise Tech Radar. It must be assessed before use.",
                )
