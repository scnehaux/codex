import re
import yaml
import datetime
from typing import Optional, Union, Any
from markdown_it import MarkdownIt
from engine.control.governance.temporal import parse_canonical_date


def _split_frontmatter(content: str) -> tuple[str | None, str]:
    """Split leading YAML frontmatter without regex inference."""
    normalized = content[1:] if content.startswith("\ufeff") else content
    lines = normalized.splitlines(keepends=True)

    if not lines or lines[0].rstrip("\r\n") != "---":
        return None, normalized

    for index, line in enumerate(lines[1:], start=1):
        if line.rstrip("\r\n") == "---":
            return "".join(lines[1:index]), "".join(lines[index + 1 :])

    return None, normalized


def parse_frontmatter(content: str) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    """
    Parse a leading YAML frontmatter block using deterministic delimiters.

    Structured frontmatter state is never inferred with regex.
    """
    frontmatter_text, _ = _split_frontmatter(content)
    if frontmatter_text is None:
        normalized = content[1:] if content.startswith("\ufeff") else content
        lines = normalized.splitlines(keepends=True)

        if lines and lines[0].rstrip("\r\n") == "---":
            candidate = "".join(lines[1:])
            try:
                yaml.safe_load(candidate)
            except Exception as exc:
                return None, f"Failed to parse YAML frontmatter: {exc}"

        return None, "Missing YAML frontmatter."

    try:
        frontmatter_data = yaml.safe_load(frontmatter_text)
    except Exception as exc:
        return None, f"Failed to parse YAML frontmatter: {exc}"

    if not isinstance(frontmatter_data, dict):
        return None, "YAML frontmatter is missing 'doc_meta' block, or it is empty."

    doc_meta = frontmatter_data.get("doc_meta")
    if not isinstance(doc_meta, dict) or not doc_meta:
        return None, "YAML frontmatter is missing 'doc_meta' block, or it is empty."

    return doc_meta, None


def parse_date(
    date_val: Union[datetime.datetime, datetime.date, str, None],
) -> Optional[datetime.date]:
    """Parse a governance date using the canonical temporal parser."""
    return parse_canonical_date(date_val)


def extract_section_contents(content: str) -> dict[str, str]:
    """
    Extract all H2 (##) level sections from a markdown document.
    Returns a dictionary mapping the lowercased, raw heading text to its content body.
    Note: The heading text retains numbering. Use extract_sections_normalized for strict matching.
    """
    # Strip YAML frontmatter to prevent Setext heading misinterpretation
    _, content_no_fm = _split_frontmatter(content)
    md = MarkdownIt()
    tokens = md.parse(content_no_fm)

    sections = {}
    current_section = None
    lines = content_no_fm.split("\n")
    last_section_start = 0

    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.type == "heading_open" and token.tag == "h2":
            # Save previous section
            if current_section is not None:
                end_line = token.map[0] if token.map else len(lines)
                sections[current_section] = "\n".join(
                    lines[last_section_start:end_line]
                ).strip()

            # Find heading title
            i += 1
            if i < len(tokens) and tokens[i].type == "inline":
                current_section = tokens[i].content.strip().lower()

            # Move past heading_close
            i += 1
            if i < len(tokens) and tokens[i].type == "heading_close":
                heading_close_token = tokens[i]
                close_map = heading_close_token.map
                if close_map is not None:
                    last_section_start = close_map[1]
                else:
                    # fallback to previous token map
                    prev_map = tokens[i - 2].map
                    if prev_map is not None:
                        last_section_start = prev_map[1]
        i += 1

    if current_section is not None:
        sections[current_section] = "\n".join(lines[last_section_start:]).strip()

    return sections


def clean_content_for_length(content: str) -> str:
    """
    Remove all semantic markdown structures (YAML frontmatter, code blocks, HTML blocks)
    and collapse the remaining text nodes into a single flat string.
    Used to accurately count the substantive prose length of a document or section.
    """
    _, content_no_fm = _split_frontmatter(content)
    md = MarkdownIt()
    tokens = md.parse(content_no_fm)
    text = []

    def walk(tokens_list: list[Any] | None) -> None:
        if not tokens_list:
            return
        for t in tokens_list:
            if t.type == "text" or t.type == "code_inline":
                text.append(t.content)
            elif t.type == "softbreak" or t.type == "hardbreak":
                text.append(" ")
            if getattr(t, "children", None) is not None:
                walk(t.children)

    for t in tokens:
        # Ignore code blocks for semantic checks
        if t.type in ("fence", "code_block", "html_block"):
            continue
        if t.type == "inline":
            if t.children is not None:
                walk(t.children)
        else:
            if getattr(t, "children", None) is not None:
                walk(t.children)

    return " ".join(text).strip()


