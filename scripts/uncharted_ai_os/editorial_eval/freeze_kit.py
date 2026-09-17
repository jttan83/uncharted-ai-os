"""Frozen Phase 1F-A manifest, holdout intake, and immutable execution records."""

from __future__ import annotations

import hashlib
import secrets
import shutil
import subprocess
from datetime import datetime  # noqa: TC003
from decimal import Decimal  # noqa: TC003
from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING, Literal, TypeVar

from pydantic import Field, TypeAdapter, model_validator

from .blinding import condition_execution_order, opaque_identifier, seed_commitment
from .canonical import assert_byte_identical_case_briefs, canonical_digest
from .contracts import (
    BlindCandidate,
    BlindReviewBundle,
    CaseBrief,
    Condition,
    ConditionSubmission,
    DatasetClass,
    FailureInfo,
    Identifier,
    PreUnblindingRecord,
    Stage1Assessment,
    Stage2Comparison,
    StrictModel,
)
from .development_runner import (
    APPROVED_DEVELOPMENT_PROFILE_V2,
    approved_development_model_config,
    approved_development_runtime,
    approved_effective_adapter_configuration,
    preflight_approved_provider_runtime,
)
from .manifest import (
    ConditionBudget,
    ContaminationRecord,
    ExperimentBudgets,
    FreezeManifest,
    FreezeReceipt,
    FrozenDataGovernance,
    FrozenEvidencePolicy,
    FrozenModelConfig,
    ManifestState,
    OperationalControls,
    RandomizationCommitment,
    create_freeze_receipt,
    protocol_file_digest,
)
from .prompt_assets import PromptName, all_prompt_digests, prompt_digest
from .rehearsal import DevelopmentWorkflows, derive_ecological_input
from .workflows import ConditionAWorkflow, ConditionBWorkflow, ConditionCWorkflow

if TYPE_CHECKING:
    from .invokers import ModelInvoker
    from .storage import PrivateExperimentStorage

FREEZE_PROFILE = APPROVED_DEVELOPMENT_PROFILE_V2
DEVELOPMENT_CONTAMINATION_REGISTER = (
    ContaminationRecord(
        case_id="case_dev_tools_before_redesign",
        topic="tools before redesign",
        labels=("DEVELOPMENT ONLY", "CONTAMINATED", "NOT HOLDOUT"),
    ),
    ContaminationRecord(
        case_id="case_dev_agreement_alignment",
        topic="agreement and alignment",
        labels=("DEVELOPMENT ONLY", "CONTAMINATED", "NOT HOLDOUT"),
    ),
    ContaminationRecord(
        case_id="case_dev_oversized_workshops",
        topic="oversized workshops",
        labels=("DEVELOPMENT ONLY", "CONTAMINATED", "NOT HOLDOUT"),
    ),
)
EVIDENCE_POLICY = FrozenEvidencePolicy()
_EXPERIMENT_VERSION = "phase_1f_a_holdout_v1"
_MANIFEST_VERSION = "phase_1f_a_freeze_v1"
_CONFIG_PROFILE = "phase1f-a-dev-v2"
_CONDITION_COUNT = 3
StrictModelT = TypeVar("StrictModelT", bound=StrictModel)


class FreezeSeedRecord(StrictModel):
    schema_version: Literal["phase-1f-a-freeze-seed-v1"] = "phase-1f-a-freeze-seed-v1"
    experiment_id: str
    freeze_digest: str
    seed_hex: str = Field(pattern=r"^[0-9a-f]{64}$")


