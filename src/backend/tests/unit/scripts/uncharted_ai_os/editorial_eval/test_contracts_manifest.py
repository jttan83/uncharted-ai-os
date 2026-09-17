from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from scripts.uncharted_ai_os.editorial_eval.canonical import (
    assert_byte_identical_case_briefs,
    canonical_digest,
    canonical_json_bytes,
)
from scripts.uncharted_ai_os.editorial_eval.contracts import (
    CASE_BRIEF_SCHEMA_VERSION,
    CaseBrief,
    Condition,
    ConditionSubmission,
    ContentJob,
    NormalizedDecision,
    NormalizedSubmission,
    ResourceUsage,
)
from scripts.uncharted_ai_os.editorial_eval.manifest import (
    ConditionBudget,
    ContaminationRecord,
    ExperimentBudgets,
    FreezeManifest,
    FrozenDataGovernance,
    FrozenEvidencePolicy,
    FrozenModelConfig,
    ManifestState,
    OperationalControls,
    RandomizationCommitment,
    create_freeze_receipt,
    protocol_file_digest,
)
from scripts.uncharted_ai_os.editorial_eval.prompt_assets import (
    PromptName,
    all_prompt_digests,
    load_prompt,
    load_prompt_body,
    prompt_digest,
)
from scripts.uncharted_ai_os.editorial_eval.security import CredentialConfigurationError
from scripts.uncharted_ai_os.editorial_eval.workflows import _messages

from .conftest import FIXED_TIME, TEST_DIGEST, make_submission


def make_manifest(**updates) -> FreezeManifest:
    condition_budget = ConditionBudget(
        max_model_calls=7,
        max_substantive_revisions=2,
        max_total_tokens=20_000,
        max_total_latency_ms=60_000,
        max_cost=Decimal(5),
        currency="USD",
    )
    payload = {
        "experiment_id": "editorial_eval",
        "experiment_version": "phase_1f_a_development_v1",
        "protocol_version": "phase-1f-a-v1",
        "protocol_digest": protocol_file_digest(),
        "protocol_commit": "1" * 40,
        "code_commit": "2" * 40,
        "manifest_version": "manifest_v1",
        "created_at": FIXED_TIME,
        "prompt_hashes": all_prompt_digests(),
        "config_hashes": {
            "case_brief_template": TEST_DIGEST,
            "case_eligibility_selection_rules": TEST_DIGEST,
            "blind_envelope": TEST_DIGEST,
            "data_handling_rules": TEST_DIGEST,
            "decision_mapping": TEST_DIGEST,
            "ecological_a_derivation_rule": TEST_DIGEST,
            "go_simplify_stop_rules": TEST_DIGEST,
            "resource_parity_method": TEST_DIGEST,
            "retry_failure_stopping_rules": TEST_DIGEST,
            "review_form": TEST_DIGEST,
            "review_session_policy": TEST_DIGEST,
            "validation_rules": TEST_DIGEST,
        },
        "generator_model": FrozenModelConfig(
            provider="provider",
            model_identifier="generator-v1",
            reasoning="medium",
            temperature=0.2,
            seed_supported=True,
            seed=7,
            timeout_seconds=30,
            max_output_tokens_per_call=2_000,
        ),
        "evaluator_model": FrozenModelConfig(
            provider="provider",
            model_identifier="evaluator-v1",
            reasoning="medium",
            temperature=0.2,
            seed_supported=True,
            seed=7,
            timeout_seconds=30,
            max_output_tokens_per_call=2_000,
        ),
        "budgets": ExperimentBudgets(
            condition_a=condition_budget.model_copy(update={"max_model_calls": 2, "max_substantive_revisions": 0}),
            condition_b=condition_budget,
            condition_c=condition_budget,
            bc_token_tolerance_percent=0,
            max_pilot_cost=Decimal(100),
            currency="USD",
            max_human_review_minutes_per_case=30,
        ),
        "randomization": RandomizationCommitment(
            seed_commitment=TEST_DIGEST,
            seed_custody_rule="Mapping custodian keeps the secret outside review materials.",
            mapping_custodian="Named test custodian",
        ),
        "data_governance": FrozenDataGovernance(
            experiment_operator="Named test operator",
            raw_case_access=("Named test operator",),
            provider_data_use="No provider calls in development tests.",
            retention_days=30,
            deletion_rule="Delete private run data after the governed review window.",
            client_or_third_party_data_permitted=False,
        ),
        "operational_controls": OperationalControls(
            development_case_ids=(
                "case_dev_agreement_alignment",
                "case_dev_tools_before_redesign",
                "case_dev_oversized_workshops",
            ),
            contamination_register=tuple(
                ContaminationRecord(
                    case_id=case_id,
                    topic=case_id,
                    labels=("DEVELOPMENT ONLY", "CONTAMINATED", "NOT HOLDOUT"),
                )
                for case_id in (
                    "case_dev_agreement_alignment",
                    "case_dev_tools_before_redesign",
                    "case_dev_oversized_workshops",
                )
            ),
            contaminated_topic_register_digest=TEST_DIGEST,
            configuration_profile="phase1f-a-dev-v2",
            treatment_source_digests={"A": TEST_DIGEST, "B": TEST_DIGEST, "C": TEST_DIGEST},
            evidence_policy=FrozenEvidencePolicy(),
            evidence_snapshot_digest=TEST_DIGEST,
            permitted_tools=(),
            conditional_fact_check_rule_digest=TEST_DIGEST,
            decision_rule_digest=TEST_DIGEST,
        ),
    }
    payload.update(updates)
    return FreezeManifest(**payload)


