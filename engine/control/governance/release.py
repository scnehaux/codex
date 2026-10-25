"""Recompute unsigned release metadata from immutable Codex and Authority objects."""

from __future__ import annotations

from hashlib import sha1, sha256
import json
import os
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory, TemporaryFile
import tomllib
from typing import Callable

import yaml

from engine.control.framework.executable import compile_framework
from engine.control.governance.genesis import parse_frontmatter
from engine.control.governance.readiness import assert_governance_readiness
from engine.core.governance.versioning import SemanticVersion


REPOSITORY = "scnehaux/codex"
AUTHORITY = "scnehaux/codex-authority"
VerifyPublication = Callable[[dict], str]


class ReleaseError(RuntimeError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ReleaseError(message)


def canonical_json(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
        + b"\n"
    )


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def _json(raw: bytes) -> dict:
    value = json.loads(raw, object_pairs_hook=_unique_object)
    _require(isinstance(value, dict), "JSON object required")
    return value


def _sha(value: object) -> str:
    _require(
        isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value) is not None,
        "exact commit SHA required",
    )
    return value


def _git(root: Path, *args: str, input: bytes | None = None) -> bytes:
    # Regular files avoid launcher EOF ambiguity and pipe-reader allocations for
    # batch output under Windows memory pressure. Git remains time bounded.
    with TemporaryFile() as stdin, TemporaryFile() as stdout, TemporaryFile() as stderr:
        if input is not None:
            stdin.write(input)
        stdin.seek(0)
        subprocess.run(
            [
                "git",
                "--no-replace-objects",
                "--literal-pathspecs",
                "-C",
                str(root),
                *args,
            ],
            env={
                k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")
            },
            stdout=stdout,
            stderr=stderr,
            stdin=stdin,
            timeout=60,
            check=True,
        )
        stdout.seek(0)
        return stdout.read()


def _text(root: Path, *args: str) -> str:
    return _git(root, *args).decode("utf-8").strip()


def _blob(root: Path, revision: str, path: str) -> tuple[str, bytes]:
    row = _git(root, "ls-tree", "-z", revision, "--", path).split(b"\0")
    _require(len(row) == 2 and bool(row[0]), "missing Git blob: " + path)
    metadata, actual = row[0].split(b"\t", 1)
    mode, kind, oid = metadata.decode("ascii").split()
    _require(
        mode in {"100644", "100755"}
        and kind == "blob"
        and actual.decode("utf-8") == path,
        "regular Git blob required: " + path,
    )
    raw = _git(root, "cat-file", "blob", oid)
    _require(_blob_id(raw) == oid, "Git blob content mismatch")
    return oid, raw


