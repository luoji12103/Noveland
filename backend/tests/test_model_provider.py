from __future__ import annotations

import uuid
from typing import cast

import httpx
import pytest
from noveland.adapters import (
    AnthropicCompatibleProvider,
    OpenAICompatibleProvider,
    ProviderConfigurationError,
    ProviderErrorCode,
    ProviderInvocationError,
    ProviderProfileRecord,
    ProviderProfileService,
    ProviderTestStatus,
    ProviderType,
)
from noveland.adapters.models import ProviderProfile
from noveland.core.settings import AppSettings
from sqlalchemy import Table, create_engine
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


def test_provider_profile_service_blocks_legacy_execution_before_transport() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    engine = create_engine("sqlite+pysqlite:///:memory:")
    with Session(engine) as session:
        service = ProviderProfileService(
            session,
            AppSettings(provider_api_keys_json={"provider-ref": "secret-key"}),
            httpx.MockTransport(handler),
        )

        with pytest.raises(ProviderConfigurationError) as exc_info:
            service.invoke_profile(
                _profile_record(ProviderType.OPENAI_COMPATIBLE),
                "hello",
            )

    assert "ProviderExecutionService" in str(exc_info.value)
    assert requests == []


def test_provider_retries_transient_errors_and_classifies_final_failure() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(500)

    provider = OpenAICompatibleProvider(
        _profile_record(ProviderType.OPENAI_COMPATIBLE, retry_attempts=1),
        api_key="secret-key",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(ProviderInvocationError) as exc_info:
        provider.complete("hello")

    assert attempts == 2
    assert exc_info.value.error_code is ProviderErrorCode.TRANSIENT


def test_provider_profile_service_blocks_legacy_execution_before_secret_lookup() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with Session(engine) as session:
        service = ProviderProfileService(
            session,
            AppSettings(provider_api_keys_json={}),
        )

        with pytest.raises(ProviderConfigurationError) as exc_info:
            service.invoke_profile(
                _profile_record(ProviderType.OPENAI_COMPATIBLE, api_key_ref="missing-ref"),
                "hello",
            )

    assert "ProviderExecutionService" in str(exc_info.value)
    assert "missing-ref" not in str(exc_info.value)


def test_provider_test_profile_updates_last_test_state() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    cast(Table, ProviderProfile.__table__).create(engine)
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"content": "OK"}}]})

    with Session(engine) as session:
        profile = ProviderProfile(
            profile_key="provider-profile",
            name="Provider Profile",
            provider_type="openai_compatible",
            base_url="https://api.example.test/v1",
            model_name="test-model",
            capabilities={},
            api_key_ref="provider-ref",
        )
        session.add(profile)
        session.flush()
        result = ProviderProfileService(
            session,
            AppSettings(provider_api_keys_json={"provider-ref": "secret-key"}),
            httpx.MockTransport(handler),
        ).test_profile(profile)

        assert result.status is ProviderTestStatus.FAILED
        assert result.text_preview is None
        assert result.error_code is ProviderErrorCode.CONFIGURATION
        assert result.error_message is not None
        assert "ProviderExecutionService" in result.error_message
        assert "secret-key" not in result.error_message
        assert requests == []
        assert profile.last_tested_at is not None
        assert profile.last_test_status == "failed"
        assert profile.last_test_error == result.error_message


def _profile_record(
    provider_type: ProviderType,
    *,
    api_key_ref: str = "provider-ref",
    capabilities: dict[str, object] | None = None,
    retry_attempts: int = 1,
    rate_limit_per_minute: int | None = None,
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
        timeout_seconds=20,
        retry_attempts=retry_attempts,
        rate_limit_per_minute=rate_limit_per_minute,
        last_tested_at=None,
        last_test_status=None,
        last_test_error=None,
        is_enabled=True,
    )
