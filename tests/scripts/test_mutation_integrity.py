from __future__ import annotations

import importlib.util
import subprocess
import sys

from tests.support.repository import REPOSITORY_ROOT


SCRIPT = REPOSITORY_ROOT / "scripts" / "mutation_integrity.py"


def _load():
    spec = importlib.util.spec_from_file_location(
        "mutation_integrity_script",
        SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_mutation_integrity_entrypoint_is_thin_adapter(monkeypatch, capsys):
    module = _load()

    class Report:
        mode = "pre-genesis"
        checked_documents = 12

    monkeypatch.setattr(
        module,
        "assert_version_mutation_integrity",
        lambda root: Report(),
    )

    assert module.main() == 0
    output = capsys.readouterr().out
    assert "Version + mutation integrity" in output
    assert "governed documents: 12" in output


def test_mutation_integrity_entrypoint_returns_nonzero(monkeypatch, capsys):
    module = _load()

    def fail(_root):
        raise RuntimeError("broken")

    monkeypatch.setattr(
        module,
        "assert_version_mutation_integrity",
        fail,
    )

    assert module.main() == 1
    assert "broken" in capsys.readouterr().out


def test_mutation_integrity_runs_as_direct_python_script():
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (result.stdout or "") + "\n" + (result.stderr or "")
    assert "[PASS] Version + mutation integrity" in result.stdout
