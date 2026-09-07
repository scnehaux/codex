from __future__ import annotations

from copy import deepcopy
import json
import shutil

import pytest
import yaml

from engine.adapters.scm.github import audit_github_projection
from engine.adapters.scm.github_activation import build_github_activation_plan
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

    plan = build_github_activation_plan(REPOSITORY_ROOT, policy)
    assert plan.ready is False
    assert plan.ruleset_payload is None
    assert {finding.code for finding in plan.blockers} == {
        "authority-integration-id-unbound",
        "authority-revision-unbound",
    }


def test_active_bootstrap_review_exception_projects_effective_state():
    policy = load_scm_enforcement_policy(REPOSITORY_ROOT)
    assert policy.review.normative_target.minimum_independent_approvals >= 1
    assert policy.review.bootstrap_exception.active is True
    assert policy.review.effective_required_approvals == 0
    assert policy.review.effective_require_qualified_owner_approval is False

    ruleset = json.loads(
        (REPOSITORY_ROOT / "governance/github/main-ruleset.json").read_text(
            encoding="utf-8"
        )
    )
    pull = next(rule for rule in ruleset["rules"] if rule["type"] == "pull_request")
    assert (
        pull["parameters"]["required_approving_review_count"]
        == policy.review.effective_required_approvals
    )
    assert (
        pull["parameters"]["require_code_owner_review"]
        is policy.review.effective_require_qualified_owner_approval
    )


def test_ruleset_projection_drift_is_detected(tmp_path):
    root = _copy(tmp_path)
    path = root / "governance/github/main-ruleset.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["rules"] = [
        rule for rule in data["rules"] if rule["type"] != "non_fast_forward"
    ]
    path.write_text(json.dumps(data), encoding="utf-8")
    assert "force-push-projection-mismatch" in _codes(root)


