from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import cast

from fastapi.testclient import TestClient
from noveland.auth import AuthRole
from noveland.auth.contracts import AuthSessionStatus
from noveland.auth.models import AuthSession, PlatformRoleAssignment, User
from noveland.auth.services import hash_session_token
from noveland.conversations.models import (
    ConversationSession,
    ConversationTurn,
    ConversationTurnPresentation,
)
from noveland.core.database import import_model_modules
from noveland.media.models import MediaAsset, MediaJob
from noveland.player_sessions.models import PlayerSession
from noveland.services.api.app import create_app
from noveland.services.api.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from noveland.services.api.dependencies import get_db_session
from noveland.worlds.models import PlayerActorProfile, Scene, World, Worldline, WorldMembership
from sqlalchemy import Table, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

FORBIDDEN_MARKERS = (
    "storage_uri",
    "media://",
    "file://",
    "s3://",
    "base64",
    "raw_prompt",
    "raw_output",
    "prompt_snapshot",
    "promptsnapshot",
    "rawprompt",
    "rawoutput",
    "storageuri",
    "event_payload",
    "api_key",
    "bearer_token",
    "authorization",
    "secret",
    "invite_token",
    "/tmp/",
    "/root/",
)


def test_player_session_resume_round_trip_is_player_safe() -> None:
    client, engine = _client_with_database()
    admin_id, _admin_token = _seed_user(engine, "admin@example.test", platform_admin=True)
    tester_id, tester_token = _seed_user(engine, "tester@example.test")
    world_id, worldline_id, scene_id = _seed_world_graph(engine, admin_id)
    _add_membership(engine, world_id, tester_id, AuthRole.HUMAN_USER)
    actor_id = _seed_player_actor(engine, world_id, worldline_id, tester_id, scene_id)
    conversation_id, turn_id, presentation_id = _seed_conversation(
        engine,
        world_id,
        worldline_id,
        scene_id,
    )
    _authenticate(client, tester_token)

    upsert = client.post(
        f"/worlds/{world_id}/player-sessions/resume",
        json={
            "worldline_id": str(worldline_id),
            "player_actor_id": str(actor_id),
            "conversation_session_id": str(conversation_id),
            "scene_id": str(scene_id),
            "last_turn_id": str(turn_id),
            "last_presentation_id": str(presentation_id),
            "route_state": {
                "mode": "scene",
                "storage_uri": "media://worlds/leak",
                "rawPrompt": "hidden system instruction",
                "promptSnapshotId": str(uuid.uuid4()),
                "nested": {
                    "raw_prompt": "leak",
                    "rawOutput": "hidden model output",
                    "storageUri": "opaque-media-object",
                    "step": "resume",
                },
            },
            "resume_state": {
                "scroll": "turn-end",
                "invite_token": "leak",
                "rawOutput": "operator output",
                "storageUri": "opaque-storage-ref",
            },
        },
        headers=_csrf_headers(client),
    )
    read_back = client.get(
        f"/worlds/{world_id}/player-sessions/resume"
        f"?worldline_id={worldline_id}&player_actor_id={actor_id}",
    )

    assert upsert.status_code == 200
    body = upsert.json()
    assert body["conversation_session_id"] == str(conversation_id)
    assert body["last_turn_id"] == str(turn_id)
    assert body["last_presentation_id"] == str(presentation_id)
    assert body["recovery_status"] == "ready"
    assert body["route_state"] == {"mode": "scene", "nested": {"step": "resume"}}
    assert body["resume_state"] == {"scroll": "turn-end"}
    assert "open_reader_playback" in body["available_actions"]
    assert read_back.status_code == 200
    assert read_back.json()["id"] == body["id"]
    _assert_no_forbidden_markers(body)
    _assert_no_forbidden_markers(read_back.json())


