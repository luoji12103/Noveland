from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any, Protocol

import httpx
from noveland.adapters.models import ProviderProfile
from noveland.core.settings import AppSettings
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session


class ProviderType(StrEnum):
    OPENAI_COMPATIBLE = "openai_compatible"
    ANTHROPIC_COMPATIBLE = "anthropic_compatible"


class ProviderErrorCode(StrEnum):
    CONFIGURATION = "configuration"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    TRANSIENT = "transient"
    PROVIDER_ERROR = "provider_error"
    INVALID_RESPONSE = "invalid_response"


class ProviderTestStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"


class ProviderError(RuntimeError):
    """Base error for provider profile and invocation failures."""


class ProviderProfileValidationError(ValueError):
    """Raised when provider profile input fails validation."""


class ProviderConfigurationError(ProviderError):
    """Raised when a provider profile cannot be configured."""


class ProviderInvocationError(ProviderError):
    """Raised when a provider invocation fails."""

    def __init__(
        self,
        message: str,
        error_code: ProviderErrorCode = ProviderErrorCode.PROVIDER_ERROR,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code


class _FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True)


class ProviderProfileCreate(_FrozenContract):
    profile_key: str = Field(
        min_length=2,
        max_length=80,
        pattern=r"^[a-z0-9][a-z0-9-]{1,78}[a-z0-9]$",
    )
    name: str = Field(min_length=1, max_length=160)
    provider_type: ProviderType
    base_url: str = Field(min_length=1, max_length=500)
    model_name: str = Field(min_length=1, max_length=200)
    capabilities: dict[str, Any] = Field(default_factory=dict)
    api_key_ref: str = Field(min_length=1, max_length=120)
    timeout_seconds: int = Field(default=20, ge=1, le=120)
    retry_attempts: int = Field(default=1, ge=0, le=5)
    rate_limit_per_minute: int | None = Field(default=None, ge=1, le=600)


class ProviderProfileUpdate(_FrozenContract):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    base_url: str | None = Field(default=None, min_length=1, max_length=500)
    model_name: str | None = Field(default=None, min_length=1, max_length=200)
    capabilities: dict[str, Any] | None = None
    api_key_ref: str | None = Field(default=None, min_length=1, max_length=120)
    timeout_seconds: int | None = Field(default=None, ge=1, le=120)
    retry_attempts: int | None = Field(default=None, ge=0, le=5)
    rate_limit_per_minute: int | None = Field(default=None, ge=1, le=600)
    is_enabled: bool | None = None


class ProviderProfileRecord(_FrozenContract):
    id: uuid.UUID
    profile_key: str
    name: str
    provider_type: ProviderType
    base_url: str
    model_name: str
    capabilities: dict[str, Any]
    api_key_ref: str
    timeout_seconds: int
    retry_attempts: int
    rate_limit_per_minute: int | None
    last_tested_at: datetime | None
    last_test_status: ProviderTestStatus | None
    last_test_error: str | None
    is_enabled: bool


class ProviderCompletion(_FrozenContract):
    text: str
    raw_response: dict[str, Any]


class ProviderInvocationResult(_FrozenContract):
    status: ProviderTestStatus
    latency_ms: int
    text_preview: str | None = None
    error_code: ProviderErrorCode | None = None
    error_message: str | None = None


class ModelProvider(Protocol):
    def complete(self, prompt: str) -> ProviderCompletion:
        """Generate one completion for the given prompt."""


