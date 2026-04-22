from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
from fastapi.testclient import TestClient
from noveland.adapters.models import ProviderProfile
from noveland.auth import AuthRole
from noveland.auth.contracts import AuthSessionStatus
from noveland.auth.models import AuthSession, PlatformRoleAssignment, User
from noveland.auth.services import hash_session_token
from noveland.conversations.models import (
    ConversationParticipant,
    ConversationSession,
    ConversationTurn,
)
from noveland.core.models import RuntimeControlState
from noveland.observability import (
    DiagnosticComponent,
    DiagnosticSeverity,
    RuntimeDiagnosticCreate,
    RuntimeDiagnosticsService,
)
from noveland.observability.models import RuntimeDiagnosticEvent
from noveland.services.api import realtime as realtime_api
from noveland.services.api.app import create_app
from noveland.services.api.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from noveland.services.api.dependencies import get_db_session
from noveland.worlds.models import World, WorldClockStateModel, WorldMembership
from sqlalchemy import Table, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.websockets import WebSocketDisconnect


def test_runtime_stream_requires_platform_admin_and_emits_initial_delta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, engine = _client_with_database(monkeypatch)
    _member_id, member_token = _seed_user(engine, "member@example.test")
    _admin_id, _admin_token = _seed_user(
        engine,
        "platform@example.test",
        platform_admin=True,
    )
    _seed_runtime_diagnostic(engine)

    _authenticate(client, member_token)
    forbidden = client.get("/runtime/stream")
    delta = realtime_api.collect_runtime_stream_delta(None)

    assert forbidden.status_code == 403
    assert delta is not None
    assert delta["event_type"] == "runtime.delta"
    assert "runtime_control" in delta["payload"]
    assert delta["payload"]["diagnostics"][0]["event_type"] == "runtime.started"


def test_conversation_stream_replays_new_turns_and_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _client, engine = _client_with_database(monkeypatch)
    owner_id, _token = _seed_user(engine, "owner@example.test")
    world_id = _seed_world(engine, owner_id)
    conversation_id = _seed_conversation(engine, world_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _seed_turn(engine, conversation_id, 0, "Hello there")

    first_delta = realtime_api.collect_conversation_stream_delta(world_id, conversation_id, None)
    assert first_delta is not None
    assert first_delta["payload"]["session"]["id"] == str(conversation_id)
    assert len(first_delta["payload"]["turns"]) == 1

    no_change = realtime_api.collect_conversation_stream_delta(
        world_id,
        conversation_id,
        first_delta["cursor"],
    )
    assert no_change is None

    _seed_turn(engine, conversation_id, 1, "Second turn")
    _seed_conversation_diagnostic(engine, world_id, conversation_id)
    next_delta = realtime_api.collect_conversation_stream_delta(
        world_id,
        conversation_id,
        first_delta["cursor"],
    )

    assert next_delta is not None
    assert [turn["turn_index"] for turn in next_delta["payload"]["turns"]] == [1]
    assert next_delta["payload"]["diagnostics"][0]["details"]["conversation_id"] == str(
        conversation_id
    )


def test_conversation_live_websocket_enforces_origin_and_admin_controls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, engine = _client_with_database(monkeypatch)
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id = _seed_world(engine, owner_id)
    conversation_id = _seed_conversation(engine, world_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)

    client.cookies.clear()
    client.cookies.set(SESSION_COOKIE_NAME, owner_token)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            f"/worlds/{world_id}/conversations/{conversation_id}/live",
        ) as websocket:
            websocket.receive_json()

    client.cookies.clear()
    client.cookies.set(SESSION_COOKIE_NAME, owner_token)
    with client.websocket_connect(
        f"/worlds/{world_id}/conversations/{conversation_id}/live",
        headers={"origin": "http://testserver"},
    ) as websocket:
        snapshot = websocket.receive_json()
        websocket.send_json(
            {
                "command": "seed",
                "request_id": "seed-1",
                "payload": {"input_text": "Operator seed"},
            }
        )
        ack = websocket.receive_json()
        appended = websocket.receive_json()

    client.cookies.clear()
    client.cookies.set(SESSION_COOKIE_NAME, member_token)
    with client.websocket_connect(
        f"/worlds/{world_id}/conversations/{conversation_id}/live",
        headers={"origin": "http://testserver"},
    ) as websocket:
        websocket.receive_json()
        websocket.send_json(
            {
                "command": "advance",
                "request_id": "advance-1",
                "payload": {},
            }
        )
        error = websocket.receive_json()

    assert snapshot["type"] == "session_snapshot"
    assert ack["type"] == "ack"
    assert appended["type"] == "turn_appended"
    assert appended["payload"]["turn_index"] == 0
    assert error["type"] == "error"
    assert error["payload"]["message"] == "Forbidden"


