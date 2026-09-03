from __future__ import annotations


import pytest

from engine.control.governance.genesis import GitResult
from engine.control.governance.mutation import (
    VersionedDocument,
    assert_version_mutation_integrity,
    audit_version_mutation_integrity,
    is_governed_document_path,
    parse_versioned_document,
    validate_document_mutation,
)
from engine.core.governance.versioning import SemanticVersion


def _doc(
    document_id="GDC-999",
    version="0.0.1",
    status="draft",
):
    return (
        "---\n"
        "doc_meta:\n"
        f"  id: {document_id}\n"
        f"  version: {version}\n"
        f"  status: {status}\n"
        "---\n"
        "# Test\n"
    )


def _runner(mapping):
    def run(args):
        return mapping.get(
            tuple(args),
            GitResult(1, "", "missing fake command"),
        )

    return run


def test_governed_path_is_numeric_architecture_root_only():
    assert is_governed_document_path("governance/GDC-001-a.md")
    assert is_governed_document_path("05-standards/STD-001.md")
    assert not is_governed_document_path("tests/fixtures/GDC-001.md")
    assert not is_governed_document_path("README.md")
    assert not is_governed_document_path("scripts/readme.md")


def test_parse_versioned_document_ignores_nonversioned_markdown():
    document, findings = parse_versioned_document(
        "governance/README.md",
        "# Readme\n",
    )
    assert document is None
    assert findings == ()


def test_parse_versioned_document_parses_identity_version_status():
    document, findings = parse_versioned_document(
        "governance/GDC-999-test.md",
        _doc(),
    )
    assert findings == ()
    assert document is not None
    assert document.document_id == "GDC-999"
    assert str(document.version) == "0.0.1"
    assert document.status == "draft"


@pytest.mark.parametrize(
    ("text", "code"),
    (
        ("---\ndoc_meta:\n  id: GDC-999\n", "invalid-doc-meta"),
        (
            "---\ndoc_meta:\n  id: 123\n  version: 0.0.1\n---\n",
            "invalid-document-id",
        ),
        (
            "---\ndoc_meta:\n  id: GDC-999\n  version: nope\n---\n",
            "invalid-version",
        ),
    ),
)
def test_parse_versioned_document_fails_closed(text, code):
    _, findings = parse_versioned_document(
        "governance/GDC-999-test.md",
        text,
    )
    assert findings[0].code == code


def test_mutation_requires_immutable_identity_and_strict_version_increase():
    before = VersionedDocument(
        "governance/GDC-001-a.md",
        "GDC-001",
        SemanticVersion.parse("0.1.0"),
        "draft",
    )

    same = VersionedDocument(
        before.path,
        before.document_id,
        before.version,
        "draft",
    )
    assert {finding.code for finding in validate_document_mutation(before, same)} == {
        "version-bump-required"
    }

    regressed = VersionedDocument(
        before.path,
        before.document_id,
        SemanticVersion.parse("0.0.9"),
        "draft",
    )
    assert {
        finding.code for finding in validate_document_mutation(before, regressed)
    } == {"version-regression"}

    changed_id = VersionedDocument(
        before.path,
        "GDC-002",
        SemanticVersion.parse("0.1.1"),
        "draft",
    )
    assert {
        finding.code for finding in validate_document_mutation(before, changed_id)
    } == {"document-id-mutation"}

    bumped = VersionedDocument(
        before.path,
        before.document_id,
        SemanticVersion.parse("0.1.1"),
        "draft",
    )
    assert validate_document_mutation(before, bumped) == ()


def test_pre_genesis_checks_current_unique_versions(tmp_path):
    governance = tmp_path / "governance"
    governance.mkdir()
    one = governance / "GDC-001-one.md"
    two = governance / "GDC-002-two.md"
    one.write_text(_doc("GDC-001"), encoding="utf-8")
    two.write_text(_doc("GDC-002"), encoding="utf-8")

    candidate = (
        "\n".join(
            (
                "governance/GDC-001-one.md",
                "governance/GDC-002-two.md",
            )
        )
        + "\n"
    )

    report = audit_version_mutation_integrity(
        tmp_path,
        git_runner=_runner(
            {
                (
                    "ls-files",
                    "--cached",
                    "--others",
                    "--exclude-standard",
                ): GitResult(0, candidate),
                ("rev-parse", "--verify", "HEAD"): GitResult(1),
            }
        ),
    )
    assert report.mode == "pre-genesis"
    assert report.checked_documents == 2
    assert report.ok


