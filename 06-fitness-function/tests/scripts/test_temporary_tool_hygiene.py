from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path

import yaml

from tests.support.repository import REPOSITORY_ROOT


SOURCE_LAYOUT = (
    REPOSITORY_ROOT
    / "00-governance"
    / "framework"
    / "source-layout.yaml"
)

REGISTRIES = (
    REPOSITORY_ROOT
    / "00-governance"
    / "normative-control-registry.yaml",
    REPOSITORY_ROOT
    / "00-governance"
    / "severity-enforcement-registry.yaml",
)


def _policy() -> dict:
    data = yaml.safe_load(
        SOURCE_LAYOUT.read_text(encoding="utf-8")
    )
    policy = data["temporary_tooling"]
    assert policy["genesis_requirement"] == (
        "temporary-root-tools-absent"
    )
    return policy


def _temporary(name: str, patterns: list[str]) -> bool:
    return any(
        fnmatch(name, pattern)
        for pattern in patterns
    )


def _registry_records(data):
    if isinstance(data, list):
        return data

    if not isinstance(data, dict):
        return []

    for key in ("controls", "rules"):
        value = data.get(key)
        if isinstance(value, list):
            return value

    return []


def test_repository_root_has_only_permanent_python_entrypoints():
    policy = _policy()
    allowed = set(
        policy["repository_root_python_allowlist"]
    )
    actual = {
        path.name
        for path in REPOSITORY_ROOT.glob("*.py")
        if path.is_file()
    }
    assert actual == allowed


def test_temporary_tool_patterns_are_absent_before_genesis():
    policy = _policy()
    patterns = policy["temporary_root_patterns"]

    temporary = sorted(
        path.name
        for path in REPOSITORY_ROOT.glob("*.py")
        if _temporary(path.name, patterns)
    )

    assert temporary == []


def test_governance_registries_do_not_use_temporary_tools_as_evidence():
    policy = _policy()
    patterns = policy["temporary_root_patterns"]
    findings = []

    for registry in REGISTRIES:
        data = yaml.safe_load(
            registry.read_text(encoding="utf-8")
        )

        for record in _registry_records(data):
            if not isinstance(record, dict):
                continue

            record_id = (
                record.get("control_id")
                or record.get("rule_id")
                or "<unknown>"
            )

            for field in (
                "implementation",
                "test_evidence",
            ):
                values = record.get(field) or []

                for value in values:
                    if not isinstance(value, str):
                        continue

                    target = (
                        value.split("::", 1)[0]
                        .split("#", 1)[0]
                        .replace("\\", "/")
                    )
                    name = Path(target).name

                    if _temporary(name, patterns):
                        findings.append(
                            f"{registry.name}:{record_id}:"
                            f"{field}:{value}"
                        )

    assert findings == []
