import math

import pytest
from langflow.services.database.models.capability import CapabilityMaturity, FrequencyPeriod
from langflow.services.database.models.capability.validation import (
    has_substantive_assessment_data,
    normalize_frequency_value,
    normalize_optional_text,
    normalize_ordered_string_array,
    normalize_required_text,
    validate_assessment_score,
    validate_frequency_pair,
    validate_non_negative_integer,
)


def test_normalize_required_text_trims_and_accepts_maximum_length():
    assert normalize_required_text("  Proposal Builder  ", field_name="name", max_length=120) == "Proposal Builder"
    assert normalize_required_text("x" * 120, field_name="name", max_length=120) == "x" * 120


@pytest.mark.parametrize("value", ["", "   ", None, 42])
def test_normalize_required_text_rejects_blank_or_non_string(value):
    with pytest.raises(ValueError, match="must"):
        normalize_required_text(value, field_name="name", max_length=120)


def test_normalize_required_text_rejects_over_limit():
    with pytest.raises(ValueError, match="at most 120"):
        normalize_required_text("x" * 121, field_name="name", max_length=120)


def test_normalize_optional_text_trims_and_converts_blank_to_null():
    assert normalize_optional_text("  context  ", field_name="description", max_length=2_000) == "context"
    assert normalize_optional_text("   ", field_name="description", max_length=2_000) is None
    assert normalize_optional_text(None, field_name="description", max_length=2_000) is None


def test_normalize_optional_text_accepts_maximum_and_rejects_over_limit():
    assert normalize_optional_text("x" * 2_000, field_name="description", max_length=2_000) == "x" * 2_000
    with pytest.raises(ValueError, match="at most 2000"):
        normalize_optional_text("x" * 2_001, field_name="description", max_length=2_000)


@pytest.mark.parametrize("period", list(FrequencyPeriod))
def test_frequency_periods_have_complete_pair_rules(period):
    if period in {FrequencyPeriod.AD_HOC, FrequencyPeriod.UNKNOWN}:
        validate_frequency_pair(period, None)
    else:
        validate_frequency_pair(period, 0.5)


@pytest.mark.parametrize("value", [0.5, 2.5, 3])
def test_frequency_value_accepts_positive_finite_numbers(value):
    assert normalize_frequency_value(value) == float(value)


@pytest.mark.parametrize("value", [0, -1, -0.5, math.nan, math.inf, -math.inf, True, "2.5"])
def test_frequency_value_rejects_invalid_numbers(value):
    with pytest.raises(ValueError, match="must"):
        normalize_frequency_value(value)


@pytest.mark.parametrize(
    ("period", "value"),
    [
        (None, 1.0),
        (FrequencyPeriod.DAY, None),
        (FrequencyPeriod.WEEK, None),
        (FrequencyPeriod.MONTH, None),
        (FrequencyPeriod.QUARTER, None),
        (FrequencyPeriod.YEAR, None),
        (FrequencyPeriod.AD_HOC, 1.0),
        (FrequencyPeriod.UNKNOWN, 1.0),
    ],
)
def test_frequency_pair_rejects_incoherent_combinations(period, value):
    with pytest.raises(ValueError, match=r"must be null|required"):
        validate_frequency_pair(period, value)


def test_frequency_pair_accepts_unassessed_frequency():
    validate_frequency_pair(None, None)


@pytest.mark.parametrize("value", [None, 0, 1, 180])
def test_non_negative_integer_accepts_valid_effort(value):
    assert validate_non_negative_integer(value, field_name="effort") == value


@pytest.mark.parametrize("value", [-1, 1.5, True, False, "1"])
def test_non_negative_integer_rejects_invalid_effort(value):
    with pytest.raises(ValueError, match="must"):
        validate_non_negative_integer(value, field_name="effort")


@pytest.mark.parametrize("value", [None, 1, 5])
def test_assessment_score_accepts_null_and_scale_endpoints(value):
    assert validate_assessment_score(value, field_name="business_value") == value


@pytest.mark.parametrize("value", [0, 6, -1, 1.5, True, False, "3"])
def test_assessment_score_rejects_out_of_range_or_non_strict_integers(value):
    with pytest.raises(ValueError, match="must"):
        validate_assessment_score(value, field_name="business_value")


def test_ordered_string_array_trims_deduplicates_and_preserves_order():
    assert normalize_ordered_string_array(
        [" Client brief ", "Discovery notes", "Client brief"],
        field_name="inputs",
    ) == ["Client brief", "Discovery notes"]


def test_ordered_string_array_deduplication_is_case_sensitive():
    assert normalize_ordered_string_array(["Brief", "brief", "Brief"], field_name="inputs") == ["Brief", "brief"]


@pytest.mark.parametrize("value", [[""], ["   "]])
def test_ordered_string_array_rejects_empty_entries(value):
    with pytest.raises(ValueError, match="must not be blank"):
        normalize_ordered_string_array(value, field_name="inputs")


def test_ordered_string_array_rejects_long_entries():
    with pytest.raises(ValueError, match="at most 200"):
        normalize_ordered_string_array(["x" * 201], field_name="inputs")


def test_ordered_string_array_rejects_more_than_fifty_raw_entries():
    with pytest.raises(ValueError, match="at most 50"):
        normalize_ordered_string_array(["same"] * 51, field_name="inputs")


@pytest.mark.parametrize("value", [["valid", 3], None, "not-an-array"])
def test_ordered_string_array_rejects_non_strings_and_non_arrays(value):
    with pytest.raises(ValueError, match="must"):
        normalize_ordered_string_array(value, field_name="inputs")


def test_assessment_helper_recognizes_default_unassessed_state():
    payload = {
        "current_maturity": CapabilityMaturity.NOT_ASSESSED,
        "target_maturity": None,
        "human_oversight": None,
        "oversight_notes": None,
        "business_value": None,
        "ai_feasibility": None,
        "ai_execution_risk": None,
        "assessment_notes": None,
    }
    assert has_substantive_assessment_data(payload) is False


@pytest.mark.parametrize(
    "payload",
    [
        {"current_maturity": CapabilityMaturity.MANUAL},
        {"target_maturity": CapabilityMaturity.AI_ASSISTED},
        {"human_oversight": "review_recommended"},
        {"oversight_notes": "Review protects client quality."},
        {"business_value": 4},
        {"ai_feasibility": 3},
        {"ai_execution_risk": 2},
        {"assessment_notes": "Evidence recorded."},
    ],
)
def test_assessment_helper_recognizes_substantive_data(payload):
    assert has_substantive_assessment_data(payload) is True


def test_assessment_helper_recognizes_cleared_assessment():
    cleared = dict.fromkeys(
        (
            "target_maturity",
            "human_oversight",
            "oversight_notes",
            "business_value",
            "ai_feasibility",
            "ai_execution_risk",
            "assessment_notes",
        ),
        None,
    )
    cleared["current_maturity"] = CapabilityMaturity.NOT_ASSESSED
    assert has_substantive_assessment_data(cleared) is False
