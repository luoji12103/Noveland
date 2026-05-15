from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import cast

from fastapi.testclient import TestClient
from noveland.agents.models import Agent, AgentRelationshipEdge
from noveland.auth import AuthRole
from noveland.auth.contracts import AuthSessionStatus
from noveland.auth.models import AuthSession, PlatformRoleAssignment, User
from noveland.auth.services import hash_session_token
from noveland.conversations.models import (
    ConversationParticipant,
    ConversationSession,
    ConversationTurn,
)
from noveland.events.models import WorldEventModel
from noveland.narrative.models import NarrativeArtifact
from noveland.services.api.app import create_app
from noveland.services.api.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from noveland.services.api.dependencies import get_db_session
from noveland.worlds.models import (
    CharacterEmotionalState,
    CharacterKnowledgeFact,
    PlotThread,
    Scene,
    SecretRecord,
    StoryHook,
    World,
    WorldBible,
    Worldline,
    WorldMembership,
)
from noveland.worlds.worldlines import ensure_primary_worldline
from sqlalchemy import Table, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_narrative_quality_context_preview_api_requires_world_admin() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id, worldline_id, agent_id = _seed_world_agent_and_fact(engine, owner_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)

    _authenticate(client, member_token)
    forbidden = client.post(
        f"/worlds/{world_id}/narrative-quality/context/preview",
        json={
            "worldline_id": str(worldline_id),
            "context_kind": "agent",
            "agent_id": str(agent_id),
        },
    )

    _authenticate(client, owner_token)
    allowed = client.post(
        f"/worlds/{world_id}/narrative-quality/context/preview",
        json={
            "worldline_id": str(worldline_id),
            "context_kind": "agent",
            "agent_id": str(agent_id),
        },
    )

    assert forbidden.status_code == 403
    assert allowed.status_code == 200
    assert allowed.json()["context_kind"] == "agent"
    assert allowed.json()["worldline_id"] == str(worldline_id)


def test_narrative_quality_context_preview_api_sanitizes_leaky_context() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id, worldline_id, agent_id = _seed_world_agent_and_fact(
        engine,
        owner_id,
        fact_text="storage_uri=media://leaky/object base64,AAAA",
    )
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)

    _authenticate(client, owner_token)
    response = client.post(
        f"/worlds/{world_id}/narrative-quality/context/preview",
        json={
            "worldline_id": str(worldline_id),
            "context_kind": "agent",
            "agent_id": str(agent_id),
        },
    )

    assert response.status_code == 200
    text = response.text.lower()
    assert "storage_uri" not in text
    assert "media://" not in text
    assert "base64" not in text


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
        cast(Table, World.__table__),
        cast(Table, Worldline.__table__),
        cast(Table, WorldMembership.__table__),
        cast(Table, Scene.__table__),
        cast(Table, Agent.__table__),
        cast(Table, AgentRelationshipEdge.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, WorldBible.__table__),
        cast(Table, SecretRecord.__table__),
        cast(Table, CharacterKnowledgeFact.__table__),
        cast(Table, CharacterEmotionalState.__table__),
        cast(Table, StoryHook.__table__),
        cast(Table, PlotThread.__table__),
        cast(Table, ConversationSession.__table__),
        cast(Table, ConversationParticipant.__table__),
        cast(Table, ConversationTurn.__table__),
        cast(Table, NarrativeArtifact.__table__),
    ):
        table.create(engine)


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
            )
        )
        session.commit()
    return user_id, token


def _seed_world_agent_and_fact(
    engine: Engine,
    owner_user_id: uuid.UUID,
    fact_text: str = "The classroom lights are on.",
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    world_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            World(
                id=world_id,
                owner_user_id=owner_user_id,
                slug=f"world-{world_id.hex[:8]}",
                name="World",
            )
        )
        worldline = ensure_primary_worldline(session, world_id)
        session.add(
            Agent(
                id=agent_id,
                world_id=world_id,
                agent_key=f"agent-{agent_id.hex[:8]}",
                display_name="Alice",
                kind="role_agent",
                character_profile={},
                config={},
            )
        )
        session.flush()
        session.add(
            CharacterKnowledgeFact(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline.id,
                agent_id=agent_id,
                fact_key="fact-1",
                knowledge_kind="fact",
                content=fact_text,
                confidence=90,
                visibility="public",
                is_active=True,
                metadata_json={},
            )
        )
        session.commit()
        return world_id, worldline.id, agent_id


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
    client.cookies.set(CSRF_COOKIE_NAME, "csrf")
    client.headers.update({CSRF_HEADER_NAME: "csrf"})
