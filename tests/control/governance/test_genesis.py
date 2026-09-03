from __future__ import annotations

import pytest
import yaml

from engine.control.governance.genesis import (
    GenesisIntegrityReport,
    GitResult,
    assert_genesis_integrity,
    audit_genesis_integrity,
    parse_frontmatter,
    path_matches_contract,
    validate_candidate_paths,
    validate_gdc_snapshot,
)
from tests.support.repository import REPOSITORY_ROOT


MANIFEST = yaml.safe_load(
    (REPOSITORY_ROOT / "governance" / "bootstrap-manifest.yaml").read_text(
        encoding="utf-8"
    )
)


def _gdc(doc_id: str, *, status: str = "draft", version: str = "0.0.1") -> str:
    return (
        "---\n"
        "doc_meta:\n"
        f"  id: {doc_id}\n"
        f"  version: {version}\n"
        f"  status: {status}\n"
        "---\n"
        "# Test\n"
    )


def _runner(mapping):
    def run(args):
        return mapping.get(tuple(args), GitResult(1, "", "missing fake command"))

    return run


def test_path_contract_supports_exact_and_recursive_prefix():
    assert path_matches_contract("engine/control/x.py", "engine/**")
    assert path_matches_contract("engine", "engine/**")
    assert path_matches_contract("conftest.py", "conftest.py")
    assert not path_matches_contract("engine-x/a.py", "engine/**")


def test_parse_frontmatter_requires_doc_meta():
    assert parse_frontmatter(_gdc("GDC-000"))["id"] == "GDC-000"

    with pytest.raises(ValueError, match="missing YAML frontmatter"):
        parse_frontmatter("# no frontmatter")

    with pytest.raises(ValueError, match="unterminated"):
        parse_frontmatter("---\ndoc_meta: {}\n")

    with pytest.raises(ValueError, match="doc_meta"):
        parse_frontmatter("---\nvalue: 1\n---\n")


def test_candidate_paths_reject_forbidden_and_outside_allowlist():
    findings = validate_candidate_paths(
        (
            "engine/control/a.py",
            "enterprise/EAD-001.md",
            "random.bin",
        ),
        MANIFEST,
    )
    assert any("forbidden architecture path" in item for item in findings)
    assert any("outside Genesis allowlist" in item for item in findings)


def test_gdc_snapshot_requires_exact_draft_zero_x_baseline():
    required = MANIFEST["governance_control_plane"]["required_baseline_ids"]
    documents = {f"governance/{doc_id}-test.md": _gdc(doc_id) for doc_id in required}
    assert validate_gdc_snapshot(documents, MANIFEST) == ()

    broken = dict(documents)
    broken.pop(next(iter(broken)))
    first_id = required[1]
    broken[f"governance/{first_id}-dup.md"] = _gdc(
        first_id,
        status="approved",
        version="1.0.0",
    )
    findings = validate_gdc_snapshot(broken, MANIFEST)
    assert any("missing" in item for item in findings)
    assert any(
        "duplicate" in item or "status" in item or "0.x.x" in item for item in findings
    )


def test_pre_genesis_audit_uses_live_candidate_and_canonical_branch(tmp_path):
    governance = tmp_path / "governance"
    governance.mkdir()

    (governance / "bootstrap-manifest.yaml").write_text(
        yaml.safe_dump(MANIFEST, sort_keys=False),
        encoding="utf-8",
    )

    required = MANIFEST["governance_control_plane"]["required_baseline_ids"]
    candidates = ["governance/bootstrap-manifest.yaml"]

    for doc_id in required:
        path = governance / f"{doc_id}-test.md"
        path.write_text(_gdc(doc_id), encoding="utf-8")
        candidates.append(f"governance/{path.name}")

    mapping = {
        ("rev-parse", "--verify", "HEAD"): GitResult(1),
        ("branch", "--show-current"): GitResult(0, "main\n"),
        (
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
        ): GitResult(0, "\n".join(candidates) + "\n"),
    }

    report = audit_genesis_integrity(
        tmp_path,
        git_runner=_runner(mapping),
    )
    assert isinstance(report, GenesisIntegrityReport)
    assert report.mode == "pre-genesis"
    assert report.root_commit is None
    assert report.findings == ()