def test_pre_genesis_rejects_duplicate_document_id(tmp_path):
    governance = tmp_path / "governance"
    governance.mkdir()
    for name in ("a", "b"):
        (governance / f"GDC-001-{name}.md").write_text(
            _doc("GDC-001"),
            encoding="utf-8",
        )

    candidate = "governance/GDC-001-a.md\ngovernance/GDC-001-b.md\n"

    report = audit_version_mutation_integrity(
        tmp_path,
        git_runner=_runner(
            {
                (
                    "ls-files",
                    "--cached",
                    "--others",
                    "--exclude-standard",
                ): GitResult(0, candidate),
                ("rev-parse", "--verify", "HEAD"): GitResult(1),
            }
        ),
    )
    assert any(finding.code == "duplicate-document-id" for finding in report.findings)


def test_candidate_enumeration_failure_is_reported(tmp_path):
    report = audit_version_mutation_integrity(
        tmp_path,
        git_runner=_runner(
            {
                (
                    "ls-files",
                    "--cached",
                    "--others",
                    "--exclude-standard",
                ): GitResult(1),
                ("rev-parse", "--verify", "HEAD"): GitResult(1),
            }
        ),
    )
    assert report.findings[0].code == "git-candidate-enumeration-failed"


def test_post_genesis_modified_document_requires_bump(tmp_path):
    governance = tmp_path / "governance"
    governance.mkdir()
    path = "governance/GDC-001-test.md"
    (tmp_path / path).write_text(
        _doc("GDC-001", "0.0.1") + "changed\n",
        encoding="utf-8",
    )

    mapping = {
        (
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
        ): GitResult(0, path + "\n"),
        ("rev-parse", "--verify", "HEAD"): GitResult(0, "head\n"),
        ("diff", "--name-status", "-M", "HEAD"): GitResult(
            0,
            "M\t" + path + "\n",
        ),
        ("show", f"HEAD:{path}"): GitResult(
            0,
            _doc("GDC-001", "0.0.1"),
        ),
    }

    report = audit_version_mutation_integrity(
        tmp_path,
        git_runner=_runner(mapping),
    )
    assert any(finding.code == "version-bump-required" for finding in report.findings)


def test_post_genesis_modified_document_passes_with_bump(tmp_path):
    governance = tmp_path / "governance"
    governance.mkdir()
    path = "governance/GDC-001-test.md"
    (tmp_path / path).write_text(
        _doc("GDC-001", "0.0.2") + "changed\n",
        encoding="utf-8",
    )

    mapping = {
        (
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
        ): GitResult(0, path + "\n"),
        ("rev-parse", "--verify", "HEAD"): GitResult(0, "head\n"),
        ("diff", "--name-status", "-M", "HEAD"): GitResult(
            0,
            "M\t" + path + "\n",
        ),
        ("show", f"HEAD:{path}"): GitResult(
            0,
            _doc("GDC-001", "0.0.1"),
        ),
    }

    report = audit_version_mutation_integrity(
        tmp_path,
        git_runner=_runner(mapping),
    )
    assert report.ok


def test_post_genesis_raw_deletion_is_forbidden(tmp_path):
    path = "governance/GDC-001-test.md"
    mapping = {
        (
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
        ): GitResult(0, ""),
        ("rev-parse", "--verify", "HEAD"): GitResult(0, "head\n"),
        ("diff", "--name-status", "-M", "HEAD"): GitResult(
            0,
            "D\t" + path + "\n",
        ),
        ("show", f"HEAD:{path}"): GitResult(
            0,
            _doc("GDC-001", "0.0.1"),
        ),
    }

    report = audit_version_mutation_integrity(
        tmp_path,
        git_runner=_runner(mapping),
    )
    assert any(
        finding.code == "governed-document-deletion" for finding in report.findings
    )


def test_post_genesis_rename_is_mutation_and_requires_bump(tmp_path):
    governance = tmp_path / "governance"
    governance.mkdir()
    old = "governance/GDC-001-old.md"
    new = "governance/GDC-001-new.md"
    (tmp_path / new).write_text(
        _doc("GDC-001", "0.0.1"),
        encoding="utf-8",
    )

    mapping = {
        (
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
        ): GitResult(0, new + "\n"),
        ("rev-parse", "--verify", "HEAD"): GitResult(0, "head\n"),
        ("diff", "--name-status", "-M", "HEAD"): GitResult(
            0,
            f"R100\t{old}\t{new}\n",
        ),
        ("show", f"HEAD:{old}"): GitResult(
            0,
            _doc("GDC-001", "0.0.1"),
        ),
    }

    report = audit_version_mutation_integrity(
        tmp_path,
        git_runner=_runner(mapping),
    )
    assert any(finding.code == "version-bump-required" for finding in report.findings)


