from __future__ import annotations

import uuid
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast

import httpx
import pytest
from fastapi.testclient import TestClient
from noveland.auth import AuthRole
from noveland.auth.contracts import AuthSessionStatus
from noveland.auth.models import AuthSession, PlatformRoleAssignment, User
from noveland.auth.services import hash_session_token
from noveland.invocations.models import (
    AgentRuntimeRunModelInvocation,
    ModelInvocation,
    ModelInvocationTag,
    PromptSnapshot,
    PromptTemplate,
)
from noveland.media.models import (
    MediaAsset,
    MediaAssetCollection,
    MediaAssetCollectionItem,
    MediaAssetContext,
    MediaAssetInput,
    MediaAssetTag,
    MediaJob,
    MediaObject,
    MediaReference,
)
from noveland.media.storage import LocalMediaObjectStorage
from noveland.providers.models import (
    ProviderBudgetPolicy,
    ProviderCapability,
    ProviderHealthCheck,
    ProviderIntegration,
)
from noveland.services.api.app import create_app
from noveland.services.api.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from noveland.services.api.dependencies import get_db_session
from noveland.services.api.providers import _media_storage
from noveland.worlds.models import World, Worldline, WorldMembership
from noveland.worlds.worldlines import ensure_primary_worldline
from sqlalchemy import Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_providers_api_crud_health_and_fake_invocation() -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test")
    world_id = _seed_world(engine, admin_id)
    worldline_id = _seed_worldline(engine, world_id)
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _authenticate(client, admin_token)

    created = client.post(
        f"/worlds/{world_id}/providers",
        json={
            "scope_kind": "world",
            "provider_kind": "image_generation",
            "adapter_kind": "fake",
            "provider_key": "fake-image",
            "display_name": "Fake Image",
            "auth_ref": "secret:fake",
            "capabilities": [
                {
                    "capability_key": "supports_image_generation",
                    "capability_json": {"value": True},
                }
            ],
        },
    )
    provider_id = created.json()["id"]
    listed = client.get(f"/worlds/{world_id}/providers", params={"adapter_kind": "fake"})
    capabilities = client.get(f"/worlds/{world_id}/providers/{provider_id}/capabilities")
    health = client.post(f"/worlds/{world_id}/providers/{provider_id}/health-check")
    invocation = client.post(
        f"/worlds/{world_id}/providers/test-invocation",
        json={
            "worldline_id": str(worldline_id),
            "provider_id": provider_id,
            "input_text": "draw this",
        },
    )

    assert created.status_code == 201
    assert created.json()["auth_ref_configured"] is True
    assert created.json()["auth_ref"] == "secret:fake"
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [provider_id]
    assert capabilities.status_code == 200
    assert capabilities.json()[0]["capability_key"] == "supports_image_generation"
    assert health.status_code == 201
    assert health.json()["status"] == "healthy"
    assert invocation.status_code == 201
    assert invocation.json()["invocation"]["media_asset_id"] is not None
    assert invocation.json()["output_objects"][0]["mime_type"] == "image/png"

    with Session(engine) as session:
        assert session.scalars(select(ModelInvocation)).one().media_asset_id is not None
        assert session.scalars(select(MediaObject)).one().storage_uri.startswith("media://")


def test_providers_api_acl_and_global_platform_admin() -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    platform_id, platform_token = _seed_user(
        engine,
        "platform@example.test",
        platform_admin=True,
    )
    world_id = _seed_world(engine, admin_id)
    _seed_worldline(engine, world_id)
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)

    _authenticate(client, member_token)
    member_create = client.post(
        f"/worlds/{world_id}/providers",
        json={
            "scope_kind": "world",
            "provider_kind": "text_generation",
            "adapter_kind": "fake",
            "provider_key": "member-fake",
            "display_name": "Member Fake",
        },
    )

    _authenticate(client, admin_token)
    admin_global = client.post(
        f"/worlds/{world_id}/providers",
        json={
            "scope_kind": "global",
            "provider_kind": "text_generation",
            "adapter_kind": "fake",
            "provider_key": "global-fake",
            "display_name": "Global Fake",
        },
    )

    _authenticate(client, platform_token)
    platform_global = client.post(
        f"/worlds/{world_id}/providers",
        json={
            "scope_kind": "global",
            "provider_kind": "text_generation",
            "adapter_kind": "fake",
            "provider_key": "global-fake",
            "display_name": "Global Fake",
            "visibility": "developer_only",
        },
    )

    assert platform_id
    assert member_create.status_code == 403
    assert admin_global.status_code == 403
    assert platform_global.status_code == 201


