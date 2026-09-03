from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


from engine.control.repository import (
    RepositoryAssembler,
    RepositoryIngestionError,
    RepositoryModelError,
)


ROOT = Path(__file__).resolve().parents[2]
GENERATOR_PATH = ROOT / "generators" / "generate_pad_sad_index.py"


def _load_generator(name: str):
    spec = importlib.util.spec_from_file_location(name, GENERATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_artifact(
    path: Path,
    document_id: str,
    metadata: str = "",
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        "doc_meta:\n"
        f"  id: {document_id}\n"
        "  title: Test Artifact\n"
        "  owner: Architecture\n"
        "  status: draft\n"
        f"{metadata}"
        "---\n"
        "# Test\n",
        encoding="utf-8",
    )


def test_governance_only_repository_is_clean_noop(tmp_path):
    module = _load_generator("pad_sad_zero")
    _write_artifact(
        tmp_path / "governance" / "GDC-000-policy.md",
        "GDC-000",
    )

    generated = module.generate_indexes(repo_root=tmp_path)

    assert generated == ()
    assert not (tmp_path / "domains").exists()
    assert not (tmp_path / "systems").exists()


def test_pad_only_generates_only_domain_index(tmp_path):
    module = _load_generator("pad_only")
    _write_artifact(
        tmp_path / "domains" / "platform" / "PAD-001.md",
        "PAD-001",
        "  fulfilled_by: [SAD-001, SAD-002]\n",
    )

    generated = module.generate_indexes(repo_root=tmp_path)

    assert generated == (tmp_path / "domains" / "INDEX.md",)
    assert not (tmp_path / "systems").exists()

    content = generated[0].read_text(encoding="utf-8")
    assert "[PAD-001](platform/PAD-001.md)" in content
    assert "| 2 |" in content


def test_sad_only_generates_only_system_index(tmp_path):
    module = _load_generator("sad_only")
    _write_artifact(
        tmp_path / "systems" / "system" / "SAD-001.md",
        "SAD-001",
        "  parent_pad: [PAD-002, PAD-001]\n",
    )

    generated = module.generate_indexes(repo_root=tmp_path)

    assert generated == (tmp_path / "systems" / "INDEX.md",)
    assert not (tmp_path / "domains").exists()

    content = generated[0].read_text(encoding="utf-8")
    assert "[SAD-001](system/SAD-001.md)" in content
    assert "PAD-002, PAD-001" in content


def test_malformed_corpus_fails_before_existing_index_changes(tmp_path):
    module = _load_generator("pad_sad_malformed")
    domain = tmp_path / "domains"
    domain.mkdir(parents=True)
    index = domain / "INDEX.md"
    index.write_text("previous-good-index\n", encoding="utf-8")

    (domain / "broken.md").write_text(
        "---\ndoc_meta: [unterminated\n---\n",
        encoding="utf-8",
    )

    with pytest.raises(RepositoryIngestionError):
        module.generate_indexes(repo_root=tmp_path)

    assert index.read_text(encoding="utf-8") == "previous-good-index\n"


def test_rerun_is_deterministic_and_generated_indexes_are_not_reingested(tmp_path):
    module = _load_generator("pad_sad_rerun")
    _write_artifact(
        tmp_path / "domains" / "z" / "PAD-002.md",
        "PAD-002",
    )
    _write_artifact(
        tmp_path / "domains" / "a" / "PAD-001.md",
        "PAD-001",
    )

    first = module.generate_indexes(repo_root=tmp_path)
    first_content = first[0].read_text(encoding="utf-8")

    second = module.generate_indexes(repo_root=tmp_path)

    assert second == first
    assert second[0].read_text(encoding="utf-8") == first_content
    assert first_content.index("PAD-001") < first_content.index("PAD-002")


def test_render_rejects_wrong_layer_path():
    module = _load_generator("pad_sad_layer_boundary")

    record = RepositoryAssembler.artifact_from_metadata(
        metadata={"id": "PAD-001", "title": "PAD-001", "status": "draft"},
        source_path="systems/SAD-001.md",
    )

    with pytest.raises(RepositoryModelError, match="outside expected layer"):
        module.render_index(
            (record,),
            artifact_type="PAD",
            layer_root=Path("domains"),
            layer_name="Platform Architecture (PAD)",
        )


def test_render_rejects_unsupported_artifact_type():
    module = _load_generator("pad_sad_bad_type")

    with pytest.raises(RepositoryModelError, match="Unsupported"):
        module.render_index(
            (),
            artifact_type="EAD",
            layer_root=Path("enterprise"),
            layer_name="Enterprise Architecture",
        )


def test_generator_has_no_shadow_ingestion_authority():
    source = GENERATOR_PATH.read_text(encoding="utf-8")

    assert "import yaml" not in source
    assert "import glob" not in source
    assert "parse_metadata" not in source
    assert "safe_load" not in source
    assert "RepositoryAssembler.load_governed_corpus" in source
    assert "_atomic_write_text" in source


def test_pad_sad_main_returns_nonzero_on_repository_failure(monkeypatch):
    module = _load_generator("pad_sad_main_failure")

    from engine.control.repository import RepositoryModelError

    def fail_generation(*args, **kwargs):
        raise RepositoryModelError("boom")

    monkeypatch.setattr(
        module,
        "generate_indexes",
        fail_generation,
    )

    assert module.main() == 1
