"""Add living world knowledge player guardrails.

Revision ID: 20260507_0027
Revises: 20260506_0026
Create Date: 2026-05-07
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260507_0027"
down_revision: str | None = "20260506_0026"
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
        "character_knowledge_facts",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("fact_key", sa.String(length=120), nullable=False),
        sa.Column("knowledge_kind", sa.String(length=24), nullable=False, server_default="fact"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_event_id", sa.Uuid(), nullable=True),
        sa.Column("source_ref", sa.String(length=160), nullable=True),
        sa.Column("confidence", sa.Integer(), nullable=False, server_default="80"),
        sa.Column("visibility", sa.String(length=24), nullable=False, server_default="private"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        _uuid_pk(),
        *_timestamps(),
        sa.CheckConstraint(
            "knowledge_kind IN ('fact', 'secret', 'guess', 'misbelief')",
            name="ck_character_knowledge_facts_knowledge_kind",
        ),
        sa.CheckConstraint(
            "visibility IN ('private', 'shared', 'public')",
            name="ck_character_knowledge_facts_visibility",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 100",
            name="ck_character_knowledge_facts_confidence_range",
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worldline_id"], ["worldlines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_event_id"], ["world_events.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "world_id",
            "worldline_id",
            "agent_id",
            "fact_key",
            name="uq_character_knowledge_facts_scope_agent_key",
        ),
    )
    op.create_index(
        "ix_character_knowledge_facts_worldline_agent",
        "character_knowledge_facts",
        ["world_id", "worldline_id", "agent_id"],
    )
    op.create_index(
        "ix_character_knowledge_facts_worldline_kind",
        "character_knowledge_facts",
        ["world_id", "worldline_id", "knowledge_kind"],
    )

    op.create_table(
        "secret_records",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("secret_key", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("holder_agent_ids", _json_type(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column(
            "reveal_conditions", _json_type(), nullable=False, server_default=sa.text("'{}'")
        ),
        sa.Column(
            "consequence_metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")
        ),
        sa.Column("visibility", sa.String(length=24), nullable=False, server_default="holders"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="hidden"),
        sa.Column("revealed_event_id", sa.Uuid(), nullable=True),
        sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        _uuid_pk(),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('hidden', 'revealed', 'archived')", name="ck_secret_records_status"
        ),
        sa.CheckConstraint(
            "visibility IN ('private', 'holders', 'public')",
            name="ck_secret_records_visibility",
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worldline_id"], ["worldlines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["revealed_event_id"], ["world_events.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "world_id", "worldline_id", "secret_key", name="uq_secret_records_scope_key"
        ),
    )
    op.create_index(
        "ix_secret_records_worldline_status",
        "secret_records",
        ["world_id", "worldline_id", "status"],
    )
    op.create_index(
        "ix_secret_records_worldline_visibility",
        "secret_records",
        ["world_id", "worldline_id", "visibility"],
    )

    op.create_table(
        "character_emotional_states",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("mood", sa.String(length=80), nullable=False, server_default="neutral"),
        sa.Column("stress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fatigue", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("anticipation", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("jealousy", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("anger", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_event_id", sa.Uuid(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        _uuid_pk(),
        *_timestamps(),
        sa.CheckConstraint(
            "stress >= 0 AND stress <= 100", name="ck_character_emotional_states_stress_range"
        ),
        sa.CheckConstraint(
            "fatigue >= 0 AND fatigue <= 100", name="ck_character_emotional_states_fatigue_range"
        ),
        sa.CheckConstraint(
            "anticipation >= 0 AND anticipation <= 100",
            name="ck_character_emotional_states_anticipation_range",
        ),
        sa.CheckConstraint(
            "jealousy >= 0 AND jealousy <= 100", name="ck_character_emotional_states_jealousy_range"
        ),
        sa.CheckConstraint(
            "anger >= 0 AND anger <= 100", name="ck_character_emotional_states_anger_range"
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worldline_id"], ["worldlines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_event_id"], ["world_events.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "world_id",
            "worldline_id",
            "agent_id",
            name="uq_character_emotional_states_scope_agent",
        ),
    )
    op.create_index(
        "ix_character_emotional_states_worldline_agent",
        "character_emotional_states",
        ["world_id", "worldline_id", "agent_id"],
    )

    op.create_table(
        "relationship_repair_records",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("relationship_id", sa.Uuid(), nullable=False),
        sa.Column("repair_kind", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("score_delta", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="proposed"),
        sa.Column("applied_event_id", sa.Uuid(), nullable=True),
        sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        _uuid_pk(),
        *_timestamps(),
        sa.CheckConstraint(
            "repair_kind IN ("
            "'decay', 'repair', 'conflict', 'apology', 'kept_promise', 'shared_event'"
            ")",
            name="ck_relationship_repair_records_repair_kind",
        ),
        sa.CheckConstraint(
            "status IN ('proposed', 'applied', 'dismissed')",
            name="ck_relationship_repair_records_status",
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worldline_id"], ["worldlines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["relationship_id"], ["agent_relationship_edges.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["applied_event_id"], ["world_events.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_relationship_repair_records_worldline_status",
        "relationship_repair_records",
        ["world_id", "worldline_id", "status"],
    )
    op.create_index(
        "ix_relationship_repair_records_relationship",
        "relationship_repair_records",
        ["relationship_id"],
    )

    op.create_table(
        "player_journal_entries",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("player_actor_id", sa.Uuid(), nullable=True),
        sa.Column("entry_kind", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("source_event_id", sa.Uuid(), nullable=True),
        sa.Column("source_ref", sa.String(length=160), nullable=True),
        sa.Column(
            "visibility", sa.String(length=24), nullable=False, server_default="player_private"
        ),
        sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        _uuid_pk(),
        *_timestamps(),
        sa.CheckConstraint(
            "entry_kind IN ('choice', 'relationship', 'event', 'narrative', 'private_note')",
            name="ck_player_journal_entries_entry_kind",
        ),
        sa.CheckConstraint(
            "visibility IN ('player_private', 'world_admin')",
            name="ck_player_journal_entries_visibility",
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worldline_id"], ["worldlines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["player_actor_id"], ["player_actor_profiles.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["source_event_id"], ["world_events.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_player_journal_entries_worldline_user",
        "player_journal_entries",
        ["world_id", "worldline_id", "user_id"],
    )
    op.create_index(
        "ix_player_journal_entries_source_event", "player_journal_entries", ["source_event_id"]
    )

    op.create_table(
        "in_world_notifications",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("notification_kind", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("source_event_id", sa.Uuid(), nullable=True),
        sa.Column("source_ref", sa.String(length=160), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="unread"),
        sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        _uuid_pk(),
        *_timestamps(),
        sa.CheckConstraint(
            "notification_kind IN ("
            "'message', 'invitation', 'rumor', 'promise', 'incident', 'intervention'"
            ")",
            name="ck_in_world_notifications_notification_kind",
        ),
        sa.CheckConstraint(
            "status IN ('unread', 'read', 'archived')",
            name="ck_in_world_notifications_status",
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worldline_id"], ["worldlines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_event_id"], ["world_events.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_in_world_notifications_worldline_user",
        "in_world_notifications",
        ["world_id", "worldline_id", "user_id"],
    )
    op.create_index(
        "ix_in_world_notifications_source_event", "in_world_notifications", ["source_event_id"]
    )

    op.create_table(
        "player_intervention_records",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("player_actor_id", sa.Uuid(), nullable=False),
        sa.Column("intervention_kind", sa.String(length=32), nullable=False),
        sa.Column("target_agent_id", sa.Uuid(), nullable=True),
        sa.Column("target_scene_id", sa.Uuid(), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("choice_id", sa.Uuid(), nullable=True),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="recorded"),
        sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        _uuid_pk(),
        *_timestamps(),
        sa.CheckConstraint(
            "intervention_kind IN ('observe', 'reply', 'travel', 'contact', 'push_event')",
            name="ck_player_intervention_records_intervention_kind",
        ),
        sa.CheckConstraint(
            "status IN ('recorded', 'resolved', 'cancelled')",
            name="ck_player_intervention_records_status",
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worldline_id"], ["worldlines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["player_actor_id"], ["player_actor_profiles.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["target_agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_scene_id"], ["scenes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["choice_id"], ["player_choice_records.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["event_id"], ["world_events.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_player_intervention_records_worldline_user",
        "player_intervention_records",
        ["world_id", "worldline_id", "user_id"],
    )
    op.create_index(
        "ix_player_intervention_records_choice", "player_intervention_records", ["choice_id"]
    )

    op.create_table(
        "gm_style_reviews",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("source_kind", sa.String(length=40), nullable=False),
        sa.Column("source_ref", sa.String(length=160), nullable=True),
        sa.Column("reviewed_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("diagnostics", _json_type(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        _uuid_pk(),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('pass', 'warning', 'fail')", name="ck_gm_style_reviews_status"
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worldline_id"], ["worldlines.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_gm_style_reviews_worldline_status",
        "gm_style_reviews",
        ["world_id", "worldline_id", "status"],
    )
    op.create_index(
        "ix_gm_style_reviews_source", "gm_style_reviews", ["world_id", "source_kind", "source_ref"]
    )

    op.create_table(
        "narrative_continuity_reviews",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("artifact_id", sa.Uuid(), nullable=True),
        sa.Column("source_kind", sa.String(length=40), nullable=False),
        sa.Column("source_ref", sa.String(length=160), nullable=True),
        sa.Column("reviewed_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("issues", _json_type(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        _uuid_pk(),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('pass', 'warning', 'fail')",
            name="ck_narrative_continuity_reviews_status",
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["worldline_id"], ["worldlines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["artifact_id"], ["narrative_artifacts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_narrative_continuity_reviews_worldline_status",
        "narrative_continuity_reviews",
        ["world_id", "worldline_id", "status"],
    )
    op.create_index(
        "ix_narrative_continuity_reviews_artifact",
        "narrative_continuity_reviews",
        ["artifact_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_narrative_continuity_reviews_artifact", table_name="narrative_continuity_reviews"
    )
    op.drop_index(
        "ix_narrative_continuity_reviews_worldline_status",
        table_name="narrative_continuity_reviews",
    )
    op.drop_table("narrative_continuity_reviews")
    op.drop_index("ix_gm_style_reviews_source", table_name="gm_style_reviews")
    op.drop_index("ix_gm_style_reviews_worldline_status", table_name="gm_style_reviews")
    op.drop_table("gm_style_reviews")
    op.drop_index("ix_player_intervention_records_choice", table_name="player_intervention_records")
    op.drop_index(
        "ix_player_intervention_records_worldline_user",
        table_name="player_intervention_records",
    )
    op.drop_table("player_intervention_records")
    op.drop_index("ix_in_world_notifications_source_event", table_name="in_world_notifications")
    op.drop_index("ix_in_world_notifications_worldline_user", table_name="in_world_notifications")
    op.drop_table("in_world_notifications")
    op.drop_index("ix_player_journal_entries_source_event", table_name="player_journal_entries")
    op.drop_index("ix_player_journal_entries_worldline_user", table_name="player_journal_entries")
    op.drop_table("player_journal_entries")
    op.drop_index(
        "ix_relationship_repair_records_relationship", table_name="relationship_repair_records"
    )
    op.drop_index(
        "ix_relationship_repair_records_worldline_status",
        table_name="relationship_repair_records",
    )
    op.drop_table("relationship_repair_records")
    op.drop_index(
        "ix_character_emotional_states_worldline_agent", table_name="character_emotional_states"
    )
    op.drop_table("character_emotional_states")
    op.drop_index("ix_secret_records_worldline_visibility", table_name="secret_records")
    op.drop_index("ix_secret_records_worldline_status", table_name="secret_records")
    op.drop_table("secret_records")
    op.drop_index(
        "ix_character_knowledge_facts_worldline_kind", table_name="character_knowledge_facts"
    )
    op.drop_index(
        "ix_character_knowledge_facts_worldline_agent", table_name="character_knowledge_facts"
    )
    op.drop_table("character_knowledge_facts")
