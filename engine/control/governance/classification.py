from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from engine.control.config.constants import GOVERNANCE_ROOT

VISIBILITY_ENV = "SCNEHAUX_REPOSITORY_VISIBILITY"
VALID_REPOSITORY_VISIBILITIES = frozenset({"public", "private", "internal"})
VALID_CLASSIFICATIONS = frozenset(
    {"public", "internal", "restricted", "confidential"}
)
PUBLIC_ALLOWED_CLASSIFICATIONS = frozenset({"public"})


@dataclass(frozen=True)
class RepositoryVisibilityPolicy:
    repository: str
    declared_visibility: str
    observed_visibility: str


@lru_cache(maxsize=1)
def _load_manifest_repository_contract() -> tuple[str, str]:
    manifest_path = Path(GOVERNANCE_ROOT) / "00-governance" / "bootstrap-manifest.yaml"
    try:
        raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise RuntimeError(
            f"Cannot load repository visibility contract from {manifest_path}: {exc}"
        ) from exc

    if not isinstance(raw, dict):
        raise RuntimeError("bootstrap-manifest.yaml must contain a YAML mapping")

    contract = raw.get("repository_contract")
    if not isinstance(contract, dict):
        raise RuntimeError(
            "bootstrap-manifest.yaml is missing repository_contract"
        )

    repository = str(contract.get("repository", "")).strip()
    declared = str(contract.get("declared_visibility", "")).strip().lower()

    if not repository:
        raise RuntimeError("repository_contract.repository must be non-empty")
    if declared not in VALID_REPOSITORY_VISIBILITIES:
        raise RuntimeError(
            "repository_contract.declared_visibility must be one of "
            f"{sorted(VALID_REPOSITORY_VISIBILITIES)}, got {declared!r}"
        )

    return repository, declared


def repository_visibility_policy() -> RepositoryVisibilityPolicy:
    repository, declared = _load_manifest_repository_contract()

    observed_raw = os.getenv(VISIBILITY_ENV)
    observed = (
        observed_raw.strip().lower()
        if observed_raw is not None and observed_raw.strip()
        else declared
    )

    if observed not in VALID_REPOSITORY_VISIBILITIES:
        raise RuntimeError(
            f"{VISIBILITY_ENV} must be one of "
            f"{sorted(VALID_REPOSITORY_VISIBILITIES)}, got {observed!r}"
        )

    return RepositoryVisibilityPolicy(
        repository=repository,
        declared_visibility=declared,
        observed_visibility=observed,
    )


def repository_classification_findings(
    doc_meta: dict | None,
) -> list[tuple[str, str]]:
    """Return blocking repository-visibility/classification boundary findings."""
    policy = repository_visibility_policy()
    findings: list[tuple[str, str]] = []

    if policy.observed_visibility != policy.declared_visibility:
        findings.append(
            (
                "repository_visibility_mismatch",
                f"Repository '{policy.repository}' is declared "
                f"'{policy.declared_visibility}' but runtime observation is "
                f"'{policy.observed_visibility}'. Repository visibility drift "
                "must be reconciled before governance validation can continue.",
            )
        )

    if not doc_meta:
        return findings

    raw_classification = doc_meta.get("classification")
    if raw_classification in (None, ""):
        # Requiredness remains schema-owned.
        return findings

    classification = str(raw_classification).strip().lower()
    if classification not in VALID_CLASSIFICATIONS:
        # Enum validity remains schema-owned.
        return findings

    if (
        policy.observed_visibility == "public"
        and classification not in PUBLIC_ALLOWED_CLASSIFICATIONS
    ):
        findings.append(
            (
                "repository_classification_violation",
                f"Public repository '{policy.repository}' cannot contain a governed "
                f"artifact classified '{classification}'. Public repository storage "
                "provides no confidentiality boundary. Move the artifact to an "
                "approved non-public estate or classify genuinely public content "
                "as 'public'.",
            )
        )

    return findings
