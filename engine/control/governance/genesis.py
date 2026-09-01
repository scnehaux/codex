from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
from typing import Callable, Iterable, Mapping, Sequence

import yaml


FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
VERSION_RE = re.compile(
    r"^(?P<major>0|[1-9][0-9]*)\.(?P<minor>0|[1-9][0-9]*)\.(?P<patch>0|[1-9][0-9]*)$"
)


@dataclass(frozen=True, slots=True)
class GitResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True, slots=True)
class GenesisIntegrityReport:
    mode: str
    candidate_files: tuple[str, ...]
    root_commit: str | None
    findings: tuple[str, ...]

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


def path_matches_contract(path: str, pattern: str) -> bool:
    candidate = _normalize(path)
    contract = _normalize(pattern)

    if contract.endswith("/**"):
        prefix = contract[:-3].rstrip("/")
        return candidate == prefix or candidate.startswith(prefix + "/")

    return candidate == contract


def parse_frontmatter(text: str) -> Mapping[str, object]:
    if not text.startswith("---\n"):
        raise ValueError("document is missing YAML frontmatter")

    end = text.find("\n---", 4)
    if end == -1:
        raise ValueError("document has unterminated YAML frontmatter")

    data = yaml.safe_load(text[4:end])
    if not isinstance(data, dict):
        raise ValueError("document frontmatter must be a mapping")

    meta = data.get("doc_meta")
    if not isinstance(meta, dict):
        raise ValueError("document frontmatter missing doc_meta mapping")

    return meta


def _manifest_findings(manifest: Mapping[str, object]) -> tuple[str, ...]:
    findings: list[str] = []

    if manifest.get("kind") != "governance-genesis":
        findings.append("bootstrap manifest kind must be governance-genesis")

    target = manifest.get("target_repository")
    branch = manifest.get("canonical_branch")
    if not isinstance(target, str) or not target.strip():
        findings.append("bootstrap target_repository must be non-empty")
    if not isinstance(branch, str) or not branch.strip():
        findings.append("bootstrap canonical_branch must be non-empty")

    source = manifest.get("source")
    if not isinstance(source, dict):
        findings.append("bootstrap source must be a mapping")
    else:
        source_repo = source.get("repository")
        source_ref = source.get("ref")
        source_commit = source.get("commit")
        if not isinstance(source_repo, str) or not source_repo.strip():
            findings.append("legacy source repository must be non-empty")
        if source_repo == target:
            findings.append("legacy source repository cannot equal target repository")
        if not isinstance(source_ref, str) or not source_ref.strip():
            findings.append("legacy source ref must be non-empty")
        if not isinstance(source_commit, str) or not FULL_SHA_RE.fullmatch(source_commit):
            findings.append("legacy source commit must be an immutable 40-hex SHA")

    contract = manifest.get("genesis_contract")
    if not isinstance(contract, dict):
        findings.append("bootstrap genesis_contract must be a mapping")
    else:
        if contract.get("root_commit_only") is not True:
            findings.append("genesis_contract.root_commit_only must be true")
        if contract.get("local_qualification_required") is not True:
            findings.append("genesis_contract.local_qualification_required must be true")
        if not isinstance(contract.get("allowed_paths"), list):
            findings.append("genesis_contract.allowed_paths must be a list")
        if not isinstance(contract.get("forbidden_architecture_paths"), list):
            findings.append("genesis_contract.forbidden_architecture_paths must be a list")

    provenance = manifest.get("provenance")
    if not isinstance(provenance, dict):
        findings.append("bootstrap provenance must be a mapping")
    elif provenance.get("architecture_artifacts_admitted_in_genesis") is not False:
        findings.append("architecture artifacts must not be admitted in Genesis")

    governance = manifest.get("governance_control_plane")
    if not isinstance(governance, dict):
        findings.append("governance_control_plane must be a mapping")
    else:
        if governance.get("lifecycle") != "draft":
            findings.append("Genesis governance lifecycle must remain draft")
        if governance.get("version_series") != "0.x.x":
            findings.append("Genesis governance version series must remain 0.x.x")
        if governance.get("architecture_admission") != "closed":
            findings.append("architecture admission must remain closed at Genesis")
        if not isinstance(governance.get("required_baseline_ids"), list):
            findings.append("required_baseline_ids must be a list")

    return tuple(findings)


