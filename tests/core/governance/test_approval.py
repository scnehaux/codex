import pytest

from engine.core.governance import (
    ApprovalDecision,
    ApprovalPackage,
    ApprovalRequirement,
    DecisionOutcome,
)


def package(**overrides):
    values = dict(
        package_id="AP-1",
        draft_id="D-1",
        proposal_id="P-1",
        validation_report_id="VAL-1",
        simulation_report_id="SIM-1",
        review_ids=("REV-1",),
        risk_classification="high",
        affected_scopes=("domain-a",),
        requirements=(ApprovalRequirement("principal-architect"),),
        mechanically_eligible=True,
        auto_approval_eligible=False,
    )
    values.update(overrides)
    return ApprovalPackage(**values)


def test_approval_package_and_human_decision():
    item = package()
    decision = ApprovalDecision(
        "DEC-1",
        item,
        DecisionOutcome.APPROVED,
        "human",
        "architect-1",
        "evidence reviewed",
    )
    assert decision.outcome is DecisionOutcome.APPROVED
    assert item.semantic_state()[0] == "AP-1"


def test_approval_requires_governed_exception_for_mechanical_blocker():
    item = package(mechanically_eligible=False)
    with pytest.raises(ValueError):
        ApprovalDecision(
            "DEC-1", item, DecisionOutcome.APPROVED, "human", "a", "r"
        )
    decision = ApprovalDecision(
        "DEC-2",
        item,
        DecisionOutcome.APPROVED,
        "human",
        "a",
        "r",
        exception_ref="EX-1",
    )
    assert decision.exception_ref == "EX-1"


def test_policy_approval_requires_explicit_auto_approval_eligibility():
    with pytest.raises(ValueError):
        ApprovalDecision(
            "D", package(), DecisionOutcome.APPROVED, "policy", "policy-1", "r"
        )
    auto = package(auto_approval_eligible=True)
    assert ApprovalDecision(
        "D", auto, DecisionOutcome.APPROVED, "policy", "policy-1", "r"
    ).authority_type == "policy"


def test_approval_package_rejects_invalid_policy_shapes():
    with pytest.raises(ValueError):
        ApprovalRequirement("role", 0)
    with pytest.raises(ValueError):
        package(affected_scopes=())
    with pytest.raises(ValueError):
        package(mechanically_eligible=False, auto_approval_eligible=True)


def test_approval_contract_additional_validation_paths():
    requirement = ApprovalRequirement(" security ", segregation_group=" independent ")
    assert requirement.role == "security"
    assert requirement.segregation_group == "independent"

    with pytest.raises(ValueError):
        ApprovalRequirement(" ")
    with pytest.raises(TypeError):
        package(requirements=(object(),))
    with pytest.raises(ValueError):
        package(requirements=())
    with pytest.raises(ValueError):
        package(review_ids=("R", "R"))
    with pytest.raises(ValueError):
        package(policy_id=" ")

    item = package(policy_id="POL-1")
    with pytest.raises(ValueError):
        ApprovalDecision(" ", item, DecisionOutcome.REJECTED, "human", "a", "r")
    with pytest.raises(TypeError):
        ApprovalDecision("D", object(), DecisionOutcome.REJECTED, "human", "a", "r")
    with pytest.raises(TypeError):
        ApprovalDecision("D", item, "approved", "human", "a", "r")
    with pytest.raises(ValueError):
        ApprovalDecision("D", item, DecisionOutcome.REJECTED, " ", "a", "r")
    with pytest.raises(ValueError):
        ApprovalDecision(
            "D", item, DecisionOutcome.REJECTED, "human", "a", "r", exception_ref=" "
        )
    rejected = ApprovalDecision(
        "D", item, DecisionOutcome.REJECTED, "human", "a", "not approved"
    )
    assert rejected.semantic_state()[2] == "rejected"
