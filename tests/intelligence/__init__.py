from __future__ import annotations

import ast
from pathlib import Path

import engine.intelligence as intelligence
import yaml

ROOT = Path(__file__).resolve().parents[2]


def _imports(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
        elif isinstance(node, ast.Import):
            modules.extend(item.name for item in node.names)
    return tuple(modules)


def test_intelligence_contracts_do_not_import_control_or_runtime_providers():
    forbidden = (
        "engine.control",
        "engine.adapters",
        "langchain",
        "langgraph",
        "openai",
        "anthropic",
    )
    for path in (ROOT / "engine" / "intelligence").rglob("*.py"):
        imports = _imports(path)
        assert not [name for name in imports if name.startswith(forbidden)], path


def test_stable_contract_exports_are_machine_addressable():
    expected = {
        "IntentSpec",
        "ArchitecturePlan",
        "ResearchPlan",
        "ResearchPackage",
        "ArchitectureProposal",
        "ArtifactDraft",
    }
    assert expected <= set(intelligence.__all__)


def test_no_agent_or_approval_runtime_is_introduced():
    root = ROOT / "engine" / "intelligence"
    production = "\n".join(
        path.read_text(encoding="utf-8") for path in root.rglob("*.py")
    )
    assert "AgentExecutor" not in production
    assert "approve(" not in production
    assert "model_provider" not in production


def test_governance_maps_intelligence_contract_authority():
    layout = yaml.safe_load(
        (ROOT / "governance" / "framework" / "source-layout.yaml").read_text(
            encoding="utf-8"
        )
    )
    contracts = layout["intelligence_contracts"]
    assert contracts["intent_and_planning"]["location"] == (
        "engine/intelligence/planning/contracts.py"
    )
    assert contracts["research"]["location"] == (
        "engine/intelligence/research/contracts.py"
    )
    assert contracts["synthesis"]["location"] == (
        "engine/intelligence/synthesis/contracts.py"
    )

    framework = yaml.safe_load(
        (ROOT / "governance" / "framework" / "scnehaux-framework.yaml").read_text(
            encoding="utf-8"
        )
    )
    stable = set(framework["capability_architecture"]["stable_contracts"])
    assert {
        "IntentSpec",
        "ArchitecturePlan",
        "ResearchPlan",
        "ResearchPackage",
        "ArchitectureProposal",
        "ArtifactDraft",
    } <= stable

