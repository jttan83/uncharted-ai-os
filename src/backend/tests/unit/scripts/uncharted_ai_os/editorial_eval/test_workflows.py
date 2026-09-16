from __future__ import annotations

from decimal import Decimal

import pytest

from scripts.uncharted_ai_os.editorial_eval.blinding import BlindIdentityLeakError, assert_blind_safe_submission
from scripts.uncharted_ai_os.editorial_eval.canonical import canonical_digest
from scripts.uncharted_ai_os.editorial_eval.contracts import (
    Claim,
    ClaimDecision,
    ClaimMap,
    ClaimType,
    CreatorStopDecision,
    CTerminalState,
    FailureDiagnostics,
    FailureInfo,
    InternalDecision,
    NormalizedDecision,
    NormalizedSubmission,
    ResourceUsage,
    VerificationStatus,
)
from scripts.uncharted_ai_os.editorial_eval.invokers import (
    InvocationModelConfig,
    LangChainModelInvoker,
    ModelMessage,
    ScriptedModelInvoker,
    ScriptedStep,
    preflight_langchain_model_config,
    sanitize_provider_metadata,
)
from scripts.uncharted_ai_os.editorial_eval.prompt_assets import PromptName
from scripts.uncharted_ai_os.editorial_eval.rehearsal import DevelopmentWorkflows, presentation_failure_diagnostics
from scripts.uncharted_ai_os.editorial_eval.security import (
    CredentialConfigurationError,
    ExternalTracingEnabledError,
    assert_credential_free,
)
from scripts.uncharted_ai_os.editorial_eval.workflows import (
    ConditionAWorkflow,
    ConditionBWorkflow,
    ConditionCWorkflow,
    CreatorResult,
    ExecutionLimits,
    RuntimeConfiguration,
    SelfReviewDecision,
    SelfReviewResult,
    _messages,
    new_run_id,
    normalize_internal_decision,
    run_comparable_bc,
)

from .conftest import FIXED_TIME, make_evaluation, make_package, make_runtime_configuration


def fixed_clock():
    return FIXED_TIME


def run_ids(prefix: str):
    counter = 0

    def factory() -> str:
        nonlocal counter
        counter += 1
        return f"run_{prefix}_{counter}"

    return factory


def test_condition_a_current_workflow(runtime_config) -> None:
    invoker = ScriptedModelInvoker(
        [
            ScriptedStep(
                parsed=NormalizedSubmission(
                    decision=NormalizedDecision.PROCEED_CANDIDATE,
                    spoken_script="A strong ecological candidate.",
                ),
                usage=ResourceUsage(input_tokens=100, output_tokens=50),
            )
        ]
    )
    workflow = ConditionAWorkflow(
        invoker=invoker,
        runtime_config=runtime_config,
        clock=fixed_clock,
        run_id_factory=run_ids("a"),
    )
    submission = workflow.run(case_id="case_a_001", ecological_input="Write a concise Reel about alignment.")
    assert submission.normalized.decision is NormalizedDecision.PROCEED_CANDIDATE
    assert len(submission.trace.calls) == 1
    assert submission.trace.calls[0].run_id == submission.run_id
    assert submission.trace.actual_usage.input_tokens == 100
    assert submission.case_brief_digest is None


def test_condition_b_is_strong_single_agent_with_self_review_and_revision(case_brief, runtime_config) -> None:
    first = make_package("b_first")
    revised = make_package("b_revised")
    invoker = ScriptedModelInvoker(
        [
            ScriptedStep(parsed=CreatorResult(package=first, rationale="Complete first pass.")),
            ScriptedStep(
                parsed=SelfReviewResult(
                    decision=SelfReviewDecision.REVISE_PACKAGE,
                    rationale="The payoff needs a material improvement.",
                    requested_changes=("Strengthen and fulfil the payoff.",),
                )
            ),
            ScriptedStep(parsed=CreatorResult(package=revised, rationale="Payoff revised.")),
            ScriptedStep(
                parsed=SelfReviewResult(
                    decision=SelfReviewDecision.ACCEPT,
                    rationale="The package now meets the professional threshold.",
                )
            ),
        ]
    )
    workflow = ConditionBWorkflow(
        invoker=invoker,
        runtime_config=runtime_config,
        clock=fixed_clock,
        run_id_factory=run_ids("b"),
    )
    submission = workflow.run(brief=case_brief, committed_brief_digest=canonical_digest(case_brief))
    assert submission.first_pass_package == first
    assert submission.final_package == revised
    assert submission.normalized.decision is NormalizedDecision.PROCEED_CANDIDATE
    assert submission.trace.substantive_revisions == 1
    assert [call.role for call in submission.trace.calls] == [
        "b_generator",
        "b_self_review",
        "b_generator",
        "b_self_review",
    ]
    assert all(record.model_config.provider_internal_retries == 0 for record in invoker.records)
    assert len(submission.trace.structural_validations) == 2


def test_condition_b_can_stop_without_script(case_brief, runtime_config) -> None:
    invoker = ScriptedModelInvoker(
        [
            ScriptedStep(
                parsed=CreatorResult(
                    stop_decision=CreatorStopDecision.BLOCKED_EVIDENCE,
                    rationale="A material factual premise has no source.",
                    next_action="Supply an appropriate source or remove the premise.",
                )
            )
        ]
    )
    submission = ConditionBWorkflow(
        invoker=invoker,
        runtime_config=runtime_config,
        clock=fixed_clock,
        run_id_factory=run_ids("b_stop"),
    ).run(brief=case_brief)
    assert submission.normalized.decision is NormalizedDecision.EVIDENCE_REQUIRED
    assert submission.normalized.spoken_script is None
    assert len(submission.trace.calls) == 1


