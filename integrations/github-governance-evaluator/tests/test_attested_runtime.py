from __future__ import annotations

from contextlib import redirect_stdout
import copy
from dataclasses import dataclass
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

PACKAGE = Path(__file__).resolve().parents[1]


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


target = load_module(PACKAGE / "attested_runtime.py", "codex_attested_runtime_tests")
BASE, HEAD, REVISION = "1" * 40, "2" * 40, "3" * 40
TREES = ("4" * 40, "5" * 40, "6" * 40)


def candidate(paths=None):
    return {"repository": target.REPOSITORY, "pull_request": 22,
            "base_sha": BASE, "head_sha": HEAD,
            "changed_files": ["governance/scm/enforcement-policy.yaml"] if paths is None else paths}


def record(bound=None):
    return {"contract_version": 1, "kind": "codex-privileged-validation-attestation",
            "candidate": candidate() if bound is None else copy.deepcopy(bound),
            "decision": "pass", "scope": "protected-governance-maintenance",
            "authority": {"repository": target.AUTHORITY_REPOSITORY,
                          "default_branch": "main", "mode": "privileged-explicit"},
            "claims": {"candidate_code_executed": False, "credentials_used": False,
                       "exact_candidate_binding": True}}


class FakeAuthority:
    def __init__(self, bound=None, raw=None):
        import base64
        raw = json.dumps(record(bound)).encode() if raw is None else raw
        self.raw = raw
        self.blob_sha = target._blob(raw)
        bound = candidate() if bound is None else bound
        self.responses = {
            target.AUTHORITY_REF: {"ref": "refs/heads/main", "object": {"type": "commit", "sha": REVISION}},
            f"{target.AUTHORITY_API}/commits/{REVISION}": {"sha": REVISION, "tree": {"sha": TREES[0]}},
            f"{target.AUTHORITY_API}/blobs/{self.blob_sha}": {"sha": self.blob_sha, "size": len(raw),
                         "encoding": "base64", "content": base64.b64encode(raw).decode() + "\n"},
        }
        for index, name in enumerate(("governance", "privileged-validations", f"{bound['head_sha']}.json")):
            entry = {"path": name, "mode": "100644" if index == 2 else "040000",
                     "type": "blob" if index == 2 else "tree",
                     "sha": self.blob_sha if index == 2 else TREES[index + 1]}
            if index == 2:
                entry["size"] = len(raw)
            self.responses[f"{target.AUTHORITY_API}/trees/{TREES[index]}"] = {
                "sha": TREES[index], "truncated": False, "tree": [entry]}
        self.calls = []

    def __call__(self, path):
        self.calls.append(path)
        return copy.deepcopy(self.responses[path])

    def tree(self, index=2):
        return self.responses[f"{target.AUTHORITY_API}/trees/{TREES[index]}"]

    def blob(self):
        return self.responses[f"{target.AUTHORITY_API}/blobs/{self.blob_sha}"]


