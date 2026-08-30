from .domains.adr_validator import ADRValidator
from .domains.sad_validator import SADValidator
from .domains.pad_validator import PADValidator
from .domains.ead_validator import EADValidator
from .domains.std_validator import STDValidator
from .domains.tdd_validator import TDDValidator
from .domains.gdc_validator import GDCValidator
from engine.control.config.constants import SCHEMA_KEY_STRUCTURE_RULES, SCHEMA_KEY_ARTIFACT_DIRS

VALIDATOR_REGISTRY = {
    "ADR": ADRValidator,
    "SAD": SADValidator,
    "PAD": PADValidator,
    "EAD": EADValidator,
    "STD": STDValidator,
    "TDD": TDDValidator,
    "GDC": GDCValidator,
}


def detect_doc_type(meta_id: str | None, global_rules: dict) -> str | None:
    """
    Determine the architecture document type based on the explicit `id` field from the document's YAML frontmatter.
    Example: 'SAD-001' -> 'SAD'

    <pre>Args:
        - meta_id (str | None): The metadata ID parsed from the document's YAML frontmatter.
        - global_rules (dict): The global rules dictionary parsed from base.schema.json.

    Returns:
        str | None: The document type prefix (e.g. 'SAD', 'PAD') or None if unknown/invalid.
    </pre>
    """
    if not meta_id:
        return None

    structure_rules = global_rules.get(SCHEMA_KEY_STRUCTURE_RULES, {})
    artifact_dirs = structure_rules.get(SCHEMA_KEY_ARTIFACT_DIRS, {})
    valid_types = artifact_dirs.keys()

    parts = meta_id.split("-")
    if not parts:
        return None

    doc_type = parts[0].upper()
    if doc_type in valid_types:
        return doc_type

    return None


def get_validator(doc_type: str):
    """
    Return the corresponding Validator subclass for the detected document type.

    Maps strings like 'SAD' to `SADValidator`, 'PAD' to `PADValidator`, etc.

    <pre>Args:
        - doc_type (str): The document type prefix (e.g. 'SAD', 'PAD').

    Returns:
        type[BaseValidator] | None: The specific validator class or None if not supported.
    </pre>
    """
    return VALIDATOR_REGISTRY.get(doc_type)
