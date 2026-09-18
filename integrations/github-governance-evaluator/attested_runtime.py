#!/usr/bin/env python3
"""Unpromoted, read-only Codex attestation runtime; never publishes a check.

Historical collector/evaluator bytes remain unchanged. Authority must separately
review and pin this entrypoint and its complete package before effective use.
"""
from __future__ import annotations

import argparse
import base64
from dataclasses import asdict
from hashlib import sha1, sha256
from http.client import HTTPException
import json
from pathlib import Path
import re
import stat
import sys
from types import ModuleType
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

REPOSITORY = "scnehaux/codex"
AUTHORITY_REPOSITORY = "scnehaux/codex-authority"
AUTHORITY_API = f"/repos/{AUTHORITY_REPOSITORY}/git"
AUTHORITY_REF = f"{AUTHORITY_API}/ref/heads/main"
API_ROOT = "https://api.github.com"
API_VERSION = "2026-03-10"
COLLECTOR_REVISION = "cbd64f78c8f72f28880d4673729a796b249d8eae"
EVALUATOR_REVISION = "23b05a855419b86b61b0c9266805bb66b143c366"
DEPENDENCY_BLOBS = {
    "runtime.py": "c59911e9c0800c917fed21e6f33f3181c3a61e60",
    "evaluator.py": "ab2f152c21bd6d6f22df21172c4d027035ff8c11",
    "promotion.json": "f8f67280baf1c8725f67592d015ff37be2c4a4c3",
    "runtime-promotion.json": "83658bf5a44d22804d1628074dd8f27a7047d68e",
}
ALLOWED_BLOCKERS = frozenset({
    "privileged-validation-missing",
    "runtime-critical-mutation-requires-privileged-validation",
})
MAX_RESPONSE_BYTES = 1_000_000
MAX_ATTESTATION_BYTES = 128_000
MAX_TREE_ENTRIES = 10_000
MAX_CHANGED_FILES = 2_000
SHA_RE = re.compile(r"[0-9a-f]{40}")
OBJECT_PATH_RE = re.compile(re.escape(AUTHORITY_API) + r"/(commits|trees|blobs)/([0-9a-f]{40})")


class AttestedRuntimeError(Exception):
    """Fixed diagnostic; remote bodies and environment values are never exposed."""
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise AttestedRuntimeError(code, "Read-only attestation boundary rejected inconsistent data.")


def _sha(value: object, code: str) -> str:
    _require(isinstance(value, str) and SHA_RE.fullmatch(value) is not None and value != "0" * 40, code)
    return value


def _object(value: object, code: str) -> dict[str, Any]:
    _require(isinstance(value, dict), code)
    return value


def _keys(value: object, expected: set[str], code: str) -> dict[str, Any]:
    result = _object(value, code)
    _require(set(result) == expected, code)
    return result


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _invalid_constant(value: str) -> None:
    raise ValueError("non-finite JSON constant")


def _json(raw: bytes, limit: int, code: str) -> dict[str, Any]:
    _require(isinstance(raw, bytes) and 0 < len(raw) <= limit, code)
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
    except (ValueError, UnicodeError, RecursionError):
        raise AttestedRuntimeError(code, "Bounded UTF-8 JSON object required.") from None
    return _object(data, code)


def _blob(raw: bytes) -> str:
    return sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def authority_get(path: str) -> dict[str, Any]:
    """Fixed-host unauthenticated GET only; no queries, redirects, or retries."""
    _require(isinstance(path, str), "authority-api-path")
    match = OBJECT_PATH_RE.fullmatch(path)
    _require(path == AUTHORITY_REF or match is not None, "authority-api-path")
    if match is not None:
        _sha(match.group(2), "authority-api-path")
    request = Request(API_ROOT + path, method="GET", headers={
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": API_VERSION,
        "User-Agent": "scnehaux-attestation-reader/0.1",
    })
    try:
        with build_opener(ProxyHandler({}), NoRedirect()).open(request, timeout=10) as response:
            _require(response.status == 200, "authority-api-status")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        status = exc.code
        exc.close()
        raise AttestedRuntimeError(f"authority-http-{status}", "Authority object read failed; no approval inferred.") from None
    except (URLError, TimeoutError, OSError, HTTPException):
        raise AttestedRuntimeError("authority-network", "Secure Authority read failed; no approval inferred.") from None
    return _json(raw, MAX_RESPONSE_BYTES, "authority-api-json")