class UnitReaderTests(unittest.TestCase):
    def assert_rejected(self, fn, *args):
        with self.assertRaises(target.AttestedRuntimeError):
            fn(*args)

    def test_exact_committed_record_has_complete_evidence(self):
        api = FakeAuthority()
        result = target.collect_attestation(candidate(), api)
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["record"], record())
        self.assertEqual(result["authority_revision"], REVISION)
        self.assertEqual(result["tree_chain"], list(TREES))
        self.assertEqual(result["blob_sha"], api.blob_sha)
        self.assertEqual(len(result["raw_sha256"]), 64)
        self.assertEqual(len(result["attestation_digest"]), 64)
        self.assertEqual(len(api.calls), 6)
        self.assertEqual(api.calls.count(target.AUTHORITY_REF), 1)

    def test_main_movement_does_not_mix_snapshots(self):
        api = FakeAuthority()
        def moving(path):
            result = api(path)
            api.responses[target.AUTHORITY_REF]["object"]["sha"] = "f" * 40
            return result
        result = target.collect_attestation(candidate(), moving)
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["authority_revision"], REVISION)
        self.assertEqual(api.calls.count(target.AUTHORITY_REF), 1)

    def test_missing_entry_in_complete_tree_is_not_approval(self):
        for index in range(3):
            with self.subTest(index=index):
                api = FakeAuthority()
                api.tree(index)["tree"] = []
                result = target.collect_attestation(candidate(), api)
                self.assertEqual(result["status"], "missing")
                self.assertIsNone(result["record"])
                self.assertIsNone(result["blob_sha"])

    def test_symlink_submodule_and_executable_attestation_rejected(self):
        for index in range(3):
            for mode, kind in (("120000", "blob"), ("160000", "commit"), ("100755", "blob")):
                with self.subTest(index=index, mode=mode):
                    api = FakeAuthority()
                    api.tree(index)["tree"][0].update(mode=mode, type=kind)
                    self.assert_rejected(target.collect_attestation, candidate(), api)

    def test_truncated_or_ambiguous_tree_rejected(self):
        for key, value in (("truncated", True), ("truncated", 0), ("sha", "f" * 40), ("tree", None)):
            api = FakeAuthority()
            api.tree()[key] = value
            self.assert_rejected(target.collect_attestation, candidate(), api)
        api = FakeAuthority()
        api.tree()["tree"] *= 2
        self.assert_rejected(target.collect_attestation, candidate(), api)
        api = FakeAuthority()
        api.tree()["tree"][0]["path"] = "dir/record.json"
        self.assert_rejected(target.collect_attestation, candidate(), api)

    def test_wrong_ref_commit_and_object_types_rejected(self):
        for update in ({"ref": "refs/heads/other"}, {"object": {"type": "tag", "sha": REVISION}},
                       {"object": {"type": "commit", "sha": "0" * 40}}):
            api = FakeAuthority()
            api.responses[target.AUTHORITY_REF].update(update)
            self.assert_rejected(target.collect_attestation, candidate(), api)
        api = FakeAuthority()
        api.responses[f"{target.AUTHORITY_API}/commits/{REVISION}"]["sha"] = "a" * 40
        self.assert_rejected(target.collect_attestation, candidate(), api)

    def test_blob_metadata_encoding_and_bytes_must_agree(self):
        for key, value in (("sha", "f" * 40), ("encoding", "utf-8"), ("size", True),
                           ("size", target.MAX_ATTESTATION_BYTES + 1), ("content", "%%%"),
                           ("content", "e30="), ("content", None)):
            with self.subTest(key=key, value=value):
                api = FakeAuthority()
                api.blob()[key] = value
                self.assert_rejected(target.collect_attestation, candidate(), api)
        api = FakeAuthority()
        api.tree()["tree"][0]["size"] += 1
        self.assert_rejected(target.collect_attestation, candidate(), api)

    def test_attestation_identity_mismatches_rejected(self):
        for key, value in (("repository", "other/repo"), ("pull_request", 23),
                           ("pull_request", True), ("base_sha", "7" * 40),
                           ("head_sha", "8" * 40), ("changed_files", ["README.md"])):
            with self.subTest(key=key):
                data = record()
                data["candidate"][key] = value
                self.assert_rejected(target.validate_attestation, json.dumps(data).encode(), candidate())

    def test_claim_flags_are_booleans_not_integer_aliases(self):
        for key in record()["claims"]:
            for value in (0, 1, "false", None):
                data = record()
                data["claims"][key] = value
                self.assert_rejected(target.validate_attestation, json.dumps(data).encode(), candidate())

    def test_scope_authority_version_and_extra_fields_rejected(self):
        for key, value in (("contract_version", True), ("contract_version", 2), ("kind", "other"),
                           ("scope", "all"), ("decision", "fail"), ("unexpected", True),
                           ("authority", {"repository": target.REPOSITORY, "default_branch": "main", "mode": "privileged-explicit"})):
            data = record()
            data[key] = value
            self.assert_rejected(target.validate_attestation, json.dumps(data).encode(), candidate())

    def test_paths_are_complete_sorted_unique_and_valid(self):
        for paths in ([], ["z", "a"], ["a", "a"], ["../x"], ["/x"], ["a\\b"],
                      ["a//b"], ["a/./b"], ["a\x00b"], ["a\ud800b"], [True]):
            with self.subTest(paths=paths):
                self.assert_rejected(target.collect_attestation, candidate(paths), FakeAuthority())

    def test_rename_previous_path_cannot_be_omitted(self):
        bound = candidate([".github/workflows/old.yml", "docs/new.md"])
        data = record(bound)
        data["candidate"]["changed_files"] = ["docs/new.md"]
        self.assert_rejected(target.validate_attestation, json.dumps(data).encode(), bound)

    def test_duplicate_keys_nan_invalid_utf8_and_oversize_rejected(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}', b'\xff',
                    b'[]', b'', b' ' * (target.MAX_ATTESTATION_BYTES + 1)):
            self.assert_rejected(target.validate_attestation, raw, candidate())
        raw = json.dumps(record()).replace('"decision": "pass"', '"decision": "fail", "decision": "pass"').encode()
        self.assert_rejected(target.validate_attestation, raw, candidate())