def test_condition_b_executes_full_two_revision_path(case_brief, runtime_config) -> None:
    packages = [make_package(f"b_full_{index}") for index in range(3)]
    revise = SelfReviewResult(
        decision=SelfReviewDecision.REVISE_PACKAGE,
        rationale="A material payoff correction remains.",
        requested_changes=("Strengthen the fulfilled payoff.",),
    )
    invoker = ScriptedModelInvoker(
        [
            ScriptedStep(parsed=CreatorResult(package=packages[0], rationale="Initial.")),
            ScriptedStep(parsed=revise),
            ScriptedStep(parsed=CreatorResult(package=packages[1], rationale="Revision one.")),
            ScriptedStep(parsed=revise),
            ScriptedStep(parsed=CreatorResult(package=packages[2], rationale="Revision two.")),
            ScriptedStep(
                parsed=SelfReviewResult(
                    decision=SelfReviewDecision.ACCEPT,
                    rationale="No material weakness remains for human consideration.",
                )
            ),
        ]
    )
    submission = ConditionBWorkflow(
        invoker=invoker,
        runtime_config=runtime_config,
        clock=fixed_clock,
        run_id_factory=run_ids("b_full"),
    ).run(brief=case_brief)
    assert submission.trace.substantive_revisions == 2
    assert len(submission.trace.calls) == 6
    assert submission.first_pass_package == packages[0]
    assert submission.final_package == packages[2]
    assert submission.normalized.decision is NormalizedDecision.PROCEED_CANDIDATE


def test_one_total_retry_cannot_repeat_on_a_later_b_step(case_brief, runtime_config) -> None:
    package = make_package("b_retry_once")
    timeout = FailureInfo(
        failure_type="transient_timeout",
        safe_message="Transient timeout.",
        retryable=True,
    )
    invoker = ScriptedModelInvoker(
        [
            ScriptedStep(failure=timeout),
            ScriptedStep(parsed=CreatorResult(package=package, rationale="Recovered generation.")),
            ScriptedStep(failure=timeout),
            ScriptedStep(
                parsed=SelfReviewResult(
                    decision=SelfReviewDecision.ACCEPT,
                    rationale="This must remain unused.",
                )
            ),
        ]
    )
    submission = ConditionBWorkflow(
        invoker=invoker,
        runtime_config=runtime_config,
        clock=fixed_clock,
        run_id_factory=run_ids("b_retry_total"),
    ).run(brief=case_brief)
    assert [call.attempt_number for call in submission.trace.calls] == [1, 2, 1]
    assert sum(call.infrastructure_retry for call in submission.trace.calls) == 1
    assert invoker.remaining_steps == 1
    assert submission.normalized.decision is NormalizedDecision.HUMAN_JUDGMENT_REQUIRED


def test_condition_c_creator_evaluator_revision_and_fresh_evaluation(case_brief, runtime_config) -> None:
    first = make_package("c_first")
    revised = make_package("c_revised")
    initial_evaluation = make_evaluation(
        first,
        InternalDecision.MAJOR_REVISION,
        evaluation_id="evaluation_first_marker",
    ).model_copy(
        update={
            "requested_actions": ("FIRST_EVALUATION_SECRET_MARKER",),
            "rationale": "FIRST_EVALUATION_SECRET_MARKER",
        }
    )
    final_evaluation = make_evaluation(revised, evaluation_id="evaluation_final")
    invoker = ScriptedModelInvoker(
        [
            ScriptedStep(parsed=CreatorResult(package=first, rationale="Initial package.")),
            ScriptedStep(parsed=initial_evaluation),
            ScriptedStep(parsed=CreatorResult(package=revised, rationale="Evaluator-directed revision.")),
            ScriptedStep(parsed=final_evaluation),
        ]
    )
    submission = ConditionCWorkflow(
        invoker=invoker,
        runtime_config=runtime_config,
        clock=fixed_clock,
        run_id_factory=run_ids("c"),
    ).run(brief=case_brief)
    assert submission.first_pass_package == first
    assert submission.final_package == revised
    assert submission.evaluator_result == final_evaluation
    assert submission.normalized.decision is NormalizedDecision.PROCEED_CANDIDATE
    assert submission.trace.substantive_revisions == 1
    evaluator_records = [record for record in invoker.records if record.output_type.__name__ == "EvaluationResult"]
    assert len(evaluator_records) == 2
    assert all(record.model_config.provider_internal_retries == 0 for record in invoker.records)
    assert "FIRST_EVALUATION_SECRET_MARKER" not in evaluator_records[1].messages[1].content
    assert "A outputs" not in evaluator_records[1].messages[1].content
    assert "reveal_mapping" not in evaluator_records[1].messages[1].content