def test_player_session_rejects_cross_player_world_and_worldline() -> None:
    client, engine = _client_with_database()
    admin_id, _admin_token = _seed_user(engine, "admin@example.test", platform_admin=True)
    tester_id, tester_token = _seed_user(engine, "tester@example.test")
    other_id, other_token = _seed_user(engine, "other@example.test")
    world_id, worldline_id, scene_id = _seed_world_graph(engine, admin_id)
    other_world_id, other_worldline_id, _other_scene_id = _seed_world_graph(
        engine,
        admin_id,
        slug="other",
    )
    fork_worldline_id = _seed_worldline(engine, world_id, "fork")
    _add_membership(engine, world_id, tester_id, AuthRole.HUMAN_USER)
    _add_membership(engine, world_id, other_id, AuthRole.HUMAN_USER)
    _add_membership(engine, other_world_id, tester_id, AuthRole.HUMAN_USER)
    actor_id = _seed_player_actor(engine, world_id, worldline_id, tester_id, scene_id)
    other_actor_id = _seed_player_actor(engine, world_id, worldline_id, other_id, scene_id)
    cross_world_actor_id = _seed_player_actor(
        engine,
        other_world_id,
        other_worldline_id,
        tester_id,
        None,
    )
    _authenticate(client, tester_token)

    created = client.post(
        f"/worlds/{world_id}/player-sessions/resume",
        json={"worldline_id": str(worldline_id), "player_actor_id": str(actor_id)},
        headers=_csrf_headers(client),
    )
    other_actor = client.post(
        f"/worlds/{world_id}/player-sessions/resume",
        json={"worldline_id": str(worldline_id), "player_actor_id": str(other_actor_id)},
        headers=_csrf_headers(client),
    )
    cross_world = client.post(
        f"/worlds/{world_id}/player-sessions/resume",
        json={"worldline_id": str(worldline_id), "player_actor_id": str(cross_world_actor_id)},
        headers=_csrf_headers(client),
    )
    cross_worldline = client.post(
        f"/worlds/{world_id}/player-sessions/resume",
        json={"worldline_id": str(fork_worldline_id), "player_actor_id": str(actor_id)},
        headers=_csrf_headers(client),
    )

    _authenticate(client, other_token)
    other_read = client.get(
        f"/worlds/{world_id}/player-sessions/resume"
        f"?worldline_id={worldline_id}&player_actor_id={actor_id}",
    )

    assert created.status_code == 200
    assert other_actor.status_code == 404
    assert cross_world.status_code == 404
    assert cross_worldline.status_code == 404
    assert other_read.status_code == 404
    _assert_no_forbidden_markers(other_read.json())


