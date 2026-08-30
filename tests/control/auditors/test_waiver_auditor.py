from datetime import date, timedelta
from engine.control.auditors.waiver_auditor import audit_waiver_expirations
from engine.control.config.severity import SeverityRule


def test_audit_waiver_expirations():
    today = date.today()
    expired = (today - timedelta(days=1)).isoformat()
    expiring_soon = (today + timedelta(days=15)).isoformat()
    valid = (today + timedelta(days=60)).isoformat()

    all_doc_metadata = {
        "ADR-001": {
            "_filepath": "docs/ADR-001.md",
            "adr_type": "exception",
            "status": "accepted",
            "exception_info": {"expiry_date": expired},
        },
        "ADR-002": {
            "_filepath": "docs/ADR-002.md",
            "adr_type": "exception",
            "status": "accepted",
            "exception_info": {"expiry_date": expiring_soon},
        },
        "ADR-003": {
            "_filepath": "docs/ADR-003.md",
            "adr_type": "exception",
            "status": "accepted",
            "exception_info": {"expiry_date": valid},
        },
        "ADR-004": {
            "_filepath": "docs/ADR-004.md",
            "adr_type": "exception",
            "status": "accepted",
            # Missing expiry_date entirely
            "exception_info": {},
        },
        "ADR-005": {
            "_filepath": "docs/ADR-005.md",
            "adr_type": "exception",
            "status": "accepted",
            # Invalid date format
            "exception_info": {"expiry_date": "15-05-2023"},
        },
        "ADR-006": {
            # Not an exception, should be ignored
            "_filepath": "docs/ADR-006.md",
            "adr_type": "standard",
            "status": "accepted",
        },
        "ADR-007": None,  # Should skip None metadata
    }

    severity_levels = {r.value: "ERROR" for r in SeverityRule}
    errors = audit_waiver_expirations(all_doc_metadata, severity_levels)

    # We expect 4 errors
    assert len(errors) == 4

    # Extract messages for assertion
    messages = {err[0]: (err[1], err[2]) for err in errors}

    assert "docs/ADR-001.md" in messages
    assert messages["docs/ADR-001.md"][0] == "ERROR"
    assert "[exception_expired]" in messages["docs/ADR-001.md"][1]

    assert "docs/ADR-002.md" in messages
    assert messages["docs/ADR-002.md"][0] == "WARNING"
    assert "[exception_expiring_soon]" in messages["docs/ADR-002.md"][1]

    assert "docs/ADR-004.md" in messages
    assert messages["docs/ADR-004.md"][0] == "ERROR"
    assert "missing 'expiry_date'" in messages["docs/ADR-004.md"][1]

    assert "docs/ADR-005.md" in messages
    assert messages["docs/ADR-005.md"][0] == "ERROR"
    assert "Invalid expiry_date format" in messages["docs/ADR-005.md"][1]
