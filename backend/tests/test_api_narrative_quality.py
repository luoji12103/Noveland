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
    ConversationTurnPresentation,
)
from noveland.events.models import WorldEventModel
from noveland.invocations.models import (
    AgentRuntimeRunModelInvocation,
    ModelInvocation,
    ModelInvocationTag,
    PromptSnapshot,
    PromptTemplate,
)
from noveland.media.models import MediaAsset
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
from noveland.speech.models import AgentVoiceProfileBinding, SpeechStyleMapping, VoiceProfile
from noveland.visual.models import CharacterSpriteSet, CharacterSpriteVariant
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


def test_narrative_quality_presentation_alignment_api_reviews_turn() -> None:
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
    _seed_aligned_presentation(
        engine,
        world_id,
        worldline_id,
        agent_id,
        conversation_id,
        turn_id,
    )
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)

    _authenticate(client, owner_token)
    response = client.post(
        f"/worlds/{world_id}/narrative-quality/presentations/alignment",
        json={
            "worldline_id": str(worldline_id),
            "conversation_id": str(conversation_id),
            "turn_id": str(turn_id),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["alignment_status"] == "pass"
    assert body["emotion_key"] == "happy"
    assert body["sprite_variant_id"] is not None
    assert body["voice_profile_id"] is not None
    assert "storage_uri" not in response.text
    assert "raw_prompt" not in response.text
    with Session(engine) as session:
        assert session.scalar(select(func.count(WorldEventModel.id))) == 0


def test_narrative_quality_presentation_alignment_api_requires_world_admin() -> None:
    client, engine = _client_with_database()
    owner_id, _owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id, worldline_id, agent_id = _seed_world_agent_and_fact(engine, owner_id)
    conversation_id, turn_id = _seed_conversation_turn(
        engine,
        world_id,
        worldline_id,
        agent_id,
        output_text="Hello.",
    )
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)

    _authenticate(client, member_token)
    response = client.post(
        f"/worlds/{world_id}/narrative-quality/presentations/alignment",
        json={
            "worldline_id": str(worldline_id),
            "conversation_id": str(conversation_id),
            "turn_id": str(turn_id),
        },
    )

    assert response.status_code == 403


def test_narrative_quality_writer_v2_api_creates_worldline_scoped_draft() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id, worldline_id, agent_id = _seed_world_agent_and_fact(engine, owner_id)
    conversation_id, _turn_id = _seed_conversation_turn(
        engine,
        world_id,
        worldline_id,
        agent_id,
        output_text="I will keep the quiet lantern safe.",
    )
    provider_id = _seed_text_provider(engine, world_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)

    _authenticate(client, owner_token)
    response = client.post(
        f"/worlds/{world_id}/narrative-quality/writer/generate",
        json={
            "worldline_id": str(worldline_id),
            "conversation_id": str(conversation_id),
            "provider_id": str(provider_id),
            "artifact_kind": "chapter_draft",
            "title": "Quiet chapter",
            "prompt_goal": "Draft a quiet reader-safe chapter.",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["dry_run"] is False
    assert body["artifact"]["worldline_id"] == str(worldline_id)
    assert body["artifact"]["source_conversation_id"] == str(conversation_id)
    assert body["artifact"]["metadata"]["source"] == "narrative_writer_v2"
    assert body["invocation"]["status"] == "succeeded"
    assert "raw_prompt" not in response.text
    assert "storage_uri" not in response.text
    with Session(engine) as session:
        artifact = session.get(NarrativeArtifact, uuid.UUID(body["artifact"]["id"]))
        assert artifact is not None
        assert artifact.worldline_id == worldline_id
        assert session.scalar(select(func.count(ModelInvocation.id))) == 1
        assert session.scalar(select(func.count(WorldEventModel.id))) == 0


def test_narrative_quality_writer_v2_api_dry_run_creates_no_artifact() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id, worldline_id, _agent_id = _seed_world_agent_and_fact(engine, owner_id)
    provider_id = _seed_text_provider(engine, world_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)

    _authenticate(client, owner_token)
    response = client.post(
        f"/worlds/{world_id}/narrative-quality/writer/generate",
        json={
            "worldline_id": str(worldline_id),
            "provider_id": str(provider_id),
            "prompt_goal": "Preview a draft.",
            "dry_run": True,
        },
    )

    assert response.status_code == 201
    assert response.json()["artifact"] is None
    with Session(engine) as session:
        assert session.scalar(select(func.count(NarrativeArtifact.id))) == 0
        assert session.scalar(select(func.count(ModelInvocation.id))) == 1


def test_narrative_quality_writer_v2_api_requires_world_admin() -> None:
    client, engine = _client_with_database()
    owner_id, _owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id, worldline_id, _agent_id = _seed_world_agent_and_fact(engine, owner_id)
    provider_id = _seed_text_provider(engine, world_id)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)

    _authenticate(client, member_token)
    response = client.post(
        f"/worlds/{world_id}/narrative-quality/writer/generate",
        json={
            "worldline_id": str(worldline_id),
            "provider_id": str(provider_id),
            "prompt_goal": "Should be forbidden.",
        },
    )

    assert response.status_code == 403
    with Session(engine) as session:
        assert session.scalar(select(func.count(NarrativeArtifact.id))) == 0
        assert session.scalar(select(func.count(ModelInvocation.id))) == 0


def test_narrative_quality_continuity_review_api_reviews_artifact() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id, worldline_id, _agent_id = _seed_world_agent_and_fact(engine, owner_id)
    artifact_id = _seed_narrative_artifact(
        engine,
        world_id,
        worldline_id,
        content="Everyone knows a time paradox happened on this route.",
    )
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)

    _authenticate(client, owner_token)
    response = client.post(
        f"/worlds/{world_id}/narrative-quality/continuity/review",
        json={
            "worldline_id": str(worldline_id),
            "artifact_id": str(artifact_id),
            "source_kind": "artifact",
            "source_ref": str(artifact_id),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["worldline_id"] == str(worldline_id)
    assert body["artifact_id"] == str(artifact_id)
    assert body["review_status"] == "warning"
    assert any(finding["code"] == "knowledge_leak_risk" for finding in body["findings"])
    assert any(report["code"] == "route_context_missing" for report in body["conflict_reports"])
    assert "storage_uri" not in response.text
    assert "raw_prompt" not in response.text
    with Session(engine) as session:
        assert session.scalar(select(func.count(NarrativeContinuityReview.id))) == 1
        assert session.scalar(select(func.count(WorldEventModel.id))) == 0


def test_narrative_quality_continuity_review_api_requires_world_admin() -> None:
    client, engine = _client_with_database()
    owner_id, _owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id, worldline_id, _agent_id = _seed_world_agent_and_fact(engine, owner_id)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)

    _authenticate(client, member_token)
    response = client.post(
        f"/worlds/{world_id}/narrative-quality/continuity/review",
        json={
            "worldline_id": str(worldline_id),
            "source_kind": "manual",
            "reviewed_text": "Safe text.",
        },
    )

    assert response.status_code == 403
    with Session(engine) as session:
        assert session.scalar(select(func.count(NarrativeContinuityReview.id))) == 0


def test_narrative_quality_continuity_review_api_rejects_sensitive_metadata() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id, worldline_id, _agent_id = _seed_world_agent_and_fact(engine, owner_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)

    _authenticate(client, owner_token)
    response = client.post(
        f"/worlds/{world_id}/narrative-quality/continuity/review",
        json={
            "worldline_id": str(worldline_id),
            "source_kind": "manual",
            "reviewed_text": "Safe text.",
            "metadata": {"nested": {"api_key": "sk-secret"}},
        },
    )

    assert response.status_code == 422
    assert "api_key" in response.text
    with Session(engine) as session:
        assert session.scalar(select(func.count(NarrativeContinuityReview.id))) == 0


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
        cast(Table, MediaAsset.__table__),
        cast(Table, ModelInvocation.__table__),
        cast(Table, PromptTemplate.__table__),
        cast(Table, PromptSnapshot.__table__),
        cast(Table, AgentRuntimeRunModelInvocation.__table__),
        cast(Table, ModelInvocationTag.__table__),
        cast(Table, ConversationSession.__table__),
        cast(Table, ConversationParticipant.__table__),
        cast(Table, ConversationTurn.__table__),
        cast(Table, NarrativeArtifact.__table__),
        cast(Table, VoiceProfile.__table__),
        cast(Table, AgentVoiceProfileBinding.__table__),
        cast(Table, SpeechStyleMapping.__table__),
        cast(Table, CharacterSpriteSet.__table__),
        cast(Table, CharacterSpriteVariant.__table__),
        cast(Table, ConversationTurnPresentation.__table__),
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


def _seed_narrative_artifact(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    *,
    content: str,
) -> uuid.UUID:
    artifact_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            NarrativeArtifact(
                id=artifact_id,
                world_id=world_id,
                worldline_id=worldline_id,
                title="Fixture artifact",
                content=content,
                artifact_kind="chapter_draft",
                artifact_metadata={"worldline_id": str(worldline_id)},
            )
        )
        session.commit()
        return artifact_id


def _seed_aligned_presentation(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    agent_id: uuid.UUID,
    conversation_id: uuid.UUID,
    turn_id: uuid.UUID,
) -> None:
    sprite_set_id = uuid.uuid4()
    sprite_variant_id = uuid.uuid4()
    voice_profile_id = uuid.uuid4()
    sprite_asset_id = uuid.uuid4()
    voice_asset_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            MediaAsset(
                id=sprite_asset_id,
                world_id=world_id,
                worldline_id=worldline_id,
                asset_kind="image",
                asset_role="character_sprite",
                source_kind="test_fixture",
                status="available",
                visibility="world_admin",
                created_by_actor_ref="test",
                metadata_json={},
            )
        )
        session.add(
            MediaAsset(
                id=voice_asset_id,
                world_id=world_id,
                worldline_id=worldline_id,
                asset_kind="audio",
                asset_role="voice_sample",
                source_kind="test_fixture",
                status="available",
                visibility="world_admin",
                created_by_actor_ref="test",
                metadata_json={},
            )
        )
        session.add(
            CharacterSpriteSet(
                id=sprite_set_id,
                world_id=world_id,
                worldline_id=worldline_id,
                agent_id=agent_id,
                style_key="default",
                display_name="Default",
                default_variant_id=sprite_variant_id,
                status="active",
                visibility="world_admin",
                metadata_json={},
            )
        )
        session.add(
            CharacterSpriteVariant(
                id=sprite_variant_id,
                world_id=world_id,
                worldline_id=worldline_id,
                sprite_set_id=sprite_set_id,
                asset_id=sprite_asset_id,
                expression_key="happy",
                mood_tags_json=["happy"],
                priority=0,
                is_default=True,
                status="active",
                visibility="world_admin",
                metadata_json={},
            )
        )
        session.add(
            VoiceProfile(
                id=voice_profile_id,
                world_id=world_id,
                worldline_id=worldline_id,
                profile_key="alice",
                display_name="Alice",
                status="active",
                visibility="world_admin",
                owner_kind="agent",
                owner_agent_id=agent_id,
                default_language="en",
                supported_languages_json=["en"],
                voice_kind="preset",
                reference_asset_id=voice_asset_id,
                consent_status="not_required",
                usage_policy_json={},
                metadata_json={},
            )
        )
        session.add(
            AgentVoiceProfileBinding(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                agent_id=agent_id,
                voice_profile_id=voice_profile_id,
                binding_role="default",
                priority=0,
                is_default=True,
                style_overrides_json={},
            )
        )
        session.add(
            SpeechStyleMapping(
                id=uuid.uuid4(),
                world_id=world_id,
                mapping_key="tts-happy",
                provider_kind="text_to_speech",
                emotion_key="happy",
                style_json={"style": "bright"},
            )
        )
        session.add(
            ConversationTurnPresentation(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                conversation_id=conversation_id,
                turn_id=turn_id,
                speaker_agent_id=agent_id,
                emotion_key="happy",
                emotion_intensity=1.0,
                sprite_set_id=sprite_set_id,
                sprite_variant_id=sprite_variant_id,
                voice_profile_id=voice_profile_id,
                presentation_json={"safe": True},
                render_state="speech_rendered",
            )
        )
        session.commit()
