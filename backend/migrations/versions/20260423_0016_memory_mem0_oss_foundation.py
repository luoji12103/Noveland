"""Add Mem0-first long-term memory foundation tables.

Revision ID: 20260423_0016
Revises: 20260422_0015
Create Date: 2026-04-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260423_0016"
down_revision: str | None = "20260422_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _json_type() -> postgresql.JSONB | sa.JSON:
    return postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "memory_backend_profiles",
        sa.Column("profile_key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("backend_kind", sa.String(length=32), nullable=False),
        sa.Column(
            "vector_store_config", _json_type(), nullable=False, server_default=sa.text("'{}'")
        ),
        sa.Column("llm_config", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("embedder_config", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("reranker_config", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("secret_refs", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("backend_kind IN ('mem0_oss', 'local_pgvector')", name="backend_kind"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_key", name="uq_memory_backend_profiles_profile_key"),
    )

    with op.batch_alter_table("memory_backend_profiles") as batch_op:
        batch_op.alter_column("vector_store_config", server_default=None)
        batch_op.alter_column("llm_config", server_default=None)
        batch_op.alter_column("embedder_config", server_default=None)
        batch_op.alter_column("reranker_config", server_default=None)
        batch_op.alter_column("secret_refs", server_default=None)
        batch_op.alter_column("is_enabled", server_default=None)

    with op.batch_alter_table("worlds") as batch_op:
        batch_op.add_column(sa.Column("memory_backend_profile_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_worlds_memory_backend_profile_id_memory_backend_profiles",
            "memory_backend_profiles",
            ["memory_backend_profile_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index(
        "ix_worlds_memory_backend_profile_id",
        "worlds",
        ["memory_backend_profile_id"],
        unique=False,
    )

    op.create_table(
        "memory_write_jobs",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("backend_profile_id", sa.Uuid(), nullable=False),
        sa.Column("source_kind", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("payload_json", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("dedupe_key", sa.String(length=240), nullable=False),
        sa.Column(
            "status", sa.String(length=16), nullable=False, server_default=sa.text("'pending'")
        ),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "source_kind IN ('agent_run', 'conversation_turn', 'world_event')",
            name="source_kind",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'succeeded', 'failed')",
            name="status",
        ),
        sa.CheckConstraint("attempt_count >= 0", name="attempt_count_non_negative"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["backend_profile_id"],
            ["memory_backend_profiles.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedupe_key", name="uq_memory_write_jobs_dedupe_key"),
    )
    with op.batch_alter_table("memory_write_jobs") as batch_op:
        batch_op.alter_column("payload_json", server_default=None)
        batch_op.alter_column("status", server_default=None)
        batch_op.alter_column("attempt_count", server_default=None)
    op.create_index(
        "ix_memory_write_jobs_status_next_attempt_at",
        "memory_write_jobs",
        ["status", "next_attempt_at"],
        unique=False,
    )
    op.create_index(
        "ix_memory_write_jobs_world_agent",
        "memory_write_jobs",
        ["world_id", "agent_id"],
        unique=False,
    )
    op.create_index(
        "ix_memory_write_jobs_backend_profile_id",
        "memory_write_jobs",
        ["backend_profile_id"],
        unique=False,
    )

    op.create_table(
        "memory_write_logs",
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("backend", sa.String(length=120), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("request_summary", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("response_summary", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("correlation_ids", _json_type(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.ForeignKeyConstraint(["job_id"], ["memory_write_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("memory_write_logs") as batch_op:
        batch_op.alter_column("request_summary", server_default=None)
        batch_op.alter_column("response_summary", server_default=None)
        batch_op.alter_column("correlation_ids", server_default=None)
    op.create_index("ix_memory_write_logs_job_id", "memory_write_logs", ["job_id"], unique=False)
    op.create_index(
        "ix_memory_write_logs_occurred_at",
        "memory_write_logs",
        ["occurred_at"],
        unique=False,
    )

    op.create_table(
        "memory_retrieval_logs",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("backend_profile_id", sa.Uuid(), nullable=True),
        sa.Column("backend", sa.String(length=120), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "selected_item_ids", _json_type(), nullable=False, server_default=sa.text("'[]'")
        ),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("context_item_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["backend_profile_id"],
            ["memory_backend_profiles.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["world_id"], ["worlds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("memory_retrieval_logs") as batch_op:
        batch_op.alter_column("hit_count", server_default=None)
        batch_op.alter_column("selected_item_ids", server_default=None)
        batch_op.alter_column("context_item_count", server_default=None)
    op.create_index(
        "ix_memory_retrieval_logs_world_agent",
        "memory_retrieval_logs",
        ["world_id", "agent_id"],
        unique=False,
    )
    op.create_index(
        "ix_memory_retrieval_logs_occurred_at",
        "memory_retrieval_logs",
        ["occurred_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_memory_retrieval_logs_occurred_at", table_name="memory_retrieval_logs")
    op.drop_index("ix_memory_retrieval_logs_world_agent", table_name="memory_retrieval_logs")
    op.drop_table("memory_retrieval_logs")

    op.drop_index("ix_memory_write_logs_occurred_at", table_name="memory_write_logs")
    op.drop_index("ix_memory_write_logs_job_id", table_name="memory_write_logs")
    op.drop_table("memory_write_logs")

    op.drop_index("ix_memory_write_jobs_backend_profile_id", table_name="memory_write_jobs")
    op.drop_index("ix_memory_write_jobs_world_agent", table_name="memory_write_jobs")
    op.drop_index("ix_memory_write_jobs_status_next_attempt_at", table_name="memory_write_jobs")
    op.drop_table("memory_write_jobs")

    op.drop_index("ix_worlds_memory_backend_profile_id", table_name="worlds")
    with op.batch_alter_table("worlds") as batch_op:
        batch_op.drop_constraint(
            "fk_worlds_memory_backend_profile_id_memory_backend_profiles",
            type_="foreignkey",
        )
        batch_op.drop_column("memory_backend_profile_id")

    op.drop_table("memory_backend_profiles")
