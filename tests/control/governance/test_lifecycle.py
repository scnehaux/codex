import pytest

from engine.control.governance.lifecycle import (
    BASELINE_BEARING,
    FULL,
    PRE_BASELINE,
    RELAXED,
    RETIRED,
    TERMINAL_NON_BASELINE,
    is_baseline_bearing,
    lifecycle_age_policy,
    lifecycle_policy,
    semantic_lifecycle,
    validation_profile,
)


@pytest.mark.parametrize(
    ("doc_type", "status", "semantic", "profile"),
    [
        ("GDC", "draft", PRE_BASELINE, FULL),
        ("EAD", "draft", PRE_BASELINE, RELAXED),
        ("STD", "draft", PRE_BASELINE, RELAXED),
        ("PAD", "chartered", PRE_BASELINE, FULL),
        ("PAD", "draft", PRE_BASELINE, RELAXED),
        ("SAD", "draft", PRE_BASELINE, RELAXED),
        ("TDD", "draft", PRE_BASELINE, RELAXED),
        ("ADR", "proposed", PRE_BASELINE, FULL),
        ("ADR", "accepted", BASELINE_BEARING, FULL),
        ("ADR", "rejected", TERMINAL_NON_BASELINE, FULL),
        ("ADR", "superseded", RETIRED, FULL),
        ("GDC", "deprecated", RETIRED, FULL),
    ],
)
def test_lifecycle_registry_is_artifact_aware(doc_type, status, semantic, profile):
    policy = lifecycle_policy(doc_type, status)
    assert policy is not None
    assert policy.semantic_class == semantic
    assert policy.validation_profile == profile
    assert semantic_lifecycle(doc_type, status) == semantic
    assert validation_profile(doc_type, status) == profile


def test_same_literal_draft_can_have_different_validation_profiles():
    assert validation_profile("GDC", "draft") == FULL
    assert validation_profile("EAD", "draft") == RELAXED


def test_unknown_state_fails_closed_to_full_validation():
    assert lifecycle_policy("GDC", "not-a-state") is None
    assert semantic_lifecycle("GDC", "not-a-state") is None
    assert validation_profile("GDC", "not-a-state") == FULL
    assert validation_profile("UNKNOWN", "draft") == FULL


@pytest.mark.parametrize(
    ("doc_type", "status", "expected"),
    [
        ("ADR", "accepted", True),
        ("ADR", "superseded", True),
        ("GDC", "deprecated", True),
        ("GDC", "approved", True),
        ("ADR", "rejected", False),
        ("GDC", "draft", False),
    ],
)
def test_baseline_bearing_is_semantic_not_literal(doc_type, status, expected):
    assert is_baseline_bearing(doc_type, status) is expected


@pytest.mark.parametrize("doc_type", ["EAD", "STD", "PAD", "SAD", "TDD"])
def test_ordinary_architecture_draft_has_wip_age_policy(doc_type):
    policy = lifecycle_age_policy(doc_type, "draft")
    assert policy is not None
    assert policy.depend_on == "created_date"
    assert policy.max_age_days == 30


@pytest.mark.parametrize(
    ("doc_type", "status"),
    [
        ("GDC", "draft"),
        ("GDC", "deprecated"),
        ("EAD", "deprecated"),
        ("ADR", "proposed"),
        ("ADR", "superseded"),
        ("UNKNOWN", "draft"),
    ],
)
def test_states_without_explicit_age_policy_have_no_generic_ttl(doc_type, status):
    assert lifecycle_age_policy(doc_type, status) is None
