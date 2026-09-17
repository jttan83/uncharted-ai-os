from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from scripts.uncharted_ai_os.editorial_eval import freeze_kit
from scripts.uncharted_ai_os.editorial_eval.blinding import condition_execution_order
from scripts.uncharted_ai_os.editorial_eval.canonical import canonical_digest, canonical_json_bytes
from scripts.uncharted_ai_os.editorial_eval.cli import build_parser
from scripts.uncharted_ai_os.editorial_eval.contracts import (
    CandidateUseDecision,
    Condition,
    DatasetClass,
    IdentityGuess,
    PreUnblindingRecord,
    RewriteBurden,
    Stage1Assessment,
    Stage2Comparison,
)
from scripts.uncharted_ai_os.editorial_eval.custody import create_main_blind_bundle, reveal_mapping
from scripts.uncharted_ai_os.editorial_eval.development_runner import (
    APPROVED_DEVELOPMENT_PROFILE_V2,
    approved_development_model_config,
    approved_development_runtime,
)
from scripts.uncharted_ai_os.editorial_eval.freeze_kit import (
    HoldoutExecutionRecord,
    MainExecutionClaim,
    create_and_persist_freeze,
    intake_holdout_batch,
    load_frozen_manifest,
    persist_holdout_execution_record,
    run_frozen_main_holdout_batch,
)
from scripts.uncharted_ai_os.editorial_eval.review import (
    lock_pre_unblinding_record,
    lock_stage_1_assessment,
    lock_stage_2_comparison,
    next_stage_1_candidate,
    next_stage_2_bundle,
)
from scripts.uncharted_ai_os.editorial_eval.storage import PrivateExperimentStorage, StorageRecordExistsError

from .conftest import FIXED_TIME, make_case_brief, make_model_call, make_submission

EXPERIMENT_ID = "phase_1f_a_holdout_test"
SOURCE_COMMIT = "f" * 40
SECRET = bytes(range(32))


def _storage(tmp_path: Path) -> PrivateExperimentStorage:
    return PrivateExperimentStorage(tmp_path, verify_ignored=False)


