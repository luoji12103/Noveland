from __future__ import annotations

import uuid
from typing import Any

from noveland.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin
from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class CharacterSpriteSet(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "character_sprite_sets"
    __table_args__ = (
        UniqueConstraint(
            "world_id",
            "worldline_id",
            "agent_id",
            "style_key",
            name="uq_character_sprite_sets_agent_style",
        ),
        CheckConstraint("status IN ('active', 'disabled', 'deleted')", name="status"),
        CheckConstraint(
            "visibility IN ('private', 'world_admin', 'world_member', 'developer_only', 'hidden')",
            name="visibility",
        ),
        Index("ix_character_sprite_sets_worldline_agent", "world_id", "worldline_id", "agent_id"),
        Index("ix_character_sprite_sets_worldline_status", "world_id", "worldline_id", "status"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    style_key: Mapped[str] = mapped_column(String(120), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    default_variant_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        server_default=text("'active'"),
        default="active",
    )
    visibility: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'world_admin'"),
        default="world_admin",
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )


class CharacterSpriteVariant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "character_sprite_variants"
    __table_args__ = (
        UniqueConstraint(
            "world_id",
            "worldline_id",
            "sprite_set_id",
            "asset_id",
            "expression_key",
            "pose_key",
            "outfit_key",
            name="uq_character_sprite_variants_asset_keys",
        ),
        CheckConstraint("status IN ('active', 'disabled', 'deleted')", name="status"),
        CheckConstraint(
            "visibility IN ('private', 'world_admin', 'world_member', 'developer_only', 'hidden')",
            name="visibility",
        ),
        CheckConstraint("priority >= 0", name="priority_nonnegative"),
        Index("ix_character_sprite_variants_set", "sprite_set_id"),
        Index(
            "ix_character_sprite_variants_worldline_expr",
            "world_id",
            "worldline_id",
            "expression_key",
        ),
        Index("ix_character_sprite_variants_asset", "asset_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    sprite_set_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("character_sprite_sets.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("media_assets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    expression_key: Mapped[str] = mapped_column(String(80), nullable=False)
    pose_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    outfit_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    mood_tags_json: Mapped[list[str]] = mapped_column(
        "mood_tags",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=list,
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        server_default=text("'active'"),
        default="active",
    )
    visibility: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'world_admin'"),
        default="world_admin",
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )


class SceneBackgroundProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "scene_background_profiles"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'disabled', 'deleted')", name="status"),
        CheckConstraint(
            "visibility IN ('private', 'world_admin', 'world_member', 'developer_only', 'hidden')",
            name="visibility",
        ),
        CheckConstraint("priority >= 0", name="priority_nonnegative"),
        Index(
            "ix_scene_background_profiles_worldline_scene",
            "world_id",
            "worldline_id",
            "scene_id",
        ),
        Index(
            "ix_scene_background_profiles_worldline_location",
            "world_id",
            "worldline_id",
            "location_key",
        ),
        Index("ix_scene_background_profiles_asset", "asset_id"),
    )

    world_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False,
    )
    worldline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("worldlines.id", ondelete="CASCADE"),
        nullable=False,
    )
    scene_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("scenes.id", ondelete="SET NULL"),
        nullable=True,
    )
    location_key: Mapped[str] = mapped_column(String(120), nullable=False)
    time_of_day: Mapped[str | None] = mapped_column(String(40), nullable=True)
    weather_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("media_assets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        server_default=text("'active'"),
        default="active",
    )
    visibility: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'world_admin'"),
        default="world_admin",
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
    )
