"""Add moderation incident workflow.

Revision ID: 20260516_0044
Revises: 20260516_0043
Create Date: 2026-05-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260516_0044"
down_revision: str | None = "20260516_0043"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "moderation_reports",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=True),
        sa.Column("reporter_user_id", sa.Uuid(), nullable=False),
        sa.Column("target_ref_kind", sa.String(length=80), nullable=False),
        sa.Column("target_ref_id", sa.Uuid(), nullable=True),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("reporter_note", sa.Text(), nullable=True),
        sa.Column("evidence_refs", JSONB, nullable=False),
        sa.Column("created_by_actor_ref", sa.String(length=160), nullable=False),
        sa.Column("reviewed_by_actor_ref", sa.String(length=160), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("metadata", JSONB, nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
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
        sa.CheckConstraint(
            "category IN ("
            "'safety', 'privacy', 'copyright', 'abuse', 'quality', 'security', 'other'"
            ")",
            name=op.f("ck_moderation_reports_category"),
        ),
        sa.CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name=op.f("ck_moderation_reports_severity"),
        ),
        sa.CheckConstraint(
            "status IN ('submitted', 'under_review', 'resolved', 'dismissed', 'escalated')",
            name=op.f("ck_moderation_reports_status"),
        ),
        sa.CheckConstraint(
            "target_ref_kind IN ("
            "'world', 'worldline', 'scene', 'narrative_publication', "
            "'conversation_session', 'conversation_turn', 'media_asset', "
            "'provider_integration', 'plugin_package', 'player_profile', 'other'"
            ")",
            name=op.f("ck_moderation_reports_target_ref_kind"),
        ),
        sa.ForeignKeyConstraint(
            ["reporter_user_id"],
            ["users.id"],
            name=op.f("fk_moderation_reports_reporter_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_moderation_reports_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_moderation_reports_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_moderation_reports")),
    )
    op.create_index(
        "ix_moderation_reports_world_status",
        "moderation_reports",
        ["world_id", "status"],
    )
    op.create_index(
        "ix_moderation_reports_worldline_status",
        "moderation_reports",
        ["world_id", "worldline_id", "status"],
    )
    op.create_index(
        "ix_moderation_reports_reporter",
        "moderation_reports",
        ["world_id", "reporter_user_id"],
    )
    op.create_index(
        "ix_moderation_reports_target",
        "moderation_reports",
        ["world_id", "target_ref_kind", "target_ref_id"],
    )

    op.create_table(
        "moderation_incidents",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("report_ids", JSONB, nullable=False),
        sa.Column("action_ids", JSONB, nullable=False),
        sa.Column("evidence_refs", JSONB, nullable=False),
        sa.Column("created_by_actor_ref", sa.String(length=160), nullable=False),
        sa.Column("reviewed_by_actor_ref", sa.String(length=160), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("metadata", JSONB, nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
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
        sa.CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name=op.f("ck_moderation_incidents_severity"),
        ),
        sa.CheckConstraint(
            "status IN ('open', 'under_review', 'mitigated', 'closed')",
            name=op.f("ck_moderation_incidents_status"),
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_moderation_incidents_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_moderation_incidents_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_moderation_incidents")),
    )
    op.create_index(
        "ix_moderation_incidents_world_status",
        "moderation_incidents",
        ["world_id", "status"],
    )
    op.create_index(
        "ix_moderation_incidents_worldline_status",
        "moderation_incidents",
        ["world_id", "worldline_id", "status"],
    )

    op.create_table(
        "moderation_actions",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=True),
        sa.Column("report_id", sa.Uuid(), nullable=True),
        sa.Column("incident_id", sa.Uuid(), nullable=True),
        sa.Column("action_kind", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("target_ref_kind", sa.String(length=80), nullable=False),
        sa.Column("target_ref_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("audit_summary", JSONB, nullable=False),
        sa.Column("evidence_refs", JSONB, nullable=False),
        sa.Column("created_by_actor_ref", sa.String(length=160), nullable=False),
        sa.Column("reviewed_by_actor_ref", sa.String(length=160), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("metadata", JSONB, nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
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
        sa.CheckConstraint(
            "action_kind IN ("
            "'disable_media', 'disable_world', 'disable_provider', 'rollback_review', "
            "'takedown_content', 'note_only'"
            ")",
            name=op.f("ck_moderation_actions_action_kind"),
        ),
        sa.CheckConstraint(
            "status IN ('proposed', 'approved', 'applied', 'rejected', 'canceled')",
            name=op.f("ck_moderation_actions_status"),
        ),
        sa.CheckConstraint(
            "target_ref_kind IN ("
            "'world', 'worldline', 'scene', 'narrative_publication', "
            "'conversation_session', 'conversation_turn', 'media_asset', "
            "'provider_integration', 'plugin_package', 'player_profile', 'other'"
            ")",
            name=op.f("ck_moderation_actions_target_ref_kind"),
        ),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["moderation_incidents.id"],
            name=op.f("fk_moderation_actions_incident_id_moderation_incidents"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["moderation_reports.id"],
            name=op.f("fk_moderation_actions_report_id_moderation_reports"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_moderation_actions_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_moderation_actions_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_moderation_actions")),
    )
    op.create_index(
        "ix_moderation_actions_world_status",
        "moderation_actions",
        ["world_id", "status"],
    )
    op.create_index(
        "ix_moderation_actions_worldline_status",
        "moderation_actions",
        ["world_id", "worldline_id", "status"],
    )
    op.create_index(
        "ix_moderation_actions_target",
        "moderation_actions",
        ["world_id", "target_ref_kind", "target_ref_id"],
    )
    op.create_index("ix_moderation_actions_report", "moderation_actions", ["report_id"])
    op.create_index("ix_moderation_actions_incident", "moderation_actions", ["incident_id"])


def downgrade() -> None:
    op.drop_index("ix_moderation_actions_incident", table_name="moderation_actions")
    op.drop_index("ix_moderation_actions_report", table_name="moderation_actions")
    op.drop_index("ix_moderation_actions_target", table_name="moderation_actions")
    op.drop_index("ix_moderation_actions_worldline_status", table_name="moderation_actions")
    op.drop_index("ix_moderation_actions_world_status", table_name="moderation_actions")
    op.drop_table("moderation_actions")
    op.drop_index("ix_moderation_incidents_worldline_status", table_name="moderation_incidents")
    op.drop_index("ix_moderation_incidents_world_status", table_name="moderation_incidents")
    op.drop_table("moderation_incidents")
    op.drop_index("ix_moderation_reports_target", table_name="moderation_reports")
    op.drop_index("ix_moderation_reports_reporter", table_name="moderation_reports")
    op.drop_index("ix_moderation_reports_worldline_status", table_name="moderation_reports")
    op.drop_index("ix_moderation_reports_world_status", table_name="moderation_reports")
    op.drop_table("moderation_reports")
