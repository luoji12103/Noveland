from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from noveland.invocations.contracts import (
    InvocationActorKind,
    InvocationRecordCreate,
    InvocationRedactionStatus,
    InvocationRetentionPolicy,
    InvocationStatus,
    InvocationStatusUpdate,
    InvocationVisibility,
    PromptSnapshotCreate,
    PromptSnapshotUpdate,
)
from noveland.invocations.models import ModelInvocation
from noveland.invocations.service import InvocationLedgerService, PromptSnapshotService
from noveland.media.contracts import (
    MediaAssetCreate,
    MediaAssetKind,
    MediaAssetRecord,
    MediaAssetStatus,
    MediaJobCreate,
    MediaJobRecord,
    MediaJobStatus,
    MediaJobUpdate,
    MediaObjectCreate,
    MediaObjectRecord,
    MediaObjectRole,
    MediaSourceKind,
    MediaVisibility,
)
from noveland.media.errors import MediaValidationError
from noveland.media.models import MediaAsset, MediaJob
from noveland.media.service import MediaJobService, MediaService
from noveland.media.storage import MediaObjectStorage
from noveland.providers.contracts import (
    ProviderAdapterKind,
    ProviderExecutionRequest,
    ProviderExecutionResult,
    ProviderIntegrationRead,
)
from noveland.providers.fake import FakeProviderAdapter
from noveland.providers.models import ProviderIntegration
from noveland.providers.registry import (
    ProviderNotFoundError,
    ProviderRegistryService,
    ProviderValidationError,
)
from noveland.providers.routing import (
    invocation_kind_for_provider,
    invocation_provider_kind_for_adapter,
    media_job_kind_for_provider,
    output_asset_shape_for_provider,
)
from noveland.worlds.worldlines import worldline_or_404
from sqlalchemy.orm import Session


class ProviderExecutionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class _ExecutionOutcome:
    output_text: str | None
    output_json: dict[str, object]
    media_job: MediaJobRecord | None = None
    output_asset: MediaAssetRecord | None = None
    output_objects: list[MediaObjectRecord] | None = None


