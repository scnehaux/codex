from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping
import re

from engine.control.config.severity import BlockingSeverity, SeverityRule
from engine.control.framework.artifacts import (
    ArtifactRuntimeView,
    compile_artifact_runtime,
)
from engine.control.framework.contracts import (
    FrameworkContractError,
    FrameworkContractSet,
    load_framework_contract_set,
)
from engine.control.framework.relationships import (
    RelationshipRuntimeView,
    compile_relationship_runtime,
)


ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True, slots=True)
class FrameworkIdentity:
    framework_id: str
    framework_version: str
    framework_status: str
    product_name: str
    profile_id: str
    profile_version: int


@dataclass(frozen=True, slots=True)
class RepositoryPolicy:
    ignored_files: tuple[str, ...]
    ignored_patterns: tuple[str, ...]
    max_directory_depth: int


@dataclass(frozen=True, slots=True)
class GovernancePolicy:
    normative_control_registry: str
    severity_evidence_registry: str
    scm_enforcement_policy: str
    repository: RepositoryPolicy
    content_rules: Mapping[str, Mapping[str, Any]]
    severity_levels: Mapping[str, str]
    blocking_severities: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExtensionDeclarations:
    extension_points: tuple[str, ...]
    company_pack_must_not_require_core_fork: bool
    profile_id: str
    profile_version: int
    profile_core_fork_required: bool


@dataclass(frozen=True, slots=True)
class ExecutableFramework:
    identity: FrameworkIdentity
    artifacts: ArtifactRuntimeView
    relationships: RelationshipRuntimeView
    governance: GovernancePolicy
    extensions: ExtensionDeclarations
    contract_sha256: str
    semantic_sha256: str

    @property
    def artifact_types(self) -> tuple[str, ...]:
        return self.artifacts.artifact_types

    @property
    def repository_layout(self) -> Mapping[str, str]:
        return self.artifacts.artifact_directories

    @property
    def lifecycle(self):
        return self.artifacts.lifecycle

    @property
    def schema_bindings(self) -> Mapping[str, str]:
        return self.artifacts.schema_bindings

    @property
    def validator_bindings(self):
        return self.artifacts.validator_bindings

    @property
    def relationship_ontology(self) -> tuple:
        return self.relationships.relationships

    @property
    def blocking_severities(self) -> tuple[str, ...]:
        return self.governance.blocking_severities

    @property
    def validation_rules(self) -> Mapping[str, Any]:
        return MappingProxyType(
            {
                "structure_rules": MappingProxyType(
                    {
                        "artifact_directories": self.repository_layout,
                        "ignored_files": MappingProxyType(
                            {
                                "exact_matches": self.governance.repository.ignored_files,
                                "patterns": self.governance.repository.ignored_patterns,
                            }
                        ),
                        "max_directory_depth": self.governance.repository.max_directory_depth,
                    }
                ),
                "content_rules": self.governance.content_rules,
                "severity_levels": self.governance.severity_levels,
                "blocking_severities": self.governance.blocking_severities,
            }
        )


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise FrameworkContractError(code)


def _plain_family(contract: FrameworkContractSet, family: str):
    return contract.families[family]["data"]


def _relative_regular_file(root: Path, value: object, code: str) -> Path:
    _require(isinstance(value, str) and bool(value), code)
    _require(
        not value.startswith("/")
        and "\\" not in value
        and ":" not in value
        and "#" not in value,
        code,
    )
    parts = Path(value).parts
    _require(parts and "." not in parts and ".." not in parts, code)
    current = root
    for part in parts:
        current = current / part
        _require(not current.is_symlink(), code + "-symlink")
    _require(current.is_file(), code + "-missing")
    return current


