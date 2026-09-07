from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Mapping

import yaml

from engine.adapters.scm.github import GitHubProjectionFinding, audit_github_projection
from engine.control.governance.scm_policy import SCMEnforcementPolicy


REVISION_RE = re.compile(r"^[0-9a-f]{40}$")


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
                GitHubProjectionFinding(
                    code="activation-source-load-failed",
                    message=str(exc),
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
            GitHubProjectionFinding(
                code="authority-integration-id-unbound",
                message=(
                    "external GitHub App authority requires a positive integration_id "
                    "before provider activation"
                ),
            )
        )

    if policy.qualification.external_authority.required and not (
        isinstance(authority_revision, str)
        and REVISION_RE.fullmatch(authority_revision)
    ):
        blockers.append(
            GitHubProjectionFinding(
                code="authority-revision-unbound",
                message=(
                    "external evaluator authority_revision must be an immutable "
                    "40-character commit SHA before provider activation"
                ),
            )
        )

    if activation.get("state") != "planned":
        blockers.append(
            GitHubProjectionFinding(
                code="activation-state-invalid",
                message="provider activation plan must remain in planned state until applied",
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
