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
from noveland.invocations.models import (
    AgentRuntimeRunModelInvocation,
    ModelInvocation,
    ModelInvocationTag,
    PromptSnapshot,
    PromptTemplate,
)
from noveland.narrative.models import NarrativeArtifact
from noveland.providers.contracts import (
    ProviderAdapterKind,
    ProviderIntegrationCreate,
    ProviderKind,
    ProviderScopeKind,
)
from noveland.providers.models import ProviderCapability, ProviderHealthCheck, ProviderIntegration
from noveland.providers.registry import ProviderRegistryService
from noveland.services.api.app import create_app
from noveland.services.api.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from noveland.services.api.dependencies import get_db_session
from noveland.worlds.models import (
    CharacterEmotionalState,
    CharacterKnowledgeFact,
    GMEventProposal,
    NarrativeContinuityReview,
    PlotThread,
    RouteAffinity,
    Scene,
    SecretRecord,
    StoryHook,
    World,
    WorldBible,
    Worldline,
    WorldMembership,
)
from noveland.worlds.worldlines import ensure_primary_worldline
from sqlalchemy import Table, create_engine, func, select
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


def test_narrative_quality_gm_generation_api_creates_proposal() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id, worldline_id, _agent_id = _seed_world_agent_and_fact(engine, owner_id)
    provider_id = _seed_text_provider(engine, world_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)

    _authenticate(client, owner_token)
    response = client.post(
        f"/worlds/{world_id}/narrative-quality/gm/proposals/generate",
        json={
            "worldline_id": str(worldline_id),
            "provider_id": str(provider_id),
            "prompt_goal": "Create a daily classroom beat.",
            "title": "Daily classroom beat",
            "event_name": "gm.classroom_beat",
            "payload_json": {"kind": "daily"},
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["dry_run"] is False
    assert body["provider"]["provider_kind"] == "text_generation"
    assert body["proposal"]["status"] == "proposed"
    assert body["proposal"]["id"] is not None
    assert "raw_output" not in response.text
    with Session(engine) as session:
        assert session.scalar(select(func.count(GMEventProposal.id))) == 1
        assert session.scalar(select(func.count(ModelInvocation.id))) == 1
        assert session.scalar(select(func.count(WorldEventModel.id))) == 0


def test_narrative_quality_gm_generation_api_requires_world_admin() -> None:
    client, engine = _client_with_database()
    owner_id, _owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id, worldline_id, _agent_id = _seed_world_agent_and_fact(engine, owner_id)
    provider_id = _seed_text_provider(engine, world_id)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)

    _authenticate(client, member_token)
    response = client.post(
        f"/worlds/{world_id}/narrative-quality/gm/proposals/generate",
        json={
            "worldline_id": str(worldline_id),
            "provider_id": str(provider_id),
            "prompt_goal": "Should be forbidden.",
        },
    )

    assert response.status_code == 403
    with Session(engine) as session:
        assert session.scalar(select(func.count(GMEventProposal.id))) == 0
        assert session.scalar(select(func.count(ModelInvocation.id))) == 0


def test_narrative_quality_dialogue_review_api_reviews_turn() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id, worldline_id, agent_id = _seed_world_agent_and_fact(engine, owner_id)
    conversation_id, turn_id = _seed_conversation_turn(
        engine,
        world_id,
        worldline_id,
        agent_id,
        output_text="I will keep the quiet lantern safe.",
    )
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)

    _authenticate(client, owner_token)
    response = client.post(
        f"/worlds/{world_id}/narrative-quality/dialogue/review",
        json={
            "worldline_id": str(worldline_id),
            "conversation_id": str(conversation_id),
            "turn_id": str(turn_id),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["speaker_agent_id"] == str(agent_id)
    assert body["turn_id"] == str(turn_id)
    assert body["review_status"] in {"pass", "warning"}


def test_narrative_quality_dialogue_review_api_requires_world_admin() -> None:
    client, engine = _client_with_database()
    owner_id, _owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id, worldline_id, agent_id = _seed_world_agent_and_fact(engine, owner_id)
    conversation_id, _turn_id = _seed_conversation_turn(
        engine,
        world_id,
        worldline_id,
        agent_id,
        output_text="Hello.",
    )
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)

    _authenticate(client, member_token)
    response = client.post(
        f"/worlds/{world_id}/narrative-quality/dialogue/review",
        json={
            "worldline_id": str(worldline_id),
            "conversation_id": str(conversation_id),
            "speaker_agent_id": str(agent_id),
            "text": "Hello.",
        },
    )

    assert response.status_code == 403


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
        cast(Table, RouteAffinity.__table__),
        cast(Table, NarrativeContinuityReview.__table__),
        cast(Table, GMEventProposal.__table__),
        cast(Table, ProviderIntegration.__table__),
        cast(Table, ProviderCapability.__table__),
        cast(Table, ProviderHealthCheck.__table__),
        cast(Table, ModelInvocation.__table__),
        cast(Table, PromptTemplate.__table__),
        cast(Table, PromptSnapshot.__table__),
        cast(Table, AgentRuntimeRunModelInvocation.__table__),
        cast(Table, ModelInvocationTag.__table__),
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


def _seed_text_provider(engine: Engine, world_id: uuid.UUID) -> uuid.UUID:
    with Session(engine) as session:
        provider = ProviderRegistryService(session).create_provider(
            ProviderIntegrationCreate(
                world_id=world_id,
                scope_kind=ProviderScopeKind.WORLD,
                provider_kind=ProviderKind.TEXT_GENERATION,
                adapter_kind=ProviderAdapterKind.FAKE,
                provider_key="fake-text",
                display_name="Fake Text",
            )
        )
        session.commit()
        return provider.id


def _seed_conversation_turn(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    agent_id: uuid.UUID,
    *,
    output_text: str,
) -> tuple[uuid.UUID, uuid.UUID]:
    conversation_id = uuid.uuid4()
    turn_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            ConversationSession(
                id=conversation_id,
                world_id=world_id,
                worldline_id=worldline_id,
                session_key=f"session-{conversation_id.hex[:8]}",
                title="Review session",
                scope_type="world",
                mode="manual_chain",
                status="running",
                objective="Review dialogue.",
                opening_prompt="Start.",
                max_turns=4,
                policy_config={
                    "error_policy": "fail_session",
                    "max_consecutive_failed_turns": 2,
                    "loop_guard_window": 3,
                    "repeat_output_threshold": 2,
                    "speaker_policy": "round_robin",
                },
                writer_config={},
                memory_config={},
            )
        )
        session.add(
            ConversationParticipant(
                id=uuid.uuid4(),
                session_id=conversation_id,
                agent_id=agent_id,
                turn_order=0,
                is_enabled=True,
            )
        )
        session.add(
            ConversationTurn(
                id=turn_id,
                session_id=conversation_id,
                turn_index=0,
                speaker_kind="agent",
                speaker_agent_id=agent_id,
                input_text="Operator prompt",
                output_text=output_text,
                status="succeeded",
            )
        )
        session.commit()
        return conversation_id, turn_id