def _blob_id(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _version(value: str) -> str:
    _require(
        SemanticVersion.parse(value) >= SemanticVersion(1, 0, 0),
        "stable release version required",
    )
    return value


def _export_blobs(root: Path, blobs: dict[str, str], destination: Path) -> None:
    raw = _git(
        root,
        "cat-file",
        "--batch",
        input=("\n".join(blobs.values()) + "\n").encode("ascii"),
    )
    cursor = 0
    for relative, oid in blobs.items():
        end = raw.index(b"\n", cursor)
        actual, kind, size = raw[cursor:end].decode("ascii").split()
        length = int(size)
        start, stop = end + 1, end + 1 + length
        _require(
            actual == oid
            and kind == "blob"
            and length >= 0
            and raw[stop : stop + 1] == b"\n",
            "Git batch blob binding",
        )
        _require(_blob_id(raw[start:stop]) == oid, "Git batch content mismatch")
        path = (destination / relative).resolve()
        _require(
            path.is_relative_to(destination) and path != destination,
            "Git blob path escapes snapshot",
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw[start:stop])
        cursor = stop + 1
    _require(cursor == len(raw), "unexpected Git batch trailing data")


def _publication(root: Path, revision: str, source: str) -> dict:
    _sha(revision)
    _git(root, "merge-base", "--is-ancestor", revision, "refs/remotes/origin/main")
    identity_blob, identity_raw = _blob(root, revision, "governance/authority.json")
    identity = _json(identity_raw)
    _require(
        identity["candidate_repository"] == REPOSITORY, "Authority repository identity"
    )
    path = f"governance/publications/{source}.json"
    oid, raw = _blob(root, revision, path)
    record = _json(raw)
    _require(
        set(record)
        == {
            "schema_version",
            "kind",
            "candidate",
            "activation_digest",
            "permit_digest",
            "check_post_attempted",
            "check_run_id",
            "status",
            "token_revoked",
            "effective_enforcement_proven",
        },
        "publication fields",
    )
    candidate = record["candidate"]
    _require(
        isinstance(candidate, dict)
        and set(candidate) == {"repository", "pull_request", "head_sha", "base_sha"},
        "publication candidate fields",
    )
    _sha(candidate["base_sha"])
    _require(
        candidate["repository"] == REPOSITORY
        and candidate["head_sha"] == source
        and type(candidate["pull_request"]) is int
        and candidate["pull_request"] > 0,
        "publication candidate binding",
    )
    _require(
        type(record["schema_version"]) is int
        and record["schema_version"] == 1
        and record["kind"] == "codex-publication-outcome",
        "publication format",
    )
    _require(
        record["status"] == "published"
        and record["check_post_attempted"] is True
        and record["token_revoked"] is True
        and record["effective_enforcement_proven"] is False,
        "successful revoked publication required",
    )
    _require(
        type(record["check_run_id"]) is int and record["check_run_id"] > 0,
        "publication check id",
    )
    for field in ("activation_digest", "permit_digest"):
        _require(
            isinstance(record[field], str)
            and re.fullmatch(r"[0-9a-f]{64}", record[field]) is not None,
            "publication digest",
        )
    return {
        "repository": AUTHORITY,
        "revision": revision,
        "path": path,
        "git_blob": oid,
        "record": record,
        "identity": {"git_blob": identity_blob, "declaration": identity},
    }


def build_release_manifest(
    source_root: Path,
    authority_root: Path,
    authority_revision: str,
    release_version: str,
) -> dict:
    """Build metadata only; this function does not approve or declare a release."""
    root, authority = Path(source_root).resolve(), Path(authority_root).resolve()
    try:
        _version(release_version)
        source = _sha(_text(root, "rev-parse", "HEAD^{commit}"))
        _require(
            not _git(root, "status", "--porcelain=v1", "--untracked-files=all").strip(),
            "clean source checkout required",
        )
        publication = _publication(authority, authority_revision, source)
        blobs = {}
        for row in _git(root, "ls-tree", "-r", "-z", source).split(b"\0"):
            if not row:
                continue
            metadata, path = row.split(b"\t", 1)
            mode, kind, oid = metadata.decode("ascii").split()
            _require(
                mode in {"100644", "100755"} and kind == "blob",
                "release tree contains non-regular source",
            )
            blobs[path.decode("utf-8")] = oid
        # Worktree line endings, ignored files and local overlays cannot affect recomputation.
        with TemporaryDirectory(prefix="codex-release-") as directory:
            exported = Path(directory)
            _export_blobs(root, blobs, exported)
            bootstrap = yaml.safe_load(
                (exported / "governance/bootstrap-manifest.yaml").read_text(
                    encoding="utf-8"
                )
            )
            required = bootstrap["governance_control_plane"]["required_baseline_ids"]
            _require(
                isinstance(required, list)
                and bool(required)
                and all(
                    isinstance(x, str) and re.fullmatch(r"GDC-\d{3}", x)
                    for x in required
                )
                and len(set(required)) == len(required),
                "unique required baseline IDs",
            )
            baseline = {}
            for path in sorted((exported / "governance").glob("GDC-*.md")):
                meta = parse_frontmatter(path.read_text(encoding="utf-8"))
                identifier = meta["id"]
                _require(identifier not in baseline, "duplicate GDC identity")
                relative = path.relative_to(exported).as_posix()
                baseline[identifier] = {
                    "id": identifier,
                    "path": relative,
                    "version": meta["version"],
                    "status": meta["status"],
                    "git_blob": blobs[relative],
                }
            _require(set(required) <= set(baseline), "required baseline GDC missing")
            framework = compile_framework(exported)
            readiness = assert_governance_readiness(exported)
            scm = yaml.safe_load(
                (exported / framework.governance.scm_enforcement_policy).read_text(
                    encoding="utf-8"
                )
            )
            policy_raw = (
                exported / "governance/reproducibility-policy.json"
            ).read_bytes()
            policy = _json(policy_raw)
            schemas = {
                p.relative_to(exported).as_posix(): blobs[
                    p.relative_to(exported).as_posix()
                ]
                for p in sorted((exported / "schemas").rglob("*.json"))
            }
            _require(bool(schemas), "release schemas missing")
            result = {
                "schema_version": 1,
                "kind": "codex-governance-release",
                "integrity": "unsigned",
                "release_version": release_version,
                "repository": REPOSITORY,
                "source_commit": source,
                "source_tree": _text(root, "rev-parse", source + "^{tree}"),
                "baseline": [baseline[x] for x in sorted(required)],
                "engine_version": tomllib.loads(
                    (exported / "pyproject.toml").read_text(encoding="utf-8")
                )["project"]["version"],
                "framework": {
                    "id": framework.identity.framework_id,
                    "version": framework.identity.framework_version,
                    "ontology_version": framework.relationships.ontology_version,
                    "contract_sha256": framework.contract_sha256,
                    "semantic_sha256": framework.semantic_sha256,
                    "authority_sha256": framework.authority_sha256,
                },
                "schemas": schemas,
                "reproducibility": {
                    "policy_sha256": sha256(policy_raw).hexdigest(),
                    "toolchain": policy,
                },
                "controls": {
                    "registry_git_blob": blobs[
                        "governance/normative-control-registry.yaml"
                    ],
                    "pending_root_of_trust": list(readiness.pending_root_of_trust),
                },
                "qualification_context": scm["qualification"]["candidate"]["context"],
                "authority_context": scm["qualification"]["external_authority"][
                    "context"
                ],
                "authority": publication,
            }
        _require(
            source == _text(root, "rev-parse", "HEAD^{commit}")
            and not _git(
                root, "status", "--porcelain=v1", "--untracked-files=all"
            ).strip(),
            "source changed during release binding",
        )
        return result
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        yaml.YAMLError,
        subprocess.SubprocessError,
    ) as exc:
        raise ReleaseError(f"release metadata failed: {exc}") from exc


