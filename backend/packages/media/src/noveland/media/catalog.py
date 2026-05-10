from __future__ import annotations

import uuid
from typing import Any

from noveland.agents.models import Agent
from noveland.media.contracts import (
    MediaAssetCollectionCreate,
    MediaAssetCollectionItemCreate,
    MediaAssetCollectionItemRecord,
    MediaAssetCollectionItemUpdate,
    MediaAssetCollectionRecord,
    MediaAssetCollectionUpdate,
    MediaAssetLineage,
    MediaAssetRecord,
    MediaAssetReferences,
    MediaAssetSearchFilters,
    MediaAssetSearchResult,
    MediaAssetStatus,
    MediaAssetTagCreate,
    MediaAssetTagRecord,
    MediaAssetTagUpdate,
    MediaCollectionStatus,
    MediaContextRecord,
    MediaTagSourceKind,
    MediaVisibility,
)
from noveland.media.errors import MediaNotFoundError, MediaValidationError
from noveland.media.models import (
    MediaAsset,
    MediaAssetCollection,
    MediaAssetCollectionItem,
    MediaAssetContext,
    MediaAssetInput,
    MediaAssetTag,
)
from noveland.media.service import _asset_record, _context_record, _input_record
from noveland.worlds.worldlines import worldline_or_404
from sqlalchemy import Select, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

MEMBER_VISIBLE_MEDIA_VISIBILITIES = {
    MediaVisibility.WORLD_MEMBER.value,
    MediaVisibility.PLAYER_VISIBLE.value,
    MediaVisibility.READER_VISIBLE.value,
}


