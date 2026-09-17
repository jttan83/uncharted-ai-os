from __future__ import annotations

import hashlib

import pytest
from pydantic import ValidationError

from scripts.uncharted_ai_os.editorial_eval.canonical import (
    canonical_digest,
    canonical_digest_from_bytes,
    canonical_json_bytes,
)
from scripts.uncharted_ai_os.editorial_eval.contracts import (
    CExecutionHistory,
    Condition,
    ConditionSubmission,
    CTerminalState,
    EvaluationResult,
    EvaluatorBinding,
    EvaluatorJudgment,
    FailureInfo,
)
from scripts.uncharted_ai_os.editorial_eval.invokers import ScriptedModelInvoker, ScriptedStep
from scripts.uncharted_ai_os.editorial_eval.validation import validate_evaluation_binding
from scripts.uncharted_ai_os.editorial_eval.workflows import _build_evaluator_request, _CallTracker

from .conftest import (
    FIXED_TIME,
    make_bound_evaluation,
    make_evaluator_call,
    make_judgment,
    make_model_call,
    make_package,
    make_submission,
)


def _tracker(run_id, invoker, model_config, bc_limits) -> _CallTracker:
    return _CallTracker(
        run_id=run_id,
        invoker=invoker,
        model_config=model_config,
        limits=bc_limits,
        clock=lambda: FIXED_TIME,
    )


def _evaluate(package, case_brief, model_config, bc_limits, *, run_id="run_binding_current"):
    request = _build_evaluator_request(canonical_json_bytes(case_brief).decode(), package)
    tracker = _tracker(
        run_id,
        ScriptedModelInvoker([ScriptedStep(parsed=make_judgment())]),
        model_config,
        bc_limits,
    )
    judgment, call = tracker.invoke_with_trace(
        role="c_evaluator",
        messages=request.messages,
        output_type=EvaluatorJudgment,
    )
    result = tracker.bind_evaluator_judgment(
        judgment=judgment,
        call=call,
        package_digest=request.package_digest,
    )
    return tracker, request, judgment, call, result


def test_normal_evaluation_binds_to_package_and_exact_call(
    case_brief, editorial_package, model_config, bc_limits
) -> None:
    tracker, _request, judgment, call, result = _evaluate(
        editorial_package,
        case_brief,
        model_config,
        bc_limits,
    )

    validate_evaluation_binding(
        result,
        editorial_package,
        case_brief,
        evaluator_call=call,
        run_id=tracker.run_id,
    )
    assert result.judgment is judgment
    assert result.binding.evaluator_call_id == call.call_id
    assert result.binding.evaluator_input_digest == call.input_digest


def test_evaluation_attached_to_different_package_fails(case_brief, editorial_package, model_config, bc_limits) -> None:
    tracker, _request, _judgment, call, result = _evaluate(
        editorial_package,
        case_brief,
        model_config,
        bc_limits,
    )
    package_b = make_package("binding_package_b")

    with pytest.raises(ValueError, match="package digest"):
        validate_evaluation_binding(
            result,
            package_b,
            case_brief,
            evaluator_call=call,
            run_id=tracker.run_id,
        )


def test_evaluation_for_earlier_revision_fails_against_revision(
    case_brief, editorial_package, model_config, bc_limits
) -> None:
    tracker, _request, _judgment, call, result = _evaluate(
        editorial_package,
        case_brief,
        model_config,
        bc_limits,
    )
    revised = editorial_package.model_copy(update={"package_version": "package_revision_two"})
    assert canonical_digest(revised) != canonical_digest(editorial_package)

    with pytest.raises(ValueError, match="package digest"):
        validate_evaluation_binding(
            result,
            revised,
            case_brief,
            evaluator_call=call,
            run_id=tracker.run_id,
        )


def test_stale_same_package_evaluation_replay_fails(case_brief, editorial_package, model_config, bc_limits) -> None:
    prior_tracker, _request, _judgment, prior_call, prior_result = _evaluate(
        editorial_package,
        case_brief,
        model_config,
        bc_limits,
        run_id="run_binding_prior",
    )
    current_tracker, _request, _judgment, current_call, _current_result = _evaluate(
        editorial_package,
        case_brief,
        model_config,
        bc_limits,
        run_id="run_binding_current",
    )

    assert prior_tracker.run_id != current_tracker.run_id
    with pytest.raises(ValueError, match="current Run"):
        validate_evaluation_binding(
            prior_result,
            editorial_package,
            case_brief,
            evaluator_call=prior_call,
            run_id=current_tracker.run_id,
        )
    with pytest.raises(ValueError, match="call ID"):
        validate_evaluation_binding(
            prior_result,
            editorial_package,
            case_brief,
            evaluator_call=current_call,
            run_id=current_tracker.run_id,
        )


