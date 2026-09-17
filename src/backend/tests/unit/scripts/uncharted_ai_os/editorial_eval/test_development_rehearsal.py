from __future__ import annotations

import subprocess

import pytest

from scripts.uncharted_ai_os.editorial_eval.blinding import RevealCustodian, ReviewGate
from scripts.uncharted_ai_os.editorial_eval.contracts import (
    CandidateUseDecision,
    Condition,
    DatasetClass,
    NormalizedDecision,
    NormalizedSubmission,
    ReviewStage,
    RewriteBurden,
    Stage1Assessment,
    Stage2Comparison,
)
from scripts.uncharted_ai_os.editorial_eval.invokers import ScriptedModelInvoker, ScriptedStep
from scripts.uncharted_ai_os.editorial_eval.rehearsal import (
    DevelopmentWorkflows,
    build_development_blind_bundle,
    build_single_case_development_blind_bundle,
    load_development_cases,
    persist_development_blind_bundle,
    persist_development_execution,
    persist_development_failure,
    run_development_case,
    run_development_case_with_persistence,
)
from scripts.uncharted_ai_os.editorial_eval.storage import PrivateExperimentStorage
from scripts.uncharted_ai_os.editorial_eval.workflows import (
    ConditionAWorkflow,
    ConditionBWorkflow,
    ConditionCWorkflow,
    CreatorResult,
    SelfReviewDecision,
    SelfReviewResult,
)

from .conftest import FIXED_TIME, make_judgment, make_package, make_submission
from .test_workflows import fixed_clock, run_ids

SECRET = bytes(reversed(range(32)))


def test_single_development_case_blinding_and_review_gating() -> None:
    case = load_development_cases()[1]
    submissions = tuple(
        make_submission(condition, case.case_id, f"single_{condition.value.lower()}") for condition in Condition
    )
    custodian = RevealCustodian()
    bundle = build_single_case_development_blind_bundle(
        case,
        submissions,
        secret_seed=SECRET,
        reveal_custodian=custodian,
    )

    assert len(bundle.candidates) == 3
    assert {candidate.position for candidate in bundle.candidates} == {1, 2, 3}
    assert {
        (candidate.submission.decision, candidate.submission.spoken_script)
        for candidate in bundle.candidates
    } == {
        (submission.normalized.decision, submission.normalized.spoken_script)
        for submission in submissions
    }
    assert all(not hasattr(candidate.submission, "explanation") for candidate in bundle.candidates)
    assert all(not hasattr(candidate.submission, "next_action") for candidate in bundle.candidates)
    assert all(candidate.blind_candidate_id not in {"A", "B", "C"} for candidate in bundle.candidates)
    assert not hasattr(bundle, "reveal_mapping")

    gate = ReviewGate(blind_bundle=bundle, review_id="single_case_review")
    for candidate in bundle.candidates:
        gate.lock_stage_1(
            Stage1Assessment(
                blind_candidate_id=candidate.blind_candidate_id,
                category_appropriate=True,
                use_decision=CandidateUseDecision.MINOR_EDIT,
                rewrite_burden=RewriteBurden.MINOR,
                main_strength="Clear editorial judgment.",
                main_weakness="Requires a localized edit.",
                confidence="medium",
                reasons=("Development-only scripted review.",),
                preference_basis="editorial",
                locked_at=FIXED_TIME,
            )
        )
    gate.begin_stage_2()
    ids = tuple(candidate.blind_candidate_id for candidate in bundle.candidates)
    gate.lock_stage_2(
        Stage2Comparison(
            case_id=case.case_id,
            acceptable_candidate_ids=ids,
            strongest_candidate_ids=(ids[0],),
            least_rewrite_candidate_ids=(ids[0],),
            strongest_point_of_view_candidate_ids=(ids[0],),
            strongest_attention_candidate_ids=(ids[0],),
            strongest_payoff_candidate_ids=(ids[0],),
            strongest_voice_candidate_ids=(ids[0],),
            better_non_script_candidate_ids=(),
            reasons=("Development-only scripted comparison.",),
            editorial_personal_difference="No difference in this synthetic review.",
            uncertainty_and_change_evidence="No additional evidence specified.",
            confidence="medium",
            locked_at=FIXED_TIME,
        )
    )
    review = gate.complete_review(timestamp=FIXED_TIME)
    mapping = custodian.reveal(gate)
    assert review.stage is ReviewStage.REVEALED
    assert len(mapping.entries) == 3
    assert {entry.condition for entry in mapping.entries} == set(Condition)

    branch_bundle = build_development_blind_bundle(
        submissions,
        secret_seed=SECRET,
        reveal_custodian=RevealCustodian(),
        case=case,
    )
    assert len(branch_bundle.candidates) == 3