def test_condition_c_honors_two_revision_limit(case_brief, runtime_config) -> None:
    packages = [make_package(f"limit_{index}") for index in range(3)]
    evaluations = [
        make_evaluation(
            package,
            InternalDecision.MAJOR_REVISION,
            evaluation_id=f"evaluation_limit_{index}",
        )
        for index, package in enumerate(packages)
    ]
    invoker = ScriptedModelInvoker(
        [
            ScriptedStep(parsed=CreatorResult(package=packages[0], rationale="Initial.")),
            ScriptedStep(parsed=evaluations[0]),
            ScriptedStep(parsed=CreatorResult(package=packages[1], rationale="Revision one.")),
            ScriptedStep(parsed=evaluations[1]),
            ScriptedStep(parsed=CreatorResult(package=packages[2], rationale="Revision two.")),
            ScriptedStep(parsed=evaluations[2]),
        ]
    )
    submission = ConditionCWorkflow(
        invoker=invoker,
        runtime_config=runtime_config,
        clock=fixed_clock,
        run_id_factory=run_ids("c_limit"),
    ).run(brief=case_brief)
    assert submission.trace.substantive_revisions == 2
    assert len(submission.trace.calls) == 6
    assert submission.normalized.decision is NormalizedDecision.EDITORIAL_REVISION_REQUIRED
    assert invoker.remaining_steps == 0
    assert submission.c_history is not None
    assert submission.c_history.packages == tuple(packages)
    assert submission.c_history.evaluations == tuple(evaluations)
    assert submission.c_history.terminal_state is CTerminalState.REVISION_BUDGET_EXHAUSTED


def test_condition_c_stops_early_on_non_script_creator_decision(case_brief, runtime_config) -> None:
    invoker = ScriptedModelInvoker(
        [
            ScriptedStep(
                parsed=CreatorResult(
                    stop_decision=CreatorStopDecision.RETURN_UPSTREAM,
                    rationale="The point of view is missing.",
                    next_action="Establish Jentz's defensible point of view.",
                )
            )
        ]
    )
    submission = ConditionCWorkflow(
        invoker=invoker,
        runtime_config=runtime_config,
        clock=fixed_clock,
        run_id_factory=run_ids("c_early"),
    ).run(brief=case_brief)
    assert submission.normalized.decision is NormalizedDecision.REVISE_BRIEF
    assert submission.evaluator_result is None
    assert submission.c_history is not None
    assert submission.c_history.terminal_state is CTerminalState.PRE_PACKAGE_CREATOR_STOP
    assert submission.c_history.creator_stops[0].phase == "pre_package"
    assert len(invoker.records) == 1


def test_condition_c_retains_evaluator_failure_after_valid_package(case_brief, runtime_config) -> None:
    package = make_package("evaluator_failure")
    failure = FailureInfo(
        failure_type="provider_rejected_request",
        safe_message="Evaluator invocation failed safely.",
        retryable=False,
    )
    submission = ConditionCWorkflow(
        invoker=ScriptedModelInvoker(
            [
                ScriptedStep(parsed=CreatorResult(package=package, rationale="Valid package.")),
                ScriptedStep(failure=failure),
            ]
        ),
        runtime_config=runtime_config,
        clock=fixed_clock,
        run_id_factory=run_ids("c_eval_failure"),
    ).run(brief=case_brief)
    assert submission.c_history is not None
    assert submission.c_history.packages == (package,)
    assert submission.c_history.evaluations == ()
    assert submission.c_history.evaluator_failures == (failure,)
    assert submission.c_history.terminal_state is CTerminalState.EVALUATOR_FAILURE
    assert submission.final_package == package


def test_condition_c_revision_stop_retains_prior_package_and_evaluation(case_brief, runtime_config) -> None:
    package = make_package("before_revision_stop")
    evaluation = make_evaluation(
        package,
        InternalDecision.MAJOR_REVISION,
        evaluation_id="evaluation_before_revision_stop",
    )
    submission = ConditionCWorkflow(
        invoker=ScriptedModelInvoker(
            [
                ScriptedStep(parsed=CreatorResult(package=package, rationale="Initial.")),
                ScriptedStep(parsed=evaluation),
                ScriptedStep(
                    parsed=CreatorResult(
                        stop_decision=CreatorStopDecision.BLOCKED_EVIDENCE,
                        rationale="The requested revision requires missing evidence.",
                        next_action="Supply evidence or remove the claim.",
                    )
                ),
            ]
        ),
        runtime_config=runtime_config,
        clock=fixed_clock,
        run_id_factory=run_ids("c_revision_stop"),
    ).run(brief=case_brief)
    assert submission.c_history is not None
    assert submission.c_history.packages == (package,)
    assert submission.c_history.evaluations == (evaluation,)
    assert submission.c_history.creator_stops[0].phase == "revision"
    assert submission.c_history.terminal_state is CTerminalState.REVISION_CREATOR_STOP
    assert submission.final_package == package
    assert submission.normalized.decision is NormalizedDecision.EVIDENCE_REQUIRED


def test_condition_c_retains_invalid_revised_package(case_brief, runtime_config) -> None:
    first = make_package("valid_before_invalid_revision")
    invalid_claim_map = ClaimMap(
        artifact_version="claims_invalid_revision",
        no_material_claims=False,
        claims=(
            Claim(
                claim_id="claim_unsupported",
                passage="An unsupported factual assertion.",
                claim_type=ClaimType.FACTUAL,
                verification_status=VerificationStatus.UNVERIFIED,
                decision=ClaimDecision.RETAIN,
            ),
        ),
    )
    revised = make_package("invalid_revision").model_copy(update={"claim_map": invalid_claim_map})
    evaluation = make_evaluation(
        first,
        InternalDecision.MAJOR_REVISION,
        evaluation_id="evaluation_before_invalid_revision",
    )
    submission = ConditionCWorkflow(
        invoker=ScriptedModelInvoker(
            [
                ScriptedStep(parsed=CreatorResult(package=first, rationale="Initial.")),
                ScriptedStep(parsed=evaluation),
                ScriptedStep(parsed=CreatorResult(package=revised, rationale="Invalid revision.")),
            ]
        ),
        runtime_config=runtime_config,
        clock=fixed_clock,
        run_id_factory=run_ids("c_invalid_revision"),
    ).run(brief=case_brief)
    assert submission.c_history is not None
    assert submission.c_history.packages == (first, revised)
    assert submission.c_history.evaluations == (evaluation,)
    assert submission.c_history.terminal_state is CTerminalState.DETERMINISTIC_VALIDATION_FAILURE
    assert submission.final_package == revised
    assert submission.normalized.decision is NormalizedDecision.EVIDENCE_REQUIRED