class HoldoutBatch(StrictModel):
    schema_version: Literal["phase-1f-a-holdout-batch-v1"] = "phase-1f-a-holdout-batch-v1"
    experiment_id: str
    freeze_digest: str
    batch_id: str = Field(pattern=r"^batch_[0-9a-f]{16}$")
    created_at: datetime
    cases: tuple[CaseBrief, ...] = Field(min_length=6, max_length=10)
    case_digests: dict[str, str]

    @model_validator(mode="after")
    def validate_batch(self) -> HoldoutBatch:
        if self.created_at.tzinfo is None:
            msg = "holdout intake timestamp must be timezone-aware"
            raise ValueError(msg)
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            msg = "holdout case IDs must be unique"
            raise ValueError(msg)
        if any(case.dataset_class is not DatasetClass.HOLDOUT for case in self.cases):
            msg = "holdout intake accepts holdout-labelled cases only"
            raise ValueError(msg)
        contaminated_ids = {record.case_id for record in DEVELOPMENT_CONTAMINATION_REGISTER}
        if contaminated_ids.intersection(case_ids):
            msg = "holdout intake rejects a registered contaminated development case"
            raise ValueError(msg)
        expected_digests = {case.case_id: canonical_digest(case) for case in self.cases}
        if self.case_digests != expected_digests:
            msg = "holdout case digest register does not match the supplied batch"
            raise ValueError(msg)
        return self


class HoldoutExecutionRecord(StrictModel):
    schema_version: Literal["phase-1f-a-holdout-execution-v1"] = "phase-1f-a-holdout-execution-v1"
    experiment_id: str
    freeze_digest: str
    case_id: str
    execution_id: str = Field(pattern=r"^execution_[0-9a-f]{32}$")
    run_kind: Literal["main", "repeatability"]
    original_execution_id: str | None = None
    execution_order: tuple[Condition, ...]
    status: Literal["succeeded", "failed"]
    submissions: tuple[ConditionSubmission, ...]
    failure: FailureInfo | None = None
    recorded_at: datetime

    @model_validator(mode="after")
    def validate_execution(self) -> HoldoutExecutionRecord:
        if self.recorded_at.tzinfo is None:
            msg = "execution record timestamp must be timezone-aware"
            raise ValueError(msg)
        if len(self.execution_order) != _CONDITION_COUNT or set(self.execution_order) != set(Condition):
            msg = "holdout execution order must contain A, B, and C exactly once"
            raise ValueError(msg)
        if any(item.case_id != self.case_id for item in self.submissions):
            msg = "every submission must belong to the execution case"
            raise ValueError(msg)
        if self.status == "succeeded":
            complete = len(self.submissions) == _CONDITION_COUNT and {
                item.condition for item in self.submissions
            } == set(Condition)
            if not complete:
                msg = "successful holdout execution requires one A, B, and C submission"
                raise ValueError(msg)
            if self.failure is not None:
                msg = "successful holdout execution cannot carry an execution failure"
                raise ValueError(msg)
        elif self.failure is None:
            msg = "failed holdout execution requires an auditable failure"
            raise ValueError(msg)
        if self.run_kind == "repeatability" and self.original_execution_id is None:
            msg = "repeatability execution requires its original main execution ID"
            raise ValueError(msg)
        if self.run_kind == "main" and self.original_execution_id is not None:
            msg = "main execution cannot reference an original execution"
            raise ValueError(msg)
        return self


class MainExecutionClaim(StrictModel):
    """Immutable reservation preventing a second substantive MAIN execution."""

    schema_version: Literal["phase-1f-a-main-execution-claim-v1"] = "phase-1f-a-main-execution-claim-v1"
    experiment_id: str
    freeze_digest: str
    case_id: str
    execution_id: str = Field(pattern=r"^execution_[0-9a-f]{32}$")
    run_kind: Literal["main"] = "main"
    reserved_at: datetime

    @model_validator(mode="after")
    def validate_timestamp(self) -> MainExecutionClaim:
        if self.reserved_at.tzinfo is None:
            msg = "main execution reservation timestamp must be timezone-aware"
            raise ValueError(msg)
        return self


class HoldoutBlindBundleRecord(StrictModel):
    schema_version: Literal["phase-1f-a-holdout-blind-bundle-v1"] = "phase-1f-a-holdout-blind-bundle-v1"
    experiment_id: str
    freeze_digest: str
    bundle_id: str
    execution_ids: tuple[str, ...]
    case_review_order: tuple[str, ...]
    bundle: BlindReviewBundle

    @model_validator(mode="after")
    def validate_bundle_id(self) -> HoldoutBlindBundleRecord:
        if self.bundle_id != self.bundle.bundle_id:
            msg = "blind bundle record identifier does not match its bundle"
            raise ValueError(msg)
        candidate_cases = {candidate.case_id for candidate in self.bundle.candidates}
        if len(self.case_review_order) != len(candidate_cases) or set(self.case_review_order) != candidate_cases:
            msg = "case review order must cover every blind-bundle case exactly once"
            raise ValueError(msg)
        return self


