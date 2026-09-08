"""Offline tests. All RSA keys are ephemeral fixtures; API calls are mocked."""
from __future__ import annotations

from contextlib import redirect_stdout
import copy
import io
import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from http.client import HTTPException
from types import SimpleNamespace
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec

PACKAGE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("github_app_preflight", PACKAGE / "github_app_preflight.py")
target = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = target
spec.loader.exec_module(target)


class HelperFixture:
    @classmethod
    def setUpClass(cls):
        cls.rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.pem = cls.rsa_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption())

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.key = self.root / "test-key.pem"
        self.key.write_bytes(self.pem)
        self.key.chmod(0o600)
        self.config_file = self.root / "config.json"
        self.raw = json.loads((PACKAGE / "config.json").read_text())
        self.config_file.write_text(json.dumps(self.raw))
        self.config = target.Config.load(self.config_file)
        self.install = {"id": self.config.installation_id, "app_id": self.config.app_id, "account": {"login": "scnehaux"}, "permissions": dict(target.REQUIRED_PERMISSIONS), "suspended_at": None, "repository_selection": "selected"}
        self.calls = []
        guard = patch.object(target, "build_opener", side_effect=AssertionError("Live HTTP is forbidden in offline tests"))
        guard.start()
        self.addCleanup(guard.stop)
        runtime = patch.object(target, "__file__", str(self.root / "trusted-kit" / "github_app_preflight.py"))
        runtime.start()
        self.addCleanup(runtime.stop)

    def fail_code(self, code, fn, *args, **kwargs):
        with self.assertRaises(target.PreflightError) as result:
            fn(*args, **kwargs)
        self.assertEqual(result.exception.code, code)

    def reader(self, path, token):
        self.calls.append((path, token))
        if path == "/app":
            return {"id": self.config.app_id}
        return copy.deepcopy(self.install)

