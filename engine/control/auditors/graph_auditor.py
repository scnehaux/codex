"""
Repository-level traceability graph audit.

Per-file validators (sad.py / pad.py / tdd.py) check individual edges. This module
runs once over the FULL registry to catch defects that are only visible globally:
circular upward dependencies (the chain EAD -> PAD -> SAD -> TDD must remain a DAG).

Self-references (e.g. GDC-000 declaring `governed_by: [GDC-000]`, the constitution
governing itself) are intentional and are NOT treated as cycles.
"""

from engine.control.config.severity import SeverityRule
from engine.control.governance.relationships import (
    artifact_type_from_id,
    dag_relation_specs_for_source,
    normalize_relation_values,
    relationship_contract_findings,
)

# Hardcoded list of metadata fields that represent an upward dependency in the DAG


def build_upward_graph(all_doc_metadata):
    """Build the DAG adjacency map from registry-declared DAG relations only."""
    known = set(all_doc_metadata.keys())
    graph = {}
    for doc_id, meta in all_doc_metadata.items():
        if not isinstance(meta, dict):
            graph[doc_id] = set()
            continue

        source_type = artifact_type_from_id(doc_id)
        targets = set()
        for spec in dag_relation_specs_for_source(source_type):
            for ref in normalize_relation_values(meta.get(spec.metadata_field)):
                if isinstance(ref, str) and ref in known and ref != doc_id:
                    targets.add(ref)
        graph[doc_id] = targets
    return graph


def audit_traceability_graph(all_doc_metadata):
    """
    Return a list of (category, message) tuples for global traceability defects.

    Currently detects circular dependencies (length >= 2) in the upward-reference
    graph and emits them as 'traceability_violation' (a blocking ERROR).
    """
    errors = []
    graph = build_upward_graph(all_doc_metadata)

    WHITE, GRAY, BLACK = 0, 1, 2
    color = {node: WHITE for node in graph}
    reported = set()

    def dfs(node, stack):
        color[node] = GRAY
        stack.append(node)
        for nxt in graph.get(node, ()):
            state = color.get(nxt, BLACK)
            if state == GRAY and nxt in stack:
                cycle = stack[stack.index(nxt) :] + [nxt]
                key = tuple(sorted(set(cycle)))
                if key not in reported:
                    reported.add(key)
                    errors.append(
                        (
                            "traceability_violation",
                            f"Circular traceability dependency detected: {' -> '.join(cycle)}. "
                            "Upward references (parent_pad/parent_sad/governed_by) must form a DAG.",
                        )
                    )
            elif state == WHITE:
                dfs(nxt, stack)
        stack.pop()
        color[node] = BLACK

    for node in list(graph.keys()):
        if color[node] == WHITE:
            dfs(node, [])
    return errors


def audit_duplicate_ids(
    duplicate_ids: dict, severity_levels: dict
) -> list[tuple[str, str, str]]:
    """
    Evaluate duplicate document IDs across the repository to enforce the SSOT (Single Source of Truth) invariant.

    This auditor iterates over the duplicate map generated during the pre-scan phase. For every duplicated
    ID, it generates an error tuple pointing to the conflicting file paths.

    Returns:
        list[tuple[str, str, str]]: A list of (severity, message, filepath) tuples.
    """
    findings = []
    for dup_id, paths in sorted(duplicate_ids.items()):
        sev = severity_levels[SeverityRule.DUPLICATE_ID]
        findings.append(
            (
                sev,
                f"Duplicate document ID '{dup_id}' declared in multiple files: {', '.join(paths)}. "
                "Document IDs must be globally unique (SSOT).",
                paths[-1],
            )
        )
    return findings


def audit_hierarchy_tiers(
    all_doc_metadata: dict, severity_levels: dict
) -> list[tuple[str, str, str]]:
    """Enforce relationship source/target/cardinality/authority semantics from the registry."""
    findings = []
    sev = severity_levels[SeverityRule.STRUCTURAL_INTEGRITY_VIOLATION]

    for doc_id, meta in all_doc_metadata.items():
        if not isinstance(meta, dict):
            continue
        filepath = meta.get("_filepath", "Unknown")
        for finding in relationship_contract_findings(
            doc_id,
            meta,
            all_doc_metadata,
        ):
            if finding.code == "missing_required":
                continue
            findings.append((sev, finding.message, filepath))

    return findings


def audit_orphans(
    all_doc_metadata: dict, severity_levels: dict
) -> list[tuple[str, str, str]]:
    """Enforce minimum relationship cardinality from the canonical registry."""
    findings = []
    sev = severity_levels[SeverityRule.ORPHAN_DOCUMENT]

    for doc_id, meta in all_doc_metadata.items():
        if not isinstance(meta, dict):
            continue
        filepath = meta.get("_filepath", "Unknown")
        for finding in relationship_contract_findings(
            doc_id,
            meta,
            all_doc_metadata,
        ):
            if finding.code == "missing_required":
                findings.append((sev, finding.message, filepath))

    return findings
