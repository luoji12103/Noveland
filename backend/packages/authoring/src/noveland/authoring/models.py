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


class AuthoringSourceBatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "authoring_source_batches"
    __table_args__ = (
        UniqueConstraint(
            "world_id",
            "worldline_id",
            "batch_key",
            name="uq_authoring_source_batches_key",
        ),
        CheckConstraint("status IN ('active', 'archived', 'deleted')", name="status"),
        CheckConstraint(
            "visibility IN ('private', 'world_admin', 'world_member', 'developer_only')",
            name="visibility",
        ),
        CheckConstraint(
            "source_kind IN ("
            "'script', 'lore', 'character_sheet', 'location_sheet', 'image', 'audio', "
            "'document', 'legacy_reference', 'other'"
            ")",
            name="source_kind",
        ),
        Index(
            "ix_authoring_source_batches_worldline_status",
            "world_id",
            "worldline_id",
            "status",
        ),
        Index(
            "ix_authoring_source_batches_kind",
            "world_id",
            "worldline_id",
            "source_kind",
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
    batch_key: Mapped[str] = mapped_column(String(120), nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        server_default=text("'active'"),
        default="active",
    )
    visibility: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'private'"),
        default="private",
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        _json_column(),
        nullable=False,
        default=dict,
    )
    created_by_actor_ref: Mapped[str] = mapped_column(String(120), nullable=False)


class AuthoringSourceAsset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "authoring_source_assets"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'archived', 'deleted')", name="status"),
        CheckConstraint(
            "source_asset_kind IN ("
            "'script', 'lore', 'character_sheet', 'location_sheet', 'image', 'audio', "
            "'document', 'legacy_reference', 'other'"
            ")",
            name="source_asset_kind",
        ),
        Index(
            "ix_authoring_source_assets_batch",
            "batch_id",
            "source_asset_kind",
        ),
        Index(
            "ix_authoring_source_assets_worldline_status",
            "world_id",
            "worldline_id",
            "status",
        ),
        Index("ix_authoring_source_assets_media_asset", "media_asset_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("authoring_source_batches.id", ondelete="CASCADE"),
        nullable=False,
    )
    media_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_asset_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    source_label: Mapped[str] = mapped_column(String(160), nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(240), nullable=True)
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        server_default=text("'active'"),
        default="active",
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        _json_column(),
        nullable=False,
        default=dict,
    )


