from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any, Mapping

import yaml

from engine.adapters.scm.github import GitHubProjectionFinding, audit_github_projection
from engine.control.governance.scm_policy import SCMEnforcementPolicy


REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
EVIDENCE_ROOT = ("governance", "github", "evidence")
LIVE_EVIDENCE_KIND = "scm-external-authority-live-provenance-evidence"
PUBLISHER_EVIDENCE_KIND = "scm-external-authority-publisher-evidence"


@dataclass(frozen=True, slots=True)
class GitHubActivationPlan:
    """Fail-closed activation material derived from governed desired state."""

    ruleset_payload: Mapping[str, Any] | None
    blockers: tuple[GitHubProjectionFinding, ...]
    integration_id: int | None
    authority_revision: str | None

    @property
    def ready(self) -> bool:
        return self.ruleset_payload is not None and not self.blockers


def _finding(code: str, message: str) -> GitHubProjectionFinding:
    return GitHubProjectionFinding(code=code, message=message)


def _is_revision(value: object) -> bool:
    return isinstance(value, str) and REVISION_RE.fullmatch(value) is not None


def _load_json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _resolve_evidence_path(root: Path, reference: object) -> Path | None:
    if not isinstance(reference, str) or not reference:
        return None
    pure = PurePosixPath(reference)
    if pure.is_absolute() or ".." in pure.parts or "\\" in reference:
        return None
    if tuple(pure.parts[:3]) != EVIDENCE_ROOT or pure.suffix != ".json":
        return None
    return root.joinpath(*pure.parts)


def _validate_live_provenance_evidence(
    root: Path,
    reference: object,
    policy: SCMEnforcementPolicy,
) -> tuple[dict[str, Any] | None, GitHubProjectionFinding | None]:
    path = _resolve_evidence_path(root, reference)
    if path is None:
        return None, _finding(
            "authority-live-provenance-evidence-unbound",
            "provider activation requires a governed live-provenance evidence JSON under governance/github/evidence",
        )
    try:
        evidence = _load_json_object(path)
        runtime_contract = _load_json_object(
            root / "integrations/github-governance-evaluator/runtime-promotion.json"
        )
        evaluator_contract = _load_json_object(
            root / "integrations/github-governance-evaluator/promotion.json"
        )
    except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
        return None, _finding(
            "authority-live-provenance-evidence-invalid",
            f"live-provenance evidence or source-promotion contract could not be loaded: {exc}",
        )

    source = evidence.get("source")
    execution = evidence.get("execution")
    observation = evidence.get("observation")
    attestation = evidence.get("attestation")
    self_report = evidence.get("source_runtime_self_report")
    qualification = (
        observation.get("candidate_qualification")
        if isinstance(observation, dict)
        else None
    )
    raw_verification = (
        execution.get("raw_blob_verification") if isinstance(execution, dict) else None
    )

    expected_source = {
        "runtime_source_revision": runtime_contract.get("runtime_source_revision"),
        "runtime_source_path": runtime_contract.get("runtime_source_path"),
        "runtime_source_blob": runtime_contract.get("runtime_source_blob"),
        "evaluator_source_revision": runtime_contract.get("evaluator_source_revision"),
        "evaluator_source_blob": runtime_contract.get("evaluator_source_blob"),
    }
    valid = (
        evidence.get("contract_version") == 1
        and evidence.get("kind") == LIVE_EVIDENCE_KIND
        and evidence.get("provider") == "github"
        and evidence.get("repository") == runtime_contract.get("repository")
        and isinstance(evidence.get("evidence_id"), str)
        and bool(evidence.get("evidence_id"))
        and source == expected_source
        and runtime_contract.get("evaluator_source_revision")
        == evaluator_contract.get("authority_source_revision")
        and _is_revision(expected_source["runtime_source_revision"])
        and _is_revision(expected_source["runtime_source_blob"])
        and _is_revision(expected_source["evaluator_source_revision"])
        and _is_revision(expected_source["evaluator_source_blob"])
        and isinstance(execution, dict)
        and execution.get("location") == "external"
        and execution.get("exported_copy_required") is True
        and execution.get("candidate_code_executed") is False
        and execution.get("credentials_used") is False
        and isinstance(raw_verification, dict)
        and raw_verification.get("mode") == "git-object-raw-bytes"
        and raw_verification.get("runtime_verified") is True
        and raw_verification.get("evaluator_verified") is True
        and isinstance(observation, dict)
        and observation.get("runtime_result_status") == "runtime_evaluation_complete"
        and observation.get("pull_state") == "open"
        and type(observation.get("pull_request")) is int
        and observation["pull_request"] > 0
        and _is_revision(observation.get("base_sha"))
        and _is_revision(observation.get("head_sha"))
        and observation.get("base_sha") != observation.get("head_sha")
        and isinstance(observation.get("changed_files"), list)
        and bool(observation.get("changed_files"))
        and all(
            isinstance(item, str) and bool(item)
            for item in observation["changed_files"]
        )
        and observation.get("facts_collected_independently") is True
        and observation.get("governance_decision") == "pass"
        and observation.get("runtime_failure_reasons") == []
        and observation.get("runtime_only_protected_mutations") == []
        and isinstance(qualification, dict)
        and qualification.get("context") == policy.qualification.candidate.context
        and qualification.get("result") == "pass"
        and type(qualification.get("check_run_id")) is int
        and qualification["check_run_id"] > 0
        and qualification.get("head_sha") == observation.get("head_sha")
        and qualification.get("source") == "github-checks-api"
        and qualification.get("source_verified") is True
        and qualification.get("status") == "completed"
        and qualification.get("conclusion") == "success"
        and isinstance(attestation, dict)
        and attestation.get("live_instance_proven") is True
        and attestation.get("facts_provenance_evidenced") is True
        and attestation.get("publisher_proven") is False
        and attestation.get("authority_binding_advanced") is False
        and attestation.get("effective_enforcement_proven") is False
        and isinstance(self_report, dict)
        and self_report.get("runtime_source_promoted") is False
        and self_report.get("facts_provenance_verified") is False
        and self_report.get("publish_enabled") is False
        and self_report.get("authority_binding_advanced") is False
        and self_report.get("effective_enforcement_proven") is False
    )
    if not valid:
        return None, _finding(
            "authority-live-provenance-evidence-invalid",
            "live-provenance evidence does not match promoted source identity and conservative live-proof semantics",
        )
    return evidence, None


