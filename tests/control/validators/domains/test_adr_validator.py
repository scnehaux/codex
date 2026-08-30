from tests.support.validators import make_validator
import os
import json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))


def _global_rules():
    with open(
        os.path.join(ROOT, "00-governance", "schemas", "base.schema.json"),
        encoding="utf-8",
    ) as f:
        return json.load(f).get("x-global-config", {})


from datetime import date, timedelta
from engine.control.validators.domains.adr_validator import ADRValidator


def test_adr_exception_expired():
    past = date.today() - timedelta(days=1)
    meta = {
        "adr_type": "exception",
        "status": "accepted",
        "exception_info": {"expiry_date": past},
    }
    rules = {
        "rules": {
            "metadata": {
                "exception_info_required_fields": ["expiry_date"],
                "allowed_types": ["standard", "exception"],
            }
        },
        "severity_levels": {},
    }
    v = make_validator(
        cls=ADRValidator, doc_meta=meta, rules=rules, filename="ADR-001.md"
    )
    v.validate_type_specific()
    assert any("has expired" in msg for sev, msg in v.errors)


# ---------- SAD ----------
