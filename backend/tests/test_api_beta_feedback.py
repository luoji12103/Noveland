from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, cast

from fastapi.testclient import TestClient
from noveland.auth import AuthRole
from noveland.auth.contracts import AuthSessionStatus
from noveland.auth.models import AuthSession, PlatformRoleAssignment, User
from noveland.auth.services import hash_session_token
from noveland.beta_feedback.models import BetaFeedbackReport
from noveland.conversations.models import (
    ConversationSession,
    ConversationTurn,
    ConversationTurnPresentation,
)
from noveland.core.database import import_model_modules
from noveland.events.models import WorldEventModel
from noveland.invocations.models import ModelInvocation
from noveland.media.models import MediaAsset, MediaJob
from noveland.services.api.app import create_app
from noveland.services.api.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from noveland.services.api.dependencies import get_db_session
from noveland.worlds.models import PlayerActorProfile, Scene, World, Worldline, WorldMembership
from sqlalchemy import Table, create_engine, func, select
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
    "bytes",
    "raw_prompt",
    "raw_output",
    "prompt_snapshot",
    "api_key",
    "bearer",
    "authorization",
    "secret",
    "invite_token",
    "/tmp/",
    "/root/",
)


def test_tester_creates_own_feedback_and_admin_triages_without_leaks() -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test", platform_admin=True)
    tester_id, tester_token = _seed_user(engine, "tester@example.test")
    world_id, worldline_id, scene_id = _seed_world_graph(engine, admin_id)
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, tester_id, AuthRole.HUMAN_USER)
    actor_id = _seed_player_actor(engine, world_id, worldline_id, tester_id, scene_id)
    conversation_id, turn_id, presentation_id = _seed_conversation(
        engine,
        world_id,
        worldline_id,
        scene_id,
    )
    media_asset_id = _seed_media(engine, world_id, worldline_id, conversation_id, turn_id)
    invocation_id = _seed_invocation(engine, world_id, worldline_id, conversation_id, turn_id)
    before_events = _count_world_events(engine)

    _authenticate(client, tester_token)
    created = client.post(
        f"/worlds/{world_id}/beta-feedback/reports",
        json={
            "worldline_id": str(worldline_id),
            "player_actor_id": str(actor_id),
            "issue_type": "dialogue",
            "severity": "medium",
            "title": "OOC response",
            "description": "The character ignored the established relationship.",
            "reporter_note": "Happened after the second reply.",
            "evidence_refs": [
                {"kind": "conversation", "id": str(conversation_id), "label": "current session"},
                {"kind": "turn", "id": str(turn_id), "label": "reported turn"},
                {"kind": "presentation", "id": str(presentation_id), "role": "scene"},
                {"kind": "media_asset", "id": str(media_asset_id), "role": "background"},
                {"kind": "invocation", "id": str(invocation_id), "role": "generation"},
            ],
            "metadata": {
                "route_state": "scene",
                "storage_uri": "media://hidden",
                "nested": {"raw_prompt": "leak"},
            },
        },
        headers=_csrf_headers(client),
    )
    own_list = client.get(f"/worlds/{world_id}/beta-feedback/reports")

    _authenticate(client, admin_token)
    admin_list = client.get(f"/worlds/{world_id}/beta-feedback/reports?status=submitted")
    triaged = client.patch(
        f"/worlds/{world_id}/beta-feedback/reports/{created.json()['id']}/triage",
        json={
            "status": "investigating",
            "severity": "high",
            "triage_note": "Reproduce against persona QA report.",
            "repair_proposal_refs": [
                {
                    "proposal_id": str(uuid.uuid4()),
                    "proposal_kind": "persona",
                    "status": "proposed",
                    "metadata": {"secret": "hidden"},
                }
            ],
        },
        headers=_csrf_headers(client),
    )

    assert created.status_code == 201
    body = created.json()
    assert body["reporter_user_id"] == str(tester_id)
    assert body["player_actor_id"] == str(actor_id)
    assert body["status"] == "submitted"
    assert [ref["kind"] for ref in body["evidence_refs"]] == [
        "conversation",
        "turn",
        "presentation",
        "media_asset",
        "invocation",
    ]
    assert own_list.status_code == 200
    assert [item["id"] for item in own_list.json()] == [body["id"]]
    assert admin_list.status_code == 200
    assert [item["id"] for item in admin_list.json()] == [body["id"]]
    assert triaged.status_code == 200
    assert triaged.json()["status"] == "investigating"
    assert triaged.json()["severity"] == "high"
    assert triaged.json()["repair_proposal_refs"][0]["proposal_kind"] == "persona"
    assert _count_world_events(engine) == before_events
    _assert_no_forbidden_markers(created.json())
    _assert_no_forbidden_markers(own_list.json())
    _assert_no_forbidden_markers(admin_list.json())
    _assert_no_forbidden_markers(triaged.json())


