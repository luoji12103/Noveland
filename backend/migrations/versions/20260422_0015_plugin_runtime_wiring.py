"""Add explicit plugin bindings and backfill built-in identifiers.

Revision ID: 20260422_0015
Revises: 20260422_0014
Create Date: 2026-04-22
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260422_0015"
down_revision: str | None = "20260422_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BUILTIN_OPENAI_COMPATIBLE = "builtin.openai_compatible"
BUILTIN_ANTHROPIC_COMPATIBLE = "builtin.anthropic_compatible"
BUILTIN_LOCAL_PGVECTOR_MEMORY = "builtin.local_pgvector_memory"
BUILTIN_DEFAULT_WORLD_RULES = "builtin.default_world_rules"
BUILTIN_DEFAULT_PERSONA_POLICY = "builtin.default_persona_policy"
BUILTIN_DEFAULT_NARRATIVE_WRITER = "builtin.default_narrative_writer"


def upgrade() -> None:
    with op.batch_alter_table("provider_profiles") as batch_op:
        batch_op.add_column(
            sa.Column(
                "plugin_identifier",
                sa.String(length=120),
                nullable=False,
                server_default=sa.text(f"'{BUILTIN_OPENAI_COMPATIBLE}'"),
            ),
        )
        batch_op.add_column(
            sa.Column(
                "plugin_config",
                postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
                nullable=False,
                server_default=sa.text("'{}'"),
            ),
        )

    with op.batch_alter_table("worlds") as batch_op:
        batch_op.add_column(
            sa.Column(
                "memory_plugin_identifier",
                sa.String(length=120),
                nullable=False,
                server_default=sa.text(f"'{BUILTIN_LOCAL_PGVECTOR_MEMORY}'"),
            ),
        )
        batch_op.add_column(
            sa.Column(
                "memory_plugin_config",
                postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
                nullable=False,
                server_default=sa.text("'{}'"),
            ),
        )
        batch_op.add_column(
            sa.Column(
                "world_rules_plugin_identifier",
                sa.String(length=120),
                nullable=False,
                server_default=sa.text(f"'{BUILTIN_DEFAULT_WORLD_RULES}'"),
            ),
        )
        batch_op.add_column(
            sa.Column(
                "world_rules_plugin_config",
                postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
                nullable=False,
                server_default=sa.text("'{}'"),
            ),
        )

    with op.batch_alter_table("agent_personas") as batch_op:
        batch_op.add_column(
            sa.Column(
                "policy_plugin_identifier",
                sa.String(length=120),
                nullable=False,
                server_default=sa.text(f"'{BUILTIN_DEFAULT_PERSONA_POLICY}'"),
            ),
        )
        batch_op.add_column(
            sa.Column(
                "policy_plugin_config",
                postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
                nullable=False,
                server_default=sa.text("'{}'"),
            ),
        )

    _backfill_provider_plugins()
    _backfill_writer_config()

    with op.batch_alter_table("provider_profiles") as batch_op:
        batch_op.alter_column("plugin_identifier", server_default=None)
        batch_op.alter_column("plugin_config", server_default=None)

    with op.batch_alter_table("worlds") as batch_op:
        batch_op.alter_column("memory_plugin_identifier", server_default=None)
        batch_op.alter_column("memory_plugin_config", server_default=None)
        batch_op.alter_column("world_rules_plugin_identifier", server_default=None)
        batch_op.alter_column("world_rules_plugin_config", server_default=None)

    with op.batch_alter_table("agent_personas") as batch_op:
        batch_op.alter_column("policy_plugin_identifier", server_default=None)
        batch_op.alter_column("policy_plugin_config", server_default=None)


def downgrade() -> None:
    _strip_writer_config_fields()

    with op.batch_alter_table("agent_personas") as batch_op:
        batch_op.drop_column("policy_plugin_config")
        batch_op.drop_column("policy_plugin_identifier")

    with op.batch_alter_table("worlds") as batch_op:
        batch_op.drop_column("world_rules_plugin_config")
        batch_op.drop_column("world_rules_plugin_identifier")
        batch_op.drop_column("memory_plugin_config")
        batch_op.drop_column("memory_plugin_identifier")

    with op.batch_alter_table("provider_profiles") as batch_op:
        batch_op.drop_column("plugin_config")
        batch_op.drop_column("plugin_identifier")


def _backfill_provider_plugins() -> None:
    bind = op.get_bind()
    provider_profiles = sa.table(
        "provider_profiles",
        sa.column("id", sa.Uuid()),
        sa.column("provider_type", sa.String()),
        sa.column("plugin_identifier", sa.String()),
        sa.column("plugin_config", sa.JSON()),
    )
    rows = bind.execute(
        sa.select(
            provider_profiles.c.id,
            provider_profiles.c.provider_type,
        ),
    ).all()
    for row in rows:
        plugin_identifier = (
            BUILTIN_ANTHROPIC_COMPATIBLE
            if row.provider_type == "anthropic_compatible"
            else BUILTIN_OPENAI_COMPATIBLE
        )
        bind.execute(
            sa.update(provider_profiles)
            .where(provider_profiles.c.id == row.id)
            .values(
                plugin_identifier=plugin_identifier,
                plugin_config={},
            ),
        )


def _backfill_writer_config() -> None:
    bind = op.get_bind()
    conversation_sessions = sa.table(
        "conversation_sessions",
        sa.column("id", sa.Uuid()),
        sa.column("writer_config", sa.JSON()),
    )
    rows = bind.execute(
        sa.select(conversation_sessions.c.id, conversation_sessions.c.writer_config),
    ).all()
    for row in rows:
        writer_config = _json_object(row.writer_config)
        writer_config.setdefault("writer_plugin_identifier", BUILTIN_DEFAULT_NARRATIVE_WRITER)
        writer_config.setdefault("writer_plugin_config", {})
        bind.execute(
            sa.update(conversation_sessions)
            .where(conversation_sessions.c.id == row.id)
            .values(writer_config=writer_config),
        )


def _strip_writer_config_fields() -> None:
    bind = op.get_bind()
    conversation_sessions = sa.table(
        "conversation_sessions",
        sa.column("id", sa.Uuid()),
        sa.column("writer_config", sa.JSON()),
    )
    rows = bind.execute(
        sa.select(conversation_sessions.c.id, conversation_sessions.c.writer_config),
    ).all()
    for row in rows:
        writer_config = _json_object(row.writer_config)
        writer_config.pop("writer_plugin_identifier", None)
        writer_config.pop("writer_plugin_config", None)
        bind.execute(
            sa.update(conversation_sessions)
            .where(conversation_sessions.c.id == row.id)
            .values(writer_config=writer_config),
        )


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        decoded = json.loads(value)
        if isinstance(decoded, dict):
            return dict(decoded)
    return {}