def test_condition_c_retains_parsed_revision_when_token_budget_exhausts(case_brief, model_config) -> None:
    limits = ExecutionLimits(
        max_model_calls=7,
        max_substantive_revisions=2,
        max_total_tokens=100,
        max_total_latency_ms=60_000,
        max_cost=Decimal(5),
        currency="USD",
    )
    runtime_config = make_runtime_configuration(model_config, bc_limits=limits)
    first = make_package("budget_first")
    revised = make_package("budget_revised")
    evaluation = make_evaluation(
        first,
        InternalDecision.MAJOR_REVISION,
        evaluation_id="evaluation_budget",
    )
    submission = ConditionCWorkflow(
        invoker=ScriptedModelInvoker(
            [
                ScriptedStep(
                    parsed=CreatorResult(package=first, rationale="Initial."),
                    usage=ResourceUsage(input_tokens=10, output_tokens=10),
                ),
                ScriptedStep(
                    parsed=evaluation,
                    usage=ResourceUsage(input_tokens=10, output_tokens=10),
                ),
                ScriptedStep(
                    parsed=CreatorResult(package=revised, rationale="Expensive revision."),
                    usage=ResourceUsage(input_tokens=100, output_tokens=100),
                ),
            ]
        ),
        runtime_config=runtime_config,
        clock=fixed_clock,
        run_id_factory=run_ids("c_budget_history"),
    ).run(brief=case_brief)
    assert submission.c_history is not None
    assert submission.c_history.packages == (first, revised)
    assert submission.c_history.evaluations == (evaluation,)
    assert submission.c_history.terminal_state is CTerminalState.RESOURCE_BUDGET_EXHAUSTED
    assert submission.trace.failures[-1].failure_type == "token_budget_exceeded"


def test_bc_identical_brief_is_enforced_before_execution(case_brief, runtime_config) -> None:
    invoker_b = ScriptedModelInvoker([])
    invoker_c = ScriptedModelInvoker([])
    changed = case_brief.model_copy(update={"portfolio_context": "Condition-specific mutation"})
    with pytest.raises(ValueError, match="canonical bytes differ"):
        run_comparable_bc(
            brief_for_b=case_brief,
            brief_for_c=changed,
            condition_b=ConditionBWorkflow(invoker=invoker_b, runtime_config=runtime_config),
            condition_c=ConditionCWorkflow(invoker=invoker_c, runtime_config=runtime_config),
        )
    assert not invoker_b.records
    assert not invoker_c.records


def test_bc_generator_configuration_and_ceiling_parity_are_enforced(case_brief, model_config, bc_limits) -> None:
    invoker_b = ScriptedModelInvoker([])
    invoker_c = ScriptedModelInvoker([])
    mismatched_model = model_config.model_copy(update={"model_identifier": "different-model"})
    mismatched_runtime = make_runtime_configuration(mismatched_model, bc_limits=bc_limits)
    runtime_config = make_runtime_configuration(model_config, bc_limits=bc_limits)
    with pytest.raises(ValueError, match="generator model configurations"):
        run_comparable_bc(
            brief_for_b=case_brief,
            brief_for_c=case_brief,
            condition_b=ConditionBWorkflow(invoker=invoker_b, runtime_config=runtime_config),
            condition_c=ConditionCWorkflow(
                invoker=invoker_c,
                runtime_config=mismatched_runtime,
            ),
        )
    lower_ceiling = bc_limits.model_copy(update={"max_total_tokens": 19_000})
    lower_runtime = make_runtime_configuration(model_config, bc_limits=lower_ceiling)
    with pytest.raises(ValueError, match="execution ceilings"):
        run_comparable_bc(
            brief_for_b=case_brief,
            brief_for_c=case_brief,
            condition_b=ConditionBWorkflow(invoker=invoker_b, runtime_config=runtime_config),
            condition_c=ConditionCWorkflow(
                invoker=invoker_c,
                runtime_config=lower_runtime,
            ),
        )
    assert not invoker_b.records
    assert not invoker_c.records


def test_runtime_rejects_insufficient_or_unequal_bc_call_ceiling_before_execution(model_config, bc_limits) -> None:
    insufficient = bc_limits.model_copy(update={"max_model_calls": 6})
    with pytest.raises(ValueError, match="six planned calls and one total infrastructure retry"):
        make_runtime_configuration(model_config, bc_limits=insufficient)
    with pytest.raises(ValueError, match="ceilings must be identical"):
        RuntimeConfiguration(
            primary_generator=model_config,
            evaluator=model_config,
            condition_a=make_runtime_configuration(model_config).condition_a,
            condition_b=bc_limits,
            condition_c=bc_limits.model_copy(update={"max_total_tokens": 19_999}),
        )


def test_development_composition_rejects_a_b_c_generator_mismatch(model_config, runtime_config) -> None:
    mismatch = make_runtime_configuration(model_config.model_copy(update={"temperature": 0.7}))
    with pytest.raises(ValueError, match="share one validated runtime configuration"):
        DevelopmentWorkflows(
            condition_a=ConditionAWorkflow(invoker=ScriptedModelInvoker([]), runtime_config=mismatch),
            condition_b=ConditionBWorkflow(invoker=ScriptedModelInvoker([]), runtime_config=runtime_config),
            condition_c=ConditionCWorkflow(invoker=ScriptedModelInvoker([]), runtime_config=runtime_config),
        )


