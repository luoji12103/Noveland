from __future__ import annotations

import uuid

from noveland.agents.models import Agent
from noveland.media.contracts import (
    MediaAssetKind,
    MediaAssetRecord,
    MediaAssetRole,
    MediaAssetStatus,
    MediaVisibility,
)
from noveland.media.models import MediaAsset
from noveland.media.service import MediaService
from noveland.visual.contracts import (
    BackgroundVisibility,
    SceneBackgroundCreate,
    SceneBackgroundRead,
    SceneBackgroundUpdate,
    SpriteBindingVisibility,
    SpriteSetCreate,
    SpriteSetRead,
    SpriteSetUpdate,
    SpriteVariantCreate,
    SpriteVariantRead,
    SpriteVariantUpdate,
    VisualRecordStatus,
)
from noveland.visual.models import (
    CharacterSpriteSet,
    CharacterSpriteVariant,
    SceneBackgroundProfile,
)
from noveland.worlds.models import Scene, World
from noveland.worlds.worldlines import worldline_or_404
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class VisualValidationError(ValueError):
    pass


class VisualNotFoundError(LookupError):
    pass


RESTRICTED_VISIBILITIES = {
    SpriteBindingVisibility.DEVELOPER_ONLY.value,
    SpriteBindingVisibility.HIDDEN.value,
}
RESTRICTED_MEDIA_VISIBILITIES = {
    MediaVisibility.DEVELOPER_ONLY.value,
    MediaVisibility.HIDDEN.value,
}


