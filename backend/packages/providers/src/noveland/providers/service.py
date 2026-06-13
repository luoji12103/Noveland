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
    MediaAssetRole,
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
from noveland.providers.adapters.anthropic_text import AnthropicCompatibleTextAdapter
from noveland.providers.adapters.comfyui import ComfyUIAdapter
from noveland.providers.adapters.gpt_sovits import GPTSoVITSAdapter
from noveland.providers.adapters.mimo_asr import MiMOASRAdapter
from noveland.providers.adapters.mimo_tts import MiMOTTSAdapter
from noveland.providers.adapters.omnivoice import OmniVoiceAdapter
from noveland.providers.adapters.openai_compatible_image import OpenAICompatibleImageAdapter
from noveland.providers.adapters.openai_image import ImageAdapterInput, OpenAIImageAdapter
from noveland.providers.adapters.openai_speech import OpenAISpeechAdapter
from noveland.providers.adapters.openai_text import OpenAICompatibleTextAdapter
from noveland.providers.adapters.speech_common import SpeechAdapterInput
from noveland.providers.budget import ProviderBudgetExceededError, ProviderBudgetService
from noveland.providers.contracts import (
    ProviderAdapterKind,
    ProviderExecutionRequest,
    ProviderExecutionResult,
    ProviderFallbackPlanRequest,
    ProviderIntegrationRead,
    ProviderIntegrationStatus,
    ProviderKind,
)
from noveland.providers.fake import FakeProviderAdapter
from noveland.providers.models import ProviderIntegration
from noveland.providers.registry import (
    ProviderNotFoundError,
    ProviderRegistryService,
    ProviderValidationError,
)
from noveland.providers.reliability import (
    ProviderReliabilityError,
    ProviderReliabilityService,
)
from noveland.providers.routing import (
    capability_key_for_provider,
    invocation_kind_for_provider,
    invocation_provider_kind_for_adapter,
    media_job_kind_for_provider,
    output_asset_shape_for_provider,
)
from noveland.providers.secrets import (
    ProviderSecretMissingError,
    ProviderSecretResolver,
    adapter_requires_auth,
    failed_auth_metadata,
    reject_sensitive_config,
    safe_auth_metadata,
    sanitize_for_persistence,
    sanitize_provider_diagnostic_text,
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
        secret_resolver: ProviderSecretResolver | None = None,
    ) -> None:
        self._session = session
        self._storage = storage
        self._secret_resolver = secret_resolver or ProviderSecretResolver()
        self._fake = FakeProviderAdapter()
        self._openai_image = OpenAIImageAdapter()
        self._openai_compatible_image = OpenAICompatibleImageAdapter()
        self._openai_text = OpenAICompatibleTextAdapter()
        self._anthropic_text = AnthropicCompatibleTextAdapter()
        self._comfyui = ComfyUIAdapter()
        self._openai_speech = OpenAISpeechAdapter()
        self._mimo_tts = MiMOTTSAdapter()
        self._mimo_asr = MiMOASRAdapter()
        self._omnivoice = OmniVoiceAdapter()
        self._gpt_sovits = GPTSoVITSAdapter()

    def execute(self, request: ProviderExecutionRequest) -> ProviderExecutionResult:
        worldline_id = self._worldline_id(request.world_id, request.worldline_id)
        provider = self._resolve_provider(request)
        reliability_metadata: dict[str, object] = {
            "provider_reliability_checked": False,
            "fallback_selected": False,
        }
        if request.fallback_provider_id is not None:
            provider, reliability_metadata = self._resolve_fallback_provider(
                request,
                provider,
            )
        model = self._provider_model(provider.id)
        if request.media_job_id is not None:
            self._validate_media_job(request.world_id, worldline_id, request.media_job_id)
        if request.media_asset_id is not None:
            self._validate_media_asset(request.world_id, worldline_id, request.media_asset_id)
        reject_sensitive_config(request.input_json, field_name="input_json")
        reject_sensitive_config(request.request_json, field_name="request_json")
        capability_key = request.capability_key or capability_key_for_provider(
            provider.provider_kind
        )

        inactive_reason = (
            None
            if model.status == ProviderIntegrationStatus.ACTIVE.value
            else _provider_not_active_reason(model.status)
        )
        budget_block_reason: str | None = None
        budget_metadata: dict[str, object] = {"budget_checked": False, "budget_blocked": False}
        if inactive_reason is None:
            try:
                quota = ProviderBudgetService(self._session).check_provider_execution(
                    request.world_id,
                    provider.id,
                    player_actor_id=request.player_actor_id,
                    capability_key=capability_key,
                ).quota_status
                budget_metadata = {
                    "budget_checked": True,
                    "budget_blocked": False,
                    "quota_policy_count": len(quota.active_policy_ids),
                }
            except ProviderBudgetExceededError as exc:
                budget_block_reason = _safe_error_text(exc)
                budget_metadata = {
                    "budget_checked": True,
                    "budget_blocked": True,
                    "budget_block_reason": budget_block_reason,
                }
        auth_metadata: dict[str, bool]
        resolved_secret: object | None = None
        if inactive_reason is not None or budget_block_reason is not None:
            auth_metadata = safe_auth_metadata(model.auth_ref, None)
        else:
            requires_auth = adapter_requires_auth(provider.adapter_kind, model.config_json)
            if not requires_auth:
                try:
                    resolved_secret = self._secret_resolver.resolve_auth_ref(model.auth_ref)
                except ProviderSecretMissingError:
                    resolved_secret = None
                auth_metadata = safe_auth_metadata(model.auth_ref, resolved_secret)
            else:
                try:
                    resolved_secret = self._secret_resolver.resolve_auth_ref(model.auth_ref)
                    auth_metadata = safe_auth_metadata(model.auth_ref, resolved_secret)
                except ProviderSecretMissingError:
                    resolved_secret = None
                    auth_metadata = failed_auth_metadata(model.auth_ref)

        safe_request_metadata = {
            "provider_id": str(provider.id),
            "provider_key": provider.provider_key,
            "provider_kind": provider.provider_kind.value,
            "adapter_kind": provider.adapter_kind.value,
            "capability_key": capability_key,
            **(
                {}
                if request.player_actor_id is None
                else {"player_actor_id": str(request.player_actor_id)}
            ),
            "provider_status": model.status,
            **budget_metadata,
            **auth_metadata,
            **reliability_metadata,
        }

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
                    **safe_request_metadata,
                    "request": sanitize_for_persistence(request.request_json),
                },
                status=InvocationStatus.RUNNING,
                visibility=InvocationVisibility.WORLD_ADMIN,
                redaction_status=InvocationRedactionStatus.RAW,
                retention_policy=InvocationRetentionPolicy.LOCAL_DEBUG,
                prompt_snapshot=PromptSnapshotCreate(
                    raw_prompt_text=request.input_text,
                    raw_request_json={
                        **safe_request_metadata,
                        "input_json": sanitize_for_persistence(request.input_json),
                        "request_json": sanitize_for_persistence(request.request_json),
                    },
                    prompt_context_snapshot_json={"worldline_id": str(worldline_id)},
                ),
            )
        )

        try:
            if inactive_reason is not None:
                raise ProviderExecutionError(inactive_reason)
            if budget_block_reason is not None:
                raise ProviderExecutionError(budget_block_reason)
            if auth_metadata["auth_failed"]:
                raise ProviderExecutionError("provider auth_missing")
            result = self._execute_provider(provider, model, request, worldline_id, resolved_secret)
            InvocationLedgerService(self._session).update_status(
                request.world_id,
                invocation.id,
                InvocationStatusUpdate(
                    status=InvocationStatus.SUCCEEDED,
                    output_text=result.output_text,
                    output_json=result.output_json,
                    response_metadata_json=safe_request_metadata,
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
            self._attach_invocation_links(invocation.id, result, request=request)
            refreshed = InvocationLedgerService(self._session).get(
                request.world_id,
                invocation.id,
                platform_admin=request.platform_admin,
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
            failed_metadata = {
                **safe_request_metadata,
                **(
                    failed_auth_metadata(model.auth_ref)
                    if auth_metadata["auth_failed"]
                    else auth_metadata
                ),
            }
            InvocationLedgerService(self._session).update_status(
                request.world_id,
                invocation.id,
                InvocationStatusUpdate(
                    status=InvocationStatus.FAILED,
                    error_text=_safe_error_text(exc),
                    response_metadata_json=failed_metadata,
                ),
            )
            PromptSnapshotService(self._session).update_snapshot_for_invocation(
                invocation.id,
                PromptSnapshotUpdate(
                    raw_response_json={"error": _safe_error_text(exc)},
                    raw_output_text=None,
                ),
            )
            self._mark_media_job_failed(request, exc)
            raise

    def _mark_media_job_failed(
        self,
        request: ProviderExecutionRequest,
        exc: Exception,
    ) -> None:
        if request.media_job_id is None:
            return
        job = self._session.get(MediaJob, request.media_job_id)
        if job is None or job.status in {
            MediaJobStatus.SUCCEEDED.value,
            MediaJobStatus.FAILED.value,
            MediaJobStatus.CANCELLED.value,
        }:
            return
        MediaJobService(self._session).update_job(
            request.world_id,
            request.media_job_id,
            MediaJobUpdate(
                status=MediaJobStatus.FAILED,
                error_text=_safe_error_text(exc),
                finished_at=datetime.now(UTC),
            ),
        )

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
            media_job, output_asset, output_objects = self._write_provider_media(
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

    def _execute_provider(
        self,
        provider: ProviderIntegrationRead,
        model: ProviderIntegration,
        request: ProviderExecutionRequest,
        worldline_id: uuid.UUID,
        resolved_secret: object | None,
    ) -> _ExecutionOutcome:
        if provider.adapter_kind in {ProviderAdapterKind.FAKE, ProviderAdapterKind.LOCAL_STUB}:
            return self.execute_fake(provider, request, worldline_id)
        if _adapter_is_implemented(provider.adapter_kind):
            adapter = self._adapter_for(provider.adapter_kind, provider.provider_kind)
            adapter_result = adapter.execute(
                base_url=model.base_url,
                auth_ref=_resolved_secret_value(resolved_secret),
                config_json=model.config_json,
                default_params_json=model.default_params_json,
                input_text=request.input_text,
                input_json=request.input_json,
                request_json=request.request_json,
                media_inputs=self._adapter_inputs_for_request(request),
            )
            media_job: MediaJobRecord | None = None
            output_asset: MediaAssetRecord | None = None
            output_objects: list[MediaObjectRecord] = []
            if adapter_result.media_bytes is not None:
                media_job, output_asset, output_objects = self._write_provider_media(
                    provider,
                    request,
                    worldline_id,
                    data=adapter_result.media_bytes,
                    mime_type=adapter_result.media_mime_type or "application/octet-stream",
                    filename=adapter_result.media_filename,
                )
            return _ExecutionOutcome(
                output_text=adapter_result.output_text,
                output_json=adapter_result.output_json,
                media_job=media_job,
                output_asset=output_asset,
                output_objects=output_objects,
            )
        raise ProviderExecutionError(
            f"adapter_kind={provider.adapter_kind.value} is not implemented"
        )

    def _adapter_for(
        self,
        adapter_kind: ProviderAdapterKind,
        provider_kind: object,
    ) -> (
        OpenAIImageAdapter
        | OpenAICompatibleImageAdapter
        | OpenAICompatibleTextAdapter
        | AnthropicCompatibleTextAdapter
        | ComfyUIAdapter
        | OpenAISpeechAdapter
        | MiMOTTSAdapter
        | MiMOASRAdapter
        | OmniVoiceAdapter
        | GPTSoVITSAdapter
    ):
        if adapter_kind == ProviderAdapterKind.OPENAI:
            if provider_kind in {ProviderKind.SPEECH_TO_TEXT, ProviderKind.TEXT_TO_SPEECH}:
                return self._openai_speech
            if provider_kind == ProviderKind.TEXT_GENERATION:
                return self._openai_text
            return self._openai_image
        if adapter_kind == ProviderAdapterKind.OPENAI_COMPATIBLE:
            if provider_kind == ProviderKind.TEXT_GENERATION:
                return self._openai_text
            return self._openai_compatible_image
        if adapter_kind in {
            ProviderAdapterKind.ANTHROPIC,
            ProviderAdapterKind.ANTHROPIC_COMPATIBLE,
        }:
            return self._anthropic_text
        if adapter_kind == ProviderAdapterKind.COMFYUI:
            return self._comfyui
        if adapter_kind == ProviderAdapterKind.MIMO_TTS:
            return self._mimo_tts
        if adapter_kind == ProviderAdapterKind.MIMO_ASR:
            return self._mimo_asr
        if adapter_kind == ProviderAdapterKind.OMNIVOICE:
            return self._omnivoice
        if adapter_kind == ProviderAdapterKind.GPT_SOVITS:
            return self._gpt_sovits
        raise ProviderExecutionError(f"adapter_kind={adapter_kind.value} is not implemented")

    def _write_provider_media(
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
        job_service = MediaJobService(self._session)
        if request.media_job_id is None:
            job = job_service.create_job(
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
        else:
            existing_job = job_service.get_job(
                request.world_id,
                request.media_job_id,
                worldline_id=worldline_id,
            )
            if existing_job is None:
                raise ProviderValidationError(
                    "media job must belong to provider execution worldline"
                )
            job = job_service.update_job(
                request.world_id,
                request.media_job_id,
                MediaJobUpdate(
                    status=MediaJobStatus.RUNNING,
                    started_at=datetime.now(UTC),
                    provider_kind=provider.provider_kind.value,
                    provider_config_json={"provider_id": str(provider.id)},
                ),
            )
        asset_kind, default_asset_role = output_asset_shape_for_provider(provider.provider_kind)
        asset_role = _output_asset_role(request, default_asset_role)
        asset_id = uuid.uuid4()
        checksum = hashlib.sha256(data).hexdigest()
        ext = _extension_for_mime(asset_kind, mime_type)
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
                metadata={
                    "provider_id": str(provider.id),
                    "adapter_kind": provider.adapter_kind.value,
                    "request_metadata": request.request_json.get("metadata", {}),
                },
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
                metadata={
                    "provider_id": str(provider.id),
                    "adapter_kind": provider.adapter_kind.value,
                },
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
        *,
        request: ProviderExecutionRequest,
    ) -> None:
        model = self._session.get(ModelInvocation, invocation_id)
        if model is None:
            return
        if result.media_job is not None:
            model.media_job_id = result.media_job.id
            job = self._session.get(MediaJob, result.media_job.id)
            if job is not None:
                job.source_invocation_id = invocation_id
        elif request.media_job_id is not None:
            job = self._session.get(MediaJob, request.media_job_id)
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
                platform_admin=request.platform_admin,
                include_hidden=request.platform_admin,
            )
            if provider is None:
                raise ProviderNotFoundError("provider integration not found")
            return provider
        return registry.resolve_provider_for_capability(
            request.world_id,
            provider_kind=provider_kind,
            capability_key=request.capability_key,
            provider_id=request.provider_id,
            platform_admin=request.platform_admin,
            include_hidden=request.platform_admin,
        )

    def _resolve_fallback_provider(
        self,
        request: ProviderExecutionRequest,
        primary_provider: ProviderIntegrationRead,
    ) -> tuple[ProviderIntegrationRead, dict[str, object]]:
        try:
            fallback_model, audit_metadata = ProviderReliabilityService(
                self._session,
                self._secret_resolver,
            ).require_fallback_provider(
                request.world_id,
                primary_provider.id,
                ProviderFallbackPlanRequest(
                    fallback_provider_id=request.fallback_provider_id
                    or primary_provider.id,
                    worldline_id=request.worldline_id,
                    capability_key=request.capability_key
                    or capability_key_for_provider(primary_provider.provider_kind),
                    player_actor_id=request.player_actor_id,
                    fallback_mode=request.fallback_mode,
                    reason=request.fallback_reason,
                ),
                platform_admin=True,
            )
        except ProviderReliabilityError as exc:
            raise ProviderExecutionError(str(exc)) from exc
        fallback = ProviderRegistryService(self._session).get_provider(
            request.world_id,
            fallback_model.id,
            platform_admin=request.platform_admin,
            include_hidden=request.platform_admin,
        )
        if fallback is None:
            raise ProviderExecutionError("provider fallback disappeared")
        return fallback, {
            "provider_reliability_checked": True,
            **audit_metadata,
        }

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

    def _adapter_inputs_for_request(
        self,
        request: ProviderExecutionRequest,
    ) -> list[ImageAdapterInput] | list[SpeechAdapterInput]:
        if self._storage is None:
            return []
        raw_ids = request.request_json.get("input_asset_ids")
        asset_ids = [str(item) for item in raw_ids] if isinstance(raw_ids, list) else []
        inputs: list[ImageAdapterInput | SpeechAdapterInput] = []
        for raw_asset_id in asset_ids:
            asset_id = uuid.UUID(raw_asset_id)
            inputs.append(
                self._media_input_for_asset(request, asset_id, field_name="image")
            )
        raw_mask_id = request.request_json.get("mask_asset_id")
        if isinstance(raw_mask_id, str):
            inputs.append(
                self._media_input_for_asset(
                    request,
                    uuid.UUID(raw_mask_id),
                    field_name="mask",
                )
            )
        if request.request_json.get("operation") == "stt":
            return [
                SpeechAdapterInput(
                    filename=item.filename,
                    data=item.data,
                    mime_type=item.mime_type,
                    field_name="file",
                )
                for item in inputs
            ]
        return [
            ImageAdapterInput(
                filename=item.filename,
                data=item.data,
                mime_type=item.mime_type,
                field_name=item.field_name,
            )
            for item in inputs
        ]

    def _media_input_for_asset(
        self,
        request: ProviderExecutionRequest,
        asset_id: uuid.UUID,
        *,
        field_name: str,
    ) -> ImageAdapterInput:
        world_id = request.world_id
        media = MediaService(self._session, self._storage)
        requested_worldline_id = self._worldline_id(world_id, request.worldline_id)
        asset = media.get_asset_by_id(world_id, asset_id, include_deleted=False)
        if asset is None or asset.worldline_id != requested_worldline_id:
            raise MediaValidationError("media input asset must belong to provider worldline")
        objects = media.list_objects(world_id, asset_id)
        if not objects:
            raise MediaValidationError("media input asset has no object")
        selected = objects[0]
        record, data = media.read_object_bytes(world_id, selected.id)
        return ImageAdapterInput(
            filename=record.filename or f"{field_name}.png",
            data=data,
            mime_type=record.mime_type,
            field_name=field_name,
        )

    def _worldline_id(self, world_id: uuid.UUID, worldline_id: uuid.UUID | None) -> uuid.UUID:
        try:
            return worldline_or_404(self._session, world_id, worldline_id).id
        except ValueError as exc:
            raise ProviderValidationError("worldline not found") from exc


def _output_asset_role(
    request: ProviderExecutionRequest,
    default_asset_role: MediaAssetRole,
) -> MediaAssetRole:
    raw_role = request.request_json.get("output_asset_role") or request.request_json.get(
        "asset_role"
    )
    if not isinstance(raw_role, str):
        return default_asset_role
    try:
        return MediaAssetRole(raw_role)
    except ValueError:
        return default_asset_role


def _extension_for_mime(asset_kind: MediaAssetKind, mime_type: str) -> str:
    if asset_kind == MediaAssetKind.AUDIO:
        if mime_type == "audio/aac":
            return ".aac"
        if mime_type == "audio/flac":
            return ".flac"
        if mime_type == "audio/mpeg":
            return ".mp3"
        if mime_type == "audio/ogg":
            return ".ogg"
        if mime_type == "audio/pcm":
            return ".pcm"
        if mime_type == "audio/webm":
            return ".webm"
        return ".wav"
    if mime_type == "image/jpeg":
        return ".jpg"
    if mime_type == "image/webp":
        return ".webp"
    return ".png"


def _adapter_is_implemented(adapter_kind: ProviderAdapterKind) -> bool:
    return adapter_kind in {
        ProviderAdapterKind.OPENAI,
        ProviderAdapterKind.OPENAI_COMPATIBLE,
        ProviderAdapterKind.ANTHROPIC,
        ProviderAdapterKind.ANTHROPIC_COMPATIBLE,
        ProviderAdapterKind.COMFYUI,
        ProviderAdapterKind.MIMO_TTS,
        ProviderAdapterKind.MIMO_ASR,
        ProviderAdapterKind.OMNIVOICE,
        ProviderAdapterKind.GPT_SOVITS,
    }


def _resolved_secret_value(resolved_secret: object | None) -> str | None:
    value = getattr(resolved_secret, "value", None)
    return value if isinstance(value, str) else None


def _provider_not_active_reason(status: str) -> str:
    if status == ProviderIntegrationStatus.DISABLED.value:
        return "provider integration is disabled"
    if status == ProviderIntegrationStatus.DELETED.value:
        return "provider integration is deleted"
    return "provider integration is not active"


def _safe_error_text(exc: Exception) -> str:
    return sanitize_provider_diagnostic_text(str(exc))