def test_prior_call_replay_in_same_run_fails_against_new_call(
    case_brief, editorial_package, model_config, bc_limits
) -> None:
    request = _build_evaluator_request(canonical_json_bytes(case_brief).decode(), editorial_package)
    tracker = _tracker(
        "run_binding_replay",
        ScriptedModelInvoker(
            [
                ScriptedStep(parsed=make_judgment()),
                ScriptedStep(parsed=make_judgment()),
            ]
        ),
        model_config,
        bc_limits,
    )
    first_judgment, first_call = tracker.invoke_with_trace(
        role="c_evaluator",
        messages=request.messages,
        output_type=EvaluatorJudgment,
    )
    first_result = tracker.bind_evaluator_judgment(
        judgment=first_judgment,
        call=first_call,
        package_digest=request.package_digest,
    )
    _second_judgment, second_call = tracker.invoke_with_trace(
        role="c_evaluator",
        messages=request.messages,
        output_type=EvaluatorJudgment,
    )

    with pytest.raises(ValueError, match="call ID"):
        validate_evaluation_binding(
            first_result,
            editorial_package,
            case_brief,
            evaluator_call=second_call,
            run_id=tracker.run_id,
        )


@pytest.mark.parametrize("field", ["package_digest", "evaluator_call_id", "evaluator_input_digest", "evaluation_id"])
def test_model_cannot_inject_authoritative_identity(field) -> None:
    payload = make_judgment().model_dump(mode="python")
    payload[field] = "model-authored-provenance"

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        EvaluatorJudgment.model_validate(payload)


def test_legacy_v1_evaluation_is_not_silently_accepted_as_v2(editorial_package) -> None:
    legacy_payload = make_judgment().model_dump(mode="python")
    legacy_payload.update(
        {
            "schema_version": "phase-1f-a-evaluation-v1",
            "evaluation_id": "evaluation_legacy",
            "package_digest": canonical_digest(editorial_package),
        }
    )

    with pytest.raises(ValidationError):
        EvaluationResult.model_validate(legacy_payload)


def test_wrong_package_in_evaluator_request_fails_against_intended_package(
    case_brief, editorial_package, model_config, bc_limits
) -> None:
    package_sent = editorial_package
    package_intended = make_package("intended_package")
    tracker, _request, _judgment, call, result = _evaluate(
        package_sent,
        case_brief,
        model_config,
        bc_limits,
    )

    with pytest.raises(ValueError, match="package digest"):
        validate_evaluation_binding(
            result,
            package_intended,
            case_brief,
            evaluator_call=call,
            run_id=tracker.run_id,
        )


def test_binding_digest_uses_exact_canonical_package_inserted_in_context(case_brief, editorial_package) -> None:
    package_bytes = canonical_json_bytes(editorial_package)
    request = _build_evaluator_request(canonical_json_bytes(case_brief).decode(), editorial_package)
    package_marker = "Current editorial package JSON:\n"
    inserted_package = request.messages[1].content.split(package_marker, maxsplit=1)[1].encode()
    expected_digest = f"sha256:{hashlib.sha256(package_bytes).hexdigest()}"

    assert inserted_package == package_bytes
    assert request.package_digest == expected_digest
    assert request.package_digest == canonical_digest_from_bytes(package_bytes)
    assert request.package_digest == canonical_digest(editorial_package)


def test_malformed_judgment_fails_before_bound_result_creation() -> None:
    malformed = make_judgment().model_dump(mode="python")
    malformed.pop("domains")

    with pytest.raises(ValidationError):
        EvaluatorJudgment.model_validate(malformed)


