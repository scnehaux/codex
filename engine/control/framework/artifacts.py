from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import importlib
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from engine.control.framework.contracts import (
    FrameworkContractError,
    FrameworkContractSet,
    load_framework_contract_set,
)


ROOT = Path(__file__).resolve().parents[3]
PRE_BASELINE = "pre-baseline"
BASELINE_BEARING = "baseline-bearing"
RETIRED = "retired"
TERMINAL_NON_BASELINE = "terminal-nonbaseline"
FULL = "full"
RELAXED = "relaxed"
SEMANTIC_CLASSES = frozenset(
    {PRE_BASELINE, BASELINE_BEARING, RETIRED, TERMINAL_NON_BASELINE}
)
VALIDATION_PROFILES = frozenset({FULL, RELAXED})


@dataclass(frozen=True, slots=True)
class AgePolicy:
    depend_on: str
    max_age_days: int
    error_message: str


@dataclass(frozen=True, slots=True)
class LifecyclePolicy:
    semantic_class: str
    validation_profile: str
    age_policy: AgePolicy | None = None


@dataclass(frozen=True, slots=True)
class ValidatorBinding:
    module: str
    class_name: str


@dataclass(frozen=True, slots=True)
class ArtifactRuntimeView:
    artifact_types: tuple[str, ...]
    artifact_families: Mapping[str, str]
    artifact_directories: Mapping[str, str]
    lifecycle: Mapping[str, Mapping[str, LifecyclePolicy]]
    schema_bindings: Mapping[str, str]
    validator_bindings: Mapping[str, ValidatorBinding]
    contract_sha256: str


def _plain_family(contract: FrameworkContractSet, family: str):
    return contract.families[family]["data"]


