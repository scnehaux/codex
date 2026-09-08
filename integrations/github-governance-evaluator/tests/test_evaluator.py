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
spec = importlib.util.spec_from_file_location(
    "governance_evaluator", PACKAGE / "evaluator.py"
)
target = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = target
spec.loader.exec_module(target)


class EvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.manifest_path = root / "candidate.json"
        self.facts_path = root / "facts.json"
        self.revision = "c" * 40
        self.manifest_data = {
            "schema_version": 1,
            "repository": "scnehaux/codex",
            "pull_request": 8,
            "base_sha": "a" * 40,
            "head_sha": "b" * 40,
            "changed_files": ["README.md"],
        }
        self.facts_data = {
            "schema_version": 1,
            "repository": "scnehaux/codex",
            "pull_request": 8,
            "base_sha": "a" * 40,
            "head_sha": "b" * 40,
            "authority_source_revision": self.revision,
            "candidate_qualification": "pass",
            "privileged_validation": "not_required",
        }

    def write_manifest(self, data=None):
        self.manifest_path.write_text(
            json.dumps(self.manifest_data if data is None else data), encoding="utf-8"
        )
        return self.manifest_path

    def write_facts(self, data=None):
        self.facts_path.write_text(
            json.dumps(self.facts_data if data is None else data), encoding="utf-8"
        )
        return self.facts_path

    def load_inputs(self):
        return (
            target.CandidateManifest.load(self.write_manifest()),
            target.EvaluationFacts.load(self.write_facts()),
        )

    def fail_code(self, code, fn, *args):
        with self.assertRaises(target.EvaluationError) as caught:
            fn(*args)
        self.assertEqual(caught.exception.code, code)

    def test_unprotected_candidate_passes_deterministically_but_cannot_publish(self):
        manifest, facts = self.load_inputs()
        result = target.evaluate(manifest, facts, self.revision)
        self.assertEqual(result["status"], "evaluation_complete")
        self.assertEqual(result["governance_decision"], "pass")
        self.assertEqual(result["failure_reasons"], [])
        self.assertFalse(result["facts_provenance_verified"])
        self.assertFalse(result["publish_enabled"])
        self.assertFalse(result["authority_promoted"])
        self.assertFalse(result["candidate_code_executed"])
        self.assertFalse(result["credentials_used"])
        self.assertFalse(result["effective_enforcement_proven"])

    def test_candidate_qualification_failure_is_governance_failure(self):
        self.facts_data["candidate_qualification"] = "fail"
        manifest, facts = self.load_inputs()
        result = target.evaluate(manifest, facts, self.revision)
        self.assertEqual(result["governance_decision"], "fail")
        self.assertEqual(result["failure_reasons"], ["candidate-qualification-failed"])

    def test_protected_candidate_requires_privileged_pass(self):
        self.manifest_data["changed_files"] = ["governance/scm/enforcement-policy.yaml"]
        self.facts_data["privileged_validation"] = "pass"
        manifest, facts = self.load_inputs()
        result = target.evaluate(manifest, facts, self.revision)
        self.assertEqual(result["governance_decision"], "pass")
        self.assertTrue(result["requires_privileged_validation"])
        self.assertEqual(
            result["protected_mutations"],
            ["governance/scm/enforcement-policy.yaml"],
        )

    def test_protected_candidate_privileged_failure_is_governance_failure(self):
        self.manifest_data["changed_files"] = [".github/workflows/governance.yml"]
        self.facts_data["privileged_validation"] = "fail"
        manifest, facts = self.load_inputs()
        result = target.evaluate(manifest, facts, self.revision)
        self.assertEqual(result["governance_decision"], "fail")
        self.assertEqual(result["failure_reasons"], ["privileged-validation-failed"])

    def test_protected_candidate_missing_privileged_validation_fails(self):
        self.manifest_data["changed_files"] = [".github/CODEOWNERS"]
        manifest, facts = self.load_inputs()
        result = target.evaluate(manifest, facts, self.revision)
        self.assertEqual(result["governance_decision"], "fail")
        self.assertEqual(result["failure_reasons"], ["privileged-validation-missing"])

    def test_multiple_failures_are_stable_and_ordered(self):
        self.manifest_data["changed_files"] = ["engine/adapters/scm/github.py"]
        self.facts_data["candidate_qualification"] = "fail"
        self.facts_data["privileged_validation"] = "fail"
        manifest, facts = self.load_inputs()
        result = target.evaluate(manifest, facts, self.revision)
        self.assertEqual(
            result["failure_reasons"],
            ["candidate-qualification-failed", "privileged-validation-failed"],
        )

    def test_unprotected_candidate_rejects_privileged_claim(self):
        self.facts_data["privileged_validation"] = "pass"
        manifest, facts = self.load_inputs()
        self.fail_code(
            "privileged-validation-unexpected",
            target.evaluate,
            manifest,
            facts,
            self.revision,
        )

    def test_facts_must_bind_exact_candidate_and_authority_identity(self):
        fields = {
            "repository": "other/repo",
            "pull_request": 99,
            "base_sha": "d" * 40,
            "head_sha": "e" * 40,
            "authority_source_revision": "f" * 40,
        }
        for field, value in fields.items():
            with self.subTest(field=field):
                facts_data = dict(self.facts_data, **{field: value})
                manifest = target.CandidateManifest.load(self.write_manifest())
                if field == "repository":
                    self.fail_code(
                        "facts-repository-mismatch",
                        target.EvaluationFacts.load,
                        self.write_facts(facts_data),
                    )
                    continue
                facts = target.EvaluationFacts.load(self.write_facts(facts_data))
                self.fail_code(
                    "facts-binding-mismatch",
                    target.evaluate,
                    manifest,
                    facts,
                    self.revision,
                )

    def test_candidate_revision_cannot_be_authority(self):
        manifest, facts = self.load_inputs()
        facts = target.EvaluationFacts(
            facts.repository,
            facts.pull_request,
            facts.base_sha,
            facts.head_sha,
            manifest.head_sha,
            facts.candidate_qualification,
            facts.privileged_validation,
        )
        self.fail_code(
            "candidate-as-authority",
            target.evaluate,
            manifest,
            facts,
            manifest.head_sha,
        )

    def test_facts_enums_are_closed(self):
        for field, value, code in (
            ("candidate_qualification", "neutral", "candidate-qualification"),
            ("candidate_qualification", True, "candidate-qualification"),
            ("privileged_validation", "skip", "privileged-validation"),
            ("privileged_validation", None, "privileged-validation"),
        ):
            data = dict(self.facts_data, **{field: value})
            self.fail_code(code, target.EvaluationFacts.load, self.write_facts(data))

    def test_manifest_rejects_wrong_schema_pr_range_and_paths(self):
        cases = [
            ({**self.manifest_data, "repository": "other/repo"}, "repository-mismatch"),
            ({**self.manifest_data, "schema_version": 2}, "manifest-version"),
            ({**self.manifest_data, "pull_request": 0}, "pull-request"),
            ({**self.manifest_data, "pull_request": True}, "pull-request"),
            (
                {**self.manifest_data, "head_sha": self.manifest_data["base_sha"]},
                "candidate-range",
            ),
        ]
        for data, code in cases:
            with self.subTest(code=code):
                self.fail_code(
                    code, target.CandidateManifest.load, self.write_manifest(data)
                )

    def test_inputs_require_exact_fields(self):
        for data, loader, writer, code in (
            (
                {**self.manifest_data, "extra": "candidate-controlled"},
                target.CandidateManifest.load,
                self.write_manifest,
                "manifest-schema",
            ),
            (
                {**self.facts_data, "extra": "caller-controlled"},
                target.EvaluationFacts.load,
                self.write_facts,
                "facts-schema",
            ),
        ):
            self.fail_code(code, loader, writer(data))

    def test_malformed_missing_and_oversized_inputs_fail_closed(self):
        for path, limit, prefix, loader in (
            (
                self.manifest_path,
                target.MAX_MANIFEST_BYTES,
                "manifest",
                target.CandidateManifest.load,
            ),
            (
                self.facts_path,
                target.MAX_FACTS_BYTES,
                "facts",
                target.EvaluationFacts.load,
            ),
        ):
            with self.subTest(prefix=prefix):
                path.write_text("{", encoding="utf-8")
                self.fail_code(f"{prefix}-invalid-json", loader, path)
                path.write_bytes(b" " * (limit + 1))
                self.fail_code(f"{prefix}-too-large", loader, path)
                self.fail_code(f"{prefix}-unreadable", loader, path.with_name("missing"))

    def test_changed_files_must_be_sorted_unique_and_bounded(self):
        for files in (
            [],
            ["b", "a"],
            ["a", "a"],
            ["a"] * (target.MAX_CHANGED_FILES + 1),
        ):
            data = dict(self.manifest_data, changed_files=files)
            code = (
                "changed-files"
                if not files or len(files) > target.MAX_CHANGED_FILES
                else "changed-files-order"
            )
            self.fail_code(code, target.CandidateManifest.load, self.write_manifest(data))

    def test_paths_reject_traversal_absolute_windows_and_controls(self):
        for value in (
            None,
            "",
            "/etc/passwd",
            "\\server\\x",
            "a\\b",
            "a/../b",
            "a//b",
            "./a",
            "a/./b",
            "a\x00b",
            "a\nb",
        ):
            with self.subTest(value=value):
                self.fail_code("changed-path", target.validate_path, value)

    def test_protection_classifier_matches_declared_surfaces(self):
        for path in (
            ".github/CODEOWNERS",
            ".github/workflows/x.yml",
            "engine/adapters/scm/github.py",
            "engine/control/governance/x.py",
            "governance/github/x.yaml",
            "governance/scm/x.yaml",
            "scripts/github_policy_check.py",
        ):
            self.assertTrue(target.is_protected(path), path)
        for path in (
            "README.md",
            "engine/core/model.py",
            "tests/test_x.py",
            "scripts/other.py",
        ):
            self.assertFalse(target.is_protected(path), path)

    def test_cli_exit_codes_distinguish_pass_fail_and_invalid_input(self):
        base_args = [
            "--candidate-manifest",
            str(self.write_manifest()),
            "--evaluation-facts",
            str(self.write_facts()),
            "--authority-source-revision",
            self.revision,
        ]
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(target.main(base_args), 0)
        self.assertEqual(json.loads(output.getvalue())["governance_decision"], "pass")

        self.facts_data["candidate_qualification"] = "fail"
        base_args[3] = str(self.write_facts())
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(target.main(base_args), 2)
        self.assertEqual(json.loads(output.getvalue())["governance_decision"], "fail")

        output = io.StringIO()
        base_args[1] = str(self.manifest_path.with_name("missing.json"))
        with redirect_stdout(output):
            self.assertEqual(target.main(base_args), 1)
        self.assertEqual(json.loads(output.getvalue())["status"], "blocked")

    def test_cli_masks_unexpected_exception(self):
        output = io.StringIO()
        with (
            patch.object(
                target.CandidateManifest, "load", side_effect=RuntimeError("SECRET")
            ),
            redirect_stdout(output),
        ):
            code = target.main(
                [
                    "--candidate-manifest",
                    str(self.write_manifest()),
                    "--evaluation-facts",
                    str(self.write_facts()),
                    "--authority-source-revision",
                    self.revision,
                ]
            )
        self.assertEqual(code, 1)
        self.assertNotIn("SECRET", output.getvalue())
        self.assertEqual(json.loads(output.getvalue())["code"], "unexpected-local-error")


if __name__ == "__main__":
    unittest.main(verbosity=2)
