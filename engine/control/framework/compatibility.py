from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CompatibilityFinding:
    code: str
    path: str
    detail: str


def _python_files(root: Path, relative_root: str) -> tuple[Path, ...]:
    base = root / relative_root
    if not base.exists():
        return ()
    return tuple(
        sorted(
            path
            for path in base.rglob("*.py")
            if "__pycache__" not in path.parts
        )
    )


def audit_ai_native_compatibility(root: Path) -> tuple[CompatibilityFinding, ...]:
    findings: list[CompatibilityFinding] = []

    parser = (
        root
        / 'engine' / "control" / "parsing"
        / "markdown_ast.py"
    )
    if parser.is_file():
        text = parser.read_text(encoding="utf-8")
        if 're.search(r"^---' in text or 're.sub(r"^---' in text:
            findings.append(
                CompatibilityFinding(
                    "SEMANTIC_FRONTMATTER_REGEX",
                    parser.relative_to(root).as_posix(),
                    "frontmatter semantics must use canonical parsing",
                )
            )

    generators = _python_files(
        root,
        "06-fitness-function/generators",
    )
    forbidden_generator_imports = {
        'engine.control.parsing.markdown_ast',
        "markdown_it",
    }
    for path in generators:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            findings.append(
                CompatibilityFinding(
                    "GENERATOR_PARSE_ERROR",
                    path.relative_to(root).as_posix(),
                    "generator could not be parsed for compatibility audit",
                )
            )
            continue

        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)

        matches = sorted(imported & forbidden_generator_imports)
        if matches:
            findings.append(
                CompatibilityFinding(
                    "GENERATOR_INDEPENDENT_PARSING",
                    path.relative_to(root).as_posix(),
                    f"generator imports parsing substrate: {matches}",
                )
            )

    graph = (
        root
        / 'engine' / "core" / "knowledge"
        / "graph.py"
    )
    if graph.is_file():
        text = graph.read_text(encoding="utf-8")
        if "class KnowledgeNode" not in text:
            findings.append(
                CompatibilityFinding(
                    "ARTIFACT_ONLY_GRAPH",
                    graph.relative_to(root).as_posix(),
                    "knowledge graph must support non-artifact nodes",
                )
            )

    profile = (
        root
        / "00-governance"
        / "framework"
        / "profiles"
        / "scnehaux-codex-default.yaml"
    )
    if not profile.is_file():
        findings.append(
            CompatibilityFinding(
                "MISSING_FRAMEWORK_PROFILE",
                profile.relative_to(root).as_posix(),
                "Scnehaux-specific defaults must live in a profile",
            )
        )

    return tuple(findings)