def test_provider_api_restricts_developer_only_visibility_to_platform_admin() -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test")
    platform_id, platform_token = _seed_user(
        engine,
        "platform@example.test",
        platform_admin=True,
    )
    world_id = _seed_world(engine, admin_id)
    _seed_worldline(engine, world_id)
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, platform_id, AuthRole.WORLD_ADMIN)

    _authenticate(client, admin_token)
    admin_create = client.post(
        f"/worlds/{world_id}/providers",
        json={
            "scope_kind": "world",
            "provider_kind": "text_generation",
            "adapter_kind": "fake",
            "provider_key": "hidden-fake",
            "display_name": "Hidden Fake",
            "visibility": "developer_only",
        },
    )
    created = client.post(
        f"/worlds/{world_id}/providers",
        json={
            "scope_kind": "world",
            "provider_kind": "text_generation",
            "adapter_kind": "fake",
            "provider_key": "safe-fake",
            "display_name": "Safe Fake",
        },
    )
    admin_update = client.patch(
        f"/worlds/{world_id}/providers/{created.json()['id']}",
        json={"visibility": "hidden"},
    )

    _authenticate(client, platform_token)
    platform_update = client.patch(
        f"/worlds/{world_id}/providers/{created.json()['id']}",
        json={"visibility": "developer_only"},
    )

    assert admin_create.status_code == 403
    assert created.status_code == 201
    assert admin_update.status_code == 403
    assert platform_update.status_code == 200
    assert platform_update.json()["visibility"] == "developer_only"


def test_provider_test_execution_respects_world_admin_visibility() -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test")
    platform_id, platform_token = _seed_user(
        engine,
        "platform@example.test",
        platform_admin=True,
    )
    world_id = _seed_world(engine, admin_id)
    worldline_id = _seed_worldline(engine, world_id)
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, platform_id, AuthRole.WORLD_ADMIN)

    _authenticate(client, platform_token)
    platform_provider = client.post(
        f"/worlds/{world_id}/providers",
        json={
            "scope_kind": "global",
            "provider_kind": "text_generation",
            "adapter_kind": "fake",
            "provider_key": "platform-text",
            "display_name": "Platform Text",
            "visibility": "developer_only",
            "capabilities": [
                {"capability_key": "supports_text_generation", "capability_json": {"value": True}}
            ],
        },
    )
    provider_id = platform_provider.json()["id"]

    _authenticate(client, admin_token)
    hidden_detail = client.get(
        f"/worlds/{world_id}/providers/{provider_id}",
        params={"include_hidden": True},
    )
    smoke = client.post(
        f"/worlds/{world_id}/providers/{provider_id}/smoke-test",
        json={"worldline_id": str(worldline_id), "input_text": "operator smoke"},
    )
    explicit_invocation = client.post(
        f"/worlds/{world_id}/providers/test-invocation",
        json={
            "worldline_id": str(worldline_id),
            "provider_id": provider_id,
            "input_text": "operator test",
        },
    )
    routed_invocation = client.post(
        f"/worlds/{world_id}/providers/test-invocation",
        json={
            "worldline_id": str(worldline_id),
            "provider_kind": "text_generation",
            "input_text": "operator auto test",
        },
    )

    assert platform_provider.status_code == 201
    assert hidden_detail.status_code == 404
    assert smoke.status_code == 404
    assert explicit_invocation.status_code == 404
    assert routed_invocation.status_code == 404
    with Session(engine) as session:
        assert session.scalars(select(ProviderHealthCheck)).all() == []
        assert session.scalars(select(ModelInvocation)).all() == []
        assert session.scalars(select(PromptSnapshot)).all() == []


