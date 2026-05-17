from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import pytest
from noveland.agents.models import Agent
from noveland.auth.models import User
from noveland.conversations.models import ConversationSession, ConversationTurn
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
from noveland.providers.contracts import (
    ProviderAdapterKind,
    ProviderCapabilityCreate,
    ProviderExecutionRequest,
    ProviderIntegrationCreate,
    ProviderKind,
    ProviderModelDiscoveryRequest,
    ProviderScopeKind,
)
from noveland.providers.model_discovery import ProviderModelDiscoveryService
from noveland.providers.models import (
    ProviderBudgetPolicy,
    ProviderCapability,
    ProviderHealthCheck,
    ProviderIntegration,
)
from noveland.providers.registry import ProviderRegistryService
from noveland.providers.service import ProviderExecutionService
from noveland.providers.templates import provider_templates
from noveland.visual_generation.mapping import map_provider_request
from noveland.worlds.models import World, Worldline
from noveland.worlds.worldlines import ensure_primary_worldline
from sqlalchemy import Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

RUN_REAL_PROVIDER_TESTS = os.getenv("NOVELAND_RUN_REAL_PROVIDER_TESTS") == "1"


@dataclass(frozen=True, slots=True)
class ProviderLabPreset:
    template_key: str
    provider_kind: ProviderKind
    adapter_kind: ProviderAdapterKind
    capability_key: str


LAB_PRESETS = (
    ProviderLabPreset(
        "openai-compatible-llm",
        ProviderKind.TEXT_GENERATION,
        ProviderAdapterKind.OPENAI_COMPATIBLE,
        "text.generate",
    ),
    ProviderLabPreset(
        "anthropic-compatible-llm",
        ProviderKind.TEXT_GENERATION,
        ProviderAdapterKind.ANTHROPIC_COMPATIBLE,
        "text.generate",
    ),
    ProviderLabPreset(
        "mimo-v2-5-tts",
        ProviderKind.TEXT_TO_SPEECH,
        ProviderAdapterKind.MIMO_TTS,
        "speech.tts",
    ),
    ProviderLabPreset(
        "mimo-v2-5-asr",
        ProviderKind.SPEECH_TO_TEXT,
        ProviderAdapterKind.MIMO_ASR,
        "speech.asr",
    ),
    ProviderLabPreset(
        "z-image",
        ProviderKind.IMAGE_GENERATION,
        ProviderAdapterKind.CUSTOM_HTTP,
        "image.generate",
    ),
    ProviderLabPreset(
        "gpt-image",
        ProviderKind.IMAGE_GENERATION,
        ProviderAdapterKind.OPENAI,
        "image.generate",
    ),
    ProviderLabPreset(
        "comfyui",
        ProviderKind.WORKFLOW_ENGINE,
        ProviderAdapterKind.COMFYUI,
        "workflow.execute",
    ),
    ProviderLabPreset(
        "openai-compatible-image",
        ProviderKind.IMAGE_GENERATION,
        ProviderAdapterKind.OPENAI_COMPATIBLE,
        "image.generate",
    ),
    ProviderLabPreset(
        "generic-image-custom-http",
        ProviderKind.IMAGE_GENERATION,
        ProviderAdapterKind.CUSTOM_HTTP,
        "image.generate",
    ),
)


def test_provider_lab_templates_cover_required_presets_without_forced_vendor_urls() -> None:
    templates = {template.template_key: template for template in provider_templates()}

    assert set(templates).issuperset({preset.template_key for preset in LAB_PRESETS})
    for preset in LAB_PRESETS:
        template = templates[preset.template_key]
        assert template.provider_kind == preset.provider_kind
        assert template.adapter_kind == preset.adapter_kind
        assert any(
            capability.capability_key == preset.capability_key
            for capability in template.capabilities
        )
        assert template.base_url_placeholder != ""
        assert "api_key" not in str(template.config_json).lower()


