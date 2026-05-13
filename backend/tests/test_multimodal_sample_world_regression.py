from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast

from noveland.asset_generation.models import AssetGenerationProposal
from noveland.auth import AuthSessionService
from noveland.conversations.models import ConversationTurn, ConversationTurnPresentation
from noveland.events.models import WorldEventModel
from noveland.invocations.models import ModelInvocation
from noveland.media.models import MediaAsset, MediaJob, MediaObject
from noveland.memory.models import MemoryWriteJob
from noveland.multimodal_eval import MultimodalEvalService
from noveland.providers.models import ProviderHealthCheck
from noveland.speech.models import AgentVoiceProfileBinding, SpeechTranscript, VoiceProfile
from noveland.visual.contracts import BackgroundResolveRequest, SpriteResolveRequest
from noveland.visual.models import (
    CharacterSpriteSet,
    CharacterSpriteVariant,
    SceneBackgroundProfile,
)
from noveland.visual.resolver import VisualResolver
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tests.fixtures.multimodal_sample_world import (
    authenticate,
    create_multimodal_sample_world,
    create_sample_world_client,
)


def test_sample_world_fixture_is_deterministic_and_worldline_scoped(tmp_path: Path) -> None:
    first = create_multimodal_sample_world(tmp_path / "first")
    second = create_multimodal_sample_world(tmp_path / "second")

    assert first.world_id == second.world_id
    assert first.worldline_id == second.worldline_id
    assert first.agent_ids == second.agent_ids
    assert first.asset_ids == second.asset_ids

    with Session(first.engine) as session:
        world_scoped_models = (
            CharacterSpriteSet,
            CharacterSpriteVariant,
            SceneBackgroundProfile,
            ConversationTurnPresentation,
            MediaAsset,
            MediaObject,
            MediaJob,
            ModelInvocation,
            SpeechTranscript,
            VoiceProfile,
            AgentVoiceProfileBinding,
            AssetGenerationProposal,
        )
        for model in world_scoped_models:
            rows = cast(list[Any], session.scalars(select(model)).all())
            assert rows, model.__name__
            assert {row.world_id for row in rows} == {first.world_id}
            assert {row.worldline_id for row in rows} == {first.worldline_id}

        assert session.scalar(
            select(func.count())
            .select_from(CharacterSpriteSet)
            .where(CharacterSpriteSet.worldline_id.is_(None))
        ) == 0
        assert session.scalar(
            select(func.count())
            .select_from(CharacterSpriteVariant)
            .where(CharacterSpriteVariant.worldline_id.is_(None))
        ) == 0
        assert session.scalar(
            select(func.count())
            .select_from(SceneBackgroundProfile)
            .where(SceneBackgroundProfile.worldline_id.is_(None))
        ) == 0


def test_sample_world_resolvers_and_presentation_references_are_valid(tmp_path: Path) -> None:
    sample = create_multimodal_sample_world(tmp_path)

    with Session(sample.engine) as session:
        resolver = VisualResolver(session)
        for expression in ("neutral", "happy", "sad"):
            resolved = resolver.resolve_sprite(
                sample.world_id,
                SpriteResolveRequest(
                    worldline_id=sample.worldline_id,
                    agent_id=sample.agent_ids[0],
                    expression_key=expression,
                ),
            )
            assert resolved.variant.id == sample.sprite_variant_ids[expression]
            assert resolved.asset.id == sample.asset_ids[f"sprite_{expression}"]
            assert resolved.fallback_reason is None
            assert "storage_uri" not in resolved.asset.model_dump()

        background = resolver.resolve_background(
            sample.world_id,
            BackgroundResolveRequest(
                worldline_id=sample.worldline_id,
                scene_id=sample.scene_id,
                location_key="classroom",
                time_of_day="night",
                weather_key="rain",
            ),
        )
        assert background.background.id == sample.background_profile_id
        assert background.asset.id == sample.asset_ids["background"]
        assert background.fallback_reason == "default_background"
        assert "storage_uri" not in background.asset.model_dump()

        presentation = session.get(ConversationTurnPresentation, sample.presentation_id)
        assert presentation is not None
        assert presentation.sprite_variant_id == sample.sprite_variant_ids["happy"]
        assert presentation.background_asset_id == sample.asset_ids["background"]
        assert presentation.voice_profile_id == sample.voice_profile_id
        assert presentation.tts_media_asset_id == sample.asset_ids["tts_audio"]
        assert presentation.composite_scene_asset_id == sample.asset_ids["composite"]
        assert presentation.transcript_id == sample.transcript_id

        referenced_asset_ids = {
            presentation.background_asset_id,
            presentation.tts_media_asset_id,
            presentation.composite_scene_asset_id,
        }
        assert None not in referenced_asset_ids
        assets = session.scalars(
            select(MediaAsset).where(MediaAsset.id.in_(referenced_asset_ids))
        ).all()
        assert {asset.worldline_id for asset in assets} == {sample.worldline_id}


def test_sample_world_media_integrity_and_no_event_payload_leak(tmp_path: Path) -> None:
    sample = create_multimodal_sample_world(tmp_path)

    with Session(sample.engine) as session:
        objects = session.scalars(select(MediaObject)).all()
        assert objects
        for media_object in objects:
            assert sample.storage.exists(media_object.storage_uri)
            data = sample.storage.read_bytes(media_object.storage_uri)
            assert hashlib.sha256(data).hexdigest() == media_object.checksum_sha256
            assert len(data) == media_object.size_bytes

        for event in session.scalars(select(WorldEventModel)).all():
            assert not _contains_forbidden_payload(event.payload)


