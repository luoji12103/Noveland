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


BETA_FEEDBACK_ISSUE_TYPE_CHECK = (
    "'dialogue', 'persona', 'memory', 'sprite', 'background', 'voice', 'playback', "
    "'provider', 'quota', 'session_recovery', 'ux', 'worldline', 'other'"
)
BETA_FEEDBACK_SEVERITY_CHECK = "'low', 'medium', 'high', 'critical'"
BETA_FEEDBACK_STATUS_CHECK = (
    "'submitted', 'triaged', 'investigating', 'linked_to_repair', 'resolved', 'dismissed'"
)


class BetaFeedbackReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "beta_feedback_reports"
    __table_args__ = (
        CheckConstraint(
            f"issue_type IN ({BETA_FEEDBACK_ISSUE_TYPE_CHECK})",
            name="issue_type",
        ),
        CheckConstraint(
            f"severity IN ({BETA_FEEDBACK_SEVERITY_CHECK})",
            name="severity",
        ),
        CheckConstraint(
            f"status IN ({BETA_FEEDBACK_STATUS_CHECK})",
            name="status",
        ),
        Index("ix_beta_feedback_reports_world_status", "world_id", "status"),
        Index("ix_beta_feedback_reports_worldline_status", "world_id", "worldline_id", "status"),
        Index("ix_beta_feedback_reports_reporter", "world_id", "reporter_user_id"),
        Index("ix_beta_feedback_reports_issue_type", "world_id", "issue_type"),
        Index("ix_beta_feedback_reports_created", "world_id", "created_at"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    reporter_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    player_actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("player_actor_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    issue_type: Mapped[str] = mapped_column(String(40), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="submitted")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reporter_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_refs_json: Mapped[list[dict[str, Any]]] = mapped_column(
        "evidence_refs",
        _json_column(),
        nullable=False,
        default=list,
    )
    repair_proposal_refs_json: Mapped[list[dict[str, Any]]] = mapped_column(
        "repair_proposal_refs",
        _json_column(),
        nullable=False,
        default=list,
    )
    triage_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    triaged_by_actor_ref: Mapped[str | None] = mapped_column(String(160), nullable=True)
    triaged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    moderation_report_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        _json_column(),
        nullable=False,
        default=dict,
    )