def test_provider_api_rejects_secret_config_and_exposes_auth_ref_only() -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test")
    world_id = _seed_world(engine, admin_id)
    _seed_worldline(engine, world_id)
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _authenticate(client, admin_token)

    rejected = client.post(
        f"/worlds/{world_id}/providers",
        json={
            "scope_kind": "world",
            "provider_kind": "image_generation",
            "adapter_kind": "fake",
            "provider_key": "bad",
            "display_name": "Bad",
            "config_json": {"api_key": "sk-secret"},
        },
    )
    created = client.post(
        f"/worlds/{world_id}/providers",
        json={
            "scope_kind": "world",
            "provider_kind": "image_generation",
            "adapter_kind": "fake",
            "provider_key": "safe",
            "display_name": "Safe",
            "auth_ref": "env:OPENAI_API_KEY",
        },
    )

    assert rejected.status_code == 422
    assert "sensitive key" in rejected.text
    assert created.status_code == 201
    assert created.json()["auth_ref"] == "env:OPENAI_API_KEY"
    assert "sk-secret" not in created.text

    rejected_update = client.patch(
        f"/worlds/{world_id}/providers/{created.json()['id']}",
        json={"default_params_json": {"headers": {"authorization": "Bearer sk-secret"}}},
    )
    rotated = client.patch(
        f"/worlds/{world_id}/providers/{created.json()['id']}",
        json={"auth_ref": "env:MIMO_API_KEY"},
    )

    assert rejected_update.status_code == 422
    assert "sensitive key" in rejected_update.text
    assert rotated.status_code == 200
    assert rotated.json()["auth_ref"] == "env:MIMO_API_KEY"
    assert "sk-secret" not in rotated.text
    with Session(engine) as session:
        model = session.get(ProviderIntegration, uuid.UUID(created.json()["id"]))
        assert model is not None
        assert model.auth_ref == "env:MIMO_API_KEY"
        assert "sk-secret" not in str(model.config_json)
        assert "sk-secret" not in str(model.default_params_json)


def test_provider_smoke_missing_auth_writes_safe_health_and_invocation() -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test")
    world_id = _seed_world(engine, admin_id)
    worldline_id = _seed_worldline(engine, world_id)
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _authenticate(client, admin_token)
    created = client.post(
        f"/worlds/{world_id}/providers",
        json={
            "scope_kind": "world",
            "provider_kind": "image_generation",
            "adapter_kind": "openai",
            "provider_key": "openai-image",
            "display_name": "OpenAI Image",
            "auth_ref": "env:MISSING_OPENAI_API_KEY",
        },
    )
    provider_id = created.json()["id"]

    smoke = client.post(
        f"/worlds/{world_id}/providers/{provider_id}/smoke-test",
        json={"worldline_id": str(worldline_id), "input_text": "draw"},
    )
    health = client.get(f"/worlds/{world_id}/providers/{provider_id}/health-checks")

    assert smoke.status_code == 201
    assert smoke.json()["smoke_status"] == "failed"
    assert "auth_missing" in smoke.text
    assert health.status_code == 200
    assert health.json()[0]["metadata_json"] == {"smoke_test": True, "status": "failed"}
    with Session(engine) as session:
        invocation = session.scalars(select(ModelInvocation)).one()
        snapshot = session.scalars(select(PromptSnapshot)).one()
        assert invocation.status == "failed"
        assert "MISSING_OPENAI_API_KEY" not in str(invocation.request_params_json)
        assert "MISSING_OPENAI_API_KEY" not in str(snapshot.raw_request_json)