def test_provider_lab_model_discovery_uses_static_models_and_manual_fallback() -> None:
    engine = _engine()
    world_id, _worldline_id = _seed_world(engine)

    with Session(engine) as session:
        discovered = ProviderModelDiscoveryService(session).discover(
            world_id,
            ProviderModelDiscoveryRequest(
                provider_kind=ProviderKind.IMAGE_GENERATION,
                adapter_kind=ProviderAdapterKind.CUSTOM_HTTP,
                base_url="https://provider.example",
                config_json={"available_models": ["z-image-turbo", "z-image-turbo"]},
            ),
        )
        failed = ProviderModelDiscoveryService(session).discover(
            world_id,
            ProviderModelDiscoveryRequest(
                provider_kind=ProviderKind.TEXT_TO_SPEECH,
                adapter_kind=ProviderAdapterKind.MIMO_TTS,
                base_url="https://provider.example",
                config_json={"disable_model_discovery": True},
            ),
        )

    assert discovered.discovery_status == "succeeded"
    assert discovered.models == ["z-image-turbo"]
    assert discovered.manual_fallback_allowed is True
    assert failed.discovery_status == "failed"
    assert failed.manual_fallback_allowed is True
    assert failed.models == []
    assert "provider.example" not in str(failed.model_dump())


@pytest.mark.parametrize(
    ("provider_kind", "capability_key", "expected_text"),
    [
        (ProviderKind.TEXT_GENERATION, "text.generate", "fake text: provider lab"),
        (ProviderKind.IMAGE_GENERATION, "image.generate", "fake image generated"),
        (ProviderKind.TEXT_TO_SPEECH, "speech.tts", "fake speech audio generated"),
        (ProviderKind.SPEECH_TO_TEXT, "speech.asr", "provider lab transcript"),
    ],
)
def test_provider_lab_fake_execution_contracts_do_not_call_external_providers(
    provider_kind: ProviderKind,
    capability_key: str,
    expected_text: str,
    tmp_path: Path,
) -> None:
    engine = _engine()
    world_id, worldline_id = _seed_world(engine)
    storage = LocalMediaObjectStorage(tmp_path)

    with Session(engine) as session:
        provider_id = _seed_provider(
            session,
            world_id,
            provider_kind=provider_kind,
            adapter_kind=ProviderAdapterKind.FAKE,
            capability_key=capability_key,
            config_json={},
        )
        result = ProviderExecutionService(session, storage).execute(
            ProviderExecutionRequest(
                world_id=world_id,
                worldline_id=worldline_id,
                provider_id=provider_id,
                input_text="provider lab",
                request_json={"transcript": "provider lab transcript"},
                actor_ref="test:provider-lab",
            )
        )
        session.commit()

    assert result.output_text == expected_text
    assert result.invocation.status == "succeeded"
    if provider_kind in {ProviderKind.IMAGE_GENERATION, ProviderKind.TEXT_TO_SPEECH}:
        assert result.media_job is not None
        assert result.output_asset is not None
    with Session(engine) as session:
        invocation = session.scalars(select(ModelInvocation)).one()
        snapshot = session.scalars(select(PromptSnapshot)).one()
        assert invocation.status == "succeeded"
        assert "api_key" not in str(invocation.request_params_json).lower()
        assert "authorization" not in str(snapshot.raw_request_json).lower()


def test_provider_lab_text_adapter_dry_runs_are_ledger_backed_without_secrets() -> None:
    engine = _engine()
    world_id, worldline_id = _seed_world(engine)

    with Session(engine) as session:
        openai_provider_id = _seed_provider(
            session,
            world_id,
            provider_kind=ProviderKind.TEXT_GENERATION,
            adapter_kind=ProviderAdapterKind.OPENAI_COMPATIBLE,
            capability_key="text.generate",
            config_json={"dry_run": True},
        )
        anthropic_provider_id = _seed_provider(
            session,
            world_id,
            provider_kind=ProviderKind.TEXT_GENERATION,
            adapter_kind=ProviderAdapterKind.ANTHROPIC_COMPATIBLE,
            capability_key="text.generate",
            config_json={"dry_run": True},
        )
        openai = ProviderExecutionService(session).execute(
            ProviderExecutionRequest(
                world_id=world_id,
                worldline_id=worldline_id,
                provider_id=openai_provider_id,
                input_text="openai compatible smoke",
                model_name="manual-openai-model",
            )
        )
        anthropic = ProviderExecutionService(session).execute(
            ProviderExecutionRequest(
                world_id=world_id,
                worldline_id=worldline_id,
                provider_id=anthropic_provider_id,
                input_text="anthropic compatible smoke",
                model_name="manual-anthropic-model",
            )
        )
        session.commit()

    assert openai.output_text == "openai-compatible dry-run: openai compatible smoke"
    assert anthropic.output_text == "anthropic-compatible dry-run: anthropic compatible smoke"
    with Session(engine) as session:
        invocations = session.scalars(
            select(ModelInvocation).order_by(ModelInvocation.created_at)
        ).all()
        assert [item.provider_kind for item in invocations] == [
            "openai_compatible",
            "anthropic_compatible",
        ]
        assert [item.status for item in invocations] == ["succeeded", "succeeded"]
        metadata = str([item.response_metadata_json for item in invocations])
        assert "OPENAI_API_KEY" not in metadata
        assert "ANTHROPIC_API_KEY" not in metadata
        assert "gateway.example" not in metadata


