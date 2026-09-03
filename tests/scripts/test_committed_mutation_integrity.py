from __future__ import annotations

import importlib.util

from tests.support.repository import REPOSITORY_ROOT

SCRIPT = REPOSITORY_ROOT / "scripts/committed_mutation_integrity.py"


def load():
    spec = importlib.util.spec_from_file_location("committed_mutation_script", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_missing_baseline_returns_2(capsys):
    module = load()
    assert module.main([]) == 2
    assert "baseline is required" in capsys.readouterr().out


def test_success_and_failure(monkeypatch, capsys):
    module = load()

    class Report:
        base_ref = "base"
        merge_base = "abc"
        head_ref = "HEAD"
        checked_mutations = 2

    monkeypatch.setattr(
        module, "assert_committed_mutation_integrity", lambda *a, **k: Report()
    )
    assert module.main(["--base-ref", "base"]) == 0
    assert "Committed mutation integrity" in capsys.readouterr().out

    def fail(*a, **k):
        raise RuntimeError("broken")

    monkeypatch.setattr(module, "assert_committed_mutation_integrity", fail)
    assert module.main(["--base-ref", "base"]) == 1
