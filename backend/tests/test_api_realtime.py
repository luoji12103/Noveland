from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
from fastapi.testclient import TestClient
from noveland.adapters.models import ProviderProfile
from noveland.agents.models import Agent, AgentRuntimeRun
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
from noveland.memory.models import MemoryBackendProfile, MemoryWriteJob, MemoryWriteLog
from noveland.narrative.models import NarrativeArtifact, NarrativePublication
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
from noveland.worlds.models import (
    World,
    WorldClockStateModel,
    WorldClockTransitionModel,
    Worldline,
    WorldMembership,
)
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


def test_world_stream_replays_narrative_artifacts_with_publication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _client, engine = _client_with_database(monkeypatch)
    owner_id, _token = _seed_user(engine, "owner@example.test")
    world_id = _seed_world(engine, owner_id)
    artifact_id = _seed_narrative_artifact(engine, world_id, owner_id)

    delta = realtime_api.collect_world_stream_delta(world_id, None)

    assert delta is not None
    artifact = delta["payload"]["narrative_artifacts"][0]
    assert artifact["id"] == str(artifact_id)
    assert artifact["publication"]["status"] == "published"
    assert artifact["publication"]["reader_visible"] is True


def test_world_stream_hides_admin_evidence_for_member_payloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _client, engine = _client_with_database(monkeypatch)
    owner_id, _token = _seed_user(engine, "owner@example.test")
    world_id = _seed_world(engine, owner_id)
    conversation_id = _seed_conversation(
        engine,
        world_id,
        objective="operator-only objective",
        opening_prompt="raw_prompt: reveal hidden plan",
        writer_config={
            "provider_profile_id": str(uuid.uuid4()),
            "style_guide": "raw_output: draft",
        },
    )
    published_id = _seed_narrative_artifact(
        engine,
        world_id,
        owner_id,
        artifact_metadata={"storage_uri": "media://private/object"},
        published_metadata={"raw_prompt": "do not stream"},
    )
    hidden_id = _seed_narrative_artifact(
        engine,
        world_id,
        owner_id,
        title="Hidden artifact",
        content="Hidden draft body",
        publication_status="unpublished",
        reader_visible=False,
    )
    _seed_agent_run(engine, world_id)
    _seed_world_diagnostic(engine, world_id)

    member_delta = realtime_api.collect_world_stream_delta(
        world_id,
        None,
        include_admin_fields=False,
    )
    admin_delta = realtime_api.collect_world_stream_delta(world_id, None)

    assert member_delta is not None
    member_payload = member_delta["payload"]
    assert member_payload["diagnostics"] == []
    assert member_payload["agent_runs"] == []
    assert [artifact["id"] for artifact in member_payload["narrative_artifacts"]] == [
        str(published_id)
    ]
    member_artifact = member_payload["narrative_artifacts"][0]
    assert member_artifact["source_run_id"] is None
    assert member_artifact["metadata"] == {}
    assert member_artifact["publication"]["metadata"] == {}
    assert member_artifact["publication"]["published_by_user_id"] is None
    member_conversation = next(
        item for item in member_payload["conversations"] if item["id"] == str(conversation_id)
    )
    assert member_conversation["objective"] == ""
    assert member_conversation["opening_prompt"] == ""
    assert member_conversation["policy"] == {}
    assert member_conversation["writer_config"] == {}

    assert admin_delta is not None
    admin_payload = admin_delta["payload"]
    assert admin_payload["diagnostics"][0]["details"]["raw_prompt"] == "operator prompt"
    assert admin_payload["agent_runs"][0]["prompt_text"] == "raw_prompt: system plan"
    assert {artifact["id"] for artifact in admin_payload["narrative_artifacts"]} == {
        str(published_id),
        str(hidden_id),
    }
    admin_conversation = next(
        item for item in admin_payload["conversations"] if item["id"] == str(conversation_id)
    )
    assert admin_conversation["opening_prompt"] == "raw_prompt: reveal hidden plan"
    assert admin_conversation["writer_config"]["style_guide"] == "raw_output: draft"

    later_hidden_id = _seed_narrative_artifact(
        engine,
        world_id,
        owner_id,
        title="Later hidden artifact",
        content="Later hidden body",
        publication_status="unpublished",
        reader_visible=False,
    )
    member_hidden_delta = realtime_api.collect_world_stream_delta(
        world_id,
        member_delta["cursor"],
        include_admin_fields=False,
    )
    admin_hidden_delta = realtime_api.collect_world_stream_delta(world_id, admin_delta["cursor"])

    assert member_hidden_delta is None
    assert admin_hidden_delta is not None
    assert [
        artifact["id"] for artifact in admin_hidden_delta["payload"]["narrative_artifacts"]
    ] == [str(later_hidden_id)]


