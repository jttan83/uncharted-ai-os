"""Development-only offline rehearsal composition."""

from __future__ import annotations

import json
import re
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import TypeAdapter

from .blinding import RevealCustodian, balanced_position_assignments, build_blind_bundle, condition_execution_order
from .canonical import canonical_digest
from .contracts import BlindReviewBundle, CaseBrief, Condition, ConditionSubmission, DatasetClass, FailureDiagnostics
from .security import assert_credential_free
from .workflows import ConditionAWorkflow, ConditionBWorkflow, ConditionCWorkflow, run_comparable_bc

if TYPE_CHECKING:
    from .storage import PrivateExperimentStorage

_FIXTURE_PATH = Path(__file__).with_name("fixtures") / "development_cases.json"
_DEVELOPMENT_SUBMISSION_COUNT = 3
_MAX_DIAGNOSTIC_MESSAGE_LENGTH = 240


@dataclass(frozen=True)
class DevelopmentWorkflows:
    condition_a: ConditionAWorkflow
    condition_b: ConditionBWorkflow
    condition_c: ConditionCWorkflow

    def __post_init__(self) -> None:
        expected = self.condition_a.runtime_config
        if self.condition_b.runtime_config != expected or self.condition_c.runtime_config != expected:
            msg = "A, B, and C workflows must share one validated runtime configuration"
            raise ValueError(msg)


