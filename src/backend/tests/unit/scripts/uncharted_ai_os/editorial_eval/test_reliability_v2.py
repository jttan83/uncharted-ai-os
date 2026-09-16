from __future__ import annotations

import json
import shutil
import subprocess
from datetime import timedelta
from typing import TYPE_CHECKING

import httpx
import pytest
from openai import APIConnectionError, APITimeoutError

from scripts.uncharted_ai_os.editorial_eval.cli import build_parser
from scripts.uncharted_ai_os.editorial_eval.contracts import (
    CreatorStopDecision,
    DatasetClass,
    NormalizedSubmission,
    ResourceUsage,
)
from scripts.uncharted_ai_os.editorial_eval.development_runner import (
    APPROVED_DEVELOPMENT_PROFILE,
    APPROVED_DEVELOPMENT_PROFILE_V2,
    APPROVED_DEVELOPMENT_PROFILES,
    DevelopmentRunError,
    OperatorLifecycleRecorder,
    approved_development_model_config,
    approved_development_runtime,
    preflight_development_run,
    record_superseded_process_termination_diagnostic,
    select_development_case,
)
from scripts.uncharted_ai_os.editorial_eval.invokers import (
    LangChainModelInvoker,
    ModelMessage,
    ScriptedModelInvoker,
    ScriptedStep,
    build_langchain_parameters,
)
from scripts.uncharted_ai_os.editorial_eval.storage import PrivateExperimentStorage
from scripts.uncharted_ai_os.editorial_eval.workflows import ConditionBWorkflow, CreatorResult

from .conftest import FIXED_TIME

if TYPE_CHECKING:
    from pathlib import Path

_EXPECTED_EFFECTIVE_CONFIGURATION_V1 = {
    "model": "gpt-5.6-sol",
    "reasoning_effort": "medium",
    "temperature": None,
    "seed": 7,
    "max_completion_tokens": 2_000,
    "timeout": 30,
    "max_retries": 0,
}
_EXPECTED_EFFECTIVE_CONFIGURATION_V2 = {
    "model": "gpt-5.6-sol",
    "reasoning_effort": "medium",
    "temperature": None,
    "seed": 7,
    "max_completion_tokens": 8_000,
    "timeout": 120,
    "max_retries": 0,
}


def _initialize_repo(path: Path) -> PrivateExperimentStorage:
    subprocess.run(["git", "init", "--quiet", str(path)], check=True)  # noqa: S603, S607
    (path / ".gitignore").write_text("var/\n", encoding="utf-8")
    return PrivateExperimentStorage(path)


def _initialize_clean_branch_repo(path: Path) -> PrivateExperimentStorage:
    git = shutil.which("git")
    assert git is not None
    subprocess.run(  # noqa: S603
        [git, "init", "--quiet", "--initial-branch=uncharted-v0.1", str(path)],
        check=True,
    )
    (path / ".gitignore").write_text("var/\n", encoding="utf-8")
    subprocess.run([git, "-C", str(path), "add", ".gitignore"], check=True)  # noqa: S603
    subprocess.run(  # noqa: S603
        [
            git,
            "-C",
            str(path),
            "-c",
            "user.name=Offline Test",
            "-c",
            "user.email=offline@example.invalid",
            "commit",
            "--quiet",
            "-m",
            "baseline",
        ],
        check=True,
    )
    return PrivateExperimentStorage(path)


def _configure_safe_preflight(monkeypatch, normalized=None) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-value")
    for name in ("LANGCHAIN_TRACING", "LANGCHAIN_TRACING_V2", "LANGSMITH_TRACING", "LANGSMITH_TRACING_V2"):
        monkeypatch.delenv(name, raising=False)
    effective = _EXPECTED_EFFECTIVE_CONFIGURATION_V1 if normalized is None else normalized
    monkeypatch.setattr(
        "scripts.uncharted_ai_os.editorial_eval.development_runner.preflight_langchain_model_config",
        lambda _config: effective,
    )


