"""Experiment-owned model invocation boundary and offline scripted implementation."""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Sequence  # noqa: TC003
from dataclasses import dataclass, field
from typing import Any, Generic, Literal, Protocol, TypeVar

from pydantic import BaseModel, Field, model_validator

from .contracts import FailureInfo, JsonValue, ResourceUsage, ShortText, StrictModel, assert_json_safe
from .security import assert_credential_free, assert_external_tracing_disabled

OutputT = TypeVar("OutputT", bound=BaseModel)
_SENSITIVE_KEY_PARTS = ("api_key", "apikey", "authorization", "credential", "password", "secret", "token")
_SAFE_PROVIDER_METADATA_KEYS = {
    "finish_reason",
    "id",
    "model",
    "model_name",
    "model_version",
    "provider",
    "response_id",
    "stop_reason",
    "system_fingerprint",
}


class ModelMessage(StrictModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=200_000)


class InvocationModelConfig(StrictModel):
    """Explicit non-secret provider settings; credentials are resolved externally."""

    provider: ShortText
    model_identifier: ShortText
    reasoning: ShortText
    temperature: float = Field(ge=0, le=2)
    seed: int | None = None
    max_output_tokens: int = Field(gt=0)
    timeout_seconds: int = Field(gt=0)

    @model_validator(mode="after")
    def reject_sensitive_configuration(self) -> InvocationModelConfig:
        assert_credential_free(self.model_dump(mode="python"))
        return self


class ModelResponse(StrictModel, Generic[OutputT]):
    parsed: OutputT | None = None
    raw_provider_metadata: dict[str, JsonValue] = Field(default_factory=dict)
    usage: ResourceUsage = Field(default_factory=ResourceUsage)
    latency_ms: int = Field(ge=0)
    attempt_number: int = Field(ge=1, le=2)
    failure: FailureInfo | None = None

    @model_validator(mode="after")
    def validate_result(self) -> ModelResponse[OutputT]:
        if (self.parsed is None) == (self.failure is None):
            msg = "model response requires exactly one of parsed result or failure"
            raise ValueError(msg)
        return self


class ModelInvoker(Protocol):
    """Minimal provider-neutral interface owned by this experiment."""

    def invoke(
        self,
        messages: Sequence[ModelMessage],
        output_type: type[OutputT],
        model_config: InvocationModelConfig,
        *,
        attempt_number: int = 1,
    ) -> ModelResponse[OutputT]: ...


@dataclass(frozen=True)
class InvocationRecord:
    messages: tuple[ModelMessage, ...]
    output_type: type[BaseModel]
    model_config: InvocationModelConfig
    attempt_number: int