def _validate_publisher_evidence(
    root: Path,
    reference: object,
    repository: object,
    integration_id: object,
    policy: SCMEnforcementPolicy,
) -> GitHubProjectionFinding | None:
    path = _resolve_evidence_path(root, reference)
    if path is None:
        return _finding(
            "authority-publisher-evidence-unbound",
            "provider activation requires governed evidence that the external GitHub App publisher emitted the authority check",
        )
    try:
        evidence = _load_json_object(path)
    except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
        return _finding(
            "authority-publisher-evidence-invalid",
            f"publisher evidence could not be loaded: {exc}",
        )

    authority = evidence.get("authority")
    publisher = evidence.get("publisher")
    claims = evidence.get("claims")
    valid = (
        evidence.get("contract_version") == 1
        and evidence.get("kind") == PUBLISHER_EVIDENCE_KIND
        and evidence.get("provider") == "github"
        and evidence.get("repository") == repository
        and isinstance(authority, dict)
        and authority.get("integration_id") == integration_id
        and authority.get("check_context")
        == policy.qualification.external_authority.context
        and authority.get("expected_source_binding") == "integration_id"
        and isinstance(publisher, dict)
        and publisher.get("execution_location") == "external"
        and publisher.get("check_run_published") is True
        and publisher.get("source_verified") is True
        and publisher.get("exact_candidate_binding") is True
        and publisher.get("credentials_isolated") is True
        and publisher.get("candidate_code_executed") is False
        and type(publisher.get("check_run_id")) is int
        and publisher["check_run_id"] > 0
        and _is_revision(publisher.get("candidate_sha"))
        and publisher.get("conclusion") == "success"
        and isinstance(claims, dict)
        and claims.get("effective_enforcement_proven") is False
    )
    if not valid:
        return _finding(
            "authority-publisher-evidence-invalid",
            "publisher evidence is not bound to the configured App identity, authority context, and exact candidate SHA",
        )
    return None


