"""Add provider reliability fields.

Revision ID: 20260417_0009
Revises: 20260417_0008
Create Date: 2026-04-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260417_0009"
down_revision: str | None = "20260417_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "provider_profiles",
        sa.Column(
            "timeout_seconds",
            sa.Integer(),
            server_default=sa.text("20"),
            nullable=False,
        ),
    )
    op.add_column(
        "provider_profiles",
        sa.Column(
            "retry_attempts",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
    )
    op.add_column(
        "provider_profiles",
        sa.Column("rate_limit_per_minute", sa.Integer(), nullable=True),
    )
    op.add_column(
        "provider_profiles",
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "provider_profiles",
        sa.Column("last_test_status", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "provider_profiles",
        sa.Column("last_test_error", sa.Text(), nullable=True),
    )
    op.create_check_constraint(
        "ck_provider_profiles_timeout_seconds_positive",
        "provider_profiles",
        "timeout_seconds > 0",
    )
    op.create_check_constraint(
        "ck_provider_profiles_retry_attempts_non_negative",
        "provider_profiles",
        "retry_attempts >= 0",
    )
    op.create_check_constraint(
        "ck_provider_profiles_rate_limit_per_minute_positive",
        "provider_profiles",
        "rate_limit_per_minute IS NULL OR rate_limit_per_minute > 0",
    )
    op.create_check_constraint(
        "ck_provider_profiles_last_test_status",
        "provider_profiles",
        "last_test_status IS NULL OR last_test_status IN ('success', 'failed')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_provider_profiles_last_test_status",
        "provider_profiles",
        type_="check",
    )
    op.drop_constraint(
        "ck_provider_profiles_rate_limit_per_minute_positive",
        "provider_profiles",
        type_="check",
    )
    op.drop_constraint(
        "ck_provider_profiles_retry_attempts_non_negative",
        "provider_profiles",
        type_="check",
    )
    op.drop_constraint(
        "ck_provider_profiles_timeout_seconds_positive",
        "provider_profiles",
        type_="check",
    )
    op.drop_column("provider_profiles", "last_test_error")
    op.drop_column("provider_profiles", "last_test_status")
    op.drop_column("provider_profiles", "last_tested_at")
    op.drop_column("provider_profiles", "rate_limit_per_minute")
    op.drop_column("provider_profiles", "retry_attempts")
    op.drop_column("provider_profiles", "timeout_seconds")
