import os
import ast
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FITNESS_DIR = os.path.dirname(SCRIPT_DIR)
ROOT_DIR = os.path.dirname(FITNESS_DIR)
CONTROL_DIR = os.path.join(ROOT_DIR, "engine", "control")
INTERFACES_DIR = os.path.join(ROOT_DIR, "engine", "interfaces")
ENGINE_INDEX = os.path.join(CONTROL_DIR, "INDEX.md")
GENERATORS_DIR = os.path.join(FITNESS_DIR, "generators")
SCRIPTS_DIR = os.path.join(FITNESS_DIR, "scripts")


def extract_functions(filepath):
    """
    Parse a Python file using the `ast` module to extract all function and class method definitions.
    Captures the docstring and line number.
    """

    def format_docstring(doc):
        # Convert leading spaces to &nbsp; to prevent HTML from collapsing indentation in the table
        lines = []
        for line in doc.split("\n"):
            stripped = line.lstrip(" ")
            indent = len(line) - len(stripped)
            lines.append("&nbsp;" * indent + stripped)
        return "<br>".join(lines)

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    tree = ast.parse(content)
    functions = []

    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            if not node.name.startswith("__"):
                docstring = ast.get_docstring(node)
                if docstring:
                    desc = format_docstring(docstring)
                else:
                    desc = "*(No docstring provided)*"

                functions.append(
                    {"name": node.name, "description": desc, "line": node.lineno}
                )
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    if not item.name.startswith("__"):
                        docstring = ast.get_docstring(item)
                        if docstring:
                            desc = format_docstring(docstring)
                        else:
                            desc = "*(No docstring provided)*"
                        functions.append(
                            {
                                "name": f"{node.name}.{item.name}",
                                "description": desc,
                                "line": item.lineno,
                            }
                        )
    return sorted(functions, key=lambda x: x["line"])


def generate_markdown_table(all_funcs):
    """
    Format the extracted function metadata into a structured Markdown table.
    Groups functions by their parent Python module (file path) for clarity.
    """
    if not all_funcs:
        return "*No validation functions documented yet.*"

    lines = ["## List of functions\n"]

    # Sort modules alphabetically
    for module in sorted(all_funcs.keys()):
        funcs = all_funcs[module]
        if not funcs:
            continue

        lines.append(f"### `{module}`\n")
        lines.append("| Function | Description |")
        lines.append("| :--- | :--- |")

        for f in funcs:
            name = f["name"]
            desc = f["description"]
            desc = desc.replace("|", "\\|")
            lines.append(f"| **{name}** | {desc} |")
        lines.append("")

    return "\n".join(lines).strip()


def inject_to_markdown(md_path, table_str):
    """
    Inject the generated Markdown table into the target file, replacing whatever content
    exists between the `AUTO-GENERATED-FUNCTIONS` start and end marker tags.
    """
    if not os.path.exists(md_path):
        print(f"File not found: {md_path}")
        return False

    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r"(<!-- AUTO-GENERATED-FUNCTIONS:START -->)(.*?)(<!-- AUTO-GENERATED-FUNCTIONS:END -->)"

    if not re.search(pattern, content, flags=re.DOTALL):
        print(f"[SKIP] {md_path} -> No placeholder found")
        return False

    def replacer(match):
        return f"{match.group(1)}\n\n{table_str}\n\n{match.group(3)}"

    new_content = re.sub(pattern, replacer, content, flags=re.DOTALL)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    return True


def _documentation_relative_path(path, scan_dir):
    """Return stable repo-relative paths, with a portable external-scan fallback."""
    path_abs = os.path.abspath(path)
    root_abs = os.path.abspath(ROOT_DIR)
    scan_abs = os.path.abspath(scan_dir)
    try:
        if os.path.commonpath((path_abs, root_abs)) == root_abs:
            return os.path.relpath(path_abs, root_abs).replace("\\", "/")
    except ValueError:
        pass
    return os.path.relpath(path_abs, scan_abs).replace("\\", "/")

def update_directory_index(scan_dir):
    """
    Crawl a specific sub-ecosystem directory (e.g. `engine` or `generators`), extract all
    Python function documentation within it, and inject the results into its local `INDEX.md`.
    """
    index_md = os.path.join(scan_dir, "INDEX.md")
    if not os.path.exists(index_md):
        return

    all_funcs = {}

    for root, dirs, files in os.walk(scan_dir):
        # Allow walking into tests for the tests directory itself, but exclude caches
        dirs[:] = [
            d
            for d in dirs
            if d not in ["__pycache__", ".pytest_cache"] and not d.startswith(".")
        ]

        for file in files:
            if file.endswith(".py") and not file.startswith("__"):
                path = os.path.join(root, file)
                rel_path = _documentation_relative_path(path, scan_dir)

                funcs = extract_functions(path)
                if funcs:
                    all_funcs[rel_path] = funcs

    table_str = generate_markdown_table(all_funcs)

    if inject_to_markdown(index_md, table_str):
        print(f"[OK] Injected python function documentation into {index_md}")


