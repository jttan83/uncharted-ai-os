"""Narrow, durable operator entry point for the approved development rehearsal."""

from __future__ import annotations

import os
import secrets
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Literal
from uuid import uuid4

from pydantic import Field, model_validator

from .blinding import RevealCustodian
from .contracts import BlindCandidate, CaseBrief, DatasetClass, StrictModel
from .invokers import (
    InvocationModelConfig,
    LangChainModelInvoker,
    build_langchain_parameters,
    preflight_langchain_model_config,
)
from .rehearsal import (
    DevelopmentWorkflows,
    build_single_case_development_blind_bundle,
    load_development_cases,
    persist_development_blind_bundle,
    run_development_case_with_persistence,
)
from .security import assert_external_tracing_disabled
from .storage import PrivateExperimentStorage
from .workflows import ConditionAWorkflow, ConditionBWorkflow, ConditionCWorkflow, ExecutionLimits, RuntimeConfiguration

if TYPE_CHECKING:
    from collections.abc import Callable

APPROVED_DEVELOPMENT_PROFILE = "phase1f-a-dev-v1"
_EXPECTED_BRANCH = "uncharted-v0.1"
_REQUIRED_LABELS = frozenset({"DEVELOPMENT ONLY", "CONTAMINATED", "NOT HOLDOUT"})
_EXPECTED_LANGCHAIN_PARAMETERS = {
    "temperature": 0.2,
    "max_tokens": 2_000,
    "timeout": 30,
    "max_retries": 0,
    "seed": 7,
    "reasoning_effort": "medium",
}
# The installed reasoning-model adapter intentionally removes the requested
# non-default temperature. Treat any future normalization change as treatment drift.
_EXPECTED_EFFECTIVE_ADAPTER_CONFIGURATION = {
    "model": "gpt-5.6-sol",
    "reasoning_effort": "medium",
    "temperature": None,
    "seed": 7,
    "max_completion_tokens": 2_000,
    "timeout": 30,
    "max_retries": 0,
}
_LIFECYCLE_STATES = (
    "started",
    "preflight_passed",
    "condition_a_started",
    "condition_a_finished",
    "condition_b_started",
    "condition_b_finished",
    "condition_c_started",
    "condition_c_finished",
    "execution_persisted",
    "blind_bundle_persisted",
    "completed",
)
LifecycleState = Literal[
    "started",
    "preflight_passed",
    "condition_a_started",
    "condition_a_finished",
    "condition_b_started",
    "condition_b_finished",
    "condition_c_started",
    "condition_c_finished",
    "execution_persisted",
    "blind_bundle_persisted",
    "completed",
]


class OperatorLifecycleEvent(StrictModel):
    state: LifecycleState
    timestamp: datetime

    @model_validator(mode="after")
    def require_aware_timestamp(self) -> OperatorLifecycleEvent:
        if self.timestamp.tzinfo is None:
            msg = "operator lifecycle timestamps must be timezone-aware"
            raise ValueError(msg)
        return self


class OperatorLifecycleRecord(StrictModel):
    schema_version: Literal["phase-1f-a-operator-lifecycle-v1"] = "phase-1f-a-operator-lifecycle-v1"
    operator_run_id: str = Field(pattern=r"^operator_[0-9a-f]{32}$")
    profile: Literal["phase1f-a-dev-v1"]
    case_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{2,127}$")
    events: tuple[OperatorLifecycleEvent, ...]
    exit_status: int | None = None
    outcome: Literal["running", "succeeded", "failed"] = "running"

    @model_validator(mode="after")
    def validate_sequence(self) -> OperatorLifecycleRecord:
        indexes = [_LIFECYCLE_STATES.index(event.state) for event in self.events]
        if not indexes or indexes[0] != 0 or indexes != sorted(set(indexes)):
            msg = "operator lifecycle events must be unique and ordered from started"
            raise ValueError(msg)
        completed = self.events[-1].state == "completed"
        if completed != (self.exit_status is not None and self.outcome != "running"):
            msg = "only completed lifecycle records may carry a final exit status"
            raise ValueError(msg)
        if self.outcome == "succeeded" and indexes != list(range(len(_LIFECYCLE_STATES))):
            msg = "successful lifecycle records require every approved boundary"
            raise ValueError(msg)
        return self


