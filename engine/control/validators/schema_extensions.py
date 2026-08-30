import re
import jsonschema


SCNEHAUX_VALIDATION_KEYWORDS = frozenset(
    {
        "required_subsections",
        "prohibited_keywords",
    }
)

# Explicitly supported schema annotations. These carry authoring/documentation
# meaning but are not validation constraints and therefore must not be
# registered as fake/no-op validators.
SCNEHAUX_ANNOTATION_KEYWORDS = frozenset(
    {
        "recommended",
        "error_message",
    }
)


def _get_concept_pattern(concept: str) -> re.Pattern:
    """
    Dynamically generates a regex pattern for a required subsection concept.
    It matches the concept as a markdown header (### Concept)
    or a bolded term (**Concept**).
    """
    escaped_concept = re.escape(concept)
    pattern_str = rf"(?i)(?:^|\n)(?:\s*#{{3,5}}\s+(?:[\d\.]+\s+)?|\s*[-*]\s+\*\*\s*|\s*\*\*\s*)?{escaped_concept}\b"
    return re.compile(pattern_str)


def _validate_required_subsections(validator, required_subsections, instance, schema):
    if not isinstance(instance, str):
        return
    for concept in required_subsections:
        pattern = _get_concept_pattern(concept)
        if not pattern.search(instance):
            yield jsonschema.exceptions.ValidationError(
                f"Missing required subsection '{concept}'.",
                validator="required_subsections",
                validator_value=concept,
            )


def _validate_prohibited_keywords(validator, prohibited_keywords, instance, schema):
    if not isinstance(instance, str):
        return
    for concept in prohibited_keywords:
        pattern = re.compile(r"\b" + re.escape(concept) + r"\b", re.IGNORECASE)
        if pattern.search(instance):
            yield jsonschema.exceptions.ValidationError(
                f"Contains prohibited governance boilerplate word: '{concept}'.",
                validator="prohibited_keywords",
                validator_value=concept,
            )


ExtendedValidator = jsonschema.validators.extend(
    jsonschema.Draft7Validator,
    {
        "required_subsections": _validate_required_subsections,
        "prohibited_keywords": _validate_prohibited_keywords,
    },
)