class HoldoutBatchRunResult(StrictModel):
    experiment_id: str
    completed_case_count: int = Field(ge=6, le=10)
    bundle_id: str
    candidate_count: int = Field(ge=18, le=30)


def create_and_persist_freeze(
    repo_root: Path,
    storage: PrivateExperimentStorage,
    *,
    experiment_id: str,
    experiment_operator: str,
    mapping_custodian: str,
    max_pilot_cost: Decimal,
    max_human_review_minutes_per_case: int,
    retention_days: int,
    timestamp: datetime,
    secret_seed: bytes | None = None,
) -> FreezeReceipt:
    """Create the one frozen manifest and its separate seed-custody record."""
    commit = _clean_head_commit(repo_root)
    seed = secret_seed or secrets.token_bytes(32)
    runtime = approved_development_runtime(FREEZE_PROFILE)
    invocation = approved_development_model_config(FREEZE_PROFILE)
    effective = approved_effective_adapter_configuration(FREEZE_PROFILE)
    model = FrozenModelConfig(
        provider=invocation.provider,
        model_identifier=invocation.model_identifier,
        reasoning=invocation.reasoning,
        temperature=effective["temperature"],
        requested_temperature=invocation.temperature,
        seed_supported=invocation.seed is not None,
        seed=invocation.seed,
        timeout_seconds=invocation.timeout_seconds,
        max_output_tokens_per_call=invocation.max_output_tokens,
        provider_internal_retries=invocation.provider_internal_retries,
        immutable_model_snapshot=False,
        limitations=("Provider model identifier is not an immutable snapshot.",),
    )
    budgets = ExperimentBudgets(
        condition_a=_condition_budget(runtime.condition_a),
        condition_b=_condition_budget(runtime.condition_b),
        condition_c=_condition_budget(runtime.condition_c),
        bc_token_tolerance_percent=0,
        max_pilot_cost=max_pilot_cost,
        currency=runtime.condition_a.currency,
        max_human_review_minutes_per_case=max_human_review_minutes_per_case,
    )
    contamination_digest = canonical_digest(_contamination_payload())
    evidence_policy_digest = canonical_digest(EVIDENCE_POLICY)
    manifest = FreezeManifest(
        experiment_id=experiment_id,
        experiment_version=_EXPERIMENT_VERSION,
        protocol_version="phase-1f-a-v1",
        protocol_digest=protocol_file_digest(),
        protocol_commit=commit,
        code_commit=commit,
        manifest_version=_MANIFEST_VERSION,
        created_at=timestamp,
        prompt_hashes=all_prompt_digests(),
        config_hashes=_configuration_digests(runtime),
        generator_model=model,
        evaluator_model=model,
        budgets=budgets,
        randomization=RandomizationCommitment(
            seed_commitment=seed_commitment(seed),
            seed_custody_rule="Private local seed and mapping files; explicit reveal only after locked review.",
            mapping_custodian=mapping_custodian,
        ),
        data_governance=FrozenDataGovernance(
            experiment_operator=experiment_operator,
            raw_case_access=(experiment_operator,),
            provider_data_use="Frozen provider API configuration; no live research or external tracing.",
            retention_days=retention_days,
            deletion_rule="Delete private holdout records after the governed experiment retention period.",
            client_or_third_party_data_permitted=False,
        ),
        operational_controls=OperationalControls(
            development_case_ids=tuple(record.case_id for record in DEVELOPMENT_CONTAMINATION_REGISTER),
            contamination_register=DEVELOPMENT_CONTAMINATION_REGISTER,
            contaminated_topic_register_digest=contamination_digest,
            configuration_profile=_CONFIG_PROFILE,
            treatment_source_digests=_treatment_source_digests(repo_root),
            evidence_policy=EVIDENCE_POLICY,
            evidence_snapshot_digest=evidence_policy_digest,
            permitted_tools=(),
            conditional_fact_check_rule_digest=evidence_policy_digest,
            decision_rule_digest=protocol_file_digest(),
        ),
    ).freeze(timestamp=timestamp)
    receipt = create_freeze_receipt(manifest)
    freeze_digest = manifest.freeze_digest
    if freeze_digest is None:  # pragma: no cover - frozen contract guarantees this.
        msg = "frozen manifest did not produce a digest"
        raise RuntimeError(msg)
    base = _experiment_base(experiment_id)
    storage.write_json_once(
        f"{base}/custody/randomization_seed.json",
        FreezeSeedRecord(experiment_id=experiment_id, freeze_digest=freeze_digest, seed_hex=seed.hex()),
    )
    storage.write_json_once(f"{base}/freeze/manifest.json", manifest)
    storage.write_json_once(f"{base}/freeze/receipt.json", receipt)
    return receipt


