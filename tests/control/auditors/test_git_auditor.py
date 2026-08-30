from engine.control.auditors.git_auditor import audit_version_bump


def test_version_bump_audit_is_noop_during_prebaseline():
    assert audit_version_bump({}, {}) == []
