from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
from types import MappingProxyType

import pytest

from engine.core.repository import RepositoryArtifact, RepositoryModel

from engine.control.repository import RepositoryAssembler, RepositoryIdentityError


ROOT = Path(__file__).resolve().parents[3]
FITNESS_ROOT = ROOT / "06-fitness-function"
GENERATOR_ROOT = FITNESS_ROOT / "generators"

ARCH_GENERATORS = (
    "generate_adr_index.py",
    "generate_maturity_dashboard.py",
    "generate_pad_sad_index.py",
    "generate_traceability_graph.py",
)


def _load_generator(filename: str, name: str):
    path = GENERATOR_ROOT / filename
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _record(path: str, document_id: str, **metadata) -> RepositoryArtifact:
    artifact_type = document_id.split("-", 1)[0]
    values = {
        "id": document_id,
        "title": metadata.pop("title", document_id),
        "status": metadata.pop("status", "draft"),
        **metadata,
    }
    if artifact_type == "UNKNOWN":
        from engine.core.metamodel import ArtifactIdentity, ArtifactModel
        return RepositoryArtifact(
            artifact=ArtifactModel(
                identity=ArtifactIdentity(document_id),
                artifact_type="UNKNOWN",
                title=document_id,
                lifecycle_status="draft",
                attributes=values,
            ),
            source_path=path,
        )
    return RepositoryAssembler.artifact_from_metadata(
        metadata=values,
        source_path=path,
    )


def _snapshot(*records: RepositoryArtifact) -> RepositoryModel:
    return RepositoryModel(tuple(records))


@pytest.mark.parametrize("filename", ARCH_GENERATORS)
def test_arch_generator_standalone_import_bootstraps_repository_root(filename):
    repository = str(ROOT)
    original = list(sys.path)

    try:
        sys.path[:] = [entry for entry in sys.path if entry != repository]
        _load_generator(
            filename,
            f"bootstrap_{Path(filename).stem}",
        )
        assert repository in sys.path
    finally:
        sys.path[:] = original


@pytest.mark.parametrize("filename", ARCH_GENERATORS)
def test_arch_generator_atomic_write_cleans_temp_after_replace_failure(
    filename,
    tmp_path,
    monkeypatch,
):
    module = _load_generator(
        filename,
        f"atomic_{Path(filename).stem}",
    )
    output = tmp_path / "OUTPUT.md"
    temp = tmp_path / ".OUTPUT.md.tmp"

    def fail_replace(self, target):
        raise OSError("replace failed")

    monkeypatch.setattr(Path, "replace", fail_replace)

    with pytest.raises(OSError, match="replace failed"):
        module._atomic_write_text(output, "content\n")

    assert not temp.exists()
    assert not output.exists()


def test_pad_sad_scalar_and_empty_relationship_metadata_are_supported():
    module = _load_generator(
        "generate_pad_sad_index.py",
        "pad_sad_scalar_metadata",
    )

    assert module._relation_count("SAD-001") == 1
    assert module._render_parent_pad(None) == ""
    assert module._render_parent_pad("PAD-001") == "PAD-001"


def test_maturity_renderer_supports_empty_evidence_and_clean_registry():
    module = _load_generator(
        "generate_maturity_dashboard.py",
        "maturity_empty_evidence",
    )

    rendered = module.render_dashboard(
        artifact_inventory={},
        evidence_inventory={},
        control_total=0,
        registry_findings=(),
    )

    assert "- No evidence states recorded" in rendered
    assert "- Registry integrity: **PASS**" in rendered


def test_repository_assembler_rejects_unknown_architecture_identity():
    with pytest.raises(
        RepositoryIdentityError,
        match="Unknown governed artifact identity",
    ):
        RepositoryAssembler.artifact_from_metadata(
            metadata={
                "id": "UNKNOWN-001",
                "title": "Unknown",
                "status": "draft",
            },
            source_path="03-domain/UNKNOWN-001.md",
        )


def test_traceability_ignores_governance_artifacts():
    module = _load_generator(
        "generate_traceability_graph.py",
        "traceability_governance",
    )
    record = _record(
        "00-governance/GDC-001.md",
        "GDC-001",
    )
    assert module._architecture_records(_snapshot(record)) == ()


def test_traceability_filters_invalid_targets_and_renders_external_target():
    module = _load_generator(
        "generate_traceability_graph.py",
        "traceability_target_filtering",
    )
    pad = _record(
        "03-domain/PAD-001.md",
        "PAD-001",
        realizes_capability=("EAD-999",),
    )
    snapshot = _snapshot(pad)

    records = module._architecture_records(snapshot)
    edges = module._graph_edges(records)

    assert edges == (("PAD-001", "EAD-999", "realizes_capability"),)

    rendered = module.render_graph(snapshot)
    assert "%% External Relationship Targets" in rendered
    assert '["EAD-999"]:::external' in rendered


@pytest.mark.parametrize(
    ("filename", "target_function"),
    (
        ("generate_pad_sad_index.py", "generate_indexes"),
        ("generate_traceability_graph.py", "generate_graph"),
    ),
)
def test_remaining_arch_generator_main_success_returns_zero(
    filename,
    target_function,
    monkeypatch,
):
    module = _load_generator(
        filename,
        f"main_success_{Path(filename).stem}",
    )
    monkeypatch.setattr(
        module,
        target_function,
        lambda: None,
    )

    assert module.main() == 0

@pytest.mark.parametrize(
    "filename",
    (
        "generate_adr_index.py",
        "generate_pad_sad_index.py",
        "generate_traceability_graph.py",
    ),
)
def test_arch_generator_direct_execution_resolves_repository_root(filename):
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    result = subprocess.run(
        [sys.executable, str(GENERATOR_ROOT / filename)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        env=env,
    )

    assert result.returncode == 0, (
        (result.stdout or "") + "\n" + (result.stderr or "")
    )
    assert "ModuleNotFoundError" not in (result.stderr or "")