def validate_candidate_paths(
    paths: Iterable[str],
    manifest: Mapping[str, object],
) -> tuple[str, ...]:
    contract = manifest.get("genesis_contract")
    if not isinstance(contract, dict):
        return ("bootstrap genesis_contract is unavailable",)

    allowed = contract.get("allowed_paths")
    forbidden = contract.get("forbidden_architecture_paths")

    if not isinstance(allowed, list) or not isinstance(forbidden, list):
        return ("bootstrap Genesis path policy is invalid",)

    findings: list[str] = []

    for raw in paths:
        path = _normalize(raw)

        if any(path_matches_contract(path, pattern) for pattern in forbidden):
            findings.append(f"forbidden architecture path present: {path}")
            continue

        if not any(path_matches_contract(path, pattern) for pattern in allowed):
            findings.append(f"path is outside Genesis allowlist: {path}")

    return tuple(findings)


def validate_gdc_snapshot(
    documents: Mapping[str, str],
    manifest: Mapping[str, object],
) -> tuple[str, ...]:
    governance = manifest.get("governance_control_plane")
    if not isinstance(governance, dict):
        return ("governance_control_plane is unavailable",)

    required_raw = governance.get("required_baseline_ids")
    if not isinstance(required_raw, list):
        return ("required_baseline_ids is unavailable",)

    required = tuple(str(item) for item in required_raw)
    findings: list[str] = []
    seen: dict[str, Mapping[str, object]] = {}

    for path, text in documents.items():
        try:
            meta = parse_frontmatter(text)
        except ValueError as exc:
            findings.append(f"{path}: {exc}")
            continue

        doc_id = meta.get("id")
        if not isinstance(doc_id, str):
            findings.append(f"{path}: doc_meta.id must be a string")
            continue

        if doc_id in seen:
            findings.append(f"duplicate required governance ID: {doc_id}")
            continue

        seen[doc_id] = meta

    for doc_id in sorted(set(required) - set(seen)):
        findings.append(f"required Genesis governance document missing: {doc_id}")

    for doc_id in sorted(set(seen) - set(required)):
        findings.append(f"unexpected GDC in Genesis governance baseline: {doc_id}")

    for doc_id in required:
        meta = seen.get(doc_id)
        if meta is None:
            continue

        if meta.get("status") != "draft":
            findings.append(f"{doc_id}: Genesis status must remain draft")

        version = meta.get("version")
        if not isinstance(version, str):
            findings.append(f"{doc_id}: version must be a string")
            continue

        match = VERSION_RE.fullmatch(version)
        if match is None or int(match.group("major")) != 0:
            findings.append(f"{doc_id}: Genesis version must remain in 0.x.x")

    return tuple(findings)


def _load_manifest_text(text: str) -> Mapping[str, object]:
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("bootstrap manifest must be a YAML mapping")
    return data


def _pre_genesis_snapshot(
    repo_root: Path,
    manifest: Mapping[str, object],
    git: GitRunner,
) -> tuple[tuple[str, ...], Mapping[str, str], tuple[str, ...]]:
    findings: list[str] = []

    branch = git(["branch", "--show-current"])
    canonical_branch = manifest.get("canonical_branch")
    if branch.returncode != 0:
        findings.append("cannot resolve current Git branch")
    elif branch.stdout.strip() != canonical_branch:
        findings.append(
            f"pre-Genesis branch must be {canonical_branch!r}, "
            f"found {branch.stdout.strip()!r}"
        )

    candidate = git(
        ["ls-files", "--cached", "--others", "--exclude-standard"]
    )
    if candidate.returncode != 0:
        findings.append("cannot enumerate non-ignored Genesis candidate files")
        candidate_files: tuple[str, ...] = ()
    else:
        candidate_files = tuple(
            sorted(
                _normalize(line.strip())
                for line in candidate.stdout.splitlines()
                if line.strip()
            )
        )

    gdc_docs = {
        _normalize(str(path.relative_to(repo_root))): path.read_text(encoding="utf-8")
        for path in sorted((repo_root / "00-governance").glob("GDC-*.md"))
    }

    return candidate_files, gdc_docs, tuple(findings)


