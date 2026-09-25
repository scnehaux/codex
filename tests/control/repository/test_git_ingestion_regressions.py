from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import subprocess
import sys

import pytest

from engine.control.repository.git_ingestion import (
    GitIngestionError,
    GitRepositoryContext,
    GitRepositoryReader,
)
from engine.control.validation import (
    ValidationReport,
    build_artifact_candidate,
    parse_source_document,
    promote_candidate,
)
from engine.core.metamodel import ArchitectureNamespace


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SOURCE_PATH = "systems/SAD-001.md"
COMMITTED = (
    "---\n"
    "doc_meta:\n"
    "  id: SAD-001\n"
    "  title: Committed\n"
    "  status: draft\n"
    "---\n"
    "# Committed\n"
).encode("utf-8")


def _git(root: Path, *args: str, data: bytes | None = None) -> bytes:
    return subprocess.check_output(
        ["git", "-C", str(root), *args],
        input=data,
        stderr=subprocess.STDOUT,
    )


def _commit(root: Path) -> str:
    _git(root, "add", "--all")
    _git(root, "commit", "--quiet", "-m", "fixture")
    return _git(root, "rev-parse", "HEAD").decode("ascii").strip()


def _repository(tmp_path: Path, content: bytes = COMMITTED) -> tuple[Path, str]:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "--quiet")
    for name, value in (
        ("user.email", "fixture@example.com"),
        ("user.name", "Fixture"),
        ("core.autocrlf", "false"),
        ("core.safecrlf", "false"),
        ("core.hooksPath", str(tmp_path / "absent-hooks")),
        ("commit.gpgsign", "false"),
    ):
        _git(root, "config", name, value)
    source = root / SOURCE_PATH
    source.parent.mkdir()
    source.write_bytes(content)
    return root, _commit(root)


def _context(revision: str, namespace: str = "architecture") -> GitRepositoryContext:
    return GitRepositoryContext(
        repository_id="example.com/acme/architecture",
        namespace=ArchitectureNamespace("acme", namespace),
        revision=revision,
    )


@pytest.mark.parametrize("replacement_kind", ["commit", "blob"])
def test_recorded_commit_reads_ignore_git_replace_refs(tmp_path, replacement_kind):
    root, original = _repository(tmp_path)
    replacement_content = COMMITTED.replace(b"Committed", b"Replacement")
    (root / SOURCE_PATH).write_bytes(replacement_content)
    replacement = _commit(root)

    if replacement_kind == "commit":
        _git(root, "replace", original, replacement)
    else:
        original_blob = (
            _git(root, "rev-parse", f"{original}:{SOURCE_PATH}").decode("ascii").strip()
        )
        replacement_blob = (
            _git(root, "rev-parse", f"{replacement}:{SOURCE_PATH}")
            .decode("ascii")
            .strip()
        )
        _git(root, "replace", original_blob, replacement_blob)

    # Prove that the fixture's replacement affects ordinary Git object reads.
    assert _git(root, "cat-file", "blob", f"{original}:{SOURCE_PATH}") == (
        replacement_content
    )
    reader = GitRepositoryReader(root, _context(original))
    source, provenance = reader.read_source(SOURCE_PATH)

    assert source.content.encode("utf-8") == COMMITTED
    assert provenance.context.revision == original
    assert provenance.content_sha256 == sha256(COMMITTED).hexdigest()


