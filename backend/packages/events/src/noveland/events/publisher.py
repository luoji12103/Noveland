from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from noveland.events.contracts import WorldEventRecord
from noveland.events.errors import EventPublishError
from pydantic import BaseModel, ConfigDict, field_validator

WORLD_EVENT_SUBJECT_TEMPLATE = "noveland.world.{world_id}.events"


class WorldEventEnvelope(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: uuid.UUID
    world_id: uuid.UUID
    sequence: int
    event_name: str
    payload: dict[str, object]
    wall_time: datetime
    world_time: datetime | None = None
    actor_ref: str
    correlation_id: uuid.UUID | None = None

    @field_validator("wall_time", "world_time", mode="after")
    @classmethod
    def normalize_datetime(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("event envelope datetimes must be timezone-aware")
        return value.astimezone(UTC)

    @property
    def subject(self) -> str:
        return subject_for_world(self.world_id)

    @classmethod
    def from_record(cls, record: WorldEventRecord) -> WorldEventEnvelope:
        return cls(
            event_id=record.id,
            world_id=record.world_id,
            sequence=record.sequence,
            event_name=record.event_name,
            payload=record.payload,
            wall_time=record.wall_time,
            world_time=record.world_time,
            actor_ref=record.actor_ref,
            correlation_id=record.correlation_id,
        )

    def to_json_bytes(self) -> bytes:
        return json.dumps(
            self.model_dump(mode="json"),
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")


class WorldEventPublisher(Protocol):
    def publish(self, envelope: WorldEventEnvelope) -> None:
        """Publish one world event envelope."""


@dataclass(frozen=True, slots=True)
class PublishedWorldEvent:
    subject: str
    envelope: WorldEventEnvelope


@dataclass(slots=True)
class InMemoryWorldEventPublisher:
    published: list[PublishedWorldEvent] = field(default_factory=list)

    def publish(self, envelope: WorldEventEnvelope) -> None:
        self.published.append(PublishedWorldEvent(subject=envelope.subject, envelope=envelope))


class NatsWorldEventPublisher:
    def __init__(self, nats_url: str) -> None:
        self._nats_url = nats_url

    def publish(self, envelope: WorldEventEnvelope) -> None:
        try:
            asyncio.run(self._publish(envelope))
        except Exception as exc:
            raise EventPublishError("failed to publish world event to NATS") from exc

    async def _publish(self, envelope: WorldEventEnvelope) -> None:
        import nats

        client = await nats.connect(servers=[self._nats_url])
        try:
            await client.publish(envelope.subject, envelope.to_json_bytes())
            await client.flush()
        finally:
            await client.close()


def subject_for_world(world_id: uuid.UUID) -> str:
    return WORLD_EVENT_SUBJECT_TEMPLATE.format(world_id=world_id)


def published_subjects(events: Sequence[PublishedWorldEvent]) -> list[str]:
    return [event.subject for event in events]