def test_contracts_are_strict_and_forbid_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ContentJob(
            primary="authority",
            objective="Objective",
            target_audience="Audience",
            desired_response="Response",
            success_signals=("signal",),
            guardrail_signals=("guardrail",),
            measurement_window="window",
            invented_field=True,
        )


def test_schema_versions_are_explicit_and_reject_unknown(case_brief: CaseBrief) -> None:
    assert case_brief.schema_version == CASE_BRIEF_SCHEMA_VERSION
    payload = case_brief.model_dump(mode="json")
    payload["schema_version"] = "case-brief-v999"
    with pytest.raises(ValidationError):
        CaseBrief.model_validate_json(json.dumps(payload))


def test_canonical_serialization_and_hash_are_stable(case_brief: CaseBrief) -> None:
    first = canonical_json_bytes(case_brief)
    second = canonical_json_bytes(json.loads(first))
    assert first == second
    assert canonical_digest(case_brief) == canonical_digest(case_brief.model_dump(mode="json"))


def test_case_brief_byte_equality_and_digest_enforcement(case_brief: CaseBrief) -> None:
    clone = CaseBrief.model_validate_json(case_brief.model_dump_json())
    digest = canonical_digest(case_brief)
    assert assert_byte_identical_case_briefs(case_brief, clone, digest) == digest
    changed = clone.model_copy(update={"portfolio_context": "Different context"})
    with pytest.raises(ValueError, match="canonical bytes differ"):
        assert_byte_identical_case_briefs(case_brief, changed)
    with pytest.raises(ValueError, match="committed digest"):
        assert_byte_identical_case_briefs(case_brief, clone, TEST_DIGEST)


def test_manifest_draft_can_remain_incomplete() -> None:
    draft = FreezeManifest(created_at=FIXED_TIME)
    assert draft.state is ManifestState.DRAFT
    assert draft.freeze_digest is None


def test_manifest_freeze_validates_and_detects_tampering() -> None:
    frozen = make_manifest().freeze(timestamp=datetime(2026, 1, 3, tzinfo=timezone.utc))
    assert frozen.state is ManifestState.FROZEN
    assert frozen.freeze_digest is not None
    reloaded = FreezeManifest.model_validate_json(frozen.model_dump_json())
    assert reloaded == frozen
    tampered = frozen.model_dump(mode="json")
    tampered["generator_model"]["model_identifier"] = "different-model"
    with pytest.raises(ValidationError, match="freeze digest"):
        FreezeManifest.model_validate_json(json.dumps(tampered))


