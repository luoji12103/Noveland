from __future__ import annotations

import hashlib
import mimetypes
import uuid
from datetime import UTC, datetime

from noveland.agents.models import Agent
from noveland.conversations.models import ConversationSession, ConversationTurn
from noveland.core.database import Base
from noveland.events.models import WorldEventModel
from noveland.media.contracts import (
    AUDIO_MIME_TYPES,
    IMAGE_MIME_TYPES,
    ConversationTurnMediaAttachmentCreate,
    ConversationTurnMediaAttachmentRecord,
    MediaAssetCreate,
    MediaAssetInputCreate,
    MediaAssetInputRecord,
    MediaAssetKind,
    MediaAssetLineage,
    MediaAssetListFilters,
    MediaAssetRecord,
    MediaAssetReferences,
    MediaAssetRole,
    MediaAssetStatus,
    MediaAssetUpdate,
    MediaAssetUploadRequest,
    MediaAssetUploadResponse,
    MediaContextCreate,
    MediaContextRecord,
    MediaContextRole,
    MediaInputRole,
    MediaJobCreate,
    MediaJobKind,
    MediaJobListFilters,
    MediaJobRecord,
    MediaJobStatus,
    MediaJobUpdate,
    MediaObjectCreate,
    MediaObjectRecord,
    MediaObjectRole,
    MediaReferenceCreate,
    MediaReferenceKind,
    MediaReferenceListFilters,
    MediaReferenceRecord,
    MediaReferenceRole,
    MediaSourceKind,
    MediaVisibility,
)
from noveland.media.errors import MediaConflictError, MediaNotFoundError, MediaValidationError
from noveland.media.models import (
    MediaAsset,
    MediaAssetContext,
    MediaAssetInput,
    MediaJob,
    MediaObject,
    MediaReference,
)
from noveland.media.storage import MediaObjectStorage
from noveland.narrative.models import NarrativeArtifact
from noveland.worlds.models import Scene, World
from noveland.worlds.worldlines import worldline_or_404
from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

MEMBER_VISIBLE_ASSET_VISIBILITIES = {
    MediaVisibility.WORLD_MEMBER.value,
    MediaVisibility.PLAYER_VISIBLE.value,
    MediaVisibility.READER_VISIBLE.value,
}
RESTRICTED_ASSET_VISIBILITIES = {
    MediaVisibility.DEVELOPER_ONLY.value,
    MediaVisibility.HIDDEN.value,
}


