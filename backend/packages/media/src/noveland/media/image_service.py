from __future__ import annotations

import hashlib
import uuid
from collections.abc import Iterable
from datetime import UTC, datetime

from noveland.media.composer import compose_png
from noveland.media.contracts import (
    MediaAssetCreate,
    MediaAssetInputCreate,
    MediaAssetKind,
    MediaAssetRecord,
    MediaAssetStatus,
    MediaInputRole,
    MediaJobCreate,
    MediaJobKind,
    MediaJobRecord,
    MediaJobStatus,
    MediaJobUpdate,
    MediaObjectCreate,
    MediaObjectRecord,
    MediaObjectRole,
    MediaSourceKind,
    MediaVisibility,
)
from noveland.media.errors import MediaNotFoundError, MediaValidationError
from noveland.media.image_contracts import (
    ImageComposeRequest,
    ImageEditRequest,
    ImageGenerateRequest,
    ImageResult,
    TransparentBackgroundPreference,
)
from noveland.media.service import MediaJobService, MediaService
from noveland.media.storage import MediaObjectStorage
from noveland.providers.contracts import (
    ProviderCapabilityRead,
    ProviderExecutionRequest,
    ProviderKind,
)
from noveland.providers.registry import ProviderRegistryService, ProviderValidationError
from noveland.providers.service import ProviderExecutionService
from noveland.worlds.worldlines import worldline_or_404
from sqlalchemy.orm import Session


