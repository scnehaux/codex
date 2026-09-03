import os
import re
import jsonschema
from referencing import Registry, Resource
from engine.control.config.constants import BASE_SCHEMA_PATH
from engine.control.config.loader import load_json_schema_file
from .schema_extensions import ExtendedValidator

_base_schema_cache = None


def _get_base_schema():
    """
    Load and cache the global base JSON schema for document validation.
    Prevents redundant disk reads by storing the schema in memory upon first invocation.

    Note on Error Handling:
    We do not wrap this in try/except because `cli.py` already loaded and validated
    this exact schema during its boot sequence. If an error occurs here, it means
    the file was deleted or corrupted mid-execution. In that impossible state,
    `load_json_schema_file` will correctly crash the program with a ValueError or FileNotFoundError.

    <pre>Args:
        None

    Returns:
        dict: The parsed JSON dictionary of the base schema.
    </pre>
    """
    global _base_schema_cache
    if _base_schema_cache is None:
        _base_schema_cache = load_json_schema_file(BASE_SCHEMA_PATH)
    return _base_schema_cache


class BaseValidator:
    """
    Base class for all document type validators.

    Orchestrates the 3-phase validation lifecycle for Markdown architecture documents:
    1. JSON Schema Validation (structural and pattern compliance).
    2. Global Rules Validation (repository-wide governance constraints).
    3. Domain-Specific Validation (implemented by subclasses like ADRValidator).

    Responsibilities include state management of the document being linted,
    parsing of `lint_disable` inline directives, and uniform error reporting
    with severity level resolution.
    """

    # --- Instance Variable Type Declarations ---
    file_path: str  # Absolute path to the markdown file being validated
    content: str  # The raw markdown text content
    doc_meta: dict | None  # Parsed YAML frontmatter (metadata)
    global_rules: dict  # Parsed base.schema.json containing repository-wide rules
    domain_schema: dict  # Parsed domain-specific schema (e.g., adr.schema.json)
    all_doc_ids: (
        set  # Registry of all known document IDs to check for orphans/duplicates
    )
    all_doc_metadata: dict  # Registry of all document metadata for cross-referencing
    errors: list[
        tuple[str, str]
    ]  # Accumulated list of (severity_level, error_message) tuples
    rel_path: str  # Relative path from execution root (used for display)
    filename: str  # Base name of the file (e.g., '1234-my-adr.md')
    block_disables: (
        dict  # Maps rule_id -> list of (start_line, end_line, reason) tuples
    )
    rejected_disables: (
        set  # Set of CRITICAL rule IDs that the user tried to disable but were rejected
    )
    severity_levels: dict  # Flattened mapping of SeverityRule -> severity string
    blocking_severities: tuple  # Tuple of strings representing blocking severity levels
    # -------------------------------------------

    doc_type_name: str = "Unknown"

    def __init__(
        self,
        file_path: str,
        content: str,
        doc_meta: dict,
        global_rules: dict,
        domain_schema: dict,
        all_doc_ids: set,
        all_doc_metadata: dict,
        severity_levels: dict,
        blocking_severities: tuple,
    ):
        self.file_path = file_path
        self.content = content
        self.doc_meta = doc_meta
        self.global_rules = global_rules
        self.domain_schema = domain_schema
        self.all_doc_ids = all_doc_ids
        self.all_doc_metadata = all_doc_metadata or {}
        self.severity_levels = severity_levels
        self.blocking_severities = blocking_severities
        self.errors: list[tuple[str, str]] = []
        # Cross-drive paths are already blocked by crawler.py, so relpath is guaranteed to succeed.
        self.rel_path = os.path.relpath(file_path, ".").replace("\\", "/")
        self.filename = os.path.basename(file_path)

        # --- PARSE INLINE LINT DIRECTIVES ---
        # Extracts `lint_disable` directives to suppress specific rules based on line ranges.
        #
        # Supported Forms:
        # 1. Block-Scoped: <!-- lint_disable_start: rule_a (reason: approved) --> ... <!-- lint_disable_end -->
        #    (Suppresses 'rule_a' strictly between the start and end tags)
        # 2. Inline: <!-- lint_disable: rule_b -->
        #    (Suppresses 'rule_b' from the line it is declared downwards to the end of the document)
        #
        # Notes:
        # - Reasons are optional but recommended for auditing.
        # - Unclosed `_start` tags will automatically extend to the end of the document.
        # - Code blocks are stripped first (replaced with blank lines) so illustrative examples aren't parsed.
        # ------------------------------------
        # Maps rule_id -> list of (start_line, end_line, reason) tuples
        self.block_disables: dict[str, list[tuple[int, float, str | None]]] = {}

        # Set of CRITICAL rule IDs that the user tried to disable, but the engine rejected.
        # Example: {"structural_integrity_violation"}
        self.rejected_disables: set[str] = set()

        self._parse_lint_directives()

    def _extract_rules_and_reason(
        self, directive_payload: str
    ) -> tuple[list[str], str | None]:
        """
        Parses the payload of a `lint_disable` tag to extract rule IDs and an optional reason.

        Args:
            directive_payload (str): The string inside the tag (e.g., "rule_a, rule_b (reason: waiver)").

        Returns:
            tuple: A list of unique rule IDs and the extracted reason string (or None).
        """
        reason = None
        reason_match = re.search(r"\(reason:\s*(.*?)\)\s*$", directive_payload)
        if reason_match:
            reason = reason_match.group(1).strip()
            directive_payload = directive_payload[: reason_match.start()].strip()

        rule_ids = []
        if directive_payload:
            for raw_rule in directive_payload.split(","):
                rule_id = raw_rule.strip()
                # Defensive check: ensure the rule ID only contains valid characters.
                # This prevents crashes from typos (like trailing commas resulting in empty strings) or garbage input.
                if re.fullmatch(r"[a-zA-Z0-9_]+", rule_id):
                    rule_ids.append(rule_id)

        # Deduplicate rule_ids while preserving order (e.g. for <!-- lint_disable: rule_a, rule_a -->)
        rule_ids = list(dict.fromkeys(rule_ids))

        return rule_ids, reason

    def _close_all_active_blocks(
        self,
        closing_line_num: float,
        unclosed_start_tags_by_rule: dict[str, list[tuple[int, str | None]]],
    ):
        """
        Drains all currently unclosed `_start` tags and commits them as finalized block coordinates.
        This is triggered either when a `_end` tag is encountered, or at the very end of the file
        (using `float('inf')` to keep the block open indefinitely).

        Args:
            closing_line_num (float): The line number where the block ends (or infinity).
            unclosed_start_tags_by_rule (dict): A mapping of rule IDs to their pending (start_line, reason) tuples.
        """
        for rule_id, start_tags in unclosed_start_tags_by_rule.items():
            while start_tags:
                start_line, reason = start_tags.pop()
                self.block_disables.setdefault(rule_id, []).append(
                    (start_line, closing_line_num, reason)
                )

    def _parse_lint_directives(self):
        """
        Extract `<!-- lint_disable... -->` comments from the document to build an O(1) lookup
        table for active disables per line.

        This uses an AST-driven approach:
        1. `html_block` (standalone comment): Disables the rule for its own line and the next adjacent line.
        2. `html_inline` (embedded comment): Disables the rule for the entire parent block (e.g. paragraph).
        3. `_start` / `_end` tags: Explicitly open and close suppression blocks.
        4. Validates that the suppressed `rule_id` actually exists in the schema.
        """
        from markdown_it import MarkdownIt

        md = MarkdownIt()
        tokens = md.parse(self.content)

        unclosed_start_tags_by_rule: dict[str, list[tuple[int, str | None]]] = {}
        directive_pattern = re.compile(
            r"<!--\s*lint_disable(?:_start|_end)?(?::\s*(.*?))?\s*-->"
        )

        def process_match(match, map_range):
            if not match or not map_range:
                return

            tag_type = None
            full_tag = match.group(0)
            if "lint_disable_start" in full_tag:
                tag_type = "_start"
            elif "lint_disable_end" in full_tag:
                tag_type = "_end"

            # map_range is 0-indexed [start, end)
            start_line = map_range[0] + 1
            end_line = map_range[1]

            if tag_type == "_end":
                self._close_all_active_blocks(end_line, unclosed_start_tags_by_rule)
                return

            directive_payload = match.group(1) or ""
            rule_ids, reason = self._extract_rules_and_reason(directive_payload)

            for rule_id in rule_ids:
                if rule_id not in self.severity_levels:
                    # Fail fast on typo rule IDs so engineers aren't left confused
                    self.add_error(
                        "invalid_lint_disable",
                        f"Unrecognized rule ID '{rule_id}' in disable directive. Typo?",
                        line_num=start_line,
                    )
                    continue

                if tag_type == "_start":
                    unclosed_start_tags_by_rule.setdefault(rule_id, []).append(
                        (start_line, reason)
                    )
                else:
                    # Inline disable: suppress for the AST node's range + 1 next line
                    # This gracefully handles both inline comments (suppresses the paragraph)
                    # and standalone block comments (suppresses the comment line + the next line)
                    self.block_disables.setdefault(rule_id, []).append(
                        (start_line, end_line + 1, reason)
                    )

        for t in tokens:
            if t.type == "html_block":
                for match in directive_pattern.finditer(t.content):
                    process_match(match, t.map)
            elif t.type == "inline" and t.children:
                for child in t.children:
                    if child.type == "html_inline":
                        for match in directive_pattern.finditer(child.content):
                            process_match(match, t.map)

        # Any unclosed active blocks go to infinity
        self._close_all_active_blocks(float("inf"), unclosed_start_tags_by_rule)

    def add_error(self, rule_id: str, message: str, line_num: int | None = None):
        """
        Record a validation finding. Resolves the severity level from global governance rules.
        If the rule is suppressed via a `lint_disable` directive (either block or inline), the finding is dropped UNLESS
        its severity is CRITICAL, in which case the disable is rejected and the finding fires anyway.

        <pre>Args:
            - rule_id (str): The rule ID triggering the error.
            - message (str): The specific validation error message.
            - line_num (int | None, optional): The line number where the error occurred.

        Returns:
            None
        </pre>
        """
        # By this point, cli.py has already validated that all RuleIDs exist in severity_levels
        try:
            severity = self.severity_levels[rule_id]
        except KeyError:
            raise RuntimeError(
                f"Rule '{rule_id}' triggered but not found in severity_levels mapping. Execution blocked due to configuration drift."
            )

        is_disabled = False
        if rule_id in self.block_disables:
            check_line = line_num if line_num is not None else 1
            for start_line, end_line, _reason in self.block_disables[rule_id]:
                if start_line <= check_line <= end_line:
                    is_disabled = True
                    break

        if is_disabled:
            # Blocking severity findings can never be silenced by an inline directive.
            # The disable is rejected (recorded for the audit) and the finding still fires.
            if severity in self.blocking_severities:
                self.rejected_disables.add(rule_id)
            else:
                return

        self.errors.append((severity, message))

    def validate(self) -> list[tuple[str, str]]:
        """
        Execute the complete validation lifecycle for this document.

        The lifecycle runs in three sequential phases:
        1. JSON-Schema Validation: Strict structural and pattern checking based on the domain schema.
        2. Global Rules Validation: Execution of governance rules applicable to all documents.
        3. Domain-Specific Rules: Execution of custom rules defined in the specific subclass validator.
        <pre>Args:
            None

        Returns:
            list[tuple[str, str]]: An aggregated list of (severity, message) error tuples.
        </pre>
        """
        # @flow-validator: Validate(("3.0. <b>validate()</b>: Start lifecycle")) --> ValidateSchema["3.1. <b>_validate_schema()</b>: JSON Schema Check"]
        self._validate_schema()
        from .global_rules import run_common_validations

        # @flow-validator: ValidateSchema --> GlobalRules["3.2. <b>global_rules.py</b>: run_common_validations()"]
        run_common_validations(self)
        # @flow-validator: GlobalRules --> TypeSpecific["3.3. <b>validate_type_specific()</b>: Domain Rules"]
        self.validate_type_specific()
        # @flow-validator: TypeSpecific --> ReturnErrors(("3.4. Return accumulated errors"))
        return self.errors

    def _validate_schema(self):
        """
        Execute JSON-Schema validation against the document's metadata block and section bodies.
        Translates raw jsonschema exceptions into actionable, governance-aware error messages
        (e.g., mapping pattern failures to missing keywords).
        """
        from engine.control.parsing.markdown_ast import extract_sections_normalized
        import datetime

        # Schemas declare required sections by Title-Case, unnumbered name, and their
        # content_rules run `pattern` checks against the section's text. Map each
        # normalized section title to its content so both presence (`required`) and
        # content patterns validate, and expose `filename` so guideline-only
        # conditional rules (if filename ~ *-guideline.md) gate correctly.
        # @flow-validator: subgraph SchemaPhase[3.1. JSON Schema Validation Phase]
        # @flow-validator: ValidateSchema --> ExtractSections["<b>extract_sections_normalized()</b>: Parse sections"]
        sections = extract_sections_normalized(self.content)

        def convert_dates(obj):
            if isinstance(obj, dict):
                return {k: convert_dates(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_dates(i) for i in obj]
            elif isinstance(obj, (datetime.date, datetime.datetime)):
                return obj.isoformat()
            return obj

        doc_instance = {
            "doc_meta": convert_dates(self.doc_meta),
            "filename": self.filename,
        }
        for title, body in sections.items():
            doc_instance[title] = body

        # @flow-validator: ExtractSections --> BuildDocInstance["Build validation instance dict"]
        # @flow-validator: BuildDocInstance --> ExecJsonSchema["<b>ExtendedValidator.iter_errors()</b>"]
        base_schema = _get_base_schema()
        base_id = base_schema.get(
            "$id",
            "https://scnehaux.com/codex/gov/guidelines/schemas/base.schema.json",
        )
        registry = Registry().with_resource(
            base_id, Resource.from_contents(base_schema)
        )
        validator = ExtendedValidator(
            schema=self.domain_schema,
            registry=registry,
            format_checker=jsonschema.FormatChecker(),
        )
        for e in validator.iter_errors(doc_instance):
            # @flow-validator: ExecJsonSchema -->|ValidationError| MapError["Map jsonschema errors to category"]
            path = " -> ".join([str(p) for p in e.absolute_path]) or "root"

            # Map common errors to clearer categories.
            if e.validator == "required":
                category = "missing_section" if path == "root" else "missing_metadata"
                message = f"Schema validation failed at {path}: {e.message}"
            elif e.validator == "enum":
                category = "missing_metadata"
                message = f"Schema validation failed at {path}: {e.message}"
            elif e.validator == "pattern":
                category = "missing_section_keyword"
                message = f"Section '{path}' is missing required content (expected pattern: {e.validator_value})."
            elif e.validator == "required_subsections":
                category = "missing_required_subsection"
                message = f"Section '{path}' is missing required subsection '{e.validator_value}'."
            elif e.validator == "prohibited_keywords":
                category = "prohibited_words"
                message = f"Section '{path}' contains prohibited governance boilerplate word: '{e.validator_value}'."
            else:
                category = "schema_validation_failed"
                message = f"Schema validation failed at {path}: {e.message}"

            # @flow-validator: MapError --> AddError["<b>add_error()</b>: Record finding"]
            self.add_error(category, message)
        # @flow-validator: end

    def validate_type_specific(self):
        """Override in subclass for doc-type-specific checks."""
        pass
