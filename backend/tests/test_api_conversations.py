from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
from fastapi.testclient import TestClient
from noveland.adapters import ProviderCompletion, ProviderProfileService
from noveland.adapters.models import ProviderProfile
from noveland.agents.models import Agent, AgentObservation, AgentPersona, AgentRuntimeRun
from noveland.auth import AuthRole
from noveland.auth.contracts import AuthSessionStatus
from noveland.auth.models import AuthSession, PlatformRoleAssignment, User
from noveland.auth.services import hash_session_token
from noveland.calendar.models import AgentCalendarEntry, WorldScheduleRule
from noveland.conversations.models import (
    ConversationParticipant,
    ConversationSession,
    ConversationTurn,
)
from noveland.events.models import WorldEventModel
from noveland.observability.models import RuntimeDiagnosticEvent
from noveland.services.api.app import create_app
from noveland.services.api.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from noveland.services.api.dependencies import get_db_session
from noveland.worlds.models import Scene, World, WorldMembership
from sqlalchemy import Table, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_conversation_api_enforces_access_and_manual_advance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    _stranger_id, stranger_token = _seed_user(engine, "stranger@example.test")
    world_id = _seed_world(engine, owner_id, "dialogue-world")
    scene_id = _seed_scene(engine, world_id, "square")
    first_agent_id = _seed_agent(engine, world_id, "guide", scene_id)
    second_agent_id = _seed_agent(engine, world_id, "scribe", scene_id)
    _seed_provider_profile(engine)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)

    def fake_invoke_profile(
        self: ProviderProfileService,
        profile: object,
        prompt: str,
    ) -> ProviderCompletion:
        del self, profile
        return ProviderCompletion(text=f"reply for {prompt}", raw_response={"ok": True})

    monkeypatch.setattr(ProviderProfileService, "invoke_profile", fake_invoke_profile)

    _authenticate(client, owner_token)
    create_response = client.post(
        f"/worlds/{world_id}/conversations",
        json={
            "session_key": "manual-chain",
            "title": "Manual chain",
            "scope_type": "scene",
            "mode": "manual_chain",
            "scene_id": str(scene_id),
            "max_turns": 3,
            "policy": _policy_json(),
        },
    )
    conversation_id = create_response.json()["id"]
    replace_participants = client.put(
        f"/worlds/{world_id}/conversations/{conversation_id}/participants",
        json=[
            {"agent_id": str(first_agent_id), "turn_order": 0, "is_enabled": True},
            {"agent_id": str(second_agent_id), "turn_order": 1, "is_enabled": True},
        ],
    )
    seed_response = client.post(
        f"/worlds/{world_id}/conversations/{conversation_id}/seed",
        json={"input_text": "Operator seed"},
    )
    advance_response = client.post(f"/worlds/{world_id}/conversations/{conversation_id}/advance")

    _authenticate(client, member_token)
    member_list = client.get(f"/worlds/{world_id}/conversations")
    member_turns = client.get(f"/worlds/{world_id}/conversations/{conversation_id}/turns")
    member_diagnostics = client.get(
        f"/worlds/{world_id}/conversations/{conversation_id}/diagnostics",
    )
    member_advance = client.post(f"/worlds/{world_id}/conversations/{conversation_id}/advance")

    _authenticate(client, stranger_token)
    stranger_list = client.get(f"/worlds/{world_id}/conversations")

    assert create_response.status_code == 201
    assert replace_participants.status_code == 200
    assert seed_response.status_code == 200
    assert advance_response.status_code == 200
    assert advance_response.json()["turn"]["speaker_agent_id"] == str(first_agent_id)
    assert member_list.status_code == 200
    assert member_turns.status_code == 200
    assert member_diagnostics.status_code == 403
    assert [turn["speaker_kind"] for turn in member_turns.json()] == ["operator", "agent"]
    assert member_advance.status_code == 403
    assert stranger_list.status_code == 404