class ProviderExecutionService:
    def __init__(
        self,
        session: Session,
        storage: MediaObjectStorage | None = None,
    ) -> None:
        self._session = session
        self._storage = storage
        self._fake = FakeProviderAdapter()

    def execute(self, request: ProviderExecutionRequest) -> ProviderExecutionResult:
        worldline_id = self._worldline_id(request.world_id, request.worldline_id)
        provider = self._resolve_provider(request)
        model = self._provider_model(provider.id)
        if model.status != "active":
            raise ProviderValidationError("provider integration is not active")
        if request.media_job_id is not None:
            self._validate_media_job(request.world_id, worldline_id, request.media_job_id)
        if request.media_asset_id is not None:
            self._validate_media_asset(request.world_id, worldline_id, request.media_asset_id)

        invocation = InvocationLedgerService(self._session).record(
            InvocationRecordCreate(
                world_id=request.world_id,
                worldline_id=worldline_id,
                invocation_kind=invocation_kind_for_provider(provider.provider_kind),
                actor_kind=InvocationActorKind.SERVICE,
                actor_ref=request.actor_ref or "service:provider-execution",
                media_job_id=request.media_job_id,
                media_asset_id=request.media_asset_id,
                provider_kind=invocation_provider_kind_for_adapter(
                    provider.provider_kind,
                    provider.adapter_kind,
                ),
                model_name=request.model_name,
                input_text=request.input_text,
                input_json=request.input_json,
                request_params_json={
                    "provider_id": str(provider.id),
                    "provider_key": provider.provider_key,
                    "provider_kind": provider.provider_kind.value,
                    "adapter_kind": provider.adapter_kind.value,
                    "request": request.request_json,
                },
                status=InvocationStatus.RUNNING,
                visibility=InvocationVisibility.WORLD_ADMIN,
                redaction_status=InvocationRedactionStatus.RAW,
                retention_policy=InvocationRetentionPolicy.LOCAL_DEBUG,
                prompt_snapshot=PromptSnapshotCreate(
                    raw_prompt_text=request.input_text,
                    raw_request_json={
                        "provider_id": str(provider.id),
                        "provider_key": provider.provider_key,
                        "provider_kind": provider.provider_kind.value,
                        "adapter_kind": provider.adapter_kind.value,
                        "input_json": request.input_json,
                        "request_json": request.request_json,
                    },
                    prompt_context_snapshot_json={"worldline_id": str(worldline_id)},
                ),
            )
        )

        try:
            result = self.execute_fake(provider, request, worldline_id)
            InvocationLedgerService(self._session).update_status(
                request.world_id,
                invocation.id,
                InvocationStatusUpdate(
                    status=InvocationStatus.SUCCEEDED,
                    output_text=result.output_text,
                    output_json=result.output_json,
                    response_metadata_json={
                        "provider_id": str(provider.id),
                        "provider_key": provider.provider_key,
                        "adapter_kind": provider.adapter_kind.value,
                    },
                    latency_ms=0,
                ),
            )
            PromptSnapshotService(self._session).update_snapshot_for_invocation(
                invocation.id,
                PromptSnapshotUpdate(
                    raw_response_json=result.output_json,
                    raw_output_text=result.output_text,
                    normalized_output_json=result.output_json,
                ),
            )
            self._attach_invocation_links(invocation.id, result)
            refreshed = InvocationLedgerService(self._session).get(
                request.world_id,
                invocation.id,
                platform_admin=True,
            )
            if refreshed is None:
                raise ProviderExecutionError("provider invocation disappeared")
            return ProviderExecutionResult(
                provider=provider,
                invocation=refreshed,
                output_text=result.output_text,
                output_json=result.output_json,
                media_job=result.media_job,
                output_asset=result.output_asset,
                output_objects=[] if result.output_objects is None else result.output_objects,
            )
        except Exception as exc:
            InvocationLedgerService(self._session).update_status(
                request.world_id,
                invocation.id,
                InvocationStatusUpdate(status=InvocationStatus.FAILED, error_text=str(exc)),
            )
            PromptSnapshotService(self._session).update_snapshot_for_invocation(
                invocation.id,
                PromptSnapshotUpdate(raw_response_json={"error": str(exc)}, raw_output_text=None),
            )
            raise

    def execute_fake(
        self,
        provider: ProviderIntegrationRead,
        request: ProviderExecutionRequest,
        worldline_id: uuid.UUID,
    ) -> _ExecutionOutcome:
        if provider.adapter_kind not in {ProviderAdapterKind.FAKE, ProviderAdapterKind.LOCAL_STUB}:
            raise ProviderExecutionError(
                f"adapter_kind={provider.adapter_kind.value} is not implemented in Phase 5"
            )
        fake = self._fake.execute(
            provider.provider_kind,
            input_text=request.input_text,
            input_json=request.input_json,
            request_json=request.request_json,
        )
        media_job: MediaJobRecord | None = None
        output_asset: MediaAssetRecord | None = None
        output_objects: list[MediaObjectRecord] = []
        if fake.media_bytes is not None:
            media_job, output_asset, output_objects = self._write_fake_media(
                provider,
                request,
                worldline_id,
                data=fake.media_bytes,
                mime_type=fake.media_mime_type or "application/octet-stream",
                filename=fake.media_filename,
            )
        return _ExecutionOutcome(
            output_text=fake.output_text,
            output_json=fake.output_json,
            media_job=media_job,
            output_asset=output_asset,
            output_objects=output_objects,
        )

    def _write_fake_media(
        self,
        provider: ProviderIntegrationRead,
        request: ProviderExecutionRequest,
        worldline_id: uuid.UUID,
        *,
        data: bytes,
        mime_type: str,
        filename: str | None,
    ) -> tuple[MediaJobRecord, MediaAssetRecord, list[MediaObjectRecord]]:
        if self._storage is None:
            raise ProviderValidationError("provider media execution requires media storage")
        job_kind = media_job_kind_for_provider(provider.provider_kind)
        if job_kind is None:
            raise ProviderValidationError("provider kind does not produce media jobs")
        job = MediaJobService(self._session).create_job(
            MediaJobCreate(
                world_id=request.world_id,
                worldline_id=worldline_id,
                job_kind=job_kind,
                provider_kind=provider.provider_kind.value,
                source_invocation_id=None,
                provider_config_json={"provider_id": str(provider.id)},
                request_json=request.request_json,
            ),
            actor_ref=request.actor_ref or "service:provider-execution",
        )
        asset_kind, asset_role = output_asset_shape_for_provider(provider.provider_kind)
        asset_id = uuid.uuid4()
        checksum = hashlib.sha256(data).hexdigest()
        ext = ".png" if asset_kind == MediaAssetKind.IMAGE else ".wav"
        key = (
            f"worlds/{request.world_id}/worldlines/{worldline_id}/assets/{asset_id}/"
            f"original-{checksum}{ext}"
        )
        stored = self._storage.write_bytes(key, data, content_type=mime_type)
        asset = MediaService(self._session, self._storage).create_asset(
            MediaAssetCreate(
                world_id=request.world_id,
                worldline_id=worldline_id,
                asset_kind=asset_kind,
                asset_role=asset_role,
                source_kind=MediaSourceKind.PROVIDER_GENERATED,
                status=MediaAssetStatus.AVAILABLE,
                visibility=MediaVisibility.WORLD_ADMIN,
                storage_uri=stored.uri,
                mime_type=mime_type,
                file_ext=ext.removeprefix("."),
                size_bytes=stored.size_bytes,
                checksum_sha256=stored.checksum_sha256,
                provider_kind=provider.provider_kind.value,
                source_job_id=job.id,
                title=filename,
                metadata={"provider_id": str(provider.id), "fake": True},
            ),
            actor_ref=request.actor_ref or "service:provider-execution",
        )
        media_object = MediaService(self._session, self._storage).add_object(
            request.world_id,
            asset.id,
            MediaObjectCreate(
                world_id=request.world_id,
                worldline_id=worldline_id,
                object_role=MediaObjectRole.ORIGINAL,
                storage_uri=stored.uri,
                filename=filename,
                mime_type=mime_type,
                size_bytes=stored.size_bytes,
                checksum_sha256=stored.checksum_sha256,
                metadata={"provider_id": str(provider.id), "fake": True},
            ),
        )
        job = MediaJobService(self._session).update_job(
            request.world_id,
            job.id,
            MediaJobUpdate(
                status=MediaJobStatus.SUCCEEDED,
                result_json={"asset_id": str(asset.id), "object_id": str(media_object.id)},
                finished_at=datetime.now(UTC),
            ),
        )
        return job, asset, [media_object]

    def _attach_invocation_links(
        self,
        invocation_id: uuid.UUID,
        result: _ExecutionOutcome,
    ) -> None:
        model = self._session.get(ModelInvocation, invocation_id)
        if model is None:
            return
        if result.media_job is not None:
            model.media_job_id = result.media_job.id
            job = self._session.get(MediaJob, result.media_job.id)
            if job is not None:
                job.source_invocation_id = invocation_id
        if result.output_asset is not None:
            model.media_asset_id = result.output_asset.id
            asset = self._session.get(MediaAsset, result.output_asset.id)
            if asset is not None:
                asset.source_invocation_id = invocation_id
        self._session.flush()

    def _resolve_provider(self, request: ProviderExecutionRequest) -> ProviderIntegrationRead:
        registry = ProviderRegistryService(self._session)
        provider_kind = request.provider_kind
        if provider_kind is None and request.provider_id is not None:
            provider = registry.get_provider(
                request.world_id,
                request.provider_id,
                platform_admin=True,
                include_hidden=True,
            )
            if provider is None:
                raise ProviderNotFoundError("provider integration not found")
            return provider
        return registry.resolve_provider_for_capability(
            request.world_id,
            provider_kind=provider_kind,
            capability_key=request.capability_key,
            provider_id=request.provider_id,
        )

    def _provider_model(self, provider_id: uuid.UUID) -> ProviderIntegration:
        return ProviderRegistryService(self._session).internal_model(provider_id)

    def _validate_media_job(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        media_job_id: uuid.UUID,
    ) -> None:
        job = self._session.get(MediaJob, media_job_id)
        if job is None or job.world_id != world_id or job.worldline_id != worldline_id:
            raise MediaValidationError("media job must belong to provider execution worldline")

    def _validate_media_asset(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        media_asset_id: uuid.UUID,
    ) -> None:
        asset = self._session.get(MediaAsset, media_asset_id)
        if asset is None or asset.world_id != world_id or asset.worldline_id != worldline_id:
            raise MediaValidationError("media asset must belong to provider execution worldline")

    def _worldline_id(self, world_id: uuid.UUID, worldline_id: uuid.UUID | None) -> uuid.UUID:
        try:
            return worldline_or_404(self._session, world_id, worldline_id).id
        except ValueError as exc:
            raise ProviderValidationError("worldline not found") from exc
