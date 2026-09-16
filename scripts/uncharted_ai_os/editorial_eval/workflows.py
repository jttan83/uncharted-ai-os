"""Explicit offline A/B/C workflow orchestration for Phase 1F-A."""

from __future__ import annotations

from collections.abc import Callable, Sequence  # noqa: TC003
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Literal, TypeVar
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from .canonical import assert_byte_identical_case_briefs, canonical_digest, canonical_json_bytes
from .contracts import (
    CaseBrief,
    CExecutionHistory,
    Condition,
    ConditionSubmission,
    CreatorStopDecision,
    CreatorStopTrace,
    CTerminalState,
    EditorialPackage,
    EvaluationResult,
    FailureInfo,
    InternalDecision,
    ModelCallTrace,
    NormalizedDecision,
    NormalizedSubmission,
    ResourceUsage,
    RunTrace,
    StrictModel,
    StructuralValidationTrace,
)
from .invokers import InvocationModelConfig, ModelInvoker, ModelMessage, ModelResponse
from .prompt_assets import PromptName, load_prompt_body
from .security import assert_credential_free, assert_external_tracing_disabled
from .validation import validate_editorial_package, validate_evaluation_binding

OutputT = TypeVar("OutputT", bound=BaseModel)

_TOTAL_INFRASTRUCTURE_RETRY_LIMIT = 1
_PROTOCOL_REVISION_LIMIT = 2
_CONDITION_A_CALL_CEILING = 2
_BC_PLANNED_CALLS = 6
_MINIMUM_BC_CALL_CEILING = _BC_PLANNED_CALLS + _TOTAL_INFRASTRUCTURE_RETRY_LIMIT


class ExecutionLimits(StrictModel):
    max_model_calls: int = Field(ge=1)
    max_substantive_revisions: int = Field(ge=0, le=2)
    max_total_tokens: int = Field(gt=0)
    max_total_latency_ms: int = Field(gt=0)
    max_cost: Decimal = Field(ge=0)
    currency: Literal["USD", "EUR", "GBP"]


class RuntimeConfiguration(StrictModel):
    """Validated development execution settings shared by all conditions."""

    primary_generator: InvocationModelConfig
    evaluator: InvocationModelConfig
    condition_a: ExecutionLimits
    condition_b: ExecutionLimits
    condition_c: ExecutionLimits

    @model_validator(mode="after")
    def validate_fairness(self) -> RuntimeConfiguration:
        assert_credential_free(self.model_dump(mode="python"))
        if (
            self.condition_a.max_model_calls != _CONDITION_A_CALL_CEILING
            or self.condition_a.max_substantive_revisions != 0
        ):
            msg = "Condition A requires one generation call and one total infrastructure-retry opportunity"
            raise ValueError(msg)
        if self.condition_b != self.condition_c:
            msg = "B and C execution ceilings must be identical"
            raise ValueError(msg)
        if self.condition_b.max_substantive_revisions != _PROTOCOL_REVISION_LIMIT:
            msg = "B and C require the protocol ceiling of two substantive revisions"
            raise ValueError(msg)
        if self.condition_b.max_model_calls < _MINIMUM_BC_CALL_CEILING:
            msg = "B/C call ceilings must permit six planned calls and one total infrastructure retry"
            raise ValueError(msg)
        return self

    def limits_for(self, condition: Condition) -> ExecutionLimits:
        return {
            Condition.A: self.condition_a,
            Condition.B: self.condition_b,
            Condition.C: self.condition_c,
        }[condition]


class CreatorResult(StrictModel):
    schema_version: Literal["phase-1f-a-creator-result-v1"] = "phase-1f-a-creator-result-v1"
    package: EditorialPackage | None = None
    stop_decision: CreatorStopDecision | None = None
    rationale: str = Field(min_length=1, max_length=10_000)
    next_action: str | None = Field(default=None, min_length=1, max_length=10_000)

    @model_validator(mode="after")
    def validate_result(self) -> CreatorResult:
        if (self.package is None) == (self.stop_decision is None):
            msg = "creator result requires exactly one of package or stop decision"
            raise ValueError(msg)
        if self.stop_decision is not None and self.next_action is None:
            msg = "creator stop decision requires a next action"
            raise ValueError(msg)
        return self


class SelfReviewDecision(str, Enum):
    ACCEPT = "accept"
    REVISE_PACKAGE = "revise_package"
    REVISE_BRIEF = "revise_brief"
    EVIDENCE_REQUIRED = "evidence_required"
    DO_NOT_DEVELOP = "do_not_develop"
    HUMAN_JUDGMENT_REQUIRED = "human_judgment_required"


