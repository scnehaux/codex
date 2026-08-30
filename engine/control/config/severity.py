from enum import Enum, unique


@unique
class SeverityRule(str, Enum):
    """
    Centralized registry of all valid Governance Rule IDs.
    Every rule listed here MUST have a corresponding severity level mapped in base.schema.json.
    """

    # 0. ENGINE EXECUTION DOMAIN (System Fatality)
    UNREADABLE_ARTIFACT = "unreadable_artifact"
    CORRUPT_FRONTMATTER = "corrupt_frontmatter"
    UNKNOWN_DOCUMENT_TYPE = "unknown_document_type"
    MISSING_VALIDATOR = "missing_validator"
    INVALID_LINT_DISABLE = "invalid_lint_disable"

    # 1. TOPOLOGY & IDENTITY DOMAIN (Graph & Lineage)
    CIRCULAR_DEPENDENCY = "circular_dependency"
    CROSS_REFERENCE_MISSING = "cross_reference_missing"
    DUPLICATE_ID = "duplicate_id"
    INLINE_REFERENCE_MISSING = "inline_reference_missing"
    ORPHAN_DOCUMENT = "orphan_document"
    TRACEABILITY_VIOLATION = "traceability_violation"
    BROKEN_INTERNAL_LINK = "broken_internal_link"

    # 2. STRUCTURAL COMPLIANCE DOMAIN (Shape & Completeness)
    MISSING_METADATA = "missing_metadata"
    MISSING_REQUIRED_SUBSECTION = "missing_required_subsection"
    MISSING_SECTION = "missing_section"
    MISSING_SECTION_KEYWORD = "missing_section_keyword"
    SCHEMA_VALIDATION_FAILED = "schema_validation_failed"
    SUBSECTION_ORDER_VIOLATION = "subsection_order_violation"

    # 3. SEMANTIC & QUALITY DOMAIN (Meaning & Language)
    AMBIGUITY_RULES = "ambiguity_rules"
    NFR_TAXONOMY_VIOLATION = "nfr_taxonomy_violation"
    PROHIBITED_WORDS = "prohibited_words"
    STRUCTURAL_INTEGRITY_VIOLATION = "structural_integrity_violation"
    STYLISTIC_DEVIATION = "stylistic_deviation"

    # 4. LIFECYCLE & ENVIRONMENT DOMAIN (Time, Space, & State)
    APPROVED_VERSION_NOT_STABLE = "approved_version_not_stable"
    ARCHITECTURE_ADMISSION_VIOLATION = "architecture_admission_violation"
    COMPLIANCE_FILENAME_MATCH = "compliance_filename_match"
    COMPLIANCE_MACRO_DIRECTORY = "compliance_macro_directory"
    LIFECYCLE_AGE_VIOLATION = "lifecycle_age_violation"
    EXCEPTION_EXPIRED = "exception_expired"
    RELAXED_VALIDATION_APPLIED = "relaxed_validation_applied"
    REVIEW_AGE_VIOLATION = "review_age_violation"
    TEMPORAL_INTEGRITY_VIOLATION = "temporal_integrity_violation"
    REPOSITORY_CLASSIFICATION_VIOLATION = "repository_classification_violation"
    REPOSITORY_VISIBILITY_MISMATCH = "repository_visibility_mismatch"
    VERSION_BUMP_REQUIRED = "version_bump_required"

    # 5. ARCHITECTURE CONSTRAINTS DOMAIN (Hard Technical Limits)
    OPERATIONAL_STABILITY_VIOLATION = "operational_stability_violation"
    TECHNOLOGY_HOLD_VIOLATION = "technology_hold_violation"
    TECHNOLOGY_POLICY_UNAVAILABLE = "technology_policy_unavailable"
    UNAPPROVED_TECHNOLOGY = "unapproved_technology"


@unique
class BlockingSeverity(str, Enum):
    """
    Standardized severity levels across the architecture linting engine.
    Used to validate the configuration values provided in base.schema.json.
    """

    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