def test_player_session_validates_references_and_safe_fallbacks() -> None:
    client, engine = _client_with_database()
    admin_id, _admin_token = _seed_user(engine, "admin@example.test", platform_admin=True)
    tester_id, tester_token = _seed_user(engine, "tester@example.test")
    world_id, worldline_id, scene_id = _seed_world_graph(engine, admin_id)
    other_world_id, other_worldline_id, other_scene_id = _seed_world_graph(
        engine,
        admin_id,
        slug="other",
    )
    _add_membership(engine, world_id, tester_id, AuthRole.HUMAN_USER)
    actor_id = _seed_player_actor(engine, world_id, worldline_id, tester_id, scene_id)
    conversation_id, turn_id, failed_presentation_id = _seed_conversation(
        engine,
        world_id,
        worldline_id,
        scene_id,
        render_state="failed",
    )
    hidden_conversation_id, hidden_turn_id, hidden_base_presentation_id = _seed_conversation(
        engine,
        world_id,
        worldline_id,
        scene_id,
    )
    failed_media_conversation_id, failed_media_turn_id, failed_media_base_presentation_id = (
        _seed_conversation(
            engine,
            world_id,
            worldline_id,
            scene_id,
        )
    )
    other_conversation_id, _other_turn_id, _other_presentation_id = _seed_conversation(
        engine,
        other_world_id,
        other_worldline_id,
        other_scene_id,
    )
    hidden_presentation_id = _attach_media_to_presentation(
        engine,
        world_id,
        worldline_id,
        hidden_base_presentation_id,
        visibility="hidden",
    )
    failed_media_presentation_id = _attach_media_to_presentation(
        engine,
        world_id,
        worldline_id,
        failed_media_base_presentation_id,
        visibility="player_visible",
        media_job_status="failed",
    )
    failed_conversation_id, _failed_turn_id, _failed_presentation_id = _seed_conversation(
        engine,
        world_id,
        worldline_id,
        scene_id,
        conversation_status="failed",
    )
    _authenticate(client, tester_token)

    cross_conversation = client.post(
        f"/worlds/{world_id}/player-sessions/resume",
        json={
            "worldline_id": str(worldline_id),
            "player_actor_id": str(actor_id),
            "conversation_session_id": str(other_conversation_id),
        },
        headers=_csrf_headers(client),
    )
    failed_presentation = client.post(
        f"/worlds/{world_id}/player-sessions/resume",
        json={
            "worldline_id": str(worldline_id),
            "player_actor_id": str(actor_id),
            "conversation_session_id": str(conversation_id),
            "scene_id": str(scene_id),
            "last_turn_id": str(turn_id),
            "last_presentation_id": str(failed_presentation_id),
        },
        headers=_csrf_headers(client),
    )
    hidden_media = client.post(
        f"/worlds/{world_id}/player-sessions/resume",
        json={
            "worldline_id": str(worldline_id),
            "player_actor_id": str(actor_id),
            "conversation_session_id": str(hidden_conversation_id),
            "scene_id": str(scene_id),
            "last_turn_id": str(hidden_turn_id),
            "last_presentation_id": str(hidden_presentation_id),
        },
        headers=_csrf_headers(client),
    )
    failed_media = client.post(
        f"/worlds/{world_id}/player-sessions/resume",
        json={
            "worldline_id": str(worldline_id),
            "player_actor_id": str(actor_id),
            "conversation_session_id": str(failed_media_conversation_id),
            "scene_id": str(scene_id),
            "last_turn_id": str(failed_media_turn_id),
            "last_presentation_id": str(failed_media_presentation_id),
        },
        headers=_csrf_headers(client),
    )
    failed_conversation = client.post(
        f"/worlds/{world_id}/player-sessions/resume",
        json={
            "worldline_id": str(worldline_id),
            "player_actor_id": str(actor_id),
            "conversation_session_id": str(failed_conversation_id),
        },
        headers=_csrf_headers(client),
    )

    assert cross_conversation.status_code == 400
    assert failed_presentation.status_code == 200
    assert failed_presentation.json()["recovery_status"] == "presentation_unavailable"
    assert hidden_media.status_code == 200
    assert hidden_media.json()["recovery_status"] == "missing_media"
    assert failed_media.status_code == 200
    assert failed_media.json()["recovery_status"] == "media_failure"
    assert failed_conversation.status_code == 200
    assert failed_conversation.json()["recovery_status"] == "provider_failure"
    for response in (
        cross_conversation,
        failed_presentation,
        hidden_media,
        failed_media,
        failed_conversation,
    ):
        _assert_no_forbidden_markers(response.json())


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
        cast(Table, Scene.__table__),
        cast(Table, PlayerActorProfile.__table__),
        cast(Table, ConversationSession.__table__),
        cast(Table, ConversationTurn.__table__),
        cast(Table, MediaJob.__table__),
        cast(Table, MediaAsset.__table__),
        cast(Table, ConversationTurnPresentation.__table__),
        cast(Table, PlayerSession.__table__),
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