def load_frozen_manifest(
    storage: PrivateExperimentStorage,
    experiment_id: str,
    *,
    repo_root: Path | None = None,
) -> FreezeManifest:
    manifest = storage.read_model(
        f"{_experiment_base(experiment_id)}/freeze/manifest.json",
        FreezeManifest,
    )
    if manifest.state is not ManifestState.FROZEN:
        msg = "holdout operation requires a frozen manifest"
        raise ValueError(msg)
    if repo_root is not None and manifest.code_commit != _clean_head_commit(repo_root):
        msg = "checked-out harness does not match the frozen source commit"
        raise ValueError(msg)
    return manifest


def intake_holdout_batch(
    storage: PrivateExperimentStorage,
    *,
    experiment_id: str,
    source_path: Path,
    timestamp: datetime,
    repo_root: Path | None = None,
) -> HoldoutBatch:
    """Validate the complete local batch before one immutable private write."""
    manifest = load_frozen_manifest(storage, experiment_id, repo_root=repo_root)
    cases = TypeAdapter(tuple[CaseBrief, ...]).validate_json(source_path.read_bytes())
    case_digests = {case.case_id: canonical_digest(case) for case in cases}
    batch_token = hashlib.sha256("\x1f".join(sorted(case_digests.values())).encode()).hexdigest()[:16]
    batch = HoldoutBatch(
        experiment_id=experiment_id,
        freeze_digest=manifest.freeze_digest,
        batch_id=f"batch_{batch_token}",
        created_at=timestamp,
        cases=cases,
        case_digests=case_digests,
    )
    storage.write_json_once(f"{_experiment_base(experiment_id)}/holdout/batch.json", batch)
    return batch


def load_holdout_batch(storage: PrivateExperimentStorage, experiment_id: str) -> HoldoutBatch:
    return storage.read_model(f"{_experiment_base(experiment_id)}/holdout/batch.json", HoldoutBatch)


def build_holdout_workflows(
    invoker: ModelInvoker,
    manifest: FreezeManifest,
) -> DevelopmentWorkflows:
    """Bind the unchanged A/B/C workflows to frozen holdout trace identifiers."""
    runtime = approved_development_runtime(FREEZE_PROFILE)
    if manifest.operational_controls is None or manifest.operational_controls.configuration_profile != FREEZE_PROFILE:
        msg = "manifest does not bind the approved Phase 1F-A V2 configuration"
        raise ValueError(msg)
    kwargs = {
        "invoker": invoker,
        "runtime_config": runtime,
        "experiment_version": manifest.experiment_version,
        "manifest_version": manifest.manifest_version,
    }
    return DevelopmentWorkflows(
        condition_a=ConditionAWorkflow(**kwargs),
        condition_b=ConditionBWorkflow(**kwargs),
        condition_c=ConditionCWorkflow(**kwargs),
    )


