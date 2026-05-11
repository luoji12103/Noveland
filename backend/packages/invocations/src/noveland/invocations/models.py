from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from noveland.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin
from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


def _json_column() -> JSONB | JSON:
    return JSONB().with_variant(JSON(), "sqlite")


INVOCATION_KIND_CHECK = (
    "'agent_runtime', 'conversation_turn', 'narrative_generation', 'gm_generation', "
    "'eval', 'image_generation', 'image_edit', 'image_analysis', 'speech_to_text', "
    "'text_to_speech', 'voice_clone', 'tool_planning', 'repair', 'critique', 'other'"
)
ACTOR_KIND_CHECK = (
    "'system', 'platform_admin', 'world_admin', 'agent', 'player', 'runtime', 'service'"
)
PROVIDER_KIND_CHECK = (
    "'openai_compatible', 'anthropic_compatible', 'openai_image', 'openai_audio', "
    "'custom_http', 'comfyui', 'mimo_tts', 'mimo_asr', 'omnivoice', 'gpt_sovits', "
    "'local_stub', 'other'"
)
INVOCATION_STATUS_CHECK = "'pending', 'running', 'succeeded', 'failed', 'cancelled', 'redacted'"
VISIBILITY_CHECK = "'private', 'world_admin', 'developer_only', 'hidden'"
REDACTION_STATUS_CHECK = "'raw', 'redacted', 'hidden', 'checksum_only'"
RETENTION_POLICY_CHECK = (
    "'local_debug', 'short_term', 'long_term', 'eval_only', 'purge_after_days'"
)
PROMPT_TEMPLATE_SCOPE_CHECK = "'global', 'world'"
PROMPT_TEMPLATE_STATUS_CHECK = "'draft', 'active', 'deprecated', 'archived'"
INVOCATION_ROLE_CHECK = (
    "'primary', 'retry', 'fallback', 'repair', 'critique', 'tool_planning', "
    "'vision_analysis', 'image_generation', 'speech_generation', 'other'"
)


