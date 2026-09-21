from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import yaml

from engine.control.framework.artifacts import (
    ArtifactRuntimeView,
    compile_artifact_runtime,
)
from engine.control.framework.contracts import (
    FrameworkContractError,
    FrameworkContractSet,
    load_framework_contract_set,
)
from engine.control.framework.relationships import compile_relationship_runtime


FRAMEWORK_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT_ORDER = compile_artifact_runtime(FRAMEWORK_ROOT).artifact_types


def _plain(value: Any) -> Any:
    if isinstance(value, dict) or hasattr(value, "items"):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value


def _family(contract: FrameworkContractSet, name: str) -> dict[str, Any]:
    return _plain(contract.families[name]["data"])


def _validator_binding_findings(runtime: ArtifactRuntimeView, root: Path) -> list[str]:
    findings: list[str] = []
    for artifact_type, binding in runtime.validator_bindings.items():
        relative = Path(*binding.module.split(".")).with_suffix(".py")
        source = root / relative
        if not source.is_file() or source.is_symlink():
            findings.append(f"validator-binding-unresolvable:{artifact_type}")
            continue
        try:
            tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        except (OSError, UnicodeError, SyntaxError):
            findings.append(f"validator-binding-unreadable:{artifact_type}")
            continue
        class_node = next(
            (
                node
                for node in tree.body
                if isinstance(node, ast.ClassDef) and node.name == binding.class_name
            ),
            None,
        )
        if class_node is None:
            findings.append(f"validator-binding-unresolvable:{artifact_type}")
            continue
        declared_type = None
        for node in class_node.body:
            target = None
            value = None
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                target, value = node.target.id, node.value
            elif (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
            ):
                target, value = node.targets[0].id, node.value
            if target == "doc_type_name" and isinstance(value, ast.Constant):
                declared_type = value.value
        if declared_type != artifact_type:
            findings.append(f"validator-binding-type-drift:{artifact_type}")
    return findings


def framework_contract_findings(repo_root: str | Path) -> tuple[str, ...]:
    root = Path(repo_root).resolve()
    try:
        contract = load_framework_contract_set(root)
        runtime = compile_artifact_runtime(root)
        compile_relationship_runtime(root)
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

    layout = _family(contract, "repository-layout")["artifact_directories"]
    if layout != base["x-global-config"]["structure_rules"]["artifact_directories"]:
        findings.append("repository-layout-schema-projection-drift")

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

    findings.extend(_validator_binding_findings(runtime, root))

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
