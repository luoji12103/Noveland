from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from fastapi.testclient import TestClient
from noveland.auth import AuthRole
from noveland.auth.contracts import AuthSessionStatus
from noveland.auth.models import AuthSession, PlatformRoleAssignment, User
from noveland.auth.services import hash_session_token
from noveland.core.database import import_model_modules
from noveland.providers.models import ProviderCapability, ProviderIntegration
from noveland.services.api.app import create_app
from noveland.services.api.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from noveland.services.api.dependencies import get_db_session
from noveland.worlds.models import World, Worldline, WorldMembership
from sqlalchemy import Table, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

FORBIDDEN_MARKERS = (
    "storage_uri",
    "media://",
    "file://",
    "s3://",
    "gs://",
    "base64",
    "raw_prompt",
    "raw_output",
    "prompt_snapshot",
    "bearer_token",
    "authorization",
    "secret-value",
    "/tmp/",
    "/root/",
)


def test_package_contract_validates_plugin_and_provider_metadata() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id = _seed_world_graph(engine, owner_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _seed_provider(engine, world_id)

    response = _authenticated_post(
        client,
        owner_token,
        f"/worlds/{world_id}/package-contracts/validate",
        _valid_contract(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["blocker_count"] == 0
    assert body["warning_count"] == 0
    assert body["safety_review_status"] == "pending_review"
    assert body["provider_execution"] is False
    assert body["marketplace_install"] is False
    assert body["resolved_secrets"] is False
    _assert_no_forbidden_markers(body)


def test_package_contract_reports_registry_and_secret_issues() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id = _seed_world_graph(engine, owner_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    payload = _valid_contract()
    payload["plugins"][0]["plugin_identifier"] = "missing.plugin"
    payload["providers"][0]["config_template"] = {"nested": {"api_key": "secret-value"}}
    payload["providers"][0]["auth_ref"] = "plain-secret-value"

    response = _authenticated_post(
        client,
        owner_token,
        f"/worlds/{world_id}/package-contracts/validate",
        payload,
    )

    assert response.status_code == 200
    body = response.json()
    codes = {issue["code"] for issue in body["issues"]}
    assert body["safety_review_status"] == "blocked"
    assert "missing_plugin" in codes
    assert "forbidden_config_key" in codes
    assert "invalid_auth_ref" in codes
    assert body["provider_execution"] is False
    assert body["marketplace_install"] is False


def test_provider_config_export_is_sanitized_and_does_not_resolve_secret() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id = _seed_world_graph(engine, owner_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    provider_id = _seed_provider(engine, world_id)

    response = _authenticated_get(
        client,
        owner_token,
        f"/worlds/{world_id}/package-contracts/provider-config-export",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provider_execution"] is False
    assert body["marketplace_install"] is False
    assert body["resolved_secrets"] is False
    assert len(body["providers"]) == 1
    exported = body["providers"][0]
    assert exported["provider_id"] == str(provider_id)
    assert exported["auth_ref"] == "env:OPENAI_API_KEY"
    assert exported["auth_ref_configured"] is True
    assert exported["config_json"] == {"metadata": {"safe_note": "[redacted]"}}
    assert exported["default_params_json"] == {"temperature": 0.4}
    assert exported["capabilities"][0]["capability_key"] == "supports_text_generation"
    _assert_no_forbidden_markers(body)


def test_package_contract_routes_require_world_admin_access() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id = _seed_world_graph(engine, owner_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)

    unauthenticated = client.post(
        f"/worlds/{world_id}/package-contracts/validate",
        json=_valid_contract(),
    )
    member = _authenticated_post(
        client,
        member_token,
        f"/worlds/{world_id}/package-contracts/validate",
        _valid_contract(),
    )
    owner = _authenticated_post(
        client,
        owner_token,
        f"/worlds/{world_id}/package-contracts/validate",
        _valid_contract(),
    )

    assert unauthenticated.status_code == 401
    assert member.status_code == 403
    assert owner.status_code == 200


def test_package_contract_routes_do_not_replace_existing_provider_routes() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id = _seed_world_graph(engine, owner_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _seed_provider(engine, world_id)

    _authenticate(client, owner_token)
    providers = client.get(f"/worlds/{world_id}/providers")

    assert providers.status_code == 200
    assert providers.json()[0]["provider_key"] == "openai-text"
    assert "package_contract" not in json.dumps(providers.json()).lower()


def _client_with_database() -> tuple[TestClient, Engine]:
    import_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    _create_required_tables(engine)

    def override_session() -> Iterator[Session]:
        session = Session(engine)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[get_db_session] = override_session
    return TestClient(app), engine


def _create_required_tables(engine: Engine) -> None:
    for table in (
        cast(Table, User.__table__),
        cast(Table, AuthSession.__table__),
        cast(Table, PlatformRoleAssignment.__table__),
        cast(Table, World.__table__),
        cast(Table, Worldline.__table__),
        cast(Table, WorldMembership.__table__),
        cast(Table, ProviderIntegration.__table__),
        cast(Table, ProviderCapability.__table__),
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
        session.add(User(id=user_id, email=email, display_name=email.split("@")[0], is_active=True))
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


def _seed_world_graph(engine: Engine, owner_id: uuid.UUID) -> uuid.UUID:
    world_id = uuid.uuid4()
    worldline_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            World(
                id=world_id,
                owner_user_id=owner_id,
                slug=f"package-contract-{world_id.hex[:8]}",
                name="Package Contract World",
                is_active=True,
            )
        )
        session.add(
            Worldline(
                id=worldline_id,
                world_id=world_id,
                worldline_key="primary",
                name="Primary",
                status="active",
                created_by_actor_ref="system:test",
                metadata_json={},
            )
        )
        session.commit()
    return world_id


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


def _seed_provider(engine: Engine, world_id: uuid.UUID) -> uuid.UUID:
    provider_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            ProviderIntegration(
                id=provider_id,
                world_id=world_id,
                scope_kind="world",
                scope_key=f"world:{world_id}",
                provider_kind="text_generation",
                adapter_kind="openai",
                provider_key="openai-text",
                display_name="OpenAI Text",
                base_url=None,
                auth_ref="env:OPENAI_API_KEY",
                config_json={
                    "metadata": {
                        "safe_note": "uses storage_uri media://internal as redaction test"
                    },
                    "password": "secret-value",
                },
                default_params_json={"temperature": 0.4},
                status="active",
                visibility="world_admin",
            )
        )
        session.add(
            ProviderCapability(
                id=uuid.uuid4(),
                provider_integration_id=provider_id,
                capability_key="supports_text_generation",
                capability_json={"mode": "chat"},
            )
        )
        session.commit()
    return provider_id


def _valid_contract() -> dict[str, Any]:
    return {
        "metadata": {
            "package_key": "provider-contract",
            "version": "0.1.0",
            "display_name": "Provider Contract",
            "publisher_ref": "builtin",
            "safety_review_status": "pending_review",
            "safety_notes": {"review": "safe config only"},
        },
        "plugins": [
            {
                "plugin_identifier": "builtin.openai_compatible",
                "category": "model_provider",
                "version": "0.1.0",
                "capabilities": ["chat.completions"],
                "config_template": {"headers": {"X-Test": "1"}},
            }
        ],
        "providers": [
            {
                "provider_kind": "text_generation",
                "adapter_kind": "openai",
                "capability_keys": ["supports_text_generation"],
                "config_template": {"timeout_ms": 30000},
                "default_params_template": {"temperature": 0.4},
                "auth_ref": "env:OPENAI_API_KEY",
                "safety_notes": {"boundary": "provider execution service only"},
            }
        ],
    }


def _authenticated_post(
    client: TestClient,
    token: str,
    path: str,
    payload: dict[str, Any],
) -> Any:
    _authenticate(client, token)
    return client.post(path, json=payload)


def _authenticated_get(client: TestClient, token: str, path: str) -> Any:
    _authenticate(client, token)
    return client.get(path)


def _authenticate(client: TestClient, token: str) -> None:
    client.cookies.clear()
    client.headers.clear()
    client.cookies.set(SESSION_COOKIE_NAME, token)
    client.cookies.set(CSRF_COOKIE_NAME, "csrf-token")
    client.headers.update({CSRF_HEADER_NAME: "csrf-token"})


def _assert_no_forbidden_markers(value: object) -> None:
    serialized = json.dumps(value, sort_keys=True).lower()
    for marker in FORBIDDEN_MARKERS:
        assert marker not in serialized
