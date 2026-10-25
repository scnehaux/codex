from __future__ import annotations

import json

import pytest
import yaml

from scripts import governance_release as target
from tests.support.repository import REPOSITORY_ROOT


@pytest.fixture
def working(tmp_path, monkeypatch):
    source = tmp_path / "source"
    authority = tmp_path / "authority"
    source.mkdir()
    authority.mkdir()
    monkeypatch.chdir(source)
    return source, authority, tmp_path / "metadata.json"


def test_build_is_reviewable_and_never_declares_or_overwrites_release(
    working, monkeypatch, capsys
):
    source, authority, output = working
    monkeypatch.setattr(
        target.release,
        "build_release_manifest",
        lambda *args: {"source_commit": "a" * 40, "pending": True},
    )
    args = [
        "build",
        "--authority-root",
        str(authority),
        "--authority-revision",
        "b" * 40,
        "--release-version",
        "1.0.0",
        "--output",
        str(output),
    ]
    assert target.main(args) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "release_metadata_bound"
    assert report["release_declared"] is False
    before = output.read_bytes()
    assert target.main(args) == 1
    assert output.read_bytes() == before
    for forbidden in (source / "inside.json", authority / "inside.json"):
        assert target.main(args[:-1] + [str(forbidden)]) == 1
        assert not forbidden.exists()


@pytest.mark.parametrize("mode", ["build", "verify"])
def test_required_mode_inputs_fail_closed(working, mode, capsys):
    _, authority, _ = working
    assert (
        target.main(
            [mode, "--authority-root", str(authority), "--release-version", "1.0.0"]
        )
        == 1
    )
    assert "requires" in capsys.readouterr().out


def test_verify_passes_exact_manifest_and_tag_to_verifier(working, monkeypatch, capsys):
    source, authority, _ = working
    observed = []

    def verify(*args, **kwargs):
        observed.append((args, kwargs))
        return {"status": "release_candidate_verified"}

    monkeypatch.setattr(target.release, "verify_release_manifest", verify)
    args = [
        "verify",
        "--authority-root",
        str(authority),
        "--manifest-revision",
        "b" * 40,
        "--manifest-sha256",
        "c" * 64,
        "--release-version",
        "1.0.0",
        "--tag",
        "governance-v1.0.0",
    ]
    assert target.main(args) == 0
    assert observed[0][0] == (
        source.resolve(),
        authority,
        "b" * 40,
        "1.0.0",
        "c" * 64,
        target.github.verify_publication,
    )
    assert observed[0][1] == {"tag": "governance-v1.0.0"}
    assert "release_candidate_verified" in capsys.readouterr().out


def test_declared_candidate_workflow_verifies_before_qualification():
    workflow = yaml.load(
        (REPOSITORY_ROOT / ".github/workflows/governance-release.yml").read_text(
            encoding="utf-8"
        ),
        Loader=yaml.BaseLoader,
    )
    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert set(workflow["on"]["workflow_dispatch"]["inputs"]) == {
        "source_commit",
        "authority_commit",
        "release_version",
        "manifest_sha256",
    }
    assert workflow["permissions"] == {
        "contents": "read",
        "checks": "read",
        "pull-requests": "read",
    }
    steps = workflow["jobs"]["release-candidate"]["steps"]
    checks = [
        i
        for i, step in enumerate(steps)
        if "scripts/governance_release.py verify" in step.get("run", "")
    ]
    qualify = next(
        i
        for i, step in enumerate(steps)
        if step.get("run") == "make governance-qualify"
    )
    assert len(checks) == 1 and checks[0] < qualify
    assert all("if" not in step for step in steps)
    checkouts = [s for s in steps if s.get("uses", "").startswith("actions/checkout@")]
    assert len(checkouts) == 2
    assert all(
        c["with"]["persist-credentials"] == "false" and c["with"]["fetch-depth"] == "0"
        for c in checkouts
    )
    assert all("${{" not in s.get("run", "") for s in steps)
