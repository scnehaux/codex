from __future__ import annotations

import os
from pathlib import Path
import subprocess
import yaml

from engine.control.framework.executable import compile_framework
from engine.control.governance.genesis import parse_frontmatter
from engine.control.repository.git_ingestion import (
    GitRepositoryContext,
    GitRepositoryReader,
)
from engine.control.repository.snapshot import (
    ValidatedRepositorySnapshot,
    build_validated_repository_snapshot,
)
from engine.core.metamodel import ArchitectureNamespace


def _git(root: Path, *args: str) -> str:
    return (
        subprocess.check_output(
            [
                "git",
                "--no-replace-objects",
                "--literal-pathspecs",
                "-C",
                str(root),
                *args,
            ],
            env={
                key: value
                for key, value in os.environ.items()
                if not key.startswith("GIT_")
            },
            stderr=subprocess.PIPE,
        )
        .decode("utf-8")
        .strip()
    )


def _clean_revision(root: Path) -> str:
    if _git(root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise ValueError(
            "GDC corpus qualification requires a clean checkout; commit candidate changes before qualification"
        )
    return _git(root, "rev-parse", "--verify", "HEAD^{commit}")


def assert_governed_corpus(repo_root: str | Path) -> ValidatedRepositorySnapshot:
    """Qualify the committed corpus with the framework from the same clean revision."""
    root = Path(repo_root).resolve()
    try:
        revision = _clean_revision(root)
        runtime = compile_framework(root)
        manifest = yaml.safe_load(
            (root / "governance/bootstrap-manifest.yaml").read_text(encoding="utf-8")
        )
        repository_id = manifest["target_repository"]
        organization, repository = repository_id.split("/", 1)
        context = GitRepositoryContext(
            repository_id, ArchitectureNamespace(organization, repository), revision
        )
        reader = GitRepositoryReader(root, context)
        batch = reader.ingest_governed_candidates(runtime)
        # Discovery must not silently omit any required baseline GDC.
        required_ids = manifest["governance_control_plane"]["required_baseline_ids"]
        if (
            not isinstance(required_ids, list)
            or not required_ids
            or any(
                not isinstance(item, str) or not item.startswith("GDC-")
                for item in required_ids
            )
            or len(required_ids) != len(set(required_ids))
        ):
            raise ValueError(
                "required baseline GDC IDs must be a non-empty unique list"
            )
        required = set(required_ids)
        present = {
            parse_frontmatter(entry.candidate.parsed.source.content)["id"]
            for entry in batch.entries
        }
        missing = required - present
        if missing:
            raise ValueError(
                "required baseline GDCs missing: " + ", ".join(sorted(missing))
            )
        snapshot = build_validated_repository_snapshot(
            batch, framework=runtime, repo_root=root
        )
        if _clean_revision(root) != revision:
            raise ValueError(
                "repository revision changed during GDC corpus qualification"
            )
        return snapshot
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        yaml.YAMLError,
        subprocess.CalledProcessError,
    ) as exc:
        raise RuntimeError(f"Governed corpus qualification failed: {exc}") from exc