def execute_holdout_case(
    storage: PrivateExperimentStorage,
    *,
    repo_root: Path,
    experiment_id: str,
    execution_id: str,
    case_id: str,
    workflows: DevelopmentWorkflows,
    run_kind: Literal["main", "repeatability"],
    timestamp: datetime,
    original_execution_id: str | None = None,
) -> HoldoutExecutionRecord:
    """Run unchanged condition workflows in the frozen seeded order and persist once."""
    manifest = load_frozen_manifest(storage, experiment_id, repo_root=repo_root)
    batch = load_holdout_batch(storage, experiment_id)
    case = _select_holdout_case(batch, case_id)
    expected_runtime = approved_development_runtime(FREEZE_PROFILE)
    if any(
        workflow.runtime_config != expected_runtime
        for workflow in (workflows.condition_a, workflows.condition_b, workflows.condition_c)
    ):
        msg = "holdout workflows do not match the frozen Phase 1F-A V2 runtime"
        raise ValueError(msg)
    seed = _load_freeze_seed(storage, manifest)
    order = condition_execution_order(case_id if run_kind == "main" else execution_id, seed)
    assert_byte_identical_case_briefs(case, case, batch.case_digests[case_id])
    original_run_ids: dict[Condition, str] = {}
    if run_kind == "repeatability":
        if original_execution_id is None:  # pragma: no cover - record contract also enforces this.
            msg = "repeatability execution requires an original execution ID"
            raise ValueError(msg)
        original = storage.read_model(
            f"{_experiment_base(experiment_id)}/executions/{case_id}/{original_execution_id}.json",
            HoldoutExecutionRecord,
        )
        if (
            original.experiment_id != experiment_id
            or original.freeze_digest != manifest.freeze_digest
            or original.case_id != case_id
            or original.run_kind != "main"
            or original.status != "succeeded"
        ):
            msg = "repeatability execution must reference a successful main execution"
            raise ValueError(msg)
        original_run_ids = {submission.condition: submission.run_id for submission in original.submissions}
    submissions: list[ConditionSubmission] = []
    try:
        for condition in order:
            workflow = {
                Condition.A: workflows.condition_a,
                Condition.B: workflows.condition_b,
                Condition.C: workflows.condition_c,
            }[condition]
            if condition is Condition.A:
                submission = workflow.run(
                    case_id=case.case_id,
                    ecological_input=derive_ecological_input(case),
                    original_run_id=original_run_ids.get(condition),
                )
            else:
                submission = workflow.run(
                    brief=case,
                    committed_brief_digest=batch.case_digests[case_id],
                    original_run_id=original_run_ids.get(condition),
                )
            submissions.append(submission)
        record = HoldoutExecutionRecord(
            experiment_id=experiment_id,
            freeze_digest=manifest.freeze_digest,
            case_id=case_id,
            execution_id=execution_id,
            run_kind=run_kind,
            original_execution_id=original_execution_id,
            execution_order=order,
            status="succeeded",
            submissions=tuple(submissions),
            recorded_at=timestamp,
        )
    except Exception as exc:
        record = HoldoutExecutionRecord(
            experiment_id=experiment_id,
            freeze_digest=manifest.freeze_digest,
            case_id=case_id,
            execution_id=execution_id,
            run_kind=run_kind,
            original_execution_id=original_execution_id,
            execution_order=order,
            status="failed",
            submissions=tuple(submissions),
            failure=FailureInfo(
                failure_type="holdout_execution_failure",
                safe_message=f"Holdout execution stopped with {type(exc).__name__}.",
                retryable=False,
            ),
            recorded_at=timestamp,
        )
        persist_holdout_execution_record(storage, record)
        raise
    persist_holdout_execution_record(storage, record)
    return record


def persist_holdout_execution_record(
    storage: PrivateExperimentStorage,
    record: HoldoutExecutionRecord,
) -> Path:
    """Persist a validated execution without allowing an execution-ID overwrite."""
    return storage.write_json_once(
        f"{_experiment_base(record.experiment_id)}/executions/{record.case_id}/{record.execution_id}.json",
        record,
    )