class MediaCatalogService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_tag(
        self,
        world_id: uuid.UUID,
        asset_id: uuid.UUID,
        tag_create: MediaAssetTagCreate,
        *,
        actor_ref: str,
    ) -> MediaAssetTagRecord:
        if tag_create.world_id != world_id:
            raise MediaValidationError("tag world_id must match route world_id")
        asset = _asset_required(self._session, world_id, asset_id)
        worldline_id = _worldline_id(self._session, world_id, tag_create.worldline_id)
        if asset.worldline_id != worldline_id:
            raise MediaValidationError("tag asset must belong to the tag worldline")
        model = MediaAssetTag(
            id=uuid.uuid4(),
            world_id=world_id,
            worldline_id=worldline_id,
            asset_id=asset_id,
            tag_type=tag_create.tag_type,
            tag_key=tag_create.tag_key,
            tag_value=tag_create.tag_value,
            confidence=tag_create.confidence,
            source_kind=tag_create.source_kind.value,
            visibility=tag_create.visibility.value,
            created_by_actor_ref=actor_ref,
            metadata_json=tag_create.metadata,
        )
        self._session.add(model)
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise MediaValidationError("media asset tag already exists") from exc
        self._session.refresh(model)
        return _tag_record(model)

    def list_tags(
        self,
        world_id: uuid.UUID,
        asset_id: uuid.UUID,
        *,
        member_visible_only: bool = False,
    ) -> list[MediaAssetTagRecord]:
        asset = _asset_required(self._session, world_id, asset_id, include_deleted=True)
        statement = select(MediaAssetTag).where(
            MediaAssetTag.world_id == world_id,
            MediaAssetTag.worldline_id == asset.worldline_id,
            MediaAssetTag.asset_id == asset_id,
        )
        if member_visible_only:
            statement = statement.where(
                MediaAssetTag.visibility.in_(MEMBER_VISIBLE_MEDIA_VISIBILITIES)
            )
        statement = statement.order_by(
            MediaAssetTag.tag_type,
            MediaAssetTag.tag_key,
            MediaAssetTag.tag_value,
        )
        return [_tag_record(model) for model in self._session.scalars(statement).all()]

    def update_tag(
        self,
        world_id: uuid.UUID,
        asset_id: uuid.UUID,
        tag_id: uuid.UUID,
        tag_update: MediaAssetTagUpdate,
    ) -> MediaAssetTagRecord:
        model = self._tag_required(world_id, asset_id, tag_id)
        if tag_update.confidence is not None:
            model.confidence = tag_update.confidence
        if tag_update.visibility is not None:
            model.visibility = tag_update.visibility.value
        if tag_update.metadata is not None:
            model.metadata_json = tag_update.metadata
        self._session.flush()
        self._session.refresh(model)
        return _tag_record(model)

    def delete_tag(self, world_id: uuid.UUID, asset_id: uuid.UUID, tag_id: uuid.UUID) -> None:
        model = self._tag_required(world_id, asset_id, tag_id)
        self._session.delete(model)
        self._session.flush()

    def search_assets(
        self,
        world_id: uuid.UUID,
        filters: MediaAssetSearchFilters,
        *,
        member_visible_only: bool = False,
    ) -> MediaAssetSearchResult:
        worldline_id = _worldline_id(self._session, world_id, filters.worldline_id)
        statement = select(MediaAsset).where(
            MediaAsset.world_id == world_id,
            MediaAsset.worldline_id == worldline_id,
            MediaAsset.status != MediaAssetStatus.DELETED.value,
        )
        if filters.asset_kind is not None:
            statement = statement.where(MediaAsset.asset_kind == filters.asset_kind.value)
        if filters.asset_role is not None:
            statement = statement.where(MediaAsset.asset_role == filters.asset_role.value)
        if filters.source_kind is not None:
            statement = statement.where(MediaAsset.source_kind == filters.source_kind.value)
        if filters.status is not None:
            statement = statement.where(MediaAsset.status == filters.status.value)
        if filters.visibility is not None:
            statement = statement.where(MediaAsset.visibility == filters.visibility.value)
        if filters.has_alpha is not None:
            statement = statement.where(MediaAsset.has_alpha.is_(filters.has_alpha))
        if filters.mime_type is not None:
            statement = statement.where(MediaAsset.mime_type == filters.mime_type)
        if filters.provider_kind is not None:
            statement = statement.where(MediaAsset.provider_kind == filters.provider_kind)
        if filters.contains_text is not None:
            pattern = f"%{filters.contains_text}%"
            statement = statement.where(
                or_(MediaAsset.title.ilike(pattern), MediaAsset.description.ilike(pattern))
            )
        if member_visible_only:
            statement = statement.where(
                MediaAsset.visibility.in_(MEMBER_VISIBLE_MEDIA_VISIBILITIES)
            )
        statement = self._apply_context_filters(statement, filters)
        statement = self._apply_collection_filter(
            statement,
            world_id,
            worldline_id,
            filters,
            member_visible_only=member_visible_only,
        )
        for tag_filter in filters.tags:
            tag_exists = (
                select(MediaAssetTag.id)
                .where(
                    MediaAssetTag.world_id == world_id,
                    MediaAssetTag.worldline_id == worldline_id,
                    MediaAssetTag.asset_id == MediaAsset.id,
                    MediaAssetTag.tag_type == tag_filter.tag_type,
                    MediaAssetTag.tag_key == tag_filter.tag_key,
                    MediaAssetTag.tag_value == tag_filter.tag_value,
                )
                .limit(1)
            )
            if member_visible_only:
                tag_exists = tag_exists.where(
                    MediaAssetTag.visibility.in_(MEMBER_VISIBLE_MEDIA_VISIBILITIES)
                )
            statement = statement.where(tag_exists.exists())
        statement = statement.order_by(MediaAsset.created_at.desc()).limit(filters.limit)
        return MediaAssetSearchResult(
            assets=[_asset_record(model) for model in self._session.scalars(statement).all()]
        )

    def _apply_context_filters(
        self, statement: Select[tuple[MediaAsset]], filters: MediaAssetSearchFilters
    ) -> Select[tuple[MediaAsset]]:
        context_filters: list[Any] = []
        if filters.used_by_agent_id is not None:
            context_filters.append(MediaAssetContext.agent_id == filters.used_by_agent_id)
        if filters.used_in_conversation_id is not None:
            context_filters.append(
                MediaAssetContext.conversation_id == filters.used_in_conversation_id
            )
        if filters.used_in_turn_id is not None:
            context_filters.append(MediaAssetContext.turn_id == filters.used_in_turn_id)
        if filters.used_in_world_event_id is not None:
            context_filters.append(
                MediaAssetContext.world_event_id == filters.used_in_world_event_id
            )
        if not context_filters:
            return statement
        return statement.where(
            select(MediaAssetContext.id)
            .where(
                MediaAssetContext.world_id == MediaAsset.world_id,
                MediaAssetContext.worldline_id == MediaAsset.worldline_id,
                MediaAssetContext.asset_id == MediaAsset.id,
                *context_filters,
            )
            .exists()
        )

    def _apply_collection_filter(
        self,
        statement: Select[tuple[MediaAsset]],
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        filters: MediaAssetSearchFilters,
        *,
        member_visible_only: bool,
    ) -> Select[tuple[MediaAsset]]:
        if filters.collection_id is None:
            return statement
        collection_item_exists = (
            select(MediaAssetCollectionItem.id)
            .join(
                MediaAssetCollection,
                MediaAssetCollection.id == MediaAssetCollectionItem.collection_id,
            )
            .where(
                MediaAssetCollectionItem.world_id == world_id,
                MediaAssetCollectionItem.worldline_id == worldline_id,
                MediaAssetCollectionItem.asset_id == MediaAsset.id,
                MediaAssetCollectionItem.collection_id == filters.collection_id,
                MediaAssetCollection.status == MediaCollectionStatus.ACTIVE.value,
            )
            .limit(1)
        )
        if member_visible_only:
            collection_item_exists = collection_item_exists.where(
                MediaAssetCollection.visibility.in_(MEMBER_VISIBLE_MEDIA_VISIBILITIES)
            )
        return statement.where(collection_item_exists.exists())

    def _tag_required(
        self, world_id: uuid.UUID, asset_id: uuid.UUID, tag_id: uuid.UUID
    ) -> MediaAssetTag:
        model = self._session.get(MediaAssetTag, tag_id)
        if model is None or model.world_id != world_id or model.asset_id != asset_id:
            raise MediaNotFoundError("media asset tag not found")
        return model


