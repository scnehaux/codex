from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import yaml

from engine.control.framework.contracts import (
    FrameworkContractError,
    FrameworkContractSet,
    load_framework_contract_set,
)
from engine.control.governance.lifecycle import LIFECYCLE_REGISTRY
from engine.control.governance.relationships import (
    ARTIFACT_TYPES,
    RELATIONSHIP_REGISTRY,
)


ARTIFACT_ORDER = ("GDC", "EAD", "STD", "PAD", "SAD", "ADR", "TDD")


def _plain(value: Any) -> Any:
    if isinstance(value, dict) or hasattr(value, "items"):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value


def _family(contract: FrameworkContractSet, name: str) -> dict[str, Any]:
    return _plain(contract.families[name]["data"])


def _validator_bindings(root: Path) -> dict[str, dict[str, str]]:
    path = root / "engine/control/validators/registry.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: dict[str, tuple[str, str]] = {}
    registry: ast.Dict | None = None
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and isinstance(node.module, str):
            module = node.module
            if node.level:
                package = ["engine", "control", "validators"]
                keep = len(package) - (node.level - 1)
                if keep <= 0:
                    raise FrameworkContractError(
                        "framework-equivalence-validator-import"
                    )
                module = ".".join([*package[:keep], module])
            for alias in node.names:
                imports[alias.asname or alias.name] = (module, alias.name)
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "VALIDATOR_REGISTRY"
            for target in node.targets
        ):
            if isinstance(node.value, ast.Dict):
                registry = node.value

    if registry is None:
        raise FrameworkContractError("framework-equivalence-validator-registry")

    result: dict[str, dict[str, str]] = {}
    for key_node, value_node in zip(registry.keys, registry.values, strict=True):
        if not (
            isinstance(key_node, ast.Constant)
            and isinstance(key_node.value, str)
            and isinstance(value_node, ast.Name)
            and value_node.id in imports
        ):
            raise FrameworkContractError("framework-equivalence-validator-shape")
        module, class_name = imports[value_node.id]
        if key_node.value in result:
            raise FrameworkContractError("framework-equivalence-validator-duplicate")
        result[key_node.value] = {"module": module, "class": class_name}
    return result


def _lifecycle() -> dict[str, Any]:
    result: dict[str, Any] = {}
    for doc_type in ARTIFACT_ORDER:
        statuses: dict[str, Any] = {}
        for status, policy in LIFECYCLE_REGISTRY[doc_type].items():
            item = {
                "semantic_class": policy.semantic_class,
                "validation_profile": policy.validation_profile,
            }
            if policy.age_policy is not None:
                item["age_policy"] = {
                    "depend_on": policy.age_policy.depend_on,
                    "max_age_days": policy.age_policy.max_age_days,
                    "error_message": policy.age_policy.error_message,
                }
            statuses[status] = item
        result[doc_type] = statuses
    return result


def _relationships() -> list[dict[str, Any]]:
    result = []
    for spec in RELATIONSHIP_REGISTRY:
        result.append(
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
    return result


def framework_contract_findings(repo_root: str | Path) -> tuple[str, ...]:
    root = Path(repo_root).resolve()
    try:
        contract = load_framework_contract_set(root)
    except FrameworkContractError as exc:
        return (f"contract-load:{exc}",)
    findings: list[str] = []
    base = json.loads((root / "schemas/base.schema.json").read_text(encoding="utf-8"))
    framework = yaml.safe_load(
        (root / "governance/framework/scnehaux-framework.yaml").read_text(
            encoding="utf-8"
        )
    )
    profile = yaml.safe_load(
        (root / "governance/framework/profiles/scnehaux-codex-default.yaml").read_text(
            encoding="utf-8"
        )
    )

    identity = _family(contract, "identity")
    expected_identity = {
        "framework_id": "scnehaux-codex",
        "framework_version": contract.framework_version,
        "product_name": framework["product"]["name"],
        "profile_id": profile["profile_id"],
        "profile_version": profile["profile_version"],
    }
    if identity != expected_identity:
        findings.append("identity-drift")

    declared_types = _family(contract, "artifact-types")["artifact_types"]
    if set(declared_types) != set(ARTIFACT_TYPES) or declared_types != list(
        ARTIFACT_ORDER
    ):
        findings.append("artifact-type-drift")

    layout = _family(contract, "repository-layout")["artifact_directories"]
    if layout != base["x-global-config"]["structure_rules"]["artifact_directories"]:
        findings.append("repository-layout-drift")

    if _family(contract, "lifecycle")["artifact_lifecycle"] != _lifecycle():
        findings.append("lifecycle-drift")

    if _family(contract, "relationships")["relationships"] != _relationships():
        findings.append("relationship-drift")
    schemas = _family(contract, "schema-bindings")
    expected_schemas = {
        "base_schema": "schemas/base.schema.json",
        "artifact_schemas": {
            doc_type: f"schemas/{doc_type.lower()}.schema.json"
            for doc_type in ARTIFACT_ORDER
        },
    }
    if schemas != expected_schemas:
        findings.append("schema-binding-drift")
    else:
        for relative in [schemas["base_schema"], *schemas["artifact_schemas"].values()]:
            if not (root / relative).is_file():
                findings.append(f"schema-binding-missing:{relative}")

    if _family(contract, "validator-bindings")["validators"] != _validator_bindings(
        root
    ):
        findings.append("validator-binding-drift")

    policy = _family(contract, "governance-policy")
    expected_policy = {
        "global_config": "schemas/base.schema.json#x-global-config",
        "normative_control_registry": "governance/normative-control-registry.yaml",
        "severity_evidence_registry": "governance/severity-enforcement-registry.yaml",
        "scm_enforcement_policy": "governance/scm/enforcement-policy.yaml",
        "blocking_severities": base["x-global-config"]["blocking_severities"],
    }
    if policy != expected_policy:
        findings.append("governance-policy-reference-drift")
    for relative in (
        "governance/normative-control-registry.yaml",
        "governance/severity-enforcement-registry.yaml",
        "governance/scm/enforcement-policy.yaml",
    ):
        if not (root / relative).is_file():
            findings.append(f"governance-policy-reference-missing:{relative}")
    extensions = _family(contract, "extensions")
    expected_extensions = {
        "extension_points": framework["extension_points"],
        "company_pack_must_not_require_core_fork": framework["company_pack"][
            "must_not_require_core_fork"
        ],
        "profile_id": profile["profile_id"],
        "profile_version": profile["profile_version"],
        "profile_core_fork_required": profile["extension"]["core_fork_required"],
    }
    if extensions != expected_extensions:
        findings.append("extension-contract-drift")

    return tuple(findings)


def assert_framework_contract_equivalence(
    repo_root: str | Path,
) -> FrameworkContractSet:
    findings = framework_contract_findings(repo_root)
    if findings:
        raise RuntimeError(
            "Declarative framework contract equivalence failed:\n  - "
            + "\n  - ".join(findings)
        )
    return load_framework_contract_set(repo_root)
