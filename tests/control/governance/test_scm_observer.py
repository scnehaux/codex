from __future__ import annotations

import pytest

from engine.control.governance.scm_observer import (
    SCMLiveStateEvidence,
    compare_effective_policy,
    desired_effective_policy,
    evidence_dict,
    validate_live_evidence,
)
from engine.control.governance.scm_policy import assert_scm_enforcement_policy
from tests.support.repository import REPOSITORY_ROOT


POLICY = assert_scm_enforcement_policy(REPOSITORY_ROOT)


def test_desired_effective_policy_is_provider_neutral_projection():
    effective = desired_effective_policy(POLICY)
    assert effective.required_approvals == 0
    assert effective.require_qualified_owner_approval is False
    assert effective.candidate_check_context == "Governance Qualification"


def test_compare_effective_policy_reports_only_changed_fields():
    desired = desired_effective_policy(POLICY)
    observed = type(desired)(
        **{
            **{
                field: getattr(desired, field) for field in desired.__dataclass_fields__
            },
            "force_push_allowed": True,
        }
    )
    assert compare_effective_policy(desired, observed) == ("force_push_allowed",)


def test_live_evidence_distinguishes_not_installed_from_unknown():
    not_installed = SCMLiveStateEvidence(
        provider="github",
        repository="scnehaux/codex",
        observed_revision="abc",
        observation_time="2026-09-05T00:00:00+00:00",
        observation_state="observed",
        installed_state="not-installed",
        enforcement_state="unknown",
        effective_policy=None,
        drift=("ruleset-not-installed",),
        notes=(),
    )
    validate_live_evidence(not_installed)
    assert not_installed.drift_state == "drifted"

    unknown = SCMLiveStateEvidence(
        provider="github",
        repository="scnehaux/codex",
        observed_revision="unknown",
        observation_time="2026-09-05T00:00:00+00:00",
        observation_state="unknown",
        installed_state="unknown",
        enforcement_state="unknown",
        effective_policy=None,
        drift=(),
        notes=(),
    )
    validate_live_evidence(unknown)
    assert unknown.drift_state == "unknown"


def test_invalid_installed_evidence_fails_closed():
    evidence = SCMLiveStateEvidence(
        provider="github",
        repository="scnehaux/codex",
        observed_revision="abc",
        observation_time="2026-09-05T00:00:00+00:00",
        observation_state="observed",
        installed_state="installed",
        enforcement_state="active",
        effective_policy=None,
        drift=(),
        notes=(),
    )
    with pytest.raises(ValueError, match="requires effective_policy"):
        validate_live_evidence(evidence)


def test_evidence_dict_materializes_drift_state():
    evidence = SCMLiveStateEvidence(
        provider="github",
        repository="scnehaux/codex",
        observed_revision="abc",
        observation_time="2026-09-05T00:00:00+00:00",
        observation_state="observed",
        installed_state="not-installed",
        enforcement_state="inactive",
        effective_policy=None,
        drift=("ruleset-not-installed",),
        notes=(),
    )
    assert evidence_dict(evidence)["drift_state"] == "drifted"


def test_validation_error_paths_are_covered():
    desired = desired_effective_policy(POLICY)

    base = dict(
        provider="github",
        repository="scnehaux/codex",
        observed_revision="abc",
        observation_time="2026-09-05T00:00:00+00:00",
        observation_state="observed",
        installed_state="not-installed",
        enforcement_state="inactive",
        effective_policy=None,
        drift=("ruleset-not-installed",),
        notes=(),
    )

    cases = (
        ({"provider": ""}, "provider must be non-blank"),
        ({"repository": ""}, "repository must be non-blank"),
        ({"observed_revision": ""}, "observed_revision must be non-blank"),
        ({"observation_time": ""}, "observation_time must be non-blank"),
        ({"observation_state": "broken"}, "invalid observation_state"),
        ({"installed_state": "broken"}, "invalid installed_state"),
        ({"enforcement_state": "broken"}, "invalid enforcement_state"),
        (
            {"effective_policy": desired},
            "not-installed state cannot contain effective_policy",
        ),
    )

    for override, message in cases:
        evidence = SCMLiveStateEvidence(**{**base, **override})
        with pytest.raises(ValueError, match=message):
            validate_live_evidence(evidence)
