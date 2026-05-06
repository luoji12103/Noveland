"""Add living world GM choices and worldlines.

Revision ID: 20260505_0025
Revises: 20260505_0024
Create Date: 2026-05-05
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260505_0025"
down_revision: str | None = "20260505_0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _json_type() -> postgresql.JSONB | sa.JSON:
    return postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "worldlines",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("parent_worldline_id", sa.Uuid(), nullable=True),
        sa.Column("forked_from_snapshot_id", sa.Uuid(), nullable=True),
        sa.Column("fork_event_sequence", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("created_by_actor_ref", sa.String(length=120), nullable=False),
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
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_worldlines_status"),
        sa.CheckConstraint(
            "fork_event_sequence IS NULL OR fork_event_sequence >= 0",
            name="ck_worldlines_fork_event_sequence_nonnegative",
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["parent_worldline_id"],
            ["worldlines.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["forked_from_snapshot_id"],
            ["world_snapshots.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("world_id", "worldline_key", name="uq_worldlines_world_key"),
    )
    with op.batch_alter_table("worldlines") as batch_op:
        batch_op.alter_column("status", server_default=None)
        batch_op.alter_column("metadata", server_default=None)
    op.create_index("ix_worldlines_world_status", "worldlines", ["world_id", "status"])
    op.create_index("ix_worldlines_parent_worldline_id", "worldlines", ["parent_worldline_id"])

    op.execute(
        sa.text(
            """
            INSERT INTO worldlines (
                id,
                world_id,
                worldline_key,
                name,
                description,
                parent_worldline_id,
                forked_from_snapshot_id,
                fork_event_sequence,
                status,
                created_by_actor_ref,
                metadata,
                created_at,
                updated_at
            )
            SELECT
                gen_random_uuid(),
                worlds.id,
                'primary',
                'Primary Worldline',
                'Default branch for pre-worldline and mainline world state.',
                NULL,
                NULL,
                NULL,
                'active',
                'system:migration',
                '{}'::jsonb,
                now(),
                now()
            FROM worlds
            WHERE NOT EXISTS (
                SELECT 1
                FROM worldlines
                WHERE worldlines.world_id = worlds.id
                  AND worldlines.worldline_key = 'primary'
            )
            """,
        ),
    )

    _add_worldline_column("world_events")
    _add_worldline_column("world_snapshots")
    _add_worldline_column("agent_memory_items")
    _add_worldline_column("memory_write_jobs")
    _add_worldline_column("memory_retrieval_logs")
    _add_worldline_column("agent_relationship_edges")
    _add_worldline_column("faction_progress_tracks")
    _add_worldline_column("agent_presence_states")
    _add_worldline_column("daily_life_event_candidates")
    _add_worldline_column("offscreen_event_queue")

    _backfill_worldline("world_events")
    _backfill_worldline("world_snapshots")
    _backfill_worldline("agent_memory_items")
    _backfill_worldline("memory_write_jobs")
    _backfill_worldline("memory_retrieval_logs")
    _backfill_worldline("agent_relationship_edges")
    _backfill_worldline("faction_progress_tracks")
    _backfill_worldline("agent_presence_states")
    _backfill_worldline("daily_life_event_candidates")
    _backfill_worldline("offscreen_event_queue")

    with op.batch_alter_table("world_events") as batch_op:
        batch_op.drop_constraint("uq_world_events_world_sequence", type_="unique")
        batch_op.create_unique_constraint(
            "uq_world_events_worldline_sequence",
            ["world_id", "worldline_id", "sequence"],
        )
        batch_op.create_index(
            "ix_world_events_worldline_sequence", ["world_id", "worldline_id", "sequence"]
        )

    with op.batch_alter_table("world_snapshots") as batch_op:
        batch_op.create_index(
            "ix_world_snapshots_worldline_sequence",
            ["world_id", "worldline_id", "covers_event_sequence"],
        )

    op.create_index(
        "ix_agent_memory_items_worldline_agent",
        "agent_memory_items",
        ["world_id", "worldline_id", "agent_id"],
    )
    op.create_index(
        "ix_agent_memory_items_worldline_agent_active",
        "agent_memory_items",
        ["world_id", "worldline_id", "agent_id", "is_active"],
    )
    op.create_index(
        "ix_memory_write_jobs_worldline_agent",
        "memory_write_jobs",
        ["world_id", "worldline_id", "agent_id"],
    )
    op.create_index(
        "ix_memory_retrieval_logs_worldline_agent",
        "memory_retrieval_logs",
        ["world_id", "worldline_id", "agent_id"],
    )
    op.create_index(
        "ix_agent_relationship_edges_worldline_source",
        "agent_relationship_edges",
        ["world_id", "worldline_id", "source_agent_id"],
    )
    op.create_index(
        "ix_faction_progress_tracks_worldline_organization",
        "faction_progress_tracks",
        ["world_id", "worldline_id", "organization_id"],
    )
    op.create_index(
        "ix_agent_presence_states_worldline_agent",
        "agent_presence_states",
        ["world_id", "worldline_id", "agent_id"],
    )
    op.create_index(
        "ix_daily_life_event_candidates_worldline_status",
        "daily_life_event_candidates",
        ["world_id", "worldline_id", "status"],
    )
    op.create_index(
        "ix_offscreen_event_queue_worldline_status_due",
        "offscreen_event_queue",
        ["world_id", "worldline_id", "status", "due_at"],
    )

    op.create_table(
        "gm_agendas",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("focus_agents", _json_type(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column(
            "focus_organizations", _json_type(), nullable=False, server_default=sa.text("'[]'")
        ),
        sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('active', 'paused', 'completed', 'archived')", name="ck_gm_agendas_status"
        ),
        sa.CheckConstraint(
            "priority >= 0 AND priority <= 100", name="ck_gm_agendas_priority_range"
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worldline_id"], ["worldlines.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("gm_agendas") as batch_op:
        batch_op.alter_column("priority", server_default=None)
        batch_op.alter_column("status", server_default=None)
        batch_op.alter_column("focus_agents", server_default=None)
        batch_op.alter_column("focus_organizations", server_default=None)
        batch_op.alter_column("metadata", server_default=None)
    op.create_index(
        "ix_gm_agendas_worldline_status", "gm_agendas", ["world_id", "worldline_id", "status"]
    )

    op.create_table(
        "gm_event_proposals",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("agenda_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("event_name", sa.String(length=120), nullable=False),
        sa.Column("proposed_payload", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("importance", sa.String(length=32), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("affected_agents", _json_type(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column(
            "affected_organizations", _json_type(), nullable=False, server_default=sa.text("'[]'")
        ),
        sa.Column("source_context", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="proposed"),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("resolved_event_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('proposed', 'accepted', 'rejected', 'resolved')",
            name="ck_gm_event_proposals_status",
        ),
        sa.CheckConstraint(
            "importance IN ('daily', 'relationship', 'organization', 'route', 'main_plot')",
            name="ck_gm_event_proposals_importance",
        ),
        sa.CheckConstraint(
            "risk_score >= 0 AND risk_score <= 100", name="ck_gm_event_proposals_risk_score_range"
        ),
        sa.ForeignKeyConstraint(["agenda_id"], ["gm_agendas.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resolved_event_id"], ["world_events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worldline_id"], ["worldlines.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("gm_event_proposals") as batch_op:
        batch_op.alter_column("proposed_payload", server_default=None)
        batch_op.alter_column("risk_score", server_default=None)
        batch_op.alter_column("affected_agents", server_default=None)
        batch_op.alter_column("affected_organizations", server_default=None)
        batch_op.alter_column("source_context", server_default=None)
        batch_op.alter_column("status", server_default=None)
    op.create_index(
        "ix_gm_event_proposals_worldline_status",
        "gm_event_proposals",
        ["world_id", "worldline_id", "status"],
    )

    op.create_table(
        "event_resolution_rules",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("rule_key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("conditions", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("effects", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('active', 'inactive')", name="ck_event_resolution_rules_status"
        ),
        sa.CheckConstraint(
            "priority >= 0 AND priority <= 100", name="ck_event_resolution_rules_priority_range"
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("world_id", "rule_key", name="uq_event_resolution_rules_world_key"),
    )
    with op.batch_alter_table("event_resolution_rules") as batch_op:
        batch_op.alter_column("priority", server_default=None)
        batch_op.alter_column("status", server_default=None)
        batch_op.alter_column("conditions", server_default=None)
        batch_op.alter_column("effects", server_default=None)
    op.create_index(
        "ix_event_resolution_rules_world_status", "event_resolution_rules", ["world_id", "status"]
    )

    op.create_table(
        "player_actor_profiles",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("actor_ref", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("current_scene_id", sa.Uuid(), nullable=True),
        sa.Column("profile", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["current_scene_id"], ["scenes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worldline_id"], ["worldlines.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "world_id", "worldline_id", "user_id", name="uq_player_actor_profiles_scope_user"
        ),
    )
    with op.batch_alter_table("player_actor_profiles") as batch_op:
        batch_op.alter_column("profile", server_default=None)
        batch_op.alter_column("is_active", server_default=None)
    op.create_index(
        "ix_player_actor_profiles_worldline", "player_actor_profiles", ["world_id", "worldline_id"]
    )

    op.create_table(
        "player_choice_records",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("player_actor_id", sa.Uuid(), nullable=False),
        sa.Column("choice_key", sa.String(length=120), nullable=False),
        sa.Column("choice_kind", sa.String(length=40), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("selected_option", sa.Text(), nullable=False),
        sa.Column("context", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "consequence_preview", _json_type(), nullable=False, server_default=sa.text("'{}'")
        ),
        sa.Column("applied_event_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "choice_kind IN ('dialogue', 'travel', 'contact', 'intervention', 'route')",
            name="ck_player_choice_records_choice_kind",
        ),
        sa.ForeignKeyConstraint(["applied_event_id"], ["world_events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["player_actor_id"], ["player_actor_profiles.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worldline_id"], ["worldlines.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("player_choice_records") as batch_op:
        batch_op.alter_column("context", server_default=None)
        batch_op.alter_column("consequence_preview", server_default=None)
    op.create_index(
        "ix_player_choice_records_worldline_user",
        "player_choice_records",
        ["world_id", "worldline_id", "user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_player_choice_records_worldline_user", table_name="player_choice_records")
    op.drop_table("player_choice_records")
    op.drop_index("ix_player_actor_profiles_worldline", table_name="player_actor_profiles")
    op.drop_table("player_actor_profiles")
    op.drop_index("ix_event_resolution_rules_world_status", table_name="event_resolution_rules")
    op.drop_table("event_resolution_rules")
    op.drop_index("ix_gm_event_proposals_worldline_status", table_name="gm_event_proposals")
    op.drop_table("gm_event_proposals")
    op.drop_index("ix_gm_agendas_worldline_status", table_name="gm_agendas")
    op.drop_table("gm_agendas")

    op.drop_index(
        "ix_offscreen_event_queue_worldline_status_due", table_name="offscreen_event_queue"
    )
    op.drop_index(
        "ix_daily_life_event_candidates_worldline_status", table_name="daily_life_event_candidates"
    )
    op.drop_index("ix_agent_presence_states_worldline_agent", table_name="agent_presence_states")
    op.drop_index(
        "ix_faction_progress_tracks_worldline_organization", table_name="faction_progress_tracks"
    )
    op.drop_index(
        "ix_agent_relationship_edges_worldline_source", table_name="agent_relationship_edges"
    )
    op.drop_index("ix_memory_retrieval_logs_worldline_agent", table_name="memory_retrieval_logs")
    op.drop_index("ix_memory_write_jobs_worldline_agent", table_name="memory_write_jobs")
    op.drop_index("ix_agent_memory_items_worldline_agent_active", table_name="agent_memory_items")
    op.drop_index("ix_agent_memory_items_worldline_agent", table_name="agent_memory_items")

    with op.batch_alter_table("world_snapshots") as batch_op:
        batch_op.drop_index("ix_world_snapshots_worldline_sequence")
    with op.batch_alter_table("world_events") as batch_op:
        batch_op.drop_index("ix_world_events_worldline_sequence")
        batch_op.drop_constraint("uq_world_events_worldline_sequence", type_="unique")
        batch_op.create_unique_constraint(
            "uq_world_events_world_sequence", ["world_id", "sequence"]
        )

    for table_name in (
        "offscreen_event_queue",
        "daily_life_event_candidates",
        "agent_presence_states",
        "faction_progress_tracks",
        "agent_relationship_edges",
        "memory_retrieval_logs",
        "memory_write_jobs",
        "agent_memory_items",
        "world_snapshots",
        "world_events",
    ):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_column("worldline_id")

    op.drop_index("ix_worldlines_parent_worldline_id", table_name="worldlines")
    op.drop_index("ix_worldlines_world_status", table_name="worldlines")
    op.drop_table("worldlines")


def _add_worldline_column(table_name: str) -> None:
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.add_column(sa.Column("worldline_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            f"fk_{table_name}_worldline_id_worldlines",
            "worldlines",
            ["worldline_id"],
            ["id"],
            ondelete="CASCADE",
        )


def _backfill_worldline(table_name: str) -> None:
    op.execute(
        sa.text(
            f"""
            UPDATE {table_name}
            SET worldline_id = worldlines.id
            FROM worldlines
            WHERE {table_name}.world_id = worldlines.world_id
              AND worldlines.parent_worldline_id IS NULL
              AND {table_name}.worldline_id IS NULL
            """
        )
    )