class SelfReviewResult(StrictModel):
    schema_version: Literal["phase-1f-a-self-review-v1"] = "phase-1f-a-self-review-v1"
    decision: SelfReviewDecision
    rationale: str = Field(min_length=1, max_length=10_000)
    requested_changes: tuple[str, ...] = Field(default_factory=tuple, max_length=20)

    @model_validator(mode="after")
    def validate_requested_changes(self) -> SelfReviewResult:
        if self.decision is SelfReviewDecision.REVISE_PACKAGE and not self.requested_changes:
            msg = "package revision requires at least one requested change"
            raise ValueError(msg)
        return self


class WorkflowExecutionError(RuntimeError):
    def __init__(self, failure: FailureInfo) -> None:
        super().__init__(failure.safe_message)
        self.failure = failure


class _CallTracker:
    def __init__(
        self,
        *,
        run_id: str,
        invoker: ModelInvoker,
        model_config: InvocationModelConfig,
        limits: ExecutionLimits,
        clock: Callable[[], datetime],
    ) -> None:
        self.run_id = run_id
        self.invoker = invoker
        self.model_config = model_config
        self.limits = limits
        self.clock = clock
        self.calls: list[ModelCallTrace] = []
        self.validations: list[StructuralValidationTrace] = []
        self.failures: list[FailureInfo] = []
        self.parsed_results: list[tuple[str, BaseModel]] = []
        self.limitations: list[str] = []
        self.infrastructure_retries = 0

    def invoke(
        self,
        *,
        role: Literal["a_generator", "b_generator", "b_self_review", "c_creator", "c_evaluator"],
        messages: Sequence[ModelMessage],
        output_type: type[OutputT],
        model_config: InvocationModelConfig | None = None,
    ) -> OutputT:
        assert_external_tracing_disabled()
        active_model_config = model_config or self.model_config
        attempt = 1
        while True:
            if len(self.calls) >= self.limits.max_model_calls:
                failure = FailureInfo(
                    failure_type="model_call_budget_exceeded",
                    safe_message="The model-call ceiling was reached.",
                    retryable=False,
                )
                self.failures.append(failure)
                raise WorkflowExecutionError(failure)
            started = self.clock()
            response = self.invoker.invoke(
                messages,
                output_type,
                active_model_config,
                attempt_number=attempt,
            )
            ended = self.clock()
            self._record_call(
                role=role,
                messages=messages,
                response=response,
                model_config=active_model_config,
                started=started,
                ended=ended,
            )
            if response.parsed is not None:
                self.parsed_results.append((role, response.parsed))
            try:
                self._enforce_resource_limits()
            except WorkflowExecutionError:
                if response.failure is not None and response.failure.retryable:
                    self._record_retry_decision("resource_ceiling")
                raise
            if response.parsed is not None:
                return response.parsed
            if response.failure is None:
                msg = "model response contract lost both result and failure"
                raise RuntimeError(msg)
            if not response.failure.retryable or self.infrastructure_retries >= _TOTAL_INFRASTRUCTURE_RETRY_LIMIT:
                if response.failure.retryable:
                    self._record_retry_decision("retry_limit_reached")
                self.failures.append(response.failure)
                raise WorkflowExecutionError(response.failure)
            self._record_retry_decision("retry_scheduled")
            self.infrastructure_retries += 1
            attempt += 1

    def record_validation(self, result: StructuralValidationTrace) -> None:
        self.validations.append(result)

    def aggregate_usage(self) -> ResourceUsage:
        usages = [call.usage for call in self.calls]
        cost_values = [usage.monetary_cost for usage in usages]
        currencies = {usage.currency for usage in usages if usage.currency is not None}
        cost_known = bool(usages) and all(value is not None for value in cost_values) and len(currencies) == 1
        return ResourceUsage(
            input_tokens=_sum_if_all_known([usage.input_tokens for usage in usages]),
            output_tokens=_sum_if_all_known([usage.output_tokens for usage in usages]),
            cached_input_tokens=_sum_if_all_known([usage.cached_input_tokens for usage in usages]),
            reasoning_tokens=_sum_if_all_known([usage.reasoning_tokens for usage in usages]),
            tool_calls=_sum_if_all_known([usage.tool_calls for usage in usages]),
            monetary_cost=(
                sum((value for value in cost_values if value is not None), Decimal(0)) if cost_known else None
            ),
            currency=next(iter(currencies)) if cost_known else None,
        )

    def _record_call(
        self,
        *,
        role: Literal["a_generator", "b_generator", "b_self_review", "c_creator", "c_evaluator"],
        messages: Sequence[ModelMessage],
        response: ModelResponse[BaseModel],
        model_config: InvocationModelConfig,
        started: datetime,
        ended: datetime,
    ) -> None:
        sequence = len(self.calls) + 1
        call_id = f"call_{self.run_id.removeprefix('run_')[:16]}_{sequence:02d}"
        self.calls.append(
            ModelCallTrace(
                call_id=call_id,
                run_id=self.run_id,
                role=role,
                prompt_digest=canonical_digest(messages[0].content),
                input_digest=canonical_digest([message.model_dump(mode="json") for message in messages]),
                provider=model_config.provider,
                model_identifier=model_config.model_identifier,
                reasoning=model_config.reasoning,
                model_config_digest=canonical_digest(model_config),
                provider_internal_retries=model_config.provider_internal_retries,
                attempt_number=response.attempt_number,
                infrastructure_retry=response.attempt_number > 1,
                infrastructure_retry_eligible=bool(response.failure and response.failure.retryable),
                started_at=started,
                ended_at=ended,
                latency_ms=response.latency_ms,
                usage=response.usage,
                failure=response.failure,
            )
        )

    def _record_retry_decision(
        self,
        decision: Literal["retry_scheduled", "retry_limit_reached", "resource_ceiling"],
    ) -> None:
        self.calls[-1] = self.calls[-1].model_copy(update={"retry_decision": decision})

    def _enforce_resource_limits(self) -> None:
        if any(call.usage.currency is not None and call.usage.currency != self.limits.currency for call in self.calls):
            failure = FailureInfo(
                failure_type="cost_currency_mismatch",
                safe_message="Provider cost currency does not match the frozen budget currency.",
                retryable=False,
            )
            self.failures.append(failure)
            raise WorkflowExecutionError(failure)
        usage = self.aggregate_usage()
        accounted_tokens = usage.accounted_total_tokens
        if accounted_tokens is None:
            self._record_limitation("token_ceiling_not_enforced_unknown_usage")
        elif accounted_tokens > self.limits.max_total_tokens:
            failure = FailureInfo(
                failure_type="token_budget_exceeded",
                safe_message="Known token usage exceeded the frozen ceiling.",
                retryable=False,
            )
            self.failures.append(failure)
            raise WorkflowExecutionError(failure)
        total_latency = sum(call.latency_ms for call in self.calls)
        if total_latency > self.limits.max_total_latency_ms:
            failure = FailureInfo(
                failure_type="latency_budget_exceeded",
                safe_message="Model latency exceeded the frozen ceiling.",
                retryable=False,
            )
            self.failures.append(failure)
            raise WorkflowExecutionError(failure)
        if usage.monetary_cost is None:
            self._record_limitation("cost_ceiling_not_enforced_unknown_cost")
        elif usage.monetary_cost > self.limits.max_cost:
            failure = FailureInfo(
                failure_type="cost_budget_exceeded",
                safe_message="Known model cost exceeded the frozen ceiling.",
                retryable=False,
            )
            self.failures.append(failure)
            raise WorkflowExecutionError(failure)

    def _record_limitation(self, code: str) -> None:
        if code not in self.limitations:
            self.limitations.append(code)


