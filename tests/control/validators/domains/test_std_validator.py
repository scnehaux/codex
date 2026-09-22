from tests.support.validators import make_validator
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))


def _global_rules():
    from tests.support.validators import runtime_rules

    return runtime_rules()


from engine.control.validators.domains.std_validator import STDValidator


def test_std_hold_status():
    rules = {"rules": {"metadata": {}}, "severity_levels": {}}
    v = make_validator(
        cls=STDValidator,
        doc_meta={"status": "hold"},
        rules=rules,
        filename="STD-001.md",
    )
    v.validate_type_specific()
    assert any("retirement phase" in msg for sev, msg in v.errors)


# ---------- GDC ----------
