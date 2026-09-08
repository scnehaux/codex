#!/usr/bin/env python3
"""Read-only Stage 3c facts collector for the future external authority runtime.

The collector obtains pull-request identity, touched paths, and the candidate-side
Governance Qualification result directly from GitHub's public API. It never accepts
caller-supplied candidate/facts JSON, credentials, endpoint overrides, or a publish
option. It loads the already source-pinned Stage 3b evaluator only after verifying
that the local evaluator blob exactly matches the promoted commit.

This source is not itself promoted yet. Therefore even independently collected
facts remain ineligible for publication as ``Codex Governance Authority`` until a
later privileged change pins the runtime revision and validates an exported copy.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha1
from http.client import HTTPException
import importlib.util
import json
from pathlib import Path
import re
import stat
import sys
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

API_ROOT = "https://api.github.com"
API_VERSION = "2026-03-10"
REPOSITORY = "scnehaux/codex"
DEFAULT_BRANCH = "main"
QUALIFICATION_CONTEXT = "Governance Qualification"
QUALIFICATION_APP_ID = 15368
QUALIFICATION_APP_SLUG = "github-actions"
PINNED_AUTHORITY_REVISION = "23b05a855419b86b61b0c9266805bb66b143c366"
PINNED_EVALUATOR_BLOB = "ab2f152c21bd6d6f22df21172c4d027035ff8c11"
MAX_RESPONSE_BYTES = 4_000_000
PAGE_SIZE = 100
MAX_CHANGED_FILE_RECORDS = 2_000

# Conservative surfaces not yet represented by the source-pinned Stage 3b
# classifier. Touching one fails closed at the runtime layer until a later
# evaluator re-promotion incorporates the expanded classifier.
RUNTIME_CRITICAL_EXACT = {
    "Makefile",
    "constraints.txt",
    "conftest.py",
    "pyproject.toml",
}
RUNTIME_CRITICAL_PREFIXES = (
    "engine/control/",
    "generators/",
    "integrations/github-governance-evaluator/",
    "scripts/",
)

_PULL_RE = re.compile(r"/repos/scnehaux/codex/pulls/[1-9][0-9]*")
_FILES_RE = re.compile(r"/repos/scnehaux/codex/pulls/[1-9][0-9]*/files")
_CHECKS_RE = re.compile(
    r"/repos/scnehaux/codex/commits/[0-9a-f]{40}/check-runs"
)


class RuntimeBoundaryError(Exception):
    """Fixed, operator-safe runtime boundary failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _validate_query(path: str, query: dict[str, Any] | None) -> str:
    if query is None:
        query = {}
    if not isinstance(query, dict):
        raise RuntimeBoundaryError("api-query", "Invalid GitHub API query.")
    if _PULL_RE.fullmatch(path):
        if query:
            raise RuntimeBoundaryError("api-query", "Pull metadata request cannot carry a query.")
    elif _FILES_RE.fullmatch(path):
        if set(query) != {"per_page", "page"}:
            raise RuntimeBoundaryError("api-query", "Pull files request requires bounded pagination.")
        if query["per_page"] != PAGE_SIZE or type(query["page"]) is not int or not 1 <= query["page"] <= 21:
            raise RuntimeBoundaryError("api-query", "Pull files pagination is outside the supported bounds.")
    elif _CHECKS_RE.fullmatch(path):
        if query != {
            "check_name": QUALIFICATION_CONTEXT,
            "filter": "latest",
            "per_page": PAGE_SIZE,
        }:
            raise RuntimeBoundaryError("api-query", "Qualification request must use the fixed check context and latest filter.")
    else:
        raise RuntimeBoundaryError("api-path", "GitHub API path is outside the read-only collector allowlist.")
    return "?" + urlencode(query) if query else ""


