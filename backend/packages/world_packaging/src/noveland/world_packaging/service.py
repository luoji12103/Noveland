from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any

from noveland.media.models import MediaAsset, MediaObject, MediaReference
from noveland.world_packaging.contracts import (
    FORBIDDEN_KEYS,
    FORBIDDEN_VALUE_MARKERS,
    SUPPORTED_MANIFEST_VERSION,
    WorldPackageApplyRequest,
    WorldPackageApplyResult,
    WorldPackageExportRequest,
    WorldPackageIssue,
    WorldPackageIssueSeverity,
    WorldPackageManifest,
    WorldPackageMediaManifest,
    WorldPackageMediaObjectManifest,
    WorldPackageMediaReferenceManifest,
    WorldPackageMetadata,
    WorldPackagePreviewResult,
    WorldPackageSceneManifest,
    WorldPackageWorldlineManifest,
    WorldPackageWorldManifest,
)
from noveland.worlds.models import Scene, World, Worldline
from sqlalchemy import select
from sqlalchemy.orm import Session


class WorldPackagingNotFoundError(Exception):
    """Requested package source record was not found."""


class WorldPackagingValidationError(Exception):
    """Package validation failed before a safe apply could run."""


class WorldPackagingService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def export_preview(
        self,
        world_id: uuid.UUID,
        request: WorldPackageExportRequest,
    ) -> WorldPackagePreviewResult:
        world = self._session.get(World, world_id)
        if world is None:
            raise WorldPackagingNotFoundError("world not found")
        worldline = self._resolve_export_worldline(world_id, request.worldline_id)
        package_key = request.package_key or _safe_package_key(world.slug)
        manifest = WorldPackageManifest(
            metadata=WorldPackageMetadata(
                manifest_version=SUPPORTED_MANIFEST_VERSION,
                package_key=package_key,
                generated_at=datetime.now(UTC),
                capabilities=("world", "worldline", "scene", "media-manifest"),
            ),
            world=WorldPackageWorldManifest(
                slug=world.slug,
                name=world.name,
                description=world.description,
                memory_plugin_identifier=world.memory_plugin_identifier,
                memory_plugin_config=_safe_json(world.memory_plugin_config),
                world_rules_plugin_identifier=world.world_rules_plugin_identifier,
                world_rules_plugin_config=_safe_json(world.world_rules_plugin_config),
                rules_config=_safe_json(world.rules_config),
                is_active=world.is_active,
            ),
            worldlines=(
                WorldPackageWorldlineManifest(
                    worldline_key=worldline.worldline_key,
                    name=worldline.name,
                    description=worldline.description,
                    status=worldline.status,
                    metadata=_safe_json(worldline.metadata_json),
                ),
            ),
            scenes=tuple(self._export_scenes(world_id)),
            media=tuple(
                self._export_media(world_id, worldline.id) if request.include_media else ()
            ),
        )
        return self.preview_import(manifest)

    def preview_import(self, manifest: WorldPackageManifest) -> WorldPackagePreviewResult:
        issues = list(self._validate_manifest(manifest))
        blockers = [
            issue for issue in issues if issue.severity is WorldPackageIssueSeverity.BLOCKER
        ]
        warnings = [
            issue for issue in issues if issue.severity is WorldPackageIssueSeverity.WARNING
        ]
        return WorldPackagePreviewResult(
            manifest=manifest,
            issues=tuple(issues),
            blocker_count=len(blockers),
            warning_count=len(warnings),
            creates_world=True,
            creates_scene_count=len(manifest.scenes),
            creates_media_asset_count=len(manifest.media),
            provider_execution=False,
            world_event_writes=False,
        )

    def apply_import(
        self,
        owner_user_id: uuid.UUID,
        request: WorldPackageApplyRequest,
        *,
        actor_ref: str,
    ) -> WorldPackageApplyResult:
        preview = self.preview_import(request.manifest)
        if preview.blocker_count > 0:
            raise WorldPackagingValidationError("package manifest has blockers")

        world = World(
            id=uuid.uuid4(),
            owner_user_id=owner_user_id,
            slug=request.slug or f"imported-{request.manifest.world.slug}",
            name=request.name or request.manifest.world.name,
            description=request.manifest.world.description,
            rules_config=dict(request.manifest.world.rules_config),
            memory_plugin_identifier=request.manifest.world.memory_plugin_identifier
            or "builtin.local_pgvector_memory",
            memory_plugin_config=dict(request.manifest.world.memory_plugin_config),
            world_rules_plugin_identifier=request.manifest.world.world_rules_plugin_identifier
            or "builtin.default_world_rules",
            world_rules_plugin_config=dict(request.manifest.world.world_rules_plugin_config),
            is_active=request.manifest.world.is_active,
        )
        self._session.add(world)
        self._session.flush()

        worldline_ids: dict[str, uuid.UUID] = {}
        for manifest_worldline in request.manifest.worldlines:
            worldline = Worldline(
                id=uuid.uuid4(),
                world_id=world.id,
                worldline_key=manifest_worldline.worldline_key,
                name=manifest_worldline.name,
                description=manifest_worldline.description,
                parent_worldline_id=None,
                forked_from_snapshot_id=None,
                fork_event_sequence=None,
                status=manifest_worldline.status,
                created_by_actor_ref=actor_ref,
                metadata_json=dict(manifest_worldline.metadata),
            )
            self._session.add(worldline)
            self._session.flush()
            worldline_ids[worldline.worldline_key] = worldline.id

        scene_ids: list[uuid.UUID] = []
        for manifest_scene in request.manifest.scenes:
            scene = Scene(
                id=uuid.uuid4(),
                world_id=world.id,
                scene_key=manifest_scene.scene_key,
                name=manifest_scene.name,
                description=manifest_scene.description,
                region_key=manifest_scene.region_key,
                location_tags=list(manifest_scene.location_tags),
                opening_rules=dict(manifest_scene.opening_rules),
                is_active=manifest_scene.is_active,
            )
            self._session.add(scene)
            self._session.flush()
            scene_ids.append(scene.id)

        media_asset_ids: list[uuid.UUID] = []
        for manifest_asset in request.manifest.media:
            worldline_id = worldline_ids[manifest_asset.worldline_key]
            asset = MediaAsset(
                id=uuid.uuid4(),
                world_id=world.id,
                worldline_id=worldline_id,
                asset_kind=manifest_asset.asset_kind,
                asset_role=manifest_asset.asset_role,
                source_kind=manifest_asset.source_kind,
                status=manifest_asset.status,
                visibility=manifest_asset.visibility,
                storage_uri=None,
                preview_uri=None,
                thumbnail_uri=None,
                mime_type=manifest_asset.mime_type,
                size_bytes=manifest_asset.size_bytes,
                checksum_sha256=manifest_asset.checksum_sha256,
                title=manifest_asset.title,
                description=manifest_asset.description,
                created_by_actor_ref=actor_ref,
                metadata_json={
                    **dict(manifest_asset.metadata),
                    "package_asset_key": manifest_asset.package_asset_key,
                    "package_import_placeholder": True,
                },
            )
            self._session.add(asset)
            self._session.flush()
            media_asset_ids.append(asset.id)

        return WorldPackageApplyResult(
            preview=preview,
            applied=True,
            created_world_id=world.id,
            created_worldline_ids=tuple(worldline_ids.values()),
            created_scene_ids=tuple(scene_ids),
            created_media_asset_ids=tuple(media_asset_ids),
            provider_execution=False,
            world_event_writes=False,
        )

    def _resolve_export_worldline(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
    ) -> Worldline:
        statement = (
            select(Worldline).where(Worldline.world_id == world_id).order_by(Worldline.created_at)
        )
        if worldline_id is not None:
            statement = statement.where(Worldline.id == worldline_id)
        worldline = self._session.scalars(statement).first()
        if worldline is None:
            raise WorldPackagingNotFoundError("worldline not found")
        return worldline

    def _export_scenes(self, world_id: uuid.UUID) -> list[WorldPackageSceneManifest]:
        scenes = self._session.scalars(
            select(Scene).where(Scene.world_id == world_id).order_by(Scene.scene_key)
        ).all()
        return [
            WorldPackageSceneManifest(
                scene_key=scene.scene_key,
                name=scene.name,
                description=scene.description,
                region_key=scene.region_key,
                location_tags=tuple(scene.location_tags),
                opening_rules=_safe_json(scene.opening_rules),
                is_active=scene.is_active,
            )
            for scene in scenes
        ]

    def _export_media(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
    ) -> list[WorldPackageMediaManifest]:
        assets = self._session.scalars(
            select(MediaAsset)
            .where(MediaAsset.world_id == world_id, MediaAsset.worldline_id == worldline_id)
            .order_by(MediaAsset.created_at, MediaAsset.id)
        ).all()
        return [
            WorldPackageMediaManifest(
                package_asset_key=f"asset-{asset.id}",
                worldline_key=self._worldline_key(asset.worldline_id),
                asset_kind=asset.asset_kind,
                asset_role=asset.asset_role,
                source_kind=asset.source_kind,
                status=asset.status,
                visibility=asset.visibility,
                mime_type=asset.mime_type,
                size_bytes=asset.size_bytes,
                checksum_sha256=asset.checksum_sha256,
                title=asset.title,
                description=asset.description,
                objects=tuple(self._export_media_objects(asset)),
                references=tuple(self._export_media_references(asset)),
                metadata=_safe_json(asset.metadata_json),
            )
            for asset in assets
            if asset.visibility not in {"hidden", "developer_only"}
        ]

    def _worldline_key(self, worldline_id: uuid.UUID) -> str:
        worldline = self._session.get(Worldline, worldline_id)
        if worldline is None:
            raise WorldPackagingNotFoundError("media worldline not found")
        return worldline.worldline_key

    def _export_media_objects(self, asset: MediaAsset) -> list[WorldPackageMediaObjectManifest]:
        objects = self._session.scalars(
            select(MediaObject)
            .where(MediaObject.world_id == asset.world_id, MediaObject.asset_id == asset.id)
            .order_by(MediaObject.created_at)
        ).all()
        return [
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
            for media_object in objects
        ]

    def _export_media_references(
        self,
        asset: MediaAsset,
    ) -> list[WorldPackageMediaReferenceManifest]:
        refs = self._session.scalars(
            select(MediaReference)
            .where(MediaReference.world_id == asset.world_id, MediaReference.asset_id == asset.id)
            .order_by(MediaReference.display_order, MediaReference.created_at)
        ).all()
        return [
            WorldPackageMediaReferenceManifest(
                ref_kind=ref.ref_kind,
                ref_key=str(ref.ref_id),
                ref_role=ref.ref_role,
                display_order=ref.display_order,
            )
            for ref in refs
        ]

    def _validate_manifest(self, manifest: WorldPackageManifest) -> list[WorldPackageIssue]:
        issues: list[WorldPackageIssue] = []
        if manifest.metadata.manifest_version != SUPPORTED_MANIFEST_VERSION:
            issues.append(
                _blocker(
                    "unsupported_manifest_version",
                    "metadata.manifest_version",
                    f"Unsupported manifest version {manifest.metadata.manifest_version}.",
                )
            )
        if self._world_slug_exists(manifest.world.slug):
            issues.append(
                _warning(
                    "slug_exists",
                    "world.slug",
                    "World slug already exists; apply can use an override slug.",
                )
            )
        worldline_keys = {worldline.worldline_key for worldline in manifest.worldlines}
        for index, asset in enumerate(manifest.media):
            if asset.worldline_key not in worldline_keys:
                issues.append(
                    _blocker(
                        "unknown_worldline",
                        f"media[{index}].worldline_key",
                        "Media asset references a worldline key not present in the manifest.",
                    )
                )
            if asset.objects and (asset.checksum_sha256 is None or asset.size_bytes is None):
                issues.append(
                    _warning(
                        "asset_object_summary_missing",
                        f"media[{index}]",
                        (
                            "Media object entries exist but asset-level checksum/size summary "
                            "is missing."
                        ),
                    )
                )
        issues.extend(_forbidden_marker_issues(manifest.model_dump(mode="json")))
        return issues

    def _world_slug_exists(self, slug: str) -> bool:
        return self._session.scalar(select(World.id).where(World.slug == slug)) is not None


