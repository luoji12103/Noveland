from __future__ import annotations

import uuid
from enum import StrEnum
from typing import Any

from noveland.invocations.contracts import InvocationRecordView
from noveland.media.contracts import (
    MediaAssetRecord,
    MediaAssetRole,
    MediaJobRecord,
    MediaObjectRecord,
)
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TransparentBackgroundPreference(StrEnum):
    REQUIRE = "require"
    PREFER = "prefer"
    IGNORE = "ignore"


class ImageOutputFormat(StrEnum):
    PNG = "png"
    JPEG = "jpeg"
    WEBP = "webp"


class _FrozenContract(BaseModel):
    model_config = ConfigDict(frozen=True)


class ImageGenerateRequest(_FrozenContract):
    worldline_id: uuid.UUID | None = None
    provider_id: uuid.UUID
    prompt: str = Field(min_length=1)
    negative_prompt: str | None = Field(default=None, min_length=1)
    asset_role: MediaAssetRole = MediaAssetRole.ORIGINAL_IMAGE
    media_job_id: uuid.UUID | None = None
    reference_asset_ids: tuple[uuid.UUID, ...] = ()
    output_format: ImageOutputFormat = ImageOutputFormat.PNG
    size: str = Field(default="1024x1024", min_length=3, max_length=40)
    transparent_background: TransparentBackgroundPreference = (
        TransparentBackgroundPreference.IGNORE
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata", mode="after")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value)
        return value


class ImageEditRequest(_FrozenContract):
    worldline_id: uuid.UUID | None = None
    provider_id: uuid.UUID
    prompt: str = Field(min_length=1)
    input_asset_ids: tuple[uuid.UUID, ...] = Field(min_length=1)
    mask_asset_id: uuid.UUID | None = None
    output_role: MediaAssetRole = MediaAssetRole.ORIGINAL_IMAGE
    output_format: ImageOutputFormat = ImageOutputFormat.PNG
    size: str = Field(default="1024x1024", min_length=3, max_length=40)
    transparent_background: TransparentBackgroundPreference = (
        TransparentBackgroundPreference.IGNORE
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata", mode="after")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value)
        return value


class ImageLayer(_FrozenContract):
    asset_id: uuid.UUID
    x: int
    y: int
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)
    z_index: int = 0
    blend_mode: str | None = Field(default=None, min_length=1, max_length=40)

    @model_validator(mode="after")
    def validate_size_pair(self) -> ImageLayer:
        if (self.width is None) != (self.height is None):
            raise ValueError("width and height must be provided together")
        return self


class ImageComposeRequest(_FrozenContract):
    worldline_id: uuid.UUID | None = None
    background_asset_id: uuid.UUID
    layers: tuple[ImageLayer, ...] = ()
    output_asset_role: MediaAssetRole = MediaAssetRole.COMPOSITE_IMAGE
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata", mode="after")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        _assert_json_serializable(value)
        return value


class ImageResult(_FrozenContract):
    media_job: MediaJobRecord
    output_asset: MediaAssetRecord
    output_objects: list[MediaObjectRecord] = Field(default_factory=list)
    model_invocation: InvocationRecordView | None = None
    model_invocation_id: uuid.UUID | None = None


def _assert_json_serializable(value: dict[str, Any]) -> None:
    import json

    json.dumps(value)
