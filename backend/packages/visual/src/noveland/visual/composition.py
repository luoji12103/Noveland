from __future__ import annotations

import uuid

from noveland.media.image_contracts import ImageComposeRequest, ImageLayer
from noveland.media.image_service import ImageService
from noveland.media.storage import MediaObjectStorage
from noveland.visual.contracts import (
    SceneComposeRequest,
    SceneComposeResult,
    visual_asset_ref,
    visual_object_ref,
)
from sqlalchemy.orm import Session


class VisualCompositionService:
    def __init__(self, session: Session, storage: MediaObjectStorage) -> None:
        self._session = session
        self._storage = storage

    def compose_scene(
        self,
        world_id: uuid.UUID,
        request: SceneComposeRequest,
        *,
        actor_ref: str,
    ) -> SceneComposeResult:
        result = ImageService(self._session, self._storage).compose_image(
            world_id,
            ImageComposeRequest(
                worldline_id=request.worldline_id,
                background_asset_id=request.background_asset_id,
                layers=tuple(
                    ImageLayer(
                        asset_id=layer.asset_id,
                        x=layer.x,
                        y=layer.y,
                        width=layer.width,
                        height=layer.height,
                        opacity=layer.opacity,
                        z_index=layer.z_index,
                        blend_mode=layer.blend_mode,
                    )
                    for layer in request.layers
                ),
                metadata={
                    **request.metadata_json,
                    "source": "visual_compose_scene",
                },
            ),
            actor_ref=actor_ref,
        )
        return SceneComposeResult(
            media_job=result.media_job,
            output_asset=visual_asset_ref(result.output_asset),
            output_objects=[visual_object_ref(item) for item in result.output_objects],
        )
