"""Strict, experiment-owned contracts for the Phase 1F-A pilot."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, StringConstraints, model_validator

from .canonical import canonical_digest

CONTRACT_SCHEMA_VERSION = "phase-1f-a-contracts-v1"
CASE_BRIEF_SCHEMA_VERSION = "phase-1f-a-case-brief-v1"
ARTIFACT_SCHEMA_VERSION = "phase-1f-a-artifact-v1"
EVALUATOR_JUDGMENT_SCHEMA_VERSION = "phase-1f-a-evaluator-judgment-v1"
EVALUATOR_BINDING_SCHEMA_VERSION = "phase-1f-a-evaluator-binding-v1"
EVALUATION_SCHEMA_VERSION = "phase-1f-a-evaluation-v2"
TRACE_SCHEMA_VERSION = "phase-1f-a-trace-v1"
SUBMISSION_SCHEMA_VERSION = "phase-1f-a-submission-v1"
BLIND_SCHEMA_VERSION = "phase-1f-a-blind-v1"
REVIEW_SCHEMA_VERSION = "phase-1f-a-review-v1"
BUNDLE_SCHEMA_VERSION = "phase-1f-a-bundle-v1"

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10_000)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
Identifier = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_-]{2,127}$")]
Sha256Digest = Annotated[str, StringConstraints(pattern=r"^sha256:[0-9a-f]{64}$")]
EVIDENCE_REFS_DESCRIPTION = (
    "Every value must exactly match an existing CaseBrief.evidence[].evidence_id. "
    "CaseBrief field names, paths, aliases, insight IDs, point-of-view fields, content_job fields, objectives, "
    "and guardrails are not evidence IDs. When the CaseBrief contains no evidence items, evidence_refs must be []."
)


class StrictModel(BaseModel):
    """Immutable strict base for experimental data passed between stages."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class Condition(str, Enum):
    A = "A"
    B = "B"
    C = "C"


class DatasetClass(str, Enum):
    DEVELOPMENT = "development"
    HOLDOUT = "holdout"


class ContentJobKind(str, Enum):
    AUTHORITY = "authority"
    REACH = "reach"
    TRUST = "trust"
    CONVERSATION = "conversation"
    EDUCATION = "education"
    POSITIONING = "positioning"
    CONVERSION = "conversion"
    EXPERIMENT = "experiment"


class InputState(str, Enum):
    PROVIDED = "provided"
    WEAK = "weak"
    UNRESOLVED = "unresolved"
    MISSING = "missing"


class InternalDecision(str, Enum):
    READY_FOR_HUMAN_APPROVAL = "ready_for_human_approval"
    MINOR_REVISION = "minor_revision"
    MAJOR_REVISION = "major_revision"
    RETURN_UPSTREAM = "return_upstream"
    BLOCKED_EVIDENCE = "blocked_evidence"
    REJECT = "reject"
    HUMAN_ESCALATION = "human_escalation"


class CreatorStopDecision(str, Enum):
    """Terminal decisions a creator may make without certifying readiness."""

    RETURN_UPSTREAM = "return_upstream"
    BLOCKED_EVIDENCE = "blocked_evidence"
    REJECT = "reject"
    HUMAN_ESCALATION = "human_escalation"


class NormalizedDecision(str, Enum):
    """Only decision vocabulary permitted in primary blind review."""

    PROCEED_CANDIDATE = "PROCEED / CANDIDATE"
    EDITORIAL_REVISION_REQUIRED = "EDITORIAL REVISION REQUIRED"
    REVISE_BRIEF = "REVISE BRIEF"
    EVIDENCE_REQUIRED = "EVIDENCE REQUIRED"
    DO_NOT_DEVELOP = "DO NOT DEVELOP"
    HUMAN_JUDGMENT_REQUIRED = "HUMAN JUDGMENT REQUIRED"


class ContentJob(StrictModel):
    schema_version: Literal["phase-1f-a-content-job-v1"] = "phase-1f-a-content-job-v1"
    primary: ContentJobKind
    secondary: ContentJobKind | None = None
    objective: Text
    target_audience: Text
    desired_response: Text
    success_signals: tuple[ShortText, ...] = Field(min_length=1, max_length=3)
    guardrail_signals: tuple[ShortText, ...] = Field(min_length=1, max_length=3)
    measurement_window: ShortText
    limitations: tuple[ShortText, ...] = Field(default_factory=tuple, max_length=10)

    @model_validator(mode="after")
    def validate_secondary(self) -> ContentJob:
        if self.secondary == self.primary:
            msg = "secondary Content Job must differ from primary"
            raise ValueError(msg)
        return self


