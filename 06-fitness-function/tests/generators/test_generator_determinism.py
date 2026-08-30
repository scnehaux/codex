import importlib.util
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]


def load_module(name: str, relative_path: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_traceability_render_is_independent_of_snapshot_order():
    module = load_module(
        "traceability_generator",
        "06-fitness-function/generators/generate_traceability_graph.py",
    )

    from engine.control.repository import RepositoryAssembler
    from engine.core.repository import RepositoryModel

    def entry(path, artifact_id, **metadata):
        return RepositoryAssembler.artifact_from_metadata(
            metadata={
                "id": artifact_id,
                "title": artifact_id,
                "status": "draft",
                **metadata,
            },
            source_path=path,
        )

    records = (
        entry("04-system/SAD-002.md", "SAD-002", parent_pad="PAD-PLT-002"),
        entry("01-enterprise/EAD-002.md", "EAD-002", governed_by="GDC-000"),
        entry(
            "03-domain/PAD-PLT-002.md",
            "PAD-PLT-002",
            realizes_capability=["EAD-002", "EAD-001"],
        ),
        entry("01-enterprise/EAD-001.md", "EAD-001", governed_by="GDC-000"),
    )

    snapshot = RepositoryModel(records)
    reversed_snapshot = RepositoryModel(tuple(reversed(records)))

    assert module.render_graph(snapshot) == module.render_graph(reversed_snapshot)


def test_topography_render_is_independent_of_path_order():
    module = load_module(
        "topography_generator",
        "06-fitness-function/generators/generate_engine_topography.py",
    )

    paths = [
        ("engine", "reporting", "reporter.py"),
        ("engine", "cli.py"),
        ("scripts", "codeowners-validator.py"),
        ("generators", "generate_traceability_graph.py"),
    ]

    assert module.generate_markdown_from_paths(
        paths
    ) == module.generate_markdown_from_paths(list(reversed(paths)))


def test_topography_uses_live_canonical_inputs_not_git_index(tmp_path, monkeypatch):
    module = load_module(
        "topography_generator_live",
        "06-fitness-function/generators/generate_engine_topography.py",
    )
    monkeypatch.setattr(module, "ROOT_DIR", str(tmp_path))

    (tmp_path / "engine" / "control" / "reporting").mkdir(parents=True)
    (tmp_path / "engine" / "control" / "reporting" / "reporter.py").write_text("", encoding="utf-8")
    (tmp_path / "06-fitness-function" / "scratch").mkdir(parents=True)
    (tmp_path / "06-fitness-function" / "scratch" / "tmp.py").write_text("", encoding="utf-8")
    (tmp_path / "06-fitness-function" / "scnehaux_linter.egg-info").mkdir()
    (tmp_path / "06-fitness-function" / "scnehaux_linter.egg-info" / "PKG-INFO").write_text("", encoding="utf-8")

    live = module.live_paths()
    flattened = {"/".join(parts) for parts in live}

    assert not any("scratch/" in path for path in flattened)
    assert not any(".egg-info/" in path for path in flattened)
    assert "engine/control/reporting/reporter.py" in flattened