def test_provider_lab_mimo_tts_asr_dry_runs_are_opt_in_safe(tmp_path: Path) -> None:
    engine = _engine()
    world_id, worldline_id = _seed_world(engine)
    storage = LocalMediaObjectStorage(tmp_path)

    with Session(engine) as session:
        tts_provider_id = _seed_provider(
            session,
            world_id,
            provider_kind=ProviderKind.TEXT_TO_SPEECH,
            adapter_kind=ProviderAdapterKind.MIMO_TTS,
            capability_key="speech.tts",
            config_json={"dry_run": True},
        )
        asr_provider_id = _seed_provider(
            session,
            world_id,
            provider_kind=ProviderKind.SPEECH_TO_TEXT,
            adapter_kind=ProviderAdapterKind.MIMO_ASR,
            capability_key="speech.asr",
            config_json={"dry_run": True},
        )
        tts = ProviderExecutionService(session, storage).execute(
            ProviderExecutionRequest(
                world_id=world_id,
                worldline_id=worldline_id,
                provider_id=tts_provider_id,
                input_text="hello",
                request_json={"provider_voice_id": "voice-1", "style_json": {"emotion": "calm"}},
            )
        )
        asr = ProviderExecutionService(session, storage).execute(
            ProviderExecutionRequest(
                world_id=world_id,
                worldline_id=worldline_id,
                provider_id=asr_provider_id,
                request_json={"transcript": "mimo transcript"},
            )
        )
        session.commit()

    assert tts.output_text == "mimo dry-run speech audio generated"
    assert tts.output_asset is not None
    assert tts.output_objects[0].mime_type == "audio/wav"
    assert asr.output_text == "mimo transcript"
    assert asr.output_asset is None
    with Session(engine) as session:
        assert session.scalars(select(ModelInvocation)).all()
        assert os.getenv("NOVELAND_RUN_REAL_PROVIDER_TESTS") != "1"


@pytest.mark.parametrize(
    ("adapter_kind", "provider_key", "slot_values", "prompt_plan", "model_plan", "expected_kind"),
    [
        (
            ProviderAdapterKind.COMFYUI,
            "comfyui",
            {"positive_prompt": "heroine", "checkpoint_id": str(uuid.uuid4())},
            {"positive_prompt": "heroine"},
            {},
            "comfyui",
        ),
        (
            ProviderAdapterKind.CUSTOM_HTTP,
            "z-image",
            {"prompt": "background"},
            {"prompt": "background"},
            {"provider_family": "z_image"},
            "z_image",
        ),
        (
            ProviderAdapterKind.OPENAI,
            "gpt-image",
            {"prompt": "event cg"},
            {"prompt": "event cg"},
            {},
            "openai",
        ),
        (
            ProviderAdapterKind.OPENAI_COMPATIBLE,
            "openai-compatible-image",
            {"prompt": "sprite"},
            {"prompt": "sprite"},
            {},
            "openai_compatible",
        ),
        (
            ProviderAdapterKind.CUSTOM_HTTP,
            "generic-image-custom-http",
            {"prompt": "custom"},
            {"prompt": "custom"},
            {},
            "custom_http",
        ),
    ],
)
def test_provider_lab_visual_generation_mappings_are_validation_only(
    adapter_kind: ProviderAdapterKind,
    provider_key: str,
    slot_values: dict[str, Any],
    prompt_plan: dict[str, Any],
    model_plan: dict[str, Any],
    expected_kind: str,
) -> None:
    result = map_provider_request(
        adapter_kind=adapter_kind,
        provider_key=provider_key,
        template_payload_json={"nodes": {}} if adapter_kind == ProviderAdapterKind.COMFYUI else {},
        slot_values=slot_values,
        prompt_plan_json=prompt_plan,
        model_plan_json=model_plan,
        output_plan_json={"size": "1024x1024"},
    )

    assert result.validation.passed is True
    assert result.validation.provider_call_made is False
    assert result.mapping_kind == expected_kind
    assert "base64" not in str(result.request_json).lower()
    assert "storage_uri" not in str(result.request_json).lower()


