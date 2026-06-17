from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from fastapi.testclient import TestClient
from noveland.auth import AuthRole
from noveland.auth.contracts import AuthSessionStatus
from noveland.auth.models import AuthSession, PlatformRoleAssignment, User
from noveland.auth.services import hash_session_token
from noveland.conversations.models import ConversationSession
from noveland.core.database import import_model_modules
from noveland.events.models import WorldEventModel
from noveland.player_privacy.models import PlayerPrivacyRequest
from noveland.services.api.app import create_app
from noveland.services.api.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from noveland.services.api.dependencies import get_db_session
from noveland.worlds.models import (
    InWorldNotification,
    PlayerActorProfile,
    PlayerChoiceRecord,
    PlayerInterventionRecord,
    PlayerJournalEntry,
    World,
    Worldline,
    WorldMembership,
)
from sqlalchemy import Table, create_engine, func, select
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
    "api_key",
    "bearer_token",
    "authorization",
    "secret",
    "/tmp/",
    "/root/",
)


def test_player_privacy_export_is_player_scoped_and_redacted() -> None:
    client, engine = _client_with_database()
    admin_id, _admin_token = _seed_user(engine, "admin@example.test", platform_admin=True)
    member_id, member_token = _seed_user(engine, "member@example.test")
    other_id, other_token = _seed_user(engine, "other@example.test")
    world_id, worldline_id = _seed_world_graph(engine, admin_id)
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    _add_membership(engine, world_id, other_id, AuthRole.HUMAN_USER)
    _seed_player_records(engine, world_id, worldline_id, member_id)
    _seed_player_records(engine, world_id, worldline_id, other_id, choice_key="other-choice")
    with Session(engine) as session:
        member = session.get(User, member_id)
        assert member is not None
        member.display_name = "Member raw_prompt display"
        actor = session.scalars(
            select(PlayerActorProfile).where(
                PlayerActorProfile.world_id == world_id,
                PlayerActorProfile.worldline_id == worldline_id,
                PlayerActorProfile.user_id == member_id,
            )
        ).one()
        actor.display_name = "Player storage_uri media://private/actor"
        session.commit()

    unauthenticated = client.get(f"/worlds/{world_id}/player/privacy/export")
    _authenticate_without_csrf(client, member_token)
    missing_csrf_export_request = client.post(
        f"/worlds/{world_id}/player/privacy/export",
        json={"worldline_id": str(worldline_id)},
    )

    _authenticate(client, member_token)
    export_response = client.get(
        f"/worlds/{world_id}/player/privacy/export",
        params={"worldline_id": str(worldline_id)},
    )
    export_request_response = client.post(
        f"/worlds/{world_id}/player/privacy/export",
        json={"worldline_id": str(worldline_id)},
    )

    _authenticate(client, other_token)
    other_export_response = client.get(
        f"/worlds/{world_id}/player/privacy/export",
        params={"worldline_id": str(worldline_id)},
    )

    assert unauthenticated.status_code == 401
    assert missing_csrf_export_request.status_code == 403
    assert export_response.status_code == 200
    export = export_response.json()
    assert export["profile"]["email"] == "member@example.test"
    assert export["profile"]["display_name"] == "[REDACTED]"
    assert export["player_actors"][0]["display_name"] == "[REDACTED]"
    assert export["counts"] == {
        "player_actors": 1,
        "choices": 1,
        "journal_entries": 1,
        "notifications": 1,
        "interventions": 1,
        "conversation_references": 1,
    }
    assert export["choices"][0]["choice_key"] == "member-choice"
    assert export["player_actors"][0]["profile"]["safe_label"] == "visible"
    assert "hidden profile prompt" not in str(export).lower()
    assert export["choices"][0]["applied_event_id"] is None
    assert "prompt" not in export["choices"][0]
    assert "context" not in export["choices"][0]
    assert "consequence_preview" not in export["choices"][0]
    assert export["journal_entries"][0]["source_ref"] is None
    assert export["notifications"][0]["source_ref"] is None
    assert export["interventions"][0]["choice_id"] is None
    assert export["interventions"][0]["event_id"] is None
    assert export_request_response.status_code == 200
    assert export_request_response.json()["request_id"] is not None
    assert other_export_response.status_code == 200
    assert other_export_response.json()["choices"][0]["choice_key"] == "other-choice"
    _assert_no_forbidden_markers(export)
    _assert_no_forbidden_markers(export_request_response.json())

    with Session(engine) as session:
        requests = session.scalars(select(PlayerPrivacyRequest)).all()
        assert len(requests) == 1
        assert requests[0].request_kind == "export"
        assert requests[0].status == "completed"


