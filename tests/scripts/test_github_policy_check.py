from __future__ import annotations

import importlib.util

from tests.support.repository import REPOSITORY_ROOT


SCRIPT = REPOSITORY_ROOT / "scripts/github_policy_check.py"


def _load():
    spec = importlib.util.spec_from_file_location("github_policy_check_script", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_current_repository_projection_passes(monkeypatch, capsys):
    module = _load()
    assert module.main() == 0
    capsys.readouterr()

    assert module.main(["--activation-plan"]) == 2
    blocked = capsys.readouterr().out
    assert "authority-integration-id-unbound" in blocked
    assert "authority-revision-unbound" in blocked
    assert "effective enforcement: NOT CLAIMED" in blocked

    class ReadyPlan:
        ready = True
        blockers = ()
        authority_revision = "a" * 40
        integration_id = 4242
        ruleset_payload = {"name": "main-governance"}

    monkeypatch.setattr(
        module, "build_github_activation_plan", lambda root, policy: ReadyPlan()
    )
    assert module.main(["--activation-plan"]) == 0
    rendered = capsys.readouterr().out
    assert '"integration_id": 4242' in rendered
    assert '"authority_revision"' in rendered
    assert '"ruleset_payload"' in rendered

    assert module.main(["--invalid"]) == 2
    assert "usage:" in capsys.readouterr().out


def test_policy_failure_is_reported(monkeypatch, capsys):
    module = _load()

    def fail(_root):
        raise module.SCMPolicyError("broken")

    monkeypatch.setattr(module, "assert_scm_enforcement_policy", fail)
    assert module.main() == 1
    assert "broken" in capsys.readouterr().out


def test_projection_failure_is_reported(monkeypatch, capsys):
    module = _load()

    class Policy:
        pass

    class Finding:
        code = "drift"
        message = "broken projection"

    class Report:
        findings = (Finding(),)

    monkeypatch.setattr(module, "assert_scm_enforcement_policy", lambda root: Policy())
    monkeypatch.setattr(
        module, "audit_github_projection", lambda root, policy: Report()
    )
    assert module.main() == 1
    assert "broken projection" in capsys.readouterr().out