def test_bc_actual_consumption_is_measured_independently(case_brief, runtime_config) -> None:
    package_b = make_package("usage_b")
    package_c = make_package("usage_c")
    condition_b = ConditionBWorkflow(
        invoker=ScriptedModelInvoker(
            [
                ScriptedStep(
                    parsed=CreatorResult(package=package_b, rationale="Complete."),
                    usage=ResourceUsage(input_tokens=10, output_tokens=5),
                ),
                ScriptedStep(
                    parsed=SelfReviewResult(
                        decision=SelfReviewDecision.ACCEPT,
                        rationale="Professionally usable.",
                    ),
                    usage=ResourceUsage(input_tokens=8, output_tokens=3),
                ),
            ]
        ),
        runtime_config=runtime_config,
        clock=fixed_clock,
        run_id_factory=run_ids("usage_b"),
    )
    condition_c = ConditionCWorkflow(
        invoker=ScriptedModelInvoker(
            [
                ScriptedStep(
                    parsed=CreatorResult(package=package_c, rationale="Complete."),
                    usage=ResourceUsage(input_tokens=100, output_tokens=50),
                ),
                ScriptedStep(
                    parsed=make_evaluation(package_c, evaluation_id="evaluation_usage_c"),
                    usage=ResourceUsage(input_tokens=80, output_tokens=30),
                ),
            ]
        ),
        runtime_config=runtime_config,
        clock=fixed_clock,
        run_id_factory=run_ids("usage_c"),
    )
    submission_b, submission_c = run_comparable_bc(
        brief_for_b=case_brief,
        brief_for_c=case_brief,
        condition_b=condition_b,
        condition_c=condition_c,
    )
    assert submission_b.trace.actual_usage.accounted_total_tokens == 26
    assert submission_c.trace.actual_usage.accounted_total_tokens == 260
    assert submission_b.trace.max_total_tokens == submission_c.trace.max_total_tokens


def test_unknown_token_and_cost_categories_remain_unknown_and_disclosed(case_brief, runtime_config) -> None:
    invoker = ScriptedModelInvoker(
        [
            ScriptedStep(
                parsed=CreatorResult(package=make_package("unknown_usage"), rationale="Complete."),
                usage=ResourceUsage(input_tokens=10),
            ),
            ScriptedStep(
                parsed=SelfReviewResult(
                    decision=SelfReviewDecision.ACCEPT,
                    rationale="Professionally usable.",
                ),
                usage=ResourceUsage(input_tokens=5),
            ),
        ]
    )
    submission = ConditionBWorkflow(
        invoker=invoker,
        runtime_config=runtime_config,
        clock=fixed_clock,
        run_id_factory=run_ids("unknown_usage"),
    ).run(brief=case_brief)
    assert submission.trace.actual_usage.output_tokens is None
    assert submission.trace.actual_usage.monetary_cost is None
    assert set(submission.trace.deviations) == {
        "token_ceiling_not_enforced_unknown_usage",
        "cost_ceiling_not_enforced_unknown_cost",
    }


def test_known_resource_ceiling_is_enforced_and_recorded(model_config) -> None:
    invoker = ScriptedModelInvoker(
        [
            ScriptedStep(
                parsed=NormalizedSubmission(
                    decision=NormalizedDecision.PROCEED_CANDIDATE,
                    spoken_script="Would otherwise be a candidate.",
                ),
                usage=ResourceUsage(input_tokens=90, output_tokens=20),
            )
        ]
    )
    runtime_config = make_runtime_configuration(
        model_config,
        a_limits=ExecutionLimits(
            max_model_calls=2,
            max_substantive_revisions=0,
            max_total_tokens=100,
            max_total_latency_ms=10_000,
            max_cost=Decimal(1),
            currency="USD",
        ),
    )
    submission = ConditionAWorkflow(
        invoker=invoker,
        runtime_config=runtime_config,
        clock=fixed_clock,
        run_id_factory=run_ids("budget"),
    ).run(case_id="case_budget", ecological_input="Input")
    assert submission.normalized.decision is NormalizedDecision.HUMAN_JUDGMENT_REQUIRED
    assert submission.trace.failures[0].failure_type == "token_budget_exceeded"
    assert submission.trace.actual_usage.input_tokens == 90


def test_one_identical_infrastructure_retry_is_traced(model_config) -> None:
    invoker = ScriptedModelInvoker(
        [
            ScriptedStep(
                failure=FailureInfo(
                    failure_type="transient_timeout",
                    safe_message="Transient timeout.",
                    retryable=True,
                )
            ),
            ScriptedStep(
                parsed=NormalizedSubmission(
                    decision=NormalizedDecision.PROCEED_CANDIDATE,
                    spoken_script="Retry candidate.",
                )
            ),
        ]
    )
    runtime_config = make_runtime_configuration(
        model_config,
        a_limits=ExecutionLimits(
            max_model_calls=2,
            max_substantive_revisions=0,
            max_total_tokens=1_000,
            max_total_latency_ms=10_000,
            max_cost=Decimal(1),
            currency="USD",
        ),
    )
    workflow = ConditionAWorkflow(
        invoker=invoker,
        runtime_config=runtime_config,
        clock=fixed_clock,
        run_id_factory=run_ids("retry"),
    )
    submission = workflow.run(case_id="case_retry", ecological_input="Input")
    assert [call.attempt_number for call in submission.trace.calls] == [1, 2]
    assert submission.trace.calls[0].infrastructure_retry_eligible is True
    assert submission.trace.calls[0].retry_decision == "retry_scheduled"
    assert submission.trace.calls[1].infrastructure_retry is True
    assert submission.trace.calls[1].retry_decision == "not_applicable"
    assert all(call.provider_internal_retries == 0 for call in submission.trace.calls)
    assert invoker.records[0].messages == invoker.records[1].messages
    assert submission.normalized.decision is NormalizedDecision.PROCEED_CANDIDATE


