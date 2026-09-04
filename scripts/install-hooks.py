import os
import stat
import sys


def repository_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def install_hook() -> int:
    """
    Install a Git pre-commit hook that enforces Scnehaux Architecture Governance rules.
    Detects the host OS and injects the appropriate shell script (PowerShell for Windows, Bash for Unix).
    """
    repo_root = repository_root()
    hooks_dir = os.path.join(repo_root, ".git", "hooks")

    if not os.path.exists(hooks_dir):
        print(
            f"Error: .git/hooks directory not found at {hooks_dir}. Are you in the root of the repository?"
        )
        return 1

    hook_path = os.path.join(hooks_dir, "pre-commit")

    is_windows = sys.platform.startswith("win")

    if is_windows:
        hook_content = '#!/usr/bin/env powershell\n# Pre-commit hook to enforce Scnehaux Architecture Governance\nWrite-Host "Running Scnehaux Governance Linter..."\n\n$CHANGED_FILES = git diff --cached --name-only --diff-filter=ACM | Select-String -Pattern \'\\.md$\' | ForEach-Object { $_.Line }\n\nif (-not $CHANGED_FILES) {\n    Write-Host "No markdown files changed. Skipping linter."\n    exit 0\n}\n\n$TARGETS = $CHANGED_FILES -join \' \'\n\nWrite-Host "Verifying code and documentation formatting..."\nInvoke-Expression "make lint-code"\nif ($LASTEXITCODE -ne 0) {\n    Write-Host "âŒ [CRITICAL] Code formatting failed (Ruff)!"\n    exit 1\n}\n\nInvoke-Expression "make lint-docs-format"\nif ($LASTEXITCODE -ne 0) {\n    Write-Host "âŒ [CRITICAL] Markdown/JSON formatting failed (Prettier)!"\n    exit 1\n}\n\nWrite-Host "Running Unit Tests..."\nInvoke-Expression "make test"\nif ($LASTEXITCODE -ne 0) {\n    Write-Host "âŒ [CRITICAL] Unit tests failed! Please fix the tests before committing."\n    exit 1\n}\n\n$env:PYTHONPATH="."\nInvoke-Expression "python -m engine.interfaces.cli --format text --target $TARGETS"\n\nif ($LASTEXITCODE -ne 0) {\n    Write-Host ""\n    Write-Host "âŒ [CRITICAL] Architecture Linter failed!"\n    Write-Host "Commit rejected. Please fix the governance violations before committing."\n    exit 1\n}\n\nWrite-Host "âœ… Governance check passed. Proceeding with commit."\nexit 0\n'
    else:
        hook_content = '#!/bin/bash\n# Pre-commit hook to enforce Scnehaux Architecture Governance\necho "Running Scnehaux Governance Linter..."\n\n# Extract only changed markdown files\nCHANGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep \'\\.md$\')\n\nif [ -z "$CHANGED_FILES" ]; then\n    echo "No markdown files changed. Skipping linter."\n    exit 0\nfi\n\n# Convert newlines to spaces for the target argument\nTARGETS=$(echo "$CHANGED_FILES" | tr \'\\n\' \' \')\n\necho "Verifying code and documentation formatting..."\nmake lint-code\nif [ $? -ne 0 ]; then\n  echo "âŒ [CRITICAL] Code formatting failed (Ruff)!"\n  exit 1\nfi\n\nmake lint-docs-format\nif [ $? -ne 0 ]; then\n  echo "âŒ [CRITICAL] Markdown/JSON formatting failed (Prettier)!"\n  exit 1\nfi\n\necho "Running Unit Tests..."\nmake test\nif [ $? -ne 0 ]; then\n  echo "âŒ [CRITICAL] Unit tests failed! Please fix the tests before committing."\n  exit 1\nfi\n\nexport PYTHONPATH="."\npython -m engine.interfaces.cli --format text --target $TARGETS\n\nif [ $? -ne 0 ]; then\n  echo ""\n  echo "âŒ [CRITICAL] Architecture Linter failed!"\n  echo "Commit rejected. Please fix the governance violations before committing."\n  exit 1\nfi\n\necho "âœ… Governance check passed. Proceeding with commit."\nexit 0\n'

    with open(hook_path, "w", encoding="utf-8") as f:
        f.write(hook_content)

    if not is_windows:
        st = os.stat(hook_path)
        os.chmod(hook_path, st.st_mode | stat.S_IEXEC)

    print(
        f"Successfully installed pre-commit hook at {hook_path} (OS: {'Windows' if is_windows else 'Unix'})"
    )
    return 0


def main() -> int:
    return install_hook()


if __name__ == "__main__":
    raise SystemExit(main())
