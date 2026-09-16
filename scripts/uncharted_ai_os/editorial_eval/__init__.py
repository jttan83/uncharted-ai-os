"""Offline Phase 1F-A editorial evaluation harness.

This package is an experimental, file-backed harness. It is deliberately not a
product persistence or execution layer.
"""

from .canonical import canonical_digest, canonical_json_bytes
from .contracts import (
    BlindCandidate,
    BlindReviewBundle,
    CaseBrief,
    ConditionSubmission,
    EditorialPackage,
    EvaluationResult,
    HumanReview,
    ModelCallTrace,
    NormalizedDecision,
    ResourceUsage,
    RunTrace,
)

__all__ = [
    "BlindCandidate",
    "BlindReviewBundle",
    "CaseBrief",
    "ConditionSubmission",
    "EditorialPackage",
    "EvaluationResult",
    "HumanReview",
    "ModelCallTrace",
    "NormalizedDecision",
    "ResourceUsage",
    "RunTrace",
    "canonical_digest",
    "canonical_json_bytes",
]
