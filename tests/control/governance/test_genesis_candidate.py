from __future__ import annotations


import pytest
import yaml

from engine.control.governance.genesis import GitResult
from engine.control.governance.genesis_candidate import (
    assert_genesis_commit_candidate,
    audit_genesis_commit_candidate,
)
from tests.support.repository import REPOSITORY_ROOT


MANIFEST = yaml.safe_load(
    (REPOSITORY_ROOT / "governance" / "bootstrap-manifest.yaml").read_text(
        encoding="utf-8"
    )
)


def _gdc(doc_id: str) -> str:
    return (
        "---\n"
        "doc_meta:\n"
        f"  id: {doc_id}\n"
        "  version: 0.0.1\n"
        "  status: draft\n"
        "---\n"
        "# Test\n"
        "Unicode decode sentinel: ŝ\n"
    )


def _runner(mapping):
    def run(args):
        return mapping.get(
            tuple(args),
            GitResult(1, "", "missing fake command"),
        )

    return run


def _repo(tmp_path):
    governance = tmp_path / "governance"
    governance.mkdir(parents=True)

    (governance / "bootstrap-manifest.yaml").write_text(
        yaml.safe_dump(MANIFEST, sort_keys=False),
        encoding="utf-8",
    )

    required = MANIFEST["governance_control_plane"]["required_baseline_ids"]

    staged = ["governance/bootstrap-manifest.yaml"]
    mapping = {
        ("rev-parse", "--verify", "HEAD"): GitResult(1),
        ("branch", "--show-current"): GitResult(0, "main\n"),
        ("ls-files", "--others", "--exclude-standard"): GitResult(0, ""),
        ("diff", "--name-only"): GitResult(0, ""),
        ("write-tree",): GitResult(0, "a" * 40 + "\n"),
    }

    for doc_id in required:
        path = f"governance/{doc_id}-test.md"
        staged.append(path)
        mapping[("show", f":{path}")] = GitResult(
            0,
            _gdc(doc_id),
        )

    mapping[("ls-files", "--cached")] = GitResult(
        0,
        "\n".join(staged) + "\n",
    )

    return tmp_path, mapping


def test_valid_staged_genesis_candidate_passes(tmp_path):
    root, mapping = _repo(tmp_path)

    report = assert_genesis_commit_candidate(
        root,
        git_runner=_runner(mapping),
    )

    assert report.ok
    assert report.tree_sha == "a" * 40
    assert len(report.staged_files) >= 13


def test_manifest_failure_is_fail_closed(tmp_path):
    governance = tmp_path / "governance"
    governance.mkdir()
    (governance / "bootstrap-manifest.yaml").write_text(
        "- invalid\n",
        encoding="utf-8",
    )

    report = audit_genesis_commit_candidate(
        tmp_path,
        git_runner=_runner({}),
    )

    assert report.findings[0].code == "bootstrap-manifest-invalid"


