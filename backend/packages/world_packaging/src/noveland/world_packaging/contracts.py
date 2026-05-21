from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SUPPORTED_MANIFEST_VERSION = "v0.8.7"
CHECKSUM_PATTERN = re.compile(r"^[a-f0-9]{64}$")
PACKAGE_KEY_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,79}$")
FORBIDDEN_KEYS = {
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
    "storage_uri",
    "preview_uri",
    "thumbnail_uri",
    "object_storage_path",
    "filesystem_path",
    "file_path",
    "path",
    "base64",
    "bytes",
    "raw_prompt",
    "raw_output",
    "prompt_snapshot",
}
FORBIDDEN_VALUE_MARKERS = (
    "media://",
    "file://",
    "s3://",
    "gs://",
    "storage_uri",
    "base64,",
    "raw_prompt",
    "raw_output",
    "/tmp/",
    "/root/",
    "api_key",
    "bearer ",
)


class WorldPackageIssueSeverity(StrEnum):
    BLOCKER = "blocker"
    WARNING = "warning"


class _FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True)


class WorldPackageIssue(_FrozenContract):
    severity: WorldPackageIssueSeverity
    code: str = Field(min_length=1, max_length=80)
    field: str = Field(min_length=1, max_length=240)
    message: str = Field(min_length=1, max_length=400)


