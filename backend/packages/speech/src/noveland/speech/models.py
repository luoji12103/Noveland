from __future__ import annotations

import uuid
from typing import Any

from noveland.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin
from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class VoiceProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "voice_profiles"
    __table_args__ = (
        UniqueConstraint("world_id", "worldline_id", "profile_key", name="uq_voice_profiles_key"),
        CheckConstraint("status IN ('active', 'disabled', 'deleted')", name="status"),
        CheckConstraint(
            "visibility IN ('private', 'world_admin', 'world_member', 'developer_only', 'hidden')",
            name="visibility",
        ),
        CheckConstraint(
            "owner_kind IN ('world', 'agent', 'user', 'provider', 'other')",
            name="owner_kind",
        ),
        CheckConstraint(
            "voice_kind IN ("
            "'preset', 'cloned', 'designed', 'imported', 'generated', "
            "'external_provider', 'other'"
            ")",
            name="voice_kind",
        ),
        CheckConstraint(
            "consent_status IN ("
            "'not_required', 'user_owned_or_authorized', 'admin_authorized', "
            "'pending_review', 'restricted', 'unknown'"
            ")",
            name="consent_status",
        ),
        Index("ix_voice_profiles_worldline_status", "world_id", "worldline_id", "status"),
        Index("ix_voice_profiles_owner_agent", "owner_agent_id"),
        Index("ix_voice_profiles_provider", "provider_integration_id"),
        Index("ix_voice_profiles_reference_asset", "reference_asset_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=True,
    )
    profile_key: Mapped[str] = mapped_column(String(120), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        server_default=text("'active'"),
        default="active",
    )
    visibility: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'world_admin'"),
        default="world_admin",
    )
    owner_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    owner_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )
    provider_integration_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("provider_integrations.id", ondelete="SET NULL"),
        nullable=True,
    )
    provider_voice_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    default_language: Mapped[str | None] = mapped_column(String(40), nullable=True)
    supported_languages_json: Mapped[list[str]] = mapped_column(
        "supported_languages",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=list,
    )
    voice_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    reference_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    consent_status: Mapped[str] = mapped_column(String(40), nullable=False)
    usage_policy_json: Mapped[dict[str, Any]] = mapped_column(
        "usage_policy",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )


class AgentVoiceProfileBinding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_voice_profile_bindings"
    __table_args__ = (
        CheckConstraint(
            "binding_role IN ("
            "'default', 'narration', 'inner_voice', 'phone_call', "
            "'disguise', 'alternate', 'other'"
            ")",
            name="binding_role",
        ),
        CheckConstraint("priority >= 0", name="priority_nonnegative"),
        UniqueConstraint(
            "world_id",
            "worldline_id",
            "agent_id",
            "voice_profile_id",
            "binding_role",
            name="uq_agent_voice_profile_bindings_role",
        ),
        Index("ix_agent_voice_profile_bindings_agent", "world_id", "worldline_id", "agent_id"),
        Index("ix_agent_voice_profile_bindings_profile", "voice_profile_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=True,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    voice_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("voice_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    binding_role: Mapped[str] = mapped_column(String(32), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    style_overrides_json: Mapped[dict[str, Any]] = mapped_column(
        "style_overrides",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )


class SpeechTranscript(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "speech_transcripts"
    __table_args__ = (
        CheckConstraint("status IN ('available', 'failed', 'deleted')", name="status"),
        CheckConstraint(
            "visibility IN ('private', 'world_admin', 'world_member', 'developer_only', 'hidden')",
            name="visibility",
        ),
        Index("ix_speech_transcripts_worldline_created", "world_id", "worldline_id", "created_at"),
        Index("ix_speech_transcripts_source_asset", "source_asset_id"),
        Index("ix_speech_transcripts_media_job", "media_job_id"),
        Index("ix_speech_transcripts_invocation", "model_invocation_id"),
        Index("ix_speech_transcripts_turn", "conversation_id", "turn_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("media_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    media_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    model_invocation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("model_invocations.id", ondelete="SET NULL"),
        nullable=True,
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("conversation_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    turn_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("conversation_turns.id", ondelete="SET NULL"),
        nullable=True,
    )
    speaker_actor_ref: Mapped[str | None] = mapped_column(String(160), nullable=True)
    language: Mapped[str | None] = mapped_column(String(40), nullable=True)
    transcript_text: Mapped[str] = mapped_column(Text, nullable=False)
    segments_json: Mapped[list[dict[str, Any]] | None] = mapped_column(
        "segments",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=True,
    )
    confidence_json: Mapped[dict[str, Any] | None] = mapped_column(
        "confidence",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        server_default=text("'available'"),
        default="available",
    )
    visibility: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'world_admin'"),
        default="world_admin",
    )


class SpeechStyleMapping(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "speech_style_mappings"
    __table_args__ = (
        UniqueConstraint(
            "world_id",
            "mapping_key",
            "provider_kind",
            "emotion_key",
            name="uq_speech_style_mappings_key",
        ),
        Index("ix_speech_style_mappings_world_provider", "world_id", "provider_kind"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    mapping_key: Mapped[str] = mapped_column(String(120), nullable=False)
    provider_kind: Mapped[str] = mapped_column(String(80), nullable=False)
    emotion_key: Mapped[str] = mapped_column(String(80), nullable=False)
    style_json: Mapped[dict[str, Any]] = mapped_column(
        "style",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
