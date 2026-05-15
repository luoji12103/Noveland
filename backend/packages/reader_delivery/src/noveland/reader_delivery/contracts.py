from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class _FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True)


class ReaderMediaObjectDescriptor(_FrozenContract):
    object_id: uuid.UUID
    object_role: str = Field(min_length=1)
    content_type: str = Field(min_length=1)
    size: int = Field(ge=0)
    checksum_sha256: str = Field(min_length=64, max_length=64)
    width: int | None = Field(default=None, ge=0)
    height: int | None = Field(default=None, ge=0)
    duration_ms: int | None = Field(default=None, ge=0)
    sample_rate_hz: int | None = Field(default=None, ge=0)
    audio_channels: int | None = Field(default=None, ge=0)
    download_url: str = Field(min_length=1)


class ReaderMediaReferenceDescriptor(_FrozenContract):
    reference_id: uuid.UUID
    ref_kind: str = Field(min_length=1)
    ref_id: uuid.UUID
    ref_role: str = Field(min_length=1)
    display_order: int = Field(ge=0)


class ReaderMediaDescriptor(_FrozenContract):
    asset_id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    asset_kind: str = Field(min_length=1)
    asset_role: str = Field(min_length=1)
    visibility: str = Field(min_length=1)
    title: str | None = None
    description: str | None = None
    content_type: str | None = None
    size: int | None = Field(default=None, ge=0)
    width: int | None = Field(default=None, ge=0)
    height: int | None = Field(default=None, ge=0)
    duration_ms: int | None = Field(default=None, ge=0)
    objects: tuple[ReaderMediaObjectDescriptor, ...]
    references: tuple[ReaderMediaReferenceDescriptor, ...]
    created_at: datetime
    updated_at: datetime