def test_pre_genesis_audit_rejects_wrong_branch(tmp_path):
    governance = tmp_path / "governance"
    governance.mkdir()
    (governance / "bootstrap-manifest.yaml").write_text(
        yaml.safe_dump(MANIFEST, sort_keys=False),
        encoding="utf-8",
    )

    mapping = {
        ("rev-parse", "--verify", "HEAD"): GitResult(1),
        ("branch", "--show-current"): GitResult(0, "feature\n"),
        (
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
        ): GitResult(0, ""),
    }

    report = audit_genesis_integrity(
        tmp_path,
        git_runner=_runner(mapping),
    )
    assert any("pre-Genesis branch" in item for item in report.findings)


def test_post_genesis_audit_reads_root_commit_snapshot(tmp_path):
    governance = tmp_path / "governance"
    governance.mkdir()
    (governance / "bootstrap-manifest.yaml").write_text(
        yaml.safe_dump(MANIFEST, sort_keys=False),
        encoding="utf-8",
    )

    required = MANIFEST["governance_control_plane"]["required_baseline_ids"]
    tree = ["governance/bootstrap-manifest.yaml"]
    mapping = {
        ("rev-parse", "--verify", "HEAD"): GitResult(0, "head\n"),
        ("rev-list", "--max-parents=0", "HEAD"): GitResult(0, "rootsha\n"),
        ("show", "rootsha:governance/bootstrap-manifest.yaml"): GitResult(0, yaml.safe_dump(MANIFEST, sort_keys=False)),
    }

    for doc_id in required:
        path = f"governance/{doc_id}-test.md"
        tree.append(path)
        mapping[("show", f"rootsha:{path}")] = GitResult(0, _gdc(doc_id))

    mapping[("ls-tree", "-r", "--name-only", "rootsha")] = GitResult(
        0,
        "\n".join(tree) + "\n",
    )

    report = audit_genesis_integrity(
        tmp_path,
        git_runner=_runner(mapping),
    )
    assert report.mode == "post-genesis"
    assert report.root_commit == "rootsha"
    assert report.findings == ()


def test_post_genesis_requires_exactly_one_root_commit(tmp_path):
    governance = tmp_path / "governance"
    governance.mkdir()
    (governance / "bootstrap-manifest.yaml").write_text(
        yaml.safe_dump(MANIFEST, sort_keys=False),
        encoding="utf-8",
    )

    mapping = {
        ("rev-parse", "--verify", "HEAD"): GitResult(0, "head\n"),
        ("rev-list", "--max-parents=0", "HEAD"): GitResult(0, "a\nb\n"),
    }

    report = audit_genesis_integrity(
        tmp_path,
        git_runner=_runner(mapping),
    )
    assert any("exactly one root commit" in item for item in report.findings)


def test_assert_genesis_integrity_raises_on_findings(tmp_path):
    with pytest.raises(RuntimeError, match="Genesis integrity audit failed"):
        assert_genesis_integrity(
            tmp_path,
            git_runner=_runner(
                {
                    ("rev-parse", "--verify", "HEAD"): GitResult(1),
                }
            ),
        )


def _manifest_copy():
    import copy

    return copy.deepcopy(MANIFEST)


