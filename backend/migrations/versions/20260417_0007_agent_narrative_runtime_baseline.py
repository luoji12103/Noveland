"""Add provider profiles, runtime control, agent runs, and narrative artifacts.

Revision ID: 20260417_0007
Revises: 20260417_0006
Create Date: 2026-04-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260417_0007"
down_revision: str | None = "20260417_0006"
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
        "provider_profiles",
        *common_columns(),
        sa.Column("profile_key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("provider_type", sa.String(length=32), nullable=False),
        sa.Column("base_url", sa.String(length=500), nullable=False),
        sa.Column("model_name", sa.String(length=200), nullable=False),
        sa.Column("capabilities", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("api_key_ref", sa.String(length=120), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.CheckConstraint(
            "provider_type IN ('openai_compatible', 'anthropic_compatible')",
            name="ck_provider_profiles_provider_type",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_provider_profiles"),
        sa.UniqueConstraint("profile_key", name="uq_provider_profiles_profile_key"),
    )

    op.create_table(
        "runtime_control_states",
        *common_columns(),
        sa.Column(
            "control_key",
            sa.String(length=32),
            server_default=sa.text("'default'"),
            nullable=False,
        ),
        sa.Column(
            "desired_state",
            sa.String(length=16),
            server_default=sa.text("'stopped'"),
            nullable=False,
        ),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "desired_state IN ('running', 'stopped')",
            name="ck_runtime_control_states_desired_state",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_runtime_control_states"),
        sa.UniqueConstraint("control_key", name="uq_runtime_control_states_control_key"),
    )

    op.create_table(
        "agent_runtime_runs",
        *common_columns(),
        sa.Column("world_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_calendar_entry_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_schedule_rule_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("trigger_source", sa.String(length=32), nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=True),
        sa.Column("diagnostics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'failed')",
            name="ck_agent_runtime_runs_status",
        ),
        sa.CheckConstraint(
            "trigger_source IN ('manual', 'calendar_entry', 'schedule_rule', 'runtime_tick')",
            name="ck_agent_runtime_runs_trigger_source",
        ),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["agents.id"],
            name="fk_agent_runtime_runs_agent_id_agents",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_event_id"],
            ["world_events.id"],
            name="fk_agent_runtime_runs_created_event_id_world_events",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["provider_profile_id"],
            ["provider_profiles.id"],
            name="fk_agent_runtime_runs_provider_profile_id_provider_profiles",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_calendar_entry_id"],
            ["agent_calendar_entries.id"],
            name="fk_agent_runtime_runs_source_calendar_entry_id_agent_calendar_entries",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_schedule_rule_id"],
            ["world_schedule_rules.id"],
            name="fk_agent_runtime_runs_source_schedule_rule_id_world_schedule_rules",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name="fk_agent_runtime_runs_world_id_worlds",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_agent_runtime_runs"),
    )
    op.create_index(
        "ix_agent_runtime_runs_world_agent_started_at",
        "agent_runtime_runs",
        ["world_id", "agent_id", "started_at"],
    )
    op.create_index(
        "ix_agent_runtime_runs_provider_profile_id",
        "agent_runtime_runs",
        ["provider_profile_id"],
    )

    op.create_table(
        "narrative_artifacts",
        *common_columns(),
        sa.Column("world_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("artifact_kind", sa.String(length=32), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.CheckConstraint(
            "artifact_kind IN ('agent_note', 'world_summary')",
            name="ck_narrative_artifacts_artifact_kind",
        ),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["agents.id"],
            name="fk_narrative_artifacts_agent_id_agents",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_run_id"],
            ["agent_runtime_runs.id"],
            name="fk_narrative_artifacts_source_run_id_agent_runtime_runs",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name="fk_narrative_artifacts_world_id_worlds",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_narrative_artifacts"),
    )
    op.create_index(
        "ix_narrative_artifacts_world_created_at",
        "narrative_artifacts",
        ["world_id", "created_at"],
    )
    op.create_index(
        "ix_narrative_artifacts_world_agent",
        "narrative_artifacts",
        ["world_id", "agent_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_narrative_artifacts_world_agent", table_name="narrative_artifacts")
    op.drop_index("ix_narrative_artifacts_world_created_at", table_name="narrative_artifacts")
    op.drop_table("narrative_artifacts")
    op.drop_index("ix_agent_runtime_runs_provider_profile_id", table_name="agent_runtime_runs")
    op.drop_index("ix_agent_runtime_runs_world_agent_started_at", table_name="agent_runtime_runs")
    op.drop_table("agent_runtime_runs")
    op.drop_table("runtime_control_states")
    op.drop_table("provider_profiles")
