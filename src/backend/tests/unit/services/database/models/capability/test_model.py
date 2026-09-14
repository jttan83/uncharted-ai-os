from __future__ import annotations

from datetime import timedelta
from uuid import UUID, uuid4

import sqlalchemy as sa
from langflow.services.database.models.capability import Capability, CapabilityMaturity, CapabilityStatus
from langflow.services.database.models.flow.model import Flow
from langflow.services.database.models.user.model import User
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.schema import CreateIndex, CreateTable

EXPECTED_COLUMNS = {
    "id",
    "name",
    "description",
    "functional_area",
    "parent_capability_id",
    "status",
    "user_id",
    "workspace_id",
    "current_maturity",
    "target_maturity",
    "human_oversight",
    "oversight_notes",
    "frequency_value",
    "frequency_period",
    "baseline_human_effort_minutes_per_run",
    "business_value",
    "ai_feasibility",
    "ai_execution_risk",
    "assessment_notes",
    "assessed_at",
    "assessed_by",
    "inputs",
    "outputs",
    "tools",
    "primary_flow_id",
    "created_at",
    "updated_at",
}

EXPECTED_INDEXES = {
    "ix_capability_user_status": ("user_id", "status"),
    "ix_capability_parent_capability_id": ("parent_capability_id",),
    "ix_capability_primary_flow_id": ("primary_flow_id",),
    "ix_capability_workspace_id": ("workspace_id",),
}

EXPECTED_CHECKS = {
    "ck_capability_status",
    "ck_capability_current_maturity",
    "ck_capability_target_maturity",
    "ck_capability_human_oversight",
    "ck_capability_frequency_period",
    "ck_capability_frequency_coherence",
    "ck_capability_baseline_effort_nonnegative",
    "ck_capability_business_value_range",
    "ck_capability_ai_feasibility_range",
    "ck_capability_ai_execution_risk_range",
}


def _new_capability() -> Capability:
    return Capability(name="Proposal Builder", functional_area="Clients", user_id=uuid4())


def _foreign_key(column_name: str) -> sa.ForeignKey:
    foreign_keys = Capability.__table__.c[column_name].foreign_keys
    assert len(foreign_keys) == 1
    return next(iter(foreign_keys))


def _check_sql(name: str) -> str:
    constraint = next(
        constraint
        for constraint in Capability.__table__.constraints
        if isinstance(constraint, sa.CheckConstraint) and constraint.name == name
    )
    return " ".join(str(constraint.sqltext).lower().split())


def test_table_identity_and_exact_columns() -> None:
    assert Capability.__tablename__ == "capability"
    assert set(Capability.__table__.c.keys()) == EXPECTED_COLUMNS
    assert "primary_flow_link" not in Capability.__table__.c


def test_uuid_primary_key_and_independent_generated_ids() -> None:
    first = _new_capability()
    second = _new_capability()
    id_column = Capability.__table__.c.id

    assert isinstance(first.id, UUID)
    assert isinstance(second.id, UUID)
    assert first.id != second.id
    assert id_column.primary_key is True
    assert isinstance(id_column.type, sa.Uuid)


def test_column_nullability_contract() -> None:
    required_columns = {
        "id",
        "name",
        "functional_area",
        "status",
        "user_id",
        "current_maturity",
        "inputs",
        "outputs",
        "tools",
        "created_at",
        "updated_at",
    }

    actual = {column.name: column.nullable for column in Capability.__table__.c}
    assert actual == {name: name not in required_columns for name in EXPECTED_COLUMNS}


