import pytest

from engine.control.simulation import (
    SimulationFinding,
    SimulationOutcome,
    SimulationReport,
)


def test_simulation_report_normalizes_and_derives_outcome():
    finding = SimulationFinding(
        "f1",
        "cycle",
        "cycle found",
        ("B", "A"),
        True,
    )
    report = SimulationReport(
        "SIM-1",
        "D-1",
        "current",
        "proposed",
        added_node_keys=("B", "A"),
        impacted_keys=("C", "A"),
        findings=(finding,),
    )
    assert report.added_node_keys == ("A", "B")
    assert report.outcome is SimulationOutcome.FAIL
    assert report.semantic_state()[7] == "fail"


def test_simulation_contract_rejects_invalid_shapes():
    with pytest.raises(ValueError):
        SimulationFinding("f", "cycle", "m", (), False)
    with pytest.raises(ValueError):
        SimulationReport("S", "D", "c", "p", added_node_keys=("A", "A"))
    with pytest.raises(TypeError):
        SimulationReport("S", "D", "c", "p", findings=(object(),))


def test_simulation_contract_additional_validation_paths():
    with pytest.raises(ValueError):
        SimulationFinding(" ", "cycle", "m", ("A",))
    with pytest.raises(ValueError):
        SimulationFinding("f", "cycle", "m", ("A", "A"))
    with pytest.raises(ValueError):
        SimulationReport(" ", "D", "c", "p")
    duplicate = SimulationFinding("f", "cycle", "m", ("A",))
    with pytest.raises(ValueError):
        SimulationReport("S", "D", "c", "p", findings=(duplicate, duplicate))
    assert SimulationReport("S", "D", "c", "p").outcome is SimulationOutcome.PASS
