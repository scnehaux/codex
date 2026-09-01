from __future__ import annotations

from pathlib import Path
import sys
from types import MappingProxyType

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from engine.control.repository import RepositoryAssembler, RepositoryModelError
from engine.core.repository import RepositoryArtifact, RepositoryModel

OUTPUT_RELATIVE_PATH = Path("03-domain") / "TRACEABILITY.md"

_STYLE_CLASS = MappingProxyType(
    {
        "EAD": "ead",
        "STD": "std",
        "PAD": "pad",
        "SAD": "sad",
        "ADR": "adr",
        "TDD": "tdd",
    }
)

_STYLE_DEFINITIONS = (
    "    classDef ead fill:#059669,stroke:#047857,color:#fff",
    "    classDef std fill:#0891b2,stroke:#0e7490,color:#fff",
    "    classDef pad fill:#2563eb,stroke:#1d4ed8,color:#fff",
    "    classDef sad fill:#7c3aed,stroke:#6d28d9,color:#fff",
    "    classDef adr fill:#d97706,stroke:#b45309,color:#fff",
    "    classDef tdd fill:#4f46e5,stroke:#4338ca,color:#fff",
)


def _architecture_records(
    snapshot: RepositoryModel,
) -> tuple[tuple[RepositoryArtifact, str], ...]:
    records = [
        (record, record.artifact_type)
        for record in snapshot.artifacts
        if record.artifact_type != "GDC"
    ]
    return tuple(
        sorted(
            records,
            key=lambda item: (item[1], item[0].document_id, item[0].path),
        )
    )


def _graph_edges(
    records: tuple[tuple[RepositoryArtifact, str], ...],
) -> tuple[tuple[str, str, str], ...]:
    edges = {
        (
            record.document_id,
            relationship.target.artifact_id,
            relationship.relation_type,
        )
        for record, _ in records
        for relationship in record.artifact.relationships
    }
    return tuple(sorted(edges))


def render_graph(snapshot: RepositoryModel) -> str:
    """Render repository traceability using only canonical model + ontology."""
    records = _architecture_records(snapshot)

    node_ids = {
        record.document_id: f"n{index}"
        for index, (record, _) in enumerate(records)
        if record.document_id is not None
    }

    external_targets = sorted(
        {
            target_id
            for _, target_id, _ in _graph_edges(records)
            if target_id not in node_ids
        }
    )
    external_node_ids = {
        target_id: f"x{index}"
        for index, target_id in enumerate(external_targets)
    }

    out = [
        "```mermaid",
        "%%{init: {'theme': 'neutral'}}%%",
        "graph LR",
    ]

    current_type = None
    for record, artifact_type in records:
        document_id = record.document_id
        if artifact_type != current_type:
            out.append(f"    %% {artifact_type} Layer")
            current_type = artifact_type

        style_class = _STYLE_CLASS.get(artifact_type, "artifact")
        out.append(
            f'    {node_ids[document_id]}["{document_id}"]:::{style_class}'
        )

    if external_targets:
        out.append("    %% External Relationship Targets")
        for target_id in external_targets:
            out.append(
                f'    {external_node_ids[target_id]}["{target_id}"]:::external'
            )

    edges = _graph_edges(records)
    if edges:
        out.append("    %% Canonical Relationships")

    for source_id, target_id, field in edges:
        source_node = node_ids[source_id]
        target_node = node_ids.get(target_id, external_node_ids.get(target_id))
        if target_node is None:
            continue
        out.append(f"    {source_node} -->|{field}| {target_node}")

    out.extend(_STYLE_DEFINITIONS)
    out.extend(
        [
            "    classDef artifact fill:#475569,stroke:#334155,color:#fff",
            "    classDef external fill:#fff,stroke:#64748b,color:#0f172a",
            "```",
        ]
    )

    return "\n".join(out)


def _atomic_write_text(path: Path, content: str) -> None:
    temp_path = path.with_name(f".{path.name}.tmp")

    try:
        temp_path.write_text(content, encoding="utf-8", newline="\n")
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def generate_graph(
    repo_root: str | Path | None = None,
) -> Path | None:
    """Generate traceability graph from the canonical RepositoryModel."""
    root = (
        Path(repo_root).resolve()
        if repo_root is not None
        else Path(__file__).resolve().parents[2]
    )

    snapshot = RepositoryAssembler.load_governed_corpus(repo_root=root)
    records = _architecture_records(snapshot)

    # TRACEABILITY.md belongs to the domain plane. Governance-only, EAD-only,
    # and STD-only repositories must not manufacture an empty 03-domain tree.
    has_domain_corpus = any(
        artifact_type in {"PAD", "SAD"}
        for _, artifact_type in records
    )
    if not has_domain_corpus:
        print("[SKIP] No domain architecture corpus; traceability graph not generated")
        return None

    output_path = root / OUTPUT_RELATIVE_PATH
    if not output_path.parent.is_dir():
        raise RepositoryModelError(
            "Traceability output blocked: domain corpus exists but "
            f"'{output_path.parent}' is missing."
        )

    rendered = "# Architecture Traceability Graph\n\n" + render_graph(snapshot) + "\n"
    _atomic_write_text(output_path, rendered)

    print(f"[OK] Generated Traceability Graph -> {output_path}")
    return output_path


def main() -> int:
    try:
        generate_graph()
    except (RepositoryModelError, OSError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
