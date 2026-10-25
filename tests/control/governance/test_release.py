"""Synthetic release estate: no test record represents a real governance approval."""

from __future__ import annotations

import copy
from hashlib import sha256
import json
import shutil
import subprocess
from types import SimpleNamespace

import pytest
import yaml

from engine.control.governance import release as target
from engine.adapters.scm import github_release as github
from tests.support.repository import REPOSITORY_ROOT


def _git(root, *args, input=None):
    try:
        raw = subprocess.check_output(
            ["git", "-C", str(root), *args], input=input, stderr=subprocess.PIPE
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            "Git fixture failed: " + exc.stderr.decode("utf-8", errors="replace")[:800]
        ) from exc
    return raw.decode().strip()


def _commit(root):
    _git(root, "config", "gc.auto", "0")
    _git(root, "config", "maintenance.auto", "false")
    _git(root, "add", ".")
    _git(
        root,
        "-c",
        "user.name=Release fixture",
        "-c",
        "user.email=release@example.invalid",
        "commit",
        "--no-gpg-sign",
        "-qm",
        "Synthetic fixture",
    )
    head = _git(root, "rev-parse", "HEAD")
    _git(root, "update-ref", "refs/remotes/origin/main", head)
    return head


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(target.canonical_json(value))


def _publication(authority, source):
    head = _git(source, "rev-parse", "HEAD")
    record = {
        "schema_version": 1,
        "kind": "codex-publication-outcome",
        "candidate": {
            "repository": target.REPOSITORY,
            "pull_request": 999,
            "head_sha": head,
            "base_sha": _git(source, "rev-parse", "HEAD^"),
        },
        "activation_digest": "a" * 64,
        "permit_digest": "b" * 64,
        "check_post_attempted": True,
        "check_run_id": 42,
        "status": "published",
        "token_revoked": True,
        "effective_enforcement_proven": False,
    }
    _write(authority / f"governance/publications/{head}.json", record)
    return _commit(authority)


def _manifest_commit(estate, value=None, raw=None):
    path = estate.authority / "governance/releases/governance-1.0.0.json"
    data = raw if raw is not None else target.canonical_json(value or estate.manifest)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    # A repeated byte sequence can reuse the existing commit.
    if _git(estate.authority, "status", "--porcelain"):
        _commit(estate.authority)
    return _git(estate.authority, "rev-parse", "HEAD"), sha256(data).hexdigest()


@pytest.fixture(scope="module")
def estate(tmp_path_factory):
    root = tmp_path_factory.mktemp("release-estate")
    source = root / "source"
    _git(
        REPOSITORY_ROOT,
        "clone",
        "--shared",
        "--quiet",
        str(REPOSITORY_ROOT),
        str(source),
    )
    # Use current permanent proof declarations, including new implementation files
    # while this slice is still an uncommitted candidate during local preflight.
    layout_path = "governance/framework/source-layout.yaml"
    layout = yaml.safe_load((REPOSITORY_ROOT / layout_path).read_text(encoding="utf-8"))
    proof_paths = {layout_path}
    for closure in layout["governance_qualification"]["required_controls"].values():
        proof_paths.update(closure["implementation"])
        proof_paths.update(closure["test_evidence"])
    for relative in proof_paths:
        destination = source / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPOSITORY_ROOT / relative, destination)
    for path in (source / "governance").glob("GDC-*.md"):
        text = path.read_text(encoding="utf-8")
        import re

        text = re.sub(r"  version: [^\n]+", "  version: 1.0.0", text, count=1).replace(
            "  status: draft", "  status: approved", 1
        )
        path.write_text(text, encoding="utf-8")
    path = source / "governance/normative-control-registry.yaml"
    registry = yaml.safe_load(path.read_text(encoding="utf-8"))
    for record in registry["controls"]:
        if record["release_class"] == "root-of-trust":
            record["evidence_status"] = "verified"
            record["implementation"] = ["engine/control/governance/controls.py"]
            record["test_evidence"] = ["tests/control/governance/test_controls.py"]
    path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    head = _commit(source)
    tree = _git(source, "rev-parse", "HEAD^{tree}")
    # A genuine different commit with exactly the candidate tree models squash merge.
    merge = _git(
        source,
        "-c",
        "user.name=Release fixture",
        "-c",
        "user.email=release@example.invalid",
        "commit-tree",
        tree,
        "-p",
        _git(source, "rev-parse", "HEAD^"),
        input=b"Synthetic squash\n",
    )
    _git(source, "update-ref", "refs/remotes/origin/main", merge)
    _git(source, "tag", "governance-v1.0.0", head)
    authority = root / "authority"
    authority.mkdir()
    _git(authority, "init", "-q")
    _write(
        authority / "governance/authority.json",
        {
            "candidate_repository": target.REPOSITORY,
            "authority_check_context": "Codex Governance Authority",
            "github_app_id": 4864946,
        },
    )
    revision = _publication(authority, source)
    manifest = target.build_release_manifest(source, authority, revision, "1.0.0")
    check = {
        "id": 42,
        "name": "Codex Governance Authority",
        "head_sha": head,
        "status": "completed",
        "conclusion": "success",
        "app": {"id": 4864946},
    }
    pr = {
        "merged": True,
        "head": {"sha": head},
        "base": {
            "sha": _git(source, "rev-parse", "HEAD^"),
            "ref": "main",
            "repo": {"full_name": target.REPOSITORY},
        },
        "merge_commit_sha": merge,
    }
    qualification = {
        "check_runs": [
            {
                "name": "Governance Qualification",
                "head_sha": head,
                "status": "completed",
                "conclusion": "success",
                "app": {"id": 15368},
            }
        ]
    }
    result = SimpleNamespace(
        source=source,
        authority=authority,
        revision=revision,
        manifest=manifest,
        check=check,
        pr=pr,
        qualification=qualification,
    )
    result.manifest_revision, result.digest = _manifest_commit(result)
    return result