class AuthoringSourceFragment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "authoring_source_fragments"
    __table_args__ = (
        UniqueConstraint(
            "source_asset_id",
            "fragment_key",
            name="uq_authoring_source_fragments_key",
        ),
        CheckConstraint(
            "fragment_kind IN ("
            "'dialogue', 'lore', 'character', 'relationship', 'asset', 'memory', "
            "'scene', 'other'"
            ")",
            name="fragment_kind",
        ),
        CheckConstraint("sequence >= 0", name="sequence_nonnegative"),
        Index(
            "ix_authoring_source_fragments_asset_sequence",
            "source_asset_id",
            "sequence",
        ),
        Index(
            "ix_authoring_source_fragments_worldline_kind",
            "world_id",
            "worldline_id",
            "fragment_kind",
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
    source_asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("authoring_source_assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    fragment_key: Mapped[str] = mapped_column(String(120), nullable=False)
    fragment_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    excerpt_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    locator_json: Mapped[dict[str, Any]] = mapped_column(
        "locator",
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


class AuthoringImportRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "authoring_import_runs"
    __table_args__ = (
        CheckConstraint("run_kind IN ('manual', 'preview', 'apply')", name="run_kind"),
        CheckConstraint(
            "status IN ('draft', 'previewed', 'applied', 'failed')",
            name="status",
        ),
        Index(
            "ix_authoring_import_runs_worldline_created",
            "world_id",
            "worldline_id",
            "created_at",
        ),
        Index("ix_authoring_import_runs_source_batch", "source_batch_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("authoring_source_batches.id", ondelete="SET NULL"),
        nullable=True,
    )
    run_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        server_default=text("'draft'"),
        default="draft",
    )
    summary_json: Mapped[dict[str, Any]] = mapped_column(
        "summary",
        _json_column(),
        nullable=False,
        default=dict,
    )
    created_by_actor_ref: Mapped[str] = mapped_column(String(120), nullable=False)


class AuthoringImportProposal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "authoring_import_proposals"
    __table_args__ = (
        CheckConstraint(
            "proposal_kind IN ("
            "'dialogue', 'character', 'relationship', 'lore', 'asset_match', "
            "'memory', 'other'"
            ")",
            name="proposal_kind",
        ),
        CheckConstraint(
            "status IN ("
            "'proposed', 'reviewed', 'approved', 'rejected', 'applied', 'blocked'"
            ")",
            name="status",
        ),
        CheckConstraint("priority >= 0", name="priority_nonnegative"),
        CheckConstraint("confidence IS NULL OR confidence >= 0", name="confidence_min"),
        CheckConstraint("confidence IS NULL OR confidence <= 1", name="confidence_max"),
        Index(
            "ix_authoring_import_proposals_run_priority",
            "run_id",
            "priority",
            "created_at",
        ),
        Index(
            "ix_authoring_import_proposals_worldline_status",
            "world_id",
            "worldline_id",
            "status",
        ),
        Index(
            "ix_authoring_import_proposals_fragment",
            "source_fragment_id",
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
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("authoring_import_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_fragment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("authoring_source_fragments.id", ondelete="SET NULL"),
        nullable=True,
    )
    proposal_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    target_ref_kind: Mapped[str | None] = mapped_column(String(60), nullable=True)
    target_ref_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_payload_json: Mapped[dict[str, Any]] = mapped_column(
        "proposed_payload",
        _json_column(),
        nullable=False,
        default=dict,
    )
    evidence_json: Mapped[dict[str, Any]] = mapped_column(
        "evidence",
        _json_column(),
        nullable=False,
        default=dict,
    )
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        server_default=text("'proposed'"),
        default="proposed",
    )
    applied_ref_json: Mapped[dict[str, Any]] = mapped_column(
        "applied_ref",
        _json_column(),
        nullable=False,
        default=dict,
    )


class AuthoringReviewDecision(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "authoring_review_decisions"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('approve', 'reject', 'needs_changes', 'dismiss')",
            name="decision",
        ),
        Index("ix_authoring_review_decisions_proposal", "proposal_id"),
        Index(
            "ix_authoring_review_decisions_worldline_created",
            "world_id",
            "worldline_id",
            "created_at",
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
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("authoring_import_proposals.id", ondelete="CASCADE"),
        nullable=False,
    )
    decision: Mapped[str] = mapped_column(String(24), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_json: Mapped[dict[str, Any]] = mapped_column(
        "decision_payload",
        _json_column(),
        nullable=False,
        default=dict,
    )
    decided_by_actor_ref: Mapped[str] = mapped_column(String(120), nullable=False)


class AuthoringSourceTraceability(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "authoring_source_traceability"
    __table_args__ = (
        CheckConstraint(
            "trace_kind IN ("
            "'proposal_created', 'proposal_reviewed', 'proposal_applied', 'apply_blocked'"
            ")",
            name="trace_kind",
        ),
        Index(
            "ix_authoring_source_traceability_fragment",
            "source_fragment_id",
            "trace_kind",
        ),
        Index(
            "ix_authoring_source_traceability_proposal",
            "proposal_id",
        ),
        Index(
            "ix_authoring_source_traceability_worldline",
            "world_id",
            "worldline_id",
            "created_at",
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
    source_fragment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("authoring_source_fragments.id", ondelete="CASCADE"),
        nullable=False,
    )
    proposal_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("authoring_import_proposals.id", ondelete="SET NULL"),
        nullable=True,
    )
    applied_ref_kind: Mapped[str | None] = mapped_column(String(60), nullable=True)
    applied_ref_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    trace_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        _json_column(),
        nullable=False,
        default=dict,
    )
