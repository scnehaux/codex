from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Mapping

import yaml


REQUIRED_CONTROL_KEYS = frozenset(
    {
        "temporary_tooling",
        "genesis_integrity",
        "version_mutation_integrity",
        "genesis_commit_qualification",
        "github_enforcement",
    }
)
TEMPORARY_PATTERNS = ("phase*.py", "slice5_*.py")
PERMANENT_PREFIXES = (
    "governance/",
    "schemas/",
    "templates/",
    ".github/",
    "engine/",
    "generators/",
    "scripts/",
    "tests/",
)
PERMANENT_ROOT_FILES = frozenset(
    {
        "conftest.py",
        "Makefile",
        "pyproject.toml",
    }
)


@dataclass(frozen=True, slots=True)
class ReadinessFinding:
    code: str
    path: str
    message: str


@dataclass(frozen=True, slots=True)
class GovernanceReadinessReport:
    checked_controls: tuple[str, ...]
    findings: tuple[ReadinessFinding, ...]

    @property
    def ok(self) -> bool:
        return not self.findings


def _load_mapping(
    path: Path,
) -> tuple[Mapping[str, Any] | None, tuple[ReadinessFinding, ...]]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return None, (
            ReadinessFinding(
                code="yaml-load-failed",
                path=path.as_posix(),
                message=str(exc),
            ),
        )

    if not isinstance(data, dict):
        return None, (
            ReadinessFinding(
                code="yaml-root-invalid",
                path=path.as_posix(),
                message="YAML root must be a mapping",
            ),
        )

    return data, ()


def _normalize(value: str) -> str:
    return value.replace("\\", "/").removeprefix("./")


def _temporary(path: str) -> bool:
    name = Path(_normalize(path)).name
    return any(fnmatch(name, pattern) for pattern in TEMPORARY_PATTERNS)


def _permanent_path(path: str) -> bool:
    normalized = _normalize(path)
    return normalized in PERMANENT_ROOT_FILES or any(
        normalized.startswith(prefix) for prefix in PERMANENT_PREFIXES
    )


def _path_findings(
    root: Path,
    control_key: str,
    field: str,
    values: object,
) -> tuple[ReadinessFinding, ...]:
    if not isinstance(values, list) or not values:
        return (
            ReadinessFinding(
                code="evidence-list-invalid",
                path=control_key,
                message=f"{field} must be a non-empty list",
            ),
        )

    findings: list[ReadinessFinding] = []

    for raw in values:
        if not isinstance(raw, str) or not raw.strip():
            findings.append(
                ReadinessFinding(
                    code="evidence-path-invalid",
                    path=control_key,
                    message=f"{field} contains a non-string/blank path",
                )
            )
            continue

        normalized = _normalize(raw)

        if _temporary(normalized):
            findings.append(
                ReadinessFinding(
                    code="temporary-evidence-forbidden",
                    path=normalized,
                    message=f"{control_key}.{field} references temporary tooling",
                )
            )
            continue

        if not _permanent_path(normalized):
            findings.append(
                ReadinessFinding(
                    code="evidence-path-outside-permanent-roots",
                    path=normalized,
                    message=f"{control_key}.{field} is outside permanent roots",
                )
            )
            continue

        if not (root / normalized).is_file():
            findings.append(
                ReadinessFinding(
                    code="evidence-path-missing",
                    path=normalized,
                    message=f"{control_key}.{field} path does not exist",
                )
            )

    return tuple(findings)


def _makefile_target_findings(
    text: str,
    target: str,
    command: str,
) -> tuple[ReadinessFinding, ...]:
    marker = f"{target}:"
    if marker not in text:
        return (
            ReadinessFinding(
                code="makefile-target-missing",
                path="Makefile",
                message=f"missing target {target}",
            ),
        )

    lines = text.splitlines()
    index = next(i for i, line in enumerate(lines) if line.strip() == marker)
    body = lines[index + 1 : index + 4]

    if not any(command in line for line in body):
        return (
            ReadinessFinding(
                code="makefile-command-mismatch",
                path="Makefile",
                message=f"{target} must invoke {command}",
            ),
        )

    return ()


