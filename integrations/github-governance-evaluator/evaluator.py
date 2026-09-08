#!/usr/bin/env python3
"""Plan-only trusted evaluator skeleton for Codex SCM governance.

This module deliberately performs no network access and publishes no GitHub check.
It validates a candidate manifest as untrusted data, binds it to an explicit
trusted evaluator source revision, and identifies governance-sensitive mutations
that require privileged validation before any future authority decision.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

SHA_RE = re.compile(r"[0-9a-f]{40}")
REPOSITORY = "scnehaux/codex"
CHECK_CONTEXT = "Codex Governance Authority"
MAX_MANIFEST_BYTES = 1_000_000
MAX_CHANGED_FILES = 2_000

PROTECTED_EXACT = {
    ".github/CODEOWNERS",
    ".github/workflows/governance.yml",
    "scripts/github_policy_check.py",
}
PROTECTED_PREFIXES = (
    ".github/workflows/",
    "engine/adapters/scm/",
    "engine/control/governance/",
    "governance/github/",
    "governance/scm/",
)


class EvaluationError(Exception):
    """Fail-closed evaluator input error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class CandidateManifest:
    repository: str
    pull_request: int
    base_sha: str
    head_sha: str
    changed_files: tuple[str, ...]

    @classmethod
    def load(cls, path: Path) -> CandidateManifest:
        try:
            with path.open("rb") as handle:
                raw = handle.read(MAX_MANIFEST_BYTES + 1)
        except OSError:
            raise EvaluationError("manifest-unreadable", "Candidate manifest is unreadable.") from None
        if len(raw) > MAX_MANIFEST_BYTES:
            raise EvaluationError("manifest-too-large", "Candidate manifest exceeds the supported size.")
        try:
            data = json.loads(raw)
        except (ValueError, UnicodeError):
            raise EvaluationError("manifest-invalid-json", "Candidate manifest must be valid UTF-8 JSON.") from None
        expected = {"schema_version", "repository", "pull_request", "base_sha", "head_sha", "changed_files"}
        if not isinstance(data, dict) or set(data) != expected:
            raise EvaluationError("manifest-schema", "Candidate manifest fields do not match schema version 1.")
        if type(data["schema_version"]) is not int or data["schema_version"] != 1:
            raise EvaluationError("manifest-version", "Unsupported candidate manifest schema version.")
        repository = data["repository"]
        if repository != REPOSITORY:
            raise EvaluationError("repository-mismatch", "Candidate repository does not match the bound repository.")
        pr = data["pull_request"]
        if type(pr) is not int or pr <= 0:
            raise EvaluationError("pull-request", "Pull request number must be a positive integer.")
        base_sha = require_sha(data["base_sha"], "base-sha")
        head_sha = require_sha(data["head_sha"], "head-sha")
        if base_sha == head_sha:
            raise EvaluationError("candidate-range", "Base and candidate SHAs must differ.")
        files = data["changed_files"]
        if not isinstance(files, list) or not files or len(files) > MAX_CHANGED_FILES:
            raise EvaluationError("changed-files", "Changed files must be a non-empty bounded list.")
        normalized = tuple(validate_path(item) for item in files)
        if list(normalized) != sorted(normalized) or len(set(normalized)) != len(normalized):
            raise EvaluationError("changed-files-order", "Changed files must be unique and lexicographically sorted.")
        return cls(repository, pr, base_sha, head_sha, normalized)


def require_sha(value: object, code: str) -> str:
    if not isinstance(value, str) or SHA_RE.fullmatch(value) is None or value == "0" * 40:
        raise EvaluationError(code, "Use an exact nonzero lowercase 40-character commit SHA.")
    return value


def validate_path(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > 4096:
        raise EvaluationError("changed-path", "Changed paths must be bounded non-empty strings.")
    if value.startswith(("/", "\\")) or "\\" in value or "\x00" in value:
        raise EvaluationError("changed-path", "Changed paths must be repository-relative POSIX paths.")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise EvaluationError("changed-path", "Changed paths may not contain empty or traversal segments.")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise EvaluationError("changed-path", "Changed paths may not contain control characters.")
    return value


def is_protected(path: str) -> bool:
    return path in PROTECTED_EXACT or path.startswith(PROTECTED_PREFIXES)


def build_plan(manifest: CandidateManifest, authority_source_revision: str) -> dict[str, Any]:
    revision = require_sha(authority_source_revision, "authority-source-revision")
    if revision == manifest.head_sha:
        raise EvaluationError(
            "candidate-as-authority",
            "Candidate revision cannot be used as the effective authority revision.",
        )
    protected = [path for path in manifest.changed_files if is_protected(path)]
    return {
        "schema_version": 1,
        "status": "evaluation_plan_ready",
        "repository": manifest.repository,
        "pull_request": manifest.pull_request,
        "base_sha": manifest.base_sha,
        "candidate_sha": manifest.head_sha,
        "authority_source_revision": revision,
        "check_context": CHECK_CONTEXT,
        "protected_mutations": protected,
        "requires_privileged_validation": bool(protected),
        "governance_decision": "not_evaluated",
        "publish_enabled": False,
        "authority_promoted": False,
        "candidate_code_executed": False,
        "credentials_used": False,
        "effective_enforcement_proven": False,
        "notice": "Plan only. This skeleton does not publish Codex Governance Authority or claim governance success.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-manifest", type=Path, required=True)
    parser.add_argument("--authority-source-revision", required=True)
    args = parser.parse_args(argv)
    try:
        manifest = CandidateManifest.load(args.candidate_manifest)
        plan = build_plan(manifest, args.authority_source_revision)
    except EvaluationError as exc:
        print(json.dumps({
            "status": "blocked",
            "code": exc.code,
            "message": str(exc),
            "governance_decision": "not_evaluated",
            "publish_enabled": False,
            "effective_enforcement_proven": False,
        }, sort_keys=True))
        return 1
    except Exception:
        print(json.dumps({
            "status": "blocked",
            "code": "unexpected-local-error",
            "message": "Unexpected local error; details suppressed.",
            "governance_decision": "not_evaluated",
            "publish_enabled": False,
            "effective_enforcement_proven": False,
        }, sort_keys=True))
        return 1
    print(json.dumps(plan, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