def test_single_case_blinding_rejects_holdout(case_brief) -> None:
    holdout = case_brief.model_copy(update={"dataset_class": DatasetClass.HOLDOUT, "contamination_labels": ()})
    submissions = tuple(
        make_submission(condition, holdout.case_id, f"holdout_{condition.value.lower()}") for condition in Condition
    )
    with pytest.raises(ValueError, match="DEVELOPMENT ONLY"):
        build_single_case_development_blind_bundle(
            holdout,
            submissions,
            secret_seed=SECRET,
            reveal_custodian=RevealCustodian(),
        )


def test_execution_evidence_is_persisted_before_bundle_failure(tmp_path, case_brief) -> None:
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)  # noqa: S603, S607
    (tmp_path / ".gitignore").write_text("var/\n", encoding="utf-8")
    storage = PrivateExperimentStorage(tmp_path)
    submissions = tuple(
        make_submission(condition, case_brief.case_id, f"persist_{condition.value.lower()}") for condition in Condition
    )

    execution_path = persist_development_execution(
        storage,
        case_brief,
        submissions,
        review_mode="single_case_development",
    )
    with pytest.raises(ValueError, match="exactly three submissions"):
        build_single_case_development_blind_bundle(
            case_brief,
            submissions[:2],
            secret_seed=SECRET,
            reveal_custodian=RevealCustodian(),
        )
    failure_path = persist_development_failure(
        storage,
        case_brief.case_id,
        stage="blind_bundle",
        failure_type="simulated_bundle_failure",
        safe_message="Simulated bundle failure.",
    )
    bundle = build_single_case_development_blind_bundle(
        case_brief,
        submissions,
        secret_seed=SECRET,
        reveal_custodian=RevealCustodian(),
    )
    blind_path = persist_development_blind_bundle(storage, case_brief, bundle)

    assert execution_path.exists()
    assert failure_path.exists()
    assert blind_path.exists()
    persisted = storage.read_json(f"runs/{case_brief.case_id}.json")
    assert len(persisted["condition_submissions"]) == 3
    assert persisted["review_mode"] == "single_case_development"
    assert storage.read_json(f"blind/{case_brief.case_id}.json")["review_mode"] == "single_case_development"
    serialized = execution_path.read_text(encoding="utf-8").casefold()
    assert "api_key" not in serialized
    assert "prompt body" not in serialized
    assert "chain of thought" not in serialized

    with pytest.raises(ValueError, match="credentials"):
        persist_development_failure(
            storage,
            case_brief.case_id,
            stage="blind_bundle",
            failure_type="simulated_bundle_failure",
            safe_message="api_key=must-not-persist",
        )


def test_persisted_execution_wrapper_orders_evidence_before_presentation(tmp_path, case_brief, monkeypatch) -> None:
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)  # noqa: S603, S607
    (tmp_path / ".gitignore").write_text("var/\n", encoding="utf-8")
    storage = PrivateExperimentStorage(tmp_path)
    submissions = tuple(
        make_submission(condition, case_brief.case_id, f"ordered_{condition.value.lower()}") for condition in Condition
    )
    events: list[str] = []

    def fake_execute(_brief, _workflows):
        events.append("execute")
        return submissions

    monkeypatch.setattr("scripts.uncharted_ai_os.editorial_eval.rehearsal.run_development_case", fake_execute)
    original_write = storage.write_json

    def record_write(relative_path, value):
        events.append("persist")
        return original_write(relative_path, value)

    monkeypatch.setattr(storage, "write_json", record_write)
    run_development_case_with_persistence(case_brief, object(), storage)
    assert events == ["execute", "persist"]