def test_conversation_api_validates_scene_scope_auto_lifecycle_and_agent_provider_profile() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id = _seed_world(engine, owner_id, "scene-world")
    first_scene_id = _seed_scene(engine, world_id, "hall")
    second_scene_id = _seed_scene(engine, world_id, "garden")
    in_scene_agent_id = _seed_agent(engine, world_id, "guide", first_scene_id)
    out_of_scene_agent_id = _seed_agent(engine, world_id, "outsider", second_scene_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _authenticate(client, owner_token)

    create_agent = client.post(
        f"/worlds/{world_id}/agents",
        json={
            "agent_key": "planner",
            "display_name": "Planner",
            "kind": "role_agent",
            "provider_profile_id": str(uuid.uuid4()),
            "config": {"tone": "direct"},
        },
    )
    created_agent_id = create_agent.json()["id"]
    clear_provider = client.patch(
        f"/worlds/{world_id}/agents/{created_agent_id}",
        json={"provider_profile_id": None},
    )

    create_conversation = client.post(
        f"/worlds/{world_id}/conversations",
        json={
            "session_key": "auto-room",
            "title": "Auto room",
            "scope_type": "scene",
            "mode": "auto_dialogue",
            "scene_id": str(first_scene_id),
            "policy": _policy_json(),
        },
    )
    invalid_world_scope = client.post(
        f"/worlds/{world_id}/conversations",
        json={
            "session_key": "invalid-world-scene",
            "title": "Invalid world scene",
            "scope_type": "world",
            "mode": "manual_chain",
            "scene_id": str(first_scene_id),
            "policy": _policy_json(),
        },
    )
    invalid_scene_scope = client.post(
        f"/worlds/{world_id}/conversations",
        json={
            "session_key": "invalid-scene-missing",
            "title": "Invalid scene missing",
            "scope_type": "scene",
            "mode": "manual_chain",
            "policy": _policy_json(),
        },
    )
    conversation_id = create_conversation.json()["id"]
    mismatched_participant = client.put(
        f"/worlds/{world_id}/conversations/{conversation_id}/participants",
        json=[{"agent_id": str(out_of_scene_agent_id), "turn_order": 0, "is_enabled": True}],
    )
    valid_participant = client.put(
        f"/worlds/{world_id}/conversations/{conversation_id}/participants",
        json=[{"agent_id": str(in_scene_agent_id), "turn_order": 0, "is_enabled": True}],
    )
    start_response = client.post(f"/worlds/{world_id}/conversations/{conversation_id}/start")
    advance_while_running = client.post(
        f"/worlds/{world_id}/conversations/{conversation_id}/advance",
    )
    pause_response = client.post(f"/worlds/{world_id}/conversations/{conversation_id}/pause")
    resume_response = client.post(f"/worlds/{world_id}/conversations/{conversation_id}/resume")

    assert create_agent.status_code == 201
    assert create_agent.json()["provider_profile_id"] is not None
    assert (
        create_agent.json()["config"]["provider_profile_id"]
        == create_agent.json()["provider_profile_id"]
    )
    assert clear_provider.status_code == 200
    assert clear_provider.json()["provider_profile_id"] is None
    assert "provider_profile_id" not in clear_provider.json()["config"]
    assert create_conversation.status_code == 201
    assert invalid_world_scope.status_code == 422
    assert invalid_scene_scope.status_code == 422
    assert mismatched_participant.status_code == 404
    assert valid_participant.status_code == 200
    assert start_response.status_code == 200
    assert start_response.json()["status"] == "running"
    assert advance_while_running.status_code == 409
    assert pause_response.status_code == 200
    assert pause_response.json()["status"] == "paused"
    assert resume_response.status_code == 200
    assert resume_response.json()["status"] == "running"


def test_conversation_api_stop_and_diagnostics() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id = _seed_world(engine, owner_id, "stop-world")
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _authenticate(client, owner_token)

    create_conversation = client.post(
        f"/worlds/{world_id}/conversations",
        json={
            "session_key": "stoppable",
            "title": "Stoppable",
            "scope_type": "world",
            "mode": "manual_chain",
            "policy": _policy_json(),
        },
    )
    conversation_id = create_conversation.json()["id"]
    stop_response = client.post(f"/worlds/{world_id}/conversations/{conversation_id}/stop")
    diagnostics_response = client.get(
        f"/worlds/{world_id}/conversations/{conversation_id}/diagnostics",
    )

    assert stop_response.status_code == 200
    assert stop_response.json()["status"] == "stopped"
    assert stop_response.json()["terminal_reason"] == "operator_stopped"
    assert diagnostics_response.status_code == 200
    assert diagnostics_response.json()[0]["component"] == "conversation"
    assert diagnostics_response.json()[0]["details"]["conversation_id"] == str(conversation_id)


def _client_with_database() -> tuple[TestClient, Engine]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in (
        cast(Table, User.__table__),
        cast(Table, AuthSession.__table__),
        cast(Table, PlatformRoleAssignment.__table__),
        cast(Table, World.__table__),
        cast(Table, WorldMembership.__table__),
        cast(Table, Scene.__table__),
        cast(Table, ProviderProfile.__table__),
        cast(Table, Agent.__table__),
        cast(Table, AgentPersona.__table__),
        cast(Table, AgentObservation.__table__),
        cast(Table, AgentCalendarEntry.__table__),
        cast(Table, WorldScheduleRule.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, AgentRuntimeRun.__table__),
        cast(Table, RuntimeDiagnosticEvent.__table__),
        cast(Table, ConversationSession.__table__),
        cast(Table, ConversationParticipant.__table__),
        cast(Table, ConversationTurn.__table__),
    ):
        table.create(engine)
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


def _seed_user(engine: Engine, email: str) -> tuple[uuid.UUID, str]:
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
            ),
        )
        session.commit()
    return user_id, token


