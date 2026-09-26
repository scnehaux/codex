from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping
import re


_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


class FrameworkVersionError(ValueError):
    pass


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise FrameworkVersionError(code)


@dataclass(frozen=True, order=True, slots=True)
class SemanticVersion:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, value: object, code: str = "framework-version-semver") -> "SemanticVersion":
        _require(isinstance(value, str), code)
        match = _SEMVER.fullmatch(value)
        _require(match is not None, code)
        return cls(*(int(part) for part in match.groups()))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


@dataclass(frozen=True, slots=True)
class VersionRange:
    minimum: SemanticVersion
    maximum_exclusive: SemanticVersion

    def __post_init__(self) -> None:
        _require(self.minimum < self.maximum_exclusive, "framework-version-range-order")

    def contains(self, version: SemanticVersion) -> bool:
        return self.minimum <= version < self.maximum_exclusive


@dataclass(frozen=True, slots=True)
class MigrationPoint:
    framework: SemanticVersion
    ontology: SemanticVersion


@dataclass(frozen=True, slots=True)
class MigrationRule:
    source: MigrationPoint
    target: MigrationPoint
    classification: str
    action: str


@dataclass(frozen=True, slots=True)
class DeprecationPolicy:
    mode: str
    minimum_notice_minor_releases: int
    removal_requires_major_bump: bool
    declarations: tuple[Mapping[str, str], ...]


@dataclass(frozen=True, slots=True)
class CompatibilityPolicy:
    backward_compatibility: str
    migration_mode: str
    history_origin: MigrationPoint
    migration_rules: tuple[MigrationRule, ...]
    deprecation: DeprecationPolicy

    def migration_path(
        self,
        *,
        source_framework: str,
        source_ontology: str,
        target_framework: str,
        target_ontology: str,
    ) -> tuple[MigrationRule, ...]:
        source = MigrationPoint(
            SemanticVersion.parse(source_framework),
            SemanticVersion.parse(source_ontology, "ontology-version-semver"),
        )
        target = MigrationPoint(
            SemanticVersion.parse(target_framework),
            SemanticVersion.parse(target_ontology, "ontology-version-semver"),
        )
        if source == target:
            return ()
        by_source: dict[MigrationPoint, list[MigrationRule]] = {}
        for rule in self.migration_rules:
            by_source.setdefault(rule.source, []).append(rule)
        frontier: list[tuple[MigrationPoint, tuple[MigrationRule, ...]]] = [(source, ())]
        visited = {source}
        while frontier:
            point, path = frontier.pop(0)
            for rule in sorted(
                by_source.get(point, ()),
                key=lambda item: (
                    item.target.framework,
                    item.target.ontology,
                    item.classification,
                    item.action,
                ),
            ):
                next_path = path + (rule,)
                if rule.target == target:
                    return next_path
                if rule.target not in visited:
                    visited.add(rule.target)
                    frontier.append((rule.target, next_path))
        raise FrameworkVersionError("framework-migration-path-missing")


def _exact(value: object, fields: set[str], code: str) -> Mapping:
    _require(isinstance(value, dict), code + "-mapping")
    _require(set(value) == fields, code + "-fields")
    return value


def load_version_range(value: object, *, code: str) -> VersionRange:
    raw = _exact(value, {"minimum", "maximum_exclusive"}, code)
    return VersionRange(
        SemanticVersion.parse(raw["minimum"], code + "-minimum"),
        SemanticVersion.parse(raw["maximum_exclusive"], code + "-maximum"),
    )


def _migration_point(value: object, code: str) -> MigrationPoint:
    raw = _exact(value, {"framework", "ontology"}, code)
    return MigrationPoint(
        SemanticVersion.parse(raw["framework"], code + "-framework"),
        SemanticVersion.parse(raw["ontology"], code + "-ontology"),
    )


