from __future__ import annotations

import importlib
import sys
import tempfile
from io import StringIO
from pathlib import Path
from uuid import uuid4

import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from langflow.alembic.migration_validator import MigrationValidator
from langflow.services.database import models
from langflow.services.database.models.capability import Capability
from langflow.services.database.service import SQLModel
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.engine import make_url

_REVISION = "7ab9c064c615"  # pragma: allowlist secret
_PREVIOUS_REVISION = "d7e9f1a3b5c8"  # pragma: allowlist secret
_SCRIPT_LOCATION = Path(__file__).resolve().parents[3] / "base/langflow/alembic"
_MIGRATION_PATH = _SCRIPT_LOCATION / "versions/7ab9c064c615_add_capability_table.py"


def _make_alembic_config(database_url: str, *, output_buffer: StringIO | None = None) -> Config:
    config = Config(output_buffer=output_buffer)
    config.set_main_option("script_location", str(_SCRIPT_LOCATION))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _sync_sqlite_url(database_url: str) -> str:
    return database_url.replace("sqlite+aiosqlite", "sqlite", 1)


def _normalized_sql(value: object) -> str:
    return "".join(str(value).lower().split())


def _model_foreign_keys() -> dict[tuple[str, ...], tuple[str, tuple[str, ...], str | None]]:
    foreign_keys = {}
    for constraint in Capability.__table__.foreign_key_constraints:
        local_columns = tuple(column.name for column in constraint.columns)
        remote_columns = tuple(element.target_fullname.split(".", 1)[1] for element in constraint.elements)
        remote_table = constraint.elements[0].target_fullname.split(".", 1)[0]
        foreign_keys[local_columns] = (remote_table, remote_columns, constraint.ondelete)
    return foreign_keys


def _model_check_names() -> set[str]:
    return {
        constraint.name
        for constraint in Capability.__table__.constraints
        if isinstance(constraint, sa.CheckConstraint) and constraint.name is not None
    }


def _model_index_names() -> set[str]:
    return {index.name for index in Capability.__table__.indexes if index.name is not None}


def _assert_capability_schema_matches_model(database_url: str) -> None:
    engine = sa.create_engine(_sync_sqlite_url(database_url))
    try:
        with engine.connect() as connection:
            inspector = sa.inspect(connection)
            model_table = Capability.__table__
            reflected_columns = {column["name"]: column for column in inspector.get_columns("capability")}

            assert list(reflected_columns) == list(model_table.c.keys())
            assert len(reflected_columns) == 27
            for model_column in model_table.c:
                reflected = reflected_columns[model_column.name]
                assert reflected["nullable"] is model_column.nullable
                assert reflected["type"].compile(dialect=sqlite.dialect()) == model_column.type.compile(
                    dialect=sqlite.dialect()
                )

            primary_key = inspector.get_pk_constraint("capability")
            assert tuple(primary_key["constrained_columns"]) == tuple(
                column.name for column in model_table.primary_key.columns
            )

            reflected_indexes = {
                index["name"]: tuple(index["column_names"]) for index in inspector.get_indexes("capability")
            }
            model_indexes = {
                index.name: tuple(column.name for column in index.columns) for index in model_table.indexes
            }
            assert reflected_indexes == model_indexes

            reflected_foreign_keys = {
                tuple(foreign_key["constrained_columns"]): (
                    foreign_key["referred_table"],
                    tuple(foreign_key["referred_columns"]),
                    foreign_key.get("options", {}).get("ondelete"),
                )
                for foreign_key in inspector.get_foreign_keys("capability")
            }
            assert reflected_foreign_keys == _model_foreign_keys()

            reflected_checks = {
                check["name"]: _normalized_sql(check["sqltext"])
                for check in inspector.get_check_constraints("capability")
            }
            model_checks = {
                constraint.name: _normalized_sql(constraint.sqltext)
                for constraint in model_table.constraints
                if isinstance(constraint, sa.CheckConstraint)
            }
            assert reflected_checks == model_checks

            model_server_defaults = {
                column.name: _normalized_sql(column.server_default.arg.compile(dialect=sqlite.dialect()))
                for column in model_table.c
                if column.server_default is not None
            }
            reflected_server_defaults = {
                name: _normalized_sql(column["default"])
                for name, column in reflected_columns.items()
                if column["default"] is not None
            }
            assert reflected_server_defaults == model_server_defaults
    finally:
        engine.dispose()


def _table_names(database_url: str) -> set[str]:
    engine = sa.create_engine(_sync_sqlite_url(database_url))
    try:
        return set(sa.inspect(engine).get_table_names())
    finally:
        engine.dispose()


