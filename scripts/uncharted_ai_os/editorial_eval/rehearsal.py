"""Development-only offline rehearsal composition."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import TypeAdapter

from .blinding import RevealCustodian, balanced_position_assignments, build_blind_bundle
from .contracts import BlindReviewBundle, CaseBrief, ConditionSubmission, DatasetClass
from .workflows import ConditionAWorkflow, ConditionBWorkflow, ConditionCWorkflow, run_comparable_bc

_FIXTURE_PATH = Path(__file__).with_name("fixtures") / "development_cases.json"


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
    bundle_label: str = "contaminated_development_rehearsal",
) -> BlindReviewBundle:
    """Return only the blind view; the custodian separately seals the reveal map."""
    case_ids = sorted({submission.case_id for submission in submissions})
    positions = balanced_position_assignments(case_ids, secret_seed)
    return build_blind_bundle(
        submissions,
        secret_seed=secret_seed,
        position_orders=positions,
        bundle_label=bundle_label,
        reveal_custodian=reveal_custodian,
    )
