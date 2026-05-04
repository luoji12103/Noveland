"""Add plugin runtime diagnostic component.

Revision ID: 20260504_0022
Revises: 20260504_0021
Create Date: 2026-05-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260504_0022"
down_revision: str | None = "20260504_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("runtime_diagnostic_events") as batch_op:
        batch_op.drop_constraint("ck_runtime_diagnostic_events_component", type_="check")
        batch_op.create_check_constraint(
            "ck_runtime_diagnostic_events_component",
            sa.text(
                "component IN ("
                "'runtime', "
                "'provider', "
                "'agent', "
                "'conversation', "
                "'event_publisher', "
                "'api', "
                "'plugin'"
                ")",
            ),
        )


def downgrade() -> None:
    with op.batch_alter_table("runtime_diagnostic_events") as batch_op:
        batch_op.drop_constraint("ck_runtime_diagnostic_events_component", type_="check")
        batch_op.create_check_constraint(
            "ck_runtime_diagnostic_events_component",
            sa.text(
                "component IN ("
                "'runtime', "
                "'provider', "
                "'agent', "
                "'conversation', "
                "'event_publisher', "
                "'api'"
                ")",
            ),
        )