class MaterialInput(StrictModel):
    state: InputState
    value: Text | None
    notes: Text | None = None

    @model_validator(mode="after")
    def validate_state(self) -> MaterialInput:
        if self.state is InputState.PROVIDED and self.value is None:
            msg = "provided input requires a value"
            raise ValueError(msg)
        if self.state is InputState.MISSING and self.value is not None:
            msg = "missing input must not contain a value"
            raise ValueError(msg)
        return self


class EvidenceItem(StrictModel):
    evidence_id: Identifier
    description: Text
    source: Text
    content_digest: Sha256Digest | None = None
    limitations: tuple[ShortText, ...] = Field(default_factory=tuple, max_length=10)


class AttachmentRef(StrictModel):
    attachment_id: Identifier
    filename: ShortText
    content_digest: Sha256Digest
    media_type: ShortText


class CaseBrief(StrictModel):
    """Canonical B/C input. Explicit missing states are valid case content."""

    schema_version: Literal[CASE_BRIEF_SCHEMA_VERSION] = CASE_BRIEF_SCHEMA_VERSION
    case_id: Identifier
    dataset_class: DatasetClass
    source_record_version: Identifier
    input_surface_version: Identifier
    cohort: Literal["organic-instagram-reel-talking-head-en-v1"] = "organic-instagram-reel-talking-head-en-v1"
    contamination_labels: tuple[Literal["NOT HOLDOUT", "CONTAMINATED", "DEVELOPMENT ONLY"], ...] = ()
    content_job: ContentJob
    insight: MaterialInput
    point_of_view: MaterialInput
    attention_thesis_input: MaterialInput
    evidence: tuple[EvidenceItem, ...] = Field(default_factory=tuple, max_length=50)
    guardrails: tuple[ShortText, ...] = Field(min_length=1, max_length=20)
    voice_references: tuple[Text, ...] = Field(default_factory=tuple, max_length=20)
    portfolio_context: Text | None = None
    production_assumptions: tuple[ShortText, ...] = Field(default_factory=tuple, max_length=20)
    attachments: tuple[AttachmentRef, ...] = Field(default_factory=tuple, max_length=20)

    @model_validator(mode="after")
    def validate_dataset_marking(self) -> CaseBrief:
        required = {"NOT HOLDOUT", "CONTAMINATED", "DEVELOPMENT ONLY"}
        actual = set(self.contamination_labels)
        if self.dataset_class is DatasetClass.DEVELOPMENT and actual != required:
            msg = "development cases require all three contamination labels"
            raise ValueError(msg)
        if self.dataset_class is DatasetClass.HOLDOUT and actual:
            msg = "holdout cases must not carry development contamination labels"
            raise ValueError(msg)
        return self


class AttentionThesis(StrictModel):
    schema_version: Literal[ARTIFACT_SCHEMA_VERSION] = ARTIFACT_SCHEMA_VERSION
    artifact_version: Identifier
    audience_entry_state: Text
    why_now: Text
    stop_hypothesis: Text
    continue_hypothesis: Text
    promised_payoff: Text
    truthfulness_basis: Text
    uncertainty: tuple[ShortText, ...] = Field(default_factory=tuple, max_length=10)
    alternative_explanations: tuple[ShortText, ...] = Field(default_factory=tuple, max_length=10)


class AttentionBeat(StrictModel):
    beat_id: Identifier
    entering_state: Text
    attention_job: Literal["capture", "sustain", "renew", "reward", "pay_off"]
    potential_mechanism: ShortText
    value_delivered: Text
    unresolved_tension: Text | None = None
    reason_to_continue: Text | None = None
    payoff: Text
    transition: Text | None = None
    uncertainty: Text | None = None


class AttentionMap(StrictModel):
    schema_version: Literal[ARTIFACT_SCHEMA_VERSION] = ARTIFACT_SCHEMA_VERSION
    artifact_version: Identifier
    beats: tuple[AttentionBeat, ...] = Field(min_length=1, max_length=20)


class StoryBeat(StrictModel):
    beat_id: Identifier
    function: ShortText
    content: Text


class StoryArchitecture(StrictModel):
    schema_version: Literal[ARTIFACT_SCHEMA_VERSION] = ARTIFACT_SCHEMA_VERSION
    artifact_version: Identifier
    governing_movement: Text
    central_tension: Text
    beats: tuple[StoryBeat, ...] = Field(min_length=1, max_length=20)
    resolution: Text


class ScriptArtifact(StrictModel):
    schema_version: Literal[ARTIFACT_SCHEMA_VERSION] = ARTIFACT_SCHEMA_VERSION
    artifact_version: Identifier
    spoken_script: Text
    hook_packaging_direction: Text
    voice_refinement_notes: tuple[ShortText, ...] = Field(default_factory=tuple, max_length=20)


