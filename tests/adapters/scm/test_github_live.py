from __future__ import annotations

import pytest

from engine.adapters.scm.github_live import (
    find_ruleset_summary,
    normalize_github_ruleset,
    observe_github_state,
)
from engine.control.governance.scm_policy import assert_scm_enforcement_policy
from tests.support.repository import REPOSITORY_ROOT


POLICY = assert_scm_enforcement_policy(REPOSITORY_ROOT)


def _detail():
    return {
        "name": "main-governance",
        "enforcement": "active",
        "bypass_actors": [],
        "rules": [
            {"type": "deletion"},
            {"type": "non_fast_forward"},
            {"type": "required_linear_history"},
            {
                "type": "pull_request",
                "parameters": {
                    "allowed_merge_methods": ["squash"],
                    "dismiss_stale_reviews_on_push": True,
                    "require_code_owner_review": False,
                    "require_last_push_approval": False,
                    "required_approving_review_count": 0,
                    "required_review_thread_resolution": True,
                },
            },
            {
                "type": "required_status_checks",
                "parameters": {
                    "strict_required_status_checks_policy": True,
                    "required_status_checks": [
                        {"context": "Governance Qualification"},
                        {
                            "context": "Codex Governance Authority",
                            "integration_id": 4242,
                        },
                    ],
                },
            },
        ],
    }


def test_find_ruleset_summary_is_strict():
    assert find_ruleset_summary([]) is None
    assert find_ruleset_summary([{"id": 1, "name": "main-governance"}])["id"] == 1
    with pytest.raises(ValueError, match="multiple"):
        find_ruleset_summary(
            [
                {"id": 1, "name": "main-governance"},
                {"id": 2, "name": "main-governance"},
            ]
        )


def test_normalized_ruleset_matches_current_effective_policy():
    effective = normalize_github_ruleset(_detail(), POLICY)
    assert effective.force_push_allowed is False
    assert effective.required_approvals == 0
    assert effective.candidate_check_context == "Governance Qualification"
    assert effective.external_authority_check_required is True
    assert effective.external_authority_check_context == "Codex Governance Authority"
    assert effective.external_authority_source_bound is True


def test_absent_ruleset_is_observed_not_installed_and_drifted():
    evidence = observe_github_state(
        repository="scnehaux/codex",
        observed_revision="abc",
        policy=POLICY,
        rulesets_payload=[],
        ruleset_detail=None,
        branch_protection_error="HTTP 403",
        observation_time="2026-09-05T00:00:00+00:00",
    )
    assert evidence.observation_state == "observed"
    assert evidence.installed_state == "not-installed"
    assert evidence.enforcement_state == "unknown"
    assert evidence.drift_state == "drifted"


def test_inaccessible_rulesets_are_unknown_not_absent():
    evidence = observe_github_state(
        repository="scnehaux/codex",
        observed_revision="unknown",
        policy=POLICY,
        rulesets_payload=None,
        ruleset_detail=None,
        rulesets_error="HTTP 403",
        observation_time="2026-09-05T00:00:00+00:00",
    )
    assert evidence.observation_state == "unknown"
    assert evidence.installed_state == "unknown"
    assert evidence.drift_state == "unknown"


def test_aligned_live_ruleset_has_zero_semantic_drift():
    evidence = observe_github_state(
        repository="scnehaux/codex",
        observed_revision="abc",
        policy=POLICY,
        rulesets_payload=[{"id": 7, "name": "main-governance"}],
        ruleset_detail=_detail(),
        observation_time="2026-09-05T00:00:00+00:00",
    )
    assert evidence.installed_state == "installed"
    assert evidence.enforcement_state == "active"
    assert evidence.drift_state == "aligned"


def test_github_live_fail_closed_and_partial_observation_paths():
    with pytest.raises(ValueError, match="response must be a list"):
        find_ruleset_summary({})

    with pytest.raises(ValueError, match="detail must be a mapping"):
        normalize_github_ruleset({}, POLICY)

    empty_rules = normalize_github_ruleset({"rules": None}, POLICY)
    assert empty_rules.changes_require_review is False
    assert empty_rules.force_push_allowed is True
    assert empty_rules.external_authority_check_required is False
    assert empty_rules.external_authority_source_bound is False

    missing_external = _detail()
    status = next(
        rule
        for rule in missing_external["rules"]
        if rule["type"] == "required_status_checks"
    )
    status["parameters"]["required_status_checks"] = [
        {"context": "Governance Qualification"}
    ]
    evidence = observe_github_state(
        repository="scnehaux/codex",
        observed_revision="abc",
        policy=POLICY,
        rulesets_payload=[{"id": 7, "name": "main-governance"}],
        ruleset_detail=missing_external,
        observation_time="2026-09-05T00:00:00+00:00",
    )
    assert "external_authority_check_required" in evidence.drift
    assert "external_authority_check_context" in evidence.drift
    assert "external_authority_source_bound" in evidence.drift

    unbound_external = _detail()
    status = next(
        rule
        for rule in unbound_external["rules"]
        if rule["type"] == "required_status_checks"
    )
    status["parameters"]["required_status_checks"][1].pop("integration_id")
    evidence = observe_github_state(
        repository="scnehaux/codex",
        observed_revision="abc",
        policy=POLICY,
        rulesets_payload=[{"id": 7, "name": "main-governance"}],
        ruleset_detail=unbound_external,
        observation_time="2026-09-05T00:00:00+00:00",
    )
    assert evidence.drift == ("external_authority_source_bound",)

    evidence = observe_github_state(
        repository="scnehaux/codex",
        observed_revision="abc",
        policy=POLICY,
        rulesets_payload=[{"id": 7, "name": "main-governance"}],
        ruleset_detail=None,
        observation_time="2026-09-05T00:00:00+00:00",
    )
    assert evidence.observation_state == "unknown"
    assert evidence.installed_state == "installed"
    assert evidence.enforcement_state == "unknown"