def load_compatibility_policy(
    value: object,
    *,
    current_framework: str,
    current_ontology: str,
) -> CompatibilityPolicy:
    raw = _exact(
        value,
        {
            "backward_compatibility",
            "migration_mode",
            "history_origin",
            "migration_rules",
            "deprecation",
        },
        "framework-compatibility",
    )
    _require(
        raw["backward_compatibility"] == "same-major",
        "framework-backward-compatibility-policy",
    )
    _require(raw["migration_mode"] == "explicit-only", "framework-migration-mode")
    origin = _migration_point(raw["history_origin"], "framework-history-origin")

    rules_raw = raw["migration_rules"]
    _require(isinstance(rules_raw, list), "framework-migration-rules")
    rules: list[MigrationRule] = []
    edges: set[tuple[MigrationPoint, MigrationPoint]] = set()
    for item in rules_raw:
        item = _exact(
            item,
            {"from", "to", "classification", "action"},
            "framework-migration-rule",
        )
        source = _migration_point(item["from"], "framework-migration-from")
        target = _migration_point(item["to"], "framework-migration-to")
        edge = (source, target)
        _require(source != target, "framework-migration-self-edge")
        _require(edge not in edges, "framework-migration-duplicate-edge")
        edges.add(edge)
        classification = item["classification"]
        action = item["action"]
        _require(
            classification in {"backward-compatible", "breaking"},
            "framework-migration-classification",
        )
        _require(
            action in {"no-transform", "explicit-transform-required"},
            "framework-migration-action",
        )
        if classification == "backward-compatible":
            _require(
                source.framework.major == target.framework.major
                and source.ontology.major == target.ontology.major,
                "framework-compatible-migration-major-drift",
            )
            _require(action == "no-transform", "framework-compatible-migration-action")
        else:
            _require(
                source.framework.major != target.framework.major
                or source.ontology.major != target.ontology.major,
                "framework-breaking-migration-needs-major-bump",
            )
            _require(
                action == "explicit-transform-required",
                "framework-breaking-migration-action",
            )
        rules.append(MigrationRule(source, target, classification, action))

    deprecation_raw = _exact(
        raw["deprecation"],
        {
            "mode",
            "minimum_notice_minor_releases",
            "removal_requires_major_bump",
            "declarations",
        },
        "framework-deprecation",
    )
    _require(deprecation_raw["mode"] == "explicit", "framework-deprecation-mode")
    notice = deprecation_raw["minimum_notice_minor_releases"]
    _require(type(notice) is int and notice >= 1, "framework-deprecation-notice")
    _require(
        deprecation_raw["removal_requires_major_bump"] is True,
        "framework-deprecation-removal-policy",
    )
    declarations_raw = deprecation_raw["declarations"]
    _require(isinstance(declarations_raw, list), "framework-deprecation-declarations")
    declarations: list[Mapping[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for declaration in declarations_raw:
        declaration = _exact(
            declaration,
            {"kind", "id", "deprecated_in", "remove_not_before"},
            "framework-deprecation-declaration",
        )
        _require(
            declaration["kind"] in {"artifact-type", "relationship-type", "extension-point"},
            "framework-deprecation-kind",
        )
        _require(
            isinstance(declaration["id"], str) and bool(declaration["id"]),
            "framework-deprecation-id",
        )
        deprecated = SemanticVersion.parse(
            declaration["deprecated_in"], "framework-deprecation-version"
        )
        removal = SemanticVersion.parse(
            declaration["remove_not_before"], "framework-removal-version"
        )
        _require(
            removal.major > deprecated.major,
            "framework-deprecation-removal-major-bump",
        )
        key = (declaration["kind"], declaration["id"])
        _require(key not in seen, "framework-deprecation-duplicate")
        seen.add(key)
        declarations.append(MappingProxyType(dict(declaration)))

    policy = CompatibilityPolicy(
        backward_compatibility="same-major",
        migration_mode="explicit-only",
        history_origin=origin,
        migration_rules=tuple(rules),
        deprecation=DeprecationPolicy(
            mode="explicit",
            minimum_notice_minor_releases=notice,
            removal_requires_major_bump=True,
            declarations=tuple(declarations),
        ),
    )
    current = MigrationPoint(
        SemanticVersion.parse(current_framework),
        SemanticVersion.parse(current_ontology, "ontology-version-semver"),
    )
    policy.migration_path(
        source_framework=str(origin.framework),
        source_ontology=str(origin.ontology),
        target_framework=str(current.framework),
        target_ontology=str(current.ontology),
    )
    return policy


def assert_range_contains(
    value: object,
    *,
    version: str,
    code: str,
) -> VersionRange:
    range_ = load_version_range(value, code=code)
    parsed = SemanticVersion.parse(version, code + "-version")
    _require(range_.contains(parsed), code + "-incompatible")
    return range_