class ClaimType(str, Enum):
    FACTUAL = "factual_claim"
    OPINION = "jentz_opinion"
    PERSONAL_EXPERIENCE = "personal_experience"
    INFERENCE = "inference"
    ILLUSTRATIVE = "illustrative_or_hypothetical"


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    PARTIALLY_VERIFIED = "partially_verified"
    UNVERIFIED = "unverified"
    CONTRADICTED = "contradicted"
    NOT_APPLICABLE = "not_applicable"


class ClaimDecision(str, Enum):
    RETAIN = "retain"
    QUALIFY = "qualify"
    REPLACE = "replace"
    REMOVE = "remove"
    BLOCK_EVIDENCE = "block_for_evidence"
    ESCALATE = "escalate"


class Claim(StrictModel):
    claim_id: Identifier
    passage: Text
    claim_type: ClaimType
    evidence_refs: tuple[Identifier, ...] = Field(
        default_factory=tuple,
        max_length=20,
        description=EVIDENCE_REFS_DESCRIPTION,
    )
    verification_status: VerificationStatus
    decision: ClaimDecision
    uncertainty: Text | None = None


class ClaimMap(StrictModel):
    schema_version: Literal[ARTIFACT_SCHEMA_VERSION] = ARTIFACT_SCHEMA_VERSION
    artifact_version: Identifier
    no_material_claims: bool
    claims: tuple[Claim, ...] = Field(default_factory=tuple, max_length=50)

    @model_validator(mode="after")
    def validate_claim_presence(self) -> ClaimMap:
        if self.no_material_claims == bool(self.claims):
            msg = "no_material_claims must be true exactly when claims is empty"
            raise ValueError(msg)
        return self


class ArtifactProvenance(StrictModel):
    artifact_name: Literal["attention_thesis", "attention_map", "story_architecture", "script", "claim_map"]
    artifact_version: Identifier
    capability_step: ShortText


class EditorialPackage(StrictModel):
    schema_version: Literal[ARTIFACT_SCHEMA_VERSION] = ARTIFACT_SCHEMA_VERSION
    package_version: Identifier
    attention_thesis: AttentionThesis
    attention_map: AttentionMap
    story_architecture: StoryArchitecture
    script: ScriptArtifact
    claim_map: ClaimMap
    provenance: tuple[ArtifactProvenance, ...] = Field(min_length=5, max_length=5)

    @model_validator(mode="after")
    def validate_provenance(self) -> EditorialPackage:
        expected = {"attention_thesis", "attention_map", "story_architecture", "script", "claim_map"}
        names = [item.artifact_name for item in self.provenance]
        if set(names) != expected or len(names) != len(set(names)):
            msg = "provenance must contain each required artifact exactly once"
            raise ValueError(msg)
        version_by_name = {
            "attention_thesis": self.attention_thesis.artifact_version,
            "attention_map": self.attention_map.artifact_version,
            "story_architecture": self.story_architecture.artifact_version,
            "script": self.script.artifact_version,
            "claim_map": self.claim_map.artifact_version,
        }
        if any(item.artifact_version != version_by_name[item.artifact_name] for item in self.provenance):
            msg = "provenance versions must match the packaged artifacts"
            raise ValueError(msg)
        return self


class DomainName(str, Enum):
    INTEGRITY = "integrity"
    EDITORIAL_VALUE = "editorial_value"
    ATTENTION_ARCHITECTURE = "attention_architecture"
    EXPRESSION = "expression"
    STRATEGIC_FIT = "strategic_fit"


class EvaluationAnchor(str, Enum):
    STRONG = "strong"
    ACCEPTABLE = "acceptable"
    WEAK = "weak"
    CRITICAL_PROBLEM = "critical_problem"
    NOT_ASSESSABLE = "not_assessable"


class DomainEvaluation(StrictModel):
    domain: DomainName
    anchor: EvaluationAnchor
    evidence: tuple[Text, ...] = Field(min_length=1, max_length=10)
    uncertainty: Text | None = None


class EvaluatorJudgment(StrictModel):
    """Model-authored semantic evaluation with no authoritative identity fields."""

    schema_version: Literal[EVALUATOR_JUDGMENT_SCHEMA_VERSION] = EVALUATOR_JUDGMENT_SCHEMA_VERSION
    decision: InternalDecision
    domains: tuple[DomainEvaluation, ...] = Field(min_length=5, max_length=5)
    hard_failures: tuple[Text, ...] = Field(default_factory=tuple, max_length=20)
    requested_actions: tuple[Text, ...] = Field(default_factory=tuple, max_length=20)
    rationale: Text

    @model_validator(mode="after")
    def validate_domains_and_decision(self) -> EvaluatorJudgment:
        names = [item.domain for item in self.domains]
        if set(names) != set(DomainName) or len(names) != len(set(names)):
            msg = "evaluation must contain every domain exactly once"
            raise ValueError(msg)
        if self.decision is InternalDecision.READY_FOR_HUMAN_APPROVAL:
            unacceptable = {
                EvaluationAnchor.WEAK,
                EvaluationAnchor.CRITICAL_PROBLEM,
                EvaluationAnchor.NOT_ASSESSABLE,
            }
            if self.hard_failures or any(item.anchor in unacceptable for item in self.domains):
                msg = "ready decision cannot coexist with a hard failure or unresolved domain"
                raise ValueError(msg)
        return self