class OperatorLifecycleRecorder:
    """Atomically persist only safe operator-control state."""

    def __init__(
        self,
        storage: PrivateExperimentStorage,
        *,
        profile: str,
        case_id: str,
        clock: Callable[[], datetime] | None = None,
        operator_run_id: str | None = None,
    ) -> None:
        if profile != APPROVED_DEVELOPMENT_PROFILE:
            msg = "unsupported development profile"
            raise ValueError(msg)
        self.storage = storage
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.relative_path = f"operator_runs/{operator_run_id or f'operator_{uuid4().hex}'}.json"
        self.record = OperatorLifecycleRecord(
            operator_run_id=Path(self.relative_path).stem,
            profile=profile,
            case_id=case_id,
            events=(OperatorLifecycleEvent(state="started", timestamp=self.clock()),),
        )
        self.storage.write_json(self.relative_path, self.record)

    def transition(self, state: LifecycleState, *, exit_status: int | None = None) -> None:
        outcome: Literal["running", "succeeded", "failed"] = "running"
        if state == "completed":
            if exit_status is None:
                msg = "completed lifecycle transition requires an exit status"
                raise ValueError(msg)
            outcome = "succeeded" if exit_status == 0 else "failed"
        elif exit_status is not None:
            msg = "exit status is valid only for the completed lifecycle transition"
            raise ValueError(msg)
        self.record = OperatorLifecycleRecord(
            operator_run_id=self.record.operator_run_id,
            profile=self.record.profile,
            case_id=self.record.case_id,
            events=(*self.record.events, OperatorLifecycleEvent(state=state, timestamp=self.clock())),
            exit_status=exit_status,
            outcome=outcome,
        )
        self.storage.write_json(self.relative_path, self.record)


@dataclass(frozen=True)
class DevelopmentRunResult:
    operator_run_id: str
    candidate: BlindCandidate


class DevelopmentRunError(RuntimeError):
    """Safe operator-facing failure for the bounded development command."""


def approved_development_model_config(profile: str) -> InvocationModelConfig:
    if profile != APPROVED_DEVELOPMENT_PROFILE:
        msg = "unsupported development profile"
        raise ValueError(msg)
    return InvocationModelConfig(
        provider="openai",
        model_identifier="gpt-5.6-sol",
        reasoning="medium",
        temperature=0.2,
        seed=7,
        max_output_tokens=2_000,
        timeout_seconds=30,
        provider_internal_retries=0,
    )


def approved_development_runtime(profile: str) -> RuntimeConfiguration:
    model_config = approved_development_model_config(profile)
    bc_limits = ExecutionLimits(
        max_model_calls=7,
        max_substantive_revisions=2,
        max_total_tokens=20_000,
        max_total_latency_ms=60_000,
        max_cost=Decimal(5),
        currency="USD",
    )
    return RuntimeConfiguration(
        primary_generator=model_config,
        evaluator=model_config,
        condition_a=ExecutionLimits(
            max_model_calls=2,
            max_substantive_revisions=0,
            max_total_tokens=20_000,
            max_total_latency_ms=60_000,
            max_cost=Decimal(5),
            currency="USD",
        ),
        condition_b=bc_limits,
        condition_c=bc_limits,
    )


def select_development_case(case_id: str, cases: tuple[CaseBrief, ...] | None = None) -> CaseBrief:
    available = load_development_cases() if cases is None else cases
    matches = [case for case in available if case.case_id == case_id]
    if len(matches) != 1:
        msg = "requested case is not an existing eligible development fixture"
        raise ValueError(msg)
    case = matches[0]
    if case.dataset_class is not DatasetClass.DEVELOPMENT or set(case.contamination_labels) != _REQUIRED_LABELS:
        msg = "development runner rejects holdout or improperly classified fixtures"
        raise ValueError(msg)
    return case


