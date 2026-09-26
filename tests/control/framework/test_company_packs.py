from __future__ import annotations

from pathlib import Path
import shutil

import pytest
import yaml

from engine.control.framework.contracts import FrameworkContractError
from engine.control.framework.executable import compile_framework
from tests.support.repository import REPOSITORY_ROOT


ROOT = REPOSITORY_ROOT


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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(value, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
        newline="\n",
    )


def _activate_pack(root: Path, pack: dict, name: str = "acme.yaml") -> Path:
    pack_path = root / "governance/framework/company-packs" / name
    _write(pack_path, pack)
    extensions = root / "governance/framework/contracts/extensions.yaml"
    value = _yaml(extensions)
    value["data"]["company_packs"] = [
        {
            "path": f"governance/framework/company-packs/{name}",
            "kind": "scnehaux-company-pack",
        }
    ]
    _write(extensions, value)
    return pack_path


def _artifact_definition(name: str = "RISK") -> dict:
    return {
        "artifact_type": name,
        "family": name,
        "directory": "risks",
        "lifecycle": {
            "draft": {
                "semantic_class": "pre-baseline",
                "validation_profile": "full",
            },
            "approved": {
                "semantic_class": "baseline-bearing",
                "validation_profile": "full",
            },
        },
        "schema": "schemas/company/risk.schema.json",
        "validator": {
            "module": "company_packs.acme.validators.risk",
            "class": "RiskValidator",
        },
    }


def _relationship_definition() -> dict:
    return {
        "name": "risk-governed-by",
        "metadata_field": "governed_by",
        "source_types": ["RISK"],
        "target_types": ["GDC"],
        "min_targets": 1,
        "max_targets": None,
        "direction": "up",
        "dag_participation": True,
        "authority_requirement": "target-exists",
        "inverse_relation": None,
        "allow_self_reference": False,
        "source_statuses_requiring_authority": [],
        "allowed_target_statuses": [],
    }


def _pack(*operations: dict) -> dict:
    return {
        "contract_version": 1,
        "kind": "scnehaux-company-pack",
        "pack_id": "acme-governance",
        "pack_version": "1.0.0",
        "profile": {"id": "scnehaux-codex-default", "version": 2},
        "operations": list(operations),
    }


def _op(mode: str, target: str, definition: dict) -> dict:
    return {"mode": mode, "target": target, "definition": definition}


def test_company_pack_adds_artifact_and_relationship_without_core_contract_edit(
    tmp_path,
):
    root = _fixture(tmp_path)
    schema = root / "schemas/company/risk.schema.json"
    schema.parent.mkdir(parents=True)
    shutil.copy2(root / "schemas/base.schema.json", schema)

    before = compile_framework(root)
    _activate_pack(
        root,
        _pack(
            _op("additive", "artifact-type", _artifact_definition()),
            _op("additive", "relationship-type", _relationship_definition()),
        ),
    )
    after = compile_framework(root)

    assert "RISK" not in before.artifact_types
    assert "RISK" in after.artifact_types
    assert after.repository_layout["RISK"] == "risks"
    assert after.schema_bindings["RISK"] == "schemas/company/risk.schema.json"
    assert (
        after.validator_bindings["RISK"].module == "company_packs.acme.validators.risk"
    )
    assert any(spec.name == "risk-governed-by" for spec in after.relationship_ontology)
    assert [layer.layer_kind for layer in after.provenance] == [
        "core-framework",
        "framework-profile",
        "company-pack",
    ]
    assert after.provenance[-1].layer_id == "acme-governance"
    assert after.provenance[-1].layer_version == "1.0.0"
    assert all(len(layer.sha256) == 64 for layer in after.provenance)
    assert after.semantic_sha256 != before.semantic_sha256
    assert compile_framework(root).semantic_sha256 == after.semantic_sha256


def test_company_pack_cannot_additively_replace_core_artifact(tmp_path):
    root = _fixture(tmp_path)
    definition = _artifact_definition("EAD")
    definition["directory"] = "company-enterprise"
    _activate_pack(root, _pack(_op("additive", "artifact-type", definition)))
    with pytest.raises(
        FrameworkContractError,
        match="company-pack-core-artifact-override-forbidden",
    ):
        compile_framework(root)


def test_company_pack_cannot_replace_core_relationship(tmp_path):
    root = _fixture(tmp_path)
    relationship = _relationship_definition()
    relationship["name"] = "ead-governed-by"
    _activate_pack(root, _pack(_op("additive", "relationship-type", relationship)))
    with pytest.raises(
        FrameworkContractError,
        match="company-pack-core-relationship-override-forbidden",
    ):
        compile_framework(root)


@pytest.mark.parametrize(
    ("mode", "error"),
    [
        ("governed-restriction", "company-pack-governed-restriction-not-allowed"),
        (
            "compatibility-preserving-override",
            "company-pack-compatibility-preserving-override-not-allowed",
        ),
    ],
)
def test_non_additive_modes_are_distinguished_and_default_denied(tmp_path, mode, error):
    root = _fixture(tmp_path)
    _activate_pack(
        root,
        _pack(_op(mode, "relationship-type", _relationship_definition())),
    )
    with pytest.raises(FrameworkContractError, match=error):
        compile_framework(root)


def test_forbidden_core_semantic_override_is_explicitly_rejected(tmp_path):
    root = _fixture(tmp_path)
    _activate_pack(
        root,
        _pack(
            _op(
                "forbidden-core-semantic-override",
                "artifact-type",
                _artifact_definition("EAD"),
            )
        ),
    )
    with pytest.raises(
        FrameworkContractError,
        match="company-pack-core-semantic-override-forbidden",
    ):
        compile_framework(root)


def test_company_pack_profile_binding_is_exact(tmp_path):
    root = _fixture(tmp_path)
    pack = _pack(_op("additive", "relationship-type", _relationship_definition()))
    pack["profile"]["version"] = 3
    _activate_pack(root, pack)
    with pytest.raises(FrameworkContractError, match="company-pack-profile-drift"):
        compile_framework(root)


def test_company_pack_contract_version_is_strict_integer(tmp_path):
    root = _fixture(tmp_path)
    pack = _pack(_op("additive", "relationship-type", _relationship_definition()))
    pack["contract_version"] = True
    _activate_pack(root, pack)
    with pytest.raises(FrameworkContractError, match="company-pack-version"):
        compile_framework(root)
