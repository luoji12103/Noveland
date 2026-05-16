from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from noveland.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin
from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


def _json_column() -> JSONB | JSON:
    return JSONB().with_variant(JSON(), "sqlite")


MODERATION_SEVERITY_CHECK = "'low', 'medium', 'high', 'critical'"
MODERATION_REPORT_STATUS_CHECK = (
    "'submitted', 'under_review', 'resolved', 'dismissed', 'escalated'"
)
MODERATION_ACTION_STATUS_CHECK = "'proposed', 'approved', 'applied', 'rejected', 'canceled'"
MODERATION_INCIDENT_STATUS_CHECK = "'open', 'under_review', 'mitigated', 'closed'"
MODERATION_CATEGORY_CHECK = (
    "'safety', 'privacy', 'copyright', 'abuse', 'quality', 'security', 'other'"
)
MODERATION_TARGET_KIND_CHECK = (
    "'world', 'worldline', 'scene', 'narrative_publication', 'conversation_session', "
    "'conversation_turn', 'media_asset', 'provider_integration', 'plugin_package', "
    "'player_profile', 'other'"
)
MODERATION_ACTION_KIND_CHECK = (
    "'disable_media', 'disable_world', 'disable_provider', 'rollback_review', "
    "'takedown_content', 'note_only'"
)


class ModerationReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "moderation_reports"
    __table_args__ = (
        CheckConstraint(
            f"category IN ({MODERATION_CATEGORY_CHECK})",
            name="category",
        ),
        CheckConstraint(
            f"severity IN ({MODERATION_SEVERITY_CHECK})",
            name="severity",
        ),
        CheckConstraint(
            f"status IN ({MODERATION_REPORT_STATUS_CHECK})",
            name="status",
        ),
        CheckConstraint(
            f"target_ref_kind IN ({MODERATION_TARGET_KIND_CHECK})",
            name="target_ref_kind",
        ),
        Index("ix_moderation_reports_world_status", "world_id", "status"),
        Index("ix_moderation_reports_worldline_status", "world_id", "worldline_id", "status"),
        Index("ix_moderation_reports_reporter", "world_id", "reporter_user_id"),
        Index("ix_moderation_reports_target", "world_id", "target_ref_kind", "target_ref_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=True,
    )
    reporter_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_ref_kind: Mapped[str] = mapped_column(String(80), nullable=False)
    target_ref_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="submitted")
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    reporter_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_refs_json: Mapped[list[dict[str, Any]]] = mapped_column(
        "evidence_refs",
        _json_column(),
        nullable=False,
        default=list,
    )
    created_by_actor_ref: Mapped[str] = mapped_column(String(160), nullable=False)
    reviewed_by_actor_ref: Mapped[str | None] = mapped_column(String(160), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        _json_column(),
        nullable=False,
        default=dict,
    )


class ModerationIncident(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "moderation_incidents"
    __table_args__ = (
        CheckConstraint(
            f"severity IN ({MODERATION_SEVERITY_CHECK})",
            name="severity",
        ),
        CheckConstraint(
            f"status IN ({MODERATION_INCIDENT_STATUS_CHECK})",
            name="status",
        ),
        Index("ix_moderation_incidents_world_status", "world_id", "status"),
        Index("ix_moderation_incidents_worldline_status", "world_id", "worldline_id", "status"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    report_ids_json: Mapped[list[str]] = mapped_column(
        "report_ids",
        _json_column(),
        nullable=False,
        default=list,
    )
    action_ids_json: Mapped[list[str]] = mapped_column(
        "action_ids",
        _json_column(),
        nullable=False,
        default=list,
    )
    evidence_refs_json: Mapped[list[dict[str, Any]]] = mapped_column(
        "evidence_refs",
        _json_column(),
        nullable=False,
        default=list,
    )
    created_by_actor_ref: Mapped[str] = mapped_column(String(160), nullable=False)
    reviewed_by_actor_ref: Mapped[str | None] = mapped_column(String(160), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        _json_column(),
        nullable=False,
        default=dict,
    )


class ModerationAction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "moderation_actions"
    __table_args__ = (
        CheckConstraint(
            f"action_kind IN ({MODERATION_ACTION_KIND_CHECK})",
            name="action_kind",
        ),
        CheckConstraint(
            f"status IN ({MODERATION_ACTION_STATUS_CHECK})",
            name="status",
        ),
        CheckConstraint(
            f"target_ref_kind IN ({MODERATION_TARGET_KIND_CHECK})",
            name="target_ref_kind",
        ),
        Index("ix_moderation_actions_world_status", "world_id", "status"),
        Index("ix_moderation_actions_worldline_status", "world_id", "worldline_id", "status"),
        Index("ix_moderation_actions_target", "world_id", "target_ref_kind", "target_ref_id"),
        Index("ix_moderation_actions_report", "report_id"),
        Index("ix_moderation_actions_incident", "incident_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=True,
    )
    report_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("moderation_reports.id", ondelete="SET NULL"),
        nullable=True,
    )
    incident_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("moderation_incidents.id", ondelete="SET NULL"),
        nullable=True,
    )
    action_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="proposed")
    target_ref_kind: Mapped[str] = mapped_column(String(80), nullable=False)
    target_ref_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    audit_summary_json: Mapped[dict[str, Any]] = mapped_column(
        "audit_summary",
        _json_column(),
        nullable=False,
        default=dict,
    )
    evidence_refs_json: Mapped[list[dict[str, Any]]] = mapped_column(
        "evidence_refs",
        _json_column(),
        nullable=False,
        default=list,
    )
    created_by_actor_ref: Mapped[str] = mapped_column(String(160), nullable=False)
    reviewed_by_actor_ref: Mapped[str | None] = mapped_column(String(160), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        _json_column(),
        nullable=False,
        default=dict,
    )
