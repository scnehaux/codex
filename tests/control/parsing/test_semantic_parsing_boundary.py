from tests.support.repository import REPOSITORY_ROOT
from pathlib import Path

ROOT = REPOSITORY_ROOT
PARSER = (
    ROOT / 'engine' / "control" / "parsing" / "markdown_ast.py"
)
WAIVER = (
    ROOT / "06-fitness-function" / "scripts" / "waiver-expiry-check.py"
)


def test_semantic_frontmatter_state_has_no_regex_parser():
    parser_source = PARSER.read_text(encoding="utf-8")
    waiver_source = WAIVER.read_text(encoding="utf-8")

    assert 're.search(r"^---' not in parser_source
    assert 're.sub(r"^---' not in parser_source
    assert "yaml.safe_load(match.group(1))" not in waiver_source
    assert "re.search(" not in waiver_source


def test_frontmatter_supports_yaml_literal_containing_delimiter():
    from engine.control.parsing.markdown_ast import parse_frontmatter

    content = (
        "---\n"
        "doc_meta:\n"
        "  id: SAD-001\n"
        "  note: |\n"
        "    ---\n"
        "    still yaml\n"
        "---\n"
        "# Body\n"
    )

    metadata, error = parse_frontmatter(content)

    assert error is None
    assert metadata["id"] == "SAD-001"
    assert metadata["note"] == "---\nstill yaml\n"


def test_frontmatter_supports_bom_and_crlf():
    from engine.control.parsing.markdown_ast import parse_frontmatter

    content = (
        "\ufeff---\r\n"
        "doc_meta:\r\n"
        "  id: PAD-001\r\n"
        "---\r\n"
        "# Body\r\n"
    )

    metadata, error = parse_frontmatter(content)

    assert error is None
    assert metadata == {"id": "PAD-001"}


def test_frontmatter_missing_unclosed_and_invalid_shapes():
    from engine.control.parsing.markdown_ast import parse_frontmatter

    assert parse_frontmatter("# Body\n") == (
        None,
        "Missing YAML frontmatter.",
    )
    assert parse_frontmatter("---\ndoc_meta:\n  id: SAD-001\n") == (
        None,
        "Missing YAML frontmatter.",
    )

    metadata, error = parse_frontmatter("---\n[]\n---\n")
    assert metadata is None
    assert "missing 'doc_meta'" in error

    metadata, error = parse_frontmatter("---\ndoc_meta: {}\n---\n")
    assert metadata is None
    assert "missing 'doc_meta'" in error

    metadata, error = parse_frontmatter("---\ndoc_meta: [broken\n---\n")
    assert metadata is None
    assert error.startswith("Failed to parse YAML frontmatter:")
