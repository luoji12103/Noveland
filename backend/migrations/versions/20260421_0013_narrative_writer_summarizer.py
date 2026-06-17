"""Add conversation writer config and conversation narrative artifacts.

Revision ID: 20260421_0013
Revises: 20260421_0012
Create Date: 2026-04-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260421_0013"
down_revision: str | None = "20260421_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SOURCE_CONVERSATION_FK_NAME = "fk_narrative_artifacts_source_conversation"

DEFAULT_WRITER_CONFIG_JSON = (
    '{"provider_profile_id":null,'
    '"auto_generate_on_complete":false,'
    '"generate_summary":true,'
    '"generate_chapter":true}'
)


def writer_config_server_default() -> sa.TextClause:
    escaped_json = DEFAULT_WRITER_CONFIG_JSON.replace(":", r"\:")
    return sa.text(f"'{escaped_json}'")


def upgrade() -> None:
    with op.batch_alter_table("conversation_sessions") as batch_op:
        batch_op.add_column(
            sa.Column(
                "writer_config",
                postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
                nullable=False,
                server_default=writer_config_server_default(),
            ),
        )
        batch_op.alter_column("writer_config", server_default=None)

    with op.batch_alter_table("narrative_artifacts") as batch_op:
        batch_op.add_column(sa.Column("source_conversation_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            SOURCE_CONVERSATION_FK_NAME,
            "conversation_sessions",
            ["source_conversation_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.drop_constraint("ck_narrative_artifacts_artifact_kind", type_="check")
        batch_op.create_check_constraint(
            "ck_narrative_artifacts_artifact_kind",
            "artifact_kind IN ("
            "'agent_note', "
            "'world_summary', "
            "'conversation_summary', "
            "'chapter_draft'"
            ")",
        )

    op.create_index(
        "ix_narrative_artifacts_world_conversation_created_at",
        "narrative_artifacts",
        ["world_id", "source_conversation_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_narrative_artifacts_world_conversation_created_at",
        table_name="narrative_artifacts",
    )

    with op.batch_alter_table("narrative_artifacts") as batch_op:
        batch_op.drop_constraint(
            SOURCE_CONVERSATION_FK_NAME,
            type_="foreignkey",
        )
        batch_op.drop_constraint("ck_narrative_artifacts_artifact_kind", type_="check")
        batch_op.create_check_constraint(
            "ck_narrative_artifacts_artifact_kind",
            "artifact_kind IN ('agent_note', 'world_summary')",
        )
        batch_op.drop_column("source_conversation_id")

    with op.batch_alter_table("conversation_sessions") as batch_op:
        batch_op.drop_column("writer_config")