@dataclass(frozen=True)
class ScriptedStep:
    """One deterministic offline result consumed by ScriptedModelInvoker."""

    parsed: BaseModel | dict[str, Any] | None = None
    failure: FailureInfo | None = None
    usage: ResourceUsage = field(default_factory=ResourceUsage)
    latency_ms: int = 1
    raw_provider_metadata: dict[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if (self.parsed is None) == (self.failure is None):
            msg = "scripted step requires exactly one of parsed or failure"
            raise ValueError(msg)


class ScriptedModelInvoker:
    """Deterministic fake used for all offline tests and rehearsals."""

    def __init__(self, steps: Sequence[ScriptedStep]) -> None:
        self._steps = deque(steps)
        self.records: list[InvocationRecord] = []

    @property
    def remaining_steps(self) -> int:
        return len(self._steps)

    def invoke(
        self,
        messages: Sequence[ModelMessage],
        output_type: type[OutputT],
        model_config: InvocationModelConfig,
        *,
        attempt_number: int = 1,
    ) -> ModelResponse[OutputT]:
        assert_credential_free(model_config.model_dump(mode="python"))
        self.records.append(
            InvocationRecord(
                messages=tuple(messages),
                output_type=output_type,
                model_config=model_config,
                attempt_number=attempt_number,
            )
        )
        if not self._steps:
            msg = "scripted invoker has no remaining result"
            raise RuntimeError(msg)
        step = self._steps.popleft()
        parsed: OutputT | None = None
        if step.parsed is not None:
            parsed = step.parsed if isinstance(step.parsed, output_type) else output_type.model_validate(step.parsed)
        return ModelResponse[OutputT](
            parsed=parsed,
            raw_provider_metadata=sanitize_provider_metadata(step.raw_provider_metadata),
            usage=step.usage,
            latency_ms=step.latency_ms,
            attempt_number=attempt_number,
            failure=step.failure,
        )


class LangChainModelInvoker:
    """Thin adapter over existing LangChain chat-model initialization.

    It is intentionally not provider routing. The caller supplies one frozen
    model configuration, and the external tracing guard runs before any model
    is initialized or invoked.
    """

    def invoke(
        self,
        messages: Sequence[ModelMessage],
        output_type: type[OutputT],
        model_config: InvocationModelConfig,
        *,
        attempt_number: int = 1,
    ) -> ModelResponse[OutputT]:
        assert_credential_free(model_config.model_dump(mode="python"))
        assert_external_tracing_disabled()
        started = time.perf_counter()
        try:
            from langchain.chat_models import init_chat_model

            parameters: dict[str, Any] = {
                "temperature": model_config.temperature,
                "max_tokens": model_config.max_output_tokens,
                "timeout": model_config.timeout_seconds,
            }
            if model_config.seed is not None:
                parameters["seed"] = model_config.seed
            if model_config.reasoning != "not_exposed":
                parameters["reasoning_effort"] = model_config.reasoning
            model = init_chat_model(
                model=model_config.model_identifier,
                model_provider=model_config.provider,
                **parameters,
            )
            structured = model.with_structured_output(output_type, include_raw=True)
            provider_result = structured.invoke(
                [(message.role, message.content) for message in messages],
                config={"callbacks": []},
            )
            parsed = provider_result.get("parsed")
            parsing_error = provider_result.get("parsing_error")
            raw = provider_result.get("raw")
            usage = _extract_usage(raw)
            metadata = sanitize_provider_metadata(getattr(raw, "response_metadata", {}) or {})
            latency_ms = round((time.perf_counter() - started) * 1000)
            if parsing_error is not None or not isinstance(parsed, output_type):
                return ModelResponse[OutputT](
                    raw_provider_metadata=metadata,
                    usage=usage,
                    latency_ms=latency_ms,
                    attempt_number=attempt_number,
                    failure=FailureInfo(
                        failure_type="structured_output_error",
                        safe_message="Model response did not satisfy the requested structured output.",
                        retryable=False,
                    ),
                )
            return ModelResponse[OutputT](
                parsed=parsed,
                raw_provider_metadata=metadata,
                usage=usage,
                latency_ms=latency_ms,
                attempt_number=attempt_number,
            )
        except Exception as exc:  # noqa: BLE001  # External SDK exceptions vary by provider.
            latency_ms = round((time.perf_counter() - started) * 1000)
            retryable = isinstance(exc, (ConnectionError, TimeoutError))
            return ModelResponse[OutputT](
                usage=ResourceUsage(),
                latency_ms=latency_ms,
                attempt_number=attempt_number,
                failure=FailureInfo(
                    failure_type="model_invocation_failure",
                    safe_message="Model invocation failed; provider details were suppressed.",
                    retryable=retryable,
                ),
            )


def sanitize_provider_metadata(value: Any) -> dict[str, JsonValue]:
    """Retain only a small allowlist of non-content provider metadata."""
    if not isinstance(value, dict):
        return {}

    def sanitize(item: Any) -> JsonValue:
        if item is None or isinstance(item, (bool, int, float, str)):
            return item
        if isinstance(item, (list, tuple)):
            return [sanitize(child) for child in item]
        if isinstance(item, dict):
            return {
                str(key): sanitize(child)
                for key, child in item.items()
                if not any(part in str(key).lower() for part in _SENSITIVE_KEY_PARTS)
            }
        return f"<{type(item).__name__}>"

    allowed = {key: item for key, item in value.items() if key.lower() in _SAFE_PROVIDER_METADATA_KEYS}
    return assert_json_safe(sanitize(allowed))  # type: ignore[return-value]


def _extract_usage(raw: Any) -> ResourceUsage:
    metadata = getattr(raw, "usage_metadata", None) or {}
    if not isinstance(metadata, dict):
        return ResourceUsage()
    input_details = metadata.get("input_token_details") or {}
    output_details = metadata.get("output_token_details") or {}
    tool_calls = getattr(raw, "tool_calls", None)
    return ResourceUsage(
        input_tokens=_optional_nonnegative_int(metadata.get("input_tokens")),
        output_tokens=_optional_nonnegative_int(metadata.get("output_tokens")),
        cached_input_tokens=_optional_nonnegative_int(input_details.get("cache_read")),
        reasoning_tokens=_optional_nonnegative_int(output_details.get("reasoning")),
        tool_calls=len(tool_calls) if isinstance(tool_calls, list) else None,
    )


def _optional_nonnegative_int(value: Any) -> int | None:
    return value if isinstance(value, int) and value >= 0 else None