class _WorkflowBase:
    condition: Condition

    def __init__(
        self,
        *,
        invoker: ModelInvoker,
        runtime_config: RuntimeConfiguration,
        experiment_version: str = "phase_1f_a_development_v1",
        manifest_version: str = "unfrozen_development_manifest_v1",
        clock: Callable[[], datetime] | None = None,
        run_id_factory: Callable[[], str] | None = None,
    ) -> None:
        runtime_config = RuntimeConfiguration.model_validate(runtime_config.model_dump(mode="python"))
        self.invoker = invoker
        self.runtime_config = runtime_config
        self.model_config = runtime_config.primary_generator
        self.limits = runtime_config.limits_for(self.condition)
        self.experiment_version = experiment_version
        self.manifest_version = manifest_version
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.run_id_factory = run_id_factory or new_run_id

    def _tracker(self, run_id: str) -> _CallTracker:
        return _CallTracker(
            run_id=run_id,
            invoker=self.invoker,
            model_config=self.model_config,
            limits=self.limits,
            clock=self.clock,
        )

    def _finish(
        self,
        *,
        run_id: str,
        case_id: str,
        started_at: datetime,
        input_surface_digest: str,
        brief_digest: str | None,
        tracker: _CallTracker,
        normalized: NormalizedSubmission,
        revisions: int,
        first_pass: EditorialPackage | None = None,
        final_package: EditorialPackage | None = None,
        evaluator_result: EvaluationResult | None = None,
        c_history: CExecutionHistory | None = None,
        original_run_id: str | None = None,
    ) -> ConditionSubmission:
        retained_packages = (
            c_history.packages
            if c_history is not None
            else tuple(package for package in (first_pass, final_package) if package is not None)
        )
        artifacts = tuple(dict.fromkeys(canonical_digest(package) for package in retained_packages))
        trace = RunTrace(
            run_id=run_id,
            experiment_version=self.experiment_version,
            manifest_version=self.manifest_version,
            case_id=case_id,
            condition=self.condition,
            original_run_id=original_run_id,
            case_brief_digest=brief_digest,
            input_surface_digest=input_surface_digest,
            calls=tuple(tracker.calls),
            substantive_revisions=revisions,
            max_substantive_revisions=self.limits.max_substantive_revisions,
            max_model_calls=self.limits.max_model_calls,
            max_total_tokens=self.limits.max_total_tokens,
            max_total_latency_ms=self.limits.max_total_latency_ms,
            max_cost=self.limits.max_cost,
            budget_currency=self.limits.currency,
            actual_usage=tracker.aggregate_usage(),
            artifact_digests=artifacts,
            structural_validations=tuple(tracker.validations),
            failures=tuple(tracker.failures),
            terminal_decision=normalized.decision,
            deviations=tuple(tracker.limitations),
            started_at=started_at,
            completed_at=self.clock(),
        )
        return ConditionSubmission(
            run_id=run_id,
            case_id=case_id,
            condition=self.condition,
            case_brief_digest=brief_digest,
            first_pass_package=first_pass,
            final_package=final_package,
            evaluator_result=evaluator_result,
            c_history=c_history,
            normalized=normalized,
            trace=trace,
        )


