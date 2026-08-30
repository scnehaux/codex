from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from engine.control.repository import RepositoryIngestionError

ROOT = Path(__file__).resolve().parents[3]
GENERATOR_PATH = (
    ROOT
    / "06-fitness-function"
    / "generators"
    / "generate_traceability_graph.py"
)


def _load_generator(name: str = "traceability_repository_model"):
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
        "  title: Test\n"
        "  status: draft\n"
        f"{metadata}"
        "---\n"
        "# Test\n",
        encoding="utf-8",
    )


def test_governance_only_repository_is_clean_noop(tmp_path):
    module = _load_generator("traceability_zero_corpus")
    _write_artifact(
        tmp_path / "00-governance" / "GDC-000-policy.md",
        "GDC-000",
    )

    result = module.generate_graph(repo_root=tmp_path)

    assert result is None
    assert not (tmp_path / "03-domain").exists()


def test_malformed_architecture_corpus_fails_before_output(tmp_path):
    module = _load_generator("traceability_malformed")
    domain = tmp_path / "03-domain"
    domain.mkdir(parents=True)
    output = domain / "TRACEABILITY.md"
    output.write_text("previous-good-output\n", encoding="utf-8")
    (domain / "broken.md").write_text(
        "---\n"
        "doc_meta: [unterminated\n"
        "---\n",
        encoding="utf-8",
    )

    with pytest.raises(RepositoryIngestionError):
        module.generate_graph(repo_root=tmp_path)

    assert output.read_text(encoding="utf-8") == "previous-good-output\n"


def test_traceability_uses_canonical_relationship_fields(tmp_path):
    module = _load_generator("traceability_canonical_relations")

    _write_artifact(
        tmp_path / "01-enterprise" / "EAD-001-enterprise.md",
        "EAD-001",
    )
    _write_artifact(
        tmp_path / "03-domain" / "PAD-001-platform.md",
        "PAD-001",
        "  realizes_capability: [EAD-001]\n",
    )
    _write_artifact(
        tmp_path / "04-system" / "SAD-001-system.md",
        "SAD-001",
        "  parent_pad: PAD-001\n",
    )

    output = module.generate_graph(repo_root=tmp_path)

    assert output == tmp_path / "03-domain" / "TRACEABILITY.md"
    rendered = output.read_text(encoding="utf-8")
    assert "|realizes_capability|" in rendered
    assert "|parent_pad|" in rendered
    assert "EAD-001" in rendered
    assert "PAD-001" in rendered
    assert "SAD-001" in rendered


def test_generated_traceability_is_ignored_on_rerun(tmp_path):
    module = _load_generator("traceability_rerun")

    _write_artifact(
        tmp_path / "03-domain" / "PAD-001-platform.md",
        "PAD-001",
    )

    first = module.generate_graph(repo_root=tmp_path)
    assert first is not None
    first_content = first.read_text(encoding="utf-8")

    second = module.generate_graph(repo_root=tmp_path)

    assert second == first
    assert second.read_text(encoding="utf-8") == first_content


def test_generator_has_no_shadow_ingestion_authority():
    source = GENERATOR_PATH.read_text(encoding="utf-8")

    assert "import yaml" not in source
    assert "import glob" not in source
    assert "parse_metadata" not in source
    assert "discover_markdown_files" not in source
    assert "parse_frontmatter" not in source
    assert "relationship_specs_for_source" not in source
    assert "record.artifact.relationships" in source
    assert "RepositoryAssembler.load_governed_corpus" in source

def test_traceability_main_returns_nonzero_on_repository_failure(monkeypatch):
    module = _load_generator("traceability_main_failure")

    from engine.control.repository import RepositoryModelError

    def fail_generation(*args, **kwargs):
        raise RepositoryModelError("boom")

    monkeypatch.setattr(
        module,
        "generate_graph",
        fail_generation,
    )

    assert module.main() == 1

