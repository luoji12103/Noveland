"""Add provider execution kernel.

Revision ID: 20260512_0034
Revises: 20260512_0033
Create Date: 2026-05-12
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260512_0034"
down_revision: str | None = "20260512_0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


JSONB = postgresql.JSONB(astext_type=sa.Text())
PROVIDER_SCOPE = "'global', 'world'"
PROVIDER_KIND = (
    "'text_generation', 'image_generation', 'image_editing', 'image_analysis', "
    "'image_composition', 'speech_to_text', 'text_to_speech', 'voice_cloning', "
    "'background_removal', 'workflow_engine', 'embedding', 'reranker', 'other'"
)
ADAPTER_KIND = (
    "'fake', 'openai', 'openai_compatible', 'anthropic', 'anthropic_compatible', "
    "'comfyui', 'mimo_tts', 'mimo_asr', 'omnivoice', 'gpt_sovits', 'rembg', "
    "'sam2', 'custom_http', 'local_stub', 'other'"
)
PROVIDER_STATUS = "'draft', 'active', 'disabled', 'deleted'"
PROVIDER_VISIBILITY = "'private', 'world_admin', 'developer_only', 'hidden'"
HEALTH_STATUS = "'healthy', 'degraded', 'unhealthy', 'unknown'"


def upgrade() -> None:
    op.create_table(
        "provider_integrations",
        sa.Column("world_id", sa.Uuid(), nullable=True),
        sa.Column("scope_kind", sa.String(length=16), nullable=False),
        sa.Column("scope_key", sa.String(length=120), nullable=False),
        sa.Column("provider_kind", sa.String(length=40), nullable=False),
        sa.Column("adapter_kind", sa.String(length=40), nullable=False),
        sa.Column("provider_key", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("base_url", sa.String(length=500), nullable=True),
        sa.Column("auth_ref", sa.String(length=200), nullable=True),
        sa.Column("config_json", JSONB, nullable=False),
        sa.Column("default_params_json", JSONB, nullable=False),
        sa.Column(
            "status",
            sa.String(length=24),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column(
            "visibility",
            sa.String(length=32),
            server_default=sa.text("'world_admin'"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            f"scope_kind IN ({PROVIDER_SCOPE})",
            name=op.f("ck_provider_integrations_scope_kind"),
        ),
        sa.CheckConstraint(
            f"provider_kind IN ({PROVIDER_KIND})",
            name=op.f("ck_provider_integrations_provider_kind"),
        ),
        sa.CheckConstraint(
            f"adapter_kind IN ({ADAPTER_KIND})",
            name=op.f("ck_provider_integrations_adapter_kind"),
        ),
        sa.CheckConstraint(
            f"status IN ({PROVIDER_STATUS})",
            name=op.f("ck_provider_integrations_status"),
        ),
        sa.CheckConstraint(
            f"visibility IN ({PROVIDER_VISIBILITY})",
            name=op.f("ck_provider_integrations_visibility"),
        ),
        sa.CheckConstraint(
            "(scope_kind = 'global' AND world_id IS NULL AND scope_key = 'global') OR "
            "(scope_kind = 'world' AND world_id IS NOT NULL)",
            name=op.f("ck_provider_integrations_scope_consistency"),
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_provider_integrations_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_provider_integrations")),
        sa.UniqueConstraint(
            "scope_key",
            "provider_key",
            name="uq_provider_integrations_key",
        ),
    )
    op.create_index(
        "ix_provider_integrations_scope_status",
        "provider_integrations",
        ["scope_kind", "world_id", "status"],
    )
    op.create_index(
        "ix_provider_integrations_world_kind",
        "provider_integrations",
        ["world_id", "provider_kind", "status"],
    )
    op.create_index(
        "ix_provider_integrations_adapter",
        "provider_integrations",
        ["adapter_kind"],
    )

    op.create_table(
        "provider_capabilities",
        sa.Column("provider_integration_id", sa.Uuid(), nullable=False),
        sa.Column("capability_key", sa.String(length=120), nullable=False),
        sa.Column("capability_json", JSONB, nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["provider_integration_id"],
            ["provider_integrations.id"],
            name=op.f("fk_provider_capabilities_provider_integration_id_provider_integrations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_provider_capabilities")),
        sa.UniqueConstraint(
            "provider_integration_id",
            "capability_key",
            name="uq_provider_capabilities_key",
        ),
    )
    op.create_index(
        "ix_provider_capabilities_provider",
        "provider_capabilities",
        ["provider_integration_id"],
    )
    op.create_index("ix_provider_capabilities_key", "provider_capabilities", ["capability_key"])

    op.create_table(
        "provider_health_checks",
        sa.Column("provider_integration_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column(
            "checked_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.Column("metadata", JSONB, nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint(
            f"status IN ({HEALTH_STATUS})",
            name=op.f("ck_provider_health_checks_status"),
        ),
        sa.CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name=op.f("ck_provider_health_checks_latency_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["provider_integration_id"],
            ["provider_integrations.id"],
            name=op.f(
                "fk_provider_health_checks_provider_integration_id_provider_integrations"
            ),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_provider_health_checks")),
    )
    op.create_index(
        "ix_provider_health_checks_provider_checked",
        "provider_health_checks",
        ["provider_integration_id", "checked_at"],
    )
    op.create_index("ix_provider_health_checks_status", "provider_health_checks", ["status"])


def downgrade() -> None:
    op.drop_index("ix_provider_health_checks_status", table_name="provider_health_checks")
    op.drop_index(
        "ix_provider_health_checks_provider_checked",
        table_name="provider_health_checks",
    )
    op.drop_table("provider_health_checks")
    op.drop_index("ix_provider_capabilities_key", table_name="provider_capabilities")
    op.drop_index("ix_provider_capabilities_provider", table_name="provider_capabilities")
    op.drop_table("provider_capabilities")
    op.drop_index("ix_provider_integrations_adapter", table_name="provider_integrations")
    op.drop_index("ix_provider_integrations_world_kind", table_name="provider_integrations")
    op.drop_index("ix_provider_integrations_scope_status", table_name="provider_integrations")
    op.drop_table("provider_integrations")
