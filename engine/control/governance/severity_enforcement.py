from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from engine.control.config.severity import SeverityRule


VALID_EVIDENCE_STATUS = frozenset({"verified", "pending"})
VALID_ENFORCEMENT_KINDS = frozenset(
    {
        "runtime-rule",
        "schema-translation",
        "dynamic-config",
        "auditor",
        "cli-fatal",
        "deferred",
    }
)


@dataclass(frozen=True)
class SeverityEnforcementRecord:
    rule_id: str
    evidence_status: str
    enforcement_kind: str
    implementation: tuple[str, ...]
    test_evidence: tuple[str, ...]
    control_owner: str
    target_phase: str
    rationale: str


def load_severity_enforcement_registry(
    path: str | Path,
) -> tuple[SeverityEnforcementRecord, ...]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("rules"), list):
        raise ValueError("Severity Enforcement Registry must contain a 'rules' list")

    records: list[SeverityEnforcementRecord] = []
    for raw in data["rules"]:
        if not isinstance(raw, dict):
            raise ValueError("Severity Enforcement Registry entries must be mappings")
        records.append(
            SeverityEnforcementRecord(
                rule_id=str(raw.get("rule_id", "")),
                evidence_status=str(raw.get("evidence_status", "")),
                enforcement_kind=str(raw.get("enforcement_kind", "")),
                implementation=tuple(raw.get("implementation") or ()),
                test_evidence=tuple(raw.get("test_evidence") or ()),
                control_owner=str(raw.get("control_owner", "")),
                target_phase=str(raw.get("target_phase", "")),
                rationale=str(raw.get("rationale", "")),
            )
        )
    return tuple(records)


def _evidence_path_exists(repo_root: Path, value: str) -> bool:
    candidate = value.split("::", 1)[0].split("#", 1)[0].strip()
    return bool(candidate) and (repo_root / candidate).exists()


def severity_registry_findings(
    repo_root: str | Path,
    severity_levels: dict,
) -> tuple[str, ...]:
    root = Path(repo_root).resolve()
    registry_path = root / "governance" / "severity-enforcement-registry.yaml"

    try:
        records = load_severity_enforcement_registry(registry_path)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return (f"F09 severity enforcement registry invalid: {exc}",)

    findings: list[str] = []
    declared = {item.value for item in SeverityRule}
    configured = set(severity_levels)
    record_ids = [record.rule_id for record in records]
    registry_ids = set(record_ids)

    duplicates = sorted(
        rule_id for rule_id in registry_ids if record_ids.count(rule_id) > 1
    )
    for rule_id in duplicates:
        findings.append(f"F09 {rule_id}: duplicate severity enforcement record")

    for rule_id in sorted(declared - configured):
        findings.append(f"F09 {rule_id}: SeverityRule missing schema severity mapping")
    for rule_id in sorted(configured - declared):
        findings.append(f"F09 {rule_id}: schema severity has no SeverityRule")
    for rule_id in sorted(declared - registry_ids):
        findings.append(f"F09 {rule_id}: missing severity enforcement record")
    for rule_id in sorted(registry_ids - declared):
        findings.append(f"F09 {rule_id}: registry entry has no SeverityRule")

    for record in records:
        if not record.rule_id:
            findings.append("F09 severity enforcement record missing rule_id")
            continue

        if record.evidence_status not in VALID_EVIDENCE_STATUS:
            findings.append(
                f"F09 {record.rule_id}: invalid evidence_status "
                f"{record.evidence_status!r}"
            )
        if record.enforcement_kind not in VALID_ENFORCEMENT_KINDS:
            findings.append(
                f"F09 {record.rule_id}: invalid enforcement_kind "
                f"{record.enforcement_kind!r}"
            )
        if not record.rationale:
            findings.append(f"F09 {record.rule_id}: missing rationale")

        if record.evidence_status == "verified":
            if record.enforcement_kind == "deferred":
                findings.append(
                    f"F09 {record.rule_id}: verified rule cannot be deferred"
                )
            if not record.implementation:
                findings.append(
                    f"F09 {record.rule_id}: verified rule missing implementation"
                )
            if not record.test_evidence:
                findings.append(
                    f"F09 {record.rule_id}: verified rule missing test evidence"
                )
            for evidence in (*record.implementation, *record.test_evidence):
                if not _evidence_path_exists(root, evidence):
                    findings.append(
                        f"F09 {record.rule_id}: evidence path does not exist: "
                        f"{evidence}"
                    )

        if record.evidence_status == "pending":
            if not record.control_owner:
                findings.append(
                    f"F09 {record.rule_id}: pending rule missing control_owner"
                )
            if not record.target_phase:
                findings.append(
                    f"F09 {record.rule_id}: pending rule missing target_phase"
                )

    return tuple(findings)
