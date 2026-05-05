from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from noveland.agents.models import Agent
from noveland.calendar.models import AgentCalendarEntry, WorldScheduleRule
from noveland.events import WorldEventAppend, WorldEventImportance, WorldEventStore
from noveland.worlds.clock_service import WorldClockService
from noveland.worlds.models import (
    AgentPresenceState,
    DailyLifeEventCandidate,
    FactionProgressTrack,
    OffscreenEventQueueItem,
    Scene,
    World,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

DEFAULT_RUNTIME_ACTOR_REF = "system:runtime"


@dataclass(frozen=True, slots=True)
class DailyLifePreviewResult:
    world_id: uuid.UUID
    start_world_time: datetime
    horizon_hours: int
    candidate_count: int
    candidates: list[DailyLifeEventCandidate]


@dataclass(frozen=True, slots=True)
class OffscreenResolutionResult:
    processed_count: int
    resolved_count: int
    failed_count: int
    event_ids: list[uuid.UUID]


class LivingWorldAutonomyService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def preview_daily_life(
        self,
        *,
        world_id: uuid.UUID,
        start_world_time: datetime | None = None,
        horizon_hours: int = 24,
        limit: int = 20,
    ) -> DailyLifePreviewResult:
        start = (
            _utc(start_world_time) if start_world_time is not None else self._world_time(world_id)
        )
        candidates: list[DailyLifeEventCandidate] = []
        for agent in self._enabled_agents(world_id):
            if len(candidates) >= limit:
                break
            scene_id = self._presence_scene_id(world_id, agent.id) or agent.home_scene_id
            candidates.append(
                DailyLifeEventCandidate(
                    world_id=world_id,
                    agent_id=agent.id,
                    scene_id=scene_id,
                    title=f"{agent.display_name} daily life beat",
                    summary=self._daily_summary(agent, scene_id),
                    importance="daily",
                    starts_at=start,
                    source_kind="daily_life_scheduler",
                    source_ref=str(agent.id),
                    status="candidate",
                    metadata_json={
                        "horizon_hours": horizon_hours,
                        "agent_key": agent.agent_key,
                        "schedule_rule_count": self._schedule_rule_count(world_id),
                    },
                ),
            )
        return DailyLifePreviewResult(
            world_id=world_id,
            start_world_time=start,
            horizon_hours=horizon_hours,
            candidate_count=len(candidates),
            candidates=candidates,
        )

    def generate_daily_life_candidates(
        self,
        *,
        world_id: uuid.UUID,
        horizon_hours: int = 24,
        limit: int = 20,
    ) -> list[DailyLifeEventCandidate]:
        preview = self.preview_daily_life(
            world_id=world_id,
            horizon_hours=horizon_hours,
            limit=limit,
        )
        persisted: list[DailyLifeEventCandidate] = []
        for candidate in preview.candidates:
            existing = self._session.scalars(
                select(DailyLifeEventCandidate).where(
                    DailyLifeEventCandidate.world_id == world_id,
                    DailyLifeEventCandidate.agent_id == candidate.agent_id,
                    DailyLifeEventCandidate.starts_at == candidate.starts_at,
                    DailyLifeEventCandidate.source_kind == candidate.source_kind,
                ),
            ).first()
            if existing is not None:
                persisted.append(existing)
                continue
            self._session.add(candidate)
            persisted.append(candidate)
        self._session.flush()
        return persisted

    def queue_candidate(
        self,
        *,
        candidate_id: uuid.UUID,
        event_name: str = "living_world.daily_life",
    ) -> OffscreenEventQueueItem:
        candidate = self._session.get(DailyLifeEventCandidate, candidate_id)
        if candidate is None:
            raise ValueError("candidate not found")
        item = OffscreenEventQueueItem(
            world_id=candidate.world_id,
            source_candidate_id=candidate.id,
            event_name=event_name,
            title=candidate.title,
            payload_json={
                "title": candidate.title,
                "summary": candidate.summary,
                "agent_id": None if candidate.agent_id is None else str(candidate.agent_id),
                "scene_id": None if candidate.scene_id is None else str(candidate.scene_id),
                "source_candidate_id": str(candidate.id),
            },
            due_at=candidate.starts_at,
            importance=candidate.importance,
            status="pending",
        )
        candidate.status = "queued"
        self._session.add(item)
        self._session.flush()
        return item

    def resolve_due_offscreen_events(
        self,
        *,
        world_id: uuid.UUID | None = None,
        wall_time: datetime | None = None,
        limit: int = 20,
        actor_ref: str = DEFAULT_RUNTIME_ACTOR_REF,
    ) -> OffscreenResolutionResult:
        now = _utc(wall_time)
        statement = (
            select(OffscreenEventQueueItem)
            .join(World, World.id == OffscreenEventQueueItem.world_id)
            .where(
                World.is_active.is_(True),
                OffscreenEventQueueItem.status == "pending",
                OffscreenEventQueueItem.due_at <= now,
            )
        )
        if world_id is not None:
            statement = statement.where(OffscreenEventQueueItem.world_id == world_id)
        items = self._session.scalars(
            statement.order_by(
                OffscreenEventQueueItem.due_at,
                OffscreenEventQueueItem.created_at,
            ).limit(limit),
        ).all()
        resolved = 0
        failed = 0
        event_ids: list[uuid.UUID] = []
        store = WorldEventStore(self._session)
        for item in items:
            try:
                event = store.append_event(
                    WorldEventAppend(
                        world_id=item.world_id,
                        event_name=item.event_name,
                        importance=WorldEventImportance(item.importance),
                        payload=item.payload_json,
                        wall_time=now,
                        world_time=_utc(item.due_at),
                        actor_ref=actor_ref,
                    ),
                )
                item.status = "resolved"
                item.resolved_event_id = event.id
                item.last_error = None
                self._apply_resolution_side_effects(item, event.id)
                resolved += 1
                event_ids.append(event.id)
            except Exception as exc:
                item.status = "failed"
                item.last_error = str(exc)
                failed += 1
        self._session.flush()
        return OffscreenResolutionResult(
            processed_count=len(items),
            resolved_count=resolved,
            failed_count=failed,
            event_ids=event_ids,
        )

    def gm_iteration(
        self,
        *,
        wall_time: datetime | None = None,
        limit: int = 20,
        actor_ref: str = DEFAULT_RUNTIME_ACTOR_REF,
    ) -> OffscreenResolutionResult:
        return self.resolve_due_offscreen_events(
            wall_time=wall_time,
            limit=limit,
            actor_ref=actor_ref,
        )

    def _apply_resolution_side_effects(
        self, item: OffscreenEventQueueItem, event_id: uuid.UUID
    ) -> None:
        candidate = (
            None
            if item.source_candidate_id is None
            else self._session.get(DailyLifeEventCandidate, item.source_candidate_id)
        )
        if candidate is not None and candidate.agent_id is not None:
            presence = self._presence_model(candidate.world_id, candidate.agent_id)
            if presence is None:
                presence = AgentPresenceState(
                    world_id=candidate.world_id,
                    agent_id=candidate.agent_id,
                )
                self._session.add(presence)
            presence.current_scene_id = candidate.scene_id
            presence.visibility_status = "visible"
            presence.encounter_eligible = True
            presence.last_event_id = event_id
        if item.importance == "organization":
            track = self._session.scalars(
                select(FactionProgressTrack)
                .where(FactionProgressTrack.world_id == item.world_id)
                .order_by(FactionProgressTrack.updated_at.desc()),
            ).first()
            if track is not None:
                track.progress = min(100, track.progress + 1)

    def _enabled_agents(self, world_id: uuid.UUID) -> list[Agent]:
        return list(
            self._session.scalars(
                select(Agent)
                .where(Agent.world_id == world_id, Agent.is_enabled.is_(True))
                .order_by(Agent.agent_key),
            ).all(),
        )

    def _presence_model(
        self,
        world_id: uuid.UUID,
        agent_id: uuid.UUID,
    ) -> AgentPresenceState | None:
        return self._session.scalars(
            select(AgentPresenceState).where(
                AgentPresenceState.world_id == world_id,
                AgentPresenceState.agent_id == agent_id,
            ),
        ).one_or_none()

    def _presence_scene_id(self, world_id: uuid.UUID, agent_id: uuid.UUID) -> uuid.UUID | None:
        presence = self._presence_model(world_id, agent_id)
        return None if presence is None else presence.current_scene_id

    def _world_time(self, world_id: uuid.UUID) -> datetime:
        return WorldClockService(self._session).view(world_id).effective_world_time

    def _daily_summary(self, agent: Agent, scene_id: uuid.UUID | None) -> str:
        if scene_id is None:
            return f"{agent.display_name} continues their routine offscreen."
        scene = self._session.get(Scene, scene_id)
        if scene is None:
            return f"{agent.display_name} continues their routine offscreen."
        return f"{agent.display_name} spends time at {scene.name}."

    def _schedule_rule_count(self, world_id: uuid.UUID) -> int:
        return len(
            self._session.scalars(
                select(WorldScheduleRule.id).where(
                    WorldScheduleRule.world_id == world_id,
                    WorldScheduleRule.is_enabled.is_(True),
                ),
            ).all(),
        ) + len(
            self._session.scalars(
                select(AgentCalendarEntry.id).where(
                    AgentCalendarEntry.world_id == world_id,
                    AgentCalendarEntry.status == "active",
                ),
            ).all(),
        )


def _utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