def _compile_identity(contract: FrameworkContractSet) -> FrameworkIdentity:
    data = _plain_family(contract, "identity")
    expected = {
        "framework_id",
        "framework_version",
        "product_name",
        "profile_id",
        "profile_version",
    }
    _require(set(data) == expected, "executable-framework-identity-fields")
    _require(data["framework_id"] == contract.framework_id, "executable-framework-id")
    _require(
        data["framework_version"] == contract.framework_version,
        "executable-framework-version",
    )
    _require(
        isinstance(data["product_name"], str) and bool(data["product_name"]),
        "executable-framework-product-name",
    )
    _require(
        isinstance(data["profile_id"], str) and bool(data["profile_id"]),
        "executable-framework-profile-id",
    )
    _require(
        type(data["profile_version"]) is int and data["profile_version"] > 0,
        "executable-framework-profile-version",
    )
    return FrameworkIdentity(
        framework_id=contract.framework_id,
        framework_version=contract.framework_version,
        framework_status=contract.framework_status,
        product_name=data["product_name"],
        profile_id=data["profile_id"],
        profile_version=data["profile_version"],
    )


def _freeze_mapping(value: object, code: str) -> Mapping[str, Any]:
    _require(hasattr(value, "items"), code)
    result: dict[str, Any] = {}
    for key, item in value.items():
        _require(isinstance(key, str) and bool(key), code)
        if hasattr(item, "items"):
            result[key] = _freeze_mapping(item, code)
        elif isinstance(item, tuple):
            result[key] = tuple(item)
        else:
            result[key] = item
    return MappingProxyType(result)


def _compile_governance(root: Path, contract: FrameworkContractSet) -> GovernancePolicy:
    data = _plain_family(contract, "governance-policy")
    expected = {
        "normative_control_registry",
        "severity_evidence_registry",
        "scm_enforcement_policy",
        "repository_policy",
        "content_rules",
        "severity_levels",
        "blocking_severities",
    }
    _require(set(data) == expected, "executable-framework-governance-fields")

    refs = {}
    for key in (
        "normative_control_registry",
        "severity_evidence_registry",
        "scm_enforcement_policy",
    ):
        value = data[key]
        _relative_regular_file(root, value, f"executable-framework-{key}")
        refs[key] = value

    repository = data["repository_policy"]
    _require(
        hasattr(repository, "items")
        and set(repository)
        == {"ignored_files", "ignored_patterns", "max_directory_depth"},
        "executable-framework-repository-policy",
    )
    ignored_files = repository["ignored_files"]
    ignored_patterns = repository["ignored_patterns"]
    max_depth = repository["max_directory_depth"]
    _require(
        isinstance(ignored_files, tuple)
        and all(isinstance(item, str) and item for item in ignored_files)
        and len(ignored_files) == len(set(ignored_files)),
        "executable-framework-ignored-files",
    )
    _require(
        isinstance(ignored_patterns, tuple)
        and all(isinstance(item, str) and item for item in ignored_patterns)
        and len(ignored_patterns) == len(set(ignored_patterns)),
        "executable-framework-ignored-patterns",
    )
    for pattern in ignored_patterns:
        try:
            re.compile(pattern)
        except re.error as exc:
            raise FrameworkContractError(
                "executable-framework-ignored-pattern-invalid"
            ) from exc
    _require(
        type(max_depth) is int and 1 <= max_depth <= 64,
        "executable-framework-max-directory-depth",
    )

    content_rules = _freeze_mapping(
        data["content_rules"], "executable-framework-content-rules"
    )
    required_content = {
        "max_review_age_days",
        "min_content_length_chars",
        "prohibited_words",
        "ambiguity_rules",
        "nfr_taxonomy",
    }
    _require(
        set(content_rules) == required_content,
        "executable-framework-content-rule-set",
    )

    severity_raw = data["severity_levels"]
    _require(
        hasattr(severity_raw, "items"),
        "executable-framework-severity-levels",
    )
    severity_levels = dict(severity_raw.items())
    expected_rules = {item.value for item in SeverityRule}
    _require(
        set(severity_levels) == expected_rules,
        "executable-framework-severity-rule-set",
    )
    allowed_levels = {"CRITICAL", "ERROR", "WARNING", "INFO"}
    _require(
        all(level in allowed_levels for level in severity_levels.values()),
        "executable-framework-severity-value",
    )

    declared_blocking = data["blocking_severities"]
    expected_blocking = tuple(item.value for item in BlockingSeverity)
    _require(
        isinstance(declared_blocking, tuple)
        and tuple(declared_blocking) == expected_blocking,
        "executable-framework-blocking-severities",
    )

    return GovernancePolicy(
        normative_control_registry=refs["normative_control_registry"],
        severity_evidence_registry=refs["severity_evidence_registry"],
        scm_enforcement_policy=refs["scm_enforcement_policy"],
        repository=RepositoryPolicy(
            ignored_files=tuple(ignored_files),
            ignored_patterns=tuple(ignored_patterns),
            max_directory_depth=max_depth,
        ),
        content_rules=content_rules,
        severity_levels=MappingProxyType(dict(sorted(severity_levels.items()))),
        blocking_severities=expected_blocking,
    )


