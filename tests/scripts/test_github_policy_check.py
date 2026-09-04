from __future__ import annotations

import importlib.util
import json
import shutil

from tests.support.repository import REPOSITORY_ROOT

SCRIPT = REPOSITORY_ROOT / "scripts/github_policy_check.py"


def load(path=SCRIPT):
    spec = importlib.util.spec_from_file_location("github_policy_check_script", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_current_repository_policy_passes():
    assert load().main() == 0


def test_bypass_actor_drift_fails(tmp_path, monkeypatch):
    for rel in (
        "governance/github/main-ruleset.json",
        "governance/github/authority-binding.yaml",
        ".github/workflows/governance.yml",
        ".github/CODEOWNERS",
        ".github/pull_request_template.md",
    ):
        src = REPOSITORY_ROOT / rel
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    path = tmp_path / "governance/github/main-ruleset.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["bypass_actors"] = [{"actor_id": 1}]
    path.write_text(json.dumps(data), encoding="utf-8")
    module = load()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    assert module.main() == 1


def test_floating_action_tag_fails(tmp_path, monkeypatch):
    for rel in (
        "governance/github/main-ruleset.json",
        "governance/github/authority-binding.yaml",
        ".github/workflows/governance.yml",
        ".github/CODEOWNERS",
        ".github/pull_request_template.md",
    ):
        src = REPOSITORY_ROOT / rel
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    workflow = tmp_path / ".github/workflows/governance.yml"
    workflow.write_text(
        workflow.read_text(encoding="utf-8").replace(
            "actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803",
            "actions/checkout@v6",
        ),
        encoding="utf-8",
    )
    module = load()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    assert module.main() == 1


def test_candidate_workflow_cannot_emit_external_authority_context(
    tmp_path, monkeypatch
):
    for rel in (
        "governance/github/main-ruleset.json",
        "governance/github/authority-binding.yaml",
        ".github/workflows/governance.yml",
        ".github/CODEOWNERS",
        ".github/pull_request_template.md",
    ):
        src = REPOSITORY_ROOT / rel
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    workflow = tmp_path / ".github/workflows/governance.yml"
    workflow.write_text(
        workflow.read_text(encoding="utf-8") + "\n# Codex Governance Authority\n",
        encoding="utf-8",
    )
    module = load()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    assert module.main() == 1


def test_candidate_revision_cannot_be_external_authority(tmp_path, monkeypatch):
    for rel in (
        "governance/github/main-ruleset.json",
        "governance/github/authority-binding.yaml",
        ".github/workflows/governance.yml",
        ".github/CODEOWNERS",
        ".github/pull_request_template.md",
    ):
        src = REPOSITORY_ROOT / rel
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    binding = tmp_path / "governance/github/authority-binding.yaml"
    data = __import__("yaml").safe_load(binding.read_text(encoding="utf-8"))
    data["evaluator"]["candidate_revision_as_authority"] = True
    binding.write_text(
        __import__("yaml").safe_dump(data, sort_keys=False), encoding="utf-8"
    )
    module = load()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    assert module.main() == 1
