from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
from typing import Callable


class DependencyUpdateError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class DependencyUpdateReport:
    base_ref: str
    head_ref: str
    changed_files: tuple[str, ...]
    checked_bundles: tuple[str, ...]


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise DependencyUpdateError(code)


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise DependencyUpdateError("dependency-update-git-failed")
    return result.stdout.strip()


def _policy(root: Path) -> dict:
    try:
        value = json.loads(
            (root / "governance/dependency-update-policy.json").read_text(
                encoding="utf-8"
            )
        )
    except (OSError, ValueError) as exc:
        raise DependencyUpdateError("dependency-update-policy-load") from exc

    _require(value.get("schema_version") == 1, "dependency-update-policy-version")
    _require(
        value.get("kind") == "scnehaux-dependency-update-policy",
        "dependency-update-policy-kind",
    )
    _require(
        value.get("claims")
        == {
            "manual_lock_only_updates_allowed": False,
            "partial_dependency_updates_allowed": False,
        },
        "dependency-update-policy-claims",
    )

    procedure = value.get("procedure")
    _require(
        isinstance(procedure, dict) and set(procedure) == {"python", "npm"},
        "dependency-update-procedure",
    )
    for steps in procedure.values():
        _require(
            isinstance(steps, list)
            and steps
            and all(isinstance(step, str) and step for step in steps),
            "dependency-update-procedure-steps",
        )

    for name in ("python_bundle", "npm_bundle"):
        bundle = value.get(name)
        _require(
            isinstance(bundle, list)
            and len(bundle) >= 3
            and len(bundle) == len(set(bundle)),
            f"dependency-update-{name}",
        )
        _require(
            all(isinstance(item, str) and item for item in bundle),
            f"dependency-update-{name}-path",
        )
    return value


def assert_dependency_update_integrity(
    repo_root: str | Path,
    *,
    base_ref: str,
    head_ref: str = "HEAD",
    git: Callable[..., str] | None = None,
) -> DependencyUpdateReport:
    root = Path(repo_root).resolve()
    policy = _policy(root)
    git_fn = _git if git is None else git
    merge_base = git_fn(root, "merge-base", base_ref, head_ref)
    _require(bool(merge_base), "dependency-update-merge-base")

    changed = tuple(
        sorted(
            filter(
                None,
                git_fn(
                    root,
                    "diff",
                    "--name-only",
                    f"{merge_base}..{head_ref}",
                    "--",
                ).splitlines(),
            )
        )
    )
    changed_set = set(changed)
    checked: list[str] = []

    for name in ("python_bundle", "npm_bundle"):
        bundle = set(policy[name])
        triggers = bundle - {"governance/reproducibility-policy.json"}
        if changed_set & triggers:
            missing = sorted(bundle - changed_set)
            _require(
                not missing,
                f"dependency-update-partial-{name}:" + ",".join(missing),
            )
            checked.append(name)

    return DependencyUpdateReport(
        base_ref=base_ref,
        head_ref=head_ref,
        changed_files=changed,
        checked_bundles=tuple(checked),
    )