@pytest.mark.parametrize(
    "modules",
    [
        ("engine.control.validation", "engine.control.repository"),
        ("engine.control.validation.pipeline",),
        ("engine.control.repository.assembler", "engine.control.validation"),
        ("engine.control.repository.git_ingestion", "engine.control.validation"),
    ],
)
def test_ingestion_and_validation_import_in_fresh_processes(modules):
    script = "\n".join(f"import {module}" for module in modules)
    result = subprocess.run(
        [sys.executable, "-B", "-c", script],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_git_source_digest_preserves_crlf_bom_and_unicode(tmp_path):
    raw = (
        "\ufeff---\r\n"
        "doc_meta:\r\n"
        "  id: SAD-001\r\n"
        "  title: Café 日本語\r\n"
        "  status: draft\r\n"
        "---\r\n"
        "# Café 日本語\r\n"
    ).encode("utf-8")
    root, revision = _repository(tmp_path, raw)

    source, provenance = GitRepositoryReader(root, _context(revision)).read_source(
        SOURCE_PATH
    )

    assert source.content.encode("utf-8") == raw
    assert source.content.startswith("\ufeff---\r\n")
    assert source.content_sha256 == sha256(raw).hexdigest()
    assert provenance.content_sha256 == sha256(raw).hexdigest()
    provenance.verify_content(raw)
    provenance.verify_content(source.content)


def test_non_utf8_committed_source_fails_closed(tmp_path):
    root, revision = _repository(tmp_path, b"\xff\xfe---\x00")
    reader = GitRepositoryReader(root, _context(revision))

    with pytest.raises(GitIngestionError, match="UTF-8"):
        reader.read_source(SOURCE_PATH)


def test_commit_ingestion_ignores_staged_dirty_and_untracked_files(tmp_path):
    root, revision = _repository(tmp_path)
    reader = GitRepositoryReader(root, _context(revision))
    before = reader.ingest_governed_candidates()

    path = root / SOURCE_PATH
    path.write_bytes(COMMITTED.replace(b"Committed", b"Staged"))
    _git(root, "add", SOURCE_PATH)
    path.write_bytes(COMMITTED.replace(b"Committed", b"Dirty"))
    (root / "systems/SAD-002.md").write_bytes(COMMITTED.replace(b"SAD-001", b"SAD-002"))

    after = reader.ingest_governed_candidates()

    assert after.batch_id == before.batch_id
    assert tuple(entry.provenance.source_path for entry in after.entries) == (
        SOURCE_PATH,
    )
    assert after.candidates[0].parsed.source.content.encode("utf-8") == COMMITTED
    assert after.candidates[0].candidate_id == before.candidates[0].candidate_id


def test_git_ingestion_ignores_inherited_repository_environment(tmp_path, monkeypatch):
    original_parent = tmp_path / "original"
    foreign_parent = tmp_path / "foreign"
    original_parent.mkdir()
    foreign_parent.mkdir()
    root, revision = _repository(original_parent)
    foreign, foreign_revision = _repository(
        foreign_parent, COMMITTED.replace(b"Committed", b"Foreign")
    )
    for name, value in {
        "GIT_DIR": str(foreign / ".git"),
        "GIT_WORK_TREE": str(foreign),
        "GIT_COMMON_DIR": str(foreign / ".git"),
        "GIT_INDEX_FILE": str(foreign / ".git" / "index"),
        "GIT_OBJECT_DIRECTORY": str(foreign / ".git" / "objects"),
    }.items():
        monkeypatch.setenv(name, value)

    # Inherited Git settings really redirect an ordinary command to the other repo.
    assert _git(root, "rev-parse", "HEAD").decode("ascii").strip() == foreign_revision
    source, provenance = GitRepositoryReader(root, _context(revision)).read_source(
        SOURCE_PATH
    )

    assert source.content.encode("utf-8") == COMMITTED
    assert provenance.context.revision == revision


def _tree(root: Path, entries: list[tuple[str, str, str, str]]) -> str:
    records = b"".join(
        f"{mode} {kind} {oid}\t{name}".encode("utf-8") + b"\0"
        for mode, kind, oid, name in entries
    )
    return _git(root, "mktree", "-z", data=records).decode("ascii").strip()


@pytest.mark.parametrize("noncanonical_name", ["SAD-001.md ", "nested\\SAD-002.md"])
def test_noncanonical_git_names_cannot_alias_and_hide_governed_sources(
    tmp_path, noncanonical_name
):
    root, parent = _repository(tmp_path)
    blob = _git(root, "hash-object", "-w", "--stdin", data=COMMITTED)
    blob_id = blob.decode("ascii").strip()
    nested = _tree(root, [("100644", "blob", blob_id, "SAD-002.md")])
    systems = _tree(
        root,
        [
            ("100644", "blob", blob_id, "SAD-001.md"),
            ("040000", "tree", nested, "nested"),
            ("100644", "blob", blob_id, noncanonical_name),
        ],
    )
    top = _tree(root, [("040000", "tree", systems, "systems")])
    # Object plumbing preserves names Windows cannot materialize in a checkout.
    revision = (
        _git(root, "commit-tree", top, "-p", parent, "-m", "noncanonical paths")
        .decode("ascii")
        .strip()
    )
    reader = GitRepositoryReader(root, _context(revision))

    with pytest.raises(GitIngestionError):
        reader.ingest_governed_candidates()


def test_git_discovery_preserves_authored_ignore_pattern_case(tmp_path):
    root, _ = _repository(tmp_path)
    for source_path in (
        "systems/templates/SAD-002.md",
        "systems/scratch/SAD-003.md",
        "governance/TEMPLATES/GDC-004.md",
        "systems/ReadMe.MD",
        "systems/INDEX.md",
        "notes/SAD-005.md",
    ):
        path = root / source_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(COMMITTED)
    revision = _commit(root)

    paths = GitRepositoryReader(root, _context(revision)).list_governed_markdown_paths()

    assert paths == ("governance/TEMPLATES/GDC-004.md", SOURCE_PATH)


@pytest.mark.parametrize(
    "content",
    [COMMITTED, b"---\ndoc_meta: [\n---\n"],
    ids=["parsed", "malformed"],
)
def test_candidate_identity_binds_namespace_even_when_parsing_fails(tmp_path, content):
    root, revision = _repository(tmp_path, content)
    contexts = (_context(revision, "one"), _context(revision, "two"))
    candidates = tuple(
        GitRepositoryReader(root, context).ingest_governed_candidates().candidates[0]
        for context in contexts
    )

    assert candidates[0].candidate_id != candidates[1].candidate_id
    for candidate, context in zip(candidates, contexts, strict=True):
        assert candidate.parsed.source.source_namespace == context.namespace
        if content == COMMITTED:
            assert candidate.artifact is not None
            assert candidate.artifact.artifact.identity.namespace == context.namespace
        else:
            assert candidate.artifact is None
            assert candidate.parsed.parse_error

    report = ValidationReport(
        report_id="namespace-one",
        draft_id=candidates[0].candidate_id,
        findings=(),
    )
    with pytest.raises(ValueError, match="not bound"):
        promote_candidate(candidates[1], report)


def test_builder_inherits_bound_namespace_and_rejects_override(tmp_path):
    root, revision = _repository(tmp_path)
    context = _context(revision)
    source, _ = GitRepositoryReader(root, context).read_source(SOURCE_PATH)
    parsed = parse_source_document(source)

    candidate = build_artifact_candidate(parsed)

    assert candidate.artifact is not None
    assert candidate.artifact.artifact.identity.namespace == context.namespace
    with pytest.raises(ValueError, match="namespace"):
        build_artifact_candidate(
            parsed, namespace=ArchitectureNamespace("acme", "other")
        )