def test_post_genesis_metadata_removal_is_forbidden(tmp_path):
    governance = tmp_path / "governance"
    governance.mkdir()
    path = "governance/GDC-001-test.md"
    (tmp_path / path).write_text(
        "# no metadata\n",
        encoding="utf-8",
    )

    mapping = {
        (
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
        ): GitResult(0, path + "\n"),
        ("rev-parse", "--verify", "HEAD"): GitResult(0, "head\n"),
        ("diff", "--name-status", "-M", "HEAD"): GitResult(
            0,
            "M\t" + path + "\n",
        ),
        ("show", f"HEAD:{path}"): GitResult(
            0,
            _doc("GDC-001", "0.0.1"),
        ),
    }

    report = audit_version_mutation_integrity(
        tmp_path,
        git_runner=_runner(mapping),
    )
    assert any(
        finding.code == "governed-metadata-removal" for finding in report.findings
    )


def test_invalid_diff_and_git_failures_are_reported(tmp_path):
    mapping = {
        (
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
        ): GitResult(0, ""),
        ("rev-parse", "--verify", "HEAD"): GitResult(0, "head\n"),
        ("diff", "--name-status", "-M", "HEAD"): GitResult(1),
    }
    report = audit_version_mutation_integrity(
        tmp_path,
        git_runner=_runner(mapping),
    )
    assert any(finding.code == "git-diff-failed" for finding in report.findings)


def test_assertion_raises_with_structured_findings(tmp_path):
    with pytest.raises(
        RuntimeError,
        match="Version/mutation integrity audit failed",
    ):
        assert_version_mutation_integrity(
            tmp_path,
            git_runner=_runner(
                {
                    (
                        "ls-files",
                        "--cached",
                        "--others",
                        "--exclude-standard",
                    ): GitResult(1),
                    ("rev-parse", "--verify", "HEAD"): GitResult(1),
                }
            ),
        )


def test_parse_versioned_document_rejects_nongoverned_path_even_with_doc_meta():
    document, findings = parse_versioned_document(
        "tests/GDC-999-test.md",
        _doc(),
    )
    assert document is None
    assert findings == ()


def test_parse_versioned_document_detects_doc_meta_in_generic_filename():
    document, findings = parse_versioned_document(
        "governance/custom.md",
        _doc("GDC-999", "0.0.1"),
    )
    assert findings == ()
    assert document is not None
    assert document.document_id == "GDC-999"


def test_generic_filename_with_unterminated_doc_meta_is_governed_and_fails_closed():
    document, findings = parse_versioned_document(
        "governance/custom.md",
        "---\ndoc_meta:\n  id: GDC-999\n",
    )
    assert document is None
    assert findings
    assert findings[0].code == "invalid-doc-meta"


def test_scan_skips_nongoverned_candidates_and_reports_missing_governed_file(tmp_path):
    candidate = "README.md\ngovernance/GDC-404-missing.md\n"

    report = audit_version_mutation_integrity(
        tmp_path,
        git_runner=_runner(
            {
                (
                    "ls-files",
                    "--cached",
                    "--others",
                    "--exclude-standard",
                ): GitResult(0, candidate),
                ("rev-parse", "--verify", "HEAD"): GitResult(1),
            }
        ),
    )

    assert any(finding.code == "document-read-failed" for finding in report.findings)


def test_post_genesis_invalid_diff_entries_are_reported(tmp_path):
    mapping = {
        (
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
        ): GitResult(0, ""),
        ("rev-parse", "--verify", "HEAD"): GitResult(0, "head\n"),
        ("diff", "--name-status", "-M", "HEAD"): GitResult(
            0,
            "\nM\nR100\told-only\nA\tREADME.md\nD\tREADME.md\nM\tREADME.md\n",
        ),
    }

    report = audit_version_mutation_integrity(
        tmp_path,
        git_runner=_runner(mapping),
    )

    codes = {finding.code for finding in report.findings}
    assert "invalid-git-diff-entry" in codes
    assert "invalid-git-rename-entry" in codes


def test_post_genesis_baseline_read_failure_is_reported_for_delete(tmp_path):
    path = "governance/GDC-001-test.md"
    mapping = {
        (
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
        ): GitResult(0, ""),
        ("rev-parse", "--verify", "HEAD"): GitResult(0, "head\n"),
        ("diff", "--name-status", "-M", "HEAD"): GitResult(
            0,
            "D\t" + path + "\n",
        ),
        ("show", f"HEAD:{path}"): GitResult(1),
    }

    report = audit_version_mutation_integrity(
        tmp_path,
        git_runner=_runner(mapping),
    )
    assert any(finding.code == "baseline-read-failed" for finding in report.findings)


