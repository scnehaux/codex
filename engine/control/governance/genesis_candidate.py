from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Callable, Mapping, Sequence

import yaml

from engine.control.governance.genesis import (
    GitResult,
    validate_candidate_paths,
    validate_gdc_snapshot,
)


@dataclass(frozen=True, slots=True)
class GenesisCandidateFinding:
    code: str
    path: str
    message: str


@dataclass(frozen=True, slots=True)
class GenesisCandidateReport:
    staged_files: tuple[str, ...]
    tree_sha: str | None
    findings: tuple[GenesisCandidateFinding, ...]

    @property
    def ok(self) -> bool:
        return not self.findings


GitRunner = Callable[[Sequence[str]], GitResult]


def _default_git_runner(repo_root: Path) -> GitRunner:
    def run(args: Sequence[str]) -> GitResult:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="strict",
        )
        return GitResult(
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    return run


def _normalize(path: str) -> str:
    return path.replace("\\", "/").removeprefix("./")


def _load_manifest(root: Path) -> Mapping[str, object]:
    path = root / "00-governance" / "bootstrap-manifest.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ValueError("bootstrap manifest must be a mapping")

    return data


def _lines(result: GitResult) -> tuple[str, ...]:
    return tuple(
        sorted(
            _normalize(line.strip())
            for line in result.stdout.splitlines()
            if line.strip()
        )
    )


def audit_genesis_commit_candidate(
    repo_root: str | Path,
    *,
    git_runner: GitRunner | None = None,
) -> GenesisCandidateReport:
    root = Path(repo_root).resolve()
    git = git_runner or _default_git_runner(root)
    findings: list[GenesisCandidateFinding] = []

    try:
        manifest = _load_manifest(root)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return GenesisCandidateReport(
            staged_files=(),
            tree_sha=None,
            findings=(
                GenesisCandidateFinding(
                    code="bootstrap-manifest-invalid",
                    path="00-governance/bootstrap-manifest.yaml",
                    message=str(exc),
                ),
            ),
        )

    head = git(["rev-parse", "--verify", "HEAD"])
    if head.returncode == 0:
        findings.append(
            GenesisCandidateFinding(
                code="genesis-already-exists",
                path=".",
                message=(
                    "Genesis commit qualification is only valid while HEAD "
                    "is unborn"
                ),
            )
        )

    canonical_branch = manifest.get("canonical_branch")
    branch = git(["branch", "--show-current"])
    if branch.returncode != 0:
        findings.append(
            GenesisCandidateFinding(
                code="branch-resolution-failed",
                path=".",
                message="cannot resolve current Git branch",
            )
        )
    elif branch.stdout.strip() != canonical_branch:
        findings.append(
            GenesisCandidateFinding(
                code="canonical-branch-mismatch",
                path=".",
                message=(
                    f"Genesis must be committed on {canonical_branch!r}, "
                    f"found {branch.stdout.strip()!r}"
                ),
            )
        )

    staged = git(["ls-files", "--cached"])
    if staged.returncode != 0:
        findings.append(
            GenesisCandidateFinding(
                code="index-enumeration-failed",
                path=".",
                message="cannot enumerate Git index",
            )
        )
        staged_files: tuple[str, ...] = ()
    else:
        staged_files = _lines(staged)

    if not staged_files:
        findings.append(
            GenesisCandidateFinding(
                code="empty-genesis-index",
                path=".",
                message="Genesis index is empty; stage the candidate tree first",
            )
        )

    untracked = git(["ls-files", "--others", "--exclude-standard"])
    if untracked.returncode != 0:
        findings.append(
            GenesisCandidateFinding(
                code="untracked-enumeration-failed",
                path=".",
                message="cannot enumerate untracked files",
            )
        )
    else:
        for path in _lines(untracked):
            findings.append(
                GenesisCandidateFinding(
                    code="unstaged-untracked-file",
                    path=path,
                    message="candidate file exists outside the staged Genesis tree",
                )
            )

    unstaged = git(["diff", "--name-only"])
    if unstaged.returncode != 0:
        findings.append(
            GenesisCandidateFinding(
                code="unstaged-diff-failed",
                path=".",
                message="cannot inspect unstaged worktree mutations",
            )
        )
    else:
        for path in _lines(unstaged):
            findings.append(
                GenesisCandidateFinding(
                    code="unstaged-worktree-mutation",
                    path=path,
                    message="working tree differs from staged Genesis candidate",
                )
            )

    for message in validate_candidate_paths(staged_files, manifest):
        code = (
            "forbidden-architecture-path"
            if message.startswith("forbidden architecture path")
            else "genesis-path-outside-allowlist"
        )
        findings.append(
            GenesisCandidateFinding(
                code=code,
                path=".",
                message=message,
            )
        )

    governance = manifest.get("governance_control_plane")
    required = (
        governance.get("required_baseline_ids", [])
        if isinstance(governance, dict)
        else []
    )

    gdc_documents: dict[str, str] = {}

    if isinstance(required, list):
        for doc_id in required:
            matches = [
                path
                for path in staged_files
                if path.startswith(f"00-governance/{doc_id}-")
                and path.endswith(".md")
            ]

            if len(matches) != 1:
                continue

            path = matches[0]
            shown = git(["show", f":{path}"])

            if shown.returncode != 0:
                findings.append(
                    GenesisCandidateFinding(
                        code="staged-document-read-failed",
                        path=path,
                        message="cannot read required governance document from index",
                    )
                )
                continue

            gdc_documents[path] = shown.stdout

    for message in validate_gdc_snapshot(gdc_documents, manifest):
        findings.append(
            GenesisCandidateFinding(
                code="staged-governance-baseline-invalid",
                path="00-governance",
                message=message,
            )
        )

    tree_sha: str | None = None

    if not findings:
        tree = git(["write-tree"])
        if tree.returncode != 0:
            findings.append(
                GenesisCandidateFinding(
                    code="staged-tree-write-failed",
                    path=".",
                    message="cannot materialize staged Genesis tree object",
                )
            )
        else:
            candidate = tree.stdout.strip()
            if len(candidate) != 40:
                findings.append(
                    GenesisCandidateFinding(
                        code="staged-tree-sha-invalid",
                        path=".",
                        message="git write-tree did not return a 40-hex tree SHA",
                    )
                )
            else:
                tree_sha = candidate

    return GenesisCandidateReport(
        staged_files=staged_files,
        tree_sha=tree_sha,
        findings=tuple(findings),
    )


def assert_genesis_commit_candidate(
    repo_root: str | Path,
    *,
    git_runner: GitRunner | None = None,
) -> GenesisCandidateReport:
    report = audit_genesis_commit_candidate(
        repo_root,
        git_runner=git_runner,
    )

    if report.findings:
        raise RuntimeError(
            "Genesis commit candidate qualification failed:\n  - "
            + "\n  - ".join(
                f"[{finding.code}] {finding.path}: {finding.message}"
                for finding in report.findings
            )
        )

    return report
