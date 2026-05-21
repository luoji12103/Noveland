from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any

from noveland.agents.models import Agent, AgentPersona
from noveland.authoring.models import (
    AuthoringSourceAsset,
    AuthoringSourceBatch,
    AuthoringSourceFragment,
    AuthoringSourceTraceability,
)
from noveland.media.models import MediaAsset, MediaObject, MediaReference
from noveland.memory.models import AgentMemoryItem
from noveland.providers.models import ProviderCapability, ProviderIntegration
from noveland.speech.models import AgentVoiceProfileBinding, VoiceProfile
from noveland.visual.models import (
    CharacterSpriteSet,
    CharacterSpriteVariant,
    SceneBackgroundProfile,
)
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
    WorldPackageMemoryManifest,
    WorldPackageMetadata,
    WorldPackagePersonaManifest,
    WorldPackagePreviewResult,
    WorldPackageProviderManifest,
    WorldPackageSceneManifest,
    WorldPackageSourceTraceManifest,
    WorldPackageVisualMappingManifest,
    WorldPackageVoiceMappingManifest,
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
                self._export_media(
                    world_id,
                    worldline.id,
                    public_sample=request.public_sample,
                )
                if request.include_media
                else ()
            ),
            providers=tuple(
                self._export_providers(world_id) if request.include_extended_manifests else ()
            ),
            personas=tuple(
                self._export_personas(world_id) if request.include_extended_manifests else ()
            ),
            memories=tuple(
                self._export_memories(world_id, worldline.id)
                if request.include_extended_manifests
                else ()
            ),
            visual_mappings=tuple(
                self._export_visual_mappings(world_id, worldline.id)
                if request.include_extended_manifests
                else ()
            ),
            voice_mappings=tuple(
                self._export_voice_mappings(world_id, worldline.id)
                if request.include_extended_manifests
                else ()
            ),
            source_traceability=tuple(
                self._export_source_traceability(
                    world_id,
                    worldline.id,
                    public_sample=request.public_sample,
                )
                if request.include_extended_manifests
                else ()
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
            provider_manifest_count=len(manifest.providers),
            persona_manifest_count=len(manifest.personas),
            memory_manifest_count=len(manifest.memories),
            visual_mapping_count=len(manifest.visual_mappings),
            voice_mapping_count=len(manifest.voice_mappings),
            source_traceability_count=len(manifest.source_traceability),
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

        if _has_extended_manifest_sections(request.manifest):
            world.rules_config = {
                **dict(world.rules_config),
                "package_import_extended_manifests": {
                    "providers": [
                        provider.model_dump(mode="json")
                        for provider in request.manifest.providers
                    ],
                    "personas": [
                        persona.model_dump(mode="json")
                        for persona in request.manifest.personas
                    ],
                    "memories": [
                        memory.model_dump(mode="json") for memory in request.manifest.memories
                    ],
                    "visual_mappings": [
                        mapping.model_dump(mode="json")
                        for mapping in request.manifest.visual_mappings
                    ],
                    "voice_mappings": [
                        mapping.model_dump(mode="json")
                        for mapping in request.manifest.voice_mappings
                    ],
                    "source_traceability": [
                        trace.model_dump(mode="json")
                        for trace in request.manifest.source_traceability
                    ],
                    "apply_owner": "world_packaging_manifest_metadata",
                    "review_apply_required_for_specialized_records": True,
                },
            }

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
        *,
        public_sample: bool,
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
                objects=tuple(
                    () if _is_user_provided_media(asset) and public_sample
                    else self._export_media_objects(asset)
                ),
                references=tuple(self._export_media_references(asset)),
                metadata=_safe_json(
                    {
                        **dict(asset.metadata_json),
                        **(
                            {
                                "public_sample_policy": "excluded_placeholder",
                                "exclusion_reason": (
                                    "user-provided galgame media is excluded from "
                                    "public sample export"
                                ),
                            }
                            if _is_user_provided_media(asset) and public_sample
                            else {}
                        ),
                    }
                ),
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

    def _export_providers(self, world_id: uuid.UUID) -> list[WorldPackageProviderManifest]:
        providers = self._session.scalars(
            select(ProviderIntegration)
            .where(
                ProviderIntegration.world_id == world_id,
                ProviderIntegration.visibility.notin_(("hidden", "developer_only")),
            )
            .order_by(ProviderIntegration.provider_key)
        ).all()
        return [
            WorldPackageProviderManifest(
                provider_key=provider.provider_key,
                provider_kind=provider.provider_kind,
                adapter_kind=provider.adapter_kind,
                display_name=provider.display_name,
                auth_ref_configured=provider.auth_ref is not None,
                config=_safe_json(provider.config_json),
                default_params=_safe_json(provider.default_params_json),
                capabilities=tuple(self._provider_capabilities(provider.id)),
                status=provider.status,
                visibility=provider.visibility,
            )
            for provider in providers
        ]

    def _provider_capabilities(self, provider_id: uuid.UUID) -> list[str]:
        return list(
            self._session.scalars(
                select(ProviderCapability.capability_key)
                .where(ProviderCapability.provider_integration_id == provider_id)
                .order_by(ProviderCapability.capability_key)
            ).all()
        )

    def _export_personas(self, world_id: uuid.UUID) -> list[WorldPackagePersonaManifest]:
        rows = self._session.execute(
            select(Agent, AgentPersona)
            .join(AgentPersona, AgentPersona.agent_id == Agent.id)
            .where(Agent.world_id == world_id, AgentPersona.world_id == world_id)
            .order_by(Agent.agent_key)
        ).all()
        return [
            WorldPackagePersonaManifest(
                agent_key=agent.agent_key,
                display_name=agent.display_name,
                persona_summary=_summarize_text(persona.persona_text),
                character_profile=_safe_json(agent.character_profile),
                behavior_policy=_safe_json(persona.behavior_policy),
                enabled=persona.is_enabled,
            )
            for agent, persona in rows
        ]

    def _export_memories(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
    ) -> list[WorldPackageMemoryManifest]:
        rows = self._session.execute(
            select(AgentMemoryItem, Agent, Worldline)
            .join(Agent, Agent.id == AgentMemoryItem.agent_id)
            .outerjoin(Worldline, Worldline.id == AgentMemoryItem.worldline_id)
            .where(
                AgentMemoryItem.world_id == world_id,
                (
                    (AgentMemoryItem.worldline_id.is_(None))
                    | (AgentMemoryItem.worldline_id == worldline_id)
                ),
                AgentMemoryItem.is_active.is_(True),
            )
            .order_by(Agent.agent_key, AgentMemoryItem.created_at, AgentMemoryItem.id)
        ).all()
        return [
            WorldPackageMemoryManifest(
                agent_key=agent.agent_key,
                worldline_key=worldline.worldline_key if worldline is not None else None,
                memory_key=f"memory-{memory.id}",
                content_summary=_summarize_text(memory.content),
                metadata=_safe_json(memory.metadata_json),
                active=memory.is_active,
            )
            for memory, agent, worldline in rows
        ]

    def _export_visual_mappings(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
    ) -> list[WorldPackageVisualMappingManifest]:
        mappings: list[WorldPackageVisualMappingManifest] = []
        sprite_rows = self._session.execute(
            select(CharacterSpriteVariant, CharacterSpriteSet, Agent, MediaAsset)
            .join(CharacterSpriteSet, CharacterSpriteSet.id == CharacterSpriteVariant.sprite_set_id)
            .join(Agent, Agent.id == CharacterSpriteSet.agent_id)
            .join(MediaAsset, MediaAsset.id == CharacterSpriteVariant.asset_id)
            .where(
                CharacterSpriteVariant.world_id == world_id,
                CharacterSpriteVariant.worldline_id == worldline_id,
                CharacterSpriteVariant.visibility.notin_(("hidden", "developer_only")),
                CharacterSpriteSet.visibility.notin_(("hidden", "developer_only")),
                MediaAsset.visibility.notin_(("hidden", "developer_only")),
            )
            .order_by(Agent.agent_key, CharacterSpriteVariant.expression_key)
        ).all()
        for variant, sprite_set, agent, asset in sprite_rows:
            mappings.append(
                WorldPackageVisualMappingManifest(
                    mapping_kind="character_sprite",
                    worldline_key=self._worldline_key(variant.worldline_id),
                    agent_key=agent.agent_key,
                    package_asset_key=f"asset-{asset.id}",
                    role=variant.expression_key,
                    metadata=_safe_json(
                        {
                            "style_key": sprite_set.style_key,
                            "pose_key": variant.pose_key,
                            "outfit_key": variant.outfit_key,
                            "mood_tags": variant.mood_tags_json,
                            "is_default": variant.is_default,
                        }
                    ),
                )
            )
        background_rows = self._session.execute(
            select(SceneBackgroundProfile, Scene, MediaAsset)
            .outerjoin(Scene, Scene.id == SceneBackgroundProfile.scene_id)
            .join(MediaAsset, MediaAsset.id == SceneBackgroundProfile.asset_id)
            .where(
                SceneBackgroundProfile.world_id == world_id,
                SceneBackgroundProfile.worldline_id == worldline_id,
                SceneBackgroundProfile.visibility.notin_(("hidden", "developer_only")),
                MediaAsset.visibility.notin_(("hidden", "developer_only")),
            )
            .order_by(SceneBackgroundProfile.location_key, SceneBackgroundProfile.priority)
        ).all()
        for background, scene, asset in background_rows:
            mappings.append(
                WorldPackageVisualMappingManifest(
                    mapping_kind="scene_background",
                    worldline_key=self._worldline_key(background.worldline_id),
                    scene_key=scene.scene_key if scene is not None else None,
                    package_asset_key=f"asset-{asset.id}",
                    role=background.location_key,
                    metadata=_safe_json(
                        {
                            "time_of_day": background.time_of_day,
                            "weather_key": background.weather_key,
                            "is_default": background.is_default,
                        }
                    ),
                )
            )
        return mappings

    def _export_voice_mappings(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
    ) -> list[WorldPackageVoiceMappingManifest]:
        rows = self._session.execute(
            select(VoiceProfile, AgentVoiceProfileBinding, Agent, ProviderIntegration)
            .outerjoin(
                AgentVoiceProfileBinding,
                AgentVoiceProfileBinding.voice_profile_id == VoiceProfile.id,
            )
            .outerjoin(Agent, Agent.id == AgentVoiceProfileBinding.agent_id)
            .outerjoin(
                ProviderIntegration,
                ProviderIntegration.id == VoiceProfile.provider_integration_id,
            )
            .where(
                VoiceProfile.world_id == world_id,
                (
                    (VoiceProfile.worldline_id.is_(None))
                    | (VoiceProfile.worldline_id == worldline_id)
                ),
                VoiceProfile.visibility.notin_(("hidden", "developer_only")),
            )
            .order_by(VoiceProfile.profile_key)
        ).all()
        return [
            WorldPackageVoiceMappingManifest(
                worldline_key=(
                    self._worldline_key(voice.worldline_id)
                    if voice.worldline_id is not None
                    else None
                ),
                agent_key=agent.agent_key if agent is not None else None,
                voice_profile_key=voice.profile_key,
                display_name=voice.display_name,
                provider_key=provider.provider_key if provider is not None else None,
                provider_voice_id=voice.provider_voice_id,
                binding_role=binding.binding_role if binding is not None else None,
                style_overrides=(
                    _safe_json(binding.style_overrides_json) if binding is not None else {}
                ),
                metadata=_safe_json(voice.metadata_json),
            )
            for voice, binding, agent, provider in rows
        ]

    def _export_source_traceability(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        *,
        public_sample: bool,
    ) -> list[WorldPackageSourceTraceManifest]:
        rows = self._session.execute(
            select(
                AuthoringSourceBatch,
                AuthoringSourceAsset,
                AuthoringSourceFragment,
                AuthoringSourceTraceability,
                Worldline,
            )
            .join(AuthoringSourceAsset, AuthoringSourceAsset.batch_id == AuthoringSourceBatch.id)
            .outerjoin(
                AuthoringSourceFragment,
                AuthoringSourceFragment.source_asset_id == AuthoringSourceAsset.id,
            )
            .outerjoin(
                AuthoringSourceTraceability,
                AuthoringSourceTraceability.source_fragment_id == AuthoringSourceFragment.id,
            )
            .join(Worldline, Worldline.id == AuthoringSourceBatch.worldline_id)
            .where(
                AuthoringSourceBatch.world_id == world_id,
                AuthoringSourceBatch.worldline_id == worldline_id,
                AuthoringSourceBatch.status == "active",
            )
            .order_by(AuthoringSourceBatch.batch_key, AuthoringSourceAsset.source_label)
        ).all()
        manifests: list[WorldPackageSourceTraceManifest] = []
        seen: set[tuple[str, str, str | None, str | None]] = set()
        for batch, asset, _fragment, trace, worldline in rows:
            user_provided = _is_user_provided_source(batch, asset)
            key = (
                worldline.worldline_key,
                asset.source_label,
                asset.source_ref,
                trace.trace_kind if trace is not None else None,
            )
            if key in seen:
                continue
            seen.add(key)
            manifests.append(
                WorldPackageSourceTraceManifest(
                    worldline_key=worldline.worldline_key,
                    source_kind=asset.source_asset_kind,
                    source_label=asset.source_label,
                    source_ref=asset.source_ref,
                    trace_kind=trace.trace_kind if trace is not None else None,
                    applied_ref_kind=trace.applied_ref_kind if trace is not None else None,
                    metadata=_safe_json(
                        {
                            "batch_key": batch.batch_key,
                            "source_type": batch.metadata_json.get("source_type")
                            or asset.metadata_json.get("source_type"),
                            "public_sample_policy": (
                                "excluded_placeholder"
                                if public_sample and user_provided
                                else "safe_metadata_only"
                            ),
                        }
                    ),
                    excluded_from_public_sample=public_sample and user_provided,
                    exclusion_reason=(
                        "user-provided galgame source assets are excluded from public sample export"
                        if public_sample and user_provided
                        else None
                    ),
                )
            )
        return manifests

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
        provider_keys = {provider.provider_key for provider in manifest.providers}
        agent_keys = {persona.agent_key for persona in manifest.personas}
        asset_keys = {asset.package_asset_key for asset in manifest.media}
        scene_keys = {scene.scene_key for scene in manifest.scenes}
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
        for index, memory in enumerate(manifest.memories):
            if memory.worldline_key is not None and memory.worldline_key not in worldline_keys:
                issues.append(
                    _blocker(
                        "unknown_worldline",
                        f"memories[{index}].worldline_key",
                        "Memory manifest references a worldline key not present in the manifest.",
                    )
                )
            if agent_keys and memory.agent_key not in agent_keys:
                issues.append(
                    _warning(
                        "memory_agent_not_in_persona_manifest",
                        f"memories[{index}].agent_key",
                        "Memory manifest references an agent without a persona manifest.",
                    )
                )
        for index, mapping in enumerate(manifest.visual_mappings):
            if mapping.worldline_key not in worldline_keys:
                issues.append(
                    _blocker(
                        "unknown_worldline",
                        f"visual_mappings[{index}].worldline_key",
                        "Visual mapping references a worldline key not present in the manifest.",
                    )
                )
            if mapping.package_asset_key not in asset_keys:
                issues.append(
                    _blocker(
                        "unknown_media_asset",
                        f"visual_mappings[{index}].package_asset_key",
                        "Visual mapping references a media asset key not present in the manifest.",
                    )
                )
            if mapping.scene_key is not None and mapping.scene_key not in scene_keys:
                issues.append(
                    _warning(
                        "unknown_scene_reference",
                        f"visual_mappings[{index}].scene_key",
                        "Visual mapping references a scene key not present in the manifest.",
                    )
                )
        for index, voice_mapping in enumerate(manifest.voice_mappings):
            if (
                voice_mapping.worldline_key is not None
                and voice_mapping.worldline_key not in worldline_keys
            ):
                issues.append(
                    _blocker(
                        "unknown_worldline",
                        f"voice_mappings[{index}].worldline_key",
                        "Voice mapping references a worldline key not present in the manifest.",
                    )
                )
            if (
                voice_mapping.provider_key is not None
                and voice_mapping.provider_key not in provider_keys
            ):
                issues.append(
                    _warning(
                        "voice_provider_not_in_manifest",
                        f"voice_mappings[{index}].provider_key",
                        "Voice mapping references a provider not present in the manifest.",
                    )
                )
        for index, trace in enumerate(manifest.source_traceability):
            if trace.worldline_key not in worldline_keys:
                issues.append(
                    _blocker(
                        "unknown_worldline",
                        f"source_traceability[{index}].worldline_key",
                        (
                            "Source traceability references a worldline key not present "
                            "in the manifest."
                        ),
                    )
                )
            if trace.excluded_from_public_sample:
                issues.append(
                    _warning(
                        "proprietary_source_excluded",
                        f"source_traceability[{index}]",
                        (
                            "User-provided source content is represented by safe "
                            "placeholder metadata only."
                        ),
                    )
                )
        if self._world_slug_exists(f"imported-{manifest.world.slug}"):
            issues.append(
                _warning(
                    "duplicate_import_target",
                    "world.slug",
                    "A default imported slug already exists; apply should use an override slug.",
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


def _summarize_text(value: str, *, limit: int = 500) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 3].rstrip()}..."


def _has_extended_manifest_sections(manifest: WorldPackageManifest) -> bool:
    return any(
        (
            manifest.providers,
            manifest.personas,
            manifest.memories,
            manifest.visual_mappings,
            manifest.voice_mappings,
            manifest.source_traceability,
        )
    )


def _is_user_provided_source(
    batch: AuthoringSourceBatch,
    asset: AuthoringSourceAsset,
) -> bool:
    source_type = batch.metadata_json.get("source_type") or asset.metadata_json.get("source_type")
    if source_type == "already_unpacked_galgame":
        return True
    return bool(
        batch.metadata_json.get("user_provided")
        or asset.metadata_json.get("user_provided")
        or batch.metadata_json.get("proprietary")
        or asset.metadata_json.get("proprietary")
    )


def _is_user_provided_media(asset: MediaAsset) -> bool:
    source_type = asset.metadata_json.get("source_type")
    return bool(
        source_type == "already_unpacked_galgame"
        or asset.metadata_json.get("user_provided")
        or asset.metadata_json.get("proprietary")
    )


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
