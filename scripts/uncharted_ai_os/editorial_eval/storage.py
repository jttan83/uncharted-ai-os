"""Constrained private JSON storage for the disposable experiment harness."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from pydantic import BaseModel

from .canonical import canonical_json_bytes

ModelT = TypeVar("ModelT", bound="BaseModel")

EXPERIMENT_ROOT = Path("var/uncharted-ai-os/phase-1f-a")


class StorageSafetyError(RuntimeError):
    """Raised when a storage operation would cross an experiment boundary."""


class StorageRecordExistsError(StorageSafetyError):
    """Raised when an immutable private record already exists."""


class PrivateExperimentStorage:
    """Atomic, permission-restricted JSON storage under the one allowed root."""

    def __init__(self, repo_root: Path, *, verify_ignored: bool = True) -> None:
        self.repo_root = repo_root.resolve()
        self.root = (self.repo_root / EXPERIMENT_ROOT).resolve()
        expected = self.repo_root / "var" / "uncharted-ai-os" / "phase-1f-a"
        if self.root != expected:
            msg = "experiment storage root did not resolve to the required repository path"
            raise StorageSafetyError(msg)
        if verify_ignored and not self._is_ignored():
            msg = f"private experiment root is not ignored by git: {EXPERIMENT_ROOT}"
            raise StorageSafetyError(msg)
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._restrict_directory(self.root)

    def write_json(self, relative_path: str | Path, value: BaseModel | Any) -> Path:
        """Atomically write canonical JSON with restrictive permissions."""
        destination = self._confined_path(relative_path)
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._verify_no_symlink_path(destination.parent)
        self._restrict_directory(destination.parent)
        payload = canonical_json_bytes(value) + b"\n"
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
        )
        temporary_path = Path(temporary_name)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            temporary_path.replace(destination)
            destination.chmod(0o600)
            self._fsync_directory(destination.parent)
        except BaseException:
            if temporary_path.exists():
                temporary_path.unlink()
            raise
        return destination

    def write_json_once(self, relative_path: str | Path, value: BaseModel | Any) -> Path:
        """Atomically create canonical JSON without replacing historical evidence."""
        destination = self._confined_path(relative_path)
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._verify_no_symlink_path(destination.parent)
        self._restrict_directory(destination.parent)
        payload = canonical_json_bytes(value) + b"\n"
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
        )
        temporary_path = Path(temporary_name)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary_path, destination)
            except FileExistsError as exc:
                msg = f"immutable experiment record already exists: {relative_path}"
                raise StorageRecordExistsError(msg) from exc
            destination.chmod(0o600)
            self._fsync_directory(destination.parent)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()
        return destination

    def read_json(self, relative_path: str | Path) -> Any:
        """Read JSON only from within the confined experiment root."""
        source = self._confined_path(relative_path)
        self._verify_no_symlink_path(source)
        with source.open("r", encoding="utf-8") as stream:
            return json.load(stream)

    def read_model(self, relative_path: str | Path, model_type: type[ModelT]) -> ModelT:
        """Read a strict Pydantic model through its JSON validation boundary."""
        source = self._confined_path(relative_path)
        self._verify_no_symlink_path(source)
        return model_type.model_validate_json(source.read_bytes())

    def _confined_path(self, relative_path: str | Path) -> Path:
        raw = str(relative_path)
        requested = Path(relative_path)
        if not raw or "\\" in raw or "\x00" in raw or requested.is_absolute() or ".." in requested.parts:
            msg = f"unsafe experiment-relative path: {raw!r}"
            raise StorageSafetyError(msg)
        unresolved = self.root / requested
        self._verify_no_symlink_path(unresolved)
        candidate = unresolved.resolve()
        if not candidate.is_relative_to(self.root) or candidate == self.root:
            msg = f"path escapes or does not identify a file under the experiment root: {raw!r}"
            raise StorageSafetyError(msg)
        self._verify_no_symlink_path(candidate)
        return candidate

    def _is_ignored(self) -> bool:
        result = subprocess.run(  # noqa: S603
            ["git", "check-ignore", "--quiet", "--no-index", "--", EXPERIMENT_ROOT.as_posix()],  # noqa: S607
            cwd=self.repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
        return result.returncode == 0

    def _verify_no_symlink_path(self, path: Path) -> None:
        current = path
        while current != self.repo_root:
            if current.exists() and current.is_symlink():
                msg = f"symlinks are forbidden in private experiment storage: {current}"
                raise StorageSafetyError(msg)
            if current == self.root:
                return
            current = current.parent
        if path != self.repo_root:
            msg = "storage path did not descend from the private experiment root"
            raise StorageSafetyError(msg)

    @staticmethod
    def _restrict_directory(path: Path) -> None:
        if os.name == "posix":
            path.chmod(0o700)

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        if os.name != "posix":
            return
        flags = os.O_RDONLY
        descriptor = os.open(path, flags)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
