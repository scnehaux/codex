from __future__ import annotations

from dataclasses import dataclass

PRE_BASELINE = "pre-baseline"
BASELINE_BEARING = "baseline-bearing"
RETIRED = "retired"
TERMINAL_NON_BASELINE = "terminal-nonbaseline"

FULL = "full"
RELAXED = "relaxed"


@dataclass(frozen=True)
class AgePolicy:
    depend_on: str
    max_age_days: int
    error_message: str


@dataclass(frozen=True)
class LifecyclePolicy:
    semantic_class: str
    validation_profile: str
    age_policy: AgePolicy | None = None


DRAFT_WIP_AGE = AgePolicy(
    depend_on="created_date",
    max_age_days=30,
    error_message=(
        "Document with status '{doc_status}' has an age of {age_days} days "
        "(since {depend_on}), exceeding limit of {limit} days. "
        "Must be reviewed, finalized, or deleted."
    ),
)


LIFECYCLE_REGISTRY: dict[str, dict[str, LifecyclePolicy]] = {
    "GDC": {
        "draft": LifecyclePolicy(PRE_BASELINE, FULL),
        "approved": LifecyclePolicy(BASELINE_BEARING, FULL),
        "deprecated": LifecyclePolicy(RETIRED, FULL),
    },
    "EAD": {
        "draft": LifecyclePolicy(PRE_BASELINE, RELAXED, DRAFT_WIP_AGE),
        "approved": LifecyclePolicy(BASELINE_BEARING, FULL),
        "deprecated": LifecyclePolicy(RETIRED, FULL),
    },
    "STD": {
        "draft": LifecyclePolicy(PRE_BASELINE, RELAXED, DRAFT_WIP_AGE),
        "approved": LifecyclePolicy(BASELINE_BEARING, FULL),
        "deprecated": LifecyclePolicy(RETIRED, FULL),
    },
    "PAD": {
        "chartered": LifecyclePolicy(PRE_BASELINE, FULL),
        "draft": LifecyclePolicy(PRE_BASELINE, RELAXED, DRAFT_WIP_AGE),
        "approved": LifecyclePolicy(BASELINE_BEARING, FULL),
        "deprecated": LifecyclePolicy(RETIRED, FULL),
    },
    "SAD": {
        "chartered": LifecyclePolicy(PRE_BASELINE, FULL),
        "draft": LifecyclePolicy(PRE_BASELINE, RELAXED, DRAFT_WIP_AGE),
        "approved": LifecyclePolicy(BASELINE_BEARING, FULL),
        "deprecated": LifecyclePolicy(RETIRED, FULL),
    },
    "TDD": {
        "draft": LifecyclePolicy(PRE_BASELINE, RELAXED, DRAFT_WIP_AGE),
        "approved": LifecyclePolicy(BASELINE_BEARING, FULL),
        "deprecated": LifecyclePolicy(RETIRED, FULL),
    },
    "ADR": {
        "proposed": LifecyclePolicy(PRE_BASELINE, FULL),
        "accepted": LifecyclePolicy(BASELINE_BEARING, FULL),
        "rejected": LifecyclePolicy(TERMINAL_NON_BASELINE, FULL),
        "superseded": LifecyclePolicy(RETIRED, FULL),
        "deprecated": LifecyclePolicy(RETIRED, FULL),
    },
}


def lifecycle_policy(doc_type: str, status: str) -> LifecyclePolicy | None:
    return LIFECYCLE_REGISTRY.get(str(doc_type).upper(), {}).get(
        str(status).strip().lower()
    )


def semantic_lifecycle(doc_type: str, status: str) -> str | None:
    policy = lifecycle_policy(doc_type, status)
    return policy.semantic_class if policy else None


def validation_profile(doc_type: str, status: str) -> str:
    policy = lifecycle_policy(doc_type, status)
    return policy.validation_profile if policy else FULL


def lifecycle_age_policy(doc_type: str, status: str) -> AgePolicy | None:
    policy = lifecycle_policy(doc_type, status)
    return policy.age_policy if policy else None


def is_baseline_bearing(doc_type: str, status: str) -> bool:
    semantic = semantic_lifecycle(doc_type, status)
    return semantic in {BASELINE_BEARING, RETIRED}