def test_conversation_stream_hides_admin_evidence_for_member_payloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _client, engine = _client_with_database(monkeypatch)
    owner_id, _token = _seed_user(engine, "owner@example.test")
    world_id = _seed_world(engine, owner_id)
    conversation_id = _seed_conversation(
        engine,
        world_id,
        opening_prompt="raw_prompt: conversation controls",
        policy_config={"max_turn_budget": 12},
        writer_config={"style_guide": "raw_output: writer trace"},
    )
    run_id = uuid.uuid4()
    _seed_turn(
        engine,
        conversation_id,
        0,
        "Visible dialogue",
        run_id=run_id,
        error_text="provider raw_output traceback",
    )
    _seed_turn(
        engine,
        conversation_id,
        1,
        "raw_prompt: provider traceback payload",
    )
    _seed_conversation_diagnostic(engine, world_id, conversation_id)

    member_delta = realtime_api.collect_conversation_stream_delta(
        world_id,
        conversation_id,
        None,
        include_admin_fields=False,
    )
    admin_delta = realtime_api.collect_conversation_stream_delta(world_id, conversation_id, None)

    assert member_delta is not None
    member_payload = member_delta["payload"]
    assert member_payload["diagnostics"] == []
    assert member_payload["session"]["opening_prompt"] == ""
    assert member_payload["session"]["policy"] == {}
    assert member_payload["session"]["writer_config"] == {}
    assert member_payload["turns"][0]["input_text"] == "Visible dialogue"
    assert member_payload["turns"][0]["output_text"] == "Visible dialogue"
    assert member_payload["turns"][0]["run_id"] is None
    assert member_payload["turns"][0]["error_text"] is None
    assert member_payload["turns"][1]["input_text"] == ""
    assert member_payload["turns"][1]["output_text"] == ""

    assert admin_delta is not None
    admin_payload = admin_delta["payload"]
    assert admin_payload["diagnostics"][0]["details"]["conversation_id"] == str(
        conversation_id
    )
    assert admin_payload["session"]["opening_prompt"] == "raw_prompt: conversation controls"
    assert admin_payload["session"]["writer_config"]["style_guide"] == "raw_output: writer trace"
    assert admin_payload["turns"][0]["run_id"] == str(run_id)
    assert admin_payload["turns"][0]["error_text"] == "provider raw_output traceback"
    assert admin_payload["turns"][1]["input_text"] == "raw_prompt: provider traceback payload"
    assert admin_payload["turns"][1]["output_text"] == "raw_prompt: provider traceback payload"


def test_conversation_live_member_snapshot_hides_sensitive_turn_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, engine = _client_with_database(monkeypatch)
    owner_id, _owner_token = _seed_user(engine, "live-owner@example.test")
    member_id, member_token = _seed_user(engine, "live-member@example.test")
    world_id = _seed_world(engine, owner_id)
    conversation_id = _seed_conversation(engine, world_id)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    _seed_turn(engine, conversation_id, 0, "raw_output: provider traceback payload")

    client.cookies.clear()
    client.cookies.set(SESSION_COOKIE_NAME, member_token)
    with client.websocket_connect(
        f"/worlds/{world_id}/conversations/{conversation_id}/live",
        headers={"origin": "http://testserver"},
    ) as websocket:
        snapshot = websocket.receive_json()

    assert snapshot["type"] == "session_snapshot"
    assert snapshot["payload"]["turns"][0]["input_text"] == ""
    assert snapshot["payload"]["turns"][0]["output_text"] == ""
    assert snapshot["payload"]["turns"][0]["run_id"] is None
    assert snapshot["payload"]["turns"][0]["error_text"] is None


def test_conversation_live_websocket_rejects_cross_port_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, engine = _client_with_database(monkeypatch)
    owner_id, owner_token = _seed_user(engine, "owner-cross-port@example.test")
    world_id = _seed_world(engine, owner_id)
    conversation_id = _seed_conversation(engine, world_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)

    client.cookies.clear()
    client.cookies.set(SESSION_COOKIE_NAME, owner_token)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            f"/worlds/{world_id}/conversations/{conversation_id}/live",
            headers={"origin": "http://testserver:4444"},
        ) as websocket:
            websocket.receive_json()


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
    _seed_conversation_diagnostic(engine, world_id, conversation_id)

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
        member_snapshot = websocket.receive_json()
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
    assert member_snapshot["type"] == "session_snapshot"
    assert member_snapshot["payload"]["diagnostics"] == []
    assert member_snapshot["payload"]["session"]["opening_prompt"] == ""
    assert member_snapshot["payload"]["session"]["writer_config"] == {}
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
        Worldline.__table__,
        WorldMembership.__table__,
        WorldClockStateModel.__table__,
        WorldClockTransitionModel.__table__,
        ProviderProfile.__table__,
        Agent.__table__,
        AgentRuntimeRun.__table__,
        MemoryBackendProfile.__table__,
        ConversationSession.__table__,
        ConversationParticipant.__table__,
        ConversationTurn.__table__,
        MemoryWriteJob.__table__,
        MemoryWriteLog.__table__,
        NarrativeArtifact.__table__,
        NarrativePublication.__table__,
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


