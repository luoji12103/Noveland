from __future__ import annotations

import uuid
from typing import Any

from noveland.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin
from sqlalchemy import (
    JSON,
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


def _json_column() -> JSONB | JSON:
    return JSONB().with_variant(JSON(), "sqlite")


class AssetGenerationPolicy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "asset_generation_policies"
    __table_args__ = (
        UniqueConstraint(
            "world_id",
            "worldline_id",
            "policy_key",
            name="uq_asset_generation_policies_key",
        ),
        CheckConstraint("status IN ('active', 'disabled', 'deleted')", name="status"),
        Index(
            "ix_asset_generation_policies_worldline_status",
            "world_id",
            "worldline_id",
            "status",
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
    policy_key: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        server_default=text("'active'"),
        default="active",
    )
    budget_json: Mapped[dict[str, Any]] = mapped_column(
        "budget",
        _json_column(),
        nullable=False,
        default=dict,
    )
    lookahead_json: Mapped[dict[str, Any]] = mapped_column(
        "lookahead",
        _json_column(),
        nullable=False,
        default=dict,
    )
    provider_preferences_json: Mapped[dict[str, Any]] = mapped_column(
        "provider_preferences",
        _json_column(),
        nullable=False,
        default=dict,
    )
    rules_json: Mapped[dict[str, Any]] = mapped_column(
        "rules",
        _json_column(),
        nullable=False,
        default=dict,
    )


class AssetGenerationRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "asset_generation_runs"
    __table_args__ = (
        CheckConstraint("run_kind IN ('preview', 'apply')", name="run_kind"),
        CheckConstraint("status IN ('succeeded', 'failed')", name="status"),
        Index(
            "ix_asset_generation_runs_worldline_created",
            "world_id",
            "worldline_id",
            "created_at",
        ),
        Index("ix_asset_generation_runs_policy", "policy_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    policy_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("asset_generation_policies.id", ondelete="SET NULL"),
        nullable=True,
    )
    run_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    summary_json: Mapped[dict[str, Any]] = mapped_column(
        "summary",
        _json_column(),
        nullable=False,
        default=dict,
    )
    created_by_actor_ref: Mapped[str] = mapped_column(String(120), nullable=False)


class AssetGenerationProposal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "asset_generation_proposals"
    __table_args__ = (
        CheckConstraint(
            "proposal_kind IN ("
            "'visual_scene', 'speech_audio', 'scene_background', "
            "'character_sprite', 'composite_scene'"
            ")",
            name="proposal_kind",
        ),
        CheckConstraint("priority >= 0", name="priority_nonnegative"),
        CheckConstraint("estimated_cost IS NULL OR estimated_cost >= 0", name="cost_nonnegative"),
        CheckConstraint("status IN ('proposed', 'applied', 'dismissed', 'blocked')", name="status"),
        Index(
            "ix_asset_generation_proposals_run_priority",
            "run_id",
            "priority",
            "created_at",
        ),
        Index(
            "ix_asset_generation_proposals_worldline_status",
            "world_id",
            "worldline_id",
            "status",
        ),
        Index("ix_asset_generation_proposals_provider", "provider_id"),
        Index("ix_asset_generation_proposals_media_job", "resulting_media_job_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("asset_generation_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    proposal_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    target_ref_kind: Mapped[str] = mapped_column(String(60), nullable=False)
    target_ref_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_json: Mapped[dict[str, Any]] = mapped_column(
        "evidence",
        _json_column(),
        nullable=False,
        default=dict,
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    provider_kind: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("provider_integrations.id", ondelete="SET NULL"),
        nullable=True,
    )
    request_json: Mapped[dict[str, Any]] = mapped_column(
        "request",
        _json_column(),
        nullable=False,
        default=dict,
    )
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        server_default=text("'proposed'"),
        default="proposed",
    )
    resulting_media_job_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
