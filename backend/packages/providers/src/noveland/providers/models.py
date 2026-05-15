from __future__ import annotations

import uuid
from datetime import UTC, datetime
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
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


def _json_column() -> JSONB | JSON:
    return JSONB().with_variant(JSON(), "sqlite")


PROVIDER_SCOPE_CHECK = "'global', 'world'"
PROVIDER_KIND_CHECK = (
    "'text_generation', 'image_generation', 'image_editing', 'image_analysis', "
    "'image_composition', 'speech_to_text', 'text_to_speech', 'voice_cloning', "
    "'background_removal', 'workflow_engine', 'embedding', 'reranker', 'other'"
)
ADAPTER_KIND_CHECK = (
    "'fake', 'openai', 'openai_compatible', 'anthropic', 'anthropic_compatible', "
    "'comfyui', 'mimo_tts', 'mimo_asr', 'omnivoice', 'gpt_sovits', 'rembg', "
    "'sam2', 'custom_http', 'local_stub', 'other'"
)
PROVIDER_STATUS_CHECK = "'draft', 'active', 'disabled', 'deleted'"
PROVIDER_VISIBILITY_CHECK = "'private', 'world_admin', 'developer_only', 'hidden'"
HEALTH_STATUS_CHECK = "'healthy', 'degraded', 'unhealthy', 'unknown'"


class ProviderIntegration(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "provider_integrations"
    __table_args__ = (
        UniqueConstraint("scope_key", "provider_key", name="uq_provider_integrations_key"),
        CheckConstraint(f"scope_kind IN ({PROVIDER_SCOPE_CHECK})", name="scope_kind"),
        CheckConstraint(f"provider_kind IN ({PROVIDER_KIND_CHECK})", name="provider_kind"),
        CheckConstraint(f"adapter_kind IN ({ADAPTER_KIND_CHECK})", name="adapter_kind"),
        CheckConstraint(f"status IN ({PROVIDER_STATUS_CHECK})", name="status"),
        CheckConstraint(f"visibility IN ({PROVIDER_VISIBILITY_CHECK})", name="visibility"),
        CheckConstraint(
            "(scope_kind = 'global' AND world_id IS NULL AND scope_key = 'global') OR "
            "(scope_kind = 'world' AND world_id IS NOT NULL)",
            name="scope_consistency",
        ),
        Index("ix_provider_integrations_scope_status", "scope_kind", "world_id", "status"),
        Index(
            "ix_provider_integrations_world_kind",
            "world_id",
            "provider_kind",
            "status",
        ),
        Index("ix_provider_integrations_adapter", "adapter_kind"),
    )

    world_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=True,
    )
    scope_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    scope_key: Mapped[str] = mapped_column(String(120), nullable=False)
    provider_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    adapter_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    provider_key: Mapped[str] = mapped_column(String(120), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    auth_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    config_json: Mapped[dict[str, Any]] = mapped_column(
        _json_column(),
        nullable=False,
        default=dict,
    )
    default_params_json: Mapped[dict[str, Any]] = mapped_column(
        _json_column(),
        nullable=False,
        default=dict,
    )
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


class ProviderCapability(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "provider_capabilities"
    __table_args__ = (
        UniqueConstraint(
            "provider_integration_id",
            "capability_key",
            name="uq_provider_capabilities_key",
        ),
        Index("ix_provider_capabilities_provider", "provider_integration_id"),
        Index("ix_provider_capabilities_key", "capability_key"),
    )

    provider_integration_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("provider_integrations.id", ondelete="CASCADE"),
        nullable=False,
    )
    capability_key: Mapped[str] = mapped_column(String(120), nullable=False)
    capability_json: Mapped[dict[str, Any]] = mapped_column(
        _json_column(),
        nullable=False,
        default=dict,
    )


class ProviderHealthCheck(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "provider_health_checks"
    __table_args__ = (
        CheckConstraint(f"status IN ({HEALTH_STATUS_CHECK})", name="status"),
        CheckConstraint("latency_ms IS NULL OR latency_ms >= 0", name="latency_nonnegative"),
        Index(
            "ix_provider_health_checks_provider_checked",
            "provider_integration_id",
            "checked_at",
        ),
        Index("ix_provider_health_checks_status", "status"),
    )

    provider_integration_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("provider_integrations.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        _json_column(),
        nullable=False,
        default=dict,
    )


class ProviderBudgetPolicy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "provider_budget_policies"
    __table_args__ = (
        UniqueConstraint("world_id", "provider_id", "policy_key", name="uq_provider_budget_key"),
        CheckConstraint("status IN ('active', 'disabled', 'deleted')", name="status"),
        Index("ix_provider_budget_world_status", "world_id", "status"),
        Index("ix_provider_budget_provider_status", "provider_id", "status"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("provider_integrations.id", ondelete="CASCADE"),
        nullable=True,
    )
    policy_key: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        server_default=text("'active'"),
        default="active",
    )
    emergency_stop_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
        default=False,
    )
    limits_json: Mapped[dict[str, Any]] = mapped_column(
        "limits",
        _json_column(),
        nullable=False,
        default=dict,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        _json_column(),
        nullable=False,
        default=dict,
    )
