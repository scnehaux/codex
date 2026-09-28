from __future__ import annotations

import json
from pathlib import Path
import re
import tomllib


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "governance/reproducibility-policy.json"
WORKFLOW_RELATIVES = (
    ".github/workflows/governance.yml",
    ".github/workflows/governance-evaluator.yml",
    ".github/workflows/local-app-tooling.yml",
)
EXACT_PIN = re.compile(r"^[A-Za-z0-9_.-]+(?:\[[A-Za-z0-9_,.-]+\])?==[^=<>!~\s]+$")
HASH_TOKEN = re.compile(r"--hash=sha256:[0-9a-f]{64}")
ACTION_SHA = re.compile(r"^\s*uses:\s*[^@\s]+@([0-9a-f]{40})(?:\s+#.*)?$")
PYTHON_VERSION = 'python-version: "3.13.15"'
NODE_VERSION = 'node-version: "24.21.0"'


class ReproducibilityError(RuntimeError):
    pass


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise ReproducibilityError(code)


def _requirements(path: Path) -> tuple[str, ...]:
    rows = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("-r "):
            continue
        rows.append(line)
    return tuple(rows)


def _assert_exact(rows: tuple[str, ...], code: str) -> None:
    for row in rows:
        _require(EXACT_PIN.fullmatch(row) is not None, f"{code}:{row}")


def _hash_lock(path: Path) -> dict[str, tuple[str, ...]]:
    locked: dict[str, tuple[str, ...]] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        requirement = parts[0]
        _require(
            EXACT_PIN.fullmatch(requirement) is not None,
            f"reproducibility-lock-pin:{requirement}",
        )
        hashes = tuple(item for item in parts[1:] if HASH_TOKEN.fullmatch(item))
        _require(bool(hashes), f"reproducibility-lock-hash:{requirement}")
        _require(
            len(parts) == 1 + len(hashes), f"reproducibility-lock-token:{requirement}"
        )
        _require(
            requirement not in locked, f"reproducibility-lock-duplicate:{requirement}"
        )
        locked[requirement] = hashes
    return locked


