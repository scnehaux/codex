from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, Mapping

import yaml


MANIFEST = Path("governance/framework/contract-set.yaml")
PROFILE_ROOT = Path("governance/framework/profiles")
COMPANY_PACK_ROOT = Path("governance/framework/company-packs")
FAMILY_NAMES = frozenset(
    {
        "identity",
        "artifact-types",
        "repository-layout",
        "lifecycle",
        "relationships",
        "schema-bindings",
        "validator-bindings",
        "governance-policy",
        "extensions",
    }
)
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
PACK_VERSION = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
MAX_YAML_BYTES = 256_000
EXTENSION_MODES = (
    "additive",
    "governed-restriction",
    "compatibility-preserving-override",
    "forbidden-core-semantic-override",
)
EXTENSION_TARGETS = frozenset({"artifact-type", "relationship-type"})


class FrameworkContractError(RuntimeError):
    pass


class _UniqueSafeLoader(yaml.SafeLoader):
    pass


def _unique_mapping(loader: _UniqueSafeLoader, node, deep=False):
    loader.flatten_mapping(node)
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in result
        except TypeError as exc:
            raise FrameworkContractError("framework-contract-key-invalid") from exc
        if duplicate:
            raise FrameworkContractError(f"framework-contract-duplicate-key:{key}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _unique_mapping,
)


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise FrameworkContractError(code)


def _exact_fields(value: object, fields: set[str], code: str) -> Mapping[str, Any]:
    _require(isinstance(value, dict), code + "-mapping")
    _require(set(value) == fields, code + "-fields")
    return value


def _load_yaml(path: Path) -> dict[str, Any]:
    _require(path.is_file() and not path.is_symlink(), "framework-contract-file")
    raw = path.read_bytes()
    _require(0 < len(raw) <= MAX_YAML_BYTES, "framework-contract-size")
    try:
        text = raw.decode("utf-8")
        value = yaml.load(text, Loader=_UniqueSafeLoader)
    except (UnicodeError, yaml.YAMLError) as exc:
        raise FrameworkContractError("framework-contract-yaml") from exc
    _require(isinstance(value, dict), "framework-contract-root")
    return value


def _relative_file(root: Path, raw: object, prefix: str, code: str) -> Path:
    _require(isinstance(raw, str) and bool(raw), code)
    _require(
        "\\" not in raw and not raw.startswith("/") and ":" not in raw,
        code,
    )
    parts = Path(raw).parts
    _require(parts and ".." not in parts and "." not in parts, code)
    _require(raw.startswith(prefix), code + "-root")
    current = root
    for part in parts:
        current = current / part
        _require(not current.is_symlink(), code + "-symlink")
    _require(current.is_file(), code + "-missing")
    return current


def _relative_contract_file(root: Path, raw: object) -> Path:
    return _relative_file(
        root,
        raw,
        "governance/framework/contracts/",
        "framework-contract-path",
    )


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(value[key]) for key in sorted(value)})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _digest(value: object) -> str:
    return sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True, slots=True)
class FrameworkLayer:
    layer_kind: str
    layer_id: str
    layer_version: str
    path: str
    sha256: str


@dataclass(frozen=True, slots=True)
class FrameworkContractSet:
    contract_version: int
    framework_id: str
    framework_version: str
    framework_status: str
    families: Mapping[str, Mapping[str, Any]]
    ownership: Mapping[str, str]
    runtime_authority: str
    layers: tuple[FrameworkLayer, ...]
    canonical_sha256: str


def _load_profile(
    root: Path, profile_id: str, profile_version: int
) -> tuple[dict, FrameworkLayer]:
    relative = f"governance/framework/profiles/{profile_id}.yaml"
    path = _relative_file(
        root,
        relative,
        "governance/framework/profiles/",
        "framework-profile-path",
    )
    profile = _load_yaml(path)
    _require(
        profile.get("kind") == "scnehaux-codex-governance-profile",
        "framework-profile-kind",
    )
    _require(
        profile.get("profile_id") == profile_id, "executable-framework-profile-drift"
    )
    _require(
        profile.get("profile_version") == profile_version,
        "executable-framework-profile-drift",
    )
    extension = profile.get("extension")
    _require(isinstance(extension, dict), "framework-profile-extension")
    _require(
        extension.get("core_fork_required") is False,
        "framework-profile-core-fork",
    )
    return profile, FrameworkLayer(
        layer_kind="framework-profile",
        layer_id=profile_id,
        layer_version=str(profile_version),
        path=relative,
        sha256=_digest(profile),
    )


