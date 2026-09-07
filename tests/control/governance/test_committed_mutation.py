from __future__ import annotations

import subprocess

from engine.control.governance.committed_mutation import (
    audit_committed_mutation_integrity,
)
from engine.control.governance.genesis import GitResult


def run(root, *args):
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def init(root):
    run(root, "init", "-b", "main")
    run(root, "config", "user.email", "test@example.com")
    run(root, "config", "user.name", "Test")
    return root


def doc(doc_id, version, body="body"):
    return (
        "---\n"
        "doc_meta:\n"
        f"  id: {doc_id}\n"
        f"  version: {version}\n"
        "  status: draft\n"
        "---\n"
        f"# Test\n\n{body}\n"
    )


def commit(root, message):
    run(root, "add", "-A")
    run(root, "commit", "-m", message)
    return run(root, "rev-parse", "HEAD").stdout.strip()


def test_valid_bump_passes(tmp_path):
    root = init(tmp_path)
    gov = root / "governance"
    gov.mkdir()
    path = gov / "GDC-900-test.md"
    path.write_text(doc("GDC-900", "0.0.1"), encoding="utf-8")
    base = commit(root, "base")
    path.write_text(doc("GDC-900", "0.0.2", "changed ŝ"), encoding="utf-8")
    commit(root, "change")
    report = audit_committed_mutation_integrity(root, base_ref=base)
    assert report.ok and report.merge_base == base and report.checked_mutations == 1


def test_missing_bump_fails(tmp_path):
    root = init(tmp_path)
    gov = root / "governance"
    gov.mkdir()
    path = gov / "GDC-901-test.md"
    path.write_text(doc("GDC-901", "0.0.1"), encoding="utf-8")
    base = commit(root, "base")
    path.write_text(doc("GDC-901", "0.0.1", "changed"), encoding="utf-8")
    commit(root, "change")
    report = audit_committed_mutation_integrity(root, base_ref=base)
    assert any(f.code == "version-bump-required" for f in report.findings)


def test_deletion_fails(tmp_path):
    root = init(tmp_path)
    gov = root / "governance"
    gov.mkdir()
    path = gov / "GDC-902-test.md"
    path.write_text(doc("GDC-902", "0.0.1"), encoding="utf-8")
    base = commit(root, "base")
    path.unlink()
    commit(root, "delete")
    report = audit_committed_mutation_integrity(root, base_ref=base)
    assert any(f.code == "governed-document-deletion" for f in report.findings)


def test_rename_with_bump_passes(tmp_path):
    root = init(tmp_path)
    gov = root / "governance"
    gov.mkdir()
    old = gov / "GDC-903-old.md"
    new = gov / "GDC-903-new.md"
    old.write_text(doc("GDC-903", "0.0.1"), encoding="utf-8")
    base = commit(root, "base")
    old.rename(new)
    new.write_text(doc("GDC-903", "0.0.2", "renamed"), encoding="utf-8")
    commit(root, "rename")
    report = audit_committed_mutation_integrity(root, base_ref=base)
    assert report.ok and report.checked_mutations == 1


def test_identity_mutation_and_metadata_removal_fail(tmp_path):
    root = init(tmp_path)
    gov = root / "governance"
    gov.mkdir()
    path = gov / "GDC-904-test.md"
    path.write_text(doc("GDC-904", "0.0.1"), encoding="utf-8")
    base = commit(root, "base")
    path.write_text(doc("GDC-X", "0.0.2"), encoding="utf-8")
    commit(root, "id")
    report = audit_committed_mutation_integrity(root, base_ref=base)
    assert any(f.code == "document-id-mutation" for f in report.findings)

    base2 = run(root, "rev-parse", "HEAD").stdout.strip()
    path.write_text("# no metadata\n", encoding="utf-8")
    commit(root, "remove")
    report2 = audit_committed_mutation_integrity(root, base_ref=base2)
    assert any(f.code == "governed-metadata-removal" for f in report2.findings)


def test_new_governed_document_allowed(tmp_path):
    root = init(tmp_path)
    (root / "README.txt").write_text("base\n", encoding="utf-8")
    base = commit(root, "base")
    gov = root / "governance"
    gov.mkdir()
    (gov / "GDC-905-test.md").write_text(doc("GDC-905", "0.0.1"), encoding="utf-8")
    commit(root, "add")
    report = audit_committed_mutation_integrity(root, base_ref=base)
    assert report.ok and report.checked_mutations == 1