def preflight_development_run(repo_root: Path, runtime: RuntimeConfiguration, case: CaseBrief) -> None:
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        msg = "OPENAI_API_KEY is not present or is empty"
        raise DevelopmentRunError(msg)
    assert_external_tracing_disabled()
    git = shutil.which("git")
    if git is None:
        msg = "git executable is unavailable"
        raise DevelopmentRunError(msg)
    branch = subprocess.run(  # noqa: S603
        [git, "branch", "--show-current"], cwd=repo_root, check=True, capture_output=True, text=True
    ).stdout.strip()
    if branch != _EXPECTED_BRANCH:
        msg = "repository branch does not match the approved development branch"
        raise DevelopmentRunError(msg)
    tracked_status = subprocess.run(  # noqa: S603
        [git, "status", "--short", "--untracked-files=all"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if tracked_status:
        msg = "working tree is not clean"
        raise DevelopmentRunError(msg)
    select_development_case(case.case_id, (case,))
    if runtime.primary_generator != runtime.evaluator:
        msg = "primary and evaluator model configurations differ"
        raise DevelopmentRunError(msg)
    expected = approved_development_model_config(APPROVED_DEVELOPMENT_PROFILE)
    if runtime.primary_generator != expected:
        msg = "runtime does not match the approved development profile"
        raise DevelopmentRunError(msg)
    parameters = build_langchain_parameters(expected)
    if parameters != _EXPECTED_LANGCHAIN_PARAMETERS:
        msg = "requested LangChain parameters do not match the approved development profile"
        raise DevelopmentRunError(msg)
    normalized = preflight_langchain_model_config(expected)
    if normalized != _EXPECTED_EFFECTIVE_ADAPTER_CONFIGURATION:
        msg = "effective adapter configuration does not match the approved normalized behavior"
        raise DevelopmentRunError(msg)


def execute_approved_development_run(
    repo_root: Path,
    *,
    profile: str,
    case_id: str,
) -> DevelopmentRunResult:
    """Execute only the approved development profile through existing harness components."""
    storage = PrivateExperimentStorage(repo_root)
    lifecycle = OperatorLifecycleRecorder(storage, profile=profile, case_id=case_id)
    try:
        case = select_development_case(case_id)
        runtime = approved_development_runtime(profile)
        preflight_development_run(repo_root, runtime, case)
        lifecycle.transition("preflight_passed")
        invoker = LangChainModelInvoker()
        workflows = DevelopmentWorkflows(
            condition_a=ConditionAWorkflow(invoker=invoker, runtime_config=runtime),
            condition_b=ConditionBWorkflow(invoker=invoker, runtime_config=runtime),
            condition_c=ConditionCWorkflow(invoker=invoker, runtime_config=runtime),
        )
        submissions = run_development_case_with_persistence(
            case,
            workflows,
            storage,
            review_mode="single_case_development",
            boundary_callback=lifecycle.transition,
        )
        lifecycle.transition("execution_persisted")
        if any(submission.trace.failures for submission in submissions):
            msg = "development execution completed with a bounded failure; execution evidence was persisted"
            raise DevelopmentRunError(msg)
        bundle = build_single_case_development_blind_bundle(
            case,
            submissions,
            secret_seed=secrets.token_bytes(32),
            reveal_custodian=RevealCustodian(),
        )
        persist_development_blind_bundle(
            storage,
            case,
            bundle,
            review_mode="single_case_development",
        )
        lifecycle.transition("blind_bundle_persisted")
        lifecycle.transition("completed", exit_status=0)
        candidate = min(bundle.candidates, key=lambda item: item.position)
        return DevelopmentRunResult(operator_run_id=lifecycle.record.operator_run_id, candidate=candidate)
    except Exception:
        if lifecycle.record.events[-1].state != "completed":
            lifecycle.transition("completed", exit_status=2)
        raise


def record_superseded_process_termination_diagnostic(
    storage: PrivateExperimentStorage,
    *,
    timestamp: datetime,
) -> Path:
    """Add an immutable correction while preserving the superseded diagnostic."""
    if timestamp.tzinfo is None:
        msg = "correction timestamp must be timezone-aware"
        raise ValueError(msg)
    return storage.write_json_once(
        "deviations/case_dev_tools_before_redesign_corrected_rehearsal_process_termination_superseded.json",
        {
            "schema_version": "phase-1f-a-diagnostic-correction-v1",
            "case_id": "case_dev_tools_before_redesign",
            "superseded_artifact": (
                "failures/case_dev_tools_before_redesign_corrected_rehearsal_process_termination.json"
            ),
            "correction": "subprocess_continued_and_persisted_corrected_run",
            "recorded_at": timestamp.isoformat(),
        },
    )
