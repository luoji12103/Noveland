from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest
from noveland.agents.models import Agent
from noveland.auth.models import User
from noveland.conversations.models import ConversationSession, ConversationTurn
from noveland.events import WorldEventAppend, WorldEventStore
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
from noveland.providers.budget import ProviderBudgetService
from noveland.providers.contracts import (
    ProviderAdapterKind,
    ProviderBudgetPolicyCreate,
    ProviderExecutionRequest,
    ProviderIntegrationCreate,
    ProviderKind,
    ProviderScopeKind,
)
from noveland.providers.models import (
    ProviderBudgetPolicy,
    ProviderCapability,
    ProviderHealthCheck,
    ProviderIntegration,
)
from noveland.providers.registry import ProviderRegistryService
from noveland.providers.secrets import ProviderSecretResolver
from noveland.providers.service import ProviderExecutionError, ProviderExecutionService
from noveland.worlds.models import World, Worldline
from noveland.worlds.worldlines import ensure_primary_worldline
from sqlalchemy import Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_fake_text_execution_writes_invocation_and_snapshot() -> None:
    engine = _engine()
    world_id, worldline_id = _seed_world(engine)

    with Session(engine) as session:
        provider = _seed_provider(session, world_id, ProviderKind.TEXT_GENERATION)
        result = ProviderExecutionService(session).execute(
            ProviderExecutionRequest(
                world_id=world_id,
                worldline_id=worldline_id,
                provider_id=provider,
                input_text="hello",
                request_json={"purpose": "test"},
            )
        )
        session.commit()

    with Session(engine) as session:
        snapshot = session.scalars(
            select(PromptSnapshot).where(PromptSnapshot.invocation_id == result.invocation.id)
        ).one()
        invocation = session.get(ModelInvocation, result.invocation.id)
        assert invocation is not None
        assert invocation.status == "succeeded"
        assert invocation.provider_kind == "local_stub"
        assert result.output_text == "fake text: hello"
        assert snapshot.raw_prompt_text == "hello"
        assert snapshot.raw_response_json == {"text": "fake text: hello"}


def test_fake_image_and_speech_execution_write_media_and_links(tmp_path: Path) -> None:
    engine = _engine()
    world_id, worldline_id = _seed_world(engine)
    event_id = _seed_event(engine, world_id)
    storage = LocalMediaObjectStorage(tmp_path)

    with Session(engine) as session:
        image_provider = _seed_provider(session, world_id, ProviderKind.IMAGE_GENERATION)
        speech_provider = _seed_provider(session, world_id, ProviderKind.TEXT_TO_SPEECH)
        image = ProviderExecutionService(session, storage).execute(
            ProviderExecutionRequest(
                world_id=world_id,
                worldline_id=worldline_id,
                provider_id=image_provider,
                input_text="draw a test image",
            )
        )
        speech = ProviderExecutionService(session, storage).execute(
            ProviderExecutionRequest(
                world_id=world_id,
                worldline_id=worldline_id,
                provider_id=speech_provider,
                input_text="speak test",
            )
        )
        session.commit()

    with Session(engine) as session:
        image_invocation = session.get(ModelInvocation, image.invocation.id)
        speech_invocation = session.get(ModelInvocation, speech.invocation.id)
        assert image.media_job is not None
        assert image.output_asset is not None
        assert image.output_objects[0].mime_type == "image/png"
        assert speech.output_asset is not None
        assert speech.output_objects[0].mime_type == "audio/wav"
        assert image_invocation is not None
        assert image_invocation.media_job_id == image.media_job.id
        assert image_invocation.media_asset_id == image.output_asset.id
        assert speech_invocation is not None
        assert speech_invocation.media_asset_id == speech.output_asset.id
        asset = session.get(MediaAsset, image.output_asset.id)
        event = session.get(WorldEventModel, event_id)
        assert asset is not None
        assert event is not None
        assert asset.source_invocation_id == image.invocation.id
        assert event.payload == {"kind": "seed"}


def test_fake_stt_execution_returns_transcript_without_media(tmp_path: Path) -> None:
    engine = _engine()
    world_id, worldline_id = _seed_world(engine)

    with Session(engine) as session:
        provider = _seed_provider(session, world_id, ProviderKind.SPEECH_TO_TEXT)
        result = ProviderExecutionService(session, LocalMediaObjectStorage(tmp_path)).execute(
            ProviderExecutionRequest(
                world_id=world_id,
                worldline_id=worldline_id,
                provider_id=provider,
                request_json={"transcript": "recognized words"},
            )
        )
        session.commit()

    assert result.output_text == "recognized words"
    assert result.media_job is None
    assert result.output_asset is None


