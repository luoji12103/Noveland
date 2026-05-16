from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from noveland.media.models import MediaAsset, MediaObject
from noveland.world_packaging.contracts import (
    SUPPORTED_MANIFEST_VERSION,
    WorldPackageManifest,
    WorldPackageMediaManifest,
    WorldPackageMediaObjectManifest,
    WorldPackageMediaReferenceManifest,
    WorldPackageMetadata,
    WorldPackageSceneManifest,
    WorldPackageWorldlineManifest,
    WorldPackageWorldManifest,
)
from noveland.worlds.models import LongRunEvalRun, Scene, World, Worldline
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.fixtures.multimodal_sample_world import (
    MultimodalSampleWorld,
    create_multimodal_sample_world,
)

SAMPLE_RELEASE_PACKAGE_KEY = "phase13-sample-world-release"
SAMPLE_RELEASE_FIXTURE_KEY = "phase13_multimodal_sample_world"
SAMPLE_RELEASE_GENERATED_AT = datetime(2026, 5, 16, 0, 0, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class SampleWorldReleasePackage:
    sample: MultimodalSampleWorld
    manifest: WorldPackageManifest
    expected_counts: dict[str, int]
    reader_visible_asset_keys: tuple[str, ...]
    diagnostics_eval_key: str


def create_sample_world_release_package(tmp_path: Path) -> SampleWorldReleasePackage:
    sample = create_multimodal_sample_world(tmp_path)
    expected_counts = {
        "worlds": 1,
        "worldlines": 1,
        "agents": 2,
        "scenes": 1,
        "conversation_sessions": 1,
        "conversation_turns": 1,
        "media_assets": 7,
        "media_objects": 7,
        "sprite_variants": 3,
        "voice_profiles": 1,
        "transcripts": 1,
        "presentations": 1,
        "asset_generation_proposals": 1,
        "multimodal_eval_runs": 1,
    }
    reader_visible_asset_keys = (
        "background",
        "sprite_neutral",
        "sprite_happy",
        "sprite_sad",
        "tts_audio",
        "composite",
    )
    manifest = _build_manifest(
        sample,
        expected_counts=expected_counts,
        reader_visible_asset_keys=reader_visible_asset_keys,
    )
    return SampleWorldReleasePackage(
        sample=sample,
        manifest=manifest,
        expected_counts=expected_counts,
        reader_visible_asset_keys=reader_visible_asset_keys,
        diagnostics_eval_key="multimodal-smoke",
    )


def _build_manifest(
    sample: MultimodalSampleWorld,
    *,
    expected_counts: dict[str, int],
    reader_visible_asset_keys: tuple[str, ...],
) -> WorldPackageManifest:
    with Session(sample.engine) as session:
        world = session.get(World, sample.world_id)
        worldline = session.get(Worldline, sample.worldline_id)
        scene = session.get(Scene, sample.scene_id)
        eval_run = session.get(LongRunEvalRun, sample.long_run_eval_id)
        if world is None or worldline is None or scene is None or eval_run is None:
            raise RuntimeError("sample world fixture is incomplete")

        return WorldPackageManifest(
            metadata=WorldPackageMetadata(
                manifest_version=SUPPORTED_MANIFEST_VERSION,
                package_key=SAMPLE_RELEASE_PACKAGE_KEY,
                generated_at=SAMPLE_RELEASE_GENERATED_AT,
                capabilities=(
                    "world",
                    "worldline",
                    "scene",
                    "media-manifest",
                    "sample-fixture",
                    "reader-playback",
                    "multimodal-diagnostics",
                ),
            ),
            world=WorldPackageWorldManifest(
                slug=world.slug,
                name=world.name,
                description=(
                    "Deterministic Noveland multimodal sample world release package."
                ),
                memory_plugin_identifier=world.memory_plugin_identifier,
                memory_plugin_config={},
                world_rules_plugin_identifier=world.world_rules_plugin_identifier,
                world_rules_plugin_config={},
                rules_config={
                    "release_package": "v0.8.9",
                    "fixture_linkage": {
                        "fixture_key": SAMPLE_RELEASE_FIXTURE_KEY,
                        "expected_counts": expected_counts,
                    },
                    "diagnostics_evidence": {
                        "eval_key": eval_run.eval_key,
                        "status": eval_run.status,
                    },
                },
                is_active=True,
            ),
            worldlines=(
                WorldPackageWorldlineManifest(
                    worldline_key=worldline.worldline_key,
                    name=worldline.name,
                    description="Primary branch for the deterministic sample release.",
                    status=worldline.status,
                    metadata={
                        "fixture_key": SAMPLE_RELEASE_FIXTURE_KEY,
                        "primary": True,
                    },
                ),
            ),
            scenes=(
                WorldPackageSceneManifest(
                    scene_key=scene.scene_key,
                    name=scene.name,
                    description="Sample classroom scene for playback and scene view checks.",
                    region_key=scene.region_key,
                    location_tags=tuple(scene.location_tags),
                    opening_rules={},
                    is_active=True,
                ),
            ),
            media=tuple(
                _media_manifest(
                    session,
                    sample,
                    asset_key=asset_key,
                    visibility=(
                        "reader_visible"
                        if asset_key in reader_visible_asset_keys
                        else "world_admin"
                    ),
                )
                for asset_key in _release_asset_keys()
            ),
        )


def _media_manifest(
    session: Session,
    sample: MultimodalSampleWorld,
    *,
    asset_key: str,
    visibility: str,
) -> WorldPackageMediaManifest:
    asset = session.get(MediaAsset, sample.asset_ids[asset_key])
    if asset is None:
        raise RuntimeError(f"sample media asset is missing: {asset_key}")
    objects = tuple(
        WorldPackageMediaObjectManifest(
            object_role=media_object.object_role,
            mime_type=media_object.mime_type,
            size_bytes=media_object.size_bytes,
            checksum_sha256=media_object.checksum_sha256,
            width=media_object.width,
            height=media_object.height,
            duration_ms=media_object.duration_ms,
            sample_rate_hz=media_object.sample_rate_hz,
            audio_channels=media_object.audio_channels,
        )
        for media_object in session.scalars(
            select(MediaObject)
            .where(MediaObject.asset_id == asset.id)
            .order_by(MediaObject.created_at, MediaObject.id)
        ).all()
    )
    return WorldPackageMediaManifest(
        package_asset_key=asset_key,
        worldline_key="primary",
        asset_kind=asset.asset_kind,
        asset_role=asset.asset_role,
        source_kind="test_fixture",
        status="available",
        visibility=visibility,
        mime_type=asset.mime_type,
        size_bytes=asset.size_bytes,
        checksum_sha256=asset.checksum_sha256,
        title=_asset_title(asset_key),
        description="Synthetic Noveland sample fixture media.",
        objects=objects,
        references=_asset_references(sample, asset_key),
        metadata={
            "fixture_key": SAMPLE_RELEASE_FIXTURE_KEY,
            "rights": {
                "license": "Noveland sample fixture",
                "source": "synthetic deterministic test fixture",
                "attribution": "Noveland",
                "third_party_content": False,
            },
            "release_roles": _release_roles(asset_key),
        },
    )


def _asset_references(
    sample: MultimodalSampleWorld,
    asset_key: str,
) -> tuple[WorldPackageMediaReferenceManifest, ...]:
    turn_ref = WorldPackageMediaReferenceManifest(
        ref_kind="conversation_turn",
        ref_key="phase13-session:turn-0",
        ref_role=_turn_ref_role(asset_key),
        display_order=_asset_order(asset_key),
    )
    if asset_key == "background":
        return (
            WorldPackageMediaReferenceManifest(
                ref_kind="scene",
                ref_key="classroom",
                ref_role="background",
                display_order=0,
            ),
            turn_ref,
        )
    if asset_key.startswith("sprite_"):
        expression = asset_key.removeprefix("sprite_")
        return (
            WorldPackageMediaReferenceManifest(
                ref_kind="sprite_variant",
                ref_key=f"alice:{expression}",
                ref_role="character_sprite",
                display_order=_asset_order(asset_key),
            ),
            turn_ref,
        )
    if asset_key == "tts_audio":
        return (
            WorldPackageMediaReferenceManifest(
                ref_kind="turn_presentation",
                ref_key=str(sample.presentation_id),
                ref_role="speech_audio",
                display_order=3,
            ),
            turn_ref,
        )
    if asset_key == "composite":
        return (
            WorldPackageMediaReferenceManifest(
                ref_kind="turn_presentation",
                ref_key=str(sample.presentation_id),
                ref_role="composite_scene",
                display_order=2,
            ),
            turn_ref,
        )
    return (turn_ref,)


def _release_asset_keys() -> tuple[str, ...]:
    return (
        "background",
        "sprite_neutral",
        "sprite_happy",
        "sprite_sad",
        "tts_audio",
        "stt_audio",
        "composite",
    )


def _asset_title(asset_key: str) -> str:
    return asset_key.replace("_", " ").title()


def _release_roles(asset_key: str) -> tuple[str, ...]:
    if asset_key == "background":
        return ("playback", "scene_view", "background")
    if asset_key.startswith("sprite_"):
        return ("playback", "scene_view", "character_sprite")
    if asset_key == "tts_audio":
        return ("playback", "speech_audio")
    if asset_key == "composite":
        return ("playback", "scene_view", "composite_scene")
    return ("diagnostic_source",)


def _turn_ref_role(asset_key: str) -> str:
    if asset_key == "background":
        return "background"
    if asset_key.startswith("sprite_"):
        return "character_sprite"
    if asset_key == "tts_audio":
        return "speech_audio"
    if asset_key == "stt_audio":
        return "transcript_source"
    if asset_key == "composite":
        return "composite_scene"
    return "attachment"


def _asset_order(asset_key: str) -> int:
    return _release_asset_keys().index(asset_key)
