from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


TRUST_CONTRACT_PATH = Path("governance/scm/trust-boundary.yaml")
_ALLOWED_TOP_LEVEL = frozenset(
    {
        "contract_version",
        "kind",
        "provider_neutral",
        "candidate_state",
        "required_external_authority",
        "protected_concerns",
        "evidence",
    }
)
_REQUIRED_CAPABILITIES = frozenset(
    {
        "block-guardrail-self-authorization",
        "protect-governance-critical-mutations",
    }
)
_REQUIRED_CONCERNS = frozenset(
    {
        "ci-definition",
        "ownership-definition",
        "provider-policy-projection",
        "governance-enforcement-code",
        "governance-entrypoint",
    }
)


@dataclass(frozen=True, slots=True)
class SCMTrustFinding:
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class SCMTrustBoundaryReport:
    path: str
    findings: tuple[SCMTrustFinding, ...]

    @property
    def ok(self) -> bool:
        return not self.findings


def _f(code: str, message: str) -> SCMTrustFinding:
    return SCMTrustFinding(code, message)


def audit_scm_trust_boundary(repo_root: str | Path) -> SCMTrustBoundaryReport:
    path = Path(repo_root).resolve() / TRUST_CONTRACT_PATH

    try:
        data: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return SCMTrustBoundaryReport(
            TRUST_CONTRACT_PATH.as_posix(),
            (_f("trust-contract-load-failed", str(exc)),),
        )

    if not isinstance(data, dict):
        return SCMTrustBoundaryReport(
            TRUST_CONTRACT_PATH.as_posix(),
            (
                _f(
                    "trust-contract-root-invalid",
                    "SCM trust-boundary YAML root must be a mapping",
                ),
            ),
        )

    findings: list[SCMTrustFinding] = []

    unknown = sorted(set(data) - _ALLOWED_TOP_LEVEL)
    if unknown:
        findings.append(
            _f(
                "trust-contract-unknown-field",
                f"unknown top-level fields are forbidden: {unknown}",
            )
        )

    if data.get("contract_version") != 1:
        findings.append(
            _f("trust-contract-version-invalid", "contract_version must be 1")
        )

    if data.get("kind") != "scm-enforcement-trust-boundary":
        findings.append(
            _f(
                "trust-contract-kind-invalid",
                "kind must be scm-enforcement-trust-boundary",
            )
        )

    if data.get("provider_neutral") is not True:
        findings.append(
            _f(
                "provider-neutrality-required",
                "core SCM trust semantics must remain provider-neutral",
            )
        )

    candidate = data.get("candidate_state")
    if not isinstance(candidate, dict):
        findings.append(
            _f("candidate-state-invalid", "candidate_state must be a mapping")
        )
    else:
        if candidate.get("may_validate_candidate") is not True:
            findings.append(
                _f(
                    "candidate-validation-contract-invalid",
                    "candidate state may validate candidate code",
                )
            )
        if candidate.get("may_be_sole_guardrail_authority") is not False:
            findings.append(
                _f(
                    "candidate-self-authorization-forbidden",
                    "candidate repository state must never be sole guardrail authority",
                )
            )

    authority = data.get("required_external_authority")
    if not isinstance(authority, dict):
        findings.append(
            _f(
                "external-authority-invalid",
                "required_external_authority must be a mapping",
            )
        )
    else:
        if authority.get("required") is not True:
            findings.append(
                _f(
                    "external-authority-required",
                    "an external enforcement authority is mandatory",
                )
            )
        if authority.get("mutable_by_candidate") is not False:
            findings.append(
                _f(
                    "external-authority-candidate-mutable",
                    "external enforcement authority must not be mutable by candidate state",
                )
            )
        if authority.get("independently_administered") is not True:
            findings.append(
                _f(
                    "external-authority-not-independent",
                    "external enforcement authority must be independently administered",
                )
            )

        identity = authority.get("identity_binding")
        if not isinstance(identity, dict):
            findings.append(
                _f(
                    "external-authority-identity-binding-invalid",
                    "external authority identity_binding must be a mapping",
                )
            )
        else:
            if identity.get("required") is not True:
                findings.append(
                    _f(
                        "external-authority-identity-binding-required",
                        "effective external authority identity must be explicitly bound",
                    )
                )
            if identity.get("candidate_may_define_desired_binding") is not True:
                findings.append(
                    _f(
                        "desired-binding-contract-invalid",
                        "candidate state may propose desired provider binding",
                    )
                )
            if identity.get("candidate_may_select_effective_identity") is not False:
                findings.append(
                    _f(
                        "candidate-effective-identity-selection-forbidden",
                        "candidate state must not select effective external authority identity",
                    )
                )

        runtime = authority.get("evaluator_runtime")
        if not isinstance(runtime, dict):
            findings.append(
                _f(
                    "external-authority-runtime-invalid",
                    "external authority evaluator_runtime must be a mapping",
                )
            )
        else:
            if runtime.get("candidate_revision_as_authority") is not False:
                findings.append(
                    _f(
                        "candidate-revision-authority-forbidden",
                        "candidate revision must not execute as the external authority",
                    )
                )
            if runtime.get("candidate_auto_deploy") is not False:
                findings.append(
                    _f(
                        "candidate-auto-deploy-forbidden",
                        "candidate state must not auto-deploy the authority evaluator",
                    )
                )
            if runtime.get("privileged_promotion_required") is not True:
                findings.append(
                    _f(
                        "privileged-authority-promotion-required",
                        "authority evaluator promotion must cross a privileged external boundary",
                    )
                )

        caps = authority.get("capabilities")
        if not isinstance(caps, list):
            findings.append(
                _f(
                    "external-authority-capabilities-invalid",
                    "external authority capabilities must be a list",
                )
            )
        else:
            missing = sorted(_REQUIRED_CAPABILITIES - set(caps))
            if missing:
                findings.append(
                    _f(
                        "external-authority-capability-missing",
                        f"missing external authority capabilities: {missing}",
                    )
                )

    concerns = data.get("protected_concerns")
    if not isinstance(concerns, list):
        findings.append(
            _f(
                "protected-concerns-invalid",
                "protected_concerns must be a list",
            )
        )
    else:
        missing = sorted(_REQUIRED_CONCERNS - set(concerns))
        if missing:
            findings.append(
                _f(
                    "protected-concern-missing",
                    f"missing protected concerns: {missing}",
                )
            )

    evidence = data.get("evidence")
    if not isinstance(evidence, dict):
        findings.append(_f("trust-evidence-invalid", "evidence must be a mapping"))
    else:
        if evidence.get("proves_effective_enforcement") is not False:
            findings.append(
                _f(
                    "effective-enforcement-claim-forbidden",
                    "design-time trust contract must not claim effective enforcement",
                )
            )
        if evidence.get("activation_slice") != "10.10":
            findings.append(
                _f(
                    "activation-slice-invalid",
                    "effective provider activation belongs to Slice 10.10",
                )
            )

    return SCMTrustBoundaryReport(
        TRUST_CONTRACT_PATH.as_posix(),
        tuple(findings),
    )


def assert_scm_trust_boundary(repo_root: str | Path) -> SCMTrustBoundaryReport:
    report = audit_scm_trust_boundary(repo_root)

    if report.findings:
        raise RuntimeError(
            "SCM enforcement trust-boundary audit failed:\n  - "
            + "\n  - ".join(
                f"[{finding.code}] {finding.message}" for finding in report.findings
            )
        )

    return report