def audit_governance_readiness(
    repo_root: str | Path,
) -> GovernanceReadinessReport:
    root = Path(repo_root).resolve()
    findings: list[ReadinessFinding] = []

    source_layout_path = root / "governance" / "framework" / "source-layout.yaml"
    bootstrap_path = root / "governance" / "bootstrap-manifest.yaml"
    makefile_path = root / "Makefile"

    source_layout, layout_findings = _load_mapping(source_layout_path)
    bootstrap, bootstrap_findings = _load_mapping(bootstrap_path)
    findings.extend(layout_findings)
    findings.extend(bootstrap_findings)

    checked_controls: tuple[str, ...] = ()

    if source_layout is not None:
        qualification = source_layout.get("governance_qualification")

        if not isinstance(qualification, dict):
            findings.append(
                ReadinessFinding(
                    code="qualification-contract-missing",
                    path=source_layout_path.as_posix(),
                    message="governance_qualification must be a mapping",
                )
            )
        else:
            controls = qualification.get("required_controls")

            if not isinstance(controls, dict):
                findings.append(
                    ReadinessFinding(
                        code="required-controls-invalid",
                        path=source_layout_path.as_posix(),
                        message="required_controls must be a mapping",
                    )
                )
            else:
                checked_controls = tuple(sorted(controls))
                missing = sorted(REQUIRED_CONTROL_KEYS - set(controls))

                for control_key in missing:
                    findings.append(
                        ReadinessFinding(
                            code="required-control-missing",
                            path=control_key,
                            message="required P1 governance control is missing",
                        )
                    )

                for control_key, closure in controls.items():
                    if not isinstance(closure, dict):
                        findings.append(
                            ReadinessFinding(
                                code="control-closure-invalid",
                                path=str(control_key),
                                message="control closure must be a mapping",
                            )
                        )
                        continue

                    policy_ref = closure.get("policy_ref")
                    if not isinstance(policy_ref, str) or not isinstance(
                        source_layout.get(policy_ref), dict
                    ):
                        findings.append(
                            ReadinessFinding(
                                code="policy-reference-invalid",
                                path=str(control_key),
                                message=f"policy_ref {policy_ref!r} does not resolve",
                            )
                        )

                    findings.extend(
                        _path_findings(
                            root,
                            str(control_key),
                            "implementation",
                            closure.get("implementation"),
                        )
                    )
                    findings.extend(
                        _path_findings(
                            root,
                            str(control_key),
                            "test_evidence",
                            closure.get("test_evidence"),
                        )
                    )

            authority = qualification.get("authority")
            invocation = qualification.get("invocation")

            for field, value in (
                ("authority", authority),
                ("invocation", invocation),
            ):
                if (
                    not isinstance(value, str)
                    or not _permanent_path(value)
                    or not (root / _normalize(value)).is_file()
                ):
                    findings.append(
                        ReadinessFinding(
                            code="qualification-entrypoint-invalid",
                            path=str(value),
                            message=f"governance_qualification.{field} is invalid",
                        )
                    )

    if bootstrap is not None:
        contract = bootstrap.get("genesis_contract")
        governance = bootstrap.get("governance_control_plane")
        provenance = bootstrap.get("provenance")

        if not isinstance(contract, dict):
            findings.append(
                ReadinessFinding(
                    code="bootstrap-contract-invalid",
                    path=bootstrap_path.as_posix(),
                    message="genesis_contract must be a mapping",
                )
            )
        else:
            if contract.get("local_qualification_required") is not True:
                findings.append(
                    ReadinessFinding(
                        code="local-qualification-not-required",
                        path=bootstrap_path.as_posix(),
                        message="local qualification must be required",
                    )
                )

            if contract.get("local_qualification_entrypoint") != (
                "scripts/governance_qualify.py"
            ):
                findings.append(
                    ReadinessFinding(
                        code="local-qualification-entrypoint-mismatch",
                        path=bootstrap_path.as_posix(),
                        message="bootstrap must point to permanent governance qualifier",
                    )
                )

        if (
            not isinstance(governance, dict)
            or governance.get("architecture_admission") != "closed"
            or governance.get("lifecycle") != "draft"
            or governance.get("version_series") != "0.x.x"
        ):
            findings.append(
                ReadinessFinding(
                    code="bootstrap-governance-state-invalid",
                    path=bootstrap_path.as_posix(),
                    message="pre-Genesis governance must remain draft 0.x with admission closed",
                )
            )

        if (
            not isinstance(provenance, dict)
            or provenance.get("architecture_artifacts_admitted_in_genesis") is not False
        ):
            findings.append(
                ReadinessFinding(
                    code="bootstrap-provenance-invalid",
                    path=bootstrap_path.as_posix(),
                    message="Genesis must admit zero architecture artifacts",
                )
            )

    try:
        makefile_text = makefile_path.read_text(encoding="utf-8")
    except OSError as exc:
        findings.append(
            ReadinessFinding(
                code="makefile-read-failed",
                path="Makefile",
                message=str(exc),
            )
        )
    else:
        findings.extend(
            _makefile_target_findings(
                makefile_text,
                "genesis-check",
                "scripts/genesis_integrity.py",
            )
        )
        findings.extend(
            _makefile_target_findings(
                makefile_text,
                "mutation-check",
                "scripts/mutation_integrity.py",
            )
        )
        findings.extend(
            _makefile_target_findings(
                makefile_text,
                "governance-qualify",
                "scripts/governance_qualify.py",
            )
        )
        findings.extend(
            _makefile_target_findings(
                makefile_text,
                "mutation-ci-check",
                "scripts/committed_mutation_integrity.py",
            )
        )
        findings.extend(
            _makefile_target_findings(
                makefile_text,
                "github-policy-check",
                "scripts/github_policy_check.py",
            )
        )

    root_python = sorted(path.name for path in root.glob("*.py") if path.is_file())
    if root_python != ["conftest.py"]:
        findings.append(
            ReadinessFinding(
                code="repository-root-python-not-clean",
                path=".",
                message=f"root Python must be conftest.py only, found {root_python}",
            )
        )

    return GovernanceReadinessReport(
        checked_controls=checked_controls,
        findings=tuple(findings),
    )


def assert_governance_readiness(
    repo_root: str | Path,
) -> GovernanceReadinessReport:
    report = audit_governance_readiness(repo_root)

    if report.findings:
        raise RuntimeError(
            "Governance readiness audit failed:\n  - "
            + "\n  - ".join(
                f"[{finding.code}] {finding.path}: {finding.message}"
                for finding in report.findings
            )
        )

    return report