def build_github_activation_plan(
    repo_root: str | Path,
    policy: SCMEnforcementPolicy,
) -> GitHubActivationPlan:
    """Build, but never apply, the privileged GitHub ruleset activation payload."""
    root = Path(repo_root).resolve()

    try:
        ruleset = json.loads(
            (root / "governance/github/main-ruleset.json").read_text(encoding="utf-8")
        )
        binding = yaml.safe_load(
            (root / "governance/github/authority-binding.yaml").read_text(
                encoding="utf-8"
            )
        )
    except (OSError, json.JSONDecodeError, yaml.YAMLError) as exc:
        return GitHubActivationPlan(
            ruleset_payload=None,
            blockers=(
                _finding(
                    "activation-source-load-failed",
                    str(exc),
                ),
            ),
            integration_id=None,
            authority_revision=None,
        )

    projection = audit_github_projection(root, policy)
    if projection.findings:
        return GitHubActivationPlan(
            ruleset_payload=None,
            blockers=projection.findings,
            integration_id=None,
            authority_revision=None,
        )

    assert isinstance(ruleset, dict)
    assert isinstance(binding, dict)
    authority = binding.get("authority")
    evaluator = binding.get("evaluator")
    activation = binding.get("activation")
    assert isinstance(authority, dict)
    assert isinstance(evaluator, dict)
    assert isinstance(activation, dict)

    integration_id = authority.get("integration_id")
    authority_revision = evaluator.get("authority_revision")
    blockers: list[GitHubProjectionFinding] = []

    if policy.qualification.external_authority.required and not (
        type(integration_id) is int and integration_id > 0
    ):
        blockers.append(
            _finding(
                "authority-integration-id-unbound",
                "external GitHub App authority requires a positive integration_id before provider activation",
            )
        )

    revision_valid = _is_revision(authority_revision)
    if policy.qualification.external_authority.required and not revision_valid:
        blockers.append(
            _finding(
                "authority-revision-unbound",
                "external evaluator authority_revision must be an immutable 40-character commit SHA before provider activation",
            )
        )

    live_evidence: dict[str, Any] | None = None
    if policy.qualification.external_authority.required:
        live_evidence, live_finding = _validate_live_provenance_evidence(
            root,
            activation.get("live_provenance_evidence"),
            policy,
        )
        if live_finding is not None:
            blockers.append(live_finding)

        publisher_finding = _validate_publisher_evidence(
            root,
            activation.get("publisher_evidence"),
            live_evidence.get("repository") if live_evidence is not None else None,
            integration_id,
            policy,
        )
        if publisher_finding is not None:
            blockers.append(publisher_finding)

    if revision_valid and live_evidence is not None:
        expected_revision = live_evidence["source"]["evaluator_source_revision"]
        if authority_revision != expected_revision:
            blockers.append(
                _finding(
                    "authority-revision-evidence-mismatch",
                    "authority_revision must equal the evaluator revision bound by the governed live-provenance evidence",
                )
            )

    if activation.get("state") != "planned":
        blockers.append(
            _finding(
                "activation-state-invalid",
                "provider activation plan must remain in planned state until applied",
            )
        )

    if activation.get("effective_enforcement_claimed") is not False:
        blockers.append(
            _finding(
                "effective-enforcement-claim-premature",
                "effective enforcement must remain explicitly unclaimed until provider-side negative proof completes",
            )
        )

    if blockers:
        return GitHubActivationPlan(
            ruleset_payload=None,
            blockers=tuple(blockers),
            integration_id=(integration_id if type(integration_id) is int else None),
            authority_revision=(
                authority_revision if isinstance(authority_revision, str) else None
            ),
        )

    payload = json.loads(json.dumps(ruleset))
    status_rule = next(
        rule
        for rule in payload["rules"]
        if rule.get("type") == "required_status_checks"
    )
    checks: list[dict[str, Any]] = []
    if policy.qualification.candidate.required:
        checks.append({"context": policy.qualification.candidate.context})
    if policy.qualification.external_authority.required:
        checks.append(
            {
                "context": policy.qualification.external_authority.context,
                "integration_id": integration_id,
            }
        )
    status_rule["parameters"]["required_status_checks"] = checks

    return GitHubActivationPlan(
        ruleset_payload=payload,
        blockers=(),
        integration_id=integration_id,
        authority_revision=authority_revision,
    )