def test_second_infrastructure_failure_stops_and_is_retained(model_config) -> None:
    failure = FailureInfo(
        failure_type="transient_timeout",
        safe_message="Transient timeout.",
        retryable=True,
    )
    invoker = ScriptedModelInvoker([ScriptedStep(failure=failure), ScriptedStep(failure=failure)])
    runtime_config = make_runtime_configuration(
        model_config,
        a_limits=ExecutionLimits(
            max_model_calls=2,
            max_substantive_revisions=0,
            max_total_tokens=1_000,
            max_total_latency_ms=10_000,
            max_cost=Decimal(1),
            currency="USD",
        ),
    )
    submission = ConditionAWorkflow(
        invoker=invoker,
        runtime_config=runtime_config,
        clock=fixed_clock,
        run_id_factory=run_ids("retry_fail"),
    ).run(case_id="case_retry_failure", ecological_input="Input")
    assert submission.normalized.decision is NormalizedDecision.HUMAN_JUDGMENT_REQUIRED
    assert len(submission.trace.calls) == 2
    assert submission.trace.calls[0].retry_decision == "retry_scheduled"
    assert submission.trace.calls[1].retry_decision == "retry_limit_reached"
    assert submission.trace.failures == (failure,)


def test_resource_ceiling_suppresses_retry_and_records_decision(model_config) -> None:
    failure = FailureInfo(
        failure_type="infrastructure_timeout",
        safe_message="Transient timeout.",
        retryable=True,
    )
    invoker = ScriptedModelInvoker([ScriptedStep(failure=failure, latency_ms=31_000)])
    runtime_config = make_runtime_configuration(
        model_config,
        a_limits=ExecutionLimits(
            max_model_calls=2,
            max_substantive_revisions=0,
            max_total_tokens=1_000,
            max_total_latency_ms=30_000,
            max_cost=Decimal(1),
            currency="USD",
        ),
    )
    submission = ConditionAWorkflow(
        invoker=invoker,
        runtime_config=runtime_config,
        clock=fixed_clock,
        run_id_factory=run_ids("retry_suppressed"),
    ).run(case_id="case_retry_suppressed", ecological_input="Input")
    assert len(invoker.records) == 1
    assert submission.trace.calls[0].infrastructure_retry_eligible is True
    assert submission.trace.calls[0].retry_decision == "resource_ceiling"
    assert submission.trace.failures[0].failure_type == "latency_budget_exceeded"


def test_condition_c_uses_separately_traced_evaluator_configuration(case_brief, model_config, bc_limits) -> None:
    package = make_package("separate_evaluator")
    evaluator_config = model_config.model_copy(update={"model_identifier": "evaluator-model-v2"})
    invoker = ScriptedModelInvoker(
        [
            ScriptedStep(parsed=CreatorResult(package=package, rationale="Creator result.")),
            ScriptedStep(parsed=make_evaluation(package, evaluation_id="evaluation_separate")),
        ]
    )
    runtime_config = make_runtime_configuration(
        model_config,
        bc_limits=bc_limits,
        evaluator_config=evaluator_config,
    )
    submission = ConditionCWorkflow(
        invoker=invoker,
        runtime_config=runtime_config,
        clock=fixed_clock,
        run_id_factory=run_ids("evaluator_config"),
    ).run(brief=case_brief)
    assert invoker.records[0].model_config == model_config
    assert invoker.records[1].model_config == evaluator_config
    assert submission.trace.calls[0].model_config_digest != submission.trace.calls[1].model_config_digest


def test_evaluator_binding_failure_becomes_safe_terminal_trace(case_brief, model_config, bc_limits) -> None:
    package = make_package("binding_failure")
    wrong_package = make_package("other_package")
    invoker = ScriptedModelInvoker(
        [
            ScriptedStep(parsed=CreatorResult(package=package, rationale="Creator result.")),
            ScriptedStep(parsed=make_evaluation(wrong_package, evaluation_id="evaluation_wrong_binding")),
        ]
    )
    runtime_config = make_runtime_configuration(model_config, bc_limits=bc_limits)
    submission = ConditionCWorkflow(
        invoker=invoker,
        runtime_config=runtime_config,
        clock=fixed_clock,
        run_id_factory=run_ids("binding_failure"),
    ).run(brief=case_brief)
    assert submission.normalized.decision is NormalizedDecision.HUMAN_JUDGMENT_REQUIRED
    assert submission.evaluator_result is not None
    assert submission.c_history is not None
    assert submission.c_history.terminal_state is CTerminalState.EVALUATOR_FAILURE
    assert submission.c_history.evaluator_failures[0].failure_type == "evaluator_binding_failure"
    assert submission.trace.failures[0].failure_type == "evaluator_binding_failure"
    assert len(submission.trace.calls) == 2