def run_frozen_main_holdout_batch(
    repo_root: Path,
    storage: PrivateExperimentStorage,
    *,
    experiment_id: str,
    timestamp: datetime,
) -> HoldoutBatchRunResult:
    """Run or safely resume the one frozen MAIN execution for every holdout case."""
    manifest = load_frozen_manifest(storage, experiment_id, repo_root=repo_root)
    batch = load_holdout_batch(storage, experiment_id)
    if (
        manifest.experiment_id != experiment_id
        or batch.experiment_id != experiment_id
        or batch.freeze_digest != manifest.freeze_digest
    ):
        msg = "frozen holdout batch does not match the frozen experiment"
        raise ValueError(msg)
    seed = _load_freeze_seed(storage, manifest)
    planned = tuple(
        (case.case_id, _main_execution_id(seed, experiment_id, case.case_id)) for case in batch.cases
    )
    completed: dict[str, HoldoutExecutionRecord] = {}
    pending: list[tuple[str, str]] = []
    for case_id, execution_id in planned:
        claim = _read_optional_model(storage, _main_claim_path(experiment_id, case_id), MainExecutionClaim)
        record = _read_optional_model(
            storage,
            _execution_path(experiment_id, case_id, execution_id),
            HoldoutExecutionRecord,
        )
        if record is None:
            if claim is not None:
                msg = "reserved MAIN execution has no valid terminal record; automatic rerun is forbidden"
                raise RuntimeError(msg)
            pending.append((case_id, execution_id))
            continue
        _validate_main_execution_record(record, manifest, batch, seed, execution_id)
        _validate_main_execution_claim(claim, record)
        completed[case_id] = record

    if pending:
        runtime = approved_development_runtime(FREEZE_PROFILE)
        preflight_approved_provider_runtime(runtime, profile=FREEZE_PROFILE)
        from .invokers import LangChainModelInvoker

        workflows = build_holdout_workflows(LangChainModelInvoker(), manifest)
        for case_id, execution_id in pending:
            claim = MainExecutionClaim(
                experiment_id=experiment_id,
                freeze_digest=manifest.freeze_digest,
                case_id=case_id,
                execution_id=execution_id,
                reserved_at=timestamp,
            )
            storage.write_json_once(_main_claim_path(experiment_id, case_id), claim)
            record = execute_holdout_case(
                storage,
                repo_root=repo_root,
                experiment_id=experiment_id,
                execution_id=execution_id,
                case_id=case_id,
                workflows=workflows,
                run_kind="main",
                timestamp=timestamp,
            )
            _validate_main_execution_record(record, manifest, batch, seed, execution_id)
            completed[case_id] = record

    executions = tuple(completed[case_id] for case_id, _execution_id in planned)
    bundle_record = _load_or_create_main_blind_bundle(
        storage,
        repo_root=repo_root,
        manifest=manifest,
        batch=batch,
        seed=seed,
        executions=executions,
    )
    return HoldoutBatchRunResult(
        experiment_id=experiment_id,
        completed_case_count=len(executions),
        bundle_id=bundle_record.bundle_id,
        candidate_count=len(bundle_record.bundle.candidates),
    )


def _load_or_create_main_blind_bundle(
    storage: PrivateExperimentStorage,
    *,
    repo_root: Path,
    manifest: FreezeManifest,
    batch: HoldoutBatch,
    seed: bytes,
    executions: tuple[HoldoutExecutionRecord, ...],
) -> HoldoutBlindBundleRecord:
    bundle_id = opaque_identifier(
        seed,
        namespace="bundle",
        components=(f"{manifest.experiment_id}_main",),
    )
    existing = _read_optional_model(
        storage,
        f"{_experiment_base(batch.experiment_id)}/presentations/{bundle_id}.json",
        HoldoutBlindBundleRecord,
    )
    expected_execution_ids = tuple(record.execution_id for record in executions)
    if existing is not None:
        candidate_cases = [candidate.case_id for candidate in existing.bundle.candidates]
        if (
            existing.experiment_id != batch.experiment_id
            or existing.freeze_digest != manifest.freeze_digest
            or existing.bundle_id != bundle_id
            or existing.execution_ids != expected_execution_ids
            or len(candidate_cases) != len(batch.cases) * _CONDITION_COUNT
            or set(candidate_cases) != set(batch.case_digests)
        ):
            msg = "persisted main blind bundle is incompatible with the frozen MAIN executions"
            raise ValueError(msg)
        from .custody import validate_bundle_custody

        validate_bundle_custody(storage, existing)
        return existing
    from .custody import create_main_blind_bundle

    return create_main_blind_bundle(
        storage,
        repo_root=repo_root,
        experiment_id=batch.experiment_id,
        executions=executions,
    )


