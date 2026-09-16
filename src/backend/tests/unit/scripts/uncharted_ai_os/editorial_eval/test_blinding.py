from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

import pytest

from scripts.uncharted_ai_os.editorial_eval.blinding import (
    BlindIdentityLeakError,
    RevealCustodian,
    ReviewGate,
    assert_blind_safe_submission,
    balanced_position_assignments,
    build_blind_bundle,
    case_review_order,
    condition_execution_order,
    opaque_identifier,
    select_repeatability_cases,
)
from scripts.uncharted_ai_os.editorial_eval.contracts import (
    Condition,
    RevealEntry,
    RevealMapping,
    ReviewStage,
    RewriteBurden,
    Stage1Assessment,
    Stage2Comparison,
)

from .conftest import make_submission

SECRET = bytes(range(32))
LOCK_TIME = datetime(2026, 2, 1, tzinfo=timezone.utc)


@pytest.mark.parametrize("size", range(6, 11))
def test_balanced_positions_for_holdout_sizes_six_through_ten(size: int) -> None:
    case_ids = [f"case_{index:02d}" for index in range(size)]
    assignments = balanced_position_assignments(case_ids, SECRET)
    for position in range(3):
        counts = Counter(order[position] for order in assignments.values())
        assert max(counts.values()) - min(counts.values()) <= 1


def test_blinding_is_deterministic_and_ids_are_opaque() -> None:
    first = opaque_identifier(SECRET, namespace="candidate", components=("case_01", "A", "run_01"))
    second = opaque_identifier(SECRET, namespace="candidate", components=("case_01", "A", "run_01"))
    assert first == second
    assert "case_01" not in first
    assert "run_01" not in first
    assert "A" not in first
    assert len(first) == len("candidate_") + 32


def test_blind_bundle_has_no_condition_or_evaluator_leak_and_mapping_is_bijective() -> None:
    case_ids = ["case_01", "case_02", "case_03"]
    submissions = [
        make_submission(condition, case_id, f"{case_id}_{condition.value.lower()}")
        for case_id in case_ids
        for condition in Condition
    ]
    positions = balanced_position_assignments(case_ids, SECRET)
    custodian = RevealCustodian()
    bundle = build_blind_bundle(
        submissions,
        secret_seed=SECRET,
        position_orders=positions,
        bundle_label="development",
        reveal_custodian=custodian,
    )
    serialized = bundle.model_dump_json()
    assert '"condition"' not in serialized
    assert "evaluator" not in serialized.lower()
    assert not hasattr(bundle, "reveal_mapping")
    gate = ReviewGate(blind_bundle=bundle, review_id="review_unfinished")
    assert not hasattr(gate, "reveal_mapping")
    assert not hasattr(custodian, "mapping")
    with pytest.raises(AttributeError):
        gate.stage = ReviewStage.REVEALED
    with pytest.raises(RuntimeError, match="completed review"):
        custodian.reveal(gate)


def test_reveal_map_requires_complete_condition_set_per_case() -> None:
    with pytest.raises(ValueError, match="exactly one A, B, and C"):
        RevealMapping(
            mapping_id="mapping_invalid",
            entries=(
                RevealEntry(
                    blind_candidate_id="candidate_one",
                    case_id="case_01",
                    condition=Condition.A,
                    run_id="run_one",
                ),
            ),
        )


def test_reveal_map_rejects_a_a_b_c_membership() -> None:
    with pytest.raises(ValueError, match="exactly one A, B, and C"):
        RevealMapping(
            mapping_id="mapping_invalid_membership",
            entries=tuple(
                RevealEntry(
                    blind_candidate_id=f"candidate_{index}",
                    case_id="case_01",
                    condition=condition,
                    run_id=f"run_{index}",
                )
                for index, condition in enumerate(
                    (Condition.A, Condition.A, Condition.B, Condition.C),
                    start=1,
                )
            ),
        )


def test_repeatability_selection_is_deterministic_and_sized_by_protocol() -> None:
    for size, expected in ((6, 2), (7, 2), (8, 3), (9, 3), (10, 3)):
        case_ids = [f"case_{index:02d}" for index in range(size)]
        first = select_repeatability_cases(case_ids, SECRET)
        assert first == select_repeatability_cases(case_ids, SECRET)
        assert len(first) == expected
        assert set(first) <= set(case_ids)


