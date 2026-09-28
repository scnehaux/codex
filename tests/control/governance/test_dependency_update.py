from __future__ import annotations

import json
from pathlib import Path

import pytest

import engine.control.governance.dependency_update as target

from engine.control.governance.dependency_update import (
    DependencyUpdateError,
    assert_dependency_update_integrity,
)


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    policy = root / "governance/dependency-update-policy.json"
    policy.parent.mkdir(parents=True)
    policy.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "scnehaux-dependency-update-policy",
                "python_bundle": [
                    "pyproject.toml",
                    "constraints.txt",
                    "requirements-lock.txt",
                    "governance/reproducibility-policy.json",
                ],
                "npm_bundle": [
                    "package.json",
                    "package-lock.json",
                    "governance/reproducibility-policy.json",
                ],
                "procedure": {"python": ["x"], "npm": ["x"]},
                "claims": {
                    "manual_lock_only_updates_allowed": False,
                    "partial_dependency_updates_allowed": False,
                },
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return root


def _git(changed: list[str]):
    def run(root: Path, *args: str) -> str:
        if args[0] == "merge-base":
            return "base"
        if args[0] == "diff":
            return "\n".join(changed)
        raise AssertionError(args)

    return run


def test_no_dependency_changes_pass(tmp_path):
    report = assert_dependency_update_integrity(
        _root(tmp_path),
        base_ref="a",
        git=_git(["README.md"]),
    )
    assert report.checked_bundles == ()


def test_complete_python_bundle_passes(tmp_path):
    files = [
        "pyproject.toml",
        "constraints.txt",
        "requirements-lock.txt",
        "governance/reproducibility-policy.json",
    ]
    report = assert_dependency_update_integrity(
        _root(tmp_path),
        base_ref="a",
        git=_git(files),
    )
    assert report.checked_bundles == ("python_bundle",)


def test_complete_npm_bundle_passes(tmp_path):
    files = [
        "package.json",
        "package-lock.json",
        "governance/reproducibility-policy.json",
    ]
    report = assert_dependency_update_integrity(
        _root(tmp_path),
        base_ref="a",
        git=_git(files),
    )
    assert report.checked_bundles == ("npm_bundle",)


@pytest.mark.parametrize(
    "changed",
    [
        ["pyproject.toml"],
        ["requirements-lock.txt"],
        ["package.json"],
        ["package-lock.json"],
    ],
)
def test_partial_bundle_fails_closed(tmp_path, changed):
    with pytest.raises(DependencyUpdateError, match="dependency-update-partial"):
        assert_dependency_update_integrity(
            _root(tmp_path),
            base_ref="a",
            git=_git(changed),
        )


def test_git_failure_is_fail_closed(monkeypatch, tmp_path):
    class Result:
        returncode = 1
        stdout = ""

    monkeypatch.setattr(target.subprocess, "run", lambda *args, **kwargs: Result())
    with pytest.raises(DependencyUpdateError, match="dependency-update-git-failed"):
        target._git(tmp_path, "status")


def test_policy_load_failure_is_fail_closed(tmp_path):
    root = tmp_path / "repo"
    policy = root / "governance/dependency-update-policy.json"
    policy.parent.mkdir(parents=True)
    policy.write_text("{not-json", encoding="utf-8")
    with pytest.raises(DependencyUpdateError, match="dependency-update-policy-load"):
        target._policy(root)
