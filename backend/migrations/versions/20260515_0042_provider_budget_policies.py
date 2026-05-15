"""Add provider budget policies.

Revision ID: 20260515_0042
Revises: 20260515_0041
Create Date: 2026-05-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260515_0042"
down_revision: str | None = "20260515_0041"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "provider_budget_policies",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("provider_id", sa.Uuid(), nullable=True),
        sa.Column("policy_key", sa.String(length=120), nullable=False),
        sa.Column(
            "status",
            sa.String(length=24),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column(
            "emergency_stop_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("limits", JSONB, nullable=False),
        sa.Column("metadata", JSONB, nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('active', 'disabled', 'deleted')",
            name=op.f("ck_provider_budget_policies_status"),
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            ["provider_integrations.id"],
            name=op.f("fk_provider_budget_policies_provider_id_provider_integrations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_provider_budget_policies_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_provider_budget_policies")),
        sa.UniqueConstraint(
            "world_id",
            "provider_id",
            "policy_key",
            name="uq_provider_budget_key",
        ),
    )
    op.create_index(
        "ix_provider_budget_world_status",
        "provider_budget_policies",
        ["world_id", "status"],
    )
    op.create_index(
        "ix_provider_budget_provider_status",
        "provider_budget_policies",
        ["provider_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_provider_budget_provider_status", table_name="provider_budget_policies")
    op.drop_index("ix_provider_budget_world_status", table_name="provider_budget_policies")
    op.drop_table("provider_budget_policies")