def test_binding_rejects_equal_but_not_exact_trace_object(
    case_brief, editorial_package, model_config, bc_limits
) -> None:
    request = _build_evaluator_request(canonical_json_bytes(case_brief).decode(), editorial_package)
    tracker = _tracker(
        "run_binding_identity",
        ScriptedModelInvoker([ScriptedStep(parsed=make_judgment())]),
        model_config,
        bc_limits,
    )
    judgment, call = tracker.invoke_with_trace(
        role="c_evaluator",
        messages=request.messages,
        output_type=EvaluatorJudgment,
    )

    with pytest.raises(ValueError, match="exact trace"):
        tracker.bind_evaluator_judgment(
            judgment=judgment,
            call=call.model_copy(),
            package_digest=request.package_digest,
        )


@pytest.mark.parametrize("role", ["c_creator", "b_self_review"])
def test_non_evaluator_trace_cannot_be_substituted(
    case_brief, editorial_package, model_config, bc_limits, role
) -> None:
    request = _build_evaluator_request(canonical_json_bytes(case_brief).decode(), editorial_package)
    tracker = _tracker(
        "run_binding_wrong_role",
        ScriptedModelInvoker([ScriptedStep(parsed=make_judgment())]),
        model_config,
        bc_limits,
    )
    judgment, non_evaluator_call = tracker.invoke_with_trace(
        role=role,
        messages=request.messages,
        output_type=EvaluatorJudgment,
    )

    with pytest.raises(ValueError, match="successful evaluator call"):
        tracker.bind_evaluator_judgment(
            judgment=judgment,
            call=non_evaluator_call,
            package_digest=request.package_digest,
        )


def test_retry_binds_only_successful_evaluator_attempt(case_brief, editorial_package, model_config, bc_limits) -> None:
    request = _build_evaluator_request(canonical_json_bytes(case_brief).decode(), editorial_package)
    tracker = _tracker(
        "run_binding_retry",
        ScriptedModelInvoker(
            [
                ScriptedStep(
                    failure=FailureInfo(
                        failure_type="infrastructure_timeout",
                        safe_message="Transient timeout.",
                        retryable=True,
                    )
                ),
                ScriptedStep(parsed=make_judgment()),
            ]
        ),
        model_config,
        bc_limits,
    )

    judgment, successful_call = tracker.invoke_with_trace(
        role="c_evaluator",
        messages=request.messages,
        output_type=EvaluatorJudgment,
    )

    assert len(tracker.calls) == 2
    assert tracker.calls[0].failure is not None
    assert successful_call is tracker.calls[1]
    assert successful_call.attempt_number == 2
    with pytest.raises(ValueError, match="successful evaluator call"):
        tracker.bind_evaluator_judgment(
            judgment=judgment,
            call=tracker.calls[0],
            package_digest=request.package_digest,
        )
    result = tracker.bind_evaluator_judgment(
        judgment=judgment,
        call=successful_call,
        package_digest=request.package_digest,
    )
    assert result.binding.evaluator_call_id == successful_call.call_id


def test_trace_from_another_run_cannot_be_substituted(case_brief, editorial_package, model_config, bc_limits) -> None:
    _tracker_a, request, judgment, call, _result = _evaluate(
        editorial_package,
        case_brief,
        model_config,
        bc_limits,
        run_id="run_binding_other",
    )
    tracker_b = _tracker(
        "run_binding_target",
        ScriptedModelInvoker([]),
        model_config,
        bc_limits,
    )

    with pytest.raises(ValueError, match="current Run"):
        tracker_b.bind_evaluator_judgment(
            judgment=judgment,
            call=call,
            package_digest=request.package_digest,
        )


def test_input_digest_mismatch_fails_closed(case_brief, editorial_package, model_config, bc_limits) -> None:
    tracker, _request, _judgment, call, result = _evaluate(
        editorial_package,
        case_brief,
        model_config,
        bc_limits,
    )
    tampered = EvaluationResult(
        judgment=result.judgment,
        binding=EvaluatorBinding(
            package_digest=result.binding.package_digest,
            evaluator_call_id=result.binding.evaluator_call_id,
            evaluator_input_digest=f"sha256:{'f' * 64}",
        ),
    )

    with pytest.raises(ValueError, match="input digest"):
        validate_evaluation_binding(
            tampered,
            editorial_package,
            case_brief,
            evaluator_call=call,
            run_id=tracker.run_id,
        )


