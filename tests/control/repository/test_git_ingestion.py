from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from engine.control.repository.git_ingestion import (
    GitCandidateBatch,
    GitIngestedCandidate,
    GitIngestionError,
    GitRepositoryContext,
    GitRepositoryReader,
    GitSourceProvenance,
)
from engine.control.validation import (
    SourceDocument,
    build_artifact_candidate,
    parse_source_document,
)
from engine.core.metamodel import ArchitectureNamespace


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args],
        text=True,
        stderr=subprocess.STDOUT,
    ).strip()


def _init_repo(root: Path, *, title: str = "System") -> str:
    root.mkdir(parents=True)
    _git(root, "init")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    systems = root / "systems"
    systems.mkdir()
    (systems / "SAD-001.md").write_text(
        "---\n"
        "doc_meta:\n"
        "  id: SAD-001\n"
        f"  title: {title}\n"
        "  status: draft\n"
        "  created_date: 2026-01-01\n"
        "---\n"
        f"# {title}\n",
        encoding="utf-8",
        newline="\n",
    )
    (systems / "README.md").write_text("# Ignore\n", encoding="utf-8", newline="\n")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "initial")
    return _git(root, "rev-parse", "HEAD")


def _context(revision: str, repo: str = "github.com/acme/architecture"):
    return GitRepositoryContext(
        repo,
        ArchitectureNamespace("acme", "architecture"),
        revision,
    )


def test_git_repository_context_is_explicit_and_deterministic():
    revision = "a" * 40
    context = _context(revision)
    assert context.semantic_state() == (
        "github.com/acme/architecture",
        ("acme", "architecture"),
        revision,
    )
    assert context.context_id == _context(revision).context_id

    with pytest.raises(ValueError, match="repository_id"):
        GitRepositoryContext(" ", ArchitectureNamespace("a", "b"), revision)
    with pytest.raises(TypeError, match="namespace"):
        GitRepositoryContext("repo", object(), revision)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="40-character"):
        GitRepositoryContext("repo", ArchitectureNamespace("a", "b"), "HEAD")


def test_git_source_provenance_round_trips_and_verifies_content():
    content = "hello\n"
    digest = __import__("hashlib").sha256(content.encode()).hexdigest()
    provenance = GitSourceProvenance(_context("b" * 40), "systems/SAD-001.md", digest)

    assert provenance.source_reference.revision == "b" * 40
    assert provenance.source_reference.content_digest == digest
    assert provenance.origin.startswith("git+repo://")
    assert GitSourceProvenance.from_record(provenance.to_record()) == provenance
    assert GitSourceProvenance.from_record(provenance.to_record()).provenance_id == (
        provenance.provenance_id
    )
    provenance.verify_content(content)
    provenance.verify_content(content.encode())

    with pytest.raises(ValueError, match="digest"):
        provenance.verify_content("tampered")
    with pytest.raises(ValueError, match="fields"):
        GitSourceProvenance.from_record({"repository_id": "x"})  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="64-character"):
        GitSourceProvenance(_context("b" * 40), "x.md", "bad")
    with pytest.raises(TypeError, match="context"):
        GitSourceProvenance(object(), "x.md", digest)  # type: ignore[arg-type]


def test_bound_source_document_rejects_content_digest_drift():
    digest = "0" * 64
    from engine.core.metamodel import SourceReference

    with pytest.raises(ValueError, match="content_digest"):
        SourceDocument(
            "systems/SAD-001.md",
            "actual",
            SourceReference("repo://source", "a" * 40, content_digest=digest),
        )


def test_reader_reads_exact_commit_not_dirty_worktree(tmp_path):
    root = tmp_path / "repo"
    revision = _init_repo(root, title="Committed")
    reader = GitRepositoryReader(root, _context(revision))

    path = root / "systems/SAD-001.md"
    committed = path.read_text(encoding="utf-8")
    path.write_text(committed.replace("Committed", "Dirty"), encoding="utf-8")

    source, provenance = reader.read_source("systems/SAD-001.md")
    assert "Committed" in source.content
    assert "Dirty" not in source.content
    assert source.source_reference == provenance.source_reference
    assert source.source_reference.revision == revision
    provenance.verify_content(source.content)

    candidate = build_artifact_candidate(
        parse_source_document(source),
        namespace=reader.context.namespace,
    )
    assert candidate.artifact is not None
    assert candidate.artifact.artifact.canonical_key == "acme/architecture/SAD-001"
    assert candidate.artifact.artifact.evidence == (provenance.source_reference,)


