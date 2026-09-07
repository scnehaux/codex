from __future__ import annotations

import ast
from pathlib import Path

import yaml

from engine.control.linting import lint_file
from engine.control.linting.facade import lint_file as facade_lint_file
from tests.support.repository import REPOSITORY_ROOT


def _imports(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            found.append(node.module)
        elif isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
    return tuple(found)


def test_linting_facade_is_canonical_control_owner():
    assert lint_file is facade_lint_file
    facade = REPOSITORY_ROOT / "engine" / "control" / "linting" / "facade.py"
    cli = REPOSITORY_ROOT / "engine" / "interfaces" / "cli.py"
    facade_tree = ast.parse(facade.read_text(encoding="utf-8"))
    cli_tree = ast.parse(cli.read_text(encoding="utf-8"))
    assert any(
        isinstance(node, ast.FunctionDef) and node.name == "lint_file"
        for node in facade_tree.body
    )
    assert not any(
        isinstance(node, ast.FunctionDef) and node.name == "lint_file"
        for node in cli_tree.body
    )
    assert "engine.control.linting" in _imports(cli)
    assert not any(name.startswith("engine.interfaces") for name in _imports(facade))


def test_tooling_is_verification_not_product_runtime():
    layout = yaml.safe_load(
        (REPOSITORY_ROOT / "governance" / "framework" / "source-layout.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert layout["tooling"]["product_runtime_allowed"] is False
    assert (REPOSITORY_ROOT / "engine").is_dir()
    assert (REPOSITORY_ROOT / "engine" / "control" / "linting").is_dir()


def test_control_layout_declares_linting_responsibility():
    layout = yaml.safe_load(
        (REPOSITORY_ROOT / "governance" / "framework" / "source-layout.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert "linting" in layout["package"]["control"]["responsibility"]
