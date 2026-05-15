from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import cast

from fastapi.testclient import TestClient
from noveland.agents.models import Agent
from noveland.asset_generation.models import (
    AssetGenerationPolicy,
    AssetGenerationProposal,
    AssetGenerationRun,
)
from noveland.auth import AuthRole
from noveland.auth.contracts import AuthSessionStatus
from noveland.auth.models import AuthSession, PlatformRoleAssignment, User
from noveland.auth.services import hash_session_token
from noveland.conversations.models import (
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
from noveland.media.models import (
    MediaAsset,
    MediaAssetCollection,
    MediaAssetCollectionItem,
    MediaAssetContext,
    MediaAssetInput,
    MediaAssetTag,
    MediaJob,
    MediaObject,
    MediaReference,
)
from noveland.memory.models import MemoryBackendProfile, MemoryWriteJob
from noveland.narrative.models import NarrativeArtifact
from noveland.providers.models import (
    ProviderBudgetPolicy,
    ProviderCapability,
    ProviderHealthCheck,
    ProviderIntegration,
)
from noveland.services.api.app import create_app
from noveland.services.api.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from noveland.services.api.dependencies import get_db_session
from noveland.speech.models import (
    AgentVoiceProfileBinding,
    SpeechStyleMapping,
    SpeechTranscript,
    VoiceProfile,
)
from noveland.visual.models import (
    CharacterSpriteSet,
    CharacterSpriteVariant,
    SceneBackgroundProfile,
)
from noveland.worlds.models import Scene, World, Worldline, WorldMembership
from noveland.worlds.worldlines import ensure_primary_worldline
from sqlalchemy import Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_asset_generation_api_preview_apply_and_job_controls() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id = _seed_world(engine, owner_id)
    worldline_id = _seed_worldline(engine, world_id)
    agent_id, conversation_id, turn_id = _seed_conversation(engine, world_id, worldline_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    _seed_provider(engine, world_id, "image_generation", "supports_image_generation")
    _seed_provider(engine, world_id, "text_to_speech", "supports_tts")
    _seed_voice_profile(engine, world_id, worldline_id, agent_id)

    _authenticate(client, member_token)
    member_preview = client.post(
        f"/worlds/{world_id}/asset-generation/preview",
        json={"worldline_id": str(worldline_id), "conversation_id": str(conversation_id)},
    )

    _authenticate(client, owner_token)
    policy = client.post(
        f"/worlds/{world_id}/asset-generation/policies",
        json={
            "worldline_id": str(worldline_id),
            "policy_key": "default",
            "lookahead_json": {"max_proposals": 10},
        },
    )
    preview = client.post(
        f"/worlds/{world_id}/asset-generation/preview",
        json={
            "worldline_id": str(worldline_id),
            "policy_id": policy.json()["id"],
            "conversation_id": str(conversation_id),
            "current_turn_id": str(turn_id),
        },
    )
    proposal_id = next(
        item["id"]
        for item in preview.json()["run"]["proposals"]
        if item["status"] == "proposed"
    )
    apply = client.post(
        f"/worlds/{world_id}/asset-generation/apply",
        json={
            "worldline_id": str(worldline_id),
            "run_id": preview.json()["run"]["id"],
            "proposal_ids": [proposal_id],
        },
    )
    job_id = apply.json()["media_jobs"][0]["id"]
    reprioritize = client.post(
        f"/worlds/{world_id}/media/jobs/reprioritize",
        json={
            "worldline_id": str(worldline_id),
            "job_ids": [job_id],
            "priority": 2,
        },
    )
    cancel = client.post(
        f"/worlds/{world_id}/media/jobs/cancel-superseded",
        json={"worldline_id": str(worldline_id), "job_ids": [job_id]},
    )
    fetched_run = client.get(
        f"/worlds/{world_id}/asset-generation/runs/{preview.json()['run']['id']}",
    )
    leak_policy = client.post(
        f"/worlds/{world_id}/asset-generation/policies",
        json={
            "worldline_id": str(worldline_id),
            "policy_key": "leaky",
            "rules_json": {"storage_uri": "local://leak"},
        },
    )

    assert member_preview.status_code == 403
    assert policy.status_code == 201
    assert preview.status_code == 201
    assert apply.status_code == 201
    assert len(apply.json()["media_jobs"]) == 1
    assert reprioritize.status_code == 200
    assert reprioritize.json()["jobs"][0]["priority"] == 2
    assert cancel.status_code == 200
    assert cancel.json()["cancelled_job_ids"] == [job_id]
    assert fetched_run.status_code == 200
    assert leak_policy.status_code == 422
    assert "storage_uri" not in _json_text(preview.json())
    assert "storage_uri" not in _json_text(apply.json())

    with Session(engine) as session:
        assert len(session.scalars(select(MediaJob)).all()) == 1
        assert session.scalars(select(WorldEventModel)).all() == []


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
        cast(Table, Agent.__table__),
        cast(Table, Scene.__table__),
        cast(Table, ConversationSession.__table__),
        cast(Table, ConversationTurn.__table__),
        cast(Table, ConversationTurnPresentation.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, MemoryBackendProfile.__table__),
        cast(Table, MemoryWriteJob.__table__),
        cast(Table, ProviderIntegration.__table__),
        cast(Table, ProviderCapability.__table__),
        cast(Table, ProviderHealthCheck.__table__),
        cast(Table, ProviderBudgetPolicy.__table__),
        cast(Table, MediaJob.__table__),
        cast(Table, MediaAsset.__table__),
        cast(Table, MediaObject.__table__),
        cast(Table, MediaReference.__table__),
        cast(Table, NarrativeArtifact.__table__),
        cast(Table, MediaAssetContext.__table__),
        cast(Table, MediaAssetInput.__table__),
        cast(Table, MediaAssetTag.__table__),
        cast(Table, MediaAssetCollection.__table__),
        cast(Table, MediaAssetCollectionItem.__table__),
        cast(Table, ModelInvocation.__table__),
        cast(Table, PromptTemplate.__table__),
        cast(Table, PromptSnapshot.__table__),
        cast(Table, AgentRuntimeRunModelInvocation.__table__),
        cast(Table, ModelInvocationTag.__table__),
        cast(Table, VoiceProfile.__table__),
        cast(Table, AgentVoiceProfileBinding.__table__),
        cast(Table, SpeechTranscript.__table__),
        cast(Table, SpeechStyleMapping.__table__),
        cast(Table, CharacterSpriteSet.__table__),
        cast(Table, CharacterSpriteVariant.__table__),
        cast(Table, SceneBackgroundProfile.__table__),
        cast(Table, AssetGenerationPolicy.__table__),
        cast(Table, AssetGenerationRun.__table__),
        cast(Table, AssetGenerationProposal.__table__),
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


def _seed_world(engine: Engine, owner_user_id: uuid.UUID) -> uuid.UUID:
    world_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            World(
                id=world_id,
                owner_user_id=owner_user_id,
                slug=f"world-{world_id.hex[:8]}",
                name="World",
            )
        )
        session.commit()
    return world_id


def _seed_worldline(engine: Engine, world_id: uuid.UUID) -> uuid.UUID:
    with Session(engine) as session:
        primary = ensure_primary_worldline(session, world_id)
        session.commit()
        return primary.id


def _seed_conversation(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    agent_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    turn_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            Agent(
                id=agent_id,
                world_id=world_id,
                agent_key="agent",
                display_name="Agent",
                kind="role_agent",
            )
        )
        session.add(
            ConversationSession(
                id=conversation_id,
                world_id=world_id,
                worldline_id=worldline_id,
                session_key="session",
                title="Session",
                scope_type="world",
                mode="manual_chain",
                status="running",
                objective="",
                opening_prompt="",
                max_turns=3,
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
                speaker_agent_id=agent_id,
                input_text="hi",
                output_text="hello",
                status="succeeded",
            )
        )
        session.commit()
    return agent_id, conversation_id, turn_id


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


def _seed_provider(
    engine: Engine,
    world_id: uuid.UUID,
    provider_kind: str,
    capability_key: str,
) -> uuid.UUID:
    provider_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            ProviderIntegration(
                id=provider_id,
                world_id=world_id,
                scope_kind="world",
                scope_key=f"world:{world_id}",
                provider_kind=provider_kind,
                adapter_kind="fake",
                provider_key=f"fake-{provider_kind}",
                display_name=f"Fake {provider_kind}",
                config_json={},
                default_params_json={},
                status="active",
                visibility="world_admin",
            )
        )
        session.add(
            ProviderCapability(
                id=uuid.uuid4(),
                provider_integration_id=provider_id,
                capability_key=capability_key,
                capability_json={},
            )
        )
        session.commit()
    return provider_id


def _seed_voice_profile(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    agent_id: uuid.UUID,
) -> uuid.UUID:
    profile_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            VoiceProfile(
                id=profile_id,
                world_id=world_id,
                worldline_id=worldline_id,
                profile_key="default",
                display_name="Default Voice",
                status="active",
                visibility="world_admin",
                owner_kind="agent",
                owner_agent_id=agent_id,
                supported_languages_json=["en"],
                voice_kind="preset",
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
                voice_profile_id=profile_id,
                binding_role="default",
                priority=0,
                is_default=True,
                style_overrides_json={},
            )
        )
        session.commit()
    return profile_id


def _authenticate(client: TestClient, token: str) -> None:
    client.cookies.set(SESSION_COOKIE_NAME, token)
    client.cookies.set(CSRF_COOKIE_NAME, "csrf")
    client.headers.update({CSRF_HEADER_NAME: "csrf"})


def _json_text(value: object) -> str:
    return str(value).lower()
