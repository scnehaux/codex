from __future__ import annotations

from pathlib import Path
import shutil

import pytest

import scripts.reproducibility_check as target
from tests.support.repository import REPOSITORY_ROOT


ROOT = REPOSITORY_ROOT


def _fixture(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    for relative in (
        "pyproject.toml",
        "constraints.txt",
        "requirements.txt",
        "governance/reproducibility-policy.json",
        "scripts/prettier_runner.py",
        "integrations/github-app-local/requirements.txt",
        "integrations/github-app-local/requirements-dev.txt",
        ".github/workflows/governance.yml",
        ".github/workflows/governance-evaluator.yml",
        ".github/workflows/local-app-tooling.yml",
    ):
        source = ROOT / relative
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return root


def test_current_reproducibility_policy_passes():
    target.assert_reproducibility_policy(ROOT)


@pytest.mark.parametrize(
    ("relative", "old", "new", "error"),
    [
        ("pyproject.toml", "setuptools==84.0.0", "setuptools>=84.0.0", "build-backend"),
        (
            "pyproject.toml",
            "jsonschema==4.21.1",
            "jsonschema>=4.21.1",
            "project-dependency",
        ),
        (
            ".github/workflows/governance.yml",
            'python-version: "3.13.15"',
            'python-version: "3.13"',
            "python-runner",
        ),
        (
            ".github/workflows/governance.yml",
            'node-version: "24.21.0"',
            'node-version: "24"',
            "node-runner",
        ),
        (
            ".github/workflows/governance.yml",
            "actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803",
            "actions/checkout@v6",
            "action-sha",
        ),
        (
            "scripts/prettier_runner.py",
            'PRETTIER_PACKAGE = "prettier@3.9.6"',
            'PRETTIER_PACKAGE = "prettier@latest"',
            "prettier-pin",
        ),
    ],
)
def test_reproducibility_policy_fails_closed_on_floating_or_mutable_inputs(
    tmp_path, relative, old, new, error
):
    root = _fixture(tmp_path)
    path = root / relative
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    with pytest.raises(target.ReproducibilityError, match=error):
        target.assert_reproducibility_policy(root)


def test_missing_resolved_constraint_fails_closed(tmp_path):
    root = _fixture(tmp_path)
    path = root / "constraints.txt"
    rows = [
        row
        for row in path.read_text(encoding="utf-8").splitlines()
        if row != "colorama==0.4.6"
    ]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    with pytest.raises(
        target.ReproducibilityError, match="constraints-resolution-drift"
    ):
        target.assert_reproducibility_policy(root)