def _validate_main_execution_claim(
    claim: MainExecutionClaim | None,
    record: HoldoutExecutionRecord,
) -> None:
    if claim is None or (
        claim.experiment_id != record.experiment_id
        or claim.freeze_digest != record.freeze_digest
        or claim.case_id != record.case_id
        or claim.execution_id != record.execution_id
    ):
        msg = "successful MAIN execution is missing its matching immutable reservation"
        raise ValueError(msg)


def _validate_main_execution_record(
    record: HoldoutExecutionRecord,
    manifest: FreezeManifest,
    batch: HoldoutBatch,
    seed: bytes,
    execution_id: str,
) -> None:
    runtime = approved_development_runtime(FREEZE_PROFILE)
    model_config = approved_development_model_config(FREEZE_PROFILE)
    if (
        record.experiment_id != batch.experiment_id
        or record.freeze_digest != manifest.freeze_digest
        or record.case_id not in batch.case_digests
        or record.execution_id != execution_id
        or record.run_kind != "main"
        or record.original_execution_id is not None
        or record.status != "succeeded"
        or record.execution_order != condition_execution_order(record.case_id, seed)
    ):
        msg = "persisted MAIN execution is not a valid frozen successful record"
        raise ValueError(msg)
    expected_config_digest = canonical_digest(model_config)
    for submission in record.submissions:
        limits = {
            Condition.A: runtime.condition_a,
            Condition.B: runtime.condition_b,
            Condition.C: runtime.condition_c,
        }[submission.condition]
        trace = submission.trace
        expected_brief_digest = None if submission.condition is Condition.A else batch.case_digests[record.case_id]
        if (
            trace.experiment_version != manifest.experiment_version
            or trace.manifest_version != manifest.manifest_version
            or trace.case_id != record.case_id
            or trace.condition is not submission.condition
            or trace.case_brief_digest != expected_brief_digest
            or trace.max_model_calls != limits.max_model_calls
            or trace.max_substantive_revisions != limits.max_substantive_revisions
            or trace.max_total_tokens != limits.max_total_tokens
            or trace.max_total_latency_ms != limits.max_total_latency_ms
            or trace.max_cost != limits.max_cost
            or trace.budget_currency != limits.currency
            or not trace.calls
        ):
            msg = "persisted MAIN execution trace does not match the frozen runtime"
            raise ValueError(msg)
        if any(
            call.provider != model_config.provider
            or call.model_identifier != model_config.model_identifier
            or call.reasoning != model_config.reasoning
            or call.model_config_digest != expected_config_digest
            or call.provider_internal_retries != model_config.provider_internal_retries
            for call in trace.calls
        ):
            msg = "persisted MAIN execution used a non-frozen provider configuration"
            raise ValueError(msg)


def _read_optional_model(
    storage: PrivateExperimentStorage,
    relative_path: str,
    model_type: type[StrictModelT],
) -> StrictModelT | None:
    try:
        return storage.read_model(relative_path, model_type)
    except FileNotFoundError:
        return None


def _main_execution_id(seed: bytes, experiment_id: str, case_id: str) -> str:
    return opaque_identifier(seed, namespace="execution", components=(experiment_id, case_id, "main"))


def _execution_path(experiment_id: str, case_id: str, execution_id: str) -> str:
    return f"{_experiment_base(experiment_id)}/executions/{case_id}/{execution_id}.json"


def _main_claim_path(experiment_id: str, case_id: str) -> str:
    return f"{_experiment_base(experiment_id)}/main_execution_claims/{case_id}.json"


