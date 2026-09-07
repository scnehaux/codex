"""Exercise real GNU Make orchestration without installing or generating anything."""

from pathlib import Path
import os
import shlex
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
STAGES = ("install", "install-hooks", "generate-docs", "lint", "test")

# Leaf recipes are replaced only in a temporary Makefile. Recursive make still
# executes the production `all` recipe, but cannot run pip, generators, or pytest.
WORKER = f"""
from pathlib import Path
import os
import sys

stages = {STAGES!r}
stage = sys.argv[1]

def record(event):
    with Path("events.txt").open("a", encoding="utf-8") as handle:
        handle.write(event + "\\n")

record(stage + ":start")
index = stages.index(stage)
if index and not (Path("completed") / stages[index - 1]).is_file():
    raise SystemExit("stage started before its prerequisite completed: " + stage)
if os.environ.get("MAKE_TEST_FAIL_STAGE") == stage:
    raise SystemExit(17)
(Path("completed") / stage).write_text("done", encoding="utf-8")
record(stage + ":end")
"""


@pytest.fixture
def make_env() -> dict[str, str]:
    """Do not inherit outer make flags, jobserver descriptors, or test controls."""
    env = os.environ.copy()
    for name in (
        "MAKEFLAGS",
        "MFLAGS",
        "GNUMAKEFLAGS",
        "MAKELEVEL",
        "MAKEOVERRIDES",
        "MAKEFILES",
        "MAKE_TEST_FAIL_STAGE",
    ):
        env.pop(name, None)
    return env


@pytest.fixture
def gnu_make(make_env: dict[str, str]) -> str:
    executable = shutil.which("gmake") or shutil.which("make")
    if executable is None:
        pytest.skip("GNU Make is required for Makefile orchestration tests")
    result = subprocess.run(
        [executable, "--version"],
        env=make_env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode or "GNU Make" not in result.stdout:
        pytest.skip("GNU Make is required for Makefile orchestration tests")
    return executable


@pytest.fixture
def make_sandbox(tmp_path: Path) -> Path:
    root = tmp_path / "make sandbox"
    root.mkdir()
    (root / "completed").mkdir()
    (root / "record_step.py").write_text(WORKER, encoding="utf-8")
    overrides = "\n# Test-only leaf recipes; preserve production orchestration.\n"
    for stage in STAGES:
        overrides += f'{stage}:\n\t"{sys.executable}" -S record_step.py {stage}\n'
    (root / "Makefile").write_text(
        (ROOT / "Makefile").read_text(encoding="utf-8") + overrides,
        encoding="utf-8",
    )
    return root


def _run_make(
    executable: str,
    root: Path,
    env: dict[str, str],
    *arguments: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [executable, "--no-print-directory", *arguments],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _events(root: Path) -> list[str]:
    return (root / "events.txt").read_text(encoding="utf-8").splitlines()


def _completed_events(stages: tuple[str, ...]) -> list[str]:
    return [f"{stage}:{event}" for stage in stages for event in ("start", "end")]


@pytest.mark.parametrize("jobs", [1, 2, 8])
def test_all_runs_stages_in_order(
    jobs: int, gnu_make: str, make_sandbox: Path, make_env: dict[str, str]
) -> None:
    result = _run_make(gnu_make, make_sandbox, make_env, f"-j{jobs}", "all")
    assert result.returncode == 0, result.stdout + result.stderr
    assert _events(make_sandbox) == _completed_events(STAGES)


@pytest.mark.parametrize("jobs", [1, 2, 8])
@pytest.mark.parametrize("failed_stage", STAGES)
def test_all_stops_after_failure_even_with_keep_going(
    jobs: int,
    failed_stage: str,
    gnu_make: str,
    make_sandbox: Path,
    make_env: dict[str, str],
) -> None:
    make_env["MAKE_TEST_FAIL_STAGE"] = failed_stage
    result = _run_make(gnu_make, make_sandbox, make_env, f"-j{jobs}", "-k", "all")
    assert result.returncode != 0, result.stdout + result.stderr
    expected = _completed_events(STAGES[: STAGES.index(failed_stage)])
    assert _events(make_sandbox) == expected + [f"{failed_stage}:start"]


def test_default_goal_remains_all(
    gnu_make: str, make_sandbox: Path, make_env: dict[str, str]
) -> None:
    result = _run_make(gnu_make, make_sandbox, make_env, "-j8")
    assert result.returncode == 0, result.stdout + result.stderr
    assert _events(make_sandbox) == _completed_events(STAGES)


def test_install_uses_python_pip_and_repository_constraints(
    gnu_make: str, tmp_path: Path, make_env: dict[str, str]
) -> None:
    # Dry-run the untouched install recipe: no dependency download is performed.
    shutil.copyfile(ROOT / "Makefile", tmp_path / "Makefile")
    result = _run_make(gnu_make, tmp_path, make_env, "--dry-run", "install")
    assert result.returncode == 0, result.stdout + result.stderr
    assert shlex.split(result.stdout.strip()) == [
        "python",
        "-m",
        "pip",
        "install",
        "-c",
        "constraints.txt",
        "-e",
        ".[dev]",
    ]
