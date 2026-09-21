from engine.control.framework.artifacts import validator_registry
from engine.control.framework.executable import executable_framework


# Compatibility projection: values are compiled from validator-bindings.yaml, not authored here.
VALIDATOR_REGISTRY = validator_registry()


def detect_doc_type(
    meta_id: str | None, global_rules: dict | None = None
) -> str | None:
    """Detect type from declarative artifact vocabulary; global_rules is compatibility-only."""
    del global_rules
    if not meta_id:
        return None
    doc_type = meta_id.split("-", 1)[0].upper()
    return doc_type if doc_type in executable_framework().artifact_types else None


def get_validator(doc_type: str):
    return VALIDATOR_REGISTRY.get(str(doc_type).upper())