class ProviderProfileService:
    def __init__(
        self,
        session: Session,
        settings: AppSettings,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._transport = transport

    def list_profiles(self) -> list[ProviderProfileRecord]:
        return [
            _record(model)
            for model in self._session.scalars(
                select(ProviderProfile).order_by(ProviderProfile.profile_key),
            ).all()
        ]

    def get_profile(self, profile_id: uuid.UUID) -> ProviderProfileRecord | None:
        model = self._session.get(ProviderProfile, profile_id)
        return None if model is None else _record(model)

    def first_enabled_profile(self) -> ProviderProfileRecord | None:
        model = self._session.scalars(
            select(ProviderProfile)
            .where(ProviderProfile.is_enabled.is_(True))
            .order_by(ProviderProfile.profile_key),
        ).first()
        return None if model is None else _record(model)

    def create_profile(self, profile_create: ProviderProfileCreate) -> ProviderProfileRecord:
        if self._profile_key_exists(profile_create.profile_key):
            raise ProviderConfigurationError("Provider profile key already exists")
        model = ProviderProfile(
            profile_key=profile_create.profile_key,
            name=profile_create.name,
            provider_type=profile_create.provider_type.value,
            base_url=profile_create.base_url,
            model_name=profile_create.model_name,
            capabilities=profile_create.capabilities,
            api_key_ref=profile_create.api_key_ref,
            timeout_seconds=profile_create.timeout_seconds,
            retry_attempts=profile_create.retry_attempts,
            rate_limit_per_minute=profile_create.rate_limit_per_minute,
            is_enabled=True,
        )
        self._session.add(model)
        self._session.flush()
        return _record(model)

    def update_profile(
        self,
        model: ProviderProfile,
        profile_update: ProviderProfileUpdate,
    ) -> ProviderProfileRecord:
        if "name" in profile_update.model_fields_set and profile_update.name is not None:
            model.name = profile_update.name
        if "base_url" in profile_update.model_fields_set and profile_update.base_url is not None:
            model.base_url = profile_update.base_url
        if (
            "model_name" in profile_update.model_fields_set
            and profile_update.model_name is not None
        ):
            model.model_name = profile_update.model_name
        if "capabilities" in profile_update.model_fields_set:
            model.capabilities = profile_update.capabilities or {}
        if (
            "api_key_ref" in profile_update.model_fields_set
            and profile_update.api_key_ref is not None
        ):
            model.api_key_ref = profile_update.api_key_ref
        if (
            "timeout_seconds" in profile_update.model_fields_set
            and profile_update.timeout_seconds is not None
        ):
            model.timeout_seconds = profile_update.timeout_seconds
        if (
            "retry_attempts" in profile_update.model_fields_set
            and profile_update.retry_attempts is not None
        ):
            model.retry_attempts = profile_update.retry_attempts
        if "rate_limit_per_minute" in profile_update.model_fields_set:
            model.rate_limit_per_minute = profile_update.rate_limit_per_minute
        if "is_enabled" in profile_update.model_fields_set:
            model.is_enabled = bool(profile_update.is_enabled)
        self._session.flush()
        return _record(model)

    def disable_profile(self, model: ProviderProfile) -> None:
        model.is_enabled = False
        self._session.flush()

    def invoke_profile(self, profile: ProviderProfileRecord, prompt: str) -> ProviderCompletion:
        api_key = self._settings.provider_api_keys_json.get(profile.api_key_ref)
        if api_key is None or api_key == "":
            raise ProviderConfigurationError("Provider API key ref is not configured")
        _rate_limiter.check(profile)
        provider = _provider_for_profile(profile, api_key, self._transport)
        return provider.complete(prompt)

    def test_profile(
        self,
        model: ProviderProfile,
        prompt: str = "Reply with OK.",
    ) -> ProviderInvocationResult:
        started_at = datetime.now(UTC)
        try:
            completion = self.invoke_profile(_record(model), prompt)
        except ProviderConfigurationError as exc:
            result = _failed_invocation_result(
                started_at,
                ProviderErrorCode.CONFIGURATION,
                str(exc),
            )
        except ProviderInvocationError as exc:
            result = _failed_invocation_result(started_at, exc.error_code, str(exc))
        except ProviderError as exc:
            result = _failed_invocation_result(
                started_at,
                ProviderErrorCode.PROVIDER_ERROR,
                str(exc),
            )
        else:
            result = ProviderInvocationResult(
                status=ProviderTestStatus.SUCCESS,
                latency_ms=_latency_ms(started_at),
                text_preview=_text_preview(completion.text),
            )

        model.last_tested_at = datetime.now(UTC)
        model.last_test_status = result.status.value
        model.last_test_error = result.error_message
        self._session.flush()
        return result

    def _profile_key_exists(self, profile_key: str) -> bool:
        existing = self._session.scalars(
            select(ProviderProfile.id).where(ProviderProfile.profile_key == profile_key),
        ).first()
        return existing is not None


class OpenAICompatibleProvider:
    def __init__(
        self,
        profile: ProviderProfileRecord,
        api_key: str,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._profile = profile
        self._api_key = api_key
        self._transport = transport

    def complete(self, prompt: str) -> ProviderCompletion:
        headers = _base_headers(self._api_key)
        headers.update(_extra_headers(self._profile.capabilities))
        payload = {
            "model": self._profile.model_name,
            "messages": [{"role": "user", "content": prompt}],
        }
        raw_response = _post_json(
            f"{self._profile.base_url.rstrip('/')}/chat/completions",
            headers,
            payload,
            self._transport,
            self._profile.timeout_seconds,
            self._profile.retry_attempts,
        )
        try:
            content = raw_response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderInvocationError(
                "OpenAI-compatible response did not include text content",
                ProviderErrorCode.INVALID_RESPONSE,
            ) from exc
        if not isinstance(content, str):
            raise ProviderInvocationError(
                "OpenAI-compatible response did not include text content",
                ProviderErrorCode.INVALID_RESPONSE,
            )
        return ProviderCompletion(text=content, raw_response=raw_response)


class AnthropicCompatibleProvider:
    def __init__(
        self,
        profile: ProviderProfileRecord,
        api_key: str,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._profile = profile
        self._api_key = api_key
        self._transport = transport

    def complete(self, prompt: str) -> ProviderCompletion:
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        headers.update(_extra_headers(self._profile.capabilities))
        payload = {
            "model": self._profile.model_name,
            "max_tokens": 256,
            "messages": [{"role": "user", "content": prompt}],
        }
        raw_response = _post_json(
            f"{self._profile.base_url.rstrip('/')}/messages",
            headers,
            payload,
            self._transport,
            self._profile.timeout_seconds,
            self._profile.retry_attempts,
        )
        parts = raw_response.get("content")
        if not isinstance(parts, list):
            raise ProviderInvocationError(
                "Anthropic-compatible response did not include content parts",
                ProviderErrorCode.INVALID_RESPONSE,
            )
        text = "".join(
            part.get("text", "")
            for part in parts
            if isinstance(part, dict) and part.get("type") == "text"
        )
        if text == "":
            raise ProviderInvocationError(
                "Anthropic-compatible response did not include text content",
                ProviderErrorCode.INVALID_RESPONSE,
            )
        return ProviderCompletion(text=text, raw_response=raw_response)


def _provider_for_profile(
    profile: ProviderProfileRecord,
    api_key: str,
    transport: httpx.BaseTransport | None,
) -> ModelProvider:
    if profile.provider_type is ProviderType.OPENAI_COMPATIBLE:
        return OpenAICompatibleProvider(profile, api_key, transport)
    if profile.provider_type is ProviderType.ANTHROPIC_COMPATIBLE:
        return AnthropicCompatibleProvider(profile, api_key, transport)
    raise ProviderConfigurationError("Unsupported provider type")


def _record(model: ProviderProfile) -> ProviderProfileRecord:
    return ProviderProfileRecord(
        id=model.id,
        profile_key=model.profile_key,
        name=model.name,
        provider_type=ProviderType(model.provider_type),
        base_url=model.base_url,
        model_name=model.model_name,
        capabilities=model.capabilities,
        api_key_ref=model.api_key_ref,
        timeout_seconds=model.timeout_seconds,
        retry_attempts=model.retry_attempts,
        rate_limit_per_minute=model.rate_limit_per_minute,
        last_tested_at=model.last_tested_at,
        last_test_status=None
        if model.last_test_status is None
        else ProviderTestStatus(model.last_test_status),
        last_test_error=model.last_test_error,
        is_enabled=model.is_enabled,
    )


def _base_headers(api_key: str) -> dict[str, str]:
    return {
        "authorization": f"Bearer {api_key}",
        "content-type": "application/json",
    }


def _extra_headers(capabilities: dict[str, Any]) -> dict[str, str]:
    headers = capabilities.get("headers")
    if headers is None:
        return {}
    if not isinstance(headers, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in headers.items()
    ):
        raise ProviderConfigurationError("Provider capabilities.headers must be a string map")
    return dict(headers)


def _post_json(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    transport: httpx.BaseTransport | None,
    timeout_seconds: int,
    retry_attempts: int,
) -> dict[str, Any]:
    max_attempts = retry_attempts + 1
    body: Any = None
    with httpx.Client(transport=transport, timeout=float(timeout_seconds)) as client:
        for attempt in range(max_attempts):
            try:
                response = client.post(url, headers=headers, json=payload)
            except httpx.TimeoutException as exc:
                if attempt < retry_attempts:
                    continue
                raise ProviderInvocationError(
                    "Provider request timed out",
                    ProviderErrorCode.TIMEOUT,
                ) from exc
            except httpx.TransportError as exc:
                if attempt < retry_attempts:
                    continue
                raise ProviderInvocationError(
                    "Provider request failed transiently",
                    ProviderErrorCode.TRANSIENT,
                ) from exc

            retryable_error = _error_for_status(response.status_code)
            if retryable_error is not None:
                if retryable_error.error_code in {
                    ProviderErrorCode.RATE_LIMITED,
                    ProviderErrorCode.TRANSIENT,
                } and attempt < retry_attempts:
                    continue
                raise retryable_error

            try:
                body = response.json()
            except ValueError as exc:
                raise ProviderInvocationError(
                    "Provider response body must be valid JSON",
                    ProviderErrorCode.INVALID_RESPONSE,
                ) from exc
            break
        else:
            raise ProviderInvocationError("Provider request failed")

    if not isinstance(body, dict):
        raise ProviderInvocationError(
            "Provider response body must be an object",
            ProviderErrorCode.INVALID_RESPONSE,
        )
    return body


def _error_for_status(status_code: int) -> ProviderInvocationError | None:
    if status_code < 400:
        return None
    if status_code == 429:
        return ProviderInvocationError(
            "Provider rate limited the request",
            ProviderErrorCode.RATE_LIMITED,
        )
    if status_code >= 500:
        return ProviderInvocationError(
            "Provider request failed transiently",
            ProviderErrorCode.TRANSIENT,
        )
    return ProviderInvocationError(
        f"Provider returned HTTP {status_code}",
        ProviderErrorCode.PROVIDER_ERROR,
    )


def _failed_invocation_result(
    started_at: datetime,
    error_code: ProviderErrorCode,
    message: str,
) -> ProviderInvocationResult:
    return ProviderInvocationResult(
        status=ProviderTestStatus.FAILED,
        latency_ms=_latency_ms(started_at),
        error_code=error_code,
        error_message=_text_preview(message),
    )


def _latency_ms(started_at: datetime) -> int:
    return int((datetime.now(UTC) - started_at).total_seconds() * 1000)


def _text_preview(value: str) -> str:
    return value if len(value) <= 500 else f"{value[:500]}..."


class _ProviderRateLimiter:
    def __init__(self) -> None:
        self._calls: dict[uuid.UUID, list[datetime]] = defaultdict(list)

    def check(self, profile: ProviderProfileRecord) -> None:
        if profile.rate_limit_per_minute is None:
            return
        now = datetime.now(UTC)
        cutoff = now - timedelta(minutes=1)
        recent_calls = [call_at for call_at in self._calls[profile.id] if call_at >= cutoff]
        if len(recent_calls) >= profile.rate_limit_per_minute:
            self._calls[profile.id] = recent_calls
            raise ProviderInvocationError(
                "Provider rate limit exceeded",
                ProviderErrorCode.RATE_LIMITED,
            )
        recent_calls.append(now)
        self._calls[profile.id] = recent_calls


_rate_limiter = _ProviderRateLimiter()