class ConditionAWorkflow(_WorkflowBase):
    condition = Condition.A

    def run(self, *, case_id: str, ecological_input: str, original_run_id: str | None = None) -> ConditionSubmission:
        run_id = self.run_id_factory()
        started_at = self.clock()
        tracker = self._tracker(run_id)
        input_digest = canonical_digest(ecological_input)
        messages = _messages(PromptName.CONDITION_A, ecological_input)
        try:
            normalized = tracker.invoke(role="a_generator", messages=messages, output_type=NormalizedSubmission)
        except WorkflowExecutionError as exc:
            normalized = _execution_failure_submission(exc.failure)
        return self._finish(
            run_id=run_id,
            case_id=case_id,
            started_at=started_at,
            input_surface_digest=input_digest,
            brief_digest=None,
            tracker=tracker,
            normalized=normalized,
            revisions=0,
            original_run_id=original_run_id,
        )


class ConditionBWorkflow(_WorkflowBase):
    condition = Condition.B

    def run(
        self,
        *,
        brief: CaseBrief,
        committed_brief_digest: str | None = None,
        original_run_id: str | None = None,
    ) -> ConditionSubmission:
        run_id = self.run_id_factory()
        started_at = self.clock()
        tracker = self._tracker(run_id)
        brief_digest = canonical_digest(brief)
        if committed_brief_digest is not None and brief_digest != committed_brief_digest:
            msg = "Condition B CaseBrief does not match the committed digest"
            raise ValueError(msg)
        brief_text = canonical_json_bytes(brief).decode()
        input_digest = brief_digest
        first_pass: EditorialPackage | None = None
        current: EditorialPackage | None = None
        revisions = 0
        try:
            result = tracker.invoke(
                role="b_generator",
                messages=_messages(PromptName.CONDITION_B, f"Canonical CaseBrief JSON:\n{brief_text}"),
                output_type=CreatorResult,
            )
            if result.stop_decision is not None:
                normalized = _normalize_creator_stop(result)
            else:
                if result.package is None:
                    msg = "validated creator result did not include a package"
                    raise RuntimeError(msg)
                first_pass = result.package
                current = result.package
                invalid = self._record_validation(tracker, current, brief)
                if invalid is not None:
                    normalized = invalid
                else:
                    normalized, current, revisions = self._self_review_loop(
                        tracker=tracker,
                        brief=brief,
                        brief_text=brief_text,
                        package=current,
                    )
        except WorkflowExecutionError as exc:
            normalized = _execution_failure_submission(exc.failure)
        return self._finish(
            run_id=run_id,
            case_id=brief.case_id,
            started_at=started_at,
            input_surface_digest=input_digest,
            brief_digest=brief_digest,
            tracker=tracker,
            normalized=normalized,
            revisions=revisions,
            first_pass=first_pass,
            final_package=current,
            original_run_id=original_run_id,
        )

    def _self_review_loop(
        self,
        *,
        tracker: _CallTracker,
        brief: CaseBrief,
        brief_text: str,
        package: EditorialPackage,
    ) -> tuple[NormalizedSubmission, EditorialPackage, int]:
        current = package
        revisions = 0
        while True:
            review_context = (
                f"Canonical CaseBrief JSON:\n{brief_text}\n\n"
                f"Current package JSON:\n{canonical_json_bytes(current).decode()}"
            )
            review = tracker.invoke(
                role="b_self_review",
                messages=_messages(PromptName.CONDITION_B_SELF_REVIEW, review_context),
                output_type=SelfReviewResult,
            )
            if review.decision is SelfReviewDecision.ACCEPT:
                normalized = _candidate_submission(NormalizedDecision.PROCEED_CANDIDATE, current, review.rationale)
                return normalized, current, revisions
            direct = _normalize_self_review_stop(review)
            if direct is not None:
                return direct, current, revisions
            if revisions >= self.limits.max_substantive_revisions:
                return (
                    _candidate_submission(NormalizedDecision.EDITORIAL_REVISION_REQUIRED, current, review.rationale),
                    current,
                    revisions,
                )
            revision_context = (
                f"Canonical CaseBrief JSON:\n{brief_text}\n\n"
                f"Current package JSON:\n{canonical_json_bytes(current).decode()}\n\n"
                f"Material self-review:\n{canonical_json_bytes(review).decode()}\n\n"
                "Return a complete revised package or a proportionate stop decision."
            )
            revised = tracker.invoke(
                role="b_generator",
                messages=_messages(PromptName.CONDITION_B, revision_context),
                output_type=CreatorResult,
            )
            revisions += 1
            if revised.stop_decision is not None:
                return _normalize_creator_stop(revised), current, revisions
            if revised.package is None:
                msg = "validated revision result did not include a package"
                raise RuntimeError(msg)
            current = revised.package
            invalid = self._record_validation(tracker, current, brief)
            if invalid is not None:
                return invalid, current, revisions

    @staticmethod
    def _record_validation(
        tracker: _CallTracker, package: EditorialPackage, brief: CaseBrief
    ) -> NormalizedSubmission | None:
        validation = validate_editorial_package(package, brief)
        tracker.record_validation(validation)
        return _structural_failure_submission(package, validation) if not validation.valid else None


