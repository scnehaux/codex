from engine.control.validators.base import BaseValidator
from tests.support.validators import make_validator
from engine.control.config.severity import SeverityRule


def _mock_rules():
    return {"severity_levels": {r.value: "ERROR" for r in SeverityRule}}


def test_base_validator_lint_disable():
    content = "<!-- lint_disable: missing_metadata, prohibited_words -->\nSome content"
    validator = make_validator(
        BaseValidator,
        "dummy.md",
        content,
        {},
        {
            "severity_levels": {
                "missing_metadata": "WARNING",
                "prohibited_words": "WARNING",
            }
        },
        {},
        set(),
        {},
    )
    assert "missing_metadata" in validator.block_disables
    assert "prohibited_words" in validator.block_disables

    # Check that error is bypassed
    validator.add_error("missing_metadata", "This should be ignored")
    assert len(validator.errors) == 0


def test_base_validator_add_error():
    rules = {
        "severity_levels": {
            "structural_integrity_violation": "CRITICAL",
            "missing_metadata": "ERROR",
            "ambiguity_rules": "WARNING",
        }
    }
    validator = make_validator(BaseValidator, "dummy.md", "", {}, rules, {}, set(), {})
    validator.add_error("structural_integrity_violation", "Bad structure")
    validator.add_error("ambiguity_rules", "Vague")

    assert len(validator.errors) == 2
    assert validator.errors[0][0] == "CRITICAL"
    assert validator.errors[1][0] == "WARNING"


def test_base_validator_execution_loop():
    rules = {
        "severity_levels": {"structural_integrity_violation": "ERROR"},
        "rules": {
            "metadata": {"allowed_statuses": ["draft"]},
            "structure": {"required_sections": []},
            "content": {"min_content_length_chars": 1},
        },
    }
    content = "---\ndoc_meta:\n  status: draft\n---\nHello World"
    doc_meta = {"status": "draft", "owner": "team", "classification": "public"}

    validator = make_validator(
        BaseValidator, "ADR-001.md", content, doc_meta, rules, {}, set(), {}
    )
    validator.validate_type_specific = lambda: None

    errors = validator.validate()
    assert isinstance(errors, list)


def test_base_validator_default():
    validator = make_validator(
        BaseValidator, "ADR-001.md", "", {}, {"rules": {}}, {}, set(), {}
    )
    validator.validate_type_specific()
    assert True


def test_base_validator_lint_disable_ignored_inside_code_fence():
    content = "```html\n<!-- lint_disable: missing_metadata -->\n```\nreal body"
    v = make_validator(BaseValidator, "x.md", content, {}, {}, {}, set(), {})
    assert "missing_metadata" not in v.block_disables


def test_base_validator_lint_disable_honored_with_reason():
    content = (
        "<!-- lint_disable: prohibited_words (reason: ARB waiver in ADR-GLB-009) -->"
    )
    v = make_validator(
        BaseValidator,
        "x.md",
        content,
        {},
        {"severity_levels": {"prohibited_words": "WARNING"}},
        {},
        set(),
        {},
    )
    assert "prohibited_words" in v.block_disables
    assert v.block_disables["prohibited_words"][0][2] == "ARB waiver in ADR-GLB-009"


def test_base_validator_lint_disable_undocumented_has_none_reason():
    content = "<!-- lint_disable: prohibited_words -->"
    v = make_validator(
        BaseValidator,
        "x.md",
        content,
        {},
        {"severity_levels": {"prohibited_words": "WARNING"}},
        {},
        set(),
        {},
    )
    assert v.block_disables["prohibited_words"][0][2] is None


def test_base_validator_lint_disable_invalid_rule_fails_fast():
    rules = {"severity_levels": {"invalid_lint_disable": "ERROR"}}
    content = "<!-- lint_disable: some_typo_rule -->"
    v = make_validator(BaseValidator, "x.md", content, {}, rules, {}, set(), {})

    # Should automatically inject an error for the unknown rule
    assert len(v.errors) == 1
    assert v.errors[0][0] == "ERROR"  # severity
    assert "Unrecognized rule ID 'some_typo_rule'" in v.errors[0][1]


def test_base_validator_lint_disable_inline_scope_limited():
    rules = {"severity_levels": {"prohibited_words": "WARNING"}}
    # Inline comment inside a paragraph. Should suppress only the paragraph's line range + 1.
    # markdown-it parses this paragraph as lines [0, 1]. So start=1, end=2.
    content = "This is a paragraph <!-- lint_disable: prohibited_words -->\n\nThis is another paragraph."
    v = make_validator(BaseValidator, "x.md", content, {}, rules, {}, set(), {})

    # Should suppress on line 1
    v.add_error("prohibited_words", "weasel word", line_num=1)
    assert len(v.errors) == 0

    # Should NOT suppress on line 3 (the next paragraph)
    v.add_error("prohibited_words", "weasel word", line_num=3)
    assert len(v.errors) == 1


