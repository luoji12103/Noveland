from __future__ import annotations

import uuid
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


class ProviderError(RuntimeError):
    """Base error for provider profile and invocation failures."""


class ProviderProfileValidationError(ValueError):
    """Raised when provider profile input fails validation."""


class ProviderConfigurationError(ProviderError):
    """Raised when a provider profile cannot be configured."""


class ProviderInvocationError(ProviderError):
    """Raised when a provider invocation fails."""


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


class ProviderProfileUpdate(_FrozenContract):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    base_url: str | None = Field(default=None, min_length=1, max_length=500)
    model_name: str | None = Field(default=None, min_length=1, max_length=200)
    capabilities: dict[str, Any] | None = None
    api_key_ref: str | None = Field(default=None, min_length=1, max_length=120)
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
    is_enabled: bool


class ProviderCompletion(_FrozenContract):
    text: str
    raw_response: dict[str, Any]


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
        provider = _provider_for_profile(profile, api_key, self._transport)
        return provider.complete(prompt)

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
        )
        content = raw_response["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise ProviderInvocationError("OpenAI-compatible response did not include text content")
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
        )
        parts = raw_response.get("content")
        if not isinstance(parts, list):
            raise ProviderInvocationError(
                "Anthropic-compatible response did not include content parts",
            )
        text = "".join(
            part.get("text", "")
            for part in parts
            if isinstance(part, dict) and part.get("type") == "text"
        )
        if text == "":
            raise ProviderInvocationError(
                "Anthropic-compatible response did not include text content",
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
) -> dict[str, Any]:
    try:
        with httpx.Client(transport=transport, timeout=20.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            body = response.json()
    except httpx.HTTPError as exc:
        raise ProviderInvocationError("Provider request failed") from exc

    if not isinstance(body, dict):
        raise ProviderInvocationError("Provider response body must be an object")
    return body