def _provider(estate, *, check=None, pr=None, qualification=None):
    def read(path):
        if "/check-runs/" in path:
            return copy.deepcopy(estate.check if check is None else check)
        if "/pulls/" in path:
            return copy.deepcopy(estate.pr if pr is None else pr)
        return copy.deepcopy(
            estate.qualification if qualification is None else qualification
        )

    return read


def _verify(estate, *, revision=None, digest=None, tag=None, read=None):
    return target.verify_release_manifest(
        estate.source,
        estate.authority,
        revision or estate.manifest_revision,
        "1.0.0",
        digest or estate.digest,
        lambda expected: github.verify_publication(expected, read or _provider(estate)),
        tag=tag,
    )


@pytest.fixture
def bound_metadata(estate, monkeypatch):
    # Isolate manifest/provider decisions; integration tests separately run real
    # Git export, framework compilation and readiness recomputation.
    monkeypatch.setattr(
        target, "build_release_manifest", lambda *args: copy.deepcopy(estate.manifest)
    )


def test_real_recomputation_is_deterministic_and_binds_every_inventory(estate):
    first = target.build_release_manifest(
        estate.source, estate.authority, estate.revision, "1.0.0"
    )
    assert target.canonical_json(first) == target.canonical_json(estate.manifest)
    assert len(first["baseline"]) == 12
    assert len(first["schemas"]) >= 9
    assert first["engine_version"] == "1.0.0"
    assert first["framework"]["version"] == "0.2.0"
    assert (
        first["reproducibility"]["toolchain"]["qualification_runtime"]["python"]
        == "3.13.15"
    )
    assert not first["controls"]["pending_root_of_trust"]
    assert _verify(estate)["status"] == "release_candidate_verified"
    assert _verify(estate, tag="governance-v1.0.0")["tag_verified"]


@pytest.mark.parametrize(
    "field",
    [
        "schema_version",
        "kind",
        "integrity",
        "release_version",
        "repository",
        "source_commit",
        "source_tree",
        "baseline",
        "engine_version",
        "framework",
        "schemas",
        "reproducibility",
        "controls",
        "authority",
        "qualification_context",
        "authority_context",
        "extra",
    ],
)
def test_manifest_field_drift_is_not_repaired_or_ignored(estate, field, bound_metadata):
    value = copy.deepcopy(estate.manifest)
    if field == "authority":
        value[field]["record"]["token_revoked"] = False
    else:
        value[field] = "tampered"
    revision, digest = _manifest_commit(estate, value)
    with pytest.raises(target.ReleaseError, match="manifest drift"):
        _verify(estate, revision=revision, digest=digest)


