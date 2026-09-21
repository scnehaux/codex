from __future__ import annotations

from dataclasses import dataclass

from engine.control.framework.artifacts import artifact_type_from_id
from engine.control.framework.relationships import (
    APPROVED_PARENT_FOR_ACTIVE_SAD,
    RelationshipSpec,
    relationship_runtime,
)


# Compatibility projections only; ontology semantics are authored in relationships.yaml.
RELATIONSHIP_REGISTRY: tuple[RelationshipSpec, ...] = (
    relationship_runtime().relationships
)
ALL_RELATION_FIELDS = relationship_runtime().all_fields


@dataclass(frozen=True)
class RelationshipFinding:
    code: str
    field: str
    message: str


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
    return relationship_runtime().by_source.get(normalized, ())


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
