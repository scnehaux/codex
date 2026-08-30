import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            values.append(node.module)
        elif isinstance(node, ast.Import):
            values.extend(alias.name for alias in node.names)
    return values


def test_control_and_intelligence_do_not_import_each_other():
    for path in (ROOT / "engine" / "control").rglob("*.py"):
        assert not any(item.startswith("engine.intelligence") for item in imports(path)), path
    for path in (ROOT / "engine" / "intelligence").rglob("*.py"):
        assert not any(item.startswith("engine.control") for item in imports(path)), path


def test_approval_contract_is_neutral_core():
    path = ROOT / "engine" / "core" / "governance" / "approval.py"
    assert not any(item.startswith("engine.control") or item.startswith("engine.intelligence") for item in imports(path))


def test_phase69_contract_locations_and_stable_contracts():
    import yaml

    layout = yaml.safe_load(
        (ROOT / "00-governance" / "framework" / "source-layout.yaml").read_text(
            encoding="utf-8"
        )
    )
    phase = layout["phase6_9_contracts"]
    assert phase["validation"]["contract"] == "ValidationReport"
    assert phase["simulation"]["contract"] == "SimulationReport"
    assert phase["review"]["contract"] == "ArchitectureReview"
    assert phase["approval"]["contract"] == "ApprovalPackage"
    assert phase["review"]["authority"] == "advisory-only"

    framework = yaml.safe_load(
        (ROOT / "00-governance" / "framework" / "scnehaux-framework.yaml").read_text(
            encoding="utf-8"
        )
    )
    stable = set(framework["capability_architecture"]["stable_contracts"])
    assert {"ValidationReport", "SimulationReport", "ArchitectureReview", "ApprovalPackage"} <= stable
