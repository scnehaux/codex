from __future__ import annotations

from pathlib import Path
import shutil

import pytest
import yaml

from engine.control.framework.artifacts import artifact_runtime
from engine.control.framework.contracts import FrameworkContractError
from engine.control.framework.executable import (
    compile_framework,
    executable_framework,
)
from engine.control.framework.relationships import relationship_runtime
from tests.support.repository import REPOSITORY_ROOT


ROOT = REPOSITORY_ROOT
EXPECTED_SEMANTIC = "6f7e79c82aea1342d7f8eed9d2181383bb52b349f30af3cdf7ea3c609cf14980"


def _fixture(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(ROOT / "governance/framework", root / "governance/framework")
    shutil.copytree(ROOT / "schemas", root / "schemas")
    for relative in (
        "governance/normative-control-registry.yaml",
        "governance/severity-enforcement-registry.yaml",
        "governance/scm/enforcement-policy.yaml",
    ):
        source = ROOT / relative
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return root


def _yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write(path: Path, value) -> None:
    path.write_text(
        yaml.safe_dump(value, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
        newline="\n",
    )


def test_current_executable_framework_is_deterministic_and_complete():
    first = compile_framework(ROOT)
    second = compile_framework(ROOT)
    assert first.semantic_sha256 == second.semantic_sha256 == EXPECTED_SEMANTIC
    assert first.contract_sha256 == second.contract_sha256
    assert first.identity.framework_id == "scnehaux-codex"
    assert first.artifact_types == ("GDC", "EAD", "STD", "PAD", "SAD", "ADR", "TDD")
    assert len(first.relationship_ontology) == 10
    assert first.blocking_severities == ("CRITICAL", "ERROR")
    assert len(first.governance.severity_levels) == 39


def test_legacy_runtime_accessors_delegate_to_single_executable_framework():
    framework = executable_framework()
    assert artifact_runtime() is framework.artifacts
    assert relationship_runtime() is framework.relationships


def test_executable_framework_state_is_immutable():
    framework = executable_framework()
    with pytest.raises(TypeError):
        framework.repository_layout["SAD"] = "other"  # type: ignore[index]
    with pytest.raises(TypeError):
        framework.governance.severity_levels["missing_metadata"] = "INFO"  # type: ignore[index]


def test_reordering_semantically_unordered_declarations_keeps_semantic_digest(tmp_path):
    root = _fixture(tmp_path)
    before = compile_framework(root)

    relationships = root / "governance/framework/contracts/relationships.yaml"
    value = _yaml(relationships)
    value["data"]["relationships"] = list(reversed(value["data"]["relationships"]))
    _write(relationships, value)

    extensions = root / "governance/framework/contracts/extensions.yaml"
    value = _yaml(extensions)
    value["data"]["extension_points"] = list(
        reversed(value["data"]["extension_points"])
    )
    _write(extensions, value)

    after = compile_framework(root)
    assert after.semantic_sha256 == before.semantic_sha256
    assert after.contract_sha256 != before.contract_sha256


def test_semantic_change_changes_executable_digest(tmp_path):
    root = _fixture(tmp_path)
    before = compile_framework(root)
    lifecycle = root / "governance/framework/contracts/lifecycle.yaml"
    value = _yaml(lifecycle)
    value["data"]["artifact_lifecycle"]["GDC"]["draft"]["semantic_class"] = "retired"
    _write(lifecycle, value)
    after = compile_framework(root)
    assert after.semantic_sha256 != before.semantic_sha256


def test_missing_governance_reference_fails_compilation(tmp_path):
    root = _fixture(tmp_path)
    (root / "governance/severity-enforcement-registry.yaml").unlink()
    with pytest.raises(
        FrameworkContractError,
        match="executable-framework-severity_evidence_registry-missing",
    ):
        compile_framework(root)


def test_blocking_severity_contract_cannot_drift_from_runtime_policy(tmp_path):
    root = _fixture(tmp_path)
    path = root / "governance/framework/contracts/governance-policy.yaml"
    value = _yaml(path)
    value["data"]["blocking_severities"] = ["ERROR"]
    _write(path, value)
    with pytest.raises(
        FrameworkContractError,
        match="executable-framework-blocking-severities",
    ):
        compile_framework(root)


def test_identity_and_extension_profile_must_match(tmp_path):
    root = _fixture(tmp_path)
    path = root / "governance/framework/contracts/extensions.yaml"
    value = _yaml(path)
    value["data"]["profile_version"] = 3
    _write(path, value)
    with pytest.raises(
        FrameworkContractError, match="executable-framework-profile-drift"
    ):
        compile_framework(root)


def test_invalid_global_config_is_fail_closed(tmp_path):
    root = _fixture(tmp_path)
    schema = root / "schemas/base.schema.json"
    text = schema.read_text(encoding="utf-8")
    schema.write_text(
        text.replace(
            '"blocking_severities": ["CRITICAL", "ERROR"]',
            '"blocking_severities": ["ERROR"]',
        ),
        encoding="utf-8",
    )
    with pytest.raises(
        FrameworkContractError, match="executable-framework-severity-policy"
    ):
        compile_framework(root)


def test_fragment_contract_identity_must_match_full_contract(monkeypatch):
    import engine.control.framework.executable as module

    actual = module.compile_artifact_runtime(ROOT)
    fake = type(
        "Artifact",
        (),
        {
            **{
                name: getattr(actual, name)
                for name in (
                    "artifact_types",
                    "artifact_families",
                    "artifact_directories",
                    "lifecycle",
                    "schema_bindings",
                    "validator_bindings",
                )
            },
            "contract_sha256": "0" * 64,
        },
    )()
    monkeypatch.setattr(module, "compile_artifact_runtime", lambda _root: fake)
    with pytest.raises(
        FrameworkContractError,
        match="executable-framework-artifact-contract-drift",
    ):
        module.compile_framework(ROOT)
