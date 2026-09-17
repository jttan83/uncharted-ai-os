"""Draft/frozen manifest validation and sanitized reproducibility receipts."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime  # noqa: TC003
from decimal import Decimal  # noqa: TC003
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import Field, StringConstraints, model_validator

from .canonical import canonical_digest
from .contracts import Identifier, Sha256Digest, ShortText, StrictModel
from .prompt_assets import all_prompt_digests
from .security import assert_credential_free

FREEZE_MANIFEST_SCHEMA_VERSION = "phase-1f-a-freeze-manifest-v1"
FREEZE_RECEIPT_SCHEMA_VERSION = "phase-1f-a-freeze-receipt-v1"

CommitHash = Annotated[str, StringConstraints(pattern=r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")]
_PLACEHOLDER = re.compile(r"(?:^|\b)(?:TBD|TODO|PLACEHOLDER|FILL[ -]?ME|CHANGEME)(?:\b|$)", re.IGNORECASE)
_REQUIRED_PROMPTS = {
    "shared_editorial_context",
    "canonical_editorial_standard",
    "condition_a",
    "condition_b",
    "condition_b_self_review",
    "condition_c_creator",
    "condition_c_evaluator",
    "condition_c_revision",
}
_REQUIRED_CONFIGS = {
    "case_brief_template",
    "case_eligibility_selection_rules",
    "blind_envelope",
    "data_handling_rules",
    "decision_mapping",
    "ecological_a_derivation_rule",
    "go_simplify_stop_rules",
    "resource_parity_method",
    "retry_failure_stopping_rules",
    "review_form",
    "review_session_policy",
    "validation_rules",
}
_PROTOCOL_REVISION_LIMIT = 2
_CONDITION_A_CALL_CEILING = 2
_MINIMUM_BC_CALL_CEILING = 7


class ManifestState(str, Enum):
    DRAFT = "draft"
    FROZEN = "frozen"


class FrozenModelConfig(StrictModel):
    provider: ShortText
    model_identifier: ShortText
    reasoning: ShortText
    temperature: float | None = Field(default=None, ge=0, le=2)
    requested_temperature: float | None = Field(default=None, ge=0, le=2)
    seed_supported: bool
    seed: int | None = None
    timeout_seconds: int = Field(gt=0)
    max_output_tokens_per_call: int = Field(gt=0)
    provider_internal_retries: Literal[0] = 0
    immutable_model_snapshot: bool = False
    limitations: tuple[ShortText, ...] = ()

    @model_validator(mode="after")
    def reject_sensitive_configuration(self) -> FrozenModelConfig:
        assert_credential_free(self.model_dump(mode="python"))
        return self


class ConditionBudget(StrictModel):
    max_model_calls: int = Field(gt=0)
    max_infrastructure_retries_per_run: Literal[1] = 1
    max_substantive_revisions: int = Field(ge=0, le=2)
    max_total_tokens: int = Field(gt=0)
    max_total_latency_ms: int = Field(gt=0)
    max_cost: Decimal = Field(ge=0)
    currency: Literal["USD", "EUR", "GBP"]


class ExperimentBudgets(StrictModel):
    condition_a: ConditionBudget
    condition_b: ConditionBudget
    condition_c: ConditionBudget
    bc_token_tolerance_percent: Literal[0] = 0
    max_pilot_cost: Decimal = Field(gt=0)
    currency: Literal["USD", "EUR", "GBP"]
    max_human_review_minutes_per_case: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_comparability(self) -> ExperimentBudgets:
        if self.condition_a.max_substantive_revisions != 0:
            msg = "Condition A must use the frozen ecological workflow without substantive revisions"
            raise ValueError(msg)
        if self.condition_a.max_model_calls != _CONDITION_A_CALL_CEILING:
            msg = "Condition A permits one generation call and at most one infrastructure retry"
            raise ValueError(msg)
        if (
            self.condition_b.max_substantive_revisions != _PROTOCOL_REVISION_LIMIT
            or self.condition_c.max_substantive_revisions != _PROTOCOL_REVISION_LIMIT
        ):
            msg = "B and C must both use the protocol ceiling of two substantive revisions"
            raise ValueError(msg)
        if self.condition_b.currency != self.currency or self.condition_c.currency != self.currency:
            msg = "B/C and pilot budget currencies must match"
            raise ValueError(msg)
        if self.condition_a.currency != self.currency:
            msg = "A and pilot budget currencies must match"
            raise ValueError(msg)
        if self.condition_b.max_model_calls != self.condition_c.max_model_calls:
            msg = "B/C maximum model-call ceilings must match"
            raise ValueError(msg)
        if self.condition_b.max_model_calls < _MINIMUM_BC_CALL_CEILING:
            msg = "B/C call ceilings must permit six planned calls and one total infrastructure retry"
            raise ValueError(msg)
        if self.condition_b.max_total_latency_ms != self.condition_c.max_total_latency_ms:
            msg = "B/C maximum latency ceilings must match"
            raise ValueError(msg)
        if self.condition_b.max_cost != self.condition_c.max_cost:
            msg = "B/C maximum cost ceilings must match"
            raise ValueError(msg)
        if self.condition_b.max_total_tokens != self.condition_c.max_total_tokens:
            msg = "B/C token ceilings must match for this conservative pilot harness"
            raise ValueError(msg)
        return self


class RandomizationCommitment(StrictModel):
    identifier_algorithm: Literal["hmac-sha256"] = "hmac-sha256"
    commitment_algorithm: Literal["sha256"] = "sha256"
    seed_commitment: Sha256Digest
    position_algorithm: Literal["balanced-latin-v1"] = "balanced-latin-v1"
    execution_order_algorithm: Literal["hmac-rank-v1"] = "hmac-rank-v1"
    case_review_order_algorithm: Literal["hmac-rank-v1"] = "hmac-rank-v1"
    repeat_selection_algorithm: Literal["hmac-rank-v1"] = "hmac-rank-v1"
    seed_custody_rule: ShortText
    mapping_custodian: ShortText


class FrozenDataGovernance(StrictModel):
    experiment_operator: ShortText
    raw_case_access: tuple[ShortText, ...] = Field(min_length=1)
    provider_data_use: ShortText
    retention_days: int = Field(gt=0)
    deletion_rule: ShortText
    client_or_third_party_data_permitted: bool


class ContaminationRecord(StrictModel):
    case_id: Identifier
    topic: ShortText
    labels: tuple[Literal["DEVELOPMENT ONLY", "CONTAMINATED", "NOT HOLDOUT"], ...]

    @model_validator(mode="after")
    def validate_labels(self) -> ContaminationRecord:
        if set(self.labels) != {"DEVELOPMENT ONLY", "CONTAMINATED", "NOT HOLDOUT"}:
            msg = "every contamination record must carry all three exclusion labels"
            raise ValueError(msg)
        return self


class FrozenEvidencePolicy(StrictModel):
    live_research_permitted: Literal[False] = False
    authoritative_evidence: Literal["CaseBrief.evidence snapshot only"] = "CaseBrief.evidence snapshot only"
    evidence_reference_namespace: Literal["CaseBrief.evidence[].evidence_id"] = (
        "CaseBrief.evidence[].evidence_id"
    )
    unsupported_material_claim_rule: Literal[
        "qualify, remove, or return EVIDENCE REQUIRED"
    ] = "qualify, remove, or return EVIDENCE REQUIRED"
    deterministic_validation: Literal["fail_closed"] = "fail_closed"


class OperationalControls(StrictModel):
    """Concrete controls not safely reducible to prompt or budget fields."""

    development_case_ids: tuple[Identifier, ...] = Field(min_length=1)
    contamination_register: tuple[ContaminationRecord, ...] = Field(min_length=1)
    contaminated_topic_register_digest: Sha256Digest
    configuration_profile: Literal["phase1f-a-dev-v2"]
    treatment_source_digests: dict[str, Sha256Digest]
    evidence_policy: FrozenEvidencePolicy
    evidence_snapshot_digest: Sha256Digest
    permitted_tools: tuple[ShortText, ...]
    conditional_fact_check_rule_digest: Sha256Digest
    decision_rule_digest: Sha256Digest
    human_review_form_version: Literal["phase-1f-a-human-review-v1"] = "phase-1f-a-human-review-v1"
    reveal_custody_rule_version: Literal["phase-1f-a-reveal-custody-v1"] = "phase-1f-a-reveal-custody-v1"
    minimum_holdout_cases: Literal[6] = 6
    maximum_holdout_cases: Literal[10] = 10
    infrastructure_retry_limit: Literal[1] = 1

    @model_validator(mode="after")
    def validate_development_roster(self) -> OperationalControls:
        if len(self.development_case_ids) != len(set(self.development_case_ids)):
            msg = "development case roster must not contain duplicate IDs"
            raise ValueError(msg)
        registered_ids = tuple(record.case_id for record in self.contamination_register)
        if len(registered_ids) != len(set(registered_ids)) or set(registered_ids) != set(self.development_case_ids):
            msg = "contamination register must cover the development roster exactly once"
            raise ValueError(msg)
        if set(self.treatment_source_digests) != {"A", "B", "C"}:
            msg = "treatment source digests must bind exactly A, B, and C"
            raise ValueError(msg)
        return self


class FreezeManifest(StrictModel):
    """Compact operational snapshot; drafts may omit whole unresolved sections."""

    schema_version: Literal[FREEZE_MANIFEST_SCHEMA_VERSION] = FREEZE_MANIFEST_SCHEMA_VERSION
    state: ManifestState = ManifestState.DRAFT
    experiment_id: Identifier | None = None
    experiment_version: Identifier | None = None
    protocol_version: Literal["phase-1f-a-v1"] | None = None
    protocol_digest: Sha256Digest | None = None
    protocol_commit: CommitHash | None = None
    code_commit: CommitHash | None = None
    manifest_version: Identifier | None = None
    created_at: datetime
    freeze_timestamp: datetime | None = None
    prompt_hashes: dict[str, Sha256Digest] | None = None
    config_hashes: dict[str, Sha256Digest] | None = None
    generator_model: FrozenModelConfig | None = None
    evaluator_model: FrozenModelConfig | None = None
    budgets: ExperimentBudgets | None = None
    randomization: RandomizationCommitment | None = None
    data_governance: FrozenDataGovernance | None = None
    operational_controls: OperationalControls | None = None
    freeze_digest: Sha256Digest | None = None

    @model_validator(mode="after")
    def validate_state(self) -> FreezeManifest:
        _assert_model_configs_credential_free(self)
        if self.created_at.tzinfo is None or (self.freeze_timestamp and self.freeze_timestamp.tzinfo is None):
            msg = "manifest timestamps must be timezone-aware"
            raise ValueError(msg)
        if self.state is ManifestState.DRAFT:
            if self.freeze_timestamp is not None or self.freeze_digest is not None:
                msg = "draft manifests cannot carry freeze timestamp or digest"
                raise ValueError(msg)
            return self
        _validate_complete_frozen_manifest(self)
        expected = _manifest_digest(self)
        if self.freeze_digest != expected:
            msg = "freeze digest does not match the frozen manifest content"
            raise ValueError(msg)
        return self

    def freeze(self, *, timestamp: datetime) -> FreezeManifest:
        """Return a validated frozen copy; this does not freeze the live experiment."""
        if self.state is not ManifestState.DRAFT:
            msg = "only a draft manifest can be frozen"
            raise ValueError(msg)
        if timestamp.tzinfo is None:
            msg = "freeze timestamp must be timezone-aware"
            raise ValueError(msg)
        candidate = self.model_copy(
            update={"state": ManifestState.FROZEN, "freeze_timestamp": timestamp, "freeze_digest": None}
        )
        _validate_complete_frozen_manifest(candidate)
        digest = _manifest_digest(candidate)
        payload = candidate.model_dump(mode="python")
        payload["freeze_digest"] = digest
        return FreezeManifest.model_validate(payload)


class FreezeReceipt(StrictModel):
    """Public-safe receipt built by an explicit allowlist from a frozen manifest."""

    schema_version: Literal[FREEZE_RECEIPT_SCHEMA_VERSION] = FREEZE_RECEIPT_SCHEMA_VERSION
    experiment_version: Identifier
    protocol_version: Literal["phase-1f-a-v1"]
    protocol_digest: Sha256Digest
    protocol_commit: CommitHash
    code_commit: CommitHash
    prompt_hashes: dict[str, Sha256Digest]
    config_hashes: dict[str, Sha256Digest]
    generator_model_identifier: ShortText
    evaluator_model_identifier: ShortText
    manifest_schema_version: Literal[FREEZE_MANIFEST_SCHEMA_VERSION]
    budgets: ExperimentBudgets
    randomization_commitment: Sha256Digest
    configuration_profile: Literal["phase1f-a-dev-v2"]
    evidence_policy_digest: Sha256Digest
    decision_rule_digest: Sha256Digest
    human_review_form_version: Literal["phase-1f-a-human-review-v1"]
    reveal_custody_rule_version: Literal["phase-1f-a-reveal-custody-v1"]
    freeze_digest: Sha256Digest
    freeze_timestamp: datetime


def create_freeze_receipt(manifest: FreezeManifest) -> FreezeReceipt:
    """Create a sanitized receipt without seed, credentials, cases, or mapping."""
    _assert_model_configs_credential_free(manifest)
    if manifest.state is not ManifestState.FROZEN:
        msg = "freeze receipt requires a validated frozen manifest"
        raise ValueError(msg)
    experiment_version = _required(manifest.experiment_version, "experiment_version")
    protocol_version = _required(manifest.protocol_version, "protocol_version")
    protocol_digest = _required(manifest.protocol_digest, "protocol_digest")
    protocol_commit = _required(manifest.protocol_commit, "protocol_commit")
    code_commit = _required(manifest.code_commit, "code_commit")
    prompt_hashes = _required(manifest.prompt_hashes, "prompt_hashes")
    config_hashes = _required(manifest.config_hashes, "config_hashes")
    generator_model = _required(manifest.generator_model, "generator_model")
    evaluator_model = _required(manifest.evaluator_model, "evaluator_model")
    budgets = _required(manifest.budgets, "budgets")
    randomization = _required(manifest.randomization, "randomization")
    operational_controls = _required(manifest.operational_controls, "operational_controls")
    freeze_digest = _required(manifest.freeze_digest, "freeze_digest")
    freeze_timestamp = _required(manifest.freeze_timestamp, "freeze_timestamp")
    return FreezeReceipt(
        experiment_version=experiment_version,
        protocol_version=protocol_version,
        protocol_digest=protocol_digest,
        protocol_commit=protocol_commit,
        code_commit=code_commit,
        prompt_hashes=prompt_hashes,
        config_hashes=config_hashes,
        generator_model_identifier=generator_model.model_identifier,
        evaluator_model_identifier=evaluator_model.model_identifier,
        manifest_schema_version=manifest.schema_version,
        budgets=budgets,
        randomization_commitment=randomization.seed_commitment,
        configuration_profile=operational_controls.configuration_profile,
        evidence_policy_digest=canonical_digest(operational_controls.evidence_policy),
        decision_rule_digest=operational_controls.decision_rule_digest,
        human_review_form_version=operational_controls.human_review_form_version,
        reveal_custody_rule_version=operational_controls.reveal_custody_rule_version,
        freeze_digest=freeze_digest,
        freeze_timestamp=freeze_timestamp,
    )


def _validate_complete_frozen_manifest(manifest: FreezeManifest) -> None:
    _assert_model_configs_credential_free(manifest)
    required = (
        "experiment_id",
        "experiment_version",
        "protocol_version",
        "protocol_digest",
        "protocol_commit",
        "code_commit",
        "manifest_version",
        "freeze_timestamp",
        "prompt_hashes",
        "config_hashes",
        "generator_model",
        "evaluator_model",
        "budgets",
        "randomization",
        "data_governance",
        "operational_controls",
    )
    missing = [field for field in required if getattr(manifest, field) is None]
    if missing:
        msg = f"frozen manifest is incomplete: {', '.join(missing)}"
        raise ValueError(msg)
    prompt_hashes = _required(manifest.prompt_hashes, "prompt_hashes")
    config_hashes = _required(manifest.config_hashes, "config_hashes")
    if set(prompt_hashes) != _REQUIRED_PROMPTS:
        msg = "frozen manifest must hash every required prompt and no unknown prompt"
        raise ValueError(msg)
    if prompt_hashes != all_prompt_digests():
        msg = "frozen manifest prompt hashes do not match the checked-in prompt assets"
        raise ValueError(msg)
    if manifest.protocol_digest != protocol_file_digest():
        msg = "frozen manifest protocol hash does not match the canonical protocol document"
        raise ValueError(msg)
    if set(config_hashes) != _REQUIRED_CONFIGS:
        msg = "frozen manifest must hash every required configuration and no unknown configuration"
        raise ValueError(msg)
    _reject_placeholders(manifest.model_dump(mode="json", exclude={"freeze_digest"}))


def _reject_placeholders(value: Any, path: str = "manifest") -> None:
    if isinstance(value, str) and _PLACEHOLDER.search(value):
        msg = f"placeholder value is forbidden in frozen manifest at {path}"
        raise ValueError(msg)
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_placeholders(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_placeholders(item, f"{path}[{index}]")


def _assert_model_configs_credential_free(manifest: FreezeManifest) -> None:
    for model_config in (manifest.generator_model, manifest.evaluator_model):
        if model_config is not None:
            assert_credential_free(model_config.model_dump(mode="python"))


def _manifest_digest(manifest: FreezeManifest) -> str:
    return canonical_digest(manifest.model_dump(mode="json", exclude={"freeze_digest"}))


def _required(value: Any, field_name: str) -> Any:
    if value is None:
        msg = f"frozen manifest is missing {field_name}"
        raise ValueError(msg)
    return value


def protocol_file_digest() -> str:
    """Hash the canonical protocol bytes used by this checked-out harness."""
    repo_root = Path(__file__).resolve().parents[3]
    path = repo_root / "docs" / "uncharted-ai-os" / "experiments" / "PHASE_1F_A_EDITORIAL_EVAL_PROTOCOL.md"
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"
