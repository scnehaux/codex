.PHONY: lint lint-code lint-docs-format lint-sarif format format-code format-docs test install install-hooks generate-docs verify-generated check-waivers all coverage docker-build docker-run clean genesis-check mutation-check governance-qualify genesis-commit-check

# Run all processes (setup, generate docs, linting, and testing)
all: install install-hooks generate-docs lint test

# Install Python dependencies into the local environment
install:
	pip install -e .[dev]

# Install the Git hook script to block dirty/unformatted commits
install-hooks:
	python 06-fitness-function/scripts/install-hooks.py

# Automatically build/update all Markdown documents sourced from JSON Schemas or scripts
generate-docs:
	python 06-fitness-function/generators/generate_rules_doc.py
	python 06-fitness-function/generators/generate_functions_doc.py
	python 06-fitness-function/generators/generate_engine_topography.py
	python 06-fitness-function/generators/generate_adr_index.py
	python 06-fitness-function/generators/generate_pad_sad_index.py
	python 06-fitness-function/generators/generate_traceability_graph.py
	python 06-fitness-function/generators/generate_maturity_dashboard.py

# Verify the committed state equals generate-then-format.
#
# The two steps must run in this order and the check must come after both. The generators inject
# blocks into documents that `lint-docs-format` also governs, and their raw output is not
# Prettier-formatted -- so comparing straight after generation asks the repository to hold
# formatted and unformatted content simultaneously, which no commit can satisfy. Generating and
# then formatting is the definition of the committed state, and this target is what proves a
# checkout still matches it.
verify-generated: generate-docs format-docs
	git diff --exit-code || (echo "Generated documentation is out of sync. Run 'make verify-generated' locally and commit the result." && exit 1)

# Run the core architecture linter to validate document compliance (C4, NFRs, etc.)
lint:
	python -m engine.interfaces.cli --target .

# Run the architecture linter and output the results in SARIF format (for GitHub Code Scanning)
lint-sarif:
	python -m engine.interfaces.cli --target . --format sarif > linter.sarif

# Check for expired architecture exception waivers based on the current date
check-waivers:
	python 06-fitness-function/scripts/waiver-expiry-check.py

# Auto-format Python code using Ruff
format-code:
	ruff check --fix engine tests 06-fitness-function conftest.py
	ruff format engine tests 06-fitness-function conftest.py

# Auto-format Markdown & JSON documents using Prettier
format-docs:
	npx --yes prettier@3.9.6 --write "**/*.md" "**/*.json"

# Auto-format ALL files (Python, Markdown, and JSON) at once
format: format-code format-docs

# Check Python code formatting (no auto-fix, used by CI/CD & Git hooks)
lint-code:
	ruff check engine tests 06-fitness-function conftest.py
	ruff format --check engine tests 06-fitness-function conftest.py

# Check document formatting (no auto-fix, used by CI/CD & Git hooks)
lint-docs-format:
	npx --yes prettier@3.9.6 --check "**/*.md" "**/*.json"

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
	python 06-fitness-function/scripts/genesis_integrity.py
# Verify governed document version and mutation integrity
mutation-check:
	python 06-fitness-function/scripts/mutation_integrity.py
# Qualify the complete local governance control plane
governance-qualify:
	python 06-fitness-function/scripts/governance_qualify.py
# Qualify the exact staged tree for the Genesis root commit
genesis-commit-check:
	python 06-fitness-function/scripts/genesis_commit_qualify.py
