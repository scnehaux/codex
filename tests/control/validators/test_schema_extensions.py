from engine.control.validators.schema_extensions import (
    ExtendedValidator,
    SCNEHAUX_ANNOTATION_KEYWORDS,
    SCNEHAUX_VALIDATION_KEYWORDS,
    _get_concept_pattern,
    _validate_prohibited_keywords,
    _validate_required_subsections,
)


def test_get_concept_pattern():
    pattern = _get_concept_pattern("Security")
    assert pattern.search("### Security")
    assert pattern.search("#### Security")
    assert pattern.search("**Security**")
    assert pattern.search("- **Security**")
    assert not pattern.search("Insecurity")


def test_validate_required_subsections():
    errs = list(
        _validate_required_subsections(None, ["Security"], "### Performance\nFast", {})
    )
    assert len(errs) == 1
    assert "Missing required subsection 'Security'" in errs[0].message
    assert errs[0].validator == "required_subsections"
    assert errs[0].validator_value == "Security"

    errs2 = list(
        _validate_required_subsections(None, ["Security"], "### Security\nGood", {})
    )
    assert len(errs2) == 0

    errs3 = list(_validate_required_subsections(None, ["Security"], {"a": "b"}, {}))
    assert len(errs3) == 0


def test_validate_prohibited_keywords():
    errs = list(_validate_prohibited_keywords(None, ["ADR"], "Here is an ADR.", {}))
    assert len(errs) == 1
    assert "prohibited governance boilerplate word: 'ADR'" in errs[0].message
    assert errs[0].validator == "prohibited_keywords"

    errs2 = list(
        _validate_prohibited_keywords(None, ["ADR"], "Here is a Waiver.", {})
    )
    assert len(errs2) == 0

    errs3 = list(
        _validate_prohibited_keywords(None, ["ADR"], {"a": "b"}, {})
    )
    assert len(errs3) == 0


def test_custom_keyword_registry_separates_validation_from_annotations():
    assert SCNEHAUX_VALIDATION_KEYWORDS == {
        "required_subsections",
        "prohibited_keywords",
    }
    assert SCNEHAUX_VALIDATION_KEYWORDS.issubset(ExtendedValidator.VALIDATORS)

    assert {"recommended", "error_message"}.issubset(
        SCNEHAUX_ANNOTATION_KEYWORDS
    )
    assert "recommended" not in ExtendedValidator.VALIDATORS
    assert "error_message" not in ExtendedValidator.VALIDATORS