def generate_cli_flowchart():
    """
    Scan engine/cli.py for special inline comments starting with `# @flow:`
    and compile them into a Mermaid flowchart injected into engine/INDEX.md.
    """
    cli_path = os.path.join(INTERFACES_DIR, "cli.py")
    index_md = ENGINE_INDEX

    if not os.path.exists(cli_path) or not os.path.exists(index_md):
        return

    with open(cli_path, "r", encoding="utf-8") as f:
        content = f.read()

    flow_lines = []
    for line in content.split("\n"):
        match = re.search(r"#\s*@flow:\s*(.*)", line)
        if match:
            flow_lines.append(f"    {match.group(1).strip()}")

    if not flow_lines:
        return

    theme_config = "%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#e6e6fa', 'primaryTextColor': '#333', 'primaryBorderColor': '#7a67ee', 'lineColor': '#888', 'edgeLabelBackground': '#f4f4f4'}}}%%"
    table_str = (
        f"```mermaid\n{theme_config}\ngraph TD\n" + "\n".join(flow_lines) + "\n```"
    )

    with open(index_md, "r", encoding="utf-8") as f:
        md_content = f.read()

    pattern = r"(<!-- AUTO-GENERATED-CLI-FLOW:START -->)(.*?)(<!-- AUTO-GENERATED-CLI-FLOW:END -->)"
    if not re.search(pattern, md_content, flags=re.DOTALL):
        print(f"[SKIP] CLI flowchart -> No placeholder found in {index_md}")
        return

    def replacer(m):
        return f"{m.group(1)}\n\n{table_str}\n\n{m.group(3)}"

    new_content = re.sub(pattern, replacer, md_content, flags=re.DOTALL)

    with open(index_md, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"[OK] Injected CLI flowchart into {index_md}")


def generate_lint_flowchart():
    """
    Scan engine/cli.py for special inline comments starting with `# @flow-lint:`
    and compile them into a Mermaid flowchart injected into engine/INDEX.md.
    """
    cli_path = os.path.join(INTERFACES_DIR, "cli.py")
    index_md = ENGINE_INDEX

    if not os.path.exists(cli_path) or not os.path.exists(index_md):
        return

    with open(cli_path, "r", encoding="utf-8") as f:
        content = f.read()

    flow_lines = []
    for line in content.split("\n"):
        match = re.search(r"#\s*@flow-lint:\s*(.*)", line)
        if match:
            flow_lines.append(f"    {match.group(1).strip()}")

    if not flow_lines:
        return

    theme_config = "%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#e6e6fa', 'primaryTextColor': '#333', 'primaryBorderColor': '#7a67ee', 'lineColor': '#888', 'edgeLabelBackground': '#f4f4f4'}}}%%"
    table_str = (
        f"```mermaid\n{theme_config}\ngraph TD\n" + "\n".join(flow_lines) + "\n```"
    )

    with open(index_md, "r", encoding="utf-8") as f:
        md_content = f.read()

    pattern = r"(<!-- AUTO-GENERATED-LINT-FLOW:START -->)(.*?)(<!-- AUTO-GENERATED-LINT-FLOW:END -->)"
    if not re.search(pattern, md_content, flags=re.DOTALL):
        print(f"[SKIP] Lint flowchart -> No placeholder found in {index_md}")
        return

    def replacer(m):
        return f"{m.group(1)}\n\n{table_str}\n\n{m.group(3)}"

    new_content = re.sub(pattern, replacer, md_content, flags=re.DOTALL)

    with open(index_md, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"[OK] Injected Lint flowchart into {index_md}")