@pytest.mark.parametrize("raw", [b"[]\n", b"{", b'{"a":1,"a":2}\n'])
def test_malformed_manifest_fails_closed(estate, raw):
    revision, digest = _manifest_commit(estate, raw=raw)
    with pytest.raises(target.ReleaseError):
        _verify(estate, revision=revision, digest=digest)


def test_digest_and_canonical_bytes_are_required(estate):
    with pytest.raises(target.ReleaseError, match="digest mismatch"):
        _verify(estate, digest="0" * 64)
    revision, digest = _manifest_commit(
        estate, raw=json.dumps(estate.manifest, indent=2).encode()
    )
    with pytest.raises(target.ReleaseError, match="canonical manifest"):
        _verify(estate, revision=revision, digest=digest)


@pytest.mark.parametrize(
    "field,value",
    [
        ("id", 43),
        ("name", "other"),
        ("head_sha", "f" * 40),
        ("status", "queued"),
        ("conclusion", "failure"),
        ("app", {"id": 15368}),
    ],
)
def test_provider_check_must_belong_to_exact_app_and_source(
    estate, field, value, bound_metadata
):
    check = copy.deepcopy(estate.check)
    check[field] = value
    with pytest.raises(target.ReleaseError, match="provider check mismatch"):
        _verify(estate, read=_provider(estate, check=check))


@pytest.mark.parametrize(
    "damage",
    [
        "unmerged",
        "head",
        "base",
        "branch",
        "repository",
        "tree",
        "history",
        "missing-field",
    ],
)
def test_unmerged_or_different_canonical_tree_cannot_release(
    estate, damage, bound_metadata
):
    pr = copy.deepcopy(estate.pr)
    if damage == "unmerged":
        pr["merged"] = False
    elif damage == "head":
        pr["head"]["sha"] = "f" * 40
    elif damage == "base":
        pr["base"]["sha"] = "f" * 40
    elif damage == "branch":
        pr["base"]["ref"] = "other"
    elif damage == "repository":
        pr["base"]["repo"]["full_name"] = "other/repo"
    elif damage == "tree":
        pr["merge_commit_sha"] = pr["base"]["sha"]
    elif damage == "history":
        pr["merge_commit_sha"] = estate.manifest["source_commit"]
    else:
        pr.pop("merged")
    with pytest.raises(target.ReleaseError):
        _verify(estate, read=_provider(estate, pr=pr))


def test_missing_exact_qualification_and_wrong_tags_fail(estate, bound_metadata):
    with pytest.raises(target.ReleaseError, match="qualification missing"):
        _verify(estate, read=_provider(estate, qualification={"check_runs": []}))
    with pytest.raises(target.ReleaseError, match="tag name"):
        _verify(estate, tag="v1.0.0")
    _git(estate.source, "tag", "-f", "governance-v1.0.0", estate.pr["merge_commit_sha"])
    try:
        with pytest.raises(target.ReleaseError, match="tag commit"):
            _verify(estate, tag="governance-v1.0.0")
    finally:
        _git(
            estate.source,
            "tag",
            "-f",
            "governance-v1.0.0",
            estate.manifest["source_commit"],
        )


