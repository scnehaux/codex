from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from engine.control.framework.artifacts import compile_artifact_runtime
from engine.control.framework.contracts import (
    FrameworkContractError,
    load_framework_contract_set,
)


UP = "up"
DOWN = "down"
TARGET_EXISTS = "target-exists"
APPROVED_PARENT_FOR_ACTIVE_SAD = "approved-parent-for-active-sad"
DIRECTIONS = frozenset({UP, DOWN})
AUTHORITY_REQUIREMENTS = frozenset({TARGET_EXISTS, APPROVED_PARENT_FOR_ACTIVE_SAD})
ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True, slots=True)
class RelationshipSpec:
    name: str
    metadata_field: str
    source_types: frozenset[str]
    target_types: frozenset[str]
    min_targets: int
    max_targets: int | None
    direction: str
    dag_participation: bool
    authority_requirement: str
    inverse_relation: str | None = None
    allow_self_reference: bool = False
    source_statuses_requiring_authority: frozenset[str] = frozenset()
    allowed_target_statuses: frozenset[str] = frozenset()

    @property
    def cardinality(self) -> str:
        maximum = "*" if self.max_targets is None else str(self.max_targets)
        return f"{self.min_targets}..{maximum}"


@dataclass(frozen=True, slots=True)
class RelationshipRuntimeView:
    relationships: tuple[RelationshipSpec, ...]
    by_source: Mapping[str, tuple[RelationshipSpec, ...]]
    all_fields: frozenset[str]
    ontology_sha256: str
    contract_sha256: str


_FIELDS = {
    "name",
    "metadata_field",
    "source_types",
    "target_types",
    "min_targets",
    "max_targets",
    "direction",
    "dag_participation",
    "authority_requirement",
    "inverse_relation",
    "allow_self_reference",
    "source_statuses_requiring_authority",
    "allowed_target_statuses",
}


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise FrameworkContractError(code)


def _text(value: object, code: str) -> str:
    _require(isinstance(value, str) and bool(value), code)
    return value


def _types(value: object, valid: frozenset[str], code: str) -> frozenset[str]:
    _require(isinstance(value, tuple) and bool(value), code)
    _require(all(isinstance(item, str) and item for item in value), code)
    result = frozenset(value)
    _require(len(result) == len(value), code + "-duplicate")
    _require(result <= valid, code + "-unknown")
    return result


def _statuses(value: object, valid: set[str], code: str) -> frozenset[str]:
    _require(isinstance(value, tuple), code)
    _require(all(isinstance(item, str) and item for item in value), code)
    result = frozenset(value)
    _require(len(result) == len(value), code + "-duplicate")
    _require(result <= valid, code + "-unknown")
    return result


