from __future__ import annotations

import hashlib
import unittest
from unittest.mock import patch

from engine.control.framework.executable import executable_framework
from engine.control.repository.git_ingestion import (
    GitCandidateBatch,
    GitIngestedCandidate,
    GitRepositoryContext,
    GitSourceProvenance,
)
from engine.control.repository.snapshot import (
    ValidatedRepositorySnapshot,
    build_validated_repository_snapshot,
)
from engine.control.validation.contracts import ValidationReport
from engine.control.validation.pipeline import (
    SourceDocument,
    build_artifact_candidate,
    parse_source_document,
)
from engine.core.knowledge.compiler import compile_repository_graph
from engine.core.metamodel import ArchitectureNamespace
from engine.core.repository import RepositoryModel

SHA = "a" * 40
NS = ArchitectureNamespace("acme", "architecture")


def entry(path: str, content: str) -> GitIngestedCandidate:
    context = GitRepositoryContext("acme/architecture", NS, SHA)
    provenance = GitSourceProvenance(
        context, path, hashlib.sha256(content.encode()).hexdigest()
    )
    source = SourceDocument(
        path,
        content,
        source_reference=provenance.source_reference,
        source_namespace=NS,
    )
    candidate = build_artifact_candidate(parse_source_document(source))
    return GitIngestedCandidate(provenance, candidate)


def batch_of(*entries: GitIngestedCandidate) -> GitCandidateBatch:
    return GitCandidateBatch(entries[0].provenance.context, tuple(entries))


def passing_report(item: GitIngestedCandidate) -> ValidationReport:
    return ValidationReport(
        "report-" + item.candidate.candidate_id, item.candidate.candidate_id
    )


ADR = """---
doc_meta:
  id: ADR-001
  title: Decision
  status: proposed
---
# Decision
"""


