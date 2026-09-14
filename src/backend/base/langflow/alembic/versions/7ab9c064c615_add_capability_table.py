"""Add the Uncharted AI OS Capability table.

Revision ID: 7ab9c064c615
Revises: d7e9f1a3b5c8
Create Date: 2026-09-14 19:38:57.762866

Phase: EXPAND
Safe to rollback: YES (drops only the new capability table).
Services compatible: All earlier versions ignore the new table.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from langflow.utils import migration
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

# Keep this cross-dialect type aligned with the Capability SQLModel.
JsonVariant = JSON().with_variant(JSONB(), "postgresql")

revision: str = "7ab9c064c615"  # pragma: allowlist secret
down_revision: str | None = "d7e9f1a3b5c8"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE_NAME = "capability"

INDEXES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ix_capability_user_status", ("user_id", "status")),
    ("ix_capability_parent_capability_id", ("parent_capability_id",)),
    ("ix_capability_primary_flow_id", ("primary_flow_id",)),
    ("ix_capability_workspace_id", ("workspace_id",)),
)


def upgrade() -> None:
    conn = op.get_bind()
    if migration.table_exists(TABLE_NAME, conn):
        return

    op.create_table(
        TABLE_NAME,
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("functional_area", sa.String(length=120), nullable=False),
        sa.Column("parent_capability_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default=sa.text("'active'"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=True),
        sa.Column("current_maturity", sa.String(length=32), server_default=sa.text("'not_assessed'"), nullable=False),
        sa.Column("target_maturity", sa.String(length=32), nullable=True),
        sa.Column("human_oversight", sa.String(length=32), nullable=True),
        sa.Column("oversight_notes", sa.Text(), nullable=True),
        sa.Column("frequency_value", sa.Float(), nullable=True),
        sa.Column("frequency_period", sa.String(length=32), nullable=True),
        sa.Column("baseline_human_effort_minutes_per_run", sa.Integer(), nullable=True),
        sa.Column("business_value", sa.Integer(), nullable=True),
        sa.Column("ai_feasibility", sa.Integer(), nullable=True),
        sa.Column("ai_execution_risk", sa.Integer(), nullable=True),
        sa.Column("assessment_notes", sa.Text(), nullable=True),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assessed_by", sa.Uuid(), nullable=True),
        sa.Column("inputs", JsonVariant, server_default=sa.text("'[]'"), nullable=False),
        sa.Column("outputs", JsonVariant, server_default=sa.text("'[]'"), nullable=False),
        sa.Column("tools", JsonVariant, server_default=sa.text("'[]'"), nullable=False),
        sa.Column("primary_flow_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name=op.f("fk_capability_user_id_user"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parent_capability_id"],
            ["capability.id"],
            name=op.f("fk_capability_parent_capability_id_capability"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["assessed_by"],
            ["user.id"],
            name=op.f("fk_capability_assessed_by_user"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["primary_flow_id"],
            ["flow.id"],
            name=op.f("fk_capability_primary_flow_id_flow"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_capability")),
        sa.CheckConstraint(
            "status IN ('active', 'archived')",
            name=op.f("ck_capability_status"),
        ),
        sa.CheckConstraint(
            "current_maturity IN ('not_assessed', 'manual', 'ai_assisted', 'ai_executable', 'automated')",
            name=op.f("ck_capability_current_maturity"),
        ),
        sa.CheckConstraint(
            "target_maturity IS NULL OR "
            "target_maturity IN ('not_assessed', 'manual', 'ai_assisted', 'ai_executable', 'automated')",
            name=op.f("ck_capability_target_maturity"),
        ),
        sa.CheckConstraint(
            "human_oversight IS NULL OR "
            "human_oversight IN ('none', 'review_recommended', 'approval_required', 'human_led')",
            name=op.f("ck_capability_human_oversight"),
        ),
        sa.CheckConstraint(
            "frequency_period IS NULL OR "
            "frequency_period IN ('day', 'week', 'month', 'quarter', 'year', 'ad_hoc', 'unknown')",
            name=op.f("ck_capability_frequency_period"),
        ),
        sa.CheckConstraint(
            "(frequency_period IS NULL AND frequency_value IS NULL) "
            "OR (frequency_period IN ('ad_hoc', 'unknown') AND frequency_value IS NULL) "
            "OR (frequency_period IN ('day', 'week', 'month', 'quarter', 'year') "
            "AND frequency_value IS NOT NULL AND frequency_value > 0)",
            name=op.f("ck_capability_frequency_coherence"),
        ),
        sa.CheckConstraint(
            "baseline_human_effort_minutes_per_run IS NULL OR baseline_human_effort_minutes_per_run >= 0",
            name=op.f("ck_capability_baseline_effort_nonnegative"),
        ),
        sa.CheckConstraint(
            "business_value IS NULL OR business_value BETWEEN 1 AND 5",
            name=op.f("ck_capability_business_value_range"),
        ),
        sa.CheckConstraint(
            "ai_feasibility IS NULL OR ai_feasibility BETWEEN 1 AND 5",
            name=op.f("ck_capability_ai_feasibility_range"),
        ),
        sa.CheckConstraint(
            "ai_execution_risk IS NULL OR ai_execution_risk BETWEEN 1 AND 5",
            name=op.f("ck_capability_ai_execution_risk_range"),
        ),
    )

    for index_name, columns in INDEXES:
        op.create_index(index_name, TABLE_NAME, list(columns), unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    if not migration.table_exists(TABLE_NAME, conn):
        return

    for index_name, _columns in reversed(INDEXES):
        op.drop_index(index_name, table_name=TABLE_NAME)
    op.drop_table(TABLE_NAME)