def _seed_world(engine: Engine, owner_user_id: uuid.UUID, slug: str) -> uuid.UUID:
    world_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            World(
                id=world_id,
                owner_user_id=owner_user_id,
                slug=slug,
                name=slug,
                rules_config={},
                is_active=True,
            ),
        )
        session.commit()
    return world_id


def _seed_scene(engine: Engine, world_id: uuid.UUID, scene_key: str) -> uuid.UUID:
    scene_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            Scene(
                id=scene_id,
                world_id=world_id,
                scene_key=scene_key,
                name=scene_key,
                is_active=True,
            ),
        )
        session.commit()
    return scene_id


def _seed_agent(
    engine: Engine,
    world_id: uuid.UUID,
    agent_key: str,
    scene_id: uuid.UUID | None = None,
) -> uuid.UUID:
    agent_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            Agent(
                id=agent_id,
                world_id=world_id,
                home_scene_id=scene_id,
                agent_key=agent_key,
                display_name=agent_key,
                kind="role_agent",
                config={},
                is_enabled=True,
            ),
        )
        session.commit()
    return agent_id


def _seed_provider_profile(engine: Engine) -> None:
    with Session(engine) as session:
        session.add(
            ProviderProfile(
                profile_key="runtime-profile",
                name="Runtime Profile",
                provider_type="openai_compatible",
                base_url="https://api.example.test/v1",
                model_name="test-model",
                capabilities={},
                api_key_ref="runtime-ref",
                is_enabled=True,
            ),
        )
        session.commit()


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
            ),
        )
        session.commit()


def _authenticate(client: TestClient, token: str) -> None:
    client.cookies.clear()
    client.headers.clear()
    client.cookies.set(SESSION_COOKIE_NAME, token)
    client.cookies.set(CSRF_COOKIE_NAME, "csrf-token")
    client.headers.update({CSRF_HEADER_NAME: "csrf-token"})


def _policy_json() -> dict[str, object]:
    return {
        "error_policy": "retry_once_then_fail",
        "max_consecutive_failed_turns": 2,
        "loop_guard_window": 4,
        "repeat_output_threshold": 3,
    }
