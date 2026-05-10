from __future__ import annotations

import uuid
from datetime import UTC, datetime

from noveland.agents.models import Agent
from noveland.conversations.models import ConversationSession, ConversationTurn
from noveland.events.models import WorldEventModel
from noveland.media.contracts import (
    AUDIO_MIME_TYPES,
    IMAGE_MIME_TYPES,
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
    MediaContextCreate,
    MediaContextRecord,
    MediaContextRole,
    MediaInputRole,
    MediaJobCreate,
    MediaJobKind,
    MediaJobRecord,
    MediaJobStatus,
    MediaSourceKind,
    MediaVisibility,
)
from noveland.media.errors import MediaConflictError, MediaNotFoundError, MediaValidationError
from noveland.media.models import MediaAsset, MediaAssetContext, MediaAssetInput, MediaJob
from noveland.media.storage import MediaObjectStorage
from noveland.narrative.models import NarrativeArtifact
from noveland.worlds.worldlines import worldline_or_404
from sqlalchemy import func, select
from sqlalchemy.orm import Session

MEMBER_VISIBLE_ASSET_VISIBILITIES = {
    MediaVisibility.WORLD_MEMBER.value,
    MediaVisibility.PLAYER_VISIBLE.value,
    MediaVisibility.READER_VISIBLE.value,
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
            title=asset_create.title or asset_create.filename,
            description=asset_create.description,
            created_by_actor_ref=actor_ref,
            metadata_json=asset_create.metadata,
        )
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return _asset_record(model)

    def get_asset(
        self,
        world_id: uuid.UUID,
        asset_id: uuid.UUID,
        *,
        worldline_id: uuid.UUID | None = None,
        include_deleted: bool = False,
        member_visible_only: bool = False,
    ) -> MediaAssetRecord | None:
        resolved_worldline_id = self._worldline_id(world_id, worldline_id)
        model = self._asset_or_none(
            world_id,
            resolved_worldline_id,
            asset_id,
            include_deleted=include_deleted,
            member_visible_only=member_visible_only,
        )
        return None if model is None else _asset_record(model)

    def get_asset_by_id(
        self,
        world_id: uuid.UUID,
        asset_id: uuid.UUID,
        *,
        include_deleted: bool = False,
        member_visible_only: bool = False,
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
        if filters.status is not None:
            statement = statement.where(MediaAsset.status == filters.status.value)
        if filters.visibility is not None:
            statement = statement.where(MediaAsset.visibility == filters.visibility.value)
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
        allowed = IMAGE_MIME_TYPES if asset_kind == MediaAssetKind.IMAGE else AUDIO_MIME_TYPES
        if mime_type not in allowed:
            raise MediaValidationError("mime_type is not allowed for asset kind")

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
        *,
        worldline_id: uuid.UUID | None = None,
        status: MediaJobStatus | None = None,
        limit: int = 100,
    ) -> list[MediaJobRecord]:
        resolved_worldline_id = self._worldline_id(world_id, worldline_id)
        statement = select(MediaJob).where(
            MediaJob.world_id == world_id,
            MediaJob.worldline_id == resolved_worldline_id,
        )
        if status is not None:
            statement = statement.where(MediaJob.status == status.value)
        statement = statement.order_by(MediaJob.created_at.desc()).limit(limit)
        return [_job_record(model) for model in self._session.scalars(statement).all()]

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
