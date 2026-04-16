"""Add world event log and snapshot metadata tables.

Revision ID: 20260416_0003
Revises: 20260415_0002
Create Date: 2026-04-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260416_0003"
down_revision: str | None = "20260415_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def common_columns() -> list[sa.Column[object]]:
    return [
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
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


def upgrade() -> None:
    op.create_table(
        "world_events",
        *common_columns(),
        sa.Column("world_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.BigInteger(), nullable=False),
        sa.Column("event_name", sa.String(length=120), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("wall_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("world_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actor_ref", sa.String(length=120), nullable=False),
        sa.Column("causation_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint("sequence > 0", name="ck_world_events_sequence_positive"),
        sa.CheckConstraint(
            "event_name ~ '^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)+$'",
            name="ck_world_events_event_name_format",
        ),
        sa.ForeignKeyConstraint(
            ["causation_event_id"],
            ["world_events.id"],
            name="fk_world_events_causation_event_id_world_events",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name="fk_world_events_world_id_worlds",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_world_events"),
        sa.UniqueConstraint("world_id", "sequence", name="uq_world_events_world_sequence"),
    )
    op.create_index("ix_world_events_world_sequence", "world_events", ["world_id", "sequence"])
    op.create_index("ix_world_events_world_event_name", "world_events", ["world_id", "event_name"])
    op.create_index("ix_world_events_world_wall_time", "world_events", ["world_id", "wall_time"])

    op.create_table(
        "world_snapshots",
        *common_columns(),
        sa.Column("world_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("covers_event_sequence", sa.BigInteger(), nullable=False),
        sa.Column("schema_version", sa.String(length=80), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default=sa.text("'valid'"),
            nullable=False,
        ),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("payload_uri", sa.String(length=500), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_by_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.CheckConstraint(
            "covers_event_sequence >= 0",
            name="ck_world_snapshots_covers_event_sequence_nonnegative",
        ),
        sa.CheckConstraint(
            "status IN ('valid', 'invalid')",
            name="ck_world_snapshots_status",
        ),
        sa.CheckConstraint(
            "payload IS NOT NULL OR payload_uri IS NOT NULL",
            name="ck_world_snapshots_payload_or_uri",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_event_id"],
            ["world_events.id"],
            name="fk_world_snapshots_created_by_event_id_world_events",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name="fk_world_snapshots_world_id_worlds",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_world_snapshots"),
    )
    op.create_index(
        "ix_world_snapshots_world_sequence",
        "world_snapshots",
        ["world_id", "covers_event_sequence"],
    )
    op.create_index(
        "ix_world_snapshots_world_latest_valid",
        "world_snapshots",
        ["world_id", "status", "covers_event_sequence"],
    )


def downgrade() -> None:
    op.drop_index("ix_world_snapshots_world_latest_valid", table_name="world_snapshots")
    op.drop_index("ix_world_snapshots_world_sequence", table_name="world_snapshots")
    op.drop_table("world_snapshots")

    op.drop_index("ix_world_events_world_wall_time", table_name="world_events")
    op.drop_index("ix_world_events_world_event_name", table_name="world_events")
    op.drop_index("ix_world_events_world_sequence", table_name="world_events")
    op.drop_table("world_events")