def test_reader_requires_repository_root_and_exact_commit(tmp_path):
    root = tmp_path / "repo"
    revision = _init_repo(root)
    nested = root / "systems"

    with pytest.raises(GitIngestionError, match="top-level"):
        GitRepositoryReader(nested, _context(revision))

    with pytest.raises(GitIngestionError, match="Git command failed"):
        GitRepositoryReader(root, _context("f" * 40))


def test_batch_discovers_only_governed_markdown_and_is_deterministic(tmp_path):
    root = tmp_path / "repo"
    revision = _init_repo(root)
    context = _context(revision)
    reader = GitRepositoryReader(root, context)

    first = reader.ingest_governed_candidates()
    second = reader.ingest_governed_candidates()

    assert isinstance(first, GitCandidateBatch)
    assert first.batch_id == second.batch_id
    assert [entry.provenance.source_path for entry in first.entries] == [
        "systems/SAD-001.md"
    ]
    assert len(first.candidates) == 1
    entry = first.entries[0]
    assert entry.candidate.artifact is not None
    assert entry.candidate.artifact.artifact.identity.namespace == context.namespace
    assert entry.candidate.artifact.artifact.evidence[0].content_digest == (
        entry.provenance.content_sha256
    )


def test_same_artifact_id_is_distinguished_across_repository_and_revision():
    content = (
        "---\ndoc_meta:\n  id: SAD-001\n  title: System\n"
        "  status: draft\n  created_date: 2026-01-01\n---\n# System\n"
    )

    def build(context: GitRepositoryContext):
        digest = __import__("hashlib").sha256(content.encode()).hexdigest()
        provenance = GitSourceProvenance(context, "systems/SAD-001.md", digest)
        source = SourceDocument(
            "systems/SAD-001.md",
            content,
            provenance.source_reference,
            source_namespace=context.namespace,
        )
        candidate = build_artifact_candidate(
            parse_source_document(source),
            namespace=context.namespace,
        )
        return provenance, candidate

    repo_a = GitRepositoryContext(
        "repo-a",
        ArchitectureNamespace("acme", "repo-a"),
        "a" * 40,
    )
    repo_b = GitRepositoryContext(
        "repo-b",
        ArchitectureNamespace("acme", "repo-b"),
        "a" * 40,
    )
    prov_a, candidate_a = build(repo_a)
    prov_b, candidate_b = build(repo_b)

    assert candidate_a.artifact.artifact.canonical_key == "acme/repo-a/SAD-001"
    assert candidate_b.artifact.artifact.canonical_key == "acme/repo-b/SAD-001"
    assert prov_a.provenance_id != prov_b.provenance_id

    next_revision = GitRepositoryContext(
        "repo-a",
        ArchitectureNamespace("acme", "repo-a"),
        "b" * 40,
    )
    prov_next, candidate_next = build(next_revision)
    assert candidate_next.artifact.artifact.canonical_key == "acme/repo-a/SAD-001"
    assert candidate_next.artifact.artifact.evidence[0].revision == "b" * 40
    assert prov_a.provenance_id != prov_next.provenance_id


def test_ingested_candidate_and_batch_fail_closed_on_mismatch():
    content = "---\ndoc_meta:\n  id: SAD-001\n  title: S\n  status: draft\n---\n"
    digest = __import__("hashlib").sha256(content.encode()).hexdigest()
    context = _context("c" * 40)
    provenance = GitSourceProvenance(context, "systems/SAD-001.md", digest)
    good_source = SourceDocument(
        "systems/SAD-001.md",
        content,
        provenance.source_reference,
        source_namespace=context.namespace,
    )
    candidate = build_artifact_candidate(
        parse_source_document(good_source), namespace=context.namespace
    )
    entry = GitIngestedCandidate(provenance, candidate)
    assert entry.provenance_id == provenance.provenance_id

    other = GitSourceProvenance(context, "systems/SAD-002.md", digest)
    with pytest.raises(ValueError, match="source path"):
        GitIngestedCandidate(other, candidate)
    with pytest.raises(TypeError, match="provenance"):
        GitIngestedCandidate(object(), candidate)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="candidate"):
        GitIngestedCandidate(provenance, object())  # type: ignore[arg-type]

    assert GitCandidateBatch(context, (entry,)).candidates == (candidate,)
    with pytest.raises(ValueError, match="share one"):
        GitCandidateBatch(
            _context("d" * 40),
            (entry,),
        )