@pytest.mark.parametrize(
    ("mutation", "code"),
    (
        (
            lambda m: m.__setitem__(
                ("rev-parse", "--verify", "HEAD"),
                GitResult(0, "head\n"),
            ),
            "genesis-already-exists",
        ),
        (
            lambda m: m.__setitem__(
                ("branch", "--show-current"),
                GitResult(1),
            ),
            "branch-resolution-failed",
        ),
        (
            lambda m: m.__setitem__(
                ("branch", "--show-current"),
                GitResult(0, "feature\n"),
            ),
            "canonical-branch-mismatch",
        ),
        (
            lambda m: m.__setitem__(
                ("ls-files", "--cached"),
                GitResult(1),
            ),
            "index-enumeration-failed",
        ),
        (
            lambda m: m.__setitem__(
                ("ls-files", "--cached"),
                GitResult(0, ""),
            ),
            "empty-genesis-index",
        ),
        (
            lambda m: m.__setitem__(
                ("ls-files", "--others", "--exclude-standard"),
                GitResult(1),
            ),
            "untracked-enumeration-failed",
        ),
        (
            lambda m: m.__setitem__(
                ("ls-files", "--others", "--exclude-standard"),
                GitResult(0, "extra.txt\n"),
            ),
            "unstaged-untracked-file",
        ),
        (
            lambda m: m.__setitem__(
                ("diff", "--name-only"),
                GitResult(1),
            ),
            "unstaged-diff-failed",
        ),
        (
            lambda m: m.__setitem__(
                ("diff", "--name-only"),
                GitResult(0, "Makefile\n"),
            ),
            "unstaged-worktree-mutation",
        ),
        (
            lambda m: m.__setitem__(
                ("write-tree",),
                GitResult(1),
            ),
            "staged-tree-write-failed",
        ),
        (
            lambda m: m.__setitem__(
                ("write-tree",),
                GitResult(0, "short\n"),
            ),
            "staged-tree-sha-invalid",
        ),
    ),
)
def test_candidate_failure_modes_are_explicit(
    tmp_path,
    mutation,
    code,
):
    root, mapping = _repo(tmp_path)
    mutation(mapping)

    report = audit_genesis_commit_candidate(
        root,
        git_runner=_runner(mapping),
    )

    assert any(finding.code == code for finding in report.findings)


def test_path_outside_allowlist_is_rejected(tmp_path):
    root, mapping = _repo(tmp_path)
    staged = mapping[("ls-files", "--cached")].stdout
    mapping[("ls-files", "--cached")] = GitResult(
        0,
        staged + "random.bin\n",
    )

    report = audit_genesis_commit_candidate(
        root,
        git_runner=_runner(mapping),
    )

    assert any(
        finding.code == "genesis-path-outside-allowlist" for finding in report.findings
    )


def test_forbidden_architecture_path_is_rejected(tmp_path):
    root, mapping = _repo(tmp_path)
    staged = mapping[("ls-files", "--cached")].stdout
    mapping[("ls-files", "--cached")] = GitResult(
        0,
        staged + "enterprise/EAD-001-test.md\n",
    )

    report = audit_genesis_commit_candidate(
        root,
        git_runner=_runner(mapping),
    )

    assert any(
        finding.code == "forbidden-architecture-path" for finding in report.findings
    )


def test_required_staged_gdc_read_failure_is_reported(tmp_path):
    root, mapping = _repo(tmp_path)
    required = MANIFEST["governance_control_plane"]["required_baseline_ids"]
    path = f"governance/{required[0]}-test.md"
    mapping[("show", f":{path}")] = GitResult(1)

    report = audit_genesis_commit_candidate(
        root,
        git_runner=_runner(mapping),
    )

    codes = {finding.code for finding in report.findings}
    assert "staged-document-read-failed" in codes
    assert "staged-governance-baseline-invalid" in codes


def test_assertion_raises_with_structured_findings(tmp_path):
    root, mapping = _repo(tmp_path)
    mapping[("ls-files", "--cached")] = GitResult(0, "")

    with pytest.raises(
        RuntimeError,
        match="Genesis commit candidate qualification failed",
    ):
        assert_genesis_commit_candidate(
            root,
            git_runner=_runner(mapping),
        )


def test_default_git_runner_operates_on_real_unborn_index(tmp_path):
    import subprocess

    subprocess.run(
        ["git", "init", "-b", "main", str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    governance = tmp_path / "governance"
    governance.mkdir()

    (governance / "bootstrap-manifest.yaml").write_text(
        yaml.safe_dump(MANIFEST, sort_keys=False),
        encoding="utf-8",
    )

    required = MANIFEST["governance_control_plane"]["required_baseline_ids"]
    for doc_id in required:
        (governance / f"{doc_id}-test.md").write_text(
            _gdc(doc_id),
            encoding="utf-8",
        )

    subprocess.run(
        ["git", "-C", str(tmp_path), "add", "-A"],
        check=True,
        capture_output=True,
        text=True,
    )

    report = audit_genesis_commit_candidate(tmp_path)

    assert report.ok
    assert report.tree_sha is not None
