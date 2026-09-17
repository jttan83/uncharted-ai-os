"""Deterministic HMAC blinding, balanced positions, and review gating."""

from __future__ import annotations

import hashlib
import hmac
import re
from collections.abc import Iterable, Sequence  # noqa: TC003
from dataclasses import dataclass, field
from datetime import datetime  # noqa: TC003

from .canonical import canonical_digest
from .contracts import (
    BlindCandidate,
    BlindReviewBundle,
    BlindReviewSubmission,
    Condition,
    ConditionSubmission,
    HumanReview,
    RevealEntry,
    RevealMapping,
    ReviewStage,
    Stage1Assessment,
    Stage2Comparison,
)

_BASE_SCHEDULE = (
    (Condition.A, Condition.B, Condition.C),
    (Condition.B, Condition.C, Condition.A),
    (Condition.C, Condition.A, Condition.B),
    (Condition.A, Condition.C, Condition.B),
    (Condition.C, Condition.B, Condition.A),
    (Condition.B, Condition.A, Condition.C),
)
_MIN_HOLDOUT_SIZE = 6
_MAX_HOLDOUT_SIZE = 10
_SMALL_HOLDOUT_MAX = 7
_MIN_SECRET_BYTES = 32
_CONDITION_COUNT = 3
_MIN_IDENTITY_TOKEN_LENGTH = 3
_BLIND_TEXT_PATTERNS = {
    "condition_identity": re.compile(r"\bcondition[\s_-]*[abc]\b", re.IGNORECASE),
    "evaluator_identity": re.compile(r"\b(?:independent\s+)?(?:editorial\s+)?evaluator\b", re.IGNORECASE),
    "prompt_identity": re.compile(
        r"\b(?:system\s+(?:prompt|message)|hidden\s+instructions|prompt\s+(?:asset|identity|version))\b|phase-1f-a",
        re.IGNORECASE,
    ),
    "orchestration_identity": re.compile(
        r"\b(?:orchestration|multi[-\s]?agent|agentic\s+workflow|multi[-\s]?stage\s+workflow|self[-\s]?review|"
        r"creator\s+(?:agent|role|step|output)|revision\s+(?:loop|round)|model\s+call|workflow\s+condition)\b",
        re.IGNORECASE,
    ),
}


class BlindIdentityLeakError(ValueError):
    """Raised when model-authored blind text exposes treatment machinery."""


def seed_commitment(secret_seed: bytes) -> str:
    """Commit to, but do not reveal, the secret randomization seed."""
    _validate_secret(secret_seed)
    return f"sha256:{hashlib.sha256(secret_seed).hexdigest()}"


def opaque_identifier(secret_seed: bytes, *, namespace: str, components: Iterable[str]) -> str:
    """Derive an opaque deterministic identifier without embedding condition identity."""
    _validate_secret(secret_seed)
    payload = "\x1f".join((namespace, *components)).encode()
    token = hmac.new(secret_seed, payload, hashlib.sha256).hexdigest()[:32]
    return f"{namespace}_{token}"


def balanced_position_assignments(case_ids: Sequence[str], secret_seed: bytes) -> dict[str, tuple[Condition, ...]]:
    """Assign balanced A/B/C orders for 3-case rehearsal or 6-10-case holdout."""
    _validate_secret(secret_seed)
    size = len(case_ids)
    if size not in {3, 6, 7, 8, 9, 10}:
        msg = "balanced assignment supports 3 development cases or holdout sizes 6 through 10"
        raise ValueError(msg)
    if len(set(case_ids)) != size:
        msg = "case IDs must be unique"
        raise ValueError(msg)

    labels = list(Condition)
    labels.sort(key=lambda condition: _rank(secret_seed, "label", condition.value))
    relabel = dict(zip(Condition, labels, strict=True))
    schedule = [tuple(relabel[condition] for condition in order) for order in _BASE_SCHEDULE]
    selected = [schedule[index % len(schedule)] for index in range(size)]
    selected.sort(key=lambda order: _rank(secret_seed, "schedule", "".join(item.value for item in order)))
    ordered_cases = sorted(case_ids, key=lambda case_id: _rank(secret_seed, "case", case_id))
    result = dict(zip(ordered_cases, selected, strict=True))
    _assert_balanced(result.values())
    return result


def select_repeatability_cases(case_ids: Sequence[str], secret_seed: bytes) -> tuple[str, ...]:
    """Select the frozen diagnostic subset by HMAC rank."""
    _validate_secret(secret_seed)
    size = len(case_ids)
    if size < _MIN_HOLDOUT_SIZE or size > _MAX_HOLDOUT_SIZE or len(set(case_ids)) != size:
        msg = "repeatability selection requires 6-10 unique holdout cases"
        raise ValueError(msg)
    count = 2 if size <= _SMALL_HOLDOUT_MAX else 3
    return tuple(sorted(case_ids, key=lambda case_id: _rank(secret_seed, "repeat", case_id))[:count])


def condition_execution_order(case_id: str, secret_seed: bytes) -> tuple[Condition, ...]:
    """Derive one deterministic per-case execution order for the compact block."""
    _validate_secret(secret_seed)
    return tuple(
        sorted(Condition, key=lambda condition: _rank(secret_seed, "execution", f"{case_id}:{condition.value}"))
    )


