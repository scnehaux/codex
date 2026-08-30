from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
FITNESS = ROOT / "06-fitness-function"
GEN = FITNESS / "generators"


def _load(filename: str, name: str):
    path = GEN / filename
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_topography_live_paths_filters_and_normalizes(tmp_path, monkeypatch):
    module = _load("generate_engine_topography.py", "topography_filters")
    monkeypatch.setattr(module, "ROOT_DIR", str(tmp_path))

    (tmp_path / "engine" / "control").mkdir(parents=True)
    (tmp_path / "engine" / "interfaces").mkdir(parents=True)
    (tmp_path / "engine" / "control" / "base.py").write_text("", encoding="utf-8")
    (tmp_path / "engine" / "control" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "engine" / "interfaces" / "cli.py").write_text("", encoding="utf-8")
    (tmp_path / "engine" / "control" / "__pycache__").mkdir()
    (tmp_path / "engine" / "control" / "__pycache__" / "x.py").write_text("", encoding="utf-8")
    (tmp_path / "06-fitness-function" / "scratch").mkdir(parents=True)
    (tmp_path / "06-fitness-function" / "scratch" / "tmp.py").write_text("", encoding="utf-8")
    (tmp_path / "06-fitness-function" / "pkg.egg-info").mkdir()
    (tmp_path / "06-fitness-function" / "pkg.egg-info" / "PKG-INFO").write_text("", encoding="utf-8")

    assert module.live_paths() == [
        ("engine", "control", "base.py"),
        ("engine", "interfaces", "cli.py"),
    ]


