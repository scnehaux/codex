#!/usr/bin/env python3
"""Local GitHub App preflight and opt-in connectivity probe, NOT an evaluator.

Default: GET-only authentication preflight. --probe-sha alone: offline preview.
Only --write with matching repository/SHA confirmations can mint a scoped token
and publish the fixed, non-required connectivity check. No candidate code runs.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from http.client import HTTPException
import json
import os
from pathlib import Path
import re
import stat
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

API_ROOT = "https://api.github.com"
API_VERSION = "2026-03-10"
MAX_RESPONSE_BYTES = 1_000_000
KEY_MAX_BYTES = 32_768
PROBE_NAME = "Codex App Connectivity Probe"
TOKEN_PERMISSIONS = {"contents": "read", "checks": "write", "metadata": "read"}
REQUIRED_PERMISSIONS = {
    "contents": "read",
    "pull_requests": "read",
    "checks": "write",
    "metadata": "read",
}


class PreflightError(Exception):
    """A fixed, operator-safe error; never include upstream bodies or secrets."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class Config:
    app_id: int
    installation_id: int
    client_id: str
    repository: str

    @classmethod
    def load(cls, path: Path) -> Config:
        try:
            with path.open("rb") as handle:
                raw = handle.read(8193)
            if len(raw) > 8192:
                raise ValueError
            data = json.loads(raw)
        except (OSError, ValueError, UnicodeError):
            raise PreflightError(
                "config-invalid", "Cannot read a valid local config.json."
            ) from None
        keys = {
            "config_version",
            "app_id",
            "installation_id",
            "client_id",
            "repository",
        }
        if not isinstance(data, dict) or set(data) != keys:
            raise PreflightError(
                "config-invalid", "Config fields do not match the expected schema."
            )
        if type(data["config_version"]) is not int or data["config_version"] != 1:
            raise PreflightError("config-version", "Unsupported config version.")
        for name in ("app_id", "installation_id"):
            if type(data[name]) is not int or not 0 < data[name] < 2**63:
                raise PreflightError(
                    "config-id", "App and Installation IDs must be positive integers."
                )
        client = data["client_id"]
        repo = data["repository"]
        if (
            not isinstance(client, str)
            or re.fullmatch(r"[A-Za-z0-9]{8,128}", client) is None
        ):
            raise PreflightError(
                "config-client",
                "Client ID must be the public alphanumeric ID, not a secret.",
            )
        if (
            not isinstance(repo, str)
            or re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_.-]{1,100}", repo
            )
            is None
        ):
            raise PreflightError(
                "config-repository", "Repository must be owner/name, not a URL."
            )
        if repo.split("/")[1] in (".", ".."):
            raise PreflightError("config-repository", "Invalid repository name.")
        return cls(data["app_id"], data["installation_id"], client, repo)


def default_key_path() -> Path:
    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local")))
        return root / "scnehaux-codex-authority/secrets/github-app.pem"
    return Path.home() / ".local/share/scnehaux-codex-authority/secrets/github-app.pem"


