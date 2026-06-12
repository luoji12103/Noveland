from __future__ import annotations

import uuid

from noveland.conversations.models import ConversationSession, ConversationTurn
from noveland.media.contracts import MediaAssetStatus, MediaReferenceKind, MediaVisibility
from noveland.media.models import MediaAsset, MediaObject, MediaReference
from noveland.media.storage import MediaObjectStorage
from noveland.moderation import ModerationService, ModerationTargetKind
from noveland.narrative.models import NarrativeArtifact, NarrativePublication
from noveland.reader_delivery.contracts import (
    ReaderMediaDescriptor,
    ReaderMediaObjectDescriptor,
    ReaderMediaReferenceDescriptor,
)
from noveland.worlds.models import Worldline
from sqlalchemy import select
from sqlalchemy.orm import Session

READER_DELIVERABLE_VISIBILITIES = {
    MediaVisibility.WORLD_MEMBER.value,
    MediaVisibility.PLAYER_VISIBLE.value,
    MediaVisibility.READER_VISIBLE.value,
}
READER_DELIVERABLE_KINDS = {"image", "audio", "video"}
READER_REFERENCE_KINDS = {
    MediaReferenceKind.NARRATIVE_ARTIFACT.value,
    MediaReferenceKind.CONVERSATION_TURN.value,
    MediaReferenceKind.CONVERSATION_SESSION.value,
}