def test_run_ids_are_unique_and_stable_in_each_trace(model_config) -> None:
    assert new_run_id() != new_run_id()
    invoker = ScriptedModelInvoker(
        [
            ScriptedStep(
                parsed=NormalizedSubmission(
                    decision=NormalizedDecision.PROCEED_CANDIDATE,
                    spoken_script="Stable correlation candidate.",
                )
            )
        ]
    )
    runtime_config = make_runtime_configuration(
        model_config,
        a_limits=ExecutionLimits(
            max_model_calls=2,
            max_substantive_revisions=0,
            max_total_tokens=1_000,
            max_total_latency_ms=10_000,
            max_cost=Decimal(1),
            currency="USD",
        ),
    )
    submission = ConditionAWorkflow(
        invoker=invoker,
        runtime_config=runtime_config,
        clock=fixed_clock,
        run_id_factory=run_ids("stable"),
    ).run(case_id="case_stable_run", ecological_input="Input")
    assert {submission.run_id, submission.trace.run_id, submission.trace.calls[0].run_id} == {"run_stable_1"}


def test_blind_scan_rejects_exact_runtime_model_identity(runtime_config) -> None:
    submission = ConditionAWorkflow(
        invoker=ScriptedModelInvoker(
            [
                ScriptedStep(
                    parsed=NormalizedSubmission(
                        decision=NormalizedDecision.PROCEED_CANDIDATE,
                        spoken_script="This was generated by test-model-v1.",
                    )
                )
            ]
        ),
        runtime_config=runtime_config,
        clock=fixed_clock,
        run_id_factory=run_ids("model_leak"),
    ).run(case_id="case_model_leak", ecological_input="Input")
    with pytest.raises(BlindIdentityLeakError, match="model_identity"):
        assert_blind_safe_submission(submission)


def test_langchain_adapter_refuses_external_tracing_before_model_initialization(monkeypatch, model_config) -> None:
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    with pytest.raises(ExternalTracingEnabledError):
        LangChainModelInvoker().invoke(
            (ModelMessage(role="user", content="No external call may occur."),),
            NormalizedSubmission,
            model_config,
        )


