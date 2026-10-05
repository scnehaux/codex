from __future__ import annotations

import shutil
import subprocess

import pytest
import yaml

from engine.control.governance.corpus import assert_governed_corpus
from engine.core.knowledge import compile_repository_graph
from tests.support.repository import REPOSITORY_ROOT


def _git(root, *args):
    return (
        subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.PIPE)
        .decode()
        .strip()
    )


def _commit(root):
    _git(root, "add", ".")
    _git(
        root,
        "-c",
        "user.name=Corpus test",
        "-c",
        "user.email=corpus@example.invalid",
        "commit",
        "--no-gpg-sign",
        "-qm",
        "Corpus fixture",
    )


@pytest.fixture
def corpus_root(tmp_path):
    root = tmp_path / "corpus"
    for directory in ("governance", "schemas", "engine"):
        shutil.copytree(
            REPOSITORY_ROOT / directory,
            root / directory,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    for directory in ("generators", "scripts", "tests"):
        target = root / directory
        target.mkdir()
        shutil.copyfile(REPOSITORY_ROOT / directory / "INDEX.md", target / "INDEX.md")
    _git(root, "init", "-q")
    _commit(root)
    return root


def test_real_corpus_builds_commit_bound_snapshot_and_graph(corpus_root):
    first = assert_governed_corpus(corpus_root)
    second = assert_governed_corpus(corpus_root)
    assert first == second
    assert first.revision == _git(corpus_root, "rev-parse", "HEAD")
    assert len(first.repository.artifacts) == 12
    assert len(compile_repository_graph(first).nodes) == 12
    assert all(
        artifact.artifact.evidence[0].revision == first.revision
        for artifact in first.repository.artifacts
    )


@pytest.mark.parametrize("tracked", [True, False])
def test_dirty_corpus_cannot_claim_committed_snapshot(corpus_root, tracked):
    path = corpus_root / (
        "governance/GDC-011-tdd-guideline.md" if tracked else "untracked.md"
    )
    path.write_text("broken candidate", encoding="utf-8")
    with pytest.raises(RuntimeError, match="clean checkout"):
        assert_governed_corpus(corpus_root)


def test_malformed_committed_gdc_blocks_qualification(corpus_root):
    path = corpus_root / "governance/GDC-000-governance-policy.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "classification: public", "classification: invalid"
        ),
        encoding="utf-8",
    )
    _commit(corpus_root)
    with pytest.raises(RuntimeError, match="pass validation.*GDC-000"):
        assert_governed_corpus(corpus_root)


def test_missing_required_gdc_blocks_qualification(corpus_root):
    path = next((corpus_root / "governance").glob("GDC-011-*.md"))
    path.unlink()
    _commit(corpus_root)
    with pytest.raises(RuntimeError, match="required baseline GDCs missing: GDC-011"):
        assert_governed_corpus(corpus_root)


def test_duplicate_committed_gdc_identity_blocks_qualification(corpus_root):
    source = corpus_root / "governance/GDC-000-governance-policy.md"
    shutil.copyfile(source, source.with_name("GDC-000-duplicate.md"))
    _commit(corpus_root)
    with pytest.raises(RuntimeError, match="[Dd]uplicate"):
        assert_governed_corpus(corpus_root)


@pytest.mark.parametrize("ids", [None, [], ["GDC-000", "GDC-000"], ["SAD-001"], [42]])
def test_invalid_baseline_inventory_fails_closed(corpus_root, ids):
    path = corpus_root / "governance/bootstrap-manifest.yaml"
    manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
    manifest["governance_control_plane"]["required_baseline_ids"] = ids
    path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
    _commit(corpus_root)
    with pytest.raises(RuntimeError, match="baseline GDC IDs"):
        assert_governed_corpus(corpus_root)


def test_revision_change_during_qualification_fails_closed(corpus_root, monkeypatch):
    import engine.control.governance.corpus as module

    revisions = iter((_git(corpus_root, "rev-parse", "HEAD"), "f" * 40))
    monkeypatch.setattr(module, "_clean_revision", lambda root: next(revisions))
    with pytest.raises(RuntimeError, match="revision changed"):
        assert_governed_corpus(corpus_root)


def test_unreadable_git_repository_fails_closed(tmp_path):
    with pytest.raises(RuntimeError, match="corpus qualification failed"):
        assert_governed_corpus(tmp_path)
