import pytest

from engine.intelligence.review import ArchitectureReview, ReviewFinding


def test_architecture_review_is_advisory_and_deterministic():
    finding = ReviewFinding(
        "f1",
        "operability",
        "failure mode unclear",
        "define recovery objective",
        ("C2", "C1"),
        0.8,
    )
    review = ArchitectureReview(
        "REV-1",
        "D-1",
        "review-run-1",
        "material operability challenge",
        (finding,),
        validation_report_id="VAL-1",
        simulation_report_id="SIM-1",
        independent_from_generation=True,
    )
    assert review.findings[0].related_claim_ids == ("C1", "C2")
    assert not hasattr(review, "approved")
    assert review.semantic_state()[-1] is True


def test_review_contract_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        ReviewFinding("f", "c", "x", "y", confidence=2.0)
    with pytest.raises(TypeError):
        ArchitectureReview("r", "d", "reviewer", "summary", findings=(object(),))
    duplicate = ReviewFinding("f", "c", "x", "y")
    with pytest.raises(ValueError):
        ArchitectureReview(
            "r", "d", "reviewer", "summary", findings=(duplicate, duplicate)
        )


def test_review_contract_additional_validation_paths():
    with pytest.raises(ValueError):
        ReviewFinding(" ", "c", "x", "y")
    with pytest.raises(ValueError):
        ReviewFinding("f", "c", "x", "y", related_claim_ids=("C", "C"))
    with pytest.raises(ValueError):
        ArchitectureReview("r", "d", "reviewer", "summary", validation_report_id=" ")
    review = ArchitectureReview("r", "d", "reviewer", "summary")
    assert review.findings == ()