class EvaluatorBinding(StrictModel):
    """Host-owned provenance for one evaluator judgment and its exact invocation."""

    schema_version: Literal[EVALUATOR_BINDING_SCHEMA_VERSION] = EVALUATOR_BINDING_SCHEMA_VERSION
    package_digest: Sha256Digest
    evaluator_call_id: Identifier
    evaluator_input_digest: Sha256Digest


class EvaluationResult(StrictModel):
    """Persisted semantic judgment bound to deterministic host provenance."""

    schema_version: Literal[EVALUATION_SCHEMA_VERSION] = EVALUATION_SCHEMA_VERSION
    judgment: EvaluatorJudgment
    binding: EvaluatorBinding

    @property
    def decision(self) -> InternalDecision:
        return self.judgment.decision


class ResourceUsage(StrictModel):
    """Provider usage with cached/reasoning tokens retained as diagnostic subsets.

    The enforceable total is input plus output tokens. Provider-reported cached
    input and reasoning tokens are normally subsets of those totals and are not
    added again. If either total is unavailable, the enforceable total is
    unknown rather than partially summed.
    """

    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cached_input_tokens: int | None = Field(default=None, ge=0)
    reasoning_tokens: int | None = Field(default=None, ge=0)
    tool_calls: int | None = Field(default=None, ge=0)
    monetary_cost: Decimal | None = Field(default=None, ge=0)
    currency: Literal["USD", "EUR", "GBP"] | None = None

    @model_validator(mode="after")
    def validate_cost_currency(self) -> ResourceUsage:
        if (self.monetary_cost is None) != (self.currency is None):
            msg = "monetary_cost and currency must either both be known or both be unknown"
            raise ValueError(msg)
        return self

    @property
    def accounted_total_tokens(self) -> int | None:
        if self.input_tokens is None or self.output_tokens is None:
            return None
        return self.input_tokens + self.output_tokens


class FailureInfo(StrictModel):
    failure_type: Identifier
    safe_message: ShortText
    retryable: bool
    diagnostics: "FailureDiagnostics | None" = None


class FailureDiagnostics(StrictModel):
    """Allowlisted, non-content diagnostics for private failure traces."""

    exception_class: ShortText
    exception_module: ShortText
    stage: Literal[
        "model_initialization",
        "structured_output_binding",
        "request_construction",
        "provider_request",
        "provider_response",
        "structured_output_parsing",
        "usage_extraction",
        "contract_validation",
        "presentation",
    ]
    http_status_code: int | None = Field(default=None, ge=100, le=599)
    provider_error_code: ShortText | None = None
    provider_error_type: ShortText | None = None
    request_id: ShortText | None = None
    network_request_attempted: bool = False
    diagnostic_message: ShortText
    module_path: ShortText | None = None
    function_name: ShortText | None = None
    line_number: int | None = Field(default=None, ge=1)
    object_type: ShortText | None = None
    expected_type: ShortText | None = None
    actual_type: ShortText | None = None


class ModelCallTrace(StrictModel):
    schema_version: Literal[TRACE_SCHEMA_VERSION] = TRACE_SCHEMA_VERSION
    call_id: Identifier
    run_id: Identifier
    role: Literal["a_generator", "b_generator", "b_self_review", "c_creator", "c_evaluator"]
    prompt_digest: Sha256Digest
    input_digest: Sha256Digest
    provider: ShortText
    model_identifier: ShortText
    reasoning: ShortText
    model_config_digest: Sha256Digest
    provider_internal_retries: Literal[0] = 0
    attempt_number: int = Field(ge=1, le=2)
    infrastructure_retry: bool
    infrastructure_retry_eligible: bool = False
    retry_decision: Literal[
        "not_applicable",
        "retry_scheduled",
        "retry_limit_reached",
        "resource_ceiling",
    ] = "not_applicable"
    started_at: datetime
    ended_at: datetime
    latency_ms: int = Field(ge=0)
    usage: ResourceUsage
    failure: FailureInfo | None = None

    @model_validator(mode="after")
    def validate_time_and_attempt(self) -> ModelCallTrace:
        if self.started_at.tzinfo is None or self.ended_at.tzinfo is None:
            msg = "trace timestamps must be timezone-aware"
            raise ValueError(msg)
        if self.ended_at < self.started_at:
            msg = "model call cannot end before it starts"
            raise ValueError(msg)
        if self.infrastructure_retry != (self.attempt_number > 1):
            msg = "retry marker must agree with attempt number"
            raise ValueError(msg)
        if self.retry_decision != "not_applicable" and not self.infrastructure_retry_eligible:
            msg = "retry decisions require a retry-eligible infrastructure failure"
            raise ValueError(msg)
        return self