def test_execution_and_case_review_orders_are_deterministic_permutations() -> None:
    case_ids = ["case_01", "case_02", "case_03"]
    execution = condition_execution_order("case_01", SECRET)
    assert execution == condition_execution_order("case_01", SECRET)
    assert set(execution) == set(Condition)
    review = case_review_order(case_ids, SECRET)
    assert review == case_review_order(case_ids, SECRET)
    assert set(review) == set(case_ids)


def test_review_gate_enforces_stage_one_then_stage_two_then_reveal() -> None:
    case_ids = ["case_01", "case_02", "case_03"]
    submissions = [
        make_submission(condition, case_id, f"{case_id}_{condition.value.lower()}")
        for case_id in case_ids
        for condition in Condition
    ]
    custodian = RevealCustodian()
    bundle = build_blind_bundle(
        submissions,
        secret_seed=SECRET,
        position_orders=balanced_position_assignments(case_ids, SECRET),
        bundle_label="development",
        reveal_custodian=custodian,
    )
    gate = ReviewGate(blind_bundle=bundle, review_id="review_development")
    with pytest.raises(RuntimeError, match="Stage 1"):
        gate.begin_stage_2()
    with pytest.raises(RuntimeError, match="Stage 2"):
        gate.complete_review(timestamp=LOCK_TIME)
    for candidate in bundle.candidates:
        gate.lock_stage_1(
            Stage1Assessment(
                blind_candidate_id=candidate.blind_candidate_id,
                category_appropriate=True,
                rewrite_burden=RewriteBurden.MINOR,
                confidence="medium",
                reasons=("Development rehearsal judgment.",),
                preference_basis="editorial",
                locked_at=LOCK_TIME,
            )
        )
    stage_two_review = gate.begin_stage_2()
    assert stage_two_review.stage is ReviewStage.STAGE_2
    with pytest.raises(RuntimeError, match="Stage 2"):
        gate.complete_review(timestamp=LOCK_TIME)
    for case_id in case_ids:
        candidate_ids = tuple(
            candidate.blind_candidate_id for candidate in bundle.candidates if candidate.case_id == case_id
        )
        gate.lock_stage_2(
            Stage2Comparison(
                case_id=case_id,
                acceptable_candidate_ids=candidate_ids,
                strongest_candidate_ids=(candidate_ids[0],),
                least_rewrite_candidate_ids=(candidate_ids[0],),
                reasons=("Development-only comparison.",),
                confidence="medium",
                locked_at=LOCK_TIME,
            )
        )
    review = gate.complete_review(timestamp=LOCK_TIME)
    assert review.stage is ReviewStage.REVEALED
    revealed_mapping = custodian.reveal(gate)
    assert len({entry.blind_candidate_id for entry in revealed_mapping.entries}) == len(revealed_mapping.entries)
    assert {candidate.blind_candidate_id for candidate in bundle.candidates} == {
        entry.blind_candidate_id for entry in revealed_mapping.entries
    }
    with pytest.raises(RuntimeError):
        gate.lock_stage_1(review.stage_1_assessments[0])


@pytest.mark.parametrize(
    ("leaked_text", "leak_code"),
    [
        ("Condition A produced this candidate.", "condition_identity"),
        ("The independent evaluator produced this candidate.", "evaluator_identity"),
        ("The system prompt required this candidate.", "prompt_identity"),
        ("A multi-agent workflow produced this candidate.", "orchestration_identity"),
    ],
)
def test_free_text_identity_leak_is_rejected_without_rewriting(leaked_text, leak_code) -> None:
    submission = make_submission(Condition.A, "case_01", "leak").model_copy(
        update={
            "normalized": make_submission(Condition.A, "case_01", "leak").normalized.model_copy(
                update={"spoken_script": leaked_text}
            )
        }
    )
    with pytest.raises(BlindIdentityLeakError, match=leak_code):
        assert_blind_safe_submission(submission)
