"""
Audits ADR waivers for temporal expiration.

Extracts all documents where `adr_type == "exception"` and `status == "accepted"`.
Checks the `expiry_date` inside `exception_info` against the current system date.
If the date has passed, triggers an `exception_expired` hard block.
If it is approaching within 30 days, triggers an `exception_expiring_soon` warning.
"""

from datetime import date, datetime, timedelta
from engine.control.config.severity import SeverityRule


def audit_waiver_expirations(
    all_doc_metadata: dict, severity_levels: dict
) -> list[tuple[str, str, str]]:
    """
    Validates expiration dates on all accepted Exception ADRs.

    Args:
        all_doc_metadata (dict): Mapping of filepath to its parsed YAML frontmatter.
        severity_levels (dict): Mapping of SeverityRule to severity string.

    Returns:
        list of tuples: [(filepath, level, message), ...]
    """
    errors = []
    today = date.today()
    warning_threshold = today + timedelta(days=30)

    for doc_id, meta in all_doc_metadata.items():
        if not meta:
            continue

        filepath = meta.get("_filepath", doc_id)

        adr_type = meta.get("adr_type")
        status = meta.get("status")

        if adr_type == "exception" and status == "accepted":
            exception_info = meta.get("exception_info", {})
            expiry_str = exception_info.get("expiry_date")

            if not expiry_str:
                errors.append(
                    (
                        filepath,
                        "ERROR",
                        "Exception ADR is missing 'expiry_date' in 'exception_info'.",
                    )
                )
                continue

            try:
                # ISO Format: YYYY-MM-DD
                expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
            except ValueError:
                errors.append(
                    (
                        filepath,
                        "ERROR",
                        f"Invalid expiry_date format '{expiry_str}'. Must be YYYY-MM-DD.",
                    )
                )
                continue

            if expiry_date < today:
                errors.append(
                    (
                        filepath,
                        severity_levels[SeverityRule.EXCEPTION_EXPIRED],
                        f"[exception_expired] Waiver expired on {expiry_str}. "
                        "Resolve the technical debt or request a renewal (GDC-010 §2.4.3).",
                    )
                )
            elif expiry_date <= warning_threshold:
                days_left = (expiry_date - today).days
                errors.append(
                    (
                        filepath,
                        "WARNING",
                        f"[exception_expiring_soon] Waiver will expire in {days_left} days on {expiry_str}.",
                    )
                )

    return errors
