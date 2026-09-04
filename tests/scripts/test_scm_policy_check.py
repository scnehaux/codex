from __future__ import annotations

import importlib.util

from tests.support.repository import REPOSITORY_ROOT


SCRIPT = REPOSITORY_ROOT / "scripts/scm_policy_check.py"


def _load():
    spec = importlib.util.spec_from_file_location("scm_policy_check_script", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_current_repository_policy_passes():
    assert _load().main() == 0


def test_policy_failure_is_reported(monkeypatch, capsys):
    module = _load()

    def fail(_root):
        raise module.SCMPolicyError("broken")

    monkeypatch.setattr(module, "assert_scm_enforcement_policy", fail)
    assert module.main() == 1
    assert "broken" in capsys.readouterr().out
