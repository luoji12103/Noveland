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
from noveland.core.database import import_model_modules
from noveland.events.models import WorldEventModel
from noveland.private_beta.models import PrivateBetaInvite
from noveland.private_beta.tokens import hash_invite_token
from noveland.services.api.app import create_app
from noveland.services.api.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from noveland.services.api.dependencies import get_db_session
from noveland.worlds.models import PlayerActorProfile, World, Worldline, WorldMembership
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


def test_admin_invite_lifecycle_redeem_and_profile_bootstrap_are_safe() -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test", platform_admin=True)
    tester_id, tester_token = _seed_user(engine, "tester@example.test")
    world_id, worldline_id = _seed_world_graph(engine, admin_id)
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _authenticate(client, admin_token)

    created = client.post(
        f"/worlds/{world_id}/private-beta/invites",
        json={
            "invited_email": "tester@example.test",
            "worldline_id": str(worldline_id),
            "expires_at": _iso(datetime.now(UTC) + timedelta(hours=2)),
            "metadata": {
                "note": "first tester",
                "token": "should be removed",
                "rawPrompt": "hidden invite prompt",
                "promptSnapshotId": str(uuid.uuid4()),
                "nested": {
                    "rawOutput": "hidden invite output",
                    "storageUri": "opaque-invite-storage",
                    "safe": "kept",
                },
            },
        },
        headers=_csrf_headers(client),
    )
    listed = client.get(f"/worlds/{world_id}/private-beta/invites")

    assert created.status_code == 201
    created_body = created.json()
    token = created_body["token"]
    assert isinstance(token, str)
    assert len(token) >= 32
    invite_id = created_body["invite"]["id"]
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == invite_id
    assert listed.json()[0]["metadata"] == {"note": "first tester", "nested": {"safe": "kept"}}
    assert "token" not in str(listed.json()).lower()
    assert "should be removed" not in str(listed.json()).lower()

    with Session(engine) as session:
        invite = session.get(PrivateBetaInvite, uuid.UUID(invite_id))
        assert invite is not None
        assert invite.token_hash == hash_invite_token(token)
        assert invite.token_hash != token

    _authenticate(client, tester_token)
    redeem = client.post(
        "/private-beta/invites/redeem",
        json={"token": token},
        headers=_csrf_headers(client),
    )
    repeat = client.post(
        "/private-beta/invites/redeem",
        json={"token": token},
        headers=_csrf_headers(client),
    )
    status_response = client.get("/private-beta/onboarding")
    profile = client.post(
        f"/worlds/{world_id}/private-beta/onboarding/player-profile",
        json={
            "worldline_id": str(worldline_id),
            "display_name": "Tester Player",
            "profile": {"pronouns": "they/them", "raw_prompt": "redacted"},
        },
        headers=_csrf_headers(client),
    )
    provider_admin = client.get(f"/worlds/{world_id}/providers")
    invocations_admin = client.get(f"/worlds/{world_id}/invocations")

    assert redeem.status_code == 200
    redeem_body = redeem.json()
    assert redeem_body["membership_role"] == "human_user"
    assert redeem_body["idempotent"] is False
    assert repeat.status_code == 200
    assert repeat.json()["idempotent"] is True
    assert status_response.status_code == 200
    assert len(status_response.json()["access"]) == 1
    assert profile.status_code == 200
    assert profile.json()["player_profile"]["display_name"] == "Tester Player"
    assert "raw_prompt" not in str(profile.json()).lower()
    assert provider_admin.status_code == 403
    assert invocations_admin.status_code in {403, 404}
    _assert_no_forbidden_markers(redeem_body)
    _assert_no_forbidden_markers(status_response.json())
    _assert_no_forbidden_markers(profile.json())

    with Session(engine) as session:
        membership = session.scalars(
            select(WorldMembership).where(
                WorldMembership.world_id == world_id,
                WorldMembership.user_id == tester_id,
            )
        ).one()
        actor = session.scalars(
            select(PlayerActorProfile).where(
                PlayerActorProfile.world_id == world_id,
                PlayerActorProfile.worldline_id == worldline_id,
                PlayerActorProfile.user_id == tester_id,
            )
        ).one()
        assert membership.role == AuthRole.HUMAN_USER.value
        assert actor.display_name == "Tester Player"
        assert _count_rows(session, WorldEventModel) == 0


