"""
Global configuration constants for the Scnehaux Architecture Linter.
"""

import os

# Framework-owned resources resolve from the Codex checkout/package, while
# architecture-owned policy instances resolve from the consumer repository CWD.
FRAMEWORK_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
BASE_SCHEMA_PATH = os.path.join(FRAMEWORK_ROOT, "schemas", "base.schema.json")
TECH_RADAR_SCHEMA_PATH = os.path.join(
    FRAMEWORK_ROOT, "schemas", "tech-radar.schema.json"
)
TECH_RADAR_YAML_PATH = os.path.join("enterprise", "tech-radar.yaml")

# Global denylist of directories to ignore during filesystem traversal.
# This prevents the linter from crawling through caches and dependencies,
# dramatically improving performance and eliminating false positives.
EXCLUDED_DIRS = (
    ".git",
    "__pycache__",
    "node_modules",
    ".vscode",
    "validators",
    ".pytest_cache",
    ".ruff_cache",
    "htmlcov",
    "scnehaux_linter.egg-info",
    "scratch",
)

# Base Schema Keys Constants
SCHEMA_KEY_GLOBAL_CONFIG = "x-global-config"
SCHEMA_KEY_SEVERITY_LEVELS = "severity_levels"
SCHEMA_KEY_BLOCKING_SEVERITIES = "blocking_severities"

# Structure Rules
SCHEMA_KEY_STRUCTURE_RULES = "structure_rules"
SCHEMA_KEY_ARTIFACT_DIRS = "artifact_directories"
SCHEMA_KEY_IGNORED_FILES = "ignored_files"
SCHEMA_KEY_EXACT_MATCHES = "exact_matches"
SCHEMA_KEY_MAX_DIR_DEPTH = "max_directory_depth"

# Content Rules
SCHEMA_KEY_CONTENT_RULES = "content_rules"
SCHEMA_KEY_MIN_CONTENT_LENGTH = "min_content_length_chars"
SCHEMA_KEY_MAX_REVIEW_AGE = "max_review_age_days"
