from __future__ import annotations

import importlib.util
import os
from datetime import date
from pathlib import Path
import stat

import pytest


ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "06-fitness-function" / "scripts"


def _load(filename: str, name: str):
    path = SCRIPTS / filename
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_codeowners_parse_ignores_comments_blank_and_global(tmp_path):
    module = _load("codeowners-validator.py", "codeowners_parse")

    codeowners = tmp_path / "CODEOWNERS"
    codeowners.write_text(
        '# comment\n\n* @global\n/00-governance/ @architecture\nengine/control/ @engine\n',
        encoding="utf-8",
    )

    assert module.parse_codeowners(codeowners) == [
        (4, "/00-governance/"),
        (5, 'engine/control/'),
    ]


def test_codeowners_resolve_file_directory_glob_and_missing(tmp_path, monkeypatch):
    module = _load("codeowners-validator.py", "codeowners_resolve")
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)

    directory = tmp_path / "docs"
    directory.mkdir()
    file_path = tmp_path / "README.md"
    file_path.write_text("x", encoding="utf-8")
    nested = tmp_path / "rules"
    nested.mkdir()
    (nested / "a.md").write_text("x", encoding="utf-8")

    assert module.resolve_path("/docs/") is True
    assert module.resolve_path("/README.md") is True
    assert module.resolve_path("rules/*.md") is True
    assert module.resolve_path("/missing.md") is False
    assert module.resolve_path("/missing/") is False
    assert module.resolve_path("missing/*.md") is False


def test_codeowners_main_missing_file_returns_one(tmp_path, monkeypatch, capsys):
    module = _load("codeowners-validator.py", "codeowners_missing")
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(module, "CODEOWNERS_PATH", tmp_path / ".github" / "CODEOWNERS")

    assert module.main() == 1
    assert "CODEOWNERS file not found" in capsys.readouterr().out


def test_codeowners_main_reports_stale_and_success(tmp_path, monkeypatch, capsys):
    module = _load("codeowners-validator.py", "codeowners_main")
    github = tmp_path / ".github"
    github.mkdir()
    codeowners = github / "CODEOWNERS"

    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(module, "CODEOWNERS_PATH", codeowners)

    codeowners.write_text(
        "/exists/ @team\n"
        "/missing/ @team\n",
        encoding="utf-8",
    )
    (tmp_path / "exists").mkdir()

    assert module.main() == 1
    output = capsys.readouterr().out
    assert "CODEOWNERS PATH VALIDATION FAILED" in output
    assert "Line 2: /missing/" in output
    assert "Fix: Update the paths" in output

    codeowners.write_text("/exists/ @team\n", encoding="utf-8")
    assert module.main() == 0
    assert "SUCCESS: CODEOWNERS validation passed" in capsys.readouterr().out


def test_install_hook_missing_git_hooks_returns_one(tmp_path, monkeypatch, capsys):
    module = _load("install-hooks.py", "install_missing")
    monkeypatch.setattr(module, "repository_root", lambda: str(tmp_path))

    assert module.install_hook() == 1
    assert ".git/hooks directory not found" in capsys.readouterr().out


def test_install_hook_windows_writes_powershell(tmp_path, monkeypatch):
    module = _load("install-hooks.py", "install_windows")
    hooks = tmp_path / ".git" / "hooks"
    hooks.mkdir(parents=True)

    monkeypatch.setattr(module, "repository_root", lambda: str(tmp_path))
    monkeypatch.setattr(module.sys, "platform", "win32")

    assert module.install_hook() == 0

    content = (hooks / "pre-commit").read_text(encoding="utf-8")
    assert content.startswith("#!/usr/bin/env powershell")
    assert "make lint-code" in content
    assert "make test" in content
    assert "Governance check passed" in content


def test_install_hook_unix_writes_bash_and_requests_executable_bit(
    tmp_path,
    monkeypatch,
):
    module = _load("install-hooks.py", "install_unix")
    hooks = tmp_path / ".git" / "hooks"
    hooks.mkdir(parents=True)

    monkeypatch.setattr(module, "repository_root", lambda: str(tmp_path))
    monkeypatch.setattr(module.sys, "platform", "linux")

    chmod_calls = []
    real_stat = module.os.stat

    monkeypatch.setattr(
        module.os,
        "chmod",
        lambda path, mode: chmod_calls.append((path, mode)),
    )

    assert module.install_hook() == 0

    hook = hooks / "pre-commit"
    content = hook.read_text(encoding="utf-8")
    assert content.startswith("#!/bin/bash")
    assert "make lint-docs-format" in content

    assert len(chmod_calls) == 1
    chmod_path, chmod_mode = chmod_calls[0]
    assert Path(chmod_path) == hook
    assert chmod_mode == (real_stat(hook).st_mode | stat.S_IEXEC)