class MediaCollectionService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_collection(
        self,
        collection_create: MediaAssetCollectionCreate,
        *,
        actor_ref: str,
    ) -> MediaAssetCollectionRecord:
        worldline_id = _worldline_id(
            self._session,
            collection_create.world_id,
            collection_create.worldline_id,
        )
        if collection_create.owner_agent_id is not None:
            agent = self._session.get(Agent, collection_create.owner_agent_id)
            if agent is None or agent.world_id != collection_create.world_id:
                raise MediaValidationError("owner agent must belong to collection world")
        model = MediaAssetCollection(
            id=uuid.uuid4(),
            world_id=collection_create.world_id,
            worldline_id=worldline_id,
            collection_kind=collection_create.collection_kind,
            title=collection_create.title,
            description=collection_create.description,
            owner_agent_id=collection_create.owner_agent_id,
            visibility=collection_create.visibility.value,
            status=MediaCollectionStatus.ACTIVE.value,
            created_by_actor_ref=actor_ref,
            metadata_json=collection_create.metadata,
        )
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return _collection_record(model)

    def get_collection(
        self,
        world_id: uuid.UUID,
        collection_id: uuid.UUID,
        *,
        member_visible_only: bool = False,
    ) -> MediaAssetCollectionRecord | None:
        model = self._collection_or_none(
            world_id,
            collection_id,
            include_deleted=False,
            member_visible_only=member_visible_only,
        )
        return None if model is None else _collection_record(model)

    def list_collections(
        self,
        world_id: uuid.UUID,
        *,
        worldline_id: uuid.UUID | None = None,
        collection_kind: str | None = None,
        member_visible_only: bool = False,
        limit: int = 100,
    ) -> list[MediaAssetCollectionRecord]:
        resolved_worldline_id = _worldline_id(self._session, world_id, worldline_id)
        statement = select(MediaAssetCollection).where(
            MediaAssetCollection.world_id == world_id,
            MediaAssetCollection.worldline_id == resolved_worldline_id,
            MediaAssetCollection.status == MediaCollectionStatus.ACTIVE.value,
        )
        if collection_kind is not None:
            statement = statement.where(MediaAssetCollection.collection_kind == collection_kind)
        if member_visible_only:
            statement = statement.where(
                MediaAssetCollection.visibility.in_(MEMBER_VISIBLE_MEDIA_VISIBILITIES)
            )
        statement = statement.order_by(MediaAssetCollection.created_at.desc()).limit(limit)
        return [_collection_record(model) for model in self._session.scalars(statement).all()]

    def update_collection(
        self,
        world_id: uuid.UUID,
        collection_id: uuid.UUID,
        collection_update: MediaAssetCollectionUpdate,
    ) -> MediaAssetCollectionRecord:
        model = self._collection_required(world_id, collection_id)
        if collection_update.title is not None:
            model.title = collection_update.title
        if collection_update.description is not None:
            model.description = collection_update.description
        if collection_update.visibility is not None:
            model.visibility = collection_update.visibility.value
        if collection_update.status is not None:
            model.status = collection_update.status.value
        if collection_update.metadata is not None:
            model.metadata_json = collection_update.metadata
        self._session.flush()
        self._session.refresh(model)
        return _collection_record(model)

    def delete_collection(self, world_id: uuid.UUID, collection_id: uuid.UUID) -> None:
        model = self._collection_required(world_id, collection_id)
        model.status = MediaCollectionStatus.DELETED.value
        self._session.flush()

    def add_item(
        self,
        world_id: uuid.UUID,
        collection_id: uuid.UUID,
        item_create: MediaAssetCollectionItemCreate,
    ) -> MediaAssetCollectionItemRecord:
        if item_create.world_id != world_id:
            raise MediaValidationError("collection item world_id must match route world_id")
        collection = self._collection_required(world_id, collection_id)
        worldline_id = _worldline_id(self._session, world_id, item_create.worldline_id)
        if collection.worldline_id != worldline_id:
            raise MediaValidationError("collection item worldline must match collection worldline")
        asset = _asset_required(self._session, world_id, item_create.asset_id)
        if asset.worldline_id != worldline_id:
            raise MediaValidationError("collection item asset must match collection worldline")
        model = MediaAssetCollectionItem(
            id=uuid.uuid4(),
            world_id=world_id,
            worldline_id=worldline_id,
            collection_id=collection_id,
            asset_id=item_create.asset_id,
            role=item_create.role,
            display_order=item_create.display_order,
            metadata_json=item_create.metadata,
        )
        self._session.add(model)
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise MediaValidationError("media asset collection item already exists") from exc
        self._session.refresh(model)
        return _collection_item_record(model)

    def list_items(
        self,
        world_id: uuid.UUID,
        collection_id: uuid.UUID,
        *,
        member_visible_only: bool = False,
    ) -> list[MediaAssetCollectionItemRecord]:
        collection = self._collection_required(world_id, collection_id)
        if member_visible_only and collection.visibility not in MEMBER_VISIBLE_MEDIA_VISIBILITIES:
            raise MediaNotFoundError("media asset collection not found")
        statement = (
            select(MediaAssetCollectionItem)
            .join(MediaAsset, MediaAsset.id == MediaAssetCollectionItem.asset_id)
            .where(
                MediaAssetCollectionItem.world_id == world_id,
                MediaAssetCollectionItem.worldline_id == collection.worldline_id,
                MediaAssetCollectionItem.collection_id == collection_id,
                MediaAsset.status != MediaAssetStatus.DELETED.value,
            )
        )
        if member_visible_only:
            statement = statement.where(
                MediaAsset.visibility.in_(MEMBER_VISIBLE_MEDIA_VISIBILITIES)
            )
        statement = statement.order_by(
            MediaAssetCollectionItem.display_order,
            MediaAssetCollectionItem.created_at,
        )
        return [_collection_item_record(model) for model in self._session.scalars(statement).all()]

    def update_item(
        self,
        world_id: uuid.UUID,
        collection_id: uuid.UUID,
        item_id: uuid.UUID,
        item_update: MediaAssetCollectionItemUpdate,
    ) -> MediaAssetCollectionItemRecord:
        model = self._item_required(world_id, collection_id, item_id)
        if item_update.display_order is not None:
            model.display_order = item_update.display_order
        if item_update.metadata is not None:
            model.metadata_json = item_update.metadata
        self._session.flush()
        self._session.refresh(model)
        return _collection_item_record(model)

    def remove_item(
        self, world_id: uuid.UUID, collection_id: uuid.UUID, item_id: uuid.UUID
    ) -> None:
        model = self._item_required(world_id, collection_id, item_id)
        self._session.delete(model)
        self._session.flush()

    def _collection_required(
        self, world_id: uuid.UUID, collection_id: uuid.UUID
    ) -> MediaAssetCollection:
        model = self._collection_or_none(
            world_id,
            collection_id,
            include_deleted=False,
            member_visible_only=False,
        )
        if model is None:
            raise MediaNotFoundError("media asset collection not found")
        return model

    def _collection_or_none(
        self,
        world_id: uuid.UUID,
        collection_id: uuid.UUID,
        *,
        include_deleted: bool,
        member_visible_only: bool,
    ) -> MediaAssetCollection | None:
        model = self._session.get(MediaAssetCollection, collection_id)
        if model is None or model.world_id != world_id:
            return None
        if not include_deleted and model.status == MediaCollectionStatus.DELETED.value:
            return None
        if member_visible_only and model.visibility not in MEMBER_VISIBLE_MEDIA_VISIBILITIES:
            return None
        return model

    def _item_required(
        self, world_id: uuid.UUID, collection_id: uuid.UUID, item_id: uuid.UUID
    ) -> MediaAssetCollectionItem:
        model = self._session.get(MediaAssetCollectionItem, item_id)
        if model is None or model.world_id != world_id or model.collection_id != collection_id:
            raise MediaNotFoundError("media asset collection item not found")
        return model