class UnitTransportTests(unittest.TestCase):
    def test_rejects_paths_before_network(self):
        with patch.object(target, "build_opener") as factory:
            for path in ("https://evil.test/", "/repos/other/repo/git/ref/heads/main",
                         target.AUTHORITY_REF + "?ref=main", target.AUTHORITY_API + "/refs/heads/main",
                         target.AUTHORITY_API + "/blobs/" + "0" * 40, None):
                with self.subTest(path=path), self.assertRaises(target.AttestedRuntimeError):
                    target.authority_get(path)
            factory.assert_not_called()

    def test_fixed_https_get_no_credentials_proxy_redirect_or_retry(self):
        response = io.BytesIO(b'{"ok":true}')
        response.status = 200
        with patch.object(target, "build_opener") as factory:
            factory.return_value.open.return_value = response
            self.assertEqual(target.authority_get(target.AUTHORITY_REF), {"ok": True})
            request = factory.return_value.open.call_args.args[0]
            self.assertEqual(request.full_url, target.API_ROOT + target.AUTHORITY_REF)
            self.assertEqual(request.get_method(), "GET")
            self.assertIsNone(request.get_header("Authorization"))
            self.assertEqual(factory.call_args.args[0].proxies, {})
            self.assertIsInstance(factory.call_args.args[1], target.NoRedirect)
            self.assertEqual(factory.return_value.open.call_args.kwargs["timeout"], 10)
            self.assertIsNone(target.NoRedirect().redirect_request(None, None, 302, "", {}, "https://evil.test"))

    def test_errors_are_not_misreported_as_missing_approval(self):
        for error in (HTTPError("https://api.github.com/x", 404, "SECRET", {}, io.BytesIO(b"SECRET")),
                      HTTPError("https://api.github.com/x", 403, "SECRET", {}, io.BytesIO(b"SECRET")),
                      HTTPError("https://api.github.com/x", 302, "SECRET", {}, io.BytesIO(b"SECRET")),
                      URLError("SECRET"), TimeoutError("SECRET")):
            with patch.object(target, "build_opener") as factory:
                factory.return_value.open.side_effect = error
                with self.assertRaises(target.AttestedRuntimeError) as caught:
                    target.authority_get(target.AUTHORITY_REF)
                self.assertNotIn("SECRET", str(caught.exception))
                factory.return_value.open.assert_called_once()

    def test_response_status_size_and_json_rejected(self):
        for raw, status in ((b'{}', 202), (b'{', 200), (b'x' * (target.MAX_RESPONSE_BYTES + 1), 200),
                            (b'{"sha":"a","sha":"b"}', 200)):
            response = io.BytesIO(raw)
            response.status = status
            with patch.object(target, "build_opener") as factory:
                factory.return_value.open.return_value = response
                with self.assertRaises(target.AttestedRuntimeError):
                    target.authority_get(target.AUTHORITY_REF)