def _client_with_database(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[TestClient, Engine]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    _create_tables(engine)
    app = create_app()
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_db_session() -> Iterator[Session]:
        with Session(engine) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    monkeypatch.setattr(realtime_api, "get_session_factory", lambda: factory)
    app.dependency_overrides[get_db_session] = override_get_db_session
    return TestClient(app), engine


def _create_tables(engine: Engine) -> None:
    for table in (
        User.__table__,
        AuthSession.__table__,
        PlatformRoleAssignment.__table__,
        World.__table__,
        WorldMembership.__table__,
        WorldClockStateModel.__table__,
        ProviderProfile.__table__,
        ConversationSession.__table__,
        ConversationParticipant.__table__,
        ConversationTurn.__table__,
        RuntimeControlState.__table__,
        RuntimeDiagnosticEvent.__table__,
    ):
        cast(Table, table).create(engine)


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
            ),
        )
        if platform_admin:
            session.add(
                PlatformRoleAssignment(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    role=AuthRole.PLATFORM_ADMIN.value,
                    assigned_at=now,
                ),
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
                slug=f"world-{str(world_id)[:8]}",
                name="Realtime world",
                description=None,
                rules_config={},
                is_active=True,
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


def _seed_conversation(engine: Engine, world_id: uuid.UUID) -> uuid.UUID:
    conversation_id = uuid.uuid4()
    now = datetime.now(UTC)
    with Session(engine) as session:
        session.add(
            ConversationSession(
                id=conversation_id,
                world_id=world_id,
                scene_id=None,
                session_key="realtime-conversation",
                title="Realtime conversation",
                scope_type="world",
                mode="manual_chain",
                status="draft",
                objective="",
                opening_prompt="",
                max_turns=6,
                next_turn_index=0,
                policy_config={
                    "error_policy": "retry_once_then_fail",
                    "max_consecutive_failed_turns": 2,
                    "loop_guard_window": 4,
                    "repeat_output_threshold": 3,
                },
                writer_config={
                    "provider_profile_id": None,
                    "auto_generate_on_complete": False,
                    "generate_summary": True,
                    "generate_chapter": True,
                },
                terminal_reason=None,
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()
    return conversation_id


def _seed_turn(engine: Engine, conversation_id: uuid.UUID, turn_index: int, text: str) -> None:
    with Session(engine) as session:
        session.add(
            ConversationTurn(
                id=uuid.uuid4(),
                session_id=conversation_id,
                turn_index=turn_index,
                speaker_kind="operator" if turn_index == 0 else "agent",
                speaker_agent_id=None,
                input_text=text,
                output_text=text,
                status="succeeded",
                run_id=None,
                error_text=None,
            )
        )
        session.commit()


def _seed_runtime_diagnostic(engine: Engine) -> None:
    with Session(engine) as session:
        RuntimeDiagnosticsService(session).record(
            RuntimeDiagnosticCreate(
                severity=DiagnosticSeverity.INFO,
                component=DiagnosticComponent.RUNTIME,
                event_type="runtime.started",
                message="Runtime started.",
                details={"state": "running"},
            )
        )
        session.commit()


def _seed_conversation_diagnostic(
    engine: Engine,
    world_id: uuid.UUID,
    conversation_id: uuid.UUID,
) -> None:
    with Session(engine) as session:
        RuntimeDiagnosticsService(session).record(
            RuntimeDiagnosticCreate(
                severity=DiagnosticSeverity.WARNING,
                component=DiagnosticComponent.CONVERSATION,
                event_type="conversation.turn_skipped",
                message="Turn skipped.",
                details={"conversation_id": str(conversation_id)},
                world_id=world_id,
            )
        )
        session.commit()


def _authenticate(client: TestClient, token: str) -> None:
    client.cookies.clear()
    client.headers.clear()
    client.cookies.set(SESSION_COOKIE_NAME, token)
    client.cookies.set(CSRF_COOKIE_NAME, "csrf-token")
    client.headers.update({CSRF_HEADER_NAME: "csrf-token"})
