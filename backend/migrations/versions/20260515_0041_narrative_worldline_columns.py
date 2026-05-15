"""Add narrative artifact worldline columns.

Revision ID: 20260515_0041
Revises: 20260514_0040
Create Date: 2026-05-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260515_0041"
down_revision: str | None = "20260514_0040"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("narrative_artifacts", sa.Column("worldline_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_narrative_artifacts_worldline_id_worldlines"),
        "narrative_artifacts",
        "worldlines",
        ["worldline_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_narrative_artifacts_worldline_created_at",
        "narrative_artifacts",
        ["world_id", "worldline_id", "created_at"],
    )

    op.add_column("narrative_publications", sa.Column("worldline_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_narrative_publications_worldline_id_worldlines"),
        "narrative_publications",
        "worldlines",
        ["worldline_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_narrative_publications_worldline_status_visible",
        "narrative_publications",
        ["world_id", "worldline_id", "status", "reader_visible"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_narrative_publications_worldline_status_visible",
        table_name="narrative_publications",
    )
    op.drop_constraint(
        op.f("fk_narrative_publications_worldline_id_worldlines"),
        "narrative_publications",
        type_="foreignkey",
    )
    op.drop_column("narrative_publications", "worldline_id")

    op.drop_index("ix_narrative_artifacts_worldline_created_at", table_name="narrative_artifacts")
    op.drop_constraint(
        op.f("fk_narrative_artifacts_worldline_id_worldlines"),
        "narrative_artifacts",
        type_="foreignkey",
    )
    op.drop_column("narrative_artifacts", "worldline_id")
