from __future__ import annotations

import json
from pathlib import Path

from noveland.media.models import MediaAsset, MediaObject
from noveland.world_packaging import WorldPackageApplyRequest, WorldPackagingService
from noveland.worlds.models import Scene, World
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tests.fixtures.sample_world_release_package import (
    SAMPLE_RELEASE_FIXTURE_KEY,
    SAMPLE_RELEASE_PACKAGE_KEY,
    create_sample_world_release_package,
)

FORBIDDEN_MARKERS = (
    "storage_uri",
    "media://",
    "file://",
    "s3://",
    "gs://",
    "base64",
    "raw_prompt",
    "raw_output",
    "prompt_snapshot",
    "secret",
    "api_key",
    "/tmp/",
    "/root/",
)


def test_sample_world_release_package_is_deterministic(tmp_path: Path) -> None:
    first = create_sample_world_release_package(tmp_path / "first")
    second = create_sample_world_release_package(tmp_path / "second")

    first_manifest = first.manifest.model_dump(mode="json")
    second_manifest = second.manifest.model_dump(mode="json")

    assert first_manifest == second_manifest
    assert first.manifest.metadata.package_key == SAMPLE_RELEASE_PACKAGE_KEY
    assert first.manifest.world.rules_config["fixture_linkage"]["fixture_key"] == (
        SAMPLE_RELEASE_FIXTURE_KEY
    )
    assert first.manifest.world.rules_config["fixture_linkage"]["expected_counts"] == (
        first.expected_counts
    )
    assert first.manifest.world.rules_config["diagnostics_evidence"]["eval_key"] == (
        first.diagnostics_eval_key
    )
    _assert_no_forbidden_markers(first_manifest)


def test_sample_world_release_package_has_rights_visibility_and_reader_media(
    tmp_path: Path,
) -> None:
    package = create_sample_world_release_package(tmp_path)
    media = {asset.package_asset_key: asset for asset in package.manifest.media}

    assert set(media) == {
        "background",
        "sprite_neutral",
        "sprite_happy",
        "sprite_sad",
        "tts_audio",
        "stt_audio",
        "composite",
    }
    for asset_key, asset in media.items():
        rights = asset.metadata["rights"]
        assert rights["license"] == "Noveland sample fixture"
        assert rights["source"] == "synthetic deterministic test fixture"
        assert rights["third_party_content"] is False
        assert asset.visibility in {"reader_visible", "world_admin"}
        assert asset.visibility != "hidden"
        assert asset.visibility != "developer_only"
        assert asset.objects
        assert asset.references
        if asset_key in package.reader_visible_asset_keys:
            assert asset.visibility == "reader_visible"
            assert any(role in asset.metadata["release_roles"] for role in ("playback",))
        _assert_no_forbidden_markers(asset.model_dump(mode="json"))

    assert media["background"].asset_role == "scene_background"
    assert media["sprite_happy"].asset_role == "character_sprite"
    assert media["tts_audio"].asset_role == "speech_audio"
    assert media["composite"].asset_role == "composite_image"


def test_sample_world_release_package_import_preview_and_apply_are_safe(
    tmp_path: Path,
) -> None:
    package = create_sample_world_release_package(tmp_path)

    with Session(package.sample.engine) as session:
        before_worlds = _count(session, World)
        before_assets = _count(session, MediaAsset)
        before_objects = _count(session, MediaObject)
        preview = WorldPackagingService(session).preview_import(package.manifest)
        after_preview_worlds = _count(session, World)
        after_preview_assets = _count(session, MediaAsset)
        apply = WorldPackagingService(session).apply_import(
            package.sample.admin_user_id,
            WorldPackageApplyRequest(
                manifest=package.manifest,
                slug="phase13-release-import",
                name="Phase 13 Release Import",
            ),
            actor_ref="test:sample-release",
        )
        session.commit()
        after_apply_worlds = _count(session, World)
        after_apply_assets = _count(session, MediaAsset)
        after_apply_objects = _count(session, MediaObject)
        imported_world = session.get(World, apply.created_world_id)
        imported_scene_count = session.scalar(
            select(func.count())
            .select_from(Scene)
            .where(Scene.world_id == apply.created_world_id)
        )

    assert preview.blocker_count == 0
    assert preview.creates_media_asset_count == 7
    assert preview.provider_execution is False
    assert preview.world_event_writes is False
    assert after_preview_worlds == before_worlds
    assert after_preview_assets == before_assets
    assert apply.applied is True
    assert apply.provider_execution is False
    assert apply.world_event_writes is False
    assert after_apply_worlds == before_worlds + 1
    assert after_apply_assets == before_assets + 7
    assert after_apply_objects == before_objects
    assert len(apply.created_media_asset_ids) == 7
    assert imported_world is not None
    assert imported_world.rules_config["fixture_linkage"]["fixture_key"] == (
        SAMPLE_RELEASE_FIXTURE_KEY
    )
    assert imported_scene_count == 1
    _assert_no_forbidden_markers(preview.model_dump(mode="json"))
    _assert_no_forbidden_markers(apply.model_dump(mode="json"))


def test_sample_world_release_package_links_to_existing_fixture_diagnostics(
    tmp_path: Path,
) -> None:
    package = create_sample_world_release_package(tmp_path)
    evidence = package.manifest.world.rules_config["diagnostics_evidence"]
    expected_counts = package.manifest.world.rules_config["fixture_linkage"]["expected_counts"]

    assert evidence == {"eval_key": "multimodal-smoke", "status": "completed"}
    assert expected_counts["media_assets"] == 7
    assert expected_counts["sprite_variants"] == 3
    assert expected_counts["presentations"] == 1
    assert "raw" not in json.dumps(evidence).lower()
    _assert_no_forbidden_markers(package.manifest.model_dump(mode="json"))


def _count(session: Session, model: type[object]) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def _assert_no_forbidden_markers(value: object) -> None:
    serialized = json.dumps(value, sort_keys=True).lower()
    for marker in FORBIDDEN_MARKERS:
        assert marker not in serialized