def test_langchain_adapter_invokes_mocked_structured_output_and_extracts_usage(monkeypatch, model_config) -> None:
    captured = {}
    candidate = NormalizedSubmission(
        decision=NormalizedDecision.PROCEED_CANDIDATE,
        spoken_script="Offline structured candidate.",
    )

    class FakeRaw:
        usage_metadata = {
            "input_tokens": 120,
            "output_tokens": 45,
            "input_token_details": {"cache_read": 20},
            "output_token_details": {"reasoning": 15},
        }
        response_metadata = {
            "model_name": "mocked-model",
            "finish_reason": "stop",
            "message": "must not persist",
        }
        tool_calls = []

    class FakeStructuredModel:
        def invoke(self, messages, *, config):
            captured["messages"] = messages
            captured["config"] = config
            return {"parsed": candidate, "parsing_error": None, "raw": FakeRaw()}

    class FakeChatModel:
        def with_structured_output(self, output_type, *, include_raw):
            captured["output_type"] = output_type
            captured["include_raw"] = include_raw
            return FakeStructuredModel()

    def fake_init_chat_model(*, model, model_provider, **parameters):
        captured["model"] = model
        captured["provider"] = model_provider
        captured["parameters"] = parameters
        return FakeChatModel()

    for name in ("LANGCHAIN_TRACING", "LANGCHAIN_TRACING_V2", "LANGSMITH_TRACING", "LANGSMITH_TRACING_V2"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr("langchain.chat_models.init_chat_model", fake_init_chat_model)
    messages = _messages(PromptName.CONDITION_A, "Offline input")
    response = LangChainModelInvoker().invoke(messages, NormalizedSubmission, model_config)

    assert response.parsed == candidate
    assert response.usage.input_tokens == 120
    assert response.usage.output_tokens == 45
    assert response.usage.cached_input_tokens == 20
    assert response.usage.reasoning_tokens == 15
    assert response.usage.accounted_total_tokens == 165
    assert response.raw_provider_metadata == {"model_name": "mocked-model", "finish_reason": "stop"}
    assert captured["config"] == {"callbacks": []}
    assert captured["parameters"]["max_retries"] == 0
    assert "prompt_version:" not in captured["messages"][0][1]


def test_langchain_adapter_retains_safe_provider_failure_diagnostics(monkeypatch, model_config) -> None:
    class FakeProviderError(Exception):
        status_code = 400
        code = "invalid_request"
        type = "invalid_request_error"
        request_id = "req_opaque_123"

    def fake_init_chat_model(**_kwargs):
        raise FakeProviderError

    monkeypatch.setattr("langchain.chat_models.init_chat_model", fake_init_chat_model)
    response = LangChainModelInvoker().invoke(
        (ModelMessage(role="user", content="private case prompt"),),
        NormalizedSubmission,
        model_config,
    )
    assert response.failure is not None
    diagnostics = response.failure.diagnostics
    assert diagnostics is not None
    assert diagnostics.stage == "model_initialization"
    assert diagnostics.http_status_code == 400
    assert diagnostics.provider_error_code == "invalid_request"
    assert diagnostics.request_id == "req_opaque_123"
    assert diagnostics.network_request_attempted is False
    serialized = response.model_dump_json()
    assert "secret" not in serialized
    assert "private case prompt" not in serialized


def test_langchain_model_config_preflight_uses_adapter_normalization(monkeypatch, model_config) -> None:
    class FakeModel:
        max_retries = 0
        request_timeout = 30
        temperature = None
        _default_params = {
            "model": "gpt-5.6-sol",
            "max_completion_tokens": 2000,
            "seed": 7,
            "reasoning_effort": "medium",
        }

    captured = {}

    def fake_init_chat_model(**kwargs):
        captured.update(kwargs)
        return FakeModel()

    monkeypatch.setattr("langchain.chat_models.init_chat_model", fake_init_chat_model)
    normalized = preflight_langchain_model_config(model_config)
    assert normalized == {
        "model": "gpt-5.6-sol",
        "reasoning_effort": "medium",
        "temperature": None,
        "seed": 7,
        "max_completion_tokens": 2000,
        "timeout": 30,
        "max_retries": 0,
    }
    assert captured["max_tokens"] == 2000
    assert captured["timeout"] == 30
    assert captured["max_retries"] == 0


def test_presentation_failure_diagnostics_retain_only_safe_location() -> None:
    try:
        raise AttributeError("candidate mapping=secret").with_traceback(None)
    except AttributeError as exc:
        diagnostics = presentation_failure_diagnostics(
            exc,
            object_type="BlindCandidate",
            expected_type="NormalizedSubmission",
            actual_type="NoneType",
        )
    assert isinstance(diagnostics, FailureDiagnostics)
    assert diagnostics.stage == "presentation"
    assert diagnostics.exception_class == "AttributeError"
    assert diagnostics.object_type == "BlindCandidate"
    assert diagnostics.expected_type == "NormalizedSubmission"
    assert diagnostics.actual_type == "NoneType"
    assert diagnostics.module_path is not None
    assert diagnostics.function_name == "test_presentation_failure_diagnostics_retain_only_safe_location"
    assert diagnostics.line_number is not None
    assert "secret" not in diagnostics.diagnostic_message


@pytest.mark.parametrize(
    ("internal", "external"),
    [
        (InternalDecision.READY_FOR_HUMAN_APPROVAL, NormalizedDecision.PROCEED_CANDIDATE),
        (InternalDecision.MINOR_REVISION, NormalizedDecision.EDITORIAL_REVISION_REQUIRED),
        (InternalDecision.MAJOR_REVISION, NormalizedDecision.EDITORIAL_REVISION_REQUIRED),
        (InternalDecision.RETURN_UPSTREAM, NormalizedDecision.REVISE_BRIEF),
        (InternalDecision.BLOCKED_EVIDENCE, NormalizedDecision.EVIDENCE_REQUIRED),
        (InternalDecision.REJECT, NormalizedDecision.DO_NOT_DEVELOP),
        (InternalDecision.HUMAN_ESCALATION, NormalizedDecision.HUMAN_JUDGMENT_REQUIRED),
    ],
)
def test_internal_decisions_map_to_neutral_vocabulary(internal, external) -> None:
    package = make_package("mapping")
    evaluation = make_evaluation(package, internal)
    normalized = normalize_internal_decision(evaluation, package)
    assert normalized.decision is external
    serialized = normalized.model_dump_json()
    assert "ready_for_human_approval" not in serialized
    assert "return_upstream" not in serialized


@pytest.mark.parametrize(
    "payload",
    [
        {"nested": {"authorization": "redacted"}},
        {"headers": {"X-Api-Key": "redacted"}},
        {"nested": {"accessToken": "redacted"}},
        {"headers": {"proxyAuthorization": "redacted"}},
        ["https://user:redacted@example.invalid/v1"],
        "https://example.invalid/v1?access_token=redacted",
        "Bearer redacted-value",
    ],
)
def test_credential_guard_recursively_rejects_nested_and_url_credentials(payload) -> None:
    with pytest.raises(CredentialConfigurationError, match=r"credentials|credential-bearing"):
        assert_credential_free(payload)


def test_model_configuration_has_strict_positive_allowlist(model_config) -> None:
    payload = model_config.model_dump(mode="python")
    payload["additional_parameters"] = {"top_p": 0.8}
    with pytest.raises(ValueError, match="additional_parameters"):
        InvocationModelConfig.model_validate(payload)


def test_credential_rejection_error_never_echoes_value() -> None:
    marker = "credential-value-must-not-appear"
    with pytest.raises(CredentialConfigurationError) as exc_info:
        assert_credential_free({"nested": {"clientSecret": marker}})
    assert marker not in str(exc_info.value)


def test_model_configuration_rejects_credential_bearing_identifier(model_config) -> None:
    payload = model_config.model_dump(mode="python")
    payload["model_identifier"] = "https://user:redacted@example.invalid/model"
    with pytest.raises(ValueError, match="credential-bearing"):
        InvocationModelConfig.model_validate(payload)


def test_model_copy_cannot_bypass_runtime_credential_guard(model_config) -> None:
    unsafe = model_config.model_copy(update={"model_identifier": "https://user:credential-value@example.invalid/model"})
    with pytest.raises(CredentialConfigurationError, match="credential-bearing"):
        ScriptedModelInvoker([]).invoke(
            (ModelMessage(role="user", content="No invocation may occur."),),
            NormalizedSubmission,
            unsafe,
        )
    with pytest.raises(ValueError, match="credential-bearing"):
        ConditionAWorkflow(
            invoker=ScriptedModelInvoker([]),
            runtime_config=make_runtime_configuration(model_config).model_copy(update={"primary_generator": unsafe}),
        )


def test_provider_metadata_uses_safe_allowlist() -> None:
    sanitized = sanitize_provider_metadata(
        {
            "model_name": "model-v1",
            "finish_reason": "stop",
            "authorization": "credential",
            "message": "provider error might contain a credential",
            "token_usage": {"input_tokens": 10},
        }
    )
    assert sanitized == {"model_name": "model-v1", "finish_reason": "stop"}
