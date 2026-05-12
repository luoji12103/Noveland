"""Add asset generation proposal orchestrator.

Revision ID: 20260512_0039
Revises: 20260512_0038
Create Date: 2026-05-12
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260512_0039"
down_revision: str | None = "20260512_0038"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "asset_generation_policies",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("policy_key", sa.String(length=120), nullable=False),
        sa.Column(
            "status",
            sa.String(length=24),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column("budget", JSONB, nullable=False),
        sa.Column("lookahead", JSONB, nullable=False),
        sa.Column("provider_preferences", JSONB, nullable=False),
        sa.Column("rules", JSONB, nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('active', 'disabled', 'deleted')",
            name=op.f("ck_asset_generation_policies_status"),
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_asset_generation_policies_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_asset_generation_policies_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_asset_generation_policies")),
        sa.UniqueConstraint(
            "world_id",
            "worldline_id",
            "policy_key",
            name="uq_asset_generation_policies_key",
        ),
    )
    op.create_index(
        "ix_asset_generation_policies_worldline_status",
        "asset_generation_policies",
        ["world_id", "worldline_id", "status"],
    )

    op.create_table(
        "asset_generation_runs",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("policy_id", sa.Uuid(), nullable=True),
        sa.Column("run_kind", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
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
            "run_kind IN ('preview', 'apply')",
            name=op.f("ck_asset_generation_runs_run_kind"),
        ),
        sa.CheckConstraint(
            "status IN ('succeeded', 'failed')",
            name=op.f("ck_asset_generation_runs_status"),
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_asset_generation_runs_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_asset_generation_runs_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["policy_id"],
            ["asset_generation_policies.id"],
            name=op.f("fk_asset_generation_runs_policy_id_asset_generation_policies"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_asset_generation_runs")),
    )
    op.create_index(
        "ix_asset_generation_runs_worldline_created",
        "asset_generation_runs",
        ["world_id", "worldline_id", "created_at"],
    )
    op.create_index("ix_asset_generation_runs_policy", "asset_generation_runs", ["policy_id"])

    op.create_table(
        "asset_generation_proposals",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("proposal_kind", sa.String(length=40), nullable=False),
        sa.Column("target_ref_kind", sa.String(length=60), nullable=False),
        sa.Column("target_ref_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("evidence", JSONB, nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("estimated_cost", sa.Float(), nullable=True),
        sa.Column("provider_kind", sa.String(length=64), nullable=True),
        sa.Column("provider_id", sa.Uuid(), nullable=True),
        sa.Column("request", JSONB, nullable=False),
        sa.Column(
            "status",
            sa.String(length=24),
            server_default=sa.text("'proposed'"),
            nullable=False,
        ),
        sa.Column("resulting_media_job_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "proposal_kind IN ("
            "'visual_scene', 'speech_audio', 'scene_background', "
            "'character_sprite', 'composite_scene'"
            ")",
            name=op.f("ck_asset_generation_proposals_proposal_kind"),
        ),
        sa.CheckConstraint(
            "priority >= 0",
            name=op.f("ck_asset_generation_proposals_priority_nonnegative"),
        ),
        sa.CheckConstraint(
            "estimated_cost IS NULL OR estimated_cost >= 0",
            name=op.f("ck_asset_generation_proposals_cost_nonnegative"),
        ),
        sa.CheckConstraint(
            "status IN ('proposed', 'applied', 'dismissed', 'blocked')",
            name=op.f("ck_asset_generation_proposals_status"),
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_asset_generation_proposals_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_asset_generation_proposals_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["asset_generation_runs.id"],
            name=op.f("fk_asset_generation_proposals_run_id_asset_generation_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            ["provider_integrations.id"],
            name=op.f("fk_asset_generation_proposals_provider_id_provider_integrations"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["resulting_media_job_id"],
            ["media_jobs.id"],
            name=op.f("fk_asset_generation_proposals_resulting_media_job_id_media_jobs"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_asset_generation_proposals")),
    )
    op.create_index(
        "ix_asset_generation_proposals_run_priority",
        "asset_generation_proposals",
        ["run_id", "priority", "created_at"],
    )
    op.create_index(
        "ix_asset_generation_proposals_worldline_status",
        "asset_generation_proposals",
        ["world_id", "worldline_id", "status"],
    )
    op.create_index(
        "ix_asset_generation_proposals_provider",
        "asset_generation_proposals",
        ["provider_id"],
    )
    op.create_index(
        "ix_asset_generation_proposals_media_job",
        "asset_generation_proposals",
        ["resulting_media_job_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_asset_generation_proposals_media_job",
        table_name="asset_generation_proposals",
    )
    op.drop_index(
        "ix_asset_generation_proposals_provider",
        table_name="asset_generation_proposals",
    )
    op.drop_index(
        "ix_asset_generation_proposals_worldline_status",
        table_name="asset_generation_proposals",
    )
    op.drop_index(
        "ix_asset_generation_proposals_run_priority",
        table_name="asset_generation_proposals",
    )
    op.drop_table("asset_generation_proposals")
    op.drop_index("ix_asset_generation_runs_policy", table_name="asset_generation_runs")
    op.drop_index(
        "ix_asset_generation_runs_worldline_created",
        table_name="asset_generation_runs",
    )
    op.drop_table("asset_generation_runs")
    op.drop_index(
        "ix_asset_generation_policies_worldline_status",
        table_name="asset_generation_policies",
    )
    op.drop_table("asset_generation_policies")