def case_review_order(case_ids: Sequence[str], secret_seed: bytes) -> tuple[str, ...]:
    """Derive the fixed review-session case order without inspecting outputs."""
    _validate_secret(secret_seed)
    if len(case_ids) != len(set(case_ids)):
        msg = "case IDs must be unique"
        raise ValueError(msg)
    return tuple(sorted(case_ids, key=lambda case_id: _rank(secret_seed, "review", case_id)))


def build_blind_bundle(
    submissions: Sequence[ConditionSubmission],
    *,
    secret_seed: bytes,
    position_orders: dict[str, tuple[Condition, ...]],
    bundle_label: str,
    reveal_custodian: RevealCustodian,
) -> BlindReviewBundle:
    """Return only blind material while sealing the mapping with its custodian."""
    _validate_secret(secret_seed)
    by_case: dict[str, dict[Condition, ConditionSubmission]] = {}
    for submission in submissions:
        conditions = by_case.setdefault(submission.case_id, {})
        if submission.condition in conditions:
            msg = f"duplicate condition for case {submission.case_id}"
            raise ValueError(msg)
        conditions[submission.condition] = submission
    if set(by_case) != set(position_orders):
        msg = "position schedule must cover exactly the submitted cases"
        raise ValueError(msg)

    candidates: list[BlindCandidate] = []
    reveal_entries: list[RevealEntry] = []
    for case_id in sorted(by_case):
        if set(by_case[case_id]) != set(Condition):
            msg = f"case {case_id} must contain exactly one A, B, and C submission"
            raise ValueError(msg)
        for position, condition in enumerate(position_orders[case_id], start=1):
            submission = by_case[case_id][condition]
            assert_blind_safe_submission(submission)
            candidate_id = opaque_identifier(
                secret_seed,
                namespace="candidate",
                components=(bundle_label, case_id, condition.value, submission.run_id),
            )
            candidates.append(
                BlindCandidate(
                    blind_candidate_id=candidate_id,
                    case_id=case_id,
                    position=position,
                    submission=BlindReviewSubmission(
                        decision=submission.normalized.decision,
                        spoken_script=submission.normalized.spoken_script,
                    ),
                )
            )
            reveal_entries.append(
                RevealEntry(
                    blind_candidate_id=candidate_id,
                    case_id=case_id,
                    condition=condition,
                    run_id=submission.run_id,
                )
            )
    bundle_id = opaque_identifier(secret_seed, namespace="bundle", components=(bundle_label,))
    mapping_id = opaque_identifier(secret_seed, namespace="mapping", components=(bundle_label,))
    bundle = BlindReviewBundle(bundle_id=bundle_id, candidates=tuple(candidates))
    mapping = RevealMapping(mapping_id=mapping_id, entries=tuple(reveal_entries))
    reveal_custodian._seal(bundle, mapping)  # noqa: SLF001 - Builder is the custodian's sealing boundary.
    return bundle


def assert_blind_safe_submission(submission: ConditionSubmission) -> None:
    """Fail closed when reviewer-visible script text exposes treatment identity."""
    fields = {"spoken_script": submission.normalized.spoken_script}
    identifiers = {
        identifier.casefold()
        for call in submission.trace.calls
        for identifier in (call.provider, call.model_identifier)
        if len(identifier.strip()) >= _MIN_IDENTITY_TOKEN_LENGTH
    }
    for field_name, value in fields.items():
        if value is None:
            continue
        leak_codes = [name for name, pattern in _BLIND_TEXT_PATTERNS.items() if pattern.search(value)]
        folded = value.casefold()
        if any(identifier in folded for identifier in identifiers):
            leak_codes.append("model_identity")
        if leak_codes:
            codes = ", ".join(sorted(set(leak_codes)))
            msg = f"blind text in {field_name} leaks treatment identity: {codes}"
            raise BlindIdentityLeakError(msg)