class StructuralValidationTrace(StrictModel):
    artifact_digest: Sha256Digest
    valid: bool
    issue_codes: tuple[Identifier, ...] = ()

    @model_validator(mode="after")
    def validate_issues(self) -> StructuralValidationTrace:
        if self.valid == bool(self.issue_codes):
            msg = "valid structural results have no issues; invalid results require issue codes"
            raise ValueError(msg)
        return self


class RunTrace(StrictModel):
    schema_version: Literal[TRACE_SCHEMA_VERSION] = TRACE_SCHEMA_VERSION
    run_id: Identifier
    experiment_version: Identifier
    protocol_version: Literal["phase-1f-a-v1"] = "phase-1f-a-v1"
    manifest_version: Identifier
    case_id: Identifier
    condition: Condition
    original_run_id: Identifier | None = None
    case_brief_digest: Sha256Digest | None = None
    input_surface_digest: Sha256Digest
    calls: tuple[ModelCallTrace, ...]
    substantive_revisions: int = Field(ge=0, le=2)
    max_substantive_revisions: int = Field(ge=0, le=2)
    max_model_calls: int = Field(ge=1)
    max_total_tokens: int = Field(gt=0)
    max_total_latency_ms: int = Field(gt=0)
    max_cost: Decimal = Field(ge=0)
    budget_currency: Literal["USD", "EUR", "GBP"]
    actual_usage: ResourceUsage
    artifact_digests: tuple[Sha256Digest, ...] = ()
    structural_validations: tuple[StructuralValidationTrace, ...] = ()
    failures: tuple[FailureInfo, ...] = ()
    terminal_decision: NormalizedDecision
    deviations: tuple[Text, ...] = ()
    started_at: datetime
    completed_at: datetime

    @model_validator(mode="after")
    def validate_trace(self) -> RunTrace:
        if self.started_at.tzinfo is None or self.completed_at.tzinfo is None:
            msg = "run timestamps must be timezone-aware"
            raise ValueError(msg)
        if self.completed_at < self.started_at:
            msg = "run cannot complete before it starts"
            raise ValueError(msg)
        if len(self.calls) > self.max_model_calls:
            msg = "trace exceeds maximum model-call budget"
            raise ValueError(msg)
        if self.substantive_revisions > self.max_substantive_revisions:
            msg = "trace exceeds maximum substantive-revision budget"
            raise ValueError(msg)
        if any(call.run_id != self.run_id for call in self.calls):
            msg = "every call must carry the parent run_id"
            raise ValueError(msg)
        call_ids = [call.call_id for call in self.calls]
        if len(call_ids) != len(set(call_ids)):
            msg = "model call IDs must be unique within a run"
            raise ValueError(msg)
        return self


class CTerminalState(str, Enum):
    EVALUATOR_DECISION = "evaluator_decision"
    PRE_PACKAGE_CREATOR_STOP = "pre_package_creator_stop"
    REVISION_CREATOR_STOP = "revision_creator_stop"
    DETERMINISTIC_VALIDATION_FAILURE = "deterministic_validation_failure"
    EVALUATOR_FAILURE = "evaluator_failure"
    REVISION_BUDGET_EXHAUSTED = "revision_budget_exhausted"
    RESOURCE_BUDGET_EXHAUSTED = "resource_budget_exhausted"
    EXECUTION_FAILURE = "execution_failure"


class CreatorStopTrace(StrictModel):
    phase: Literal["pre_package", "revision"]
    decision: CreatorStopDecision
    rationale: Text
    next_action: Text


