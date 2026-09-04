from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml


POLICY_PATH = Path("governance/scm/enforcement-policy.yaml")


class SCMPolicyError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class DefaultBranchPolicy:
    selector: str
    changes_require_review: bool
    deletion_allowed: bool
    force_push_allowed: bool
    linear_history_required: bool


@dataclass(frozen=True, slots=True)
class MergePolicy:
    allowed_methods: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReviewPolicy:
    required_approvals: int
    dismiss_stale_on_push: bool
    require_code_owner_review: bool
    require_last_push_approval: bool
    require_thread_resolution: bool


@dataclass(frozen=True, slots=True)
class BypassPolicy:
    allowed: bool


@dataclass(frozen=True, slots=True)
class CandidateQualificationPolicy:
    required: bool
    context: str
    strict_against_latest_base: bool


@dataclass(frozen=True, slots=True)
class ExternalAuthorityPolicy:
    required: bool
    context: str


@dataclass(frozen=True, slots=True)
class QualificationPolicy:
    candidate: CandidateQualificationPolicy
    external_authority: ExternalAuthorityPolicy


@dataclass(frozen=True, slots=True)
class WorkflowPolicy:
    pull_request_default_branch: bool
    push_default_branch: bool
    repository_contents_permission: str
    committed_mutation_validation_required: bool
    full_governance_qualification_required: bool


@dataclass(frozen=True, slots=True)
class OwnershipPolicy:
    repository_default_owner_required: bool
    governance_path_owner_required: bool
    provider_config_owner_required: bool


@dataclass(frozen=True, slots=True)
class SCMEnforcementPolicy:
    default_branch: DefaultBranchPolicy
    merge: MergePolicy
    review: ReviewPolicy
    bypass: BypassPolicy
    qualification: QualificationPolicy
    workflow: WorkflowPolicy
    ownership: OwnershipPolicy


