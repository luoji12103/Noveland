from fastapi import FastAPI
from noveland.core.version import PROJECT_VERSION
from noveland.services.api.auth import router as auth_router
from pydantic import BaseModel


class HealthResponse(BaseModel):
    service: str
    status: str
    version: str


def create_app() -> FastAPI:
    api = FastAPI(title="Noveland API", version=PROJECT_VERSION)
    api.include_router(auth_router)

    @api.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(service="api", status="ok", version=PROJECT_VERSION)

    return api


app = create_app()
