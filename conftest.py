"""Repository-wide pytest lifecycle and hard coverage gate."""

from pathlib import Path
import tomllib

import pytest


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_sessionfinish(session, exitstatus):
    """Hard-gate statement coverage for every production control source file."""
    yield

    terminal = session.config.pluginmanager.getplugin("terminalreporter")
    if terminal is not None and terminal.stats.get("error"):
        return

    cov_plugin = session.config.pluginmanager.getplugin("_cov")
    if cov_plugin is None:
        return

    controller = getattr(cov_plugin, "cov_controller", None)
    cov = getattr(controller, "cov", None)
    if cov is None:
        return

    root = Path(str(session.config.rootpath))
    with (root / "pyproject.toml").open("rb") as handle:
        config = tomllib.load(handle)
    threshold = float(config["tool"]["scnehaux"]["coverage"]["per_file_min"])

    engine_root = root / "engine" / "control"
    failures = []

    for source in sorted(engine_root.rglob("*.py")):
        try:
            _filename, statements, _excluded, missing, _formatted = cov.analysis2(str(source))
        except Exception as exc:
            failures.append((source, 0.0, f"coverage analysis failed: {exc}"))
            continue

        executable = len(statements)
        percent = 100.0 if executable == 0 else ((executable - len(missing)) / executable) * 100.0
        if percent + 1e-9 < threshold:
            failures.append((source, percent, f"missing lines: {missing}"))

    if failures:
        if terminal:
            terminal.write_sep("=", f"PER-FILE COVERAGE GATE FAILED (< {threshold:.0f}%)")
            for source, percent, detail in failures:
                rel = source.relative_to(root)
                terminal.write_line(f"{rel}: {percent:.2f}% — {detail}")
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
    elif terminal:
        terminal.write_sep("=", f"PER-FILE COVERAGE GATE PASSED (>= {threshold:.0f}% EACH)")
