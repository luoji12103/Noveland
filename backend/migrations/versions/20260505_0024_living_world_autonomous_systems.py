"""Add living world autonomous systems.

Revision ID: 20260505_0024
Revises: 20260505_0023
Create Date: 2026-05-05
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260505_0024"
down_revision: str | None = "20260505_0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _json_type() -> postgresql.JSONB | sa.JSON:
    return postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    with op.batch_alter_table("world_events") as batch_op:
        batch_op.add_column(
            sa.Column("importance", sa.String(length=32), nullable=False, server_default="system"),
        )
        batch_op.create_check_constraint(
            "ck_world_events_importance",
            sa.text(
                "importance IN ('system', 'daily', 'relationship', 'organization', "
                "'route', 'main_plot')",
            ),
        )
        batch_op.create_index("ix_world_events_world_importance", ["world_id", "importance"])
        batch_op.alter_column("importance", server_default=None)

    with op.batch_alter_table("scenes") as batch_op:
        batch_op.add_column(sa.Column("region_key", sa.String(length=80), nullable=True))
        batch_op.add_column(
            sa.Column(
                "location_tags", _json_type(), nullable=False, server_default=sa.text("'[]'")
            ),
        )
        batch_op.add_column(
            sa.Column(
                "opening_rules", _json_type(), nullable=False, server_default=sa.text("'{}'")
            ),
        )
        batch_op.create_index("ix_scenes_world_region", ["world_id", "region_key"])
        batch_op.alter_column("location_tags", server_default=None)
        batch_op.alter_column("opening_rules", server_default=None)

    op.create_table(
        "world_organizations",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("organization_key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("organization_type", sa.String(length=40), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("public_summary", sa.Text(), nullable=True),
        sa.Column("hidden_summary", sa.Text(), nullable=True),
        sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "organization_type IN ('school', 'club', 'family', 'company', "
            "'faction', 'secret_group', 'other')",
            name="ck_world_organizations_organization_type",
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "world_id", "organization_key", name="uq_world_organizations_world_key"
        ),
    )
    with op.batch_alter_table("world_organizations") as batch_op:
        batch_op.alter_column("metadata", server_default=None)
        batch_op.alter_column("is_active", server_default=None)
    op.create_index("ix_world_organizations_world_id", "world_organizations", ["world_id"])
    op.create_index(
        "ix_world_organizations_world_type",
        "world_organizations",
        ["world_id", "organization_type"],
    )

    op.create_table(
        "organization_memberships",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("role_title", sa.String(length=120), nullable=True),
        sa.Column("visibility", sa.String(length=16), nullable=False, server_default="public"),
        sa.Column("loyalty", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("influence", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("responsibilities", _json_type(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "visibility IN ('public', 'hidden')", name="ck_organization_memberships_visibility"
        ),
        sa.CheckConstraint(
            "loyalty >= 0 AND loyalty <= 100", name="ck_organization_memberships_loyalty_range"
        ),
        sa.CheckConstraint(
            "influence >= 0 AND influence <= 100",
            name="ck_organization_memberships_influence_range",
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["world_organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "agent_id",
            name="uq_organization_memberships_organization_agent",
        ),
    )
    with op.batch_alter_table("organization_memberships") as batch_op:
        batch_op.alter_column("visibility", server_default=None)
        batch_op.alter_column("loyalty", server_default=None)
        batch_op.alter_column("influence", server_default=None)
        batch_op.alter_column("responsibilities", server_default=None)
        batch_op.alter_column("metadata", server_default=None)
    op.create_index(
        "ix_organization_memberships_world_agent",
        "organization_memberships",
        ["world_id", "agent_id"],
    )
    op.create_index(
        "ix_organization_memberships_world_organization",
        "organization_memberships",
        ["world_id", "organization_id"],
    )

    op.create_table(
        "faction_progress_tracks",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("track_key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("track_type", sa.String(length=40), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pressure", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "track_type IN ('goal', 'conflict', 'resource', 'reputation', 'risk')",
            name="ck_faction_progress_tracks_track_type",
        ),
        sa.CheckConstraint(
            "progress >= 0 AND progress <= 100", name="ck_faction_progress_tracks_progress_range"
        ),
        sa.CheckConstraint(
            "pressure >= 0 AND pressure <= 100", name="ck_faction_progress_tracks_pressure_range"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["world_organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "track_key",
            name="uq_faction_progress_tracks_organization_key",
        ),
    )
    with op.batch_alter_table("faction_progress_tracks") as batch_op:
        batch_op.alter_column("progress", server_default=None)
        batch_op.alter_column("pressure", server_default=None)
        batch_op.alter_column("metadata", server_default=None)
    op.create_index(
        "ix_faction_progress_tracks_world_organization",
        "faction_progress_tracks",
        ["world_id", "organization_id"],
    )
    op.create_index(
        "ix_faction_progress_tracks_world_type",
        "faction_progress_tracks",
        ["world_id", "track_type"],
    )

    op.create_table(
        "scene_location_edges",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("source_scene_id", sa.Uuid(), nullable=False),
        sa.Column("target_scene_id", sa.Uuid(), nullable=False),
        sa.Column("travel_label", sa.String(length=120), nullable=True),
        sa.Column("traversal_rules", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source_scene_id <> target_scene_id", name="ck_scene_location_edges_distinct_scenes"
        ),
        sa.ForeignKeyConstraint(["source_scene_id"], ["scenes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_scene_id"], ["scenes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_scene_id", "target_scene_id", name="uq_scene_location_edges_pair"
        ),
    )
    with op.batch_alter_table("scene_location_edges") as batch_op:
        batch_op.alter_column("traversal_rules", server_default=None)
    op.create_index(
        "ix_scene_location_edges_world_source",
        "scene_location_edges",
        ["world_id", "source_scene_id"],
    )
    op.create_index(
        "ix_scene_location_edges_world_target",
        "scene_location_edges",
        ["world_id", "target_scene_id"],
    )

    op.create_table(
        "agent_presence_states",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("current_scene_id", sa.Uuid(), nullable=True),
        sa.Column(
            "visibility_status", sa.String(length=24), nullable=False, server_default="visible"
        ),
        sa.Column(
            "encounter_eligible", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "scheduled_movement", _json_type(), nullable=False, server_default=sa.text("'{}'")
        ),
        sa.Column("last_event_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "visibility_status IN ('visible', 'offscreen', 'hidden', 'unavailable')",
            name="ck_agent_presence_states_visibility_status",
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["current_scene_id"], ["scenes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["last_event_id"], ["world_events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("world_id", "agent_id", name="uq_agent_presence_states_world_agent"),
    )
    with op.batch_alter_table("agent_presence_states") as batch_op:
        batch_op.alter_column("visibility_status", server_default=None)
        batch_op.alter_column("encounter_eligible", server_default=None)
        batch_op.alter_column("scheduled_movement", server_default=None)
    op.create_index(
        "ix_agent_presence_states_world_agent",
        "agent_presence_states",
        ["world_id", "agent_id"],
    )
    op.create_index(
        "ix_agent_presence_states_world_scene",
        "agent_presence_states",
        ["world_id", "current_scene_id"],
    )

    op.create_table(
        "daily_life_event_candidates",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=True),
        sa.Column("scene_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("importance", sa.String(length=32), nullable=False, server_default="daily"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "source_kind", sa.String(length=80), nullable=False, server_default="daily_preview"
        ),
        sa.Column("source_ref", sa.String(length=160), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="candidate"),
        sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('candidate', 'queued', 'dismissed')",
            name="ck_daily_life_event_candidates_status",
        ),
        sa.CheckConstraint(
            "importance IN ('daily', 'relationship', 'organization')",
            name="ck_daily_life_event_candidates_importance",
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["scene_id"], ["scenes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("daily_life_event_candidates") as batch_op:
        batch_op.alter_column("importance", server_default=None)
        batch_op.alter_column("source_kind", server_default=None)
        batch_op.alter_column("status", server_default=None)
        batch_op.alter_column("metadata", server_default=None)
    op.create_index(
        "ix_daily_life_event_candidates_world_status",
        "daily_life_event_candidates",
        ["world_id", "status"],
    )
    op.create_index(
        "ix_daily_life_event_candidates_world_time",
        "daily_life_event_candidates",
        ["world_id", "starts_at"],
    )

    op.create_table(
        "offscreen_event_queue",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("source_candidate_id", sa.Uuid(), nullable=True),
        sa.Column("event_name", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("payload", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("importance", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("resolved_event_id", sa.Uuid(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'resolved', 'cancelled', 'failed')",
            name="ck_offscreen_event_queue_status",
        ),
        sa.CheckConstraint(
            "importance IN ('daily', 'relationship', 'organization', 'route', 'main_plot')",
            name="ck_offscreen_event_queue_importance",
        ),
        sa.ForeignKeyConstraint(["resolved_event_id"], ["world_events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["source_candidate_id"],
            ["daily_life_event_candidates.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("offscreen_event_queue") as batch_op:
        batch_op.alter_column("payload", server_default=None)
        batch_op.alter_column("status", server_default=None)
    op.create_index(
        "ix_offscreen_event_queue_world_status_due",
        "offscreen_event_queue",
        ["world_id", "status", "due_at"],
    )
    op.create_index(
        "ix_offscreen_event_queue_world_importance",
        "offscreen_event_queue",
        ["world_id", "importance"],
    )


def downgrade() -> None:
    op.drop_index("ix_offscreen_event_queue_world_importance", table_name="offscreen_event_queue")
    op.drop_index("ix_offscreen_event_queue_world_status_due", table_name="offscreen_event_queue")
    op.drop_table("offscreen_event_queue")

    op.drop_index(
        "ix_daily_life_event_candidates_world_time",
        table_name="daily_life_event_candidates",
    )
    op.drop_index(
        "ix_daily_life_event_candidates_world_status",
        table_name="daily_life_event_candidates",
    )
    op.drop_table("daily_life_event_candidates")

    op.drop_index("ix_agent_presence_states_world_scene", table_name="agent_presence_states")
    op.drop_index("ix_agent_presence_states_world_agent", table_name="agent_presence_states")
    op.drop_table("agent_presence_states")

    op.drop_index("ix_scene_location_edges_world_target", table_name="scene_location_edges")
    op.drop_index("ix_scene_location_edges_world_source", table_name="scene_location_edges")
    op.drop_table("scene_location_edges")

    op.drop_index("ix_faction_progress_tracks_world_type", table_name="faction_progress_tracks")
    op.drop_index(
        "ix_faction_progress_tracks_world_organization",
        table_name="faction_progress_tracks",
    )
    op.drop_table("faction_progress_tracks")

    op.drop_index(
        "ix_organization_memberships_world_organization",
        table_name="organization_memberships",
    )
    op.drop_index("ix_organization_memberships_world_agent", table_name="organization_memberships")
    op.drop_table("organization_memberships")

    op.drop_index("ix_world_organizations_world_type", table_name="world_organizations")
    op.drop_index("ix_world_organizations_world_id", table_name="world_organizations")
    op.drop_table("world_organizations")

    with op.batch_alter_table("scenes") as batch_op:
        batch_op.drop_index("ix_scenes_world_region")
        batch_op.drop_column("opening_rules")
        batch_op.drop_column("location_tags")
        batch_op.drop_column("region_key")

    with op.batch_alter_table("world_events") as batch_op:
        batch_op.drop_index("ix_world_events_world_importance")
        batch_op.drop_constraint("ck_world_events_importance", type_="check")
        batch_op.drop_column("importance")
