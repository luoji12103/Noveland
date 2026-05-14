"""Add authoring import core tables.

Revision ID: 20260514_0040
Revises: 20260512_0039
Create Date: 2026-05-14
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260514_0040"
down_revision: str | None = "20260512_0039"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "authoring_source_batches",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("batch_key", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_kind", sa.String(length=40), nullable=False),
        sa.Column(
            "status",
            sa.String(length=24),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column(
            "visibility",
            sa.String(length=32),
            server_default=sa.text("'private'"),
            nullable=False,
        ),
        sa.Column("metadata", JSONB, nullable=False),
        sa.Column("created_by_actor_ref", sa.String(length=120), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('active', 'archived', 'deleted')",
            name=op.f("ck_authoring_source_batches_status"),
        ),
        sa.CheckConstraint(
            "visibility IN ('private', 'world_admin', 'world_member', 'developer_only')",
            name=op.f("ck_authoring_source_batches_visibility"),
        ),
        sa.CheckConstraint(
            "source_kind IN ("
            "'script', 'lore', 'character_sheet', 'location_sheet', 'image', 'audio', "
            "'document', 'legacy_reference', 'other'"
            ")",
            name=op.f("ck_authoring_source_batches_source_kind"),
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_authoring_source_batches_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_authoring_source_batches_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_authoring_source_batches")),
        sa.UniqueConstraint(
            "world_id",
            "worldline_id",
            "batch_key",
            name="uq_authoring_source_batches_key",
        ),
    )
    op.create_index(
        "ix_authoring_source_batches_worldline_status",
        "authoring_source_batches",
        ["world_id", "worldline_id", "status"],
    )
    op.create_index(
        "ix_authoring_source_batches_kind",
        "authoring_source_batches",
        ["world_id", "worldline_id", "source_kind"],
    )

    op.create_table(
        "authoring_source_assets",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("media_asset_id", sa.Uuid(), nullable=True),
        sa.Column("source_asset_kind", sa.String(length=40), nullable=False),
        sa.Column("source_label", sa.String(length=160), nullable=False),
        sa.Column("source_ref", sa.String(length=240), nullable=True),
        sa.Column(
            "status",
            sa.String(length=24),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column("metadata", JSONB, nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('active', 'archived', 'deleted')",
            name=op.f("ck_authoring_source_assets_status"),
        ),
        sa.CheckConstraint(
            "source_asset_kind IN ("
            "'script', 'lore', 'character_sheet', 'location_sheet', 'image', 'audio', "
            "'document', 'legacy_reference', 'other'"
            ")",
            name=op.f("ck_authoring_source_assets_source_asset_kind"),
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_authoring_source_assets_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_authoring_source_assets_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["authoring_source_batches.id"],
            name=op.f("fk_authoring_source_assets_batch_id_authoring_source_batches"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["media_asset_id"],
            ["media_assets.id"],
            name=op.f("fk_authoring_source_assets_media_asset_id_media_assets"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_authoring_source_assets")),
    )
    op.create_index(
        "ix_authoring_source_assets_batch",
        "authoring_source_assets",
        ["batch_id", "source_asset_kind"],
    )
    op.create_index(
        "ix_authoring_source_assets_worldline_status",
        "authoring_source_assets",
        ["world_id", "worldline_id", "status"],
    )
    op.create_index(
        "ix_authoring_source_assets_media_asset",
        "authoring_source_assets",
        ["media_asset_id"],
    )

    op.create_table(
        "authoring_source_fragments",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("source_asset_id", sa.Uuid(), nullable=False),
        sa.Column("fragment_key", sa.String(length=120), nullable=False),
        sa.Column("fragment_kind", sa.String(length=40), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("excerpt_text", sa.Text(), nullable=True),
        sa.Column("locator", JSONB, nullable=False),
        sa.Column("metadata", JSONB, nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "fragment_kind IN ("
            "'dialogue', 'lore', 'character', 'relationship', 'asset', 'memory', "
            "'scene', 'other'"
            ")",
            name=op.f("ck_authoring_source_fragments_fragment_kind"),
        ),
        sa.CheckConstraint(
            "sequence >= 0",
            name=op.f("ck_authoring_source_fragments_sequence_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_authoring_source_fragments_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_authoring_source_fragments_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_asset_id"],
            ["authoring_source_assets.id"],
            name=op.f("fk_authoring_source_fragments_source_asset_id_authoring_source_assets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_authoring_source_fragments")),
        sa.UniqueConstraint(
            "source_asset_id",
            "fragment_key",
            name="uq_authoring_source_fragments_key",
        ),
    )
    op.create_index(
        "ix_authoring_source_fragments_asset_sequence",
        "authoring_source_fragments",
        ["source_asset_id", "sequence"],
    )
    op.create_index(
        "ix_authoring_source_fragments_worldline_kind",
        "authoring_source_fragments",
        ["world_id", "worldline_id", "fragment_kind"],
    )

    op.create_table(
        "authoring_import_runs",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("source_batch_id", sa.Uuid(), nullable=True),
        sa.Column("run_kind", sa.String(length=24), nullable=False),
        sa.Column(
            "status",
            sa.String(length=24),
            server_default=sa.text("'draft'"),
            nullable=False,
        ),
        sa.Column("summary", JSONB, nullable=False),
        sa.Column("created_by_actor_ref", sa.String(length=120), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "run_kind IN ('manual', 'preview', 'apply')",
            name=op.f("ck_authoring_import_runs_run_kind"),
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'previewed', 'applied', 'failed')",
            name=op.f("ck_authoring_import_runs_status"),
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_authoring_import_runs_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_authoring_import_runs_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_batch_id"],
            ["authoring_source_batches.id"],
            name=op.f("fk_authoring_import_runs_source_batch_id_authoring_source_batches"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_authoring_import_runs")),
    )
    op.create_index(
        "ix_authoring_import_runs_worldline_created",
        "authoring_import_runs",
        ["world_id", "worldline_id", "created_at"],
    )
    op.create_index(
        "ix_authoring_import_runs_source_batch",
        "authoring_import_runs",
        ["source_batch_id"],
    )

    op.create_table(
        "authoring_import_proposals",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("source_fragment_id", sa.Uuid(), nullable=True),
        sa.Column("proposal_kind", sa.String(length=40), nullable=False),
        sa.Column("target_ref_kind", sa.String(length=60), nullable=True),
        sa.Column("target_ref_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("proposed_payload", JSONB, nullable=False),
        sa.Column("evidence", JSONB, nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=24),
            server_default=sa.text("'proposed'"),
            nullable=False,
        ),
        sa.Column("applied_ref", JSONB, nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "proposal_kind IN ("
            "'dialogue', 'character', 'relationship', 'lore', 'asset_match', "
            "'memory', 'other'"
            ")",
            name=op.f("ck_authoring_import_proposals_proposal_kind"),
        ),
        sa.CheckConstraint(
            "status IN ("
            "'proposed', 'reviewed', 'approved', 'rejected', 'applied', 'blocked'"
            ")",
            name=op.f("ck_authoring_import_proposals_status"),
        ),
        sa.CheckConstraint(
            "priority >= 0",
            name=op.f("ck_authoring_import_proposals_priority_nonnegative"),
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR confidence >= 0",
            name=op.f("ck_authoring_import_proposals_confidence_min"),
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR confidence <= 1",
            name=op.f("ck_authoring_import_proposals_confidence_max"),
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_authoring_import_proposals_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_authoring_import_proposals_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["authoring_import_runs.id"],
            name=op.f("fk_authoring_import_proposals_run_id_authoring_import_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_fragment_id"],
            ["authoring_source_fragments.id"],
            name=op.f(
                "fk_authoring_import_proposals_source_fragment_id_authoring_source_fragments"
            ),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_authoring_import_proposals")),
    )
    op.create_index(
        "ix_authoring_import_proposals_run_priority",
        "authoring_import_proposals",
        ["run_id", "priority", "created_at"],
    )
    op.create_index(
        "ix_authoring_import_proposals_worldline_status",
        "authoring_import_proposals",
        ["world_id", "worldline_id", "status"],
    )
    op.create_index(
        "ix_authoring_import_proposals_fragment",
        "authoring_import_proposals",
        ["source_fragment_id"],
    )

    op.create_table(
        "authoring_review_decisions",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("proposal_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(length=24), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("decision_payload", JSONB, nullable=False),
        sa.Column("decided_by_actor_ref", sa.String(length=120), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "decision IN ('approve', 'reject', 'needs_changes', 'dismiss')",
            name=op.f("ck_authoring_review_decisions_decision"),
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_authoring_review_decisions_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_authoring_review_decisions_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["proposal_id"],
            ["authoring_import_proposals.id"],
            name=op.f("fk_authoring_review_decisions_proposal_id_authoring_import_proposals"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_authoring_review_decisions")),
    )
    op.create_index(
        "ix_authoring_review_decisions_proposal",
        "authoring_review_decisions",
        ["proposal_id"],
    )
    op.create_index(
        "ix_authoring_review_decisions_worldline_created",
        "authoring_review_decisions",
        ["world_id", "worldline_id", "created_at"],
    )

    op.create_table(
        "authoring_source_traceability",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("source_fragment_id", sa.Uuid(), nullable=False),
        sa.Column("proposal_id", sa.Uuid(), nullable=True),
        sa.Column("applied_ref_kind", sa.String(length=60), nullable=True),
        sa.Column("applied_ref_id", sa.Uuid(), nullable=True),
        sa.Column("trace_kind", sa.String(length=40), nullable=False),
        sa.Column("metadata", JSONB, nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "trace_kind IN ("
            "'proposal_created', 'proposal_reviewed', 'proposal_applied', 'apply_blocked'"
            ")",
            name=op.f("ck_authoring_source_traceability_trace_kind"),
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_authoring_source_traceability_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_authoring_source_traceability_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_fragment_id"],
            ["authoring_source_fragments.id"],
            name=op.f(
                "fk_authoring_source_traceability_source_fragment_id_authoring_source_fragments"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["proposal_id"],
            ["authoring_import_proposals.id"],
            name=op.f("fk_authoring_source_traceability_proposal_id_authoring_import_proposals"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_authoring_source_traceability")),
    )
    op.create_index(
        "ix_authoring_source_traceability_fragment",
        "authoring_source_traceability",
        ["source_fragment_id", "trace_kind"],
    )
    op.create_index(
        "ix_authoring_source_traceability_proposal",
        "authoring_source_traceability",
        ["proposal_id"],
    )
    op.create_index(
        "ix_authoring_source_traceability_worldline",
        "authoring_source_traceability",
        ["world_id", "worldline_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_authoring_source_traceability_worldline",
        table_name="authoring_source_traceability",
    )
    op.drop_index(
        "ix_authoring_source_traceability_proposal",
        table_name="authoring_source_traceability",
    )
    op.drop_index(
        "ix_authoring_source_traceability_fragment",
        table_name="authoring_source_traceability",
    )
    op.drop_table("authoring_source_traceability")
    op.drop_index(
        "ix_authoring_review_decisions_worldline_created",
        table_name="authoring_review_decisions",
    )
    op.drop_index(
        "ix_authoring_review_decisions_proposal",
        table_name="authoring_review_decisions",
    )
    op.drop_table("authoring_review_decisions")
    op.drop_index(
        "ix_authoring_import_proposals_fragment",
        table_name="authoring_import_proposals",
    )
    op.drop_index(
        "ix_authoring_import_proposals_worldline_status",
        table_name="authoring_import_proposals",
    )
    op.drop_index(
        "ix_authoring_import_proposals_run_priority",
        table_name="authoring_import_proposals",
    )
    op.drop_table("authoring_import_proposals")
    op.drop_index(
        "ix_authoring_import_runs_source_batch",
        table_name="authoring_import_runs",
    )
    op.drop_index(
        "ix_authoring_import_runs_worldline_created",
        table_name="authoring_import_runs",
    )
    op.drop_table("authoring_import_runs")
    op.drop_index(
        "ix_authoring_source_fragments_worldline_kind",
        table_name="authoring_source_fragments",
    )
    op.drop_index(
        "ix_authoring_source_fragments_asset_sequence",
        table_name="authoring_source_fragments",
    )
    op.drop_table("authoring_source_fragments")
    op.drop_index(
        "ix_authoring_source_assets_media_asset",
        table_name="authoring_source_assets",
    )
    op.drop_index(
        "ix_authoring_source_assets_worldline_status",
        table_name="authoring_source_assets",
    )
    op.drop_index(
        "ix_authoring_source_assets_batch",
        table_name="authoring_source_assets",
    )
    op.drop_table("authoring_source_assets")
    op.drop_index(
        "ix_authoring_source_batches_kind",
        table_name="authoring_source_batches",
    )
    op.drop_index(
        "ix_authoring_source_batches_worldline_status",
        table_name="authoring_source_batches",
    )
    op.drop_table("authoring_source_batches")
