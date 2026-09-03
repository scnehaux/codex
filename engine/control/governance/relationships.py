from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ARTIFACT_TYPES = frozenset({"GDC", "EAD", "STD", "PAD", "SAD", "ADR", "TDD"})

UP = "up"
DOWN = "down"

TARGET_EXISTS = "target-exists"
APPROVED_PARENT_FOR_ACTIVE_SAD = "approved-parent-for-active-sad"


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class RelationshipFinding:
    code: str
    field: str
    message: str


RELATIONSHIP_REGISTRY: tuple[RelationshipSpec, ...] = (
    RelationshipSpec(
        name="gdc-governed-by",
        metadata_field="governed_by",
        source_types=frozenset({"GDC"}),
        target_types=frozenset({"GDC"}),
        min_targets=1,
        max_targets=None,
        direction=UP,
        dag_participation=True,
        authority_requirement=TARGET_EXISTS,
        allow_self_reference=True,
    ),
    RelationshipSpec(
        name="ead-governed-by",
        metadata_field="governed_by",
        source_types=frozenset({"EAD"}),
        target_types=frozenset({"GDC"}),
        min_targets=1,
        max_targets=None,
        direction=UP,
        dag_participation=True,
        authority_requirement=TARGET_EXISTS,
    ),
    RelationshipSpec(
        name="std-governed-by",
        metadata_field="governed_by",
        source_types=frozenset({"STD"}),
        target_types=frozenset({"GDC", "EAD", "PAD"}),
        min_targets=1,
        max_targets=None,
        direction=UP,
        dag_participation=True,
        authority_requirement=TARGET_EXISTS,
    ),
    RelationshipSpec(
        name="pad-governed-by",
        metadata_field="governed_by",
        source_types=frozenset({"PAD"}),
        target_types=frozenset({"GDC", "EAD", "ADR"}),
        min_targets=1,
        max_targets=None,
        direction=UP,
        dag_participation=True,
        authority_requirement=TARGET_EXISTS,
    ),
    RelationshipSpec(
        name="sad-governed-by",
        metadata_field="governed_by",
        source_types=frozenset({"SAD"}),
        target_types=frozenset({"GDC", "EAD", "STD", "ADR"}),
        min_targets=1,
        max_targets=None,
        direction=UP,
        dag_participation=True,
        authority_requirement=TARGET_EXISTS,
    ),
    RelationshipSpec(
        name="adr-governed-by",
        metadata_field="governed_by",
        source_types=frozenset({"ADR"}),
        target_types=frozenset({"GDC", "EAD", "PAD", "SAD"}),
        min_targets=1,
        max_targets=None,
        direction=UP,
        dag_participation=True,
        authority_requirement=TARGET_EXISTS,
    ),
    RelationshipSpec(
        name="pad-realizes-capability",
        metadata_field="realizes_capability",
        source_types=frozenset({"PAD"}),
        target_types=frozenset({"EAD"}),
        min_targets=1,
        max_targets=None,
        direction=UP,
        dag_participation=True,
        authority_requirement=TARGET_EXISTS,
    ),
    RelationshipSpec(
        name="sad-parent-pad",
        metadata_field="parent_pad",
        source_types=frozenset({"SAD"}),
        target_types=frozenset({"PAD"}),
        min_targets=1,
        max_targets=1,
        direction=UP,
        dag_participation=True,
        authority_requirement=APPROVED_PARENT_FOR_ACTIVE_SAD,
        inverse_relation="fulfilled_by",
        source_statuses_requiring_authority=frozenset({"draft", "approved"}),
        allowed_target_statuses=frozenset({"approved"}),
    ),
    RelationshipSpec(
        name="tdd-parent-sad",
        metadata_field="parent_sad",
        source_types=frozenset({"TDD"}),
        target_types=frozenset({"SAD"}),
        min_targets=1,
        max_targets=None,
        direction=UP,
        dag_participation=True,
        authority_requirement=TARGET_EXISTS,
    ),
    RelationshipSpec(
        name="pad-fulfilled-by",
        metadata_field="fulfilled_by",
        source_types=frozenset({"PAD"}),
        target_types=frozenset({"SAD"}),
        min_targets=0,
        max_targets=None,
        direction=DOWN,
        dag_participation=False,
        authority_requirement=TARGET_EXISTS,
        inverse_relation="parent_pad",
    ),
)

ALL_RELATION_FIELDS = frozenset(spec.metadata_field for spec in RELATIONSHIP_REGISTRY)


def artifact_type_from_id(doc_id: Any) -> str | None:
    if not isinstance(doc_id, str):
        return None
    prefix = doc_id.strip().split("-", 1)[0].upper()
    return prefix if prefix in ARTIFACT_TYPES else None


