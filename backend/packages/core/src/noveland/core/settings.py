from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

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


@lru_cache(maxsize=1)
def load_settings() -> AppSettings:
    return AppSettings()