def _mapping(value: object, path: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise SCMPolicyError(f"{path} must be a mapping")
    return value


def _keys(value: Mapping[str, Any], expected: set[str], path: str) -> None:
    actual = set(value)
    if actual != expected:
        raise SCMPolicyError(
            f"{path} fields must be exactly {sorted(expected)}, got {sorted(actual)}"
        )


def _string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SCMPolicyError(f"{path} must be a non-blank string")
    return value


def _bool(value: object, path: str) -> bool:
    if type(value) is not bool:
        raise SCMPolicyError(f"{path} must be a boolean")
    return value


def _nonnegative_int(value: object, path: str) -> int:
    if type(value) is not int or value < 0:
        raise SCMPolicyError(f"{path} must be a non-negative integer")
    return value


def _string_tuple(value: object, path: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise SCMPolicyError(f"{path} must be a non-empty list")
    result = tuple(_string(item, f"{path}[]") for item in value)
    if len(set(result)) != len(result):
        raise SCMPolicyError(f"{path} must not contain duplicates")
    return result


def load_scm_enforcement_policy(repo_root: str | Path) -> SCMEnforcementPolicy:
    path = Path(repo_root).resolve() / POLICY_PATH
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise SCMPolicyError(f"cannot load {POLICY_PATH.as_posix()}: {exc}") from exc

    root = _mapping(raw, "policy")
    _keys(
        root,
        {
            "contract_version",
            "kind",
            "provider_neutral",
            "default_branch",
            "merge",
            "review",
            "bypass",
            "qualification",
            "workflow",
            "ownership",
        },
        "policy",
    )
    if root["contract_version"] != 1:
        raise SCMPolicyError("contract_version must be 1")
    if root["kind"] != "scm-enforcement-policy":
        raise SCMPolicyError("kind must be scm-enforcement-policy")
    if root["provider_neutral"] is not True:
        raise SCMPolicyError("SCM enforcement policy must remain provider-neutral")

    default = _mapping(root["default_branch"], "default_branch")
    _keys(
        default,
        {
            "selector",
            "changes_require_review",
            "deletion_allowed",
            "force_push_allowed",
            "linear_history_required",
        },
        "default_branch",
    )

    merge = _mapping(root["merge"], "merge")
    _keys(merge, {"allowed_methods"}, "merge")

    review = _mapping(root["review"], "review")
    _keys(
        review,
        {
            "required_approvals",
            "dismiss_stale_on_push",
            "require_code_owner_review",
            "require_last_push_approval",
            "require_thread_resolution",
        },
        "review",
    )

    bypass = _mapping(root["bypass"], "bypass")
    _keys(bypass, {"allowed"}, "bypass")

    qualification = _mapping(root["qualification"], "qualification")
    _keys(qualification, {"candidate", "external_authority"}, "qualification")
    candidate = _mapping(qualification["candidate"], "qualification.candidate")
    _keys(
        candidate,
        {"required", "context", "strict_against_latest_base"},
        "qualification.candidate",
    )
    external = _mapping(
        qualification["external_authority"],
        "qualification.external_authority",
    )
    _keys(external, {"required", "context"}, "qualification.external_authority")

    workflow = _mapping(root["workflow"], "workflow")
    _keys(
        workflow,
        {
            "pull_request_default_branch",
            "push_default_branch",
            "repository_contents_permission",
            "committed_mutation_validation_required",
            "full_governance_qualification_required",
        },
        "workflow",
    )

    ownership = _mapping(root["ownership"], "ownership")
    _keys(
        ownership,
        {
            "repository_default_owner_required",
            "governance_path_owner_required",
            "provider_config_owner_required",
        },
        "ownership",
    )

    return SCMEnforcementPolicy(
        default_branch=DefaultBranchPolicy(
            selector=_string(default["selector"], "default_branch.selector"),
            changes_require_review=_bool(
                default["changes_require_review"],
                "default_branch.changes_require_review",
            ),
            deletion_allowed=_bool(
                default["deletion_allowed"],
                "default_branch.deletion_allowed",
            ),
            force_push_allowed=_bool(
                default["force_push_allowed"],
                "default_branch.force_push_allowed",
            ),
            linear_history_required=_bool(
                default["linear_history_required"],
                "default_branch.linear_history_required",
            ),
        ),
        merge=MergePolicy(
            allowed_methods=_string_tuple(
                merge["allowed_methods"],
                "merge.allowed_methods",
            ),
        ),
        review=ReviewPolicy(
            required_approvals=_nonnegative_int(
                review["required_approvals"],
                "review.required_approvals",
            ),
            dismiss_stale_on_push=_bool(
                review["dismiss_stale_on_push"],
                "review.dismiss_stale_on_push",
            ),
            require_code_owner_review=_bool(
                review["require_code_owner_review"],
                "review.require_code_owner_review",
            ),
            require_last_push_approval=_bool(
                review["require_last_push_approval"],
                "review.require_last_push_approval",
            ),
            require_thread_resolution=_bool(
                review["require_thread_resolution"],
                "review.require_thread_resolution",
            ),
        ),
        bypass=BypassPolicy(allowed=_bool(bypass["allowed"], "bypass.allowed")),
        qualification=QualificationPolicy(
            candidate=CandidateQualificationPolicy(
                required=_bool(
                    candidate["required"], "qualification.candidate.required"
                ),
                context=_string(
                    candidate["context"], "qualification.candidate.context"
                ),
                strict_against_latest_base=_bool(
                    candidate["strict_against_latest_base"],
                    "qualification.candidate.strict_against_latest_base",
                ),
            ),
            external_authority=ExternalAuthorityPolicy(
                required=_bool(
                    external["required"],
                    "qualification.external_authority.required",
                ),
                context=_string(
                    external["context"],
                    "qualification.external_authority.context",
                ),
            ),
        ),
        workflow=WorkflowPolicy(
            pull_request_default_branch=_bool(
                workflow["pull_request_default_branch"],
                "workflow.pull_request_default_branch",
            ),
            push_default_branch=_bool(
                workflow["push_default_branch"],
                "workflow.push_default_branch",
            ),
            repository_contents_permission=_string(
                workflow["repository_contents_permission"],
                "workflow.repository_contents_permission",
            ),
            committed_mutation_validation_required=_bool(
                workflow["committed_mutation_validation_required"],
                "workflow.committed_mutation_validation_required",
            ),
            full_governance_qualification_required=_bool(
                workflow["full_governance_qualification_required"],
                "workflow.full_governance_qualification_required",
            ),
        ),
        ownership=OwnershipPolicy(
            repository_default_owner_required=_bool(
                ownership["repository_default_owner_required"],
                "ownership.repository_default_owner_required",
            ),
            governance_path_owner_required=_bool(
                ownership["governance_path_owner_required"],
                "ownership.governance_path_owner_required",
            ),
            provider_config_owner_required=_bool(
                ownership["provider_config_owner_required"],
                "ownership.provider_config_owner_required",
            ),
        ),
    )


def assert_scm_enforcement_policy(repo_root: str | Path) -> SCMEnforcementPolicy:
    return load_scm_enforcement_policy(repo_root)
