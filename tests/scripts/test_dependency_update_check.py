from __future__ import annotations

from types import SimpleNamespace

import scripts.dependency_update_check as target


def test_dependency_update_check_requires_baseline(capsys):
    assert target.main([]) == 2
    assert "baseline is required" in capsys.readouterr().out


def test_dependency_update_check_reports_engine_failure(monkeypatch, capsys):
    def fail(*args, **kwargs):
        raise RuntimeError("synthetic partial dependency update")

    monkeypatch.setattr(target, "assert_dependency_update_integrity", fail)
    assert target.main(["--base-ref", "base"]) == 1
    assert "synthetic partial dependency update" in capsys.readouterr().out


def test_dependency_update_check_reports_success(monkeypatch, capsys):
    report = SimpleNamespace(
        changed_files=("README.md",),
        checked_bundles=(),
    )
    monkeypatch.setattr(
        target,
        "assert_dependency_update_integrity",
        lambda *args, **kwargs: report,
    )
    assert target.main(["--base-ref", "base"]) == 0
    output = capsys.readouterr().out
    assert "dependency update integrity" in output
    assert "checked bundles: none" in output