def test_c_history_rejects_duplicate_evaluation_for_one_package(editorial_package) -> None:
    call = make_evaluator_call("run_duplicate_binding", "duplicate_binding")
    evaluation = make_bound_evaluation(editorial_package, call)

    with pytest.raises(ValidationError, match="more evaluations than packages"):
        CExecutionHistory(
            packages=(editorial_package,),
            evaluations=(evaluation, evaluation),
            terminal_state=CTerminalState.EVALUATOR_DECISION,
        )


def test_c_history_rejects_missing_package_association() -> None:
    package_a = make_package("missing_association_a")
    package_b = make_package("missing_association_b")
    call_b = make_evaluator_call("run_missing_association", "missing_association_b")
    evaluation_b = make_bound_evaluation(package_b, call_b)
    assert canonical_digest(package_a) != canonical_digest(package_b)

    with pytest.raises(ValidationError, match="corresponding package"):
        CExecutionHistory(
            packages=(package_a, package_b),
            evaluations=(evaluation_b,),
            terminal_state=CTerminalState.EVALUATOR_DECISION,
        )


def test_submission_rejects_out_of_order_evaluator_calls_for_identical_packages(editorial_package) -> None:
    base = make_submission(Condition.C, "case_binding_order", "binding_order")
    creator_a = make_model_call(base.run_id, "binding_order_creator_a", "c_creator")
    creator_b = make_model_call(base.run_id, "binding_order_creator_b", "c_creator")
    call_a = make_evaluator_call(base.run_id, "binding_order_a")
    call_b = make_evaluator_call(base.run_id, "binding_order_b")
    evaluation_a = make_bound_evaluation(editorial_package, call_a)
    evaluation_b = make_bound_evaluation(editorial_package, call_b)
    history = CExecutionHistory(
        packages=(editorial_package, editorial_package),
        evaluations=(evaluation_b, evaluation_a),
        terminal_state=CTerminalState.EVALUATOR_DECISION,
    )
    payload = base.model_dump(mode="python")
    payload.update(
        {
            "first_pass_package": editorial_package,
            "final_package": editorial_package,
            "evaluator_result": evaluation_a,
            "c_history": history,
            "normalized": base.normalized.model_copy(
                update={"spoken_script": editorial_package.script.spoken_script}
            ),
            "trace": base.trace.model_copy(update={"calls": (creator_a, call_a, creator_b, call_b)}),
        }
    )

    with pytest.raises(ValidationError, match="revision window"):
        ConditionSubmission.model_validate(payload)


def test_submission_rejects_evaluation_before_its_revision_creator(editorial_package) -> None:
    base = make_submission(Condition.C, "case_binding_interleave", "binding_interleave")
    creator_a = make_model_call(base.run_id, "binding_interleave_creator_a", "c_creator")
    creator_b = make_model_call(base.run_id, "binding_interleave_creator_b", "c_creator")
    call_a = make_evaluator_call(base.run_id, "binding_interleave_a")
    call_b = make_evaluator_call(base.run_id, "binding_interleave_b")
    evaluation_a = make_bound_evaluation(editorial_package, call_a)
    evaluation_b = make_bound_evaluation(editorial_package, call_b)
    history = CExecutionHistory(
        packages=(editorial_package, editorial_package),
        evaluations=(evaluation_a, evaluation_b),
        terminal_state=CTerminalState.EVALUATOR_DECISION,
    )
    payload = base.model_dump(mode="python")
    payload.update(
        {
            "first_pass_package": editorial_package,
            "final_package": editorial_package,
            "evaluator_result": evaluation_b,
            "c_history": history,
            "normalized": base.normalized.model_copy(
                update={"spoken_script": editorial_package.script.spoken_script}
            ),
            "trace": base.trace.model_copy(update={"calls": (creator_a, call_a, call_b, creator_b)}),
        }
    )

    with pytest.raises(ValidationError, match="revision window"):
        ConditionSubmission.model_validate(payload)


