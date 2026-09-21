from __future__ import annotations


import pytest

from engine.control.framework.artifacts import compile_artifact_runtime
from engine.control.framework.contracts import (
    FrameworkContractError,
    load_framework_contract_set,
)
from engine.control.framework.relationships import (
    APPROVED_PARENT_FOR_ACTIVE_SAD,
    compile_relationship_runtime,
    relationship_runtime,
)
from tests.support.repository import REPOSITORY_ROOT


ROOT = REPOSITORY_ROOT
EXPECTED_DIGEST = "7fa6c8a1114986f6a3d2095933b0f3cd8536f3012bedeb751438bf4ed4189e07"


def _plain(value):
    if hasattr(value, "items"):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value


def _freeze(value):
    if isinstance(value, dict):
        return {key: _freeze(item) for key, item in value.items()}
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _fake(monkeypatch, mutator):
    import engine.control.framework.relationships as module

    contract = load_framework_contract_set(ROOT)
    data = _plain(contract.families["relationships"]["data"])
    mutator(data)
    fake = type(
        "Contract",
        (),
        {
            "families": {"relationships": {"data": _freeze(data)}},
            "canonical_sha256": "0" * 64,
        },
    )()
    artifact = compile_artifact_runtime(ROOT)
    monkeypatch.setattr(module, "load_framework_contract_set", lambda _root: fake)
    monkeypatch.setattr(module, "compile_artifact_runtime", lambda _root: artifact)


def _relation(data, name):
    return next(item for item in data["relationships"] if item["name"] == name)


def test_current_relationship_runtime_preserves_pre_cutover_semantics():
    runtime = relationship_runtime()
    assert len(runtime.relationships) == 10
    assert runtime.ontology_sha256 == EXPECTED_DIGEST
    assert runtime.all_fields == frozenset(
        {
            "governed_by",
            "realizes_capability",
            "parent_pad",
            "parent_sad",
            "fulfilled_by",
        }
    )
    sad_parent = next(
        spec for spec in runtime.relationships if spec.name == "sad-parent-pad"
    )
    assert sad_parent.authority_requirement == APPROVED_PARENT_FOR_ACTIVE_SAD
    assert sad_parent.cardinality == "1..1"
    assert sad_parent.inverse_relation == "fulfilled_by"


def test_python_governance_facade_no_longer_authors_relationship_specs():
    source = (ROOT / "engine/control/governance/relationships.py").read_text(
        encoding="utf-8"
    )
    assert "RelationshipSpec(" not in source
    assert "relationship_runtime().relationships" in source


@pytest.mark.parametrize(
    ("mutator", "error"),
    [
        (lambda d: d.__setitem__("relationships", []), "ontology"),
        (lambda d: d["relationships"].__setitem__(0, "bad"), "entry"),
        (lambda d: d["relationships"][0].__setitem__("extra", True), "entry-fields"),
        (
            lambda d: d["relationships"][1].__setitem__(
                "name", d["relationships"][0]["name"]
            ),
            "name-duplicate",
        ),
    ],
)
def test_compiler_rejects_invalid_ontology_and_identity(monkeypatch, mutator, error):
    _fake(monkeypatch, mutator)
    with pytest.raises(FrameworkContractError, match=f"relationship-runtime-{error}$"):
        compile_relationship_runtime(ROOT)


@pytest.mark.parametrize(
    ("mutator", "error"),
    [
        (
            lambda d: d["relationships"][0].__setitem__("source_types", []),
            "source-types",
        ),
        (
            lambda d: d["relationships"][0].__setitem__("source_types", ["GDC", "GDC"]),
            "source-types-duplicate",
        ),
        (
            lambda d: d["relationships"][0].__setitem__("source_types", ["UNKNOWN"]),
            "source-types-unknown",
        ),
        (
            lambda d: d["relationships"][0].__setitem__("target_types", ["UNKNOWN"]),
            "target-types-unknown",
        ),
        (
            lambda d: d["relationships"][1].update(
                source_types=["GDC"], metadata_field="governed_by"
            ),
            "source-field",
        ),
    ],
)
def test_compiler_rejects_invalid_type_surfaces(monkeypatch, mutator, error):
    _fake(monkeypatch, mutator)
    with pytest.raises(FrameworkContractError, match=f"relationship-runtime-{error}$"):
        compile_relationship_runtime(ROOT)


@pytest.mark.parametrize(
    ("mutator", "error"),
    [
        (
            lambda d: d["relationships"][0].__setitem__("min_targets", -1),
            "min-targets",
        ),
        (
            lambda d: d["relationships"][7].__setitem__("max_targets", 0),
            "max-targets",
        ),
        (
            lambda d: d["relationships"][0].__setitem__("direction", "sideways"),
            "direction",
        ),
        (
            lambda d: d["relationships"][0].__setitem__("dag_participation", 1),
            "dag-participation",
        ),
        (
            lambda d: d["relationships"][0].__setitem__(
                "authority_requirement", "unknown"
            ),
            "authority-requirement",
        ),
        (
            lambda d: d["relationships"][0].__setitem__("inverse_relation", ""),
            "inverse",
        ),
        (
            lambda d: d["relationships"][0].__setitem__("allow_self_reference", 1),
            "self-reference",
        ),
    ],
)
def test_compiler_rejects_invalid_relation_policy(monkeypatch, mutator, error):
    _fake(monkeypatch, mutator)
    with pytest.raises(FrameworkContractError, match=f"relationship-runtime-{error}$"):
        compile_relationship_runtime(ROOT)


@pytest.mark.parametrize(
    ("mutator", "error"),
    [
        (
            lambda d: _relation(d, "sad-parent-pad").__setitem__(
                "source_statuses_requiring_authority", ["missing"]
            ),
            "source-statuses-unknown",
        ),
        (
            lambda d: _relation(d, "sad-parent-pad").__setitem__(
                "allowed_target_statuses", ["missing"]
            ),
            "target-statuses-unknown",
        ),
        (
            lambda d: d["relationships"][0].__setitem__(
                "source_statuses_requiring_authority", ["draft"]
            ),
            "unexpected-status-constraint",
        ),
        (
            lambda d: _relation(d, "sad-parent-pad").__setitem__(
                "source_statuses_requiring_authority", []
            ),
            "authority-status-constraint",
        ),
    ],
)
def test_compiler_rejects_invalid_lifecycle_constraints(monkeypatch, mutator, error):
    _fake(monkeypatch, mutator)
    with pytest.raises(FrameworkContractError, match=f"relationship-runtime-{error}$"):
        compile_relationship_runtime(ROOT)


def test_compiler_rejects_missing_inverse(monkeypatch):
    def mutate(data):
        _relation(data, "sad-parent-pad")["inverse_relation"] = "missing"

    _fake(monkeypatch, mutate)
    with pytest.raises(FrameworkContractError, match="inverse-missing"):
        compile_relationship_runtime(ROOT)


def test_compiler_rejects_inconsistent_inverse(monkeypatch):
    def mutate(data):
        _relation(data, "sad-parent-pad")["inverse_relation"] = "governed_by"

    _fake(monkeypatch, mutate)
    with pytest.raises(FrameworkContractError, match="inverse-inconsistent"):
        compile_relationship_runtime(ROOT)


def test_runtime_grouping_is_source_specific_and_immutable():
    runtime = relationship_runtime()
    assert {spec.metadata_field for spec in runtime.by_source["TDD"]} == {
        "parent_sad",
    }
    with pytest.raises(TypeError):
        runtime.by_source["TDD"] = ()  # type: ignore[index]
