from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError

import pytest
import yaml

from engine.control.governance.scm_policy import (
    SCMPolicyError,
    load_scm_enforcement_policy,
)
from tests.support.repository import REPOSITORY_ROOT


POLICY_PATH = REPOSITORY_ROOT / "governance/scm/enforcement-policy.yaml"
CANONICAL = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))


def _write(tmp_path, data) -> None:
    path = tmp_path / "governance/scm/enforcement-policy.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        path.write_text(data, encoding="utf-8")
    else:
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def test_current_policy_loads_as_immutable_typed_contract():
    policy = load_scm_enforcement_policy(REPOSITORY_ROOT)
    assert policy.default_branch.selector == "default"
    assert policy.merge.allowed_methods == ("squash",)
    assert policy.review.normative_target.minimum_independent_approvals == 1
    assert policy.review.normative_target.require_qualified_owner_approval is True
    assert policy.review.bootstrap_exception.active is True
    assert policy.review.effective_required_approvals == 0
    assert policy.review.effective_require_qualified_owner_approval is False
    assert policy.review.bootstrap_exception.exit_condition.signal == (
        "independent-qualified-reviewer-count"
    )
    assert policy.review.bootstrap_exception.exit_condition.operator == "gte"
    assert policy.review.bootstrap_exception.exit_condition.value == 2
    assert policy.qualification.candidate.context == "Governance Qualification"
    assert (
        policy.qualification.external_authority.context == "Codex Governance Authority"
    )
    with pytest.raises(FrozenInstanceError):
        policy.default_branch.selector = "main"


@pytest.mark.parametrize(
    "mutator",
    (
        lambda data: data.__setitem__("contract_version", 3),
        lambda data: data.__setitem__("kind", "github-ruleset"),
        lambda data: data.__setitem__("provider_neutral", False),
        lambda data: data.__setitem__("extra", True),
        lambda data: data.__setitem__("default_branch", []),
        lambda data: data["default_branch"].__setitem__("selector", ""),
        lambda data: data["default_branch"].__setitem__("deletion_allowed", "false"),
        lambda data: data.__setitem__("merge", []),
        lambda data: data["merge"].__setitem__("allowed_methods", []),
        lambda data: data["merge"].__setitem__("allowed_methods", ["squash", "squash"]),
        lambda data: data.__setitem__("review", []),
        lambda data: data["review"]["normative_target"].__setitem__(
            "minimum_independent_approvals", 0
        ),
        lambda data: data["review"]["bootstrap_exception"].__setitem__(
            "required_approvals", -1
        ),
        lambda data: data["review"]["bootstrap_exception"].__setitem__(
            "required_approvals", 1
        ),
        lambda data: data["review"]["bootstrap_exception"].__setitem__("reason", ""),
        lambda data: data["review"]["bootstrap_exception"].__setitem__(
            "exit_condition", []
        ),
        lambda data: data["review"]["bootstrap_exception"][
            "exit_condition"
        ].__setitem__("value", 0),
        lambda data: data.__setitem__("bypass", []),
        lambda data: data.__setitem__("qualification", []),
        lambda data: data["qualification"].__setitem__("candidate", []),
        lambda data: data["qualification"].__setitem__("external_authority", []),
        lambda data: data["qualification"]["candidate"].__setitem__("context", 3),
        lambda data: data.__setitem__("workflow", []),
        lambda data: data["workflow"].__setitem__("repository_contents_permission", ""),
        lambda data: data.__setitem__("ownership", []),
    ),
)
def test_policy_corruption_fails_closed(tmp_path, mutator):
    data = copy.deepcopy(CANONICAL)
    mutator(data)
    _write(tmp_path, data)
    with pytest.raises(SCMPolicyError):
        load_scm_enforcement_policy(tmp_path)


def test_yaml_failure_and_root_shape_fail_closed(tmp_path):
    _write(tmp_path, "[")
    with pytest.raises(SCMPolicyError):
        load_scm_enforcement_policy(tmp_path)

    _write(tmp_path, "- list\n")
    with pytest.raises(SCMPolicyError):
        load_scm_enforcement_policy(tmp_path)


def test_missing_policy_fails_closed(tmp_path):
    with pytest.raises(SCMPolicyError):
        load_scm_enforcement_policy(tmp_path)