def test_delete_request_is_reviewable_and_does_not_mutate_shared_history() -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test", platform_admin=True)
    member_id, member_token = _seed_user(engine, "member@example.test")
    other_id, other_token = _seed_user(engine, "other@example.test")
    world_id, worldline_id = _seed_world_graph(engine, admin_id)
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    _add_membership(engine, world_id, other_id, AuthRole.HUMAN_USER)
    _seed_player_records(engine, world_id, worldline_id, member_id)

    before_events = _count_rows(engine, WorldEventModel)
    _authenticate_without_csrf(client, member_token)
    missing_csrf_delete_request = client.post(
        f"/worlds/{world_id}/player/privacy/delete-requests",
        json={
            "worldline_id": str(worldline_id),
            "target_ref_kind": "all_player_data",
            "reason": "CSRF must be present.",
        },
    )

    _authenticate(client, member_token)
    created = client.post(
        f"/worlds/{world_id}/player/privacy/delete-requests",
        json={
            "worldline_id": str(worldline_id),
            "target_ref_kind": "all_player_data",
            "reason": "I want this reviewed.",
        },
    )
    unsafe = client.post(
        f"/worlds/{world_id}/player/privacy/delete-requests",
        json={
            "worldline_id": str(worldline_id),
            "reason": "leak storage_uri media://private-object",
        },
    )
    member_review = client.patch(
        f"/worlds/{world_id}/player/privacy/requests/{created.json()['id']}",
        json={"status": "under_review", "review_note": "member cannot review"},
    )

    _authenticate(client, other_token)
    other_list = client.get(f"/worlds/{world_id}/player/privacy/requests")

    _authenticate_without_csrf(client, admin_token)
    missing_csrf_review = client.patch(
        f"/worlds/{world_id}/player/privacy/requests/{created.json()['id']}",
        json={"status": "under_review", "review_note": "missing csrf"},
    )

    _authenticate(client, admin_token)
    admin_list = client.get(f"/worlds/{world_id}/player/privacy/requests")
    reviewed = client.patch(
        f"/worlds/{world_id}/player/privacy/requests/{created.json()['id']}",
        json={"status": "under_review", "review_note": "Safe review started."},
    )
    invalid_complete = client.patch(
        f"/worlds/{world_id}/player/privacy/requests/{created.json()['id']}",
        json={"status": "completed", "review_note": "Should not complete deletion."},
    )

    assert missing_csrf_delete_request.status_code == 403
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "requested"
    assert body["redaction_plan"]["automatic_delete"] is False
    assert body["redaction_plan"]["shared_canonical_records_protected"] is True
    assert unsafe.status_code == 400
    assert member_review.status_code == 403
    assert other_list.status_code == 200
    assert other_list.json() == []
    assert admin_list.status_code == 200
    assert missing_csrf_review.status_code == 403
    assert [item["id"] for item in admin_list.json()] == [body["id"]]
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "under_review"
    assert invalid_complete.status_code == 400
    assert _count_rows(engine, WorldEventModel) == before_events
    _assert_no_forbidden_markers(body)
    _assert_no_forbidden_markers(reviewed.json())


