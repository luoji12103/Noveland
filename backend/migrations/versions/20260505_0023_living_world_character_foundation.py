"""Add living world character foundation.

Revision ID: 20260505_0023
Revises: 20260504_0022
Create Date: 2026-05-05
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260505_0023"
down_revision: str | None = "20260504_0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _json_type() -> postgresql.JSONB | sa.JSON:
    return postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "world_bibles",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("source_material", sa.Text(), nullable=False, server_default=""),
        sa.Column("canon_timeline", _json_type(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("setting_rules", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "forbidden_changes",
            _json_type(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column(
            "sequel_boundaries",
            _json_type(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column(
            "continuity_config",
            _json_type(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
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
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("world_id", name="uq_world_bibles_world_id"),
    )
    with op.batch_alter_table("world_bibles") as batch_op:
        batch_op.alter_column("source_material", server_default=None)
        batch_op.alter_column("canon_timeline", server_default=None)
        batch_op.alter_column("setting_rules", server_default=None)
        batch_op.alter_column("forbidden_changes", server_default=None)
        batch_op.alter_column("sequel_boundaries", server_default=None)
        batch_op.alter_column("continuity_config", server_default=None)
        batch_op.alter_column("metadata", server_default=None)
    op.create_index("ix_world_bibles_world_id", "world_bibles", ["world_id"])

    with op.batch_alter_table("agents") as batch_op:
        batch_op.add_column(sa.Column("narrative_role", sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column("importance", sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column("canon_status", sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column("character_category", sa.String(length=40), nullable=True))
        batch_op.add_column(
            sa.Column(
                "character_profile",
                _json_type(),
                nullable=False,
                server_default=sa.text("'{}'"),
            ),
        )
        batch_op.alter_column("character_profile", server_default=None)
        batch_op.create_check_constraint(
            "ck_agents_narrative_role",
            sa.text(
                "narrative_role IS NULL OR narrative_role IN ("
                "'protagonist', 'main_character', 'side_character', "
                "'supporting_cast', 'ordinary_member', 'organization_member', "
                "'original_character', 'narrative_agent'"
                ")",
            ),
        )
        batch_op.create_check_constraint(
            "ck_agents_importance",
            sa.text("importance IS NULL OR importance IN ('lead', 'major', 'minor', 'background')"),
        )
        batch_op.create_check_constraint(
            "ck_agents_canon_status",
            sa.text(
                "canon_status IS NULL OR canon_status IN ("
                "'canon', 'post_canon', 'alternate', 'original_expansion'"
                ")",
            ),
        )
        batch_op.create_check_constraint(
            "ck_agents_character_category",
            sa.text(
                "character_category IS NULL OR character_category IN ("
                "'player', 'main_character', 'side_character', 'ordinary_member', "
                "'organization_member', 'original_character', 'narrative_agent'"
                ")",
            ),
        )
        batch_op.create_index("ix_agents_world_canon_status", ["world_id", "canon_status"])
        batch_op.create_index(
            "ix_agents_world_character_category",
            ["world_id", "character_category"],
        )

    op.create_table(
        "agent_relationship_edges",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("source_agent_id", sa.Uuid(), nullable=False),
        sa.Column("target_agent_id", sa.Uuid(), nullable=False),
        sa.Column("relationship_type", sa.String(length=40), nullable=False),
        sa.Column("affection", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trust", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hostility", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("intimacy", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("obligation", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rivalry", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("debt", sa.Integer(), nullable=False, server_default="0"),
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
            "source_agent_id <> target_agent_id",
            name="ck_agent_relationship_edges_distinct_agents",
        ),
        sa.CheckConstraint(
            "relationship_type IN ('affection', 'friendship', 'rivalry', 'family', "
            "'alliance', 'hostility', 'obligation', 'debt', 'secret', 'custom')",
            name="ck_agent_relationship_edges_relationship_type",
        ),
        sa.CheckConstraint(
            "affection >= -100 AND affection <= 100",
            name="ck_agent_relationship_edges_affection_range",
        ),
        sa.CheckConstraint(
            "trust >= -100 AND trust <= 100",
            name="ck_agent_relationship_edges_trust_range",
        ),
        sa.CheckConstraint(
            "hostility >= 0 AND hostility <= 100",
            name="ck_agent_relationship_edges_hostility_range",
        ),
        sa.CheckConstraint(
            "intimacy >= 0 AND intimacy <= 100",
            name="ck_agent_relationship_edges_intimacy_range",
        ),
        sa.CheckConstraint(
            "obligation >= 0 AND obligation <= 100",
            name="ck_agent_relationship_edges_obligation_range",
        ),
        sa.CheckConstraint(
            "rivalry >= 0 AND rivalry <= 100",
            name="ck_agent_relationship_edges_rivalry_range",
        ),
        sa.CheckConstraint(
            "debt >= 0 AND debt <= 100",
            name="ck_agent_relationship_edges_debt_range",
        ),
        sa.ForeignKeyConstraint(["source_agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_agent_id",
            "target_agent_id",
            "relationship_type",
            name="uq_agent_relationship_edges_source_target_type",
        ),
    )
    with op.batch_alter_table("agent_relationship_edges") as batch_op:
        batch_op.alter_column("affection", server_default=None)
        batch_op.alter_column("trust", server_default=None)
        batch_op.alter_column("hostility", server_default=None)
        batch_op.alter_column("intimacy", server_default=None)
        batch_op.alter_column("obligation", server_default=None)
        batch_op.alter_column("rivalry", server_default=None)
        batch_op.alter_column("debt", server_default=None)
        batch_op.alter_column("metadata", server_default=None)
    op.create_index(
        "ix_agent_relationship_edges_world_source",
        "agent_relationship_edges",
        ["world_id", "source_agent_id"],
    )
    op.create_index(
        "ix_agent_relationship_edges_world_target",
        "agent_relationship_edges",
        ["world_id", "target_agent_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_agent_relationship_edges_world_target", table_name="agent_relationship_edges")
    op.drop_index("ix_agent_relationship_edges_world_source", table_name="agent_relationship_edges")
    op.drop_table("agent_relationship_edges")

    with op.batch_alter_table("agents") as batch_op:
        batch_op.drop_index("ix_agents_world_character_category")
        batch_op.drop_index("ix_agents_world_canon_status")
        batch_op.drop_constraint("ck_agents_character_category", type_="check")
        batch_op.drop_constraint("ck_agents_canon_status", type_="check")
        batch_op.drop_constraint("ck_agents_importance", type_="check")
        batch_op.drop_constraint("ck_agents_narrative_role", type_="check")
        batch_op.drop_column("character_profile")
        batch_op.drop_column("character_category")
        batch_op.drop_column("canon_status")
        batch_op.drop_column("importance")
        batch_op.drop_column("narrative_role")

    op.drop_index("ix_world_bibles_world_id", table_name="world_bibles")
    op.drop_table("world_bibles")