class UnitLoaderTests(unittest.TestCase):
    def test_dependency_bytes_and_regular_file_requirement(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "source.py"
            raw = b'value = 1\n'
            path.write_bytes(raw)
            self.assertEqual(target._read_dependency(path, target._blob(raw)), raw)
            with self.assertRaises(target.AttestedRuntimeError):
                target._read_dependency(path, "a" * 40)
            link = Path(temp) / "link.py"
            link.symlink_to(path)
            with self.assertRaises(target.AttestedRuntimeError):
                target._read_dependency(link, target._blob(raw))
            with self.assertRaises(target.AttestedRuntimeError):
                target._read_dependency(Path(temp) / "missing", "a" * 40)

    def test_compiles_verified_bytes_instead_of_reading_path_again(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "module.py"
            path.write_text('raise RuntimeError("wrong source")\n')
            result = target._module(b'value = 42\n', path, "_attested_test_raw_module")
            self.assertEqual(result.value, 42)
            sys.modules.pop(result.__name__, None)

    def test_module_failure_is_sanitized(self):
        with self.assertRaises(target.AttestedRuntimeError) as caught:
            target._module(b'raise RuntimeError("SECRET")', Path("test.py"), "_attested_test_failed_module")
        self.assertNotIn("SECRET", str(caught.exception))
        self.assertNotIn("_attested_test_failed_module", sys.modules)

    def test_all_dependencies_verified_before_execution(self):
        with patch.object(target, "_read_dependency", side_effect=target.AttestedRuntimeError("test", "blocked")), patch.object(target, "_module") as loader:
            with self.assertRaises(target.AttestedRuntimeError):
                target.load_dependencies()
            loader.assert_not_called()

    def test_cli_rejects_checkout_before_collection(self):
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".git").mkdir()
            with patch.object(target, "__file__", str(root / "attested_runtime.py")), patch.object(target, "collect_and_evaluate") as collect, redirect_stdout(output):
                self.assertEqual(target.main(["--pull-request", "22"]), 1)
                collect.assert_not_called()
        self.assertEqual(json.loads(output.getvalue())["code"], "runtime-checkout")


@dataclass(frozen=True)
class Manifest:
    repository: str
    pull_request: int
    base_sha: str
    head_sha: str
    changed_files: tuple[str, ...]


class UnitOrchestrationTests(unittest.TestCase):
    """Mock only the already-pinned dependency boundary, not attestation validation."""
    def run_case(self, paths, qualification="pass", authority=None, drift=False, unknown=False, qualification_drift=False):
        from types import SimpleNamespace
        bound = candidate(paths)
        manifest = Manifest(target.REPOSITORY, 22, BASE, HEAD, tuple(paths))
        calls = [0]
        def collect(*args):
            calls[0] += 1
            latest = Manifest(target.REPOSITORY, 22, "9" * 40, HEAD, tuple(paths)) if drift and calls[0] > 1 else manifest
            return latest, {"identity_verified": True, "changed_files_verified": True, "pull_state": "open"}
        def protected(path):
            return path.startswith("governance/")
        def evaluate(observed, facts, revision):
            failures = ["candidate-qualification-failed"] if qualification != "pass" else []
            if any(protected(p) for p in paths) and facts[-1] != "pass":
                failures.append("privileged-validation-missing")
            if unknown:
                failures.append("unknown-blocker")
            return {"failure_reasons": failures, "governance_decision": "fail" if failures else "pass"}
        def qualify(*args):
            return qualification, {"check_run_id": 2 if qualification_drift and calls[0] > 1 else 1}
        collector = SimpleNamespace(api_get=None, collect_candidate=collect,
                    collect_candidate_qualification=qualify, is_runtime_critical=lambda p: p.startswith("integrations/"))
        evaluator = SimpleNamespace(is_protected=protected, EvaluationFacts=lambda *args: args, evaluate=evaluate)
        api = FakeAuthority(bound) if authority is None else authority
        with patch.object(target, "load_dependencies", return_value=(collector, evaluator)):
            return target.collect_and_evaluate(22, lambda *a: None, api), api

    def test_protected_attestation_preserves_original_failure(self):
        result, _ = self.run_case(candidate()["changed_files"])
        self.assertEqual(result["governance_decision"], "pass")
        self.assertEqual(result["original_evaluation"]["governance_decision"], "fail")
        self.assertEqual(result["original_evaluation"]["evaluator_result"]["failure_reasons"], ["privileged-validation-missing"])
        self.assertEqual(result["privileged_validation_evidence"]["status"], "verified")
        self.assertEqual(result["schema_version"], 2)
        self.assertFalse(result["publish_enabled"])
        self.assertFalse(result["runtime_source_promoted"])
        self.assertFalse(result["effective_enforcement_proven"])

    def test_runtime_only_and_mixed_paths_can_satisfy_privilege(self):
        for paths in (["integrations/github-governance-evaluator/attested_runtime.py"],
                      ["governance/scm/enforcement-policy.yaml", "integrations/github-governance-evaluator/attested_runtime.py"]):
            result, _ = self.run_case(paths)
            self.assertEqual(result["governance_decision"], "pass")
            self.assertEqual(result["runtime_failure_reasons"], [])
            self.assertEqual(result["original_evaluation"]["governance_decision"], "fail")

    def test_missing_approval_preserves_privilege_failures(self):
        api = FakeAuthority()
        api.tree()["tree"] = []
        result, _ = self.run_case(candidate()["changed_files"], authority=api)
        self.assertEqual(result["governance_decision"], "fail")
        self.assertEqual(result["failure_reasons"], ["privileged-validation-missing"])

    def test_failed_qualification_and_unknown_failure_not_overridden(self):
        for options in ({"qualification": "fail"}, {"unknown": True}):
            result, api = self.run_case(candidate()["changed_files"], **options)
            self.assertEqual(result["governance_decision"], "fail")
            self.assertEqual(api.calls, [])

    def test_unprotected_candidate_does_not_read_authority(self):
        result, api = self.run_case(["README.md"])
        self.assertEqual(result["governance_decision"], "pass")
        self.assertEqual(api.calls, [])

    def test_candidate_and_qualification_drift_rejected(self):
        for options in ({"drift": True}, {"qualification_drift": True}):
            with self.assertRaises(target.AttestedRuntimeError):
                self.run_case(candidate()["changed_files"], **options)

    def test_wrong_attestation_and_transport_error_block(self):
        wrong = FakeAuthority(candidate(["README.md"]))
        with self.assertRaises(target.AttestedRuntimeError):
            self.run_case(candidate()["changed_files"], authority=wrong)
        def failed(path):
            raise target.AttestedRuntimeError("network", "failed")
        with self.assertRaises(target.AttestedRuntimeError):
            self.run_case(candidate()["changed_files"], authority=failed)


class LegacyIntegrationTests(unittest.TestCase):
    """Runs against the actual repository's pinned collector/evaluator in CI."""
    def setUp(self):
        self.fixtures = load_module(PACKAGE / "tests/test_runtime.py", "_attested_existing_runtime_tests")
        self.api = self.fixtures.FakeGitHub()

    def run_real(self, paths, qualification="success", authority=None):
        self.api.pr["changed_files"] = len(paths)
        self.api.file_pages[1] = [{"filename": p, "status": "modified"} for p in paths]
        self.api.qualification["check_runs"][0]["conclusion"] = qualification
        bound = {"repository": target.REPOSITORY, "pull_request": self.api.pr_number,
                 "base_sha": self.api.base_sha, "head_sha": self.api.head_sha, "changed_files": sorted(paths)}
        authority = FakeAuthority(bound) if authority is None else authority
        return target.collect_and_evaluate(self.api.pr_number, self.api, authority), authority

    def test_actual_pinned_dependencies_load(self):
        collector, evaluator = target.load_dependencies()
        self.assertEqual(collector.PINNED_AUTHORITY_REVISION, target.EVALUATOR_REVISION)
        self.assertEqual(evaluator.REPOSITORY, target.REPOSITORY)

    def test_actual_evaluator_and_runtime_only_protection(self):
        for paths in (["governance/scm/enforcement-policy.yaml"], ["integrations/github-governance-evaluator/attested_runtime.py"],
                      ["governance/scm/enforcement-policy.yaml", "integrations/github-governance-evaluator/attested_runtime.py"]):
            with self.subTest(paths=paths):
                result, _ = self.run_real(paths)
                self.assertEqual(result["governance_decision"], "pass")
                self.assertEqual(result["original_evaluation"]["governance_decision"], "fail")
                self.assertEqual(result["privileged_validation_evidence"]["status"], "verified")

    def test_real_qualification_failure_never_uses_attestation(self):
        result, authority = self.run_real(["governance/scm/enforcement-policy.yaml"], "failure")
        self.assertEqual(result["governance_decision"], "fail")
        self.assertIn("candidate-qualification-failed", result["failure_reasons"])
        self.assertEqual(authority.calls, [])

    def test_actual_unprotected_candidate_unchanged(self):
        result, authority = self.run_real(["README.md"])
        self.assertEqual(result["governance_decision"], "pass")
        self.assertEqual(authority.calls, [])

    def test_wrong_qualification_source_fails_before_attestation(self):
        self.api.qualification["check_runs"][0]["app"]["id"] = 999
        with self.assertRaises(Exception) as caught:
            self.run_real(["governance/scm/enforcement-policy.yaml"])
        self.assertEqual(getattr(caught.exception, "code", None), "qualification-source")


if __name__ == "__main__":
    unittest.main()