class ModelInvocation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "model_invocations"
    __table_args__ = (
        CheckConstraint(f"invocation_kind IN ({INVOCATION_KIND_CHECK})", name="invocation_kind"),
        CheckConstraint(f"actor_kind IN ({ACTOR_KIND_CHECK})", name="actor_kind"),
        CheckConstraint(f"provider_kind IN ({PROVIDER_KIND_CHECK})", name="provider_kind"),
        CheckConstraint(f"status IN ({INVOCATION_STATUS_CHECK})", name="status"),
        CheckConstraint(f"visibility IN ({VISIBILITY_CHECK})", name="visibility"),
        CheckConstraint(
            f"redaction_status IN ({REDACTION_STATUS_CHECK})",
            name="redaction_status",
        ),
        CheckConstraint(
            f"retention_policy IN ({RETENTION_POLICY_CHECK})",
            name="retention_policy",
        ),
        CheckConstraint("latency_ms IS NULL OR latency_ms >= 0", name="latency_nonnegative"),
        CheckConstraint(
            "estimated_cost IS NULL OR estimated_cost >= 0",
            name="estimated_cost_nonnegative",
        ),
        Index("ix_model_invocations_worldline_created", "world_id", "worldline_id", "created_at"),
        Index(
            "ix_model_invocations_worldline_kind",
            "world_id",
            "worldline_id",
            "invocation_kind",
        ),
        Index(
            "ix_model_invocations_worldline_status",
            "world_id",
            "worldline_id",
            "status",
        ),
        Index("ix_model_invocations_trace", "trace_id"),
        Index("ix_model_invocations_parent", "parent_invocation_id"),
        Index(
            "ix_model_invocations_provider_model",
            "world_id",
            "worldline_id",
            "provider_kind",
            "model_name",
        ),
        Index("ix_model_invocations_agent", "world_id", "worldline_id", "agent_id"),
        Index(
            "ix_model_invocations_conversation_turn",
            "world_id",
            "worldline_id",
            "conversation_id",
            "turn_id",
        ),
        Index(
            "ix_model_invocations_media",
            "world_id",
            "worldline_id",
            "media_job_id",
            "media_asset_id",
        ),
        Index(
            "ix_model_invocations_memory_job",
            "world_id",
            "worldline_id",
            "memory_write_job_id",
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
    trace_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    parent_invocation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("model_invocations.id", ondelete="SET NULL"),
        nullable=True,
    )
    invocation_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    actor_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_ref: Mapped[str | None] = mapped_column(String(160), nullable=True)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"),
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
    world_event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("world_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    media_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    media_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    memory_write_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("memory_write_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    provider_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    provider_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("provider_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    model_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    prompt_template_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    prompt_template_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_json: Mapped[dict[str, Any] | None] = mapped_column(_json_column(), nullable=True)
    output_json: Mapped[dict[str, Any] | None] = mapped_column(_json_column(), nullable=True)
    request_params_json: Mapped[dict[str, Any] | None] = mapped_column(
        _json_column(),
        nullable=True,
    )
    response_metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        _json_column(),
        nullable=True,
    )
    usage_json: Mapped[dict[str, Any] | None] = mapped_column(_json_column(), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    visibility: Mapped[str] = mapped_column(String(32), nullable=False)
    redaction_status: Mapped[str] = mapped_column(String(24), nullable=False)
    retention_policy: Mapped[str] = mapped_column(String(32), nullable=False)
    contains_sensitive_context: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
        default=False,
    )
    purge_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PromptTemplate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "prompt_templates"
    __table_args__ = (
        UniqueConstraint("scope_key", "template_key", "version", name="uq_prompt_templates_key"),
        CheckConstraint(f"scope_kind IN ({PROMPT_TEMPLATE_SCOPE_CHECK})", name="scope_kind"),
        CheckConstraint(f"invocation_kind IN ({INVOCATION_KIND_CHECK})", name="invocation_kind"),
        CheckConstraint(f"status IN ({PROMPT_TEMPLATE_STATUS_CHECK})", name="status"),
        CheckConstraint(
            "(scope_kind = 'global' AND world_id IS NULL AND scope_key = 'global') OR "
            "(scope_kind = 'world' AND world_id IS NOT NULL)",
            name="scope_consistency",
        ),
        CheckConstraint("version > 0", name="version_positive"),
        Index("ix_prompt_templates_scope_status", "scope_kind", "world_id", "status"),
        Index("ix_prompt_templates_key_status", "template_key", "invocation_kind", "status"),
    )

    scope_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    world_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=True,
    )
    scope_key: Mapped[str] = mapped_column(String(120), nullable=False)
    template_key: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    invocation_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    input_schema_json: Mapped[dict[str, Any] | None] = mapped_column(_json_column(), nullable=True)
    output_schema_json: Mapped[dict[str, Any] | None] = mapped_column(_json_column(), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        _json_column(),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)


class PromptSnapshot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "prompt_snapshots"
    __table_args__ = (
        CheckConstraint(f"visibility IN ({VISIBILITY_CHECK})", name="visibility"),
        CheckConstraint(
            f"redaction_status IN ({REDACTION_STATUS_CHECK})",
            name="redaction_status",
        ),
        Index("ix_prompt_snapshots_template_id", "template_id"),
    )

    invocation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("model_invocations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("prompt_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    template_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    template_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_prompt_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_messages_json: Mapped[list[dict[str, Any]] | None] = mapped_column(
        _json_column(),
        nullable=True,
    )
    raw_request_json: Mapped[dict[str, Any] | None] = mapped_column(_json_column(), nullable=True)
    raw_response_json: Mapped[dict[str, Any] | None] = mapped_column(_json_column(), nullable=True)
    raw_output_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_output_json: Mapped[dict[str, Any] | None] = mapped_column(
        _json_column(),
        nullable=True,
    )
    prompt_context_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(
        _json_column(),
        nullable=True,
    )
    tool_definitions_json: Mapped[dict[str, Any] | None] = mapped_column(
        _json_column(),
        nullable=True,
    )
    context_pack_refs_json: Mapped[dict[str, Any] | None] = mapped_column(
        _json_column(),
        nullable=True,
    )
    input_asset_refs_json: Mapped[list[dict[str, Any]] | None] = mapped_column(
        _json_column(),
        nullable=True,
    )
    prompt_checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    request_checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    response_checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    output_checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    visibility: Mapped[str] = mapped_column(String(32), nullable=False)
    redaction_status: Mapped[str] = mapped_column(String(24), nullable=False)
    contains_sensitive_context: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
        default=False,
    )


class AgentRuntimeRunModelInvocation(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "agent_runtime_run_model_invocations"
    __table_args__ = (
        UniqueConstraint(
            "agent_runtime_run_id",
            "model_invocation_id",
            name="uq_agent_run_invocations_run_invocation",
        ),
        UniqueConstraint(
            "agent_runtime_run_id",
            "sequence_index",
            name="uq_agent_run_invocations_run_sequence",
        ),
        CheckConstraint(f"invocation_role IN ({INVOCATION_ROLE_CHECK})", name="invocation_role"),
        CheckConstraint("sequence_index >= 0", name="sequence_index_nonnegative"),
        Index(
            "ix_agent_run_invocations_run",
            "agent_runtime_run_id",
            "sequence_index",
        ),
        Index("ix_agent_run_invocations_invocation", "model_invocation_id"),
        Index(
            "ix_agent_run_invocations_worldline",
            "world_id",
            "worldline_id",
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
    agent_runtime_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_runtime_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    model_invocation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("model_invocations.id", ondelete="CASCADE"),
        nullable=False,
    )
    invocation_role: Mapped[str] = mapped_column(String(32), nullable=False)
    sequence_index: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class ModelInvocationTag(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "model_invocation_tags"
    __table_args__ = (
        UniqueConstraint(
            "world_id",
            "worldline_id",
            "invocation_id",
            "tag_type",
            "tag_key",
            "tag_value",
            name="uq_model_invocation_tags_identity",
        ),
        Index(
            "ix_model_invocation_tags_lookup",
            "world_id",
            "worldline_id",
            "tag_type",
            "tag_key",
            "tag_value",
        ),
        Index("ix_model_invocation_tags_invocation", "invocation_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    invocation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("model_invocations.id", ondelete="CASCADE"),
        nullable=False,
    )
    tag_type: Mapped[str] = mapped_column(String(40), nullable=False)
    tag_key: Mapped[str] = mapped_column(String(80), nullable=False)
    tag_value: Mapped[str] = mapped_column(String(220), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