class VisualAssetService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_sprite_set(self, create: SpriteSetCreate) -> SpriteSetRead:
        self._validate_world(create.world_id)
        worldline_id = self._worldline_id(create.world_id, create.worldline_id)
        self._validate_agent(create.world_id, create.agent_id)
        model = CharacterSpriteSet(
            id=uuid.uuid4(),
            world_id=create.world_id,
            worldline_id=worldline_id,
            agent_id=create.agent_id,
            style_key=create.style_key,
            display_name=create.display_name,
            default_variant_id=create.default_variant_id,
            status=create.status.value,
            visibility=create.visibility.value,
            metadata_json=create.metadata_json,
        )
        self._session.add(model)
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise VisualValidationError("sprite set already exists") from exc
        if create.default_variant_id is not None:
            self._variant_required(create.world_id, worldline_id, create.default_variant_id)
        self._session.refresh(model)
        return _sprite_set_record(model)

    def list_sprite_sets(
        self,
        world_id: uuid.UUID,
        *,
        worldline_id: uuid.UUID | None = None,
        agent_id: uuid.UUID | None = None,
        include_restricted: bool = False,
    ) -> list[SpriteSetRead]:
        resolved = self._worldline_id(world_id, worldline_id)
        statement = select(CharacterSpriteSet).where(
            CharacterSpriteSet.world_id == world_id,
            CharacterSpriteSet.worldline_id == resolved,
            CharacterSpriteSet.status != VisualRecordStatus.DELETED.value,
        )
        if agent_id is not None:
            statement = statement.where(CharacterSpriteSet.agent_id == agent_id)
        if not include_restricted:
            statement = statement.where(
                CharacterSpriteSet.visibility.not_in(RESTRICTED_VISIBILITIES),
            )
        statement = statement.order_by(CharacterSpriteSet.agent_id, CharacterSpriteSet.style_key)
        return [_sprite_set_record(model) for model in self._session.scalars(statement).all()]

    def get_sprite_set(
        self,
        world_id: uuid.UUID,
        sprite_set_id: uuid.UUID,
        *,
        include_restricted: bool = False,
    ) -> SpriteSetRead | None:
        model = self._session.get(CharacterSpriteSet, sprite_set_id)
        if (
            model is None
            or model.world_id != world_id
            or model.status == VisualRecordStatus.DELETED.value
        ):
            return None
        if not include_restricted and model.visibility in RESTRICTED_VISIBILITIES:
            return None
        return _sprite_set_record(model)

    def update_sprite_set(
        self,
        world_id: uuid.UUID,
        sprite_set_id: uuid.UUID,
        update: SpriteSetUpdate,
    ) -> SpriteSetRead:
        model = self._sprite_set_required(world_id, sprite_set_id)
        if update.display_name is not None:
            model.display_name = update.display_name
        if "default_variant_id" in update.model_fields_set:
            if update.default_variant_id is not None:
                variant = self._variant_required(
                    world_id,
                    model.worldline_id,
                    update.default_variant_id,
                )
                if variant.sprite_set_id != model.id:
                    raise VisualValidationError("default variant must belong to sprite set")
            model.default_variant_id = update.default_variant_id
        if update.status is not None:
            model.status = update.status.value
        if update.visibility is not None:
            model.visibility = update.visibility.value
        if update.metadata_json is not None:
            model.metadata_json = update.metadata_json
        self._session.flush()
        self._session.refresh(model)
        return _sprite_set_record(model)

    def delete_sprite_set(self, world_id: uuid.UUID, sprite_set_id: uuid.UUID) -> None:
        model = self._sprite_set_required(world_id, sprite_set_id)
        model.status = VisualRecordStatus.DELETED.value
        self._session.flush()

    def create_sprite_variant(self, create: SpriteVariantCreate) -> SpriteVariantRead:
        worldline_id = self._worldline_id(create.world_id, create.worldline_id)
        sprite_set = self._sprite_set_required(create.world_id, create.sprite_set_id)
        if sprite_set.worldline_id != worldline_id:
            raise VisualValidationError("sprite variant worldline must match sprite set")
        self._validate_sprite_asset(create.world_id, worldline_id, create.asset_id)
        if create.is_default:
            self._clear_default_variant(create.world_id, create.sprite_set_id)
        model = CharacterSpriteVariant(
            id=uuid.uuid4(),
            world_id=create.world_id,
            worldline_id=worldline_id,
            sprite_set_id=create.sprite_set_id,
            asset_id=create.asset_id,
            expression_key=create.expression_key,
            pose_key=create.pose_key,
            outfit_key=create.outfit_key,
            mood_tags_json=list(create.mood_tags),
            priority=create.priority,
            is_default=create.is_default,
            status=create.status.value,
            visibility=create.visibility.value,
            metadata_json=create.metadata_json,
        )
        self._session.add(model)
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise VisualValidationError("sprite variant already exists") from exc
        if create.is_default:
            sprite_set.default_variant_id = model.id
        self._session.refresh(model)
        return _sprite_variant_record(model)

    def list_sprite_variants(
        self,
        world_id: uuid.UUID,
        sprite_set_id: uuid.UUID,
        *,
        include_restricted: bool = False,
    ) -> list[SpriteVariantRead]:
        sprite_set = self._sprite_set_required(world_id, sprite_set_id)
        statement = select(CharacterSpriteVariant).where(
            CharacterSpriteVariant.world_id == world_id,
            CharacterSpriteVariant.worldline_id == sprite_set.worldline_id,
            CharacterSpriteVariant.sprite_set_id == sprite_set_id,
            CharacterSpriteVariant.status != VisualRecordStatus.DELETED.value,
        )
        if not include_restricted:
            statement = statement.where(
                CharacterSpriteVariant.visibility.not_in(RESTRICTED_VISIBILITIES)
            )
        statement = statement.order_by(
            CharacterSpriteVariant.is_default.desc(),
            CharacterSpriteVariant.priority,
            CharacterSpriteVariant.created_at,
        )
        return [_sprite_variant_record(model) for model in self._session.scalars(statement).all()]

    def update_sprite_variant(
        self,
        world_id: uuid.UUID,
        variant_id: uuid.UUID,
        update: SpriteVariantUpdate,
    ) -> SpriteVariantRead:
        model = self._variant_required_any(world_id, variant_id)
        if update.asset_id is not None:
            self._validate_sprite_asset(world_id, model.worldline_id, update.asset_id)
            model.asset_id = update.asset_id
        if update.expression_key is not None:
            model.expression_key = update.expression_key.strip().lower()
        if "pose_key" in update.model_fields_set:
            model.pose_key = None if update.pose_key is None else update.pose_key.strip().lower()
        if "outfit_key" in update.model_fields_set:
            model.outfit_key = (
                None if update.outfit_key is None else update.outfit_key.strip().lower()
            )
        if update.mood_tags is not None:
            model.mood_tags_json = sorted({item.strip().lower() for item in update.mood_tags})
        if update.priority is not None:
            model.priority = update.priority
        if update.is_default is not None:
            if update.is_default:
                self._clear_default_variant(world_id, model.sprite_set_id)
                sprite_set = self._sprite_set_required(world_id, model.sprite_set_id)
                sprite_set.default_variant_id = model.id
            model.is_default = update.is_default
        if update.status is not None:
            model.status = update.status.value
        if update.visibility is not None:
            model.visibility = update.visibility.value
        if update.metadata_json is not None:
            model.metadata_json = update.metadata_json
        self._session.flush()
        self._session.refresh(model)
        return _sprite_variant_record(model)

    def delete_sprite_variant(self, world_id: uuid.UUID, variant_id: uuid.UUID) -> None:
        model = self._variant_required_any(world_id, variant_id)
        model.status = VisualRecordStatus.DELETED.value
        sprite_set = self._session.get(CharacterSpriteSet, model.sprite_set_id)
        if sprite_set is not None and sprite_set.default_variant_id == model.id:
            sprite_set.default_variant_id = None
        self._session.flush()

    def create_background(self, create: SceneBackgroundCreate) -> SceneBackgroundRead:
        worldline_id = self._worldline_id(create.world_id, create.worldline_id)
        self._validate_scene(create.world_id, create.scene_id)
        self._validate_background_asset(create.world_id, worldline_id, create.asset_id)
        if create.is_default:
            self._clear_default_background(
                create.world_id,
                worldline_id,
                create.scene_id,
                create.location_key,
            )
        model = SceneBackgroundProfile(
            id=uuid.uuid4(),
            world_id=create.world_id,
            worldline_id=worldline_id,
            scene_id=create.scene_id,
            location_key=create.location_key,
            time_of_day=create.time_of_day,
            weather_key=create.weather_key,
            asset_id=create.asset_id,
            priority=create.priority,
            is_default=create.is_default,
            status=create.status.value,
            visibility=create.visibility.value,
            metadata_json=create.metadata_json,
        )
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return _background_record(model)

    def list_backgrounds(
        self,
        world_id: uuid.UUID,
        *,
        worldline_id: uuid.UUID | None = None,
        include_restricted: bool = False,
    ) -> list[SceneBackgroundRead]:
        resolved = self._worldline_id(world_id, worldline_id)
        statement = select(SceneBackgroundProfile).where(
            SceneBackgroundProfile.world_id == world_id,
            SceneBackgroundProfile.worldline_id == resolved,
            SceneBackgroundProfile.status != VisualRecordStatus.DELETED.value,
        )
        if not include_restricted:
            statement = statement.where(
                SceneBackgroundProfile.visibility.not_in(RESTRICTED_VISIBILITIES),
            )
        statement = statement.order_by(
            SceneBackgroundProfile.location_key,
            SceneBackgroundProfile.priority,
        )
        return [_background_record(model) for model in self._session.scalars(statement).all()]

    def update_background(
        self,
        world_id: uuid.UUID,
        background_id: uuid.UUID,
        update: SceneBackgroundUpdate,
    ) -> SceneBackgroundRead:
        model = self._background_required(world_id, background_id)
        if "scene_id" in update.model_fields_set:
            self._validate_scene(world_id, update.scene_id)
            model.scene_id = update.scene_id
        if update.location_key is not None:
            model.location_key = update.location_key.strip().lower()
        if "time_of_day" in update.model_fields_set:
            model.time_of_day = (
                None if update.time_of_day is None else update.time_of_day.strip().lower()
            )
        if "weather_key" in update.model_fields_set:
            model.weather_key = (
                None if update.weather_key is None else update.weather_key.strip().lower()
            )
        if update.asset_id is not None:
            self._validate_background_asset(world_id, model.worldline_id, update.asset_id)
            model.asset_id = update.asset_id
        if update.priority is not None:
            model.priority = update.priority
        if update.is_default is not None:
            if update.is_default:
                self._clear_default_background(
                    world_id,
                    model.worldline_id,
                    model.scene_id,
                    model.location_key,
                )
            model.is_default = update.is_default
        if update.status is not None:
            model.status = update.status.value
        if update.visibility is not None:
            model.visibility = update.visibility.value
        if update.metadata_json is not None:
            model.metadata_json = update.metadata_json
        self._session.flush()
        self._session.refresh(model)
        return _background_record(model)

    def delete_background(self, world_id: uuid.UUID, background_id: uuid.UUID) -> None:
        model = self._background_required(world_id, background_id)
        model.status = VisualRecordStatus.DELETED.value
        self._session.flush()

    def media_asset(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        asset_id: uuid.UUID,
        *,
        allow_restricted: bool = False,
    ) -> MediaAssetRecord:
        asset = MediaService(self._session).get_asset_by_id(
            world_id,
            asset_id,
            include_deleted=False,
            allow_restricted=allow_restricted,
        )
        if asset is None or asset.worldline_id != worldline_id:
            raise VisualNotFoundError("media asset not found")
        return asset

    def _sprite_set_required(
        self,
        world_id: uuid.UUID,
        sprite_set_id: uuid.UUID,
    ) -> CharacterSpriteSet:
        model = self._session.get(CharacterSpriteSet, sprite_set_id)
        if model is None or model.world_id != world_id or model.status == "deleted":
            raise VisualNotFoundError("sprite set not found")
        return model

    def _variant_required(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        variant_id: uuid.UUID,
    ) -> CharacterSpriteVariant:
        model = self._variant_required_any(world_id, variant_id)
        if model.worldline_id != worldline_id:
            raise VisualNotFoundError("sprite variant not found")
        return model

    def _variant_required_any(
        self,
        world_id: uuid.UUID,
        variant_id: uuid.UUID,
    ) -> CharacterSpriteVariant:
        model = self._session.get(CharacterSpriteVariant, variant_id)
        if model is None or model.world_id != world_id or model.status == "deleted":
            raise VisualNotFoundError("sprite variant not found")
        return model

    def _background_required(
        self,
        world_id: uuid.UUID,
        background_id: uuid.UUID,
    ) -> SceneBackgroundProfile:
        model = self._session.get(SceneBackgroundProfile, background_id)
        if model is None or model.world_id != world_id or model.status == "deleted":
            raise VisualNotFoundError("background profile not found")
        return model

    def _clear_default_variant(self, world_id: uuid.UUID, sprite_set_id: uuid.UUID) -> None:
        for model in self._session.scalars(
            select(CharacterSpriteVariant).where(
                CharacterSpriteVariant.world_id == world_id,
                CharacterSpriteVariant.sprite_set_id == sprite_set_id,
                CharacterSpriteVariant.is_default.is_(True),
            )
        ):
            model.is_default = False

    def _clear_default_background(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        scene_id: uuid.UUID | None,
        location_key: str,
    ) -> None:
        for model in self._session.scalars(
            select(SceneBackgroundProfile).where(
                SceneBackgroundProfile.world_id == world_id,
                SceneBackgroundProfile.worldline_id == worldline_id,
                SceneBackgroundProfile.scene_id == scene_id,
                SceneBackgroundProfile.location_key == location_key,
                SceneBackgroundProfile.is_default.is_(True),
            )
        ):
            model.is_default = False

    def _validate_world(self, world_id: uuid.UUID) -> None:
        if self._session.get(World, world_id) is None:
            raise VisualValidationError("world not found")

    def _validate_agent(self, world_id: uuid.UUID, agent_id: uuid.UUID) -> None:
        model = self._session.get(Agent, agent_id)
        if model is None or model.world_id != world_id:
            raise VisualValidationError("agent not found")

    def _validate_scene(self, world_id: uuid.UUID, scene_id: uuid.UUID | None) -> None:
        if scene_id is None:
            return
        model = self._session.get(Scene, scene_id)
        if model is None or model.world_id != world_id:
            raise VisualValidationError("scene not found")

    def _validate_sprite_asset(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        asset_id: uuid.UUID,
    ) -> None:
        asset = self._asset_model(world_id, worldline_id, asset_id)
        if asset.asset_kind != MediaAssetKind.IMAGE.value:
            raise VisualValidationError("sprite asset must be an image")
        if asset.asset_role not in {
            MediaAssetRole.CHARACTER_SPRITE.value,
            MediaAssetRole.CHARACTER_EXPRESSION.value,
            MediaAssetRole.CHARACTER_POSE.value,
            MediaAssetRole.TRANSPARENT_PNG.value,
            MediaAssetRole.REFERENCE_IMAGE.value,
        }:
            raise VisualValidationError("sprite asset role is not visual-character compatible")

    def _validate_background_asset(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        asset_id: uuid.UUID,
    ) -> None:
        asset = self._asset_model(world_id, worldline_id, asset_id)
        if asset.asset_kind != MediaAssetKind.IMAGE.value:
            raise VisualValidationError("background asset must be an image")

    def _asset_model(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        asset_id: uuid.UUID,
    ) -> MediaAsset:
        asset = self._session.get(MediaAsset, asset_id)
        if (
            asset is None
            or asset.world_id != world_id
            or asset.worldline_id != worldline_id
            or asset.status == MediaAssetStatus.DELETED.value
        ):
            raise VisualValidationError("media asset must belong to request worldline")
        return asset

    def _worldline_id(self, world_id: uuid.UUID, worldline_id: uuid.UUID | None) -> uuid.UUID:
        if worldline_id is None:
            raise VisualValidationError("visual records require worldline_id")
        try:
            return worldline_or_404(self._session, world_id, worldline_id).id
        except ValueError as exc:
            raise VisualValidationError("worldline not found") from exc