class CExecutionHistory(StrictModel):
    """Ordered parsed C evidence retained independently from terminal success."""

    packages: tuple[EditorialPackage, ...] = Field(default_factory=tuple, max_length=3)
    evaluations: tuple[EvaluationResult, ...] = Field(default_factory=tuple, max_length=3)
    creator_stops: tuple[CreatorStopTrace, ...] = Field(default_factory=tuple, max_length=1)
    evaluator_failures: tuple[FailureInfo, ...] = Field(default_factory=tuple, max_length=3)
    terminal_state: CTerminalState

    @model_validator(mode="after")
    def validate_terminal_evidence(self) -> CExecutionHistory:
        if len(self.evaluations) > len(self.packages):
            msg = "C history cannot contain more evaluations than packages"
            raise ValueError(msg)
        for index, evaluation in enumerate(self.evaluations):
            if evaluation.binding.package_digest != canonical_digest(self.packages[index]):
                msg = "each retained C evaluation must bind to its corresponding package"
                raise ValueError(msg)
        if self.terminal_state is CTerminalState.PRE_PACKAGE_CREATOR_STOP and (
            self.packages or len(self.creator_stops) != 1 or self.creator_stops[0].phase != "pre_package"
        ):
            msg = "pre-package creator stop requires one pre-package stop and no package"
            raise ValueError(msg)
        if self.terminal_state is CTerminalState.REVISION_CREATOR_STOP and (
            not self.packages or len(self.creator_stops) != 1 or self.creator_stops[0].phase != "revision"
        ):
            msg = "revision creator stop requires retained package history and one revision stop"
            raise ValueError(msg)
        if self.terminal_state in {
            CTerminalState.EVALUATOR_DECISION,
            CTerminalState.REVISION_BUDGET_EXHAUSTED,
        } and (not self.packages or not self.evaluations):
            msg = "evaluator terminal states require retained package and evaluation history"
            raise ValueError(msg)
        if self.terminal_state is CTerminalState.EVALUATOR_FAILURE and not self.evaluator_failures:
            msg = "evaluator failure terminal state requires retained evaluator failure evidence"
            raise ValueError(msg)
        return self


class NormalizedSubmission(StrictModel):
    decision: NormalizedDecision
    spoken_script: Text | None = None
    explanation: Text | None = None
    next_action: Text | None = None

    @model_validator(mode="after")
    def validate_surface(self) -> NormalizedSubmission:
        has_candidate = self.decision in {
            NormalizedDecision.PROCEED_CANDIDATE,
            NormalizedDecision.EDITORIAL_REVISION_REQUIRED,
        }
        if has_candidate and self.spoken_script is None:
            msg = "candidate decisions require a spoken script"
            raise ValueError(msg)
        if not has_candidate and self.spoken_script is not None:
            msg = "non-candidate decisions must explicitly omit the script"
            raise ValueError(msg)
        if not has_candidate and (self.explanation is None or self.next_action is None):
            msg = "non-candidate decisions require an explanation and next action"
            raise ValueError(msg)
        return self


