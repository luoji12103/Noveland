"""Add agent preset version provenance.

Revision ID: 20260504_0021
Revises: 20260504_0020
Create Date: 2026-05-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260504_0021"
down_revision: str | None = "20260504_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("agent_presets") as batch_op:
        batch_op.add_column(
            sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        )
        batch_op.alter_column("version", server_default=None)

    with op.batch_alter_table("agents") as batch_op:
        batch_op.add_column(sa.Column("source_preset_version", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("agents") as batch_op:
        batch_op.drop_column("source_preset_version")

    with op.batch_alter_table("agent_presets") as batch_op:
        batch_op.drop_column("version")