def test_provider_smoke_openai_image_uses_env_secret_without_persisting_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test")
    world_id = _seed_world(engine, admin_id)
    worldline_id = _seed_worldline(engine, world_id)
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _authenticate(client, admin_token)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-phase8-secret")
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers["authorization"]
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "b64_json": (
                            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAA"
                            "DUlEQVR4nGP4z8DwHwAFgwJ/lq9S9wAAAABJRU5ErkJggg=="
                        )
                    }
                ]
            },
        )

    monkeypatch.setattr(httpx, "Client", _httpx_client_factory(handler))
    created = client.post(
        f"/worlds/{world_id}/providers",
        json={
            "scope_kind": "world",
            "provider_kind": "image_generation",
            "adapter_kind": "openai",
            "provider_key": "openai-image",
            "display_name": "OpenAI Image",
            "base_url": "https://gateway.example/v1",
            "auth_ref": "env:OPENAI_API_KEY",
        },
    )
    provider_id = created.json()["id"]

    smoke = client.post(
        f"/worlds/{world_id}/providers/{provider_id}/smoke-test",
        json={
            "worldline_id": str(worldline_id),
            "input_text": "draw",
            "request_json": {"output_format": "png"},
        },
    )
    health = client.get(f"/worlds/{world_id}/providers/{provider_id}/health-checks")

    assert smoke.status_code == 201
    assert smoke.json()["smoke_status"] == "succeeded"
    assert smoke.json()["output_asset"] is not None
    assert captured["authorization"] == "Bearer sk-phase8-secret"
    assert health.status_code == 200
    assert health.json()[0]["metadata_json"] == {"smoke_test": True, "status": "succeeded"}
    with Session(engine) as session:
        invocation = session.scalars(select(ModelInvocation)).one()
        snapshot = session.scalars(select(PromptSnapshot)).one()
        assert invocation.status == "succeeded"
        assert invocation.media_asset_id is not None
        assert "sk-phase8-secret" not in str(invocation.request_params_json)
        assert "sk-phase8-secret" not in str(invocation.response_metadata_json)
        assert "sk-phase8-secret" not in str(snapshot.raw_request_json)
        assert "sk-phase8-secret" not in str(snapshot.raw_response_json)


def test_provider_templates_and_model_discovery_are_admin_scoped_and_redacted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id = _seed_world(engine, admin_id)
    _seed_worldline(engine, world_id)
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-model-discovery-secret")
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["authorization"]
        return httpx.Response(
            200,
            json={"data": [{"id": "alpha-model"}, {"id": "beta-model"}]},
        )

    monkeypatch.setattr(httpx, "Client", _httpx_client_factory(handler))

    _authenticate(client, member_token)
    forbidden_templates = client.get(f"/worlds/{world_id}/providers/templates")

    _authenticate(client, admin_token)
    templates = client.get(f"/worlds/{world_id}/providers/templates")
    created = client.post(
        f"/worlds/{world_id}/providers",
        json={
            "scope_kind": "world",
            "provider_kind": "text_generation",
            "adapter_kind": "openai_compatible",
            "provider_key": "openai-compatible-llm",
            "display_name": "OpenAI-compatible LLM",
            "base_url": "https://gateway.example/v1",
            "auth_ref": "env:OPENAI_API_KEY",
            "config_json": {"model_discovery_path": "/models"},
        },
    )
    discovery = client.post(
        f"/worlds/{world_id}/providers/model-discovery",
        json={"provider_id": created.json()["id"]},
    )

    template_keys = {item["template_key"] for item in templates.json()}
    assert forbidden_templates.status_code == 403
    assert templates.status_code == 200
    assert {
        "openai-compatible-llm",
        "anthropic-compatible-llm",
        "mimo-v2-5-tts",
        "mimo-v2-5-asr",
        "z-image",
        "gpt-image",
        "comfyui",
        "openai-compatible-image",
        "generic-image-custom-http",
    }.issubset(template_keys)
    assert "sk-model-discovery-secret" not in templates.text
    assert created.status_code == 201
    assert discovery.status_code == 200
    assert discovery.json()["discovery_status"] == "succeeded"
    assert discovery.json()["models"] == ["alpha-model", "beta-model"]
    assert discovery.json()["manual_fallback_allowed"] is True
    assert captured["url"] == "https://gateway.example/v1/models"
    assert captured["authorization"] == "Bearer sk-model-discovery-secret"
    assert "sk-model-discovery-secret" not in discovery.text