def compile_artifact_runtime(repo_root: str | Path) -> ArtifactRuntimeView:
    """Compile the Slice 11.2 artifact/layout/lifecycle subset from authored contracts."""
    contract = load_framework_contract_set(repo_root)
    types_raw = _plain_family(contract, "artifact-types").get("artifact_types")
    if not isinstance(types_raw, tuple) or not types_raw:
        raise FrameworkContractError("artifact-runtime-types")
    artifact_types = tuple(types_raw)
    if any(not isinstance(value, str) or not value for value in artifact_types):
        raise FrameworkContractError("artifact-runtime-type")
    if len(artifact_types) != len(set(artifact_types)):
        raise FrameworkContractError("artifact-runtime-type-duplicate")

    families_raw = _plain_family(contract, "artifact-types").get("artifact_families")
    if not hasattr(families_raw, "items"):
        raise FrameworkContractError("artifact-runtime-families")
    artifact_families = dict(families_raw.items())
    if set(artifact_families) != set(artifact_types):
        raise FrameworkContractError("artifact-runtime-family-types")
    if any(
        not isinstance(family, str) or not family
        for family in artifact_families.values()
    ):
        raise FrameworkContractError("artifact-runtime-family")
    if artifact_families != {
        artifact_type: artifact_type for artifact_type in artifact_types
    }:
        raise FrameworkContractError("artifact-runtime-family-reclassification")

    layout_raw = _plain_family(contract, "repository-layout").get(
        "artifact_directories"
    )
    if not hasattr(layout_raw, "items"):
        raise FrameworkContractError("artifact-runtime-layout")
    layout = dict(layout_raw.items())
    if set(layout) != set(artifact_types):
        raise FrameworkContractError("artifact-runtime-layout-types")
    if any(
        not isinstance(path, str)
        or not path
        or "/" in path
        or "\\" in path
        or path in {".", ".."}
        for path in layout.values()
    ):
        raise FrameworkContractError("artifact-runtime-layout-root")
    if len(layout.values()) != len(set(layout.values())):
        raise FrameworkContractError("artifact-runtime-layout-duplicate")
    if layout.get("TDD") != "designs":
        raise FrameworkContractError("artifact-runtime-tdd-topology")

    lifecycle_raw = _plain_family(contract, "lifecycle").get("artifact_lifecycle")
    if not hasattr(lifecycle_raw, "items") or set(lifecycle_raw) != set(artifact_types):
        raise FrameworkContractError("artifact-runtime-lifecycle-types")
    lifecycle: dict[str, Mapping[str, LifecyclePolicy]] = {}
    for artifact_type in artifact_types:
        statuses_raw = lifecycle_raw[artifact_type]
        if not hasattr(statuses_raw, "items") or not statuses_raw:
            raise FrameworkContractError("artifact-runtime-lifecycle-statuses")
        statuses: dict[str, LifecyclePolicy] = {}
        for status, raw_policy in statuses_raw.items():
            if (
                not isinstance(status, str)
                or not status
                or not hasattr(raw_policy, "items")
            ):
                raise FrameworkContractError("artifact-runtime-lifecycle-status")
            semantic = raw_policy.get("semantic_class")
            profile = raw_policy.get("validation_profile")
            if semantic not in SEMANTIC_CLASSES:
                raise FrameworkContractError("artifact-runtime-semantic-class")
            if profile not in VALIDATION_PROFILES:
                raise FrameworkContractError("artifact-runtime-validation-profile")
            unknown = set(raw_policy) - {
                "semantic_class",
                "validation_profile",
                "age_policy",
            }
            if unknown:
                raise FrameworkContractError("artifact-runtime-lifecycle-fields")
            age = None
            if "age_policy" in raw_policy:
                raw_age = raw_policy["age_policy"]
                if not hasattr(raw_age, "items") or set(raw_age) != {
                    "depend_on",
                    "max_age_days",
                    "error_message",
                }:
                    raise FrameworkContractError("artifact-runtime-age-policy")
                depend_on = raw_age["depend_on"]
                max_age_days = raw_age["max_age_days"]
                error_message = raw_age["error_message"]
                if (
                    not isinstance(depend_on, str)
                    or not depend_on
                    or type(max_age_days) is not int
                    or max_age_days <= 0
                    or not isinstance(error_message, str)
                    or not error_message
                ):
                    raise FrameworkContractError("artifact-runtime-age-policy-value")
                age = AgePolicy(depend_on, max_age_days, error_message)
            statuses[status] = LifecyclePolicy(semantic, profile, age)
        lifecycle[artifact_type] = MappingProxyType(statuses)

    schemas_raw = _plain_family(contract, "schema-bindings").get("artifact_schemas")
    if not hasattr(schemas_raw, "items") or set(schemas_raw) != set(artifact_types):
        raise FrameworkContractError("artifact-runtime-schema-bindings")
    schemas = dict(schemas_raw.items())
    for artifact_type, relative in schemas.items():
        if not isinstance(relative, str) or not relative.startswith("schemas/"):
            raise FrameworkContractError("artifact-runtime-schema-path")
        path = Path(repo_root).resolve() / relative
        if not path.is_file() or path.is_symlink():
            raise FrameworkContractError("artifact-runtime-schema-missing")

    validators_raw = _plain_family(contract, "validator-bindings").get("validators")
    if not hasattr(validators_raw, "items") or set(validators_raw) != set(
        artifact_types
    ):
        raise FrameworkContractError("artifact-runtime-validator-bindings")
    validators: dict[str, ValidatorBinding] = {}
    for artifact_type, raw_binding in validators_raw.items():
        if not hasattr(raw_binding, "items") or set(raw_binding) != {"module", "class"}:
            raise FrameworkContractError("artifact-runtime-validator-binding")
        module, class_name = raw_binding["module"], raw_binding["class"]
        if not isinstance(module, str) or not module.startswith(
            "engine.control.validators.domains."
        ):
            raise FrameworkContractError("artifact-runtime-validator-module")
        if not isinstance(class_name, str) or not class_name.endswith("Validator"):
            raise FrameworkContractError("artifact-runtime-validator-class")
        validators[artifact_type] = ValidatorBinding(module, class_name)

    return ArtifactRuntimeView(
        artifact_types=artifact_types,
        artifact_families=MappingProxyType(artifact_families),
        artifact_directories=MappingProxyType(layout),
        lifecycle=MappingProxyType(lifecycle),
        schema_bindings=MappingProxyType(schemas),
        validator_bindings=MappingProxyType(validators),
        contract_sha256=contract.canonical_sha256,
    )


@lru_cache(maxsize=1)
def artifact_runtime() -> ArtifactRuntimeView:
    return compile_artifact_runtime(ROOT)


def artifact_type_from_id(doc_id: object) -> str | None:
    if not isinstance(doc_id, str):
        return None
    prefix = doc_id.strip().split("-", 1)[0].upper()
    return prefix if prefix in artifact_runtime().artifact_types else None


def validator_registry() -> Mapping[str, type]:
    registry: dict[str, type] = {}
    for artifact_type, binding in artifact_runtime().validator_bindings.items():
        try:
            module = importlib.import_module(binding.module)
            validator = getattr(module, binding.class_name)
        except (ImportError, AttributeError) as exc:
            raise FrameworkContractError(
                f"artifact-runtime-validator-unresolvable:{artifact_type}"
            ) from exc
        if getattr(validator, "doc_type_name", None) != artifact_type:
            raise FrameworkContractError(
                f"artifact-runtime-validator-type:{artifact_type}"
            )
        registry[artifact_type] = validator
    return MappingProxyType(registry)