def test_player_privacy_rejects_cross_worldline_requests() -> None:
    client, engine = _client_with_database()
    admin_id, _admin_token = _seed_user(engine, "admin@example.test", platform_admin=True)
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id, _worldline_id = _seed_world_graph(engine, admin_id)
    other_world_id, other_worldline_id = _seed_world_graph(engine, admin_id, slug="other-world")
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    _add_membership(engine, other_world_id, member_id, AuthRole.HUMAN_USER)

    _authenticate(client, member_token)
    response = client.get(
        f"/worlds/{world_id}/player/privacy/export",
        params={"worldline_id": str(other_worldline_id)},
    )
    request_list = client.get(
        f"/worlds/{world_id}/player/privacy/requests",
        params={"worldline_id": str(other_worldline_id)},
    )

    assert response.status_code == 404
    assert request_list.status_code == 404


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
        cast(Table, ConversationSession.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, PlayerActorProfile.__table__),
        cast(Table, PlayerChoiceRecord.__table__),
        cast(Table, PlayerJournalEntry.__table__),
        cast(Table, InWorldNotification.__table__),
        cast(Table, PlayerInterventionRecord.__table__),
        cast(Table, PlayerPrivacyRequest.__table__),
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
    slug: str = "privacy-world",
) -> tuple[uuid.UUID, uuid.UUID]:
    world_id = uuid.uuid4()
    worldline_id = uuid.uuid4()
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
            ConversationSession(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                scene_id=None,
                session_key=f"{slug}-conversation",
                title="Player visible conversation",
                scope_type="world",
                mode="manual_chain",
                status="completed",
                objective="internal objective should not export",
                opening_prompt="raw opening prompt should not export",
                max_turns=4,
                next_turn_index=0,
                policy_config={},
                writer_config={},
                memory_config={},
            )
        )
        session.commit()
    return world_id, worldline_id


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


def _seed_player_records(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    choice_key: str = "member-choice",
) -> None:
    actor_id = uuid.uuid4()
    choice_id = uuid.uuid4()
    now = datetime.now(UTC)
    with Session(engine) as session:
        session.add(
            PlayerActorProfile(
                id=actor_id,
                world_id=world_id,
                worldline_id=worldline_id,
                user_id=user_id,
                actor_ref=f"player:{user_id}:primary",
                display_name=f"Player {user_id}",
                current_scene_id=None,
                profile_json={
                    "safe_label": "visible",
                    "rawPrompt": "hidden profile prompt",
                    "promptSnapshotId": str(uuid.uuid4()),
                    "redacted_test": {
                        "storage_uri": "media://private-object",
                        "storageUri": "opaque-profile-storage",
                    },
                },
                is_active=True,
            )
        )
        session.add(
            PlayerChoiceRecord(
                id=choice_id,
                world_id=world_id,
                worldline_id=worldline_id,
                user_id=user_id,
                player_actor_id=actor_id,
                choice_key=choice_key,
                choice_kind="route",
                prompt="Raw prompt should never appear in export.",
                selected_option="Stay after school.",
                context_json={"raw_prompt": "internal context"},
                consequence_preview={"raw_output": "internal consequence"},
                applied_event_id=uuid.uuid4(),
            )
        )
        session.add(
            PlayerJournalEntry(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                user_id=user_id,
                player_actor_id=actor_id,
                entry_kind="choice",
                title="Festival prep",
                body="The player helped with festival preparations.",
                source_event_id=None,
                source_ref=str(choice_id),
                visibility="player_private",
                metadata_json={"authorization": "Bearer sk-private"},
            )
        )
        session.add(
            InWorldNotification(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                user_id=user_id,
                notification_kind="rumor",
                title="Club room notice",
                body="Someone mentioned the letter.",
                source_event_id=None,
                source_ref=str(choice_id),
                status="unread",
                metadata_json={"secret": "private"},
            )
        )
        session.add(
            PlayerInterventionRecord(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                user_id=user_id,
                player_actor_id=actor_id,
                intervention_kind="contact",
                target_agent_id=None,
                target_scene_id=None,
                prompt="Raw intervention prompt should not export.",
                choice_id=choice_id,
                event_id=uuid.uuid4(),
                status="recorded",
                metadata_json={},
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()


def _authenticate(client: TestClient, token: str) -> None:
    client.cookies.clear()
    client.headers.clear()
    client.cookies.set(SESSION_COOKIE_NAME, token)
    client.cookies.set(CSRF_COOKIE_NAME, "csrf-token")
    client.headers.update({CSRF_HEADER_NAME: "csrf-token"})


def _authenticate_without_csrf(client: TestClient, token: str) -> None:
    client.cookies.clear()
    client.headers.clear()
    client.cookies.set(SESSION_COOKIE_NAME, token)


def _count_rows(engine: Engine, model: type[Any]) -> int:
    with Session(engine) as session:
        return session.scalar(select(func.count(model.id))) or 0


def _assert_no_forbidden_markers(value: object) -> None:
    serialized = str(value).lower()
    for marker in FORBIDDEN_MARKERS:
        assert marker.lower() not in serialized