def test_tree_entry_rejects_symlink_and_git_output_failures(monkeypatch, tmp_path):
    context = _context("a" * 40)
    reader = object.__new__(GitRepositoryReader)
    reader.repo_root = tmp_path
    reader.context = context

    monkeypatch.setattr(
        reader,
        "_git_bytes",
        lambda *args: (
            b"120000 blob 0123456789012345678901234567890123456789\tsystems/x.md\0"
        ),
    )
    with pytest.raises(GitIngestionError, match="regular file"):
        reader._tree_entry("systems/x.md")

    monkeypatch.setattr(reader, "_git_bytes", lambda *args: b"")
    with pytest.raises(GitIngestionError, match="absent or ambiguous"):
        reader._tree_entry("systems/x.md")


def test_git_bytes_wraps_command_failures(monkeypatch, tmp_path):
    context = _context("a" * 40)
    reader = object.__new__(GitRepositoryReader)
    reader.repo_root = tmp_path
    reader.context = context

    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, args[0])

    monkeypatch.setattr(subprocess, "check_output", fail)
    with pytest.raises(GitIngestionError, match="Git command failed"):
        reader._git_bytes("status")


@pytest.mark.parametrize(
    "path",
    [
        "",
        ".",
        "./x.md",
        "a/./x.md",
        "a/../x.md",
        "/x.md",
        "C:/x.md",
        "C:x.md",
        "//host/share/x",
        "a//b.md",
        "a\x00b.md",
    ],
)
def test_git_paths_reject_ambiguous_or_nonrelative_names(path):
    with pytest.raises(ValueError, match="source_path"):
        GitSourceProvenance(_context("a" * 40), path, "b" * 64)


def test_git_contracts_reject_wrong_types():
    from engine.control.fs.source_path import repository_source_path

    with pytest.raises(TypeError, match="source_path"):
        repository_source_path(42)
    with pytest.raises(TypeError, match="repository_id"):
        GitRepositoryContext(None, ArchitectureNamespace("a", "b"), "a" * 40)
    with pytest.raises(TypeError, match="namespace"):
        SourceDocument("x.md", "", source_namespace="wrong")
    with pytest.raises(TypeError, match="source_reference"):
        SourceDocument("x.md", "", source_reference="wrong")
    with pytest.raises(TypeError, match="content"):
        GitSourceProvenance(_context("a" * 40), "x.md", "b" * 64).verify_content(42)
    with pytest.raises(TypeError, match="context"):
        GitCandidateBatch(object(), ())
    with pytest.raises(TypeError, match="entries"):
        GitCandidateBatch(_context("a" * 40), (object(),))


def test_candidate_rejects_inconsistent_provenance_and_evidence(tmp_path):
    from dataclasses import replace
    from engine.core.metamodel import SourceReference

    root = tmp_path / "repo"
    revision = _init_repo(root)
    entry = (
        GitRepositoryReader(root, _context(revision))
        .ingest_governed_candidates()
        .entries[0]
    )
    candidate = entry.candidate
    record = candidate.artifact
    source = candidate.parsed.source
    alternate = _context(revision, repo="other-repo")
    with pytest.raises(ValueError, match="SourceReference"):
        GitIngestedCandidate(replace(entry.provenance, context=alternate), candidate)
    changed_source = replace(
        source, source_namespace=ArchitectureNamespace("other", "ns")
    )
    with pytest.raises(ValueError, match="source namespace"):
        GitIngestedCandidate(
            entry.provenance,
            replace(candidate, parsed=replace(candidate.parsed, source=changed_source)),
        )
    with pytest.raises(ValueError, match="artifact path"):
        GitIngestedCandidate(
            entry.provenance,
            replace(
                candidate, artifact=replace(record, source_path="systems/other.md")
            ),
        )
    changed_artifact = replace(record.artifact, evidence=(SourceReference("other"),))
    with pytest.raises(ValueError, match="evidence"):
        GitIngestedCandidate(
            entry.provenance,
            replace(candidate, artifact=replace(record, artifact=changed_artifact)),
        )
    identity = replace(
        record.artifact.identity, namespace=ArchitectureNamespace("other", "ns")
    )
    changed_artifact = replace(record.artifact, identity=identity)
    with pytest.raises(ValueError, match="candidate namespace"):
        GitIngestedCandidate(
            entry.provenance,
            replace(candidate, artifact=replace(record, artifact=changed_artifact)),
        )
    with pytest.raises(ValueError, match="source paths"):
        GitCandidateBatch(entry.provenance.context, (entry, entry))