def test_sample_world_security_boundaries_and_admin_controlled_generation(
    tmp_path: Path,
) -> None:
    sample = create_multimodal_sample_world(tmp_path)
    client = create_sample_world_client(sample)
    secret_value = "sk-phase13-secret"

    with Session(sample.engine) as session:
        subject = AuthSessionService(session).authenticate_session(sample.admin_token)
        assert subject.user_id == sample.admin_user_id

    authenticate(client, sample.admin_token)
    providers = client.get(f"/worlds/{sample.world_id}/providers")
    assert providers.status_code == 200
    assert secret_value not in providers.text
    assert "storage_uri" not in providers.text
    for provider in providers.json():
        health = client.get(
            f"/worlds/{sample.world_id}/providers/{provider['id']}/health-checks",
        )
        assert health.status_code == 200
        assert secret_value not in health.text
        for check in health.json():
            _assert_no_sensitive_keys(check["metadata_json"])

    authenticate(client, sample.member_token)
    member_snapshot = client.get(
        f"/worlds/{sample.world_id}/model-invocations/"
        f"{sample.invocation_ids['tts']}/prompt-snapshot",
    )
    member_preview = client.post(
        f"/worlds/{sample.world_id}/asset-generation/preview",
        json={
            "worldline_id": str(sample.worldline_id),
            "conversation_id": str(sample.conversation_id),
            "current_turn_id": str(sample.turn_id),
        },
    )
    member_apply = client.post(
        f"/worlds/{sample.world_id}/asset-generation/apply",
        json={
            "worldline_id": str(sample.worldline_id),
            "run_id": str(sample.asset_generation_preview_run_id),
            "proposal_ids": [str(sample.asset_generation_proposal_id)],
        },
    )

    assert member_snapshot.status_code == 403
    assert member_preview.status_code == 403
    assert member_apply.status_code == 403

    with Session(sample.engine) as session:
        proposal = session.get(AssetGenerationProposal, sample.asset_generation_proposal_id)
        job = session.get(MediaJob, sample.media_job_ids["asset_generation"])
        assert proposal is not None
        assert proposal.status == "applied"
        assert proposal.resulting_media_job_id == sample.media_job_ids["asset_generation"]
        assert job is not None
        assert job.status == "queued"
        assert job.started_at is None
        assert job.finished_at is None

        transcript = session.get(SpeechTranscript, sample.transcript_id)
        turn = session.get(ConversationTurn, sample.turn_id)
        assert transcript is not None
        assert turn is not None
        assert turn.input_text == "Hello."
        assert turn.output_text == "Welcome to the classroom."
        assert session.scalar(
            select(func.count())
            .select_from(MemoryWriteJob)
            .where(MemoryWriteJob.source_id == sample.transcript_id)
        ) == 0


def test_sample_world_multimodal_diagnostics_pass(tmp_path: Path) -> None:
    sample = create_multimodal_sample_world(tmp_path)

    with Session(sample.engine) as session:
        diagnostics = MultimodalEvalService(session, sample.storage).diagnostics(
            sample.world_id,
            worldline_id=sample.worldline_id,
        )
        run = MultimodalEvalService(session, sample.storage).run_eval(
            sample.world_id,
            request=__import__(
                "noveland.multimodal_eval.contracts",
                fromlist=["MultimodalEvalRunRequest"],
            ).MultimodalEvalRunRequest(worldline_id=sample.worldline_id),
        )
        session.commit()

    assert diagnostics.status == "completed"
    assert diagnostics.blockers == []
    assert diagnostics.warnings == []
    assert diagnostics.metrics["media_assets"]["missing_object_count"] == 0
    assert diagnostics.metrics["media_assets"]["missing_storage_count"] == 0
    assert diagnostics.metrics["visual"]["sprite_sets_missing_default_count"] == 0
    assert diagnostics.metrics["visual"]["sprite_sets_missing_neutral_count"] == 0
    assert diagnostics.metrics["speech"]["agents_missing_default_voice_count"] == 0
    assert diagnostics.metrics["speech"]["transcript_memory_write_count"] == 0
    assert diagnostics.metrics["invocations"]["estimated_cost_total"] == 0.03
    assert diagnostics.metrics["media_jobs"]["status_counts"]["queued"] == 1
    assert run.status == "completed"
    assert run.eval_key == "multimodal-smoke"

    with Session(sample.engine) as session:
        for check in session.scalars(select(ProviderHealthCheck)).all():
            _assert_no_sensitive_keys(check.metadata_json)


def _contains_forbidden_payload(value: object) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).lower()
            if lowered in {
                "storage_uri",
                "preview_uri",
                "thumbnail_uri",
                "base64",
                "bytes",
                "path",
                "file_path",
                "raw_prompt",
                "raw_output",
                "raw_prompt_text",
                "raw_output_text",
            }:
                return True
            if _contains_forbidden_payload(item):
                return True
    elif isinstance(value, list | tuple):
        return any(_contains_forbidden_payload(item) for item in value)
    elif isinstance(value, str):
        lowered = value.lower()
        return lowered.startswith(("media://", "local://", "file://", "/", "./", "../")) or (
            "base64," in lowered
        )
    return False


def _assert_no_sensitive_keys(value: object) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            assert str(key).lower() not in {
                "api_key",
                "apikey",
                "token",
                "bearer_token",
                "authorization",
                "secret",
                "client_secret",
                "access_key",
                "password",
                "private_key",
            }
            _assert_no_sensitive_keys(item)
    elif isinstance(value, list | tuple):
        for item in value:
            _assert_no_sensitive_keys(item)
    elif isinstance(value, str):
        assert not value.startswith("sk-")


def _json_text(value: Any) -> str:
    return json.dumps(value, sort_keys=True)
