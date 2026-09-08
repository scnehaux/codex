#!/usr/bin/env python3
"""Deterministic, offline staging evaluator for Codex SCM governance.

This module deliberately performs no network access, reads no credentials, and
publishes no GitHub check. Candidate state and caller-supplied evaluation facts
are bounded data. The engine validates exact identity binding, applies deterministic
pass/fail policy, and keeps publication and authority promotion disabled.
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
MAX_FACTS_BYTES = 256_000
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
        data = load_json_object(path, MAX_MANIFEST_BYTES, "manifest")
        expected = {
            "schema_version",
            "repository",
            "pull_request",
            "base_sha",
            "head_sha",
            "changed_files",
        }
        if set(data) != expected:
            raise EvaluationError(
                "manifest-schema",
                "Candidate manifest fields do not match schema version 1.",
            )
        if type(data["schema_version"]) is not int or data["schema_version"] != 1:
            raise EvaluationError(
                "manifest-version", "Unsupported candidate manifest schema version."
            )
        repository = data["repository"]
        if repository != REPOSITORY:
            raise EvaluationError(
                "repository-mismatch",
                "Candidate repository does not match the bound repository.",
            )
        pull_request = require_positive_int(data["pull_request"], "pull-request")
        base_sha = require_sha(data["base_sha"], "base-sha")
        head_sha = require_sha(data["head_sha"], "head-sha")
        if base_sha == head_sha:
            raise EvaluationError(
                "candidate-range", "Base and candidate SHAs must differ."
            )
        files = data["changed_files"]
        if not isinstance(files, list) or not files or len(files) > MAX_CHANGED_FILES:
            raise EvaluationError(
                "changed-files", "Changed files must be a non-empty bounded list."
            )
        normalized = tuple(validate_path(item) for item in files)
        if list(normalized) != sorted(normalized) or len(set(normalized)) != len(
            normalized
        ):
            raise EvaluationError(
                "changed-files-order",
                "Changed files must be unique and lexicographically sorted.",
            )
        return cls(repository, pull_request, base_sha, head_sha, normalized)


@dataclass(frozen=True)
class EvaluationFacts:
    repository: str
    pull_request: int
    base_sha: str
    head_sha: str
    authority_source_revision: str
    candidate_qualification: str
    privileged_validation: str

    @classmethod
    def load(cls, path: Path) -> EvaluationFacts:
        data = load_json_object(path, MAX_FACTS_BYTES, "facts")
        expected = {
            "schema_version",
            "repository",
            "pull_request",
            "base_sha",
            "head_sha",
            "authority_source_revision",
            "candidate_qualification",
            "privileged_validation",
        }
        if set(data) != expected:
            raise EvaluationError(
                "facts-schema",
                "Evaluation facts fields do not match schema version 1.",
            )
        if type(data["schema_version"]) is not int or data["schema_version"] != 1:
            raise EvaluationError(
                "facts-version", "Unsupported evaluation facts schema version."
            )
        repository = data["repository"]
        if repository != REPOSITORY:
            raise EvaluationError(
                "facts-repository-mismatch",
                "Evaluation facts repository does not match the bound repository.",
            )
        pull_request = require_positive_int(data["pull_request"], "facts-pull-request")
        base_sha = require_sha(data["base_sha"], "facts-base-sha")
        head_sha = require_sha(data["head_sha"], "facts-head-sha")
        revision = require_sha(
            data["authority_source_revision"], "facts-authority-source-revision"
        )
        qualification = data["candidate_qualification"]
        if qualification not in {"pass", "fail"}:
            raise EvaluationError(
                "candidate-qualification",
                "Candidate qualification must be exactly pass or fail.",
            )
        privileged = data["privileged_validation"]
        if privileged not in {"pass", "fail", "not_required"}:
            raise EvaluationError(
                "privileged-validation",
                "Privileged validation must be pass, fail, or not_required.",
            )
        return cls(
            repository,
            pull_request,
            base_sha,
            head_sha,
            revision,
            qualification,
            privileged,
        )


def load_json_object(path: Path, limit: int, prefix: str) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            raw = handle.read(limit + 1)
    except OSError:
        raise EvaluationError(
            f"{prefix}-unreadable", f"{prefix.capitalize()} input is unreadable."
        ) from None
    if len(raw) > limit:
        raise EvaluationError(
            f"{prefix}-too-large", f"{prefix.capitalize()} input exceeds the supported size."
        )
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeError):
        raise EvaluationError(
            f"{prefix}-invalid-json",
            f"{prefix.capitalize()} input must be valid UTF-8 JSON.",
        ) from None
    if not isinstance(data, dict):
        raise EvaluationError(
            f"{prefix}-schema", f"{prefix.capitalize()} input must be a JSON object."
        )
    return data


def require_positive_int(value: object, code: str) -> int:
    if type(value) is not int or value <= 0:
        raise EvaluationError(code, "Value must be a positive integer.")
    return value


def require_sha(value: object, code: str) -> str:
    if (
        not isinstance(value, str)
        or SHA_RE.fullmatch(value) is None
        or value == "0" * 40
    ):
        raise EvaluationError(
            code, "Use an exact nonzero lowercase 40-character commit SHA."
        )
    return value


def validate_path(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > 4096:
        raise EvaluationError(
            "changed-path", "Changed paths must be bounded non-empty strings."
        )
    if value.startswith(("/", "\\")) or "\\" in value or "\x00" in value:
        raise EvaluationError(
            "changed-path", "Changed paths must be repository-relative POSIX paths."
        )
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise EvaluationError(
            "changed-path", "Changed paths may not contain empty or traversal segments."
        )
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise EvaluationError(
            "changed-path", "Changed paths may not contain control characters."
        )
    return value


def is_protected(path: str) -> bool:
    return path in PROTECTED_EXACT or path.startswith(PROTECTED_PREFIXES)


def bind_inputs(
    manifest: CandidateManifest,
    facts: EvaluationFacts,
    authority_source_revision: str,
) -> str:
    revision = require_sha(authority_source_revision, "authority-source-revision")
    if revision == manifest.head_sha:
        raise EvaluationError(
            "candidate-as-authority",
            "Candidate revision cannot be used as the effective authority revision.",
        )
    expected = (
        manifest.repository,
        manifest.pull_request,
        manifest.base_sha,
        manifest.head_sha,
        revision,
    )
    observed = (
        facts.repository,
        facts.pull_request,
        facts.base_sha,
        facts.head_sha,
        facts.authority_source_revision,
    )
    if observed != expected:
        raise EvaluationError(
            "facts-binding-mismatch",
            "Evaluation facts are not bound to the exact repository, PR, base, head, and authority revision.",
        )
    return revision


def evaluate(
    manifest: CandidateManifest,
    facts: EvaluationFacts,
    authority_source_revision: str,
) -> dict[str, Any]:
    revision = bind_inputs(manifest, facts, authority_source_revision)
    protected = [path for path in manifest.changed_files if is_protected(path)]
    if not protected and facts.privileged_validation != "not_required":
        raise EvaluationError(
            "privileged-validation-unexpected",
            "Unprotected candidates must declare privileged validation as not_required.",
        )

    failures: list[str] = []
    if facts.candidate_qualification != "pass":
        failures.append("candidate-qualification-failed")
    if protected:
        if facts.privileged_validation == "fail":
            failures.append("privileged-validation-failed")
        elif facts.privileged_validation == "not_required":
            failures.append("privileged-validation-missing")

    decision = "fail" if failures else "pass"
    return {
        "schema_version": 2,
        "status": "evaluation_complete",
        "decision_scope": "staging-offline",
        "repository": manifest.repository,
        "pull_request": manifest.pull_request,
        "base_sha": manifest.base_sha,
        "candidate_sha": manifest.head_sha,
        "authority_source_revision": revision,
        "check_context": CHECK_CONTEXT,
        "protected_mutations": protected,
        "requires_privileged_validation": bool(protected),
        "candidate_qualification": facts.candidate_qualification,
        "privileged_validation": facts.privileged_validation,
        "failure_reasons": failures,
        "governance_decision": decision,
        "facts_provenance_verified": False,
        "publish_enabled": False,
        "authority_promoted": False,
        "candidate_code_executed": False,
        "credentials_used": False,
        "effective_enforcement_proven": False,
        "notice": (
            "Deterministic staging decision only. Caller-supplied facts have no provenance proof here; "
            "the result cannot be published as Codex Governance Authority until a trusted promoted runtime collects them."
        ),
    }


def blocked(exc: EvaluationError) -> dict[str, Any]:
    return {
        "status": "blocked",
        "code": exc.code,
        "message": str(exc),
        "governance_decision": "not_evaluated",
        "publish_enabled": False,
        "effective_enforcement_proven": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-manifest", type=Path, required=True)
    parser.add_argument("--evaluation-facts", type=Path, required=True)
    parser.add_argument("--authority-source-revision", required=True)
    args = parser.parse_args(argv)
    try:
        manifest = CandidateManifest.load(args.candidate_manifest)
        facts = EvaluationFacts.load(args.evaluation_facts)
        result = evaluate(manifest, facts, args.authority_source_revision)
    except EvaluationError as exc:
        print(json.dumps(blocked(exc), sort_keys=True))
        return 1
    except Exception:
        print(
            json.dumps(
                {
                    "status": "blocked",
                    "code": "unexpected-local-error",
                    "message": "Unexpected local error; details suppressed.",
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