def test_python_defaults() -> None:
    capability = _new_capability()

    assert capability.status is CapabilityStatus.ACTIVE
    assert capability.current_maturity is CapabilityMaturity.NOT_ASSESSED
    assert capability.workspace_id is None
    assert capability.parent_capability_id is None
    assert capability.target_maturity is None
    assert capability.human_oversight is None
    assert capability.oversight_notes is None
    assert capability.frequency_value is None
    assert capability.frequency_period is None
    assert capability.baseline_human_effort_minutes_per_run is None
    assert capability.business_value is None
    assert capability.ai_feasibility is None
    assert capability.ai_execution_risk is None
    assert capability.assessment_notes is None
    assert capability.assessed_at is None
    assert capability.assessed_by is None
    assert capability.primary_flow_id is None
    assert capability.inputs == []
    assert capability.outputs == []
    assert capability.tools == []
    assert capability.created_at.utcoffset() == timedelta(0)
    assert capability.updated_at.utcoffset() == timedelta(0)


def test_collection_defaults_are_independent() -> None:
    first = _new_capability()
    second = _new_capability()

    first.inputs.append("Client brief")
    first.outputs.append("Proposal")
    first.tools.append("CRM")

    assert second.inputs == []
    assert second.outputs == []
    assert second.tools == []


def test_column_types() -> None:
    columns = Capability.__table__.c

    assert isinstance(columns.name.type, sa.String)
    assert columns.name.type.length == 120
    assert isinstance(columns.functional_area.type, sa.String)
    assert columns.functional_area.type.length == 120
    assert isinstance(columns.description.type, sa.Text)
    assert isinstance(columns.oversight_notes.type, sa.Text)
    assert isinstance(columns.assessment_notes.type, sa.Text)
    assert isinstance(columns.frequency_value.type, sa.Float)
    assert isinstance(columns.baseline_human_effort_minutes_per_run.type, sa.Integer)
    assert isinstance(columns.business_value.type, sa.Integer)
    assert isinstance(columns.ai_feasibility.type, sa.Integer)
    assert isinstance(columns.ai_execution_risk.type, sa.Integer)
    assert columns.assessed_at.type.timezone is True
    assert columns.created_at.type.timezone is True
    assert columns.updated_at.type.timezone is True

    for column_name in ("inputs", "outputs", "tools"):
        column_type = columns[column_name].type
        assert column_type.compile(dialect=sqlite.dialect()) == "JSON"
        assert column_type.compile(dialect=postgresql.dialect()) == "JSONB"


def test_enum_like_columns_use_plain_strings() -> None:
    for column_name in (
        "status",
        "current_maturity",
        "target_maturity",
        "human_oversight",
        "frequency_period",
    ):
        column_type = Capability.__table__.c[column_name].type
        assert isinstance(column_type, sa.String)
        assert not isinstance(column_type, sa.Enum)


def test_foreign_key_targets_and_delete_behaviour() -> None:
    assert User.__table__.name == "user"
    assert Flow.__table__.name == "flow"

    expected = {
        "user_id": ("user.id", "CASCADE"),
        "parent_capability_id": ("capability.id", "SET NULL"),
        "assessed_by": ("user.id", "SET NULL"),
        "primary_flow_id": ("flow.id", "SET NULL"),
    }
    for column_name, (target, ondelete) in expected.items():
        foreign_key = _foreign_key(column_name)
        assert foreign_key.target_fullname == target
        assert foreign_key.ondelete == ondelete


def test_exact_indexes_and_column_order_without_duplicates() -> None:
    indexes = {index.name: tuple(column.name for column in index.columns) for index in Capability.__table__.indexes}

    assert indexes == EXPECTED_INDEXES
    assert len(indexes.values()) == len(set(indexes.values()))


def test_exact_check_constraint_names() -> None:
    check_names = {
        constraint.name for constraint in Capability.__table__.constraints if isinstance(constraint, sa.CheckConstraint)
    }
    assert check_names == EXPECTED_CHECKS


def test_allow_list_check_constraints_contain_domain_values() -> None:
    assert all(value in _check_sql("ck_capability_status") for value in ("active", "archived"))
    for constraint_name in ("ck_capability_current_maturity", "ck_capability_target_maturity"):
        assert all(
            value in _check_sql(constraint_name)
            for value in ("not_assessed", "manual", "ai_assisted", "ai_executable", "automated")
        )
    assert all(
        value in _check_sql("ck_capability_human_oversight")
        for value in ("none", "review_recommended", "approval_required", "human_led")
    )
    assert all(
        value in _check_sql("ck_capability_frequency_period")
        for value in ("day", "week", "month", "quarter", "year", "ad_hoc", "unknown")
    )
    assert "target_maturity is null" in _check_sql("ck_capability_target_maturity")
    assert "human_oversight is null" in _check_sql("ck_capability_human_oversight")
    assert "frequency_period is null" in _check_sql("ck_capability_frequency_period")