def test_provider_model_discovery_failure_keeps_manual_fallback_safe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test")
    world_id = _seed_world(engine, admin_id)
    _seed_worldline(engine, world_id)
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _authenticate(client, admin_token)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-failing-discovery-secret")

    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(httpx, "Client", _httpx_client_factory(handler))
    discovery = client.post(
        f"/worlds/{world_id}/providers/model-discovery",
        json={
            "provider_kind": "text_generation",
            "adapter_kind": "openai_compatible",
            "base_url": "https://gateway.example/v1",
            "auth_ref": "env:OPENAI_API_KEY",
            "config_json": {"model_discovery_path": "/models"},
        },
    )

    assert discovery.status_code == 200
    assert discovery.json()["discovery_status"] == "failed"
    assert discovery.json()["manual_fallback_allowed"] is True
    assert discovery.json()["models"] == []
    assert discovery.json()["error_message"] == (
        "Model discovery failed. Enter a model name manually."
    )
    assert "sk-failing-discovery-secret" not in discovery.text
    assert "OPENAI_API_KEY" not in discovery.text


def test_provider_health_check_records_safe_auth_status() -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test")
    world_id = _seed_world(engine, admin_id)
    _seed_worldline(engine, world_id)
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _authenticate(client, admin_token)
    created = client.post(
        f"/worlds/{world_id}/providers",
        json={
            "scope_kind": "world",
            "provider_kind": "text_to_speech",
            "adapter_kind": "openai",
            "provider_key": "openai-speech",
            "display_name": "OpenAI Speech",
            "auth_ref": "env:MISSING_OPENAI_API_KEY",
        },
    )
    provider_id = created.json()["id"]

    health = client.post(f"/worlds/{world_id}/providers/{provider_id}/health-check")

    assert health.status_code == 201
    assert health.json()["status"] == "unhealthy"
    assert health.json()["metadata_json"]["auth_missing"] is True


def test_disabled_provider_smoke_test_records_safe_failed_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test")
    world_id = _seed_world(engine, admin_id)
    worldline_id = _seed_worldline(engine, world_id)
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _authenticate(client, admin_token)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-disabled-smoke-secret")

    created = client.post(
        f"/worlds/{world_id}/providers",
        json={
            "scope_kind": "world",
            "provider_kind": "text_generation",
            "adapter_kind": "fake",
            "provider_key": "disabled-fake",
            "display_name": "Disabled Fake",
            "auth_ref": "env:OPENAI_API_KEY",
            "status": "disabled",
        },
    )
    provider_id = created.json()["id"]

    smoke = client.post(
        f"/worlds/{world_id}/providers/{provider_id}/smoke-test",
        json={"worldline_id": str(worldline_id), "input_text": "blocked"},
    )
    health = client.post(f"/worlds/{world_id}/providers/{provider_id}/health-check")
    health_list = client.get(f"/worlds/{world_id}/providers/{provider_id}/health-checks")

    assert smoke.status_code == 201
    assert smoke.json()["smoke_status"] == "failed"
    assert smoke.json()["invocation"]["status"] == "failed"
    assert smoke.json()["invocation"]["error_text"] == "provider integration is disabled"
    assert "sk-disabled-smoke-secret" not in smoke.text
    assert health.status_code == 201
    assert health.json()["status"] == "unhealthy"
    assert health.json()["metadata_json"]["execution_blocked"] is True
    assert health.json()["metadata_json"]["reason"] == "provider_not_active"
    assert health_list.status_code == 200
    assert "sk-disabled-smoke-secret" not in health_list.text
    with Session(engine) as session:
        invocation = session.scalars(select(ModelInvocation)).one()
        snapshot = session.scalars(select(PromptSnapshot)).one()
        assert invocation.status == "failed"
        assert invocation.request_params_json is not None
        assert invocation.request_params_json["provider_status"] == "disabled"
        assert snapshot.raw_request_json is not None
        assert snapshot.raw_request_json["provider_status"] == "disabled"


