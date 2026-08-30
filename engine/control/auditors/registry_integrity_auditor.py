from __future__ import annotations

import ast
import glob as glob_module
import json
from pathlib import Path
from typing import Iterable

import jsonschema

from engine.control.config.severity import SeverityRule
from engine.control.governance.controls import load_control_registry, registry_structure_errors
from engine.control.governance.severity_enforcement import severity_registry_findings
from engine.control.validators.registry import VALIDATOR_REGISTRY
from engine.control.validators.schema_extensions import (
    ExtendedValidator,
    SCNEHAUX_ANNOTATION_KEYWORDS,
    SCNEHAUX_VALIDATION_KEYWORDS,
)


ARTIFACT_GUIDELINES = {
    "GDC": "GDC-005",
    "EAD": "GDC-006",
    "STD": "GDC-007",
    "PAD": "GDC-008",
    "SAD": "GDC-009",
    "ADR": "GDC-010",
    "TDD": "GDC-011",
}

# JSON Schema Draft-07 vocabulary. We keep this explicit because
# Draft7Validator.VALIDATORS contains executable validators, not the whole
# schema vocabulary (e.g. definitions/then are valid but not standalone
# validator callbacks).
_DRAFT7_KEYWORDS = frozenset(
    {
        "$id",
        "$schema",
        "$ref",
        "$comment",
        "title",
        "description",
        "default",
        "examples",
        "readOnly",
        "writeOnly",
        "multipleOf",
        "maximum",
        "exclusiveMaximum",
        "minimum",
        "exclusiveMinimum",
        "maxLength",
        "minLength",
        "pattern",
        "additionalItems",
        "items",
        "maxItems",
        "minItems",
        "uniqueItems",
        "contains",
        "maxProperties",
        "minProperties",
        "required",
        "additionalProperties",
        "definitions",
        "properties",
        "patternProperties",
        "dependencies",
        "propertyNames",
        "const",
        "enum",
        "type",
        "format",
        "contentMediaType",
        "contentEncoding",
        "if",
        "then",
        "else",
        "allOf",
        "anyOf",
        "oneOf",
        "not",
    }
)

_SCHEMA_MAP_CHILDREN = frozenset(
    {"properties", "patternProperties", "definitions"}
)
_SCHEMA_SINGLE_CHILDREN = frozenset(
    {
        "additionalProperties",
        "additionalItems",
        "contains",
        "propertyNames",
        "not",
        "if",
        "then",
        "else",
    }
)
_SCHEMA_LIST_CHILDREN = frozenset({"allOf", "anyOf", "oneOf"})