def test_base_validator_lint_disable_cannot_silence_critical():
    rules = {
        "severity_levels": {"structural_integrity_violation": "CRITICAL"},
        "blocking_severities": ["CRITICAL", "ERROR"],
    }
    content = "<!-- lint_disable: structural_integrity_violation -->"
    v = make_validator(BaseValidator, "x.md", content, {}, rules, {}, set(), {})
    v.add_error("structural_integrity_violation", "sections out of order")
    assert any(sev == "CRITICAL" for sev, _ in v.errors), (
        "CRITICAL finding must still fire"
    )
    assert "structural_integrity_violation" in v.rejected_disables


def test_base_validator_lint_disable_honors_non_critical():
    rules = {"severity_levels": {"prohibited_words": "WARNING"}}
    content = "<!-- lint_disable: prohibited_words -->"
    v = make_validator(BaseValidator, "x.md", content, {}, rules, {}, set(), {})
    v.add_error("prohibited_words", "weasel word")
    assert len(v.errors) == 0


# ---------- FIX#3: inline reference validation ----------


def test_schema_validation_enum():
    schema = {
        "type": "object",
        "properties": {
            "doc_meta": {
                "type": "object",
                "properties": {"status": {"enum": ["active"]}},
            }
        },
    }
    v = make_validator(
        BaseValidator,
        "test.md",
        "content",
        {"status": "draft"},
        _mock_rules(),
        schema,
        set(),
        {},
    )
    v.validate()
    assert any("Schema validation failed at doc_meta" in e[1] for e in v.errors)


def test_schema_validation_pattern():
    schema = {"type": "object", "properties": {"Context": {"pattern": "^[a-z]+$"}}}
    v = make_validator(
        BaseValidator,
        "test.md",
        "## Context\n\n123",
        {},
        _mock_rules(),
        schema,
        set(),
        {},
    )
    v.validate()
    assert any("expected pattern" in e[1] for e in v.errors)


def test_schema_validation_other():
    schema = {"type": "object", "properties": {"doc_meta": {"type": "string"}}}
    v = make_validator(
        BaseValidator,
        "test.md",
        "content",
        {"status": "draft"},
        _mock_rules(),
        schema,
        set(),
        {},
    )
    v.validate()
    assert any("type" in e[1] or "Schema validation failed" in e[1] for e in v.errors)


def test_convert_dates():
    import datetime

    schema = {}
    v = make_validator(
        BaseValidator,
        "test.md",
        "content",
        {"d": datetime.date(2023, 1, 1), "l": [datetime.date(2023, 1, 2)]},
        _mock_rules(),
        schema,
        set(),
        {},
    )
    v.validate()
    # It shouldn't crash, the dates should be converted.


def test_lint_disable_block_start_end_scope_and_reason():
    content = (
        "<!-- lint_disable_start: prohibited_words (reason: literal policy example) -->\n"
        "body\n"
        "<!-- lint_disable_end -->\n"
        "tail"
    )
    v = make_validator(
        BaseValidator,
        "x.md",
        content,
        {},
        {"severity_levels": {"prohibited_words": "WARNING"}},
        {},
        set(),
        {},
    )
    assert "prohibited_words" in v.block_disables
    start, end, reason = v.block_disables["prohibited_words"][0]
    assert start == 1
    assert end >= 3
    assert reason == "literal policy example"


def test_extract_rules_deduplicates_and_filters_garbage():
    v = make_validator(BaseValidator, "x.md", "", {}, {}, {}, set(), {})
    rules, reason = v._extract_rules_and_reason(
        "missing_metadata, bad-rule!, missing_metadata (reason: test)"
    )
    assert rules == ["missing_metadata"]
    assert reason == "test"


def test_add_error_unknown_rule_is_configuration_drift():
    import pytest

    v = make_validator(BaseValidator, "x.md", "", {}, {}, {}, set(), {})
    with pytest.raises(RuntimeError, match="configuration drift"):
        v.add_error("does_not_exist", "boom")


def test_schema_validation_required_root_maps_missing_section():
    schema = {"type": "object", "required": ["Context & Scope"]}
    v = make_validator(
        BaseValidator,
        "test.md",
        "content",
        {},
        _mock_rules(),
        schema,
        set(),
        {},
    )
    v.validate()
    assert any("Schema validation failed at root" in message for _, message in v.errors)


def test_schema_format_checker_rejects_invalid_calendar_date():
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "doc_meta": {
                "type": "object",
                "properties": {
                    "created_date": {
                        "type": "string",
                        "format": "date",
                    }
                },
            }
        },
    }
    v = make_validator(
        doc_meta={"created_date": "2023-02-29"},
        domain_schema=schema,
    )
    v._validate_schema()
    assert any("not a 'date'" in message for _, message in v.errors)


def test_schema_format_checker_accepts_valid_leap_day():
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "doc_meta": {
                "type": "object",
                "properties": {
                    "created_date": {
                        "type": "string",
                        "format": "date",
                    }
                },
            }
        },
    }
    v = make_validator(
        doc_meta={"created_date": "2024-02-29"},
        domain_schema=schema,
    )
    v._validate_schema()
    assert not any("not a 'date'" in message for _, message in v.errors)