def test_missing_real_provider_secret_writes_safe_failed_invocation() -> None:
    engine = _engine()
    world_id, worldline_id = _seed_world(engine)

    with Session(engine) as session:
        provider = ProviderRegistryService(session).create_provider(
            ProviderIntegrationCreate(
                world_id=world_id,
                scope_kind=ProviderScopeKind.WORLD,
                provider_kind=ProviderKind.IMAGE_GENERATION,
                adapter_kind=ProviderAdapterKind.OPENAI,
                provider_key="openai-image",
                display_name="OpenAI Image",
                auth_ref="env:MISSING_OPENAI_API_KEY",
            )
        )
        try:
            ProviderExecutionService(session).execute(
                ProviderExecutionRequest(
                    world_id=world_id,
                    worldline_id=worldline_id,
                    provider_id=provider.id,
                    input_text="draw",
                )
            )
        except Exception as exc:
            assert "auth_missing" in str(exc)
        session.commit()

    with Session(engine) as session:
        invocation = session.scalars(select(ModelInvocation)).one()
        snapshot = session.scalars(select(PromptSnapshot)).one()
        assert invocation.status == "failed"
        assert invocation.error_text == "provider auth_missing"
        assert invocation.request_params_json is not None
        assert invocation.request_params_json["auth_ref_present"] is True
        assert invocation.request_params_json["auth_resolved"] is False
        assert invocation.request_params_json["auth_failed"] is True
        assert "MISSING_OPENAI_API_KEY" not in str(invocation.request_params_json)
        assert "MISSING_OPENAI_API_KEY" not in str(snapshot.raw_request_json)


def test_disabled_provider_writes_failed_invocation_without_resolving_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _engine()
    world_id, worldline_id = _seed_world(engine)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-disabled-provider-secret")

    with Session(engine) as session:
        provider_id = _seed_provider(session, world_id, ProviderKind.TEXT_GENERATION)
        model = session.get(ProviderIntegration, provider_id)
        assert model is not None
        model.status = "disabled"
        model.auth_ref = "env:OPENAI_API_KEY"
        with pytest.raises(ProviderExecutionError, match="disabled"):
            ProviderExecutionService(
                session,
                secret_resolver=ProviderSecretResolver(),
            ).execute(
                ProviderExecutionRequest(
                    world_id=world_id,
                    worldline_id=worldline_id,
                    provider_id=provider_id,
                    input_text="blocked",
                )
            )
        session.commit()

    with Session(engine) as session:
        invocation = session.scalars(select(ModelInvocation)).one()
        snapshot = session.scalars(select(PromptSnapshot)).one()
        assert invocation.status == "failed"
        assert invocation.error_text == "provider integration is disabled"
        assert invocation.request_params_json is not None
        assert invocation.request_params_json["provider_status"] == "disabled"
        assert invocation.request_params_json["auth_ref_present"] is True
        assert invocation.request_params_json["auth_resolved"] is False
        assert "sk-disabled-provider-secret" not in str(invocation.request_params_json)
        assert "sk-disabled-provider-secret" not in str(invocation.response_metadata_json)
        assert "sk-disabled-provider-secret" not in str(snapshot.raw_request_json)
        assert "sk-disabled-provider-secret" not in str(snapshot.raw_response_json)


def test_emergency_stop_blocks_before_secret_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _engine()
    world_id, worldline_id = _seed_world(engine)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-budget-secret")

    with Session(engine) as session:
        provider_id = _seed_provider(session, world_id, ProviderKind.TEXT_GENERATION)
        provider = session.get(ProviderIntegration, provider_id)
        assert provider is not None
        provider.auth_ref = "env:OPENAI_API_KEY"
        ProviderBudgetService(session).create_policy(
            ProviderBudgetPolicyCreate(
                world_id=world_id,
                provider_id=provider_id,
                policy_key="provider-stop",
                emergency_stop_enabled=True,
            )
        )
        with pytest.raises(ProviderExecutionError, match="emergency_stop"):
            ProviderExecutionService(
                session,
                secret_resolver=ProviderSecretResolver(),
            ).execute(
                ProviderExecutionRequest(
                    world_id=world_id,
                    worldline_id=worldline_id,
                    provider_id=provider_id,
                    input_text="blocked",
                )
            )
        session.commit()

    with Session(engine) as session:
        invocation = session.scalars(select(ModelInvocation)).one()
        snapshot = session.scalars(select(PromptSnapshot)).one()
        assert invocation.status == "failed"
        assert invocation.request_params_json is not None
        assert invocation.request_params_json["budget_checked"] is True
        assert invocation.request_params_json["budget_blocked"] is True
        assert invocation.request_params_json["auth_ref_present"] is True
        assert invocation.request_params_json["auth_resolved"] is False
        assert "sk-budget-secret" not in str(invocation.request_params_json)
        assert "sk-budget-secret" not in str(invocation.response_metadata_json)
        assert "sk-budget-secret" not in str(snapshot.raw_request_json)