def extract_links(content: str) -> list[str]:
    """
    Traverse the Markdown AST to find and extract all hyperlink targets (href values).
    Used to validate internal repository links and prevent link rot.
    """
    _, content_no_fm = _split_frontmatter(content)
    md = MarkdownIt()
    tokens = md.parse(content_no_fm)
    links = []

    def walk(tokens_list: list[Any] | None) -> None:
        if not tokens_list:
            return
        for t in tokens_list:
            if t.type == "link_open" and t.attrs:
                if isinstance(t.attrs, dict):
                    if "href" in t.attrs:
                        links.append(t.attrs["href"])
                else:
                    for attr in t.attrs:
                        if attr[0] == "href":
                            links.append(attr[1])
            if getattr(t, "children", None) is not None:
                walk(t.children)

    for t in tokens:
        if t.type == "inline":
            if t.children is not None:
                walk(t.children)

    return links


def normalize_section(name: str) -> str:
    """Normalize section name for comparison by stripping numbering."""
    return re.sub(r"^\d+(\.\d+)*\.?\s*", "", name).strip().lower()


def extract_sections_normalized(content: str) -> dict[str, str]:
    """
    Return {section_title: section_content} for H2 sections, with any leading
    numbering stripped and the ORIGINAL case preserved
    (e.g. '## 1. Context & Scope' -> key 'Context & Scope').

    This is the canonical source of section identity for JSON-Schema validation:
    schemas declare required/recommended sections by their Title-Case, unnumbered
    name, and `content_rules` run `pattern` checks against the section's text.
    (`extract_section_contents` lowercases the key and keeps the numeric prefix, so
    it can neither satisfy a `required` match nor feed content patterns.)
    """
    _, content_no_fm = _split_frontmatter(content)
    md = MarkdownIt()
    tokens = md.parse(content_no_fm)

    sections: dict[str, str] = {}
    current_section = None
    lines = content_no_fm.split("\n")
    last_section_start = 0

    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.type == "heading_open" and token.tag == "h2":
            if current_section is not None:
                end_line = token.map[0] if token.map else len(lines)
                sections[current_section] = "\n".join(
                    lines[last_section_start:end_line]
                ).strip()

            i += 1
            if i < len(tokens) and tokens[i].type == "inline":
                raw = tokens[i].content.strip()
                current_section = re.sub(r"^\d+(\.\d+)*\.?\s*", "", raw).strip()

            i += 1
            if i < len(tokens) and tokens[i].type == "heading_close":
                close_map = tokens[i].map
                if close_map is not None:
                    last_section_start = close_map[1]
                else:
                    prev_map = tokens[i - 2].map
                    if prev_map is not None:
                        last_section_start = prev_map[1]
        i += 1

    if current_section is not None:
        sections[current_section] = "\n".join(lines[last_section_start:]).strip()

    return sections


def strip_code_fences(content: str) -> str:
    """
    Remove fenced and indented code blocks safely using AST parsing.
    This replaces the blocks with an equivalent number of newlines to preserve line numbering,
    avoiding regex false positives with nested backticks, indented blocks, or unclosed fences.

    Args:
        content (str): The raw Markdown text to be processed.

    Returns:
        str: The Markdown text with all code blocks replaced by blank lines.
    """
    md = MarkdownIt()
    tokens = md.parse(content)

    lines = content.split("\n")
    for t in tokens:
        # "fence"      = code block using backticks (```) or tildes (~~~)
        # "code_block" = code block using 4-space indentation
        if t.type in ("fence", "code_block"):
            if t.map:
                start_line, end_line = t.map
                # Blank out the lines to preserve line numbers underneath
                for i in range(start_line, end_line):
                    if i < len(lines):
                        lines[i] = ""

    return "\n".join(lines)


DOC_ID_REFERENCE_PATTERN = re.compile(
    r"\b(?:GDC|EAD|STD|PAD|SAD|ADR|TDD)-[A-Z0-9]+(?:-[A-Z0-9]+)*\b"
)


def extract_doc_id_references(content: str) -> list[str]:
    """
    Extract architecture document IDs referenced in prose (e.g. '(**ADR-018**)').
    Code fences and frontmatter are excluded via clean_content_for_length.
    Returns a de-duplicated, order-preserving list.
    """
    prose = clean_content_for_length(content)
    return list(dict.fromkeys(DOC_ID_REFERENCE_PATTERN.findall(prose)))