@pytest.mark.parametrize("helper_first", [False, True])
@pytest.mark.parametrize(
    "scenario",
    [
        "baseline",
        "explicit-read",
        "helper-none",
        "helper-empty-permissions",
        "helper-read-all",
        "explicit-success",
        "job-write",
        "helper-write",
        "helper-write-all",
        "job-empty-permissions",
        "job-malformed-permissions",
        "job-skipped",
        "job-ignores-failure",
        "job-depends-on-skipped-helper",
        "mutation-skipped",
        "qualification-ignores-failure",
        "mutation-in-helper",
        "qualification-in-helper",
        "checkout-in-helper",
        "python-in-helper",
        "node-in-helper",
        "unsafe-checkout-before-safe",
        "shallow-checkout-before-safe",
        "unpinned-checkout-before-safe",
        "unpinned-python-before-safe",
        "unpinned-node-before-safe",
        "unsafe-helper-checkout",
        "shallow-helper-checkout",
        "job-malformed-steps",
        "job-malformed-step",
        "helper-malformed-job",
        "conditional-checkout",
    ],
)
def test_workflow_is_validated_structurally_not_by_comments(
    tmp_path, scenario, helper_first
):
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

    workflow = yaml.load(text, Loader=yaml.BaseLoader)
    job = workflow["jobs"]["qualification"]
    checkout, python, node = job["steps"][:3]
    mutation = next(
        step for step in job["steps"] if step.get("run") == "make mutation-ci-check"
    )
    qualification = next(
        step for step in job["steps"] if step.get("run") == "make governance-qualify"
    )
    helper = {
        "name": "Supplemental check",
        "runs-on": "ubuntu-24.04",
        "if": "false",
        "steps": [deepcopy(checkout)],
    }
    jobs = {"qualification": job, "helper": helper}
    workflow["jobs"] = dict(reversed(tuple(jobs.items()))) if helper_first else jobs

    mutations = {
        "baseline": (helper, "if", "false", None),
        "explicit-read": (job, "permissions", {"contents": "read"}, None),
        "helper-none": (helper, "permissions", {"contents": "none"}, None),
        "helper-empty-permissions": (helper, "permissions", {}, None),
        "helper-read-all": (helper, "permissions", "read-all", None),
        "explicit-success": (job, "if", "${{ success() }}", None),
        "job-write": (
            job,
            "permissions",
            {"contents": "write"},
            "job-permission-projection-mismatch",
        ),
        "helper-write": (
            helper,
            "permissions",
            {"contents": "write"},
            "job-permission-projection-mismatch",
        ),
        "helper-write-all": (
            helper,
            "permissions",
            "write-all",
            "job-permission-projection-mismatch",
        ),
        "job-empty-permissions": (
            job,
            "permissions",
            {},
            "candidate-check-permission-mismatch",
        ),
        "job-malformed-permissions": (
            job,
            "permissions",
            [],
            "job-permission-projection-mismatch",
        ),
        "job-skipped": (job, "if", "false", "candidate-check-execution-drift"),
        "job-ignores-failure": (
            job,
            "continue-on-error",
            "true",
            "candidate-check-execution-drift",
        ),
        "job-depends-on-skipped-helper": (
            job,
            "needs",
            "helper",
            "candidate-check-execution-drift",
        ),
        "mutation-skipped": (
            mutation,
            "if",
            "false",
            "mutation-validation-step-missing",
        ),
        "qualification-ignores-failure": (
            qualification,
            "continue-on-error",
            "true",
            "governance-qualification-step-missing",
        ),
        "unsafe-helper-checkout": (
            helper["steps"][0]["with"],
            "persist-credentials",
            "true",
            "checkout-credential-safety-drift",
        ),
        "shallow-helper-checkout": (
            helper["steps"][0]["with"],
            "fetch-depth",
            "1",
            "checkout-history-safety-drift",
        ),
        "job-malformed-steps": (
            job,
            "steps",
            "not-a-list",
            "workflow-job-structure-invalid",
        ),
        "conditional-checkout": (
            checkout,
            "if",
            "false",
            "pinned-action-projection-mismatch",
        ),
    }
    if scenario in mutations:
        target, key, value, expected = mutations[scenario]
        target[key] = value
    elif scenario.endswith("-in-helper"):
        moved, expected = {
            "mutation-in-helper": (mutation, "mutation-validation-step-missing"),
            "qualification-in-helper": (
                qualification,
                "governance-qualification-step-missing",
            ),
            "checkout-in-helper": (checkout, "pinned-action-projection-mismatch"),
            "python-in-helper": (python, "pinned-action-projection-mismatch"),
            "node-in-helper": (node, "pinned-action-projection-mismatch"),
        }[scenario]
        job["steps"].remove(moved)
        helper["steps"].append(moved)
    elif scenario.endswith("-before-safe"):
        if "python" in scenario:
            original = python
        elif "node" in scenario:
            original = node
        else:
            original = checkout
        duplicate = deepcopy(original)
        job["steps"].insert(0, duplicate)
        if scenario.startswith("unpinned"):
            duplicate["uses"] = original["uses"].split("@")[0] + "@v6"
            expected = "pinned-action-projection-mismatch"
        elif scenario.startswith("shallow"):
            duplicate["with"]["fetch-depth"] = "1"
            expected = "checkout-history-safety-drift"
        else:
            duplicate["with"]["persist-credentials"] = "true"
            expected = "checkout-credential-safety-drift"
    elif scenario == "job-malformed-step":
        job["steps"].append("not-a-step")
        expected = "workflow-job-structure-invalid"
    else:
        assert scenario == "helper-malformed-job"
        workflow["jobs"]["helper"] = "not-a-job"
        expected = "workflow-job-structure-invalid"

    path.write_text(yaml.safe_dump(workflow, sort_keys=False), encoding="utf-8")
    # Even a structurally bound activation plan must reject unsafe workflow state.
    binding_path = root / "governance/github/authority-binding.yaml"
    binding = yaml.safe_load(binding_path.read_text(encoding="utf-8"))
    binding["authority"]["integration_id"] = 4242
    binding["evaluator"]["authority_revision"] = "a" * 40
    binding_path.write_text(yaml.safe_dump(binding, sort_keys=False), encoding="utf-8")
    policy = load_scm_enforcement_policy(root)
    report = audit_github_projection(root, policy)
    plan = build_github_activation_plan(root, policy)
    if expected is None:
        assert report.ok, report.findings
        assert plan.ready
    else:
        assert expected in {finding.code for finding in report.findings}
        assert not plan.ready
        assert plan.ruleset_payload is None
        assert expected in {finding.code for finding in plan.blockers}


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

    policy = load_scm_enforcement_policy(root)
    blocked = build_github_activation_plan(root, policy)
    assert blocked.ready is False
    assert "authority-binding-projection-mismatch" in {
        finding.code for finding in blocked.blockers
    }

    ready_root = _copy(tmp_path / "ready")
    ready_binding = ready_root / "governance/github/authority-binding.yaml"
    ready_data = yaml.safe_load(ready_binding.read_text(encoding="utf-8"))
    ready_data["authority"]["integration_id"] = 4242
    ready_data["evaluator"]["authority_revision"] = "a" * 40
    ready_binding.write_text(
        yaml.safe_dump(ready_data, sort_keys=False), encoding="utf-8"
    )
    ready_policy = load_scm_enforcement_policy(ready_root)
    plan = build_github_activation_plan(ready_root, ready_policy)
    assert plan.ready is True
    assert plan.integration_id == 4242
    assert plan.authority_revision == "a" * 40
    status = next(
        rule
        for rule in plan.ruleset_payload["rules"]
        if rule["type"] == "required_status_checks"
    )
    assert status["parameters"]["required_status_checks"] == [
        {"context": "Governance Qualification"},
        {"context": "Codex Governance Authority", "integration_id": 4242},
    ]

    invalid_root = _copy(tmp_path / "invalid-activation")
    invalid_binding = invalid_root / "governance/github/authority-binding.yaml"
    invalid_data = yaml.safe_load(invalid_binding.read_text(encoding="utf-8"))
    invalid_data["authority"]["integration_id"] = 4242
    invalid_data["evaluator"]["authority_revision"] = "b" * 40
    invalid_data["activation"]["state"] = "active"
    invalid_binding.write_text(
        yaml.safe_dump(invalid_data, sort_keys=False), encoding="utf-8"
    )
    invalid_policy = load_scm_enforcement_policy(invalid_root)
    invalid_plan = build_github_activation_plan(invalid_root, invalid_policy)
    assert invalid_plan.ready is False
    assert {finding.code for finding in invalid_plan.blockers} == {
        "activation-state-invalid"
    }

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

    policy = load_scm_enforcement_policy(root)
    plan = build_github_activation_plan(root, policy)
    assert plan.ready is False
    assert plan.blockers[0].code == "activation-source-load-failed"