def test_provider_lab_real_provider_marker_is_skipped_by_default() -> None:
    assert RUN_REAL_PROVIDER_TESTS is False


@pytest.mark.real_provider
@pytest.mark.skipif(
    not RUN_REAL_PROVIDER_TESTS,
    reason="requires NOVELAND_RUN_REAL_PROVIDER_TESTS=1",
)
def test_provider_lab_real_provider_examples_require_explicit_opt_in() -> None:
    config = _real_provider_lab_config()
    missing = [name for name, value in config.items() if not value]
    if missing:
        pytest.skip(f"provider lab env not configured: {', '.join(sorted(missing))}")

    evidence = _safe_provider_lab_evidence(
        provider_family="openai-compatible",
        provider_kind=ProviderKind.TEXT_GENERATION,
        adapter_kind=ProviderAdapterKind.OPENAI_COMPATIBLE,
        capability_key="text.generate",
        model_name=config["openai_model"],
        status="configured",
        error_class=None,
    )

    assert evidence == {
        "provider_family": "openai-compatible",
        "provider_kind": "text_generation",
        "adapter_kind": "openai_compatible",
        "capability_key": "text.generate",
        "model_name": config["openai_model"],
        "status": "configured",
        "error_class": None,
    }
    assert "auth_ref" not in evidence
    assert "base_url" not in evidence


def _real_provider_lab_config() -> dict[str, str | None]:
    return {
        "openai_base_url": os.getenv("NOVELAND_PROVIDER_LAB_OPENAI_BASE_URL"),
        "openai_auth_ref": os.getenv("NOVELAND_PROVIDER_LAB_OPENAI_AUTH_REF"),
        "openai_model": os.getenv("NOVELAND_PROVIDER_LAB_OPENAI_MODEL"),
    }


def _safe_provider_lab_evidence(
    *,
    provider_family: str,
    provider_kind: ProviderKind,
    adapter_kind: ProviderAdapterKind,
    capability_key: str,
    model_name: str | None,
    status: str,
    error_class: str | None,
) -> dict[str, str | None]:
    return {
        "provider_family": provider_family,
        "provider_kind": provider_kind.value,
        "adapter_kind": adapter_kind.value,
        "capability_key": capability_key,
        "model_name": model_name,
        "status": status,
        "error_class": error_class,
    }


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
                is_active=True,
            )
        )
        session.flush()
        worldline = ensure_primary_worldline(session, world_id)
        session.commit()
        return world_id, worldline.id


def _seed_provider(
    session: Session,
    world_id: uuid.UUID,
    *,
    provider_kind: ProviderKind,
    adapter_kind: ProviderAdapterKind,
    capability_key: str,
    config_json: dict[str, Any],
) -> uuid.UUID:
    provider = ProviderRegistryService(session).create_provider(
        ProviderIntegrationCreate(
            world_id=world_id,
            scope_kind=ProviderScopeKind.WORLD,
            provider_kind=provider_kind,
            adapter_kind=adapter_kind,
            provider_key=f"{adapter_kind.value}-{uuid.uuid4().hex[:8]}",
            display_name=f"{adapter_kind.value} Provider",
            config_json=config_json,
            capabilities=(
                ProviderCapabilityCreate(
                    capability_key=capability_key,
                    capability_json={"value": True},
                ),
            ),
        )
    )
    return provider.id


@pytest.fixture(autouse=True)
def _real_provider_default_guard() -> Iterator[None]:
    original = os.environ.get("NOVELAND_RUN_REAL_PROVIDER_TESTS")
    if original is None:
        os.environ.pop("NOVELAND_RUN_REAL_PROVIDER_TESTS", None)
    yield
    if original is None:
        os.environ.pop("NOVELAND_RUN_REAL_PROVIDER_TESTS", None)
    else:
        os.environ["NOVELAND_RUN_REAL_PROVIDER_TESTS"] = original
