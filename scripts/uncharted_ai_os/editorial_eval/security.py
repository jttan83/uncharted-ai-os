"""Security guards for strictly local experimental execution."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import parse_qsl, urlsplit

_EXTERNAL_TRACING_FLAGS = (
    "LANGCHAIN_TRACING",
    "LANGCHAIN_TRACING_V2",
    "LANGSMITH_TRACING",
    "LANGSMITH_TRACING_V2",
)
_TRUE_VALUES = {"1", "true", "yes", "on", "enabled"}
_SENSITIVE_FIELD = re.compile(
    r"(?:^|[_-])(?:api[_-]?key|access[_-]?key|authorization|bearer|token|password|passwd|secret|credential|signature|cookie|x[_-]?api[_-]?key)"
    r"(?:[_-]|$)",
    re.IGNORECASE,
)
_SENSITIVE_ASSIGNMENT = re.compile(
    r"(?:^|[?&;\s])(?:api[_-]?key|access[_-]?key|authorization|bearer|token|password|passwd|secret|credential|signature|cookie)\s*[=:]",
    re.IGNORECASE,
)
_SECRET_VALUE_PREFIX = re.compile(r"^(?:bearer\s+|sk-[a-z0-9_-]{12,})", re.IGNORECASE)
_CREDENTIAL_ERROR = "credentials are forbidden in model configuration"
_CREDENTIAL_URL_ERROR = "credential-bearing URLs are forbidden in model configuration"


class ExternalTracingEnabledError(RuntimeError):
    """Raised before model execution when known external tracing is enabled."""


class CredentialConfigurationError(ValueError):
    """Raised without echoing a value when model configuration contains credential material."""


def assert_external_tracing_disabled(environment: Mapping[str, str] | None = None) -> None:
    """Fail closed without mutating global tracing configuration or logging values."""
    values = os.environ if environment is None else environment
    enabled = sorted(name for name in _EXTERNAL_TRACING_FLAGS if values.get(name, "").strip().lower() in _TRUE_VALUES)
    if enabled:
        names = ", ".join(enabled)
        msg = f"external LangChain/LangSmith tracing is enabled via: {names}"
        raise ExternalTracingEnabledError(msg)


def assert_credential_free(value: Any) -> None:
    """Reject credential-bearing keys and values recursively without logging their contents."""
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str) and _is_sensitive_key(key):
                raise CredentialConfigurationError(_CREDENTIAL_ERROR)
            assert_credential_free(item)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            assert_credential_free(item)
        return
    if not isinstance(value, str):
        return
    candidate = value.strip()
    if _SECRET_VALUE_PREFIX.search(candidate) or _SENSITIVE_ASSIGNMENT.search(candidate):
        raise CredentialConfigurationError(_CREDENTIAL_ERROR)
    if "://" not in candidate:
        return
    try:
        parsed = urlsplit(candidate)
    except ValueError as exc:
        raise CredentialConfigurationError(_CREDENTIAL_URL_ERROR) from exc
    if parsed.username is not None or parsed.password is not None:
        raise CredentialConfigurationError(_CREDENTIAL_URL_ERROR)
    if any(_is_sensitive_key(key) for key, _ in parse_qsl(parsed.query, keep_blank_values=True)):
        raise CredentialConfigurationError(_CREDENTIAL_URL_ERROR)


def _is_sensitive_key(key: str) -> bool:
    if _SENSITIVE_FIELD.search(key):
        return True
    normalized = re.sub(r"[^a-z0-9]", "", key.casefold())
    exact_or_embedded = ("apikey", "accesskey", "authorization", "bearer", "password", "passwd", "secret", "credential")
    return (
        any(part in normalized for part in exact_or_embedded)
        or normalized.startswith(("token", "cookie", "signature"))
        or normalized.endswith(("token", "cookie", "signature"))
    )
