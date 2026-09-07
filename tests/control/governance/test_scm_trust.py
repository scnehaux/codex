from __future__ import annotations

import copy

import pytest
import yaml

from engine.control.governance.scm_trust import (
    assert_scm_trust_boundary,
    audit_scm_trust_boundary,
)
from tests.support.repository import REPOSITORY_ROOT


CONTRACT_PATH = REPOSITORY_ROOT / "governance" / "scm" / "trust-boundary.yaml"
CANONICAL = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))


def _materialize(tmp_path, data=None):
    path = tmp_path / "governance" / "scm" / "trust-boundary.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            copy.deepcopy(CANONICAL if data is None else data),
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return tmp_path


def test_current_repository_trust_boundary_passes():
    report = assert_scm_trust_boundary(REPOSITORY_ROOT)
    assert report.ok
    assert report.path == "governance/scm/trust-boundary.yaml"


@pytest.mark.parametrize(
    ("mutator", "code"),
    (
        (
            lambda data: data.__setitem__("contract_version", 2),
            "trust-contract-version-invalid",
        ),
        (
            lambda data: data.__setitem__("kind", "github-ruleset"),
            "trust-contract-kind-invalid",
        ),
        (
            lambda data: data.__setitem__("provider_neutral", False),
            "provider-neutrality-required",
        ),
        (
            lambda data: data.__setitem__("candidate_state", []),
            "candidate-state-invalid",
        ),
        (
            lambda data: data["candidate_state"].__setitem__(
                "may_validate_candidate", False
            ),
            "candidate-validation-contract-invalid",
        ),
        (
            lambda data: data["candidate_state"].__setitem__(
                "may_be_sole_guardrail_authority", True
            ),
            "candidate-self-authorization-forbidden",
        ),
        (
            lambda data: data.__setitem__("required_external_authority", []),
            "external-authority-invalid",
        ),
        (
            lambda data: data["required_external_authority"].__setitem__(
                "required", False
            ),
            "external-authority-required",
        ),
        (
            lambda data: data["required_external_authority"].__setitem__(
                "mutable_by_candidate", True
            ),
            "external-authority-candidate-mutable",
        ),
        (
            lambda data: data["required_external_authority"].__setitem__(
                "independently_administered", False
            ),
            "external-authority-not-independent",
        ),
        (
            lambda data: data["required_external_authority"][
                "identity_binding"
            ].__setitem__("candidate_may_select_effective_identity", True),
            "candidate-effective-identity-selection-forbidden",
        ),
        (
            lambda data: data["required_external_authority"][
                "evaluator_runtime"
            ].__setitem__("candidate_revision_as_authority", True),
            "candidate-revision-authority-forbidden",
        ),
        (
            lambda data: data["required_external_authority"][
                "evaluator_runtime"
            ].__setitem__("candidate_auto_deploy", True),
            "candidate-auto-deploy-forbidden",
        ),
        (
            lambda data: data["required_external_authority"][
                "evaluator_runtime"
            ].__setitem__("privileged_promotion_required", False),
            "privileged-authority-promotion-required",
        ),
        (
            lambda data: data["required_external_authority"].__setitem__(
                "capabilities", "bad"
            ),
            "external-authority-capabilities-invalid",
        ),
        (
            lambda data: data["required_external_authority"]["capabilities"].remove(
                "block-guardrail-self-authorization"
            ),
            "external-authority-capability-missing",
        ),
        (
            lambda data: data.__setitem__("protected_concerns", "bad"),
            "protected-concerns-invalid",
        ),
        (
            lambda data: data["protected_concerns"].remove("ci-definition"),
            "protected-concern-missing",
        ),
        (
            lambda data: data.__setitem__("evidence", []),
            "trust-evidence-invalid",
        ),
        (
            lambda data: data["evidence"].__setitem__(
                "proves_effective_enforcement", True
            ),
            "effective-enforcement-claim-forbidden",
        ),
        (
            lambda data: data["evidence"].__setitem__("activation_slice", "10.6"),
            "activation-slice-invalid",
        ),
        (
            lambda data: data.__setitem__("github", {}),
            "trust-contract-unknown-field",
        ),
    ),
)
def test_trust_boundary_corruption_fails_closed(tmp_path, mutator, code):
    data = copy.deepcopy(CANONICAL)
    mutator(data)
    root = _materialize(tmp_path, data)

    report = audit_scm_trust_boundary(root)

    assert any(finding.code == code for finding in report.findings)


def test_yaml_load_failure_is_reported(tmp_path):
    path = tmp_path / "governance" / "scm" / "trust-boundary.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("[", encoding="utf-8")

    report = audit_scm_trust_boundary(tmp_path)

    assert any(
        finding.code == "trust-contract-load-failed" for finding in report.findings
    )


def test_yaml_root_shape_failure_is_reported(tmp_path):
    path = tmp_path / "governance" / "scm" / "trust-boundary.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("- list\n", encoding="utf-8")

    report = audit_scm_trust_boundary(tmp_path)

    assert any(
        finding.code == "trust-contract-root-invalid" for finding in report.findings
    )


def test_assertion_raises_with_structured_findings(tmp_path):
    data = copy.deepcopy(CANONICAL)
    data["candidate_state"]["may_be_sole_guardrail_authority"] = True
    root = _materialize(tmp_path, data)

    with pytest.raises(
        RuntimeError,
        match="SCM enforcement trust-boundary audit failed",
    ):
        assert_scm_trust_boundary(root)