def _candidate(value: object) -> dict[str, Any]:
    candidate = _keys(value, {"repository", "pull_request", "base_sha", "head_sha", "changed_files"}, "candidate-shape")
    _require(candidate["repository"] == REPOSITORY, "candidate-repository")
    _require(type(candidate["pull_request"]) is int and candidate["pull_request"] > 0, "candidate-pr")
    base = _sha(candidate["base_sha"], "candidate-base")
    head = _sha(candidate["head_sha"], "candidate-head")
    _require(base != head, "candidate-range")
    paths = candidate["changed_files"]
    _require(isinstance(paths, list) and 0 < len(paths) <= MAX_CHANGED_FILES, "candidate-files")
    for path in paths:
        _require(isinstance(path, str) and 0 < len(path) <= 4096, "candidate-files")
        _require(not path.startswith("/") and "\\" not in path, "candidate-files")
        _require(all(part not in {"", ".", ".."} for part in path.split("/")), "candidate-files")
        _require(all(32 <= ord(char) != 127 and not 0xD800 <= ord(char) <= 0xDFFF for char in path), "candidate-files")
    _require(paths == sorted(set(paths)), "candidate-files")
    return candidate


def validate_attestation(raw: bytes, candidate: dict[str, Any]) -> dict[str, Any]:
    """Validate data only; caller must establish its committed Authority origin."""
    candidate = _candidate(candidate)
    data = _keys(_json(raw, MAX_ATTESTATION_BYTES, "attestation-json"), {
        "contract_version", "kind", "candidate", "decision", "scope", "authority", "claims",
    }, "attestation-shape")
    _require(type(data["contract_version"]) is int and data["contract_version"] == 1, "attestation-version")
    _require(data["kind"] == "codex-privileged-validation-attestation", "attestation-kind")
    _require(data["decision"] == "pass" and data["scope"] == "protected-governance-maintenance", "attestation-decision")
    observed = _candidate(data["candidate"])
    _require(observed == candidate, "attestation-candidate")
    authority = _keys(data["authority"], {"repository", "default_branch", "mode"}, "attestation-authority")
    _require(authority == {"repository": AUTHORITY_REPOSITORY, "default_branch": "main", "mode": "privileged-explicit"}, "attestation-authority")
    claims = _keys(data["claims"], {"candidate_code_executed", "credentials_used", "exact_candidate_binding"}, "attestation-claims")
    _require(claims["candidate_code_executed"] is False and claims["credentials_used"] is False and claims["exact_candidate_binding"] is True, "attestation-claims")
    return data


def _tree_entry(get: Callable, tree_sha: str, name: str) -> dict[str, Any] | None:
    tree = _object(get(f"{AUTHORITY_API}/trees/{tree_sha}"), "authority-tree")
    _require(tree.get("sha") == tree_sha and tree.get("truncated") is False, "authority-tree")
    entries = tree.get("tree")
    _require(isinstance(entries, list) and len(entries) <= MAX_TREE_ENTRIES, "authority-tree")
    names: set[str] = set()
    found = None
    for value in entries:
        entry = _object(value, "authority-tree")
        path = entry.get("path")
        _require(isinstance(path, str) and 0 < len(path) <= 4096 and "/" not in path and path not in {".", ".."}, "authority-tree")
        _require(path not in names, "authority-tree")
        names.add(path)
        if path == name:
            found = entry
    return found


