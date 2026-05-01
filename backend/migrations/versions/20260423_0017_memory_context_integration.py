"""Add conversation memory configuration.

Revision ID: 20260423_0017
Revises: 20260423_0016
Create Date: 2026-04-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260423_0017"
down_revision: str | None = "20260423_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("conversation_sessions") as batch_op:
        batch_op.add_column(
            sa.Column(
                "memory_config",
                postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
                nullable=False,
                server_default=sa.text("'{}'"),
            ),
        )
        batch_op.alter_column("memory_config", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("conversation_sessions") as batch_op:
        batch_op.drop_column("memory_config")