class MediaService:
    def __init__(
        self,
        session: Session,
        storage: MediaObjectStorage | None = None,
    ) -> None:
        self._session = session
        self._storage = storage

    def create_asset(
        self,
        asset_create: MediaAssetCreate,
        *,
        actor_ref: str,
    ) -> MediaAssetRecord:
        worldline_id = self._worldline_id(asset_create.world_id, asset_create.worldline_id)
        self._validate_source_refs(asset_create.world_id, worldline_id, asset_create)
        self._validate_asset_status(asset_create, worldline_id)
        model = MediaAsset(
            id=uuid.uuid4(),
            world_id=asset_create.world_id,
            worldline_id=worldline_id,
            asset_kind=asset_create.asset_kind.value,
            asset_role=asset_create.asset_role.value,
            source_kind=asset_create.source_kind.value,
            status=asset_create.status.value,
            visibility=asset_create.visibility.value,
            storage_uri=asset_create.storage_uri,
            preview_uri=asset_create.preview_uri,
            thumbnail_uri=asset_create.thumbnail_uri,
            mime_type=asset_create.mime_type,
            file_ext=asset_create.file_ext,
            size_bytes=asset_create.size_bytes,
            checksum_sha256=asset_create.checksum_sha256,
            width=asset_create.width,
            height=asset_create.height,
            duration_ms=asset_create.duration_ms,
            sample_rate_hz=asset_create.sample_rate_hz,
            audio_channels=asset_create.audio_channels,
            has_alpha=asset_create.has_alpha,
            color_mode=asset_create.color_mode,
            provider_kind=asset_create.provider_kind,
            source_job_id=asset_create.source_job_id,
            source_event_id=asset_create.source_event_id,
            source_invocation_id=asset_create.source_invocation_id,
            title=asset_create.title or asset_create.filename,
            description=asset_create.description,
            created_by_actor_ref=actor_ref,
            metadata_json=asset_create.metadata,
        )
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return _asset_record(model)

    def upload_asset(
        self,
        upload: MediaAssetUploadRequest,
        *,
        data: bytes,
        filename: str | None,
        mime_type: str,
        actor_ref: str,
    ) -> MediaAssetUploadResponse:
        if self._storage is None:
            raise MediaValidationError("media upload requires media storage")
        worldline_id = self._worldline_id(upload.world_id, upload.worldline_id)
        checksum = hashlib.sha256(data).hexdigest()
        asset_id = uuid.uuid4()
        file_ext = _file_extension(filename, mime_type)
        key = (
            f"worlds/{upload.world_id}/worldlines/{worldline_id}/assets/{asset_id}/"
            f"original-{checksum}{file_ext}"
        )
        stored = self._storage.write_bytes(key, data, content_type=mime_type)
        asset = MediaAsset(
            id=asset_id,
            world_id=upload.world_id,
            worldline_id=worldline_id,
            asset_kind=upload.asset_kind.value,
            asset_role=upload.asset_role.value,
            source_kind=MediaSourceKind.MANUAL_UPLOAD.value,
            status=MediaAssetStatus.AVAILABLE.value,
            visibility=upload.visibility.value,
            storage_uri=stored.uri,
            preview_uri=None,
            thumbnail_uri=None,
            mime_type=mime_type,
            file_ext=file_ext.removeprefix(".") if file_ext else None,
            size_bytes=stored.size_bytes,
            checksum_sha256=stored.checksum_sha256,
            width=None,
            height=None,
            duration_ms=None,
            sample_rate_hz=None,
            audio_channels=None,
            has_alpha=None,
            color_mode=None,
            provider_kind=None,
            source_job_id=None,
            source_event_id=None,
            source_invocation_id=None,
            title=upload.title or filename,
            description=upload.description,
            created_by_actor_ref=actor_ref,
            metadata_json=upload.metadata,
        )
        media_object = MediaObject(
            id=uuid.uuid4(),
            asset_id=asset_id,
            world_id=upload.world_id,
            worldline_id=worldline_id,
            object_role=MediaObjectRole.ORIGINAL.value,
            storage_uri=stored.uri,
            filename=filename,
            mime_type=mime_type,
            size_bytes=stored.size_bytes,
            checksum_sha256=stored.checksum_sha256,
            width=None,
            height=None,
            duration_ms=None,
            sample_rate_hz=None,
            audio_channels=None,
            frame_rate=None,
            metadata_json={},
        )
        self._session.add(asset)
        self._session.add(media_object)
        self._session.flush()
        self._session.refresh(asset)
        self._session.refresh(media_object)
        return MediaAssetUploadResponse(
            asset=_asset_record(asset),
            object=_object_record(media_object),
        )

    def add_object(
        self,
        world_id: uuid.UUID,
        asset_id: uuid.UUID,
        object_create: MediaObjectCreate,
    ) -> MediaObjectRecord:
        if object_create.world_id != world_id:
            raise MediaValidationError("object world_id must match route world_id")
        asset = self._asset_required_any_worldline(world_id, asset_id)
        worldline_id = self._worldline_id(world_id, object_create.worldline_id)
        if asset.worldline_id != worldline_id:
            raise MediaValidationError("object worldline must match asset worldline")
        self._validate_media_uri_scope(object_create.storage_uri, world_id, worldline_id)
        if self._storage is not None:
            if not self._storage.exists(object_create.storage_uri):
                raise MediaValidationError("media object storage URI does not exist")
            data = self._storage.read_bytes(object_create.storage_uri)
            if hashlib.sha256(data).hexdigest() != object_create.checksum_sha256:
                raise MediaValidationError("media object checksum does not match storage object")
            if len(data) != object_create.size_bytes:
                raise MediaValidationError("media object size does not match storage object")
        model = MediaObject(
            id=uuid.uuid4(),
            asset_id=asset_id,
            world_id=world_id,
            worldline_id=worldline_id,
            object_role=object_create.object_role.value,
            storage_uri=object_create.storage_uri,
            filename=object_create.filename,
            mime_type=object_create.mime_type,
            size_bytes=object_create.size_bytes,
            checksum_sha256=object_create.checksum_sha256,
            width=object_create.width,
            height=object_create.height,
            duration_ms=object_create.duration_ms,
            sample_rate_hz=object_create.sample_rate_hz,
            audio_channels=object_create.audio_channels,
            frame_rate=object_create.frame_rate,
            metadata_json=object_create.metadata,
        )
        self._session.add(model)
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise MediaValidationError("media object storage_uri already exists") from exc
        self._session.refresh(model)
        return _object_record(model)

    def list_objects(
        self,
        world_id: uuid.UUID,
        asset_id: uuid.UUID,
        *,
        allow_restricted: bool = True,
    ) -> list[MediaObjectRecord]:
        asset = self._asset_required_any_worldline(world_id, asset_id, include_deleted=True)
        if not allow_restricted and asset.visibility in RESTRICTED_ASSET_VISIBILITIES:
            raise MediaNotFoundError("media asset not found")
        statement = (
            select(MediaObject)
            .where(
                MediaObject.world_id == world_id,
                MediaObject.worldline_id == asset.worldline_id,
                MediaObject.asset_id == asset_id,
            )
            .order_by(MediaObject.created_at)
        )
        return [_object_record(model) for model in self._session.scalars(statement).all()]

    def get_object(
        self,
        world_id: uuid.UUID,
        object_id: uuid.UUID,
        *,
        member_visible_only: bool = False,
        allow_restricted: bool = True,
    ) -> MediaObjectRecord | None:
        model = self._object_or_none(
            world_id,
            object_id,
            member_visible_only=member_visible_only,
            allow_restricted=allow_restricted,
        )
        return None if model is None else _object_record(model)

    def read_object_bytes(
        self,
        world_id: uuid.UUID,
        object_id: uuid.UUID,
        *,
        member_visible_only: bool = False,
        allow_restricted: bool = True,
    ) -> tuple[MediaObjectRecord, bytes]:
        if self._storage is None:
            raise MediaValidationError("media download requires media storage")
        model = self._object_or_none(
            world_id,
            object_id,
            member_visible_only=member_visible_only,
            allow_restricted=allow_restricted,
        )
        if model is None:
            raise MediaNotFoundError("media object not found")
        return _object_record(model), self._storage.read_bytes(model.storage_uri)

    def get_asset(
        self,
        world_id: uuid.UUID,
        asset_id: uuid.UUID,
        *,
        worldline_id: uuid.UUID | None = None,
        include_deleted: bool = False,
        member_visible_only: bool = False,
        allow_restricted: bool = True,
    ) -> MediaAssetRecord | None:
        resolved_worldline_id = self._worldline_id(world_id, worldline_id)
        model = self._asset_or_none(
            world_id,
            resolved_worldline_id,
            asset_id,
            include_deleted=include_deleted,
            member_visible_only=member_visible_only,
            allow_restricted=allow_restricted,
        )
        return None if model is None else _asset_record(model)

    def get_asset_by_id(
        self,
        world_id: uuid.UUID,
        asset_id: uuid.UUID,
        *,
        include_deleted: bool = False,
        member_visible_only: bool = False,
        allow_restricted: bool = True,
    ) -> MediaAssetRecord | None:
        model = self._session.get(MediaAsset, asset_id)
        if (
            model is None
            or model.world_id != world_id
            or (not include_deleted and model.status == MediaAssetStatus.DELETED.value)
        ):
            return None
        if member_visible_only and model.visibility not in MEMBER_VISIBLE_ASSET_VISIBILITIES:
            return None
        if not allow_restricted and model.visibility in RESTRICTED_ASSET_VISIBILITIES:
            return None
        return _asset_record(model)

    def list_assets(
        self,
        world_id: uuid.UUID,
        filters: MediaAssetListFilters,
        *,
        member_visible_only: bool = False,
    ) -> list[MediaAssetRecord]:
        worldline_id = self._worldline_id(world_id, filters.worldline_id)
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
        if filters.created_after is not None:
            statement = statement.where(MediaAsset.created_at >= filters.created_after)
        if filters.created_before is not None:
            statement = statement.where(MediaAsset.created_at <= filters.created_before)
        if filters.source_event_id is not None:
            statement = statement.where(MediaAsset.source_event_id == filters.source_event_id)
        if filters.source_invocation_id is not None:
            statement = statement.where(
                MediaAsset.source_invocation_id == filters.source_invocation_id
            )
        if filters.contains_text is not None:
            pattern = f"%{filters.contains_text}%"
            statement = statement.where(
                MediaAsset.title.ilike(pattern) | MediaAsset.description.ilike(pattern)
            )
        statement = self._apply_reference_filter(statement, filters)
        if member_visible_only:
            statement = statement.where(
                MediaAsset.visibility.in_(MEMBER_VISIBLE_ASSET_VISIBILITIES)
            )
        statement = statement.order_by(MediaAsset.created_at.desc()).limit(filters.limit)
        return [_asset_record(model) for model in self._session.scalars(statement).all()]

    def update_asset(
        self,
        world_id: uuid.UUID,
        asset_id: uuid.UUID,
        asset_update: MediaAssetUpdate,
    ) -> MediaAssetRecord:
        model = self._asset_required_any_worldline(world_id, asset_id)
        if asset_update.visibility is not None:
            model.visibility = asset_update.visibility.value
        if asset_update.status is not None:
            if asset_update.status == MediaAssetStatus.AVAILABLE:
                raise MediaValidationError(
                    "available status requires verified storage registration"
                )
            model.status = asset_update.status.value
        if asset_update.title is not None:
            model.title = asset_update.title
        if asset_update.description is not None:
            model.description = asset_update.description
        if asset_update.metadata is not None:
            model.metadata_json = asset_update.metadata
        self._session.flush()
        self._session.refresh(model)
        return _asset_record(model)

    def delete_asset(self, world_id: uuid.UUID, asset_id: uuid.UUID) -> None:
        model = self._asset_required_any_worldline(world_id, asset_id)
        model.status = MediaAssetStatus.DELETED.value
        self._session.flush()

    def attach_context(
        self,
        world_id: uuid.UUID,
        asset_id: uuid.UUID,
        context_create: MediaContextCreate,
    ) -> MediaContextRecord:
        if context_create.world_id != world_id:
            raise MediaValidationError("context world_id must match route world_id")
        asset = self._asset_required_any_worldline(world_id, asset_id, include_deleted=False)
        worldline_id = self._worldline_id(world_id, context_create.worldline_id)
        if asset.worldline_id != worldline_id:
            raise MediaValidationError("asset and context worldline must match")
        self._validate_context_refs(world_id, worldline_id, context_create)
        model = MediaAssetContext(
            id=uuid.uuid4(),
            world_id=world_id,
            worldline_id=worldline_id,
            asset_id=asset_id,
            conversation_id=context_create.conversation_id,
            turn_id=context_create.turn_id,
            agent_id=context_create.agent_id,
            world_event_id=context_create.world_event_id,
            narrative_artifact_id=context_create.narrative_artifact_id,
            context_role=context_create.context_role.value,
            metadata_json=context_create.metadata,
        )
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return _context_record(model)

    def list_contexts(self, world_id: uuid.UUID, asset_id: uuid.UUID) -> list[MediaContextRecord]:
        asset = self._asset_required_any_worldline(world_id, asset_id, include_deleted=True)
        statement = (
            select(MediaAssetContext)
            .where(
                MediaAssetContext.world_id == world_id,
                MediaAssetContext.worldline_id == asset.worldline_id,
                MediaAssetContext.asset_id == asset_id,
            )
            .order_by(MediaAssetContext.created_at.desc())
        )
        return [_context_record(model) for model in self._session.scalars(statement).all()]

    def detach_context(
        self, world_id: uuid.UUID, asset_id: uuid.UUID, context_id: uuid.UUID
    ) -> None:
        model = self._session.get(MediaAssetContext, context_id)
        if model is None or model.world_id != world_id or model.asset_id != asset_id:
            raise MediaNotFoundError("media context not found")
        self._session.delete(model)
        self._session.flush()

    def add_input(
        self,
        world_id: uuid.UUID,
        output_asset_id: uuid.UUID,
        input_create: MediaAssetInputCreate,
    ) -> MediaAssetInputRecord:
        if input_create.world_id != world_id:
            raise MediaValidationError("input world_id must match route world_id")
        output_asset = self._asset_required_any_worldline(world_id, output_asset_id)
        input_asset = self._asset_required_any_worldline(world_id, input_create.input_asset_id)
        worldline_id = self._worldline_id(world_id, input_create.worldline_id)
        if output_asset.worldline_id != worldline_id or input_asset.worldline_id != worldline_id:
            raise MediaValidationError("input and output assets must share one worldline")
        if input_create.source_job_id is not None:
            job = self._job_required(world_id, worldline_id, input_create.source_job_id)
            if job.worldline_id != worldline_id:
                raise MediaValidationError("source job worldline must match asset worldline")
        model = MediaAssetInput(
            id=uuid.uuid4(),
            world_id=world_id,
            worldline_id=worldline_id,
            output_asset_id=output_asset_id,
            input_asset_id=input_create.input_asset_id,
            source_job_id=input_create.source_job_id,
            input_role=input_create.input_role.value,
            display_order=input_create.display_order,
            metadata_json=input_create.metadata,
        )
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return _input_record(model)

    def list_inputs(self, world_id: uuid.UUID, asset_id: uuid.UUID) -> list[MediaAssetInputRecord]:
        asset = self._asset_required_any_worldline(world_id, asset_id, include_deleted=True)
        statement = (
            select(MediaAssetInput)
            .where(
                MediaAssetInput.world_id == world_id,
                MediaAssetInput.worldline_id == asset.worldline_id,
                MediaAssetInput.output_asset_id == asset_id,
            )
            .order_by(MediaAssetInput.display_order, MediaAssetInput.created_at)
        )
        return [_input_record(model) for model in self._session.scalars(statement).all()]

    def references(self, world_id: uuid.UUID, asset_id: uuid.UUID) -> MediaAssetReferences:
        contexts = self.list_contexts(world_id, asset_id)
        input_count = self._session.scalar(
            select(func.count(MediaAssetInput.id)).where(
                MediaAssetInput.input_asset_id == asset_id
            ),
        )
        output_count = self._session.scalar(
            select(func.count(MediaAssetInput.id)).where(
                MediaAssetInput.output_asset_id == asset_id
            ),
        )
        return MediaAssetReferences(
            asset_id=asset_id,
            contexts=contexts,
            input_count=int(input_count or 0),
            output_count=int(output_count or 0),
        )

    def lineage(self, world_id: uuid.UUID, asset_id: uuid.UUID) -> MediaAssetLineage:
        asset = self._asset_required_any_worldline(world_id, asset_id, include_deleted=True)
        inputs = self._session.scalars(
            select(MediaAssetInput)
            .where(
                MediaAssetInput.world_id == world_id,
                MediaAssetInput.worldline_id == asset.worldline_id,
                MediaAssetInput.output_asset_id == asset_id,
            )
            .order_by(MediaAssetInput.display_order, MediaAssetInput.created_at),
        ).all()
        outputs = self._session.scalars(
            select(MediaAssetInput)
            .where(
                MediaAssetInput.world_id == world_id,
                MediaAssetInput.worldline_id == asset.worldline_id,
                MediaAssetInput.input_asset_id == asset_id,
            )
            .order_by(MediaAssetInput.display_order, MediaAssetInput.created_at),
        ).all()
        return MediaAssetLineage(
            asset_id=asset_id,
            inputs=[_input_record(model) for model in inputs],
            outputs=[_input_record(model) for model in outputs],
        )

    def _validate_source_refs(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        asset_create: MediaAssetCreate,
    ) -> None:
        if asset_create.source_job_id is not None:
            self._job_required(world_id, worldline_id, asset_create.source_job_id)
        if asset_create.source_event_id is not None:
            event = self._session.get(WorldEventModel, asset_create.source_event_id)
            if event is None or event.world_id != world_id or event.worldline_id != worldline_id:
                raise MediaValidationError("source event must belong to the asset worldline")
        if asset_create.source_invocation_id is not None:
            _validate_model_invocation(
                self._session,
                world_id,
                worldline_id,
                asset_create.source_invocation_id,
                "source invocation",
            )

    def _validate_asset_status(
        self,
        asset_create: MediaAssetCreate,
        worldline_id: uuid.UUID,
    ) -> None:
        if asset_create.status == MediaAssetStatus.REGISTERED:
            if asset_create.storage_uri is not None:
                self._validate_media_uri_scope(
                    asset_create.storage_uri,
                    asset_create.world_id,
                    worldline_id,
                )
            return
        if asset_create.status == MediaAssetStatus.AVAILABLE:
            self._validate_available_asset(asset_create, worldline_id)
            return
        if asset_create.storage_uri is not None:
            self._validate_media_uri_scope(
                asset_create.storage_uri, asset_create.world_id, worldline_id
            )

    def _validate_available_asset(
        self,
        asset_create: MediaAssetCreate,
        worldline_id: uuid.UUID,
    ) -> None:
        if self._storage is None:
            raise MediaValidationError("available asset registration requires media storage")
        if asset_create.storage_uri is None:
            raise MediaValidationError("available assets require a storage_uri")
        if asset_create.size_bytes is None or asset_create.size_bytes <= 0:
            raise MediaValidationError("available assets require positive size_bytes")
        if asset_create.checksum_sha256 is None:
            raise MediaValidationError("available assets require checksum_sha256")
        if asset_create.mime_type is None:
            raise MediaValidationError("available assets require mime_type")
        self._validate_media_uri_scope(
            asset_create.storage_uri, asset_create.world_id, worldline_id
        )
        if not self._storage.exists(asset_create.storage_uri):
            raise MediaValidationError("available asset storage object does not exist")
        data = self._storage.read_bytes(asset_create.storage_uri)
        import hashlib

        checksum = hashlib.sha256(data).hexdigest()
        if checksum != asset_create.checksum_sha256:
            raise MediaValidationError("available asset checksum does not match storage object")
        if len(data) != asset_create.size_bytes:
            raise MediaValidationError("available asset size does not match storage object")
        self._validate_mime(asset_create.asset_kind, asset_create.mime_type)

    def _validate_context_refs(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        context_create: MediaContextCreate,
    ) -> None:
        if context_create.narrative_artifact_id is not None:
            artifact = self._session.get(NarrativeArtifact, context_create.narrative_artifact_id)
            if artifact is None or artifact.world_id != world_id:
                raise MediaValidationError("narrative artifact must belong to media world")
            raise MediaValidationError(
                "narrative artifact media contexts are not supported in Phase 1"
            )
        if context_create.conversation_id is not None:
            conversation = self._session.get(ConversationSession, context_create.conversation_id)
            if (
                conversation is None
                or conversation.world_id != world_id
                or conversation.worldline_id != worldline_id
            ):
                raise MediaValidationError("conversation must belong to the context worldline")
        if context_create.turn_id is not None:
            turn = self._session.get(ConversationTurn, context_create.turn_id)
            if turn is None:
                raise MediaValidationError("turn must belong to the context worldline")
            session_model = self._session.get(ConversationSession, turn.session_id)
            if (
                session_model is None
                or session_model.world_id != world_id
                or session_model.worldline_id != worldline_id
            ):
                raise MediaValidationError("turn must belong to the context worldline")
            if (
                context_create.conversation_id is not None
                and context_create.conversation_id != session_model.id
            ):
                raise MediaValidationError("turn must belong to the referenced conversation")
        if context_create.agent_id is not None:
            agent = self._session.get(Agent, context_create.agent_id)
            if agent is None or agent.world_id != world_id:
                raise MediaValidationError("agent must belong to media world")
        if context_create.world_event_id is not None:
            event = self._session.get(WorldEventModel, context_create.world_event_id)
            if event is None or event.world_id != world_id or event.worldline_id != worldline_id:
                raise MediaValidationError("event must belong to the context worldline")

    def _validate_media_uri_scope(
        self,
        uri: str,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
    ) -> None:
        expected_prefix = f"media://worlds/{world_id}/worldlines/{worldline_id}/"
        if not uri.startswith(expected_prefix):
            raise MediaValidationError("media URI must belong to the asset worldline")

    def _validate_mime(self, asset_kind: MediaAssetKind, mime_type: str) -> None:
        if asset_kind == MediaAssetKind.IMAGE:
            allowed: set[str] | None = IMAGE_MIME_TYPES
        elif asset_kind == MediaAssetKind.AUDIO:
            allowed = AUDIO_MIME_TYPES
        else:
            allowed = None
        if allowed is not None and mime_type not in allowed:
            raise MediaValidationError("mime_type is not allowed for asset kind")

    def _apply_reference_filter(
        self,
        statement: Select[tuple[MediaAsset]],
        filters: MediaAssetListFilters,
    ) -> Select[tuple[MediaAsset]]:
        if filters.ref_kind is None and filters.ref_id is None:
            return statement
        reference_exists = select(MediaReference.id).where(
            MediaReference.world_id == MediaAsset.world_id,
            MediaReference.worldline_id == MediaAsset.worldline_id,
            MediaReference.asset_id == MediaAsset.id,
        )
        if filters.ref_kind is not None:
            reference_exists = reference_exists.where(
                MediaReference.ref_kind == filters.ref_kind.value
            )
        if filters.ref_id is not None:
            reference_exists = reference_exists.where(MediaReference.ref_id == filters.ref_id)
        return statement.where(reference_exists.exists())

    def _asset_required_any_worldline(
        self,
        world_id: uuid.UUID,
        asset_id: uuid.UUID,
        *,
        include_deleted: bool = False,
    ) -> MediaAsset:
        model = self._session.get(MediaAsset, asset_id)
        if model is None or model.world_id != world_id:
            raise MediaNotFoundError("media asset not found")
        if not include_deleted and model.status == MediaAssetStatus.DELETED.value:
            raise MediaNotFoundError("media asset not found")
        return model

    def _asset_or_none(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        asset_id: uuid.UUID,
        *,
        include_deleted: bool,
        member_visible_only: bool,
        allow_restricted: bool,
    ) -> MediaAsset | None:
        model = self._session.get(MediaAsset, asset_id)
        if (
            model is None
            or model.world_id != world_id
            or model.worldline_id != worldline_id
            or (not include_deleted and model.status == MediaAssetStatus.DELETED.value)
        ):
            return None
        if member_visible_only and model.visibility not in MEMBER_VISIBLE_ASSET_VISIBILITIES:
            return None
        if not allow_restricted and model.visibility in RESTRICTED_ASSET_VISIBILITIES:
            return None
        return model

    def _object_or_none(
        self,
        world_id: uuid.UUID,
        object_id: uuid.UUID,
        *,
        member_visible_only: bool,
        allow_restricted: bool,
    ) -> MediaObject | None:
        model = self._session.get(MediaObject, object_id)
        if model is None or model.world_id != world_id:
            return None
        asset = self._session.get(MediaAsset, model.asset_id)
        if asset is None or asset.world_id != world_id or asset.worldline_id != model.worldline_id:
            return None
        if asset.status == MediaAssetStatus.DELETED.value:
            return None
        if member_visible_only and asset.visibility not in MEMBER_VISIBLE_ASSET_VISIBILITIES:
            return None
        if not allow_restricted and asset.visibility in RESTRICTED_ASSET_VISIBILITIES:
            return None
        return model

    def _job_required(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        job_id: uuid.UUID,
    ) -> MediaJob:
        model = self._session.get(MediaJob, job_id)
        if model is None or model.world_id != world_id or model.worldline_id != worldline_id:
            raise MediaValidationError("media job must belong to the target worldline")
        return model

    def _worldline_id(self, world_id: uuid.UUID, worldline_id: uuid.UUID | None) -> uuid.UUID:
        try:
            return worldline_or_404(self._session, world_id, worldline_id).id
        except ValueError as exc:
            raise MediaValidationError("worldline not found") from exc


