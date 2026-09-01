from __future__ import annotations

from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from engine.control.repository import RepositoryAssembler, RepositoryModelError
from engine.core.repository import RepositoryArtifact, RepositoryModel


_LAYER_CONFIG = {
    "PAD": (
        Path("03-domain"),
        "Platform Architecture (PAD)",
    ),
    "SAD": (
        Path("04-system"),
        "Software Architecture (SAD)",
    ),
}


def _records_for_type(
    snapshot: RepositoryModel,
    artifact_type: str,
) -> tuple[RepositoryArtifact, ...]:
    records = []

    for record in snapshot.artifacts:
        document_id = record.document_id
        if record.artifact_type == artifact_type:
            records.append(record)

    return tuple(
        sorted(
            records,
            key=lambda record: (
                record.document_id or "",
                record.path,
            ),
        )
    )


def _relative_link(record: RepositoryArtifact, layer_root: Path) -> str:
    path = Path(record.path)
    try:
        return path.relative_to(layer_root).as_posix()
    except ValueError as exc:
        raise RepositoryModelError(
            f"Artifact '{record.path}' is outside expected layer "
            f"'{layer_root.as_posix()}'."
        ) from exc


def _relation_count(value) -> int:
    if value is None:
        return 0
    if isinstance(value, (list, tuple)):
        return len(value)
    return 1


def _render_parent_pad(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value)
    return str(value)


def render_index(
    records: tuple[RepositoryArtifact, ...],
    *,
    artifact_type: str,
    layer_root: Path,
    layer_name: str,
) -> str:
    out = [
        f"# {layer_name} Layer Index",
        "",
        "> **Auto-generated**: This file is maintained by "
        "`06-fitness-function/generators/generate_pad_sad_index.py`.",
        "",
    ]

    if artifact_type == "PAD":
        out.extend(
            [
                "| ID | Title | Owner | Status | Fulfilled By (SADs) |",
                "|---|---|---|---|---|",
            ]
        )
        for record in records:
            meta = record.metadata
            document_id = record.document_id or ""
            link = _relative_link(record, layer_root)
            out.append(
                f"| [{document_id}]({link}) | "
                f"{meta.get('title', '')} | "
                f"{meta.get('owner', '')} | "
                f"{meta.get('status', '')} | "
                f"{_relation_count(meta.get('fulfilled_by'))} |"
            )
    elif artifact_type == "SAD":
        out.extend(
            [
                "| ID | Title | Parent PAD | Owner | Status |",
                "|---|---|---|---|---|",
            ]
        )
        for record in records:
            meta = record.metadata
            document_id = record.document_id or ""
            link = _relative_link(record, layer_root)
            out.append(
                f"| [{document_id}]({link}) | "
                f"{meta.get('title', '')} | "
                f"{_render_parent_pad(meta.get('parent_pad'))} | "
                f"{meta.get('owner', '')} | "
                f"{meta.get('status', '')} |"
            )
    else:
        raise RepositoryModelError(
            f"Unsupported index artifact type: {artifact_type}"
        )

    return "\n".join(out) + "\n"


def _atomic_write_text(path: Path, content: str) -> None:
    temp_path = path.with_name(f".{path.name}.tmp")
    try:
        temp_path.write_text(content, encoding="utf-8", newline="\n")
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def generate_indexes(
    repo_root: str | Path | None = None,
) -> tuple[Path, ...]:
    root = (
        Path(repo_root).resolve()
        if repo_root is not None
        else Path(__file__).resolve().parents[2]
    )

    snapshot = RepositoryAssembler.load_governed_corpus(repo_root=root)

    generated = []

    for artifact_type in ("PAD", "SAD"):
        layer_root, layer_name = _LAYER_CONFIG[artifact_type]
        records = _records_for_type(snapshot, artifact_type)

        if not records:
            print(
                f"[SKIP] No {artifact_type} corpus; "
                f"{layer_root.as_posix()}/INDEX.md not generated"
            )
            continue

        output_dir = root / layer_root
        if not output_dir.is_dir():
            raise RepositoryModelError(
                f"{artifact_type} corpus exists but expected layer directory "
                f"'{output_dir}' is missing."
            )

        output_path = output_dir / "INDEX.md"
        rendered = render_index(
            records,
            artifact_type=artifact_type,
            layer_root=layer_root,
            layer_name=layer_name,
        )
        _atomic_write_text(output_path, rendered)
        generated.append(output_path)
        print(f"[OK] Generated {artifact_type} Index -> {output_path}")

    return tuple(generated)


def main() -> int:
    try:
        generate_indexes()
    except (RepositoryModelError, OSError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
