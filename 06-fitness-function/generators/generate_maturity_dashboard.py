from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys

FITNESS_ROOT = Path(__file__).resolve().parents[1]
if str(FITNESS_ROOT) not in sys.path:
    sys.path.insert(0, str(FITNESS_ROOT))

from engine.control.governance.controls import (
    load_control_registry,
    registry_structure_errors,
)
from engine.control.repository import RepositoryAssembler, RepositoryModelError
from engine.core.repository import RepositoryModel


CONTROL_REGISTRY = Path("00-governance/normative-control-registry.yaml")
MATURITY_FILE = Path("MATURITY.md")
ARTIFACT_TYPES = ("GDC", "EAD", "STD", "PAD", "SAD", "ADR", "TDD")


def _artifact_inventory(snapshot) -> dict[str, int]:
    counts = Counter({artifact_type: 0 for artifact_type in ARTIFACT_TYPES})

    for record in snapshot.artifacts:
        artifact_type = record.artifact_type
        if artifact_type in counts:
            counts[artifact_type] += 1

    return dict(counts)


def _evidence_inventory(records) -> dict[str, int]:
    counts = Counter(record.evidence_status for record in records)
    return dict(sorted(counts.items()))


def render_dashboard(
    *,
    artifact_inventory: dict[str, int],
    evidence_inventory: dict[str, int],
    control_total: int,
    registry_findings: tuple[str, ...],
) -> str:
    lines = [
        "# Architecture Governance Evidence Dashboard",
        "",
        "> **Auto-generated** by "
        "`06-fitness-function/generators/generate_maturity_dashboard.py`",
        "",
        "> This dashboard separates repository inventory from governance evidence. "
        "Artifact presence or lifecycle status is not treated as proof of maturity "
        "or compliance.",
        "",
        "## 1. Repository Inventory",
        "",
        "| Artifact Type | Documents |",
        "| :--- | ---: |",
    ]

    for artifact_type in ARTIFACT_TYPES:
        lines.append(
            f"| {artifact_type} | {artifact_inventory.get(artifact_type, 0)} |"
        )

    lines.extend(
        [
            "",
            "## 2. Normative Control Evidence",
            "",
            f"- Total registered controls: **{control_total}**",
        ]
    )

    if evidence_inventory:
        for state, count in evidence_inventory.items():
            lines.append(f"- `{state}`: **{count}**")
    else:
        lines.append("- No evidence states recorded")

    lines.extend(
        [
            "",
            "## 3. Evidence Registry Integrity",
            "",
        ]
    )

    if registry_findings:
        lines.append(
            f"- Registry integrity: **FAIL** ({len(registry_findings)} finding(s))"
        )
        for finding in registry_findings:
            lines.append(f"  - {finding}")
    else:
        lines.append("- Registry integrity: **PASS**")

    lines.extend(
        [
            "",
            "## 4. Interpretation Contract",
            "",
            "- Inventory counts describe repository contents only",
            "- `verified` means the control registry contains verified evidence state",
            "- `pending` means evidence is not yet sufficient for verification",
            "- `gap` means the governance obligation lacks required control coverage or evidence",
            "- No CODEOWNERS, CI, schema, or compliance claim is emitted without explicit runtime evidence",
            "",
        ]
    )

    return "\n".join(lines)


def _atomic_write_text(path: Path, content: str) -> None:
    temp_path = path.with_name(f".{path.name}.tmp")
    try:
        temp_path.write_text(content, encoding="utf-8", newline="\n")
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def generate_dashboard(
    repo_root: str | Path | None = None,
) -> Path:
    root = (
        Path(repo_root).resolve()
        if repo_root is not None
        else Path(__file__).resolve().parents[2]
    )

    snapshot = RepositoryAssembler.load_governed_corpus(repo_root=root)

    registry_path = root / CONTROL_REGISTRY
    if not registry_path.is_file():
        raise RepositoryModelError(
            "Canonical normative control registry is missing: "
            f"{registry_path}"
        )

    records = load_control_registry(registry_path)
    findings = registry_structure_errors(records)

    content = render_dashboard(
        artifact_inventory=_artifact_inventory(snapshot),
        evidence_inventory=_evidence_inventory(records),
        control_total=len(records),
        registry_findings=findings,
    )

    output_path = root / MATURITY_FILE
    _atomic_write_text(output_path, content)
    print(
        "[OK] Generated Governance Evidence Dashboard "
        f"({len(records)} controls) -> {output_path}"
    )
    return output_path


def main() -> int:
    try:
        generate_dashboard()
    except (RepositoryModelError, OSError, ValueError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