def make_jwt(key_path: Path, client_id: str) -> str:
    # Keep credentials out of the setup kit and any Git checkout/worktree.
    original = key_path.expanduser().absolute()
    try:
        info = original.lstat()
        key = original.resolve(strict=True)
    except OSError:
        raise PreflightError(
            "key-missing",
            "Private key file not found. Store it locally, outside the repository.",
        ) from None
    if not stat.S_ISREG(info.st_mode):
        raise PreflightError(
            "key-type",
            "Private key must be a regular file, not a symlink or directory.",
        )
    kit = Path(__file__).resolve().parent
    if key.is_relative_to(kit) or any((p / ".git").exists() for p in key.parents):
        raise PreflightError(
            "key-location",
            "Move the private key outside the setup kit and all Git repositories.",
        )
    if os.name != "nt":
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise PreflightError(
                "key-permissions",
                "Key must belong to your user and have chmod 600 permissions.",
            )
    # Windows ACLs are NOT inferred from POSIX mode bits. See README for icacls.
    try:
        with key.open("rb") as handle:
            pem = handle.read(KEY_MAX_BYTES + 1)
    except OSError:
        raise PreflightError(
            "key-unreadable", "Private key file is not readable by this user."
        ) from None
    if not pem or len(pem) > KEY_MAX_BYTES:
        raise PreflightError(
            "key-size", "Private key file is empty or exceeds the supported size."
        )
    try:
        import jwt
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
    except ImportError:
        raise PreflightError(
            "dependencies-missing",
            "Install requirements.txt in the dedicated virtual environment first.",
        ) from None
    try:
        private_key = serialization.load_pem_private_key(pem, password=None)
        if (
            not isinstance(private_key, rsa.RSAPrivateKey)
            or private_key.key_size < 2048
        ):
            raise ValueError
        now = int(time.time())
        token = jwt.encode(
            {"iat": now - 60, "exp": now + 300, "iss": client_id},
            private_key,
            algorithm="RS256",
        )
        if not isinstance(token, str):
            raise ValueError
        return token
    except Exception:
        # Deliberately do not render library errors, which could include sensitive data.
        raise PreflightError(
            "key-invalid",
            "Use an unencrypted RSA PEM private key from this GitHub App (at least 2048 bits).",
        ) from None


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request_json(
    path: str, token: str, *, method: str = "GET", body: dict | None = None
) -> dict[str, Any]:
    """Fixed-host HTTPS transport. Mutations are restricted to probe endpoints."""
    if (
        not isinstance(path, str)
        or re.fullmatch(r"/[A-Za-z0-9_./-]+", path) is None
        or "//" in path
        or any(part in {".", ".."} for part in path.split("/"))
    ):
        raise PreflightError("api-path", "Invalid API request path.")
    allowed_write = (
        method == "POST"
        and (
            re.fullmatch(r"/app/installations/[1-9][0-9]*/access_tokens", path)
            or re.fullmatch(r"/repos/[A-Za-z0-9-]+/[A-Za-z0-9_.-]+/check-runs", path)
        )
    ) or (method == "DELETE" and path == "/installation/token")
    if method != "GET" and not allowed_write:
        raise PreflightError(
            "api-method",
            "Only token issuance/revocation and connectivity checks may be written.",
        )
    if method != "POST" and body is not None:
        raise PreflightError("api-body", "GET and DELETE requests cannot carry a body.")
    if method == "POST" and path.endswith("/check-runs"):
        if (
            not isinstance(body, dict)
            or body.get("name") != PROBE_NAME
            or body.get("conclusion") != "neutral"
        ):
            raise PreflightError(
                "probe-payload",
                "Only the fixed neutral connectivity probe is permitted.",
            )
    request = Request(
        API_ROOT + path,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + token,
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": "scnehaux-local-app/0.2",
            "Content-Type": "application/json",
        },
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        method=method,
    )
    expected = {"GET": 200, "POST": 201, "DELETE": 204}[method]
    try:
        with build_opener(NoRedirect()).open(request, timeout=20) as response:
            if response.status != expected:
                raise PreflightError(
                    "api-status", "Unexpected GitHub API status; verification stopped."
                )
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        status = exc.code
        exc.close()
        messages = {
            401: "GitHub rejected authentication. Check the key, Client ID, and your computer clock.",
            403: "GitHub denied access. Check installation permissions, restrictions, or API rate limits.",
            404: "GitHub could not find this installation/repository/commit for the authenticated App.",
        }
        raise PreflightError(
            "github-http-" + str(status),
            messages.get(
                status,
                "GitHub request failed. No redirect or automatic retry was attempted.",
            ),
        ) from None
    except (URLError, TimeoutError, OSError, HTTPException):
        raise PreflightError(
            "network-error",
            "Secure connection to api.github.com failed. Check internet/proxy/clock; do not disable TLS verification.",
        ) from None
    if len(raw) > MAX_RESPONSE_BYTES:
        raise PreflightError(
            "api-response-size", "GitHub response exceeded the supported size."
        )
    if expected == 204:
        return {}
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeError):
        raise PreflightError(
            "api-json", "GitHub returned invalid JSON; verification stopped."
        ) from None
    if not isinstance(data, dict):
        raise PreflightError(
            "api-shape", "GitHub returned an unexpected response shape."
        )
    return data