class ConditionCWorkflow(_WorkflowBase):
    condition = Condition.C

    def __init__(
        self,
        *,
        invoker: ModelInvoker,
        runtime_config: RuntimeConfiguration,
        experiment_version: str = "phase_1f_a_development_v1",
        manifest_version: str = "unfrozen_development_manifest_v1",
        clock: Callable[[], datetime] | None = None,
        run_id_factory: Callable[[], str] | None = None,
    ) -> None:
        super().__init__(
            invoker=invoker,
            runtime_config=runtime_config,
            experiment_version=experiment_version,
            manifest_version=manifest_version,
            clock=clock,
            run_id_factory=run_id_factory,
        )
        self.evaluator_model_config = runtime_config.evaluator

    def run(
        self,
        *,
        brief: CaseBrief,
        committed_brief_digest: str | None = None,
        original_run_id: str | None = None,
    ) -> ConditionSubmission:
        run_id = self.run_id_factory()
        started_at = self.clock()
        tracker = self._tracker(run_id)
        brief_digest = canonical_digest(brief)
        if committed_brief_digest is not None and brief_digest != committed_brief_digest:
            msg = "Condition C CaseBrief does not match the committed digest"
            raise ValueError(msg)
        brief_text = canonical_json_bytes(brief).decode()
        revisions = 0
        terminal_state = CTerminalState.EXECUTION_FAILURE
        try:
            created = tracker.invoke(
                role="c_creator",
                messages=_messages(PromptName.CONDITION_C_CREATOR, f"Canonical CaseBrief JSON:\n{brief_text}"),
                output_type=CreatorResult,
            )
            if created.stop_decision is not None:
                normalized = _normalize_creator_stop(created)
                terminal_state = CTerminalState.PRE_PACKAGE_CREATOR_STOP
            else:
                if created.package is None:
                    msg = "validated creator result did not include a package"
                    raise RuntimeError(msg)
                validation = validate_editorial_package(created.package, brief)
                tracker.record_validation(validation)
                if not validation.valid:
                    normalized = _structural_failure_submission(created.package, validation)
                    terminal_state = CTerminalState.DETERMINISTIC_VALIDATION_FAILURE
                else:
                    normalized, revisions, terminal_state = self._evaluation_loop(
                        tracker=tracker,
                        brief=brief,
                        brief_text=brief_text,
                        package=created.package,
                    )
        except WorkflowExecutionError as exc:
            normalized = _execution_failure_submission(exc.failure)
            terminal_state = _failure_terminal_state(tracker, exc.failure)
        history = _build_c_history(tracker, terminal_state)
        revisions = max(revisions, len(history.packages) - 1, 0)
        first_pass = history.packages[0] if history.packages else None
        current = history.packages[-1] if history.packages else None
        evaluation = history.evaluations[-1] if history.evaluations else None
        return self._finish(
            run_id=run_id,
            case_id=brief.case_id,
            started_at=started_at,
            input_surface_digest=brief_digest,
            brief_digest=brief_digest,
            tracker=tracker,
            normalized=normalized,
            revisions=revisions,
            first_pass=first_pass,
            final_package=current,
            evaluator_result=evaluation,
            c_history=history,
            original_run_id=original_run_id,
        )

    def _evaluation_loop(
        self,
        *,
        tracker: _CallTracker,
        brief: CaseBrief,
        brief_text: str,
        package: EditorialPackage,
    ) -> tuple[NormalizedSubmission, int, CTerminalState]:
        current = package
        revisions = 0
        while True:
            # A fresh evaluator context contains only the shared/evaluator prompt,
            # canonical brief, and current package. No prior evaluation is passed.
            evaluation_context = (
                f"Canonical CaseBrief JSON:\n{brief_text}\n\n"
                f"Current editorial package JSON:\n{canonical_json_bytes(current).decode()}"
            )
            evaluation = tracker.invoke(
                role="c_evaluator",
                messages=_messages(PromptName.CONDITION_C_EVALUATOR, evaluation_context),
                output_type=EvaluationResult,
                model_config=self.evaluator_model_config,
            )
            try:
                validate_evaluation_binding(evaluation, current, brief)
            except ValueError as exc:
                failure = FailureInfo(
                    failure_type="evaluator_binding_failure",
                    safe_message="Evaluator output was not bound to the package it received.",
                    retryable=False,
                )
                tracker.failures.append(failure)
                raise WorkflowExecutionError(failure) from exc
            if evaluation.decision not in {InternalDecision.MINOR_REVISION, InternalDecision.MAJOR_REVISION}:
                return normalize_internal_decision(evaluation, current), revisions, CTerminalState.EVALUATOR_DECISION
            if revisions >= self.limits.max_substantive_revisions:
                return (
                    _candidate_submission(
                        NormalizedDecision.EDITORIAL_REVISION_REQUIRED,
                        current,
                        "The candidate still requires material editorial revision.",
                    ),
                    revisions,
                    CTerminalState.REVISION_BUDGET_EXHAUSTED,
                )
            revision_context = (
                f"Canonical CaseBrief JSON:\n{brief_text}\n\n"
                f"Current editorial package JSON:\n{canonical_json_bytes(current).decode()}\n\n"
                f"Evaluator result JSON:\n{canonical_json_bytes(evaluation).decode()}"
            )
            revised = tracker.invoke(
                role="c_creator",
                messages=_messages(PromptName.CONDITION_C_REVISION, revision_context),
                output_type=CreatorResult,
            )
            revisions += 1
            if revised.stop_decision is not None:
                return _normalize_creator_stop(revised), revisions, CTerminalState.REVISION_CREATOR_STOP
            if revised.package is None:
                msg = "validated revision result did not include a package"
                raise RuntimeError(msg)
            current = revised.package
            validation = validate_editorial_package(current, brief)
            tracker.record_validation(validation)
            if not validation.valid:
                return (
                    _structural_failure_submission(current, validation),
                    revisions,
                    CTerminalState.DETERMINISTIC_VALIDATION_FAILURE,
                )


