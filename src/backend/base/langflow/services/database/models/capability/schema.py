from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID  # noqa: TC003 - SQLModel resolves this annotation at runtime

from pydantic import AwareDatetime, ConfigDict, ValidationInfo, field_validator, model_validator
from sqlmodel import Field, SQLModel

from .constants import (
    ASSESSMENT_NOTES_MAX_LENGTH,
    DESCRIPTION_MAX_LENGTH,
    FUNCTIONAL_AREA_MAX_LENGTH,
    NAME_MAX_LENGTH,
    OVERSIGHT_NOTES_MAX_LENGTH,
    CapabilityMaturity,
    CapabilityStatus,
    FrequencyPeriod,
    HumanOversight,
)
from .validation import (
    normalize_frequency_value,
    normalize_optional_text,
    normalize_ordered_string_array,
    normalize_required_text,
    validate_assessment_score,
    validate_frequency_pair,
    validate_non_negative_integer,
)


class _CapabilityApiSchema(SQLModel):
    model_config = ConfigDict(extra="forbid")


class _CapabilityInputSchema(_CapabilityApiSchema):
    @field_validator("name", "functional_area", mode="before", check_fields=False)
    @classmethod
    def normalize_required_business_text(cls, value: Any, info: ValidationInfo) -> str:
        max_length = NAME_MAX_LENGTH if info.field_name == "name" else FUNCTIONAL_AREA_MAX_LENGTH
        return normalize_required_text(value, field_name=info.field_name, max_length=max_length)

    @field_validator("description", "oversight_notes", "assessment_notes", mode="before", check_fields=False)
    @classmethod
    def normalize_optional_business_text(cls, value: Any, info: ValidationInfo) -> str | None:
        max_lengths = {
            "description": DESCRIPTION_MAX_LENGTH,
            "oversight_notes": OVERSIGHT_NOTES_MAX_LENGTH,
            "assessment_notes": ASSESSMENT_NOTES_MAX_LENGTH,
        }
        return normalize_optional_text(value, field_name=info.field_name, max_length=max_lengths[info.field_name])

    @field_validator("frequency_value", mode="before", check_fields=False)
    @classmethod
    def validate_frequency_value(cls, value: Any) -> float | None:
        return normalize_frequency_value(value)

    @field_validator("baseline_human_effort_minutes_per_run", mode="before", check_fields=False)
    @classmethod
    def validate_human_effort(cls, value: Any, info: ValidationInfo) -> int | None:
        return validate_non_negative_integer(value, field_name=info.field_name)

    @field_validator("business_value", "ai_feasibility", "ai_execution_risk", mode="before", check_fields=False)
    @classmethod
    def validate_score(cls, value: Any, info: ValidationInfo) -> int | None:
        return validate_assessment_score(value, field_name=info.field_name)

    @field_validator("inputs", "outputs", "tools", mode="before", check_fields=False)
    @classmethod
    def normalize_context_array(cls, value: Any, info: ValidationInfo) -> list[str]:
        return normalize_ordered_string_array(value, field_name=info.field_name)


class CapabilityCreate(_CapabilityInputSchema):
    name: str
    functional_area: str
    description: str | None = None
    parent_capability_id: UUID | None = None
    status: CapabilityStatus = CapabilityStatus.ACTIVE
    current_maturity: CapabilityMaturity = CapabilityMaturity.NOT_ASSESSED
    target_maturity: CapabilityMaturity | None = None
    human_oversight: HumanOversight | None = None
    oversight_notes: str | None = None
    frequency_value: float | None = None
    frequency_period: FrequencyPeriod | None = None
    baseline_human_effort_minutes_per_run: int | None = None
    business_value: int | None = None
    ai_feasibility: int | None = None
    ai_execution_risk: int | None = None
    assessment_notes: str | None = None
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    primary_flow_id: UUID | None = None

    @model_validator(mode="after")
    def validate_frequency(self) -> CapabilityCreate:
        validate_frequency_pair(self.frequency_period, self.frequency_value)
        return self


class CapabilityUpdate(_CapabilityInputSchema):
    # A non-null annotation with a null default makes each PATCH field optional
    # while still rejecting an explicitly supplied null. Later CRUD must use
    # model_fields_set or model_dump(exclude_unset=True), never these defaults.
    name: str = Field(default=None)
    functional_area: str = Field(default=None)
    description: str | None = None
    parent_capability_id: UUID | None = None
    status: CapabilityStatus = Field(default=None)
    current_maturity: CapabilityMaturity = Field(default=None)
    target_maturity: CapabilityMaturity | None = None
    human_oversight: HumanOversight | None = None
    oversight_notes: str | None = None
    frequency_value: float | None = None
    frequency_period: FrequencyPeriod | None = None
    baseline_human_effort_minutes_per_run: int | None = None
    business_value: int | None = None
    ai_feasibility: int | None = None
    ai_execution_risk: int | None = None
    assessment_notes: str | None = None
    inputs: list[str] = Field(default=None)
    outputs: list[str] = Field(default=None)
    tools: list[str] = Field(default=None)
    primary_flow_id: UUID | None = None

    @model_validator(mode="after")
    def validate_supplied_frequency_pair(self) -> CapabilityUpdate:
        if {"frequency_period", "frequency_value"} <= self.model_fields_set:
            validate_frequency_pair(self.frequency_period, self.frequency_value)
        return self


class FlowLinkSummary(_CapabilityApiSchema):
    id: UUID
    name: str


class FlowLinkAvailabilityStatus(str, Enum):
    NOT_LINKED = "not_linked"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class FlowLinkAvailability(_CapabilityApiSchema):
    status: FlowLinkAvailabilityStatus
    flow: FlowLinkSummary | None

    @model_validator(mode="after")
    def validate_availability(self) -> FlowLinkAvailability:
        if self.status is FlowLinkAvailabilityStatus.AVAILABLE and self.flow is None:
            msg = "flow is required when status is available"
            raise ValueError(msg)
        if self.status is not FlowLinkAvailabilityStatus.AVAILABLE and self.flow is not None:
            msg = "flow must be null unless status is available"
            raise ValueError(msg)
        return self


class CapabilitySummary(_CapabilityApiSchema):
    id: UUID
    name: str
    functional_area: str
    parent_capability_id: UUID | None
    status: CapabilityStatus
    current_maturity: CapabilityMaturity
    target_maturity: CapabilityMaturity | None
    business_value: int | None
    ai_feasibility: int | None
    ai_execution_risk: int | None
    primary_flow_id: UUID | None
    primary_flow_link: FlowLinkAvailability


class CapabilityRead(CapabilitySummary):
    description: str | None
    user_id: UUID
    workspace_id: UUID | None
    human_oversight: HumanOversight | None
    oversight_notes: str | None
    frequency_value: float | None
    frequency_period: FrequencyPeriod | None
    baseline_human_effort_minutes_per_run: int | None
    assessment_notes: str | None
    assessed_at: AwareDatetime | None
    assessed_by: UUID | None
    inputs: list[str]
    outputs: list[str]
    tools: list[str]
    created_at: AwareDatetime
    updated_at: AwareDatetime


class CapabilityListResponse(_CapabilityApiSchema):
    items: list[CapabilitySummary]
    total: int
    offset: int
    limit: int