class MediaLineageService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def references(
        self,
        world_id: uuid.UUID,
        asset_id: uuid.UUID,
        *,
        member_visible_only: bool = False,
    ) -> MediaAssetReferences:
        asset = _asset_required(self._session, world_id, asset_id, include_deleted=True)
        visible_asset_ids = self._visible_asset_ids(world_id, member_visible_only)
        contexts = self._contexts(world_id, asset)
        tags = MediaCatalogService(self._session).list_tags(
            world_id,
            asset_id,
            member_visible_only=member_visible_only,
        )
        collections = self._collections_for_asset(
            world_id,
            asset,
            member_visible_only=member_visible_only,
        )
        input_count = self._count_inputs(world_id, asset, visible_asset_ids, as_input=True)
        output_count = self._count_inputs(world_id, asset, visible_asset_ids, as_input=False)
        return MediaAssetReferences(
            asset_id=asset_id,
            contexts=contexts,
            tags=tags,
            collections=collections,
            input_count=input_count,
            output_count=output_count,
            tag_count=len(tags),
            collection_count=len(collections),
        )

    def lineage(
        self,
        world_id: uuid.UUID,
        asset_id: uuid.UUID,
        *,
        member_visible_only: bool = False,
    ) -> MediaAssetLineage:
        asset = _asset_required(self._session, world_id, asset_id, include_deleted=True)
        visible_asset_ids = self._visible_asset_ids(world_id, member_visible_only)
        input_statement = select(MediaAssetInput).where(
            MediaAssetInput.world_id == world_id,
            MediaAssetInput.worldline_id == asset.worldline_id,
            MediaAssetInput.output_asset_id == asset_id,
        )
        output_statement = select(MediaAssetInput).where(
            MediaAssetInput.world_id == world_id,
            MediaAssetInput.worldline_id == asset.worldline_id,
            MediaAssetInput.input_asset_id == asset_id,
        )
        if visible_asset_ids is not None:
            input_statement = input_statement.where(
                MediaAssetInput.input_asset_id.in_(visible_asset_ids)
            )
            output_statement = output_statement.where(
                MediaAssetInput.output_asset_id.in_(visible_asset_ids)
            )
        inputs = self._session.scalars(
            input_statement.order_by(MediaAssetInput.display_order, MediaAssetInput.created_at)
        ).all()
        outputs = self._session.scalars(
            output_statement.order_by(MediaAssetInput.display_order, MediaAssetInput.created_at)
        ).all()
        related_ids = {
            item.input_asset_id for item in inputs
        } | {
            item.output_asset_id for item in outputs
        }
        related_assets: list[MediaAssetRecord] = []
        if related_ids:
            related_statement = select(MediaAsset).where(
                MediaAsset.id.in_(related_ids),
                MediaAsset.world_id == world_id,
                MediaAsset.worldline_id == asset.worldline_id,
                MediaAsset.status != MediaAssetStatus.DELETED.value,
            )
            if member_visible_only:
                related_statement = related_statement.where(
                    MediaAsset.visibility.in_(MEMBER_VISIBLE_MEDIA_VISIBILITIES)
                )
            related_assets = [
                _asset_record(model) for model in self._session.scalars(related_statement).all()
            ]
        return MediaAssetLineage(
            asset_id=asset_id,
            inputs=[_input_record(model) for model in inputs],
            outputs=[_input_record(model) for model in outputs],
            related_assets=related_assets,
        )

    def _contexts(self, world_id: uuid.UUID, asset: MediaAsset) -> list[MediaContextRecord]:
        statement = (
            select(MediaAssetContext)
            .where(
                MediaAssetContext.world_id == world_id,
                MediaAssetContext.worldline_id == asset.worldline_id,
                MediaAssetContext.asset_id == asset.id,
            )
            .order_by(MediaAssetContext.created_at.desc())
        )
        return [_context_record(model) for model in self._session.scalars(statement).all()]

    def _collections_for_asset(
        self,
        world_id: uuid.UUID,
        asset: MediaAsset,
        *,
        member_visible_only: bool,
    ) -> list[MediaAssetCollectionRecord]:
        statement = (
            select(MediaAssetCollection)
            .join(
                MediaAssetCollectionItem,
                MediaAssetCollectionItem.collection_id == MediaAssetCollection.id,
            )
            .where(
                MediaAssetCollectionItem.world_id == world_id,
                MediaAssetCollectionItem.worldline_id == asset.worldline_id,
                MediaAssetCollectionItem.asset_id == asset.id,
                MediaAssetCollection.status == MediaCollectionStatus.ACTIVE.value,
            )
        )
        if member_visible_only:
            statement = statement.where(
                MediaAssetCollection.visibility.in_(MEMBER_VISIBLE_MEDIA_VISIBILITIES)
            )
        statement = statement.order_by(MediaAssetCollection.created_at.desc())
        return [_collection_record(model) for model in self._session.scalars(statement).all()]

    def _count_inputs(
        self,
        world_id: uuid.UUID,
        asset: MediaAsset,
        visible_asset_ids: set[uuid.UUID] | None,
        *,
        as_input: bool,
    ) -> int:
        statement = select(func.count(MediaAssetInput.id)).where(
            MediaAssetInput.world_id == world_id,
            MediaAssetInput.worldline_id == asset.worldline_id,
        )
        if as_input:
            statement = statement.where(MediaAssetInput.input_asset_id == asset.id)
            if visible_asset_ids is not None:
                statement = statement.where(MediaAssetInput.output_asset_id.in_(visible_asset_ids))
        else:
            statement = statement.where(MediaAssetInput.output_asset_id == asset.id)
            if visible_asset_ids is not None:
                statement = statement.where(MediaAssetInput.input_asset_id.in_(visible_asset_ids))
        return int(self._session.scalar(statement) or 0)

    def _visible_asset_ids(
        self, world_id: uuid.UUID, member_visible_only: bool
    ) -> set[uuid.UUID] | None:
        if not member_visible_only:
            return None
        return set(
            self._session.scalars(
                select(MediaAsset.id).where(
                    MediaAsset.world_id == world_id,
                    MediaAsset.status != MediaAssetStatus.DELETED.value,
                    MediaAsset.visibility.in_(MEMBER_VISIBLE_MEDIA_VISIBILITIES),
                )
            ).all()
        )


