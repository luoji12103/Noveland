"""Add conversation policies and stop conditions.

Revision ID: 20260421_0012
Revises: 20260419_0011
Create Date: 2026-04-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260421_0012"
down_revision: str | None = "20260419_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_POLICY_JSON = (
    '{"error_policy":"retry_once_then_fail",'
    '"max_consecutive_failed_turns":2,'
    '"loop_guard_window":4,'
    '"repeat_output_threshold":3}'
)


def upgrade() -> None:
    with op.batch_alter_table("conversation_sessions") as batch_op:
        batch_op.add_column(
            sa.Column(
                "policy_config",
                postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
                nullable=False,
                server_default=sa.text(f"'{DEFAULT_POLICY_JSON}'"),
            ),
        )
        batch_op.add_column(sa.Column("terminal_reason", sa.String(length=64), nullable=True))
        batch_op.drop_constraint("ck_conversation_sessions_status", type_="check")
        batch_op.create_check_constraint(
            "ck_conversation_sessions_status",
            "status IN ('draft', 'running', 'paused', 'completed', 'stopped', 'failed')",
        )
        batch_op.create_check_constraint(
            "ck_conversation_sessions_terminal_reason",
            "terminal_reason IN ("
            "'max_turns_reached', "
            "'loop_guard_repeated_output', "
            "'no_enabled_participants', "
            "'consecutive_failures_exceeded', "
            "'operator_stopped', "
            "'speaker_error'"
            ") OR terminal_reason IS NULL",
        )
        batch_op.alter_column("policy_config", server_default=None)

    with op.batch_alter_table("conversation_turns") as batch_op:
        batch_op.drop_constraint("ck_conversation_turns_status", type_="check")
        batch_op.create_check_constraint(
            "ck_conversation_turns_status",
            "status IN ('succeeded', 'skipped', 'failed')",
        )

    with op.batch_alter_table("runtime_diagnostic_events") as batch_op:
        batch_op.drop_constraint("ck_runtime_diagnostic_events_component", type_="check")
        batch_op.create_check_constraint(
            "ck_runtime_diagnostic_events_component",
            "component IN ("
            "'runtime', "
            "'provider', "
            "'agent', "
            "'conversation', "
            "'event_publisher', "
            "'api'"
            ")",
        )


def downgrade() -> None:
    with op.batch_alter_table("runtime_diagnostic_events") as batch_op:
        batch_op.drop_constraint("ck_runtime_diagnostic_events_component", type_="check")
        batch_op.create_check_constraint(
            "ck_runtime_diagnostic_events_component",
            "component IN ('runtime', 'provider', 'agent', 'event_publisher', 'api')",
        )

    with op.batch_alter_table("conversation_turns") as batch_op:
        batch_op.drop_constraint("ck_conversation_turns_status", type_="check")
        batch_op.create_check_constraint(
            "ck_conversation_turns_status",
            "status IN ('succeeded', 'failed')",
        )

    with op.batch_alter_table("conversation_sessions") as batch_op:
        batch_op.drop_constraint("ck_conversation_sessions_terminal_reason", type_="check")
        batch_op.drop_constraint("ck_conversation_sessions_status", type_="check")
        batch_op.create_check_constraint(
            "ck_conversation_sessions_status",
            "status IN ('draft', 'running', 'paused', 'completed', 'failed')",
        )
        batch_op.drop_column("terminal_reason")
        batch_op.drop_column("policy_config")
