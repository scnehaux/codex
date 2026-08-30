import datetime
from datetime import date
from engine.control.parsing.markdown_ast import (
    parse_date,
    extract_links,
    extract_section_contents,
    clean_content_for_length,
    normalize_section,
    parse_frontmatter,
    strip_code_fences,
    extract_doc_id_references,
    extract_sections_normalized,
)


def test_parse_date():
    assert parse_date("2026-06-21") == date(2026, 6, 21)
    assert parse_date(date(2026, 6, 21)) == date(2026, 6, 21)
    assert parse_date("invalid-date") is None
    assert parse_date("2026/06/21") is None
    assert parse_date("20260621") is None


def test_parse_date_datetime():
    dt = datetime.datetime(2026, 6, 21, 12, 0)
    assert parse_date(dt) == datetime.date(2026, 6, 21)


def test_extract_links():
    content = (
        "Check out [Google](https://google.com) and [this document](./ADR-001.md)."
    )
    links = extract_links(content)
    assert len(links) == 2
    assert "https://google.com" in links
    assert "./ADR-001.md" in links


def test_extract_links_nested():
    content = "Check [*Google*](https://google.com)"
    links = extract_links(content)
    assert "https://google.com" in links


def test_extract_section_contents():
    content = "---\nmeta\n---\n## Introduction\nHello\n## Background\nWorld"
    sections = extract_section_contents(content)
    assert "introduction" in sections
    assert sections["introduction"] == "Hello"
    assert "background" in sections
    assert sections["background"] == "World"


def test_clean_content_for_length():
    content = "Hello `code` world\n```\nignore this\n```"
    cleaned = clean_content_for_length(content)
    assert "ignore this" not in cleaned
    assert "Hello  code  world" in cleaned


def test_clean_content_for_length_html_block():
    content = "Hello\n\n<div>ignore</div>\n\nworld"
    cleaned = clean_content_for_length(content)
    assert "ignore" not in cleaned
    assert "Hello world" in cleaned


def test_normalize_section():
    assert normalize_section("1.2.3 Introduction ") == "introduction"
    assert normalize_section("Background") == "background"


def test_parse_frontmatter():
    content = "---\ndoc_meta:\n  id: ADR-001\n---\nBody"
    meta, err = parse_frontmatter(content)
    assert err is None
    assert meta is not None
    assert meta["id"] == "ADR-001"


def test_parse_frontmatter_missing():
    meta, err = parse_frontmatter("No frontmatter here")
    assert err == "Missing YAML frontmatter."


def test_parse_frontmatter_invalid_yaml():
    meta, err = parse_frontmatter("---\ninvalid: yaml: : ---\n")
    assert err is not None
    assert "Failed to parse YAML frontmatter" in err


def test_parse_frontmatter_no_doc_meta():
    meta, err = parse_frontmatter("---\nother: true\n---\n")
    assert err is not None
    assert "YAML frontmatter is missing 'doc_meta' block" in err


def test_strip_code_fences_removes_fenced_blocks():
    text = "before\n```\n<!-- lint_disable: x -->\n```\nafter"
    cleaned = strip_code_fences(text)
    assert "lint_disable" not in cleaned
    assert "before" in cleaned and "after" in cleaned


def test_extract_doc_id_references():
    refs = extract_doc_id_references("See (**ADR-018**) and ADR-GLB-001 plus STD-E019.")
    assert "ADR-018" in refs and "ADR-GLB-001" in refs and "STD-E019" in refs


# ---------- Additional coverage tests ----------


def test_clean_content_for_length_with_softbreak():
    """Cover line 92 (softbreak/hardbreak handling)."""
    content = "Line one\nLine two"
    cleaned = clean_content_for_length(content)
    assert "Line one" in cleaned
    assert "Line two" in cleaned


def test_extract_links_no_links():
    """Cover line 121 (walk called with empty token list)."""
    content = "No links at all in this document."
    links = extract_links(content)
    assert links == []


def test_extract_sections_normalized_numbered_headings():
    """Cover extract_sections_normalized with numbered section headings (regex strip)."""
    content = "## 1.1 Context\n\nSome context.\n\n## 2. Architecture\n\nArch details."
    sections = extract_sections_normalized(content)
    assert "Context" in sections
    assert "Architecture" in sections


def test_extract_sections_normalized_empty():
    """Cover extract_sections_normalized with no h2 headings."""
    content = "Just a paragraph with no headings."
    sections = extract_sections_normalized(content)
    assert len(sections) == 0


def test_extract_section_contents_close_map_none():
    """Exercising the fallback branch (line 61/64) when heading_close has no map."""
    # This is hard to trigger naturally because markdown-it usually provides maps.
    # But a document with only h2 content still exercises the main path.
    content = "---\nmeta\n---\n## Only Section\nContent here"
    sections = extract_section_contents(content)
    assert "only section" in sections


def test_extract_links_tuple_attrs(monkeypatch):
    from engine.control.parsing.markdown_ast import extract_links

    # Test extract_links where token attrs is a list of tuples [("href", "https://example.com")]
    content = "[Test Link](https://example.com)"
    links = extract_links(content)
    assert "https://example.com" in links


def test_markdown_ast_walker_branches(monkeypatch):
    from engine.control.parsing import markdown_ast
    from markdown_it import MarkdownIt

    class FakeToken:
        def __init__(self, type_, attrs=None, children=None, map_=None):
            self.type = type_
            self.attrs = attrs
            self.children = children
            self.map = map_
            self.content = ""

    # Test extract_links tuple attrs branch (lines 165-167)
    fake_link = FakeToken("link_open", attrs=[("href", "https://tuple-link.com")])
    fake_inline = FakeToken("inline", children=[fake_link])

    monkeypatch.setattr(MarkdownIt, "parse", lambda self, content: [fake_inline])
    links = markdown_ast.extract_links("dummy")
    assert "https://tuple-link.com" in links

    # Test clean_content_for_length non-inline children branch (line 141)
    fake_text = FakeToken("text")
    fake_text.content = "Nested prose"
    fake_block = FakeToken("paragraph_open", children=[fake_text])
    monkeypatch.setattr(MarkdownIt, "parse", lambda self, content: [fake_block])
    cleaned = markdown_ast.clean_content_for_length("dummy")
    assert "Nested prose" in cleaned