def get_json(path: str, token: str) -> dict[str, Any]:
    """Preserve the GET-only preflight boundary."""
    return request_json(path, token)


def verify_permissions(value: object) -> None:
    if not isinstance(value, dict):
        raise PreflightError(
            "permissions-missing", "Installation permission information is missing."
        )
    for name, level in REQUIRED_PERMISSIONS.items():
        if value.get(name) != level:
            raise PreflightError(
                "permissions-mismatch",
                "Require Contents: read, Pull requests: read, Checks: write, Metadata: read. Approve pending installation changes.",
            )
    if any(
        level != "none"
        for name, level in value.items()
        if name not in REQUIRED_PERMISSIONS
    ):
        raise PreflightError(
            "permissions-excess",
            "Remove extra App permissions; this dedicated App needs only the four documented permissions.",
        )


def verify_installation(data: dict[str, Any], config: Config) -> None:
    if type(data.get("id")) is not int or data["id"] != config.installation_id:
        raise PreflightError(
            "installation-mismatch",
            "The installation does not match the configured Installation ID.",
        )
    if type(data.get("app_id")) is not int or data["app_id"] != config.app_id:
        raise PreflightError(
            "installation-app-mismatch",
            "The installation does not belong to the expected App.",
        )
    account = data.get("account")
    login = account.get("login") if isinstance(account, dict) else None
    if (
        not isinstance(login, str)
        or login.lower() != config.repository.split("/")[0].lower()
    ):
        raise PreflightError(
            "installation-owner",
            "The installation account does not match the repository owner.",
        )
    if data.get("suspended_at", "missing") is not None:
        raise PreflightError(
            "installation-suspended",
            "Installation is suspended or its suspension status is unavailable.",
        )
    if data.get("repository_selection") != "selected":
        raise PreflightError(
            "repository-selection",
            "Limit this dedicated App to selected repositories, not all repositories.",
        )
    verify_permissions(data.get("permissions"))


def preflight(
    config: Config, token: str, read: Callable[[str, str], dict[str, Any]] = get_json
) -> dict[str, Any]:
    app = read("/app", token)
    if type(app.get("id")) is not int or app["id"] != config.app_id:
        raise PreflightError(
            "app-mismatch", "This private key authenticates as a different App."
        )
    installation = read(f"/app/installations/{config.installation_id}", token)
    verify_installation(installation, config)
    # Repository lookup verifies inclusion without listing unrelated repositories.
    repository_installation = read(f"/repos/{config.repository}/installation", token)
    verify_installation(repository_installation, config)
    return {
        "status": "connection_verified",
        "app_id": config.app_id,
        "installation_id": config.installation_id,
        "repository": config.repository,
        "installed_permissions": dict(REQUIRED_PERMISSIONS),
        "checks_write_tested": False,
        "governance_evaluated": False,
        "effective_enforcement_proven": False,
        "remote_mutations": 0,
    }


def probe_plan(config: Config, sha: str) -> dict[str, Any]:
    """Build an offline, credential-free preview; never resolve a floating ref."""
    if (
        not isinstance(sha, str)
        or re.fullmatch(r"[0-9a-f]{40}", sha) is None
        or sha == "0" * 40
    ):
        raise PreflightError(
            "probe-sha",
            "Specify an exact nonzero, lowercase 40-character commit SHA; not a branch, tag, or PR number.",
        )
    return {
        "status": "preview_only",
        "repository": config.repository,
        "app_id": config.app_id,
        "installation_id": config.installation_id,
        "head_sha": sha,
        "name": PROBE_NAME,
        "conclusion": "neutral",
        "governance_evaluated": False,
        "effective_enforcement_proven": False,
        "remote_mutations": 0,
        "notice": "A write creates one non-required connectivity check, NOT a governance result. Never require this probe for merging.",
    }