def collect_attestation(candidate: dict[str, Any], get: Callable = authority_get) -> dict[str, Any]:
    """Walk one immutable Git snapshot, rejecting symlinks and truncated trees."""
    candidate = _candidate(candidate)
    ref = _object(get(AUTHORITY_REF), "authority-ref")
    obj = _object(ref.get("object"), "authority-ref")
    _require(ref.get("ref") == "refs/heads/main" and obj.get("type") == "commit", "authority-ref")
    revision = _sha(obj.get("sha"), "authority-ref")
    commit = _object(get(f"{AUTHORITY_API}/commits/{revision}"), "authority-commit")
    _require(commit.get("sha") == revision, "authority-commit")
    tree_sha = _sha(_object(commit.get("tree"), "authority-commit").get("sha"), "authority-commit")
    path = f"governance/privileged-validations/{candidate['head_sha']}.json"
    evidence: dict[str, Any] = {
        "status": "missing", "authority_repository": AUTHORITY_REPOSITORY,
        "authority_revision": revision, "path": path, "tree_chain": [],
        "blob_sha": None, "raw_sha256": None, "attestation_digest": None, "record": None,
    }
    parts = path.split("/")
    for index, name in enumerate(parts):
        evidence["tree_chain"].append(tree_sha)
        entry = _tree_entry(get, tree_sha, name)
        if entry is None:
            return evidence
        last = index == len(parts) - 1
        _require(entry.get("type") == ("blob" if last else "tree") and entry.get("mode") == ("100644" if last else "040000"), "authority-path-mode")
        tree_sha = _sha(entry.get("sha"), "authority-entry")
    blob_sha = tree_sha
    blob = _object(get(f"{AUTHORITY_API}/blobs/{blob_sha}"), "attestation-blob")
    _require(blob.get("sha") == blob_sha and blob.get("encoding") == "base64", "attestation-blob")
    size = blob.get("size")
    _require(type(size) is int and 0 < size <= MAX_ATTESTATION_BYTES, "attestation-size")
    _require(type(entry.get("size")) is int and entry["size"] == size, "attestation-size")
    encoded = blob.get("content")
    _require(isinstance(encoded, str) and len(encoded) <= MAX_RESPONSE_BYTES, "attestation-blob")
    try:
        raw = base64.b64decode(encoded.replace("\n", ""), validate=True)
    except (ValueError, UnicodeError):
        raise AttestedRuntimeError("attestation-encoding", "Invalid Authority blob encoding.") from None
    _require(len(raw) == size and _blob(raw) == blob_sha, "attestation-blob-identity")
    record = validate_attestation(raw, candidate)
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
    evidence.update(status="verified", blob_sha=blob_sha, raw_sha256=sha256(raw).hexdigest(),
                    attestation_digest=sha256(canonical).hexdigest(), record=record)
    return evidence


def _read_dependency(path: Path, expected: str) -> bytes:
    try:
        _require(stat.S_ISREG(path.lstat().st_mode), "dependency-source")
        with path.open("rb") as handle:
            raw = handle.read(MAX_RESPONSE_BYTES + 1)
    except OSError:
        raise AttestedRuntimeError("dependency-source", "Pinned dependency is missing or unreadable.") from None
    _require(len(raw) <= MAX_RESPONSE_BYTES and _blob(raw) == expected, "dependency-blob")
    return raw


def _module(raw: bytes, path: Path, name: str) -> ModuleType:
    # Execute the bytes just verified, never a cached .pyc or an import-path lookup.
    module = ModuleType(name)
    module.__file__ = str(path)
    previous = sys.modules.get(name)
    sys.modules[name] = module
    try:
        exec(compile(raw, str(path), "exec", dont_inherit=True), module.__dict__)
    except Exception:
        if previous is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous
        raise AttestedRuntimeError("dependency-load", "Pinned dependency could not be loaded.") from None
    return module


def load_dependencies() -> tuple[ModuleType, ModuleType]:
    package = Path(__file__).resolve().parent
    # Verify the entire historical dependency package before executing any of it.
    sources = {name: _read_dependency(package / name, blob) for name, blob in DEPENDENCY_BLOBS.items()}
    collector = _module(sources["runtime.py"], package / "runtime.py", "_codex_attested_collector")
    evaluator = _module(sources["evaluator.py"], package / "evaluator.py", "_codex_attested_evaluator")
    return collector, evaluator