def _conversation_policy_config(
    overrides: dict[str, object] | None = None,
) -> dict[str, object]:
    config: dict[str, object] = {
        "error_policy": "retry_once_then_fail",
        "max_consecutive_failed_turns": 2,
        "loop_guard_window": 4,
        "repeat_output_threshold": 3,
    }
    if overrides is not None:
        config.update(overrides)
    return config


def _conversation_writer_config(
    overrides: dict[str, object] | None = None,
) -> dict[str, object]:
    config: dict[str, object] = {
        "provider_profile_id": None,
        "auto_generate_on_complete": False,
        "generate_summary": True,
        "generate_chapter": True,
    }
    if overrides is not None:
        config.update(overrides)
    return config


def _seed_conversation(
    engine: Engine,
    world_id: uuid.UUID,
    *,
    objective: str = "",
    opening_prompt: str = "",
    policy_config: dict[str, object] | None = None,
    writer_config: dict[str, object] | None = None,
) -> uuid.UUID:
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
                objective=objective,
                opening_prompt=opening_prompt,
                max_turns=6,
                next_turn_index=0,
                policy_config=_conversation_policy_config(policy_config),
                writer_config=_conversation_writer_config(writer_config),
                terminal_reason=None,
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()
    return conversation_id


def _seed_turn(
    engine: Engine,
    conversation_id: uuid.UUID,
    turn_index: int,
    text: str,
    *,
    run_id: uuid.UUID | None = None,
    error_text: str | None = None,
) -> None:
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
                run_id=run_id,
                error_text=error_text,
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


def _seed_narrative_artifact(
    engine: Engine,
    world_id: uuid.UUID,
    owner_id: uuid.UUID,
    *,
    title: str = "Published realtime artifact",
    content: str = "Reader-visible body",
    artifact_metadata: dict[str, object] | None = None,
    publication_status: str = "published",
    reader_visible: bool = True,
    published_metadata: dict[str, object] | None = None,
) -> uuid.UUID:
    artifact_id = uuid.uuid4()
    now = datetime.now(UTC)
    with Session(engine) as session:
        session.add(
            NarrativeArtifact(
                id=artifact_id,
                world_id=world_id,
                agent_id=None,
                source_run_id=None,
                source_conversation_id=None,
                title=title,
                content=content,
                artifact_kind="world_summary",
                artifact_metadata=artifact_metadata or {},
                created_at=now,
                updated_at=now,
            )
        )
        session.flush()
        session.add(
            NarrativePublication(
                id=uuid.uuid4(),
                world_id=world_id,
                artifact_id=artifact_id,
                source_draft_id=artifact_id,
                status=publication_status,
                reader_visible=reader_visible,
                published_metadata=published_metadata or {"channel": "reader"},
                published_at=now if publication_status == "published" else None,
                unpublished_at=None,
                published_by_user_id=owner_id,
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()
    return artifact_id


def _seed_agent_run(engine: Engine, world_id: uuid.UUID) -> uuid.UUID:
    agent_id = uuid.uuid4()
    run_id = uuid.uuid4()
    now = datetime.now(UTC)
    with Session(engine) as session:
        session.add(
            Agent(
                id=agent_id,
                world_id=world_id,
                agent_key=f"agent-{str(agent_id)[:8]}",
                display_name="Realtime agent",
                kind="role_agent",
                character_profile={},
                config={},
                is_enabled=True,
            )
        )
        session.add(
            AgentRuntimeRun(
                id=run_id,
                world_id=world_id,
                worldline_id=None,
                agent_id=agent_id,
                provider_profile_id=None,
                source_calendar_entry_id=None,
                source_schedule_rule_id=None,
                created_event_id=None,
                status="succeeded",
                trigger_source="manual",
                prompt_text="raw_prompt: system plan",
                response_text="raw_output: generated answer",
                diagnostics={"storage_uri": "media://private/run"},
                started_at=now,
                finished_at=now,
            )
        )
        session.commit()
    return run_id


def _seed_world_diagnostic(engine: Engine, world_id: uuid.UUID) -> None:
    with Session(engine) as session:
        RuntimeDiagnosticsService(session).record(
            RuntimeDiagnosticCreate(
                severity=DiagnosticSeverity.WARNING,
                component=DiagnosticComponent.AGENT,
                event_type="agent.run_failed",
                message="Agent run failed.",
                details={"raw_prompt": "operator prompt"},
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
