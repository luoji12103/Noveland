from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from noveland.events import (
    EventPublishError,
    WorldEventAppend,
    WorldEventEnvelope,
    WorldEventPublisher,
    WorldEventRecord,
    WorldEventStore,
)
from noveland.worlds.clock import WorldClockStatus
from noveland.worlds.clock_service import WorldClockService, WorldClockView
from noveland.worlds.models import World, WorldClockStateModel
from sqlalchemy import select
from sqlalchemy.orm import Session

RUNTIME_ACTOR_REF = "system:runtime"
CLOCK_ADVANCED_EVENT_NAME = "world.clock_advanced"


class RuntimeEventPublishError(RuntimeError):
    """Raised when runtime events were persisted but could not be broadcast."""

    def __init__(self, failures: list[EventPublishFailure]) -> None:
        super().__init__("failed to publish one or more runtime events")
        self.failures = failures


@dataclass(frozen=True, slots=True)
class EventPublishFailure:
    event: WorldEventRecord
    error: EventPublishError


@dataclass(frozen=True, slots=True)
class RuntimeTickResult:
    advanced_worlds: int
    published_events: int
    events: tuple[WorldEventRecord, ...] = field(default_factory=tuple)


class RuntimeClockTicker:
    def __init__(self, session: Session, publisher: WorldEventPublisher) -> None:
        self._session = session
        self._publisher = publisher

    def run_once(self, wall_time: datetime | None = None) -> RuntimeTickResult:
        tick_wall_time = _utc(wall_time)
        world_ids = self._running_world_ids()
        events: list[WorldEventRecord] = []
        publish_failures: list[EventPublishFailure] = []
        published_events = 0

        for world_id in world_ids:
            view = WorldClockService(self._session).advance(
                world_id,
                wall_time=tick_wall_time,
                actor_ref=RUNTIME_ACTOR_REF,
                reason="runtime tick",
            )
            event = WorldEventStore(self._session).append_event(
                WorldEventAppend(
                    world_id=world_id,
                    event_name=CLOCK_ADVANCED_EVENT_NAME,
                    payload=_clock_event_payload(view),
                    wall_time=tick_wall_time,
                    world_time=view.state.current_world_time,
                    actor_ref=RUNTIME_ACTOR_REF,
                ),
            )
            self._session.commit()
            events.append(event)

            try:
                self._publisher.publish(WorldEventEnvelope.from_record(event))
            except EventPublishError as exc:
                publish_failures.append(EventPublishFailure(event=event, error=exc))
            else:
                published_events += 1

        if publish_failures:
            raise RuntimeEventPublishError(publish_failures)

        return RuntimeTickResult(
            advanced_worlds=len(world_ids),
            published_events=published_events,
            events=tuple(events),
        )

    def _running_world_ids(self) -> list[uuid.UUID]:
        statement = (
            select(WorldClockStateModel.world_id)
            .join(World, World.id == WorldClockStateModel.world_id)
            .where(
                World.is_active.is_(True),
                WorldClockStateModel.status == WorldClockStatus.RUNNING.value,
            )
            .order_by(WorldClockStateModel.world_id)
        )
        return list(self._session.scalars(statement).all())


def _clock_event_payload(view: WorldClockView) -> dict[str, object]:
    return {
        "status": view.state.status.value,
        "current_world_time": view.state.current_world_time.isoformat(),
        "effective_world_time": view.effective_world_time.isoformat(),
        "wall_time_anchor": None
        if view.state.wall_time_anchor is None
        else view.state.wall_time_anchor.isoformat(),
        "speed_multiplier": str(view.state.speed_multiplier),
        "revision": view.state.revision,
    }


def _utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
