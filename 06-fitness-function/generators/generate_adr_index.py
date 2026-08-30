from __future__ import annotations

from pathlib import Path
import sys

FITNESS_ROOT = Path(__file__).resolve().parents[1]
if str(FITNESS_ROOT) not in sys.path:
    sys.path.insert(0, str(FITNESS_ROOT))

from engine.control.repository import RepositoryAssembler, RepositoryModelError
from engine.core.repository import RepositoryArtifact, RepositoryModel


ADR_ROOT = Path("05-decisions")
ADR_INDEX = ADR_ROOT / "INDEX.md"


def _adr_records(
    snapshot: RepositoryModel,
) -> tuple[RepositoryArtifact, ...]:
    records = []

    for record in snapshot.artifacts:
        document_id = record.document_id
        if record.artifact_type == "ADR":
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


def _relative_link(record: RepositoryArtifact) -> str:
    path = Path(record.path)
    try:
        return path.relative_to(ADR_ROOT).as_posix()
    except ValueError as exc:
        raise RepositoryModelError(
            f"ADR artifact '{record.path}' is outside expected layer "
            f"'{ADR_ROOT.as_posix()}'."
        ) from exc


def _cell(value, default: str = "N/A") -> str:
    if value is None or value == "":
        return default
    return str(value)


def _escape_markdown_cell(value) -> str:
    return _cell(value).replace("|", r"\|")


def render_index(records: tuple[RepositoryArtifact, ...]) -> str:
    lines = [
        "# Architectural Decision Records (ADR) Index",
        "",
        "This is the authoritative index of all Architectural Decision Records "
        "within the Scnehaux enterprise.",
        "",
        "| ID | Title | Type | Status | Created | Expiry Date |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for record in records:
        meta = record.metadata
        document_id = record.document_id or "N/A"
        link = _relative_link(record)

        lines.append(
            f"| [{document_id}]({link}) | "
            f"{_escape_markdown_cell(meta.get('title'))} | "
            f"{_cell(meta.get('adr_type'))} | "
            f"{_cell(meta.get('status'))} | "
            f"{_cell(meta.get('created'))} | "
            f"{_cell(meta.get('expiry_date'))} |"
        )

    return "\n".join(lines) + "\n"


def _atomic_write_text(path: Path, content: str) -> None:
    temp_path = path.with_name(f".{path.name}.tmp")
    try:
        temp_path.write_text(content, encoding="utf-8", newline="\n")
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def generate_index(
    repo_root: str | Path | None = None,
) -> Path | None:
    root = (
        Path(repo_root).resolve()
        if repo_root is not None
        else Path(__file__).resolve().parents[2]
    )

    snapshot = RepositoryAssembler.load_governed_corpus(repo_root=root)
    records = _adr_records(snapshot)

    if not records:
        print(
            "[SKIP] No ADR corpus; "
            "05-decisions/INDEX.md not generated"
        )
        return None

    output_dir = root / ADR_ROOT
    if not output_dir.is_dir():
        raise RepositoryModelError(
            "ADR corpus exists but expected layer directory "
            f"'{output_dir}' is missing."
        )

    output_path = root / ADR_INDEX
    rendered = render_index(records)
    _atomic_write_text(output_path, rendered)

    print(
        f"[OK] Generated ADR Index ({len(records)} records) "
        f"-> {output_path}"
    )
    return output_path


def main() -> int:
    try:
        generate_index()
    except (RepositoryModelError, OSError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
