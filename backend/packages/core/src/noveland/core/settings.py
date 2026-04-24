from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    environment: str = Field(default="local", validation_alias="NOVELAND_ENV")
    database_url: str = Field(
        default="postgresql+psycopg://noveland:noveland@localhost:5432/noveland",
        validation_alias="NOVELAND_DATABASE_URL",
    )
    nats_url: str = Field(default="nats://localhost:4222", validation_alias="NOVELAND_NATS_URL")
    object_storage_root: Path = Field(
        default=Path(".local/object-storage"),
        validation_alias="NOVELAND_OBJECT_STORAGE_ROOT",
    )
    memory_backend_secrets_json: dict[str, str] = Field(
        default_factory=dict,
        validation_alias="NOVELAND_MEMORY_BACKEND_SECRETS_JSON",
    )
    provider_api_keys_json: dict[str, str] = Field(
        default_factory=dict,
        validation_alias="NOVELAND_PROVIDER_API_KEYS_JSON",
    )
    runtime_loop_interval_seconds: int = Field(
        default=5,
        ge=1,
        le=3600,
        validation_alias="NOVELAND_RUNTIME_LOOP_INTERVAL_SECONDS",
    )
    runtime_batch_limit: int = Field(
        default=20,
        ge=1,
        le=500,
        validation_alias="NOVELAND_RUNTIME_BATCH_LIMIT",
    )


@lru_cache(maxsize=1)
def load_settings() -> AppSettings:
    return AppSettings()
