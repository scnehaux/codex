from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
from typing import Callable, Iterable, Sequence

from engine.control.governance.genesis import (
    GitResult,
    parse_frontmatter,
)
from engine.core.governance.versioning import SemanticVersion


ARTIFACT_NAME_RE = re.compile(
    r"^(?:GDC|EAD|PAD|SAD|TDD|ADR|STD)-[A-Za-z0-9][A-Za-z0-9._-]*\.md$"
)
GOVERNED_ROOT_PREFIXES = tuple(f"{index:02d}-" for index in range(6))


@dataclass(frozen=True, slots=True)
class VersionedDocument:
    path: str
    document_id: str
    version: SemanticVersion
    status: str | None


@dataclass(frozen=True, slots=True)
class MutationFinding:
    code: str
    path: str
    message: str


@dataclass(frozen=True, slots=True)
class MutationReport:
    mode: str
    checked_documents: int
    findings: tuple[MutationFinding, ...]

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
    return path.replace("\\", "/").lstrip("./")


def is_governed_document_path(path: str) -> bool:
    normalized = _normalize(path)
    parts = normalized.split("/", 1)

    if len(parts) < 2:
        return False

    root = parts[0]
    return (
        root.startswith(GOVERNED_ROOT_PREFIXES)
        and normalized.lower().endswith(".md")
    )


def _looks_versioned(path: str, text: str) -> bool:
    name = Path(_normalize(path)).name
    if ARTIFACT_NAME_RE.fullmatch(name):
        return True

    if not text.startswith("---\n"):
        return False

    end = text.find("\n---", 4)
    if end == -1:
        return "doc_meta:" in text[:4096]

    return "doc_meta:" in text[4:end]


def parse_versioned_document(
    path: str,
    text: str,
) -> tuple[VersionedDocument | None, tuple[MutationFinding, ...]]:
    normalized = _normalize(path)

    if not is_governed_document_path(normalized):
        return None, ()

    if not _looks_versioned(normalized, text):
        return None, ()

    try:
        meta = parse_frontmatter(text)
    except ValueError as exc:
        return None, (
            MutationFinding(
                code="invalid-doc-meta",
                path=normalized,
                message=str(exc),
            ),
        )

    document_id = meta.get("id")
    version_raw = meta.get("version")
    status = meta.get("status")

    findings: list[MutationFinding] = []

    if not isinstance(document_id, str) or not document_id.strip():
        findings.append(
            MutationFinding(
                code="invalid-document-id",
                path=normalized,
                message="doc_meta.id must be a non-empty string",
            )
        )

    try:
        version = SemanticVersion.parse(version_raw)
    except (TypeError, ValueError) as exc:
        findings.append(
            MutationFinding(
                code="invalid-version",
                path=normalized,
                message=str(exc),
            )
        )
        version = None

    if findings:
        return None, tuple(findings)

    assert isinstance(document_id, str)
    assert version is not None

    return (
        VersionedDocument(
            path=normalized,
            document_id=document_id,
            version=version,
            status=status if isinstance(status, str) else None,
        ),
        (),
    )


def validate_document_mutation(
    before: VersionedDocument,
    after: VersionedDocument,
) -> tuple[MutationFinding, ...]:
    findings: list[MutationFinding] = []

    if before.document_id != after.document_id:
        findings.append(
            MutationFinding(
                code="document-id-mutation",
                path=after.path,
                message=(
                    f"document identity is immutable: "
                    f"{before.document_id} -> {after.document_id}"
                ),
            )
        )

    if after.version < before.version:
        findings.append(
            MutationFinding(
                code="version-regression",
                path=after.path,
                message=(
                    f"version regressed: {before.version} -> {after.version}"
                ),
            )
        )
    elif after.version == before.version:
        findings.append(
            MutationFinding(
                code="version-bump-required",
                path=after.path,
                message=(
                    "governed document mutation requires a strictly "
                    f"higher version than {before.version}"
                ),
            )
        )

    return tuple(findings)


def _candidate_paths(git: GitRunner) -> tuple[tuple[str, ...], tuple[MutationFinding, ...]]:
    result = git(
        [
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
        ]
    )
    if result.returncode != 0:
        return (), (
            MutationFinding(
                code="git-candidate-enumeration-failed",
                path=".",
                message="cannot enumerate repository candidate files",
            ),
        )

    return (
        tuple(
            sorted(
                _normalize(line.strip())
                for line in result.stdout.splitlines()
                if line.strip()
            )
        ),
        (),
    )


def _read_current(
    root: Path,
    path: str,
) -> tuple[str | None, tuple[MutationFinding, ...]]:
    target = root / path

    try:
        return target.read_text(encoding="utf-8"), ()
    except OSError as exc:
        return None, (
            MutationFinding(
                code="document-read-failed",
                path=path,
                message=str(exc),
            ),
        )


