from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from engine.control.repository import RepositoryAssembler, RepositoryIngestionError, RepositoryModelError


ROOT = Path(__file__).resolve().parents[3]
GENERATOR_PATH = (
    ROOT
    / "06-fitness-function"
    / "generators"
    / "generate_maturity_dashboard.py"
)


def _load_generator(name: str):
    spec = importlib.util.spec_from_file_location(name, GENERATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_artifact(
    path: Path,
    document_id: str,
    *,
    status: str = "draft",
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        "doc_meta:\n"
        f"  id: {document_id}\n"
        "  title: Test Artifact\n"
        "  owner: Architecture\n"
        f"  status: {status}\n"
        "---\n"
        "# Test\n",
        encoding="utf-8",
    )


def _write_control_registry(path: Path, controls: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = ["controls:"]
    for control in controls:
        lines.extend(
            [
                f"  - control_id: {control['control_id']}",
                "    source_gdc: GDC-000",
                "    source_file: GDC-000-governance-policy.md",
                "    source_clause: Test Clause",
                "    source_fingerprint: abc123def456",
                "    modality: MUST",
                "    statement: Test governance obligation",
                "    scope: test",
                "    severity: ERROR",
                "    enforcement_mode: fitness-function",
                "    implementation:",
                '      - engine/interfaces/cli.py',
                "    test_evidence:",
            ]
        )

        evidence = control.get("test_evidence", [])
        if evidence:
            for item in evidence:
                lines.append(f"      - {item}")
        else:
            lines.append("      []")

        lines.extend(
            [
                f"    evidence_status: {control['evidence_status']}",
                "    evidence_expectation: test evidence",
                "    control_owner: Architecture",
                "    target_phase: Phase 5",
            ]
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_approved_artifact_does_not_create_verified_evidence(tmp_path):
    module = _load_generator("maturity_no_inference")

    _write_artifact(
        tmp_path / "00-governance" / "GDC-000-policy.md",
        "GDC-000",
        status="approved",
    )
    _write_control_registry(
        tmp_path / "00-governance" / "normative-control-registry.yaml",
        [
            {
                "control_id": "CTRL-GDC-000-001",
                "evidence_status": "pending",
            }
        ],
    )

    output = module.generate_dashboard(repo_root=tmp_path)
    content = output.read_text(encoding="utf-8")

    assert "| GDC | 1 |" in content
    assert "`pending`: **1**" in content
    assert "`verified`: **1**" not in content
    assert "Active / Approved" not in content


def test_dashboard_uses_explicit_control_evidence_states(tmp_path):
    module = _load_generator("maturity_evidence")

    _write_artifact(
        tmp_path / "00-governance" / "GDC-000-policy.md",
        "GDC-000",
    )
    _write_control_registry(
        tmp_path / "00-governance" / "normative-control-registry.yaml",
        [
            {
                "control_id": "CTRL-GDC-000-001",
                "evidence_status": "verified",
                "test_evidence": [
                    "06-fitness-function/tests/engine/test_cli.py"
                ],
            },
            {
                "control_id": "CTRL-GDC-000-002",
                "evidence_status": "pending",
            },
        ],
    )

    output = module.generate_dashboard(repo_root=tmp_path)
    content = output.read_text(encoding="utf-8")

    assert "Total registered controls: **2**" in content
    assert "`verified`: **1**" in content
    assert "`pending`: **1**" in content


def test_missing_control_registry_fails_before_existing_dashboard_changes(tmp_path):
    module = _load_generator("maturity_missing_registry")

    maturity = tmp_path / "MATURITY.md"
    maturity.write_text("previous-good-dashboard\n", encoding="utf-8")

    with pytest.raises(RepositoryModelError, match="registry is missing"):
        module.generate_dashboard(repo_root=tmp_path)

    assert maturity.read_text(encoding="utf-8") == "previous-good-dashboard\n"


def test_malformed_corpus_fails_before_existing_dashboard_changes(tmp_path):
    module = _load_generator("maturity_malformed")

    maturity = tmp_path / "MATURITY.md"
    maturity.write_text("previous-good-dashboard\n", encoding="utf-8")

    governance = tmp_path / "00-governance"
    governance.mkdir(parents=True)
    (governance / "broken.md").write_text(
        "---\n"
        "doc_meta: [unterminated\n"
        "---\n",
        encoding="utf-8",
    )

    with pytest.raises(RepositoryIngestionError):
        module.generate_dashboard(repo_root=tmp_path)

    assert maturity.read_text(encoding="utf-8") == "previous-good-dashboard\n"


def test_registry_integrity_findings_are_not_reported_as_pass():
    module = _load_generator("maturity_integrity")

    content = module.render_dashboard(
        artifact_inventory={"GDC": 1},
        evidence_inventory={"pending": 1},
        control_total=1,
        registry_findings=("broken evidence path",),
    )

    assert "Registry integrity: **FAIL** (1 finding(s))" in content
    assert "broken evidence path" in content
    assert "Registry integrity: **PASS**" not in content


def test_no_synthetic_ci_or_codeowners_green_claims():
    source = GENERATOR_PATH.read_text(encoding="utf-8")

    assert "CODEOWNERS Status" not in source
    assert "Schema Drift" not in source
    assert "Validated via CI" not in source
    assert "status: approved" not in source
    assert "os.walk" not in source
    assert "RepositoryAssembler.load_governed_corpus" in source
    assert "load_control_registry" in source
    assert "registry_structure_errors" in source


def test_main_returns_nonzero_on_failure(monkeypatch):
    module = _load_generator("maturity_main_failure")

    def fail_generation():
        raise RepositoryModelError("boom")

    monkeypatch.setattr(module, "generate_dashboard", fail_generation)

    assert module.main() == 1


def test_main_returns_zero_on_success(monkeypatch):
    module = _load_generator("maturity_main_success")
    monkeypatch.setattr(module, "generate_dashboard", lambda: Path("MATURITY.md"))

    assert module.main() == 0
