from __future__ import annotations

from pathlib import Path

import pytest

from scripts.uncharted_ai_os.editorial_eval.canonical import canonical_digest
from scripts.uncharted_ai_os.editorial_eval.cli import build_parser, main
from scripts.uncharted_ai_os.editorial_eval.contracts import (
    Claim,
    ClaimDecision,
    ClaimMap,
    ClaimType,
    VerificationStatus,
)
from scripts.uncharted_ai_os.editorial_eval.validation import (
    validate_editorial_package,
    validate_evaluation_binding,
)

from .conftest import make_evaluation


def test_claim_map_evidence_rules_are_deterministic(case_brief, editorial_package) -> None:
    claim_map = ClaimMap(
        artifact_version="claims_invalid",
        no_material_claims=False,
        claims=(
            Claim(
                claim_id="claim_one",
                passage="A factual claim.",
                claim_type=ClaimType.FACTUAL,
                verification_status=VerificationStatus.VERIFIED,
                decision=ClaimDecision.RETAIN,
            ),
            Claim(
                claim_id="claim_two",
                passage="An unsupported factual claim.",
                claim_type=ClaimType.FACTUAL,
                verification_status=VerificationStatus.UNVERIFIED,
                decision=ClaimDecision.RETAIN,
            ),
        ),
    )
    package = editorial_package.model_copy(update={"claim_map": claim_map})
    validation = validate_editorial_package(package, case_brief)
    assert validation.valid is False
    assert set(validation.issue_codes) == {
        "unverified_factual_claim_retained",
        "verified_factual_claim_missing_evidence",
    }


def test_evaluator_result_is_bound_to_exact_package(case_brief, editorial_package) -> None:
    evaluation = make_evaluation(editorial_package)
    changed = editorial_package.model_copy(update={"package_version": "package_changed"})
    with pytest.raises(ValueError, match="digest"):
        validate_evaluation_binding(evaluation, changed, case_brief)


def test_cli_parser_preserves_inspection_commands() -> None:
    parser = build_parser()
    parsed = parser.parse_args(["validate-case", "case.json"])
    assert parsed.command == "validate-case"
    assert parsed.path == Path("case.json")


def test_cli_validates_case_without_printing_content(tmp_path: Path, case_brief, capsys) -> None:
    path = tmp_path / "case.json"
    path.write_text(case_brief.model_dump_json(), encoding="utf-8")
    assert main(["validate-case", str(path)]) == 0
    output = capsys.readouterr().out
    assert canonical_digest(case_brief) in output
    assert case_brief.content_job.objective not in output