class MediaJobService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_job(self, job_create: MediaJobCreate, *, actor_ref: str) -> MediaJobRecord:
        worldline_id = self._worldline_id(job_create.world_id, job_create.worldline_id)
        self._validate_context(job_create.world_id, worldline_id, job_create)
        model = MediaJob(
            id=uuid.uuid4(),
            world_id=job_create.world_id,
            worldline_id=worldline_id,
            conversation_id=job_create.conversation_id,
            turn_id=job_create.turn_id,
            agent_id=job_create.agent_id,
            job_kind=job_create.job_kind.value,
            provider_kind=job_create.provider_kind,
            status=MediaJobStatus.QUEUED.value,
            priority=job_create.priority,
            cancel_policy=job_create.cancel_policy,
            deadline_hint=job_create.deadline_hint,
            dedupe_key=job_create.dedupe_key,
            invalidation_key=job_create.invalidation_key,
            source_event_id=job_create.source_event_id,
            source_invocation_id=job_create.source_invocation_id,
            provider_config_json=job_create.provider_config_json,
            request_json=job_create.request_json,
            result_json={},
            error_text=None,
            created_by_actor_ref=actor_ref,
            started_at=None,
            finished_at=None,
        )
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return _job_record(model)

    def get_job(
        self,
        world_id: uuid.UUID,
        job_id: uuid.UUID,
        *,
        worldline_id: uuid.UUID | None = None,
    ) -> MediaJobRecord | None:
        resolved_worldline_id = self._worldline_id(world_id, worldline_id)
        model = self._session.get(MediaJob, job_id)
        if (
            model is None
            or model.world_id != world_id
            or model.worldline_id != resolved_worldline_id
        ):
            return None
        return _job_record(model)

    def list_jobs(
        self,
        world_id: uuid.UUID,
        filters: MediaJobListFilters | None = None,
        *,
        worldline_id: uuid.UUID | None = None,
        status: MediaJobStatus | None = None,
        limit: int | None = None,
    ) -> list[MediaJobRecord]:
        if filters is None:
            filters = MediaJobListFilters(
                worldline_id=worldline_id,
                status=status,
                limit=100 if limit is None else limit,
            )
        resolved_worldline_id = self._worldline_id(world_id, filters.worldline_id)
        statement = select(MediaJob).where(
            MediaJob.world_id == world_id,
            MediaJob.worldline_id == resolved_worldline_id,
        )
        if filters.job_kind is not None:
            statement = statement.where(MediaJob.job_kind == filters.job_kind.value)
        if filters.status is not None:
            statement = statement.where(MediaJob.status == filters.status.value)
        if filters.priority_min is not None:
            statement = statement.where(MediaJob.priority >= filters.priority_min)
        if filters.priority_max is not None:
            statement = statement.where(MediaJob.priority <= filters.priority_max)
        if filters.agent_id is not None:
            statement = statement.where(MediaJob.agent_id == filters.agent_id)
        if filters.conversation_id is not None:
            statement = statement.where(MediaJob.conversation_id == filters.conversation_id)
        if filters.turn_id is not None:
            statement = statement.where(MediaJob.turn_id == filters.turn_id)
        if filters.source_event_id is not None:
            statement = statement.where(MediaJob.source_event_id == filters.source_event_id)
        if filters.source_invocation_id is not None:
            statement = statement.where(
                MediaJob.source_invocation_id == filters.source_invocation_id
            )
        if filters.provider_kind is not None:
            statement = statement.where(MediaJob.provider_kind == filters.provider_kind)
        if filters.invalidation_key is not None:
            statement = statement.where(MediaJob.invalidation_key == filters.invalidation_key)
        if filters.created_after is not None:
            statement = statement.where(MediaJob.created_at >= filters.created_after)
        if filters.created_before is not None:
            statement = statement.where(MediaJob.created_at <= filters.created_before)
        statement = statement.order_by(MediaJob.created_at.desc()).limit(filters.limit)
        return [_job_record(model) for model in self._session.scalars(statement).all()]

    def update_job(
        self,
        world_id: uuid.UUID,
        job_id: uuid.UUID,
        job_update: MediaJobUpdate,
    ) -> MediaJobRecord:
        model = self._job_required_any_worldline(world_id, job_id)
        if job_update.status is not None:
            model.status = job_update.status.value
        if job_update.priority is not None:
            model.priority = job_update.priority
        if job_update.cancel_policy is not None:
            model.cancel_policy = job_update.cancel_policy
        if job_update.deadline_hint is not None:
            model.deadline_hint = job_update.deadline_hint
        if job_update.provider_kind is not None:
            model.provider_kind = job_update.provider_kind
        if job_update.provider_config_json is not None:
            model.provider_config_json = job_update.provider_config_json
        if job_update.request_json is not None:
            model.request_json = job_update.request_json
        if job_update.result_json is not None:
            model.result_json = job_update.result_json
        if job_update.error_text is not None:
            model.error_text = job_update.error_text
        if job_update.started_at is not None:
            model.started_at = job_update.started_at
        if job_update.finished_at is not None:
            model.finished_at = job_update.finished_at
        self._session.flush()
        self._session.refresh(model)
        return _job_record(model)

    def cancel_job(self, world_id: uuid.UUID, job_id: uuid.UUID) -> MediaJobRecord:
        model = self._job_required_any_worldline(world_id, job_id)
        if model.status not in {MediaJobStatus.QUEUED.value, MediaJobStatus.RUNNING.value}:
            raise MediaConflictError("only queued or running media jobs can be cancelled")
        model.status = MediaJobStatus.CANCELLED.value
        model.finished_at = datetime.now(UTC)
        self._session.flush()
        self._session.refresh(model)
        return _job_record(model)

    def retry_job(
        self, world_id: uuid.UUID, job_id: uuid.UUID, *, actor_ref: str
    ) -> MediaJobRecord:
        model = self._job_required_any_worldline(world_id, job_id)
        if model.status not in {MediaJobStatus.FAILED.value, MediaJobStatus.CANCELLED.value}:
            raise MediaConflictError("only failed or cancelled media jobs can be retried")
        retry = MediaJob(
            id=uuid.uuid4(),
            world_id=model.world_id,
            worldline_id=model.worldline_id,
            conversation_id=model.conversation_id,
            turn_id=model.turn_id,
            agent_id=model.agent_id,
            job_kind=model.job_kind,
            provider_kind=model.provider_kind,
            status=MediaJobStatus.QUEUED.value,
            priority=model.priority,
            cancel_policy=model.cancel_policy,
            deadline_hint=model.deadline_hint,
            dedupe_key=model.dedupe_key,
            invalidation_key=model.invalidation_key,
            source_event_id=model.source_event_id,
            source_invocation_id=model.source_invocation_id,
            provider_config_json=model.provider_config_json,
            request_json=model.request_json,
            result_json={},
            error_text=None,
            created_by_actor_ref=actor_ref,
            started_at=None,
            finished_at=None,
        )
        self._session.add(retry)
        self._session.flush()
        self._session.refresh(retry)
        return _job_record(retry)

    def _validate_context(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        job_create: MediaJobCreate,
    ) -> None:
        if job_create.conversation_id is not None:
            conversation = self._session.get(ConversationSession, job_create.conversation_id)
            if (
                conversation is None
                or conversation.world_id != world_id
                or conversation.worldline_id != worldline_id
            ):
                raise MediaValidationError("conversation must belong to job worldline")
        if job_create.turn_id is not None:
            turn = self._session.get(ConversationTurn, job_create.turn_id)
            if turn is None:
                raise MediaValidationError("turn must belong to job worldline")
            session_model = self._session.get(ConversationSession, turn.session_id)
            if (
                session_model is None
                or session_model.world_id != world_id
                or session_model.worldline_id != worldline_id
            ):
                raise MediaValidationError("turn must belong to job worldline")
            if (
                job_create.conversation_id is not None
                and job_create.conversation_id != session_model.id
            ):
                raise MediaValidationError("turn must belong to the referenced conversation")
        if job_create.agent_id is not None:
            agent = self._session.get(Agent, job_create.agent_id)
            if agent is None or agent.world_id != world_id:
                raise MediaValidationError("agent must belong to job world")
        if job_create.source_event_id is not None:
            event = self._session.get(WorldEventModel, job_create.source_event_id)
            if event is None or event.world_id != world_id or event.worldline_id != worldline_id:
                raise MediaValidationError("source event must belong to job worldline")
        if job_create.source_invocation_id is not None:
            _validate_model_invocation(
                self._session,
                world_id,
                worldline_id,
                job_create.source_invocation_id,
                "source invocation",
            )

    def _job_required_any_worldline(self, world_id: uuid.UUID, job_id: uuid.UUID) -> MediaJob:
        model = self._session.get(MediaJob, job_id)
        if model is None or model.world_id != world_id:
            raise MediaNotFoundError("media job not found")
        return model

    def _worldline_id(self, world_id: uuid.UUID, worldline_id: uuid.UUID | None) -> uuid.UUID:
        try:
            return worldline_or_404(self._session, world_id, worldline_id).id
        except ValueError as exc:
            raise MediaValidationError("worldline not found") from exc


