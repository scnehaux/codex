from __future__ import annotations

import datetime
import os
import re
from typing import Any

EVALUATION_DATE_ENV = "SCNEHAUX_EVALUATION_DATE"
_CANONICAL_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TEMPORAL_FIELDS = ("created_date", "last_updated", "last_reviewed")


def parse_canonical_date(value: Any) -> datetime.date | None:
    """Parse only canonical YYYY-MM-DD governance dates."""
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if not isinstance(value, str):
        return None

    raw = value.strip()
    if not _CANONICAL_DATE_RE.fullmatch(raw):
        return None

    try:
        return datetime.date.fromisoformat(raw)
    except ValueError:
        return None


def evaluation_date() -> datetime.date:
    """Return the deterministic governance evaluation date."""
    raw = os.getenv(EVALUATION_DATE_ENV)
    if raw is None or not raw.strip():
        return datetime.date.today()

    parsed = parse_canonical_date(raw)
    if parsed is None:
        raise RuntimeError(
            f"{EVALUATION_DATE_ENV} must be a valid canonical YYYY-MM-DD date, got {raw!r}"
        )
    return parsed


def temporal_integrity_findings(
    doc_meta: dict | None,
    *,
    today: datetime.date | None = None,
) -> list[str]:
    """Return semantic temporal findings without duplicating schema format checks."""
    if not doc_meta:
        return []

    eval_date = today or evaluation_date()
    parsed: dict[str, datetime.date] = {}
    findings: list[str] = []

    for field in TEMPORAL_FIELDS:
        if field not in doc_meta or doc_meta.get(field) in (None, ""):
            continue

        value = parse_canonical_date(doc_meta.get(field))
        if value is None:
            # JSON Schema FormatChecker owns canonical date syntax.
            continue

        parsed[field] = value
        if value > eval_date:
            findings.append(
                f"Metadata field '{field}' is in the future ({value.isoformat()}) "
                f"relative to governance evaluation date {eval_date.isoformat()}."
            )

    created = parsed.get("created_date")
    updated = parsed.get("last_updated")
    reviewed = parsed.get("last_reviewed")

    if created and updated and created > updated:
        findings.append(
            f"'created_date' ({created.isoformat()}) must not be later than "
            f"'last_updated' ({updated.isoformat()})."
        )

    if created and reviewed and created > reviewed:
        findings.append(
            f"'created_date' ({created.isoformat()}) must not be later than "
            f"'last_reviewed' ({reviewed.isoformat()})."
        )

    return findings