def verify_release_manifest(
    source_root: Path,
    authority_root: Path,
    manifest_revision: str,
    release_version: str,
    manifest_sha256: str,
    verify_publication: VerifyPublication,
    *,
    tag: str | None = None,
) -> dict:
    """Verify committed metadata, baseline eligibility and independent provider readback."""
    try:
        _sha(manifest_revision)
        _version(release_version)
        _git(
            Path(authority_root),
            "merge-base",
            "--is-ancestor",
            manifest_revision,
            "refs/remotes/origin/main",
        )
        path = f"governance/releases/governance-{release_version}.json"
        _, raw = _blob(Path(authority_root), manifest_revision, path)
        _require(sha256(raw).hexdigest() == manifest_sha256, "manifest digest mismatch")
        manifest = _json(raw)
        _require(
            raw == canonical_json(manifest), "canonical manifest encoding required"
        )
        expected = build_release_manifest(
            source_root,
            authority_root,
            manifest["authority"]["revision"],
            release_version,
        )
        _require(
            canonical_json(manifest) == canonical_json(expected),
            "release manifest drift",
        )
        _require(
            not expected["controls"]["pending_root_of_trust"],
            "root-of-trust controls pending",
        )
        for gdc in expected["baseline"]:
            _require(
                gdc["status"] == "approved",
                "required GDC is not approved: " + gdc["id"],
            )
            _version(gdc["version"])
        record = expected["authority"]["record"]
        merge = _sha(verify_publication(expected))
        root = Path(source_root)
        _require(
            _text(root, "rev-parse", merge + "^{tree}") == expected["source_tree"],
            "squash merge tree differs from release source",
        )
        _git(root, "merge-base", "--is-ancestor", merge, "refs/remotes/origin/main")
        if tag is not None:
            _require(
                tag == "governance-v" + release_version, "release tag name mismatch"
            )
            _require(
                _text(root, "rev-parse", "refs/tags/" + tag + "^{commit}")
                == expected["source_commit"],
                "release tag commit mismatch",
            )
        return {
            "status": "release_candidate_verified",
            "source_commit": expected["source_commit"],
            "manifest_sha256": manifest_sha256,
            "check_run_id": record["check_run_id"],
            "tag_verified": tag is not None,
        }
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        subprocess.SubprocessError,
    ) as exc:
        raise ReleaseError(f"release verification failed: {exc}") from exc
