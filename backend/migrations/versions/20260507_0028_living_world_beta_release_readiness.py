"""Add living world beta release readiness.

Revision ID: 20260507_0028
Revises: 20260507_0027
Create Date: 2026-05-07
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260507_0028"
down_revision: str | None = "20260507_0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _json_type() -> postgresql.JSONB | sa.JSON:
    return postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def _uuid_pk() -> sa.Column:
    return sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False)


def upgrade() -> None:
    op.create_table(
        "route_milestones",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("route_affinity_id", sa.Uuid(), nullable=True),
        sa.Column("plot_thread_id", sa.Uuid(), nullable=True),
        sa.Column("agent_id", sa.Uuid(), nullable=True),
        sa.Column("milestone_key", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("stage", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="planned"),
        sa.Column("conditions", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "evidence_metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")
        ),
        sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        _uuid_pk(),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('planned', 'active', 'completed', 'blocked')",
            name="ck_route_milestones_status",
        ),
        sa.CheckConstraint("stage >= 0", name="ck_route_milestones_stage_nonnegative"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worldline_id"], ["worldlines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["route_affinity_id"],
            ["route_affinities.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["plot_thread_id"], ["plot_threads.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "world_id",
            "worldline_id",
            "milestone_key",
            name="uq_route_milestones_scope_key",
        ),
    )
    op.create_index(
        "ix_route_milestones_worldline_status",
        "route_milestones",
        ["world_id", "worldline_id", "status"],
    )
    op.create_index("ix_route_milestones_route_affinity", "route_milestones", ["route_affinity_id"])
    op.create_index("ix_route_milestones_plot_thread", "route_milestones", ["plot_thread_id"])

    op.create_table(
        "ending_candidates",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("route_affinity_id", sa.Uuid(), nullable=True),
        sa.Column("plot_thread_id", sa.Uuid(), nullable=True),
        sa.Column("agent_id", sa.Uuid(), nullable=True),
        sa.Column("ending_key", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("ending_type", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="planned"),
        sa.Column("requirements", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("outcome_summary", sa.Text(), nullable=True),
        sa.Column(
            "evidence_metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")
        ),
        sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        _uuid_pk(),
        *_timestamps(),
        sa.CheckConstraint(
            "ending_type IN ('normal', 'bad', 'hidden', 'epilogue')",
            name="ck_ending_candidates_ending_type",
        ),
        sa.CheckConstraint(
            "status IN ('planned', 'available', 'locked', 'achieved', 'retired')",
            name="ck_ending_candidates_status",
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worldline_id"], ["worldlines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["route_affinity_id"],
            ["route_affinities.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["plot_thread_id"], ["plot_threads.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "world_id",
            "worldline_id",
            "ending_key",
            name="uq_ending_candidates_scope_key",
        ),
    )
    op.create_index(
        "ix_ending_candidates_worldline_status",
        "ending_candidates",
        ["world_id", "worldline_id", "status"],
    )
    op.create_index(
        "ix_ending_candidates_worldline_type",
        "ending_candidates",
        ["world_id", "worldline_id", "ending_type"],
    )

    op.create_table(
        "long_run_eval_runs",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("eval_key", sa.String(length=120), nullable=False),
        sa.Column("horizon_days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metrics", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("recommendations", _json_type(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("blockers", _json_type(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        _uuid_pk(),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('completed', 'warning', 'failed')",
            name="ck_long_run_eval_runs_status",
        ),
        sa.CheckConstraint(
            "horizon_days >= 1 AND horizon_days <= 90",
            name="ck_long_run_eval_runs_horizon_days_range",
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worldline_id"], ["worldlines.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_long_run_eval_runs_worldline_status",
        "long_run_eval_runs",
        ["world_id", "worldline_id", "status"],
    )
    op.create_index(
        "ix_long_run_eval_runs_worldline_created",
        "long_run_eval_runs",
        ["world_id", "worldline_id", "created_at"],
    )

    op.create_table(
        "authoring_templates",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("template_key", sa.String(length=120), nullable=False),
        sa.Column("template_kind", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("content", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "validation_issues",
            _json_type(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        _uuid_pk(),
        *_timestamps(),
        sa.CheckConstraint(
            "template_kind IN ('source_notes', 'character', 'event', 'route', 'world_bundle')",
            name="ck_authoring_templates_template_kind",
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("world_id", "template_key", name="uq_authoring_templates_world_key"),
    )
    op.create_index(
        "ix_authoring_templates_world_kind",
        "authoring_templates",
        ["world_id", "template_kind"],
    )
    op.create_index(
        "ix_authoring_templates_world_active",
        "authoring_templates",
        ["world_id", "is_active"],
    )

    op.create_table(
        "authoring_import_jobs",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("template_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("preview_summary", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("applied_refs", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "validation_issues",
            _json_type(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        _uuid_pk(),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('preview', 'applied', 'failed')",
            name="ck_authoring_import_jobs_status",
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_id"], ["authoring_templates.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_authoring_import_jobs_world_status",
        "authoring_import_jobs",
        ["world_id", "status"],
    )
    op.create_index("ix_authoring_import_jobs_template", "authoring_import_jobs", ["template_id"])

    op.create_table(
        "living_world_release_profiles",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("profile_key", sa.String(length=120), nullable=False, server_default="default"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="draft"),
        sa.Column("branch_policy", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("backup_policy", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "content_review_policy", _json_type(), nullable=False, server_default=sa.text("'{}'")
        ),
        sa.Column(
            "player_permission_policy",
            _json_type(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("worldline_policy", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("checklist", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        _uuid_pk(),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('draft', 'ready', 'blocked', 'released')",
            name="ck_living_world_release_profiles_status",
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("world_id", name="uq_living_world_release_profiles_world_id"),
    )
    op.create_index(
        "ix_living_world_release_profiles_status",
        "living_world_release_profiles",
        ["status"],
    )

    op.create_table(
        "beta_checklist_runs",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("run_key", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("evidence", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("blocker_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by_actor_ref", sa.String(length=120), nullable=False),
        sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        _uuid_pk(),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('pending', 'passed', 'warning', 'blocked')",
            name="ck_beta_checklist_runs_status",
        ),
        sa.CheckConstraint(
            "blocker_count >= 0",
            name="ck_beta_checklist_runs_blocker_count_nonnegative",
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worldline_id"], ["worldlines.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_beta_checklist_runs_worldline_status",
        "beta_checklist_runs",
        ["world_id", "worldline_id", "status"],
    )
    op.create_index(
        "ix_beta_checklist_runs_worldline_created",
        "beta_checklist_runs",
        ["world_id", "worldline_id", "created_at"],
    )

    op.create_table(
        "beta_checklist_items",
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("item_key", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("evidence", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("recommendation", sa.Text(), nullable=True),
        _uuid_pk(),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('pending', 'passed', 'warning', 'blocked')",
            name="ck_beta_checklist_items_status",
        ),
        sa.ForeignKeyConstraint(["run_id"], ["beta_checklist_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "item_key", name="uq_beta_checklist_items_run_key"),
    )
    op.create_index(
        "ix_beta_checklist_items_run_status",
        "beta_checklist_items",
        ["run_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_beta_checklist_items_run_status", table_name="beta_checklist_items")
    op.drop_table("beta_checklist_items")
    op.drop_index("ix_beta_checklist_runs_worldline_created", table_name="beta_checklist_runs")
    op.drop_index("ix_beta_checklist_runs_worldline_status", table_name="beta_checklist_runs")
    op.drop_table("beta_checklist_runs")
    op.drop_index(
        "ix_living_world_release_profiles_status",
        table_name="living_world_release_profiles",
    )
    op.drop_table("living_world_release_profiles")
    op.drop_index("ix_authoring_import_jobs_template", table_name="authoring_import_jobs")
    op.drop_index("ix_authoring_import_jobs_world_status", table_name="authoring_import_jobs")
    op.drop_table("authoring_import_jobs")
    op.drop_index("ix_authoring_templates_world_active", table_name="authoring_templates")
    op.drop_index("ix_authoring_templates_world_kind", table_name="authoring_templates")
    op.drop_table("authoring_templates")
    op.drop_index("ix_long_run_eval_runs_worldline_created", table_name="long_run_eval_runs")
    op.drop_index("ix_long_run_eval_runs_worldline_status", table_name="long_run_eval_runs")
    op.drop_table("long_run_eval_runs")
    op.drop_index("ix_ending_candidates_worldline_type", table_name="ending_candidates")
    op.drop_index("ix_ending_candidates_worldline_status", table_name="ending_candidates")
    op.drop_table("ending_candidates")
    op.drop_index("ix_route_milestones_plot_thread", table_name="route_milestones")
    op.drop_index("ix_route_milestones_route_affinity", table_name="route_milestones")
    op.drop_index("ix_route_milestones_worldline_status", table_name="route_milestones")
    op.drop_table("route_milestones")
