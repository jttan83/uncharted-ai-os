"""Deterministic structural checks that must not be delegated to an LLM."""

from __future__ import annotations

from .canonical import canonical_digest
from .contracts import (
    CaseBrief,
    ClaimDecision,
    ClaimType,
    EditorialPackage,
    EvaluationResult,
    InternalDecision,
    StructuralValidationTrace,
    VerificationStatus,
)


def validate_editorial_package(package: EditorialPackage, brief: CaseBrief) -> StructuralValidationTrace:
    """Check objective package/Claim Map invariants with stable issue codes."""
    issues: set[str] = set()
    evidence_ids = {item.evidence_id for item in brief.evidence}
    for claim in package.claim_map.claims:
        if not set(claim.evidence_refs) <= evidence_ids:
            issues.add("unknown_evidence_reference")
        if claim.claim_type is ClaimType.FACTUAL:
            if claim.verification_status is VerificationStatus.NOT_APPLICABLE:
                issues.add("factual_status_not_applicable")
            if (
                claim.verification_status
                in {
                    VerificationStatus.VERIFIED,
                    VerificationStatus.PARTIALLY_VERIFIED,
                }
                and not claim.evidence_refs
            ):
                issues.add("verified_factual_claim_missing_evidence")
            if claim.verification_status is VerificationStatus.UNVERIFIED and claim.decision is ClaimDecision.RETAIN:
                issues.add("unverified_factual_claim_retained")
            if claim.verification_status is VerificationStatus.CONTRADICTED and claim.decision not in {
                ClaimDecision.REPLACE,
                ClaimDecision.REMOVE,
                ClaimDecision.ESCALATE,
            }:
                issues.add("contradicted_claim_not_removed")
    digest = canonical_digest(package)
    return StructuralValidationTrace(
        artifact_digest=digest,
        valid=not issues,
        issue_codes=tuple(sorted(issues)),
    )


def validate_evaluation_binding(result: EvaluationResult, package: EditorialPackage, brief: CaseBrief) -> None:
    """Ensure an evaluator result is attributable to exactly the package shown."""
    expected = canonical_digest(package)
    if result.package_digest != expected:
        msg = "evaluator result package digest does not match the evaluated package"
        raise ValueError(msg)
    if result.decision is InternalDecision.READY_FOR_HUMAN_APPROVAL:
        validation = validate_editorial_package(package, brief)
        if not validation.valid:
            msg = "ready decision conflicts with deterministic Claim Map rules"
            raise ValueError(msg)