class ConditionSubmission(StrictModel):
    schema_version: Literal[SUBMISSION_SCHEMA_VERSION] = SUBMISSION_SCHEMA_VERSION
    run_id: Identifier
    case_id: Identifier
    condition: Condition
    case_brief_digest: Sha256Digest | None
    first_pass_package: EditorialPackage | None = None
    final_package: EditorialPackage | None = None
    evaluator_result: EvaluationResult | None = None
    c_history: CExecutionHistory | None = None
    normalized: NormalizedSubmission
    trace: RunTrace

    @model_validator(mode="after")
    def validate_submission(self) -> ConditionSubmission:
        if self.trace.run_id != self.run_id or self.trace.case_id != self.case_id:
            msg = "submission and trace identities must match"
            raise ValueError(msg)
        if self.trace.condition is not self.condition:
            msg = "submission and trace conditions must match"
            raise ValueError(msg)
        if self.trace.terminal_decision is not self.normalized.decision:
            msg = "submission and trace terminal decisions must match"
            raise ValueError(msg)
        if self.trace.case_brief_digest != self.case_brief_digest:
            msg = "submission and trace CaseBrief digests must match"
            raise ValueError(msg)
        if self.condition is Condition.A and any(
            item is not None
            for item in (
                self.case_brief_digest,
                self.first_pass_package,
                self.final_package,
                self.evaluator_result,
                self.c_history,
            )
        ):
            msg = "Condition A cannot carry canonical-brief, package, evaluator, or C-history data"
            raise ValueError(msg)
        if self.condition in {Condition.B, Condition.C} and self.case_brief_digest is None:
            msg = "B and C submissions require the canonical CaseBrief digest"
            raise ValueError(msg)
        if self.condition is Condition.B and (self.evaluator_result is not None or self.c_history is not None):
            msg = "Condition B cannot carry independent evaluator or C-history data"
            raise ValueError(msg)
        if (
            self.condition in {Condition.B, Condition.C}
            and self.normalized.decision
            in {
                NormalizedDecision.PROCEED_CANDIDATE,
                NormalizedDecision.EDITORIAL_REVISION_REQUIRED,
            }
            and (self.final_package is None or self.normalized.spoken_script != self.final_package.script.spoken_script)
        ):
            msg = "B/C candidate text must match the retained final package"
            raise ValueError(msg)
        if self.condition is Condition.C:
            if self.c_history is None:
                msg = "Condition C requires ordered execution history"
                raise ValueError(msg)
            packages = self.c_history.packages
            if self.first_pass_package != (packages[0] if packages else None):
                msg = "C first-pass package must match the first retained package"
                raise ValueError(msg)
            if self.final_package != (packages[-1] if packages else None):
                msg = "C final package must match the latest retained package"
                raise ValueError(msg)
            latest_evaluation = self.c_history.evaluations[-1] if self.c_history.evaluations else None
            if self.evaluator_result != latest_evaluation:
                msg = "C evaluator result must match the latest retained evaluation"
                raise ValueError(msg)
            evaluator_calls = {
                call.call_id: call
                for call in self.trace.calls
                if call.role == "c_evaluator" and call.failure is None
            }
            successful_creator_positions = [
                index
                for index, call in enumerate(self.trace.calls)
                if call.role == "c_creator" and call.failure is None
            ]
            if len(successful_creator_positions) < len(packages):
                msg = "each retained C package requires a preceding successful creator call"
                raise ValueError(msg)
            evaluation_call_positions: list[int] = []
            trace_positions = {call.call_id: index for index, call in enumerate(self.trace.calls)}
            for index, evaluation in enumerate(self.c_history.evaluations):
                binding = evaluation.binding
                call = evaluator_calls.get(binding.evaluator_call_id)
                if call is None or call.run_id != self.run_id:
                    msg = "C evaluation binding must identify a successful evaluator call in the current Run"
                    raise ValueError(msg)
                if call.input_digest != binding.evaluator_input_digest:
                    msg = "C evaluation binding input digest must match its evaluator call"
                    raise ValueError(msg)
                evaluation_position = trace_positions[call.call_id]
                creator_position = successful_creator_positions[index]
                next_creator_position = (
                    successful_creator_positions[index + 1]
                    if index + 1 < len(successful_creator_positions)
                    else None
                )
                evaluator_window_end = (
                    next_creator_position if next_creator_position is not None else len(self.trace.calls)
                )
                successful_evaluator_calls = [
                    candidate
                    for position, candidate in enumerate(self.trace.calls)
                    if creator_position < position < evaluator_window_end
                    and candidate.role == "c_evaluator"
                    and candidate.failure is None
                ]
                if len(successful_evaluator_calls) != 1:
                    msg = (
                        "each evaluated C package requires exactly one successful evaluator call "
                        "in its revision window"
                    )
                    raise ValueError(msg)
                if successful_evaluator_calls[0].call_id != binding.evaluator_call_id:
                    msg = (
                        "C evaluation binding must identify the unique successful evaluator call "
                        "in its revision window"
                    )
                    raise ValueError(msg)
                if evaluation_position <= creator_position or (
                    next_creator_position is not None and evaluation_position >= next_creator_position
                ):
                    msg = "each C evaluation call must follow its package creator and precede the next revision"
                    raise ValueError(msg)
                evaluation_call_positions.append(evaluation_position)
            duplicate_bindings = len(evaluation_call_positions) != len(set(evaluation_call_positions))
            out_of_order_bindings = evaluation_call_positions != sorted(evaluation_call_positions)
            if duplicate_bindings or out_of_order_bindings:
                msg = "C evaluations must bind once each in evaluator-call order"
                raise ValueError(msg)
            if self.normalized.decision is NormalizedDecision.PROCEED_CANDIDATE and (
                latest_evaluation is None or latest_evaluation.decision is not InternalDecision.READY_FOR_HUMAN_APPROVAL
            ):
                msg = "a C candidate cannot proceed without evaluator-authored readiness"
                raise ValueError(msg)
        return self


class BlindCandidate(StrictModel):
    """Primary-review surface. It intentionally has no condition or evaluator fields."""

    schema_version: Literal[BLIND_SCHEMA_VERSION] = BLIND_SCHEMA_VERSION
    blind_candidate_id: Identifier
    case_id: Identifier
    position: int = Field(ge=1, le=3)
    submission: NormalizedSubmission


class RevealEntry(StrictModel):
    blind_candidate_id: Identifier
    case_id: Identifier
    condition: Condition
    run_id: Identifier


