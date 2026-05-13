from __future__ import annotations

import hashlib
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
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
from noveland.media.storage import LocalMediaObjectStorage
from noveland.memory.models import MemoryBackendProfile, MemoryWriteJob
from noveland.narrative.models import NarrativeArtifact
from noveland.providers.models import ProviderCapability, ProviderHealthCheck, ProviderIntegration
from noveland.services.api.app import create_app
from noveland.services.api.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from noveland.services.api.dependencies import get_db_session
from noveland.services.api.multimodal_evals import _eval_storage
from noveland.services.api.providers import _media_storage
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
from noveland.worlds.models import LongRunEvalRun, Scene, World, Worldline, WorldMembership
from sqlalchemy import Table, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

_NAMESPACE = uuid.UUID("7b69bb06-34e4-4af7-bad8-d82151f3e30b")
_NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
_SESSION_EXPIRES_AT = datetime(2099, 1, 1, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class MultimodalSampleWorld:
    engine: Engine
    storage: LocalMediaObjectStorage
    admin_token: str
    member_token: str
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    admin_user_id: uuid.UUID
    member_user_id: uuid.UUID
    agent_ids: tuple[uuid.UUID, uuid.UUID]
    scene_id: uuid.UUID
    conversation_id: uuid.UUID
    turn_id: uuid.UUID
    provider_ids: dict[str, uuid.UUID]
    media_job_ids: dict[str, uuid.UUID]
    invocation_ids: dict[str, uuid.UUID]
    prompt_snapshot_ids: dict[str, uuid.UUID]
    asset_ids: dict[str, uuid.UUID]
    object_ids: dict[str, uuid.UUID]
    sprite_set_id: uuid.UUID
    sprite_variant_ids: dict[str, uuid.UUID]
    background_profile_id: uuid.UUID
    voice_profile_id: uuid.UUID
    transcript_id: uuid.UUID
    presentation_id: uuid.UUID
    asset_generation_policy_id: uuid.UUID
    asset_generation_preview_run_id: uuid.UUID
    asset_generation_apply_run_id: uuid.UUID
    asset_generation_proposal_id: uuid.UUID
    long_run_eval_id: uuid.UUID


def create_multimodal_sample_world(tmp_path: Path) -> MultimodalSampleWorld:
    engine = _engine()
    storage = LocalMediaObjectStorage(tmp_path / "media")
    graph = _ids()

    with Session(engine) as session:
        _seed_users(session, graph)
        _seed_world(session, graph)
        _seed_story(session, graph)
        _seed_providers(session, graph)
        _seed_jobs_invocations_and_assets(session, storage, graph)
        _seed_visual_speech_and_presentation(session, graph)
        _seed_asset_generation(session, graph)
        _seed_eval_and_safe_event(session, graph)
        session.commit()

    return MultimodalSampleWorld(
        engine=engine,
        storage=storage,
        admin_token="phase13-admin-token",
        member_token="phase13-member-token",
        world_id=graph["world"],
        worldline_id=graph["worldline"],
        admin_user_id=graph["admin_user"],
        member_user_id=graph["member_user"],
        agent_ids=(graph["agent_a"], graph["agent_b"]),
        scene_id=graph["scene"],
        conversation_id=graph["conversation"],
        turn_id=graph["turn"],
        provider_ids={
            "image": graph["provider_image"],
            "tts": graph["provider_tts"],
            "stt": graph["provider_stt"],
        },
        media_job_ids={
            "tts": graph["job_tts"],
            "stt": graph["job_stt"],
            "composition": graph["job_composition"],
            "asset_generation": graph["job_asset_generation"],
        },
        invocation_ids={"tts": graph["invocation_tts"], "stt": graph["invocation_stt"]},
        prompt_snapshot_ids={"tts": graph["snapshot_tts"], "stt": graph["snapshot_stt"]},
        asset_ids={
            "background": graph["asset_background"],
            "sprite_neutral": graph["asset_sprite_neutral"],
            "sprite_happy": graph["asset_sprite_happy"],
            "sprite_sad": graph["asset_sprite_sad"],
            "tts_audio": graph["asset_tts_audio"],
            "stt_audio": graph["asset_stt_audio"],
            "composite": graph["asset_composite"],
        },
        object_ids={
            "background": graph["object_background"],
            "sprite_neutral": graph["object_sprite_neutral"],
            "sprite_happy": graph["object_sprite_happy"],
            "sprite_sad": graph["object_sprite_sad"],
            "tts_audio": graph["object_tts_audio"],
            "stt_audio": graph["object_stt_audio"],
            "composite": graph["object_composite"],
        },
        sprite_set_id=graph["sprite_set"],
        sprite_variant_ids={
            "neutral": graph["variant_neutral"],
            "happy": graph["variant_happy"],
            "sad": graph["variant_sad"],
        },
        background_profile_id=graph["background_profile"],
        voice_profile_id=graph["voice_profile"],
        transcript_id=graph["transcript"],
        presentation_id=graph["presentation"],
        asset_generation_policy_id=graph["asset_generation_policy"],
        asset_generation_preview_run_id=graph["asset_generation_preview_run"],
        asset_generation_apply_run_id=graph["asset_generation_apply_run"],
        asset_generation_proposal_id=graph["asset_generation_proposal"],
        long_run_eval_id=graph["long_run_eval"],
    )


def create_sample_world_client(sample: MultimodalSampleWorld) -> TestClient:
    app = create_app()

    def override_get_db_session() -> Iterator[Session]:
        with Session(sample.engine) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[_media_storage] = lambda: sample.storage
    app.dependency_overrides[_eval_storage] = lambda: sample.storage
    return TestClient(app)


def authenticate(client: TestClient, token: str) -> None:
    client.cookies.clear()
    client.headers.clear()
    client.cookies.set(SESSION_COOKIE_NAME, token)
    client.cookies.set(CSRF_COOKIE_NAME, "csrf-token")
    client.headers.update({CSRF_HEADER_NAME: "csrf-token"})


def _engine() -> Engine:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    _create_tables(engine)
    return engine


def _create_tables(engine: Engine) -> None:
    for table in (
        cast(Table, User.__table__),
        cast(Table, AuthSession.__table__),
        cast(Table, PlatformRoleAssignment.__table__),
        cast(Table, MemoryBackendProfile.__table__),
        cast(Table, World.__table__),
        cast(Table, Worldline.__table__),
        cast(Table, WorldMembership.__table__),
        cast(Table, Agent.__table__),
        cast(Table, Scene.__table__),
        cast(Table, ConversationSession.__table__),
        cast(Table, ConversationTurn.__table__),
        cast(Table, ConversationTurnPresentation.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, MemoryWriteJob.__table__),
        cast(Table, ProviderIntegration.__table__),
        cast(Table, ProviderCapability.__table__),
        cast(Table, ProviderHealthCheck.__table__),
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
        cast(Table, LongRunEvalRun.__table__),
    ):
        table.create(engine)


def _ids() -> dict[str, uuid.UUID]:
    names = (
        "admin_user",
        "member_user",
        "world",
        "worldline",
        "agent_a",
        "agent_b",
        "scene",
        "conversation",
        "turn",
        "provider_image",
        "provider_tts",
        "provider_stt",
        "job_tts",
        "job_stt",
        "job_composition",
        "job_asset_generation",
        "invocation_tts",
        "invocation_stt",
        "snapshot_tts",
        "snapshot_stt",
        "asset_background",
        "asset_sprite_neutral",
        "asset_sprite_happy",
        "asset_sprite_sad",
        "asset_tts_audio",
        "asset_stt_audio",
        "asset_composite",
        "object_background",
        "object_sprite_neutral",
        "object_sprite_happy",
        "object_sprite_sad",
        "object_tts_audio",
        "object_stt_audio",
        "object_composite",
        "sprite_set",
        "variant_neutral",
        "variant_happy",
        "variant_sad",
        "background_profile",
        "voice_profile",
        "voice_binding_a",
        "voice_binding_b",
        "transcript",
        "presentation",
        "asset_generation_policy",
        "asset_generation_preview_run",
        "asset_generation_apply_run",
        "asset_generation_proposal",
        "long_run_eval",
        "event",
    )
    return {name: uuid.uuid5(_NAMESPACE, name) for name in names}


def _seed_users(session: Session, graph: dict[str, uuid.UUID]) -> None:
    for key, token, email in (
        ("admin_user", "phase13-admin-token", "phase13-admin@example.test"),
        ("member_user", "phase13-member-token", "phase13-member@example.test"),
    ):
        user_id = graph[key]
        session.add(User(id=user_id, email=email, display_name=email, is_active=True))
        session.add(
            AuthSession(
                id=uuid.uuid5(_NAMESPACE, f"session:{key}"),
                user_id=user_id,
                token_hash=hash_session_token(token),
                status=AuthSessionStatus.ACTIVE.value,
                expires_at=_SESSION_EXPIRES_AT,
            )
        )


def _seed_world(session: Session, graph: dict[str, uuid.UUID]) -> None:
    session.add(
        World(
            id=graph["world"],
            owner_user_id=graph["admin_user"],
            slug="phase13-sample-world",
            name="Phase 13 Sample World",
            is_active=True,
        )
    )
    session.add(
        Worldline(
            id=graph["worldline"],
            world_id=graph["world"],
            worldline_key="primary",
            name="Primary Worldline",
            parent_worldline_id=None,
            status="active",
            created_by_actor_ref="test:phase13",
            metadata_json={"primary": True},
        )
    )
    for user_key, role in (
        ("admin_user", AuthRole.WORLD_ADMIN),
        ("member_user", AuthRole.HUMAN_USER),
    ):
        session.add(
            WorldMembership(
                id=uuid.uuid5(_NAMESPACE, f"membership:{user_key}"),
                world_id=graph["world"],
                user_id=graph[user_key],
                role=role.value,
            )
        )
    session.flush()


def _seed_story(session: Session, graph: dict[str, uuid.UUID]) -> None:
    session.add(
        Scene(
            id=graph["scene"],
            world_id=graph["world"],
            scene_key="classroom",
            name="Classroom",
            location_tags=["school", "day"],
        )
    )
    session.add_all(
        [
            Agent(
                id=graph["agent_a"],
                world_id=graph["world"],
                home_scene_id=graph["scene"],
                agent_key="alice",
                display_name="Alice",
                kind="role_agent",
                importance="lead",
                is_enabled=True,
            ),
            Agent(
                id=graph["agent_b"],
                world_id=graph["world"],
                home_scene_id=graph["scene"],
                agent_key="bob",
                display_name="Bob",
                kind="role_agent",
                importance="major",
                is_enabled=True,
            ),
        ]
    )
    session.add(
        ConversationSession(
            id=graph["conversation"],
            world_id=graph["world"],
            worldline_id=graph["worldline"],
            scene_id=graph["scene"],
            session_key="phase13-session",
            title="Phase 13 Session",
            scope_type="scene",
            mode="manual_chain",
            status="running",
            objective="Regression fixture",
            opening_prompt="",
            max_turns=4,
            next_turn_index=1,
            policy_config={},
            writer_config={},
            memory_config={},
        )
    )
    session.add(
        ConversationTurn(
            id=graph["turn"],
            session_id=graph["conversation"],
            turn_index=0,
            speaker_kind="agent",
            speaker_agent_id=graph["agent_a"],
            input_text="Hello.",
            output_text="Welcome to the classroom.",
            status="succeeded",
        )
    )
    session.flush()


def _seed_providers(session: Session, graph: dict[str, uuid.UUID]) -> None:
    providers = (
        (
            "provider_image",
            "image_generation",
            "fake-image",
            "Fake Image",
            "supports_image_generation",
        ),
        ("provider_tts", "text_to_speech", "fake-tts", "Fake TTS", "supports_tts"),
        ("provider_stt", "speech_to_text", "fake-stt", "Fake STT", "supports_stt"),
    )
    for key, provider_kind, provider_key, display_name, capability_key in providers:
        provider_id = graph[key]
        session.add(
            ProviderIntegration(
                id=provider_id,
                world_id=graph["world"],
                scope_kind="world",
                scope_key=f"world:{graph['world']}",
                provider_kind=provider_kind,
                adapter_kind="fake",
                provider_key=provider_key,
                display_name=display_name,
                auth_ref="env:OPENAI_API_KEY" if provider_kind == "image_generation" else None,
                config_json={},
                default_params_json={},
                status="active",
                visibility="world_admin",
            )
        )
        session.add(
            ProviderCapability(
                id=uuid.uuid5(_NAMESPACE, f"capability:{key}"),
                provider_integration_id=provider_id,
                capability_key=capability_key,
                capability_json={"fixture": True},
            )
        )
        session.add(
            ProviderHealthCheck(
                id=uuid.uuid5(_NAMESPACE, f"health:{key}"),
                provider_integration_id=provider_id,
                status="healthy",
                latency_ms=1,
                checked_at=_NOW,
                metadata_json={"auth_ref_present": provider_kind == "image_generation"},
            )
        )
    session.flush()


def _seed_jobs_invocations_and_assets(
    session: Session,
    storage: LocalMediaObjectStorage,
    graph: dict[str, uuid.UUID],
) -> None:
    _add_media_job(
        session,
        graph,
        "job_tts",
        "speech_generation",
        "succeeded",
        request_json={"action": "generate_speech_audio", "turn_id": str(graph["turn"])},
    )
    _add_media_job(
        session,
        graph,
        "job_stt",
        "speech_transcription",
        "succeeded",
        request_json={"action": "transcribe_audio", "turn_id": str(graph["turn"])},
    )
    _add_media_job(
        session,
        graph,
        "job_composition",
        "composition",
        "succeeded",
        request_json={"action": "compose_scene", "turn_id": str(graph["turn"])},
    )
    session.flush()
    _add_invocation(
        session,
        graph,
        invocation_key="invocation_tts",
        snapshot_key="snapshot_tts",
        job_key="job_tts",
        invocation_kind="text_to_speech",
        cost=Decimal("0.02"),
    )
    _add_invocation(
        session,
        graph,
        invocation_key="invocation_stt",
        snapshot_key="snapshot_stt",
        job_key="job_stt",
        invocation_kind="speech_to_text",
        cost=Decimal("0.01"),
    )
    session.flush()

    _add_asset_object(
        session,
        storage,
        graph,
        asset_key="asset_background",
        object_key="object_background",
        asset_role="scene_background",
        asset_kind="image",
        mime_type="image/png",
        data=b"phase13-background",
    )
    for expression in ("neutral", "happy", "sad"):
        _add_asset_object(
            session,
            storage,
            graph,
            asset_key=f"asset_sprite_{expression}",
            object_key=f"object_sprite_{expression}",
            asset_role="character_sprite",
            asset_kind="image",
            mime_type="image/png",
            data=f"phase13-sprite-{expression}".encode(),
        )
    _add_asset_object(
        session,
        storage,
        graph,
        asset_key="asset_tts_audio",
        object_key="object_tts_audio",
        asset_role="speech_audio",
        asset_kind="audio",
        mime_type="audio/wav",
        data=b"phase13-tts-audio",
        source_kind="provider_generated",
        source_job_key="job_tts",
        source_invocation_key="invocation_tts",
    )
    _add_asset_object(
        session,
        storage,
        graph,
        asset_key="asset_stt_audio",
        object_key="object_stt_audio",
        asset_role="transcript_audio",
        asset_kind="audio",
        mime_type="audio/wav",
        data=b"phase13-stt-source",
    )
    _add_asset_object(
        session,
        storage,
        graph,
        asset_key="asset_composite",
        object_key="object_composite",
        asset_role="composite_image",
        asset_kind="image",
        mime_type="image/png",
        data=b"phase13-composite",
        source_kind="composed",
        source_job_key="job_composition",
    )
    session.flush()

    tts_invocation = session.get(ModelInvocation, graph["invocation_tts"])
    if tts_invocation is not None:
        tts_invocation.media_asset_id = graph["asset_tts_audio"]
    _add_composite_inputs(session, graph)
    _add_turn_references(session, graph)
    session.flush()


def _seed_visual_speech_and_presentation(
    session: Session,
    graph: dict[str, uuid.UUID],
) -> None:
    session.add(
        CharacterSpriteSet(
            id=graph["sprite_set"],
            world_id=graph["world"],
            worldline_id=graph["worldline"],
            agent_id=graph["agent_a"],
            style_key="default",
            display_name="Default",
            default_variant_id=graph["variant_neutral"],
            status="active",
            visibility="world_admin",
            metadata_json={"fixture": True},
        )
    )
    for expression, priority in (("neutral", 0), ("happy", 10), ("sad", 20)):
        session.add(
            CharacterSpriteVariant(
                id=graph[f"variant_{expression}"],
                world_id=graph["world"],
                worldline_id=graph["worldline"],
                sprite_set_id=graph["sprite_set"],
                asset_id=graph[f"asset_sprite_{expression}"],
                expression_key=expression,
                priority=priority,
                is_default=expression == "neutral",
                status="active",
                visibility="world_admin",
                mood_tags_json=[expression],
                metadata_json={},
            )
        )
    session.add(
        SceneBackgroundProfile(
            id=graph["background_profile"],
            world_id=graph["world"],
            worldline_id=graph["worldline"],
            scene_id=graph["scene"],
            location_key="classroom",
            asset_id=graph["asset_background"],
            priority=0,
            is_default=True,
            status="active",
            visibility="world_admin",
            metadata_json={"fixture": True},
        )
    )
    session.add(
        VoiceProfile(
            id=graph["voice_profile"],
            world_id=graph["world"],
            worldline_id=graph["worldline"],
            profile_key="alice-default",
            display_name="Alice Default Voice",
            status="active",
            visibility="world_admin",
            owner_kind="agent",
            owner_agent_id=graph["agent_a"],
            provider_integration_id=graph["provider_tts"],
            default_language="en",
            supported_languages_json=["en"],
            voice_kind="preset",
            reference_asset_id=graph["asset_stt_audio"],
            consent_status="not_required",
            usage_policy_json={},
            metadata_json={"fixture": True},
        )
    )
    for agent_key, binding_key in (
        ("agent_a", "voice_binding_a"),
        ("agent_b", "voice_binding_b"),
    ):
        session.add(
            AgentVoiceProfileBinding(
                id=graph[binding_key],
                world_id=graph["world"],
                worldline_id=graph["worldline"],
                agent_id=graph[agent_key],
                voice_profile_id=graph["voice_profile"],
                binding_role="default",
                priority=0,
                is_default=True,
                style_overrides_json={},
            )
        )
    session.add(
        SpeechTranscript(
            id=graph["transcript"],
            world_id=graph["world"],
            worldline_id=graph["worldline"],
            source_asset_id=graph["asset_stt_audio"],
            media_job_id=graph["job_stt"],
            model_invocation_id=graph["invocation_stt"],
            conversation_id=graph["conversation"],
            turn_id=graph["turn"],
            speaker_actor_ref="agent:alice",
            language="en",
            transcript_text="Welcome to the classroom.",
            status="available",
            visibility="world_admin",
        )
    )
    session.add(
        ConversationTurnPresentation(
            id=graph["presentation"],
            world_id=graph["world"],
            worldline_id=graph["worldline"],
            conversation_id=graph["conversation"],
            turn_id=graph["turn"],
            speaker_agent_id=graph["agent_a"],
            emotion_key="happy",
            emotion_intensity=1.0,
            sprite_set_id=graph["sprite_set"],
            sprite_variant_id=graph["variant_happy"],
            voice_profile_id=graph["voice_profile"],
            tts_media_asset_id=graph["asset_tts_audio"],
            background_asset_id=graph["asset_background"],
            composite_scene_asset_id=graph["asset_composite"],
            transcript_id=graph["transcript"],
            presentation_json={"fixture": True, "style": "default"},
            render_state="speech_rendered",
        )
    )
    session.flush()


def _seed_asset_generation(session: Session, graph: dict[str, uuid.UUID]) -> None:
    session.add(
        AssetGenerationPolicy(
            id=graph["asset_generation_policy"],
            world_id=graph["world"],
            worldline_id=graph["worldline"],
            policy_key="default",
            status="active",
            budget_json={"max_total_estimated_cost": 1.0},
            lookahead_json={"max_proposals": 4},
            provider_preferences_json={"image_generation": str(graph["provider_image"])},
            rules_json={"admin_apply_only": True},
        )
    )
    session.add(
        AssetGenerationRun(
            id=graph["asset_generation_preview_run"],
            world_id=graph["world"],
            worldline_id=graph["worldline"],
            policy_id=graph["asset_generation_policy"],
            run_kind="preview",
            status="succeeded",
            summary_json={"proposal_count": 1, "media_job_count": 0},
            created_by_actor_ref="user:phase13-admin",
        )
    )
    _add_media_job(
        session,
        graph,
        "job_asset_generation",
        "composition",
        "queued",
        request_json={
            "action": "compose_scene",
            "turn_id": str(graph["turn"]),
            "asset_generation_proposal_id": str(graph["asset_generation_proposal"]),
        },
        provider_kind=None,
        priority=0,
        cancel_policy="cancel_superseded",
        invalidation_key=f"turn:{graph['turn']}:compose_scene",
    )
    session.add(
        AssetGenerationProposal(
            id=graph["asset_generation_proposal"],
            world_id=graph["world"],
            worldline_id=graph["worldline"],
            run_id=graph["asset_generation_preview_run"],
            proposal_kind="composite_scene",
            target_ref_kind="conversation_turn",
            target_ref_id=graph["turn"],
            reason="fixture admin-applied composite scene proposal",
            evidence_json={"turn_id": str(graph["turn"]), "missing": "composite_scene"},
            priority=0,
            estimated_cost=0.0,
            provider_kind=None,
            provider_id=None,
            request_json={"action": "compose_scene", "turn_id": str(graph["turn"])},
            status="applied",
            resulting_media_job_id=graph["job_asset_generation"],
        )
    )
    session.add(
        AssetGenerationRun(
            id=graph["asset_generation_apply_run"],
            world_id=graph["world"],
            worldline_id=graph["worldline"],
            policy_id=graph["asset_generation_policy"],
            run_kind="apply",
            status="succeeded",
            summary_json={
                "source_run_id": str(graph["asset_generation_preview_run"]),
                "applied_count": 1,
                "media_job_count": 1,
            },
            created_by_actor_ref="user:phase13-admin",
        )
    )
    session.flush()


def _seed_eval_and_safe_event(session: Session, graph: dict[str, uuid.UUID]) -> None:
    session.add(
        LongRunEvalRun(
            id=graph["long_run_eval"],
            world_id=graph["world"],
            worldline_id=graph["worldline"],
            eval_key="multimodal-smoke",
            horizon_days=7,
            status="completed",
            started_at=_NOW,
            finished_at=_NOW,
            metrics={"fixture": True},
            recommendations=[],
            blockers=[],
            metadata_json={"phase": 13},
        )
    )
    session.add(
        WorldEventModel(
            id=graph["event"],
            world_id=graph["world"],
            worldline_id=graph["worldline"],
            sequence=1,
            event_name="fixture.sample_world",
            importance="system",
            payload={"kind": "phase13_fixture", "turn_id": str(graph["turn"])},
            wall_time=_NOW,
            actor_ref="test:phase13",
        )
    )
    session.flush()


def _add_media_job(
    session: Session,
    graph: dict[str, uuid.UUID],
    job_key: str,
    job_kind: str,
    status: str,
    *,
    request_json: dict[str, str],
    provider_kind: str | None = "local_stub",
    priority: int = 10,
    cancel_policy: str | None = None,
    invalidation_key: str | None = None,
) -> None:
    session.add(
        MediaJob(
            id=graph[job_key],
            world_id=graph["world"],
            worldline_id=graph["worldline"],
            conversation_id=graph["conversation"],
            turn_id=graph["turn"],
            agent_id=graph["agent_a"],
            job_kind=job_kind,
            provider_kind=provider_kind,
            status=status,
            priority=priority,
            cancel_policy=cancel_policy,
            dedupe_key=invalidation_key,
            invalidation_key=invalidation_key,
            provider_config_json={},
            request_json=request_json,
            result_json={},
            created_by_actor_ref="test:phase13",
        )
    )


def _add_invocation(
    session: Session,
    graph: dict[str, uuid.UUID],
    *,
    invocation_key: str,
    snapshot_key: str,
    job_key: str,
    invocation_kind: str,
    cost: Decimal,
) -> None:
    session.add(
        ModelInvocation(
            id=graph[invocation_key],
            world_id=graph["world"],
            worldline_id=graph["worldline"],
            trace_id=uuid.uuid5(_NAMESPACE, f"trace:{invocation_key}"),
            invocation_kind=invocation_kind,
            actor_kind="service",
            actor_ref="test:phase13",
            agent_id=graph["agent_a"],
            conversation_id=graph["conversation"],
            turn_id=graph["turn"],
            media_job_id=graph[job_key],
            provider_kind="local_stub",
            model_name="fake",
            input_text=None,
            output_text=None,
            input_json={"turn_id": str(graph["turn"])},
            output_json={"status": "ok"},
            request_params_json={"auth_ref_present": False, "auth_resolved": False},
            response_metadata_json={"provider": "fake"},
            usage_json={"fixture": True},
            latency_ms=12,
            estimated_cost=cost,
            status="succeeded",
            visibility="world_admin",
            redaction_status="redacted",
            retention_policy="eval_only",
        )
    )
    session.add(
        PromptSnapshot(
            id=graph[snapshot_key],
            invocation_id=graph[invocation_key],
            raw_prompt_text=None,
            raw_messages_json=None,
            raw_request_json={
                "headers": {"authorization": "[REDACTED]"},
                "input_ref": f"conversation_turn:{graph['turn']}",
            },
            raw_response_json={"status": "ok"},
            raw_output_text=None,
            normalized_output_json={"status": "ok"},
            prompt_checksum_sha256=hashlib.sha256(invocation_kind.encode()).hexdigest(),
            visibility="world_admin",
            redaction_status="redacted",
        )
    )


def _add_asset_object(
    session: Session,
    storage: LocalMediaObjectStorage,
    graph: dict[str, uuid.UUID],
    *,
    asset_key: str,
    object_key: str,
    asset_role: str,
    asset_kind: str,
    mime_type: str,
    data: bytes,
    source_kind: str = "test_fixture",
    source_job_key: str | None = None,
    source_invocation_key: str | None = None,
) -> None:
    asset_id = graph[asset_key]
    stored = storage.write_bytes(
        f"worlds/{graph['world']}/worldlines/{graph['worldline']}/assets/{asset_id}/original.bin",
        data,
        content_type=mime_type,
    )
    session.add(
        MediaAsset(
            id=asset_id,
            world_id=graph["world"],
            worldline_id=graph["worldline"],
            asset_kind=asset_kind,
            asset_role=asset_role,
            source_kind=source_kind,
            status="available",
            visibility="world_admin",
            storage_uri=stored.uri,
            mime_type=mime_type,
            size_bytes=stored.size_bytes,
            checksum_sha256=stored.checksum_sha256,
            source_job_id=None if source_job_key is None else graph[source_job_key],
            source_invocation_id=(
                None if source_invocation_key is None else graph[source_invocation_key]
            ),
            created_by_actor_ref="test:phase13",
            metadata_json={"fixture": True},
        )
    )
    session.add(
        MediaObject(
            id=graph[object_key],
            asset_id=asset_id,
            world_id=graph["world"],
            worldline_id=graph["worldline"],
            object_role="original",
            storage_uri=stored.uri,
            filename=f"{asset_key}.bin",
            mime_type=mime_type,
            size_bytes=stored.size_bytes,
            checksum_sha256=stored.checksum_sha256,
            metadata_json={"fixture": True},
        )
    )


def _add_composite_inputs(session: Session, graph: dict[str, uuid.UUID]) -> None:
    for index, (asset_key, role) in enumerate(
        (
            ("asset_background", "background"),
            ("asset_sprite_happy", "layer"),
        )
    ):
        session.add(
            MediaAssetInput(
                id=uuid.uuid5(_NAMESPACE, f"input:{asset_key}"),
                world_id=graph["world"],
                worldline_id=graph["worldline"],
                output_asset_id=graph["asset_composite"],
                input_asset_id=graph[asset_key],
                source_job_id=graph["job_composition"],
                input_role=role,
                display_order=index,
                metadata_json={},
            )
        )


def _add_turn_references(session: Session, graph: dict[str, uuid.UUID]) -> None:
    references = (
        ("asset_background", "background", 0),
        ("asset_sprite_happy", "character_sprite", 1),
        ("asset_composite", "output", 2),
        ("asset_tts_audio", "attachment", 3),
        ("asset_stt_audio", "source", 4),
    )
    for asset_key, role, order in references:
        session.add(
            MediaReference(
                id=uuid.uuid5(_NAMESPACE, f"reference:{asset_key}:{role}"),
                world_id=graph["world"],
                worldline_id=graph["worldline"],
                asset_id=graph[asset_key],
                ref_kind="conversation_turn",
                ref_id=graph["turn"],
                ref_role=role,
                display_order=order,
                metadata_json={"conversation_id": str(graph["conversation"])},
            )
        )
