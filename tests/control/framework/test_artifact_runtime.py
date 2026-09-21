from __future__ import annotations

from pathlib import Path
import shutil

import pytest
import yaml

from engine.control.framework.artifacts import (
    BASELINE_BEARING,
    PRE_BASELINE,
    FrameworkContractError,
    artifact_runtime,
    compile_artifact_runtime,
)
from tests.support.repository import REPOSITORY_ROOT


ROOT = REPOSITORY_ROOT


def _fixture(tmp_path: Path) -> Path:
    target = tmp_path / "repo"
    shutil.copytree(ROOT / "governance/framework", target / "governance/framework")
    shutil.copytree(ROOT / "schemas", target / "schemas")
    return target


def _yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write(path: Path, value) -> None:
    path.write_text(
        yaml.safe_dump(value, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
        newline="\n",
    )


def test_current_artifact_runtime_is_declarative_and_immutable():
    runtime = artifact_runtime()
    assert runtime.artifact_types == ("GDC", "EAD", "STD", "PAD", "SAD", "ADR", "TDD")
    assert dict(runtime.artifact_families) == {
        artifact_type: artifact_type for artifact_type in runtime.artifact_types
    }
    assert runtime.artifact_directories["TDD"] == "designs"
    assert runtime.lifecycle["GDC"]["approved"].semantic_class == BASELINE_BEARING
    assert runtime.lifecycle["SAD"]["draft"].semantic_class == PRE_BASELINE
    assert set(runtime.schema_bindings) == set(runtime.artifact_types)
    assert set(runtime.validator_bindings) == set(runtime.artifact_types)
    with pytest.raises(TypeError):
        runtime.artifact_directories["SAD"] = "other"  # type: ignore[index]


def test_schema_projection_cannot_redefine_runtime_layout(tmp_path):
    root = _fixture(tmp_path)
    before = compile_artifact_runtime(root)
    schema = root / "schemas/base.schema.json"
    raw = schema.read_text(encoding="utf-8")
    schema.write_text(
        raw.replace('"SAD": "systems"', '"SAD": "wrong"'), encoding="utf-8"
    )
    after = compile_artifact_runtime(root)
    assert dict(after.artifact_directories) == dict(before.artifact_directories)


def test_declarative_lifecycle_change_drives_compiled_view(tmp_path):
    root = _fixture(tmp_path)
    path = root / "governance/framework/contracts/lifecycle.yaml"
    value = _yaml(path)
    value["data"]["artifact_lifecycle"]["GDC"]["draft"]["semantic_class"] = "retired"
    _write(path, value)
    runtime = compile_artifact_runtime(root)
    assert runtime.lifecycle["GDC"]["draft"].semantic_class == "retired"


def test_artifact_type_and_layout_must_cover_each_other(tmp_path):
    root = _fixture(tmp_path)
    path = root / "governance/framework/contracts/artifact-types.yaml"
    value = _yaml(path)
    value["data"]["artifact_types"].append("NEW")
    _write(path, value)
    with pytest.raises(FrameworkContractError, match="family-types"):
        compile_artifact_runtime(root)


def test_tdd_topology_is_explicit_and_unique(tmp_path):
    root = _fixture(tmp_path)
    path = root / "governance/framework/contracts/repository-layout.yaml"
    value = _yaml(path)
    value["data"]["artifact_directories"]["TDD"] = "systems"
    _write(path, value)
    with pytest.raises(FrameworkContractError, match="layout-duplicate|tdd-topology"):
        compile_artifact_runtime(root)


def test_invalid_lifecycle_semantics_fail_closed(tmp_path):
    root = _fixture(tmp_path)
    path = root / "governance/framework/contracts/lifecycle.yaml"
    value = _yaml(path)
    value["data"]["artifact_lifecycle"]["GDC"]["draft"]["semantic_class"] = "invented"
    _write(path, value)
    with pytest.raises(FrameworkContractError, match="semantic-class"):
        compile_artifact_runtime(root)


def test_schema_and_validator_bindings_cover_exact_vocabulary(tmp_path):
    root = _fixture(tmp_path)
    path = root / "governance/framework/contracts/schema-bindings.yaml"
    value = _yaml(path)
    value["data"]["artifact_schemas"].pop("TDD")
    _write(path, value)
    with pytest.raises(FrameworkContractError, match="schema-bindings"):
        compile_artifact_runtime(root)

    root = _fixture(tmp_path / "validator")
    path = root / "governance/framework/contracts/validator-bindings.yaml"
    value = _yaml(path)
    value["data"]["validators"]["SAD"]["class"] = "Broken"
    _write(path, value)
    with pytest.raises(FrameworkContractError, match="validator-class"):
        compile_artifact_runtime(root)


def test_family_reclassification_requires_separate_governed_change(tmp_path):
    root = _fixture(tmp_path)
    path = root / "governance/framework/contracts/artifact-types.yaml"
    value = _yaml(path)
    value["data"]["artifact_families"]["TDD"] = "SAD"
    _write(path, value)
    with pytest.raises(FrameworkContractError, match="family-reclassification"):
        compile_artifact_runtime(root)


def _plain(value):
    if hasattr(value, "items"):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value


def _fake_contract(monkeypatch, mutator):
    import engine.control.framework.artifacts as module

    real = module.load_framework_contract_set(ROOT)
    families = {
        name: {"data": _plain(family["data"])}
        for name, family in real.families.items()
    }
    mutator(families)
    families["artifact-types"]["data"]["artifact_types"] = tuple(
        families["artifact-types"]["data"]["artifact_types"]
    )
    fake = type("Contract", (), {"families": families, "canonical_sha256": "0" * 64})()
    monkeypatch.setattr(module, "load_framework_contract_set", lambda _root: fake)


@pytest.mark.parametrize(
    ("mutator", "error"),
    [
        (lambda f: f["artifact-types"]["data"].__setitem__("artifact_types", []), "types"),
        (lambda f: f["artifact-types"]["data"].__setitem__("artifact_types", ["GDC", ""]), "type"),
        (lambda f: f["artifact-types"]["data"].__setitem__("artifact_types", ["GDC", "GDC"]), "type-duplicate"),
        (lambda f: f["artifact-types"]["data"].__setitem__("artifact_families", None), "families"),
    ],
)
def test_compiler_rejects_invalid_type_and_family_shapes(monkeypatch, mutator, error):
    _fake_contract(monkeypatch, mutator)
    with pytest.raises(FrameworkContractError, match=f"artifact-runtime-{error}$"):
        compile_artifact_runtime(ROOT)

@pytest.mark.parametrize(
    ("mutator", "error"),
    [
        (lambda f: f["repository-layout"]["data"].__setitem__("artifact_directories", None), "layout"),
        (lambda f: f["repository-layout"]["data"]["artifact_directories"].__setitem__("GDC", "../bad"), "layout-root"),
        (lambda f: f["lifecycle"]["data"].__setitem__("artifact_lifecycle", {}), "lifecycle-types"),
        (lambda f: f["lifecycle"]["data"]["artifact_lifecycle"].__setitem__("GDC", {}), "lifecycle-statuses"),
        (lambda f: f["lifecycle"]["data"]["artifact_lifecycle"]["GDC"].__setitem__("", {}), "lifecycle-status"),
        (lambda f: f["lifecycle"]["data"]["artifact_lifecycle"]["GDC"]["draft"].__setitem__("validation_profile", "other"), "validation-profile"),
        (lambda f: f["lifecycle"]["data"]["artifact_lifecycle"]["GDC"]["draft"].__setitem__("extra", True), "lifecycle-fields"),
    ],
)
def test_compiler_rejects_invalid_layout_and_lifecycle_shapes(monkeypatch, mutator, error):
    _fake_contract(monkeypatch, mutator)
    with pytest.raises(FrameworkContractError, match=f"artifact-runtime-{error}$"):
        compile_artifact_runtime(ROOT)

@pytest.mark.parametrize(
    ("mutator", "error"),
    [
        (lambda f: f["lifecycle"]["data"]["artifact_lifecycle"]["EAD"]["draft"].__setitem__("age_policy", {}), "age-policy"),
        (lambda f: f["lifecycle"]["data"]["artifact_lifecycle"]["EAD"]["draft"]["age_policy"].__setitem__("max_age_days", 0), "age-policy-value"),
        (lambda f: f["schema-bindings"]["data"]["artifact_schemas"].__setitem__("GDC", "other/gdc.json"), "schema-path"),
        (lambda f: f["validator-bindings"]["data"].__setitem__("validators", {}), "validator-bindings"),
        (lambda f: f["validator-bindings"]["data"]["validators"].__setitem__("GDC", {}), "validator-binding"),
        (lambda f: f["validator-bindings"]["data"]["validators"]["GDC"].__setitem__("module", "other.module"), "validator-module"),
    ],
)
def test_compiler_rejects_invalid_age_schema_and_validator_shapes(monkeypatch, mutator, error):
    _fake_contract(monkeypatch, mutator)
    with pytest.raises(FrameworkContractError, match=f"artifact-runtime-{error}$"):
        compile_artifact_runtime(ROOT)

def test_artifact_type_from_id_rejects_non_string_and_unknown():
    from engine.control.framework.artifacts import artifact_type_from_id

    assert artifact_type_from_id(None) is None
    assert artifact_type_from_id("UNKNOWN-001") is None
    assert artifact_type_from_id("sad-001") == "SAD"


def test_validator_registry_fails_closed_on_import_and_type_drift(monkeypatch):
    import engine.control.framework.artifacts as module

    runtime = artifact_runtime()

    def missing(_name):
        raise ImportError("missing")

    monkeypatch.setattr(module.importlib, "import_module", missing)
    with pytest.raises(FrameworkContractError, match="validator-unresolvable"):
        module.validator_registry()

    class Wrong:
        doc_type_name = "WRONG"

    fake_module = type("Module", (), {"GDCValidator": Wrong})()
    one = type("Runtime", (), {"validator_bindings": {"GDC": runtime.validator_bindings["GDC"]}})()
    monkeypatch.setattr(module, "artifact_runtime", lambda: one)
    monkeypatch.setattr(module.importlib, "import_module", lambda _name: fake_module)
    with pytest.raises(FrameworkContractError, match="validator-type"):
        module.validator_registry()