class RevealMapping(StrictModel):
    schema_version: Literal[BLIND_SCHEMA_VERSION] = BLIND_SCHEMA_VERSION
    mapping_id: Identifier
    entries: tuple[RevealEntry, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_bijection(self) -> RevealMapping:
        blind_ids = [entry.blind_candidate_id for entry in self.entries]
        run_ids = [entry.run_id for entry in self.entries]
        if len(blind_ids) != len(set(blind_ids)) or len(run_ids) != len(set(run_ids)):
            msg = "reveal mapping must be a bijection between blind IDs and run IDs"
            raise ValueError(msg)
        conditions_by_case: dict[str, list[Condition]] = {}
        for entry in self.entries:
            conditions_by_case.setdefault(entry.case_id, []).append(entry.condition)
        if any(
            len(conditions) != len(Condition) or set(conditions) != set(Condition)
            for conditions in conditions_by_case.values()
        ):
            msg = "each mapped case must contain exactly one A, B, and C condition"
            raise ValueError(msg)
        return self


class ReviewStage(str, Enum):
    STAGE_1 = "stage_1"
    STAGE_2 = "stage_2"
    REVEALED = "revealed"


class RewriteBurden(str, Enum):
    NONE = "none"
    MINOR = "localized_minor"
    MAJOR = "substantial_major"
    NEW_PIECE = "effectively_new_piece"


class CandidateUseDecision(str, Enum):
    USE_AS_IS = "use_as_is"
    MINOR_EDIT = "minor_edit"
    MAJOR_REDEVELOPMENT = "major_redevelopment"
    NOT_USE = "not_use"


class Stage1Assessment(StrictModel):
    blind_candidate_id: Identifier
    category_appropriate: bool
    use_decision: CandidateUseDecision
    rewrite_burden: RewriteBurden
    main_strength: Text
    main_weakness: Text
    confidence: Literal["low", "medium", "high"]
    reasons: tuple[Text, ...] = Field(min_length=1, max_length=10)
    preference_basis: Literal["editorial", "personal", "both"]
    locked_at: datetime


class Stage2Comparison(StrictModel):
    case_id: Identifier
    acceptable_candidate_ids: tuple[Identifier, ...]
    strongest_candidate_ids: tuple[Identifier, ...]
    least_rewrite_candidate_ids: tuple[Identifier, ...]
    strongest_point_of_view_candidate_ids: tuple[Identifier, ...]
    strongest_attention_candidate_ids: tuple[Identifier, ...]
    strongest_payoff_candidate_ids: tuple[Identifier, ...]
    strongest_voice_candidate_ids: tuple[Identifier, ...]
    better_non_script_candidate_ids: tuple[Identifier, ...]
    reasons: tuple[Text, ...] = Field(min_length=1, max_length=20)
    editorial_personal_difference: Text
    uncertainty_and_change_evidence: Text
    confidence: Literal["low", "medium", "high"]
    locked_at: datetime


class IdentityGuess(StrictModel):
    blind_candidate_id: Identifier
    guessed_condition: Condition
    confidence: Literal["low", "medium", "high"]


class PreUnblindingRecord(StrictModel):
    schema_version: Literal["phase-1f-a-pre-unblinding-v1"] = "phase-1f-a-pre-unblinding-v1"
    bundle_id: Identifier
    identity_guesses: tuple[IdentityGuess, ...] = Field(min_length=1)
    evidence_summary: Text
    comparative_decision_record: Text
    known_limitations: tuple[Text, ...] = Field(default_factory=tuple, max_length=20)
    locked_at: datetime

    @model_validator(mode="after")
    def validate_guesses(self) -> PreUnblindingRecord:
        candidate_ids = [guess.blind_candidate_id for guess in self.identity_guesses]
        if len(candidate_ids) != len(set(candidate_ids)):
            msg = "pre-unblinding identity guesses must be unique per candidate"
            raise ValueError(msg)
        if self.locked_at.tzinfo is None:
            msg = "pre-unblinding lock timestamp must be timezone-aware"
            raise ValueError(msg)
        return self


class HumanReview(StrictModel):
    schema_version: Literal[REVIEW_SCHEMA_VERSION] = REVIEW_SCHEMA_VERSION
    review_id: Identifier
    stage: ReviewStage
    stage_1_assessments: tuple[Stage1Assessment, ...] = ()
    stage_2_comparisons: tuple[Stage2Comparison, ...] = ()
    revealed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_stage(self) -> HumanReview:
        if self.stage is ReviewStage.STAGE_1 and (self.stage_2_comparisons or self.revealed_at):
            msg = "Stage 1 review cannot contain Stage 2 or reveal data"
            raise ValueError(msg)
        if self.stage is ReviewStage.STAGE_2 and self.revealed_at is not None:
            msg = "Stage 2 review cannot be marked revealed"
            raise ValueError(msg)
        if self.stage is ReviewStage.REVEALED and self.revealed_at is None:
            msg = "revealed review requires a reveal timestamp"
            raise ValueError(msg)
        return self


class BlindReviewBundle(StrictModel):
    schema_version: Literal[BUNDLE_SCHEMA_VERSION] = BUNDLE_SCHEMA_VERSION
    bundle_id: Identifier
    candidates: tuple[BlindCandidate, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_no_duplicate_candidates(self) -> BlindReviewBundle:
        identifiers = [candidate.blind_candidate_id for candidate in self.candidates]
        if len(identifiers) != len(set(identifiers)):
            msg = "blind candidate IDs must be unique"
            raise ValueError(msg)
        return self


def assert_json_safe(value: Any) -> JsonValue:
    """Validate recursively that provider metadata contains JSON-safe values only."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, list):
        return [assert_json_safe(item) for item in value]
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        return {key: assert_json_safe(item) for key, item in value.items()}
    msg = f"metadata value is not JSON-safe: {type(value).__name__}"
    raise TypeError(msg)
