from engine.control.auditors.graph_auditor import (
    build_upward_graph,
    audit_hierarchy_tiers,
    audit_orphans,
    audit_traceability_graph,
)


def test_audit_hierarchy_tiers():
    meta = {
        "TDD-001": {"parent_sad": "PAD-001", "_filepath": "TDD-001.md"},
        "SAD-001": {
            "status": "chartered",
            "governed_by": ["EAD-001"],
            "parent_pad": "EAD-001",
            "_filepath": "SAD-001.md",
        },
        "PAD-001": {
            "governed_by": ["STD-001"],
            "realizes_capability": ["EAD-001"],
            "fulfilled_by": [],
            "_filepath": "PAD-001.md",
        },
        "ADR-001": {"governed_by": ["TDD-001"], "_filepath": "ADR-001.md"},
        "EAD-001": {"governed_by": ["GDC-000"]},
        "GDC-000": {"governed_by": ["GDC-000"]},
        "STD-001": {"governed_by": ["EAD-001"]},
    }
    sev = {"structural_integrity_violation": "CRITICAL"}
    findings = audit_hierarchy_tiers(meta, sev)

    assert len(findings) == 4
    assert any("parent_sad" in msg and "PAD-001" in msg for _, msg, _ in findings)
    assert any("parent_pad" in msg and "EAD-001" in msg for _, msg, _ in findings)
    assert any("governed_by" in msg and "STD-001" in msg for _, msg, _ in findings)
    assert any("governed_by" in msg and "TDD-001" in msg for _, msg, _ in findings)


def test_audit_orphans():
    meta = {
        "TDD-002": {"_filepath": "TDD-002.md"},
        "SAD-002": {"_filepath": "SAD-002.md"},
        "PAD-002": {"fulfilled_by": [], "_filepath": "PAD-002.md"},
    }
    sev = {"orphan_document": "ERROR"}
    findings = audit_orphans(meta, sev)

    assert len(findings) == 5
    assert any("parent_sad" in msg for _, msg, _ in findings)
    assert any("parent_pad" in msg for _, msg, _ in findings)
    assert any(
        "SAD-002" in msg and "governed_by" in msg
        for _, msg, _ in findings
    )
    assert any(
        "PAD-002" in msg and "governed_by" in msg
        for _, msg, _ in findings
    )
    assert any("realizes_capability" in msg for _, msg, _ in findings)


def test_audit_hierarchy_tiers_accepts_multiple_sad_parents():
    meta = {
        "TDD-foundation-001": {
            "parent_sad": ["SAD-001", "SAD-004"],
            "_filepath": "docs/designs/TDD-foundation-001.md",
        }
    }
    sev = {"structural_integrity_violation": "CRITICAL"}

    assert audit_hierarchy_tiers(meta, sev) == []


def test_audit_traceability_graph_cycle_detected():
    meta = {
        "SAD-001": {"parent_pad": "PAD-001"},
        "PAD-001": {"governed_by": "SAD-001"},
    }
    errs = audit_traceability_graph(meta)
    assert any("Circular" in m for _, m in errs)


def test_audit_traceability_graph_self_reference():
    meta = {"GDC-000": {"governed_by": ["GDC-000"]}}
    assert audit_traceability_graph(meta) == []


def test_audit_traceability_graph_acyclic_clean():
    meta = {
        "SAD-001": {"parent_pad": "PAD-001"},
        "PAD-001": {"governed_by": "EAD-001"},
        "EAD-001": {},
    }
    assert audit_traceability_graph(meta) == []


def test_audit_hierarchy_and_orphans_non_dict():
    meta = {"INVALID_KEY": "not_a_dict_metadata"}
    sev = {
        "structural_integrity_violation": "CRITICAL",
        "orphan_document": "ERROR",
    }
    assert audit_hierarchy_tiers(meta, sev) == []
    assert audit_orphans(meta, sev) == []



def test_downward_inverse_relation_does_not_create_false_dag_cycle():
    meta = {
        "PAD-001": {
            "governed_by": ["EAD-001"],
            "realizes_capability": ["EAD-001"],
            "fulfilled_by": ["SAD-001"],
        },
        "SAD-001": {
            "status": "approved",
            "governed_by": ["EAD-001"],
            "parent_pad": "PAD-001",
        },
        "EAD-001": {"governed_by": ["GDC-000"]},
        "GDC-000": {"governed_by": ["GDC-000"]},
    }
    assert audit_traceability_graph(meta) == []


def test_audit_hierarchy_enforces_parent_authority_from_registry():
    meta = {
        "SAD-001": {
            "status": "draft",
            "governed_by": ["EAD-001"],
            "parent_pad": "PAD-001",
            "_filepath": "SAD-001.md",
        },
        "PAD-001": {"status": "draft"},
        "EAD-001": {},
    }
    sev = {"structural_integrity_violation": "CRITICAL"}
    findings = audit_hierarchy_tiers(meta, sev)
    assert any("requires an approved parent PAD" in msg for _, msg, _ in findings)


def test_build_upward_graph_handles_non_dict_registry_metadata():
    graph = build_upward_graph(
        {
            "BROKEN": "not-a-mapping",
            "GDC-000": {"governed_by": ["GDC-000"]},
        }
    )
    assert graph["BROKEN"] == set()
    assert graph["GDC-000"] == set()