def _scan_current_documents(
    root: Path,
    paths: Iterable[str],
) -> tuple[
    dict[str, VersionedDocument],
    tuple[MutationFinding, ...],
]:
    documents: dict[str, VersionedDocument] = {}
    findings: list[MutationFinding] = []

    for path in paths:
        if not is_governed_document_path(path):
            continue

        text, read_findings = _read_current(root, path)
        findings.extend(read_findings)

        if text is None:
            continue

        document, parse_findings = parse_versioned_document(path, text)
        findings.extend(parse_findings)

        if document is None:
            continue

        existing = documents.get(document.document_id)
        if existing is not None:
            findings.append(
                MutationFinding(
                    code="duplicate-document-id",
                    path=path,
                    message=(
                        f"{document.document_id} already exists at "
                        f"{existing.path}"
                    ),
                )
            )
            continue

        documents[document.document_id] = document

    return documents, tuple(findings)


def _diff_entries(
    git: GitRunner,
) -> tuple[tuple[tuple[str, ...], ...], tuple[MutationFinding, ...]]:
    result = git(["diff", "--name-status", "-M", "HEAD"])

    if result.returncode != 0:
        return (), (
            MutationFinding(
                code="git-diff-failed",
                path=".",
                message="cannot resolve working-tree mutations against HEAD",
            ),
        )

    entries: list[tuple[str, ...]] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        entries.append(tuple(part.strip() for part in line.split("\t")))

    return tuple(entries), ()


def _show_head(
    git: GitRunner,
    path: str,
) -> tuple[str | None, tuple[MutationFinding, ...]]:
    result = git(["show", f"HEAD:{path}"])

    if result.returncode != 0:
        return None, (
            MutationFinding(
                code="baseline-read-failed",
                path=path,
                message="cannot read governed document from HEAD",
            ),
        )

    return result.stdout, ()


def _audit_post_genesis_mutations(
    root: Path,
    git: GitRunner,
) -> tuple[MutationFinding, ...]:
    entries, diff_findings = _diff_entries(git)
    findings: list[MutationFinding] = list(diff_findings)

    for entry in entries:
        if len(entry) < 2:
            findings.append(
                MutationFinding(
                    code="invalid-git-diff-entry",
                    path=".",
                    message=f"cannot interpret git diff entry: {entry!r}",
                )
            )
            continue

        status = entry[0]

        if status.startswith("R"):
            if len(entry) != 3:
                findings.append(
                    MutationFinding(
                        code="invalid-git-rename-entry",
                        path=".",
                        message=f"cannot interpret git rename entry: {entry!r}",
                    )
                )
                continue
            old_path = _normalize(entry[1])
            new_path = _normalize(entry[2])
        else:
            old_path = _normalize(entry[1])
            new_path = old_path

        if status.startswith("A"):
            continue

        if status.startswith("D"):
            if not is_governed_document_path(old_path):
                continue

            old_text, old_read = _show_head(git, old_path)
            findings.extend(old_read)
            if old_text is None:
                continue

            old_doc, old_parse = parse_versioned_document(
                old_path,
                old_text,
            )
            findings.extend(old_parse)

            if old_doc is not None:
                findings.append(
                    MutationFinding(
                        code="governed-document-deletion",
                        path=old_path,
                        message=(
                            "governed documents cannot be removed as a raw "
                            "deletion; use an explicit lifecycle mutation"
                        ),
                    )
                )
            continue

        if not (
            is_governed_document_path(old_path)
            or is_governed_document_path(new_path)
        ):
            continue

        old_text, old_read = _show_head(git, old_path)
        findings.extend(old_read)

        new_text, new_read = _read_current(root, new_path)
        findings.extend(new_read)

        if old_text is None or new_text is None:
            continue

        before, before_findings = parse_versioned_document(
            old_path,
            old_text,
        )
        after, after_findings = parse_versioned_document(
            new_path,
            new_text,
        )
        findings.extend(before_findings)
        findings.extend(after_findings)

        if before is None and after is None:
            continue

        if before is not None and after is None:
            findings.append(
                MutationFinding(
                    code="governed-metadata-removal",
                    path=new_path,
                    message=(
                        "mutation removed governed document metadata"
                    ),
                )
            )
            continue

        if before is None:
            continue

        assert after is not None
        findings.extend(validate_document_mutation(before, after))

    return tuple(findings)


def audit_version_mutation_integrity(
    repo_root: str | Path,
    *,
    git_runner: GitRunner | None = None,
) -> MutationReport:
    root = Path(repo_root).resolve()
    git = git_runner or _default_git_runner(root)

    candidate_paths, candidate_findings = _candidate_paths(git)
    documents, scan_findings = _scan_current_documents(
        root,
        candidate_paths,
    )

    findings: list[MutationFinding] = [
        *candidate_findings,
        *scan_findings,
    ]

    head = git(["rev-parse", "--verify", "HEAD"])

    if head.returncode != 0:
        mode = "pre-genesis"
    else:
        mode = "post-genesis"
        findings.extend(
            _audit_post_genesis_mutations(root, git)
        )

    return MutationReport(
        mode=mode,
        checked_documents=len(documents),
        findings=tuple(findings),
    )


def assert_version_mutation_integrity(
    repo_root: str | Path,
    *,
    git_runner: GitRunner | None = None,
) -> MutationReport:
    report = audit_version_mutation_integrity(
        repo_root,
        git_runner=git_runner,
    )

    if report.findings:
        raise RuntimeError(
            "Version/mutation integrity audit failed:\n  - "
            + "\n  - ".join(
                f"[{finding.code}] {finding.path}: {finding.message}"
                for finding in report.findings
            )
        )

    return report
