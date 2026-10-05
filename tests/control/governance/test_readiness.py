from __future__ import annotations

import copy

import pytest
import yaml

from engine.control.governance.readiness import (
    assert_governance_readiness,
    audit_governance_readiness,
)
from tests.support.repository import REPOSITORY_ROOT


SOURCE_LAYOUT = yaml.safe_load(
    (REPOSITORY_ROOT / "governance" / "framework" / "source-layout.yaml").read_text(
        encoding="utf-8"
    )
)
BOOTSTRAP = yaml.safe_load(
    (REPOSITORY_ROOT / "governance" / "bootstrap-manifest.yaml").read_text(
        encoding="utf-8"
    )
)
MAKEFILE = (REPOSITORY_ROOT / "Makefile").read_text(encoding="utf-8")


def _materialize(
    tmp_path,
    *,
    layout=None,
    bootstrap=None,
    makefile=None,
):
    canonical_layout = copy.deepcopy(SOURCE_LAYOUT)
    layout = copy.deepcopy(SOURCE_LAYOUT if layout is None else layout)
    bootstrap = copy.deepcopy(BOOTSTRAP if bootstrap is None else bootstrap)
    makefile = MAKEFILE if makefile is None else makefile

    # Build the known-good permanent proof estate from the canonical
    # contract first. Corrupted subject state must never influence fixture
    # construction, escape tmp_path, or crash before the auditor runs.
    canonical_qualification = canonical_layout["governance_qualification"]

    canonical_paths = {
        canonical_qualification["authority"],
        canonical_qualification["invocation"],
    }

    for closure in canonical_qualification["required_controls"].values():
        canonical_paths.update(closure["implementation"])
        canonical_paths.update(closure["test_evidence"])

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

    source_layout = tmp_path / "governance" / "framework" / "source-layout.yaml"
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

    bootstrap_path = tmp_path / "governance" / "bootstrap-manifest.yaml"
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

    (tmp_path / "governance" / "normative-control-registry.yaml").write_text(
        (REPOSITORY_ROOT / "governance" / "normative-control-registry.yaml").read_text(
            encoding="utf-8"
        ),
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
        "scm_desired_state_semantics",
        "scm_live_state_observation",
    }


def test_materialized_valid_contract_passes(tmp_path):
    root = _materialize(tmp_path)
    report = assert_governance_readiness(root)
    assert report.ok


def _registry_path(root):
    return root / "governance" / "normative-control-registry.yaml"


def _write_registry(root, records):
    _registry_path(root).write_text(
        yaml.safe_dump(records, sort_keys=False), encoding="utf-8"
    )


def test_root_criterion_reports_pending_ids_without_granting_release(tmp_path):
    root = _materialize(tmp_path)
    before = _registry_path(root).read_bytes()
    report = assert_governance_readiness(root)
    records = yaml.safe_load(before)["controls"]
    expected = tuple(
        sorted(
            r["control_id"]
            for r in records
            if r["release_class"] == "root-of-trust"
            and r["evidence_status"] != "verified"
        )
    )
    assert report.ok
    assert expected and report.pending_root_of_trust == expected
    assert not report.root_of_trust_ready
    assert _registry_path(root).read_bytes() == before


def test_root_criterion_excludes_pending_content_and_consumer_controls(tmp_path):
    root = _materialize(tmp_path)
    data = yaml.safe_load(_registry_path(root).read_text(encoding="utf-8"))
    for record in data["controls"]:
        if record["release_class"] == "root-of-trust":
            record["evidence_status"] = "verified"
            record["implementation"] = ["engine/example.py"]
            record["test_evidence"] = ["tests/test_example.py"]
    # Synthetic fixture proves classification semantics, not real evidence closure.
    _write_registry(root, data)
    report = assert_governance_readiness(root)
    assert report.root_of_trust_ready
    assert report.pending_root_of_trust == ()
    assert any(r["evidence_status"] == "pending" for r in data["controls"])


@pytest.mark.parametrize(
    "damage",
    [
        "missing-file",
        "invalid-yaml",
        "invalid-root",
        "missing-class",
        "unknown-class",
        "no-roots",
        "invalid-status",
    ],
)
def test_registry_failure_cannot_satisfy_root_criterion(tmp_path, damage):
    root = _materialize(tmp_path)
    path = _registry_path(root)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if damage == "missing-file":
        path.unlink()
    elif damage == "invalid-yaml":
        path.write_text("controls: [", encoding="utf-8")
    elif damage == "invalid-root":
        path.write_text("[]", encoding="utf-8")
    else:
        if damage == "missing-class":
            data["controls"][0].pop("release_class")
        elif damage == "unknown-class":
            data["controls"][0]["release_class"] = "unknown"
        elif damage == "invalid-status":
            next(r for r in data["controls"] if r["release_class"] == "root-of-trust")[
                "evidence_status"
            ] = "unknown"
        else:
            for record in data["controls"]:
                record["release_class"] = "consumer-artifact"
        _write_registry(root, data)
    report = audit_governance_readiness(root)
    assert not report.ok
    assert not report.root_of_trust_ready
    with pytest.raises(RuntimeError, match="control-registry"):
        assert_governance_readiness(root)


