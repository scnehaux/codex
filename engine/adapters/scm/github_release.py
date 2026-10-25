"""GitHub readback adapter for an independently bound Governance release."""

from __future__ import annotations

import json
import os
from typing import Callable
from urllib.request import HTTPRedirectHandler, Request, build_opener

from engine.control.governance.release import ReleaseError


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ReleaseError(message)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ReleaseError("provider redirect refused")


def read_github(path: str) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    request = Request("https://api.github.com" + path, headers=headers, method="GET")
    with build_opener(_NoRedirect()).open(request, timeout=30) as response:
        raw = response.read(1_000_001)
    _require(len(raw) <= 1_000_000, "provider response too large")
    value = json.loads(raw)
    _require(isinstance(value, dict), "provider response must be an object")
    return value


def verify_publication(
    expected: dict, read_provider: Callable[[str], dict] | None = None
) -> str:
    """Check actual GitHub App, merged PR and Actions evidence; return its merge SHA."""
    read = read_github if read_provider is None else read_provider
    repository = expected["repository"]
    identity = expected["authority"]["identity"]["declaration"]
    _require(
        identity["candidate_repository"] == repository
        and type(identity["github_app_id"]) is int
        and identity["github_app_id"] > 0
        and isinstance(identity["authority_check_context"], str)
        and bool(identity["authority_check_context"]),
        "Authority publisher identity",
    )
    _require(
        identity["authority_check_context"] == expected["authority_context"],
        "source/Authority check context mismatch",
    )
    record = expected["authority"]["record"]
    candidate = record["candidate"]
    check = read(f"/repos/{repository}/check-runs/{record['check_run_id']}")
    _require(
        check["id"] == record["check_run_id"]
        and check["name"] == identity["authority_check_context"]
        and check["head_sha"] == expected["source_commit"]
        and check["status"] == "completed"
        and check["conclusion"] == "success"
        and check["app"]["id"] == identity["github_app_id"],
        "Authority provider check mismatch",
    )
    pr = read(f"/repos/{repository}/pulls/{candidate['pull_request']}")
    _require(
        pr["merged"] is True
        and pr["head"]["sha"] == candidate["head_sha"]
        and pr["base"]["sha"] == candidate["base_sha"]
        and pr["base"]["ref"] == "main"
        and pr["base"]["repo"]["full_name"] == repository,
        "release PR not merged with exact candidate",
    )
    qualification = read(
        f"/repos/{repository}/commits/{expected['source_commit']}/check-runs?filter=latest&per_page=100"
    )
    _require(
        any(
            c["name"] == expected["qualification_context"]
            and c["head_sha"] == expected["source_commit"]
            and c["status"] == "completed"
            and c["conclusion"] == "success"
            and c["app"]["id"] == 15368
            for c in qualification["check_runs"]
        ),
        "exact source qualification missing",
    )
    return pr["merge_commit_sha"]