class ImageService:
    def __init__(self, session: Session, storage: MediaObjectStorage) -> None:
        self._session = session
        self._storage = storage

    def generate_image(
        self,
        world_id: uuid.UUID,
        request: ImageGenerateRequest,
        *,
        actor_ref: str,
    ) -> ImageResult:
        worldline_id = self._worldline_id(world_id, request.worldline_id)
        self._validate_provider_capability(
            world_id,
            request.provider_id,
            required_capability="supports_image_generation",
            transparent_background=request.transparent_background,
        )
        for asset_id in request.reference_asset_ids:
            self._asset_required(
                world_id,
                worldline_id,
                asset_id,
                expected_kind=MediaAssetKind.IMAGE,
            )
        job = self._provider_job(
            world_id,
            worldline_id,
            request.media_job_id,
            job_kind=MediaJobKind.IMAGE_GENERATION,
            provider_id=request.provider_id,
            request_json={
                "prompt_hash": hashlib.sha256(request.prompt.encode("utf-8")).hexdigest(),
                "size": request.size,
                "output_format": request.output_format.value,
                "reference_asset_count": len(request.reference_asset_ids),
                "transparent_background": request.transparent_background.value,
            },
            actor_ref=actor_ref,
        )
        provider_kind = _provider_kind_for_generation(world_id, request.provider_id, self._session)
        result = ProviderExecutionService(self._session, self._storage).execute(
            ProviderExecutionRequest(
                world_id=world_id,
                worldline_id=worldline_id,
                provider_id=request.provider_id,
                provider_kind=provider_kind,
                capability_key="image.generate",
                input_text=request.prompt,
                request_json={
                    "prompt": request.prompt,
                    "negative_prompt": request.negative_prompt,
                    "size": request.size,
                    "output_format": request.output_format.value,
                    "asset_role": request.asset_role.value,
                    "reference_asset_ids": [str(item) for item in request.reference_asset_ids],
                    "metadata": request.metadata,
                },
                media_job_id=job.id,
                player_actor_id=request.player_actor_id,
                actor_ref=actor_ref,
            )
        )
        if result.media_job is None or result.output_asset is None:
            raise MediaValidationError("image provider did not return media output")
        for input_asset_id in request.reference_asset_ids:
            MediaService(self._session, self._storage).add_input(
                world_id,
                result.output_asset.id,
                _input_create(
                    world_id,
                    worldline_id,
                    input_asset_id,
                    job.id,
                    MediaInputRole.REFERENCE,
                ),
            )
        return ImageResult(
            media_job=result.media_job,
            output_asset=result.output_asset,
            output_objects=result.output_objects,
            model_invocation=result.invocation,
            model_invocation_id=result.invocation.id,
        )

    def edit_image(
        self,
        world_id: uuid.UUID,
        request: ImageEditRequest,
        *,
        actor_ref: str,
    ) -> ImageResult:
        worldline_id = self._worldline_id(world_id, request.worldline_id)
        self._validate_provider_capability(
            world_id,
            request.provider_id,
            required_capability="supports_image_edit",
            transparent_background=request.transparent_background,
        )
        for asset_id in request.input_asset_ids:
            self._asset_required(
                world_id,
                worldline_id,
                asset_id,
                expected_kind=MediaAssetKind.IMAGE,
            )
        if request.mask_asset_id is not None:
            self._asset_required(
                world_id,
                worldline_id,
                request.mask_asset_id,
                expected_kind=MediaAssetKind.IMAGE,
            )
        job = self._provider_job(
            world_id,
            worldline_id,
            None,
            job_kind=MediaJobKind.IMAGE_EDIT,
            provider_id=request.provider_id,
            request_json={
                "prompt_hash": hashlib.sha256(request.prompt.encode("utf-8")).hexdigest(),
                "size": request.size,
                "input_asset_count": len(request.input_asset_ids),
                "has_mask": request.mask_asset_id is not None,
            },
            actor_ref=actor_ref,
        )
        provider_kind = _provider_kind_for_edit(world_id, request.provider_id, self._session)
        result = ProviderExecutionService(self._session, self._storage).execute(
            ProviderExecutionRequest(
                world_id=world_id,
                worldline_id=worldline_id,
                provider_id=request.provider_id,
                provider_kind=provider_kind,
                capability_key="image.edit",
                input_text=request.prompt,
                request_json={
                    "prompt": request.prompt,
                    "size": request.size,
                    "output_format": request.output_format.value,
                    "output_asset_role": request.output_role.value,
                    "input_asset_ids": [str(item) for item in request.input_asset_ids],
                    "mask_asset_id": (
                        None if request.mask_asset_id is None else str(request.mask_asset_id)
                    ),
                    "metadata": request.metadata,
                },
                media_job_id=job.id,
                player_actor_id=request.player_actor_id,
                actor_ref=actor_ref,
            )
        )
        if result.media_job is None or result.output_asset is None:
            raise MediaValidationError("image provider did not return media output")
        for input_asset_id in request.input_asset_ids:
            MediaService(self._session, self._storage).add_input(
                world_id,
                result.output_asset.id,
                _input_create(
                    world_id,
                    worldline_id,
                    input_asset_id,
                    job.id,
                    MediaInputRole.SOURCE,
                ),
            )
        if request.mask_asset_id is not None:
            MediaService(self._session, self._storage).add_input(
                world_id,
                result.output_asset.id,
                _input_create(
                    world_id,
                    worldline_id,
                    request.mask_asset_id,
                    job.id,
                    MediaInputRole.MASK,
                ),
            )
        return ImageResult(
            media_job=result.media_job,
            output_asset=result.output_asset,
            output_objects=result.output_objects,
            model_invocation=result.invocation,
            model_invocation_id=result.invocation.id,
        )

    def compose_image(
        self,
        world_id: uuid.UUID,
        request: ImageComposeRequest,
        *,
        actor_ref: str,
    ) -> ImageResult:
        worldline_id = self._worldline_id(world_id, request.worldline_id)
        background = self._asset_required(
            world_id,
            worldline_id,
            request.background_asset_id,
            expected_kind=MediaAssetKind.IMAGE,
        )
        background_object, background_bytes = self._read_primary_object(world_id, background.id)
        layer_data: list[tuple[bytes, int, int, int | None, int | None, float]] = []
        for layer in sorted(request.layers, key=lambda item: item.z_index):
            asset = self._asset_required(
                world_id,
                worldline_id,
                layer.asset_id,
                expected_kind=MediaAssetKind.IMAGE,
            )
            _object, data = self._read_primary_object(world_id, asset.id)
            layer_data.append((data, layer.x, layer.y, layer.width, layer.height, layer.opacity))
        output, width, height, has_alpha = compose_png(background_bytes, layer_data)
        checksum = hashlib.sha256(output).hexdigest()
        output_asset_id = uuid.uuid4()
        key = (
            f"worlds/{world_id}/worldlines/{worldline_id}/assets/{output_asset_id}/"
            f"composed-{checksum}.png"
        )
        stored = self._storage.write_bytes(key, output, content_type="image/png")
        job = MediaJobService(self._session).create_job(
            MediaJobCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                job_kind=MediaJobKind.COMPOSITION,
                provider_kind="local_composer",
                request_json={
                    "background_asset_id": str(request.background_asset_id),
                    "layer_count": len(request.layers),
                },
            ),
            actor_ref=actor_ref,
        )
        asset = MediaService(self._session, self._storage).create_asset(
            MediaAssetCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                asset_kind=MediaAssetKind.IMAGE,
                asset_role=request.output_asset_role,
                source_kind=MediaSourceKind.COMPOSED,
                status=MediaAssetStatus.AVAILABLE,
                visibility=MediaVisibility.WORLD_ADMIN,
                storage_uri=stored.uri,
                mime_type="image/png",
                file_ext="png",
                size_bytes=stored.size_bytes,
                checksum_sha256=stored.checksum_sha256,
                width=width,
                height=height,
                has_alpha=has_alpha,
                source_job_id=job.id,
                title="Composite image",
                metadata=request.metadata,
            ),
            actor_ref=actor_ref,
        )
        media_object = MediaService(self._session, self._storage).add_object(
            world_id,
            asset.id,
            MediaObjectCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                object_role=MediaObjectRole.COMPOSED,
                storage_uri=stored.uri,
                filename="composite.png",
                mime_type="image/png",
                size_bytes=stored.size_bytes,
                checksum_sha256=stored.checksum_sha256,
                width=width,
                height=height,
                metadata={"background_object_id": str(background_object.id)},
            ),
        )
        media_service = MediaService(self._session, self._storage)
        media_service.add_input(
            world_id,
            asset.id,
            _input_create(world_id, worldline_id, background.id, job.id, MediaInputRole.BACKGROUND),
        )
        for layer in request.layers:
            media_service.add_input(
                world_id,
                asset.id,
                _input_create(world_id, worldline_id, layer.asset_id, job.id, MediaInputRole.LAYER),
            )
        job = MediaJobService(self._session).update_job(
            world_id,
            job.id,
            MediaJobUpdate(
                status=MediaJobStatus.SUCCEEDED,
                result_json={"asset_id": str(asset.id), "object_id": str(media_object.id)},
                finished_at=datetime.now(UTC),
            ),
        )
        return ImageResult(
            media_job=job,
            output_asset=asset,
            output_objects=[media_object],
            model_invocation=None,
            model_invocation_id=None,
        )

    def get_job(self, world_id: uuid.UUID, job_id: uuid.UUID) -> MediaJobRecord | None:
        return MediaJobService(self._session).get_job(world_id, job_id)

    def _validate_provider_capability(
        self,
        world_id: uuid.UUID,
        provider_id: uuid.UUID,
        *,
        required_capability: str,
        transparent_background: TransparentBackgroundPreference,
    ) -> None:
        registry = ProviderRegistryService(self._session)
        provider = registry.get_provider(
            world_id,
            provider_id,
            platform_admin=True,
            include_hidden=True,
        )
        if provider is None:
            raise ProviderValidationError("provider integration not found")
        capabilities = registry.list_capabilities(world_id, provider_id, platform_admin=True)
        if not _capability_true(capabilities, required_capability):
            raise MediaValidationError(f"provider does not support {required_capability}")
        if (
            transparent_background == TransparentBackgroundPreference.REQUIRE
            and not _capability_true(capabilities, "supports_transparent_background")
        ):
            raise MediaValidationError("provider does not support transparent background")

    def _provider_job(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        media_job_id: uuid.UUID | None,
        *,
        job_kind: MediaJobKind,
        provider_id: uuid.UUID,
        request_json: dict[str, object],
        actor_ref: str,
    ) -> MediaJobRecord:
        service = MediaJobService(self._session)
        if media_job_id is not None:
            job = service.get_job(world_id, media_job_id, worldline_id=worldline_id)
            if job is None:
                raise MediaValidationError("media job must belong to image request worldline")
            return job
        return service.create_job(
            MediaJobCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                job_kind=job_kind,
                provider_kind="image_provider",
                provider_config_json={"provider_id": str(provider_id)},
                request_json=request_json,
            ),
            actor_ref=actor_ref,
        )

    def _asset_required(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        asset_id: uuid.UUID,
        *,
        expected_kind: MediaAssetKind,
    ) -> MediaAssetRecord:
        asset = MediaService(self._session, self._storage).get_asset_by_id(
            world_id,
            asset_id,
            include_deleted=False,
        )
        if asset is None or asset.worldline_id != worldline_id or asset.asset_kind != expected_kind:
            raise MediaValidationError("image asset must belong to request worldline")
        return asset

    def _read_primary_object(
        self,
        world_id: uuid.UUID,
        asset_id: uuid.UUID,
    ) -> tuple[MediaObjectRecord, bytes]:
        objects = MediaService(self._session, self._storage).list_objects(world_id, asset_id)
        if not objects:
            raise MediaNotFoundError("image asset has no media objects")
        preferred = sorted(
            objects,
            key=lambda item: (
                item.object_role not in _PRIMARY_OBJECT_ROLES,
                item.created_at,
            ),
        )[0]
        return MediaService(self._session, self._storage).read_object_bytes(world_id, preferred.id)

    def _worldline_id(self, world_id: uuid.UUID, worldline_id: uuid.UUID | None) -> uuid.UUID:
        try:
            return worldline_or_404(self._session, world_id, worldline_id).id
        except ValueError as exc:
            raise MediaValidationError("worldline not found") from exc