def load_development_cases(path: Path = _FIXTURE_PATH) -> tuple[CaseBrief, ...]:
    """Load fixtures only when every case is explicitly contaminated development data."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        msg = "development case fixture must be a JSON list"
        raise TypeError(msg)
    cases = TypeAdapter(tuple[CaseBrief, ...]).validate_json(path.read_bytes())
    if not cases or any(case.dataset_class is not DatasetClass.DEVELOPMENT for case in cases):
        msg = "rehearsal accepts development cases only"
        raise ValueError(msg)
    return cases


def derive_ecological_input(brief: CaseBrief) -> str:
    """Frozen-candidate deterministic A-input rule for development rehearsal."""
    lines = [
        "Create a concise talking-head Instagram Reel for Jentz.",
        f"Topic/objective: {brief.content_job.objective}",
        f"Audience: {brief.content_job.target_audience}",
    ]
    if brief.insight.value:
        lines.append(f"Core observation: {brief.insight.value}")
    if brief.point_of_view.value:
        lines.append(f"Point of view: {brief.point_of_view.value}")
    lines.append("Do not publish it; return a candidate or explain why development should stop.")
    return "\n".join(lines)


def run_development_case(
    brief: CaseBrief,
    workflows: DevelopmentWorkflows,
) -> tuple[ConditionSubmission, ConditionSubmission, ConditionSubmission]:
    """Execute one complete A/B/C rehearsal with no provider-specific behavior."""
    if brief.dataset_class is not DatasetClass.DEVELOPMENT:
        msg = "only development cases may use the rehearsal runner"
        raise ValueError(msg)
    submission_a = workflows.condition_a.run(
        case_id=brief.case_id,
        ecological_input=derive_ecological_input(brief),
    )
    submission_b, submission_c = run_comparable_bc(
        brief_for_b=brief,
        brief_for_c=brief,
        condition_b=workflows.condition_b,
        condition_c=workflows.condition_c,
    )
    return submission_a, submission_b, submission_c


def build_development_blind_bundle(
    submissions: tuple[ConditionSubmission, ...],
    *,
    secret_seed: bytes,
    reveal_custodian: RevealCustodian,
    case: CaseBrief | None = None,
    bundle_label: str = "contaminated_development_rehearsal",
) -> BlindReviewBundle:
    """Return only the blind view; the custodian separately seals the reveal map."""
    case_ids = sorted({submission.case_id for submission in submissions})
    if len(case_ids) == 1:
        if case is None:
            msg = "single-case development blinding requires the explicit CaseBrief"
            raise ValueError(msg)
        single_case_label = (
            "single_case_contaminated_development_rehearsal"
            if bundle_label == "contaminated_development_rehearsal"
            else bundle_label
        )
        return build_single_case_development_blind_bundle(
            case,
            submissions,
            secret_seed=secret_seed,
            reveal_custodian=reveal_custodian,
            bundle_label=single_case_label,
        )
    positions = balanced_position_assignments(case_ids, secret_seed)
    return build_blind_bundle(
        submissions,
        secret_seed=secret_seed,
        position_orders=positions,
        bundle_label=bundle_label,
        reveal_custodian=reveal_custodian,
    )


def build_single_case_development_blind_bundle(
    case: CaseBrief,
    submissions: tuple[ConditionSubmission, ...],
    *,
    secret_seed: bytes,
    reveal_custodian: RevealCustodian,
    bundle_label: str = "single_case_contaminated_development_rehearsal",
) -> BlindReviewBundle:
    """Build one-case development blinding without weakening holdout balancing."""
    if case.dataset_class is not DatasetClass.DEVELOPMENT:
        msg = "single-case blinding is DEVELOPMENT ONLY and rejects holdout cases"
        raise ValueError(msg)
    if (
        len(submissions) != _DEVELOPMENT_SUBMISSION_COUNT
        or {submission.case_id for submission in submissions} != {case.case_id}
    ):
        msg = "single-case blinding requires exactly three submissions for the supplied case"
        raise ValueError(msg)
    if {submission.condition for submission in submissions} != set(Condition):
        msg = "single-case blinding requires exactly one A, B, and C submission"
        raise ValueError(msg)
    # This is a seeded permutation, not a cross-case balance claim.
    positions = {case.case_id: condition_execution_order(case.case_id, secret_seed)}
    return build_blind_bundle(
        submissions,
        secret_seed=secret_seed,
        position_orders=positions,
        bundle_label=bundle_label,
        reveal_custodian=reveal_custodian,
    )


def persist_development_execution(
    storage: PrivateExperimentStorage,
    case: CaseBrief,
    submissions: tuple[ConditionSubmission, ...],
    *,
    review_mode: str = "development",
) -> Path:
    """Persist bounded execution evidence before any presentation work."""
    if case.dataset_class is not DatasetClass.DEVELOPMENT:
        msg = "development execution evidence cannot persist a holdout case"
        raise ValueError(msg)
    if (
        len(submissions) != _DEVELOPMENT_SUBMISSION_COUNT
        or {submission.case_id for submission in submissions} != {case.case_id}
    ):
        msg = "execution evidence requires exactly A/B/C submissions for the case"
        raise ValueError(msg)
    payload = {
        "case_id": case.case_id,
        "dataset_class": case.dataset_class.value,
        "contamination_labels": list(case.contamination_labels),
        "review_mode": review_mode,
        "case_brief_digest": canonical_digest(case),
        "condition_submissions": [submission.model_dump(mode="json") for submission in submissions],
    }
    return storage.write_json(f"runs/{case.case_id}.json", payload)


def run_development_case_with_persistence(
    brief: CaseBrief,
    workflows: DevelopmentWorkflows,
    storage: PrivateExperimentStorage,
    *,
    review_mode: str = "development",
) -> tuple[ConditionSubmission, ConditionSubmission, ConditionSubmission]:
    """Execute A/B/C, then persist evidence before any bundle/presentation work."""
    submissions = run_development_case(brief, workflows)
    effective_mode = review_mode
    if review_mode == "development" and len({submission.case_id for submission in submissions}) == 1:
        effective_mode = "single_case_development"
    persist_development_execution(storage, brief, submissions, review_mode=effective_mode)
    return submissions


def persist_development_blind_bundle(
    storage: PrivateExperimentStorage,
    case: CaseBrief,
    bundle: BlindReviewBundle,
    *,
    review_mode: str = "development",
) -> Path:
    """Persist blind material after construction without persisting its reveal mapping."""
    if case.dataset_class is not DatasetClass.DEVELOPMENT:
        msg = "development blind material cannot persist a holdout case"
        raise ValueError(msg)
    if any(candidate.case_id != case.case_id for candidate in bundle.candidates):
        msg = "blind bundle contains a case different from the supplied development case"
        raise ValueError(msg)
    effective_mode = review_mode
    if review_mode == "development" and len({candidate.case_id for candidate in bundle.candidates}) == 1:
        effective_mode = "single_case_development"
    payload = {
        "case_id": case.case_id,
        "dataset_class": case.dataset_class.value,
        "review_mode": effective_mode,
        "blind_bundle": bundle.model_dump(mode="json"),
    }
    return storage.write_json(f"blind/{case.case_id}.json", payload)


def persist_development_failure(
    storage: PrivateExperimentStorage,
    case_id: str,
    *,
    stage: str,
    failure_type: str,
    safe_message: str,
    diagnostics: FailureDiagnostics | None = None,
) -> Path:
    """Record a safe downstream failure without replacing execution evidence."""
    assert_credential_free({"failure_type": failure_type, "stage": stage, "safe_message": safe_message})
    return storage.write_json(
        f"failures/{case_id}_{stage}.json",
        {
            "case_id": case_id,
            "stage": stage,
            "failure_type": failure_type,
            "safe_message": safe_message,
            "diagnostics": diagnostics.model_dump(mode="json") if diagnostics is not None else None,
        },
    )


def presentation_failure_diagnostics(
    exc: BaseException,
    *,
    stage: str = "presentation",
    object_type: str | None = None,
    expected_type: str | None = None,
    actual_type: str | None = None,
) -> FailureDiagnostics:
    """Extract a safe local traceback location without retaining locals/content."""
    frame = traceback.extract_tb(exc.__traceback__)[-1] if exc.__traceback__ is not None else None
    module_path = None
    if frame is not None:
        path = Path(frame.filename)
        try:
            module_path = path.resolve().relative_to(Path.cwd().resolve()).as_posix()
        except ValueError:
            module_path = path.name
    message = str(exc).replace("\n", " ").strip()
    message = re.sub(r"https?://\S+", "<url>", message, flags=re.IGNORECASE)
    message = re.sub(
        r"(?:api[_-]?key|authorization|bearer|token|secret|password|mapping|candidate)\s*[=:]\s*\S+",
        "<redacted>",
        message,
        flags=re.IGNORECASE,
    )
    if not message or len(message) > _MAX_DIAGNOSTIC_MESSAGE_LENGTH:
        message = f"{type(exc).__name__} during {stage}."
    return FailureDiagnostics(
        exception_class=type(exc).__name__,
        exception_module=type(exc).__module__,
        stage=stage,  # type: ignore[arg-type]
        diagnostic_message=message,
        module_path=module_path,
        function_name=frame.name if frame is not None else None,
        line_number=frame.lineno if frame is not None else None,
        object_type=object_type,
        expected_type=expected_type,
        actual_type=actual_type,
    )
