"""Add agent presets and world composition provenance.

Revision ID: 20260422_0014
Revises: 20260421_0013
Create Date: 2026-04-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260422_0014"
down_revision: str | None = "20260421_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_presets",
        sa.Column(
            "preset_key",
            sa.String(length=80),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("default_kind", sa.String(length=32), nullable=False),
        sa.Column("default_provider_profile_key", sa.String(length=80), nullable=True),
        sa.Column("persona_text", sa.Text(), nullable=False),
        sa.Column(
            "behavior_policy",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=False,
        ),
        sa.Column(
            "calendar_blueprint",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=False,
        ),
        sa.Column(
            "advanced_config",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_agent_presets"),
        sa.UniqueConstraint("preset_key", name="uq_agent_presets_preset_key"),
        sa.CheckConstraint(
            "default_kind IN ('role_agent', 'narrative_agent')",
            name="ck_agent_presets_default_kind",
        ),
    )
    op.create_index("ix_agent_presets_is_active", "agent_presets", ["is_active"], unique=False)

    with op.batch_alter_table("agents") as batch_op:
        batch_op.add_column(sa.Column("source_preset_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_agents_source_preset_id_agent_presets",
            "agent_presets",
            ["source_preset_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_agents_source_preset_id", ["source_preset_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("agents") as batch_op:
        batch_op.drop_index("ix_agents_source_preset_id")
        batch_op.drop_constraint("fk_agents_source_preset_id_agent_presets", type_="foreignkey")
        batch_op.drop_column("source_preset_id")

    op.drop_index("ix_agent_presets_is_active", table_name="agent_presets")
    op.drop_table("agent_presets")
