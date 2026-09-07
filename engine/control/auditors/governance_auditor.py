from __future__ import annotations

import os
import re
import yaml

from engine.control.config.severity import SeverityRule


def _major(version: object) -> int | None:
    match = re.match(r"^(\d+)\.", str(version or "").strip())
    return int(match.group(1)) if match else None


def audit_architecture_admission(
    all_doc_metadata: dict,
    severity_levels: dict,
    repo_root: str,
) -> list[tuple[str, str, str]]:
    # Enforce the bootstrap architecture-admission boundary.
    manifest_path = os.path.join(repo_root, "governance", "bootstrap-manifest.yaml")
    if not os.path.exists(manifest_path):
        return []

    severity = severity_levels[SeverityRule.ARCHITECTURE_ADMISSION_VIOLATION]

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = yaml.safe_load(f) or {}
    except Exception as exc:
        return [
            (
                severity,
                f"Governance bootstrap manifest is unreadable: {exc}",
                manifest_path,
            )
        ]

    control = manifest.get("governance_control_plane", {})
    state = str(control.get("architecture_admission", "")).strip().lower()
    required_ids = control.get("required_baseline_ids", [])

    if state not in {"closed", "open"}:
        return [
            (
                severity,
                "governance_control_plane.architecture_admission must be 'closed' or 'open'.",
                manifest_path,
            )
        ]

    architecture_docs = [
        doc_id
        for doc_id in sorted(all_doc_metadata)
        if not str(doc_id).upper().startswith("GDC-")
    ]

    if state == "closed":
        if not architecture_docs:
            return []
        return [
            (
                severity,
                "Architecture admission is CLOSED while the Governance Control Plane is "
                "pre-baseline. Found architecture artifacts: "
                + ", ".join(architecture_docs),
                manifest_path,
            )
        ]

    findings = []
    if not isinstance(required_ids, list) or not required_ids:
        findings.append("required_baseline_ids must be a non-empty list")

    for doc_id in required_ids if isinstance(required_ids, list) else []:
        meta = all_doc_metadata.get(doc_id)
        if not meta:
            findings.append(f"{doc_id} is missing")
            continue

        status = str(meta.get("status", "")).strip().lower()
        major = _major(meta.get("version"))

        if status != "approved":
            findings.append(
                f"{doc_id} status is '{status or 'missing'}', expected 'approved'"
            )
        if major is None or major < 1:
            findings.append(
                f"{doc_id} version is '{meta.get('version', '')}', expected >=1.0.0"
            )

    if findings:
        return [
            (
                severity,
                "Architecture admission cannot be OPEN because the declared Governance "
                "Control Plane baseline is not stable: " + "; ".join(findings),
                manifest_path,
            )
        ]

    return []
