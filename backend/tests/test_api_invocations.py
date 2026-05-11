from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import cast

from fastapi.testclient import TestClient
from noveland.adapters.models import ProviderProfile
from noveland.agents.models import Agent, AgentRuntimeRun
from noveland.auth import AuthRole
from noveland.auth.contracts import AuthSessionStatus
from noveland.auth.models import AuthSession, PlatformRoleAssignment, User
from noveland.auth.services import hash_session_token
from noveland.events.models import WorldEventModel
from noveland.invocations.models import (
    AgentRuntimeRunModelInvocation,
    ModelInvocation,
    ModelInvocationTag,
    PromptSnapshot,
    PromptTemplate,
)
from noveland.media.models import MediaAsset, MediaJob
from noveland.memory.models import MemoryBackendProfile, MemoryWriteJob
from noveland.services.api.app import create_app
from noveland.services.api.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from noveland.services.api.dependencies import get_db_session
from noveland.worlds.models import World, Worldline, WorldMembership
from noveland.worlds.worldlines import ensure_primary_worldline
from sqlalchemy import Table, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_invocations_api_admin_flow_search_tags_snapshot_and_redaction() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id = _seed_world(engine, owner_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    worldline_id = _seed_worldline(engine, world_id)
    agent_id = _seed_agent(engine, world_id)

    _authenticate_session_only(client, owner_token)
    missing_csrf = client.post(
        f"/worlds/{world_id}/model-invocations",
        json={
            "worldline_id": str(worldline_id),
            "invocation_kind": "agent_runtime",
            "actor_kind": "runtime",
            "provider_kind": "openai_compatible",
        },
    )

    _authenticate(client, owner_token)
    created = client.post(
        f"/worlds/{world_id}/model-invocations",
        json={
            "worldline_id": str(worldline_id),
            "invocation_kind": "agent_runtime",
            "actor_kind": "runtime",
            "actor_ref": "system:runtime",
            "agent_id": str(agent_id),
            "provider_kind": "openai_compatible",
            "model_name": "test-model",
            "input_text": "compact input",
            "status": "succeeded",
            "output_text": "compact output",
            "prompt_snapshot": {
                "raw_prompt_text": "raw prompt searchable phrase",
                "raw_output_text": "raw output phrase",
                "raw_request_json": {"prompt": "raw prompt"},
                "raw_response_json": {"ok": True},
            },
        },
    )
    invocation_id = created.json()["id"]
    tag = client.post(
        f"/worlds/{world_id}/model-invocations/{invocation_id}/tags",
        json={
            "worldline_id": str(worldline_id),
            "tag_type": "Provider",
            "tag_key": "Model",
            "tag_value": "test:model",
        },
    )
    search = client.get(
        f"/worlds/{world_id}/model-invocations",
        params=[
            ("worldline_id", str(worldline_id)),
            ("contains_text", " searchable "),
            ("tag", "provider:model:test:model"),
        ],
    )
    malformed = client.get(
        f"/worlds/{world_id}/model-invocations",
        params=[("worldline_id", str(worldline_id)), ("tag", "provider:model")],
    )
    empty_text = client.get(
        f"/worlds/{world_id}/model-invocations",
        params={"worldline_id": str(worldline_id), "contains_text": "   "},
    )
    snapshot = client.get(
        f"/worlds/{world_id}/model-invocations/{invocation_id}/prompt-snapshot"
    )
    redacted = client.post(
        f"/worlds/{world_id}/model-invocations/{invocation_id}/redact",
        json={
            "redaction_status": "redacted",
            "reason": "test",
            "mode": "clear_raw_payloads",
        },
    )
    after_redaction = client.get(f"/worlds/{world_id}/model-invocations/{invocation_id}")

    _authenticate(client, member_token)
    member_list = client.get(f"/worlds/{world_id}/model-invocations")

    assert missing_csrf.status_code == 403
    assert created.status_code == 201
    assert tag.status_code == 201
    assert tag.json()["tag_type"] == "provider"
    assert tag.json()["tag_value"] == "test:model"
    assert search.status_code == 200
    assert [row["id"] for row in search.json()["invocations"]] == [invocation_id]
    assert malformed.status_code == 422
    assert empty_text.status_code == 422
    assert snapshot.status_code == 200
    assert snapshot.json()["raw_prompt_text"] == "raw prompt searchable phrase"
    assert redacted.status_code == 200
    assert redacted.json()["status"] == "redacted"
    assert after_redaction.status_code == 200
    assert after_redaction.json()["input_text"] is None
    assert member_list.status_code == 403


def test_invocations_api_developer_only_requires_platform_admin() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    platform_id, platform_token = _seed_user(
        engine,
        "platform@example.test",
        platform_admin=True,
    )
    world_id = _seed_world(engine, owner_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    worldline_id = _seed_worldline(engine, world_id)
    invocation_id = _seed_invocation(
        engine,
        world_id,
        worldline_id,
        visibility="developer_only",
        input_text="developer raw",
    )
    hidden_id = _seed_invocation(
        engine,
        world_id,
        worldline_id,
        visibility="hidden",
        input_text="hidden raw",
    )

    _authenticate(client, owner_token)
    owner_get = client.get(f"/worlds/{world_id}/model-invocations/{invocation_id}")
    owner_hidden = client.get(f"/worlds/{world_id}/model-invocations/{hidden_id}")

    _authenticate(client, platform_token)
    platform_get = client.get(f"/worlds/{world_id}/model-invocations/{invocation_id}")
    hidden_default = client.get(f"/worlds/{world_id}/model-invocations/{hidden_id}")
    hidden_included = client.get(
        f"/worlds/{world_id}/model-invocations/{hidden_id}",
        params={"include_hidden": "true"},
    )

    assert platform_id
    assert owner_get.status_code == 404
    assert owner_hidden.status_code == 404
    assert platform_get.status_code == 200
    assert platform_get.json()["input_text"] == "developer raw"
    assert hidden_default.status_code == 404
    assert hidden_included.status_code == 200


def test_prompt_templates_api_global_requires_platform_admin_and_world_reads_global() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    _platform_id, platform_token = _seed_user(
        engine,
        "platform@example.test",
        platform_admin=True,
    )
    world_id = _seed_world(engine, owner_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)

    _authenticate(client, owner_token)
    forbidden_global = client.post(
        f"/worlds/{world_id}/prompt-templates",
        json={
            "scope_kind": "global",
            "template_key": "agent.run",
            "version": 1,
            "invocation_kind": "agent_runtime",
            "title": "Global",
            "content": "global",
        },
    )
    world_template = client.post(
        f"/worlds/{world_id}/prompt-templates",
        json={
            "scope_kind": "world",
            "template_key": "agent.run",
            "version": 1,
            "invocation_kind": "agent_runtime",
            "title": "World",
            "content": "world",
        },
    )

    _authenticate(client, platform_token)
    global_template = client.post(
        f"/worlds/{world_id}/prompt-templates",
        json={
            "scope_kind": "global",
            "template_key": "agent.run",
            "version": 1,
            "invocation_kind": "agent_runtime",
            "title": "Global",
            "content": "global",
            "status": "active",
        },
    )

    _authenticate(client, owner_token)
    list_templates = client.get(f"/worlds/{world_id}/prompt-templates")
    read_global = client.get(
        f"/worlds/{world_id}/prompt-templates/{global_template.json()['id']}"
    )

    assert forbidden_global.status_code == 403
    assert world_template.status_code == 201
    assert global_template.status_code == 201
    assert list_templates.status_code == 200
    assert {row["id"] for row in list_templates.json()} == {
        world_template.json()["id"],
        global_template.json()["id"],
    }
    assert read_global.status_code == 200


def _client_with_database() -> tuple[TestClient, Engine]:
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
    return TestClient(app), engine


def _create_tables(engine: Engine) -> None:
    for table in (
        cast(Table, User.__table__),
        cast(Table, AuthSession.__table__),
        cast(Table, PlatformRoleAssignment.__table__),
        cast(Table, MemoryBackendProfile.__table__),
        cast(Table, World.__table__),
        cast(Table, Worldline.__table__),
        cast(Table, WorldMembership.__table__),
        cast(Table, ProviderProfile.__table__),
        cast(Table, Agent.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, MediaJob.__table__),
        cast(Table, MediaAsset.__table__),
        cast(Table, MemoryWriteJob.__table__),
        cast(Table, AgentRuntimeRun.__table__),
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


def _seed_agent(engine: Engine, world_id: uuid.UUID) -> uuid.UUID:
    agent_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            Agent(
                id=agent_id,
                world_id=world_id,
                agent_key="agent",
                display_name="Agent",
                kind="role_agent",
            )
        )
        session.commit()
    return agent_id


def _seed_invocation(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    *,
    visibility: str,
    input_text: str,
) -> uuid.UUID:
    invocation_id = uuid.uuid4()
    now = datetime.now(UTC)
    with Session(engine) as session:
        session.add(
            ModelInvocation(
                id=invocation_id,
                world_id=world_id,
                worldline_id=worldline_id,
                trace_id=uuid.uuid4(),
                invocation_kind="agent_runtime",
                actor_kind="runtime",
                actor_ref="system:runtime",
                provider_kind="openai_compatible",
                input_text=input_text,
                status="succeeded",
                visibility=visibility,
                redaction_status="raw",
                retention_policy="local_debug",
                contains_sensitive_context=False,
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()
    return invocation_id


def _authenticate(client: TestClient, token: str) -> None:
    client.cookies.clear()
    client.headers.clear()
    client.cookies.set(SESSION_COOKIE_NAME, token)
    client.cookies.set(CSRF_COOKIE_NAME, "csrf-token")
    client.headers.update({CSRF_HEADER_NAME: "csrf-token"})


def _authenticate_session_only(client: TestClient, token: str) -> None:
    client.cookies.clear()
    client.headers.clear()
    client.cookies.set(SESSION_COOKIE_NAME, token)
