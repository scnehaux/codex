from __future__ import annotations

import json
import shutil

import yaml

from engine.adapters.scm.github import audit_github_projection
from engine.control.governance.scm_policy import load_scm_enforcement_policy
from tests.support.repository import REPOSITORY_ROOT


ESTATE = (
    "governance/scm/enforcement-policy.yaml",
    "governance/github/main-ruleset.json",
    "governance/github/authority-binding.yaml",
    ".github/workflows/governance.yml",
    ".github/CODEOWNERS",
    ".github/pull_request_template.md",
)


def _copy(tmp_path):
    for rel in ESTATE:
        src = REPOSITORY_ROOT / rel
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    return tmp_path


def _codes(root):
    policy = load_scm_enforcement_policy(root)
    return {finding.code for finding in audit_github_projection(root, policy).findings}


def test_current_github_projection_matches_provider_neutral_policy():
    policy = load_scm_enforcement_policy(REPOSITORY_ROOT)
    report = audit_github_projection(REPOSITORY_ROOT, policy)
    assert report.ok


def test_ruleset_projection_drift_is_detected(tmp_path):
    root = _copy(tmp_path)
    path = root / "governance/github/main-ruleset.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["rules"] = [
        rule for rule in data["rules"] if rule["type"] != "non_fast_forward"
    ]
    path.write_text(json.dumps(data), encoding="utf-8")
    assert "force-push-projection-mismatch" in _codes(root)


def test_workflow_is_validated_structurally_not_by_comments(tmp_path):
    root = _copy(tmp_path)
    path = root / ".github/workflows/governance.yml"
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text + "\n# Codex Governance Authority is not a job\n", encoding="utf-8"
    )
    assert not _codes(root)

    path.write_text(
        text.replace("branches: [main]", "branches: [develop]", 1),
        encoding="utf-8",
    )
    assert "workflow-pr-trigger-projection-mismatch" in _codes(root)


def test_candidate_workflow_cannot_emit_external_authority_job(tmp_path):
    root = _copy(tmp_path)
    path = root / ".github/workflows/governance.yml"
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace(
            "name: Governance Qualification",
            "name: Codex Governance Authority",
            1,
        ),
        encoding="utf-8",
    )
    codes = _codes(root)
    assert "candidate-check-job-mismatch" in codes
    assert "candidate-workflow-emits-external-authority" in codes


def test_authority_binding_and_codeowners_projection_drift(tmp_path):
    root = _copy(tmp_path)
    binding = root / "governance/github/authority-binding.yaml"
    data = yaml.safe_load(binding.read_text(encoding="utf-8"))
    data["authority"]["check_context"] = "Wrong Authority"
    binding.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    assert "authority-binding-projection-mismatch" in _codes(root)

    root = _copy(tmp_path / "owners")
    codeowners = root / ".github/CODEOWNERS"
    codeowners.write_text(
        codeowners.read_text(encoding="utf-8").replace(
            "/governance/ @anshacerbia2\n",
            "",
        ),
        encoding="utf-8",
    )
    assert "governance-owner-projection-mismatch" in _codes(root)


def test_malformed_provider_state_fails_closed(tmp_path):
    root = _copy(tmp_path)
    (root / "governance/github/main-ruleset.json").write_text("{", encoding="utf-8")
    assert "github-projection-load-failed" in _codes(root)