def test_beta_feedback_preserves_reporter_privacy_and_admin_only_triage() -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test", platform_admin=True)
    tester_id, tester_token = _seed_user(engine, "tester@example.test")
    other_id, other_token = _seed_user(engine, "other@example.test")
    world_id, worldline_id, scene_id = _seed_world_graph(engine, admin_id)
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, tester_id, AuthRole.HUMAN_USER)
    _add_membership(engine, world_id, other_id, AuthRole.HUMAN_USER)
    _seed_player_actor(engine, world_id, worldline_id, tester_id, scene_id)

    _authenticate(client, tester_token)
    created = client.post(
        f"/worlds/{world_id}/beta-feedback/reports",
        json=_report_payload(worldline_id, "voice"),
        headers=_csrf_headers(client),
    )
    non_admin_triage = client.patch(
        f"/worlds/{world_id}/beta-feedback/reports/{created.json()['id']}/triage",
        json={"status": "triaged", "triage_note": "not allowed"},
        headers=_csrf_headers(client),
    )

    _authenticate(client, other_token)
    other_list = client.get(f"/worlds/{world_id}/beta-feedback/reports")
    other_read = client.get(f"/worlds/{world_id}/beta-feedback/reports/{created.json()['id']}")

    _authenticate(client, admin_token)
    admin_list = client.get(f"/worlds/{world_id}/beta-feedback/reports")

    assert created.status_code == 201
    assert non_admin_triage.status_code == 403
    assert other_list.status_code == 200
    assert other_list.json() == []
    assert other_read.status_code == 404
    assert admin_list.status_code == 200
    assert admin_list.json()[0]["reporter_user_id"] == str(tester_id)
    _assert_no_forbidden_markers(admin_list.json())


def test_beta_feedback_rejects_cross_worldline_and_hidden_evidence() -> None:
    client, engine = _client_with_database()
    admin_id, _admin_token = _seed_user(engine, "admin@example.test", platform_admin=True)
    tester_id, tester_token = _seed_user(engine, "tester@example.test")
    world_id, worldline_id, scene_id = _seed_world_graph(engine, admin_id)
    fork_worldline_id = _seed_worldline(engine, world_id, "fork")
    other_world_id, other_worldline_id, other_scene_id = _seed_world_graph(
        engine,
        admin_id,
        slug="other-world",
    )
    _add_membership(engine, world_id, tester_id, AuthRole.HUMAN_USER)
    _add_membership(engine, other_world_id, tester_id, AuthRole.HUMAN_USER)
    other_conversation_id, _other_turn_id, _other_presentation_id = _seed_conversation(
        engine,
        other_world_id,
        other_worldline_id,
        other_scene_id,
    )
    fork_conversation_id, _fork_turn_id, _fork_presentation_id = _seed_conversation(
        engine,
        world_id,
        fork_worldline_id,
        scene_id,
    )
    hidden_media_id = _seed_media(
        engine,
        world_id,
        worldline_id,
        None,
        None,
        visibility="hidden",
    )

    _authenticate(client, tester_token)
    cross_world = client.post(
        f"/worlds/{world_id}/beta-feedback/reports",
        json={
            **_report_payload(worldline_id, "playback"),
            "evidence_refs": [{"kind": "conversation", "id": str(other_conversation_id)}],
        },
        headers=_csrf_headers(client),
    )
    cross_worldline = client.post(
        f"/worlds/{world_id}/beta-feedback/reports",
        json={
            **_report_payload(worldline_id, "playback"),
            "evidence_refs": [{"kind": "conversation", "id": str(fork_conversation_id)}],
        },
        headers=_csrf_headers(client),
    )
    hidden_media = client.post(
        f"/worlds/{world_id}/beta-feedback/reports",
        json={
            **_report_payload(worldline_id, "sprite"),
            "evidence_refs": [{"kind": "media_asset", "id": str(hidden_media_id)}],
        },
        headers=_csrf_headers(client),
    )
    unsafe_text = client.post(
        f"/worlds/{world_id}/beta-feedback/reports",
        json={
            **_report_payload(worldline_id, "provider"),
            "description": "raw_prompt should not be accepted",
        },
        headers=_csrf_headers(client),
    )

    assert cross_world.status_code == 404
    assert cross_worldline.status_code == 400
    assert hidden_media.status_code == 404
    assert unsafe_text.status_code == 400
    for response in (cross_world, cross_worldline, hidden_media, unsafe_text):
        _assert_no_forbidden_markers(response.json())


