from __future__ import annotations

import importlib.util

from tests.support.repository import REPOSITORY_ROOT


SCRIPT = REPOSITORY_ROOT / "scripts" / "github_live_state_observe.py"


def _load():
    spec = importlib.util.spec_from_file_location(
        "github_live_state_observe_script",
        SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_main_reports_observed_drift_without_claiming_effectiveness(
    monkeypatch,
    capsys,
):
    module = _load()
    monkeypatch.setattr(module, "_revision", lambda repository, token: "abc")

    def fake_get(url, token):
        if url.endswith("/rulesets"):
            return [], None
        if url.endswith("/branches/main/protection"):
            return None, "HTTP 403: Forbidden"
        raise AssertionError(url)

    monkeypatch.setattr(module, "_get_json", fake_get)
    assert module.main(["--repository", "scnehaux/codex"]) == 0
    output = capsys.readouterr().out
    assert "observation: OBSERVED" in output
    assert "desired ruleset: NOT-INSTALLED" in output
    assert "drift: DRIFTED" in output
    assert "behavioral enforcement proof: NOT CLAIMED" in output


def test_main_json_reports_unknown_state(monkeypatch, capsys):
    module = _load()
    monkeypatch.setattr(module, "_revision", lambda repository, token: "unknown")

    def fake_get(url, token):
        if url.endswith("/rulesets"):
            return None, "HTTP 403: Forbidden"
        if url.endswith("/branches/main/protection"):
            return None, "HTTP 403: Forbidden"
        raise AssertionError(url)

    monkeypatch.setattr(module, "_get_json", fake_get)
    assert module.main(["--repository", "scnehaux/codex", "--json"]) == 0
    output = capsys.readouterr().out
    assert '"observation_state": "unknown"' in output
    assert '"drift_state": "unknown"' in output