@pytest.mark.parametrize(
    "damage",
    [
        "draft",
        "unstable",
        "root-pending",
        "duplicate",
        "missing",
        "ids",
        "malformed",
        "schemas",
        "symlink",
    ],
)
def test_unqualified_source_is_not_a_release(estate, tmp_path, damage):
    source = tmp_path / "source"
    _git(
        estate.source,
        "clone",
        "--shared",
        "--quiet",
        str(estate.source),
        str(source),
    )
    path = source / "governance/GDC-000-governance-policy.md"
    if damage == "draft":
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "status: approved", "status: draft", 1
            ),
            encoding="utf-8",
        )
    elif damage == "unstable":
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "version: 1.0.0", "version: 0.1.0", 1
            ),
            encoding="utf-8",
        )
    elif damage == "root-pending":
        registry = source / "governance/normative-control-registry.yaml"
        data = yaml.safe_load(registry.read_text(encoding="utf-8"))
        row = next(r for r in data["controls"] if r["release_class"] == "root-of-trust")
        row.update(
            evidence_status="pending",
            control_owner="Synthetic owner",
            target_phase="Slice 13.5 Stable GDC Baseline",
        )
        registry.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    elif damage == "duplicate":
        shutil.copyfile(path, path.with_name("GDC-000-duplicate.md"))
    elif damage == "missing":
        path.unlink()
    elif damage == "ids":
        p = source / "governance/bootstrap-manifest.yaml"
        d = yaml.safe_load(p.read_text(encoding="utf-8"))
        d["governance_control_plane"]["required_baseline_ids"] = []
        p.write_text(yaml.safe_dump(d), encoding="utf-8")
    elif damage == "malformed":
        path.write_text("bad", encoding="utf-8")
    elif damage == "schemas":
        shutil.rmtree(source / "schemas")
    else:
        # Commit a symlink via the Git index, without requiring Windows symlink privileges.
        oid = _git(source, "hash-object", "-w", "--stdin", input=b"../outside")
        _git(source, "update-index", "--add", "--cacheinfo", f"120000,{oid},link")
        (source / "link").write_text("../outside", encoding="utf-8")
    _commit(source)
    revision = _publication(estate.authority, source)
    if damage in {"draft", "unstable", "root-pending"}:
        value = target.build_release_manifest(
            source, estate.authority, revision, "1.0.0"
        )
        mr, digest = _manifest_commit(estate, value)
        with pytest.raises(
            target.ReleaseError, match="not approved|stable release|root-of-trust"
        ):
            target.verify_release_manifest(
                source, estate.authority, mr, "1.0.0", digest, _provider(estate)
            )
    else:
        with pytest.raises((target.ReleaseError, RuntimeError)):
            target.build_release_manifest(source, estate.authority, revision, "1.0.0")


def test_dirty_source_and_bad_version_or_revision_fail(estate):
    path = estate.source / "untracked-release-input"
    path.write_text("bad", encoding="utf-8")
    try:
        with pytest.raises(target.ReleaseError, match="clean source"):
            target.build_release_manifest(
                estate.source, estate.authority, estate.revision, "1.0.0"
            )
    finally:
        path.unlink()
    for version in ("0.1.0", "01.0.0", "../escape"):
        with pytest.raises((ValueError, target.ReleaseError)):
            target.build_release_manifest(
                estate.source, estate.authority, estate.revision, version
            )
    with pytest.raises(target.ReleaseError, match="exact commit"):
        _verify(estate, revision="main")


@pytest.mark.parametrize(
    "damage",
    [
        "fields",
        "candidate",
        "base",
        "repository",
        "format",
        "revoked",
        "check-id",
        "digest",
        "identity",
        "context",
    ],
)
def test_retained_publication_must_be_complete_and_exact(estate, damage):
    path = (
        estate.authority
        / f"governance/publications/{estate.manifest['source_commit']}.json"
    )
    data = copy.deepcopy(estate.manifest["authority"]["record"])
    if damage == "fields":
        data["extra"] = True
    elif damage == "candidate":
        data["candidate"].pop("base_sha")
    elif damage == "base":
        data["candidate"]["base_sha"] = "main"
    elif damage == "repository":
        data["candidate"]["repository"] = "other/repo"
    elif damage == "format":
        data["schema_version"] = True
    elif damage == "revoked":
        data["token_revoked"] = False
    elif damage == "check-id":
        data["check_run_id"] = True
    elif damage == "digest":
        data["permit_digest"] = "invalid"
    else:
        _write(
            estate.authority / "governance/authority.json",
            {
                "candidate_repository": target.REPOSITORY,
                "github_app_id": 4864946 if damage == "context" else True,
                "authority_check_context": "wrong"
                if damage == "context"
                else "Codex Governance Authority",
            },
        )
    _write(path, data)
    revision = _commit(estate.authority)
    try:
        with pytest.raises(target.ReleaseError):
            value = target.build_release_manifest(
                estate.source, estate.authority, revision, "1.0.0"
            )
            if damage in {"identity", "context"}:
                github.verify_publication(value, _provider(estate))
    finally:
        # Restore independently pinned fixture records for following test cases.
        _write(path, estate.manifest["authority"]["record"])
        _write(
            estate.authority / "governance/authority.json",
            {
                "candidate_repository": target.REPOSITORY,
                "authority_check_context": "Codex Governance Authority",
                "github_app_id": 4864946,
            },
        )
        _commit(estate.authority)