class WorldPackageMetadata(_FrozenContract):
    manifest_version: str = SUPPORTED_MANIFEST_VERSION
    package_key: str = Field(min_length=1, max_length=80)
    generated_at: datetime
    capabilities: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("package_key", mode="after")
    @classmethod
    def validate_package_key(cls, value: str) -> str:
        normalized = value.strip().lower()
        if PACKAGE_KEY_PATTERN.fullmatch(normalized) is None:
            raise ValueError(
                "package_key must use lowercase letters, numbers, dashes, or underscores"
            )
        return normalized

    @field_validator("generated_at", mode="after")
    @classmethod
    def normalize_generated_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class WorldPackageWorldManifest(_FrozenContract):
    slug: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    memory_plugin_identifier: str | None = Field(default=None, max_length=120)
    memory_plugin_config: dict[str, Any] = Field(default_factory=dict)
    world_rules_plugin_identifier: str | None = Field(default=None, max_length=120)
    world_rules_plugin_config: dict[str, Any] = Field(default_factory=dict)
    rules_config: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True

    @field_validator(
        "memory_plugin_config",
        "world_rules_plugin_config",
        "rules_config",
        mode="after",
    )
    @classmethod
    def validate_config(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_safe_json(value)
        return value


class WorldPackageWorldlineManifest(_FrozenContract):
    worldline_key: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    status: str = Field(default="active", pattern="^(active|archived)$")
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata", mode="after")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_safe_json(value)
        return value


class WorldPackageSceneManifest(_FrozenContract):
    scene_key: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    region_key: str | None = Field(default=None, max_length=80)
    location_tags: tuple[str, ...] = Field(default_factory=tuple)
    opening_rules: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True

    @field_validator("opening_rules", mode="after")
    @classmethod
    def validate_opening_rules(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_safe_json(value)
        return value


class WorldPackageMediaObjectManifest(_FrozenContract):
    object_role: str = Field(min_length=1, max_length=40)
    mime_type: str = Field(min_length=1, max_length=120)
    size_bytes: int = Field(ge=0)
    checksum_sha256: str = Field(min_length=64, max_length=64)
    width: int | None = Field(default=None, ge=0)
    height: int | None = Field(default=None, ge=0)
    duration_ms: int | None = Field(default=None, ge=0)
    sample_rate_hz: int | None = Field(default=None, ge=0)
    audio_channels: int | None = Field(default=None, ge=0)

    @field_validator("checksum_sha256", mode="after")
    @classmethod
    def validate_checksum(cls, value: str) -> str:
        if CHECKSUM_PATTERN.fullmatch(value) is None:
            raise ValueError("checksum_sha256 must be a lowercase 64-character SHA-256 hex digest")
        return value


class WorldPackageMediaReferenceManifest(_FrozenContract):
    ref_kind: str = Field(min_length=1, max_length=40)
    ref_key: str = Field(min_length=1, max_length=160)
    ref_role: str = Field(min_length=1, max_length=40)
    display_order: int = Field(default=0, ge=0)


class WorldPackageMediaManifest(_FrozenContract):
    package_asset_key: str = Field(min_length=1, max_length=120)
    worldline_key: str = Field(min_length=1, max_length=80)
    asset_kind: str = Field(min_length=1, max_length=16)
    asset_role: str = Field(min_length=1, max_length=40)
    source_kind: str = Field(default="imported_original", min_length=1, max_length=40)
    status: str = Field(default="registered", min_length=1, max_length=16)
    visibility: str = Field(default="world_admin", min_length=1, max_length=32)
    mime_type: str | None = Field(default=None, max_length=120)
    size_bytes: int | None = Field(default=None, ge=0)
    checksum_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    title: str | None = Field(default=None, max_length=160)
    description: str | None = None
    objects: tuple[WorldPackageMediaObjectManifest, ...] = Field(default_factory=tuple)
    references: tuple[WorldPackageMediaReferenceManifest, ...] = Field(default_factory=tuple)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("checksum_sha256", mode="after")
    @classmethod
    def validate_optional_checksum(cls, value: str | None) -> str | None:
        if value is not None and CHECKSUM_PATTERN.fullmatch(value) is None:
            raise ValueError("checksum_sha256 must be a lowercase 64-character SHA-256 hex digest")
        return value

    @field_validator("metadata", mode="after")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_safe_json(value)
        return value


class WorldPackageProviderManifest(_FrozenContract):
    provider_key: str = Field(min_length=1, max_length=120)
    provider_kind: str = Field(min_length=1, max_length=40)
    adapter_kind: str = Field(min_length=1, max_length=40)
    display_name: str = Field(min_length=1, max_length=200)
    auth_ref_configured: bool = False
    config: dict[str, Any] = Field(default_factory=dict)
    default_params: dict[str, Any] = Field(default_factory=dict)
    capabilities: tuple[str, ...] = Field(default_factory=tuple)
    status: str = Field(default="active", min_length=1, max_length=24)
    visibility: str = Field(default="world_admin", min_length=1, max_length=32)

    @field_validator("config", "default_params", mode="after")
    @classmethod
    def validate_provider_json(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_safe_json(value)
        return value


class WorldPackagePersonaManifest(_FrozenContract):
    agent_key: str = Field(min_length=1, max_length=80)
    display_name: str = Field(min_length=1, max_length=120)
    persona_summary: str | None = Field(default=None, max_length=500)
    character_profile: dict[str, Any] = Field(default_factory=dict)
    behavior_policy: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True

    @field_validator("character_profile", "behavior_policy", mode="after")
    @classmethod
    def validate_persona_json(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_safe_json(value)
        return value


class WorldPackageMemoryManifest(_FrozenContract):
    agent_key: str = Field(min_length=1, max_length=80)
    worldline_key: str | None = Field(default=None, max_length=80)
    memory_key: str = Field(min_length=1, max_length=160)
    content_summary: str = Field(min_length=1, max_length=500)
    metadata: dict[str, Any] = Field(default_factory=dict)
    active: bool = True

    @field_validator("metadata", mode="after")
    @classmethod
    def validate_memory_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_safe_json(value)
        return value


class WorldPackageVisualMappingManifest(_FrozenContract):
    mapping_kind: str = Field(min_length=1, max_length=40)
    worldline_key: str = Field(min_length=1, max_length=80)
    agent_key: str | None = Field(default=None, max_length=80)
    scene_key: str | None = Field(default=None, max_length=80)
    package_asset_key: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=80)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata", mode="after")
    @classmethod
    def validate_visual_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_safe_json(value)
        return value


class WorldPackageVoiceMappingManifest(_FrozenContract):
    worldline_key: str | None = Field(default=None, max_length=80)
    agent_key: str | None = Field(default=None, max_length=80)
    voice_profile_key: str = Field(min_length=1, max_length=120)
    display_name: str = Field(min_length=1, max_length=200)
    provider_key: str | None = Field(default=None, max_length=120)
    provider_voice_id: str | None = Field(default=None, max_length=200)
    binding_role: str | None = Field(default=None, max_length=32)
    style_overrides: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("style_overrides", "metadata", mode="after")
    @classmethod
    def validate_voice_json(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_safe_json(value)
        return value


class WorldPackageSourceTraceManifest(_FrozenContract):
    worldline_key: str = Field(min_length=1, max_length=80)
    source_kind: str = Field(min_length=1, max_length=40)
    source_label: str = Field(min_length=1, max_length=160)
    source_ref: str | None = Field(default=None, max_length=240)
    trace_kind: str | None = Field(default=None, max_length=40)
    applied_ref_kind: str | None = Field(default=None, max_length=60)
    metadata: dict[str, Any] = Field(default_factory=dict)
    excluded_from_public_sample: bool = False
    exclusion_reason: str | None = Field(default=None, max_length=240)

    @field_validator("metadata", mode="after")
    @classmethod
    def validate_source_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_safe_json(value)
        return value


class WorldPackageManifest(_FrozenContract):
    metadata: WorldPackageMetadata
    world: WorldPackageWorldManifest
    worldlines: tuple[WorldPackageWorldlineManifest, ...]
    scenes: tuple[WorldPackageSceneManifest, ...] = Field(default_factory=tuple)
    media: tuple[WorldPackageMediaManifest, ...] = Field(default_factory=tuple)
    providers: tuple[WorldPackageProviderManifest, ...] = Field(default_factory=tuple)
    personas: tuple[WorldPackagePersonaManifest, ...] = Field(default_factory=tuple)
    memories: tuple[WorldPackageMemoryManifest, ...] = Field(default_factory=tuple)
    visual_mappings: tuple[WorldPackageVisualMappingManifest, ...] = Field(default_factory=tuple)
    voice_mappings: tuple[WorldPackageVoiceMappingManifest, ...] = Field(default_factory=tuple)
    source_traceability: tuple[WorldPackageSourceTraceManifest, ...] = Field(
        default_factory=tuple
    )

    @model_validator(mode="after")
    def validate_manifest_shape(self) -> WorldPackageManifest:
        if not self.worldlines:
            raise ValueError("manifest must include at least one worldline")
        worldline_keys = [worldline.worldline_key for worldline in self.worldlines]
        if len(worldline_keys) != len(set(worldline_keys)):
            raise ValueError("worldline keys must be unique")
        scene_keys = [scene.scene_key for scene in self.scenes]
        if len(scene_keys) != len(set(scene_keys)):
            raise ValueError("scene keys must be unique")
        asset_keys = [asset.package_asset_key for asset in self.media]
        if len(asset_keys) != len(set(asset_keys)):
            raise ValueError("media asset package keys must be unique")
        provider_keys = [provider.provider_key for provider in self.providers]
        if len(provider_keys) != len(set(provider_keys)):
            raise ValueError("provider keys must be unique")
        return self


class WorldPackageExportRequest(_FrozenContract):
    worldline_id: uuid.UUID | None = None
    package_key: str | None = Field(default=None, min_length=1, max_length=80)
    include_media: bool = True
    include_extended_manifests: bool = True
    public_sample: bool = False


class WorldPackageImportPreviewRequest(_FrozenContract):
    manifest: WorldPackageManifest


class WorldPackageApplyRequest(_FrozenContract):
    manifest: WorldPackageManifest
    slug: str | None = Field(default=None, min_length=1, max_length=80)
    name: str | None = Field(default=None, min_length=1, max_length=160)


class WorldPackagePreviewResult(_FrozenContract):
    manifest: WorldPackageManifest
    issues: tuple[WorldPackageIssue, ...]
    blocker_count: int
    warning_count: int
    creates_world: bool
    creates_scene_count: int
    creates_media_asset_count: int
    provider_manifest_count: int = 0
    persona_manifest_count: int = 0
    memory_manifest_count: int = 0
    visual_mapping_count: int = 0
    voice_mapping_count: int = 0
    source_traceability_count: int = 0
    provider_execution: bool = False
    world_event_writes: bool = False


class WorldPackageApplyResult(_FrozenContract):
    preview: WorldPackagePreviewResult
    applied: bool
    created_world_id: uuid.UUID | None = None
    created_worldline_ids: tuple[uuid.UUID, ...] = Field(default_factory=tuple)
    created_scene_ids: tuple[uuid.UUID, ...] = Field(default_factory=tuple)
    created_media_asset_ids: tuple[uuid.UUID, ...] = Field(default_factory=tuple)
    provider_execution: bool = False
    world_event_writes: bool = False


def _assert_safe_json(value: Any) -> None:
    _scan_safe_json(value, "$")
    json.dumps(value)


def _scan_safe_json(value: Any, path: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower()
            if normalized in FORBIDDEN_KEYS:
                raise ValueError(f"forbidden package manifest key at {path}.{key}")
            _scan_safe_json(child, f"{path}.{key}")
        return
    if isinstance(value, list | tuple):
        for index, child in enumerate(value):
            _scan_safe_json(child, f"{path}[{index}]")
        return
    if isinstance(value, str):
        normalized = value.lower()
        if any(marker in normalized for marker in FORBIDDEN_VALUE_MARKERS):
            raise ValueError(f"forbidden package manifest value at {path}")
