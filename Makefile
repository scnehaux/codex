.PHONY: lint lint-code lint-docs-format lint-sarif format format-code format-docs test install install-hooks generate-docs verify-generated check-waivers all coverage docker-build docker-run clean genesis-check mutation-check governance-qualify genesis-commit-check mutation-ci-check scm-trust-boundary-check scm-policy-check github-policy-check

# Run all processes (setup, generate docs, linting, and testing)
all: install install-hooks generate-docs lint test

# Install Python dependencies into the local environment
install:
	pip install -e .[dev]

# Install the Git hook script to block dirty/unformatted commits
install-hooks:
	python scripts/install-hooks.py

# Automatically build/update all Markdown documents sourced from JSON Schemas or scripts
generate-docs:
	python generators/generate_rules_doc.py
	python generators/generate_functions_doc.py
	python generators/generate_engine_topography.py
	python generators/generate_adr_index.py
	python generators/generate_pad_sad_index.py
	python generators/generate_traceability_graph.py
	python generators/generate_maturity_dashboard.py

# Verify generate-then-format is reproducible from the current repository state.
#
# The repository may already contain intentional tracked or untracked changes. Capture that state,
# run generation followed by formatting, then require the resulting state to be identical. This
# proves generation is deterministic without confusing unrelated working-tree changes with drift.
verify-generated:
	python -c "import hashlib,os,pathlib,subprocess,sys; untracked=lambda: subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z']).split(b'\0'); state=lambda: hashlib.sha256(subprocess.check_output(['git','diff','--binary','HEAD','--','.'],stderr=subprocess.DEVNULL)+b''.join(p+b'\0'+hashlib.sha256(pathlib.Path(os.fsdecode(p)).read_bytes()).digest() for p in untracked() if p)).digest(); before=state(); subprocess.run([sys.argv[1],'generate-docs'],check=True); subprocess.run([sys.argv[1],'format-docs'],check=True); after=state(); print('[PASS] Generated state is reproducible' if before==after else '[FAIL] Generate-then-format changed repository state'); sys.exit(0 if before==after else 1)" "$(MAKE)"

# Run the core architecture linter to validate document compliance (C4, NFRs, etc.)
lint:
	python -m engine.interfaces.cli --target .

# Run the architecture linter and output the results in SARIF format (for GitHub Code Scanning)
lint-sarif:
	python -m engine.interfaces.cli --target . --format sarif > linter.sarif

# Check for expired architecture exception waivers based on the current date
check-waivers:
	python scripts/waiver-expiry-check.py

# Auto-format Python code using Ruff
format-code:
	ruff check --fix engine tests generators scripts conftest.py
	ruff format engine tests generators scripts conftest.py

# Auto-format Markdown & JSON documents using Prettier
format-docs:
	python scripts/prettier_runner.py --write

# Auto-format ALL files (Python, Markdown, and JSON) at once
format: format-code format-docs

# Check Python code formatting (no auto-fix, used by CI/CD & Git hooks)
lint-code:
	ruff check engine tests generators scripts conftest.py
	ruff format --check engine tests generators scripts conftest.py

# Check document formatting (no auto-fix, used by CI/CD & Git hooks)
lint-docs-format:
	python scripts/prettier_runner.py --check

# Run unit tests for the linter engine (using pytest)
test:
	python -m pytest

# Run unit tests and generate an HTML coverage report
coverage:
	python -m pytest --cov-report html
	@echo "Open htmlcov/index.html in your browser to view the detailed results."

# Clean up cache and junk files (pycache, pytest_cache, coverage data)
clean:
ifeq ($(OS),Windows_NT)
	if exist .pytest_cache rd /s /q .pytest_cache
	if exist .coverage del .coverage
	if exist htmlcov rd /s /q htmlcov
	if exist .ruff_cache rd /s /q .ruff_cache
	for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
else
	rm -rf .pytest_cache .coverage htmlcov .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
endif

# Build a Docker Image for the linter (for isolated execution)
docker-build:
	docker build -t scnehaux-linter:test .

# Run the linter inside the Docker container
docker-run:
	docker run --rm -v "$$(pwd):/docs" scnehaux-linter:test --target /docs
# Verify the pre/post Genesis repository root-of-trust contract
genesis-check:
	python scripts/genesis_integrity.py
# Verify governed document version and mutation integrity
mutation-check:
	python scripts/mutation_integrity.py
# Qualify the complete local governance control plane
governance-qualify:
	python scripts/governance_qualify.py
# Qualify the exact staged tree for the Genesis root commit
genesis-commit-check:
	python scripts/genesis_commit_qualify.py
# Validate committed governed mutations against an explicit CI/PR base
mutation-ci-check:
	python scripts/committed_mutation_integrity.py --base-ref "$(SCNEHAUX_MUTATION_BASE_REF)"
# Validate provider-neutral SCM enforcement trust-boundary contract
scm-trust-boundary-check:
	python scripts/scm_trust_boundary_check.py
# Validate provider-neutral SCM desired-state semantic policy
scm-policy-check:
	python scripts/scm_policy_check.py
# Validate GitHub projection of the provider-neutral SCM policy
github-policy-check:
	python scripts/github_policy_check.py
