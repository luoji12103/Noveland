from __future__ import annotations

import uuid

import httpx
import pytest
from noveland.adapters import (
    AnthropicCompatibleProvider,
    OpenAICompatibleProvider,
    ProviderConfigurationError,
    ProviderProfileRecord,
    ProviderProfileService,
    ProviderType,
)
from noveland.core.settings import AppSettings
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


def test_openai_compatible_provider_extracts_text_and_uses_headers() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "OpenAI completion"}}]},
        )

    provider = OpenAICompatibleProvider(
        _profile_record(
            ProviderType.OPENAI_COMPATIBLE,
            capabilities={"headers": {"x-test-header": "1"}},
        ),
        api_key="secret-key",
        transport=httpx.MockTransport(handler),
    )

    completion = provider.complete("hello")

    assert completion.text == "OpenAI completion"
    assert str(requests[0].url) == "https://api.example.test/v1/chat/completions"
    assert requests[0].headers["authorization"] == "Bearer secret-key"
    assert requests[0].headers["x-test-header"] == "1"


def test_anthropic_compatible_provider_extracts_text() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "content": [
                    {"type": "text", "text": "Anthropic "},
                    {"type": "text", "text": "completion"},
                ],
            },
        )

    provider = AnthropicCompatibleProvider(
        _profile_record(ProviderType.ANTHROPIC_COMPATIBLE),
        api_key="secret-key",
        transport=httpx.MockTransport(handler),
    )

    completion = provider.complete("hello")

    assert completion.text == "Anthropic completion"
    assert str(requests[0].url) == "https://api.example.test/v1/messages"
    assert requests[0].headers["x-api-key"] == "secret-key"


def test_provider_service_requires_configured_api_key_ref() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with Session(engine) as session, pytest.raises(ProviderConfigurationError):
        ProviderProfileService(
            session,
            AppSettings(provider_api_keys_json={}),
        ).invoke_profile(
            _profile_record(ProviderType.OPENAI_COMPATIBLE, api_key_ref="missing-ref"),
            "hello",
        )


def _profile_record(
    provider_type: ProviderType,
    *,
    api_key_ref: str = "provider-ref",
    capabilities: dict[str, object] | None = None,
) -> ProviderProfileRecord:
    return ProviderProfileRecord(
        id=uuid.uuid4(),
        profile_key="provider-profile",
        name="Provider Profile",
        provider_type=provider_type,
        base_url="https://api.example.test/v1",
        model_name="test-model",
        capabilities=capabilities or {},
        api_key_ref=api_key_ref,
        is_enabled=True,
    )
