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
    EvidenceItem,
    VerificationStatus,
)
from scripts.uncharted_ai_os.editorial_eval.validation import (
    validate_editorial_package,
    validate_evaluation_binding,
)

from .conftest import make_bound_evaluation, make_evaluator_call


def test_claim_evidence_refs_schema_defines_exact_case_evidence_namespace() -> None:
    description = Claim.model_json_schema()["properties"]["evidence_refs"]["description"]

    assert "CaseBrief.evidence[].evidence_id" in description
    assert "field names, paths, aliases" in description
    assert "evidence_refs must be []" in description


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


def _package_with_evidence_refs(editorial_package, *evidence_refs: str):
    claim_map = ClaimMap(
        artifact_version="claims_evidence_refs",
        no_material_claims=False,
        claims=(
            Claim(
                claim_id="claim_evidence_refs",
                passage="A synthetic opinion used to test reference validation.",
                claim_type=ClaimType.OPINION,
                evidence_refs=evidence_refs,
                verification_status=VerificationStatus.NOT_APPLICABLE,
                decision=ClaimDecision.RETAIN,
            ),
        ),
    )
    return editorial_package.model_copy(update={"claim_map": claim_map})


def test_exact_case_evidence_ids_are_accepted(case_brief, editorial_package) -> None:
    evidence = (
        EvidenceItem(evidence_id="evidence_alpha", description="Synthetic evidence.", source="Offline fixture"),
    )
    brief = case_brief.model_copy(update={"evidence": evidence})
    package = _package_with_evidence_refs(editorial_package, "evidence_alpha")

    validation = validate_editorial_package(package, brief)

    assert validation.valid is True
    assert validation.issue_codes == ()


@pytest.mark.parametrize("invalid_reference", ["evidence_alias", "casebrief_point_of_view"])
def test_invented_or_case_path_evidence_references_are_rejected(
    case_brief, editorial_package, invalid_reference
) -> None:
    evidence = (
        EvidenceItem(evidence_id="evidence_alpha", description="Synthetic evidence.", source="Offline fixture"),
    )
    brief = case_brief.model_copy(update={"evidence": evidence})
    package = _package_with_evidence_refs(editorial_package, invalid_reference)

    validation = validate_editorial_package(package, brief)

    assert validation.valid is False
    assert validation.issue_codes == ("unknown_evidence_reference",)


def test_empty_case_evidence_accepts_only_empty_references(case_brief, editorial_package) -> None:
    valid = validate_editorial_package(_package_with_evidence_refs(editorial_package), case_brief)
    invalid = validate_editorial_package(
        _package_with_evidence_refs(editorial_package, "casebrief_insight"),
        case_brief,
    )

    assert valid.valid is True
    assert valid.issue_codes == ()
    assert invalid.valid is False
    assert invalid.issue_codes == ("unknown_evidence_reference",)


def test_evaluator_result_is_bound_to_exact_package(case_brief, editorial_package) -> None:
    evaluator_call = make_evaluator_call("run_validation_binding")
    evaluation = make_bound_evaluation(editorial_package, evaluator_call)
    changed = editorial_package.model_copy(update={"package_version": "package_changed"})
    with pytest.raises(ValueError, match="digest"):
        validate_evaluation_binding(
            evaluation,
            changed,
            case_brief,
            evaluator_call=evaluator_call,
            run_id="run_validation_binding",
        )


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