class ReaderMediaDeliveryService:
    def __init__(
        self,
        session: Session,
        *,
        storage: MediaObjectStorage | None = None,
    ) -> None:
        self._session = session
        self._storage = storage

    def list_media(
        self,
        world_id: uuid.UUID,
        *,
        worldline_id: uuid.UUID | None = None,
        limit: int = 100,
    ) -> list[ReaderMediaDescriptor]:
        resolved_worldline_id = self._validated_worldline_id(world_id, worldline_id)
        statement = (
            select(MediaAsset)
            .where(
                MediaAsset.world_id == world_id,
                MediaAsset.status == MediaAssetStatus.AVAILABLE.value,
                MediaAsset.visibility.in_(READER_DELIVERABLE_VISIBILITIES),
                MediaAsset.asset_kind.in_(READER_DELIVERABLE_KINDS),
            )
            .order_by(MediaAsset.created_at.desc())
            .limit(max(1, min(limit, 200)))
        )
        if resolved_worldline_id is not None:
            statement = statement.where(MediaAsset.worldline_id == resolved_worldline_id)
        descriptors: list[ReaderMediaDescriptor] = []
        for asset in self._session.scalars(statement).all():
            descriptor = self._descriptor_for_asset(asset)
            if descriptor is not None:
                descriptors.append(descriptor)
        return descriptors

    def get_media(
        self,
        world_id: uuid.UUID,
        asset_id: uuid.UUID,
        *,
        worldline_id: uuid.UUID | None = None,
    ) -> ReaderMediaDescriptor | None:
        resolved_worldline_id = self._validated_worldline_id(world_id, worldline_id)
        asset = self._session.get(MediaAsset, asset_id)
        if asset is None or asset.world_id != world_id:
            return None
        if resolved_worldline_id is not None and asset.worldline_id != resolved_worldline_id:
            return None
        return self._descriptor_for_asset(asset)

    def read_object(
        self,
        world_id: uuid.UUID,
        object_id: uuid.UUID,
        *,
        worldline_id: uuid.UUID | None = None,
    ) -> tuple[ReaderMediaObjectDescriptor, bytes] | None:
        resolved_worldline_id = self._validated_worldline_id(world_id, worldline_id)
        if self._storage is None:
            return None
        media_object = self._session.get(MediaObject, object_id)
        if media_object is None or media_object.world_id != world_id:
            return None
        if resolved_worldline_id is not None and media_object.worldline_id != resolved_worldline_id:
            return None
        asset = self._session.get(MediaAsset, media_object.asset_id)
        if (
            asset is None
            or asset.world_id != world_id
            or asset.worldline_id != media_object.worldline_id
        ):
            return None
        descriptor = self._descriptor_for_asset(asset)
        if descriptor is None:
            return None
        for object_descriptor in descriptor.objects:
            if object_descriptor.object_id == object_id:
                return object_descriptor, self._storage.read_bytes(media_object.storage_uri)
        return None

    def _validated_worldline_id(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
    ) -> uuid.UUID | None:
        if worldline_id is None:
            return None
        worldline = self._session.get(Worldline, worldline_id)
        if worldline is None or worldline.world_id != world_id:
            raise ValueError("worldline not found")
        return worldline.id

    def _descriptor_for_asset(self, asset: MediaAsset) -> ReaderMediaDescriptor | None:
        if not self._asset_is_reader_deliverable(asset):
            return None
        if self._asset_is_moderation_suppressed(asset):
            return None
        references = self._reader_visible_references(asset)
        if not references:
            return None
        objects = self._reader_objects(asset)
        if not objects:
            return None
        primary = objects[0]
        return ReaderMediaDescriptor(
            asset_id=asset.id,
            world_id=asset.world_id,
            worldline_id=asset.worldline_id,
            asset_kind=asset.asset_kind,
            asset_role=asset.asset_role,
            visibility=asset.visibility,
            title=asset.title,
            description=asset.description,
            content_type=primary.content_type,
            size=primary.size,
            width=primary.width,
            height=primary.height,
            duration_ms=primary.duration_ms,
            objects=tuple(objects),
            references=tuple(references),
            created_at=asset.created_at,
            updated_at=asset.updated_at,
        )

    def _asset_is_moderation_suppressed(self, asset: MediaAsset) -> bool:
        return ModerationService(self._session).target_is_suppressed(
            asset.world_id,
            ModerationTargetKind.MEDIA_ASSET,
            asset.id,
            worldline_id=asset.worldline_id,
        )

    def _asset_is_reader_deliverable(self, asset: MediaAsset) -> bool:
        return (
            asset.status == MediaAssetStatus.AVAILABLE.value
            and asset.visibility in READER_DELIVERABLE_VISIBILITIES
            and asset.asset_kind in READER_DELIVERABLE_KINDS
        )

    def _reader_objects(self, asset: MediaAsset) -> list[ReaderMediaObjectDescriptor]:
        objects = self._session.scalars(
            select(MediaObject)
            .where(
                MediaObject.world_id == asset.world_id,
                MediaObject.worldline_id == asset.worldline_id,
                MediaObject.asset_id == asset.id,
            )
            .order_by(MediaObject.created_at)
        ).all()
        return [
            ReaderMediaObjectDescriptor(
                object_id=media_object.id,
                object_role=media_object.object_role,
                content_type=media_object.mime_type,
                size=media_object.size_bytes,
                checksum_sha256=media_object.checksum_sha256,
                width=media_object.width,
                height=media_object.height,
                duration_ms=media_object.duration_ms,
                sample_rate_hz=media_object.sample_rate_hz,
                audio_channels=media_object.audio_channels,
                download_url=(
                    f"/worlds/{media_object.world_id}/reader/media/worldlines/"
                    f"{media_object.worldline_id}/objects/{media_object.id}/download"
                ),
            )
            for media_object in objects
        ]

    def _reader_visible_references(
        self,
        asset: MediaAsset,
    ) -> list[ReaderMediaReferenceDescriptor]:
        refs = self._session.scalars(
            select(MediaReference)
            .where(
                MediaReference.world_id == asset.world_id,
                MediaReference.worldline_id == asset.worldline_id,
                MediaReference.asset_id == asset.id,
                MediaReference.ref_kind.in_(READER_REFERENCE_KINDS),
            )
            .order_by(MediaReference.display_order, MediaReference.created_at)
        ).all()
        return [
            ReaderMediaReferenceDescriptor(
                reference_id=ref.id,
                ref_kind=ref.ref_kind,
                ref_id=ref.ref_id,
                ref_role=ref.ref_role,
                display_order=ref.display_order,
            )
            for ref in refs
            if self._reference_is_reader_visible(ref)
        ]

    def _reference_is_reader_visible(self, ref: MediaReference) -> bool:
        if ref.ref_kind == MediaReferenceKind.NARRATIVE_ARTIFACT.value:
            return self._narrative_artifact_is_reader_visible(ref)
        if ref.ref_kind == MediaReferenceKind.CONVERSATION_TURN.value:
            return self._conversation_turn_is_reader_visible(ref)
        if ref.ref_kind == MediaReferenceKind.CONVERSATION_SESSION.value:
            return self._conversation_session_is_reader_visible(ref)
        return False

    def _narrative_artifact_is_reader_visible(self, ref: MediaReference) -> bool:
        artifact = self._session.get(NarrativeArtifact, ref.ref_id)
        if (
            artifact is None
            or artifact.world_id != ref.world_id
            or (artifact.worldline_id is not None and artifact.worldline_id != ref.worldline_id)
        ):
            return False
        publication = self._session.scalars(
            select(NarrativePublication).where(
                NarrativePublication.world_id == ref.world_id,
                NarrativePublication.artifact_id == ref.ref_id,
                NarrativePublication.status == "published",
                NarrativePublication.reader_visible.is_(True),
            )
        ).first()
        return publication is not None and (
            publication.worldline_id is None or publication.worldline_id == ref.worldline_id
        )

    def _conversation_turn_is_reader_visible(self, ref: MediaReference) -> bool:
        turn = self._session.get(ConversationTurn, ref.ref_id)
        if turn is None:
            return False
        conversation = self._session.get(ConversationSession, turn.session_id)
        return (
            conversation is not None
            and conversation.world_id == ref.world_id
            and conversation.worldline_id == ref.worldline_id
        )

    def _conversation_session_is_reader_visible(self, ref: MediaReference) -> bool:
        conversation = self._session.get(ConversationSession, ref.ref_id)
        return (
            conversation is not None
            and conversation.world_id == ref.world_id
            and conversation.worldline_id == ref.worldline_id
        )