@dataclass(slots=True)
class ReviewGate:
    """In-memory enforcement of Stage 1 → Stage 2 → reveal sequencing."""

    blind_bundle: BlindReviewBundle
    review_id: str
    _stage: ReviewStage = field(default=ReviewStage.STAGE_1, init=False, repr=False)
    _stage_1: dict[str, Stage1Assessment] = field(default_factory=dict)
    _stage_2: dict[str, Stage2Comparison] = field(default_factory=dict)

    @property
    def stage(self) -> ReviewStage:
        return self._stage

    def lock_stage_1(self, assessment: Stage1Assessment) -> None:
        if self._stage is not ReviewStage.STAGE_1:
            msg = "Stage 1 assessments are closed"
            raise RuntimeError(msg)
        expected = {candidate.blind_candidate_id for candidate in self.blind_bundle.candidates}
        if assessment.blind_candidate_id not in expected:
            msg = "assessment refers to an unknown blind candidate"
            raise ValueError(msg)
        if assessment.blind_candidate_id in self._stage_1:
            msg = "Stage 1 assessment is already locked"
            raise RuntimeError(msg)
        self._stage_1[assessment.blind_candidate_id] = assessment

    def begin_stage_2(self) -> HumanReview:
        if self._stage is not ReviewStage.STAGE_1:
            msg = "Stage 2 can only begin once"
            raise RuntimeError(msg)
        expected = {candidate.blind_candidate_id for candidate in self.blind_bundle.candidates}
        if set(self._stage_1) != expected:
            msg = "all Stage 1 assessments must be locked before Stage 2"
            raise RuntimeError(msg)
        self._stage = ReviewStage.STAGE_2
        return self._snapshot()

    def lock_stage_2(self, comparison: Stage2Comparison) -> None:
        if self._stage is not ReviewStage.STAGE_2:
            msg = "Stage 2 is not open"
            raise RuntimeError(msg)
        case_candidates = {
            candidate.blind_candidate_id
            for candidate in self.blind_bundle.candidates
            if candidate.case_id == comparison.case_id
        }
        if not case_candidates:
            msg = "comparison refers to an unknown case"
            raise ValueError(msg)
        referenced = (
            set(comparison.acceptable_candidate_ids)
            | set(comparison.strongest_candidate_ids)
            | set(comparison.least_rewrite_candidate_ids)
        )
        if not referenced <= case_candidates:
            msg = "comparison refers to a blind candidate from another case"
            raise ValueError(msg)
        if comparison.case_id in self._stage_2:
            msg = "Stage 2 comparison is already locked"
            raise RuntimeError(msg)
        self._stage_2[comparison.case_id] = comparison

    def complete_review(self, *, timestamp: datetime) -> HumanReview:
        if self._stage is not ReviewStage.STAGE_2:
            msg = "review completion requires completed Stage 2 review"
            raise RuntimeError(msg)
        expected_cases = {candidate.case_id for candidate in self.blind_bundle.candidates}
        if set(self._stage_2) != expected_cases:
            msg = "all Stage 2 comparisons must be locked before reveal"
            raise RuntimeError(msg)
        if timestamp.tzinfo is None:
            msg = "review completion timestamp must be timezone-aware"
            raise ValueError(msg)
        self._stage = ReviewStage.REVEALED
        return self._snapshot(revealed_at=timestamp)

    def _snapshot(self, *, revealed_at: datetime | None = None) -> HumanReview:
        return HumanReview(
            review_id=self.review_id,
            stage=self._stage,
            stage_1_assessments=tuple(self._stage_1.values()),
            stage_2_comparisons=tuple(self._stage_2.values()),
            revealed_at=revealed_at,
        )


@dataclass(slots=True)
class RevealCustodian:
    """Hold the reveal mapping outside the normal review API until completion."""

    __mapping: RevealMapping | None = field(default=None, init=False, repr=False)
    __blind_bundle_digest: str | None = field(default=None, init=False, repr=False)

    def _seal(self, blind_bundle: BlindReviewBundle, mapping: RevealMapping) -> None:
        if self.__mapping is not None:
            msg = "reveal custodian is already sealed"
            raise RuntimeError(msg)
        blind_ids = {candidate.blind_candidate_id for candidate in blind_bundle.candidates}
        mapped_ids = {entry.blind_candidate_id for entry in mapping.entries}
        if blind_ids != mapped_ids:
            msg = "reveal mapping must cover the sealed blind bundle exactly"
            raise ValueError(msg)
        self.__mapping = mapping
        self.__blind_bundle_digest = canonical_digest(blind_bundle)

    def reveal(self, gate: ReviewGate) -> RevealMapping:
        """Release mapping only for the exact completed review bundle."""
        if self.__mapping is None or self.__blind_bundle_digest is None:
            msg = "reveal custodian has not been sealed"
            raise RuntimeError(msg)
        if gate.stage is not ReviewStage.REVEALED:
            msg = "mapping reveal requires a completed review"
            raise RuntimeError(msg)
        if canonical_digest(gate.blind_bundle) != self.__blind_bundle_digest:
            msg = "review gate does not match the custodian's sealed blind bundle"
            raise ValueError(msg)
        return self.__mapping


def _rank(secret_seed: bytes, namespace: str, value: str) -> bytes:
    return hmac.new(secret_seed, f"{namespace}\x1f{value}".encode(), hashlib.sha256).digest()


def _validate_secret(secret_seed: bytes) -> None:
    if len(secret_seed) < _MIN_SECRET_BYTES:
        msg = "secret seed must contain at least 256 bits"
        raise ValueError(msg)


def _assert_balanced(orders: Iterable[tuple[Condition, ...]]) -> None:
    counts = {position: dict.fromkeys(Condition, 0) for position in range(_CONDITION_COUNT)}
    for order in orders:
        if len(order) != _CONDITION_COUNT or set(order) != set(Condition):
            msg = "every position order must be a permutation of A/B/C"
            raise ValueError(msg)
        for position, condition in enumerate(order):
            counts[position][condition] += 1
    for condition_counts in counts.values():
        if max(condition_counts.values()) - min(condition_counts.values()) > 1:
            msg = "position assignment is not balanced"
            raise AssertionError(msg)
