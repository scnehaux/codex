from __future__ import annotations

from pathlib import Path
import copy

import pytest
import yaml

from engine.control.governance.readiness import (
    assert_governance_readiness,
    audit_governance_readiness,
)
from tests.support.repository import REPOSITORY_ROOT


SOURCE_LAYOUT = yaml.safe_load(
    (
        REPOSITORY_ROOT
        / "00-governance"
        / "framework"
        / "source-layout.yaml"
    ).read_text(encoding="utf-8")
)
BOOTSTRAP = yaml.safe_load(
    (
        REPOSITORY_ROOT
        / "00-governance"
        / "bootstrap-manifest.yaml"
    ).read_text(encoding="utf-8")
)
MAKEFILE = (
    REPOSITORY_ROOT / "Makefile"
).read_text(encoding="utf-8")


def _materialize(
    tmp_path,
    *,
    layout=None,
    bootstrap=None,
    makefile=None,
):
    canonical_layout = copy.deepcopy(SOURCE_LAYOUT)
    layout = copy.deepcopy(
        SOURCE_LAYOUT if layout is None else layout
    )
    bootstrap = copy.deepcopy(
        BOOTSTRAP if bootstrap is None else bootstrap
    )
    makefile = MAKEFILE if makefile is None else makefile

    # Build the known-good permanent proof estate from the canonical
    # contract first. Corrupted subject state must never influence fixture
    # construction, escape tmp_path, or crash before the auditor runs.
    canonical_qualification = canonical_layout[
        "governance_qualification"
    ]

    canonical_paths = {
        canonical_qualification["authority"],
        canonical_qualification["invocation"],
    }

    for closure in canonical_qualification[
        "required_controls"
    ].values():
        canonical_paths.update(
            closure["implementation"]
        )
        canonical_paths.update(
            closure["test_evidence"]
        )

    for rel in canonical_paths:
        assert isinstance(rel, str) and rel

        path = tmp_path / rel
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        path.write_text(
            "# proof\n",
            encoding="utf-8",
        )

    source_layout = (
        tmp_path
        / "00-governance"
        / "framework"
        / "source-layout.yaml"
    )
    source_layout.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    source_layout.write_text(
        yaml.safe_dump(
            layout,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    bootstrap_path = (
        tmp_path
        / "00-governance"
        / "bootstrap-manifest.yaml"
    )
    bootstrap_path.write_text(
        yaml.safe_dump(
            bootstrap,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    (tmp_path / "Makefile").write_text(
        makefile,
        encoding="utf-8",
    )
    (tmp_path / "conftest.py").write_text(
        "",
        encoding="utf-8",
    )

    return tmp_path


def test_current_repository_is_governance_ready():
    report = audit_governance_readiness(REPOSITORY_ROOT)
    assert report.ok
    assert set(report.checked_controls) >= {
        "temporary_tooling",
        "genesis_integrity",
        "version_mutation_integrity",
    }


def test_materialized_valid_contract_passes(tmp_path):
    root = _materialize(tmp_path)
    report = assert_governance_readiness(root)
    assert report.ok


@pytest.mark.parametrize(
    ("mutator", "code"),
    (
        (
            lambda l, b: l.pop("governance_qualification"),
            "qualification-contract-missing",
        ),
        (
            lambda l, b: l["governance_qualification"].__setitem__(
                "required_controls", []
            ),
            "required-controls-invalid",
        ),
        (
            lambda l, b: l["governance_qualification"][
                "required_controls"
            ].pop("genesis_integrity"),
            "required-control-missing",
        ),
        (
            lambda l, b: l["governance_qualification"][
                "required_controls"
            ].__setitem__("genesis_integrity", []),
            "control-closure-invalid",
        ),
        (
            lambda l, b: l["governance_qualification"][
                "required_controls"
            ]["genesis_integrity"].__setitem__(
                "policy_ref", "missing_policy"
            ),
            "policy-reference-invalid",
        ),
        (
            lambda l, b: l["governance_qualification"][
                "required_controls"
            ]["genesis_integrity"].__setitem__(
                "implementation", []
            ),
            "evidence-list-invalid",
        ),
        (
            lambda l, b: b["genesis_contract"].__setitem__(
                "local_qualification_required", False
            ),
            "local-qualification-not-required",
        ),
        (
            lambda l, b: b["genesis_contract"].__setitem__(
                "local_qualification_entrypoint", "wrong.py"
            ),
            "local-qualification-entrypoint-mismatch",
        ),
        (
            lambda l, b: b["governance_control_plane"].__setitem__(
                "architecture_admission", "open"
            ),
            "bootstrap-governance-state-invalid",
        ),
        (
            lambda l, b: b["provenance"].__setitem__(
                "architecture_artifacts_admitted_in_genesis", True
            ),
            "bootstrap-provenance-invalid",
        ),
    ),
)
def test_contract_corruption_is_fail_closed(tmp_path, mutator, code):
    layout = copy.deepcopy(SOURCE_LAYOUT)
    bootstrap = copy.deepcopy(BOOTSTRAP)
    mutator(layout, bootstrap)

    root = _materialize(
        tmp_path,
        layout=layout,
        bootstrap=bootstrap,
    )
    report = audit_governance_readiness(root)
    assert any(finding.code == code for finding in report.findings)


def test_evidence_path_rules_reject_blank_temporary_external_and_missing(
    tmp_path,
):
    layout = copy.deepcopy(SOURCE_LAYOUT)
    closure = layout["governance_qualification"][
        "required_controls"
    ]["genesis_integrity"]
    closure["implementation"] = [
        "",
        "phase99_probe.py",
        "outside/control.py",
        "engine/control/governance/missing.py",
    ]

    root = _materialize(tmp_path, layout=layout)
    report = audit_governance_readiness(root)
    codes = {finding.code for finding in report.findings}

    assert "evidence-path-invalid" in codes
    assert "temporary-evidence-forbidden" in codes
    assert "evidence-path-outside-permanent-roots" in codes
    assert "evidence-path-missing" in codes


def test_invalid_qualification_entrypoints_are_reported(tmp_path):
    layout = copy.deepcopy(SOURCE_LAYOUT)
    layout["governance_qualification"]["authority"] = "missing.py"
    layout["governance_qualification"]["invocation"] = 123

    root = _materialize(tmp_path, layout=layout)
    report = audit_governance_readiness(root)
    assert sum(
        finding.code == "qualification-entrypoint-invalid"
        for finding in report.findings
    ) == 2


@pytest.mark.parametrize(
    ("makefile", "code"),
    (
        (
            MAKEFILE.replace("genesis-check:", "genesis-old:"),
            "makefile-target-missing",
        ),
        (
            MAKEFILE.replace(
                "python 06-fitness-function/scripts/mutation_integrity.py",
                "python wrong.py",
            ),
            "makefile-command-mismatch",
        ),
    ),
)
def test_makefile_closure_is_fail_closed(tmp_path, makefile, code):
    root = _materialize(tmp_path, makefile=makefile)
    report = audit_governance_readiness(root)
    assert any(finding.code == code for finding in report.findings)


def test_nonclean_root_python_is_rejected(tmp_path):
    root = _materialize(tmp_path)
    (root / "probe.py").write_text("", encoding="utf-8")

    report = audit_governance_readiness(root)
    assert any(
        finding.code == "repository-root-python-not-clean"
        for finding in report.findings
    )


def test_yaml_load_and_shape_failures_are_reported(tmp_path):
    root = _materialize(tmp_path)

    layout = (
        root / "00-governance" / "framework" / "source-layout.yaml"
    )
    layout.write_text("[", encoding="utf-8")
    report = audit_governance_readiness(root)
    assert any(
        finding.code == "yaml-load-failed"
        for finding in report.findings
    )

    layout.write_text("- list\n", encoding="utf-8")
    report = audit_governance_readiness(root)
    assert any(
        finding.code == "yaml-root-invalid"
        for finding in report.findings
    )


def test_assertion_raises_with_structured_findings(tmp_path):
    root = _materialize(tmp_path)
    (root / "extra.py").write_text("", encoding="utf-8")

    with pytest.raises(
        RuntimeError,
        match="Governance readiness audit failed",
    ):
        assert_governance_readiness(root)


def test_bootstrap_contract_shape_failures_are_reported(
    tmp_path,
):
    bootstrap = copy.deepcopy(BOOTSTRAP)
    bootstrap["genesis_contract"] = None

    root = _materialize(
        tmp_path,
        bootstrap=bootstrap,
    )
    report = audit_governance_readiness(root)

    assert any(
        finding.code == "bootstrap-contract-invalid"
        for finding in report.findings
    )


def test_bootstrap_governance_and_provenance_shape_failures_are_reported(
    tmp_path,
):
    bootstrap = copy.deepcopy(BOOTSTRAP)
    bootstrap["governance_control_plane"] = None
    bootstrap["provenance"] = None

    root = _materialize(
        tmp_path,
        bootstrap=bootstrap,
    )
    report = audit_governance_readiness(root)
    codes = {
        finding.code
        for finding in report.findings
    }

    assert "bootstrap-governance-state-invalid" in codes
    assert "bootstrap-provenance-invalid" in codes


def test_makefile_read_failure_is_reported(tmp_path):
    root = _materialize(tmp_path)
    (root / "Makefile").unlink()

    report = audit_governance_readiness(root)

    assert any(
        finding.code == "makefile-read-failed"
        for finding in report.findings
    )


def test_nonstring_evidence_is_reported(tmp_path):
    layout = copy.deepcopy(SOURCE_LAYOUT)
    layout["governance_qualification"][
        "required_controls"
    ]["genesis_integrity"]["test_evidence"] = [123]

    root = _materialize(
        tmp_path,
        layout=layout,
    )
    report = audit_governance_readiness(root)

    assert any(
        finding.code == "evidence-path-invalid"
        for finding in report.findings
    )

def test_hidden_repository_paths_preserve_leading_dot():
    from engine.control.governance import genesis
    from engine.control.governance import genesis_candidate
    from engine.control.governance import mutation
    from engine.control.governance import readiness
    from engine.control.governance import committed_mutation

    normalizers = (
        genesis._normalize,
        genesis_candidate._normalize,
        mutation._normalize,
        readiness._normalize,
        committed_mutation._normalize,
    )

    for normalize in normalizers:
        assert normalize(".github/CODEOWNERS") == ".github/CODEOWNERS"
        assert normalize("./.github/CODEOWNERS") == ".github/CODEOWNERS"
        assert normalize(".gitignore") == ".gitignore"
        assert normalize(".gitattributes") == ".gitattributes"
        assert (
            normalize(r".github\workflows\governance.yml")
            == ".github/workflows/governance.yml"
        )

