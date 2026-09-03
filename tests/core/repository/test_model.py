from __future__ import annotations

from pathlib import Path

import pytest

from engine.core.metamodel import ArtifactIdentity, ArtifactModel
from engine.core.repository import RepositoryArtifact, RepositoryModel


def _entry(
    path: str, artifact_id: str, artifact_type: str = "GDC"
) -> RepositoryArtifact:
    return RepositoryArtifact(
        artifact=ArtifactModel(
            identity=ArtifactIdentity(artifact_id),
            artifact_type=artifact_type,
            title=f"{artifact_id} title",
            lifecycle_status="draft",
            attributes={"owner": "Architecture"},
        ),
        source_path=path,
    )


def test_repository_model_is_deterministic_and_indexed():
    second = _entry("systems/SAD-002.md", "SAD-002", "SAD")
    first = _entry("governance/GDC-001.md", "GDC-001")
    model = RepositoryModel((second, first))

    assert tuple(item.path for item in model.artifacts) == (
        "governance/GDC-001.md",
        "systems/SAD-002.md",
    )
    assert model.records_for_id("SAD-002") == (second,)
    assert model.artifacts_of_type("sad") == (second,)
    assert model.require("SAD-002") == second


def test_repository_model_rejects_duplicate_identity_and_path():
    a = _entry("a.md", "GDC-001")
    b = _entry("b.md", "GDC-001")
    with pytest.raises(ValueError, match="duplicate canonical artifact identity"):
        RepositoryModel((a, b))

    c = _entry("a.md", "GDC-002")
    with pytest.raises(ValueError, match="duplicate repository source path"):
        RepositoryModel((a, c))


def test_repository_artifact_projection_comes_from_artifact_model():
    entry = _entry("governance/GDC-001.md", "GDC-001")
    assert entry.document_id == "GDC-001"
    assert entry.artifact_type == "GDC"
    assert entry.metadata["title"] == "GDC-001 title"
    assert entry.metadata["status"] == "draft"
    assert entry.metadata["owner"] == "Architecture"
    with pytest.raises(TypeError):
        entry.metadata["owner"] = "mutated"  # type: ignore[index]


def test_core_repository_has_no_outward_control_dependency():
    source = (
        Path(__file__).resolve().parents[3]
        / "engine"
        / "core"
        / "repository"
        / "model.py"
    ).read_text(encoding="utf-8")
    assert "engine.control" not in source


def test_repository_artifact_rejects_invalid_source_and_type():
    artifact = ArtifactModel(
        identity=ArtifactIdentity("GDC-010"),
        artifact_type="GDC",
        title="GDC",
        lifecycle_status="draft",
    )
    with pytest.raises(ValueError, match="blank"):
        RepositoryArtifact(artifact=artifact, source_path=" ")
    with pytest.raises(ValueError, match="repository-relative"):
        RepositoryArtifact(artifact=artifact, source_path="../escape.md")
    with pytest.raises(TypeError, match="ArtifactModel"):
        RepositoryArtifact(artifact="bad", source_path="gdc.md")  # type: ignore[arg-type]


def test_repository_model_auxiliary_contracts():
    entry = _entry("governance/GDC-001.md", "GDC-001")
    model = RepositoryModel((entry,))
    assert model.artifact_models == (entry.artifact,)
    assert model.semantic_state()[0][0] == entry.source_path
    with pytest.raises(KeyError, match="unknown artifact identity"):
        model.require("GDC-404")
    with pytest.raises(TypeError, match="RepositoryArtifact"):
        RepositoryModel(("bad",))  # type: ignore[arg-type]
