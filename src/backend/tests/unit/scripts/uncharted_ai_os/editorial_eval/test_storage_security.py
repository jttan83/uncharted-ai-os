from __future__ import annotations

import os
import subprocess
from pathlib import Path  # noqa: TC003

import pytest

from scripts.uncharted_ai_os.editorial_eval.security import (
    ExternalTracingEnabledError,
    assert_external_tracing_disabled,
)
from scripts.uncharted_ai_os.editorial_eval.storage import PrivateExperimentStorage, StorageSafetyError


def initialize_repo(path: Path, ignore_rule: str) -> None:
    subprocess.run(["git", "init", "--quiet", str(path)], check=True)  # noqa: S603, S607
    (path / ".gitignore").write_text(ignore_rule, encoding="utf-8")


def test_storage_requires_ignored_root(tmp_path: Path) -> None:
    initialize_repo(tmp_path, "")
    with pytest.raises(StorageSafetyError, match="not ignored"):
        PrivateExperimentStorage(tmp_path)


def test_storage_confines_paths_and_rejects_traversal(tmp_path: Path) -> None:
    initialize_repo(tmp_path, "var/\n")
    storage = PrivateExperimentStorage(tmp_path)
    for unsafe in ("../outside.json", "/tmp/outside.json", "nested/../../outside.json", "..\\outside.json", ""):  # noqa: S108
        with pytest.raises(StorageSafetyError):
            storage.write_json(unsafe, {"unsafe": True})


def test_storage_writes_atomically_with_restrictive_permissions(tmp_path: Path) -> None:
    initialize_repo(tmp_path, "var/\n")
    storage = PrivateExperimentStorage(tmp_path)
    destination = storage.write_json("runs/run.json", {"version": 1})
    storage.write_json("runs/run.json", {"version": 2})
    assert storage.read_json("runs/run.json") == {"version": 2}
    assert not list(destination.parent.glob("*.tmp"))
    if os.name == "posix":
        assert destination.stat().st_mode & 0o777 == 0o600
        assert destination.parent.stat().st_mode & 0o777 == 0o700


def test_storage_rejects_symlink_escape(tmp_path: Path) -> None:
    initialize_repo(tmp_path, "var/\n")
    storage = PrivateExperimentStorage(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    symlink = storage.root / "escape"
    symlink.symlink_to(outside, target_is_directory=True)
    with pytest.raises(StorageSafetyError, match="symlink"):
        storage.write_json("escape/data.json", {"unsafe": True})


@pytest.mark.parametrize("flag", ["LANGCHAIN_TRACING", "LANGCHAIN_TRACING_V2", "LANGSMITH_TRACING"])
def test_external_tracing_guard_fails_closed_without_values(flag: str) -> None:
    with pytest.raises(ExternalTracingEnabledError) as exc_info:
        assert_external_tracing_disabled({flag: "TRUE", "LANGSMITH_API_KEY": "credential-must-not-appear"})
    assert flag in str(exc_info.value)
    assert "credential-must-not-appear" not in str(exc_info.value)


def test_external_tracing_guard_accepts_disabled_or_unrelated_settings() -> None:
    assert_external_tracing_disabled(
        {
            "LANGCHAIN_TRACING_V2": "false",
            "LANGSMITH_PROJECT": "configured-but-not-enabled",
            "LANGSMITH_API_KEY": "not-read-or-logged",
        }
    )
