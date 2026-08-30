from __future__ import annotations

import importlib.util

from tests.support.repository import REPOSITORY_ROOT


SCRIPT = (
    REPOSITORY_ROOT
    / "06-fitness-function"
    / "scripts"
    / "genesis_integrity.py"
)


def _load():
    spec = importlib.util.spec_from_file_location(
        "genesis_integrity_script",
        SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_genesis_integrity_entrypoint_is_thin_adapter(monkeypatch, capsys):
    module = _load()

    class Report:
        mode = "pre-genesis"
        candidate_files = ("a", "b")
        root_commit = None

    monkeypatch.setattr(
        module,
        "assert_genesis_integrity",
        lambda root: Report(),
    )

    assert module.main() == 0
    output = capsys.readouterr().out
    assert "Genesis integrity" in output
    assert "candidate files: 2" in output


def test_genesis_integrity_entrypoint_returns_nonzero_on_failure(monkeypatch, capsys):
    module = _load()

    def fail(_root):
        raise RuntimeError("broken")

    monkeypatch.setattr(
        module,
        "assert_genesis_integrity",
        fail,
    )

    assert module.main() == 1
    assert "broken" in capsys.readouterr().out


def test_genesis_integrity_entrypoint_runs_as_direct_python_script():
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        (result.stdout or "") + "\n" + (result.stderr or "")
    )
    assert "[PASS] Genesis integrity" in result.stdout