def test_post_genesis_modified_document_with_missing_current_file_is_reported(tmp_path):
    path = "governance/GDC-001-test.md"

    mapping = {
        (
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
        ): GitResult(0, ""),
        ("rev-parse", "--verify", "HEAD"): GitResult(0, "head\n"),
        ("diff", "--name-status", "-M", "HEAD"): GitResult(
            0,
            "M\t" + path + "\n",
        ),
        ("show", f"HEAD:{path}"): GitResult(
            0,
            _doc("GDC-001", "0.0.1"),
        ),
    }

    report = audit_version_mutation_integrity(
        tmp_path,
        git_runner=_runner(mapping),
    )
    assert any(finding.code == "document-read-failed" for finding in report.findings)


def test_post_genesis_both_sides_nonversioned_is_ignored(tmp_path):
    governance = tmp_path / "governance"
    governance.mkdir()
    path = "governance/notes.md"
    (tmp_path / path).write_text("# current notes\n", encoding="utf-8")

    mapping = {
        (
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
        ): GitResult(0, path + "\n"),
        ("rev-parse", "--verify", "HEAD"): GitResult(0, "head\n"),
        ("diff", "--name-status", "-M", "HEAD"): GitResult(
            0,
            "M\t" + path + "\n",
        ),
        ("show", f"HEAD:{path}"): GitResult(
            0,
            "# old notes\n",
        ),
    }

    report = audit_version_mutation_integrity(
        tmp_path,
        git_runner=_runner(mapping),
    )
    assert report.ok


def test_post_genesis_transition_from_nonversioned_to_versioned_is_allowed(tmp_path):
    governance = tmp_path / "governance"
    governance.mkdir()
    path = "governance/custom.md"
    (tmp_path / path).write_text(
        _doc("GDC-999", "0.0.1"),
        encoding="utf-8",
    )

    mapping = {
        (
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
        ): GitResult(0, path + "\n"),
        ("rev-parse", "--verify", "HEAD"): GitResult(0, "head\n"),
        ("diff", "--name-status", "-M", "HEAD"): GitResult(
            0,
            "M\t" + path + "\n",
        ),
        ("show", f"HEAD:{path}"): GitResult(
            0,
            "# old notes\n",
        ),
    }

    report = audit_version_mutation_integrity(
        tmp_path,
        git_runner=_runner(mapping),
    )
    assert report.ok


def test_assert_version_mutation_integrity_returns_report_on_success(tmp_path):
    report = assert_version_mutation_integrity(
        tmp_path,
        git_runner=_runner(
            {
                (
                    "ls-files",
                    "--cached",
                    "--others",
                    "--exclude-standard",
                ): GitResult(0, ""),
                ("rev-parse", "--verify", "HEAD"): GitResult(1),
            }
        ),
    )

    assert report.ok
    assert report.mode == "pre-genesis"


def test_default_git_runner_is_exercised_with_real_unborn_repo(tmp_path):
    import subprocess

    subprocess.run(
        ["git", "init", "-b", "main", str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    governance = tmp_path / "governance"
    governance.mkdir()
    path = governance / "GDC-001-test.md"
    path.write_text(
        _doc("GDC-001", "0.0.1"),
        encoding="utf-8",
    )

    report = audit_version_mutation_integrity(tmp_path)
    assert report.mode == "pre-genesis"
    assert report.ok
    assert report.checked_documents == 1


def test_default_git_runner_reads_utf8_head_document_post_genesis(
    tmp_path,
):
    import subprocess

    subprocess.run(
        ["git", "init", "-b", "main", str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.email", "test@example.com"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.name", "Test"],
        check=True,
    )

    governance = tmp_path / "governance"
    governance.mkdir()

    path = governance / "GDC-999-test.md"
    path.write_text(
        _doc("GDC-999", "0.0.1") + "Unicode decode sentinel: ŝ\n",
        encoding="utf-8",
    )

    subprocess.run(
        ["git", "-C", str(tmp_path), "add", "-A"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-m", "baseline"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    path.write_text(
        _doc("GDC-999", "0.0.2") + "Unicode decode sentinel: ŝ changed\n",
        encoding="utf-8",
    )

    report = audit_version_mutation_integrity(tmp_path)
    assert report.mode == "post-genesis"
    assert report.ok