def _post_genesis_snapshot(
    manifest: Mapping[str, object],
    git: GitRunner,
) -> tuple[tuple[str, ...], Mapping[str, str], str | None, tuple[str, ...]]:
    findings: list[str] = []

    roots = git(["rev-list", "--max-parents=0", "HEAD"])
    if roots.returncode != 0:
        return (), {}, None, ("cannot resolve Git root commit",)

    root_commits = tuple(
        line.strip()
        for line in roots.stdout.splitlines()
        if line.strip()
    )

    if len(root_commits) != 1:
        findings.append(
            f"repository must have exactly one root commit, found {len(root_commits)}"
        )
        return (), {}, None, tuple(findings)

    root_commit = root_commits[0]

    tree = git(["ls-tree", "-r", "--name-only", root_commit])
    if tree.returncode != 0:
        findings.append("cannot enumerate root commit tree")
        candidate_files: tuple[str, ...] = ()
    else:
        candidate_files = tuple(
            sorted(
                _normalize(line.strip())
                for line in tree.stdout.splitlines()
                if line.strip()
            )
        )

    gdc_docs: dict[str, str] = {}
    governance = manifest.get("governance_control_plane")
    required = governance.get("required_baseline_ids", []) if isinstance(governance, dict) else []

    if isinstance(required, list):
        for doc_id in required:
            prefix = f"00-governance/{doc_id}-"
            matches = [
                path
                for path in candidate_files
                if path.startswith(prefix) and path.endswith(".md")
            ]
            if len(matches) != 1:
                continue

            path = matches[0]
            shown = git(["show", f"{root_commit}:{path}"])
            if shown.returncode == 0:
                gdc_docs[path] = shown.stdout

    return candidate_files, gdc_docs, root_commit, tuple(findings)


def audit_genesis_integrity(
    repo_root: str | Path,
    *,
    git_runner: GitRunner | None = None,
) -> GenesisIntegrityReport:
    root = Path(repo_root).resolve()
    git = git_runner or _default_git_runner(root)

    manifest_path = root / "00-governance" / "bootstrap-manifest.yaml"

    try:
        manifest = _load_manifest_text(
            manifest_path.read_text(encoding="utf-8")
        )
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return GenesisIntegrityReport(
            mode="invalid",
            candidate_files=(),
            root_commit=None,
            findings=(f"cannot load bootstrap manifest: {exc}",),
        )

    findings = list(_manifest_findings(manifest))
    head = git(["rev-parse", "--verify", "HEAD"])

    if head.returncode != 0:
        mode = "pre-genesis"
        candidate_files, gdc_docs, git_findings = _pre_genesis_snapshot(
            root, manifest, git
        )
        root_commit = None
    else:
        mode = "post-genesis"
        candidate_files, gdc_docs, root_commit, git_findings = _post_genesis_snapshot(
            manifest, git
        )

    findings.extend(git_findings)
    findings.extend(validate_candidate_paths(candidate_files, manifest))
    findings.extend(validate_gdc_snapshot(gdc_docs, manifest))

    return GenesisIntegrityReport(
        mode=mode,
        candidate_files=candidate_files,
        root_commit=root_commit,
        findings=tuple(findings),
    )


def assert_genesis_integrity(
    repo_root: str | Path,
    *,
    git_runner: GitRunner | None = None,
) -> GenesisIntegrityReport:
    report = audit_genesis_integrity(repo_root, git_runner=git_runner)

    if report.findings:
        raise RuntimeError(
            "Genesis integrity audit failed:\n  - "
            + "\n  - ".join(report.findings)
        )

    return report
