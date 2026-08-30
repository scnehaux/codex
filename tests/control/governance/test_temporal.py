import datetime

import pytest

from engine.control.governance.temporal import (
    EVALUATION_DATE_ENV,
    evaluation_date,
    parse_canonical_date,
    temporal_integrity_findings,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2024-02-29", datetime.date(2024, 2, 29)),
        (datetime.date(2026, 8, 29), datetime.date(2026, 8, 29)),
        (
            datetime.datetime(2026, 8, 29, 12, 0),
            datetime.date(2026, 8, 29),
        ),
    ],
)
def test_parse_canonical_date_accepts_canonical_values(value, expected):
    assert parse_canonical_date(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "2023-02-29",
        "2026/08/29",
        "20260829",
        "29-08-2026",
        "not-a-date",
        "",
        None,
        20260829,
    ],
)
def test_parse_canonical_date_rejects_noncanonical_or_invalid_values(value):
    assert parse_canonical_date(value) is None


def test_evaluation_date_uses_environment_override(monkeypatch):
    monkeypatch.setenv(EVALUATION_DATE_ENV, "2030-01-02")
    assert evaluation_date() == datetime.date(2030, 1, 2)


def test_evaluation_date_rejects_invalid_override(monkeypatch):
    monkeypatch.setenv(EVALUATION_DATE_ENV, "2030/01/02")
    with pytest.raises(RuntimeError, match=EVALUATION_DATE_ENV):
        evaluation_date()


def test_evaluation_date_falls_back_to_system_date(monkeypatch):
    monkeypatch.delenv(EVALUATION_DATE_ENV, raising=False)
    assert evaluation_date() == datetime.date.today()


def test_temporal_integrity_accepts_valid_ordering():
    findings = temporal_integrity_findings(
        {
            "created_date": "2026-01-01",
            "last_updated": "2026-07-01",
            "last_reviewed": "2026-08-01",
        },
        today=datetime.date(2026, 8, 29),
    )
    assert findings == []


@pytest.mark.parametrize("field", ["created_date", "last_updated", "last_reviewed"])
def test_temporal_integrity_rejects_future_dates(field):
    findings = temporal_integrity_findings(
        {field: "2026-08-30"},
        today=datetime.date(2026, 8, 29),
    )
    assert len(findings) == 1
    assert field in findings[0]
    assert "future" in findings[0]


def test_temporal_integrity_rejects_created_after_updated():
    findings = temporal_integrity_findings(
        {
            "created_date": "2026-08-20",
            "last_updated": "2026-08-10",
        },
        today=datetime.date(2026, 8, 29),
    )
    assert any("last_updated" in finding for finding in findings)


def test_temporal_integrity_rejects_created_after_reviewed():
    findings = temporal_integrity_findings(
        {
            "created_date": "2026-08-20",
            "last_reviewed": "2026-08-10",
        },
        today=datetime.date(2026, 8, 29),
    )
    assert any("last_reviewed" in finding for finding in findings)


def test_temporal_integrity_does_not_duplicate_schema_date_syntax():
    assert temporal_integrity_findings(
        {"created_date": "2026/08/29"},
        today=datetime.date(2026, 8, 29),
    ) == []


def test_temporal_integrity_handles_missing_metadata():
    assert temporal_integrity_findings(None) == []
    assert temporal_integrity_findings({}) == []
