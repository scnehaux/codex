from __future__ import annotations

import importlib.util
import subprocess
import sys

from tests.support.repository import REPOSITORY_ROOT


SCRIPT = REPOSITORY_ROOT / "scripts" / "governance_qualify.py"


def _load():
    spec = importlib.util.spec_from_file_location(
        "governance_qualify_script",
        SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class _Readiness:
    checked_controls = ("a", "b", "c")


class _Genesis:
    mode = "pre-genesis"


class _Mutation:
    mode = "pre-genesis"


def _green(monkeypatch, module):
    monkeypatch.setattr(
        module,
        "assert_governance_readiness",
        lambda root: _Readiness(),
    )
    monkeypatch.setattr(
        module,
        "assert_genesis_integrity",
        lambda root: _Genesis(),
    )
    monkeypatch.setattr(
        module,
        "assert_version_mutation_integrity",
        lambda root: _Mutation(),
    )


def test_control_only_composes_all_permanent_controls(
    monkeypatch,
    capsys,
):
    module = _load()
    _green(monkeypatch, module)

    assert module.main(["--control-only"]) == 0
    output = capsys.readouterr().out
    assert "Governance control qualification" in output
    assert "controls: 3" in output
    assert "skipped" in output


def test_qualification_fails_closed_on_control_failure(
    monkeypatch,
    capsys,
):
    module = _load()

    def fail(_root):
        raise RuntimeError("broken")

    monkeypatch.setattr(
        module,
        "assert_governance_readiness",
        fail,
    )

    assert module.main(["--control-only"]) == 1
    assert "broken" in capsys.readouterr().out


def test_full_qualification_propagates_pytest_failure(
    monkeypatch,
    capsys,
):
    module = _load()
    _green(monkeypatch, module)

    class Result:
        returncode = 7

    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *args, **kwargs: Result(),
    )

    assert module.main([]) == 7
    assert "full governance qualification regression" in (capsys.readouterr().out)


def test_full_qualification_passes_when_pytest_passes(
    monkeypatch,
    capsys,
):
    module = _load()
    _green(monkeypatch, module)

    class Result:
        returncode = 0

    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *args, **kwargs: Result(),
    )

    assert module.main([]) == 0
    assert "[PASS] full governance qualification regression" in (
        capsys.readouterr().out
    )


def test_permanent_qualifier_runs_directly_in_control_only_mode():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--control-only"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (result.stdout or "") + "\n" + (result.stderr or "")
    assert "[PASS] Governance control qualification" in result.stdout
