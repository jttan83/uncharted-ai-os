from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

import pytest

from scripts.uncharted_ai_os.editorial_eval.canonical import canonical_digest
from scripts.uncharted_ai_os.editorial_eval.contracts import (
    ArtifactProvenance,
    AttentionBeat,
    AttentionMap,
    AttentionThesis,
    CaseBrief,
    CExecutionHistory,
    ClaimMap,
    Condition,
    ConditionSubmission,
    ContentJob,
    ContentJobKind,
    CTerminalState,
    DatasetClass,
    DomainEvaluation,
    DomainName,
    EditorialPackage,
    EvaluationAnchor,
    EvaluationResult,
    EvaluatorBinding,
    EvaluatorJudgment,
    InputState,
    InternalDecision,
    MaterialInput,
    ModelCallTrace,
    NormalizedDecision,
    NormalizedSubmission,
    ResourceUsage,
    RunTrace,
    ScriptArtifact,
    StoryArchitecture,
    StoryBeat,
)
from scripts.uncharted_ai_os.editorial_eval.invokers import InvocationModelConfig
from scripts.uncharted_ai_os.editorial_eval.workflows import ExecutionLimits, RuntimeConfiguration

FIXED_TIME = datetime(2026, 1, 2, 3, 4, tzinfo=timezone.utc)
TEST_DIGEST = f"sha256:{'a' * 64}"


@pytest.fixture
def case_brief() -> CaseBrief:
    return make_case_brief()


@pytest.fixture
def editorial_package() -> EditorialPackage:
    return make_package("v1")


@pytest.fixture
def model_config() -> InvocationModelConfig:
    return InvocationModelConfig(
        provider="test-provider",
        model_identifier="test-model-v1",
        reasoning="medium",
        temperature=0.2,
        seed=7,
        max_output_tokens=2_000,
        timeout_seconds=30,
    )


@pytest.fixture
def bc_limits() -> ExecutionLimits:
    return ExecutionLimits(
        max_model_calls=7,
        max_substantive_revisions=2,
        max_total_tokens=20_000,
        max_total_latency_ms=60_000,
        max_cost=Decimal(5),
        currency="USD",
    )


def make_runtime_configuration(
    model_config: InvocationModelConfig,
    *,
    a_limits: ExecutionLimits | None = None,
    bc_limits: ExecutionLimits | None = None,
    evaluator_config: InvocationModelConfig | None = None,
) -> RuntimeConfiguration:
    shared_bc_limits = bc_limits or ExecutionLimits(
        max_model_calls=7,
        max_substantive_revisions=2,
        max_total_tokens=20_000,
        max_total_latency_ms=60_000,
        max_cost=Decimal(5),
        currency="USD",
    )
    return RuntimeConfiguration(
        primary_generator=model_config,
        evaluator=evaluator_config or model_config,
        condition_a=a_limits
        or ExecutionLimits(
            max_model_calls=2,
            max_substantive_revisions=0,
            max_total_tokens=20_000,
            max_total_latency_ms=60_000,
            max_cost=Decimal(5),
            currency="USD",
        ),
        condition_b=shared_bc_limits,
        condition_c=shared_bc_limits,
    )


@pytest.fixture
def runtime_config(model_config, bc_limits) -> RuntimeConfiguration:
    return make_runtime_configuration(model_config, bc_limits=bc_limits)


def make_case_brief(case_id: str = "case_development_001") -> CaseBrief:
    return CaseBrief(
        case_id=case_id,
        dataset_class=DatasetClass.DEVELOPMENT,
        source_record_version="source_v1",
        input_surface_version="brief_v1",
        contamination_labels=("NOT HOLDOUT", "CONTAMINATED", "DEVELOPMENT ONLY"),
        content_job=ContentJob(
            primary=ContentJobKind.AUTHORITY,
            secondary=ContentJobKind.CONVERSATION,
            objective="Help decision-makers distinguish agreement from alignment.",
            target_audience="Corporate leaders and HR or L&D decision-makers.",
            desired_response="Recognize the practical distinction and reconsider meeting habits.",
            success_signals=("Relevant saves", "Substantive responses"),
            guardrail_signals=("No false certainty",),
            measurement_window="Seven days after any separately approved publication.",
            limitations=("No publication or outcome measurement occurs in this experiment.",),
        ),
        insight=MaterialInput(
            state=InputState.PROVIDED,
            value="Agreement can hide unresolved commitment; alignment makes trade-offs explicit.",
        ),
        point_of_view=MaterialInput(
            state=InputState.PROVIDED,
            value="Leaders should stop treating silence as alignment.",
        ),
        attention_thesis_input=MaterialInput(
            state=InputState.UNRESOLVED,
            value=None,
            notes="The condition must decide whether a truthful thesis can be constructed.",
        ),
        guardrails=("No publication", "Do not invent research evidence"),
        voice_references=("Direct, specific, calm, and willing to challenge a weak assumption.",),
        production_assumptions=("Single-speaker talking head",),
    )