@pytest.mark.parametrize(
    ("mutator", "expected"),
    [
        (lambda m: m.__setitem__("kind", "wrong"), "kind"),
        (lambda m: m.__setitem__("target_repository", ""), "target_repository"),
        (lambda m: m.__setitem__("canonical_branch", ""), "canonical_branch"),
        (lambda m: m.__setitem__("source", None), "source"),
        (
            lambda m: m["source"].__setitem__("repository", ""),
            "source repository",
        ),
        (
            lambda m: m["source"].__setitem__("repository", m["target_repository"]),
            "cannot equal target",
        ),
        (
            lambda m: m["source"].__setitem__("ref", ""),
            "source ref",
        ),
        (
            lambda m: m["source"].__setitem__("commit", "abc"),
            "40-hex SHA",
        ),
        (
            lambda m: m.__setitem__("genesis_contract", None),
            "genesis_contract",
        ),
        (
            lambda m: m["genesis_contract"].__setitem__("root_commit_only", False),
            "root_commit_only",
        ),
        (
            lambda m: m["genesis_contract"].__setitem__(
                "local_qualification_required", False
            ),
            "local_qualification_required",
        ),
        (
            lambda m: m["genesis_contract"].__setitem__("allowed_paths", "bad"),
            "allowed_paths",
        ),
        (
            lambda m: m["genesis_contract"].__setitem__(
                "forbidden_architecture_paths", "bad"
            ),
            "forbidden_architecture_paths",
        ),
        (
            lambda m: m.__setitem__("provenance", None),
            "provenance",
        ),
        (
            lambda m: m["provenance"].__setitem__(
                "architecture_artifacts_admitted_in_genesis", True
            ),
            "architecture artifacts",
        ),
        (
            lambda m: m.__setitem__("governance_control_plane", None),
            "governance_control_plane",
        ),
        (
            lambda m: m["governance_control_plane"].__setitem__(
                "lifecycle", "approved"
            ),
            "lifecycle",
        ),
        (
            lambda m: m["governance_control_plane"].__setitem__(
                "version_series", "1.x.x"
            ),
            "version series",
        ),
        (
            lambda m: m["governance_control_plane"].__setitem__(
                "architecture_admission", "open"
            ),
            "admission",
        ),
        (
            lambda m: m["governance_control_plane"].__setitem__(
                "required_baseline_ids", "bad"
            ),
            "required_baseline_ids",
        ),
    ],
)
def test_manifest_contract_failures_are_explicit(tmp_path, mutator, expected):
    governance = tmp_path / "governance"
    governance.mkdir()
    manifest = _manifest_copy()
    mutator(manifest)
    (governance / "bootstrap-manifest.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False),
        encoding="utf-8",
    )

    report = audit_genesis_integrity(
        tmp_path,
        git_runner=_runner(
            {
                ("rev-parse", "--verify", "HEAD"): GitResult(1),
                ("branch", "--show-current"): GitResult(0, "main\n"),
                (
                    "ls-files",
                    "--cached",
                    "--others",
                    "--exclude-standard",
                ): GitResult(0, ""),
            }
        ),
    )
    assert any(expected in item for item in report.findings)


def test_candidate_validation_fails_closed_for_missing_contract():
    manifest = _manifest_copy()
    manifest["genesis_contract"] = None
    assert "unavailable" in validate_candidate_paths((), manifest)[0]

    manifest["genesis_contract"] = {
        "allowed_paths": "bad",
        "forbidden_architecture_paths": [],
    }
    assert "policy is invalid" in validate_candidate_paths((), manifest)[0]


def test_gdc_validation_fails_closed_for_missing_governance_contract():
    manifest = _manifest_copy()
    manifest["governance_control_plane"] = None
    assert "unavailable" in validate_gdc_snapshot({}, manifest)[0]

    manifest["governance_control_plane"] = {"required_baseline_ids": "bad"}
    assert "required_baseline_ids" in validate_gdc_snapshot({}, manifest)[0]


def test_gdc_snapshot_reports_malformed_unknown_and_bad_versions():
    manifest = _manifest_copy()
    required = manifest["governance_control_plane"]["required_baseline_ids"]
    documents = {f"governance/{doc_id}-test.md": _gdc(doc_id) for doc_id in required}

    documents["governance/GDC-000-test.md"] = "not-frontmatter"
    documents["governance/GDC-999-extra.md"] = _gdc("GDC-999")

    bad_id = required[1]
    documents[f"governance/{bad_id}-test.md"] = (
        "---\ndoc_meta:\n  id: 123\n  version: 0.0.1\n  status: draft\n---\n"
    )

    bad_version_id = required[2]
    documents[f"governance/{bad_version_id}-test.md"] = _gdc(
        bad_version_id,
        status="approved",
        version="banana",
    )

    numeric_version_id = required[3]
    documents[f"governance/{numeric_version_id}-test.md"] = (
        "---\n"
        "doc_meta:\n"
        f"  id: {numeric_version_id}\n"
        "  version: 1\n"
        "  status: draft\n"
        "---\n"
    )

    findings = validate_gdc_snapshot(documents, manifest)
    assert any("missing YAML frontmatter" in item for item in findings)
    assert any("doc_meta.id must be a string" in item for item in findings)
    assert any("unexpected GDC" in item for item in findings)
    assert any("status must remain draft" in item for item in findings)
    assert any("version must remain in 0.x.x" in item for item in findings)
    assert any("version must be a string" in item for item in findings)


def test_load_invalid_bootstrap_manifest_is_reported(tmp_path):
    governance = tmp_path / "governance"
    governance.mkdir()

    (governance / "bootstrap-manifest.yaml").write_text(
        "- not\n- mapping\n",
        encoding="utf-8",
    )

    report = audit_genesis_integrity(
        tmp_path,
        git_runner=_runner({}),
    )
    assert report.mode == "invalid"
    assert "YAML mapping" in report.findings[0]