def _input_create(
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    input_asset_id: uuid.UUID,
    source_job_id: uuid.UUID,
    input_role: MediaInputRole,
) -> MediaAssetInputCreate:
    return MediaAssetInputCreate(
        world_id=world_id,
        worldline_id=worldline_id,
        input_asset_id=input_asset_id,
        source_job_id=source_job_id,
        input_role=input_role,
    )


def _capability_true(capabilities: Iterable[ProviderCapabilityRead], key: str) -> bool:
    for capability in capabilities:
        if capability.capability_key != key:
            continue
        value = capability.capability_json.get("value", True)
        return bool(value)
    return False


_PRIMARY_OBJECT_ROLES = {
    MediaObjectRole.PRIMARY,
    MediaObjectRole.ORIGINAL,
    MediaObjectRole.COMPOSED,
}


def _provider_kind_for_generation(
    world_id: uuid.UUID,
    provider_id: uuid.UUID,
    session: Session,
) -> ProviderKind:
    provider = ProviderRegistryService(session).get_provider(
        world_id,
        provider_id,
        platform_admin=True,
        include_hidden=True,
    )
    if provider is None:
        raise ProviderValidationError("provider integration not found")
    return provider.provider_kind


def _provider_kind_for_edit(
    world_id: uuid.UUID,
    provider_id: uuid.UUID,
    session: Session,
) -> ProviderKind:
    provider = ProviderRegistryService(session).get_provider(
        world_id,
        provider_id,
        platform_admin=True,
        include_hidden=True,
    )
    if provider is None:
        raise ProviderValidationError("provider integration not found")
    return provider.provider_kind
