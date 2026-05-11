from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from noveland.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class MediaAsset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "media_assets"
    __table_args__ = (
        CheckConstraint(
            "asset_kind IN ('image', 'audio', 'video', 'document', 'other')",
            name="asset_kind",
        ),
        CheckConstraint(
            "asset_role IN ("
            "'original_image', 'reference_image', 'mask_image', 'transparent_png', "
            "'composite_image', 'scene_background', 'character_sprite', "
            "'character_expression', 'character_pose', 'event_cg', 'speech_audio', "
            "'voice_file', 'voice_sample', 'transcript_audio', 'video_clip', "
            "'document', 'thumbnail', 'other'"
            ")",
            name="asset_role",
        ),
        CheckConstraint(
            "source_kind IN ("
            "'provider_generated', 'manual_upload', 'imported_original', "
            "'composed', 'background_removed', 'cropped', 'converted', "
            "'system_generated', 'test_fixture', 'other'"
            ")",
            name="source_kind",
        ),
        CheckConstraint(
            "status IN ('registered', 'available', 'failed', 'deleted')",
            name="status",
        ),
        CheckConstraint(
            "visibility IN ("
            "'private', 'world_admin', 'world_member', 'player_visible', "
            "'reader_visible', 'developer_only', 'hidden'"
            ")",
            name="visibility",
        ),
        CheckConstraint("size_bytes IS NULL OR size_bytes >= 0", name="size_bytes_nonnegative"),
        CheckConstraint("width IS NULL OR width >= 0", name="width_nonnegative"),
        CheckConstraint("height IS NULL OR height >= 0", name="height_nonnegative"),
        CheckConstraint("duration_ms IS NULL OR duration_ms >= 0", name="duration_ms_nonnegative"),
        CheckConstraint(
            "sample_rate_hz IS NULL OR sample_rate_hz >= 0",
            name="sample_rate_hz_nonnegative",
        ),
        CheckConstraint(
            "audio_channels IS NULL OR audio_channels >= 0",
            name="audio_channels_nonnegative",
        ),
        Index("ix_media_assets_worldline_created", "world_id", "worldline_id", "created_at"),
        Index(
            "ix_media_assets_worldline_kind_role",
            "world_id",
            "worldline_id",
            "asset_kind",
            "asset_role",
        ),
        Index("ix_media_assets_worldline_status", "world_id", "worldline_id", "status"),
        Index("ix_media_assets_source_job_id", "source_job_id"),
        Index("ix_media_assets_source_event_id", "source_event_id"),
        Index("ix_media_assets_source_invocation_id", "source_invocation_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    asset_role: Mapped[str] = mapped_column(String(40), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=text("'registered'"),
        default="registered",
    )
    visibility: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'private'"),
        default="private",
    )
    storage_uri: Mapped[str | None] = mapped_column(String(500), nullable=True)
    preview_uri: Mapped[str | None] = mapped_column(String(500), nullable=True)
    thumbnail_uri: Mapped[str | None] = mapped_column(String(500), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    file_ext: Mapped[str | None] = mapped_column(String(20), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sample_rate_hz: Mapped[int | None] = mapped_column(Integer, nullable=True)
    audio_channels: Mapped[int | None] = mapped_column(Integer, nullable=True)
    has_alpha: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    color_mode: Mapped[str | None] = mapped_column(String(40), nullable=True)
    provider_kind: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("world_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_invocation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("model_invocations.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str | None] = mapped_column(String(160), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_actor_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )


class MediaJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "media_jobs"
    __table_args__ = (
        CheckConstraint(
            "job_kind IN ("
            "'image_generation', 'image_edit', 'speech_generation', "
            "'speech_transcription', 'background_removal', 'composition', "
            "'upload_import', 'vision_analysis', 'transcode', 'thumbnail', "
            "'import', 'other'"
            ")",
            name="job_kind",
        ),
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')",
            name="status",
        ),
        CheckConstraint("priority >= 0", name="priority_nonnegative"),
        Index("ix_media_jobs_worldline_created", "world_id", "worldline_id", "created_at"),
        Index("ix_media_jobs_worldline_status", "world_id", "worldline_id", "status"),
        Index("ix_media_jobs_context", "world_id", "worldline_id", "conversation_id", "turn_id"),
        Index("ix_media_jobs_agent_id", "agent_id"),
        Index("ix_media_jobs_source_event_id", "source_event_id"),
        Index("ix_media_jobs_source_invocation_id", "source_invocation_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("conversation_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    turn_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("conversation_turns.id", ondelete="SET NULL"),
        nullable=True,
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )
    job_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    provider_kind: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=text("'queued'"),
        default="queued",
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
        default=0,
    )
    cancel_policy: Mapped[str | None] = mapped_column(String(40), nullable=True)
    deadline_hint: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dedupe_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
    invalidation_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
    source_event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("world_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_invocation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("model_invocations.id", ondelete="SET NULL"),
        nullable=True,
    )
    provider_config_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    request_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    result_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_actor_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MediaObject(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "media_objects"
    __table_args__ = (
        UniqueConstraint("storage_uri", name="uq_media_objects_storage_uri"),
        CheckConstraint(
            "object_role IN ("
            "'original', 'primary', 'thumbnail', 'preview', 'mask', 'alpha', "
            "'transparent', 'composed', 'waveform', 'transcript_source', "
            "'derived', 'other'"
            ")",
            name="object_role",
        ),
        CheckConstraint("size_bytes >= 0", name="size_bytes_nonnegative"),
        CheckConstraint("width IS NULL OR width >= 0", name="width_nonnegative"),
        CheckConstraint("height IS NULL OR height >= 0", name="height_nonnegative"),
        CheckConstraint("duration_ms IS NULL OR duration_ms >= 0", name="duration_ms_nonnegative"),
        CheckConstraint(
            "sample_rate_hz IS NULL OR sample_rate_hz >= 0",
            name="sample_rate_hz_nonnegative",
        ),
        CheckConstraint(
            "audio_channels IS NULL OR audio_channels >= 0",
            name="audio_channels_nonnegative",
        ),
        CheckConstraint("frame_rate IS NULL OR frame_rate >= 0", name="frame_rate_nonnegative"),
        Index("ix_media_objects_worldline_created", "world_id", "worldline_id", "created_at"),
        Index("ix_media_objects_asset_role", "asset_id", "object_role"),
        Index("ix_media_objects_checksum", "checksum_sha256"),
    )

    asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("media_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    object_role: Mapped[str] = mapped_column(String(40), nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(500), nullable=False)
    filename: Mapped[str | None] = mapped_column(String(220), nullable=True)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sample_rate_hz: Mapped[int | None] = mapped_column(Integer, nullable=True)
    audio_channels: Mapped[int | None] = mapped_column(Integer, nullable=True)
    frame_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )


class MediaReference(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "media_references"
    __table_args__ = (
        UniqueConstraint(
            "world_id",
            "worldline_id",
            "asset_id",
            "ref_kind",
            "ref_id",
            "ref_role",
            name="uq_media_references_identity",
        ),
        CheckConstraint(
            "ref_kind IN ("
            "'conversation_turn', 'conversation_session', 'world_event', "
            "'narrative_artifact', 'agent', 'scene', 'world', "
            "'model_invocation', 'media_job', 'memory_write_job', 'other'"
            ")",
            name="ref_kind",
        ),
        CheckConstraint(
            "ref_role IN ("
            "'attachment', 'input', 'output', 'evidence', 'preview', 'thumbnail', "
            "'background', 'foreground', 'character_sprite', 'voice_reference', "
            "'source', 'derived_from', 'other'"
            ")",
            name="ref_role",
        ),
        CheckConstraint("display_order >= 0", name="display_order_nonnegative"),
        Index("ix_media_references_worldline_created", "world_id", "worldline_id", "created_at"),
        Index("ix_media_references_asset_id", "asset_id"),
        Index("ix_media_references_target", "world_id", "worldline_id", "ref_kind", "ref_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("media_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    ref_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    ref_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    ref_role: Mapped[str] = mapped_column(String(40), nullable=False)
    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
        default=0,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )


class MediaAssetContext(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "media_asset_contexts"
    __table_args__ = (
        CheckConstraint(
            "context_role IN ('source', 'attachment', 'preview', 'output', "
            "'evidence', 'reference')",
            name="context_role",
        ),
        CheckConstraint(
            "conversation_id IS NOT NULL OR turn_id IS NOT NULL OR agent_id IS NOT NULL OR "
            "world_event_id IS NOT NULL OR narrative_artifact_id IS NOT NULL",
            name="context_ref_present",
        ),
        Index(
            "ix_media_asset_contexts_worldline_created",
            "world_id",
            "worldline_id",
            "created_at",
        ),
        Index("ix_media_asset_contexts_asset_id", "asset_id"),
        Index("ix_media_asset_contexts_conversation_id", "conversation_id"),
        Index("ix_media_asset_contexts_turn_id", "turn_id"),
        Index("ix_media_asset_contexts_agent_id", "agent_id"),
        Index("ix_media_asset_contexts_world_event_id", "world_event_id"),
        Index("ix_media_asset_contexts_narrative_artifact_id", "narrative_artifact_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("media_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("conversation_sessions.id", ondelete="CASCADE"),
        nullable=True,
    )
    turn_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("conversation_turns.id", ondelete="CASCADE"),
        nullable=True,
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=True,
    )
    world_event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("world_events.id", ondelete="CASCADE"),
        nullable=True,
    )
    narrative_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("narrative_artifacts.id", ondelete="CASCADE"),
        nullable=True,
    )
    context_role: Mapped[str] = mapped_column(String(32), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )


class MediaAssetInput(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "media_asset_inputs"
    __table_args__ = (
        UniqueConstraint(
            "output_asset_id",
            "input_asset_id",
            "input_role",
            "display_order",
            name="uq_media_asset_inputs_output_input_role_order",
        ),
        CheckConstraint(
            "input_role IN ('source', 'reference', 'mask', 'background', 'layer', 'audio_source')",
            name="input_role",
        ),
        CheckConstraint("display_order >= 0", name="display_order_nonnegative"),
        CheckConstraint("output_asset_id <> input_asset_id", name="distinct_assets"),
        Index("ix_media_asset_inputs_worldline_created", "world_id", "worldline_id", "created_at"),
        Index("ix_media_asset_inputs_output_asset_id", "output_asset_id"),
        Index("ix_media_asset_inputs_input_asset_id", "input_asset_id"),
        Index("ix_media_asset_inputs_source_job_id", "source_job_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    output_asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("media_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    input_asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("media_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    input_role: Mapped[str] = mapped_column(String(32), nullable=False)
    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
        default=0,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )


class MediaAssetTag(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "media_asset_tags"
    __table_args__ = (
        UniqueConstraint(
            "world_id",
            "worldline_id",
            "asset_id",
            "tag_type",
            "tag_key",
            "tag_value",
            name="uq_media_asset_tags_identity",
        ),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
        CheckConstraint(
            "source_kind IN ('manual', 'imported', 'system', 'provider', 'derived')",
            name="source_kind",
        ),
        CheckConstraint(
            "visibility IN ("
            "'private', 'world_admin', 'world_member', 'player_visible', "
            "'reader_visible', 'developer_only', 'hidden'"
            ")",
            name="visibility",
        ),
        Index(
            "ix_media_asset_tags_worldline_tag",
            "world_id",
            "worldline_id",
            "tag_type",
            "tag_key",
            "tag_value",
        ),
        Index("ix_media_asset_tags_worldline_visibility", "world_id", "worldline_id", "visibility"),
        Index("ix_media_asset_tags_asset_id", "asset_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("media_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    tag_type: Mapped[str] = mapped_column(String(40), nullable=False)
    tag_key: Mapped[str] = mapped_column(String(80), nullable=False)
    tag_value: Mapped[str] = mapped_column(String(220), nullable=False)
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default=text("1.0"),
        default=1.0,
    )
    source_kind: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        server_default=text("'manual'"),
        default="manual",
    )
    visibility: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'world_admin'"),
        default="world_admin",
    )
    created_by_actor_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )


class MediaAssetCollection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "media_asset_collections"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'deleted')",
            name="status",
        ),
        CheckConstraint(
            "visibility IN ("
            "'private', 'world_admin', 'world_member', 'player_visible', "
            "'reader_visible', 'developer_only', 'hidden'"
            ")",
            name="visibility",
        ),
        Index(
            "ix_media_asset_collections_worldline_kind",
            "world_id",
            "worldline_id",
            "collection_kind",
        ),
        Index(
            "ix_media_asset_collections_worldline_visibility",
            "world_id",
            "worldline_id",
            "visibility",
        ),
        Index(
            "ix_media_asset_collections_worldline_status_created",
            "world_id",
            "worldline_id",
            "status",
            "created_at",
        ),
        Index("ix_media_asset_collections_owner_agent_id", "owner_agent_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    collection_kind: Mapped[str] = mapped_column(String(60), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )
    visibility: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'world_admin'"),
        default="world_admin",
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=text("'active'"),
        default="active",
    )
    created_by_actor_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )


class MediaAssetCollectionItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "media_asset_collection_items"
    __table_args__ = (
        UniqueConstraint(
            "collection_id",
            "asset_id",
            "role",
            name="uq_media_asset_collection_items_collection_asset_role",
        ),
        CheckConstraint("display_order >= 0", name="display_order_nonnegative"),
        Index(
            "ix_media_asset_collection_items_collection_order",
            "collection_id",
            "display_order",
        ),
        Index("ix_media_asset_collection_items_asset_id", "asset_id"),
        Index(
            "ix_media_asset_collection_items_worldline_asset",
            "world_id",
            "worldline_id",
            "asset_id",
        ),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    collection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("media_asset_collections.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("media_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(40), nullable=False)
    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
        default=0,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