def assert_reproducibility_policy(repo_root: str | Path = ROOT) -> None:
    root = Path(repo_root).resolve()
    policy = json.loads(
        (root / "governance/reproducibility-policy.json").read_text(encoding="utf-8")
    )
    _require(policy["schema_version"] == 1, "reproducibility-policy-version")
    _require(
        policy["kind"] == "scnehaux-reproducibility-policy",
        "reproducibility-policy-kind",
    )
    _require(
        policy["qualification_runtime"] == {"python": "3.13.15", "node": "24.21.0"},
        "reproducibility-runtime",
    )
    _require(
        policy["python"]["build_backend"] == "setuptools==84.0.0",
        "reproducibility-build-backend-policy",
    )
    _require(
        policy["python"]["dependency_policy"] == "exact-pins",
        "reproducibility-python-policy",
    )
    _require(
        policy["documents"]
        == {
            "integrity_required": True,
            "lock_file": "package-lock.json",
            "package_file": "package.json",
            "prettier": "3.9.6",
            "resolution": "npm-ci-lockfile",
        },
        "reproducibility-prettier-policy",
    )
    _require(
        policy["python"].get("hash_lock") == "requirements-lock.txt",
        "reproducibility-python-hash-lock-policy",
    )
    _require(
        policy["github_actions"]["reference_policy"] == "full-commit-sha",
        "reproducibility-action-policy",
    )

    pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    _require(
        pyproject["build-system"]["requires"] == ["setuptools==84.0.0"],
        "reproducibility-build-backend",
    )
    _assert_exact(
        tuple(pyproject["project"]["dependencies"]),
        "reproducibility-project-dependency",
    )
    _assert_exact(
        tuple(pyproject["project"]["optional-dependencies"]["dev"]),
        "reproducibility-dev-dependency",
    )

    constraints = _requirements(root / "constraints.txt")
    _assert_exact(constraints, "reproducibility-constraint")
    expected_resolution = tuple(policy["python"]["resolved_packages"])
    _assert_exact(expected_resolution, "reproducibility-policy-resolution")
    _require(
        set(constraints) == set(expected_resolution),
        "reproducibility-constraints-resolution-drift",
    )
    _require(
        "setuptools==84.0.0" in constraints, "reproducibility-setuptools-constraint"
    )
    _require(
        "jsonschema==4.21.1" in constraints, "reproducibility-jsonschema-constraint"
    )

    lock = _hash_lock(root / "requirements-lock.txt")
    _require(
        set(lock) == set(constraints), "reproducibility-hash-lock-resolution-drift"
    )

    for relative in (
        "requirements.txt",
        "integrations/github-app-local/requirements.txt",
        "integrations/github-app-local/requirements-dev.txt",
    ):
        _assert_exact(_requirements(root / relative), "reproducibility-requirement")

    for relative in WORKFLOW_RELATIVES:
        workflow = root / relative
        text = workflow.read_text(encoding="utf-8")
        _require(
            PYTHON_VERSION in text, f"reproducibility-python-runner:{workflow.name}"
        )
        for line in text.splitlines():
            if line.lstrip().startswith("uses:"):
                _require(
                    ACTION_SHA.fullmatch(line) is not None,
                    f"reproducibility-action-sha:{workflow.name}:{line.strip()}",
                )
    governance = (root / ".github/workflows/governance.yml").read_text(encoding="utf-8")
    _require(NODE_VERSION in governance, "reproducibility-node-runner")

    package = json.loads((root / "package.json").read_text(encoding="utf-8"))
    package_lock = json.loads((root / "package-lock.json").read_text(encoding="utf-8"))
    _require(
        package
        == {
            "name": "scnehaux-codex-governance-tools",
            "private": True,
            "devDependencies": {"prettier": "3.9.6"},
        },
        "reproducibility-package-json",
    )
    _require(
        package_lock.get("lockfileVersion") == 3, "reproducibility-package-lock-version"
    )
    root_package = package_lock.get("packages", {}).get("")
    prettier_package = package_lock.get("packages", {}).get("node_modules/prettier")
    _require(
        isinstance(root_package, dict)
        and root_package.get("devDependencies") == {"prettier": "3.9.6"},
        "reproducibility-package-lock-root",
    )
    _require(
        isinstance(prettier_package, dict)
        and prettier_package.get("version") == "3.9.6",
        "reproducibility-prettier-lock-version",
    )
    integrity = prettier_package.get("integrity")
    _require(
        isinstance(integrity, str)
        and integrity.startswith("sha512-")
        and len(integrity) > 20,
        "reproducibility-prettier-lock-integrity",
    )
    prettier = (root / "scripts/prettier_runner.py").read_text(encoding="utf-8")
    _require('PRETTIER_VERSION = "3.9.6"' in prettier, "reproducibility-prettier-pin")
    _require(
        "_resolve_prettier" in prettier and "npx" not in prettier,
        "reproducibility-prettier-local-only",
    )
    _require(
        "--require-hashes -r requirements-lock.txt" in governance,
        "reproducibility-ci-hash-install",
    )
    _require(
        "npm ci --ignore-scripts --no-audit --no-fund" in governance,
        "reproducibility-ci-npm-lock",
    )
    _require(
        "--no-build-isolation --no-deps -e" in governance,
        "reproducibility-ci-no-build-isolation",
    )


def main() -> int:
    try:
        assert_reproducibility_policy(ROOT)
    except (OSError, KeyError, TypeError, ValueError, ReproducibilityError) as exc:
        print(f"[FAIL] reproducibility policy: {exc}")
        return 1
    print(
        "[PASS] reproducibility toolchain and dependency declarations are exact-pinned"
    )
    print("  Python: 3.13.15")
    print("  Node: 24.21.0")
    print("  build backend: setuptools==84.0.0")
    print("  Python artifact hashes: locked (Windows x64 + manylinux x86_64)")
    print("  Prettier: 3.9.6 via package-lock.json integrity + npm ci")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
