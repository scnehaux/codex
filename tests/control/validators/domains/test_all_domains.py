import inspect

from engine.control.framework.artifacts import validator_registry
from engine.control.validators import global_rules
from engine.control.validators.base import BaseValidator
from tests.support.validators import make_validator
from engine.control.validators.domains.adr_validator import ADRValidator
from engine.control.validators.domains.ead_validator import EADValidator
from engine.control.validators.domains.gdc_validator import GDCValidator
from engine.control.validators.domains.pad_validator import PADValidator
from engine.control.validators.domains.sad_validator import SADValidator
from engine.control.validators.domains.std_validator import STDValidator
from engine.control.validators.domains.tdd_validator import TDDValidator


def test_missing_doc_meta_for_all():
    rules = {"rules": {"metadata": {}}, "severity_levels": {}}
    for cls, fname in [
        (ADRValidator, "ADR-001.md"),
        (SADValidator, "SAD-001.md"),
        (PADValidator, "PAD-001.md"),
        (STDValidator, "STD-001.md"),
        (GDCValidator, "GDC-002.md"),
        (EADValidator, "EAD-001.md"),
        (TDDValidator, "TDD-001.md"),
    ]:
        v = make_validator(cls=cls, doc_meta={}, rules=rules, filename=fname)
        v.doc_meta = None  # Simulate truly missing metadata
        v.validate_type_specific()
        assert len(v.errors) == 0, f"{cls.__name__} should not crash on None doc_meta"


# CTRL-GDC-001-007: domain validators keep their logic inside validate_type_specific().
ALLOWED_OWN_MEMBERS = frozenset(
    {
        "__module__",
        "__qualname__",
        "__doc__",
        "__annotations__",
        "__firstlineno__",
        "__static_attributes__",
        "doc_type_name",
        "validate_type_specific",
    }
)


def test_domain_validators_only_override_validate_type_specific():
    registry = validator_registry()
    assert registry, "the executable framework binds no validators"
    for doc_type, cls in registry.items():
        assert issubclass(cls, BaseValidator), doc_type
        assert cls is not BaseValidator, doc_type
        own = set(vars(cls))
        assert own <= ALLOWED_OWN_MEMBERS, (doc_type, sorted(own - ALLOWED_OWN_MEMBERS))
        assert "validate_type_specific" in own, doc_type
        assert inspect.isfunction(vars(cls)["validate_type_specific"]), doc_type
        assert cls.doc_type_name == doc_type


def test_base_validator_runs_global_rules_before_domain_rules(monkeypatch):
    calls: list[str] = []

    class Probe(BaseValidator):
        doc_type_name = "TDD"

        def validate_type_specific(self) -> None:
            calls.append("domain")

    monkeypatch.setattr(
        BaseValidator, "_validate_schema", lambda self: calls.append("schema")
    )
    monkeypatch.setattr(
        global_rules, "run_common_validations", lambda v: calls.append("global")
    )
    validator = make_validator(
        cls=Probe,
        doc_meta={"id": "TDD-x-y-001-z", "status": "draft"},
        rules={"rules": {"metadata": {}}, "severity_levels": {}},
        all_doc_ids=set(),
        filename="TDD-x-y-001-z.md",
    )
    assert validator.validate() == []
    assert calls == ["schema", "global", "domain"]
