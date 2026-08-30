from __future__ import annotations

from functools import lru_cache
import json

from engine.control.config.loader import (
    validate_blocking_severities,
    validate_severity_schema,
)
from engine.control.validators.base import BaseValidator
from tests.support.repository import REPOSITORY_ROOT


@lru_cache(maxsize=1)
def _get_real_config() -> tuple[dict, dict, tuple]:
    from engine.control.config.loader import parse_and_validate_global_config

    schema_path = REPOSITORY_ROOT / "00-governance" / "schemas" / "base.schema.json"
    with schema_path.open("r", encoding="utf-8") as handle:
        schema = json.load(handle)

    return parse_and_validate_global_config(schema)


def make_validator(
    cls=BaseValidator,
    file_path: str = "/fake/test.md",
    content: str = "",
    doc_meta: dict | None = None,
    rules: dict | None = None,
    domain_schema: dict | None = None,
    all_doc_ids: set | None = None,
    all_doc_metadata: dict | None = None,
    filename: str | None = None,
):
    """Construct a validator using real validated repository configuration."""
    if doc_meta is None:
        doc_meta = {}
    if rules is None:
        rules = {}
    if all_doc_ids is None:
        all_doc_ids = set()
    if all_doc_metadata is None:
        all_doc_metadata = {}

    real_global, real_severity, real_blocking = _get_real_config()

    merged_rules = dict(real_global)
    merged_rules.update(rules)

    merged_severity = dict(real_severity)
    if "severity_levels" in rules:
        merged_severity.update(rules["severity_levels"])

    merged_blocking = tuple(rules.get("blocking_severities", list(real_blocking)))

    validate_severity_schema(merged_severity)
    validate_blocking_severities(merged_blocking)

    validator = cls(
        file_path=file_path,
        content=content,
        doc_meta=doc_meta,
        global_rules=merged_rules,
        domain_schema=domain_schema or {},
        all_doc_ids=all_doc_ids,
        all_doc_metadata=all_doc_metadata,
        severity_levels=merged_severity,
        blocking_severities=merged_blocking,
    )
    if filename is not None:
        validator.filename = filename
    return validator