def test_missing_publication_and_invalid_git_fail_closed(estate, tmp_path):
    with pytest.raises(target.ReleaseError):
        target.build_release_manifest(
            tmp_path, estate.authority, estate.revision, "1.0.0"
        )
    with pytest.raises(target.ReleaseError, match="missing Git blob"):
        target._blob(estate.authority, estate.revision, "missing.json")
    with pytest.raises(target.ReleaseError, match="regular Git blob"):
        target._blob(estate.source, estate.manifest["source_commit"], "governance")


def test_revision_change_during_binding_fails_closed(estate, monkeypatch):
    original = target._text
    count = 0

    def changed(root, *args):
        nonlocal count
        if args == ("rev-parse", "HEAD^{commit}"):
            count += 1
            if count == 2:
                return "f" * 40
        return original(root, *args)

    monkeypatch.setattr(target, "_text", changed)
    with pytest.raises(target.ReleaseError, match="source changed"):
        target.build_release_manifest(
            estate.source, estate.authority, estate.revision, "1.0.0"
        )


@pytest.mark.parametrize(
    "damage", ["oid", "kind", "length", "trailing", "escape", "content"]
)
def test_git_batch_cannot_substitute_or_escape_blobs(tmp_path, monkeypatch, damage):
    oid = target._blob_id(b"x")
    payload = (oid + " blob 1\nx\n").encode()
    if damage == "oid":
        payload = payload.replace(oid.encode(), b"b" * 40)
    elif damage == "kind":
        payload = payload.replace(b"blob", b"tree")
    elif damage == "length":
        payload = payload.replace(b"blob 1", b"blob 100")
    elif damage == "trailing":
        payload += b"extra"
    elif damage == "content":
        payload = payload.replace(b"\nx\n", b"\ny\n")
    monkeypatch.setattr(target, "_git", lambda *args, **kwargs: payload)
    with pytest.raises(target.ReleaseError):
        target._export_blobs(
            tmp_path, {"../outside" if damage == "escape" else "inside": oid}, tmp_path
        )


def test_unmerged_authority_manifest_is_rejected(estate):
    detached = _git(
        estate.authority,
        "-c",
        "user.name=Release fixture",
        "-c",
        "user.email=release@example.invalid",
        "commit-tree",
        _git(estate.authority, "rev-parse", estate.manifest_revision + "^{tree}"),
        input=b"Unmerged Authority fixture\n",
    )
    with pytest.raises(target.ReleaseError):
        _verify(estate, revision=detached)


def test_git_timeout_fails_closed(tmp_path, monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("git", 60)

    monkeypatch.setattr(target.subprocess, "run", timeout)
    with pytest.raises(target.ReleaseError, match="release metadata failed"):
        target.build_release_manifest(tmp_path, tmp_path, "a" * 40, "1.0.0")


def test_malformed_yaml_metadata_fails_closed(estate, monkeypatch):
    def invalid(*args, **kwargs):
        raise yaml.YAMLError("synthetic malformed metadata")

    monkeypatch.setattr(target.yaml, "safe_load", invalid)
    with pytest.raises(target.ReleaseError, match="synthetic malformed metadata"):
        target.build_release_manifest(
            estate.source, estate.authority, estate.revision, "1.0.0"
        )


def test_github_default_readback_uses_provider_adapter(estate, monkeypatch):
    monkeypatch.setattr(github, "read_github", _provider(estate))
    assert github.verify_publication(estate.manifest) == estate.pr["merge_commit_sha"]


def test_core_accepts_verified_publication_port_without_provider_payloads(
    estate, bound_metadata
):
    observed = []

    def verify(expected):
        observed.append(expected)
        return estate.pr["merge_commit_sha"]

    report = target.verify_release_manifest(
        estate.source,
        estate.authority,
        estate.manifest_revision,
        "1.0.0",
        estate.digest,
        verify,
    )
    assert report["status"] == "release_candidate_verified"
    assert observed == [estate.manifest]
