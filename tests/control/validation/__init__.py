import pytest

from engine.control.validation import (
    ValidationFinding,
    ValidationOutcome,
    ValidationReport,
)


def test_validation_report_outcome_and_deterministic_order():
    report = ValidationReport(
        report_id="VAL-1",
        draft_id="D-1",
        findings=(
            ValidationFinding("b", "rule-b", "warning", False),
            ValidationFinding("a", "rule-a", "blocking", True, "GDC-1"),
        ),
    )
    assert report.outcome is ValidationOutcome.FAIL
    assert [item.finding_id for item in report.findings] == ["a", "b"]
    assert report.semantic_state()[2] == "fail"


def test_validation_report_passes_without_blockers():
    report = ValidationReport("VAL-1", "D-1")
    assert report.outcome is ValidationOutcome.PASS


def test_validation_contract_rejects_bad_values():
    with pytest.raises(ValueError):
        ValidationFinding("", "rule", "message", False)
    with pytest.raises(TypeError):
        ValidationReport("VAL", "D", findings=(object(),))
    with pytest.raises(ValueError):
        ValidationReport(
            "VAL",
            "D",
            findings=(
                ValidationFinding("x", "a", "m", False),
                ValidationFinding("x", "b", "m", False),
            ),
        )

