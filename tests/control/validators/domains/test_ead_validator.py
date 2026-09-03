from tests.support.validators import make_validator

from engine.control.validators.domains.ead_validator import EADValidator


def _ead(doc_id="EAD-001", content="", doc_meta=None):
    metadata = {"id": doc_id}
    if doc_meta:
        metadata.update(doc_meta)
    return make_validator(
        cls=EADValidator,
        doc_meta=metadata,
        content=content,
        filename=f"{doc_id}-test.md",
    )


def test_ead_rejects_concrete_technology_metadata_outside_ead005():
    validator = _ead(
        doc_meta={"technologies": [{"name": "PostgreSQL"}]},
    )
    validator.validate_type_specific()
    assert any(
        "must not declare concrete technologies" in message
        for _, message in validator.errors
    )


def test_ead_rejects_prescriptive_implementation_assertion():
    validator = _ead(
        content="## Principles & Rules\nThe platform uses PostgreSQL for persistence.\n"
    )
    validator.validate_type_specific()
    assert any(
        "implementation leakage detected" in message for _, message in validator.errors
    )


def test_ead_rejects_labeled_physical_implementation():
    validator = _ead(content="## Architecture Model\nDatabase: PostgreSQL\n")
    validator.validate_type_specific()
    assert any(
        "implementation leakage detected" in message for _, message in validator.errors
    )


def test_ead_allows_quantified_sla_without_implementation_detail():
    validator = _ead(
        content=(
            "## Principles & Rules\n"
            "Critical APIs require P95 <= 200ms and availability >= 99.95%.\n"
        )
    )
    validator.validate_type_specific()
    assert validator.errors == []


def test_ead_allows_negated_technology_example():
    validator = _ead(
        content=(
            "## Principles & Rules\n"
            "The enterprise policy must not use PostgreSQL as an EAD-level mandate.\n"
        )
    )
    validator.validate_type_specific()
    assert validator.errors == []


def test_ead_ignores_fenced_illustrative_implementation():
    validator = _ead(
        content=("## Alternatives Considered\n```text\nDatabase: PostgreSQL\n```\n")
    )
    validator.validate_type_specific()
    assert validator.errors == []


def test_ead005_is_explicit_technology_portfolio_exception():
    validator = _ead(
        doc_id="EAD-005",
        content="We standardize on Kubernetes and PostgreSQL.",
        doc_meta={"technologies": [{"name": "Kubernetes"}]},
    )
    validator.validate_type_specific()
    assert validator.errors == []


def test_ead_without_metadata_is_noop():
    validator = make_validator(
        cls=EADValidator,
        doc_meta={},
        content="Database: PostgreSQL",
    )
    validator.validate_type_specific()
    assert validator.errors == []