def api_get(path: str, query: dict[str, Any] | None = None) -> Any:
    """GET one bounded GitHub public-API resource; no credentials and no redirects."""
    if not isinstance(path, str) or not path.startswith("/repos/scnehaux/codex/"):
        raise RuntimeBoundaryError("api-path", "GitHub API path is outside the bound repository.")
    suffix = _validate_query(path, query)
    request = Request(
        API_ROOT + path + suffix,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": "scnehaux-governance-facts/0.1",
        },
        method="GET",
    )
    try:
        with build_opener(NoRedirect()).open(request, timeout=20) as response:
            if response.status != 200:
                raise RuntimeBoundaryError(
                    "api-status", "Unexpected GitHub API status; collection stopped."
                )
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        status = exc.code
        exc.close()
        messages = {
            403: "GitHub denied the public read or rate limit is exhausted.",
            404: "GitHub could not find the bound pull request, commit, or check data.",
        }
        raise RuntimeBoundaryError(
            f"github-http-{status}",
            messages.get(status, "GitHub public API request failed; no redirect or retry was attempted."),
        ) from None
    except (URLError, TimeoutError, OSError, HTTPException):
        raise RuntimeBoundaryError(
            "network-error",
            "Secure read-only connection to api.github.com failed; do not disable TLS verification.",
        ) from None
    if len(raw) > MAX_RESPONSE_BYTES:
        raise RuntimeBoundaryError("api-response-size", "GitHub API response exceeded the supported size.")
    try:
        return json.loads(raw)
    except (ValueError, UnicodeError):
        raise RuntimeBoundaryError("api-json", "GitHub API returned invalid JSON.") from None


def _require_mapping(value: object, code: str, message: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RuntimeBoundaryError(code, message)
    return value


def _require_positive_int(value: object, code: str) -> int:
    if type(value) is not int or value <= 0:
        raise RuntimeBoundaryError(code, "Expected a positive integer from GitHub.")
    return value


def _git_blob_sha(path: Path) -> str:
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode):
            raise OSError
        raw = path.read_bytes()
    except OSError:
        raise RuntimeBoundaryError("evaluator-source", "Pinned evaluator source is missing or not a regular file.") from None
    if len(raw) > 1_000_000:
        raise RuntimeBoundaryError("evaluator-source", "Pinned evaluator source exceeds the supported size.")
    header = f"blob {len(raw)}\0".encode("ascii")
    return sha1(header + raw).hexdigest()


def load_promotion() -> dict[str, Any]:
    path = Path(__file__).resolve().with_name("promotion.json")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        raise RuntimeBoundaryError("promotion-contract", "Promotion contract is unreadable or invalid.") from None
    expected = {"schema_version", "repository", "authority_source_revision", "promotion", "runtime"}
    if not isinstance(data, dict) or set(data) != expected:
        raise RuntimeBoundaryError("promotion-contract", "Promotion contract fields drifted.")
    if data.get("schema_version") != 1 or data.get("repository") != REPOSITORY:
        raise RuntimeBoundaryError("promotion-contract", "Promotion contract identity drifted.")
    if data.get("authority_source_revision") != PINNED_AUTHORITY_REVISION:
        raise RuntimeBoundaryError("promotion-contract", "Runtime refuses an unreviewed evaluator source revision.")
    if data.get("promotion") != {
        "mode": "privileged-explicit",
        "state": "source-pinned",
        "candidate_may_select_effective_revision": False,
    }:
        raise RuntimeBoundaryError("promotion-contract", "Source-promotion semantics drifted.")
    if data.get("runtime") != {
        "execution_location": "external",
        "exported_copy_required": True,
        "facts_provenance_verified": False,
        "publish_enabled": False,
        "authority_binding_advanced": False,
        "effective_enforcement_proven": False,
    }:
        raise RuntimeBoundaryError("promotion-contract", "Runtime activation claims advanced before proof.")
    return data