def test_provider_budget_policy_emergency_stop_blocks_smoke_and_reports_quota() -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test")
    world_id = _seed_world(engine, admin_id)
    worldline_id = _seed_worldline(engine, world_id)
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _authenticate(client, admin_token)
    created = client.post(
        f"/worlds/{world_id}/providers",
        json={
            "scope_kind": "world",
            "provider_kind": "text_generation",
            "adapter_kind": "fake",
            "provider_key": "budget-fake",
            "display_name": "Budget Fake",
        },
    )
    provider_id = created.json()["id"]

    policy = client.post(
        f"/worlds/{world_id}/providers/budget-policies",
        json={
            "provider_id": provider_id,
            "policy_key": "provider-stop",
            "emergency_stop_enabled": True,
            "limits_json": {"max_daily_invocations": 10},
        },
    )
    quota = client.get(
        f"/worlds/{world_id}/providers/quota-status",
        params={"provider_id": provider_id},
    )
    smoke = client.post(
        f"/worlds/{world_id}/providers/{provider_id}/smoke-test",
        json={"worldline_id": str(worldline_id), "input_text": "blocked"},
    )
    unblocked = client.patch(
        f"/worlds/{world_id}/providers/budget-policies/{policy.json()['id']}",
        json={"emergency_stop_enabled": False},
    )

    assert policy.status_code == 201
    assert policy.json()["emergency_stop_enabled"] is True
    assert quota.status_code == 200
    assert quota.json()["emergency_stop_active"] is True
    assert quota.json()["blocked_reasons"] == ["emergency_stop"]
    assert "storage_uri" not in quota.text
    assert smoke.status_code == 201
    assert smoke.json()["smoke_status"] == "failed"
    assert smoke.json()["invocation"]["status"] == "failed"
    assert "emergency_stop" in smoke.json()["invocation"]["error_text"]
    assert unblocked.status_code == 200
    assert unblocked.json()["emergency_stop_enabled"] is False


def test_provider_quota_status_supports_player_and_capability_filters() -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test")
    world_id = _seed_world(engine, admin_id)
    worldline_id = _seed_worldline(engine, world_id)
    player_a = uuid.uuid4()
    player_b = uuid.uuid4()
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _authenticate(client, admin_token)
    created = client.post(
        f"/worlds/{world_id}/providers",
        json={
            "scope_kind": "world",
            "provider_kind": "image_generation",
            "adapter_kind": "fake",
            "provider_key": "quota-image",
            "display_name": "Quota Image",
        },
    )
    provider_id = created.json()["id"]
    policy = client.post(
        f"/worlds/{world_id}/providers/budget-policies",
        json={
            "provider_id": provider_id,
            "policy_key": "player-capability-limit",
            "limits_json": {"default_player": {"max_daily_invocations": 1}},
        },
    )
    first = client.post(
        f"/worlds/{world_id}/providers/{provider_id}/smoke-test",
        json={
            "worldline_id": str(worldline_id),
            "capability_key": "image.generate",
            "player_actor_id": str(player_a),
            "input_text": "draw first",
        },
    )
    blocked = client.post(
        f"/worlds/{world_id}/providers/{provider_id}/smoke-test",
        json={
            "worldline_id": str(worldline_id),
            "capability_key": "image.generate",
            "player_actor_id": str(player_a),
            "input_text": "draw blocked",
        },
    )
    other_player = client.post(
        f"/worlds/{world_id}/providers/{provider_id}/smoke-test",
        json={
            "worldline_id": str(worldline_id),
            "capability_key": "image.generate",
            "player_actor_id": str(player_b),
            "input_text": "draw allowed",
        },
    )
    quota = client.get(
        f"/worlds/{world_id}/providers/quota-status",
        params={
            "provider_id": provider_id,
            "player_actor_id": str(player_a),
            "capability_key": "image.generate",
        },
    )

    assert policy.status_code == 201
    assert first.status_code == 201
    assert first.json()["smoke_status"] == "succeeded"
    assert blocked.status_code == 201
    assert blocked.json()["smoke_status"] == "failed"
    assert "daily_invocation_limit" in blocked.json()["invocation"]["error_text"]
    assert other_player.status_code == 201
    assert other_player.json()["smoke_status"] == "succeeded"
    assert quota.status_code == 200
    assert quota.json()["player_actor_id"] == str(player_a)
    assert quota.json()["capability_key"] == "image.generate"
    assert quota.json()["blocked_reasons"] == ["daily_invocation_limit"]
    assert "storage_uri" not in quota.text
    assert "raw_prompt" not in quota.text
    assert "secret" not in quota.text


