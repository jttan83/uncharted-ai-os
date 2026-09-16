from __future__ import annotations

from scripts.uncharted_ai_os.editorial_eval.blinding import RevealCustodian, ReviewGate
from scripts.uncharted_ai_os.editorial_eval.contracts import (
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
    load_development_cases,
    run_development_case,
)
from scripts.uncharted_ai_os.editorial_eval.workflows import (
    ConditionAWorkflow,
    ConditionBWorkflow,
    ConditionCWorkflow,
    CreatorResult,
    SelfReviewDecision,
    SelfReviewResult,
)

from .conftest import FIXED_TIME, make_evaluation, make_package
from .test_workflows import fixed_clock, run_ids

SECRET = bytes(reversed(range(32)))


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
                            parsed=make_evaluation(
                                package_c,
                                evaluation_id=f"evaluation_rehearsal_{index}",
                            ).model_copy(update={"rationale": "INTERNAL_EVALUATOR_ONLY_MARKER"})
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
                rewrite_burden=RewriteBurden.MINOR,
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
                reasons=("Development-only scripted comparison.",),
                confidence="medium",
                locked_at=FIXED_TIME,
            )
        )
    review = gate.complete_review(timestamp=FIXED_TIME)
    mapping = custodian.reveal(gate)
    assert review.stage is ReviewStage.REVEALED
    assert len(mapping.entries) == 9
