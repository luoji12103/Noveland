from __future__ import annotations

import uuid
from datetime import UTC, datetime
from importlib import import_module

from noveland.core.settings import AppSettings
from sqlalchemy import DateTime, MetaData, Uuid, create_engine, func, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

MODEL_MODULES = (
    "noveland.core.models",
    "noveland.auth.models",
    "noveland.worlds.models",
    "noveland.agents.models",
    "noveland.adapters.models",
    "noveland.calendar.models",
    "noveland.conversations.models",
    "noveland.invocations.models",
    "noveland.memory.models",
    "noveland.media.models",
    "noveland.events.models",
    "noveland.narrative.models",
    "noveland.observability.models",
)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


def import_model_modules() -> None:
    for module_name in MODEL_MODULES:
        import_module(module_name)


def create_engine_from_settings(settings: AppSettings) -> Engine:
    return create_engine(settings.database_url, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)
