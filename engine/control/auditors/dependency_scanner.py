"""
Audits synchronous runtime dependencies between architecture domains to prevent circular boundaries.

Extracts the 'Relationships' or 'Synchronous Dependencies' sections from PAD and SAD documents.
Uses a title-matching heuristic to resolve text references to other domains.
Builds a directed dependency graph and detects circular dependencies.
"""

from engine.control.parsing.markdown_ast import extract_section_contents
from engine.control.config.severity import SeverityRule


def build_dependency_graph(all_doc_metadata):
    """
    Builds a directed graph of dependencies between domains/systems.
    Returns:
        graph: dict mapping doc_id -> list of depended doc_ids.
        id_to_title: dict mapping doc_id -> title.
    """
    # 1. Build a map of title (lowercase) -> doc_id to match text references
    title_to_id = {}
    id_to_title = {}

    for doc_id, meta in all_doc_metadata.items():
        if not meta or "id" not in meta or "title" not in meta:
            continue
        doc_id = meta["id"]
        title = meta["title"]
        title_to_id[title.lower()] = doc_id
        # Also map the ID itself in case they reference by ID
        title_to_id[doc_id.lower()] = doc_id
        id_to_title[doc_id] = title

    graph = {doc_id: set() for doc_id in id_to_title.keys()}

    # 2. Extract dependency references from text
    for doc_id, meta in all_doc_metadata.items():
        if not meta or "id" not in meta:
            continue

        filepath = meta.get("_filepath")
        if not filepath:
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        doc_id = meta["id"]
        sections = extract_section_contents(content)

        # Look for the dependencies section
        dep_text = ""
        for sec_title, sec_body in sections.items():
            if (
                "relationships" in sec_title.lower()
                or "dependencies" in sec_title.lower()
            ):
                dep_text += sec_body.lower() + "\n"

        if not dep_text:
            continue

        # Extract lines that talk about Synchronous Dependencies (SRD)
        srd_text = ""
        for line in dep_text.split("\n"):
            if "srd" in line or "synchronous" in line or "depends on" in line:
                srd_text += line + "\n"

        if not srd_text:
            srd_text = dep_text  # fallback to scanning the whole relationship section

        # Find which other titles are mentioned in this text
        for title_lower, target_id in title_to_id.items():
            if target_id == doc_id:
                continue  # ignore self-references

            # If the title (e.g. 'integration platform' or 'pad-plt-006') appears in the text
            if title_lower in srd_text:
                graph[doc_id].add(target_id)

    return graph, id_to_title


def find_cycles(graph):
    """Finds all simple cycles in the directed graph."""
    cycles = []

    def dfs(node, path):
        if node in path:
            cycle = path[path.index(node) :] + [node]
            cycles.append(cycle)
            return

        path.append(node)
        for neighbor in graph.get(node, []):
            dfs(neighbor, path)
        path.pop()

    for start_node in graph:
        dfs(start_node, [])

    # Deduplicate cycles (A->B->A is same as B->A->B)
    unique_cycles = []
    seen = set()
    for c in cycles:
        c_tuple = tuple(sorted(c[:-1]))
        if c_tuple not in seen:
            seen.add(c_tuple)
            unique_cycles.append(c)

    return unique_cycles


def audit_circular_dependencies(all_doc_metadata: dict, severity_levels: dict):
    """
    Main auditor entrypoint.
    Returns:
        list of tuples: [(filepath, level, message), ...]
    """
    errors = []

    # ID -> Filepath map for reporting
    id_to_filepath = {}
    for doc_id, meta in all_doc_metadata.items():
        if meta and "id" in meta:
            id_to_filepath[meta["id"]] = meta.get("_filepath", meta["id"])

    graph, id_to_title = build_dependency_graph(all_doc_metadata)
    cycles = find_cycles(graph)

    for cycle in cycles:
        cycle_str = " -> ".join([str(id_to_title.get(n, n)) for n in cycle])
        # Report error on all files involved in the cycle
        for node in cycle[:-1]:
            filepath = id_to_filepath.get(node)
            if filepath:
                errors.append(
                    (
                        filepath,
                        severity_levels[SeverityRule.CIRCULAR_DEPENDENCY],
                        f"[circular_dependency] Circular runtime dependency detected: {cycle_str}. Architectural domains must form a DAG.",
                    )
                )

    return errors