def make_package(version: str) -> EditorialPackage:
    thesis_version = f"thesis_{version}"
    map_version = f"attention_{version}"
    story_version = f"story_{version}"
    script_version = f"script_{version}"
    claims_version = f"claims_{version}"
    return EditorialPackage(
        package_version=f"package_{version}",
        attention_thesis=AttentionThesis(
            artifact_version=thesis_version,
            audience_entry_state="They may treat a quiet meeting as agreement.",
            why_now="AI-era work redesign makes hidden disagreement more costly.",
            stop_hypothesis="A direct challenge to silence-as-agreement is self-relevant.",
            continue_hypothesis="A concrete distinction creates useful tension and progress.",
            promised_payoff="A practical test for real alignment.",
            truthfulness_basis="The piece is framed as Jentz's professional judgment.",
            uncertainty=("Audience interpretation may vary.",),
            alternative_explanations=("The topic itself may drive interest.",),
        ),
        attention_map=AttentionMap(
            artifact_version=map_version,
            beats=(
                AttentionBeat(
                    beat_id="beat_open",
                    entering_state="Silence seems positive.",
                    attention_job="capture",
                    potential_mechanism="Contradiction",
                    value_delivered="Silence is not evidence of commitment.",
                    unresolved_tension="What would count as alignment?",
                    reason_to_continue="A practical distinction is promised.",
                    payoff="The familiar signal is challenged.",
                    transition="Move to the decision test.",
                ),
                AttentionBeat(
                    beat_id="beat_payoff",
                    entering_state="They want a better test.",
                    attention_job="pay_off",
                    potential_mechanism="Specificity",
                    value_delivered="Name trade-offs, owners, and next actions.",
                    payoff="A concrete alignment test.",
                ),
            ),
        ),
        story_architecture=StoryArchitecture(
            artifact_version=story_version,
            governing_movement="From assumed agreement to explicit commitment.",
            central_tension="Quiet agreement versus operational alignment.",
            beats=(
                StoryBeat(beat_id="story_problem", function="challenge", content="Silence is ambiguous."),
                StoryBeat(beat_id="story_resolution", function="test", content="Make commitments explicit."),
            ),
            resolution="Alignment is visible in explicit trade-offs, ownership, and action.",
        ),
        script=ScriptArtifact(
            artifact_version=script_version,
            spoken_script=(
                "A quiet room is not an aligned room. Agreement can mean nobody wants to reopen the debate. "
                "Alignment is harder: people can name the trade-off, the owner, and what happens next. "
                "If those answers are fuzzy, you do not have alignment. You have silence."
            ),
            hook_packaging_direction="Open directly on the false equivalence between quiet and aligned.",
            voice_refinement_notes=("Prefer plain verbs", "Keep the challenge calm"),
        ),
        claim_map=ClaimMap(
            artifact_version=claims_version,
            no_material_claims=True,
            claims=(),
        ),
        provenance=tuple(
            ArtifactProvenance(artifact_name=name, artifact_version=artifact_version, capability_step=step)
            for name, artifact_version, step in (
                ("attention_thesis", thesis_version, "Attention and Retention Engineering"),
                ("attention_map", map_version, "Attention and Retention Engineering"),
                ("story_architecture", story_version, "Story Architecture"),
                ("script", script_version, "Script Development and Voice Calibration"),
                ("claim_map", claims_version, "Claim Governance"),
            )
        ),
    )