class PreflightTests(HelperFixture, unittest.TestCase):
    def test_config_defaults_match_supplied_public_ids(self):
        self.assertEqual(self.config.app_id, 4864946)
        self.assertEqual(self.config.installation_id, 159870521)
        self.assertEqual(self.config.client_id, "Iv23li8znPY4yr7chvFD")
        self.assertEqual(self.config.repository, "scnehaux/codex")

    def test_config_ids_are_strictly_positive_ints(self):
        for field in ("app_id", "installation_id"):
            for value in (True, False, 0, -1, "4864946", 1.5, None, 2**63):
                with self.subTest(field=field, value=value):
                    data = dict(self.raw, **{field: value})
                    self.config_file.write_text(json.dumps(data))
                    self.fail_code("config-id", target.Config.load, self.config_file)

    def test_invalid_config_documents(self):
        for text in ("{", "[]", "null", "{}", '"text"'):
            with self.subTest(text=text):
                self.config_file.write_text(text)
                self.fail_code("config-invalid", target.Config.load, self.config_file)

    def test_config_missing_file(self):
        self.fail_code("config-invalid", target.Config.load, self.root / "missing.json")

    def test_config_rejects_secret_or_unknown_fields(self):
        self.raw["private_key"] = "NEVER-ECHO-THIS"
        self.config_file.write_text(json.dumps(self.raw))
        self.fail_code("config-invalid", target.Config.load, self.config_file)

    def test_config_schema_version(self):
        for version in (True, 2, "1", None):
            self.config_file.write_text(json.dumps(dict(self.raw, config_version=version)))
            self.fail_code("config-version", target.Config.load, self.config_file)

    def test_config_client_id_and_repository_validation(self):
        for client in ("", "\nsecret", 4864946, "a" * 129):
            self.config_file.write_text(json.dumps(dict(self.raw, client_id=client)))
            self.fail_code("config-client", target.Config.load, self.config_file)
        for repo in ("https://github.com/a/b", "a/../evil", "a/b?redirect=bad", "a/b\n", "a/.", "a/..", "../b", None):
            self.config_file.write_text(json.dumps(dict(self.raw, repository=repo)))
            self.fail_code("config-repository", target.Config.load, self.config_file)

    def test_real_rsa_signature_and_short_claim_lifetime(self):
        now = int(time.time())
        token = target.make_jwt(self.key, self.config.client_id)
        payload = jwt.decode(token, self.rsa_key.public_key(), algorithms=["RS256"])
        self.assertEqual(payload["iss"], self.config.client_id)
        self.assertLessEqual(payload["iat"], now)
        self.assertGreaterEqual(payload["iat"], now - 62)
        self.assertGreater(payload["exp"], now)
        self.assertLessEqual(payload["exp"], now + 302)
        self.assertEqual(jwt.get_unverified_header(token)["alg"], "RS256")

    def test_missing_and_invalid_key(self):
        self.fail_code("key-missing", target.make_jwt, self.root / "absent.pem", self.config.client_id)
        self.key.write_text("not a key, PRIVATE-SENTINEL")
        self.fail_code("key-invalid", target.make_jwt, self.key, self.config.client_id)

    def test_reject_empty_and_oversized_key(self):
        for data in (b"", b"x" * (target.KEY_MAX_BYTES + 1)):
            self.key.write_bytes(data)
            self.fail_code("key-size", target.make_jwt, self.key, self.config.client_id)

    def test_reject_non_rsa_key(self):
        key = ec.generate_private_key(ec.SECP256R1())
        self.key.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        self.fail_code("key-invalid", target.make_jwt, self.key, self.config.client_id)

    def test_reject_encrypted_key(self):
        self.key.write_bytes(self.rsa_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.BestAvailableEncryption(b"dummy-test-password")))
        self.fail_code("key-invalid", target.make_jwt, self.key, self.config.client_id)

    def test_reject_directory_key(self):
        self.fail_code("key-type", target.make_jwt, self.root, self.config.client_id)

    @unittest.skipIf(os.name == "nt", "POSIX permission semantics")
    def test_reject_world_readable_key(self):
        self.key.chmod(0o644)
        self.fail_code("key-permissions", target.make_jwt, self.key, self.config.client_id)

    @unittest.skipIf(os.name == "nt", "Symlink creation may need admin on Windows")
    def test_reject_symlink_key(self):
        link = self.root / "link.pem"
        link.symlink_to(self.key)
        self.fail_code("key-type", target.make_jwt, link, self.config.client_id)

    def test_reject_key_in_repository_or_git_worktree(self):
        for worktree in (False, True):
            git = self.root / ".git"
            if worktree:
                git.rmdir()
                git.write_text("gitdir: elsewhere")
            else:
                git.mkdir()
            self.fail_code("key-location", target.make_jwt, self.key, self.config.client_id)

    def test_reject_key_inside_setup_directory(self):
        with patch.object(target, "__file__", str(self.root / "github_app_preflight.py")):
            self.fail_code("key-location", target.make_jwt, self.key, self.config.client_id)

    def test_preflight_success_is_not_governance_success(self):
        result = target.preflight(self.config, "DUMMY-JWT", self.reader)
        self.assertEqual([item[0] for item in self.calls], ["/app", "/app/installations/159870521", "/repos/scnehaux/codex/installation"])
        self.assertEqual(result["status"], "connection_verified")
        for field in ("checks_write_tested", "governance_evaluated", "effective_enforcement_proven"):
            self.assertIs(result[field], False)
        self.assertEqual(result["remote_mutations"], 0)
        self.assertNotIn("DUMMY-JWT", json.dumps(result))

    def test_wrong_app_fails_before_installation_lookup(self):
        self.fail_code("app-mismatch", target.preflight, self.config, "dummy", lambda path, token: {"id": 123})

    def test_installation_identity_owner_status_and_scope(self):
        cases = [({"id": 123}, "installation-mismatch"), ({"id": True}, "installation-mismatch"), ({"app_id": 123}, "installation-app-mismatch"), ({"app_id": "4864946"}, "installation-app-mismatch"), ({"account": None}, "installation-owner"), ({"account": {"login": "someone-else"}}, "installation-owner"), ({"suspended_at": "2026-01-01"}, "installation-suspended"), ({"repository_selection": "all"}, "repository-selection")]
        for update, code in cases:
            with self.subTest(update=update):
                self.fail_code(code, target.verify_installation, dict(self.install, **update), self.config)
        del self.install["suspended_at"]
        self.fail_code("installation-suspended", target.verify_installation, self.install, self.config)

    def test_missing_inadequate_or_excessive_permissions(self):
        self.fail_code("permissions-missing", target.verify_permissions, None)
        for field, expected in target.REQUIRED_PERMISSIONS.items():
            for value in (None, "none", "write" if expected == "read" else "read"):
                with self.subTest(field=field, value=value):
                    data = dict(target.REQUIRED_PERMISSIONS, **{field: value})
                    self.fail_code("permissions-mismatch", target.verify_permissions, data)
        self.fail_code("permissions-excess", target.verify_permissions, dict(target.REQUIRED_PERMISSIONS, administration="write"))

    def test_repo_installation_mismatch_is_not_accepted(self):
        def read(path, token):
            if path == "/app":
                return {"id": self.config.app_id}
            if path.startswith("/repos/"):
                return dict(self.install, id=999)
            return self.install
        self.fail_code("installation-mismatch", target.preflight, self.config, "DUMMY-JWT", read)

    def test_https_get_only_request_and_timeout(self):
        response = io.BytesIO(b'{"id": 4864946}')
        response.status = 200
        with patch.object(target, "build_opener") as factory:
            factory.return_value.open.return_value = response
            self.assertEqual(target.get_json("/app", "DUMMY-JWT"), {"id": 4864946})
            args, kwargs = factory.return_value.open.call_args
            request = args[0]
            self.assertEqual(request.full_url, "https://api.github.com/app")
            self.assertEqual(request.get_method(), "GET")
            self.assertEqual(kwargs["timeout"], 20)
            self.assertIsNone(request.data)
            self.assertIsInstance(factory.call_args.args[0], target.NoRedirect)
            self.assertEqual(request.get_header("Authorization"), "Bearer DUMMY-JWT")

    def test_refuse_unexpected_path(self):
        for path in ("https://evil/app", "//evil/app", "/app\n", "/app?x=1", "/app#bad", "/app\\evil"):
            self.fail_code("api-path", target.get_json, path, "DUMMY-JWT")

    def test_redirect_handler_does_not_forward_credentials(self):
        handler = target.NoRedirect()
        self.assertIsNone(handler.redirect_request(None, None, 302, "", {}, "https://elsewhere.test/"))

    def test_http_errors_are_sanitized(self):
        for status in (301, 302, 307, 401, 403, 404, 422, 500):
            error = HTTPError("https://api.github.com/app", status, "SENSITIVE-UPSTREAM", {}, io.BytesIO(b"DO-NOT-PRINT-BODY"))
            with patch.object(target, "build_opener") as factory:
                factory.return_value.open.side_effect = error
                with self.assertRaises(target.PreflightError) as caught:
                    target.get_json("/app", "DUMMY-JWT")
                self.assertEqual(caught.exception.code, f"github-http-{status}")
                self.assertNotIn("SENSITIVE", str(caught.exception))
                self.assertNotIn("DO-NOT-PRINT", str(caught.exception))
                self.assertNotIn("DUMMY-JWT", str(caught.exception))

    def test_network_errors_are_sanitized(self):
        for error in (URLError("PRIVATE-INTERNAL"), TimeoutError("PRIVATE-INTERNAL"), OSError("PRIVATE-INTERNAL")):
            with patch.object(target, "build_opener") as factory:
                factory.return_value.open.side_effect = error
                self.fail_code("network-error", target.get_json, "/app", "DUMMY-JWT")

    def test_malformed_api_responses_fail_closed(self):
        cases = [(b"{", "api-json"), (b"\xff", "api-json"), (b"[]", "api-shape"), (b"null", "api-shape"), (b"x" * (target.MAX_RESPONSE_BYTES + 1), "api-response-size")]
        for body, code in cases:
            with self.subTest(code=code):
                response = io.BytesIO(body)
                response.status = 200
                with patch.object(target, "build_opener") as factory:
                    factory.return_value.open.return_value = response
                    self.fail_code(code, target.get_json, "/app", "DUMMY-JWT")

    def test_cli_json_and_text_do_not_render_token(self):
        report = target.preflight(self.config, "dummy", self.reader)
        for flags in ([], ["--json"]):
            output = io.StringIO()
            with patch.object(target, "make_jwt", return_value="DO-NOT-PRINT-TOKEN"), patch.object(target, "preflight", return_value=report), redirect_stdout(output):
                code = target.main(["--config", str(self.config_file), *flags])
            self.assertEqual(code, 0)
            self.assertNotIn("DO-NOT-PRINT", output.getvalue())
            if flags:
                self.assertFalse(json.loads(output.getvalue())["governance_evaluated"])
            else:
                self.assertIn("[NOT PROVEN]", output.getvalue())

    def test_cli_known_error_is_nonzero(self):
        output = io.StringIO()
        with patch.object(target, "make_jwt", side_effect=target.PreflightError("key-invalid", "Fixed safe error")), redirect_stdout(output):
            code = target.main(["--config", str(self.config_file), "--json"])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output.getvalue())["status"], "blocked")

    def test_cli_unknown_error_masks_sensitive_details(self):
        output = io.StringIO()
        with patch.object(target, "make_jwt", side_effect=RuntimeError("SECRET-TOKEN-OR-PEM")), redirect_stdout(output):
            code = target.main(["--config", str(self.config_file)])
        self.assertEqual(code, 1)
        self.assertNotIn("SECRET", output.getvalue())


    def test_config_size_limit(self):
        self.config_file.write_bytes(b" " * 8193)
        self.fail_code("config-invalid", target.Config.load, self.config_file)

    def test_default_key_paths(self):
        with patch.object(target, "os", SimpleNamespace(name="nt", environ={"LOCALAPPDATA": str(self.root)})):
            self.assertEqual(target.default_key_path(), self.root / "scnehaux-codex-authority/secrets/github-app.pem")
        with patch.object(target, "os", SimpleNamespace(name="posix")), patch.object(target.Path, "home", return_value=self.root):
            self.assertEqual(target.default_key_path(), self.root / ".local/share/scnehaux-codex-authority/secrets/github-app.pem")

    def test_key_read_error_and_missing_dependencies(self):
        with patch.object(type(self.key), "open", side_effect=PermissionError("SECRET")):
            self.fail_code("key-unreadable", target.make_jwt, self.key, self.config.client_id)
        with patch.dict(sys.modules, {"jwt": None}):
            self.fail_code("dependencies-missing", target.make_jwt, self.key, self.config.client_id)
        with patch.object(jwt, "encode", return_value=b"bad-token"):
            self.fail_code("key-invalid", target.make_jwt, self.key, self.config.client_id)

    @unittest.skipIf(os.name == "nt", "POSIX ownership semantics")
    def test_key_owned_by_another_user(self):
        with patch.object(target.os, "getuid", return_value=os.getuid() + 1):
            self.fail_code("key-permissions", target.make_jwt, self.key, self.config.client_id)

    def test_extra_permissions_none_is_allowed(self):
        target.verify_permissions(dict(target.REQUIRED_PERMISSIONS, administration="none"))

    def test_unexpected_http_status(self):
        response = io.BytesIO(b'{}')
        response.status = 202
        with patch.object(target, "build_opener") as factory:
            factory.return_value.open.return_value = response
            self.fail_code("api-status", target.get_json, "/app", "dummy")

    def test_http_protocol_errors_are_sanitized(self):
        with patch.object(target, "build_opener") as factory:
            factory.return_value.open.side_effect = HTTPException("SECRET")
            self.fail_code("network-error", target.get_json, "/app", "dummy")

    def test_transport_rejects_path_traversal_and_other_writes(self):
        for path in ("/app/../evil", "/app/./evil", "/app//evil", "/app/%2e", "/app/colon:bad", None):
            self.fail_code("api-path", target.get_json, path, "dummy")
        for method, path in (("PATCH", "/repos/scnehaux/codex/check-runs/1"), ("POST", "/repos/scnehaux/codex/git/refs"), ("DELETE", "/repos/scnehaux/codex")):
            self.fail_code("api-method", target.request_json, path, "dummy", method=method)
        self.fail_code("api-body", target.request_json, "/app", "dummy", body={})
        self.fail_code("probe-payload", target.request_json, "/repos/scnehaux/codex/check-runs", "dummy", method="POST", body={"name": "Codex Governance Authority", "conclusion": "success"})

    def test_post_and_delete_transport(self):
        for path, method, status, raw, body in (
            ("/app/installations/1/access_tokens", "POST", 201, b'{"token":"dummy"}', {"repositories": ["codex"]}),
            ("/repos/scnehaux/codex/check-runs", "POST", 201, b'{"id":1}', {"name": target.PROBE_NAME, "conclusion": "neutral"}),
            ("/installation/token", "DELETE", 204, b"", None),
        ):
            response = io.BytesIO(raw)
            response.status = status
            with patch.object(target, "build_opener") as factory:
                factory.return_value.open.return_value = response
                result = target.request_json(path, "SECRET", method=method, body=body)
                req = factory.return_value.open.call_args.args[0]
                self.assertEqual(req.get_method(), method)
                self.assertEqual(req.full_url, target.API_ROOT + path)
                self.assertEqual(req.data, json.dumps(body).encode() if body is not None else None)
                self.assertNotIn("SECRET", json.dumps(result))

    def test_cli_interrupt_and_plain_known_error(self):
        for error, code in ((KeyboardInterrupt(), 130), (target.PreflightError("example", "Safe fixed error"), 1)):
            with patch.object(target, "make_jwt", side_effect=error), redirect_stdout(io.StringIO()):
                self.assertEqual(target.main(["--config", str(self.config_file)]), code)

    def test_cli_requires_exported_runtime_for_credentials(self):
        (self.root / ".git").mkdir()
        output = io.StringIO()
        with patch.object(target, "make_jwt") as make, redirect_stdout(output):
            self.assertEqual(target.main(["--config", str(self.config_file)]), 1)
            make.assert_not_called()
        self.assertIn("runtime-checkout", output.getvalue())