def _validate_extension_policy(value: object) -> dict[str, tuple[str, ...]]:
    _require(isinstance(value, dict), "framework-extension-policy")
    _require(set(value) == set(EXTENSION_MODES), "framework-extension-policy-modes")
    result: dict[str, tuple[str, ...]] = {}
    for mode in EXTENSION_MODES:
        targets = value[mode]
        _require(isinstance(targets, list), "framework-extension-policy-targets")
        _require(
            all(
                isinstance(item, str) and item in EXTENSION_TARGETS for item in targets
            ),
            "framework-extension-policy-target",
        )
        _require(
            len(targets) == len(set(targets)), "framework-extension-policy-duplicate"
        )
        result[mode] = tuple(targets)
    return result


def _artifact_definition(value: object) -> Mapping[str, Any]:
    definition = _exact_fields(
        value,
        {"artifact_type", "family", "directory", "lifecycle", "schema", "validator"},
        "company-pack-artifact",
    )
    artifact_type = definition["artifact_type"]
    family = definition["family"]
    directory = definition["directory"]
    schema = definition["schema"]
    _require(
        isinstance(artifact_type, str)
        and bool(re.fullmatch(r"[A-Z][A-Z0-9_]{1,31}", artifact_type)),
        "company-pack-artifact-type",
    )
    _require(family == artifact_type, "company-pack-artifact-family")
    _require(
        isinstance(directory, str)
        and bool(directory)
        and "/" not in directory
        and "\\" not in directory
        and directory not in {".", ".."},
        "company-pack-artifact-directory",
    )
    _require(
        isinstance(schema, str) and schema.startswith("schemas/"),
        "company-pack-artifact-schema",
    )
    _require(
        isinstance(definition["lifecycle"], dict) and bool(definition["lifecycle"]),
        "company-pack-artifact-lifecycle",
    )
    validator = _exact_fields(
        definition["validator"],
        {"module", "class"},
        "company-pack-artifact-validator",
    )
    _require(
        isinstance(validator["module"], str) and bool(validator["module"]),
        "company-pack-artifact-validator-module",
    )
    _require(
        isinstance(validator["class"], str)
        and validator["class"].endswith("Validator"),
        "company-pack-artifact-validator-class",
    )
    return definition