def test_invalid_refs_and_git_failures_fail_closed(tmp_path):
    root = init(tmp_path)
    (root / "README.txt").write_text("x\n", encoding="utf-8")
    commit(root, "base")
    assert (
        audit_committed_mutation_integrity(root, base_ref="").findings[0].code
        == "mutation-base-ref-invalid"
    )
    assert (
        audit_committed_mutation_integrity(root, base_ref="HEAD", head_ref="")
        .findings[0]
        .code
        == "mutation-head-ref-invalid"
    )
    assert (
        audit_committed_mutation_integrity(root, base_ref="missing").findings[0].code
        == "mutation-merge-base-failed"
    )

    mapping = {
        ("merge-base", "base", "HEAD"): GitResult(0, "abc\n", ""),
        ("diff", "--name-status", "-M", "abc", "HEAD", "--"): GitResult(1, "", "boom"),
    }

    def runner(args):
        return mapping.get(tuple(args), GitResult(1, "", "missing"))

    report = audit_committed_mutation_integrity(
        tmp_path, base_ref="base", git_runner=runner
    )
    assert report.findings[0].code == "committed-git-diff-failed"


def test_malformed_diff_and_read_failures(tmp_path):
    diff = "bad\nR100\tone\nM\tgovernance/GDC-907-test.md\textra\nM\tgovernance/GDC-908-test.md\n"
    mapping = {
        ("merge-base", "base", "HEAD"): GitResult(0, "abc\n", ""),
        ("diff", "--name-status", "-M", "abc", "HEAD", "--"): GitResult(0, diff, ""),
    }

    def runner(args):
        return mapping.get(tuple(args), GitResult(1, "", "missing"))

    report = audit_committed_mutation_integrity(
        tmp_path, base_ref="base", git_runner=runner
    )
    codes = {f.code for f in report.findings}
    assert "invalid-committed-diff-entry" in codes
    assert "invalid-committed-rename-entry" in codes
    assert "committed-baseline-read-failed" in codes
    assert "committed-head-read-failed" in codes


def test_added_malformed_governed_document_fails_closed(tmp_path):
    root = init(tmp_path)
    (root / "README.txt").write_text("base\n", encoding="utf-8")
    base = commit(root, "base")

    gov = root / "governance"
    gov.mkdir()
    path = gov / "GDC-909-test.md"
    path.write_text(
        "---\ndoc_meta:\n  id: GDC-909\n  version: nope\n---\n# invalid\n",
        encoding="utf-8",
    )
    commit(root, "add-invalid")

    report = audit_committed_mutation_integrity(root, base_ref=base)
    assert any(f.code == "invalid-version" for f in report.findings)


def test_non_governed_and_blank_committed_delta_is_ignored(tmp_path):
    diff = "\nM\tREADME.txt\n"
    mapping = {
        ("merge-base", "base", "HEAD"): GitResult(0, "abc\n", ""),
        ("diff", "--name-status", "-M", "abc", "HEAD", "--"): GitResult(
            0,
            diff,
            "",
        ),
    }

    def runner(args):
        return mapping.get(tuple(args), GitResult(1, "", "unexpected"))

    report = audit_committed_mutation_integrity(
        tmp_path,
        base_ref="base",
        git_runner=runner,
    )

    assert report.ok
    assert report.checked_mutations == 0


def test_plain_governed_path_to_plain_is_ignored(tmp_path):
    root = init(tmp_path)
    gov = root / "governance"
    gov.mkdir()
    path = gov / "notes.md"
    path.write_text("# plain v1\n", encoding="utf-8")
    base = commit(root, "base")

    path.write_text("# plain v2\n", encoding="utf-8")
    commit(root, "change")

    report = audit_committed_mutation_integrity(root, base_ref=base)

    assert report.ok
    assert report.checked_mutations == 1


def test_plain_governed_path_can_become_new_versioned_document(tmp_path):
    root = init(tmp_path)
    gov = root / "governance"
    gov.mkdir()
    path = gov / "notes.md"
    path.write_text("# plain\n", encoding="utf-8")
    base = commit(root, "base")

    path.write_text(
        "---\n"
        "doc_meta:\n"
        "  id: NOTE-001\n"
        "  version: 0.0.1\n"
        "  status: draft\n"
        "---\n"
        "# promoted\n",
        encoding="utf-8",
    )
    commit(root, "promote")

    report = audit_committed_mutation_integrity(root, base_ref=base)

    assert report.ok
    assert report.checked_mutations == 1


def test_assert_committed_mutation_integrity_success_and_failure(tmp_path):
    from engine.control.governance.committed_mutation import (
        assert_committed_mutation_integrity,
    )

    root = init(tmp_path)
    gov = root / "governance"
    gov.mkdir()
    path = gov / "GDC-910-test.md"
    path.write_text(doc("GDC-910", "0.0.1"), encoding="utf-8")
    base = commit(root, "base")

    path.write_text(
        doc("GDC-910", "0.0.2", "valid change"),
        encoding="utf-8",
    )
    commit(root, "valid")

    report = assert_committed_mutation_integrity(
        root,
        base_ref=base,
    )
    assert report.ok

    failing_base = run(root, "rev-parse", "HEAD").stdout.strip()
    path.write_text(
        doc("GDC-910", "0.0.2", "invalid no bump"),
        encoding="utf-8",
    )
    commit(root, "invalid")

    import pytest

    with pytest.raises(
        RuntimeError,
        match="Committed mutation integrity audit failed",
    ):
        assert_committed_mutation_integrity(
            root,
            base_ref=failing_base,
        )