def verify_check(data: dict[str, Any], config: Config, sha: str) -> int:
    """Require exact returned identity, SHA, context, status, and probe lineage."""
    check_id = data.get("id")
    app = data.get("app")
    if (
        type(check_id) is not int
        or check_id <= 0
        or not isinstance(app, dict)
        or type(app.get("id")) is not int
        or app["id"] != config.app_id
        or data.get("head_sha") != sha
        or data.get("name") != PROBE_NAME
        or data.get("status") != "completed"
        or data.get("conclusion") != "neutral"
        or data.get("external_id") != "codex-connectivity/" + sha
    ):
        raise PreflightError(
            "check-mismatch",
            "Returned check does not match the expected App, SHA, name, or probe result.",
        )
    return check_id


def run_probe(config: Config, app_token: str, sha: str, request=None) -> dict[str, Any]:
    """Mint -> verify scope/commit -> create -> read back -> revoke. No retries."""
    plan = probe_plan(config, sha)
    request = request or request_json
    preflight(config, app_token, lambda path, token: request(path, token))
    issued = request(
        f"/app/installations/{config.installation_id}/access_tokens",
        app_token,
        method="POST",
        body={
            "repositories": [config.repository.split("/", 1)[1]],
            "permissions": {"contents": "read", "checks": "write"},
        },
    )
    token = issued.get("token")
    if (
        not isinstance(token, str)
        or not token
        or not token.isascii()
        or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in token)
    ):
        raise PreflightError(
            "token-invalid",
            "GitHub returned no usable installation token. No check was requested; token issuance may have occurred.",
        )
    try:
        if issued.get("permissions") != TOKEN_PERMISSIONS:
            raise PreflightError(
                "token-permissions",
                "Issued token permissions do not match the requested restricted scope.",
            )
        try:
            expires = datetime.fromisoformat(
                issued["expires_at"].replace("Z", "+00:00")
            )
            seconds = (expires - datetime.now(timezone.utc)).total_seconds()
            if not 0 < seconds <= 3660:
                raise ValueError
        except (KeyError, AttributeError, TypeError, ValueError):
            raise PreflightError(
                "token-expiry",
                "Issued token lifetime is missing, expired, or unexpectedly long.",
            ) from None
        listing = request("/installation/repositories", token)
        repos = listing.get("repositories")
        if (
            type(listing.get("total_count")) is not int
            or listing["total_count"] != 1
            or not isinstance(repos, list)
            or len(repos) != 1
            or not isinstance(repos[0], dict)
            or not isinstance(repos[0].get("full_name"), str)
            or repos[0]["full_name"].lower() != config.repository.lower()
        ):
            raise PreflightError(
                "token-repositories",
                "Issued token must access exactly the selected target repository.",
            )
        commit = request(f"/repos/{config.repository}/commits/{sha}", token)
        if commit.get("sha") != sha:
            raise PreflightError(
                "commit-mismatch",
                "GitHub did not resolve the exact requested commit in the target repository.",
            )
        payload = {
            "name": PROBE_NAME,
            "head_sha": sha,
            "status": "completed",
            "conclusion": "neutral",
            "completed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "external_id": "codex-connectivity/" + sha,
            "output": {
                "title": "Connectivity only - no governance evaluation",
                "summary": "Tests App authentication and Checks API transport only. NOT evidence of candidate compliance, evaluator promotion, or merge enforcement. Never configure this probe as a required check.",
            },
        }
        created = request(
            f"/repos/{config.repository}/check-runs", token, method="POST", body=payload
        )
        check_id = verify_check(created, config, sha)
        observed = request(f"/repos/{config.repository}/check-runs/{check_id}", token)
        if verify_check(observed, config, sha) != check_id:
            raise PreflightError(
                "check-id-mismatch", "Read-back returned a different Check Run ID."
            )
    finally:
        try:
            request("/installation/token", token, method="DELETE")
        except Exception:
            raise PreflightError(
                "token-revocation-failed",
                "Installation token revocation could not be confirmed. A check may already exist. Stop, inspect GitHub, and follow the runbook; do not blindly retry.",
            ) from None
    return {
        **plan,
        "status": "connectivity_verified",
        "check_run_id": check_id,
        "check_url": f"https://github.com/{config.repository}/runs/{check_id}",
        "checks_write_tested": True,
        "installation_token_revoked": True,
        "remote_mutations": 3,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=Path(__file__).with_name("config.json")
    )
    parser.add_argument(
        "--private-key",
        type=Path,
        default=default_key_path(),
        help="Local PEM path only. Never paste PEM contents or a token.",
    )
    parser.add_argument(
        "--json", action="store_true", help="Print a sanitized JSON result."
    )
    parser.add_argument(
        "--probe-sha",
        help="Preview a connectivity check for this exact commit. No network or key access without --write.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Actually create the connectivity check; requires both confirmations.",
    )
    parser.add_argument("--confirm-repository")
    parser.add_argument("--confirm-sha")
    args = parser.parse_args(argv)
    try:
        config = Config.load(args.config)
        if (
            args.write
            or args.confirm_repository is not None
            or args.confirm_sha is not None
        ):
            if (
                not args.write
                or args.probe_sha is None
                or args.confirm_repository != config.repository
                or args.confirm_sha != args.probe_sha
            ):
                raise PreflightError(
                    "write-confirmation",
                    "Write requires --probe-sha plus --write, exact --confirm-repository and matching --confirm-sha. No credentials were read.",
                )
        if args.probe_sha is not None:
            plan = probe_plan(config, args.probe_sha)
            if not args.write:
                print(json.dumps(plan, indent=2, sort_keys=True))
                return 0
        if any(
            (parent / ".git").exists() for parent in Path(__file__).resolve().parents
        ):
            raise PreflightError(
                "runtime-checkout",
                "Export a reviewed, pinned helper copy outside Git before using credentials. See the runbook.",
            )
        token = make_jwt(args.private_key, config.client_id)
        report = (
            run_probe(config, token, args.probe_sha)
            if args.write
            else preflight(config, token)
        )
    except PreflightError as exc:
        error = {
            "status": "blocked",
            "code": exc.code,
            "message": str(exc),
            "effective_enforcement_proven": False,
        }
        if args.write:
            error["notice"] = (
                "No automatic retries. Depending on failure stage, token issuance or a check may already exist. Inspect GitHub before repeating a write."
            )
        print(
            json.dumps(error)
            if args.json
            else "[BLOCKED] " + exc.code + ": " + str(exc)
        )
        if args.write and not args.json:
            print("[NOTICE] " + error["notice"])
        return 1
    except KeyboardInterrupt:
        print(
            "[STOPPED] Interrupted. In write mode a check/token may exist; inspect GitHub before retrying."
        )
        return 130
    except Exception:
        print(
            "[BLOCKED] Unexpected local error; sensitive details suppressed. In write mode inspect GitHub before retrying."
        )
        return 1
    if args.json or args.write:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"[PASS] Authenticated App ID: {config.app_id}")
        print(f"[PASS] Installation ID: {config.installation_id}")
        print(f"[PASS] Repository belongs to this installation: {config.repository}")
        print("[PASS] Installed permissions match the least-privilege setup.")
        print("[NOT RUN] Checks API write test and governance evaluation.")
        print(
            "[NOT PROVEN] Effective merge enforcement. No checks or rulesets were written."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