def test_pre_genesis_git_failures_are_findings(tmp_path):
    governance = tmp_path / "governance"
    governance.mkdir()
    (governance / "bootstrap-manifest.yaml").write_text(
        yaml.safe_dump(MANIFEST, sort_keys=False),
        encoding="utf-8",
    )

    report = audit_genesis_integrity(
        tmp_path,
        git_runner=_runner(
            {
                ("rev-parse", "--verify", "HEAD"): GitResult(1),
                ("branch", "--show-current"): GitResult(1),
                (
                    "ls-files",
                    "--cached",
                    "--others",
                    "--exclude-standard",
                ): GitResult(1),
            }
        ),
    )

    assert any("cannot resolve current Git branch" in item for item in report.findings)
    assert any("cannot enumerate" in item for item in report.findings)


def test_post_genesis_git_failures_are_findings(tmp_path):
    governance = tmp_path / "governance"
    governance.mkdir()
    (governance / "bootstrap-manifest.yaml").write_text(
        yaml.safe_dump(MANIFEST, sort_keys=False),
        encoding="utf-8",
    )

    unresolved_root = audit_genesis_integrity(
        tmp_path,
        git_runner=_runner(
            {
                ("rev-parse", "--verify", "HEAD"): GitResult(0, "head\n"),
                ("rev-list", "--max-parents=0", "HEAD"): GitResult(1),
            }
        ),
    )
    assert any(
        "cannot resolve Git root commit" in item for item in unresolved_root.findings
    )

    root = "rootsha"
    tree_failure = audit_genesis_integrity(
        tmp_path,
        git_runner=_runner(
            {
                ("rev-parse", "--verify", "HEAD"): GitResult(0, "head\n"),
                (
                    "rev-list",
                    "--max-parents=0",
                    "HEAD",
                ): GitResult(0, root + "\n"),
                (
                    "ls-tree",
                    "-r",
                    "--name-only",
                    root,
                ): GitResult(1),
            }
        ),
    )
    assert any(
        "cannot enumerate root commit tree" in item for item in tree_failure.findings
    )


def test_post_genesis_missing_or_unreadable_gdc_is_reported(tmp_path):
    governance = tmp_path / "governance"
    governance.mkdir()
    (governance / "bootstrap-manifest.yaml").write_text(
        yaml.safe_dump(MANIFEST, sort_keys=False),
        encoding="utf-8",
    )

    required = MANIFEST["governance_control_plane"]["required_baseline_ids"]
    root = "rootsha"
    tree = ["governance/bootstrap-manifest.yaml"]
    mapping = {
        ("rev-parse", "--verify", "HEAD"): GitResult(0, "head\n"),
        (
            "rev-list",
            "--max-parents=0",
            "HEAD",
        ): GitResult(0, root + "\n"),
            ("show", f"{root}:governance/bootstrap-manifest.yaml"): GitResult(0, yaml.safe_dump(MANIFEST, sort_keys=False)),
    }

    first = required[0]
    tree.extend(
        [
            f"governance/{first}-a.md",
            f"governance/{first}-b.md",
        ]
    )

    second = required[1]
    second_path = f"governance/{second}-test.md"
    tree.append(second_path)
    mapping[("show", f"{root}:{second_path}")] = GitResult(1)

    mapping[("ls-tree", "-r", "--name-only", root)] = GitResult(
        0,
        "\n".join(tree) + "\n",
    )

    report = audit_genesis_integrity(
        tmp_path,
        git_runner=_runner(mapping),
    )
    assert any(first in item and "missing" in item for item in report.findings)
    assert any(second in item and "missing" in item for item in report.findings)


def test_default_git_runner_is_exercised_by_real_unborn_repository(
    tmp_path,
):
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

    report = audit_genesis_integrity(tmp_path)
    assert report.mode == "pre-genesis"
    assert report.ok


def test_default_git_runner_reads_utf8_root_snapshot_post_genesis(
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

    (governance / "bootstrap-manifest.yaml").write_text(
        yaml.safe_dump(MANIFEST, sort_keys=False),
        encoding="utf-8",
    )

    required = MANIFEST["governance_control_plane"]["required_baseline_ids"]

    for doc_id in required:
        (governance / f"{doc_id}-test.md").write_text(
            _gdc(doc_id) + "Unicode decode sentinel: Å\n",
            encoding="utf-8",
        )

    subprocess.run(
        ["git", "-C", str(tmp_path), "add", "-A"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-m", "genesis"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    report = audit_genesis_integrity(tmp_path)
    assert report.mode == "post-genesis"
    assert report.ok