def _compile_extensions(contract: FrameworkContractSet) -> ExtensionDeclarations:
    data = _plain_family(contract, "extensions")
    expected = {
        "extension_points",
        "company_pack_must_not_require_core_fork",
        "profile_id",
        "profile_version",
        "profile_core_fork_required",
    }
    _require(set(data) == expected, "executable-framework-extension-fields")
    points = data["extension_points"]
    _require(
        isinstance(points, tuple)
        and bool(points)
        and all(isinstance(item, str) and item for item in points)
        and len(points) == len(set(points)),
        "executable-framework-extension-points",
    )
    _require(
        type(data["company_pack_must_not_require_core_fork"]) is bool
        and data["company_pack_must_not_require_core_fork"] is True,
        "executable-framework-company-pack-policy",
    )
    _require(
        isinstance(data["profile_id"], str) and bool(data["profile_id"]),
        "executable-framework-extension-profile-id",
    )
    _require(
        type(data["profile_version"]) is int and data["profile_version"] > 0,
        "executable-framework-extension-profile-version",
    )
    _require(
        type(data["profile_core_fork_required"]) is bool
        and data["profile_core_fork_required"] is False,
        "executable-framework-core-fork-policy",
    )
    return ExtensionDeclarations(
        extension_points=tuple(points),
        company_pack_must_not_require_core_fork=True,
        profile_id=data["profile_id"],
        profile_version=data["profile_version"],
        profile_core_fork_required=False,
    )


def _lifecycle_state(artifacts: ArtifactRuntimeView) -> dict:
    result = {}
    for artifact_type in sorted(artifacts.lifecycle):
        statuses = {}
        for status in sorted(artifacts.lifecycle[artifact_type]):
            policy = artifacts.lifecycle[artifact_type][status]
            item = {
                "semantic_class": policy.semantic_class,
                "validation_profile": policy.validation_profile,
                "age_policy": None,
            }
            if policy.age_policy is not None:
                item["age_policy"] = {
                    "depend_on": policy.age_policy.depend_on,
                    "max_age_days": policy.age_policy.max_age_days,
                    "error_message": policy.age_policy.error_message,
                }
            statuses[status] = item
        result[artifact_type] = statuses
    return result


def _relationship_state(relationships: RelationshipRuntimeView) -> list[dict]:
    rows = []
    for spec in sorted(relationships.relationships, key=lambda item: item.name):
        rows.append(
            {
                "name": spec.name,
                "metadata_field": spec.metadata_field,
                "source_types": sorted(spec.source_types),
                "target_types": sorted(spec.target_types),
                "min_targets": spec.min_targets,
                "max_targets": spec.max_targets,
                "direction": spec.direction,
                "dag_participation": spec.dag_participation,
                "authority_requirement": spec.authority_requirement,
                "inverse_relation": spec.inverse_relation,
                "allow_self_reference": spec.allow_self_reference,
                "source_statuses_requiring_authority": sorted(
                    spec.source_statuses_requiring_authority
                ),
                "allowed_target_statuses": sorted(spec.allowed_target_statuses),
            }
        )
    return rows


