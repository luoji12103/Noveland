from __future__ import annotations

import uuid

from noveland.visual.contracts import (
    BackgroundResolveRequest,
    BackgroundResolveResult,
    SpriteResolveRequest,
    SpriteResolveResult,
    VisualRecordStatus,
    visual_asset_ref,
)
from noveland.visual.models import (
    CharacterSpriteSet,
    CharacterSpriteVariant,
    SceneBackgroundProfile,
)
from noveland.visual.service import (
    RESTRICTED_VISIBILITIES,
    VisualAssetService,
    VisualValidationError,
    _background_record,
    _sprite_set_record,
    _sprite_variant_record,
)
from sqlalchemy import select
from sqlalchemy.orm import Session


class VisualResolver:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._assets = VisualAssetService(session)

    def resolve_sprite(
        self,
        world_id: uuid.UUID,
        request: SpriteResolveRequest,
    ) -> SpriteResolveResult:
        worldline_id = self._assets._worldline_id(world_id, request.worldline_id)
        sprite_set = self._select_sprite_set(world_id, worldline_id, request)
        variants = self._active_variants(
            world_id,
            worldline_id,
            sprite_set.id,
            include_restricted=request.include_restricted,
        )
        if not variants:
            raise VisualValidationError("sprite set has no usable variants")
        variant, fallback_reason, confidence = self._select_variant(
            sprite_set,
            variants,
            request,
        )
        asset = self._assets.media_asset(
            world_id,
            worldline_id,
            variant.asset_id,
            allow_restricted=request.include_restricted,
        )
        return SpriteResolveResult(
            sprite_set=_sprite_set_record(sprite_set),
            variant=_sprite_variant_record(variant),
            asset=visual_asset_ref(asset),
            fallback_reason=fallback_reason,
            confidence=confidence,
        )

    def resolve_background(
        self,
        world_id: uuid.UUID,
        request: BackgroundResolveRequest,
    ) -> BackgroundResolveResult:
        worldline_id = self._assets._worldline_id(world_id, request.worldline_id)
        candidates = self._background_candidates(
            world_id,
            worldline_id,
            request,
            include_restricted=request.include_restricted,
        )
        if not candidates:
            raise VisualValidationError("no usable background matches request")
        exact = [
            item
            for item in candidates
            if item.time_of_day == _norm(request.time_of_day)
            and item.weather_key == _norm(request.weather_key)
        ]
        if exact:
            selected = sorted(exact, key=lambda item: (item.priority, item.created_at))[0]
            fallback_reason = None
            confidence = 1.0
        else:
            default = [item for item in candidates if item.is_default]
            if not default:
                raise VisualValidationError("no default background fallback is available")
            selected = sorted(default, key=lambda item: (item.priority, item.created_at))[0]
            fallback_reason = "default_background"
            confidence = 0.6
        asset = self._assets.media_asset(
            world_id,
            worldline_id,
            selected.asset_id,
            allow_restricted=request.include_restricted,
        )
        return BackgroundResolveResult(
            background=_background_record(selected),
            asset=visual_asset_ref(asset),
            fallback_reason=fallback_reason,
            confidence=confidence,
        )

    def _select_sprite_set(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        request: SpriteResolveRequest,
    ) -> CharacterSpriteSet:
        statement = select(CharacterSpriteSet).where(
            CharacterSpriteSet.world_id == world_id,
            CharacterSpriteSet.worldline_id == worldline_id,
            CharacterSpriteSet.agent_id == request.agent_id,
            CharacterSpriteSet.status == VisualRecordStatus.ACTIVE.value,
        )
        if request.style_key is not None:
            statement = statement.where(CharacterSpriteSet.style_key == request.style_key.lower())
        if not request.include_restricted:
            statement = statement.where(
                CharacterSpriteSet.visibility.not_in(RESTRICTED_VISIBILITIES),
            )
        statement = statement.order_by(CharacterSpriteSet.style_key)
        model = self._session.scalars(statement).first()
        if model is None:
            raise VisualValidationError("no usable sprite set matches request")
        return model

    def _active_variants(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        sprite_set_id: uuid.UUID,
        *,
        include_restricted: bool,
    ) -> list[CharacterSpriteVariant]:
        statement = select(CharacterSpriteVariant).where(
            CharacterSpriteVariant.world_id == world_id,
            CharacterSpriteVariant.worldline_id == worldline_id,
            CharacterSpriteVariant.sprite_set_id == sprite_set_id,
            CharacterSpriteVariant.status == VisualRecordStatus.ACTIVE.value,
        )
        if not include_restricted:
            statement = statement.where(
                CharacterSpriteVariant.visibility.not_in(RESTRICTED_VISIBILITIES),
            )
        return list(self._session.scalars(statement).all())

    def _select_variant(
        self,
        sprite_set: CharacterSpriteSet,
        variants: list[CharacterSpriteVariant],
        request: SpriteResolveRequest,
    ) -> tuple[CharacterSpriteVariant, str | None, float]:
        expression = _norm(request.expression_key) or "neutral"
        pose = _norm(request.pose_key)
        outfit = _norm(request.outfit_key)
        mood_tags = {_norm(item) for item in request.mood_tags if _norm(item) is not None}
        exact = [
            item
            for item in variants
            if item.expression_key == expression
            and _optional_match(item.pose_key, pose)
            and _optional_match(item.outfit_key, outfit)
            and mood_tags.issubset(set(item.mood_tags_json))
        ]
        if exact:
            return _best_variant(exact), None, 1.0
        neutral = [
            item
            for item in variants
            if item.expression_key == "neutral"
            and _optional_match(item.pose_key, pose)
            and _optional_match(item.outfit_key, outfit)
        ]
        if neutral:
            return _best_variant(neutral), "neutral_expression", 0.75
        default = [
            item
            for item in variants
            if item.is_default
            or (
                sprite_set.default_variant_id is not None
                and item.id == sprite_set.default_variant_id
            )
        ]
        if default:
            return _best_variant(default), "default_variant", 0.5
        raise VisualValidationError("no default sprite variant fallback is available")

    def _background_candidates(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        request: BackgroundResolveRequest,
        *,
        include_restricted: bool,
    ) -> list[SceneBackgroundProfile]:
        statement = select(SceneBackgroundProfile).where(
            SceneBackgroundProfile.world_id == world_id,
            SceneBackgroundProfile.worldline_id == worldline_id,
            SceneBackgroundProfile.location_key == request.location_key.strip().lower(),
            SceneBackgroundProfile.status == VisualRecordStatus.ACTIVE.value,
        )
        if request.scene_id is not None:
            statement = statement.where(SceneBackgroundProfile.scene_id == request.scene_id)
        if not include_restricted:
            statement = statement.where(
                SceneBackgroundProfile.visibility.not_in(RESTRICTED_VISIBILITIES),
            )
        return list(self._session.scalars(statement).all())


def _best_variant(items: list[CharacterSpriteVariant]) -> CharacterSpriteVariant:
    return sorted(items, key=lambda item: (item.priority, item.created_at))[0]


def _optional_match(candidate: str | None, requested: str | None) -> bool:
    return requested is None or candidate == requested


def _norm(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized or None