def test_frozen_manifest_rejects_missing_values_placeholders_and_incomplete_budgets() -> None:
    with pytest.raises(ValueError, match="incomplete"):
        FreezeManifest(created_at=FIXED_TIME).freeze(timestamp=FIXED_TIME)
    with pytest.raises(ValueError, match="placeholder"):
        make_manifest(
            generator_model=FrozenModelConfig(
                provider="provider",
                model_identifier="TBD",
                reasoning="medium",
                temperature=0.2,
                seed_supported=True,
                seed=7,
                timeout_seconds=30,
                max_output_tokens_per_call=2_000,
            )
        ).freeze(timestamp=FIXED_TIME)
    with pytest.raises(ValidationError):
        ExperimentBudgets.model_validate(
            {
                "condition_a": make_manifest().budgets.condition_a,
                "condition_b": make_manifest().budgets.condition_b,
            }
        )


def test_manifest_enforces_a_structure_and_bc_resource_comparability() -> None:
    manifest = make_manifest()
    assert manifest.budgets is not None
    invalid_a = manifest.budgets.condition_a.model_copy(update={"max_substantive_revisions": 1})
    with pytest.raises(ValidationError, match="Condition A"):
        ExperimentBudgets(
            condition_a=invalid_a,
            condition_b=manifest.budgets.condition_b,
            condition_c=manifest.budgets.condition_c,
            bc_token_tolerance_percent=0,
            max_pilot_cost=Decimal(100),
            currency="USD",
            max_human_review_minutes_per_case=30,
        )
    unequal_c = manifest.budgets.condition_c.model_copy(update={"max_model_calls": 8})
    with pytest.raises(ValidationError, match="model-call ceilings"):
        ExperimentBudgets(
            condition_a=manifest.budgets.condition_a,
            condition_b=manifest.budgets.condition_b,
            condition_c=unequal_c,
            bc_token_tolerance_percent=0,
            max_pilot_cost=Decimal(100),
            currency="USD",
            max_human_review_minutes_per_case=30,
        )


def test_manifest_rejects_bad_hashes_protocol_schema_and_seed_commitment() -> None:
    with pytest.raises(ValidationError):
        make_manifest(prompt_hashes={"condition_a": "not-a-hash"})
    with pytest.raises(ValidationError):
        FreezeManifest.model_validate({"schema_version": "wrong", "created_at": FIXED_TIME})
    with pytest.raises(ValidationError):
        make_manifest(protocol_version="phase-1f-a-v2")
    with pytest.raises(ValueError, match="protocol hash"):
        make_manifest(protocol_digest=TEST_DIGEST).freeze(timestamp=FIXED_TIME)
    wrong_prompt_hashes = all_prompt_digests()
    wrong_prompt_hashes["condition_a"] = TEST_DIGEST
    with pytest.raises(ValueError, match="prompt hashes"):
        make_manifest(prompt_hashes=wrong_prompt_hashes).freeze(timestamp=FIXED_TIME)
    with pytest.raises(ValidationError):
        RandomizationCommitment(
            seed_commitment="sha256:1234",
            seed_custody_rule="Separated",
            mapping_custodian="Custodian",
        )


def test_freeze_receipt_is_sanitized_by_allowlist() -> None:
    frozen = make_manifest().freeze(timestamp=FIXED_TIME)
    receipt = create_freeze_receipt(frozen)
    payload = receipt.model_dump(mode="json")
    assert payload["randomization_commitment"] == TEST_DIGEST
    forbidden = {"secret_seed", "credentials", "holdout", "reveal_mapping", "data_governance"}
    assert forbidden.isdisjoint(payload)