def normalize_relation_values(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def relationship_specs_for_source(
    source_type: str | None,
) -> tuple[RelationshipSpec, ...]:
    normalized = str(source_type or "").upper()
    return tuple(
        spec for spec in RELATIONSHIP_REGISTRY if normalized in spec.source_types
    )


def relationship_spec_for(
    source_type: str | None,
    metadata_field: str,
) -> RelationshipSpec | None:
    matches = tuple(
        spec
        for spec in relationship_specs_for_source(source_type)
        if spec.metadata_field == metadata_field
    )
    if len(matches) > 1:
        raise RuntimeError(
            f"Relationship registry is ambiguous for source={source_type!r}, "
            f"field={metadata_field!r}"
        )
    return matches[0] if matches else None


def relationship_fields_for_source(source_type: str | None) -> frozenset[str]:
    specs = relationship_specs_for_source(source_type)
    if not specs:
        return ALL_RELATION_FIELDS
    return frozenset(spec.metadata_field for spec in specs)


def dag_relation_specs_for_source(
    source_type: str | None,
) -> tuple[RelationshipSpec, ...]:
    return tuple(
        spec
        for spec in relationship_specs_for_source(source_type)
        if spec.dag_participation
    )


def relationship_contract_findings(
    source_id: str,
    source_meta: dict | None,
    all_doc_metadata: dict,
) -> list[RelationshipFinding]:
    if not isinstance(source_meta, dict):
        return []

    source_type = artifact_type_from_id(source_id)
    applicable = relationship_specs_for_source(source_type)
    applicable_fields = {spec.metadata_field for spec in applicable}
    findings: list[RelationshipFinding] = []

    for field in sorted(ALL_RELATION_FIELDS):
        if field in source_meta and field not in applicable_fields:
            findings.append(
                RelationshipFinding(
                    code="unsupported_source",
                    field=field,
                    message=(
                        f"{source_type or 'UNKNOWN'} '{source_id}' is not allowed "
                        f"to declare relationship field '{field}'."
                    ),
                )
            )

    for spec in applicable:
        values = normalize_relation_values(source_meta.get(spec.metadata_field))
        count = len(values)

        if count < spec.min_targets:
            findings.append(
                RelationshipFinding(
                    code="missing_required",
                    field=spec.metadata_field,
                    message=(
                        f"{source_type} '{source_id}' relationship "
                        f"'{spec.metadata_field}' requires cardinality "
                        f"{spec.cardinality}, found {count} target(s)."
                    ),
                )
            )
            continue

        if spec.max_targets is not None and count > spec.max_targets:
            findings.append(
                RelationshipFinding(
                    code="too_many_targets",
                    field=spec.metadata_field,
                    message=(
                        f"{source_type} '{source_id}' relationship "
                        f"'{spec.metadata_field}' allows cardinality "
                        f"{spec.cardinality}, found {count} target(s)."
                    ),
                )
            )

        seen: set[str] = set()
        for target_id in values:
            if not isinstance(target_id, str):
                findings.append(
                    RelationshipFinding(
                        code="invalid_target_type",
                        field=spec.metadata_field,
                        message=(
                            f"{source_type} '{source_id}' relationship "
                            f"'{spec.metadata_field}' contains a non-string target."
                        ),
                    )
                )
                continue

            if target_id in seen:
                findings.append(
                    RelationshipFinding(
                        code="duplicate_target",
                        field=spec.metadata_field,
                        message=(
                            f"{source_type} '{source_id}' relationship "
                            f"'{spec.metadata_field}' repeats target '{target_id}'."
                        ),
                    )
                )
                continue
            seen.add(target_id)

            if target_id == source_id and not spec.allow_self_reference:
                findings.append(
                    RelationshipFinding(
                        code="self_reference",
                        field=spec.metadata_field,
                        message=(
                            f"{source_type} '{source_id}' relationship "
                            f"'{spec.metadata_field}' cannot reference itself."
                        ),
                    )
                )
                continue

            target_type = artifact_type_from_id(target_id)
            if target_type not in spec.target_types:
                allowed = ", ".join(sorted(spec.target_types))
                findings.append(
                    RelationshipFinding(
                        code="invalid_target_type",
                        field=spec.metadata_field,
                        message=(
                            f"{source_type} '{source_id}' relationship "
                            f"'{spec.metadata_field}' targets '{target_id}' "
                            f"({target_type or 'UNKNOWN'}); allowed target types: "
                            f"{allowed}."
                        ),
                    )
                )
                continue

            target_meta = all_doc_metadata.get(target_id)
            if not isinstance(target_meta, dict):
                continue

            if spec.authority_requirement == APPROVED_PARENT_FOR_ACTIVE_SAD:
                source_status = str(source_meta.get("status", "")).strip().lower()
                target_status = str(target_meta.get("status", "")).strip().lower()
                if (
                    source_status in spec.source_statuses_requiring_authority
                    and target_status not in spec.allowed_target_statuses
                ):
                    findings.append(
                        RelationshipFinding(
                            code="authority_violation",
                            field=spec.metadata_field,
                            message=(
                                f"{source_type} '{source_id}' has status "
                                f"'{source_status}' but parent '{target_id}' has "
                                f"status '{target_status or 'unknown'}'. "
                                "Active SAD design requires an approved parent PAD."
                            ),
                        )
                    )

    return findings