def test_daily_invocation_limit_blocks_after_limit_is_reached() -> None:
    engine = _engine()
    world_id, worldline_id = _seed_world(engine)

    with Session(engine) as session:
        provider_id = _seed_provider(session, world_id, ProviderKind.TEXT_GENERATION)
        ProviderBudgetService(session).create_policy(
            ProviderBudgetPolicyCreate(
                world_id=world_id,
                provider_id=provider_id,
                policy_key="one-call",
                limits_json={"max_daily_invocations": 1},
            )
        )
        first = ProviderExecutionService(session).execute(
            ProviderExecutionRequest(
                world_id=world_id,
                worldline_id=worldline_id,
                provider_id=provider_id,
                input_text="allowed",
            )
        )
        with pytest.raises(ProviderExecutionError, match="daily_invocation_limit"):
            ProviderExecutionService(session).execute(
                ProviderExecutionRequest(
                    world_id=world_id,
                    worldline_id=worldline_id,
                    provider_id=provider_id,
                    input_text="blocked",
                )
            )
        session.commit()

    with Session(engine) as session:
        invocations = session.scalars(
            select(ModelInvocation).order_by(ModelInvocation.created_at)
        ).all()
        assert first.invocation.status == "succeeded"
        assert [item.status for item in invocations] == ["succeeded", "failed"]
        assert invocations[-1].request_params_json is not None
        assert invocations[-1].request_params_json["budget_block_reason"].endswith(
            "daily_invocation_limit"
        )


def test_resolved_secret_is_not_written_to_ledger(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    engine = _engine()
    world_id, worldline_id = _seed_world(engine)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-super-secret")

    with Session(engine) as session:
        provider = _seed_provider(session, world_id, ProviderKind.IMAGE_GENERATION)
        model = session.get(ProviderIntegration, provider)
        assert model is not None
        model.adapter_kind = ProviderAdapterKind.FAKE.value
        model.auth_ref = "env:OPENAI_API_KEY"
        result = ProviderExecutionService(
            session,
            LocalMediaObjectStorage(tmp_path),
            secret_resolver=ProviderSecretResolver(),
        ).execute(
            ProviderExecutionRequest(
                world_id=world_id,
                worldline_id=worldline_id,
                provider_id=provider,
                input_text="draw",
            )
        )
        session.commit()

    with Session(engine) as session:
        invocation = session.get(ModelInvocation, result.invocation.id)
        snapshot = session.scalars(
            select(PromptSnapshot).where(PromptSnapshot.invocation_id == result.invocation.id)
        ).one()
        assert invocation is not None
        assert "sk-super-secret" not in str(invocation.request_params_json)
        assert "sk-super-secret" not in str(invocation.response_metadata_json)
        assert "sk-super-secret" not in str(snapshot.raw_request_json)


def _engine() -> Engine:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in (
        cast(Table, User.__table__),
        cast(Table, World.__table__),
        cast(Table, Worldline.__table__),
        cast(Table, Agent.__table__),
        cast(Table, ConversationSession.__table__),
        cast(Table, ConversationTurn.__table__),
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
    ):
        table.create(engine)
    return engine


def _seed_world(engine: Engine) -> tuple[uuid.UUID, uuid.UUID]:
    user_id = uuid.uuid4()
    world_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(User(id=user_id, email=f"{user_id}@example.test", display_name="Test"))
        session.add(
            World(
                id=world_id,
                owner_user_id=user_id,
                slug=f"world-{world_id.hex[:8]}",
                name="World",
            )
        )
        session.flush()
        worldline = ensure_primary_worldline(session, world_id)
        session.commit()
        return world_id, worldline.id


def _seed_provider(session: Session, world_id: uuid.UUID, provider_kind: ProviderKind) -> uuid.UUID:
    provider = ProviderRegistryService(session).create_provider(
        ProviderIntegrationCreate(
            world_id=world_id,
            scope_kind=ProviderScopeKind.WORLD,
            provider_kind=provider_kind,
            adapter_kind=ProviderAdapterKind.FAKE,
            provider_key=f"fake-{provider_kind.value}",
            display_name=f"Fake {provider_kind.value}",
        )
    )
    return provider.id


def _seed_event(engine: Engine, world_id: uuid.UUID) -> uuid.UUID:
    with Session(engine) as session:
        event = WorldEventStore(session).append_event(
            WorldEventAppend(
                world_id=world_id,
                event_name="provider.seed_event",
                payload={"kind": "seed"},
                wall_time=datetime.now(UTC),
                actor_ref="test",
            )
        )
        session.commit()
        return event.id