def test_model_copy_cannot_bypass_manifest_credential_guard() -> None:
    manifest = make_manifest()
    unsafe_model = manifest.generator_model.model_copy(
        update={"model_identifier": "https://user:credential-value@example.invalid/model"}
    )
    unsafe_manifest = manifest.model_copy(update={"generator_model": unsafe_model})
    with pytest.raises(CredentialConfigurationError, match="credential-bearing"):
        unsafe_manifest.freeze(timestamp=FIXED_TIME)


def test_neutral_decisions_enforce_candidate_surface() -> None:
    candidate = NormalizedSubmission(
        decision=NormalizedDecision.PROCEED_CANDIDATE,
        spoken_script="A usable candidate.",
    )
    assert candidate.decision.value == "PROCEED / CANDIDATE"
    with pytest.raises(ValidationError):
        NormalizedSubmission(decision=NormalizedDecision.REVISE_BRIEF, spoken_script="Leaked script")
    with pytest.raises(ValidationError):
        NormalizedSubmission(decision=NormalizedDecision.EVIDENCE_REQUIRED)


def test_resource_usage_preserves_unknown_values() -> None:
    usage = ResourceUsage()
    assert usage.input_tokens is None
    assert usage.output_tokens is None
    assert usage.monetary_cost is None
    with pytest.raises(ValidationError):
        ResourceUsage(input_tokens=-1)
    with pytest.raises(ValidationError):
        ResourceUsage(monetary_cost=Decimal(1))


def test_prompt_frontmatter_is_hashed_but_never_model_visible() -> None:
    for name in PromptName:
        raw = load_prompt(name)
        body = load_prompt_body(name)
        assert raw.startswith("---\n")
        assert "prompt_version:" in raw
        assert not body.startswith("---")
        assert "prompt_version:" not in body
        assert prompt_digest(name).startswith("sha256:")


def test_b_and_c_receive_the_same_canonical_standard_bytes_and_no_condition_labels() -> None:
    standard = load_prompt_body(PromptName.CANONICAL_STANDARD)
    names = (
        PromptName.CONDITION_B,
        PromptName.CONDITION_B_SELF_REVIEW,
        PromptName.CONDITION_C_CREATOR,
        PromptName.CONDITION_C_EVALUATOR,
        PromptName.CONDITION_C_REVISION,
    )
    systems = [_messages(name, "case input")[0].content for name in names]
    assert all(system.count(standard) == 1 for system in systems)
    assert "Strong:" in standard
    assert "Critical Problem:" in standard
    assert "Not Assessable:" in standard
    assert "True hard failures" in standard
    assert "Ready for Human Approval requires" in standard
    all_model_systems = [*systems, _messages(PromptName.CONDITION_A, "ecological input")[0].content]
    for system in all_model_systems:
        lowered = system.casefold()
        assert re.search(r"\bcondition\s+[abc]\b", lowered) is None
        assert "strong comparator" not in lowered
        assert "prompt_version:" not in system


def test_canonical_standard_is_versioned_without_copying_canonical_documents() -> None:
    standard = load_prompt_body(PromptName.CANONICAL_STANDARD)
    assert "canonical_editorial_standard" in all_prompt_digests()
    assert len(standard.split()) < 900


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda payload: payload.update({"run_id": "run_different"}), "identities must match"),
        (
            lambda payload: payload["normalized"].update(
                {
                    "decision": NormalizedDecision.HUMAN_JUDGMENT_REQUIRED,
                    "spoken_script": None,
                    "explanation": "A human decision is required.",
                    "next_action": "Escalate to the authorized human.",
                }
            ),
            "terminal decisions must match",
        ),
        (
            lambda payload: payload["normalized"].update({"spoken_script": "A mismatched candidate."}),
            "candidate text must match",
        ),
    ],
)
def test_condition_submission_enforces_cross_field_consistency(mutation, message) -> None:
    payload = make_submission(Condition.C, "case_01", "consistent").model_dump(mode="python")
    mutation(payload)
    with pytest.raises(ValidationError, match=message):
        ConditionSubmission.model_validate(payload)
