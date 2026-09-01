from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Callable, Sequence

from engine.control.governance.genesis import GitResult
from engine.control.governance.mutation import (
    MutationFinding,
    is_governed_document_path,
    parse_versioned_document,
    validate_document_mutation,
)

GitRunner = Callable[[Sequence[str]], GitResult]

@dataclass(frozen=True, slots=True)
class CommittedMutationReport:
    base_ref: str
    merge_base: str | None
    head_ref: str
    checked_mutations: int
    findings: tuple[MutationFinding, ...]

    @property
    def ok(self) -> bool:
        return not self.findings


def _default_git_runner(repo_root: Path) -> GitRunner:
    def run(args: Sequence[str]) -> GitResult:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="strict",
        )
        return GitResult(result.returncode, result.stdout, result.stderr)
    return run


def _normalize(path: str) -> str:
    return path.replace("\\", "/").removeprefix("./")


def _show(git: GitRunner, ref: str, path: str, code: str):
    result = git(["show", f"{ref}:{path}"])
    if result.returncode != 0:
        return None, (MutationFinding(code, path, f"cannot read governed document from {ref}"),)
    return result.stdout, ()


def _parse_entry(raw: str):
    parts = tuple(part.strip() for part in raw.split("\t"))
    if len(parts) < 2:
        return None, (MutationFinding("invalid-committed-diff-entry", ".", f"cannot interpret git diff entry: {parts!r}"),)
    status = parts[0]
    if status.startswith("R"):
        if len(parts) != 3:
            return None, (MutationFinding("invalid-committed-rename-entry", ".", f"cannot interpret git rename entry: {parts!r}"),)
        return (status, _normalize(parts[1]), _normalize(parts[2])), ()
    if len(parts) != 2:
        return None, (MutationFinding("invalid-committed-diff-entry", ".", f"cannot interpret git diff entry: {parts!r}"),)
    path = _normalize(parts[1])
    return (status, path, path), ()


def audit_committed_mutation_integrity(
    repo_root: str | Path,
    *,
    base_ref: str,
    head_ref: str = "HEAD",
    git_runner: GitRunner | None = None,
) -> CommittedMutationReport:
    root = Path(repo_root).resolve()
    git = git_runner or _default_git_runner(root)

    if not isinstance(base_ref, str) or not base_ref.strip():
        return CommittedMutationReport(str(base_ref), None, head_ref, 0, (
            MutationFinding("mutation-base-ref-invalid", ".", "base_ref must be a non-empty Git ref"),
        ))
    if not isinstance(head_ref, str) or not head_ref.strip():
        return CommittedMutationReport(base_ref, None, str(head_ref), 0, (
            MutationFinding("mutation-head-ref-invalid", ".", "head_ref must be a non-empty Git ref"),
        ))

    merge = git(["merge-base", base_ref, head_ref])
    if merge.returncode != 0 or not merge.stdout.strip():
        return CommittedMutationReport(base_ref, None, head_ref, 0, (
            MutationFinding("mutation-merge-base-failed", ".", f"cannot resolve merge-base between {base_ref} and {head_ref}"),
        ))

    merge_base = merge.stdout.strip().splitlines()[0].strip()
    diff = git(["diff", "--name-status", "-M", merge_base, head_ref, "--"])
    if diff.returncode != 0:
        return CommittedMutationReport(base_ref, merge_base, head_ref, 0, (
            MutationFinding("committed-git-diff-failed", ".", "cannot resolve committed mutation delta"),
        ))

    findings: list[MutationFinding] = []
    checked = 0

    for raw in diff.stdout.splitlines():
        if not raw.strip():
            continue
        entry, entry_findings = _parse_entry(raw)
        findings.extend(entry_findings)
        if entry is None:
            continue

        status, old_path, new_path = entry
        governed_before = is_governed_document_path(old_path)
        governed_after = is_governed_document_path(new_path)
        if not governed_before and not governed_after:
            continue

        checked += 1

        if status.startswith("A"):
            text, read_findings = _show(git, head_ref, new_path, "committed-head-read-failed")
            findings.extend(read_findings)
            if text is not None:
                _, parse_findings = parse_versioned_document(new_path, text)
                findings.extend(parse_findings)
            continue

        if status.startswith("D"):
            text, read_findings = _show(git, merge_base, old_path, "committed-baseline-read-failed")
            findings.extend(read_findings)
            if text is not None:
                before, parse_findings = parse_versioned_document(old_path, text)
                findings.extend(parse_findings)
                if before is not None:
                    findings.append(MutationFinding(
                        "governed-document-deletion",
                        old_path,
                        "governed documents cannot be removed as a raw deletion; use an explicit lifecycle mutation",
                    ))
            continue

        old_text, old_read = _show(git, merge_base, old_path, "committed-baseline-read-failed")
        new_text, new_read = _show(git, head_ref, new_path, "committed-head-read-failed")
        findings.extend(old_read)
        findings.extend(new_read)
        if old_text is None or new_text is None:
            continue

        before, before_findings = parse_versioned_document(old_path, old_text)
        after, after_findings = parse_versioned_document(new_path, new_text)
        findings.extend(before_findings)
        findings.extend(after_findings)

        if before is None and after is None:
            continue
        if before is not None and after is None:
            findings.append(MutationFinding(
                "governed-metadata-removal",
                new_path,
                "mutation removed governed document metadata",
            ))
            continue
        if before is None:
            continue

        assert after is not None
        findings.extend(validate_document_mutation(before, after))

    return CommittedMutationReport(base_ref, merge_base, head_ref, checked, tuple(findings))


def assert_committed_mutation_integrity(
    repo_root: str | Path,
    *,
    base_ref: str,
    head_ref: str = "HEAD",
    git_runner: GitRunner | None = None,
) -> CommittedMutationReport:
    report = audit_committed_mutation_integrity(
        repo_root,
        base_ref=base_ref,
        head_ref=head_ref,
        git_runner=git_runner,
    )
    if report.findings:
        raise RuntimeError(
            "Committed mutation integrity audit failed:\n  - "
            + "\n  - ".join(
                f"[{f.code}] {f.path}: {f.message}" for f in report.findings
            )
        )
    return report
