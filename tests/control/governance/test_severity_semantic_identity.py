from pathlib import Path


def test_broken_internal_link_has_distinct_rule_identity(tmp_path):
    from engine.control.validators.structure_rules import _validate_internal_links

    class Stub:
        def __init__(self):
            self.file_path = str(tmp_path / "artifact.md")
            self.content = "[dead link](missing-target.md)"
            self.findings = []

        def add_error(self, rule_id, message, line_num=None):
            self.findings.append((rule_id, message))

    stub = Stub()
    _validate_internal_links(stub)

    assert len(stub.findings) == 1
    assert stub.findings[0][0] == "broken_internal_link"
    assert "Link rot detected" in stub.findings[0][1]


def test_required_subsection_maps_to_specific_severity():
    from engine.control.validators.base import BaseValidator

    class DummyValidator(BaseValidator):
        doc_type_name = "GDC"

        def validate_type_specific(self):
            return None
    domain_schema = {
        "$id": "https://example.test/required-subsection.schema.json",
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "required_subsections": ["Required Concept"],
            }
        },
    }

    validator = DummyValidator(
        "artifact.md",
        "# Artifact\n",
        {"id": "GDC-TEST-001"},
        {},
        domain_schema,
        set(),
        {},
        {"missing_required_subsection": "ERROR"},
        ("CRITICAL", "ERROR"),
    )

    validator._validate_schema()

    assert len(validator.errors) == 1
    assert validator.errors[0][0] == "ERROR"
    assert "missing required subsection" in validator.errors[0][1].lower()


def test_nfr_taxonomy_has_distinct_rule_identity():
    from engine.control.validators.structure_rules import _validate_nfr_taxonomy

    class Stub:
        def __init__(self):
            self.content = (
                "# Artifact\n\n"
                "## Non-Functional Requirements\n\n"
                "### Banana\n\n"
                "This heading is deliberately outside the approved taxonomy.\n"
            )
            self.domain_schema = {
                "x-global-config": {
                    "quantification_pillars": ["Security", "Reliability"]
                }
            }
            self.findings = []

        def add_error(self, rule_id, message, line_num=None):
            self.findings.append((rule_id, message))

    stub = Stub()
    _validate_nfr_taxonomy(stub)

    assert stub.findings
    assert {rule_id for rule_id, _ in stub.findings} == {
        "nfr_taxonomy_violation"
    }
    assert any("NFR taxonomy violation" in message for _, message in stub.findings)


def test_orphan_document_has_distinct_auditor_severity():
    from engine.control.auditors.graph_auditor import audit_orphans
    from engine.control.config.severity import SeverityRule

    severities = {rule.value: "OTHER" for rule in SeverityRule}
    severities[SeverityRule.ORPHAN_DOCUMENT] = "ORPHAN"
    severities[SeverityRule.TRACEABILITY_VIOLATION] = "TRACE"

    findings = audit_orphans(
        {"SAD-TEST-001": {"_filepath": "04-system/test.sad.md"}},
        severities,
    )

    assert findings
    assert {finding[0] for finding in findings} == {"ORPHAN"}
    assert all(
        "requires cardinality" in finding[1] or "Orphan artifact" in finding[1]
        for finding in findings
    )

def test_subsection_order_has_distinct_rule_identity():
    from engine.control.validators.domains.gdc_validator import GDCValidator

    validator = GDCValidator.__new__(GDCValidator)
    validator.doc_meta = {"status": "draft"}
    validator.filename = "GDC-TEST-guideline.md"
    validator.global_rules = {
        "rules": {
            "structure": {
                "required_downstream_guideline_subsections": {
                    "Semantic Definitions": [
                        "Naming Conventions",
                        "Taxonomy",
                    ]
                }
            }
        }
    }
    validator.content = (
        "## Semantic Definitions\n"
        "### Taxonomy\n"
        "### Naming Conventions\n"
    )

    findings = []

    def capture(rule_id, message, line_num=None):
        findings.append((rule_id, message))

    validator.add_error = capture
    validator.validate_type_specific()

    assert any(
        rule_id == "subsection_order_violation" and "out of order" in message
        for rule_id, message in findings
    )


def test_removed_phantom_severity_ids_are_absent():
    from engine.control.config.severity import SeverityRule

    removed = {
        "missing_domain_schema",
        "prohibited_technology_violation",
        "security_isolation_violation",
        "vague_claim_in_nfr",
    }

    assert removed.isdisjoint({rule.value for rule in SeverityRule})