def run_comparable_bc(
    *,
    brief_for_b: CaseBrief,
    brief_for_c: CaseBrief,
    condition_b: ConditionBWorkflow,
    condition_c: ConditionCWorkflow,
    committed_brief_digest: str | None = None,
    boundary_callback: Callable[[str], None] | None = None,
) -> tuple[ConditionSubmission, ConditionSubmission]:
    """Prove canonical B/C byte identity before either workflow executes."""
    digest = assert_byte_identical_case_briefs(brief_for_b, brief_for_c, committed_brief_digest)
    if condition_b.model_config != condition_c.model_config:
        msg = "B and C generator model configurations must be identical"
        raise ValueError(msg)
    if condition_b.limits != condition_c.limits:
        msg = "B and C execution ceilings must be identical for the paired comparison"
        raise ValueError(msg)
    if (
        condition_b.limits.max_substantive_revisions != _PROTOCOL_REVISION_LIMIT
        or condition_c.limits.max_substantive_revisions != _PROTOCOL_REVISION_LIMIT
    ):
        msg = "B and C paired execution requires the protocol ceiling of two revisions"
        raise ValueError(msg)
    if boundary_callback is not None:
        boundary_callback("condition_b_started")
    submission_b = condition_b.run(brief=brief_for_b, committed_brief_digest=digest)
    if boundary_callback is not None:
        boundary_callback("condition_b_finished")
        boundary_callback("condition_c_started")
    submission_c = condition_c.run(brief=brief_for_c, committed_brief_digest=digest)
    if boundary_callback is not None:
        boundary_callback("condition_c_finished")
    return submission_b, submission_c


