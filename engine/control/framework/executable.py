from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from engine.control.config.loader import parse_and_validate_global_config
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
class GovernancePolicy:
    global_config_ref: str
    normative_control_registry: str
    severity_evidence_registry: str
    scm_enforcement_policy: str
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


def _compile_governance(root: Path, contract: FrameworkContractSet) -> GovernancePolicy:
    data = _plain_family(contract, "governance-policy")
    expected = {
        "global_config",
        "normative_control_registry",
        "severity_evidence_registry",
        "scm_enforcement_policy",
        "blocking_severities",
    }
    _require(set(data) == expected, "executable-framework-governance-fields")
    global_ref = data["global_config"]
    _require(
        isinstance(global_ref, str)
        and global_ref == "schemas/base.schema.json#x-global-config",
        "executable-framework-global-config-ref",
    )
    schema_path = _relative_regular_file(
        root, "schemas/base.schema.json", "executable-framework-global-config"
    )
    try:
        base_schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FrameworkContractError("executable-framework-global-config-json") from exc
    try:
        _global_rules, severity_levels, blocking = parse_and_validate_global_config(
            base_schema
        )
    except (RuntimeError, TypeError, ValueError) as exc:
        raise FrameworkContractError("executable-framework-severity-policy") from exc

    declared_blocking = data["blocking_severities"]
    _require(
        isinstance(declared_blocking, tuple) and tuple(declared_blocking) == blocking,
        "executable-framework-blocking-severities",
    )

    refs = {}
    for key in (
        "normative_control_registry",
        "severity_evidence_registry",
        "scm_enforcement_policy",
    ):
        value = data[key]
        _relative_regular_file(root, value, f"executable-framework-{key}")
        refs[key] = value
    return GovernancePolicy(
        global_config_ref=global_ref,
        normative_control_registry=refs["normative_control_registry"],
        severity_evidence_registry=refs["severity_evidence_registry"],
        scm_enforcement_policy=refs["scm_enforcement_policy"],
        severity_levels=MappingProxyType(dict(sorted(severity_levels.items()))),
        blocking_severities=tuple(blocking),
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
            "global_config_ref": governance.global_config_ref,
            "normative_control_registry": governance.normative_control_registry,
            "severity_evidence_registry": governance.severity_evidence_registry,
            "scm_enforcement_policy": governance.scm_enforcement_policy,
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