def _current_revision(database_url: str) -> str | None:
    engine = sa.create_engine(_sync_sqlite_url(database_url))
    try:
        with engine.connect() as connection:
            return MigrationContext.configure(connection).get_current_revision()
    finally:
        engine.dispose()


def test_global_model_registry_imports_capability() -> None:
    assert models.Capability is Capability
    assert {"capability", "user", "flow"} <= SQLModel.metadata.tables.keys()


def test_capability_revision_is_the_only_head_and_has_verified_parent() -> None:
    config = _make_alembic_config("sqlite+aiosqlite:///:memory:")
    scripts = ScriptDirectory.from_config(config)
    revision = scripts.get_revision(_REVISION)

    assert scripts.get_heads() == [_REVISION]
    assert revision is not None
    assert revision.down_revision == _PREVIOUS_REVISION


def test_capability_migration_passes_expand_validator() -> None:
    result = MigrationValidator().validate_migration_file(_MIGRATION_PATH)

    assert result["phase"] == "EXPAND"
    assert result["valid"] is True
    assert result["violations"] == []


def test_capability_sqlite_upgrade_downgrade_reupgrade_and_drift_check() -> None:
    temp_directory = Path(tempfile.gettempdir()).resolve()
    database_path = temp_directory / f"uncharted-ai-os-{uuid4()}.db"
    database_url = f"sqlite+aiosqlite:///{database_path}"
    configured_path = Path(make_url(database_url).database or "").resolve()

    sys.stdout.write(f"Disposable capability migration database: {database_url}\n")
    assert configured_path == database_path
    assert configured_path.parent == temp_directory
    assert configured_path.name.startswith("uncharted-ai-os-")
    assert configured_path.suffix == ".db"
    assert configured_path != (Path.cwd() / "langflow.db").resolve()

    config = _make_alembic_config(database_url)
    assert config.get_main_option("sqlalchemy.url") == database_url
    assert config.get_main_option("script_location") == str(_SCRIPT_LOCATION)

    try:
        command.upgrade(config, _PREVIOUS_REVISION)
        previous_tables = _table_names(database_url)
        assert "capability" not in previous_tables
        assert {"user", "flow"} <= previous_tables
        assert _current_revision(database_url) == _PREVIOUS_REVISION

        command.upgrade(config, _REVISION)
        assert _current_revision(database_url) == _REVISION
        _assert_capability_schema_matches_model(database_url)

        command.downgrade(config, _PREVIOUS_REVISION)
        assert _current_revision(database_url) == _PREVIOUS_REVISION
        assert _table_names(database_url) == previous_tables
        assert {"user", "flow"} <= previous_tables

        command.upgrade(config, _REVISION)
        assert _current_revision(database_url) == _REVISION
        _assert_capability_schema_matches_model(database_url)
        command.check(config)
    finally:
        for suffix in ("", "-wal", "-shm", "-journal"):
            Path(f"{database_path}{suffix}").unlink(missing_ok=True)


def test_capability_migration_compiles_as_postgresql_without_native_enums(monkeypatch) -> None:
    migration_module = importlib.import_module("langflow.alembic.versions.7ab9c064c615_add_capability_table")
    output = StringIO()
    context = MigrationContext.configure(
        dialect=postgresql.dialect(),
        opts={"as_sql": True, "literal_binds": True, "output_buffer": output},
    )

    monkeypatch.setattr(migration_module, "op", Operations(context))
    monkeypatch.setattr(migration_module.migration, "table_exists", lambda _name, _connection: False)
    migration_module.upgrade()

    ddl = output.getvalue()
    ddl_upper = ddl.upper()
    assert ddl_upper.count("CREATE TABLE CAPABILITY") == 1
    assert ddl_upper.count(" JSONB DEFAULT '[]' NOT NULL") == 3
    assert "CREATE TYPE" not in ddl_upper
    assert " ENUM" not in ddl_upper
    assert ddl_upper.count("ON DELETE SET NULL") == 3
    assert ddl_upper.count("ON DELETE CASCADE") == 1
    assert all(f"CONSTRAINT {name.upper()}" in ddl_upper for name in _model_check_names())
    assert all(f"CREATE INDEX {name.upper()}" in ddl_upper for name in _model_index_names())
    assert "ALTER TABLE USER" not in ddl_upper
    assert "ALTER TABLE FLOW" not in ddl_upper
    assert "ALTER TABLE FOLDER" not in ddl_upper