def test_precalibration_v1_profile_is_preserved_exactly() -> None:
    config = approved_development_model_config(APPROVED_DEVELOPMENT_PROFILE)
    assert config.model_dump(mode="python") == {
        "provider": "openai",
        "model_identifier": "gpt-5.6-sol",
        "reasoning": "medium",
        "temperature": 0.2,
        "seed": 7,
        "max_output_tokens": 2_000,
        "timeout_seconds": 30,
        "provider_internal_retries": 0,
    }
    assert build_langchain_parameters(config) == {
        "temperature": 0.2,
        "max_tokens": 2_000,
        "timeout": 30,
        "max_retries": 0,
        "seed": 7,
        "reasoning_effort": "medium",
    }
    runtime = approved_development_runtime(APPROVED_DEVELOPMENT_PROFILE)
    assert runtime.primary_generator == runtime.evaluator == config
    assert all(
        build_langchain_parameters(model_config)["max_retries"] == 0
        for model_config in (runtime.primary_generator, runtime.evaluator)
    )


def test_capacity_calibrated_v2_profile_and_guardrails_are_exact() -> None:
    config = approved_development_model_config(APPROVED_DEVELOPMENT_PROFILE_V2)
    assert config.model_dump(mode="python") == {
        "provider": "openai",
        "model_identifier": "gpt-5.6-sol",
        "reasoning": "medium",
        "temperature": 0.2,
        "seed": 7,
        "max_output_tokens": 8_000,
        "timeout_seconds": 120,
        "provider_internal_retries": 0,
    }
    assert build_langchain_parameters(config) == {
        "temperature": 0.2,
        "max_tokens": 8_000,
        "timeout": 120,
        "max_retries": 0,
        "seed": 7,
        "reasoning_effort": "medium",
    }
    runtime = approved_development_runtime(APPROVED_DEVELOPMENT_PROFILE_V2)
    assert runtime.primary_generator == runtime.evaluator == config
    assert runtime.condition_b == runtime.condition_c
    assert runtime.condition_b.model_dump(mode="python") == {
        "max_model_calls": 7,
        "max_substantive_revisions": 2,
        "max_total_tokens": 80_000,
        "max_total_latency_ms": 600_000,
        "max_cost": 5,
        "currency": "USD",
    }
    assert runtime.condition_a.model_dump(mode="python") == {
        "max_model_calls": 2,
        "max_substantive_revisions": 0,
        "max_total_tokens": 20_000,
        "max_total_latency_ms": 300_000,
        "max_cost": 5,
        "currency": "USD",
    }


def test_v2_guardrails_preserve_actual_measured_resource_use(case_brief) -> None:
    invoker = ScriptedModelInvoker(
        [
            ScriptedStep(
                parsed=CreatorResult(
                    stop_decision=CreatorStopDecision.HUMAN_ESCALATION,
                    rationale="Offline guardrail test.",
                    next_action="Stop after the initial generator.",
                ),
                usage=ResourceUsage(
                    input_tokens=3_165,
                    output_tokens=4_214,
                    reasoning_tokens=1_624,
                    cached_input_tokens=3_162,
                ),
                latency_ms=78_191,
            )
        ]
    )
    submission = ConditionBWorkflow(
        invoker=invoker,
        runtime_config=approved_development_runtime(APPROVED_DEVELOPMENT_PROFILE_V2),
        run_id_factory=lambda: "run_v2_guardrail_test",
    ).run(brief=case_brief)
    assert len(invoker.records) == 1
    assert submission.trace.actual_usage.model_dump(mode="python") == {
        "input_tokens": 3_165,
        "output_tokens": 4_214,
        "cached_input_tokens": 3_162,
        "reasoning_tokens": 1_624,
        "tool_calls": None,
        "monetary_cost": None,
        "currency": None,
    }
    assert submission.trace.calls[0].latency_ms == 78_191
    assert submission.trace.max_total_tokens == 80_000
    assert submission.trace.max_total_latency_ms == 600_000


def test_preflight_rejects_nonignored_untracked_file(tmp_path: Path, case_brief, monkeypatch) -> None:
    _initialize_clean_branch_repo(tmp_path)
    (tmp_path / "untracked_experiment_override.py").write_text("unsafe = True\n", encoding="utf-8")
    _configure_safe_preflight(monkeypatch)
    with pytest.raises(DevelopmentRunError, match="working tree is not clean"):
        preflight_development_run(
            tmp_path,
            approved_development_runtime(APPROVED_DEVELOPMENT_PROFILE),
            case_brief,
        )


