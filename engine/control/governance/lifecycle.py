from __future__ import annotations

from engine.control.framework.artifacts import (
    BASELINE_BEARING,
    FULL,
    PRE_BASELINE,
    RELAXED,
    RETIRED,
    TERMINAL_NON_BASELINE,
    AgePolicy,
    LifecyclePolicy,
    artifact_runtime,
)


__all__ = [
    "PRE_BASELINE",
    "BASELINE_BEARING",
    "RETIRED",
    "TERMINAL_NON_BASELINE",
    "FULL",
    "RELAXED",
    "AgePolicy",
    "LifecyclePolicy",
    "lifecycle_policy",
    "semantic_lifecycle",
    "validation_profile",
    "lifecycle_age_policy",
    "is_baseline_bearing",
]


def lifecycle_policy(doc_type: str, status: str) -> LifecyclePolicy | None:
    return (
        artifact_runtime()
        .lifecycle.get(str(doc_type).upper(), {})
        .get(str(status).strip().lower())
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