class MediaReferenceService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_reference(
        self,
        reference_create: MediaReferenceCreate,
        *,
        allow_restricted_assets: bool = True,
    ) -> MediaReferenceRecord:
        worldline_id = _worldline_id(
            self._session,
            reference_create.world_id,
            reference_create.worldline_id,
        )
        asset = self._asset_required(
            reference_create.world_id,
            reference_create.asset_id,
            include_deleted=False,
        )
        if asset.worldline_id != worldline_id:
            raise MediaValidationError("reference asset must belong to reference worldline")
        if (
            not allow_restricted_assets
            and asset.visibility in RESTRICTED_ASSET_VISIBILITIES
        ):
            raise MediaNotFoundError("media asset not found")
        self.validate_reference_target(
            reference_create.world_id,
            worldline_id,
            reference_create.ref_kind,
            reference_create.ref_id,
        )
        model = MediaReference(
            id=uuid.uuid4(),
            world_id=reference_create.world_id,
            worldline_id=worldline_id,
            asset_id=reference_create.asset_id,
            ref_kind=reference_create.ref_kind.value,
            ref_id=reference_create.ref_id,
            ref_role=reference_create.ref_role.value,
            display_order=reference_create.display_order,
            metadata_json=reference_create.metadata,
        )
        self._session.add(model)
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise MediaValidationError("media reference already exists") from exc
        self._session.refresh(model)
        return _reference_record(model)

    def list_references(
        self,
        world_id: uuid.UUID,
        filters: MediaReferenceListFilters,
        *,
        allow_restricted_assets: bool = True,
    ) -> list[MediaReferenceRecord]:
        worldline_id = _worldline_id(self._session, world_id, filters.worldline_id)
        statement = select(MediaReference).where(
            MediaReference.world_id == world_id,
            MediaReference.worldline_id == worldline_id,
        )
        if filters.asset_id is not None:
            statement = statement.where(MediaReference.asset_id == filters.asset_id)
        if filters.ref_kind is not None:
            statement = statement.where(MediaReference.ref_kind == filters.ref_kind.value)
        if filters.ref_id is not None:
            statement = statement.where(MediaReference.ref_id == filters.ref_id)
        if filters.ref_role is not None:
            statement = statement.where(MediaReference.ref_role == filters.ref_role.value)
        if not allow_restricted_assets:
            statement = statement.join(MediaAsset, MediaAsset.id == MediaReference.asset_id).where(
                MediaAsset.status != MediaAssetStatus.DELETED.value,
                MediaAsset.visibility.not_in(RESTRICTED_ASSET_VISIBILITIES),
            )
        statement = statement.order_by(MediaReference.created_at.desc()).limit(filters.limit)
        return [_reference_record(model) for model in self._session.scalars(statement).all()]

    def create_turn_media(
        self,
        world_id: uuid.UUID,
        conversation_id: uuid.UUID,
        turn_id: uuid.UUID,
        attachment_create: ConversationTurnMediaAttachmentCreate,
        *,
        allow_restricted_assets: bool = True,
    ) -> MediaReferenceRecord:
        worldline_id = self._turn_worldline_id(world_id, conversation_id, turn_id)
        if attachment_create.worldline_id is not None:
            requested_worldline_id = _worldline_id(
                self._session,
                world_id,
                attachment_create.worldline_id,
            )
            if requested_worldline_id != worldline_id:
                raise MediaValidationError("turn media worldline must match conversation turn")
        return self.create_reference(
            MediaReferenceCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                asset_id=attachment_create.asset_id,
                ref_kind=MediaReferenceKind.CONVERSATION_TURN,
                ref_id=turn_id,
                ref_role=attachment_create.attachment_role,
                display_order=attachment_create.display_order,
                metadata={
                    **attachment_create.metadata,
                    "conversation_id": str(conversation_id),
                },
            ),
            allow_restricted_assets=allow_restricted_assets,
        )

    def list_turn_media(
        self,
        world_id: uuid.UUID,
        conversation_id: uuid.UUID,
        turn_id: uuid.UUID,
        *,
        allow_restricted_assets: bool = True,
    ) -> list[ConversationTurnMediaAttachmentRecord]:
        worldline_id = self._turn_worldline_id(world_id, conversation_id, turn_id)
        new_refs = self._session.scalars(
            select(MediaReference)
            .where(
                MediaReference.world_id == world_id,
                MediaReference.worldline_id == worldline_id,
                MediaReference.ref_kind == MediaReferenceKind.CONVERSATION_TURN.value,
                MediaReference.ref_id == turn_id,
            )
            .order_by(MediaReference.display_order, MediaReference.created_at)
        ).all()
        records: list[ConversationTurnMediaAttachmentRecord] = []
        seen_asset_ids: set[uuid.UUID] = set()
        for ref in new_refs:
            asset = self._asset_required(world_id, ref.asset_id, include_deleted=False)
            if (
                not allow_restricted_assets
                and asset.visibility in RESTRICTED_ASSET_VISIBILITIES
            ):
                continue
            seen_asset_ids.add(asset.id)
            records.append(
                ConversationTurnMediaAttachmentRecord(
                    asset=_asset_record(asset),
                    reference=_reference_record(ref),
                    legacy_context=None,
                )
            )
        legacy_contexts = self._session.scalars(
            select(MediaAssetContext)
            .where(
                MediaAssetContext.world_id == world_id,
                MediaAssetContext.worldline_id == worldline_id,
                MediaAssetContext.conversation_id == conversation_id,
                MediaAssetContext.turn_id == turn_id,
            )
            .order_by(MediaAssetContext.created_at)
        ).all()
        for context in legacy_contexts:
            if context.asset_id in seen_asset_ids:
                continue
            asset = self._asset_required(world_id, context.asset_id, include_deleted=False)
            if (
                not allow_restricted_assets
                and asset.visibility in RESTRICTED_ASSET_VISIBILITIES
            ):
                continue
            records.append(
                ConversationTurnMediaAttachmentRecord(
                    asset=_asset_record(asset),
                    reference=None,
                    legacy_context=_context_record(context),
                )
            )
        return records

    def delete_reference(
        self,
        world_id: uuid.UUID,
        reference_id: uuid.UUID,
        *,
        allow_restricted_assets: bool = True,
    ) -> None:
        model = self._session.get(MediaReference, reference_id)
        if model is None or model.world_id != world_id:
            raise MediaNotFoundError("media reference not found")
        asset = self._asset_required(world_id, model.asset_id, include_deleted=False)
        if (
            not allow_restricted_assets
            and asset.visibility in RESTRICTED_ASSET_VISIBILITIES
        ):
            raise MediaNotFoundError("media reference not found")
        self._session.delete(model)
        self._session.flush()

    def delete_turn_media(
        self,
        world_id: uuid.UUID,
        conversation_id: uuid.UUID,
        turn_id: uuid.UUID,
        asset_id: uuid.UUID,
        *,
        allow_restricted_assets: bool = True,
    ) -> None:
        worldline_id = self._turn_worldline_id(world_id, conversation_id, turn_id)
        asset = self._asset_required(world_id, asset_id, include_deleted=False)
        if (
            not allow_restricted_assets
            and asset.visibility in RESTRICTED_ASSET_VISIBILITIES
        ):
            raise MediaNotFoundError("media reference not found")
        models = self._session.scalars(
            select(MediaReference).where(
                MediaReference.world_id == world_id,
                MediaReference.worldline_id == worldline_id,
                MediaReference.asset_id == asset_id,
                MediaReference.ref_kind == MediaReferenceKind.CONVERSATION_TURN.value,
                MediaReference.ref_id == turn_id,
            )
        ).all()
        if not models:
            raise MediaNotFoundError("media reference not found")
        for model in models:
            self._session.delete(model)
        self._session.flush()

    def validate_reference_target(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        ref_kind: MediaReferenceKind,
        ref_id: uuid.UUID,
    ) -> None:
        if ref_kind == MediaReferenceKind.CONVERSATION_TURN:
            turn = self._session.get(ConversationTurn, ref_id)
            if turn is None:
                raise MediaValidationError("turn reference target not found")
            conversation = self._session.get(ConversationSession, turn.session_id)
            if (
                conversation is None
                or conversation.world_id != world_id
                or conversation.worldline_id != worldline_id
            ):
                raise MediaValidationError("turn reference target must belong to worldline")
            return
        if ref_kind == MediaReferenceKind.CONVERSATION_SESSION:
            conversation = self._session.get(ConversationSession, ref_id)
            if (
                conversation is None
                or conversation.world_id != world_id
                or conversation.worldline_id != worldline_id
            ):
                raise MediaValidationError("conversation reference target must belong to worldline")
            return
        if ref_kind == MediaReferenceKind.WORLD_EVENT:
            event = self._session.get(WorldEventModel, ref_id)
            if event is None or event.world_id != world_id or event.worldline_id != worldline_id:
                raise MediaValidationError("event reference target must belong to worldline")
            return
        if ref_kind == MediaReferenceKind.NARRATIVE_ARTIFACT:
            artifact = self._session.get(NarrativeArtifact, ref_id)
            if artifact is None or artifact.world_id != world_id:
                raise MediaValidationError("narrative artifact reference target not found")
            artifact_worldline_id = _metadata_worldline_id(artifact.artifact_metadata)
            if artifact_worldline_id != worldline_id:
                raise MediaValidationError("narrative artifact reference target worldline unknown")
            return
        if ref_kind == MediaReferenceKind.AGENT:
            agent = self._session.get(Agent, ref_id)
            if agent is None or agent.world_id != world_id:
                raise MediaValidationError("agent reference target must belong to world")
            return
        if ref_kind == MediaReferenceKind.SCENE:
            scene = self._session.get(Scene, ref_id)
            if scene is None or scene.world_id != world_id:
                raise MediaValidationError("scene reference target must belong to world")
            return
        if ref_kind == MediaReferenceKind.WORLD:
            world = self._session.get(World, ref_id)
            if world is None or world.id != world_id:
                raise MediaValidationError("world reference target must match route world")
            return
        if ref_kind == MediaReferenceKind.MODEL_INVOCATION:
            _validate_model_invocation(
                self._session,
                world_id,
                worldline_id,
                ref_id,
                "model invocation reference target",
            )
            return
        if ref_kind == MediaReferenceKind.MEDIA_JOB:
            job = self._session.get(MediaJob, ref_id)
            if job is None or job.world_id != world_id or job.worldline_id != worldline_id:
                raise MediaValidationError("media job reference target must belong to worldline")
            return
        if ref_kind == MediaReferenceKind.MEMORY_WRITE_JOB:
            _validate_memory_write_job(self._session, world_id, worldline_id, ref_id)
            return
        if ref_kind == MediaReferenceKind.OTHER:
            return

    def _asset_required(
        self,
        world_id: uuid.UUID,
        asset_id: uuid.UUID,
        *,
        include_deleted: bool,
    ) -> MediaAsset:
        model = self._session.get(MediaAsset, asset_id)
        if model is None or model.world_id != world_id:
            raise MediaNotFoundError("media asset not found")
        if not include_deleted and model.status == MediaAssetStatus.DELETED.value:
            raise MediaNotFoundError("media asset not found")
        return model

    def _turn_worldline_id(
        self,
        world_id: uuid.UUID,
        conversation_id: uuid.UUID,
        turn_id: uuid.UUID,
    ) -> uuid.UUID:
        conversation = self._session.get(ConversationSession, conversation_id)
        turn = self._session.get(ConversationTurn, turn_id)
        if (
            conversation is None
            or turn is None
            or turn.session_id != conversation_id
            or conversation.world_id != world_id
            or conversation.worldline_id is None
        ):
            raise MediaValidationError("turn must belong to conversation worldline")
        return conversation.worldline_id


