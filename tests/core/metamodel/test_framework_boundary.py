from tests.support.repository import REPOSITORY_ROOT
from pathlib import Path

import yaml


ROOT = REPOSITORY_ROOT
CONTRACT = (
    ROOT
    / "00-governance"
    / "framework"
    / "scnehaux-framework.yaml"
)


def test_framework_boundary_contract_is_generic_and_complete():
    data = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))

    assert data["kind"] == "scnehaux-framework-boundary"
    assert (
        data["product"]["canonical_authority"]
        == "git-backed-structured-architecture"
    )

    modules = data["logical_modules"]
    assert set(modules) == {
        "scnehaux-core",
        "scnehaux-control",
        "scnehaux-knowledge",
        "scnehaux-ai",
        "scnehaux-observe",
        "scnehaux-interface",
    }

    assert data["deployment"]["default"] == "modular-monolith"
    assert data["company_pack"]["must_not_require_core_fork"] is True

    assert "foundation-model" in data["does_not_own"]
    assert "graph-database-engine" in data["does_not_own"]
    assert "model-provider" in data["extension_points"]

    serialized = CONTRACT.read_text(encoding="utf-8").lower()
    assert "ati business" not in serialized
    assert "aviation" not in serialized
    assert "banking" not in serialized
