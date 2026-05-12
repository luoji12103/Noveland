"""Add speech voice profile pipeline.

Revision ID: 20260512_0036
Revises: 20260512_0034
Create Date: 2026-05-12
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260512_0036"
down_revision: str | None = "20260512_0034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "voice_profiles",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=True),
        sa.Column("profile_key", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
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
        sa.Column("owner_kind", sa.String(length=32), nullable=False),
        sa.Column("owner_agent_id", sa.Uuid(), nullable=True),
        sa.Column("provider_integration_id", sa.Uuid(), nullable=True),
        sa.Column("provider_voice_id", sa.String(length=200), nullable=True),
        sa.Column("default_language", sa.String(length=40), nullable=True),
        sa.Column("supported_languages", JSONB, nullable=False),
        sa.Column("voice_kind", sa.String(length=40), nullable=False),
        sa.Column("reference_asset_id", sa.Uuid(), nullable=True),
        sa.Column("consent_status", sa.String(length=40), nullable=False),
        sa.Column("usage_policy", JSONB, nullable=False),
        sa.Column("metadata", JSONB, nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('active', 'disabled', 'deleted')",
            name=op.f("ck_voice_profiles_status"),
        ),
        sa.CheckConstraint(
            "visibility IN ('private', 'world_admin', 'world_member', 'developer_only', 'hidden')",
            name=op.f("ck_voice_profiles_visibility"),
        ),
        sa.CheckConstraint(
            "owner_kind IN ('world', 'agent', 'user', 'provider', 'other')",
            name=op.f("ck_voice_profiles_owner_kind"),
        ),
        sa.CheckConstraint(
            "voice_kind IN ('preset', 'cloned', 'designed', 'imported', 'generated', "
            "'external_provider', 'other')",
            name=op.f("ck_voice_profiles_voice_kind"),
        ),
        sa.CheckConstraint(
            "consent_status IN ('not_required', 'user_owned_or_authorized', "
            "'admin_authorized', 'pending_review', 'restricted', 'unknown')",
            name=op.f("ck_voice_profiles_consent_status"),
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_voice_profiles_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_voice_profiles_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["owner_agent_id"],
            ["agents.id"],
            name=op.f("fk_voice_profiles_owner_agent_id_agents"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["provider_integration_id"],
            ["provider_integrations.id"],
            name=op.f("fk_voice_profiles_provider_integration_id_provider_integrations"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["reference_asset_id"],
            ["media_assets.id"],
            name=op.f("fk_voice_profiles_reference_asset_id_media_assets"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_voice_profiles")),
        sa.UniqueConstraint(
            "world_id",
            "worldline_id",
            "profile_key",
            name="uq_voice_profiles_key",
        ),
    )
    op.create_index(
        "ix_voice_profiles_worldline_status",
        "voice_profiles",
        ["world_id", "worldline_id", "status"],
    )
    op.create_index("ix_voice_profiles_owner_agent", "voice_profiles", ["owner_agent_id"])
    op.create_index("ix_voice_profiles_provider", "voice_profiles", ["provider_integration_id"])
    op.create_index(
        "ix_voice_profiles_reference_asset",
        "voice_profiles",
        ["reference_asset_id"],
    )

    op.create_table(
        "agent_voice_profile_bindings",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=True),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("voice_profile_id", sa.Uuid(), nullable=False),
        sa.Column("binding_role", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("style_overrides", JSONB, nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "binding_role IN ('default', 'narration', 'inner_voice', 'phone_call', "
            "'disguise', 'alternate', 'other')",
            name=op.f("ck_agent_voice_profile_bindings_binding_role"),
        ),
        sa.CheckConstraint(
            "priority >= 0",
            name=op.f("ck_agent_voice_profile_bindings_priority_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_agent_voice_profile_bindings_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_agent_voice_profile_bindings_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["agent_id"],
            ["agents.id"],
            name=op.f("fk_agent_voice_profile_bindings_agent_id_agents"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["voice_profile_id"],
            ["voice_profiles.id"],
            name=op.f("fk_agent_voice_profile_bindings_voice_profile_id_voice_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agent_voice_profile_bindings")),
        sa.UniqueConstraint(
            "world_id",
            "worldline_id",
            "agent_id",
            "voice_profile_id",
            "binding_role",
            name="uq_agent_voice_profile_bindings_role",
        ),
    )
    op.create_index(
        "ix_agent_voice_profile_bindings_agent",
        "agent_voice_profile_bindings",
        ["world_id", "worldline_id", "agent_id"],
    )
    op.create_index(
        "ix_agent_voice_profile_bindings_profile",
        "agent_voice_profile_bindings",
        ["voice_profile_id"],
    )

    op.create_table(
        "speech_transcripts",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("worldline_id", sa.Uuid(), nullable=False),
        sa.Column("source_asset_id", sa.Uuid(), nullable=False),
        sa.Column("media_job_id", sa.Uuid(), nullable=True),
        sa.Column("model_invocation_id", sa.Uuid(), nullable=True),
        sa.Column("conversation_id", sa.Uuid(), nullable=True),
        sa.Column("turn_id", sa.Uuid(), nullable=True),
        sa.Column("speaker_actor_ref", sa.String(length=160), nullable=True),
        sa.Column("language", sa.String(length=40), nullable=True),
        sa.Column("transcript_text", sa.Text(), nullable=False),
        sa.Column("segments", JSONB, nullable=True),
        sa.Column("confidence", JSONB, nullable=True),
        sa.Column(
            "status", sa.String(length=24), server_default=sa.text("'available'"), nullable=False
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
            "status IN ('available', 'failed', 'deleted')",
            name=op.f("ck_speech_transcripts_status"),
        ),
        sa.CheckConstraint(
            "visibility IN ('private', 'world_admin', 'world_member', 'developer_only', 'hidden')",
            name=op.f("ck_speech_transcripts_visibility"),
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_speech_transcripts_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["worldline_id"],
            ["worldlines.id"],
            name=op.f("fk_speech_transcripts_worldline_id_worldlines"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_asset_id"],
            ["media_assets.id"],
            name=op.f("fk_speech_transcripts_source_asset_id_media_assets"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["media_job_id"],
            ["media_jobs.id"],
            name=op.f("fk_speech_transcripts_media_job_id_media_jobs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["model_invocation_id"],
            ["model_invocations.id"],
            name=op.f("fk_speech_transcripts_model_invocation_id_model_invocations"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversation_sessions.id"],
            name=op.f("fk_speech_transcripts_conversation_id_conversation_sessions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["turn_id"],
            ["conversation_turns.id"],
            name=op.f("fk_speech_transcripts_turn_id_conversation_turns"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_speech_transcripts")),
    )
    op.create_index(
        "ix_speech_transcripts_worldline_created",
        "speech_transcripts",
        ["world_id", "worldline_id", "created_at"],
    )
    op.create_index("ix_speech_transcripts_source_asset", "speech_transcripts", ["source_asset_id"])
    op.create_index("ix_speech_transcripts_media_job", "speech_transcripts", ["media_job_id"])
    op.create_index(
        "ix_speech_transcripts_invocation",
        "speech_transcripts",
        ["model_invocation_id"],
    )
    op.create_index(
        "ix_speech_transcripts_turn",
        "speech_transcripts",
        ["conversation_id", "turn_id"],
    )

    op.create_table(
        "speech_style_mappings",
        sa.Column("world_id", sa.Uuid(), nullable=False),
        sa.Column("mapping_key", sa.String(length=120), nullable=False),
        sa.Column("provider_kind", sa.String(length=80), nullable=False),
        sa.Column("emotion_key", sa.String(length=80), nullable=False),
        sa.Column("style", JSONB, nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["world_id"],
            ["worlds.id"],
            name=op.f("fk_speech_style_mappings_world_id_worlds"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_speech_style_mappings")),
        sa.UniqueConstraint(
            "world_id",
            "mapping_key",
            "provider_kind",
            "emotion_key",
            name="uq_speech_style_mappings_key",
        ),
    )
    op.create_index(
        "ix_speech_style_mappings_world_provider",
        "speech_style_mappings",
        ["world_id", "provider_kind"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_speech_style_mappings_world_provider",
        table_name="speech_style_mappings",
    )
    op.drop_table("speech_style_mappings")
    op.drop_index("ix_speech_transcripts_turn", table_name="speech_transcripts")
    op.drop_index("ix_speech_transcripts_invocation", table_name="speech_transcripts")
    op.drop_index("ix_speech_transcripts_media_job", table_name="speech_transcripts")
    op.drop_index("ix_speech_transcripts_source_asset", table_name="speech_transcripts")
    op.drop_index("ix_speech_transcripts_worldline_created", table_name="speech_transcripts")
    op.drop_table("speech_transcripts")
    op.drop_index(
        "ix_agent_voice_profile_bindings_profile",
        table_name="agent_voice_profile_bindings",
    )
    op.drop_index(
        "ix_agent_voice_profile_bindings_agent",
        table_name="agent_voice_profile_bindings",
    )
    op.drop_table("agent_voice_profile_bindings")
    op.drop_index("ix_voice_profiles_reference_asset", table_name="voice_profiles")
    op.drop_index("ix_voice_profiles_provider", table_name="voice_profiles")
    op.drop_index("ix_voice_profiles_owner_agent", table_name="voice_profiles")
    op.drop_index("ix_voice_profiles_worldline_status", table_name="voice_profiles")
    op.drop_table("voice_profiles")
