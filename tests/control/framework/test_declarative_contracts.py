from __future__ import annotations

from pathlib import Path
import shutil

import pytest
import yaml

import engine.control.framework.equivalence as equivalence
from engine.control.framework.contracts import (
    FAMILY_NAMES,
    FrameworkContractError,
    load_framework_contract_set,
)
from engine.control.framework.equivalence import (
    ARTIFACT_ORDER,
    assert_framework_contract_equivalence,
    framework_contract_findings,
)
from tests.support.repository import REPOSITORY_ROOT


ROOT = REPOSITORY_ROOT
MANIFEST = Path("governance/framework/contract-set.yaml")
CONTRACTS = Path("governance/framework/contracts")


def _fixture(tmp_path: Path) -> Path:
    target = tmp_path / "repo"
    (target / CONTRACTS).mkdir(parents=True)
    shutil.copy2(ROOT / MANIFEST, target / MANIFEST)
    for source in (ROOT / CONTRACTS).iterdir():
        if source.is_file():
            shutil.copy2(source, target / CONTRACTS / source.name)
    return target


def _yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write(path: Path, value) -> None:
    path.write_text(
        yaml.safe_dump(value, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
        newline="\n",
    )


def test_current_contract_set_is_deterministic_and_equivalent():
    first = load_framework_contract_set(ROOT)
    second = load_framework_contract_set(ROOT)
    assert first.canonical_sha256 == second.canonical_sha256
    assert first.framework_id == "scnehaux-codex"
    assert first.framework_version == "0.1.0"
    assert set(first.families) == FAMILY_NAMES
    assert framework_contract_findings(ROOT) == ()
    assert assert_framework_contract_equivalence(ROOT).canonical_sha256 == (
        first.canonical_sha256
    )


def test_loaded_contract_is_immutable():
    contract = load_framework_contract_set(ROOT)
    with pytest.raises(TypeError):
        contract.ownership["new-owner"] = "identity"  # type: ignore[index]
    with pytest.raises(TypeError):
        contract.families["identity"]["data"]["framework_id"] = "other"  # type: ignore[index]


def test_duplicate_yaml_key_is_rejected(tmp_path):
    root = _fixture(tmp_path)
    family = root / CONTRACTS / "identity.yaml"
    family.write_text(
        family.read_text(encoding="utf-8") + "kind: duplicate\n",
        encoding="utf-8",
    )
    with pytest.raises(FrameworkContractError, match="duplicate-key"):
        load_framework_contract_set(root)


def test_unknown_manifest_field_is_rejected(tmp_path):
    root = _fixture(tmp_path)
    manifest = _yaml(root / MANIFEST)
    manifest["unexpected"] = True
    _write(root / MANIFEST, manifest)
    with pytest.raises(FrameworkContractError, match="manifest-fields"):
        load_framework_contract_set(root)


def test_family_path_traversal_is_rejected(tmp_path):
    root = _fixture(tmp_path)
    manifest = _yaml(root / MANIFEST)
    manifest["families"]["identity"]["path"] = "../identity.yaml"
    _write(root / MANIFEST, manifest)
    with pytest.raises(FrameworkContractError, match="framework-contract-path"):
        load_framework_contract_set(root)


def test_duplicate_family_path_is_rejected(tmp_path):
    root = _fixture(tmp_path)
    manifest = _yaml(root / MANIFEST)
    manifest["families"]["extensions"]["path"] = manifest["families"]["identity"][
        "path"
    ]
    _write(root / MANIFEST, manifest)
    with pytest.raises(FrameworkContractError, match="family-path-unique"):
        load_framework_contract_set(root)


def test_conflicting_semantic_ownership_is_rejected(tmp_path):
    root = _fixture(tmp_path)
    extension_path = root / CONTRACTS / "extensions.yaml"
    extension = _yaml(extension_path)
    extension["owns"].append("framework-identity")
    _write(extension_path, extension)
    with pytest.raises(FrameworkContractError, match="conflicting-owner"):
        load_framework_contract_set(root)


def test_ownership_map_must_be_complete_and_exact(tmp_path):
    root = _fixture(tmp_path)
    manifest = _yaml(root / MANIFEST)
    manifest["ownership"].pop("compatibility-metadata")
    _write(root / MANIFEST, manifest)
    with pytest.raises(FrameworkContractError, match="ownership-map"):
        load_framework_contract_set(root)


@pytest.mark.parametrize("value", ["1", True, 2, None])
def test_contract_version_is_strict_integer_one(tmp_path, value):
    root = _fixture(tmp_path)
    manifest = _yaml(root / MANIFEST)
    manifest["contract_version"] = value
    _write(root / MANIFEST, manifest)
    with pytest.raises(FrameworkContractError, match="contract-version"):
        load_framework_contract_set(root)


@pytest.mark.parametrize("version", ["0.1", "v0.1.0", "01.0.0", "", True])
def test_framework_semver_is_fail_closed(tmp_path, version):
    root = _fixture(tmp_path)
    manifest = _yaml(root / MANIFEST)
    manifest["framework"]["version"] = version
    _write(root / MANIFEST, manifest)
    with pytest.raises(FrameworkContractError, match="semver"):
        load_framework_contract_set(root)


def test_runtime_activation_remains_explicitly_staged(tmp_path):
    root = _fixture(tmp_path)
    manifest = _yaml(root / MANIFEST)
    manifest["activation"]["runtime_authority"] = "declarative"
    _write(root / MANIFEST, manifest)
    with pytest.raises(FrameworkContractError, match="runtime-authority"):
        load_framework_contract_set(root)


def test_contract_hash_changes_when_authored_data_changes(tmp_path):
    root = _fixture(tmp_path)
    before = load_framework_contract_set(root).canonical_sha256
    identity_path = root / CONTRACTS / "identity.yaml"
    identity = _yaml(identity_path)
    identity["data"]["product_name"] = "Changed"
    _write(identity_path, identity)
    after = load_framework_contract_set(root).canonical_sha256
    assert after != before


def test_current_artifact_type_contract_is_lossless():
    contract = load_framework_contract_set(ROOT)
    data = contract.families["artifact-types"]["data"]
    assert tuple(data["artifact_types"]) == ARTIFACT_ORDER


def test_all_required_semantic_owners_are_unique():
    contract = load_framework_contract_set(ROOT)
    owners = list(contract.ownership)
    assert len(owners) == len(set(owners))
    assert {
        "framework-identity",
        "framework-version",
        "artifact-type-declarations",
        "repository-layout-policy",
        "lifecycle-policy",
        "relationship-ontology",
        "schema-bindings",
        "validator-bindings",
        "governance-policy-references",
        "severity-policy-references",
        "extension-declarations",
        "compatibility-metadata",
    } == set(owners)


def _equivalence_fixture(tmp_path: Path) -> Path:
    target = _fixture(tmp_path)
    required = [
        "schemas/base.schema.json",
        *[f"schemas/{kind.lower()}.schema.json" for kind in ARTIFACT_ORDER],
        "governance/framework/scnehaux-framework.yaml",
        "governance/framework/profiles/scnehaux-codex-default.yaml",
        "engine/control/validators/registry.py",
        "governance/normative-control-registry.yaml",
        "governance/severity-enforcement-registry.yaml",
        "governance/scm/enforcement-policy.yaml",
    ]
    for relative in required:
        source = ROOT / relative
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return target


def _mutate_family(root: Path, filename: str, mutator) -> None:
    path = root / CONTRACTS / filename
    value = _yaml(path)
    mutator(value["data"])
    _write(path, value)


@pytest.mark.parametrize(
    ("filename", "expected", "mutator"),
    [
        (
            "identity.yaml",
            "identity-drift",
            lambda data: data.__setitem__("product_name", "Changed"),
        ),
        (
            "artifact-types.yaml",
            "artifact-type-drift",
            lambda data: data["artifact_types"].append("UNKNOWN"),
        ),
        (
            "repository-layout.yaml",
            "repository-layout-drift",
            lambda data: data["artifact_directories"].__setitem__("GDC", "other"),
        ),
        (
            "lifecycle.yaml",
            "lifecycle-drift",
            lambda data: data["artifact_lifecycle"]["GDC"]["draft"].__setitem__(
                "semantic_class", "other"
            ),
        ),
        (
            "relationships.yaml",
            "relationship-drift",
            lambda data: data["relationships"][0].__setitem__("name", "other"),
        ),
        (
            "schema-bindings.yaml",
            "schema-binding-drift",
            lambda data: data.__setitem__("base_schema", "schemas/other.json"),
        ),
        (
            "validator-bindings.yaml",
            "validator-binding-drift",
            lambda data: data["validators"]["ADR"].__setitem__("class", "Other"),
        ),
        (
            "governance-policy.yaml",
            "governance-policy-reference-drift",
            lambda data: data.__setitem__("blocking_severities", ["ERROR"]),
        ),
        (
            "extensions.yaml",
            "extension-contract-drift",
            lambda data: data.__setitem__("profile_version", 999),
        ),
    ],
)
def test_equivalence_reports_each_semantic_family_drift(
    tmp_path, filename, expected, mutator
):
    root = _equivalence_fixture(tmp_path)
    _mutate_family(root, filename, mutator)
    assert expected in framework_contract_findings(root)


def test_equivalence_reports_missing_schema_and_policy_reference(tmp_path):
    root = _equivalence_fixture(tmp_path)
    (root / "schemas/adr.schema.json").unlink()
    assert "schema-binding-missing:schemas/adr.schema.json" in (
        framework_contract_findings(root)
    )

    root = _equivalence_fixture(tmp_path / "second")
    (root / "governance/normative-control-registry.yaml").unlink()
    assert (
        "governance-policy-reference-missing:governance/normative-control-registry.yaml"
        in framework_contract_findings(root)
    )


def test_equivalence_reports_contract_load_error(tmp_path):
    assert framework_contract_findings(tmp_path) == (
        "contract-load:framework-contract-file",
    )


def test_assert_equivalence_raises_on_drift(tmp_path):
    root = _equivalence_fixture(tmp_path)
    _mutate_family(
        root,
        "identity.yaml",
        lambda data: data.__setitem__("product_name", "Changed"),
    )
    with pytest.raises(RuntimeError, match="identity-drift"):
        assert_framework_contract_equivalence(root)


@pytest.mark.parametrize(
    ("source", "error"),
    [
        ("x = 1\n", "validator-registry"),
        (
            "from .domains.adr_validator import ADRValidator\n"
            "VALIDATOR_REGISTRY = {'ADR': 'not-a-name'}\n",
            "validator-shape",
        ),
        (
            "from .domains.adr_validator import ADRValidator\n"
            "VALIDATOR_REGISTRY = {'ADR': ADRValidator, 'ADR': ADRValidator}\n",
            "validator-duplicate",
        ),
        (
            "from ....outside import A\nVALIDATOR_REGISTRY = {'ADR': A}\n",
            "validator-import",
        ),
    ],
)
def test_validator_registry_ast_failures_are_explicit(tmp_path, source, error):
    root = tmp_path / "repo"
    path = root / "engine/control/validators/registry.py"
    path.parent.mkdir(parents=True)
    path.write_text(source, encoding="utf-8")
    with pytest.raises(FrameworkContractError, match=error):
        equivalence._validator_bindings(root)
