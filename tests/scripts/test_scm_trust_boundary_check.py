from __future__ import annotations

import importlib.util
import shutil

from tests.support.repository import REPOSITORY_ROOT


SCRIPT = REPOSITORY_ROOT / "scripts" / "scm_trust_boundary_check.py"


def _load():
    spec = importlib.util.spec_from_file_location(
        "scm_trust_boundary_check_script",
        SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_current_repository_contract_passes(capsys):
    module = _load()

    assert module.main() == 0
    output = capsys.readouterr().out
    assert "[PASS] SCM enforcement trust-boundary contract" in output
    assert "NOT PROVEN" in output


def test_invalid_contract_fails_closed(tmp_path, monkeypatch, capsys):
    src = REPOSITORY_ROOT / "governance" / "scm" / "trust-boundary.yaml"
    dst = tmp_path / "governance" / "scm" / "trust-boundary.yaml"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    dst.write_text(
        dst.read_text(encoding="utf-8").replace(
            "may_be_sole_guardrail_authority: false",
            "may_be_sole_guardrail_authority: true",
        ),
        encoding="utf-8",
    )

    module = _load()
    monkeypatch.setattr(module, "ROOT", tmp_path)

    assert module.main() == 1
    assert "candidate-self-authorization-forbidden" in capsys.readouterr().out
