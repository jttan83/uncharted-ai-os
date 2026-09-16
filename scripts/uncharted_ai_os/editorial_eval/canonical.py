"""Canonical JSON serialization and content addressing for the experiment."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel


def _json_value(value: BaseModel | Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", by_alias=True, exclude_none=False)
    return value


def canonical_json_bytes(value: BaseModel | Any) -> bytes:
    """Serialize JSON deterministically as UTF-8 without insignificant whitespace."""
    return json.dumps(
        _json_value(value),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_digest(value: BaseModel | Any) -> str:
    """Return a labelled SHA-256 digest of the canonical JSON bytes."""
    return f"sha256:{hashlib.sha256(canonical_json_bytes(value)).hexdigest()}"


def verify_canonical_digest(value: BaseModel | Any, expected: str) -> None:
    """Fail if the supplied content does not match its expected digest."""
    actual = canonical_digest(value)
    if actual != expected:
        msg = f"canonical digest mismatch: expected {expected}, got {actual}"
        raise ValueError(msg)


def assert_byte_identical_case_briefs(first: BaseModel, second: BaseModel, expected_digest: str | None = None) -> str:
    """Prove that B and C received identical canonical CaseBrief bytes."""
    first_bytes = canonical_json_bytes(first)
    second_bytes = canonical_json_bytes(second)
    if first_bytes != second_bytes:
        msg = "B and C CaseBrief canonical bytes differ"
        raise ValueError(msg)
    digest = f"sha256:{hashlib.sha256(first_bytes).hexdigest()}"
    if expected_digest is not None and digest != expected_digest:
        msg = "CaseBrief does not match the committed digest"
        raise ValueError(msg)
    return digest
