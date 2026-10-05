from engine.control.framework.artifacts import validator_registry
from engine.control.framework.executable import (
    ExecutableFramework,
    executable_framework,
)


# Compatibility projection: values are compiled from validator-bindings.yaml, not authored here.
VALIDATOR_REGISTRY = validator_registry()


def detect_doc_type(
    meta_id: str | None,
    global_rules: dict | None = None,
    *,
    framework: ExecutableFramework | None = None,
) -> str | None:
    """Detect type from declarative artifact vocabulary; global_rules is compatibility-only."""
    del global_rules
    if not meta_id:
        return None
    doc_type = meta_id.split("-", 1)[0].upper()
    runtime = framework if framework is not None else executable_framework()
    return doc_type if doc_type in runtime.artifact_types else None


def get_validator(doc_type: str, *, framework: ExecutableFramework | None = None):
    registry = (
        VALIDATOR_REGISTRY
        if framework is None
        else validator_registry(framework.artifacts)
    )
    return registry.get(str(doc_type).upper())
