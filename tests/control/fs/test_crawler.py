import os
import pytest
from unittest.mock import patch
from engine.control.fs.crawler import build_metadata_registry, gather_markdown_paths


def test_build_metadata_registry_basic(tmp_path):
    """
    Validates the basic metadata extraction flow from Markdown files.
    Ensures that YAML frontmatter is parsed correctly to build a registry,
    and explicitly verifies that exclusions like 'node_modules' are enforced.
    """
    repo_dir = tmp_path / "scnehaux"
    repo_dir.mkdir()

    valid_md = repo_dir / "ADR-001.md"
    valid_md.write_text("---\ndoc_meta:\n  id: ADR-001\n---\nBody")

    no_meta_md = repo_dir / "README.md"
    no_meta_md.write_text("# Hello")

    node_mod = repo_dir / "node_modules"
    node_mod.mkdir()
    ignored_md = node_mod / "ADR-002.md"
    ignored_md.write_text("---\ndoc_meta:\n  id: ADR-002\n---\nBody")

    ids, registry, dupes = build_metadata_registry(str(repo_dir))

    assert "ADR-001" in ids
    assert "ADR-002" not in ids
    assert not dupes
    assert registry["ADR-001"]["id"] == "ADR-001"


def test_duplicate_id_detection(tmp_path):
    """
    Validates the Single Source of Truth (SSOT) invariant mechanism.
    Ensures that if multiple Markdown files declare the same architecture ID,
    they are correctly flagged and captured in the duplicates registry.
    """
    d = tmp_path / "repo"
    d.mkdir()
    (d / "a.md").write_text("---\ndoc_meta:\n  id: ADR-001\n---\nA")
    (d / "b.md").write_text("---\ndoc_meta:\n  id: ADR-001\n---\nB")
    (d / "c.md").write_text("---\ndoc_meta:\n  id: ADR-002\n---\nC")
    ids, meta, dupes = build_metadata_registry(str(d))
    assert "ADR-001" in dupes and len(dupes["ADR-001"]) == 2
    assert "ADR-002" not in dupes
    assert "ADR-002" in ids


def test_gather_markdown_paths_valueerror_relpath():
    """
    Validates the security mechanism handling cross-drive path traversals.
    Ensures that when os.path.relpath throws a ValueError due to mismatched drives
    (e.g., on Windows), the system performs a Fail-Closed hard crash (ValueError).
    """
    with patch("os.path.relpath", side_effect=ValueError("Different drive")):
        with pytest.raises(ValueError):
            gather_markdown_paths(
                "C:/docs/file.md", repo_root="D:/repo", allowed_root_dirs={"allowed"}
            )


def test_gather_markdown_paths_target_str():
    """
    Validates the type coercion mechanism for the target_dirs argument.
    Ensures that passing a single string path is correctly converted into a list
    before path evaluation continues.
    """
    # Pass a non-existent file just to trigger the string-to-list conversion
    files = gather_markdown_paths("some_target.md", "repo_root")
    assert isinstance(files, list)


def test_gather_markdown_paths_skipped_targets(tmp_path):
    """
    Validates strict boundary enforcement against unauthorized internal directories.
    Ensures that targets not explicitly present in the allowed_root_dirs list
    trigger a Fail-Closed hard crash (ValueError).
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    allowed = repo / "allowed_dir"
    allowed.mkdir()
    (allowed / "file1.md").write_text("# Allowed")

    disallowed = repo / "disallowed_dir"
    disallowed.mkdir()
    (disallowed / "file2.md").write_text("# Disallowed")

    with pytest.raises(ValueError):
        gather_markdown_paths(
            [str(allowed), str(disallowed)],
            repo_root=str(repo),
            allowed_root_dirs={"allowed_dir"},
        )


def test_gather_markdown_paths_allows_parent_of_artifact_root(tmp_path):
    repo = tmp_path / "repo"
    designs = repo / "docs" / "designs"
    api = repo / "docs" / "api"
    designs.mkdir(parents=True)
    api.mkdir()
    expected = designs / "TDD-service-001.md"
    expected.write_text("# Design")
    (api / "reference.md").write_text("# Not an architecture artifact")

    files = gather_markdown_paths(
        str(repo / "docs"),
        repo_root=str(repo),
        allowed_root_dirs={os.path.join("docs", "designs")},
    )

    assert files == [str(expected)]


def test_unauthorized_target_keeps_accurate_error(tmp_path):
    repo = tmp_path / "repo"
    target = repo / "docs" / "api"
    target.mkdir(parents=True)

    with pytest.raises(ValueError, match="not in allowed artifact directories"):
        gather_markdown_paths(
            str(target),
            repo_root=str(repo),
            allowed_root_dirs={os.path.join("docs", "designs")},
        )


def test_gather_markdown_paths_outside_repo(tmp_path):
    """
    Validates boundary enforcement against external path traversal attacks.
    Ensures that targets located outside the designated repo_root boundary
    (e.g., ../) trigger a Fail-Closed hard crash (ValueError).
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    outside = tmp_path / "outside_dir"
    outside.mkdir()
    (outside / "file.md").write_text("# Outside")

    with pytest.raises(ValueError):
        gather_markdown_paths(
            [str(outside)], repo_root=str(repo), allowed_root_dirs={"allowed"}
        )


def test_crawler_handles_exception_during_read():
    """
    Validates graceful error handling during file read operations.
    Ensures that if a PermissionError occurs while extracting metadata,
    it safely bypasses the unreadable file without crashing the crawler.
    """
    with patch("os.walk") as mock_walk:
        mock_walk.return_value = [("some_dir", [], ["test.md"])]
        with patch(
            "builtins.open", side_effect=PermissionError("Mocked Permission Error")
        ):
            ids, metadata, duplicates = build_metadata_registry("some_dir", "some_dir")
            assert len(ids) == 0
            assert len(metadata) == 0
            assert len(duplicates) == 0


def test_gather_markdown_paths_unallowed_directory_in_tree(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    allowed = repo / "00-governance"
    allowed.mkdir()
    (allowed / "gdc.md").write_text("# GDC")

    unallowed = repo / "unallowed_subdir"
    unallowed.mkdir()
    (unallowed / "extra.md").write_text("# Extra")

    # Scanning whole repo with allowed_root_dirs set to {"00-governance"}
    files = gather_markdown_paths(
        str(repo), repo_root=str(repo), allowed_root_dirs={"00-governance"}
    )
    assert any("gdc.md" in f for f in files)
    assert not any("extra.md" in f for f in files)


def test_directory_scoped_ignore_patterns_match_full_path(tmp_path):
    repo = tmp_path / "repo"
    governance = repo / "00-governance"
    templates = governance / "templates"
    scratch = governance / "scratch"
    templates.mkdir(parents=True)
    scratch.mkdir(parents=True)

    governed = governance / "GDC-999-example.md"
    template = templates / "review-score-sheet.md"
    scratch_doc = scratch / "notes.md"

    governed.write_text("# Governed", encoding="utf-8")
    template.write_text("# Template", encoding="utf-8")
    scratch_doc.write_text("# Scratch", encoding="utf-8")

    files = gather_markdown_paths(
        str(repo),
        repo_root=str(repo),
        allowed_root_dirs={"00-governance"},
        ignored_patterns=[
            r"[\\/]templates[\\/]",
            r"[\\/]scratch[\\/]",
        ],
    )

    assert str(governed) in files
    assert str(template) not in files
    assert str(scratch_doc) not in files
