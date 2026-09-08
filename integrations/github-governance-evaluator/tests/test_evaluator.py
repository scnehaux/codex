from __future__ import annotations

from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

PACKAGE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("governance_evaluator", PACKAGE / "evaluator.py")
target = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = target
spec.loader.exec_module(target)


class EvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "candidate.json"
        self.data = {
            "schema_version": 1,
            "repository": "scnehaux/codex",
            "pull_request": 7,
            "base_sha": "a" * 40,
            "head_sha": "b" * 40,
            "changed_files": ["README.md"],
        }
        self.revision = "c" * 40

    def write(self, data=None):
        self.path.write_text(json.dumps(self.data if data is None else data), encoding="utf-8")
        return self.path

    def fail_code(self, code, fn, *args):
        with self.assertRaises(target.EvaluationError) as caught:
            fn(*args)
        self.assertEqual(caught.exception.code, code)

    def test_safe_candidate_creates_plan_not_decision(self):
        manifest = target.CandidateManifest.load(self.write())
        plan = target.build_plan(manifest, self.revision)
        self.assertEqual(plan["status"], "evaluation_plan_ready")
        self.assertEqual(plan["candidate_sha"], "b" * 40)
        self.assertEqual(plan["authority_source_revision"], self.revision)
        self.assertEqual(plan["governance_decision"], "not_evaluated")
        self.assertFalse(plan["publish_enabled"])
        self.assertFalse(plan["candidate_code_executed"])
        self.assertFalse(plan["credentials_used"])
        self.assertFalse(plan["effective_enforcement_proven"])
        self.assertEqual(plan["protected_mutations"], [])

    def test_protected_mutations_are_flagged_without_fake_failure_or_success(self):
        self.data["changed_files"] = sorted([
            ".github/CODEOWNERS",
            ".github/workflows/other.yml",
            "engine/adapters/scm/github.py",
            "engine/control/governance/scm_observer.py",
            "governance/github/authority-binding.yaml",
            "governance/scm/enforcement-policy.yaml",
            "scripts/github_policy_check.py",
        ])
        plan = target.build_plan(target.CandidateManifest.load(self.write()), self.revision)
        self.assertTrue(plan["requires_privileged_validation"])
        self.assertEqual(plan["protected_mutations"], self.data["changed_files"])
        self.assertEqual(plan["governance_decision"], "not_evaluated")
        self.assertFalse(plan["publish_enabled"])

    def test_candidate_revision_cannot_be_authority(self):
        manifest = target.CandidateManifest.load(self.write())
        self.fail_code("candidate-as-authority", target.build_plan, manifest, manifest.head_sha)

    def test_shas_are_exact_lowercase_nonzero(self):
        for value in (None, "main", "A" * 40, "0" * 40, "a" * 39, "a" * 41, "a" * 40 + "\n"):
            with self.subTest(value=value):
                self.fail_code("authority-source-revision", target.require_sha, value, "authority-source-revision")

    def test_manifest_rejects_wrong_repository_schema_and_pr(self):
        cases = [
            ({**self.data, "repository": "other/repo"}, "repository-mismatch"),
            ({**self.data, "schema_version": 2}, "manifest-version"),
            ({**self.data, "pull_request": 0}, "pull-request"),
            ({**self.data, "pull_request": True}, "pull-request"),
            ({**self.data, "head_sha": self.data["base_sha"]}, "candidate-range"),
        ]
        for data, code in cases:
            with self.subTest(code=code):
                self.fail_code(code, target.CandidateManifest.load, self.write(data))

    def test_manifest_requires_exact_fields(self):
        data = dict(self.data)
        data["extra"] = "candidate-controlled"
        self.fail_code("manifest-schema", target.CandidateManifest.load, self.write(data))
        data = dict(self.data)
        del data["changed_files"]
        self.fail_code("manifest-schema", target.CandidateManifest.load, self.write(data))

    def test_manifest_rejects_bad_json_size_and_missing_file(self):
        self.path.write_text("{", encoding="utf-8")
        self.fail_code("manifest-invalid-json", target.CandidateManifest.load, self.path)
        self.path.write_bytes(b" " * (target.MAX_MANIFEST_BYTES + 1))
        self.fail_code("manifest-too-large", target.CandidateManifest.load, self.path)
        self.fail_code("manifest-unreadable", target.CandidateManifest.load, self.path.with_name("missing.json"))

    def test_changed_files_must_be_sorted_unique_and_bounded(self):
        for files in ([], ["b", "a"], ["a", "a"], ["a"] * (target.MAX_CHANGED_FILES + 1)):
            self.data["changed_files"] = files
            code = "changed-files" if not files or len(files) > target.MAX_CHANGED_FILES else "changed-files-order"
            self.fail_code(code, target.CandidateManifest.load, self.write())

    def test_paths_reject_traversal_absolute_windows_and_controls(self):
        for value in (None, "", "/etc/passwd", "\\server\\x", "a\\b", "a/../b", "a//b", "./a", "a/./b", "a\x00b", "a\nb"):
            with self.subTest(value=value):
                self.fail_code("changed-path", target.validate_path, value)

    def test_exact_and_prefix_protection(self):
        protected = [
            ".github/CODEOWNERS",
            ".github/workflows/x.yml",
            "engine/adapters/scm/github.py",
            "engine/control/governance/x.py",
            "governance/github/x.yaml",
            "governance/scm/x.yaml",
            "scripts/github_policy_check.py",
        ]
        for path in protected:
            self.assertTrue(target.is_protected(path), path)
        for path in ("README.md", "engine/core/model.py", "tests/test_x.py", "scripts/other.py"):
            self.assertFalse(target.is_protected(path), path)

    def test_cli_success_and_blocked_outputs_never_claim_publish(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = target.main([
                "--candidate-manifest", str(self.write()),
                "--authority-source-revision", self.revision,
            ])
        self.assertEqual(code, 0)
        result = json.loads(output.getvalue())
        self.assertFalse(result["publish_enabled"])
        self.assertEqual(result["governance_decision"], "not_evaluated")

        output = io.StringIO()
        with redirect_stdout(output):
            code = target.main([
                "--candidate-manifest", str(self.path.with_name("missing.json")),
                "--authority-source-revision", self.revision,
            ])
        self.assertEqual(code, 1)
        result = json.loads(output.getvalue())
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["publish_enabled"])

    def test_cli_masks_unexpected_exception(self):
        output = io.StringIO()
        with patch.object(target.CandidateManifest, "load", side_effect=RuntimeError("SECRET")), redirect_stdout(output):
            code = target.main([
                "--candidate-manifest", str(self.write()),
                "--authority-source-revision", self.revision,
            ])
        self.assertEqual(code, 1)
        self.assertNotIn("SECRET", output.getvalue())
        self.assertEqual(json.loads(output.getvalue())["code"], "unexpected-local-error")


if __name__ == "__main__":
    unittest.main(verbosity=2)
