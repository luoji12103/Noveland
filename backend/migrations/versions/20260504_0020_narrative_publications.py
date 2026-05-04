"""Add narrative publication workflow table.

Revision ID: 20260504_0020
Revises: 20260503_0019
Create Date: 2026-05-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260504_0020"
down_revision: str | None = "20260503_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _json_type() -> postgresql.JSONB | sa.JSON:
    return postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "narrative_publications",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("artifact_id", sa.Uuid(), nullable=False),
        sa.Column("source_draft_id", sa.Uuid(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'published'"),
        ),
        sa.Column("reader_visible", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("metadata", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("unpublished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
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
        sa.CheckConstraint("status IN ('published', 'unpublished')", name="status"),
        sa.ForeignKeyConstraint(["artifact_id"], ["narrative_artifacts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["published_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_draft_id"], ["narrative_artifacts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("artifact_id", name="uq_narrative_publications_artifact_id"),
    )
    with op.batch_alter_table("narrative_publications") as batch_op:
        batch_op.alter_column("status", server_default=None)
        batch_op.alter_column("reader_visible", server_default=None)
        batch_op.alter_column("metadata", server_default=None)

    op.create_index(
        "ix_narrative_publications_world_status_visible",
        "narrative_publications",
        ["world_id", "status", "reader_visible"],
        unique=False,
    )
    op.create_index(
        "ix_narrative_publications_world_published_at",
        "narrative_publications",
        ["world_id", "published_at"],
        unique=False,
    )
    op.create_index(
        "ix_narrative_publications_source_draft",
        "narrative_publications",
        ["source_draft_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_narrative_publications_source_draft", table_name="narrative_publications")
    op.drop_index(
        "ix_narrative_publications_world_published_at",
        table_name="narrative_publications",
    )
    op.drop_index(
        "ix_narrative_publications_world_status_visible",
        table_name="narrative_publications",
    )
    op.drop_table("narrative_publications")