def _sprite_set_record(model: CharacterSpriteSet) -> SpriteSetRead:
    return SpriteSetRead(
        id=model.id,
        world_id=model.world_id,
        worldline_id=model.worldline_id,
        agent_id=model.agent_id,
        style_key=model.style_key,
        display_name=model.display_name,
        default_variant_id=model.default_variant_id,
        status=VisualRecordStatus(model.status),
        visibility=SpriteBindingVisibility(model.visibility),
        metadata_json=model.metadata_json,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _sprite_variant_record(model: CharacterSpriteVariant) -> SpriteVariantRead:
    return SpriteVariantRead(
        id=model.id,
        world_id=model.world_id,
        worldline_id=model.worldline_id,
        sprite_set_id=model.sprite_set_id,
        asset_id=model.asset_id,
        expression_key=model.expression_key,
        pose_key=model.pose_key,
        outfit_key=model.outfit_key,
        mood_tags=tuple(model.mood_tags_json),
        priority=model.priority,
        is_default=model.is_default,
        status=VisualRecordStatus(model.status),
        visibility=SpriteBindingVisibility(model.visibility),
        metadata_json=model.metadata_json,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _background_record(model: SceneBackgroundProfile) -> SceneBackgroundRead:
    return SceneBackgroundRead(
        id=model.id,
        world_id=model.world_id,
        worldline_id=model.worldline_id,
        scene_id=model.scene_id,
        location_key=model.location_key,
        time_of_day=model.time_of_day,
        weather_key=model.weather_key,
        asset_id=model.asset_id,
        priority=model.priority,
        is_default=model.is_default,
        status=VisualRecordStatus(model.status),
        visibility=BackgroundVisibility(model.visibility),
        metadata_json=model.metadata_json,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