def test_preflight_allows_ignored_private_experiment_artifact(tmp_path: Path, case_brief, monkeypatch) -> None:
    storage = _initialize_clean_branch_repo(tmp_path)
    storage.write_json("operator_runs/ignored-private-artifact.json", {"state": "offline-test"})
    _configure_safe_preflight(monkeypatch)
    preflight_development_run(
        tmp_path,
        approved_development_runtime(APPROVED_DEVELOPMENT_PROFILE),
        case_brief,
    )


@pytest.mark.parametrize("empty_value", ["", "   "])
def test_preflight_rejects_empty_api_key(tmp_path: Path, case_brief, monkeypatch, empty_value) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", empty_value)
    with pytest.raises(DevelopmentRunError, match="not present or is empty"):
        preflight_development_run(
            tmp_path,
            approved_development_runtime(APPROVED_DEVELOPMENT_PROFILE),
            case_brief,
        )


@pytest.mark.parametrize(
    ("field", "drifted_value"),
    [
        ("model", "different-model"),
        ("reasoning_effort", "low"),
        ("temperature", 0.2),
        ("seed", 8),
        ("max_completion_tokens", 1_999),
        ("timeout", 31),
        ("max_retries", 1),
    ],
)
def test_preflight_rejects_effective_adapter_configuration_drift(
    tmp_path: Path,
    case_brief,
    monkeypatch,
    field,
    drifted_value,
) -> None:
    _initialize_clean_branch_repo(tmp_path)
    normalized = {**_EXPECTED_EFFECTIVE_CONFIGURATION_V1, field: drifted_value}
    _configure_safe_preflight(monkeypatch, normalized)
    with pytest.raises(DevelopmentRunError, match="effective adapter configuration"):
        preflight_development_run(
            tmp_path,
            approved_development_runtime(APPROVED_DEVELOPMENT_PROFILE),
            case_brief,
        )


def test_v2_preflight_checks_effective_adapter_normalization(tmp_path: Path, case_brief, monkeypatch) -> None:
    _initialize_clean_branch_repo(tmp_path)
    _configure_safe_preflight(monkeypatch, _EXPECTED_EFFECTIVE_CONFIGURATION_V2)
    preflight_development_run(
        tmp_path,
        approved_development_runtime(APPROVED_DEVELOPMENT_PROFILE_V2),
        case_brief,
        profile=APPROVED_DEVELOPMENT_PROFILE_V2,
    )


def test_v2_preflight_rejects_effective_adapter_drift(tmp_path: Path, case_brief, monkeypatch) -> None:
    _initialize_clean_branch_repo(tmp_path)
    drifted = {**_EXPECTED_EFFECTIVE_CONFIGURATION_V2, "timeout": 121}
    _configure_safe_preflight(monkeypatch, drifted)
    with pytest.raises(DevelopmentRunError, match="effective adapter configuration"):
        preflight_development_run(
            tmp_path,
            approved_development_runtime(APPROVED_DEVELOPMENT_PROFILE_V2),
            case_brief,
            profile=APPROVED_DEVELOPMENT_PROFILE_V2,
        )


def test_cli_accepts_only_explicitly_approved_profiles() -> None:
    parser = build_parser()
    for profile in APPROVED_DEVELOPMENT_PROFILES:
        args = parser.parse_args(
            ["run-development", "--profile", profile, "--case", "case_dev_tools_before_redesign"]
        )
        assert args.profile == profile
    with pytest.raises(SystemExit):
        parser.parse_args(
            ["run-development", "--profile", "phase1f-a-dev-v3", "--case", "case_dev_tools_before_redesign"]
        )


def test_cli_rejects_arbitrary_frozen_setting_override() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "run-development",
                "--profile",
                APPROVED_DEVELOPMENT_PROFILE,
                "--case",
                "case_dev_tools_before_redesign",
                "--model",
                "different-model",
            ]
        )


def test_development_selection_rejects_holdout(case_brief) -> None:
    payload = case_brief.model_dump(mode="python")
    payload["dataset_class"] = DatasetClass.HOLDOUT
    payload["contamination_labels"] = ()
    holdout = type(case_brief).model_validate(payload)
    with pytest.raises(ValueError, match="rejects holdout"):
        select_development_case(holdout.case_id, (holdout,))


