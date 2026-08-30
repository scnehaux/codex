from tests.support.validators import make_validator
from engine.control.validators.structure_rules import (
    _validate_structure,
    _validate_nfr_taxonomy,
    _validate_internal_links,
    _validate_inline_references,
)


def test_validate_structure():
    rules = {
        "content_rules": {"min_content_length_chars": {"value": 100}},
        "severity_levels": {},
    }
    v = make_validator(rules=rules, content="## Introduction\nToo short.")
    _validate_structure(v)
    assert any("content length" in e[1] for e in v.errors)


def test_validate_nfr_taxonomy():
    rules = {
        "severity_levels": {"structural_integrity_violation": "ERROR"},
    }
    domain_schema = {
        "x-global-config": {"quantification_pillars": ["Security", "Reliability"]}
    }
    content = (
        "## Non-Functional Requirements\n### Security\nGood.\n### Invalid Pillar\nBad."
    )
    v = make_validator(rules=rules, domain_schema=domain_schema, content=content)
    _validate_nfr_taxonomy(v)
    assert len(v.errors) == 1
    assert "not an approved AWS WAF Pillar" in v.errors[0][1]


def test_nfr_taxonomy_unstructured_section():
    # If NFR section exists but has no ### headers, it must throw a structural integrity error.
    rules = {
        "severity_levels": {},
    }
    domain_schema = {
        "x-global-config": {"quantification_pillars": ["Security", "Reliability"]}
    }
    content = (
        "## Non-Functional Requirements\nJust some plain text without H3 pillars.\n"
    )
    v = make_validator(rules=rules, domain_schema=domain_schema, content=content)
    _validate_nfr_taxonomy(v)
    assert len(v.errors) == 1
    assert "unstructured" in v.errors[0][1]


def test_validate_internal_links(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    d = tmp_path / "docs"
    d.mkdir()
    f1 = d / "file1.md"
    f1.write_text("content")

    content = "[valid](./file1.md) [invalid](./missing.md) [external](http://google.com) [fragment](./file1.md#frag) [mail](mailto:test@test.com)"
    v = make_validator(file_path=str(d / "index.md"), content=content)
    _validate_internal_links(v)

    assert len(v.errors) == 1
    assert "missing.md" in v.errors[0][1]


def test_validate_inline_references():
    content = "This refers to **ADR-001** and **SAD-002**. Also an example **ADR-EXAMPLE-001**."

    # SAD-002 is missing from all_doc_ids
    v = make_validator(
        content=content, all_doc_ids={"ADR-001"}, doc_meta={"id": "GDC-001"}
    )
    _validate_inline_references(v)

    assert len(v.errors) == 1
    assert "SAD-002" in v.errors[0][1]
    # ADR-EXAMPLE-001 should be ignored due to regex


def test_validate_internal_links_empty_file_part(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Link pointing only to fragment `#section`
    content = "[Section Link](#section)"
    v = make_validator(file_path=str(tmp_path / "doc.md"), content=content)
    _validate_internal_links(v)
    assert len(v.errors) == 0


def test_validate_inline_references_self_reference():
    # Document citing its own ID (ADR-001) should skip it (line 91)
    content = "This document ADR-001 describes the architecture."
    v = make_validator(
        content=content, all_doc_ids={"ADR-001"}, doc_meta={"id": "ADR-001"}
    )
    _validate_inline_references(v)
    assert len(v.errors) == 0
