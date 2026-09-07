import os
import re
from pathlib import Path

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TARGET_FILE = os.path.join(ROOT_DIR, "governance", "GDC-001-fitness-functions.md")
TRACKED_ROOTS = ("engine", "generators", "scripts", "tests")

COMMENTS = {
    "auditors": "# (External environment validators)",
    "config": "# (Engine configuration & environment variables)",
    "fs": "# (File system utilities & workspace traversal)",
    "parsing": "# (Data extraction from raw files)",
    "reporting": "# (CLI output formatting & CI/CD error logs)",
    "validators": "# (The core policy sandbox)",
    "domains": "# (Federated domain-specific triad scripts)",
    "global_rules.py": "# (Foundational Python rules for all documents)",
    "cli.py": "# (Fitness Function CLI Entrypoint)",
    "engine": "# (Product runtime)",
    "generators": "# (Dynamic docs and topography autobuilders)",
    "scripts": "# (Git hooks and manual CI/CD utilities)",
    "tests": "# (Product test estate)",
}


def live_paths() -> list[tuple[str, ...]]:
    paths: list[tuple[str, ...]] = []
    root = Path(ROOT_DIR)

    for tracked_root in TRACKED_ROOTS:
        base = root / tracked_root
        if not base.exists():
            continue

        for path in base.rglob("*"):
            if not path.is_file():
                continue

            relative = path.relative_to(root)
            parts = relative.parts

            if parts[-1] == "__init__.py":
                continue
            if any(
                part.startswith(".")
                or part in {"__pycache__", "scratch"}
                or part.endswith(".egg-info")
                for part in parts
            ):
                continue

            paths.append(tuple(parts))

    return sorted(
        set(paths),
        key=lambda parts: tuple(part.casefold() for part in parts),
    )


def build_path_tree(paths: list[tuple[str, ...]]) -> dict:
    tree = {}
    for parts in paths:
        node = tree
        for part in parts:
            node = node.setdefault(part, {})
    return tree


def render_tree(tree: dict, prefix: str = "") -> list[str]:
    lines = []
    items = sorted(tree.items(), key=lambda item: item[0].casefold())
    for idx, (item, children) in enumerate(items):
        is_last = idx == len(items) - 1
        connector = "└── " if is_last else "├── "
        is_dir = bool(children)
        comment = COMMENTS.get(item, "")
        base = f"{prefix}{connector}{item}/" if is_dir else f"{prefix}{connector}{item}"
        if comment:
            clean_len = len(
                base.replace("│", "").replace("├", "").replace("─", "").replace("└", "")
            )
            lines.append(f"│   {base}{' ' * max(1, 26 - clean_len)}{comment}")
        else:
            lines.append(f"│   {base}")
        if is_dir:
            lines.extend(
                render_tree(children, prefix + ("    " if is_last else "│   "))
            )
    return lines


def generate_markdown_from_paths(paths: list[tuple[str, ...]]) -> str:
    tree_lines = ["```text", "codex/"]
    tree_lines.extend(render_tree(build_path_tree(paths)))
    tree_lines.append("```")
    return "\n".join(tree_lines)


def generate_markdown() -> str:
    return generate_markdown_from_paths(live_paths())


def update_document():
    with open(TARGET_FILE, "r", encoding="utf-8") as handle:
        content = handle.read()
    new_content = re.sub(
        r"<!-- BEGIN_ENGINE_TOPOGRAPHY -->.*?<!-- END_ENGINE_TOPOGRAPHY -->",
        f"<!-- BEGIN_ENGINE_TOPOGRAPHY -->\n{generate_markdown()}\n<!-- END_ENGINE_TOPOGRAPHY -->",
        content,
        flags=re.DOTALL,
    )
    with open(TARGET_FILE, "w", encoding="utf-8") as handle:
        handle.write(new_content)
    print("[OK] Generated Engine Topography -> GDC-001-fitness-functions.md")


if __name__ == "__main__":
    update_document()