def _safe_json(value: dict[str, Any]) -> dict[str, Any]:
    return {
        key: child
        for key, child in value.items()
        if str(key).lower() not in FORBIDDEN_KEYS
        for child in [_safe_value(child)]
    }


def _safe_value(value: Any) -> Any:
    if isinstance(value, dict):
        return _safe_json(value)
    if isinstance(value, list):
        return [_safe_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_safe_value(item) for item in value)
    if isinstance(value, str):
        normalized = value.lower()
        if any(marker in normalized for marker in FORBIDDEN_VALUE_MARKERS):
            return "[redacted]"
    return value


def _forbidden_marker_issues(value: Any, path: str = "$") -> list[WorldPackageIssue]:
    issues: list[WorldPackageIssue] = []
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower()
            if normalized in FORBIDDEN_KEYS:
                issues.append(
                    _blocker(
                        "forbidden_manifest_key",
                        f"{path}.{key}",
                        f"Manifest contains forbidden key {key}.",
                    )
                )
            issues.extend(_forbidden_marker_issues(child, f"{path}.{key}"))
        return issues
    if isinstance(value, list | tuple):
        for index, child in enumerate(value):
            issues.extend(_forbidden_marker_issues(child, f"{path}[{index}]"))
        return issues
    if isinstance(value, str):
        normalized = value.lower()
        if any(marker in normalized for marker in FORBIDDEN_VALUE_MARKERS):
            issues.append(
                _blocker(
                    "forbidden_manifest_value",
                    path,
                    "Manifest contains a forbidden storage, prompt, binary, or secret marker.",
                )
            )
    return issues


def _safe_package_key(slug: str) -> str:
    key = re.sub(r"[^a-z0-9_-]+", "-", slug.lower()).strip("-_")
    return key or "world-package"


def _blocker(code: str, field: str, message: str) -> WorldPackageIssue:
    return WorldPackageIssue(
        severity=WorldPackageIssueSeverity.BLOCKER,
        code=code,
        field=field,
        message=message,
    )


def _warning(code: str, field: str, message: str) -> WorldPackageIssue:
    return WorldPackageIssue(
        severity=WorldPackageIssueSeverity.WARNING,
        code=code,
        field=field,
        message=message,
    )
