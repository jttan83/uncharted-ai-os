from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping

from .constants import (
    ASSESSMENT_BEARING_FIELDS,
    ASSESSMENT_SCORE_MAX,
    ASSESSMENT_SCORE_MIN,
    CALENDAR_FREQUENCY_PERIODS,
    CONTEXT_ENTRIES_MAX_COUNT,
    CONTEXT_ENTRY_MAX_LENGTH,
    CapabilityMaturity,
    FrequencyPeriod,
)


def normalize_required_text(value: Any, *, field_name: str, max_length: int) -> str:
    """Trim and validate a required business text field."""
    if not isinstance(value, str):
        msg = f"{field_name} must be a string"
        raise ValueError(msg)  # noqa: TRY004 - Pydantic validators must surface ValidationError

    normalized = value.strip()
    if not normalized:
        msg = f"{field_name} must not be blank"
        raise ValueError(msg)
    if len(normalized) > max_length:
        msg = f"{field_name} must be at most {max_length} characters"
        raise ValueError(msg)
    return normalized


def normalize_optional_text(value: Any, *, field_name: str, max_length: int) -> str | None:
    """Trim optional business text, converting blank strings to null."""
    if value is None:
        return None
    if not isinstance(value, str):
        msg = f"{field_name} must be a string or null"
        raise ValueError(msg)  # noqa: TRY004 - Pydantic validators must surface ValidationError

    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > max_length:
        msg = f"{field_name} must be at most {max_length} characters"
        raise ValueError(msg)
    return normalized


def normalize_frequency_value(value: Any) -> float | None:
    """Validate an optional JSON number used as a capability cadence."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        msg = "frequency_value must be a number or null"
        raise ValueError(msg)  # noqa: TRY004 - Pydantic validators must surface ValidationError

    try:
        normalized = float(value)
    except OverflowError as exc:
        msg = "frequency_value must be finite"
        raise ValueError(msg) from exc
    if not math.isfinite(normalized):
        msg = "frequency_value must be finite"
        raise ValueError(msg)
    if normalized <= 0:
        msg = "frequency_value must be greater than zero"
        raise ValueError(msg)
    return normalized


def validate_frequency_pair(period: FrequencyPeriod | None, value: float | None) -> None:
    """Validate the coherence of a complete period/value pair."""
    if period is None:
        if value is not None:
            msg = "frequency_value must be null when frequency_period is null"
            raise ValueError(msg)
        return

    if period in CALENDAR_FREQUENCY_PERIODS:
        if value is None:
            msg = f"frequency_value is required when frequency_period is {period.value}"
            raise ValueError(msg)
        return

    if value is not None:
        msg = f"frequency_value must be null when frequency_period is {period.value}"
        raise ValueError(msg)


def validate_non_negative_integer(value: Any, *, field_name: str) -> int | None:
    """Validate a nullable, strict, non-negative integer."""
    if value is None:
        return None
    if type(value) is not int:
        msg = f"{field_name} must be an integer or null"
        raise ValueError(msg)
    if value < 0:
        msg = f"{field_name} must be greater than or equal to zero"
        raise ValueError(msg)
    return value


def validate_assessment_score(value: Any, *, field_name: str) -> int | None:
    """Validate a nullable, strict integer on the directional 1-5 scale."""
    if value is None:
        return None
    if type(value) is not int:
        msg = f"{field_name} must be an integer or null"
        raise ValueError(msg)
    if not ASSESSMENT_SCORE_MIN <= value <= ASSESSMENT_SCORE_MAX:
        msg = f"{field_name} must be between {ASSESSMENT_SCORE_MIN} and {ASSESSMENT_SCORE_MAX}"
        raise ValueError(msg)
    return value


def normalize_ordered_string_array(value: Any, *, field_name: str) -> list[str]:
    """Normalize an ordered array of plain business-language strings."""
    if not isinstance(value, list):
        msg = f"{field_name} must be an array"
        raise ValueError(msg)  # noqa: TRY004 - Pydantic validators must surface ValidationError
    if len(value) > CONTEXT_ENTRIES_MAX_COUNT:
        msg = f"{field_name} must contain at most {CONTEXT_ENTRIES_MAX_COUNT} entries"
        raise ValueError(msg)

    normalized_values: list[str] = []
    seen: set[str] = set()
    for entry in value:
        if not isinstance(entry, str):
            msg = f"every {field_name} entry must be a string"
            raise ValueError(msg)  # noqa: TRY004 - Pydantic validators must surface ValidationError
        normalized = entry.strip()
        if not normalized:
            msg = f"{field_name} entries must not be blank"
            raise ValueError(msg)
        if len(normalized) > CONTEXT_ENTRY_MAX_LENGTH:
            msg = f"{field_name} entries must be at most {CONTEXT_ENTRY_MAX_LENGTH} characters"
            raise ValueError(msg)
        if normalized in seen:
            continue
        seen.add(normalized)
        normalized_values.append(normalized)
    return normalized_values


def has_substantive_assessment_data(payload: Mapping[str, Any]) -> bool:
    """Return whether a normalized effective Capability state is assessed.

    Callers performing a PATCH must first merge supplied fields with the stored
    state. Missing fields are treated as their unassessed defaults here.
    """
    current_maturity = payload.get("current_maturity", CapabilityMaturity.NOT_ASSESSED)
    if current_maturity not in (None, CapabilityMaturity.NOT_ASSESSED, CapabilityMaturity.NOT_ASSESSED.value):
        return True

    return any(payload.get(field_name) is not None for field_name in ASSESSMENT_BEARING_FIELDS - {"current_maturity"})