def _create_freeze(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[PrivateExperimentStorage, object]:
    monkeypatch.setattr(freeze_kit, "_clean_head_commit", lambda _repo_root: SOURCE_COMMIT)
    storage = _storage(tmp_path)
    receipt = create_and_persist_freeze(
        Path.cwd(),
        storage,
        experiment_id=EXPERIMENT_ID,
        experiment_operator="Jentz",
        mapping_custodian="Jentz after locked review",
        max_pilot_cost=Decimal(200),
        max_human_review_minutes_per_case=60,
        retention_days=30,
        timestamp=FIXED_TIME,
        secret_seed=SECRET,
    )
    return storage, receipt


def _holdout_cases(count: int = 6):
    return tuple(
        make_case_brief(f"case_holdout_{index:02d}").model_copy(
            update={"dataset_class": DatasetClass.HOLDOUT, "contamination_labels": ()}
        )
        for index in range(count)
    )


def _intake(tmp_path: Path, storage: PrivateExperimentStorage):
    source = tmp_path / "synthetic_holdout_batch.json"
    source.write_bytes(canonical_json_bytes([case.model_dump(mode="json") for case in _holdout_cases()]))
    return intake_holdout_batch(
        storage,
        experiment_id=EXPERIMENT_ID,
        source_path=source,
        timestamp=FIXED_TIME,
    )


def _execution(manifest, case_id: str, index: int) -> HoldoutExecutionRecord:
    submissions = tuple(
        make_submission(condition, case_id, f"holdout_{index}_{condition.value.lower()}").model_copy(
            update={
                "trace": make_submission(
                    condition, case_id, f"holdout_{index}_{condition.value.lower()}"
                ).trace.model_copy(
                    update={
                        "experiment_version": manifest.experiment_version,
                        "manifest_version": manifest.manifest_version,
                    }
                )
            }
        )
        for condition in Condition
    )
    return HoldoutExecutionRecord(
        experiment_id=EXPERIMENT_ID,
        freeze_digest=manifest.freeze_digest,
        case_id=case_id,
        execution_id=f"execution_{index:032x}",
        run_kind="main",
        execution_order=tuple(Condition),
        status="succeeded",
        submissions=submissions,
        recorded_at=FIXED_TIME,
    )


def _frozen_execution(manifest, batch, case_id: str, execution_id: str) -> HoldoutExecutionRecord:
    runtime = approved_development_runtime(APPROVED_DEVELOPMENT_PROFILE_V2)
    model = approved_development_model_config(APPROVED_DEVELOPMENT_PROFILE_V2)
    submissions = []
    roles = {
        Condition.A: "a_generator",
        Condition.B: "b_generator",
        Condition.C: "c_creator",
    }
    for condition in Condition:
        submission = make_submission(condition, case_id, f"frozen_{case_id}_{condition.value.lower()}")
        brief_digest = None if condition is Condition.A else batch.case_digests[case_id]
        base_calls = submission.trace.calls or (
            make_model_call(submission.run_id, f"{case_id}_{condition.value.lower()}", roles[condition]),
        )
        calls = tuple(
            call.model_copy(
                update={
                    "provider": model.provider,
                    "model_identifier": model.model_identifier,
                    "reasoning": model.reasoning,
                    "model_config_digest": canonical_digest(model),
                }
            )
            for call in base_calls
        )
        limits = {
            Condition.A: runtime.condition_a,
            Condition.B: runtime.condition_b,
            Condition.C: runtime.condition_c,
        }[condition]
        submissions.append(
            submission.model_copy(
                update={
                    "case_brief_digest": brief_digest,
                    "trace": submission.trace.model_copy(
                        update={
                            "experiment_version": manifest.experiment_version,
                            "manifest_version": manifest.manifest_version,
                            "case_brief_digest": brief_digest,
                            "calls": calls,
                            "max_substantive_revisions": limits.max_substantive_revisions,
                            "max_model_calls": limits.max_model_calls,
                            "max_total_tokens": limits.max_total_tokens,
                            "max_total_latency_ms": limits.max_total_latency_ms,
                            "max_cost": limits.max_cost,
                            "budget_currency": limits.currency,
                        }
                    )
                }
            )
        )
    return HoldoutExecutionRecord(
        experiment_id=EXPERIMENT_ID,
        freeze_digest=manifest.freeze_digest,
        case_id=case_id,
        execution_id=execution_id,
        run_kind="main",
        execution_order=condition_execution_order(case_id, SECRET),
        status="succeeded",
        submissions=tuple(submissions),
        recorded_at=FIXED_TIME,
    )


def test_freeze_manifest_binds_v2_policy_sources_and_sanitized_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage, receipt = _create_freeze(tmp_path, monkeypatch)
    manifest = load_frozen_manifest(storage, EXPERIMENT_ID)
    controls = manifest.operational_controls

    assert manifest.code_commit == SOURCE_COMMIT
    assert controls is not None
    assert controls.configuration_profile == "phase1f-a-dev-v2"
    assert controls.evidence_policy.live_research_permitted is False
    assert controls.evidence_policy.deterministic_validation == "fail_closed"
    assert manifest.generator_model is not None
    assert manifest.generator_model.model_identifier == "gpt-5.6-sol"
    assert manifest.generator_model.reasoning == "medium"
    assert manifest.generator_model.requested_temperature == 0.2
    assert manifest.generator_model.temperature is None
    assert manifest.generator_model.seed == 7
    assert manifest.generator_model.timeout_seconds == 120
    assert manifest.generator_model.max_output_tokens_per_call == 8_000
    assert manifest.generator_model.provider_internal_retries == 0
    assert set(controls.treatment_source_digests) == {"A", "B", "C"}
    assert {record.case_id for record in controls.contamination_register} == {
        "case_dev_tools_before_redesign",
        "case_dev_agreement_alignment",
        "case_dev_oversized_workshops",
    }
    assert receipt.freeze_digest == manifest.freeze_digest
    serialized_receipt = receipt.model_dump_json()
    assert "seed_hex" not in serialized_receipt
    assert "contamination_register" not in serialized_receipt
    assert '"mapping":' not in serialized_receipt


def test_holdout_intake_validates_whole_batch_writes_once_and_rejects_development(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage, _ = _create_freeze(tmp_path, monkeypatch)
    batch = _intake(tmp_path, storage)
    assert len(batch.cases) == 6
    with pytest.raises(StorageRecordExistsError):
        intake_holdout_batch(
            storage,
            experiment_id=EXPERIMENT_ID,
            source_path=tmp_path / "synthetic_holdout_batch.json",
            timestamp=FIXED_TIME,
        )

    contaminated_source = tmp_path / "synthetic_contaminated_batch.json"
    contaminated_source.write_bytes(
        canonical_json_bytes(
            [case.model_dump(mode="json") for case in (*_holdout_cases(5), make_case_brief())]
        )
    )
    other_storage = _storage(tmp_path / "other")
    create_and_persist_freeze(
        Path.cwd(),
        other_storage,
        experiment_id=EXPERIMENT_ID,
        experiment_operator="Jentz",
        mapping_custodian="Jentz after locked review",
        max_pilot_cost=Decimal(200),
        max_human_review_minutes_per_case=60,
        retention_days=30,
        timestamp=FIXED_TIME,
        secret_seed=SECRET,
    )
    with pytest.raises(ValueError, match="holdout-labelled"):
        intake_holdout_batch(
            other_storage,
            experiment_id=EXPERIMENT_ID,
            source_path=contaminated_source,
            timestamp=FIXED_TIME,
        )


def test_run_holdout_batch_reserves_once_and_resumes_without_provider_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage, _ = _create_freeze(tmp_path, monkeypatch)
    batch = _intake(tmp_path, storage)
    manifest = load_frozen_manifest(storage, EXPERIMENT_ID)
    preflights: list[str] = []
    executed: list[str] = []

    monkeypatch.setattr(
        freeze_kit,
        "preflight_approved_provider_runtime",
        lambda _runtime, *, profile: preflights.append(profile),
    )
    monkeypatch.setattr(freeze_kit, "build_holdout_workflows", lambda _invoker, _manifest: object())
    from scripts.uncharted_ai_os.editorial_eval import invokers

    monkeypatch.setattr(invokers, "LangChainModelInvoker", object)

    def fake_execute(storage_arg, **kwargs):
        claim = storage_arg.read_model(
            freeze_kit._main_claim_path(EXPERIMENT_ID, kwargs["case_id"]),
            MainExecutionClaim,
        )
        assert claim.execution_id == kwargs["execution_id"]
        executed.append(kwargs["case_id"])
        record = _frozen_execution(manifest, batch, kwargs["case_id"], kwargs["execution_id"])
        persist_holdout_execution_record(storage_arg, record)
        return record

    monkeypatch.setattr(freeze_kit, "execute_holdout_case", fake_execute)
    first = run_frozen_main_holdout_batch(
        Path.cwd(),
        storage,
        experiment_id=EXPERIMENT_ID,
        timestamp=FIXED_TIME,
    )
    assert first.completed_case_count == len(batch.cases)
    assert first.candidate_count == len(batch.cases) * len(Condition)
    assert executed == [case.case_id for case in batch.cases]
    assert preflights == [APPROVED_DEVELOPMENT_PROFILE_V2]

    def reject_provider_use(*_args, **_kwargs):
        pytest.fail("a completed MAIN batch resume must not initialize or call a provider")

    monkeypatch.setattr(freeze_kit, "preflight_approved_provider_runtime", reject_provider_use)
    monkeypatch.setattr(freeze_kit, "execute_holdout_case", reject_provider_use)
    resumed = run_frozen_main_holdout_batch(
        Path.cwd(),
        storage,
        experiment_id=EXPERIMENT_ID,
        timestamp=FIXED_TIME,
    )
    assert resumed == first


def test_run_holdout_batch_stops_on_reserved_incomplete_main_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage, _ = _create_freeze(tmp_path, monkeypatch)
    batch = _intake(tmp_path, storage)
    manifest = load_frozen_manifest(storage, EXPERIMENT_ID)
    case_id = batch.cases[0].case_id
    execution_id = freeze_kit._main_execution_id(SECRET, EXPERIMENT_ID, case_id)
    storage.write_json_once(
        freeze_kit._main_claim_path(EXPERIMENT_ID, case_id),
        MainExecutionClaim(
            experiment_id=EXPERIMENT_ID,
            freeze_digest=manifest.freeze_digest,
            case_id=case_id,
            execution_id=execution_id,
            reserved_at=FIXED_TIME,
        ),
    )
    monkeypatch.setattr(
        freeze_kit,
        "preflight_approved_provider_runtime",
        lambda *_args, **_kwargs: pytest.fail("ambiguous reservation must stop before provider preflight"),
    )
    with pytest.raises(RuntimeError, match="automatic rerun is forbidden"):
        run_frozen_main_holdout_batch(
            Path.cwd(),
            storage,
            experiment_id=EXPERIMENT_ID,
            timestamp=FIXED_TIME,
        )


def test_run_holdout_batch_stops_on_incompatible_existing_main_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage, _ = _create_freeze(tmp_path, monkeypatch)
    batch = _intake(tmp_path, storage)
    manifest = load_frozen_manifest(storage, EXPERIMENT_ID)
    case_id = batch.cases[0].case_id
    execution_id = freeze_kit._main_execution_id(SECRET, EXPERIMENT_ID, case_id)
    storage.write_json_once(
        freeze_kit._main_claim_path(EXPERIMENT_ID, case_id),
        MainExecutionClaim(
            experiment_id=EXPERIMENT_ID,
            freeze_digest=manifest.freeze_digest,
            case_id=case_id,
            execution_id=execution_id,
            reserved_at=FIXED_TIME,
        ),
    )
    record = _frozen_execution(manifest, batch, case_id, execution_id)
    submissions = list(record.submissions)
    submissions[0] = submissions[0].model_copy(
        update={
            "trace": submissions[0].trace.model_copy(
                update={"max_total_tokens": submissions[0].trace.max_total_tokens + 1}
            )
        }
    )
    persist_holdout_execution_record(storage, record.model_copy(update={"submissions": tuple(submissions)}))
    monkeypatch.setattr(
        freeze_kit,
        "preflight_approved_provider_runtime",
        lambda *_args, **_kwargs: pytest.fail("an incompatible record must stop before provider preflight"),
    )
    with pytest.raises(ValueError, match="frozen runtime"):
        run_frozen_main_holdout_batch(
            Path.cwd(),
            storage,
            experiment_id=EXPERIMENT_ID,
            timestamp=FIXED_TIME,
        )


def test_main_blind_bundle_resumes_only_with_identical_persisted_custody(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage, _ = _create_freeze(tmp_path, monkeypatch)
    batch = _intake(tmp_path, storage)
    manifest = load_frozen_manifest(storage, EXPERIMENT_ID)
    executions = tuple(_execution(manifest, case.case_id, index) for index, case in enumerate(batch.cases, start=1))
    for execution in executions:
        persist_holdout_execution_record(storage, execution)
    write_once = storage.write_json_once

    def interrupt_before_presentation(relative_path, value):
        if "/presentations/" in str(relative_path):
            msg = "synthetic interruption after custody persistence"
            raise RuntimeError(msg)
        return write_once(relative_path, value)

    monkeypatch.setattr(storage, "write_json_once", interrupt_before_presentation)
    with pytest.raises(RuntimeError, match="synthetic interruption"):
        create_main_blind_bundle(
            storage,
            repo_root=Path.cwd(),
            experiment_id=EXPERIMENT_ID,
            executions=executions,
        )
    monkeypatch.setattr(storage, "write_json_once", write_once)
    resumed = create_main_blind_bundle(
        storage,
        repo_root=Path.cwd(),
        experiment_id=EXPERIMENT_ID,
        executions=executions,
    )
    assert len(resumed.bundle.candidates) == len(batch.cases) * len(Condition)


def test_cli_exposes_one_frozen_holdout_batch_command() -> None:
    args = build_parser().parse_args(["run-holdout-batch", "--experiment-id", EXPERIMENT_ID])
    assert args.command == "run-holdout-batch"
    assert vars(args) == {"command": "run-holdout-batch", "experiment_id": EXPERIMENT_ID}


def test_execution_review_and_reveal_are_immutable_resumable_and_separated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage, _ = _create_freeze(tmp_path, monkeypatch)
    batch = _intake(tmp_path, storage)
    manifest = load_frozen_manifest(storage, EXPERIMENT_ID)
    executions = tuple(_execution(manifest, case.case_id, index) for index, case in enumerate(batch.cases, start=1))
    for execution in executions:
        persist_holdout_execution_record(storage, execution)
    with pytest.raises(StorageRecordExistsError):
        persist_holdout_execution_record(storage, executions[0])

    blind_record = create_main_blind_bundle(
        storage,
        repo_root=Path.cwd(),
        experiment_id=EXPERIMENT_ID,
        executions=executions,
    )
    presentation_json = canonical_json_bytes(blind_record).decode()
    assert '"condition"' not in presentation_json
    assert '"explanation"' not in presentation_json
    assert '"next_action"' not in presentation_json
    assert '"run_id"' not in presentation_json
    assert '"mapping"' not in presentation_json
    with pytest.raises(RuntimeError, match="Stage 1"):
        reveal_mapping(
            storage,
            repo_root=Path.cwd(),
            experiment_id=EXPERIMENT_ID,
            bundle_id=blind_record.bundle_id,
            timestamp=FIXED_TIME,
        )

    while (candidate := next_stage_1_candidate(
        storage,
        experiment_id=EXPERIMENT_ID,
        bundle_id=blind_record.bundle_id,
    )) is not None:
        lock_stage_1_assessment(
            storage,
            experiment_id=EXPERIMENT_ID,
            bundle_id=blind_record.bundle_id,
            assessment=Stage1Assessment(
                blind_candidate_id=candidate.blind_candidate_id,
                category_appropriate=True,
                use_decision=CandidateUseDecision.MINOR_EDIT,
                rewrite_burden=RewriteBurden.MINOR,
                main_strength="The editorial decision is clear.",
                main_weakness="A localized edit would improve precision.",
                confidence="medium",
                reasons=("Synthetic blind-review fixture.",),
                preference_basis="editorial",
                locked_at=FIXED_TIME,
            ),
        )

    with pytest.raises(RuntimeError, match="Stage 2"):
        reveal_mapping(
            storage,
            repo_root=Path.cwd(),
            experiment_id=EXPERIMENT_ID,
            bundle_id=blind_record.bundle_id,
            timestamp=FIXED_TIME,
        )

    while (case_bundle := next_stage_2_bundle(
        storage,
        experiment_id=EXPERIMENT_ID,
        bundle_id=blind_record.bundle_id,
    )) is not None:
        candidate_ids = tuple(candidate.blind_candidate_id for candidate in case_bundle.candidates)
        lock_stage_2_comparison(
            storage,
            experiment_id=EXPERIMENT_ID,
            bundle_id=blind_record.bundle_id,
            comparison=Stage2Comparison(
                case_id=case_bundle.candidates[0].case_id,
                acceptable_candidate_ids=candidate_ids,
                strongest_candidate_ids=(candidate_ids[0],),
                least_rewrite_candidate_ids=(candidate_ids[0],),
                strongest_point_of_view_candidate_ids=(candidate_ids[0],),
                strongest_attention_candidate_ids=(candidate_ids[0],),
                strongest_payoff_candidate_ids=(candidate_ids[0],),
                strongest_voice_candidate_ids=(candidate_ids[0],),
                better_non_script_candidate_ids=(),
                reasons=("Synthetic comparative judgment.",),
                editorial_personal_difference="No difference in this synthetic review.",
                uncertainty_and_change_evidence="No additional evidence specified.",
                confidence="medium",
                locked_at=FIXED_TIME,
            ),
        )

    with pytest.raises(RuntimeError, match="pre-unblinding"):
        reveal_mapping(
            storage,
            repo_root=Path.cwd(),
            experiment_id=EXPERIMENT_ID,
            bundle_id=blind_record.bundle_id,
            timestamp=FIXED_TIME,
        )

    guesses = tuple(
        IdentityGuess(
            blind_candidate_id=candidate.blind_candidate_id,
            guessed_condition=tuple(Condition)[candidate.position - 1],
            confidence="low",
        )
        for candidate in blind_record.bundle.candidates
    )
    lock_pre_unblinding_record(
        storage,
        experiment_id=EXPERIMENT_ID,
        bundle_id=blind_record.bundle_id,
        record=PreUnblindingRecord(
            bundle_id=blind_record.bundle_id,
            identity_guesses=guesses,
            evidence_summary="All synthetic blind judgments are locked.",
            comparative_decision_record="No pre-reveal treatment conclusion is asserted in this fixture.",
            locked_at=FIXED_TIME,
        ),
    )
    mapping = reveal_mapping(
        storage,
        repo_root=Path.cwd(),
        experiment_id=EXPERIMENT_ID,
        bundle_id=blind_record.bundle_id,
        timestamp=datetime(2026, 1, 2, 4, tzinfo=timezone.utc),
    )
    assert {entry.blind_candidate_id for entry in mapping.entries} == {
        candidate.blind_candidate_id for candidate in blind_record.bundle.candidates
    }