def test_assembler_verifies_supplied_digest():
    from hashlib import sha256
    from engine.control.repository import RepositoryAssembler, RepositoryIngestionError
    from engine.core.metamodel import SourceReference

    metadata = {"id": "SAD-001", "title": "System", "status": "draft"}
    reference = SourceReference(
        "opaque://source",
        "any-revision",
        content_digest=sha256(b"original").hexdigest(),
    )
    with pytest.raises(RepositoryIngestionError, match="content_digest"):
        RepositoryAssembler.artifact_from_metadata(
            metadata=metadata,
            source_path="systems/SAD-001.md",
            content="altered",
            source_reference=reference,
        )
    with pytest.raises(RepositoryIngestionError, match="SourceReference"):
        RepositoryAssembler.artifact_from_metadata(
            metadata=metadata,
            source_path="systems/SAD-001.md",
            source_reference="wrong",
        )


@pytest.mark.parametrize(
    "raw",
    [
        b"invalid\x00",
        b"100644 blob x\tother.md\x00",
        b"040000 tree x\tsystems/x.md\x00",
        b"160000 commit x\tsystems/x.md\x00",
        b"100644 blob x\tsystems/\xff.md\x00",
    ],
)
def test_reader_rejects_malformed_or_unsupported_tree_records(
    raw, monkeypatch, tmp_path
):
    reader = object.__new__(GitRepositoryReader)
    reader.repo_root = tmp_path
    reader.context = _context("a" * 40)
    monkeypatch.setattr(reader, "_git_bytes", lambda *args: raw)
    with pytest.raises(GitIngestionError):
        reader._tree_entry("systems/x.md")


def test_reader_rejects_invalid_context_and_noncommit_object(tmp_path):
    root = tmp_path / "repo"
    revision = _init_repo(root)
    with pytest.raises(TypeError, match="context"):
        GitRepositoryReader(root, object())
    tree = _git(root, "rev-parse", revision + "^{tree}")
    with pytest.raises(GitIngestionError, match="Git command failed"):
        GitRepositoryReader(root, _context(tree))


def test_reader_wraps_non_utf8_control_output(monkeypatch, tmp_path):
    reader = object.__new__(GitRepositoryReader)
    reader.repo_root = tmp_path
    reader.context = _context("a" * 40)
    monkeypatch.setattr(reader, "_git_bytes", lambda *args: b"\xff")
    with pytest.raises(GitIngestionError, match="not UTF-8"):
        reader._git_text("rev-parse")


def test_public_ingestion_api_preserves_binding_and_report_promotion(tmp_path):
    from engine.control.repository import ingest_git_governed_corpus
    from engine.control.validation import ValidationReport, promote_candidate

    root = tmp_path / "repo"
    revision = _init_repo(root)
    context = _context(revision)
    batch = ingest_git_governed_corpus(repo_root=root, context=context)
    entry = batch.entries[0]
    report = ValidationReport(
        report_id="fixture-pass", draft_id=entry.candidate.candidate_id, findings=()
    )
    promoted = promote_candidate(entry.candidate, report)
    assert promoted.artifact.evidence == (entry.provenance.source_reference,)
    assert promoted.artifact.identity.namespace == context.namespace


def test_structured_namespace_components_do_not_alias():
    left = GitRepositoryContext("repo", ArchitectureNamespace("a/b", "c"), "a" * 40)
    right = GitRepositoryContext("repo", ArchitectureNamespace("a", "b/c"), "a" * 40)
    assert left.namespace.key == right.namespace.key
    assert left.semantic_state() != right.semantic_state()
    assert left.context_id != right.context_id
    assert GitSourceProvenance(left, "x.md", "b" * 64).provenance_id != (
        GitSourceProvenance(right, "x.md", "b" * 64).provenance_id
    )