def _semantic_state(
    identity: FrameworkIdentity,
    artifacts: ArtifactRuntimeView,
    relationships: RelationshipRuntimeView,
    governance: GovernancePolicy,
    extensions: ExtensionDeclarations,
) -> dict:
    return {
        "identity": {
            "framework_id": identity.framework_id,
            "framework_version": identity.framework_version,
            "framework_status": identity.framework_status,
            "product_name": identity.product_name,
            "profile_id": identity.profile_id,
            "profile_version": identity.profile_version,
        },
        "artifacts": {
            "types": sorted(artifacts.artifact_types),
            "families": dict(sorted(artifacts.artifact_families.items())),
            "directories": dict(sorted(artifacts.artifact_directories.items())),
            "lifecycle": _lifecycle_state(artifacts),
            "schemas": dict(sorted(artifacts.schema_bindings.items())),
            "validators": {
                key: {
                    "module": value.module,
                    "class": value.class_name,
                }
                for key, value in sorted(artifacts.validator_bindings.items())
            },
        },
        "relationships": _relationship_state(relationships),
        "governance": {
            "normative_control_registry": governance.normative_control_registry,
            "severity_evidence_registry": governance.severity_evidence_registry,
            "scm_enforcement_policy": governance.scm_enforcement_policy,
            "repository_policy": {
                "ignored_files": sorted(governance.repository.ignored_files),
                "ignored_patterns": sorted(governance.repository.ignored_patterns),
                "max_directory_depth": governance.repository.max_directory_depth,
            },
            "content_rules": {
                key: dict(value)
                for key, value in sorted(governance.content_rules.items())
            },
            "severity_levels": dict(sorted(governance.severity_levels.items())),
            "blocking_severities": sorted(governance.blocking_severities),
        },
        "extensions": {
            "extension_points": sorted(extensions.extension_points),
            "company_pack_must_not_require_core_fork": (
                extensions.company_pack_must_not_require_core_fork
            ),
            "profile_id": extensions.profile_id,
            "profile_version": extensions.profile_version,
            "profile_core_fork_required": extensions.profile_core_fork_required,
        },
    }


def _semantic_digest(state: dict) -> str:
    payload = json.dumps(
        state,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return sha256(payload).hexdigest()


class FrameworkCompiler:
    def __init__(self, repo_root: str | Path):
        self.repo_root = Path(repo_root).resolve()

    def compile(self) -> ExecutableFramework:
        contract = load_framework_contract_set(self.repo_root)
        artifacts = compile_artifact_runtime(self.repo_root)
        relationships = compile_relationship_runtime(self.repo_root)
        _require(
            artifacts.contract_sha256 == contract.canonical_sha256,
            "executable-framework-artifact-contract-drift",
        )
        _require(
            relationships.contract_sha256 == contract.canonical_sha256,
            "executable-framework-relationship-contract-drift",
        )
        identity = _compile_identity(contract)
        governance = _compile_governance(self.repo_root, contract)
        extensions = _compile_extensions(contract)
        _require(
            identity.profile_id == extensions.profile_id
            and identity.profile_version == extensions.profile_version,
            "executable-framework-profile-drift",
        )
        state = _semantic_state(
            identity,
            artifacts,
            relationships,
            governance,
            extensions,
        )
        return ExecutableFramework(
            identity=identity,
            artifacts=artifacts,
            relationships=relationships,
            governance=governance,
            extensions=extensions,
            contract_sha256=contract.canonical_sha256,
            semantic_sha256=_semantic_digest(state),
        )


def compile_framework(repo_root: str | Path) -> ExecutableFramework:
    return FrameworkCompiler(repo_root).compile()


@lru_cache(maxsize=1)
def executable_framework() -> ExecutableFramework:
    return compile_framework(ROOT)