def test_provider_reliability_fallback_and_requeue_api_are_safe() -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id = _seed_world(engine, admin_id)
    worldline_id = _seed_worldline(engine, world_id)
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    _authenticate(client, admin_token)
    primary = client.post(
        f"/worlds/{world_id}/providers",
        json={
            "scope_kind": "world",
            "provider_kind": "image_generation",
            "adapter_kind": "fake",
            "provider_key": "primary-image",
            "display_name": "Primary Image",
        },
    )
    fallback = client.post(
        f"/worlds/{world_id}/providers",
        json={
            "scope_kind": "world",
            "provider_kind": "image_generation",
            "adapter_kind": "fake",
            "provider_key": "fallback-image",
            "display_name": "Fallback Image",
        },
    )
    primary_id = primary.json()["id"]
    fallback_id = fallback.json()["id"]
    configured = client.patch(
        f"/worlds/{world_id}/providers/{primary_id}",
        json={
            "config_json": {
                "reliability": {
                    "manual_fallback_enabled": True,
                    "fallback_provider_ids": [fallback_id],
                }
            }
        },
    )
    with Session(engine) as session:
        for _ in range(3):
            session.add(
                ProviderHealthCheck(
                    id=uuid.uuid4(),
                    provider_integration_id=uuid.UUID(primary_id),
                    status="unhealthy",
                    checked_at=datetime.now(UTC),
                    metadata_json={"reason": "timeout"},
                )
            )
        session.add(
            MediaJob(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                job_kind="image_generation",
                provider_kind="image_generation",
                status="failed",
                provider_config_json={"provider_id": fallback_id},
                request_json={"prompt": "safe"},
                result_json={},
                error_text="timeout",
                created_by_actor_ref="test",
            )
        )
        job_id = session.scalar(select(MediaJob.id))
        session.commit()
    assert job_id is not None

    _authenticate(client, member_token)
    forbidden = client.get(f"/worlds/{world_id}/providers/{primary_id}/reliability")

    _authenticate(client, admin_token)
    report = client.get(f"/worlds/{world_id}/providers/{primary_id}/reliability")
    plan = client.post(
        f"/worlds/{world_id}/providers/{primary_id}/fallback-plan",
        json={
            "fallback_provider_id": fallback_id,
            "worldline_id": str(worldline_id),
            "capability_key": "image.generate",
        },
    )
    smoke = client.post(
        f"/worlds/{world_id}/providers/{primary_id}/smoke-test",
        json={
            "worldline_id": str(worldline_id),
            "fallback_provider_id": fallback_id,
            "fallback_reason": "manual provider outage",
            "capability_key": "image.generate",
            "input_text": "draw via fallback",
        },
    )
    requeue = client.post(
        f"/worlds/{world_id}/providers/{fallback_id}/media-jobs/{job_id}/requeue",
        json={"reason": "manual requeue after provider recovery"},
    )

    assert configured.status_code == 200
    assert forbidden.status_code == 403
    assert report.status_code == 200
    assert report.json()["degraded_mode_active"] is True
    assert report.json()["manual_fallback_enabled"] is True
    assert fallback_id in report.json()["fallback_provider_ids"]
    assert plan.status_code == 200
    assert plan.json()["allowed"] is True
    assert plan.json()["automatic_fallback_enabled"] is False
    assert smoke.status_code == 201
    assert smoke.json()["smoke_status"] == "succeeded"
    assert smoke.json()["provider"]["id"] == fallback_id
    assert smoke.json()["invocation"]["request_params_json"]["fallback_selected"] is True
    assert requeue.status_code == 201
    assert requeue.json()["provider_execution"] is False
    assert requeue.json()["requeued_job"]["status"] == "queued"
    assert requeue.json()["requeued_job"]["provider_config_json"][
        "provider_reliability_requeue"
    ] is True
    assert "storage_uri" not in report.text
    assert "raw_prompt" not in plan.text
    assert "secret" not in smoke.text


class _ProviderApiClient(TestClient):
    media_storage: LocalMediaObjectStorage