def _asset_required(
    session: Session,
    world_id: uuid.UUID,
    asset_id: uuid.UUID,
    *,
    include_deleted: bool = False,
) -> MediaAsset:
    model = session.get(MediaAsset, asset_id)
    if model is None or model.world_id != world_id:
        raise MediaNotFoundError("media asset not found")
    if not include_deleted and model.status == MediaAssetStatus.DELETED.value:
        raise MediaNotFoundError("media asset not found")
    return model


def _worldline_id(
    session: Session, world_id: uuid.UUID, worldline_id: uuid.UUID | None
) -> uuid.UUID:
    try:
        return worldline_or_404(session, world_id, worldline_id).id
    except ValueError as exc:
        raise MediaValidationError("worldline not found") from exc


def _tag_record(model: MediaAssetTag) -> MediaAssetTagRecord:
    return MediaAssetTagRecord(
        id=model.id,
        world_id=model.world_id,
        worldline_id=model.worldline_id,
        asset_id=model.asset_id,
        tag_type=model.tag_type,
        tag_key=model.tag_key,
        tag_value=model.tag_value,
        confidence=model.confidence,
        source_kind=MediaTagSourceKind(model.source_kind),
        visibility=MediaVisibility(model.visibility),
        created_by_actor_ref=model.created_by_actor_ref,
        metadata=model.metadata_json,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _collection_record(model: MediaAssetCollection) -> MediaAssetCollectionRecord:
    return MediaAssetCollectionRecord(
        id=model.id,
        world_id=model.world_id,
        worldline_id=model.worldline_id,
        collection_kind=model.collection_kind,
        title=model.title,
        description=model.description,
        owner_agent_id=model.owner_agent_id,
        visibility=MediaVisibility(model.visibility),
        status=MediaCollectionStatus(model.status),
        created_by_actor_ref=model.created_by_actor_ref,
        metadata=model.metadata_json,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _collection_item_record(model: MediaAssetCollectionItem) -> MediaAssetCollectionItemRecord:
    return MediaAssetCollectionItemRecord(
        id=model.id,
        world_id=model.world_id,
        worldline_id=model.worldline_id,
        collection_id=model.collection_id,
        asset_id=model.asset_id,
        role=model.role,
        display_order=model.display_order,
        metadata=model.metadata_json,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