def test_beta_feedback_schema_filtering_and_safe_issue_taxonomy() -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test", platform_admin=True)
    tester_id, tester_token = _seed_user(engine, "tester@example.test")
    world_id, worldline_id, _scene_id = _seed_world_graph(engine, admin_id)
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, tester_id, AuthRole.HUMAN_USER)

    _authenticate(client, tester_token)
    persona = client.post(
        f"/worlds/{world_id}/beta-feedback/reports",
        json=_report_payload(worldline_id, "persona"),
        headers=_csrf_headers(client),
    )
    quota = client.post(
        f"/worlds/{world_id}/beta-feedback/reports",
        json=_report_payload(worldline_id, "quota"),
        headers=_csrf_headers(client),
    )

    _authenticate(client, admin_token)
    persona_list = client.get(f"/worlds/{world_id}/beta-feedback/reports?issue_type=persona")
    triaged = client.patch(
        f"/worlds/{world_id}/beta-feedback/reports/{quota.json()['id']}/triage",
        json={"status": "dismissed", "triage_note": "Duplicate quota report."},
        headers=_csrf_headers(client),
    )
    dismissed_list = client.get(f"/worlds/{world_id}/beta-feedback/reports?status=dismissed")

    assert persona.status_code == 201
    assert quota.status_code == 201
    assert persona_list.status_code == 200
    assert [item["id"] for item in persona_list.json()] == [persona.json()["id"]]
    assert triaged.status_code == 200
    assert dismissed_list.status_code == 200
    assert [item["id"] for item in dismissed_list.json()] == [quota.json()["id"]]


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
        cast(Table, ModelInvocation.__table__),
        cast(Table, MediaAsset.__table__),
        cast(Table, ConversationTurnPresentation.__table__),
        cast(Table, BetaFeedbackReport.__table__),
        cast(Table, WorldEventModel.__table__),
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
                scene_key=f"{slug}-home",
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
                status="running",
                objective="Feedback",
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
                speaker_kind="agent",
                input_text="Hello",
                output_text="Hi",
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
                render_state="visual_rendered",
            )
        )
        session.commit()
    return conversation_id, turn_id, presentation_id


def _seed_media(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    conversation_id: uuid.UUID | None,
    turn_id: uuid.UUID | None,
    *,
    visibility: str = "player_visible",
) -> uuid.UUID:
    job_id = uuid.uuid4()
    asset_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            MediaJob(
                id=job_id,
                world_id=world_id,
                worldline_id=worldline_id,
                conversation_id=conversation_id,
                turn_id=turn_id,
                job_kind="composition",
                status="succeeded",
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
                asset_role="scene_background",
                source_kind="imported_original",
                status="available",
                visibility=visibility,
                source_job_id=job_id,
                storage_uri="media://not-returned",
                created_by_actor_ref="system:test",
            )
        )
        session.commit()
    return asset_id


def _seed_invocation(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    conversation_id: uuid.UUID,
    turn_id: uuid.UUID,
) -> uuid.UUID:
    invocation_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            ModelInvocation(
                id=invocation_id,
                world_id=world_id,
                worldline_id=worldline_id,
                trace_id=uuid.uuid4(),
                invocation_kind="conversation_turn",
                actor_kind="player",
                actor_ref="player:test",
                conversation_id=conversation_id,
                turn_id=turn_id,
                provider_kind="local_stub",
                model_name="fake-model",
                usage_json={"total_tokens": 1},
                estimated_cost=Decimal("0.00"),
                status="succeeded",
                visibility="world_admin",
                redaction_status="redacted",
                retention_policy="short_term",
                contains_sensitive_context=False,
            )
        )
        session.commit()
    return invocation_id


def _report_payload(worldline_id: uuid.UUID, issue_type: str) -> dict[str, Any]:
    return {
        "worldline_id": str(worldline_id),
        "issue_type": issue_type,
        "severity": "low",
        "title": f"{issue_type} issue",
        "description": "Tester-visible issue report.",
    }


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


def _count_world_events(engine: Engine) -> int:
    with Session(engine) as session:
        return session.scalar(select(func.count(WorldEventModel.id))) or 0


def _assert_no_forbidden_markers(value: object) -> None:
    serialized = str(value).lower()
    for marker in FORBIDDEN_MARKERS:
        assert marker.lower() not in serialized