def _client_with_database() -> tuple[_ProviderApiClient, Engine]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    _create_tables(engine)
    app = create_app()

    def override_get_db_session() -> Iterator[Session]:
        with Session(engine) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    app.dependency_overrides[get_db_session] = override_get_db_session
    storage_tmp = TemporaryDirectory()
    storage = LocalMediaObjectStorage(Path(storage_tmp.name))
    app.dependency_overrides[_media_storage] = lambda: storage
    app.state._provider_media_storage_tmp = storage_tmp
    client = _ProviderApiClient(app)
    client.media_storage = storage
    return client, engine


def _create_tables(engine: Engine) -> None:
    for table in (
        cast(Table, User.__table__),
        cast(Table, AuthSession.__table__),
        cast(Table, PlatformRoleAssignment.__table__),
        cast(Table, World.__table__),
        cast(Table, Worldline.__table__),
        cast(Table, WorldMembership.__table__),
        cast(Table, ProviderIntegration.__table__),
        cast(Table, ProviderCapability.__table__),
        cast(Table, ProviderHealthCheck.__table__),
        cast(Table, ProviderBudgetPolicy.__table__),
        cast(Table, MediaJob.__table__),
        cast(Table, MediaAsset.__table__),
        cast(Table, MediaObject.__table__),
        cast(Table, MediaReference.__table__),
        cast(Table, MediaAssetContext.__table__),
        cast(Table, MediaAssetInput.__table__),
        cast(Table, MediaAssetTag.__table__),
        cast(Table, MediaAssetCollection.__table__),
        cast(Table, MediaAssetCollectionItem.__table__),
        cast(Table, ModelInvocation.__table__),
        cast(Table, PromptTemplate.__table__),
        cast(Table, PromptSnapshot.__table__),
        cast(Table, AgentRuntimeRunModelInvocation.__table__),
        cast(Table, ModelInvocationTag.__table__),
    ):
        table.create(engine)


def _seed_user(
    engine: Engine,
    email: str,
    *,
    platform_admin: bool = False,
) -> tuple[uuid.UUID, str]:
    user_id = uuid.uuid4()
    token = f"token-{user_id}"
    now = datetime.now(UTC)
    with Session(engine) as session:
        session.add(User(id=user_id, email=email, display_name=email, is_active=True))
        session.add(
            AuthSession(
                id=uuid.uuid4(),
                user_id=user_id,
                token_hash=hash_session_token(token),
                status=AuthSessionStatus.ACTIVE.value,
                expires_at=now + timedelta(hours=1),
            )
        )
        if platform_admin:
            session.add(
                PlatformRoleAssignment(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    role=AuthRole.PLATFORM_ADMIN.value,
                    assigned_at=now,
                )
            )
        session.commit()
    return user_id, token


def _seed_world(engine: Engine, owner_user_id: uuid.UUID) -> uuid.UUID:
    world_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            World(
                id=world_id,
                owner_user_id=owner_user_id,
                slug=f"world-{world_id.hex[:8]}",
                name="World",
                is_active=True,
            )
        )
        session.commit()
    return world_id


def _seed_worldline(engine: Engine, world_id: uuid.UUID) -> uuid.UUID:
    with Session(engine) as session:
        primary = ensure_primary_worldline(session, world_id)
        session.commit()
        return primary.id


def _add_membership(
    engine: Engine,
    world_id: uuid.UUID,
    user_id: uuid.UUID,
    role: AuthRole,
) -> None:
    with Session(engine) as session:
        session.add(
            WorldMembership(
                id=uuid.uuid4(),
                world_id=world_id,
                user_id=user_id,
                role=role.value,
            )
        )
        session.commit()


def _authenticate(client: TestClient, token: str) -> None:
    client.cookies.clear()
    client.headers.clear()
    client.cookies.set(SESSION_COOKIE_NAME, token)
    client.cookies.set(CSRF_COOKIE_NAME, "csrf-token")
    client.headers.update({CSRF_HEADER_NAME: "csrf-token"})


def _httpx_client_factory(
    handler: Callable[[httpx.Request], httpx.Response],
) -> Callable[..., httpx.Client]:
    original_client = httpx.Client

    def create_client(**_: object) -> httpx.Client:
        return original_client(transport=httpx.MockTransport(handler))

    return create_client