class ProbeTests(HelperFixture, unittest.TestCase):
    """Connectivity transport tests share fixtures, not duplicated test cases."""

    def setUp(self):
        super().setUp()
        self.sha = "a" * 40
        self.issued = {
            "token": "ghs_SYNTHETIC_TEST_TOKEN",
            "permissions": dict(target.TOKEN_PERMISSIONS),
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=59)).isoformat(),
        }
        self.listing = {"total_count": 1, "repositories": [{"full_name": "scnehaux/codex"}]}
        self.commit = {"sha": self.sha}
        self.check = {"id": 42, "app": {"id": self.config.app_id}, "head_sha": self.sha, "name": target.PROBE_NAME, "status": "completed", "conclusion": "neutral", "external_id": "codex-connectivity/" + self.sha}
        self.readback = copy.deepcopy(self.check)
        self.api_calls = []
        self.fail_at = None

    def request(self, path, token, *, method="GET", body=None):
        self.api_calls.append((method, path, token, copy.deepcopy(body)))
        if path == self.fail_at:
            raise target.PreflightError("simulated", "Fixed error without upstream data")
        if path == "/app":
            return {"id": self.config.app_id}
        if path.endswith("/access_tokens"):
            return copy.deepcopy(self.issued)
        if path == "/installation/repositories":
            return copy.deepcopy(self.listing)
        if "/commits/" in path:
            return copy.deepcopy(self.commit)
        if path.endswith("/check-runs"):
            return copy.deepcopy(self.check)
        if "/check-runs/" in path:
            return copy.deepcopy(self.readback)
        if path == "/installation/token":
            return {}
        return copy.deepcopy(self.install)

    def run_probe(self):
        return target.run_probe(self.config, "SYNTHETIC-APP-JWT", self.sha, self.request)

    def test_probe_preview_is_offline_and_requires_exact_sha(self):
        plan = target.probe_plan(self.config, self.sha)
        self.assertEqual(plan["status"], "preview_only")
        self.assertEqual(plan["name"], "Codex App Connectivity Probe")
        self.assertFalse(plan["governance_evaluated"])
        self.assertEqual(plan["remote_mutations"], 0)
        for sha in (None, "main", "a" * 39, "b" * 41, "A" * 40, "0" * 40, "b" * 40 + "\n", "refs/heads/main"):
            self.fail_code("probe-sha", target.probe_plan, self.config, sha)

    def test_cli_preview_never_reads_credentials_or_calls_api(self):
        output = io.StringIO()
        with patch.object(target, "make_jwt") as make, patch.object(target, "request_json") as request, redirect_stdout(output):
            code = target.main(["--config", str(self.config_file), "--probe-sha", self.sha])
            make.assert_not_called()
            request.assert_not_called()
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "preview_only")

    def test_missing_or_incorrect_write_confirmations_are_credential_free(self):
        cases = (
            ["--write"],
            ["--confirm-sha", self.sha],
            ["--probe-sha", self.sha, "--write"],
            ["--probe-sha", self.sha, "--write", "--confirm-sha", "b" * 40, "--confirm-repository", "scnehaux/codex"],
            ["--probe-sha", self.sha, "--write", "--confirm-sha", self.sha, "--confirm-repository", "other/repo"],
        )
        for flags in cases:
            with patch.object(target, "make_jwt") as make, redirect_stdout(io.StringIO()):
                self.assertEqual(target.main(["--config", str(self.config_file), *flags]), 1)
                make.assert_not_called()

    def test_probe_success_exact_scope_readback_and_revocation(self):
        report = self.run_probe()
        self.assertEqual(report["status"], "connectivity_verified")
        self.assertEqual(report["check_run_id"], 42)
        self.assertTrue(report["installation_token_revoked"])
        self.assertFalse(report["governance_evaluated"])
        self.assertFalse(report["effective_enforcement_proven"])
        self.assertNotIn(self.issued["token"], json.dumps(report))
        mutations = [(m, p, b) for m, p, _, b in self.api_calls if m != "GET"]
        self.assertEqual(len(mutations), 3)
        self.assertEqual(mutations[0][2], {"repositories": ["codex"], "permissions": {"contents": "read", "checks": "write"}})
        self.assertEqual(mutations[1][2]["name"], target.PROBE_NAME)
        self.assertEqual(mutations[1][2]["head_sha"], self.sha)
        self.assertEqual(mutations[1][2]["conclusion"], "neutral")
        self.assertEqual(mutations[2][:2], ("DELETE", "/installation/token"))
        self.assertEqual(sum(m == "POST" and p.endswith("/check-runs") for m, p, _, _ in self.api_calls), 1)

    def test_preflight_failure_never_mints_token(self):
        self.install["app_id"] = 1
        self.fail_code("installation-app-mismatch", self.run_probe)
        self.assertTrue(all(c[0] == "GET" for c in self.api_calls))

    def test_missing_or_invalid_token_does_not_post_check(self):
        for value in (None, "", 2, "SECRET\nTOKEN", "SECRET\x00TOKEN", "SECRÉT"):
            self.issued["token"] = value
            self.api_calls.clear()
            self.fail_code("token-invalid", self.run_probe)
            self.assertFalse(any("check-runs" in c[1] for c in self.api_calls))

    def test_excess_token_permissions_revoke_and_stop(self):
        self.issued["permissions"]["contents"] = "write"
        self.fail_code("token-permissions", self.run_probe)
        self.assertEqual(self.api_calls[-1][0:2], ("DELETE", "/installation/token"))
        self.assertFalse(any("check-runs" in c[1] for c in self.api_calls))

    def test_invalid_token_expiry_revoke_and_stop(self):
        for expiry in (None, 123, "bad", "2000-01-01T00:00:00Z", "2999-01-01T00:00:00Z", "2026-09-08T00:00:00"):
            self.issued["expires_at"] = expiry
            self.fail_code("token-expiry", self.run_probe)
            self.assertEqual(self.api_calls[-1][0:2], ("DELETE", "/installation/token"))
        del self.issued["expires_at"]
        self.fail_code("token-expiry", self.run_probe)

    def test_token_must_have_exactly_one_target_repository(self):
        for listing in ({}, {"total_count": True}, {"total_count": 2, "repositories": []}, {"total_count": 1, "repositories": [None]}, {"total_count": 1, "repositories": [{"full_name": "other/repo"}]}):
            self.listing = listing
            self.fail_code("token-repositories", self.run_probe)
            self.assertEqual(self.api_calls[-1][0:2], ("DELETE", "/installation/token"))

    def test_wrong_commit_cannot_receive_probe(self):
        self.commit["sha"] = "b" * 40
        self.fail_code("commit-mismatch", self.run_probe)
        self.assertFalse(any("check-runs" in c[1] for c in self.api_calls))
        self.assertEqual(self.api_calls[-1][0:2], ("DELETE", "/installation/token"))

    def test_failures_after_issuance_always_revoke_no_retries(self):
        for path in ("/installation/repositories", f"/repos/scnehaux/codex/commits/{self.sha}", "/repos/scnehaux/codex/check-runs", "/repos/scnehaux/codex/check-runs/42"):
            self.fail_at = path
            self.api_calls.clear()
            self.fail_code("simulated", self.run_probe)
            self.assertEqual(self.api_calls[-1][0:2], ("DELETE", "/installation/token"))
            self.assertEqual(sum(c[1] == path for c in self.api_calls), 1)

    def test_check_fields_are_not_trusted_without_validation(self):
        for field, value in (("id", True), ("id", 0), ("app", None), ("app", {"id": 999}), ("head_sha", "b" * 40), ("name", "Codex Governance Authority"), ("status", "in_progress"), ("conclusion", "success"), ("external_id", "different")):
            self.fail_code("check-mismatch", target.verify_check, dict(self.check, **{field: value}), self.config, self.sha)
        self.readback["id"] = 43
        self.fail_code("check-id-mismatch", self.run_probe)
        self.assertEqual(self.api_calls[-1][0:2], ("DELETE", "/installation/token"))

    def test_revocation_failure_is_not_success(self):
        self.fail_at = "/installation/token"
        self.fail_code("token-revocation-failed", self.run_probe)

    def test_cli_write_output_and_failure_never_print_secrets(self):
        flags = ["--config", str(self.config_file), "--probe-sha", self.sha, "--write", "--confirm-repository", self.config.repository, "--confirm-sha", self.sha]
        output = io.StringIO()
        with patch.object(target, "make_jwt", return_value="SECRET-JWT"), patch.object(target, "request_json", side_effect=self.request), redirect_stdout(output):
            self.assertEqual(target.main(flags), 0)
        self.assertEqual(json.loads(output.getvalue())["check_run_id"], 42)
        self.assertNotIn("SECRET", output.getvalue())
        self.fail_at = "/repos/scnehaux/codex/check-runs"
        for json_flag in ([], ["--json"]):
            output = io.StringIO()
            with patch.object(target, "make_jwt", return_value="SECRET-JWT"), patch.object(target, "request_json", side_effect=self.request), redirect_stdout(output):
                self.assertEqual(target.main(flags + json_flag), 1)
            self.assertIn("retries", output.getvalue())
            self.assertNotIn("SECRET", output.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