def new_run_id() -> str:
    """Create one stable correlation identifier for a future execution."""
    return f"run_{uuid4().hex}"


def _messages(prompt_name: PromptName, user_content: str) -> tuple[ModelMessage, ModelMessage]:
    sections = [load_prompt_body(PromptName.SHARED)]
    if prompt_name is not PromptName.CONDITION_A:
        sections.append(load_prompt_body(PromptName.CANONICAL_STANDARD))
    sections.append(load_prompt_body(prompt_name))
    system = "\n\n".join(sections)
    return ModelMessage(role="system", content=system), ModelMessage(role="user", content=user_content)


def _build_c_history(tracker: _CallTracker, terminal_state: CTerminalState) -> CExecutionHistory:
    packages: list[EditorialPackage] = []
    evaluations: list[EvaluationResult] = []
    creator_stops: list[CreatorStopTrace] = []
    for role, parsed in tracker.parsed_results:
        if role == "c_creator" and isinstance(parsed, CreatorResult):
            if parsed.package is not None:
                packages.append(parsed.package)
            elif parsed.stop_decision is not None and parsed.next_action is not None:
                creator_stops.append(
                    CreatorStopTrace(
                        phase="pre_package" if not packages else "revision",
                        decision=parsed.stop_decision,
                        rationale=parsed.rationale,
                        next_action=parsed.next_action,
                    )
                )
        elif role == "c_evaluator" and isinstance(parsed, EvaluationResult):
            evaluations.append(parsed)

    evaluator_failures = [
        call.failure for call in tracker.calls if call.role == "c_evaluator" and call.failure is not None
    ]
    evaluator_failures.extend(
        failure for failure in tracker.failures if failure.failure_type == "evaluator_binding_failure"
    )
    return CExecutionHistory(
        packages=tuple(packages),
        evaluations=tuple(evaluations),
        creator_stops=tuple(creator_stops),
        evaluator_failures=tuple(evaluator_failures),
        terminal_state=terminal_state,
    )


def _failure_terminal_state(tracker: _CallTracker, failure: FailureInfo) -> CTerminalState:
    if failure.failure_type in {
        "model_call_budget_exceeded",
        "token_budget_exceeded",
        "latency_budget_exceeded",
        "cost_budget_exceeded",
    }:
        return CTerminalState.RESOURCE_BUDGET_EXHAUSTED
    if failure.failure_type == "evaluator_binding_failure" or (
        tracker.calls and tracker.calls[-1].role == "c_evaluator"
    ):
        return CTerminalState.EVALUATOR_FAILURE
    return CTerminalState.EXECUTION_FAILURE


def _normalize_creator_stop(result: CreatorResult) -> NormalizedSubmission:
    if result.stop_decision is None:
        msg = "creator stop normalization requires a stop decision"
        raise ValueError(msg)
    mapping = {
        CreatorStopDecision.RETURN_UPSTREAM: NormalizedDecision.REVISE_BRIEF,
        CreatorStopDecision.BLOCKED_EVIDENCE: NormalizedDecision.EVIDENCE_REQUIRED,
        CreatorStopDecision.REJECT: NormalizedDecision.DO_NOT_DEVELOP,
        CreatorStopDecision.HUMAN_ESCALATION: NormalizedDecision.HUMAN_JUDGMENT_REQUIRED,
    }
    return NormalizedSubmission(
        decision=mapping[result.stop_decision],
        explanation=result.rationale,
        next_action=result.next_action,
    )


