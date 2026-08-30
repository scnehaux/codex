import tempfile
import os
from engine.control.auditors.dependency_scanner import (
    audit_circular_dependencies,
    build_dependency_graph,
)
from engine.control.config.severity import SeverityRule


def test_dependency_scanner_no_filepath():
    meta = {
        "DOC-1": {
            "id": "DOC-1",
            "title": "Doc One",
            # missing _filepath
        }
    }
    graph, _ = build_dependency_graph(meta)
    assert not graph.get("DOC-1")


def test_audit_circular_dependencies():
    with tempfile.TemporaryDirectory() as tmpdir:
        f1 = os.path.join(tmpdir, "doc1.md")
        f2 = os.path.join(tmpdir, "doc2.md")

        with open(f1, "w", encoding="utf-8") as f:
            f.write("## Dependencies\nDepends on Doc Two")

        with open(f2, "w", encoding="utf-8") as f:
            f.write("## Dependencies\nDepends on Doc One")

        all_doc_metadata = {
            "DOC-1": {
                "id": "DOC-1",
                "title": "Doc One",
                "_filepath": f1,
            },
            "DOC-2": {
                "id": "DOC-2",
                "title": "Doc Two",
                "_filepath": f2,
            },
        }

        severity_levels = {r.value: "ERROR" for r in SeverityRule}
        errors = audit_circular_dependencies(all_doc_metadata, severity_levels)

        # Expect errors for both files in the cycle
        assert len(errors) == 2
        assert "circular runtime dependency detected" in errors[0][2].lower()

        filepaths = {err[0] for err in errors}
        assert f1 in filepaths
        assert f2 in filepaths


def test_dependency_scanner_fallback_srd_text(tmpdir):
    f1 = str(tmpdir.join("doc1.md"))
    f2 = str(tmpdir.join("doc2.md"))
    with open(f1, "w", encoding="utf-8") as f:
        # No "srd", "synchronous", or "depends on" keywords, triggers line 70 fallback
        f.write("## Dependencies\nRelies on Doc Two for processing")

    with open(f2, "w", encoding="utf-8") as f:
        f.write("## Dependencies\nNo dependencies")

    all_doc_metadata = {
        "DOC-1": {"id": "DOC-1", "title": "Doc Two", "_filepath": f1},
        "DOC-2": {"id": "DOC-2", "title": "Doc Two", "_filepath": f2},
    }
    graph, _ = build_dependency_graph(all_doc_metadata)
    assert "DOC-2" in graph.get("DOC-1", set())
