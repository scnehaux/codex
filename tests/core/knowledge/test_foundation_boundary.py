from __future__ import annotations

import ast

import yaml

from engine.core.knowledge import ContextPackage, Evidence
from tests.support.repository import REPOSITORY_ROOT


def _imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            found.append(node.module)
        elif isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
    return tuple(found)


def test_knowledge_foundation_is_core_only_and_declared_in_layout():
    knowledge = REPOSITORY_ROOT / "engine" / "core" / "knowledge"
    for name in ("provenance.py", "context.py", "retrieval.py"):
        imports = _imports(knowledge / name)
        assert not any(
            item.startswith((
                "engine.control",
                "engine.intelligence",
                "engine.adapters",
                "engine.interfaces",
            ))
            for item in imports
        )

    layout = yaml.safe_load(
        (
            REPOSITORY_ROOT
            / "00-governance"
            / "framework"
            / "source-layout.yaml"
        ).read_text(encoding="utf-8")
    )
    foundation = layout["knowledge_foundation"]
    assert foundation["provenance"]["chain"] == [
        "claim",
        "evidence",
        "source",
        "authority",
        "revision",
    ]
    assert foundation["retrieval"]["semantic_authority"] == "supplementary"
    assert foundation["retrieval"]["hybrid_supported"] is True
    assert ContextPackage.__module__.startswith("engine.core.knowledge")
    assert Evidence.__module__.startswith("engine.core.knowledge")
