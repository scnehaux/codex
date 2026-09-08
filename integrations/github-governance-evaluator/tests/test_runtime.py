from __future__ import annotations

from contextlib import redirect_stdout
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

PACKAGE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("governance_runtime", PACKAGE / "runtime.py")
target = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = target
spec.loader.exec_module(target)


class FakeGitHub:
    def __init__(self):
        self.pr_number = 10
        self.base_sha = "a" * 40
        self.head_sha = "b" * 40
        self.pr = {
            "number": self.pr_number,
            "state": "open",
            "changed_files": 1,
            "base": {
                "ref": "main",
                "sha": self.base_sha,
                "repo": {"full_name": "scnehaux/codex"},
            },
            "head": {
                "ref": "feature",
                "sha": self.head_sha,
                "repo": {"full_name": "scnehaux/codex"},
            },
        }
        self.file_pages = {
            1: [{"filename": "README.md", "status": "modified"}],
        }
        self.qualification = {
            "total_count": 1,
            "check_runs": [
                {
                    "id": 12345,
                    "name": "Governance Qualification",
                    "head_sha": self.head_sha,
                    "status": "completed",
                    "conclusion": "success",
                    "details_url": "https://github.com/scnehaux/codex/actions/runs/99/job/12345",
                    "app": {
                        "id": 15368,
                        "slug": "github-actions",
                        "owner": {"login": "github"},
                    },
                }
            ],
        }
        self.calls = []

    def __call__(self, path, query=None):
        self.calls.append((path, copy.deepcopy(query)))
        if path == f"/repos/scnehaux/codex/pulls/{self.pr_number}":
            return copy.deepcopy(self.pr)
        if path == f"/repos/scnehaux/codex/pulls/{self.pr_number}/files":
            return copy.deepcopy(self.file_pages.get(query["page"], []))
        if path == f"/repos/scnehaux/codex/commits/{self.head_sha}/check-runs":
            return copy.deepcopy(self.qualification)
        raise AssertionError(f"unexpected fake endpoint: {path}")


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.api = FakeGitHub()
        self.evaluator = target.load_pinned_evaluator()

    def fail_code(self, code, fn, *args, **kwargs):
        with self.assertRaises(target.RuntimeBoundaryError) as caught:
            fn(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)

    def test_pinned_evaluator_blob_matches_promoted_revision(self):
        self.assertEqual(target.PINNED_AUTHORITY_REVISION, "23b05a855419b86b61b0c9266805bb66b143c366")
        self.assertEqual(
            target._git_blob_sha(PACKAGE / "evaluator.py"),
            "ab2f152c21bd6d6f22df21172c4d027035ff8c11",
        )
        contract = target.load_promotion()
        self.assertEqual(contract["authority_source_revision"], target.PINNED_AUTHORITY_REVISION)

    def test_safe_pull_collects_independent_facts_but_runtime_is_not_promoted(self):
        result = target.collect_and_evaluate(self.api.pr_number, self.api)
        self.assertEqual(result["status"], "runtime_evaluation_complete")
        self.assertEqual(result["governance_decision"], "pass")
        self.assertTrue(result["facts_collected_independently"])
        self.assertFalse(result["facts_provenance_verified"])
        self.assertFalse(result["runtime_source_promoted"])
        self.assertFalse(result["publish_enabled"])
        self.assertFalse(result["authority_binding_advanced"])
        self.assertFalse(result["effective_enforcement_proven"])
        self.assertFalse(result["candidate_code_executed"])
        self.assertFalse(result["credentials_used"])
        self.assertEqual(result["candidate_manifest"]["head_sha"], self.api.head_sha)
        self.assertEqual(result["collected_facts"]["candidate_qualification"], "pass")
        self.assertTrue(result["qualification_evidence"]["source_verified"])
        self.assertEqual(result["qualification_evidence"]["app_id"], 15368)
        self.assertEqual(result["evaluator_result"]["governance_decision"], "pass")

    def test_failed_candidate_qualification_is_governance_failure(self):
        self.api.qualification["check_runs"][0]["conclusion"] = "failure"
        result = target.collect_and_evaluate(self.api.pr_number, self.api)
        self.assertEqual(result["governance_decision"], "fail")
        self.assertEqual(
            result["evaluator_result"]["failure_reasons"],
            ["candidate-qualification-failed"],
        )

    def test_pinned_evaluator_protected_mutation_fails_without_privileged_source(self):
        self.api.file_pages[1] = [
            {"filename": "governance/scm/enforcement-policy.yaml", "status": "modified"}
        ]
        result = target.collect_and_evaluate(self.api.pr_number, self.api)
        self.assertEqual(result["governance_decision"], "fail")
        self.assertEqual(
            result["evaluator_result"]["failure_reasons"],
            ["privileged-validation-missing"],
        )

    def test_runtime_only_critical_mutation_fails_closed_until_evaluator_repromotion(self):
        for path in (
            "Makefile",
            "pyproject.toml",
            "engine/control/auditors/governance_auditor.py",
            "generators/generate_engine_topography.py",
            "scripts/committed_mutation_integrity.py",
            "integrations/github-governance-evaluator/runtime.py",
        ):
            with self.subTest(path=path):
                api = FakeGitHub()
                api.file_pages[1] = [{"filename": path, "status": "modified"}]
                result = target.collect_and_evaluate(api.pr_number, api)
                self.assertEqual(result["evaluator_result"]["governance_decision"], "pass")
                self.assertEqual(result["governance_decision"], "fail")
                self.assertEqual(
                    result["runtime_failure_reasons"],
                    ["runtime-critical-mutation-requires-privileged-validation"],
                )
                self.assertEqual(result["runtime_only_protected_mutations"], [path])

    def test_renamed_previous_path_is_included_and_cannot_hide_protected_mutation(self):
        self.api.file_pages[1] = [
            {
                "filename": "docs/old-workflow.md",
                "previous_filename": ".github/workflows/governance.yml",
                "status": "renamed",
            }
        ]
        result = target.collect_and_evaluate(self.api.pr_number, self.api)
        self.assertIn(
            ".github/workflows/governance.yml",
            result["candidate_manifest"]["changed_files"],
        )
        self.assertEqual(result["governance_decision"], "fail")
        self.assertIn(
            "privileged-validation-missing",
            result["evaluator_result"]["failure_reasons"],
        )

    def test_pull_identity_is_bound_to_open_main_same_repository(self):
        cases = [
            ({"number": 11}, "pull-identity"),
            ({"state": "closed"}, "pull-identity"),
            ({"base": {"ref": "develop", "sha": self.api.base_sha, "repo": {"full_name": "scnehaux/codex"}}}, "pull-base-ref"),
            ({"head": {"ref": "feature", "sha": self.api.head_sha, "repo": {"full_name": "fork/codex"}}}, "pull-repository"),
            ({"changed_files": 0}, "pull-changed-files"),
            ({"changed_files": target.MAX_CHANGED_FILE_RECORDS + 1}, "pull-changed-files"),
        ]
        for update, code in cases:
            with self.subTest(code=code):
                api = FakeGitHub()
                api.pr.update(update)
                self.fail_code(code, target.collect_candidate, api.pr_number, self.evaluator, api)

    def test_pull_file_pagination_is_exact_and_bounded(self):
        api = FakeGitHub()
        api.pr["changed_files"] = 101
        api.file_pages[1] = [
            {"filename": f"docs/{i:03}.md", "status": "modified"}
            for i in range(100)
        ]
        api.file_pages[2] = [{"filename": "docs/100.md", "status": "modified"}]
        manifest, evidence = target.collect_candidate(api.pr_number, self.evaluator, api)
        self.assertEqual(len(manifest.changed_files), 101)
        self.assertEqual(evidence["files_pages_read"], 2)

        api = FakeGitHub()
        api.pr["changed_files"] = 2
        self.fail_code("pull-files", target.collect_candidate, api.pr_number, self.evaluator, api)

        api = FakeGitHub()
        api.file_pages[1].append({"filename": "README.md", "status": "modified"})
        api.pr["changed_files"] = 2
        self.fail_code("pull-files", target.collect_candidate, api.pr_number, self.evaluator, api)

    def test_rename_requires_valid_previous_path(self):
        for previous in (None, "../escape", "a\\b"):
            api = FakeGitHub()
            record = {"filename": "docs/new.md", "status": "renamed"}
            if previous is not None:
                record["previous_filename"] = previous
            api.file_pages[1] = [record]
            code = "pull-file-rename" if previous is None else "pull-file-path"
            self.fail_code(code, target.collect_candidate, api.pr_number, self.evaluator, api)

    def test_qualification_source_is_exact_github_actions_app_and_head_sha(self):
        mutations = [
            ("name", "Other Check"),
            ("head_sha", "c" * 40),
            ("status", "queued"),
        ]
        for field, value in mutations:
            with self.subTest(field=field):
                api = FakeGitHub()
                api.qualification["check_runs"][0][field] = value
                code = "qualification-pending" if field == "status" else "qualification-source"
                self.fail_code(code, target.collect_candidate_qualification, api.head_sha, api)

        for app_update in (
            {"id": 999},
            {"slug": "other-app"},
            {"owner": {"login": "someone"}},
        ):
            api = FakeGitHub()
            api.qualification["check_runs"][0]["app"].update(app_update)
            self.fail_code("qualification-source", target.collect_candidate_qualification, api.head_sha, api)

    def test_qualification_ambiguity_and_missing_conclusion_fail_closed(self):
        for total, runs, code in (
            (0, [], "qualification-ambiguous"),
            (2, [{}, {}], "qualification-ambiguous"),
        ):
            api = FakeGitHub()
            api.qualification = {"total_count": total, "check_runs": runs}
            self.fail_code(code, target.collect_candidate_qualification, api.head_sha, api)
        api = FakeGitHub()
        api.qualification["check_runs"][0]["conclusion"] = None
        self.fail_code("qualification-conclusion", target.collect_candidate_qualification, api.head_sha, api)

    def test_api_allowlist_rejects_endpoint_and_query_drift_before_network(self):
        with patch.object(target, "build_opener") as opener:
            for path, query in (
                ("https://evil.test/", None),
                ("/repos/scnehaux/codex/issues/1", None),
                ("/repos/other/repo/pulls/1", None),
                ("/repos/scnehaux/codex/pulls/1", {"page": 1}),
                ("/repos/scnehaux/codex/pulls/1/files", {"per_page": 99, "page": 1}),
                (
                    "/repos/scnehaux/codex/commits/" + "a" * 40 + "/check-runs",
                    {"check_name": "Codex Governance Authority", "filter": "latest", "per_page": 100},
                ),
            ):
                with self.subTest(path=path):
                    self.fail_code(
                        "api-path" if "issues" in path or "other/repo" in path or path.startswith("http") else "api-query",
                        target.api_get,
                        path,
                        query,
                    )
            opener.assert_not_called()

    def test_api_transport_is_get_only_fixed_host_no_auth_and_no_redirect(self):
        response = io.BytesIO(b'{"number":10}')
        response.status = 200
        with patch.object(target, "build_opener") as factory:
            factory.return_value.open.return_value = response
            result = target.api_get("/repos/scnehaux/codex/pulls/10")
            self.assertEqual(result, {"number": 10})
            request = factory.return_value.open.call_args.args[0]
            self.assertEqual(request.full_url, "https://api.github.com/repos/scnehaux/codex/pulls/10")
            self.assertEqual(request.get_method(), "GET")
            self.assertIsNone(request.get_header("Authorization"))
            self.assertIsInstance(factory.call_args.args[0], target.NoRedirect)
            self.assertEqual(factory.return_value.open.call_args.kwargs["timeout"], 20)

    def test_api_errors_and_bodies_are_sanitized(self):
        for error, code in (
            (HTTPError("https://api.github.com/x", 403, "SECRET", {}, io.BytesIO(b"SECRET-BODY")), "github-http-403"),
            (HTTPError("https://api.github.com/x", 500, "SECRET", {}, io.BytesIO(b"SECRET-BODY")), "github-http-500"),
            (URLError("SECRET-INTERNAL"), "network-error"),
            (TimeoutError("SECRET-INTERNAL"), "network-error"),
        ):
            with patch.object(target, "build_opener") as factory:
                factory.return_value.open.side_effect = error
                with self.assertRaises(target.RuntimeBoundaryError) as caught:
                    target.api_get("/repos/scnehaux/codex/pulls/10")
                self.assertEqual(caught.exception.code, code)
                self.assertNotIn("SECRET", str(caught.exception))

    def test_api_rejects_large_invalid_json_and_unexpected_status(self):
        for body, status, code in (
            (b"{" , 200, "api-json"),
            (b"x" * (target.MAX_RESPONSE_BYTES + 1), 200, "api-response-size"),
            (b"{}", 202, "api-status"),
        ):
            response = io.BytesIO(body)
            response.status = status
            with patch.object(target, "build_opener") as factory:
                factory.return_value.open.return_value = response
                self.fail_code(code, target.api_get, "/repos/scnehaux/codex/pulls/10")

    def test_runtime_cli_refuses_git_checkout_before_network_or_evaluator(self):
        output = io.StringIO()
        with patch.object(target, "collect_and_evaluate") as collect, redirect_stdout(output):
            code = target.main(["--pull-request", "10"])
        self.assertEqual(code, 1)
        collect.assert_not_called()
        self.assertEqual(json.loads(output.getvalue())["code"], "runtime-checkout")

    def test_cli_exit_codes_preserve_pass_fail_and_safe_error(self):
        template = {
            "status": "runtime_evaluation_complete",
            "governance_decision": "pass",
            "publish_enabled": False,
        }
        for decision, expected in (("pass", 0), ("fail", 2)):
            output = io.StringIO()
            with (
                patch.object(target, "ensure_exported_runtime"),
                patch.object(target, "collect_and_evaluate", return_value={**template, "governance_decision": decision}),
                redirect_stdout(output),
            ):
                self.assertEqual(target.main(["--pull-request", "10"]), expected)
            self.assertFalse(json.loads(output.getvalue())["publish_enabled"])

        output = io.StringIO()
        with (
            patch.object(target, "ensure_exported_runtime"),
            patch.object(target, "collect_and_evaluate", side_effect=RuntimeError("SECRET")),
            redirect_stdout(output),
        ):
            self.assertEqual(target.main(["--pull-request", "10"]), 1)
        self.assertNotIn("SECRET", output.getvalue())
        self.assertEqual(json.loads(output.getvalue())["code"], "unexpected-local-error")

    @unittest.skipIf(os.name == "nt", "Symlink creation may require administrator privileges on Windows")
    def test_evaluator_loader_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            evaluator = root / "evaluator.py"
            evaluator.symlink_to(PACKAGE / "evaluator.py")
            self.fail_code("evaluator-source", target._git_blob_sha, evaluator)


if __name__ == "__main__":
    unittest.main(verbosity=2)
