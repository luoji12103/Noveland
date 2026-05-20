from fastapi import FastAPI
from noveland.core.version import PROJECT_VERSION
from noveland.services.api.asset_generation import media_jobs_router as asset_generation_jobs_router
from noveland.services.api.asset_generation import router as asset_generation_router
from noveland.services.api.auth import router as auth_router
from noveland.services.api.authoring import router as authoring_router
from noveland.services.api.conversation_presentations import (
    router as conversation_presentations_router,
)
from noveland.services.api.conversations import router as conversations_router
from noveland.services.api.images import router as images_router
from noveland.services.api.invocations import router as invocations_router
from noveland.services.api.media import router as media_router
from noveland.services.api.media import turn_media_router
from noveland.services.api.moderation import router as moderation_router
from noveland.services.api.multimodal_evals import router as multimodal_evals_router
from noveland.services.api.narrative_quality import router as narrative_quality_router
from noveland.services.api.observability import router as observability_router
from noveland.services.api.package_contracts import router as package_contracts_router
from noveland.services.api.player_privacy import router as player_privacy_router
from noveland.services.api.player_sessions import router as player_sessions_router
from noveland.services.api.private_beta import router as private_beta_router
from noveland.services.api.providers import router as providers_router
from noveland.services.api.reader_media import router as reader_media_router
from noveland.services.api.realtime import router as realtime_router
from noveland.services.api.runtime import router as runtime_router
from noveland.services.api.speech import agent_voice_router
from noveland.services.api.speech import router as speech_router
from noveland.services.api.visual import router as visual_router
from noveland.services.api.visual_generation import router as visual_generation_router
from noveland.services.api.world_packaging import router as world_packaging_router
from noveland.services.api.worlds import root_router as worlds_root_router
from noveland.services.api.worlds import router as worlds_router
from pydantic import BaseModel


class HealthResponse(BaseModel):
    service: str
    status: str
    version: str


def create_app() -> FastAPI:
    api = FastAPI(title="Noveland API", version=PROJECT_VERSION)
    api.include_router(auth_router)
    api.include_router(runtime_router)
    api.include_router(worlds_root_router)
    api.include_router(worlds_router)
    api.include_router(media_router)
    api.include_router(turn_media_router)
    api.include_router(images_router)
    api.include_router(speech_router)
    api.include_router(agent_voice_router)
    api.include_router(visual_router)
    api.include_router(visual_generation_router)
    api.include_router(asset_generation_router)
    api.include_router(asset_generation_jobs_router)
    api.include_router(authoring_router)
    api.include_router(multimodal_evals_router)
    api.include_router(narrative_quality_router)
    api.include_router(invocations_router)
    api.include_router(providers_router)
    api.include_router(reader_media_router)
    api.include_router(moderation_router)
    api.include_router(player_privacy_router)
    api.include_router(player_sessions_router)
    api.include_router(private_beta_router)
    api.include_router(package_contracts_router)
    api.include_router(world_packaging_router)
    api.include_router(conversations_router)
    api.include_router(conversation_presentations_router)
    api.include_router(observability_router)
    api.include_router(realtime_router)

    @api.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(service="api", status="ok", version=PROJECT_VERSION)

    return api


app = create_app()
