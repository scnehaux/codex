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
MAX_YAML_BYTES = 256_000


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


def _relative_file(root: Path, raw: object) -> Path:
    _require(isinstance(raw, str) and bool(raw), "framework-contract-path")
    _require(
        "\\" not in raw and not raw.startswith("/") and ":" not in raw,
        "framework-contract-path",
    )
    parts = Path(raw).parts
    _require(
        parts and ".." not in parts and "." not in parts, "framework-contract-path"
    )
    _require(
        raw.startswith("governance/framework/contracts/"),
        "framework-contract-family-root",
    )
    current = root
    for part in parts:
        current = current / part
        _require(not current.is_symlink(), "framework-contract-symlink")
    _require(current.is_file(), "framework-contract-family-missing")
    return current


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(value[key]) for key in sorted(value)})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


@dataclass(frozen=True, slots=True)
class FrameworkContractSet:
    contract_version: int
    framework_id: str
    framework_version: str
    framework_status: str
    families: Mapping[str, Mapping[str, Any]]
    ownership: Mapping[str, str]
    runtime_authority: str
    canonical_sha256: str


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


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
        activation["runtime_authority"]
        == "declarative-artifact-lifecycle-python-relationships-until-11.3",
        "framework-contract-runtime-authority",
    )
    _require(
        activation["migration_slices"] == ["11.3", "11.4"],
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
        family = _load_yaml(_relative_file(root, path))
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
    canonical = _canonical({"manifest": manifest, "families": family_values})
    return FrameworkContractSet(
        contract_version=1,
        framework_id=framework["id"],
        framework_version=framework["version"],
        framework_status=framework["status"],
        families=_freeze(family_values),
        ownership=_freeze(ownership),
        runtime_authority=activation["runtime_authority"],
        canonical_sha256=sha256(canonical).hexdigest(),
    )
