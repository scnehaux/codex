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