def test_frequency_and_numeric_check_constraints() -> None:
    frequency_sql = _check_sql("ck_capability_frequency_coherence")
    assert "frequency_period is null and frequency_value is null" in frequency_sql
    assert all(value in frequency_sql for value in ("ad_hoc", "unknown", "day", "week", "month", "quarter", "year"))
    assert "frequency_value is not null" in frequency_sql
    assert "frequency_value > 0" in frequency_sql

    assert ">= 0" in _check_sql("ck_capability_baseline_effort_nonnegative")
    for constraint_name in (
        "ck_capability_business_value_range",
        "ck_capability_ai_feasibility_range",
        "ck_capability_ai_execution_risk_range",
    ):
        constraint_sql = _check_sql(constraint_name)
        assert "is null" in constraint_sql
        assert "between 1 and 5" in constraint_sql


def test_server_defaults_and_no_implicit_updated_at_onupdate() -> None:
    columns = Capability.__table__.c

    assert str(columns.status.server_default.arg) == "'active'"
    assert str(columns.current_maturity.server_default.arg) == "'not_assessed'"
    for column_name in ("inputs", "outputs", "tools"):
        assert str(columns[column_name].server_default.arg) == "'[]'"
    assert columns.created_at.server_default is not None
    assert columns.updated_at.server_default is not None
    assert columns.updated_at.default is None
    assert columns.updated_at.onupdate is None
    assert columns.updated_at.server_onupdate is None


def test_domain_separation_and_no_relationships() -> None:
    forbidden_fields = {
        "primary_flow_link",
        "opportunity_score",
        "organisation_id",
        "tenant_id",
        "capability_map_id",
        "capability_map",
    }

    assert forbidden_fields.isdisjoint(Capability.model_fields)
    assert forbidden_fields.isdisjoint(Capability.__table__.c.keys())
    assert list(Capability.__mapper__.relationships) == []


def _compiled_index_sql(dialect: sa.engine.Dialect) -> dict[str, str]:
    return {index.name: str(CreateIndex(index).compile(dialect=dialect)) for index in Capability.__table__.indexes}


def test_sqlite_ddl_compiles_with_json_checks_indexes_and_delete_actions() -> None:
    ddl = str(CreateTable(Capability.__table__).compile(dialect=sqlite.dialect()))
    index_ddl = _compiled_index_sql(sqlite.dialect())

    assert "CREATE TABLE capability" in ddl
    assert ddl.count(" JSON") == 3
    assert "JSONB" not in ddl
    assert all(f"CONSTRAINT {name}" in ddl for name in EXPECTED_CHECKS)
    assert set(index_ddl) == set(EXPECTED_INDEXES)
    assert ddl.count("ON DELETE SET NULL") == 3
    assert ddl.count("ON DELETE CASCADE") == 1


def test_postgresql_ddl_compiles_with_jsonb_checks_indexes_and_delete_actions() -> None:
    ddl = str(CreateTable(Capability.__table__).compile(dialect=postgresql.dialect()))
    index_ddl = _compiled_index_sql(postgresql.dialect())

    assert "CREATE TABLE capability" in ddl
    assert ddl.count(" JSONB") == 3
    assert "CREATE TYPE" not in ddl.upper()
    assert all(f"CONSTRAINT {name}" in ddl for name in EXPECTED_CHECKS)
    assert set(index_ddl) == set(EXPECTED_INDEXES)
    assert ddl.count("ON DELETE SET NULL") == 3
    assert ddl.count("ON DELETE CASCADE") == 1