def make_judgment(
    decision: InternalDecision = InternalDecision.READY_FOR_HUMAN_APPROVAL,
) -> EvaluatorJudgment:
    anchor = EvaluationAnchor.ACCEPTABLE
    return EvaluatorJudgment(
        decision=decision,
        domains=tuple(
            DomainEvaluation(domain=domain, anchor=anchor, evidence=(f"Observable {domain.value} evidence.",))
            for domain in DomainName
        ),
        requested_actions=("Revise the identified material weakness.",)
        if decision in {InternalDecision.MINOR_REVISION, InternalDecision.MAJOR_REVISION}
        else (),
        rationale="The package is coherent against the requested decision.",
    )


def make_model_call(
    run_id: str,
    suffix: str,
    role: Literal["a_generator", "b_generator", "b_self_review", "c_creator", "c_evaluator"],
) -> ModelCallTrace:
    return ModelCallTrace(
        call_id=f"call_{suffix}",
        run_id=run_id,
        role=role,
        prompt_digest=TEST_DIGEST,
        input_digest=TEST_DIGEST,
        provider="offline",
        model_identifier="offline-model",
        reasoning="medium",
        model_config_digest=TEST_DIGEST,
        provider_internal_retries=0,
        attempt_number=1,
        infrastructure_retry=False,
        started_at=FIXED_TIME,
        ended_at=FIXED_TIME,
        latency_ms=1,
        usage=ResourceUsage(),
    )


def make_evaluator_call(run_id: str, suffix: str = "evaluation") -> ModelCallTrace:
    return make_model_call(run_id, suffix, "c_evaluator")


def make_bound_evaluation(
    package: EditorialPackage,
    call: ModelCallTrace,
    decision: InternalDecision = InternalDecision.READY_FOR_HUMAN_APPROVAL,
) -> EvaluationResult:
    return EvaluationResult(
        judgment=make_judgment(decision),
        binding=EvaluatorBinding(
            package_digest=canonical_digest(package),
            evaluator_call_id=call.call_id,
            evaluator_input_digest=call.input_digest,
        ),
    )


def make_submission(condition: Condition, case_id: str, suffix: str) -> ConditionSubmission:
    run_id = f"run_{suffix}"
    brief_digest = TEST_DIGEST if condition in {Condition.B, Condition.C} else None
    package = make_package(f"blind_{suffix}") if condition in {Condition.B, Condition.C} else None
    creator_call = make_model_call(run_id, f"{suffix}_creator", "c_creator") if condition is Condition.C else None
    evaluator_call = make_evaluator_call(run_id, f"{suffix}_evaluator") if condition is Condition.C else None
    evaluation = (
        make_bound_evaluation(package, evaluator_call)
        if condition is Condition.C and package is not None and evaluator_call is not None
        else None
    )
    normalized = NormalizedSubmission(
        decision=NormalizedDecision.PROCEED_CANDIDATE,
        spoken_script=package.script.spoken_script if package is not None else f"Blind candidate script {suffix}.",
    )
    trace = RunTrace(
        run_id=run_id,
        experiment_version="development_v1",
        manifest_version="manifest_v1",
        case_id=case_id,
        condition=condition,
        case_brief_digest=brief_digest,
        input_surface_digest=TEST_DIGEST,
        calls=(creator_call, evaluator_call) if creator_call is not None and evaluator_call is not None else (),
        substantive_revisions=0,
        max_substantive_revisions=0 if condition is Condition.A else 2,
        max_model_calls=7,
        max_total_tokens=20_000,
        max_total_latency_ms=60_000,
        max_cost=Decimal(5),
        budget_currency="USD",
        actual_usage=ResourceUsage(),
        terminal_decision=normalized.decision,
        started_at=FIXED_TIME,
        completed_at=FIXED_TIME,
    )
    return ConditionSubmission(
        run_id=run_id,
        case_id=case_id,
        condition=condition,
        case_brief_digest=brief_digest,
        first_pass_package=package,
        final_package=package,
        evaluator_result=evaluation,
        c_history=(
            CExecutionHistory(
                packages=(package,),
                evaluations=(evaluation,),
                terminal_state=CTerminalState.EVALUATOR_DECISION,
            )
            if condition is Condition.C and package is not None and evaluation is not None
            else None
        ),
        normalized=normalized,
        trace=trace,
    )
