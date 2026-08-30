from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import re

import yaml

MODAL_RE = re.compile(
    r"\b(MUST\s+NOT|SHALL\s+NOT|SHOULD\s+NOT|MUST|SHALL|SHOULD|MAY)\b",
    re.I,
)
NORMATIVE_MODALITIES = frozenset({"MUST", "MUST NOT", "SHALL", "SHALL NOT"})
ENFORCEMENT_MODES = frozenset(
    {"automated", "human-review", "process-control", "repository-control"}
)
EVIDENCE_STATES = frozenset({"verified", "pending", "gap"})
SEVERITIES = frozenset({"CRITICAL", "ERROR", "WARNING", "INFO"})


@dataclass(frozen=True)
class NormativeStatement:
    source_gdc: str
    source_file: str
    source_clause: str
    modality: str
    statement: str
    fingerprint: str


@dataclass(frozen=True)
class ControlRecord:
    control_id: str
    source_gdc: str
    source_file: str
    source_clause: str
    source_fingerprint: str
    modality: str
    statement: str
    scope: str
    severity: str
    enforcement_mode: str
    implementation: tuple[str, ...]
    test_evidence: tuple[str, ...]
    evidence_status: str
    evidence_expectation: str
    control_owner: str = ""
    target_phase: str = ""


def _strip_inline_markdown(text: str) -> str:
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[*_~]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_normative_statements(path: Path) -> tuple[NormativeStatement, ...]:
    lines = path.read_text(encoding="utf-8").splitlines()
    headings: list[tuple[int, str]] = []
    in_fence = False
    found: list[NormativeStatement] = []

    for raw in lines:
        stripped = raw.strip()

        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence or not stripped or stripped.startswith("|"):
            continue

        heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", stripped)
        if heading:
            level = len(heading.group(1))
            title = _strip_inline_markdown(heading.group(2))
            headings = [item for item in headings if item[0] < level]
            headings.append((level, title))
            continue

        modal = MODAL_RE.search(stripped)
        if not modal:
            continue

        modality = modal.group(1).upper().replace("  ", " ")
        if modality not in NORMATIVE_MODALITIES:
            continue

        statement = _strip_inline_markdown(
            re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", raw)
        )
        clause = " > ".join(title for _, title in headings) or "(document root)"
        parts = path.stem.split("-", 2)
        gdc_id = "-".join(parts[:2])
        fingerprint = hashlib.sha256(
            f"{path.name}|{clause}|{statement}".encode("utf-8")
        ).hexdigest()[:12]

        found.append(
            NormativeStatement(
                source_gdc=gdc_id,
                source_file=path.name,
                source_clause=clause,
                modality=modality,
                statement=statement,
                fingerprint=fingerprint,
            )
        )

    return tuple(found)


def load_control_registry(path: Path) -> tuple[ControlRecord, ...]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("Normative Control Registry must be a YAML mapping")

    controls = data.get("controls")
    if not isinstance(controls, list):
        raise RuntimeError("Normative Control Registry must contain a controls list")

    records: list[ControlRecord] = []
    for raw in controls:
        if not isinstance(raw, dict):
            raise RuntimeError("Each control entry must be a YAML mapping")
        records.append(
            ControlRecord(
                control_id=str(raw.get("control_id", "")),
                source_gdc=str(raw.get("source_gdc", "")),
                source_file=str(raw.get("source_file", "")),
                source_clause=str(raw.get("source_clause", "")),
                source_fingerprint=str(raw.get("source_fingerprint", "")),
                modality=str(raw.get("modality", "")),
                statement=str(raw.get("statement", "")),
                scope=str(raw.get("scope", "")),
                severity=str(raw.get("severity", "")),
                enforcement_mode=str(raw.get("enforcement_mode", "")),
                implementation=tuple(raw.get("implementation") or ()),
                test_evidence=tuple(raw.get("test_evidence") or ()),
                evidence_status=str(raw.get("evidence_status", "")),
                evidence_expectation=str(raw.get("evidence_expectation", "")),
                control_owner=str(raw.get("control_owner", "")),
                target_phase=str(raw.get("target_phase", "")),
            )
        )
    return tuple(records)


def registry_structure_errors(records: tuple[ControlRecord, ...]) -> tuple[str, ...]:
    errors: list[str] = []
    ids: set[str] = set()
    fingerprints: set[tuple[str, str]] = set()

    for record in records:
        if not re.fullmatch(r"CTRL-GDC-\d{3}-\d{3}", record.control_id):
            errors.append(f"Invalid control_id: {record.control_id!r}")
        elif record.control_id in ids:
            errors.append(f"Duplicate control_id: {record.control_id}")
        ids.add(record.control_id)

        fp_key = (record.source_gdc, record.source_fingerprint)
        if fp_key in fingerprints:
            errors.append(
                f"Duplicate source fingerprint: {record.source_gdc}/{record.source_fingerprint}"
            )
        fingerprints.add(fp_key)

        if record.modality not in NORMATIVE_MODALITIES:
            errors.append(f"{record.control_id}: invalid modality {record.modality!r}")
        if record.enforcement_mode not in ENFORCEMENT_MODES:
            errors.append(
                f"{record.control_id}: invalid enforcement_mode {record.enforcement_mode!r}"
            )
        if record.evidence_status not in EVIDENCE_STATES:
            errors.append(
                f"{record.control_id}: invalid evidence_status {record.evidence_status!r}"
            )
        if record.severity not in SEVERITIES:
            errors.append(f"{record.control_id}: invalid severity {record.severity!r}")
        if not record.scope:
            errors.append(f"{record.control_id}: missing scope")
        if not record.evidence_expectation:
            errors.append(f"{record.control_id}: missing evidence_expectation")

        if record.evidence_status in {"pending", "gap"}:
            if not record.control_owner:
                errors.append(
                    f"{record.control_id}: pending/gap control is missing control_owner"
                )
            if not record.target_phase:
                errors.append(
                    f"{record.control_id}: pending/gap control is missing target_phase"
                )

        if record.enforcement_mode != "automated" and not record.implementation:
            errors.append(
                f"{record.control_id}: non-automated control has no enforcement mechanism"
            )

        if record.enforcement_mode == "automated":
            if not record.implementation and record.evidence_status == "verified":
                errors.append(
                    f"{record.control_id}: verified automated control has no implementation mapping"
                )
            if record.evidence_status == "verified" and not record.test_evidence:
                errors.append(
                    f"{record.control_id}: verified automated control has no test evidence"
                )

    return tuple(errors)


def coverage_drift(
    statements: tuple[NormativeStatement, ...],
    records: tuple[ControlRecord, ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    source_keys = {(s.source_gdc, s.fingerprint) for s in statements}
    registry_keys = {
        (r.source_gdc, r.source_fingerprint)
        for r in records
    }

    missing = tuple(
        sorted(f"{gdc}/{fp}" for gdc, fp in source_keys - registry_keys)
    )
    stale = tuple(
        sorted(f"{gdc}/{fp}" for gdc, fp in registry_keys - source_keys)
    )
    return missing, stale