def _seed_world_graph(
    engine: Engine,
    owner_id: uuid.UUID,
    *,
    slug: str = "private-beta-world",
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    world_id = uuid.uuid4()
    worldline_id = uuid.uuid4()
    scene_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            World(
                id=world_id,
                owner_user_id=owner_id,
                slug=slug,
                name=slug,
                rules_config={},
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
        session.add(
            Scene(
                id=scene_id,
                world_id=world_id,
                scene_key="home",
                name="Home",
                is_active=True,
            )
        )
        session.commit()
    return world_id, worldline_id, scene_id


def _seed_worldline(engine: Engine, world_id: uuid.UUID, key: str) -> uuid.UUID:
    worldline_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            Worldline(
                id=worldline_id,
                world_id=world_id,
                worldline_key=key,
                name=key,
                status="active",
                created_by_actor_ref="system:test",
                metadata_json={},
            )
        )
        session.commit()
    return worldline_id


def _seed_player_actor(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    user_id: uuid.UUID,
    scene_id: uuid.UUID | None,
) -> uuid.UUID:
    actor_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            PlayerActorProfile(
                id=actor_id,
                world_id=world_id,
                worldline_id=worldline_id,
                user_id=user_id,
                actor_ref=f"player:{user_id}:primary",
                display_name="Tester",
                current_scene_id=scene_id,
                profile_json={},
                is_active=True,
            )
        )
        session.commit()
    return actor_id


def _seed_conversation(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    scene_id: uuid.UUID,
    *,
    render_state: str = "visual_rendered",
    conversation_status: str = "running",
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    conversation_id = uuid.uuid4()
    turn_id = uuid.uuid4()
    presentation_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            ConversationSession(
                id=conversation_id,
                world_id=world_id,
                worldline_id=worldline_id,
                scene_id=scene_id,
                session_key=f"session-{conversation_id}",
                title="Session",
                scope_type="scene",
                mode="manual_chain",
                status=conversation_status,
                objective="Resume",
                opening_prompt="Start",
                max_turns=4,
                next_turn_index=1,
                policy_config={},
                writer_config={},
                memory_config={},
            )
        )
        session.add(
            ConversationTurn(
                id=turn_id,
                session_id=conversation_id,
                turn_index=0,
                speaker_kind="operator",
                input_text="Hello",
                status="succeeded",
            )
        )
        session.add(
            ConversationTurnPresentation(
                id=presentation_id,
                world_id=world_id,
                worldline_id=worldline_id,
                conversation_id=conversation_id,
                turn_id=turn_id,
                presentation_json={"caption": "Safe"},
                render_state=render_state,
            )
        )
        session.commit()
    return conversation_id, turn_id, presentation_id


def _attach_media_to_presentation(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    presentation_id: uuid.UUID,
    *,
    visibility: str,
    media_job_status: str = "succeeded",
) -> uuid.UUID:
    job_id = uuid.uuid4()
    asset_id = uuid.uuid4()
    with Session(engine) as session:
        presentation = session.get(ConversationTurnPresentation, presentation_id)
        assert presentation is not None
        session.add(
            MediaJob(
                id=job_id,
                world_id=world_id,
                worldline_id=worldline_id,
                conversation_id=presentation.conversation_id,
                turn_id=presentation.turn_id,
                job_kind="composition",
                status=media_job_status,
                priority=0,
                provider_config_json={},
                request_json={},
                result_json={},
                created_by_actor_ref="system:test",
            )
        )
        session.add(
            MediaAsset(
                id=asset_id,
                world_id=world_id,
                worldline_id=worldline_id,
                asset_kind="image",
                asset_role="composite_image",
                source_kind="composed",
                status="available",
                visibility=visibility,
                source_job_id=job_id,
                created_by_actor_ref="system:test",
            )
        )
        presentation.composite_scene_asset_id = asset_id
        presentation.render_state = "visual_rendered"
        session.commit()
    return presentation_id


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
    client.cookies.set(SESSION_COOKIE_NAME, token)
    client.cookies.set(CSRF_COOKIE_NAME, "csrf-token")


def _csrf_headers(client: TestClient) -> dict[str, str]:
    token = client.cookies.get(CSRF_COOKIE_NAME) or "csrf-token"
    return {CSRF_HEADER_NAME: token}


def _assert_no_forbidden_markers(value: object) -> None:
    serialized = str(value).lower()
    for marker in FORBIDDEN_MARKERS:
        assert marker.lower() not in serialized
