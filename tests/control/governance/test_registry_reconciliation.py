from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
import subprocess

import pytest
import yaml

from engine.control.governance.controls import load_control_registry
from engine.control.governance.genesis import (
    _manifest_findings,
    assert_genesis_integrity,
)
from tests.support.repository import REPOSITORY_ROOT


ROOT = REPOSITORY_ROOT
EVIDENCE = "governance/github/evidence/registry-reconciliation-001.json"
AUTHORITY_REVISION = "1f0b98f60bcb321fde762f13b8f2c558c7d0015e"
SOURCE_PINS = {
    "acceptance": (
        "governance/evidence/phase10-acceptance-001.json",
        "1c9c00cdd2c411fa3ce677c06de722cc2eb1c169",
        "72b8c715b25e2c6e020f00a69e7a5706b76ac487396005e5d6d408e433030397",
    ),
    "completion": (
        "governance/evidence/phase10-completion-001.json",
        "316b41ffde1f3437afd5e82ac2be2d3dfeb191c0",
        "b1075e02801ba56dd7d0562d9ebc65877d83f2a22d55ad6ae74a50e7b5c9f585",
    ),
    "handover": (
        "governance/attested-handover.json",
        "63a62dfa78b32643415cb9618f527e535aa6a4b4",
        "b20a662fd47758ee6e1bc9fbc8d4b5f1332eafb441373a58f87138eea24dd900",
    ),
    "maintenance": (
        "governance/privileged-maintenance.json",
        "b4757230d6f0487f515d2a44ae67cf148c63c872",
        "8b957c2c4a0a5b1273ef867b3955948cecb7c95481f02924d02e1f2c3b2135bf",
    ),
}


def _evidence():
    return json.loads((ROOT / EVIDENCE).read_text(encoding="utf-8"))


def _git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def _canonical_digest(record):
    raw = json.dumps(
        record, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return sha256(raw).hexdigest()


@pytest.mark.parametrize("name", SOURCE_PINS)
def test_imported_authority_records_retain_reviewed_content_and_identity(name):
    source = _evidence()["sources"][name]
    path, blob, digest = SOURCE_PINS[name]
    assert source["repository"] == "scnehaux/codex-authority"
    assert source["revision"] == AUTHORITY_REVISION
    assert source["path"] == path
    assert source["git_blob"] == blob
    assert source["canonical_sha256"] == digest
    assert _canonical_digest(source["record"]) == digest


def test_bootstrap_provenance_matches_the_immutable_genesis_source():
    current = yaml.safe_load((ROOT / "governance/bootstrap-manifest.yaml").read_bytes())
    assert _manifest_findings(current) == ()
    report = assert_genesis_integrity(ROOT)
    assert report.mode == "post-genesis"
    assert report.root_commit == "35ba5f427b8fcda41e8bb3a989cdf21cdf8e31cc"
    paths = (
        _git("ls-tree", "-r", "--name-only", report.root_commit).decode().splitlines()
    )
    manifest_paths = [p for p in paths if Path(p).name == "bootstrap-manifest.yaml"]
    assert len(manifest_paths) == 1
    historical = yaml.safe_load(
        _git("cat-file", "blob", f"{report.root_commit}:{manifest_paths[0]}")
    )
    assert current["target_repository"] == historical["target_repository"]
    assert current["source"] == historical["source"]


def test_accepted_provider_rows_do_not_exceed_the_owner_approved_scope():
    evidence = _evidence()
    acceptance = evidence["sources"]["acceptance"]["record"]
    completion = evidence["sources"]["completion"]["record"]
    assert acceptance["decision"]["recommendation"] == "REC-D-018"
    assert acceptance["decision"]["method_status"] == "Accepted"
    assert completion["acceptance"]["git_blob"] == SOURCE_PINS["acceptance"][1]
    assert completion["claims"]["phase10_status_finalized"] is True
    assert completion["claims"]["effective_enforcement_proven"] is True
    for record in (acceptance, completion):
        assert record["claims"]["full_mirror_equivalence_proven"] is False
        assert record["claims"]["independent_human_review_proven"] is False
        assert record["claims"]["native_git_default_deletion_observed"] is False
    rows = {row["id"]: row for row in acceptance["rows"]}
    for control_id, expected in (
        ("CTRL-GDC-000-028", {2: "force-push", 3: "default-deletion"}),
        ("CTRL-GDC-003-003", {1: "direct-push"}),
    ):
        assert evidence["controls"][control_id]["accepted_rows"] == list(expected)
        for row_id, obligation in expected.items():
            assert rows[row_id]["obligation"] == obligation
            assert rows[row_id]["assessment"] == "accepted-under-rec-d-018"
            assert rows[row_id]["limit"]


def test_provider_assessment_remains_bound_to_unchanged_semantic_policy():
    completion = _evidence()["sources"]["completion"]["record"]
    for path, expected in completion["source"][
        "semantic_policy_blobs_unchanged"
    ].items():
        raw = (ROOT / path).read_bytes().replace(b"\r\n", b"\n")
        assert (
            sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            == expected
        )
    postmerge = completion["postmerge"]
    assert postmerge["tested_rules_unchanged"] is True
    policy = postmerge["observer"]["evidence"]["effective_policy"]
    assert policy["bypass_allowed"] is False
    assert policy["force_push_allowed"] is False
    assert policy["deletion_allowed"] is False
    assert policy["changes_require_review"] is True
    assert postmerge["observer"]["evidence"]["drift"] == []


def test_incomplete_obligations_remain_pending():
    records = {
        item.control_id: item
        for item in load_control_registry(
            ROOT / "governance/normative-control-registry.yaml"
        )
    }
    evidence = _evidence()
    for control_id in (
        "CTRL-GDC-000-026",
        "CTRL-GDC-003-004",
        "CTRL-GDC-003-010",
        "CTRL-GDC-003-011",
    ):
        assert records[control_id].evidence_status == "pending"
        assert evidence["controls"][control_id]["assessment"] == "pending"
        assert evidence["controls"][control_id]["basis"]


def test_promotion_evidence_does_not_grant_publication_or_change_component_claims():
    sources = _evidence()["sources"]
    handover = sources["handover"]["record"]
    maintenance = sources["maintenance"]["record"]
    assert handover["state"] == "runtime-promoted"
    assert handover["runtime_package"]["source_revision"] == (
        "d835991afe6ada47a66d012a3ddc2c4350cd9ff8"
    )
    assert handover["execution"]["candidate_code_execution"] is False
    assert handover["execution"]["credentials_allowed"] is False
    assert handover["publication"]["write_enabled"] is False
    assert maintenance["bootstrap"]["enabled"] is False
    assert maintenance["permanent_runtime"]["state"] == "promoted"
    for record in (handover, maintenance):
        assert record["claims"]["effective_enforcement_proven"] is False
