import yaml

from engine.control.auditors.governance_auditor import audit_architecture_admission


SEVERITIES = {"architecture_admission_violation": "CRITICAL"}


def _manifest(tmp_path, state="closed", required=None):
    governance = tmp_path / "00-governance"
    governance.mkdir(parents=True)
    data = {
        "governance_control_plane": {
            "architecture_admission": state,
            "required_baseline_ids": required or ["GDC-000", "GDC-001"],
        }
    }
    (governance / "bootstrap-manifest.yaml").write_text(
        yaml.safe_dump(data),
        encoding="utf-8",
    )


def test_closed_admission_allows_governance_only(tmp_path):
    _manifest(tmp_path, "closed")
    meta = {
        "GDC-000": {"status": "draft", "version": "0.0.1"},
        "GDC-001": {"status": "draft", "version": "0.0.1"},
    }
    assert audit_architecture_admission(meta, SEVERITIES, str(tmp_path)) == []


def test_closed_admission_blocks_architecture_artifacts(tmp_path):
    _manifest(tmp_path, "closed")
    meta = {
        "GDC-000": {"status": "draft", "version": "0.0.1"},
        "PAD-001": {"status": "draft", "version": "0.0.1"},
    }
    findings = audit_architecture_admission(meta, SEVERITIES, str(tmp_path))
    assert len(findings) == 1
    assert findings[0][0] == "CRITICAL"
    assert "PAD-001" in findings[0][1]


def test_open_admission_requires_approved_stable_baseline(tmp_path):
    _manifest(tmp_path, "open")
    meta = {
        "GDC-000": {"status": "draft", "version": "0.0.1"},
        "GDC-001": {"status": "approved", "version": "1.0.0"},
    }
    findings = audit_architecture_admission(meta, SEVERITIES, str(tmp_path))
    assert len(findings) == 1
    assert "GDC-000" in findings[0][1]


def test_open_admission_accepts_stable_baseline(tmp_path):
    _manifest(tmp_path, "open")
    meta = {
        "GDC-000": {"status": "approved", "version": "1.0.0"},
        "GDC-001": {"status": "approved", "version": "1.2.0"},
        "PAD-001": {"status": "draft", "version": "0.1.0"},
    }
    assert audit_architecture_admission(meta, SEVERITIES, str(tmp_path)) == []

def test_missing_manifest_is_not_a_bootstrap_repo(tmp_path):
    assert audit_architecture_admission({}, SEVERITIES, str(tmp_path)) == []


def test_unreadable_manifest_fails_closed(tmp_path):
    governance = tmp_path / "00-governance"
    governance.mkdir()
    (governance / "bootstrap-manifest.yaml").write_text("governance_control_plane: [", encoding="utf-8")
    findings = audit_architecture_admission({}, SEVERITIES, str(tmp_path))
    assert len(findings) == 1
    assert "unreadable" in findings[0][1].lower()


def test_invalid_admission_state_fails_closed(tmp_path):
    _manifest(tmp_path, "maybe")
    findings = audit_architecture_admission({}, SEVERITIES, str(tmp_path))
    assert len(findings) == 1
    assert "closed" in findings[0][1] and "open" in findings[0][1]


def test_open_admission_reports_missing_required_baseline(tmp_path):
    _manifest(tmp_path, "open", required=["GDC-000", "GDC-404"])
    meta = {"GDC-000": {"status": "approved", "version": "1.0.0"}}
    findings = audit_architecture_admission(meta, SEVERITIES, str(tmp_path))
    assert len(findings) == 1
    assert "GDC-404 is missing" in findings[0][1]


def test_open_admission_rejects_malformed_version(tmp_path):
    _manifest(tmp_path, "open", required=["GDC-000"])
    meta = {"GDC-000": {"status": "approved", "version": "not-semver"}}
    findings = audit_architecture_admission(meta, SEVERITIES, str(tmp_path))
    assert len(findings) == 1
    assert "expected >=1.0.0" in findings[0][1]
