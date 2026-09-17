"""Persistent blind-review locks that never access reveal custody."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING

from pydantic import TypeAdapter

from .canonical import canonical_digest
from .contracts import (
    BlindCandidate,
    BlindReviewBundle,
    Condition,
    Identifier,
    PreUnblindingRecord,
    Stage1Assessment,
    Stage2Comparison,
)
from .freeze_kit import HoldoutBlindBundleRecord, _experiment_base

if TYPE_CHECKING:
    from .storage import PrivateExperimentStorage


def load_blind_bundle(
    storage: PrivateExperimentStorage,
    *,
    experiment_id: str,
    bundle_id: str,
) -> BlindReviewBundle:
    """Candidate-presentation boundary: this path has no custody dependency."""
    return _load_bundle_record(storage, experiment_id, bundle_id).bundle


def next_stage_1_candidate(
    storage: PrivateExperimentStorage,
    *,
    experiment_id: str,
    bundle_id: str,
) -> BlindCandidate | None:
    record = _load_bundle_record(storage, experiment_id, bundle_id)
    bundle = record.bundle
    ordered = sorted(
        bundle.candidates,
        key=lambda candidate: (record.case_review_order.index(candidate.case_id), candidate.position),
    )
    for candidate in ordered:
        if not _record_exists(storage, _stage_1_path(experiment_id, bundle_id, candidate.blind_candidate_id)):
            return candidate
    return None


def lock_stage_1_assessment(
    storage: PrivateExperimentStorage,
    *,
    experiment_id: str,
    bundle_id: str,
    assessment: Stage1Assessment,
) -> Path:
    bundle = load_blind_bundle(storage, experiment_id=experiment_id, bundle_id=bundle_id)
    expected = {candidate.blind_candidate_id for candidate in bundle.candidates}
    if assessment.blind_candidate_id not in expected:
        msg = "Stage 1 assessment refers to an unknown blind candidate"
        raise ValueError(msg)
    next_candidate = next_stage_1_candidate(storage, experiment_id=experiment_id, bundle_id=bundle_id)
    if next_candidate is None or next_candidate.blind_candidate_id != assessment.blind_candidate_id:
        msg = "Stage 1 assessments must be locked individually in frozen presentation order"
        raise RuntimeError(msg)
    _require_aware(assessment.locked_at, "Stage 1")
    return storage.write_json_once(
        _stage_1_path(experiment_id, bundle_id, assessment.blind_candidate_id),
        assessment,
    )


def next_stage_2_bundle(
    storage: PrivateExperimentStorage,
    *,
    experiment_id: str,
    bundle_id: str,
) -> BlindReviewBundle | None:
    record = _load_bundle_record(storage, experiment_id, bundle_id)
    bundle = record.bundle
    _require_all_stage_1_locked(storage, experiment_id, bundle)
    for case_id in record.case_review_order:
        if not _record_exists(storage, _stage_2_path(experiment_id, bundle_id, case_id)):
            candidates = tuple(candidate for candidate in bundle.candidates if candidate.case_id == case_id)
            return BlindReviewBundle(bundle_id=f"{bundle.bundle_id}_stage2", candidates=candidates)
    return None


def lock_stage_2_comparison(
    storage: PrivateExperimentStorage,
    *,
    experiment_id: str,
    bundle_id: str,
    comparison: Stage2Comparison,
) -> Path:
    bundle = load_blind_bundle(storage, experiment_id=experiment_id, bundle_id=bundle_id)
    _require_all_stage_1_locked(storage, experiment_id, bundle)
    next_bundle = next_stage_2_bundle(storage, experiment_id=experiment_id, bundle_id=bundle_id)
    if next_bundle is None or {candidate.case_id for candidate in next_bundle.candidates} != {comparison.case_id}:
        msg = "Stage 2 comparisons must be locked in frozen case order"
        raise RuntimeError(msg)
    case_candidates = {candidate.blind_candidate_id for candidate in next_bundle.candidates}
    referenced = (
        set(comparison.acceptable_candidate_ids)
        | set(comparison.strongest_candidate_ids)
        | set(comparison.least_rewrite_candidate_ids)
        | set(comparison.strongest_point_of_view_candidate_ids)
        | set(comparison.strongest_attention_candidate_ids)
        | set(comparison.strongest_payoff_candidate_ids)
        | set(comparison.strongest_voice_candidate_ids)
        | set(comparison.better_non_script_candidate_ids)
    )
    if not referenced <= case_candidates:
        msg = "Stage 2 comparison refers to a candidate outside its case"
        raise ValueError(msg)
    _require_aware(comparison.locked_at, "Stage 2")
    return storage.write_json_once(
        _stage_2_path(experiment_id, bundle_id, comparison.case_id),
        comparison,
    )


def lock_pre_unblinding_record(
    storage: PrivateExperimentStorage,
    *,
    experiment_id: str,
    bundle_id: str,
    record: PreUnblindingRecord,
) -> Path:
    bundle = load_blind_bundle(storage, experiment_id=experiment_id, bundle_id=bundle_id)
    _require_all_stage_1_locked(storage, experiment_id, bundle)
    _require_all_stage_2_locked(storage, experiment_id, bundle)
    if record.bundle_id != bundle_id:
        msg = "pre-unblinding record does not match the blind bundle"
        raise ValueError(msg)
    expected = {candidate.blind_candidate_id for candidate in bundle.candidates}
    guessed = {guess.blind_candidate_id for guess in record.identity_guesses}
    if guessed != expected:
        msg = "pre-unblinding record requires one identity guess for every candidate"
        raise ValueError(msg)
    case_by_candidate = {candidate.blind_candidate_id: candidate.case_id for candidate in bundle.candidates}
    conditions_by_case: dict[str, set[Condition]] = {}
    for guess in record.identity_guesses:
        conditions_by_case.setdefault(case_by_candidate[guess.blind_candidate_id], set()).add(guess.guessed_condition)
    if any(conditions != set(Condition) for conditions in conditions_by_case.values()):
        msg = "identity guesses for each case must assign A, B, and C exactly once"
        raise ValueError(msg)
    return storage.write_json_once(_pre_unblinding_path(experiment_id, bundle_id), record)


def locked_review_digests(
    storage: PrivateExperimentStorage,
    *,
    experiment_id: str,
    bundle_id: str,
) -> dict[str, str]:
    """Verify every lock and return content digests for the reveal audit."""
    bundle = load_blind_bundle(storage, experiment_id=experiment_id, bundle_id=bundle_id)
    _require_all_stage_1_locked(storage, experiment_id, bundle)
    _require_all_stage_2_locked(storage, experiment_id, bundle)
    try:
        pre_unblinding = storage.read_model(
            _pre_unblinding_path(experiment_id, bundle_id),
            PreUnblindingRecord,
        )
    except FileNotFoundError as exc:
        msg = "pre-unblinding record must be locked before reveal"
        raise RuntimeError(msg) from exc
    return {
        "blind_bundle": canonical_digest(bundle),
        "stage_1": canonical_digest(
            [
                storage.read_model(
                    _stage_1_path(experiment_id, bundle_id, candidate.blind_candidate_id),
                    Stage1Assessment,
                ).model_dump(mode="json")
                for candidate in bundle.candidates
            ]
        ),
        "stage_2": canonical_digest(
            [
                storage.read_model(
                    _stage_2_path(experiment_id, bundle_id, case_id),
                    Stage2Comparison,
                ).model_dump(mode="json")
                for case_id in dict.fromkeys(candidate.case_id for candidate in bundle.candidates)
            ]
        ),
        "pre_unblinding": canonical_digest(pre_unblinding),
    }


def _require_all_stage_1_locked(
    storage: PrivateExperimentStorage,
    experiment_id: str,
    bundle: BlindReviewBundle,
) -> None:
    for candidate in bundle.candidates:
        path = _stage_1_path(experiment_id, bundle.bundle_id, candidate.blind_candidate_id)
        try:
            storage.read_model(path, Stage1Assessment)
        except FileNotFoundError as exc:
            msg = "all Stage 1 assessments must be locked before Stage 2"
            raise RuntimeError(msg) from exc


def _require_all_stage_2_locked(
    storage: PrivateExperimentStorage,
    experiment_id: str,
    bundle: BlindReviewBundle,
) -> None:
    for case_id in dict.fromkeys(candidate.case_id for candidate in bundle.candidates):
        try:
            storage.read_model(_stage_2_path(experiment_id, bundle.bundle_id, case_id), Stage2Comparison)
        except FileNotFoundError as exc:
            msg = "all Stage 2 comparisons must be locked before pre-unblinding"
            raise RuntimeError(msg) from exc


def _record_exists(storage: PrivateExperimentStorage, relative_path: str) -> bool:
    try:
        storage.read_json(relative_path)
    except FileNotFoundError:
        return False
    return True


def _load_bundle_record(
    storage: PrivateExperimentStorage,
    experiment_id: str,
    bundle_id: str,
) -> HoldoutBlindBundleRecord:
    return storage.read_model(_bundle_path(experiment_id, bundle_id), HoldoutBlindBundleRecord)


def _bundle_path(experiment_id: str, bundle_id: str) -> str:
    return f"{_experiment_base(experiment_id)}/presentations/{_identifier(bundle_id)}.json"


def _stage_1_path(experiment_id: str, bundle_id: str, candidate_id: str) -> str:
    return (
        f"{_experiment_base(experiment_id)}/reviews/{_identifier(bundle_id)}"
        f"/stage_1/{_identifier(candidate_id)}.json"
    )


def _stage_2_path(experiment_id: str, bundle_id: str, case_id: str) -> str:
    return (
        f"{_experiment_base(experiment_id)}/reviews/{_identifier(bundle_id)}"
        f"/stage_2/{_identifier(case_id)}.json"
    )


def _pre_unblinding_path(experiment_id: str, bundle_id: str) -> str:
    return f"{_experiment_base(experiment_id)}/reviews/{_identifier(bundle_id)}/pre_unblinding.json"


def _identifier(value: str) -> str:
    return TypeAdapter(Identifier).validate_python(value)


def _require_aware(value: object, label: str) -> None:
    if getattr(value, "tzinfo", None) is None:
        msg = f"{label} lock timestamp must be timezone-aware"
        raise ValueError(msg)
