from __future__ import annotations

import pytest

from engine.control.framework.versioning import (
    FrameworkVersionError,
    SemanticVersion,
    assert_range_contains,
    load_compatibility_policy,
)


def policy():
    return {
        "backward_compatibility": "same-major",
        "migration_mode": "explicit-only",
        "history_origin": {"framework": "0.1.0", "ontology": "1.0.0"},
        "migration_rules": [
            {
                "from": {"framework": "0.1.0", "ontology": "1.0.0"},
                "to": {"framework": "0.2.0", "ontology": "1.0.0"},
                "classification": "backward-compatible",
                "action": "no-transform",
            }
        ],
        "deprecation": {
            "mode": "explicit",
            "minimum_notice_minor_releases": 1,
            "removal_requires_major_bump": True,
            "declarations": [],
        },
    }


def test_semantic_version_is_strict_and_ordered():
    assert SemanticVersion.parse("0.2.0") < SemanticVersion.parse("1.0.0")
    for value in ("0.2", "v0.2.0", "00.2.0", True, None):
        with pytest.raises(FrameworkVersionError):
            SemanticVersion.parse(value)


def test_range_is_half_open_and_strict():
    value = {"minimum": "0.2.0", "maximum_exclusive": "1.0.0"}
    assert assert_range_contains(value, version="0.2.0", code="range")
    assert assert_range_contains(value, version="0.9.9", code="range")
    with pytest.raises(FrameworkVersionError, match="range-incompatible"):
        assert_range_contains(value, version="1.0.0", code="range")
    with pytest.raises(FrameworkVersionError, match="framework-version-range-order"):
        assert_range_contains(
            {"minimum": "1.0.0", "maximum_exclusive": "0.2.0"},
            version="0.2.0",
            code="range",
        )


def test_current_migration_path_is_explicit_and_reproducible():
    loaded = load_compatibility_policy(
        policy(),
        current_framework="0.2.0",
        current_ontology="1.0.0",
    )
    path = loaded.migration_path(
        source_framework="0.1.0",
        source_ontology="1.0.0",
        target_framework="0.2.0",
        target_ontology="1.0.0",
    )
    assert len(path) == 1
    assert path[0].classification == "backward-compatible"
    assert path[0].action == "no-transform"


def test_missing_migration_is_never_inferred():
    value = policy()
    value["migration_rules"] = []
    with pytest.raises(FrameworkVersionError, match="framework-migration-path-missing"):
        load_compatibility_policy(
            value,
            current_framework="0.2.0",
            current_ontology="1.0.0",
        )


def test_duplicate_migration_edge_fails_closed():
    value = policy()
    value["migration_rules"].append(dict(value["migration_rules"][0]))
    with pytest.raises(FrameworkVersionError, match="framework-migration-duplicate-edge"):
        load_compatibility_policy(
            value,
            current_framework="0.2.0",
            current_ontology="1.0.0",
        )


def test_backward_compatible_rule_cannot_cross_major():
    value = policy()
    value["migration_rules"][0]["to"]["framework"] = "1.0.0"
    with pytest.raises(
        FrameworkVersionError, match="framework-compatible-migration-major-drift"
    ):
        load_compatibility_policy(
            value,
            current_framework="1.0.0",
            current_ontology="1.0.0",
        )


def test_breaking_rule_requires_major_bump_and_explicit_transform():
    value = policy()
    value["migration_rules"][0].update(
        classification="breaking", action="explicit-transform-required"
    )
    with pytest.raises(
        FrameworkVersionError, match="framework-breaking-migration-needs-major-bump"
    ):
        load_compatibility_policy(
            value,
            current_framework="0.2.0",
            current_ontology="1.0.0",
        )

    value = policy()
    value["migration_rules"][0]["to"]["framework"] = "1.0.0"
    value["migration_rules"][0]["classification"] = "breaking"
    with pytest.raises(FrameworkVersionError, match="framework-breaking-migration-action"):
        load_compatibility_policy(
            value,
            current_framework="1.0.0",
            current_ontology="1.0.0",
        )


def test_deprecation_removal_requires_explicit_major_boundary():
    value = policy()
    value["deprecation"]["declarations"] = [
        {
            "kind": "artifact-type",
            "id": "LEGACY",
            "deprecated_in": "0.2.0",
            "remove_not_before": "0.3.0",
        }
    ]
    with pytest.raises(
        FrameworkVersionError, match="framework-deprecation-removal-major-bump"
    ):
        load_compatibility_policy(
            value,
            current_framework="0.2.0",
            current_ontology="1.0.0",
        )

    value["deprecation"]["declarations"][0]["remove_not_before"] = "1.0.0"
    loaded = load_compatibility_policy(
        value,
        current_framework="0.2.0",
        current_ontology="1.0.0",
    )
    assert loaded.deprecation.declarations[0]["id"] == "LEGACY"
