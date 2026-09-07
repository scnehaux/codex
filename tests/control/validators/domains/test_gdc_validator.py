from tests.support.validators import make_validator
import os
import json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))


def _global_rules():
    with open(
        os.path.join(ROOT, "schemas", "base.schema.json"),
        encoding="utf-8",
    ) as f:
        return json.load(f).get("x-global-config", {})


from engine.control.validators.domains.gdc_validator import GDCValidator


def test_gdc_guideline_interface():
    rules = {
        "rules": {
            "structure": {
                "required_downstream_guideline_subsections": {
                    "Semantic Definitions": ["Naming Conventions", "Taxonomy"],
                    "Metadata Schema Properties": [
                        "Allowed Lifecycle Statuses",
                        "Allowed Classifications",
                    ],
                }
            }
        },
        "severity_levels": {},
    }
    # Neither required parent section present -> one missing_section error per parent (2).
    v = make_validator(
        cls=GDCValidator,
        doc_meta={"status": "draft"},
        content="## Introduction",
        rules=rules,
        filename="EAD-007-guideline.md",
    )
    v.validate_type_specific()
    assert len(v.errors) == 2

    good_content = (
        "## Semantic Definitions\n"
        "### Naming Conventions\n### Taxonomy\n"
        "## Metadata Schema Properties\n"
        "### Allowed Lifecycle Statuses\n### Allowed Classifications\n"
    )
    v_good = make_validator(
        cls=GDCValidator,
        doc_meta={"status": "draft"},
        content=good_content,
        rules=rules,
        filename="EAD-007-guideline.md",
    )
    v_good.validate_type_specific()
    assert len(v_good.errors) == 0


def test_gdc_missing_subsection():
    rules = {
        "rules": {
            "structure": {
                "required_downstream_guideline_subsections": {
                    "Semantic Definitions": ["Naming Conventions", "Taxonomy"],
                    "Metadata Schema Properties": [
                        "Allowed Lifecycle Statuses",
                        "Allowed Classifications",
                    ],
                }
            }
        },
        "severity_levels": {},
    }
    content = (
        "## Semantic Definitions\n### Naming Conventions\n"  # 'Taxonomy' missing
        "## Metadata Schema Properties\n### Allowed Lifecycle Statuses\n### Allowed Classifications\n"
    )
    v = make_validator(
        cls=GDCValidator,
        doc_meta={"status": "draft"},
        content=content,
        rules=rules,
        filename="EAD-007-guideline.md",
    )
    v.validate_type_specific()
    assert any("missing mandatory subsection 'Taxonomy'" in m for _, m in v.errors)


def test_gdc_subsection_out_of_order():
    rules = {
        "rules": {
            "structure": {
                "required_downstream_guideline_subsections": {
                    "Semantic Definitions": ["Naming Conventions", "Taxonomy"],
                    "Metadata Schema Properties": [
                        "Allowed Lifecycle Statuses",
                        "Allowed Classifications",
                    ],
                }
            }
        },
        "severity_levels": {},
    }
    content = (
        "## Semantic Definitions\n### Taxonomy\n### Naming Conventions\n"  # reversed
        "## Metadata Schema Properties\n### Allowed Lifecycle Statuses\n### Allowed Classifications\n"
    )
    v = make_validator(
        cls=GDCValidator,
        doc_meta={"status": "draft"},
        content=content,
        rules=rules,
        filename="EAD-007-guideline.md",
    )
    v.validate_type_specific()
    assert any("out of order" in m for _, m in v.errors)


def test_gdc_non_guideline_file_skipped():
    rules = {
        "rules": {
            "structure": {
                "required_downstream_guideline_subsections": {
                    "Semantic Definitions": ["Naming Conventions", "Taxonomy"],
                }
            }
        },
        "severity_levels": {},
    }
    v = make_validator(
        cls=GDCValidator,
        doc_meta={"status": "draft"},
        content="## Anything",
        rules=rules,
        filename="GDC-002-compliance-engine.control.md",
    )
    v.validate_type_specific()
    assert len(v.errors) == 0


# ---------- EAD ----------


# ---------- TDD ----------