def _schema_files(schema_dir: Path) -> dict[Path, dict]:
    loaded: dict[Path, dict] = {}
    for path in sorted(schema_dir.glob("*.schema.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        jsonschema.Draft7Validator.check_schema(data)
        loaded[path] = data
    return loaded


def _iter_refs(value) -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "$ref" and isinstance(child, str):
                yield child
            yield from _iter_refs(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_refs(child)


def _resolve_pointer(document, fragment: str) -> bool:
    if not fragment:
        return True
    if not fragment.startswith("/"):
        return False

    node = document
    for raw in fragment[1:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict) and token in node:
            node = node[token]
        elif isinstance(node, list) and token.isdigit() and int(token) < len(node):
            node = node[int(token)]
        else:
            return False
    return True


def _schema_ref_findings(schemas: dict[Path, dict]) -> list[str]:
    findings: list[str] = []
    by_id = {
        str(data["$id"]): (path, data)
        for path, data in schemas.items()
        if isinstance(data.get("$id"), str)
    }
    by_name = {path.name: (path, data) for path, data in schemas.items()}

    for source_path, source in schemas.items():
        for ref in _iter_refs(source):
            base, separator, fragment = ref.partition("#")
            if not base:
                target_path, target = source_path, source
            elif base in by_id:
                target_path, target = by_id[base]
            else:
                target_info = by_name.get(base.rsplit("/", 1)[-1])
                if target_info is None:
                    findings.append(f"F02 {source_path.name}: unresolved $ref {ref}")
                    continue
                target_path, target = target_info

            if separator and not _resolve_pointer(target, fragment):
                findings.append(
                    f"F02 {source_path.name}: unresolved JSON pointer #{fragment} "
                    f"in {target_path.name}"
                )
    return findings


def _artifact_schema_map(
    schemas: dict[Path, dict],
) -> dict[str, tuple[Path, dict]]:
    result: dict[str, tuple[Path, dict]] = {}
    for path, data in schemas.items():
        for doc_type in ARTIFACT_GUIDELINES:
            if path.name.lower() == f"{doc_type.lower()}.schema.json":
                result[doc_type] = (path, data)
    return result


def _duplicate_validator_keys(registry_path: Path) -> list[str]:
    tree = ast.parse(
        registry_path.read_text(encoding="utf-8"),
        filename=str(registry_path),
    )
    keys: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "VALIDATOR_REGISTRY"
            for target in node.targets
        ):
            continue
        if isinstance(node.value, ast.Dict):
            for key in node.value.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    keys.append(key.value)

    return sorted({key for key in keys if keys.count(key) > 1})


def _validator_findings(repo_root: Path, artifact_schemas: dict) -> list[str]:
    findings: list[str] = []
    expected = set(ARTIFACT_GUIDELINES)
    schema_types = set(artifact_schemas)
    validator_types = set(VALIDATOR_REGISTRY)

    for doc_type in sorted(expected - schema_types):
        findings.append(f"F03 {doc_type}: missing artifact schema")
    for doc_type in sorted(expected - validator_types):
        findings.append(f"F03 {doc_type}: missing validator registration")
    for doc_type in sorted(schema_types - validator_types):
        findings.append(f"F04 {doc_type}: orphan artifact schema")
    for doc_type in sorted(validator_types - schema_types):
        findings.append(f"F05 {doc_type}: orphan validator registration")

    registry_path = (
        repo_root
        / 'engine' / "control" / "validators"
        / "registry.py"
    )
    for key in _duplicate_validator_keys(registry_path):
        findings.append(f"F06 {key}: duplicate validator registration")

    for doc_type in sorted(expected & validator_types):
        validator = VALIDATOR_REGISTRY[doc_type]
        actual = getattr(validator, "doc_type_name", None)
        if actual != doc_type:
            findings.append(
                f"F06 {doc_type}: validator doc_type_name mismatch ({actual!r})"
            )

    return findings


def _target_doc_findings(
    governance_dir: Path,
    artifact_schemas: dict,
) -> list[str]:
    findings: list[str] = []
    for doc_type, (path, data) in sorted(artifact_schemas.items()):
        config = data.get("config")
        target = config.get("target_doc") if isinstance(config, dict) else None
        if not isinstance(target, str) or not target:
            findings.append(f"F07 {path.name}: missing config.target_doc")
            continue

        target_path = governance_dir / target
        if not target_path.exists():
            findings.append(f"F07 {path.name}: target_doc does not exist: {target}")
            continue

        expected_prefix = ARTIFACT_GUIDELINES[doc_type]
        if not target_path.name.startswith(expected_prefix):
            findings.append(
                f"F07 {path.name}: target_doc {target_path.name} must map to "
                f"{expected_prefix}*"
            )
    return findings


def _walk_schema_keywords(schema, findings: list[str], source: str) -> None:
    if not isinstance(schema, dict):
        return

    for key, value in schema.items():
        # Governance/config namespaces are metadata payloads, not JSON Schema
        # sub-schemas, so their internal keys are intentionally opaque here.
        if key in {"config", "x-global-config", "x-titles"} or key.startswith("x-"):
            continue

        if key in SCNEHAUX_VALIDATION_KEYWORDS:
            if key not in ExtendedValidator.VALIDATORS:
                findings.append(
                    f"F08 {source}: custom validation keyword {key!r} "
                    "has no executable extension"
                )
            continue

        if key in SCNEHAUX_ANNOTATION_KEYWORDS:
            continue

        if key not in _DRAFT7_KEYWORDS:
            findings.append(f"F08 {source}: unsupported schema keyword {key!r}")
            continue

        if key in _SCHEMA_MAP_CHILDREN and isinstance(value, dict):
            for child in value.values():
                _walk_schema_keywords(child, findings, source)
        elif key in _SCHEMA_SINGLE_CHILDREN and isinstance(value, dict):
            _walk_schema_keywords(value, findings, source)
        elif key in _SCHEMA_LIST_CHILDREN and isinstance(value, list):
            for child in value:
                _walk_schema_keywords(child, findings, source)
        elif key == "items":
            if isinstance(value, dict):
                _walk_schema_keywords(value, findings, source)
            elif isinstance(value, list):
                for child in value:
                    _walk_schema_keywords(child, findings, source)
        elif key == "dependencies" and isinstance(value, dict):
            for child in value.values():
                if isinstance(child, dict):
                    _walk_schema_keywords(child, findings, source)


def _custom_keyword_findings(schemas: dict[Path, dict]) -> list[str]:
    findings: list[str] = []
    for path, schema in schemas.items():
        _walk_schema_keywords(schema, findings, path.name)
    return findings


def _severity_findings(
    engine_root: Path,
    severity_levels: dict,
    base_schema: dict | None = None,
) -> list[str]:
    del base_schema
    repo_root = engine_root.parent.parent
    return list(severity_registry_findings(repo_root, severity_levels))

def _looks_like_repo_path(value: str) -> bool:
    return "/" in value and not value.startswith(("http://", "https://"))


def _evidence_path_part(value: str) -> str:
    candidate = value.strip()
    candidate = candidate.split("::", 1)[0]
    candidate = candidate.split("#", 1)[0]
    return candidate.strip()


def _evidence_path_exists(repo_root: Path, value: str) -> bool:
    candidate = _evidence_path_part(value)
    if not candidate:
        return False

    full = repo_root / candidate
    if glob_module.has_magic(candidate):
        return bool(glob_module.glob(str(full), recursive=True))
    return full.exists()


def _control_findings(repo_root: Path) -> list[str]:
    registry_path = repo_root / "00-governance" / "normative-control-registry.yaml"
    records = load_control_registry(registry_path)
    findings = [
        f"CONTROL {message}"
        for message in registry_structure_errors(records)
    ]

    for record in records:
        if record.evidence_status != "verified":
            continue
        for evidence in (*record.implementation, *record.test_evidence):
            if not _looks_like_repo_path(evidence):
                continue
            if not _evidence_path_exists(repo_root, evidence):
                findings.append(
                    f"CONTROL {record.control_id}: evidence path does not exist: "
                    f"{evidence}"
                )
    return findings


def audit_registry_integrity(
    repo_root: str | Path,
    severity_levels: dict,
) -> tuple[str, ...]:
    root = Path(repo_root).resolve()
    governance_dir = root / "00-governance"
    schema_dir = governance_dir / "schemas"
    engine_root = root / 'engine' / 'control'

    try:
        schemas = _schema_files(schema_dir)
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        jsonschema.SchemaError,
    ) as exc:
        return (f"F01 schema boot validation failed: {exc}",)

    findings: list[str] = []
    findings.extend(_schema_ref_findings(schemas))

    artifact_schemas = _artifact_schema_map(schemas)
    findings.extend(_validator_findings(root, artifact_schemas))
    findings.extend(_target_doc_findings(governance_dir, artifact_schemas))
    findings.extend(_custom_keyword_findings(schemas))

    base_schema = schemas.get(schema_dir / "base.schema.json")
    findings.extend(
        _severity_findings(
            engine_root,
            severity_levels,
            base_schema,
        )
    )
    findings.extend(_control_findings(root))
    return tuple(findings)


def assert_registry_integrity(
    repo_root: str | Path,
    severity_levels: dict,
) -> None:
    findings = audit_registry_integrity(repo_root, severity_levels)
    if findings:
        preview = "\n".join(f"  - {finding}" for finding in findings[:20])
        suffix = (
            f"\n  ... +{len(findings) - 20} more"
            if len(findings) > 20
            else ""
        )
        raise RuntimeError(
            "Governance registry integrity audit failed:\n"
            f"{preview}{suffix}"
        )