def generate_validator_flowchart():
    """
    Scan engine/validators/base.py for special inline comments starting with `# @flow-validator:`
    and compile them into a Mermaid flowchart injected into engine/INDEX.md.
    """
    validators_dir = os.path.join(CONTROL_DIR, "validators")
    index_md = ENGINE_INDEX

    if not os.path.exists(validators_dir) or not os.path.exists(index_md):
        return

    flow_lines = []
    files_to_scan = ["base.py", "global_rules.py"]
    for file_name in files_to_scan:
        file_path = os.path.join(validators_dir, file_name)
        if not os.path.exists(file_path):
            continue
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        for line in content.split("\n"):
            match = re.search(r"#\s*@flow-validator:\s*(.*)", line)
            if match:
                flow_lines.append(f"    {match.group(1).strip()}")

    if not flow_lines:
        return

    # Style the subgraphs with a cream background
    flow_lines.append(
        "    style SchemaPhase fill:#fffdd0,stroke:#d2b48c,stroke-width:2px,color:#333,stroke-dasharray: 5 5"
    )
    flow_lines.append(
        "    style GlobalRulesPhase fill:#fffdd0,stroke:#d2b48c,stroke-width:2px,color:#333,stroke-dasharray: 5 5"
    )

    theme_config = "%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#e6e6fa', 'primaryTextColor': '#333', 'primaryBorderColor': '#7a67ee', 'lineColor': '#888', 'edgeLabelBackground': '#f4f4f4'}}}%%"
    table_str = (
        f"```mermaid\n{theme_config}\ngraph TD\n" + "\n".join(flow_lines) + "\n```"
    )

    with open(index_md, "r", encoding="utf-8") as f:
        md_content = f.read()

    pattern = r"(<!-- AUTO-GENERATED-VALIDATOR-FLOW:START -->)(.*?)(<!-- AUTO-GENERATED-VALIDATOR-FLOW:END -->)"
    if not re.search(pattern, md_content, flags=re.DOTALL):
        print(f"[SKIP] Validator flowchart -> No placeholder found in {index_md}")
        return

    def replacer(m):
        return f"{m.group(1)}\n\n{table_str}\n\n{m.group(3)}"

    new_content = re.sub(pattern, replacer, md_content, flags=re.DOTALL)

    with open(index_md, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"[OK] Injected Validator flowchart into {index_md}")


def generate_domain_flowcharts():
    """
    Scan engine/validators/domains/*_validator.py for special inline comments starting with `# @flow-domain:`
    and compile them into isolated Mermaid flowcharts injected into engine/INDEX.md.
    """
    domains_dir = os.path.join(CONTROL_DIR, "validators", "domains")
    index_md = ENGINE_INDEX

    if not os.path.exists(domains_dir) or not os.path.exists(index_md):
        return

    domain_sections = []

    # Custom sort order defined by architecture hierarchy
    order = ["gdc", "ead", "pad", "sad", "tdd", "adr", "std"]

    def get_order(filename):
        prefix = filename.split("_")[0].lower()
        return order.index(prefix) if prefix in order else 999

    # Sort files according to the custom hierarchy
    files = sorted(
        [f for f in os.listdir(domains_dir) if f.endswith("_validator.py")],
        key=get_order,
    )

    for file_name in files:
        file_path = os.path.join(domains_dir, file_name)
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        flow_lines = []
        for line in content.split("\n"):
            match = re.search(r"#\s*@flow-domain:\s*(.*)", line)
            if match:
                flow_lines.append(f"    {match.group(1).strip()}")

        if flow_lines:
            doc_type = file_name.split("_")[0].upper()
            section = f"### {doc_type} Validator (`{file_name}`)\n"
            theme_config = "%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#e6e6fa', 'primaryTextColor': '#333', 'primaryBorderColor': '#7a67ee', 'lineColor': '#888', 'edgeLabelBackground': '#f4f4f4'}}}%%"
            section += (
                f"```mermaid\n{theme_config}\ngraph LR\n"
                + "\n".join(flow_lines)
                + "\n```\n"
            )
            domain_sections.append(section)

    if not domain_sections:
        return

    full_str = "\n".join(domain_sections)

    with open(index_md, "r", encoding="utf-8") as f:
        md_content = f.read()

    pattern = r"(<!-- AUTO-GENERATED-DOMAIN-FLOWS:START -->)(.*?)(<!-- AUTO-GENERATED-DOMAIN-FLOWS:END -->)"
    if not re.search(pattern, md_content, flags=re.DOTALL):
        print(f"[SKIP] Domain flowcharts -> No placeholder found in {index_md}")
        return

    def replacer(m):
        return f"{m.group(1)}\n\n{full_str}\n{m.group(3)}"

    new_content = re.sub(pattern, replacer, md_content, flags=re.DOTALL)

    with open(index_md, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"[OK] Injected Domain flowcharts into {index_md}")


def main():
    """
    Main execution flow. Iterates through the core sub-ecosystems (engine, generators,
    scripts, tests) and updates their respective INDEX.md files.
    """
    generate_cli_flowchart()
    generate_lint_flowchart()
    generate_validator_flowchart()
    generate_domain_flowcharts()

    dirs_to_update = [
        CONTROL_DIR,
        GENERATORS_DIR,
        SCRIPTS_DIR,
        os.path.join(FITNESS_DIR, "tests"),
    ]

    for d in dirs_to_update:
        update_directory_index(d)


if __name__ == "__main__":
    main()
