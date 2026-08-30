from __future__ import annotations

import importlib.util

from tests.support.repository import REPOSITORY_ROOT


SCRIPT = (
    REPOSITORY_ROOT
    / "06-fitness-function"
    / "scripts"
    / "genesis_commit_qualify.py"
)


def _load():
    spec = importlib.util.spec_from_file_location(
        "genesis_commit_qualify_script",
        SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_entrypoint_is_thin_adapter(monkeypatch, capsys):
    module = _load()

    class Report:
        staged_files = ("a", "b")
        tree_sha = "a" * 40

    monkeypatch.setattr(
        module,
        "assert_genesis_commit_candidate",
        lambda root: Report(),
    )

    assert module.main() == 0
    output = capsys.readouterr().out
    assert "Genesis commit candidate" in output
    assert "staged files: 2" in output


def test_entrypoint_returns_nonzero_on_failure(
    monkeypatch,
    capsys,
):
    module = _load()

    def fail(_root):
        raise RuntimeError("broken")

    monkeypatch.setattr(
        module,
        "assert_genesis_commit_candidate",
        fail,
    )

    assert module.main() == 1
    assert "broken" in capsys.readouterr().out