def _asset_record(model: MediaAsset) -> MediaAssetRecord:
    return MediaAssetRecord(
        id=model.id,
        world_id=model.world_id,
        worldline_id=model.worldline_id,
        asset_kind=MediaAssetKind(model.asset_kind),
        asset_role=MediaAssetRole(model.asset_role),
        source_kind=MediaSourceKind(model.source_kind),
        status=MediaAssetStatus(model.status),
        visibility=MediaVisibility(model.visibility),
        storage_uri=model.storage_uri,
        preview_uri=model.preview_uri,
        thumbnail_uri=model.thumbnail_uri,
        mime_type=model.mime_type,
        file_ext=model.file_ext,
        size_bytes=model.size_bytes,
        checksum_sha256=model.checksum_sha256,
        width=model.width,
        height=model.height,
        duration_ms=model.duration_ms,
        sample_rate_hz=model.sample_rate_hz,
        audio_channels=model.audio_channels,
        has_alpha=model.has_alpha,
        color_mode=model.color_mode,
        provider_kind=model.provider_kind,
        source_job_id=model.source_job_id,
        source_event_id=model.source_event_id,
        source_invocation_id=model.source_invocation_id,
        title=model.title,
        description=model.description,
        created_by_actor_ref=model.created_by_actor_ref,
        metadata=model.metadata_json,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _context_record(model: MediaAssetContext) -> MediaContextRecord:
    return MediaContextRecord(
        id=model.id,
        world_id=model.world_id,
        worldline_id=model.worldline_id,
        asset_id=model.asset_id,
        conversation_id=model.conversation_id,
        turn_id=model.turn_id,
        agent_id=model.agent_id,
        world_event_id=model.world_event_id,
        narrative_artifact_id=model.narrative_artifact_id,
        context_role=MediaContextRole(model.context_role),
        metadata=model.metadata_json,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _input_record(model: MediaAssetInput) -> MediaAssetInputRecord:
    return MediaAssetInputRecord(
        id=model.id,
        world_id=model.world_id,
        worldline_id=model.worldline_id,
        output_asset_id=model.output_asset_id,
        input_asset_id=model.input_asset_id,
        source_job_id=model.source_job_id,
        input_role=MediaInputRole(model.input_role),
        display_order=model.display_order,
        metadata=model.metadata_json,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _job_record(model: MediaJob) -> MediaJobRecord:
    return MediaJobRecord(
        id=model.id,
        world_id=model.world_id,
        worldline_id=model.worldline_id,
        conversation_id=model.conversation_id,
        turn_id=model.turn_id,
        agent_id=model.agent_id,
        job_kind=MediaJobKind(model.job_kind),
        provider_kind=model.provider_kind,
        priority=model.priority,
        cancel_policy=model.cancel_policy,
        deadline_hint=model.deadline_hint,
        dedupe_key=model.dedupe_key,
        invalidation_key=model.invalidation_key,
        source_event_id=model.source_event_id,
        source_invocation_id=model.source_invocation_id,
        provider_config_json=model.provider_config_json,
        request_json=model.request_json,
        status=MediaJobStatus(model.status),
        result_json=model.result_json,
        error_text=model.error_text,
        created_by_actor_ref=model.created_by_actor_ref,
        started_at=model.started_at,
        finished_at=model.finished_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _object_record(model: MediaObject) -> MediaObjectRecord:
    return MediaObjectRecord(
        id=model.id,
        asset_id=model.asset_id,
        world_id=model.world_id,
        worldline_id=model.worldline_id,
        object_role=MediaObjectRole(model.object_role),
        storage_uri=model.storage_uri,
        filename=model.filename,
        mime_type=model.mime_type,
        size_bytes=model.size_bytes,
        checksum_sha256=model.checksum_sha256,
        width=model.width,
        height=model.height,
        duration_ms=model.duration_ms,
        sample_rate_hz=model.sample_rate_hz,
        audio_channels=model.audio_channels,
        frame_rate=model.frame_rate,
        metadata=model.metadata_json,
        created_at=model.created_at,
    )


def _reference_record(model: MediaReference) -> MediaReferenceRecord:
    return MediaReferenceRecord(
        id=model.id,
        world_id=model.world_id,
        worldline_id=model.worldline_id,
        asset_id=model.asset_id,
        ref_kind=MediaReferenceKind(model.ref_kind),
        ref_id=model.ref_id,
        ref_role=MediaReferenceRole(model.ref_role),
        display_order=model.display_order,
        metadata=model.metadata_json,
        created_at=model.created_at,
    )


def _worldline_id(
    session: Session,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID | None,
) -> uuid.UUID:
    try:
        return worldline_or_404(session, world_id, worldline_id).id
    except ValueError as exc:
        raise MediaValidationError("worldline not found") from exc


def _validate_model_invocation(
    session: Session,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    invocation_id: uuid.UUID,
    label: str,
) -> None:
    table = Base.metadata.tables.get("model_invocations")
    if table is None:
        raise MediaValidationError("model invocation metadata is not registered")
    row = session.execute(
        select(table.c.world_id, table.c.worldline_id).where(table.c.id == invocation_id)
    ).one_or_none()
    if row is None or row.world_id != world_id or row.worldline_id != worldline_id:
        raise MediaValidationError(f"{label} must belong to the target worldline")


def _validate_memory_write_job(
    session: Session,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    job_id: uuid.UUID,
) -> None:
    table = Base.metadata.tables.get("memory_write_jobs")
    if table is None:
        raise MediaValidationError("memory write job metadata is not registered")
    row = session.execute(
        select(table.c.world_id, table.c.worldline_id).where(table.c.id == job_id)
    ).one_or_none()
    if row is None or row.world_id != world_id:
        raise MediaValidationError("memory write job reference target must belong to worldline")
    if row.worldline_id is None:
        primary_id = worldline_or_404(session, world_id, None).id
        if primary_id != worldline_id:
            raise MediaValidationError("memory write job reference target must belong to worldline")
        return
    if row.worldline_id != worldline_id:
        raise MediaValidationError("memory write job reference target must belong to worldline")


def _metadata_worldline_id(metadata: dict[str, object]) -> uuid.UUID | None:
    raw = metadata.get("worldline_id")
    if not isinstance(raw, str):
        return None
    try:
        return uuid.UUID(raw)
    except ValueError:
        return None


def _file_extension(filename: str | None, mime_type: str) -> str:
    if filename and "." in filename:
        suffix = filename.rsplit(".", 1)[-1].strip().lower()
        if suffix and suffix.isalnum() and len(suffix) <= 12:
            return f".{suffix}"
    guessed = mimetypes.guess_extension(mime_type)
    return "" if guessed is None else guessed