@pytest.mark.parametrize(
    ("exception", "failure_type"),
    [
        (APITimeoutError(httpx.Request("POST", "https://example.invalid")), "infrastructure_timeout"),
        (
            APIConnectionError(request=httpx.Request("POST", "https://example.invalid")),
            "infrastructure_connection_error",
        ),
    ],
)
def test_openai_transport_failures_map_to_generic_retryable_semantics(
    monkeypatch, model_config, exception, failure_type
) -> None:
    class FakeStructuredModel:
        def invoke(self, _messages, *, config):
            assert config == {"callbacks": []}
            raise exception

    class FakeChatModel:
        def with_structured_output(self, _output_type, *, include_raw):
            assert include_raw is True
            return FakeStructuredModel()

    captured = {}

    def fake_init_chat_model(**kwargs):
        captured.update(kwargs)
        return FakeChatModel()

    monkeypatch.setattr("langchain.chat_models.init_chat_model", fake_init_chat_model)
    response = LangChainModelInvoker().invoke(
        (ModelMessage(role="user", content="safe offline test"),),
        NormalizedSubmission,
        model_config.model_copy(update={"provider": "openai"}),
    )
    assert captured["max_retries"] == 0
    assert response.failure is not None
    assert response.failure.failure_type == failure_type
    assert response.failure.retryable is True


def test_lifecycle_is_durable_safe_and_distinguishes_incomplete_from_completed(tmp_path: Path) -> None:
    storage = _initialize_repo(tmp_path)
    timestamps = iter(FIXED_TIME + timedelta(seconds=index) for index in range(4))
    recorder = OperatorLifecycleRecorder(
        storage,
        profile=APPROVED_DEVELOPMENT_PROFILE,
        case_id="case_dev_tools_before_redesign",
        clock=lambda: next(timestamps),
        operator_run_id="operator_0123456789abcdef0123456789abcdef",
    )
    recorder.transition("preflight_passed")
    incomplete = storage.read_json(recorder.relative_path)
    assert incomplete["outcome"] == "running"
    assert incomplete["exit_status"] is None
    assert incomplete["events"][-1]["state"] == "preflight_passed"
    serialized = json.dumps(incomplete).casefold()
    for forbidden in (
        "api_key",
        "authorization",
        "prompt",
        "spoken_script",
        "raw_provider",
        "hidden_reasoning",
        "reveal_mapping",
    ):
        assert forbidden not in serialized
    recorder.transition("completed", exit_status=2)
    completed = storage.read_json(recorder.relative_path)
    assert completed["outcome"] == "failed"
    assert completed["exit_status"] == 2
    assert completed["events"][-1]["state"] == "completed"


def test_successful_lifecycle_persists_every_approved_boundary(tmp_path: Path) -> None:
    storage = _initialize_repo(tmp_path)
    timestamps = iter(FIXED_TIME + timedelta(seconds=index) for index in range(11))
    recorder = OperatorLifecycleRecorder(
        storage,
        profile=APPROVED_DEVELOPMENT_PROFILE,
        case_id="case_dev_tools_before_redesign",
        clock=lambda: next(timestamps),
        operator_run_id="operator_fedcba9876543210fedcba9876543210",
    )
    for state in (
        "preflight_passed",
        "condition_a_started",
        "condition_a_finished",
        "condition_b_started",
        "condition_b_finished",
        "condition_c_started",
        "condition_c_finished",
        "execution_persisted",
        "blind_bundle_persisted",
    ):
        recorder.transition(state)
    recorder.transition("completed", exit_status=0)
    persisted = storage.read_json(recorder.relative_path)
    assert persisted["outcome"] == "succeeded"
    assert [event["state"] for event in persisted["events"]] == [
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


def test_superseded_diagnostic_correction_is_immutable(tmp_path: Path) -> None:
    storage = _initialize_repo(tmp_path)
    original = storage.write_json(
        "failures/case_dev_tools_before_redesign_corrected_rehearsal_process_termination.json",
        {"historical": True},
    )
    original_bytes = original.read_bytes()
    correction = record_superseded_process_termination_diagnostic(storage, timestamp=FIXED_TIME)
    assert original.read_bytes() == original_bytes
    payload = storage.read_json(correction.relative_to(storage.root))
    assert payload["correction"] == "subprocess_continued_and_persisted_corrected_run"
