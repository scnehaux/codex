import pytest

from engine.control.governance import classification
from engine.control.governance.classification import (
    VISIBILITY_ENV,
    repository_classification_findings,
    repository_visibility_policy,
)
from engine.control.validators import global_rules
from tests.support.validators import make_validator


@pytest.fixture(autouse=True)
def clear_visibility_cache(monkeypatch):
    # Keep the real cached function reference because individual tests replace
    # the module attribute with a plain lambda. Pytest restores monkeypatches
    # after this fixture's teardown, so calling cache_clear() through the module
    # attribute here would target the temporary lambda.
    real_loader = classification._load_manifest_repository_contract
    real_loader.cache_clear()
    monkeypatch.delenv(VISIBILITY_ENV, raising=False)
    yield
    real_loader.cache_clear()


def _contract(monkeypatch, declared="public"):
    monkeypatch.setattr(
        classification,
        "_load_manifest_repository_contract",
        lambda: ("scnehaux/codex", declared),
    )


def test_public_repository_allows_public_classification(monkeypatch):
    _contract(monkeypatch, "public")
    assert repository_classification_findings(
        {"classification": "public"}
    ) == []


@pytest.mark.parametrize(
    "value",
    ["internal", "restricted", "confidential"],
)
def test_public_repository_rejects_nonpublic_classification(monkeypatch, value):
    _contract(monkeypatch, "public")
    findings = repository_classification_findings(
        {"classification": value}
    )
    assert len(findings) == 1
    assert findings[0][0] == "repository_classification_violation"
    assert value in findings[0][1]
    assert "Public repository" in findings[0][1]


@pytest.mark.parametrize(
    "value",
    ["public", "internal", "restricted", "confidential"],
)
def test_private_repository_can_store_all_supported_classifications(
    monkeypatch, value
):
    _contract(monkeypatch, "private")
    assert repository_classification_findings(
        {"classification": value}
    ) == []


def test_visibility_observation_mismatch_is_blocking_finding(monkeypatch):
    _contract(monkeypatch, "public")
    monkeypatch.setenv(VISIBILITY_ENV, "private")

    findings = repository_classification_findings(
        {"classification": "public"}
    )
    assert findings[0][0] == "repository_visibility_mismatch"
    assert "declared 'public'" in findings[0][1]
    assert "observation is 'private'" in findings[0][1]


def test_matching_visibility_attestation_is_accepted(monkeypatch):
    _contract(monkeypatch, "public")
    monkeypatch.setenv(VISIBILITY_ENV, "public")
    policy = repository_visibility_policy()
    assert policy.declared_visibility == "public"
    assert policy.observed_visibility == "public"


def test_invalid_runtime_visibility_is_fatal(monkeypatch):
    _contract(monkeypatch, "public")
    monkeypatch.setenv(VISIBILITY_ENV, "secret")
    with pytest.raises(RuntimeError, match=VISIBILITY_ENV):
        repository_visibility_policy()


def test_missing_or_unknown_classification_stays_schema_owned(monkeypatch):
    _contract(monkeypatch, "public")
    assert repository_classification_findings({}) == []
    assert repository_classification_findings(
        {"classification": "not-a-classification"}
    ) == []


def test_missing_metadata_still_checks_visibility_attestation(monkeypatch):
    _contract(monkeypatch, "public")
    monkeypatch.setenv(VISIBILITY_ENV, "private")
    findings = repository_classification_findings(None)
    assert findings[0][0] == "repository_visibility_mismatch"


def test_global_rule_wiring_blocks_false_security_metadata(monkeypatch):
    _contract(monkeypatch, "public")
    v = make_validator(
        doc_meta={"classification": "internal"},
    )
    v.doc_type_name = "GDC"

    global_rules._validate_repository_classification(v)

    assert any(
        severity == "CRITICAL"
        and "Public repository" in message
        for severity, message in v.errors
    )

def test_manifest_loader_reads_real_repository_contract():
    repository, visibility = classification._load_manifest_repository_contract()
    assert repository == "scnehaux/codex"
    assert visibility == "public"


def test_manifest_loader_fails_closed_on_unreadable_manifest(monkeypatch):
    real_read_text = classification.Path.read_text

    def fail_read(self, *args, **kwargs):
        if self.name == "bootstrap-manifest.yaml":
            raise OSError("simulated unreadable manifest")
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(classification.Path, "read_text", fail_read)
    classification._load_manifest_repository_contract.cache_clear()

    with pytest.raises(RuntimeError, match="Cannot load repository visibility contract"):
        classification._load_manifest_repository_contract()


def test_manifest_loader_rejects_non_mapping_yaml(monkeypatch):
    monkeypatch.setattr(
        classification.Path,
        "read_text",
        lambda self, *args, **kwargs: "- list\n- not\n- mapping\n",
    )
    classification._load_manifest_repository_contract.cache_clear()

    with pytest.raises(RuntimeError, match="must contain a YAML mapping"):
        classification._load_manifest_repository_contract()


def test_manifest_loader_requires_repository_contract(monkeypatch):
    monkeypatch.setattr(
        classification.Path,
        "read_text",
        lambda self, *args, **kwargs: "target_repository: scnehaux/codex\n",
    )
    classification._load_manifest_repository_contract.cache_clear()

    with pytest.raises(RuntimeError, match="missing repository_contract"):
        classification._load_manifest_repository_contract()


def test_manifest_loader_requires_repository_name(monkeypatch):
    monkeypatch.setattr(
        classification.Path,
        "read_text",
        lambda self, *args, **kwargs: (
            "repository_contract:\n"
            "  repository: ''\n"
            "  declared_visibility: public\n"
        ),
    )
    classification._load_manifest_repository_contract.cache_clear()

    with pytest.raises(RuntimeError, match="repository.*must be non-empty"):
        classification._load_manifest_repository_contract()


def test_manifest_loader_rejects_invalid_declared_visibility(monkeypatch):
    monkeypatch.setattr(
        classification.Path,
        "read_text",
        lambda self, *args, **kwargs: (
            "repository_contract:\n"
            "  repository: scnehaux/codex\n"
            "  declared_visibility: secret\n"
        ),
    )
    classification._load_manifest_repository_contract.cache_clear()

    with pytest.raises(RuntimeError, match="declared_visibility must be one of"):
        classification._load_manifest_repository_contract()