def _normalize_self_review_stop(review: SelfReviewResult) -> NormalizedSubmission | None:
    mapping = {
        SelfReviewDecision.REVISE_BRIEF: NormalizedDecision.REVISE_BRIEF,
        SelfReviewDecision.EVIDENCE_REQUIRED: NormalizedDecision.EVIDENCE_REQUIRED,
        SelfReviewDecision.DO_NOT_DEVELOP: NormalizedDecision.DO_NOT_DEVELOP,
        SelfReviewDecision.HUMAN_JUDGMENT_REQUIRED: NormalizedDecision.HUMAN_JUDGMENT_REQUIRED,
    }
    decision = mapping.get(review.decision)
    if decision is None:
        return None
    return NormalizedSubmission(decision=decision, explanation=review.rationale, next_action=review.rationale)


def normalize_internal_decision(evaluation: EvaluationResult, package: EditorialPackage) -> NormalizedSubmission:
    if evaluation.decision is InternalDecision.READY_FOR_HUMAN_APPROVAL:
        return _candidate_submission(
            NormalizedDecision.PROCEED_CANDIDATE,
            package,
            "A candidate is supplied for independent human editorial judgment.",
        )
    if evaluation.decision in {InternalDecision.MINOR_REVISION, InternalDecision.MAJOR_REVISION}:
        return _candidate_submission(
            NormalizedDecision.EDITORIAL_REVISION_REQUIRED,
            package,
            "The candidate still requires material editorial revision.",
        )
    mapping = {
        InternalDecision.RETURN_UPSTREAM: (
            NormalizedDecision.REVISE_BRIEF,
            "The brief contains a material upstream issue.",
            "Revise the audience, objective, insight, point of view, or attention premise before continuing.",
        ),
        InternalDecision.BLOCKED_EVIDENCE: (
            NormalizedDecision.EVIDENCE_REQUIRED,
            "A material claim is not adequately supported.",
            "Supply fit-for-purpose evidence, qualify the claim responsibly, or remove it.",
        ),
        InternalDecision.REJECT: (
            NormalizedDecision.DO_NOT_DEVELOP,
            "This content should not be developed for the stated cohort and purpose.",
            "Retire or materially reframe the idea before reconsideration.",
        ),
        InternalDecision.HUMAN_ESCALATION: (
            NormalizedDecision.HUMAN_JUDGMENT_REQUIRED,
            "A material judgment or authority question requires a human decision.",
            "Obtain the required human judgment before continuing.",
        ),
    }
    decision, explanation, next_action = mapping[evaluation.decision]
    return NormalizedSubmission(
        decision=decision,
        explanation=explanation,
        next_action=next_action,
    )


def _candidate_submission(
    decision: NormalizedDecision, package: EditorialPackage, explanation: str
) -> NormalizedSubmission:
    return NormalizedSubmission(
        decision=decision,
        spoken_script=package.script.spoken_script,
        explanation=explanation,
    )


def _structural_failure_submission(
    package: EditorialPackage, validation: StructuralValidationTrace
) -> NormalizedSubmission:
    evidence_problem = any(
        "evidence" in issue or "factual" in issue or "claim" in issue for issue in validation.issue_codes
    )
    explanation = f"Deterministic package validation failed: {', '.join(validation.issue_codes)}."
    if evidence_problem:
        return NormalizedSubmission(
            decision=NormalizedDecision.EVIDENCE_REQUIRED,
            explanation=explanation,
            next_action="Resolve the Claim Map evidence state before development continues.",
        )
    return _candidate_submission(NormalizedDecision.EDITORIAL_REVISION_REQUIRED, package, explanation)


def _execution_failure_submission(failure: FailureInfo) -> NormalizedSubmission:
    return NormalizedSubmission(
        decision=NormalizedDecision.HUMAN_JUDGMENT_REQUIRED,
        explanation=failure.safe_message,
        next_action="Review the failed trace and decide whether a protocol-valid rerun is permitted.",
    )


def _sum_if_all_known(values: Sequence[int | None]) -> int | None:
    if values and all(value is not None for value in values):
        return sum(value for value in values if value is not None)
    return None
