from fastapi import FastAPI
from noveland.core.version import PROJECT_VERSION
from noveland.services.api.auth import router as auth_router
from noveland.services.api.conversations import router as conversations_router
from noveland.services.api.media import router as media_router
from noveland.services.api.realtime import router as realtime_router
from noveland.services.api.runtime import router as runtime_router
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
    api.include_router(conversations_router)
    api.include_router(realtime_router)

    @api.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(service="api", status="ok", version=PROJECT_VERSION)

    return api


app = create_app()
