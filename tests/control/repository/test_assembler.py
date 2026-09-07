from __future__ import annotations

from pathlib import Path
from types import MappingProxyType

import pytest

from engine.control.repository import (
    RepositoryAssembler,
    RepositoryAssemblyError,
    RepositoryIdentityError,
    RepositoryIngestionError,
)


def _write_artifact(
    path: Path,
    *,
    document_id: str | None = "GDC-900",
    extra_meta: str = "",
) -> None:
    id_line = f"  id: {document_id}\n" if document_id is not None else ""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        "doc_meta:\n"
        f"{id_line}"
        "  title: Test Artifact\n"
        "  status: draft\n"
        f"{extra_meta}"
        "---\n"
        "# Test Artifact\n\n"
        "## 1. Purpose\nBody\n",
        encoding="utf-8",
    )


def test_zero_corpus_builds_empty_pure_model(tmp_path):
    model = RepositoryAssembler.load(str(tmp_path), repo_root=tmp_path)
    assert model.is_empty
    assert model.artifacts == ()


def test_load_is_deterministic_repo_relative_and_typed(tmp_path):
    _write_artifact(tmp_path / "z.md", document_id="GDC-902")
    _write_artifact(tmp_path / "nested" / "a.md", document_id="GDC-901")

    model = RepositoryAssembler.load(str(tmp_path), repo_root=tmp_path)

    assert tuple(record.path for record in model.artifacts) == (
        "nested/a.md",
        "z.md",
    )
    first = model.records_for_id("GDC-901")[0]
    assert first.artifact.artifact_type == "GDC"
    assert first.artifact.sections["1. purpose"] == "Body"


def test_metadata_projection_is_deeply_immutable(tmp_path):
    _write_artifact(
        tmp_path / "artifact.md",
        extra_meta="  tags: [one, two]\n  nested:\n    enabled: true\n",
    )
    model = RepositoryAssembler.load(str(tmp_path), repo_root=tmp_path)
    metadata = model.artifacts[0].metadata

    assert isinstance(metadata, MappingProxyType)
    assert metadata["tags"] == ("one", "two")
    assert isinstance(metadata["nested"], MappingProxyType)

    with pytest.raises(TypeError):
        metadata["nested"]["enabled"] = False  # type: ignore[index]


@pytest.mark.parametrize(
    ("content", "match"),
    (
        ("# Missing frontmatter\n", "Malformed artifact"),
        ("---\ndoc_meta: [unterminated\n---\n", "Malformed artifact"),
    ),
)
def test_malformed_markdown_fails_closed(tmp_path, content, match):
    path = tmp_path / "broken.md"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(RepositoryIngestionError, match=match):
        RepositoryAssembler.load(str(tmp_path), repo_root=tmp_path)


def test_non_utf8_artifact_fails_closed(tmp_path):
    path = tmp_path / "broken.md"
    path.write_bytes(b"\xff\xfe\x00")
    with pytest.raises(RepositoryIngestionError, match="UTF-8"):
        RepositoryAssembler.load(str(tmp_path), repo_root=tmp_path)


def test_missing_unknown_and_duplicate_identity_fail_before_model_creation(tmp_path):
    _write_artifact(tmp_path / "missing.md", document_id=None)
    with pytest.raises(RepositoryIngestionError, match="doc_meta.id"):
        RepositoryAssembler.load(str(tmp_path), repo_root=tmp_path)

    (tmp_path / "missing.md").unlink()
    _write_artifact(tmp_path / "unknown.md", document_id="UNKNOWN-001")
    with pytest.raises(
        RepositoryIdentityError, match="Unknown governed artifact identity"
    ):
        RepositoryAssembler.load(str(tmp_path), repo_root=tmp_path)

    (tmp_path / "unknown.md").unlink()
    _write_artifact(tmp_path / "a.md", document_id="GDC-999")
    _write_artifact(tmp_path / "b.md", document_id="GDC-999")
    with pytest.raises(
        RepositoryIdentityError, match="duplicate canonical artifact identity"
    ):
        RepositoryAssembler.load(str(tmp_path), repo_root=tmp_path)


def test_boundary_failure_is_normalized_to_assembly_error(tmp_path):
    repo_root = tmp_path / "repo"
    external = tmp_path / "external"
    repo_root.mkdir()
    external.mkdir()
    _write_artifact(external / "outside.md")
    with pytest.raises(RepositoryAssemblyError, match="outside"):
        RepositoryAssembler.load(str(external), repo_root=repo_root)


def test_governed_corpus_ignores_derived_and_root_support_markdown(tmp_path):
    governance = tmp_path / "governance"
    _write_artifact(governance / "GDC-900-test.md", document_id="GDC-900")
    (governance / "INDEX.md").write_text("# Derived index\n", encoding="utf-8")
    templates = governance / "templates"
    templates.mkdir()
    (templates / "review-score-sheet.md").write_text(
        "# Governance support template without artifact frontmatter\n",
        encoding="utf-8",
    )
    (tmp_path / "ROADMAP.md").write_text("# Root support\n", encoding="utf-8")

    model = RepositoryAssembler.load_governed_corpus(repo_root=tmp_path)
    assert tuple(record.document_id for record in model.artifacts) == ("GDC-900",)


def test_governed_corpus_support_exclusion_does_not_weaken_fail_closed(tmp_path):
    governance = tmp_path / "governance"
    governance.mkdir()

    (governance / "GDC-901-broken.md").write_text(
        "# Governed artifact missing frontmatter\n",
        encoding="utf-8",
    )

    with pytest.raises(RepositoryIngestionError, match="Malformed artifact"):
        RepositoryAssembler.load_governed_corpus(repo_root=tmp_path)


def test_governed_corpus_composes_caller_ignore_patterns_with_support_policy(
    tmp_path,
):
    governance = tmp_path / "governance"
    _write_artifact(governance / "GDC-902-test.md", document_id="GDC-902")
    _write_artifact(governance / "GDC-903-ignore.md", document_id="GDC-903")

    templates = governance / "templates"
    templates.mkdir()
    (templates / "review-score-sheet.md").write_text(
        "# support only\n",
        encoding="utf-8",
    )

    model = RepositoryAssembler.load_governed_corpus(
        repo_root=tmp_path,
        ignored_patterns=[r"GDC-903-ignore\.md$"],
    )

    assert tuple(record.document_id for record in model.artifacts) == ("GDC-902",)


def test_relationships_are_interpreted_once_into_typed_model():
    entry = RepositoryAssembler.artifact_from_metadata(
        metadata={
            "id": "SAD-001",
            "title": "SAD",
            "status": "draft",
            "parent_pad": "PAD-001",
            "governed_by": ["GDC-000"],
        },
        source_path="systems/SAD-001.md",
    )
    assert tuple(
        (relation.relation_type, relation.target.artifact_id)
        for relation in entry.artifact.relationships
    ) == (("governed_by", "GDC-000"), ("parent_pad", "PAD-001"))
    assert entry.metadata["parent_pad"] == ("PAD-001",)
