from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from engine.core.repository import RepositoryArtifact, RepositoryModel

from engine.control.repository import RepositoryAssembler, RepositoryIngestionError, RepositoryModelError
from types import MappingProxyType


ROOT = Path(__file__).resolve().parents[3]
GENERATOR_PATH = (
    ROOT
    / "06-fitness-function"
    / "generators"
    / "generate_adr_index.py"
)


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
        "  title: Test Decision\n"
        "  owner: Architecture\n"
        "  status: draft\n"
        f"{metadata}"
        "---\n"
        "# Test\n",
        encoding="utf-8",
    )


def test_governance_only_repository_is_clean_noop(tmp_path):
    module = _load_generator("adr_zero")
    _write_artifact(
        tmp_path / "00-governance" / "GDC-000-policy.md",
        "GDC-000",
    )

    output = module.generate_index(repo_root=tmp_path)

    assert output is None
    assert not (tmp_path / "05-decisions").exists()


def test_adr_corpus_generates_expected_index(tmp_path):
    module = _load_generator("adr_generate")
    _write_artifact(
        tmp_path / "05-decisions" / "domain" / "ADR-002.md",
        "ADR-002",
        "  title: Later | Decision\n"
        "  adr_type: architectural\n"
        "  created: 2026-08-29\n"
        "  expiry_date: 2027-08-29\n",
    )
    _write_artifact(
        tmp_path / "05-decisions" / "ADR-001.md",
        "ADR-001",
        "  title: First Decision\n"
        "  adr_type: governance\n",
    )

    output = module.generate_index(repo_root=tmp_path)

    assert output == tmp_path / "05-decisions" / "INDEX.md"
    content = output.read_text(encoding="utf-8")
    assert "[ADR-001](ADR-001.md)" in content
    assert "[ADR-002](domain/ADR-002.md)" in content
    assert "Later \\| Decision" in content
    assert content.index("ADR-001") < content.index("ADR-002")


def test_malformed_corpus_fails_before_existing_index_changes(tmp_path):
    module = _load_generator("adr_malformed")
    decisions = tmp_path / "05-decisions"
    decisions.mkdir(parents=True)
    index = decisions / "INDEX.md"
    index.write_text("previous-good-index\n", encoding="utf-8")

    (decisions / "broken.md").write_text(
        "---\n"
        "doc_meta: [unterminated\n"
        "---\n",
        encoding="utf-8",
    )

    with pytest.raises(RepositoryIngestionError):
        module.generate_index(repo_root=tmp_path)

    assert index.read_text(encoding="utf-8") == "previous-good-index\n"


def test_generated_index_is_ignored_on_rerun(tmp_path):
    module = _load_generator("adr_rerun")
    _write_artifact(
        tmp_path / "05-decisions" / "ADR-001.md",
        "ADR-001",
    )

    first = module.generate_index(repo_root=tmp_path)
    assert first is not None
    first_content = first.read_text(encoding="utf-8")

    second = module.generate_index(repo_root=tmp_path)

    assert second == first
    assert second.read_text(encoding="utf-8") == first_content


def test_render_rejects_record_outside_decision_layer():
    module = _load_generator("adr_boundary")
    record = RepositoryAssembler.artifact_from_metadata(
        metadata={"id": "ADR-001", "title": "ADR-001", "status": "draft"},
        source_path="04-system/ADR-001.md",
    )

    with pytest.raises(RepositoryModelError, match="outside expected layer"):
        module.render_index((record,))


def test_main_returns_nonzero_on_repository_failure(monkeypatch):
    module = _load_generator("adr_main_failure")

    def fail_generation():
        raise RepositoryModelError("boom")

    monkeypatch.setattr(module, "generate_index", fail_generation)

    assert module.main() == 1


def test_main_returns_zero_on_success(monkeypatch):
    module = _load_generator("adr_main_success")
    monkeypatch.setattr(module, "generate_index", lambda: None)

    assert module.main() == 0


def test_generator_has_no_shadow_ingestion_authority():
    source = GENERATOR_PATH.read_text(encoding="utf-8")

    assert "import yaml" not in source
    assert "os.walk" not in source
    assert "parse_frontmatter" not in source
    assert "safe_load" not in source
    assert "RepositoryAssembler.load_governed_corpus" in source
    assert "snapshot.require_generation_ready()" not in source
    assert "_atomic_write_text" in source