def _canonical(specs: tuple[RelationshipSpec, ...]) -> bytes:
    rows = []
    for spec in specs:
        rows.append(
            {
                "name": spec.name,
                "metadata_field": spec.metadata_field,
                "source_types": sorted(spec.source_types),
                "target_types": sorted(spec.target_types),
                "min_targets": spec.min_targets,
                "max_targets": spec.max_targets,
                "direction": spec.direction,
                "dag_participation": spec.dag_participation,
                "authority_requirement": spec.authority_requirement,
                "inverse_relation": spec.inverse_relation,
                "allow_self_reference": spec.allow_self_reference,
                "source_statuses_requiring_authority": sorted(
                    spec.source_statuses_requiring_authority
                ),
                "allowed_target_statuses": sorted(spec.allowed_target_statuses),
            }
        )
    return json.dumps(
        rows,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def compile_relationship_runtime(repo_root: str | Path) -> RelationshipRuntimeView:
    contract = load_framework_contract_set(repo_root)
    artifact = compile_artifact_runtime(repo_root)
    valid_types = frozenset(artifact.artifact_types)
    raw = contract.families["relationships"]["data"].get("relationships")
    _require(isinstance(raw, tuple) and bool(raw), "relationship-runtime-ontology")

    specs: list[RelationshipSpec] = []
    names: set[str] = set()
    source_fields: set[tuple[str, str]] = set()
    for item in raw:
        _require(hasattr(item, "items"), "relationship-runtime-entry")
        _require(set(item) == _FIELDS, "relationship-runtime-entry-fields")
        name = _text(item["name"], "relationship-runtime-name")
        field = _text(item["metadata_field"], "relationship-runtime-field")
        _require(name not in names, "relationship-runtime-name-duplicate")
        names.add(name)

        source_types = _types(
            item["source_types"], valid_types, "relationship-runtime-source-types"
        )
        target_types = _types(
            item["target_types"], valid_types, "relationship-runtime-target-types"
        )
        for source_type in source_types:
            key = (source_type, field)
            _require(key not in source_fields, "relationship-runtime-source-field")
            source_fields.add(key)

        min_targets = item["min_targets"]
        max_targets = item["max_targets"]
        _require(
            type(min_targets) is int and min_targets >= 0,
            "relationship-runtime-min-targets",
        )
        _require(
            max_targets is None
            or (type(max_targets) is int and max_targets >= min_targets),
            "relationship-runtime-max-targets",
        )
        direction = item["direction"]
        _require(direction in DIRECTIONS, "relationship-runtime-direction")
        _require(
            type(item["dag_participation"]) is bool,
            "relationship-runtime-dag-participation",
        )
        authority = item["authority_requirement"]
        _require(
            authority in AUTHORITY_REQUIREMENTS,
            "relationship-runtime-authority-requirement",
        )
        inverse = item["inverse_relation"]
        _require(
            inverse is None or (isinstance(inverse, str) and bool(inverse)),
            "relationship-runtime-inverse",
        )
        _require(
            type(item["allow_self_reference"]) is bool,
            "relationship-runtime-self-reference",
        )

        source_statuses: set[str] = set()
        for source_type in source_types:
            source_statuses.update(artifact.lifecycle[source_type])
        target_statuses: set[str] = set()
        for target_type in target_types:
            target_statuses.update(artifact.lifecycle[target_type])
        constrained_sources = _statuses(
            item["source_statuses_requiring_authority"],
            source_statuses,
            "relationship-runtime-source-statuses",
        )
        constrained_targets = _statuses(
            item["allowed_target_statuses"],
            target_statuses,
            "relationship-runtime-target-statuses",
        )
        if authority == TARGET_EXISTS:
            _require(
                not constrained_sources and not constrained_targets,
                "relationship-runtime-unexpected-status-constraint",
            )
        else:
            _require(
                bool(constrained_sources) and bool(constrained_targets),
                "relationship-runtime-authority-status-constraint",
            )

        specs.append(
            RelationshipSpec(
                name=name,
                metadata_field=field,
                source_types=source_types,
                target_types=target_types,
                min_targets=min_targets,
                max_targets=max_targets,
                direction=direction,
                dag_participation=item["dag_participation"],
                authority_requirement=authority,
                inverse_relation=inverse,
                allow_self_reference=item["allow_self_reference"],
                source_statuses_requiring_authority=constrained_sources,
                allowed_target_statuses=constrained_targets,
            )
        )

    compiled = tuple(specs)
    by_field: dict[str, list[RelationshipSpec]] = {}
    for spec in compiled:
        by_field.setdefault(spec.metadata_field, []).append(spec)
    for spec in compiled:
        if spec.inverse_relation is None:
            continue
        candidates = by_field.get(spec.inverse_relation, [])
        _require(bool(candidates), "relationship-runtime-inverse-missing")
        _require(
            any(
                other.inverse_relation == spec.metadata_field
                and bool(spec.source_types & other.target_types)
                and bool(spec.target_types & other.source_types)
                for other in candidates
            ),
            "relationship-runtime-inverse-inconsistent",
        )

    by_source: dict[str, tuple[RelationshipSpec, ...]] = {}
    for artifact_type in artifact.artifact_types:
        by_source[artifact_type] = tuple(
            spec for spec in compiled if artifact_type in spec.source_types
        )
    all_fields = frozenset(spec.metadata_field for spec in compiled)
    return RelationshipRuntimeView(
        relationships=compiled,
        by_source=MappingProxyType(by_source),
        all_fields=all_fields,
        ontology_sha256=sha256(_canonical(compiled)).hexdigest(),
        contract_sha256=contract.canonical_sha256,
    )


@lru_cache(maxsize=1)
def relationship_runtime() -> RelationshipRuntimeView:
    return compile_relationship_runtime(ROOT)