def collect_and_evaluate(pull_request: int, get: Callable | None = None,
                         get_authority: Callable = authority_get) -> dict[str, Any]:
    _require(type(pull_request) is int and pull_request > 0, "pull-request")
    collector, evaluator = load_dependencies()
    if get is None:
        get = collector.api_get
    manifest, candidate_evidence = collector.collect_candidate(pull_request, evaluator, get)
    qualification, qualification_evidence = collector.collect_candidate_qualification(manifest.head_sha, get)
    candidate = _candidate({**asdict(manifest), "changed_files": list(manifest.changed_files)})
    protected = [p for p in manifest.changed_files if evaluator.is_protected(p)]
    runtime_only = [p for p in manifest.changed_files if collector.is_runtime_critical(p) and p not in protected]

    def evaluate(privileged: str) -> dict[str, Any]:
        facts = evaluator.EvaluationFacts(manifest.repository, manifest.pull_request, manifest.base_sha,
                                         manifest.head_sha, EVALUATOR_REVISION, qualification, privileged)
        return evaluator.evaluate(manifest, facts, EVALUATOR_REVISION)

    original = evaluate("not_required")
    runtime_failures = ["runtime-critical-mutation-requires-privileged-validation"] if runtime_only else []
    original_failures = list(original["failure_reasons"]) + runtime_failures
    initial = {"evaluator_result": original, "runtime_failure_reasons": list(runtime_failures),
               "governance_decision": "fail" if original_failures else "pass"}
    evidence = {"status": "not_required" if not (protected or runtime_only) else "not_attempted"}
    final_evaluator = original
    if qualification == "pass" and original_failures and set(original_failures).issubset(ALLOWED_BLOCKERS):
        evidence = collect_attestation(candidate, get_authority)
        if evidence["status"] == "verified":
            final_evaluator = evaluate("pass" if protected else "not_required")
            runtime_failures = []
    failures = list(final_evaluator["failure_reasons"]) + runtime_failures

    # Catch drift during multi-request collection; publication still needs a fresh check.
    latest, _ = collector.collect_candidate(pull_request, evaluator, get)
    latest_qualification, latest_evidence = collector.collect_candidate_qualification(latest.head_sha, get)
    _require(latest == manifest, "candidate-drift")
    _require(latest_qualification == qualification and latest_evidence == qualification_evidence, "qualification-drift")
    return {
        "schema_version": 2, "kind": "codex-attested-runtime-result",
        "status": "attested_runtime_evaluation_complete", "repository": REPOSITORY,
        "pull_request": pull_request, "base_sha": manifest.base_sha, "candidate_sha": manifest.head_sha,
        "candidate_manifest": {"schema_version": 1, **candidate},
        "candidate_evidence": candidate_evidence, "qualification_evidence": qualification_evidence,
        "source_dependencies": {"collector_revision": COLLECTOR_REVISION,
                                "evaluator_revision": EVALUATOR_REVISION, "blobs": dict(DEPENDENCY_BLOBS)},
        "original_evaluation": initial, "privileged_validation_evidence": evidence,
        "evaluator_result": final_evaluator, "runtime_only_protected_mutations": runtime_only,
        "runtime_failure_reasons": runtime_failures, "failure_reasons": failures,
        "governance_decision": "fail" if failures else "pass",
        "facts_collected_independently": True, "facts_provenance_verified": False,
        "runtime_source_promoted": False, "candidate_code_executed": False, "credentials_used": False,
        "publish_enabled": False, "authority_binding_advanced": False, "effective_enforcement_proven": False,
        "notice": "Candidate capability only. Requires independent promotion and a version-aware Authority adapter; not a publication permit.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pull-request", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        source = Path(__file__).resolve()
        _require(not any((parent / ".git").exists() for parent in source.parents), "runtime-checkout")
        result = collect_and_evaluate(args.pull_request)
    except Exception as exc:
        if isinstance(exc, AttestedRuntimeError):
            code, message = exc.code, str(exc)
        else:
            code, message = "attested-runtime-failed", "Attested runtime failed closed; details suppressed."
        print(json.dumps({"status": "blocked", "code": code, "message": message,
                          "governance_decision": "not_evaluated", "publish_enabled": False,
                          "effective_enforcement_proven": False}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result["governance_decision"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
