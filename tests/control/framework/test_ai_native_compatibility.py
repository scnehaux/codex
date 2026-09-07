from tests.support.repository import REPOSITORY_ROOT
from pathlib import Path

from engine.control.framework.compatibility import (
    audit_ai_native_compatibility,
)


ROOT = REPOSITORY_ROOT


def test_current_repository_ai_native_compatibility_has_no_known_gap():
    findings = audit_ai_native_compatibility(ROOT)
    assert findings == ()


# PHASE-6.6A-COMPATIBILITY-BEHAVIORAL-COVERAGE

import textwrap

from engine.control.framework.compatibility import CompatibilityFinding


def _write(root: Path, relative: str, content: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        textwrap.dedent(content).lstrip(),
        encoding="utf-8",
    )
    return path


def test_compatibility_auditor_detects_semantic_frontmatter_regex(tmp_path):
    _write(
        tmp_path,
        "engine/control/parsing/markdown_ast.py",
        'import re\n\ndef parse(content):\n    return re.search(r"^---", content)\n',
    )

    findings = audit_ai_native_compatibility(tmp_path)

    assert any(finding.code == "SEMANTIC_FRONTMATTER_REGEX" for finding in findings)


def test_compatibility_auditor_detects_generator_parser_import(tmp_path):
    _write(
        tmp_path,
        "generators/example.py",
        "from engine.control.parsing.markdown_ast import parse_frontmatter\n",
    )

    findings = audit_ai_native_compatibility(tmp_path)

    assert any(finding.code == "GENERATOR_INDEPENDENT_PARSING" for finding in findings)


def test_compatibility_auditor_detects_unparseable_generator(tmp_path):
    _write(
        tmp_path,
        "generators/broken.py",
        "def broken(\n",
    )

    findings = audit_ai_native_compatibility(tmp_path)

    assert any(finding.code == "GENERATOR_PARSE_ERROR" for finding in findings)


def test_compatibility_auditor_detects_artifact_only_graph(tmp_path):
    _write(
        tmp_path,
        "engine/core/knowledge/graph.py",
        "class ArchitectureNode:\n    pass\n",
    )

    findings = audit_ai_native_compatibility(tmp_path)

    assert any(finding.code == "ARTIFACT_ONLY_GRAPH" for finding in findings)


def test_compatibility_auditor_detects_missing_framework_profile(tmp_path):
    findings = audit_ai_native_compatibility(tmp_path)

    assert any(finding.code == "MISSING_FRAMEWORK_PROFILE" for finding in findings)


def test_compatibility_finding_contract():
    finding = CompatibilityFinding(
        "CODE",
        "path.py",
        "detail",
    )

    assert finding.code == "CODE"
    assert finding.path == "path.py"
    assert finding.detail == "detail"


def test_compatibility_auditor_accepts_clean_minimal_fixture(tmp_path):
    _write(
        tmp_path,
        "engine/control/parsing/markdown_ast.py",
        "def parse_frontmatter(content):\n    return content\n",
    )
    _write(
        tmp_path,
        "engine/core/knowledge/graph.py",
        "class KnowledgeNode:\n    pass\n",
    )
    _write(
        tmp_path,
        "governance/framework/profiles/scnehaux-codex-default.yaml",
        "profile_version: 1\n",
    )

    assert audit_ai_native_compatibility(tmp_path) == ()