def _configuration_digests(runtime: object) -> dict[str, str]:
    return {
        "case_brief_template": canonical_digest(CaseBrief.model_json_schema()),
        "case_eligibility_selection_rules": canonical_digest(
            {
                "dataset_class": "holdout",
                "count": [6, 10],
                "contamination_register": canonical_digest(_contamination_payload()),
            }
        ),
        "blind_envelope": canonical_digest(BlindCandidate.model_json_schema()),
        "data_handling_rules": canonical_digest({"private": True, "write_once": True, "gitignored": True}),
        "decision_mapping": protocol_file_digest(),
        "ecological_a_derivation_rule": canonical_digest({"function": "derive_ecological_input", "version": 1}),
        "go_simplify_stop_rules": protocol_file_digest(),
        "resource_parity_method": canonical_digest(runtime),
        "retry_failure_stopping_rules": canonical_digest({"infrastructure_retries": 1, "substantive_revisions": 2}),
        "review_form": canonical_digest(
            {
                "stage_1": Stage1Assessment.model_json_schema(),
                "stage_2": Stage2Comparison.model_json_schema(),
                "pre_unblinding": PreUnblindingRecord.model_json_schema(),
            }
        ),
        "review_session_policy": canonical_digest({"stage_order": ["stage_1", "stage_2", "pre_unblinding", "reveal"]}),
        "validation_rules": canonical_digest(
            {"mode": "fail_closed", "evidence_policy": EVIDENCE_POLICY.model_dump(mode="json")}
        ),
    }


def _treatment_source_digests(repo_root: Path) -> dict[str, str]:
    workflow_digest = _file_digest(repo_root / "scripts/uncharted_ai_os/editorial_eval/workflows.py")
    return {
        "A": canonical_digest({"prompt": prompt_digest(PromptName.CONDITION_A), "workflow": workflow_digest}),
        "B": canonical_digest(
            {
                "prompts": [prompt_digest(PromptName.CONDITION_B), prompt_digest(PromptName.CONDITION_B_SELF_REVIEW)],
                "workflow": workflow_digest,
            }
        ),
        "C": canonical_digest(
            {
                "prompts": [
                    prompt_digest(PromptName.CONDITION_C_CREATOR),
                    prompt_digest(PromptName.CONDITION_C_EVALUATOR),
                    prompt_digest(PromptName.CONDITION_C_REVISION),
                ],
                "workflow": workflow_digest,
            }
        ),
    }


def _condition_budget(limits: object) -> ConditionBudget:
    return ConditionBudget.model_validate(limits.model_dump(mode="python"))


def _contamination_payload() -> list[dict[str, object]]:
    return [record.model_dump(mode="json") for record in DEVELOPMENT_CONTAMINATION_REGISTER]


def _clean_head_commit(repo_root: Path) -> str:
    git = shutil.which("git")
    if git is None:
        msg = "git executable is unavailable"
        raise ValueError(msg)
    unstaged = subprocess.run(  # noqa: S603
        [git, "diff", "--quiet"], cwd=repo_root, check=False
    ).returncode
    staged = subprocess.run(  # noqa: S603
        [git, "diff", "--cached", "--quiet"], cwd=repo_root, check=False
    ).returncode
    if unstaged or staged:
        msg = "freeze operations require a clean tracked worktree"
        raise ValueError(msg)
    return subprocess.run(  # noqa: S603
        [git, "rev-parse", "HEAD"], cwd=repo_root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _load_freeze_seed(storage: PrivateExperimentStorage, manifest: FreezeManifest) -> bytes:
    experiment_id = manifest.experiment_id
    if experiment_id is None:
        msg = "frozen manifest is missing experiment_id"
        raise ValueError(msg)
    record = storage.read_model(
        f"{_experiment_base(experiment_id)}/custody/randomization_seed.json",
        FreezeSeedRecord,
    )
    if record.freeze_digest != manifest.freeze_digest:
        msg = "randomization seed record does not match the frozen manifest"
        raise ValueError(msg)
    seed = bytes.fromhex(record.seed_hex)
    if manifest.randomization is None or seed_commitment(seed) != manifest.randomization.seed_commitment:
        msg = "randomization seed does not match the frozen commitment"
        raise ValueError(msg)
    return seed


def _select_holdout_case(batch: HoldoutBatch, case_id: str) -> CaseBrief:
    matches = [case for case in batch.cases if case.case_id == case_id]
    if len(matches) != 1:
        msg = "requested case is not in the frozen holdout batch"
        raise ValueError(msg)
    return matches[0]


def _experiment_base(experiment_id: str) -> str:
    validated = TypeAdapter(Identifier).validate_python(experiment_id)
    return f"experiments/{validated}"


def _file_digest(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"
