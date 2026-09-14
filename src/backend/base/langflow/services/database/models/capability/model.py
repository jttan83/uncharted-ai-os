from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy import JSON, CheckConstraint, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from .constants import (
    FUNCTIONAL_AREA_MAX_LENGTH,
    NAME_MAX_LENGTH,
    CapabilityMaturity,
    CapabilityStatus,
    FrequencyPeriod,
    HumanOversight,
)

if TYPE_CHECKING:
    from enum import Enum

# JSONB on PostgreSQL and JSON on SQLite, matching the repository's
# cross-dialect persistence convention.
JsonVariant = JSON().with_variant(JSONB(), "postgresql")


def _enum_values_sql(enum_type: type[Enum]) -> str:
    return ", ".join(f"'{member.value}'" for member in enum_type)


_STATUS_VALUES_SQL = _enum_values_sql(CapabilityStatus)
_MATURITY_VALUES_SQL = _enum_values_sql(CapabilityMaturity)
_HUMAN_OVERSIGHT_VALUES_SQL = _enum_values_sql(HumanOversight)
_FREQUENCY_PERIOD_VALUES_SQL = _enum_values_sql(FrequencyPeriod)
_CALENDAR_FREQUENCY_VALUES_SQL = ", ".join(
    f"'{period.value}'"
    for period in (
        FrequencyPeriod.DAY,
        FrequencyPeriod.WEEK,
        FrequencyPeriod.MONTH,
        FrequencyPeriod.QUARTER,
        FrequencyPeriod.YEAR,
    )
)
_NON_CALENDAR_FREQUENCY_VALUES_SQL = ", ".join(
    f"'{period.value}'" for period in (FrequencyPeriod.AD_HOC, FrequencyPeriod.UNKNOWN)
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Capability(SQLModel, table=True):  # type: ignore[call-arg]
    """Persistence model for an owner-scoped unit of repeatable business work."""

    __tablename__ = "capability"
    __table_args__ = (
        CheckConstraint(f"status IN ({_STATUS_VALUES_SQL})", name="ck_capability_status"),
        CheckConstraint(
            f"current_maturity IN ({_MATURITY_VALUES_SQL})",
            name="ck_capability_current_maturity",
        ),
        CheckConstraint(
            f"target_maturity IS NULL OR target_maturity IN ({_MATURITY_VALUES_SQL})",
            name="ck_capability_target_maturity",
        ),
        CheckConstraint(
            f"human_oversight IS NULL OR human_oversight IN ({_HUMAN_OVERSIGHT_VALUES_SQL})",
            name="ck_capability_human_oversight",
        ),
        CheckConstraint(
            f"frequency_period IS NULL OR frequency_period IN ({_FREQUENCY_PERIOD_VALUES_SQL})",
            name="ck_capability_frequency_period",
        ),
        CheckConstraint(
            "(frequency_period IS NULL AND frequency_value IS NULL) "
            f"OR (frequency_period IN ({_NON_CALENDAR_FREQUENCY_VALUES_SQL}) AND frequency_value IS NULL) "
            f"OR (frequency_period IN ({_CALENDAR_FREQUENCY_VALUES_SQL}) "
            "AND frequency_value IS NOT NULL AND frequency_value > 0)",
            name="ck_capability_frequency_coherence",
        ),
        CheckConstraint(
            "baseline_human_effort_minutes_per_run IS NULL OR baseline_human_effort_minutes_per_run >= 0",
            name="ck_capability_baseline_effort_nonnegative",
        ),
        CheckConstraint(
            "business_value IS NULL OR business_value BETWEEN 1 AND 5",
            name="ck_capability_business_value_range",
        ),
        CheckConstraint(
            "ai_feasibility IS NULL OR ai_feasibility BETWEEN 1 AND 5",
            name="ck_capability_ai_feasibility_range",
        ),
        CheckConstraint(
            "ai_execution_risk IS NULL OR ai_execution_risk BETWEEN 1 AND 5",
            name="ck_capability_ai_execution_risk_range",
        ),
        Index("ix_capability_user_status", "user_id", "status"),
        Index("ix_capability_parent_capability_id", "parent_capability_id"),
        Index("ix_capability_primary_flow_id", "primary_flow_id"),
        Index("ix_capability_workspace_id", "workspace_id"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(sa_column=Column(String(NAME_MAX_LENGTH), nullable=False))
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    functional_area: str = Field(sa_column=Column(String(FUNCTIONAL_AREA_MAX_LENGTH), nullable=False))
    parent_capability_id: UUID | None = Field(
        default=None,
        sa_column=Column(sa.Uuid(), ForeignKey("capability.id", ondelete="SET NULL"), nullable=True),
    )
    status: CapabilityStatus = Field(
        default=CapabilityStatus.ACTIVE,
        sa_column=Column(String(32), nullable=False, server_default=sa.text("'active'")),
    )

    user_id: UUID = Field(
        sa_column=Column(sa.Uuid(), ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
    )
    workspace_id: UUID | None = Field(default=None, sa_column=Column(sa.Uuid(), nullable=True))

    current_maturity: CapabilityMaturity = Field(
        default=CapabilityMaturity.NOT_ASSESSED,
        sa_column=Column(String(32), nullable=False, server_default=sa.text("'not_assessed'")),
    )
    target_maturity: CapabilityMaturity | None = Field(
        default=None,
        sa_column=Column(String(32), nullable=True),
    )
    human_oversight: HumanOversight | None = Field(
        default=None,
        sa_column=Column(String(32), nullable=True),
    )
    oversight_notes: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

    frequency_value: float | None = Field(default=None, sa_column=Column(Float, nullable=True))
    frequency_period: FrequencyPeriod | None = Field(
        default=None,
        sa_column=Column(String(32), nullable=True),
    )
    baseline_human_effort_minutes_per_run: int | None = Field(
        default=None,
        sa_column=Column(Integer, nullable=True),
    )

    business_value: int | None = Field(default=None, sa_column=Column(Integer, nullable=True))
    ai_feasibility: int | None = Field(default=None, sa_column=Column(Integer, nullable=True))
    ai_execution_risk: int | None = Field(default=None, sa_column=Column(Integer, nullable=True))
    assessment_notes: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    assessed_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    assessed_by: UUID | None = Field(
        default=None,
        sa_column=Column(sa.Uuid(), ForeignKey("user.id", ondelete="SET NULL"), nullable=True),
    )

    inputs: list[str] = Field(
        default_factory=list,
        sa_column=Column(JsonVariant, nullable=False, server_default=sa.text("'[]'")),
    )
    outputs: list[str] = Field(
        default_factory=list,
        sa_column=Column(JsonVariant, nullable=False, server_default=sa.text("'[]'")),
    )
    tools: list[str] = Field(
        default_factory=list,
        sa_column=Column(JsonVariant, nullable=False, server_default=sa.text("'[]'")),
    )

    primary_flow_id: UUID | None = Field(
        default=None,
        sa_column=Column(sa.Uuid(), ForeignKey("flow.id", ondelete="SET NULL"), nullable=True),
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    updated_at: datetime = Field(
        default_factory=_utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
