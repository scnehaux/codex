from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
import re
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


# Slice 13.2 evidence reconciliation 002: owner ARB records examined as review evidence.
EVIDENCE_002 = "governance/github/evidence/registry-reconciliation-002.json"
REGISTRY = ROOT / "governance/normative-control-registry.yaml"
PROFILE = ROOT / "governance/framework/profiles/scnehaux-codex-default.yaml"
ARB_AUTHORITY_REVISION = "42c3ed6eaf5d32be941e6157a7630bab0774da9c"
RECORD_PATH = re.compile(
    r"governance/arb-approvals/(GDC-\d{3})-1\.0\.0-([0-9a-f]{40})\.json"
)
SCORE = re.compile(r"(9|10)/10")
CLOSED_SLICES = {
    "Slice 13.1 Root-of-Trust Release Classification",
    "Slice 13.3 Runtime Authority Closure",
    "Slice 13.4 Release Metadata Binding",
    "Slice 13.5 Stable GDC Baseline",
}
UNRESOLVED_ROOTS = {
    "CTRL-GDC-000-026",
    "CTRL-GDC-001-013",
    "CTRL-GDC-001-014",
    "CTRL-GDC-001-015",
    "CTRL-GDC-002-003",
    "CTRL-GDC-003-004",
    "CTRL-GDC-003-005",
    "CTRL-GDC-003-006",
    "CTRL-GDC-003-010",
    "CTRL-GDC-003-011",
    "CTRL-GDC-005-010",
    "CTRL-GDC-005-012",
    "CTRL-GDC-005-013",
}


def _evidence_002():
    return json.loads((ROOT / EVIDENCE_002).read_text(encoding="utf-8"))


def _registry():
    return {item.control_id: item for item in load_control_registry(REGISTRY)}


def _doc_meta(path):
    text = path.read_text(encoding="utf-8")
    return yaml.safe_load(text.split("---", 2)[1])["doc_meta"]


def test_owner_records_retain_reviewed_content_and_identity():
    sources = _evidence_002()["sources"]
    assert sources["repository"] == "scnehaux/codex-authority"
    assert sources["revision"] == ARB_AUTHORITY_REVISION
    assert sources["arb_gate"]["path"] == "src/codex_authority/arb_gate.py"
    assert sources["arb_gate"]["minimum_score_pattern"] == SCORE.pattern
    for document, source in sources["arb_approvals"].items():
        record = source["record"]
        match = RECORD_PATH.fullmatch(source["path"])
        assert match is not None, document
        assert match.group(1) == document
        assert re.fullmatch(r"[0-9a-f]{40}", source["git_blob"])
        assert _canonical_digest(record) == source["canonical_sha256"]
        assert record["kind"] == "codex-arb-approval-record"
        assert record["schema_version"] == 1
        assert record["decision"] == "approve"
        subject = record["subject"]
        assert subject["repository"] == "scnehaux/codex"
        assert subject["document"] == document
        assert subject["head_sha"] == match.group(2)
        assert (subject["status"], subject["version"]) == ("approved", "1.0.0")
        assert record["review"]["rubric"] == "GDC-002"
        assert SCORE.fullmatch(record["review"]["score"])


def test_every_required_gdc_has_an_owner_record_for_its_approved_head():
    required = yaml.safe_load(PROFILE.read_text(encoding="utf-8"))["governance"][
        "required_baseline_ids"
    ]
    records = _evidence_002()["sources"]["arb_approvals"]
    assert sorted(records) == sorted(required)
    pull_requests = [
        records[doc]["record"]["subject"]["pull_request"] for doc in required
    ]
    assert len(set(pull_requests)) == len(required)
    for document in required:
        (path,) = (ROOT / "governance").glob(f"{document}-*.md")
        meta = _doc_meta(path)
        assert (meta["status"], meta["version"]) == ("approved", "1.0.0"), document


def test_single_person_review_is_disclosed_not_claimed_as_two_party():
    evidence = _evidence_002()
    claims = evidence["claims"]
    assert claims["owner_review_recorded_for_every_required_gdc"] is True
    for claim in (
        "two_party_review_proven",
        "independent_human_review_proven",
        "provider_observation_performed",
        "consumer_architecture_conformance_proven",
    ):
        assert claims[claim] is False, claim
    for source in evidence["sources"]["arb_approvals"].values():
        assert source["record"]["review_exception"]["author_is_approver"] is True
    limits = " ".join(evidence["claim_limits"])
    assert "Level 4" in limits and "release notes" in limits
    assert "GDC-000 record was created after its merge" in limits


def test_examined_controls_are_bound_to_this_assessment():
    registry = _registry()
    controls = _evidence_002()["controls"]
    assert controls
    for control_id, entry in controls.items():
        record = registry[control_id]
        assert entry["assessment"] == "verified"
        assert entry["method"] == "examine"
        assert entry["basis"]
        assert record.evidence_status == "verified"
        assert record.enforcement_mode != "automated"
        assert f"{EVIDENCE_002}#controls/{control_id}" in record.test_evidence


def test_reclassifications_match_the_registry():
    registry = _registry()
    reclassified = _evidence_002()["reclassifications"]
    assert set(reclassified) == {
        "CTRL-GDC-000-006",
        "CTRL-GDC-000-009",
        "CTRL-GDC-000-017",
        "CTRL-GDC-000-022",
        "CTRL-GDC-003-002",
    }
    for control_id, change in reclassified.items():
        assert change["from"] == "root-of-trust"
        assert change["reason"]
        assert registry[control_id].release_class == change["to"]


def test_no_pending_control_targets_a_closed_slice():
    for record in _registry().values():
        if record.evidence_status != "verified":
            assert record.target_phase not in CLOSED_SLICES, record.control_id


def test_unresolved_roots_remain_pending_in_slice_13_2():
    pending_roots = {
        record.control_id
        for record in _registry().values()
        if record.release_class == "root-of-trust"
        and record.evidence_status != "verified"
    }
    assert pending_roots == UNRESOLVED_ROOTS
    registry = _registry()
    for control_id in UNRESOLVED_ROOTS:
        assert registry[control_id].target_phase == (
            "Slice 13.2 Registry Evidence Reconciliation"
        )
