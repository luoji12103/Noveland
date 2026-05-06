"""Add living world plot route rumor flow.

Revision ID: 20260506_0026
Revises: 20260505_0025
Create Date: 2026-05-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260506_0026"
down_revision: str | None = "20260505_0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _json_type() -> postgresql.JSONB | sa.JSON:
    return postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def _timestamps() -> list[sa.Column]:
    return [
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
    ]


def _uuid_pk() -> sa.Column:
    return sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False)


def upgrade() -> None:
    op.create_table(
        "story_hooks",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("hook_key", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("hook_type", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="open"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("owner_agent_id", sa.Uuid(), nullable=True),
        sa.Column("target_agent_id", sa.Uuid(), nullable=True),
        sa.Column("source_event_id", sa.Uuid(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        _uuid_pk(),
        *_timestamps(),
        sa.CheckConstraint(
            "hook_type IN ('promise', 'foreshadowing', 'mystery', 'agreement', 'flag')",
            name="ck_story_hooks_hook_type",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'resolved', 'cancelled')",
            name="ck_story_hooks_status",
        ),
        sa.CheckConstraint(
            "priority >= 0 AND priority <= 100", name="ck_story_hooks_priority_range"
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worldline_id"], ["worldlines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_event_id"], ["world_events.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "world_id", "worldline_id", "hook_key", name="uq_story_hooks_scope_key"
        ),
    )
    op.create_index(
        "ix_story_hooks_worldline_status", "story_hooks", ["world_id", "worldline_id", "status"]
    )
    op.create_index(
        "ix_story_hooks_worldline_type", "story_hooks", ["world_id", "worldline_id", "hook_type"]
    )

    op.create_table(
        "plot_threads",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("thread_key", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("thread_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("stakes", sa.Text(), nullable=True),
        sa.Column("next_beats", _json_type(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column(
            "participant_agent_ids", _json_type(), nullable=False, server_default=sa.text("'[]'")
        ),
        sa.Column("organization_ids", _json_type(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column(
            "related_event_ids", _json_type(), nullable=False, server_default=sa.text("'[]'")
        ),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        _uuid_pk(),
        *_timestamps(),
        sa.CheckConstraint(
            "thread_type IN ('personal', 'organization', 'daily', 'main', 'hidden')",
            name="ck_plot_threads_thread_type",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'dormant', 'completed', 'archived')",
            name="ck_plot_threads_status",
        ),
        sa.CheckConstraint(
            "priority >= 0 AND priority <= 100", name="ck_plot_threads_priority_range"
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worldline_id"], ["worldlines.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "world_id", "worldline_id", "thread_key", name="uq_plot_threads_scope_key"
        ),
    )
    op.create_index(
        "ix_plot_threads_worldline_status", "plot_threads", ["world_id", "worldline_id", "status"]
    )
    op.create_index(
        "ix_plot_threads_worldline_type",
        "plot_threads",
        ["world_id", "worldline_id", "thread_type"],
    )

    op.create_table(
        "route_affinities",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("route_key", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="available"),
        sa.Column("affinity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stage", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("flags", _json_type(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("last_choice_id", sa.Uuid(), nullable=True),
        sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        _uuid_pk(),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('locked', 'available', 'active', 'completed', 'blocked')",
            name="ck_route_affinities_status",
        ),
        sa.CheckConstraint(
            "affinity >= -100 AND affinity <= 100", name="ck_route_affinities_affinity_range"
        ),
        sa.CheckConstraint("stage >= 0", name="ck_route_affinities_stage_nonnegative"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worldline_id"], ["worldlines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["last_choice_id"], ["player_choice_records.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "world_id",
            "worldline_id",
            "agent_id",
            "route_key",
            name="uq_route_affinities_scope_agent_key",
        ),
    )
    op.create_index(
        "ix_route_affinities_worldline_agent",
        "route_affinities",
        ["world_id", "worldline_id", "agent_id"],
    )
    op.create_index(
        "ix_route_affinities_worldline_status",
        "route_affinities",
        ["world_id", "worldline_id", "status"],
    )

    op.create_table(
        "event_trigger_conditions",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("condition_key", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("conditions", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        _uuid_pk(),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('active', 'inactive')", name="ck_event_trigger_conditions_status"
        ),
        sa.CheckConstraint(
            "priority >= 0 AND priority <= 100", name="ck_event_trigger_conditions_priority_range"
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "world_id", "condition_key", name="uq_event_trigger_conditions_world_key"
        ),
    )
    op.create_index(
        "ix_event_trigger_conditions_world_status",
        "event_trigger_conditions",
        ["world_id", "status"],
    )

    op.create_table(
        "scene_beat_drafts",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("source_kind", sa.String(length=32), nullable=False),
        sa.Column("source_ref", sa.String(length=160), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("setup", sa.Text(), nullable=False),
        sa.Column("dialogue_beats", _json_type(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("choice_points", _json_type(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("aftermath", sa.Text(), nullable=False),
        sa.Column(
            "participant_agent_ids", _json_type(), nullable=False, server_default=sa.text("'[]'")
        ),
        sa.Column("scene_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="draft"),
        sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        _uuid_pk(),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('draft', 'approved', 'published', 'archived')",
            name="ck_scene_beat_drafts_status",
        ),
        sa.CheckConstraint(
            "source_kind IN ('event', 'proposal', 'daily_episode', 'manual')",
            name="ck_scene_beat_drafts_source_kind",
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worldline_id"], ["worldlines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scene_id"], ["scenes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_scene_beat_drafts_worldline_status",
        "scene_beat_drafts",
        ["world_id", "worldline_id", "status"],
    )
    op.create_index(
        "ix_scene_beat_drafts_source",
        "scene_beat_drafts",
        ["world_id", "source_kind", "source_ref"],
    )

    op.create_table(
        "daily_episode_drafts",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("source_candidate_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("scene_beat_draft_id", sa.Uuid(), nullable=True),
        sa.Column(
            "participant_agent_ids", _json_type(), nullable=False, server_default=sa.text("'[]'")
        ),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="draft"),
        sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        _uuid_pk(),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('draft', 'queued', 'published', 'archived')",
            name="ck_daily_episode_drafts_status",
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worldline_id"], ["worldlines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["source_candidate_id"], ["daily_life_event_candidates.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["scene_beat_draft_id"], ["scene_beat_drafts.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_daily_episode_drafts_worldline_status",
        "daily_episode_drafts",
        ["world_id", "worldline_id", "status"],
    )
    op.create_index(
        "ix_daily_episode_drafts_source_candidate", "daily_episode_drafts", ["source_candidate_id"]
    )

    op.create_table(
        "group_interaction_contexts",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("context_key", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("interaction_type", sa.String(length=40), nullable=False),
        sa.Column("scene_id", sa.Uuid(), nullable=True),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column(
            "participant_agent_ids", _json_type(), nullable=False, server_default=sa.text("'[]'")
        ),
        sa.Column(
            "participant_roles", _json_type(), nullable=False, server_default=sa.text("'{}'")
        ),
        sa.Column("constraints", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="planned"),
        sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        _uuid_pk(),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('planned', 'active', 'completed', 'archived')",
            name="ck_group_interaction_contexts_status",
        ),
        sa.CheckConstraint(
            "interaction_type IN ('club', 'class', 'organization_meeting', 'conflict', 'casual')",
            name="ck_group_interaction_contexts_interaction_type",
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worldline_id"], ["worldlines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scene_id"], ["scenes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["world_organizations.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "world_id",
            "worldline_id",
            "context_key",
            name="uq_group_interaction_contexts_scope_key",
        ),
    )
    op.create_index(
        "ix_group_interaction_contexts_worldline_status",
        "group_interaction_contexts",
        ["world_id", "worldline_id", "status"],
    )

    op.create_table(
        "relationship_event_suggestions",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("relationship_id", sa.Uuid(), nullable=True),
        sa.Column("source_agent_id", sa.Uuid(), nullable=True),
        sa.Column("target_agent_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("suggested_event_name", sa.String(length=120), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="suggested"),
        sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        _uuid_pk(),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('suggested', 'accepted', 'dismissed')",
            name="ck_relationship_event_suggestions_status",
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worldline_id"], ["worldlines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["relationship_id"], ["agent_relationship_edges.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["source_agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_relationship_event_suggestions_worldline_status",
        "relationship_event_suggestions",
        ["world_id", "worldline_id", "status"],
    )
    op.create_index(
        "ix_relationship_event_suggestions_relationship",
        "relationship_event_suggestions",
        ["relationship_id"],
    )

    op.create_table(
        "organization_conflict_events",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("faction_track_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("pressure_delta", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("progress_delta", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="proposed"),
        sa.Column("resolved_event_id", sa.Uuid(), nullable=True),
        sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        _uuid_pk(),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('proposed', 'resolved', 'dismissed')",
            name="ck_organization_conflict_events_status",
        ),
        sa.CheckConstraint(
            "pressure_delta >= -100 AND pressure_delta <= 100",
            name="ck_organization_conflict_events_pressure_delta",
        ),
        sa.CheckConstraint(
            "progress_delta >= -100 AND progress_delta <= 100",
            name="ck_organization_conflict_events_progress_delta",
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worldline_id"], ["worldlines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["world_organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["faction_track_id"], ["faction_progress_tracks.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["resolved_event_id"], ["world_events.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_organization_conflict_events_worldline_status",
        "organization_conflict_events",
        ["world_id", "worldline_id", "status"],
    )
    op.create_index(
        "ix_organization_conflict_events_track",
        "organization_conflict_events",
        ["faction_track_id"],
    )

    op.create_table(
        "rumor_records",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("rumor_key", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_agent_id", sa.Uuid(), nullable=True),
        sa.Column("source_organization_id", sa.Uuid(), nullable=True),
        sa.Column("visibility", sa.String(length=24), nullable=False, server_default="private"),
        sa.Column("known_agent_ids", _json_type(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        _uuid_pk(),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('active', 'resolved', 'false', 'archived')", name="ck_rumor_records_status"
        ),
        sa.CheckConstraint(
            "visibility IN ('private', 'group', 'public')", name="ck_rumor_records_visibility"
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worldline_id"], ["worldlines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["source_organization_id"], ["world_organizations.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "world_id", "worldline_id", "rumor_key", name="uq_rumor_records_scope_key"
        ),
    )
    op.create_index(
        "ix_rumor_records_worldline_status", "rumor_records", ["world_id", "worldline_id", "status"]
    )
    op.create_index(
        "ix_rumor_records_worldline_visibility",
        "rumor_records",
        ["world_id", "worldline_id", "visibility"],
    )

    op.create_table(
        "rumor_propagations",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("rumor_id", sa.Uuid(), nullable=False),
        sa.Column("source_agent_id", sa.Uuid(), nullable=True),
        sa.Column("target_agent_id", sa.Uuid(), nullable=True),
        sa.Column("target_organization_id", sa.Uuid(), nullable=True),
        sa.Column("propagation_reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("delivered_event_id", sa.Uuid(), nullable=True),
        sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        _uuid_pk(),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('pending', 'delivered', 'blocked')", name="ck_rumor_propagations_status"
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worldline_id"], ["worldlines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rumor_id"], ["rumor_records.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["target_organization_id"], ["world_organizations.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["delivered_event_id"], ["world_events.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_rumor_propagations_rumor_status", "rumor_propagations", ["rumor_id", "status"]
    )
    op.create_index(
        "ix_rumor_propagations_worldline_target",
        "rumor_propagations",
        ["world_id", "worldline_id", "target_agent_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_rumor_propagations_worldline_target", table_name="rumor_propagations")
    op.drop_index("ix_rumor_propagations_rumor_status", table_name="rumor_propagations")
    op.drop_table("rumor_propagations")
    op.drop_index("ix_rumor_records_worldline_visibility", table_name="rumor_records")
    op.drop_index("ix_rumor_records_worldline_status", table_name="rumor_records")
    op.drop_table("rumor_records")
    op.drop_index(
        "ix_organization_conflict_events_track", table_name="organization_conflict_events"
    )
    op.drop_index(
        "ix_organization_conflict_events_worldline_status",
        table_name="organization_conflict_events",
    )
    op.drop_table("organization_conflict_events")
    op.drop_index(
        "ix_relationship_event_suggestions_relationship",
        table_name="relationship_event_suggestions",
    )
    op.drop_index(
        "ix_relationship_event_suggestions_worldline_status",
        table_name="relationship_event_suggestions",
    )
    op.drop_table("relationship_event_suggestions")
    op.drop_index(
        "ix_group_interaction_contexts_worldline_status", table_name="group_interaction_contexts"
    )
    op.drop_table("group_interaction_contexts")
    op.drop_index("ix_daily_episode_drafts_source_candidate", table_name="daily_episode_drafts")
    op.drop_index("ix_daily_episode_drafts_worldline_status", table_name="daily_episode_drafts")
    op.drop_table("daily_episode_drafts")
    op.drop_index("ix_scene_beat_drafts_source", table_name="scene_beat_drafts")
    op.drop_index("ix_scene_beat_drafts_worldline_status", table_name="scene_beat_drafts")
    op.drop_table("scene_beat_drafts")
    op.drop_index("ix_event_trigger_conditions_world_status", table_name="event_trigger_conditions")
    op.drop_table("event_trigger_conditions")
    op.drop_index("ix_route_affinities_worldline_status", table_name="route_affinities")
    op.drop_index("ix_route_affinities_worldline_agent", table_name="route_affinities")
    op.drop_table("route_affinities")
    op.drop_index("ix_plot_threads_worldline_type", table_name="plot_threads")
    op.drop_index("ix_plot_threads_worldline_status", table_name="plot_threads")
    op.drop_table("plot_threads")
    op.drop_index("ix_story_hooks_worldline_type", table_name="story_hooks")
    op.drop_index("ix_story_hooks_worldline_status", table_name="story_hooks")
    op.drop_table("story_hooks")