def test_three_contaminated_cases_complete_offline_rehearsal(runtime_config) -> None:
    cases = load_development_cases()
    assert len(cases) == 3
    assert all(set(case.contamination_labels) == {"NOT HOLDOUT", "CONTAMINATED", "DEVELOPMENT ONLY"} for case in cases)

    all_submissions = []
    for index, case in enumerate(cases):
        package_b = make_package(f"rehearsal_b_{index}")
        package_c = make_package(f"rehearsal_c_{index}")
        workflows = DevelopmentWorkflows(
            condition_a=ConditionAWorkflow(
                invoker=ScriptedModelInvoker(
                    [
                        ScriptedStep(
                            parsed=NormalizedSubmission(
                                decision=NormalizedDecision.PROCEED_CANDIDATE,
                                spoken_script=f"Development-only A candidate for {case.case_id}.",
                            )
                        )
                    ]
                ),
                runtime_config=runtime_config,
                clock=fixed_clock,
                run_id_factory=run_ids(f"rehearsal_a_{index}"),
            ),
            condition_b=ConditionBWorkflow(
                invoker=ScriptedModelInvoker(
                    [
                        ScriptedStep(parsed=CreatorResult(package=package_b, rationale="Strong B package.")),
                        ScriptedStep(
                            parsed=SelfReviewResult(
                                decision=SelfReviewDecision.ACCEPT,
                                rationale="The package meets the professional threshold.",
                            )
                        ),
                    ]
                ),
                runtime_config=runtime_config,
                clock=fixed_clock,
                run_id_factory=run_ids(f"rehearsal_b_{index}"),
            ),
            condition_c=ConditionCWorkflow(
                invoker=ScriptedModelInvoker(
                    [
                        ScriptedStep(parsed=CreatorResult(package=package_c, rationale="C creator package.")),
                        ScriptedStep(
                            parsed=make_judgment().model_copy(
                                update={"rationale": "INTERNAL_EVALUATOR_ONLY_MARKER"}
                            )
                        ),
                    ]
                ),
                runtime_config=runtime_config,
                clock=fixed_clock,
                run_id_factory=run_ids(f"rehearsal_c_{index}"),
            ),
        )
        submissions = run_development_case(case, workflows)
        assert submissions[1].case_brief_digest == submissions[2].case_brief_digest
        all_submissions.extend(submissions)

    custodian = RevealCustodian()
    bundle = build_development_blind_bundle(
        tuple(all_submissions),
        secret_seed=SECRET,
        reveal_custodian=custodian,
    )
    assert len(bundle.candidates) == 9
    assert not hasattr(bundle, "submissions")
    assert not hasattr(bundle, "reveal_mapping")
    assert len({submission.run_id for submission in all_submissions}) == 9
    assert all(call.run_id == submission.run_id for submission in all_submissions for call in submission.trace.calls)
    assert "INTERNAL_EVALUATOR_ONLY_MARKER" not in bundle.model_dump_json()

    gate = ReviewGate(blind_bundle=bundle, review_id="review_full_rehearsal")
    for candidate in bundle.candidates:
        gate.lock_stage_1(
            Stage1Assessment(
                blind_candidate_id=candidate.blind_candidate_id,
                category_appropriate=True,
                use_decision=CandidateUseDecision.MINOR_EDIT,
                rewrite_burden=RewriteBurden.MINOR,
                main_strength="Clear editorial judgment.",
                main_weakness="Requires a localized edit.",
                confidence="medium",
                reasons=("Development-only scripted review.",),
                preference_basis="editorial",
                locked_at=FIXED_TIME,
            )
        )
    gate.begin_stage_2()
    for case in cases:
        ids = tuple(
            candidate.blind_candidate_id for candidate in bundle.candidates if candidate.case_id == case.case_id
        )
        gate.lock_stage_2(
            Stage2Comparison(
                case_id=case.case_id,
                acceptable_candidate_ids=ids,
                strongest_candidate_ids=(ids[0],),
                least_rewrite_candidate_ids=(ids[0],),
                strongest_point_of_view_candidate_ids=(ids[0],),
                strongest_attention_candidate_ids=(ids[0],),
                strongest_payoff_candidate_ids=(ids[0],),
                strongest_voice_candidate_ids=(ids[0],),
                better_non_script_candidate_ids=(),
                reasons=("Development-only scripted comparison.",),
                editorial_personal_difference="No difference in this synthetic review.",
                uncertainty_and_change_evidence="No additional evidence specified.",
                confidence="medium",
                locked_at=FIXED_TIME,
            )
        )
    review = gate.complete_review(timestamp=FIXED_TIME)
    mapping = custodian.reveal(gate)
    assert review.stage is ReviewStage.REVEALED
    assert len(mapping.entries) == 9