def load_pinned_evaluator():
    """Verify promoted source identity before executing trusted evaluator code."""
    load_promotion()
    path = Path(__file__).resolve().with_name("evaluator.py")
    if _git_blob_sha(path) != PINNED_EVALUATOR_BLOB:
        raise RuntimeBoundaryError(
            "evaluator-blob-mismatch",
            "Local evaluator.py does not match the exact blob from the promoted authority revision.",
        )
    name = "_scnehaux_promoted_governance_evaluator"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeBoundaryError("evaluator-load", "Pinned evaluator module cannot be loaded.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise RuntimeBoundaryError("evaluator-load", "Pinned evaluator module failed to load; details suppressed.") from None
    return module


def ensure_exported_runtime() -> None:
    """Credential-free still does not mean candidate-controlled source is authority."""
    source = Path(__file__).resolve()
    if any((parent / ".git").exists() for parent in source.parents):
        raise RuntimeBoundaryError(
            "runtime-checkout",
            "Export a reviewed runtime copy outside every Git checkout before collecting authority facts.",
        )


def is_runtime_critical(path: str) -> bool:
    return path in RUNTIME_CRITICAL_EXACT or path.startswith(RUNTIME_CRITICAL_PREFIXES)


def collect_candidate(
    pull_request: int,
    evaluator,
    get: Callable[[str, dict[str, Any] | None], Any] = api_get,
) -> tuple[Any, dict[str, Any]]:
    if type(pull_request) is not int or pull_request <= 0:
        raise RuntimeBoundaryError("pull-request", "Pull request number must be a positive integer.")
    raw = get(f"/repos/{REPOSITORY}/pulls/{pull_request}", None)
    pr = _require_mapping(raw, "pull-shape", "GitHub pull request response must be an object.")
    if pr.get("number") != pull_request or pr.get("state") != "open":
        raise RuntimeBoundaryError("pull-identity", "Runtime evaluates only the exact open pull request requested.")
    base = _require_mapping(pr.get("base"), "pull-base", "Pull request base identity is missing.")
    head = _require_mapping(pr.get("head"), "pull-head", "Pull request head identity is missing.")
    base_repo = _require_mapping(base.get("repo"), "pull-base-repo", "Pull request base repository is missing.")
    head_repo = _require_mapping(head.get("repo"), "pull-head-repo", "Pull request head repository is missing.")
    if base_repo.get("full_name") != REPOSITORY or head_repo.get("full_name") != REPOSITORY:
        raise RuntimeBoundaryError("pull-repository", "Both base and candidate must belong to the bound repository.")
    if base.get("ref") != DEFAULT_BRANCH:
        raise RuntimeBoundaryError("pull-base-ref", "Authority runtime evaluates only pull requests targeting main.")
    try:
        base_sha = evaluator.require_sha(base.get("sha"), "base-sha")
        head_sha = evaluator.require_sha(head.get("sha"), "head-sha")
    except evaluator.EvaluationError:
        raise RuntimeBoundaryError("pull-sha", "GitHub returned a malformed base or candidate SHA.") from None
    if base_sha == head_sha:
        raise RuntimeBoundaryError("pull-range", "Pull request base and head SHA must differ.")
    expected_records = _require_positive_int(pr.get("changed_files"), "pull-changed-files")
    if expected_records > MAX_CHANGED_FILE_RECORDS:
        raise RuntimeBoundaryError("pull-changed-files", "Pull request exceeds the supported changed-file bound.")

    records: list[dict[str, Any]] = []
    page = 1
    while len(records) < expected_records:
        payload = get(
            f"/repos/{REPOSITORY}/pulls/{pull_request}/files",
            {"per_page": PAGE_SIZE, "page": page},
        )
        if not isinstance(payload, list) or not payload:
            raise RuntimeBoundaryError("pull-files", "GitHub pull-file pagination ended before the declared count.")
        if any(not isinstance(item, dict) for item in payload):
            raise RuntimeBoundaryError("pull-files", "GitHub pull-file response contains an invalid record.")
        records.extend(payload)
        if len(records) > expected_records:
            raise RuntimeBoundaryError("pull-files", "GitHub pull-file count exceeds pull metadata.")
        page += 1
    if len(records) != expected_records:
        raise RuntimeBoundaryError("pull-files", "GitHub pull-file count does not match pull metadata.")

    touched: list[str] = []
    current_names: set[str] = set()
    for record in records:
        try:
            current = evaluator.validate_path(record.get("filename"))
        except evaluator.EvaluationError:
            raise RuntimeBoundaryError("pull-file-path", "GitHub returned an invalid changed path.") from None
        if current in current_names:
            raise RuntimeBoundaryError("pull-files", "GitHub returned duplicate changed-file records.")
        current_names.add(current)
        touched.append(current)
        previous = record.get("previous_filename")
        if record.get("status") == "renamed" and previous is None:
            raise RuntimeBoundaryError("pull-file-rename", "Renamed file is missing its previous path.")
        if previous is not None:
            try:
                touched.append(evaluator.validate_path(previous))
            except evaluator.EvaluationError:
                raise RuntimeBoundaryError("pull-file-path", "GitHub returned an invalid previous changed path.") from None

    changed_files = tuple(sorted(set(touched)))
    if not changed_files:
        raise RuntimeBoundaryError("pull-files", "Pull request has no inspectable touched paths.")
    manifest = evaluator.CandidateManifest(
        REPOSITORY,
        pull_request,
        base_sha,
        head_sha,
        changed_files,
    )
    return manifest, {
        "source": "github-pull-request-api",
        "pull_state": "open",
        "base_ref": DEFAULT_BRANCH,
        "api_changed_file_records": expected_records,
        "touched_paths": len(changed_files),
        "files_pages_read": page - 1,
        "identity_verified": True,
        "changed_files_verified": True,
    }


def collect_candidate_qualification(
    head_sha: str,
    get: Callable[[str, dict[str, Any] | None], Any] = api_get,
) -> tuple[str, dict[str, Any]]:
    payload = get(
        f"/repos/{REPOSITORY}/commits/{head_sha}/check-runs",
        {
            "check_name": QUALIFICATION_CONTEXT,
            "filter": "latest",
            "per_page": PAGE_SIZE,
        },
    )
    data = _require_mapping(payload, "qualification-shape", "Qualification response must be an object.")
    runs = data.get("check_runs")
    if type(data.get("total_count")) is not int or data["total_count"] != 1 or not isinstance(runs, list) or len(runs) != 1:
        raise RuntimeBoundaryError(
            "qualification-ambiguous",
            "Exactly one latest Governance Qualification check from the trusted source is required.",
        )
    run = _require_mapping(runs[0], "qualification-shape", "Qualification check record must be an object.")
    app = _require_mapping(run.get("app"), "qualification-source", "Qualification check source is missing.")
    owner = _require_mapping(app.get("owner"), "qualification-source", "Qualification App owner is missing.")
    if (
        run.get("name") != QUALIFICATION_CONTEXT
        or run.get("head_sha") != head_sha
        or type(app.get("id")) is not int
        or app["id"] != QUALIFICATION_APP_ID
        or app.get("slug") != QUALIFICATION_APP_SLUG
        or owner.get("login") != "github"
    ):
        raise RuntimeBoundaryError(
            "qualification-source",
            "Governance Qualification is not bound to the expected GitHub Actions App and candidate SHA.",
        )
    details_url = run.get("details_url")
    if not isinstance(details_url, str) or not details_url.startswith(
        f"https://github.com/{REPOSITORY}/actions/runs/"
    ):
        raise RuntimeBoundaryError("qualification-source", "Qualification details URL is outside the bound repository Actions run.")
    if run.get("status") != "completed":
        raise RuntimeBoundaryError("qualification-pending", "Governance Qualification has not completed yet.")
    conclusion = run.get("conclusion")
    if not isinstance(conclusion, str) or not conclusion:
        raise RuntimeBoundaryError("qualification-conclusion", "Completed qualification has no usable conclusion.")
    check_id = _require_positive_int(run.get("id"), "qualification-id")
    qualification = "pass" if conclusion == "success" else "fail"
    return qualification, {
        "source": "github-checks-api",
        "check_run_id": check_id,
        "name": QUALIFICATION_CONTEXT,
        "head_sha": head_sha,
        "status": "completed",
        "conclusion": conclusion,
        "app_id": QUALIFICATION_APP_ID,
        "app_slug": QUALIFICATION_APP_SLUG,
        "source_verified": True,
        "details_url": details_url,
    }


def collect_and_evaluate(
    pull_request: int,
    get: Callable[[str, dict[str, Any] | None], Any] = api_get,
) -> dict[str, Any]:
    evaluator = load_pinned_evaluator()
    manifest, candidate_evidence = collect_candidate(pull_request, evaluator, get)
    qualification, qualification_evidence = collect_candidate_qualification(manifest.head_sha, get)

    evaluator_protected = [path for path in manifest.changed_files if evaluator.is_protected(path)]
    runtime_only_protected = [
        path
        for path in manifest.changed_files
        if is_runtime_critical(path) and path not in evaluator_protected
    ]
    privileged = "not_required"
    facts = evaluator.EvaluationFacts(
        manifest.repository,
        manifest.pull_request,
        manifest.base_sha,
        manifest.head_sha,
        PINNED_AUTHORITY_REVISION,
        qualification,
        privileged,
    )
    try:
        evaluator_result = evaluator.evaluate(
            manifest,
            facts,
            PINNED_AUTHORITY_REVISION,
        )
    except evaluator.EvaluationError:
        raise RuntimeBoundaryError(
            "evaluator-rejected-collected-facts",
            "Pinned evaluator rejected independently collected facts; runtime stopped.",
        ) from None

    runtime_failures: list[str] = []
    if runtime_only_protected:
        runtime_failures.append("runtime-critical-mutation-requires-privileged-validation")
    decision = (
        "fail"
        if evaluator_result["governance_decision"] == "fail" or runtime_failures
        else "pass"
    )
    candidate_manifest = {
        "schema_version": 1,
        **asdict(manifest),
        "changed_files": list(manifest.changed_files),
    }
    collected_facts = {
        "schema_version": 1,
        **asdict(facts),
    }
    return {
        "schema_version": 1,
        "status": "runtime_evaluation_complete",
        "repository": manifest.repository,
        "pull_request": manifest.pull_request,
        "base_sha": manifest.base_sha,
        "candidate_sha": manifest.head_sha,
        "authority_source_revision": PINNED_AUTHORITY_REVISION,
        "runtime_source_promoted": False,
        "facts_collected_independently": True,
        "facts_provenance_verified": False,
        "candidate_manifest": candidate_manifest,
        "collected_facts": collected_facts,
        "candidate_evidence": candidate_evidence,
        "qualification_evidence": qualification_evidence,
        "runtime_only_protected_mutations": runtime_only_protected,
        "runtime_failure_reasons": runtime_failures,
        "evaluator_result": evaluator_result,
        "governance_decision": decision,
        "candidate_code_executed": False,
        "credentials_used": False,
        "publish_enabled": False,
        "authority_binding_advanced": False,
        "effective_enforcement_proven": False,
        "notice": (
            "Facts were collected independently through fixed read-only GitHub endpoints, but this runtime source is not yet promoted. "
            "Do not publish Codex Governance Authority from this result. Protected mutations also remain fail-closed until privileged validation has an independently verified source."
        ),
    }


def blocked(exc: RuntimeBoundaryError) -> dict[str, Any]:
    return {
        "status": "blocked",
        "code": exc.code,
        "message": str(exc),
        "governance_decision": "not_evaluated",
        "facts_provenance_verified": False,
        "publish_enabled": False,
        "authority_binding_advanced": False,
        "effective_enforcement_proven": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pull-request", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        ensure_exported_runtime()
        result = collect_and_evaluate(args.pull_request)
    except RuntimeBoundaryError as exc:
        print(json.dumps(blocked(exc), sort_keys=True))
        return 1
    except KeyboardInterrupt:
        print(
            json.dumps(
                {
                    "status": "blocked",
                    "code": "interrupted",
                    "message": "Read-only collection was interrupted.",
                    "governance_decision": "not_evaluated",
                    "publish_enabled": False,
                    "effective_enforcement_proven": False,
                },
                sort_keys=True,
            )
        )
        return 130
    except Exception:
        print(
            json.dumps(
                {
                    "status": "blocked",
                    "code": "unexpected-local-error",
                    "message": "Unexpected runtime error; details suppressed.",
                    "governance_decision": "not_evaluated",
                    "publish_enabled": False,
                    "effective_enforcement_proven": False,
                },
                sort_keys=True,
            )
        )
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["governance_decision"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
