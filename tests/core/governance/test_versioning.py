from __future__ import annotations

import pytest

from engine.core.governance.versioning import SemanticVersion


def test_semantic_version_parses_canonical_values():
    version = SemanticVersion.parse("12.3.45")
    assert (version.major, version.minor, version.patch) == (12, 3, 45)
    assert str(version) == "12.3.45"


@pytest.mark.parametrize(
    "value",
    (
        "1",
        "1.2",
        "1.2.3.4",
        "01.2.3",
        "1.02.3",
        "1.2.03",
        "v1.2.3",
        "1.2.3-alpha",
        "",
    ),
)
def test_semantic_version_rejects_noncanonical_values(value):
    with pytest.raises(ValueError):
        SemanticVersion.parse(value)


def test_semantic_version_requires_string():
    with pytest.raises(TypeError):
        SemanticVersion.parse(1)


def test_semantic_version_orders_lexicographically_by_components():
    assert SemanticVersion.parse("0.9.9") < SemanticVersion.parse("1.0.0")
    assert SemanticVersion.parse("1.2.9") < SemanticVersion.parse("1.3.0")
    assert SemanticVersion.parse("1.3.0") < SemanticVersion.parse("1.3.1")


def test_semantic_version_rejects_negative_components():
    with pytest.raises(ValueError):
        SemanticVersion(-1, 0, 0)