class ValidatedRepositorySnapshotTests(unittest.TestCase):
    def test_snapshot_is_deterministic_and_framework_revision_bound(self):
        item = entry("decisions/ADR-001.md", ADR)
        batch = batch_of(item)
        report = passing_report(item)
        with patch(
            "engine.control.repository.snapshot.validate_candidate", return_value=report
        ):
            a = build_validated_repository_snapshot(batch)
            b = build_validated_repository_snapshot(batch)
        self.assertEqual(a, b)
        self.assertEqual(a.snapshot_id, b.snapshot_id)
        self.assertEqual(a.revision, SHA)
        self.assertEqual(
            a.framework_semantic_sha256, executable_framework().semantic_sha256
        )
        self.assertEqual(a.validation_report_ids, (report.report_id,))

    def test_builder_runs_validation_and_rejects_malformed_candidate(self):
        item = entry("decisions/bad.md", "not frontmatter")
        with self.assertRaisesRegex(ValueError, "pass validation"):
            build_validated_repository_snapshot(batch_of(item))

    def test_failed_validation_cannot_be_overridden_by_caller(self):
        item = entry("decisions/ADR-001.md", ADR)
        report = ValidationReport(
            "failing-report",
            item.candidate.candidate_id,
            (
                __import__(
                    "engine.control.validation.contracts",
                    fromlist=["ValidationFinding"],
                ).ValidationFinding("finding", "rule", "blocked", True),
            ),
        )
        with patch(
            "engine.control.repository.snapshot.validate_candidate", return_value=report
        ):
            with self.assertRaisesRegex(ValueError, "pass validation"):
                build_validated_repository_snapshot(batch_of(item))

    def test_unresolved_relationship_cannot_enter_snapshot_even_after_pass(self):
        item = entry(
            "decisions/ADR-001.md",
            """---
doc_meta:
  id: ADR-001
  title: Decision
  status: proposed
  governed_by:
    - SAD-999
---
""",
        )
        report = passing_report(item)
        with patch(
            "engine.control.repository.snapshot.validate_candidate", return_value=report
        ):
            with self.assertRaisesRegex(ValueError, "unresolved relationship"):
                build_validated_repository_snapshot(batch_of(item))

    def test_graph_compilation_requires_snapshot(self):
        with self.assertRaisesRegex(TypeError, "ValidatedRepositorySnapshot"):
            compile_repository_graph(RepositoryModel())

    def test_snapshot_compiles_to_canonical_graph(self):
        item = entry("decisions/ADR-001.md", ADR)
        report = passing_report(item)
        with patch(
            "engine.control.repository.snapshot.validate_candidate", return_value=report
        ):
            snapshot = build_validated_repository_snapshot(batch_of(item))
        graph = compile_repository_graph(snapshot)
        self.assertEqual(
            tuple(graph.node_map),
            (item.candidate.artifact.artifact.canonical_key,),
        )
        self.assertIsInstance(snapshot, ValidatedRepositorySnapshot)

    def test_value_object_rejects_invalid_identity_fields(self):
        item = entry("decisions/ADR-001.md", ADR)
        report = passing_report(item)
        with patch(
            "engine.control.repository.snapshot.validate_candidate", return_value=report
        ):
            snapshot = build_validated_repository_snapshot(batch_of(item))
        values = {
            "framework_id": snapshot.framework_id,
            "framework_version": snapshot.framework_version,
            "framework_semantic_sha256": snapshot.framework_semantic_sha256,
            "repository_context": snapshot.repository_context,
            "repository": snapshot.repository,
            "batch_id": snapshot.batch_id,
            "validation_report_ids": snapshot.validation_report_ids,
            "snapshot_id": snapshot.snapshot_id,
        }
        for field, bad in (
            ("framework_id", " "),
            ("framework_version", " "),
            ("framework_semantic_sha256", "x"),
            ("batch_id", "x"),
            ("snapshot_id", "x"),
        ):
            changed = dict(values)
            changed[field] = bad
            with self.assertRaises(ValueError):
                ValidatedRepositorySnapshot(**changed)

    def test_snapshot_value_object_type_and_report_guards(self):
        item = entry("decisions/ADR-001.md", ADR)
        report = passing_report(item)
        with patch(
            "engine.control.repository.snapshot.validate_candidate", return_value=report
        ):
            snapshot = build_validated_repository_snapshot(batch_of(item))
        values = {
            "framework_id": snapshot.framework_id,
            "framework_version": snapshot.framework_version,
            "framework_semantic_sha256": snapshot.framework_semantic_sha256,
            "repository_context": snapshot.repository_context,
            "repository": snapshot.repository,
            "batch_id": snapshot.batch_id,
            "validation_report_ids": snapshot.validation_report_ids,
            "snapshot_id": snapshot.snapshot_id,
        }
        changed = dict(values)
        changed["repository_context"] = "bad"
        with self.assertRaises(TypeError):
            ValidatedRepositorySnapshot(**changed)
        changed = dict(values)
        changed["repository"] = "bad"
        with self.assertRaises(TypeError):
            ValidatedRepositorySnapshot(**changed)
        changed = dict(values)
        changed["validation_report_ids"] = ()
        with self.assertRaises(ValueError):
            ValidatedRepositorySnapshot(**changed)
        changed = dict(values)
        changed["validation_report_ids"] = ("x", "x")
        with self.assertRaises(ValueError):
            ValidatedRepositorySnapshot(**changed)
        self.assertEqual(snapshot.semantic_state()[0], snapshot.framework_id)

    def test_builder_rejects_wrong_batch_and_framework_types(self):
        with self.assertRaises(TypeError):
            build_validated_repository_snapshot("bad")  # type: ignore[arg-type]
        item = entry("decisions/ADR-001.md", ADR)
        with self.assertRaises(TypeError):
            build_validated_repository_snapshot(batch_of(item), framework="bad")  # type: ignore[arg-type]

    def test_nonpromotable_candidate_is_rejected_even_if_validation_is_forged_pass(
        self,
    ):
        item = entry("decisions/bad.md", "not frontmatter")
        report = passing_report(item)
        with patch(
            "engine.control.repository.snapshot.validate_candidate", return_value=report
        ):
            with self.assertRaisesRegex(ValueError, "promotable artifacts"):
                build_validated_repository_snapshot(batch_of(item))


if __name__ == "__main__":
    unittest.main()