def test_gap_root_control_remains_a_release_blocker(tmp_path):
    root = _materialize(tmp_path)
    data = yaml.safe_load(_registry_path(root).read_text(encoding="utf-8"))
    record = next(
        r
        for r in data["controls"]
        if r["release_class"] == "root-of-trust" and r["evidence_status"] == "pending"
    )
    record["evidence_status"] = "gap"
    _write_registry(root, data)
    report = assert_governance_readiness(root)
    assert record["control_id"] in report.pending_root_of_trust
    assert not report.root_of_trust_ready


@pytest.mark.parametrize(
    ("mutator", "code"),
    (
        (
            lambda layout, bootstrap: layout.pop("governance_qualification"),
            "qualification-contract-missing",
        ),
        (
            lambda layout, bootstrap: layout["governance_qualification"].__setitem__(
                "required_controls", []
            ),
            "required-controls-invalid",
        ),
        (
            lambda layout, bootstrap: layout["governance_qualification"][
                "required_controls"
            ].pop("genesis_integrity"),
            "required-control-missing",
        ),
        (
            lambda layout, bootstrap: layout["governance_qualification"][
                "required_controls"
            ].__setitem__("genesis_integrity", []),
            "control-closure-invalid",
        ),
        (
            lambda layout, bootstrap: layout["governance_qualification"][
                "required_controls"
            ]["genesis_integrity"].__setitem__("policy_ref", "missing_policy"),
            "policy-reference-invalid",
        ),
        (
            lambda layout, bootstrap: layout["governance_qualification"][
                "required_controls"
            ]["genesis_integrity"].__setitem__("implementation", []),
            "evidence-list-invalid",
        ),
        (
            lambda layout, bootstrap: bootstrap["genesis_contract"].__setitem__(
                "local_qualification_required", False
            ),
            "local-qualification-not-required",
        ),
        (
            lambda layout, bootstrap: bootstrap["genesis_contract"].__setitem__(
                "local_qualification_entrypoint", "wrong.py"
            ),
            "local-qualification-entrypoint-mismatch",
        ),
        (
            lambda layout, bootstrap: bootstrap["governance_control_plane"].__setitem__(
                "architecture_admission", "open"
            ),
            "bootstrap-governance-state-invalid",
        ),
        (
            lambda layout, bootstrap: bootstrap["provenance"].__setitem__(
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
    closure = layout["governance_qualification"]["required_controls"][
        "genesis_integrity"
    ]
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
    assert (
        sum(
            finding.code == "qualification-entrypoint-invalid"
            for finding in report.findings
        )
        == 2
    )


@pytest.mark.parametrize(
    ("makefile", "code"),
    (
        (
            MAKEFILE.replace("genesis-check:", "genesis-old:"),
            "makefile-target-missing",
        ),
        (
            MAKEFILE.replace(
                "python scripts/mutation_integrity.py",
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

    layout = root / "governance" / "framework" / "source-layout.yaml"
    layout.write_text("[", encoding="utf-8")
    report = audit_governance_readiness(root)
    assert any(finding.code == "yaml-load-failed" for finding in report.findings)

    layout.write_text("- list\n", encoding="utf-8")
    report = audit_governance_readiness(root)
    assert any(finding.code == "yaml-root-invalid" for finding in report.findings)


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
        finding.code == "bootstrap-contract-invalid" for finding in report.findings
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
    codes = {finding.code for finding in report.findings}

    assert "bootstrap-governance-state-invalid" in codes
    assert "bootstrap-provenance-invalid" in codes


def test_makefile_read_failure_is_reported(tmp_path):
    root = _materialize(tmp_path)
    (root / "Makefile").unlink()

    report = audit_governance_readiness(root)

    assert any(finding.code == "makefile-read-failed" for finding in report.findings)


def test_nonstring_evidence_is_reported(tmp_path):
    layout = copy.deepcopy(SOURCE_LAYOUT)
    layout["governance_qualification"]["required_controls"]["genesis_integrity"][
        "test_evidence"
    ] = [123]

    root = _materialize(
        tmp_path,
        layout=layout,
    )
    report = audit_governance_readiness(root)

    assert any(finding.code == "evidence-path-invalid" for finding in report.findings)


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