def test_topography_generate_and_update_document(tmp_path, monkeypatch):
    module = _load("generate_engine_topography.py", "topography_update")

    monkeypatch.setattr(module, "live_paths", lambda: [("engine", "interfaces", "cli.py"), ("06-fitness-function", "generators", "x.py")])
    rendered = module.generate_markdown()
    assert "06-fitness-function/" in rendered
    assert "cli.py" in rendered

    target = tmp_path / "GDC-001.md"
    target.write_text(
        "before\n"
        "<!-- BEGIN_ENGINE_TOPOGRAPHY -->\nold\n"
        "<!-- END_ENGINE_TOPOGRAPHY -->\n"
        "after\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "TARGET_FILE", str(target))
    monkeypatch.setattr(module, "generate_markdown", lambda: "NEW-TREE")

    module.update_document()

    content = target.read_text(encoding="utf-8")
    assert "NEW-TREE" in content
    assert "old" not in content


def test_functions_extract_and_markdown_table(tmp_path):
    module = _load("generate_functions_doc.py", "functions_extract")

    source = tmp_path / "sample.py"
    source.write_text(
        'def documented():\n'
        '    """Line one\n'
        '      base line\n'
        '        indented | value"""\n'
        '    return 1\n\n'
        'def plain():\n'
        '    return 2\n\n'
        'def __hidden__():\n'
        '    return 3\n\n'
        'class Service:\n'
        '    def method(self):\n'
        '        """Method docs"""\n'
        '        return 4\n\n'
        '    def plain_method(self):\n'
        '        return 5\n\n'
        '    def __private__(self):\n'
        '        return 6\n',
        encoding="utf-8",
    )

    funcs = module.extract_functions(str(source))
    names = [item["name"] for item in funcs]

    assert names == [
        "documented",
        "plain",
        "Service.method",
        "Service.plain_method",
    ]
    assert "&nbsp;" in funcs[0]["description"]
    assert module.generate_markdown_table({}) == (
        "*No validation functions documented yet.*"
    )

    table = module.generate_markdown_table({"z.py": [], "a.py": funcs})
    assert "### `a.py`" in table
    assert "documented" in table
    assert r"\|" in table
    assert "No docstring provided" in table


def test_functions_inject_markdown_contracts(tmp_path):
    module = _load("generate_functions_doc.py", "functions_inject")

    missing = tmp_path / "missing.md"
    assert module.inject_to_markdown(str(missing), "TABLE") is False

    no_marker = tmp_path / "no-marker.md"
    no_marker.write_text("plain", encoding="utf-8")
    assert module.inject_to_markdown(str(no_marker), "TABLE") is False

    target = tmp_path / "INDEX.md"
    target.write_text(
        "x\n"
        "<!-- AUTO-GENERATED-FUNCTIONS:START -->\nold\n"
        "<!-- AUTO-GENERATED-FUNCTIONS:END -->\n",
        encoding="utf-8",
    )
    assert module.inject_to_markdown(str(target), "TABLE") is True
    assert "TABLE" in target.read_text(encoding="utf-8")


def test_functions_update_directory_index(tmp_path, monkeypatch):
    module = _load("generate_functions_doc.py", "functions_directory")

    scan = tmp_path / "engine"
    scan.mkdir()
    monkeypatch.setattr(module, "FITNESS_DIR", str(tmp_path))

    module.update_directory_index(str(scan))

    index = scan / "INDEX.md"
    index.write_text(
        "<!-- AUTO-GENERATED-FUNCTIONS:START -->\n"
        "<!-- AUTO-GENERATED-FUNCTIONS:END -->\n",
        encoding="utf-8",
    )
    (scan / "sample.py").write_text(
        'def hello():\n    """Hello docs"""\n    return 1\n',
        encoding="utf-8",
    )
    (scan / "__init__.py").write_text(
        "def ignored():\n    return 1\n",
        encoding="utf-8",
    )
    cache = scan / "__pycache__"
    cache.mkdir()
    (cache / "cached.py").write_text(
        "def cached():\n    return 1\n",
        encoding="utf-8",
    )

    module.update_directory_index(str(scan))

    content = index.read_text(encoding="utf-8")
    assert "sample.py" in content
    assert "hello" in content
    assert "cached.py" not in content


@pytest.mark.parametrize(
    ("function_name", "marker", "flow_tag"),
    (
        ("generate_cli_flowchart", "AUTO-GENERATED-CLI-FLOW", "@flow:"),
        ("generate_lint_flowchart", "AUTO-GENERATED-LINT-FLOW", "@flow-lint:"),
    ),
)
def test_functions_cli_and_lint_flowchart_contracts(
    tmp_path,
    monkeypatch,
    function_name,
    marker,
    flow_tag,
):
    module = _load("generate_functions_doc.py", f"functions_{function_name}")
    interfaces = tmp_path / "engine" / "interfaces"
    control = tmp_path / "engine" / "control"
    interfaces.mkdir(parents=True)
    control.mkdir(parents=True)
    monkeypatch.setattr(module, "INTERFACES_DIR", str(interfaces))
    monkeypatch.setattr(module, "ENGINE_INDEX", str(control / "INDEX.md"))

    function = getattr(module, function_name)
    function()

    cli = interfaces / "cli.py"
    index = control / "INDEX.md"
    cli.write_text("print('no flow')\n", encoding="utf-8")
    index.write_text("plain\n", encoding="utf-8")
    function()

    cli.write_text(f"# {flow_tag} A --> B\n", encoding="utf-8")
    function()

    index.write_text(
        f"<!-- {marker}:START -->\nold\n<!-- {marker}:END -->\n",
        encoding="utf-8",
    )
    function()

    content = index.read_text(encoding="utf-8")
    assert "```mermaid" in content
    assert "A --> B" in content


def test_functions_validator_flowchart_contracts(tmp_path, monkeypatch):
    module = _load("generate_functions_doc.py", "functions_validator_flow")
    control = tmp_path / "engine" / "control"
    control.mkdir(parents=True)
    monkeypatch.setattr(module, "CONTROL_DIR", str(control))
    monkeypatch.setattr(module, "ENGINE_INDEX", str(control / "INDEX.md"))

    module.generate_validator_flowchart()

    validators = control / "validators"
    validators.mkdir()
    index = control / "INDEX.md"
    index.write_text("plain\n", encoding="utf-8")
    (validators / "base.py").write_text("print('no flow')\n", encoding="utf-8")
    module.generate_validator_flowchart()

    (validators / "base.py").write_text(
        "# @flow-validator: SchemaPhase --> GlobalRulesPhase\n",
        encoding="utf-8",
    )
    module.generate_validator_flowchart()

    index.write_text(
        "<!-- AUTO-GENERATED-VALIDATOR-FLOW:START -->\nold\n"
        "<!-- AUTO-GENERATED-VALIDATOR-FLOW:END -->\n",
        encoding="utf-8",
    )
    module.generate_validator_flowchart()

    content = index.read_text(encoding="utf-8")
    assert "SchemaPhase --> GlobalRulesPhase" in content
    assert "style SchemaPhase" in content
    assert "style GlobalRulesPhase" in content


def test_functions_domain_flowchart_contracts(tmp_path, monkeypatch):
    module = _load("generate_functions_doc.py", "functions_domain_flow")
    control = tmp_path / "engine" / "control"
    control.mkdir(parents=True)
    monkeypatch.setattr(module, "CONTROL_DIR", str(control))
    monkeypatch.setattr(module, "ENGINE_INDEX", str(control / "INDEX.md"))

    module.generate_domain_flowcharts()

    domains = control / "validators" / "domains"
    domains.mkdir(parents=True)
    index = control / "INDEX.md"
    index.write_text("plain\n", encoding="utf-8")

    (domains / "gdc_validator.py").write_text("print('no flow')\n", encoding="utf-8")
    module.generate_domain_flowcharts()

    (domains / "gdc_validator.py").write_text(
        "# @flow-domain: GDC --> BASE\n",
        encoding="utf-8",
    )
    (domains / "zzz_validator.py").write_text(
        "# @flow-domain: ZZZ --> BASE\n",
        encoding="utf-8",
    )
    module.generate_domain_flowcharts()

    index.write_text(
        "<!-- AUTO-GENERATED-DOMAIN-FLOWS:START -->\nold\n"
        "<!-- AUTO-GENERATED-DOMAIN-FLOWS:END -->\n",
        encoding="utf-8",
    )
    module.generate_domain_flowcharts()

    content = index.read_text(encoding="utf-8")
    assert "### GDC Validator" in content
    assert "### ZZZ Validator" in content
    assert "GDC --> BASE" in content
    assert content.index("### GDC Validator") < content.index("### ZZZ Validator")


def test_functions_main_orchestrates_all_support_surfaces(monkeypatch):
    module = _load("generate_functions_doc.py", "functions_main")
    calls = []

    monkeypatch.setattr(module, "generate_cli_flowchart", lambda: calls.append("cli"))
    monkeypatch.setattr(module, "generate_lint_flowchart", lambda: calls.append("lint"))
    monkeypatch.setattr(
        module, "generate_validator_flowchart", lambda: calls.append("validator")
    )
    monkeypatch.setattr(
        module, "generate_domain_flowcharts", lambda: calls.append("domain")
    )
    monkeypatch.setattr(
        module,
        "update_directory_index",
        lambda path: calls.append(("index", path)),
    )

    module.main()

    assert calls[:4] == ["cli", "lint", "validator", "domain"]
    assert len([item for item in calls if isinstance(item, tuple)]) == 4


def test_rules_formatting_and_global_config():
    module = _load("generate_rules_doc.py", "rules_format")

    assert module.format_type({}) == ""
    assert module.format_type({"type": "string"}) == "string"
    assert module.format_type(
        {"type": "array", "items": {"type": "string"}}
    ) == "array[string]"
    assert module.format_type(
        {"type": ["string", "array"], "items": {"type": "integer"}}
    ) == "string &#124; array[integer]"
    assert module.format_enum({}) == ""
    assert r"a\|b" in module.format_enum({"enum": ["a|b", 2]})
    assert module.generate_from_x_global_config({}) == ""

    rendered = module.generate_from_x_global_config(
        {
            "x-global-config": {
                "simple_value": "x|y",
                "list_value": ["a", "b|c"],
                "nested": {"scalar": "v", "items": ["x", "y"]},
                "severity_levels": {"policy": {"bad": "ERROR"}},
            }
        }
    )
    assert "Governance" in rendered
    assert "Severity Levels" in rendered
    assert "ERROR" in rendered
    assert r"x\|y" in rendered


def test_rules_generate_json_schema_covers_metadata_structure_and_content():
    module = _load("generate_rules_doc.py", "rules_schema")

    data = {
        "definitions": {
            "metadata": {
                "title": "Artifact Metadata",
                "required": ["id"],
                "properties": {
                    "id": {"type": "string"},
                    "owner": {
                        "title": "Owner",
                        "required": ["name"],
                        "properties": {
                            "name": {"type": "string"},
                            "kind": {
                                "title": "Owner Kind",
                                "enum": ["team", "person"],
                            },
                        },
                    },
                    "conditional": {
                        "allOf": [
                            {
                                "if": {},
                                "then": {
                                    "required": ["details"],
                                    "properties": {
                                        "details": {
                                            "required": ["code"],
                                            "properties": {
                                                "code": {"type": "string"}
                                            },
                                        }
                                    },
                                },
                            }
                        ]
                    },
                },
            },
            "structure": {
                "title": "Structural Rules",
                "required": ["Purpose"],
                "recommended": ["Context"],
                "x-titles": {
                    "required": "Required Sections",
                    "recommended": "Recommended Sections",
                },
                "allOf": [
                    {
                        "if": {},
                        "then": {
                            "required": ["Security"],
                            "recommended": ["Operations"],
                            "x-titles": {"required": "Conditional Required"},
                        },
                    }
                ],
            },
            "content": {
                "title": "Content Rules",
                "properties": {
                    "Body": {
                        "x-titles": {
                            "required": "Body Required",
                            "recommended": "Body Recommended",
                            "prohibited_keywords": "Body Prohibited",
                        },
                        "required_subsections": ["Invariant"],
                        "recommended": ["Example"],
                        "prohibited_keywords": ["maybe"],
                        "allOf": [
                            "ignored-non-dict",
                            {"then": {"recommended": ["Decision"]}},
                        ],
                        "if": {"required_subsections": ["IfInvariant"]},
                        "then": {"prohibited_keywords": ["guess"]},
                    }
                },
            },
        }
    }

    rendered = module.generate_from_json_schema(data)
    assert "Artifact Metadata" in rendered
    assert "Owner Kind" in rendered
    assert "Required Sections" in rendered
    assert "Conditional Required" in rendered
    assert "Body Required" in rendered
    assert "Body Recommended" in rendered
    assert "Body Prohibited" in rendered
    assert "IfInvariant" in rendered
    assert "guess" in rendered

    assert module.generate_from_json_schema({}) == ""
    combined = module.generate_markdown_table(
        {
            "x-global-config": {"simple": "x"},
            "definitions": data["definitions"],
        }
    )
    assert "Rule Category" in combined


def test_rules_current_block_and_injection_contracts(tmp_path):
    module = _load("generate_rules_doc.py", "rules_markdown")

    missing = tmp_path / "missing.md"
    assert module.current_block(str(missing)) is None
    assert module.inject_to_markdown(str(missing), "TABLE") is False

    plain = tmp_path / "plain.md"
    plain.write_text("plain", encoding="utf-8")
    assert module.current_block(str(plain)) is None
    assert module.inject_to_markdown(str(plain), "TABLE") is False

    rules = tmp_path / "rules.md"
    rules.write_text(
        "<!-- AUTO-GENERATED-RULES:START -->\nOLD\n"
        "<!-- AUTO-GENERATED-RULES:END -->",
        encoding="utf-8",
    )
    assert module.current_block(str(rules)) == "OLD"
    assert module.inject_to_markdown(str(rules), "TABLE") is True
    assert module.current_block(str(rules)) == "TABLE"

    schema = tmp_path / "schema.md"
    schema.write_text(
        "<!-- AUTO-GENERATED-SCHEMA:START -->\nOLD2\n"
        "<!-- AUTO-GENERATED-SCHEMA:END -->",
        encoding="utf-8",
    )
    assert module.current_block(str(schema)) == "OLD2"
    assert module.inject_to_markdown(str(schema), "TABLE2") is True
    assert module.current_block(str(schema)) == "TABLE2"

    assert module.get_target_doc_name({}) == ""
    assert module.get_target_doc_name(
        {"config": {"target_doc": "GDC-001.md"}}
    ) == "GDC-001.md"


def _simple_schema(target):
    data = {
        "definitions": {
            "structure": {
                "title": "Structural Rules",
                "required": ["Purpose"],
            }
        }
    }
    if target is not None:
        data["config"] = {"target_doc": target}
    return data


def test_rules_process_update_and_check_modes(tmp_path, monkeypatch, capsys):
    module = _load("generate_rules_doc.py", "rules_process")

    schemas = tmp_path / "schemas"
    docs = tmp_path / "docs"
    schemas.mkdir()
    docs.mkdir()

    monkeypatch.setattr(module, "SCHEMAS_DIR", str(schemas))
    monkeypatch.setattr(module, "DOCS_DIR", str(docs))

    (schemas / "00-empty.schema.json").write_text("{}", encoding="utf-8")
    (schemas / "01-no-target.schema.json").write_text(
        json.dumps(_simple_schema(None)),
        encoding="utf-8",
    )
    (schemas / "02-empty-table.schema.json").write_text(
        json.dumps({"config": {"target_doc": "empty.md"}}),
        encoding="utf-8",
    )
    (schemas / "03-valid.schema.json").write_text(
        json.dumps(_simple_schema("valid.md")),
        encoding="utf-8",
    )
    (schemas / "04-broken.schema.json").write_text(
        json.dumps(_simple_schema("broken.md")),
        encoding="utf-8",
    )
    (schemas / "05-malformed.schema.json").write_text("{", encoding="utf-8")

    (docs / "valid.md").write_text(
        "<!-- AUTO-GENERATED-SCHEMA:START -->\nOLD\n"
        "<!-- AUTO-GENERATED-SCHEMA:END -->",
        encoding="utf-8",
    )
    (docs / "broken.md").write_text("no markers", encoding="utf-8")

    assert module.process(check=False) == []
    output = capsys.readouterr().out
    assert "[SKIP]" in output
    assert "[OK]" in output
    assert "[FAIL]" in output
    assert "Error processing" in output

    assert module.process(check=True) == [
        ("broken.md", "missing AUTO-GENERATED markers or file absent")
    ]

    (docs / "valid.md").write_text(
        "<!-- AUTO-GENERATED-SCHEMA:START -->\nDRIFT\n"
        "<!-- AUTO-GENERATED-SCHEMA:END -->",
        encoding="utf-8",
    )
    drift = module.process(check=True)
    assert ("valid.md", "out of sync with 03-valid.schema.json") in drift


def test_rules_main_exit_contract(monkeypatch):
    module = _load("generate_rules_doc.py", "rules_main")

    calls = []
    monkeypatch.setattr(
        module,
        "process",
        lambda check=False: calls.append(check) or [],
    )

    assert module.main([]) == 0
    assert calls[-1] is False

    assert module.main(["--check"]) == 0
    assert calls[-1] is True

    monkeypatch.setattr(
        module,
        "process",
        lambda check=False: [("GDC-001.md", "drift")],
    )
    assert module.main(["--check"]) == 1