def test_install_hook_main_delegates(monkeypatch):
    module = _load("install-hooks.py", "install_main")
    monkeypatch.setattr(module, "install_hook", lambda: 7)
    assert module.main() == 7


def _write_adr(directory: Path, filename: str, frontmatter: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / filename).write_text(
        f"---\n{frontmatter}\n---\n# ADR\n",
        encoding="utf-8",
    )


def test_waiver_expiry_no_corpus_passes(tmp_path, capsys):
    module = _load("waiver-expiry-check.py", "waiver_empty")

    assert module.check_waiver_expiry(
        adr_dir=str(tmp_path / "missing"),
        current_date=date(2026, 8, 30),
    ) == 0

    assert "[PASS] No expired waivers found." in capsys.readouterr().out


def test_waiver_expiry_ignores_non_adr_and_non_active_waivers(tmp_path, capsys):
    module = _load("waiver-expiry-check.py", "waiver_ignored")

    (tmp_path / "INDEX.md").write_text("ignored", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("ignored", encoding="utf-8")

    _write_adr(
        tmp_path,
        "ADR-001.md",
        "doc_meta:\n"
        "  adr_type: decision\n"
        "  status: accepted\n",
    )
    _write_adr(
        tmp_path,
        "ADR-002.md",
        "doc_meta:\n"
        "  adr_type: exception\n"
        "  status: proposed\n"
        "  exception_info:\n"
        "    expiry_date: 2026-08-01\n",
    )
    _write_adr(
        tmp_path,
        "ADR-003.md",
        "doc_meta:\n"
        "  adr_type: exception\n"
        "  status: accepted\n"
        "  exception_info: {}\n",
    )

    assert module.check_waiver_expiry(
        adr_dir=str(tmp_path),
        current_date=date(2026, 8, 30),
    ) == 0

    assert "[PASS]" in capsys.readouterr().out


def test_waiver_expiry_reports_expired_warning_future_and_invalid(tmp_path, capsys):
    module = _load("waiver-expiry-check.py", "waiver_states")

    common = (
        "doc_meta:\n"
        "  adr_type: exception\n"
        "  status: accepted\n"
        "  exception_info:\n"
    )

    _write_adr(
        tmp_path,
        "ADR-EXPIRED.md",
        common + "    expiry_date: 2026-08-20\n",
    )
    _write_adr(
        tmp_path,
        "ADR-WARNING.md",
        common + "    expiry_date: 2026-09-10\n",
    )
    _write_adr(
        tmp_path,
        "ADR-FUTURE.md",
        common + "    expiry_date: 2027-01-01\n",
    )
    _write_adr(
        tmp_path,
        "ADR-INVALID.md",
        common + "    expiry_date: definitely-not-a-date\n",
    )

    assert module.check_waiver_expiry(
        adr_dir=str(tmp_path),
        current_date=date(2026, 8, 30),
    ) == 1

    output = capsys.readouterr().out
    assert "[CRITICAL] Expired waiver:" in output
    assert "[WARNING] Expiring soon:" in output
    assert "[ERROR] Invalid expiry_date format" in output
    assert "[FAIL] Expiry check failed" in output
    assert "ADR-FUTURE.md" not in output


def test_waiver_expiry_malformed_frontmatter_is_skipped(tmp_path, capsys):
    module = _load("waiver-expiry-check.py", "waiver_malformed")

    (tmp_path / "ADR-BAD.md").write_text(
        "---\ndoc_meta: [broken\n---\n",
        encoding="utf-8",
    )
    (tmp_path / "ADR-NO-FRONTMATTER.md").write_text(
        "# no frontmatter\n",
        encoding="utf-8",
    )

    assert module.check_waiver_expiry(
        adr_dir=str(tmp_path),
        current_date=date(2026, 8, 30),
    ) == 0

    assert "[PASS]" in capsys.readouterr().out


def test_waiver_main_delegates(monkeypatch):
    module = _load("waiver-expiry-check.py", "waiver_main")
    monkeypatch.setattr(module, "check_waiver_expiry", lambda: 9)
    assert module.main() == 9

def test_install_hook_repository_root_contract():
    module = _load("install-hooks.py", "install_repository_root")

    expected = Path(module.__file__).resolve().parents[2]
    assert Path(module.repository_root()).resolve() == expected

