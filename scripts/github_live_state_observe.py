from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.adapters.scm.github_live import find_ruleset_summary, observe_github_state
from engine.control.governance.scm_observer import evidence_dict
from engine.control.governance.scm_policy import assert_scm_enforcement_policy


API = "https://api.github.com"
REMOTE_RE = re.compile(
    r"(?:github\.com[:/])(?P<repo>[^/\s]+/[^/\s]+?)(?:\.git)?$",
    re.I,
)


def _repository_from_origin() -> str:
    value = subprocess.check_output(
        ["git", "remote", "get-url", "origin"],
        cwd=ROOT,
        text=True,
    ).strip()
    match = REMOTE_RE.search(value)
    if not match:
        raise RuntimeError(f"cannot resolve GitHub repository from origin: {value!r}")
    return match.group("repo")


def _get_json(
    url: str,
    token: str | None,
) -> tuple[Any | None, str | None]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "scnehaux-codex-live-state-observer",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8")), None
    except HTTPError as exc:
        return None, f"HTTP {exc.code}: {exc.reason}"
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        return None, str(exc)


def _revision(repository: str, token: str | None) -> str:
    payload, error = _get_json(
        f"{API}/repos/{repository}/git/ref/heads/main",
        token,
    )
    if error or not isinstance(payload, dict):
        return "unknown"
    obj = payload.get("object")
    if not isinstance(obj, dict):
        return "unknown"
    sha = obj.get("sha")
    return sha if isinstance(sha, str) and sha else "unknown"


def observe(repository: str, token: str | None):
    policy = assert_scm_enforcement_policy(ROOT)
    revision = _revision(repository, token)

    rulesets, rulesets_error = _get_json(
        f"{API}/repos/{repository}/rulesets",
        token,
    )

    detail = None
    if rulesets_error is None and rulesets is not None:
        try:
            summary = find_ruleset_summary(rulesets)
        except ValueError as exc:
            rulesets_error = str(exc)
            summary = None
        if summary is not None:
            ruleset_id = summary.get("id")
            if isinstance(ruleset_id, int):
                detail, detail_error = _get_json(
                    f"{API}/repos/{repository}/rulesets/{ruleset_id}",
                    token,
                )
                if detail_error:
                    rulesets_error = f"ruleset detail unavailable: {detail_error}"

    _, branch_error = _get_json(
        f"{API}/repos/{repository}/branches/main/protection",
        token,
    )

    return observe_github_state(
        repository=repository,
        observed_revision=revision,
        policy=policy,
        rulesets_payload=rulesets,
        ruleset_detail=detail,
        rulesets_error=rulesets_error,
        branch_protection_error=branch_error,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only GitHub live SCM state observer",
    )
    parser.add_argument("--repository")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    repository = args.repository or _repository_from_origin()
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    evidence = observe(repository, token)

    if args.as_json:
        print(json.dumps(evidence_dict(evidence), indent=2, sort_keys=True))
        return 0

    print("[PASS] GitHub live-state observation completed")
    print(f"  provider: {evidence.provider}")
    print(f"  repository: {evidence.repository}")
    print(f"  observed revision: {evidence.observed_revision}")
    print(f"  observation: {evidence.observation_state.upper()}")
    print(f"  desired ruleset: {evidence.installed_state.upper()}")
    print(f"  provider enforcement state: {evidence.enforcement_state.upper()}")
    print(f"  drift: {evidence.drift_state.upper()}")
    print("  behavioral enforcement proof: NOT CLAIMED")
    for note in evidence.notes:
        print(f"  note: {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