def _relationship_definition(value: object) -> Mapping[str, Any]:
    fields = {
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
    definition = _exact_fields(value, fields, "company-pack-relationship")
    _require(
        isinstance(definition["name"], str) and bool(definition["name"]),
        "company-pack-relationship-name",
    )
    _require(
        isinstance(definition["metadata_field"], str)
        and bool(definition["metadata_field"]),
        "company-pack-relationship-field",
    )
    return definition


def _apply_additive_artifact(
    families: dict[str, dict[str, Any]],
    definition: Mapping[str, Any],
) -> None:
    artifact = _artifact_definition(definition)
    artifact_type = artifact["artifact_type"]
    types = families["artifact-types"]["data"]["artifact_types"]
    family_map = families["artifact-types"]["data"]["artifact_families"]
    layout = families["repository-layout"]["data"]["artifact_directories"]
    lifecycle = families["lifecycle"]["data"]["artifact_lifecycle"]
    schemas = families["schema-bindings"]["data"]["artifact_schemas"]
    validators = families["validator-bindings"]["data"]["validators"]
    _require(
        artifact_type not in types, "company-pack-core-artifact-override-forbidden"
    )
    _require(artifact_type not in family_map, "company-pack-artifact-duplicate")
    _require(
        artifact["directory"] not in set(layout.values()),
        "company-pack-artifact-directory-conflict",
    )
    types.append(artifact_type)
    family_map[artifact_type] = artifact["family"]
    layout[artifact_type] = artifact["directory"]
    lifecycle[artifact_type] = artifact["lifecycle"]
    schemas[artifact_type] = artifact["schema"]
    validators[artifact_type] = artifact["validator"]


def _apply_additive_relationship(
    families: dict[str, dict[str, Any]],
    definition: Mapping[str, Any],
) -> None:
    relationship = dict(_relationship_definition(definition))
    existing = families["relationships"]["data"]["relationships"]
    _require(
        relationship["name"] not in {item["name"] for item in existing},
        "company-pack-core-relationship-override-forbidden",
    )
    for item in existing:
        overlap = set(item["source_types"]) & set(relationship["source_types"])
        _require(
            not overlap or item["metadata_field"] != relationship["metadata_field"],
            "company-pack-relationship-source-field-conflict",
        )
    existing.append(relationship)


def _load_company_pack(
    root: Path,
    descriptor: object,
    *,
    profile_id: str,
    profile_version: int,
    policy: Mapping[str, tuple[str, ...]],
    families: dict[str, dict[str, Any]],
) -> tuple[dict, FrameworkLayer]:
    descriptor = _exact_fields(
        descriptor,
        {"path", "kind"},
        "company-pack-descriptor",
    )
    _require(descriptor["kind"] == "scnehaux-company-pack", "company-pack-kind")
    path = _relative_file(
        root,
        descriptor["path"],
        "governance/framework/company-packs/",
        "company-pack-path",
    )
    pack = _load_yaml(path)
    _exact_fields(
        pack,
        {
            "contract_version",
            "kind",
            "pack_id",
            "pack_version",
            "profile",
            "operations",
        },
        "company-pack",
    )
    _require(
        type(pack["contract_version"]) is int and pack["contract_version"] == 1,
        "company-pack-version",
    )
    _require(pack["kind"] == descriptor["kind"], "company-pack-kind")
    _require(
        isinstance(pack["pack_id"], str) and bool(pack["pack_id"]),
        "company-pack-id",
    )
    _require(
        isinstance(pack["pack_version"], str)
        and PACK_VERSION.fullmatch(pack["pack_version"]) is not None,
        "company-pack-semver",
    )
    profile = _exact_fields(pack["profile"], {"id", "version"}, "company-pack-profile")
    _require(
        profile["id"] == profile_id and profile["version"] == profile_version,
        "company-pack-profile-drift",
    )
    operations = pack["operations"]
    _require(
        isinstance(operations, list) and 0 < len(operations) <= 256,
        "company-pack-operations",
    )
    for operation in operations:
        operation = _exact_fields(
            operation,
            {"mode", "target", "definition"},
            "company-pack-operation",
        )
        mode = operation["mode"]
        target = operation["target"]
        _require(mode in EXTENSION_MODES, "company-pack-operation-mode")
        _require(target in EXTENSION_TARGETS, "company-pack-operation-target")
        _require(target in policy[mode], f"company-pack-{mode}-not-allowed")
        _require(
            mode != "forbidden-core-semantic-override",
            "company-pack-core-semantic-override-forbidden",
        )
        if mode == "additive" and target == "artifact-type":
            _apply_additive_artifact(families, operation["definition"])
        elif mode == "additive" and target == "relationship-type":
            _apply_additive_relationship(families, operation["definition"])
        else:
            raise FrameworkContractError(
                f"company-pack-operation-not-implemented:{mode}:{target}"
            )
    return pack, FrameworkLayer(
        layer_kind="company-pack",
        layer_id=pack["pack_id"],
        layer_version=pack["pack_version"],
        path=descriptor["path"],
        sha256=_digest(pack),
    )


def load_framework_contract_set(repo_root: str | Path) -> FrameworkContractSet:
    root = Path(repo_root).resolve()
    manifest = _load_yaml(root / MANIFEST)
    _exact_fields(
        manifest,
        {
            "contract_version",
            "kind",
            "framework",
            "families",
            "ownership",
            "activation",
        },
        "framework-contract-manifest",
    )
    _require(
        type(manifest["contract_version"]) is int and manifest["contract_version"] == 1,
        "framework-contract-version",
    )
    _require(
        manifest["kind"] == "scnehaux-framework-contract-set", "framework-contract-kind"
    )
    framework = _exact_fields(
        manifest["framework"],
        {"id", "version", "status"},
        "framework-contract-framework",
    )
    _require(framework["id"] == "scnehaux-codex", "framework-contract-id")
    _require(
        isinstance(framework["version"], str)
        and SEMVER.fullmatch(framework["version"]) is not None,
        "framework-contract-semver",
    )
    _require(framework["status"] == "draft", "framework-contract-status")

    descriptors = manifest["families"]
    _require(
        isinstance(descriptors, dict) and set(descriptors) == FAMILY_NAMES,
        "framework-contract-families",
    )
    ownership = manifest["ownership"]
    _require(isinstance(ownership, dict) and ownership, "framework-contract-ownership")
    activation = _exact_fields(
        manifest["activation"],
        {"runtime_authority", "migration_slices"},
        "framework-contract-activation",
    )
    _require(
        activation["runtime_authority"] == "executable-framework",
        "framework-contract-runtime-authority",
    )
    _require(
        activation["migration_slices"] == [],
        "framework-contract-migration-slices",
    )

    family_values: dict[str, dict[str, Any]] = {}
    family_paths: set[str] = set()
    validated_descriptors: dict[str, Mapping[str, Any]] = {}
    claimed: dict[str, str] = {}
    for family_name in sorted(FAMILY_NAMES):
        descriptor = _exact_fields(
            descriptors[family_name], {"path", "kind"}, "framework-contract-descriptor"
        )
        path = descriptor["path"]
        _require(
            isinstance(path, str) and path not in family_paths,
            "framework-contract-family-path-unique",
        )
        _require(
            isinstance(descriptor["kind"], str) and bool(descriptor["kind"]),
            "framework-contract-descriptor-kind",
        )
        family_paths.add(path)
        validated_descriptors[family_name] = descriptor

    for family_name in sorted(FAMILY_NAMES):
        descriptor = validated_descriptors[family_name]
        path = descriptor["path"]
        family = _load_yaml(_relative_contract_file(root, path))
        _exact_fields(
            family,
            {"contract_version", "kind", "owns", "data"},
            "framework-contract-family",
        )
        _require(
            type(family["contract_version"]) is int and family["contract_version"] == 1,
            "framework-contract-family-version",
        )
        _require(family["kind"] == descriptor["kind"], "framework-contract-family-kind")
        owns = family["owns"]
        _require(
            isinstance(owns, list)
            and owns
            and all(isinstance(item, str) and item for item in owns)
            and len(owns) == len(set(owns)),
            "framework-contract-family-owns",
        )
        _require(isinstance(family["data"], dict), "framework-contract-family-data")
        for semantic_owner in owns:
            _require(
                semantic_owner not in claimed, "framework-contract-conflicting-owner"
            )
            claimed[semantic_owner] = family_name
        family_values[family_name] = family

    _require(
        ownership == {key: claimed[key] for key in sorted(claimed)},
        "framework-contract-ownership-map",
    )

    extension_data = family_values["extensions"]["data"]
    _require(
        set(extension_data)
        == {
            "extension_points",
            "company_pack_must_not_require_core_fork",
            "profile_id",
            "profile_version",
            "profile_core_fork_required",
            "extension_policy",
            "company_packs",
        },
        "framework-extension-declaration-fields",
    )
    profile_id = extension_data["profile_id"]
    profile_version = extension_data["profile_version"]
    _require(
        isinstance(profile_id, str) and bool(profile_id),
        "framework-extension-profile-id",
    )
    _require(
        type(profile_version) is int and profile_version > 0,
        "framework-extension-profile-version",
    )
    profile, profile_layer = _load_profile(root, profile_id, profile_version)
    policy = _validate_extension_policy(extension_data["extension_policy"])
    descriptors = extension_data["company_packs"]
    _require(
        isinstance(descriptors, list) and len(descriptors) <= 64,
        "framework-company-packs",
    )
    pack_paths: set[str] = set()
    pack_ids: set[str] = set()
    pack_values: list[dict] = []
    layers = [
        FrameworkLayer(
            layer_kind="core-framework",
            layer_id=framework["id"],
            layer_version=framework["version"],
            path=MANIFEST.as_posix(),
            sha256=_digest({"manifest": manifest, "families": family_values}),
        ),
        profile_layer,
    ]
    for descriptor in descriptors:
        descriptor_map = _exact_fields(
            descriptor, {"path", "kind"}, "company-pack-descriptor"
        )
        path = descriptor_map["path"]
        _require(
            isinstance(path, str) and path not in pack_paths,
            "company-pack-path-duplicate",
        )
        pack_paths.add(path)
        pack, layer = _load_company_pack(
            root,
            descriptor,
            profile_id=profile_id,
            profile_version=profile_version,
            policy=policy,
            families=family_values,
        )
        _require(layer.layer_id not in pack_ids, "company-pack-id-duplicate")
        pack_ids.add(layer.layer_id)
        pack_values.append(pack)
        layers.append(layer)

    canonical = _canonical(
        {
            "manifest": manifest,
            "families": family_values,
            "profile": profile,
            "company_packs": pack_values,
        }
    )
    return FrameworkContractSet(
        contract_version=1,
        framework_id=framework["id"],
        framework_version=framework["version"],
        framework_status=framework["status"],
        families=_freeze(family_values),
        ownership=_freeze(ownership),
        runtime_authority=activation["runtime_authority"],
        layers=tuple(layers),
        canonical_sha256=sha256(canonical).hexdigest(),
    )