def test_private_beta_invite_rejects_non_admin_and_bad_lifecycle() -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test", platform_admin=True)
    tester_id, tester_token = _seed_user(engine, "tester@example.test")
    other_id, other_token = _seed_user(engine, "other@example.test")
    world_id, worldline_id = _seed_world_graph(engine, admin_id)
    other_world_id, other_worldline_id = _seed_world_graph(engine, admin_id, slug="other-world")
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, tester_id, AuthRole.HUMAN_USER)
    _add_membership(engine, other_world_id, admin_id, AuthRole.WORLD_ADMIN)

    _authenticate(client, tester_token)
    non_admin_create = client.post(
        f"/worlds/{world_id}/private-beta/invites",
        json={
            "expires_at": _iso(datetime.now(UTC) + timedelta(hours=2)),
        },
        headers=_csrf_headers(client),
    )

    _authenticate(client, admin_token)
    expired = client.post(
        f"/worlds/{world_id}/private-beta/invites",
        json={
            "invited_email": "tester@example.test",
            "expires_at": _iso(datetime.now(UTC) + timedelta(hours=2)),
        },
        headers=_csrf_headers(client),
    )
    revoked = client.post(
        f"/worlds/{world_id}/private-beta/invites",
        json={
            "invited_user_id": str(tester_id),
            "worldline_id": str(worldline_id),
            "expires_at": _iso(datetime.now(UTC) + timedelta(hours=2)),
        },
        headers=_csrf_headers(client),
    )
    waitlisted = client.post(
        f"/worlds/{world_id}/private-beta/invites",
        json={
            "invited_user_id": str(tester_id),
            "status": "waitlisted",
            "expires_at": _iso(datetime.now(UTC) + timedelta(hours=2)),
        },
        headers=_csrf_headers(client),
    )
    cross_world = client.post(
        f"/worlds/{world_id}/private-beta/invites",
        json={
            "invited_user_id": str(tester_id),
            "worldline_id": str(other_worldline_id),
            "expires_at": _iso(datetime.now(UTC) + timedelta(hours=2)),
        },
        headers=_csrf_headers(client),
    )
    revoked_response = client.post(
        f"/worlds/{world_id}/private-beta/invites/{revoked.json()['invite']['id']}/revoke",
        json={"reason": "capacity changed"},
        headers=_csrf_headers(client),
    )
    with Session(engine) as session:
        expired_invite = session.get(PrivateBetaInvite, uuid.UUID(expired.json()["invite"]["id"]))
        assert expired_invite is not None
        expired_invite.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        session.commit()

    _authenticate(client, tester_token)
    expired_redeem = client.post(
        "/private-beta/invites/redeem",
        json={"token": expired.json()["token"]},
        headers=_csrf_headers(client),
    )
    revoked_redeem = client.post(
        "/private-beta/invites/redeem",
        json={"token": revoked.json()["token"]},
        headers=_csrf_headers(client),
    )
    waitlisted_redeem = client.post(
        "/private-beta/invites/redeem",
        json={"token": waitlisted.json()["token"]},
        headers=_csrf_headers(client),
    )
    cross_worldline_profile = client.post(
        f"/worlds/{world_id}/private-beta/onboarding/player-profile",
        json={
            "worldline_id": str(other_worldline_id),
            "display_name": "Wrong Branch",
        },
        headers=_csrf_headers(client),
    )

    _authenticate(client, other_token)
    other_redeem = client.post(
        "/private-beta/invites/redeem",
        json={"token": expired.json()["token"]},
        headers=_csrf_headers(client),
    )

    assert non_admin_create.status_code == 403
    assert revoked_response.status_code == 200
    assert cross_world.status_code in {400, 404}
    assert expired_redeem.status_code == 400
    assert revoked_redeem.status_code == 400
    assert waitlisted_redeem.status_code == 400
    assert cross_worldline_profile.status_code in {400, 404}
    assert other_redeem.status_code == 400
    _assert_no_forbidden_markers(expired_redeem.json())
    _assert_no_forbidden_markers(revoked_redeem.json())


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
        cast(Table, PlayerActorProfile.__table__),
        cast(Table, PrivateBetaInvite.__table__),
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


def _authenticate(client: TestClient, token: str) -> None:
    client.cookies.set(SESSION_COOKIE_NAME, token)
    client.cookies.set(CSRF_COOKIE_NAME, "csrf-token")


def _csrf_headers(client: TestClient) -> dict[str, str]:
    token = client.cookies.get(CSRF_COOKIE_NAME) or "csrf-token"
    return {CSRF_HEADER_NAME: token}


def _iso(value: datetime) -> str:
    return value.isoformat()


def _count_rows(session: Session, model: type[Any]) -> int:
    return session.scalar(select(func.count(model.id))) or 0


def _assert_no_forbidden_markers(value: object) -> None:
    serialized = str(value).lower()
    for marker in FORBIDDEN_MARKERS:
        assert marker.lower() not in serialized