@pytest.mark.parametrize("bound_call_index", [0, 1])
def test_submission_rejects_two_successful_evaluators_in_one_package_window(
    editorial_package, bound_call_index
) -> None:
    base = make_submission(Condition.C, "case_ambiguous_window", f"ambiguous_window_{bound_call_index}")
    creator = make_model_call(base.run_id, f"ambiguous_creator_{bound_call_index}", "c_creator")
    evaluator_calls = (
        make_evaluator_call(base.run_id, f"ambiguous_evaluator_{bound_call_index}_one"),
        make_evaluator_call(base.run_id, f"ambiguous_evaluator_{bound_call_index}_two"),
    )
    evaluation = make_bound_evaluation(editorial_package, evaluator_calls[bound_call_index])
    history = CExecutionHistory(
        packages=(editorial_package,),
        evaluations=(evaluation,),
        terminal_state=CTerminalState.EVALUATOR_DECISION,
    )
    payload = base.model_dump(mode="python")
    payload.update(
        {
            "first_pass_package": editorial_package,
            "final_package": editorial_package,
            "evaluator_result": evaluation,
            "c_history": history,
            "normalized": base.normalized.model_copy(
                update={"spoken_script": editorial_package.script.spoken_script}
            ),
            "trace": base.trace.model_copy(update={"calls": (creator, *evaluator_calls)}),
        }
    )

    with pytest.raises(ValidationError, match="exactly one successful evaluator call"):
        ConditionSubmission.model_validate(payload)


def test_submission_accepts_failed_evaluator_attempt_then_successful_retry(editorial_package) -> None:
    base = make_submission(Condition.C, "case_retry_window", "retry_window")
    creator = make_model_call(base.run_id, "retry_window_creator", "c_creator")
    failed_attempt = make_evaluator_call(base.run_id, "retry_window_failed").model_copy(
        update={
            "failure": FailureInfo(
                failure_type="infrastructure_timeout",
                safe_message="Transient timeout.",
                retryable=True,
            ),
            "infrastructure_retry_eligible": True,
            "retry_decision": "retry_scheduled",
        }
    )
    successful_retry = make_evaluator_call(base.run_id, "retry_window_success").model_copy(
        update={"attempt_number": 2, "infrastructure_retry": True}
    )
    evaluation = make_bound_evaluation(editorial_package, successful_retry)
    history = CExecutionHistory(
        packages=(editorial_package,),
        evaluations=(evaluation,),
        terminal_state=CTerminalState.EVALUATOR_DECISION,
    )
    payload = base.model_dump(mode="python")
    payload.update(
        {
            "first_pass_package": editorial_package,
            "final_package": editorial_package,
            "evaluator_result": evaluation,
            "c_history": history,
            "normalized": base.normalized.model_copy(
                update={"spoken_script": editorial_package.script.spoken_script}
            ),
            "trace": base.trace.model_copy(update={"calls": (creator, failed_attempt, successful_retry)}),
        }
    )

    validated = ConditionSubmission.model_validate(payload)
    assert validated.evaluator_result == evaluation


def test_submission_accepts_one_creator_evaluator_and_evaluation() -> None:
    submission = make_submission(Condition.C, "case_ordinary_window", "ordinary_window")

    assert ConditionSubmission.model_validate(submission.model_dump(mode="python")) == submission


def test_submission_accepts_one_successful_evaluator_per_revision() -> None:
    base = make_submission(Condition.C, "case_multi_revision", "multi_revision")
    package_a = make_package("multi_revision_a")
    package_b = make_package("multi_revision_b")
    creator_a = make_model_call(base.run_id, "multi_revision_creator_a", "c_creator")
    evaluator_a = make_evaluator_call(base.run_id, "multi_revision_evaluator_a")
    creator_b = make_model_call(base.run_id, "multi_revision_creator_b", "c_creator")
    evaluator_b = make_evaluator_call(base.run_id, "multi_revision_evaluator_b")
    evaluation_a = make_bound_evaluation(package_a, evaluator_a)
    evaluation_b = make_bound_evaluation(package_b, evaluator_b)
    history = CExecutionHistory(
        packages=(package_a, package_b),
        evaluations=(evaluation_a, evaluation_b),
        terminal_state=CTerminalState.EVALUATOR_DECISION,
    )
    payload = base.model_dump(mode="python")
    payload.update(
        {
            "first_pass_package": package_a,
            "final_package": package_b,
            "evaluator_result": evaluation_b,
            "c_history": history,
            "normalized": base.normalized.model_copy(update={"spoken_script": package_b.script.spoken_script}),
            "trace": base.trace.model_copy(
                update={
                    "calls": (creator_a, evaluator_a, creator_b, evaluator_b),
                    "substantive_revisions": 1,
                    "artifact_digests": (canonical_digest(package_a), canonical_digest(package_b)),
                }
            ),
        }
    )

    validated = ConditionSubmission.model_validate(payload)
    assert validated.c_history == history
