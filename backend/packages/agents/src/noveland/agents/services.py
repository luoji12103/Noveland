from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from noveland.agents.contracts import (
    AgentObservationCreate,
    AgentObservationRecord,
    AgentObservationRefreshResult,
    AgentPersonaRecord,
    AgentPersonaUpsert,
)
from noveland.agents.models import AgentObservation, AgentPersona
from noveland.events.models import WorldEventModel
from sqlalchemy import select
from sqlalchemy.orm import Session

FILTERED_EVENT_NAMES = {
    "world.clock_advanced",
    "calendar.entry_due",
    "agent.run_started",
    "agent.run_completed",
    "agent.run_failed",
    "memory.item_created",
    "narrative.artifact_created",
}


class AgentPersonaService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, world_id: uuid.UUID, agent_id: uuid.UUID) -> AgentPersonaRecord | None:
        model = self._persona_model(world_id, agent_id)
        return None if model is None else _persona_record(model)

    def upsert(self, persona: AgentPersonaUpsert) -> AgentPersonaRecord:
        model = self._persona_model(persona.world_id, persona.agent_id)
        if model is None:
            model = AgentPersona(
                world_id=persona.world_id,
                agent_id=persona.agent_id,
                persona_text=persona.persona_text,
                behavior_policy=persona.behavior_policy,
                is_enabled=persona.is_enabled,
            )
            self._session.add(model)
        else:
            model.persona_text = persona.persona_text
            model.behavior_policy = persona.behavior_policy
            model.is_enabled = persona.is_enabled
        self._session.flush()
        return _persona_record(model)

    def _persona_model(self, world_id: uuid.UUID, agent_id: uuid.UUID) -> AgentPersona | None:
        return self._session.scalars(
            select(AgentPersona).where(
                AgentPersona.world_id == world_id,
                AgentPersona.agent_id == agent_id,
            ),
        ).one_or_none()


class AgentObservationService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(
        self,
        world_id: uuid.UUID,
        agent_id: uuid.UUID,
        limit: int = 20,
    ) -> list[AgentObservationRecord]:
        return [
            _observation_record(model)
            for model in self._session.scalars(
                select(AgentObservation)
                .where(
                    AgentObservation.world_id == world_id,
                    AgentObservation.agent_id == agent_id,
                )
                .order_by(AgentObservation.observed_at.desc())
                .limit(limit),
            ).all()
        ]

    def create(self, observation: AgentObservationCreate) -> AgentObservationRecord:
        model = AgentObservation(
            world_id=observation.world_id,
            agent_id=observation.agent_id,
            source_event_id=observation.source_event_id,
            observation_type=observation.observation_type,
            content=observation.content,
            metadata_json=observation.metadata,
            observed_at=observation.observed_at,
        )
        self._session.add(model)
        self._session.flush()
        return _observation_record(model)

    def refresh_from_events(
        self,
        world_id: uuid.UUID,
        agent_id: uuid.UUID,
        limit: int = 100,
    ) -> AgentObservationRefreshResult:
        events = list(
            self._session.scalars(
                select(WorldEventModel)
                .where(
                    WorldEventModel.world_id == world_id,
                    WorldEventModel.event_name.in_(FILTERED_EVENT_NAMES),
                )
                .order_by(WorldEventModel.sequence.desc())
                .limit(limit),
            ).all()
        )
        events.reverse()
        existing_source_ids = {
            source_id
            for source_id in self._session.scalars(
                select(AgentObservation.source_event_id).where(
                    AgentObservation.agent_id == agent_id,
                    AgentObservation.source_event_id.is_not(None),
                ),
            ).all()
            if source_id is not None
        }

        created: list[AgentObservationRecord] = []
        for event in events:
            if event.id in existing_source_ids:
                continue
            observation = _observation_from_event(event, agent_id)
            if observation is None:
                continue
            created.append(self.create(observation))
            existing_source_ids.add(event.id)

        return AgentObservationRefreshResult(
            created_count=len(created),
            observations=self.list(world_id, agent_id),
        )

    def mark_consumed(
        self,
        observation_ids: Sequence[uuid.UUID],
        consumed_at: datetime | None = None,
    ) -> int:
        if not observation_ids:
            return 0
        timestamp = datetime.now(UTC) if consumed_at is None else _as_utc(consumed_at)
        observations = self._session.scalars(
            select(AgentObservation).where(AgentObservation.id.in_(observation_ids)),
        ).all()
        for observation in observations:
            observation.consumed_at = timestamp
        self._session.flush()
        return len(observations)


def _observation_from_event(
    event: WorldEventModel,
    agent_id: uuid.UUID,
) -> AgentObservationCreate | None:
    payload = event.payload
    if event.event_name != "world.clock_advanced" and not _payload_matches_agent(payload, agent_id):
        return None
    content = _event_content(event.event_name, payload)
    metadata: dict[str, Any] = {
        "event_id": str(event.id),
        "event_sequence": event.sequence,
        "event_name": event.event_name,
    }
    return AgentObservationCreate(
        world_id=event.world_id,
        agent_id=agent_id,
        source_event_id=event.id,
        observation_type=event.event_name,
        content=content,
        metadata=metadata,
        observed_at=_as_utc(event.wall_time),
    )


def _payload_matches_agent(payload: dict[str, Any], agent_id: uuid.UUID) -> bool:
    return payload.get("agent_id") == str(agent_id)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _event_content(event_name: str, payload: dict[str, Any]) -> str:
    if event_name == "world.clock_advanced":
        return f"World clock advanced to revision {payload.get('revision', 'unknown')}."
    if event_name == "calendar.entry_due":
        return "Calendar or schedule rule became due for this agent."
    if event_name == "agent.run_started":
        return "This agent run started."
    if event_name == "agent.run_completed":
        return "This agent run completed."
    if event_name == "agent.run_failed":
        return f"This agent run failed: {payload.get('error', 'unknown error')}."
    if event_name == "memory.item_created":
        return "A private memory item was created for this agent."
    if event_name == "narrative.artifact_created":
        return "A narrative artifact was created from this agent context."
    return f"Observed event {event_name}."


def _persona_record(model: AgentPersona) -> AgentPersonaRecord:
    return AgentPersonaRecord(
        id=model.id,
        world_id=model.world_id,
        agent_id=model.agent_id,
        persona_text=model.persona_text,
        behavior_policy=model.behavior_policy,
        is_enabled=model.is_enabled,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _observation_record(model: AgentObservation) -> AgentObservationRecord:
    return AgentObservationRecord(
        id=model.id,
        world_id=model.world_id,
        agent_id=model.agent_id,
        source_event_id=model.source_event_id,
        observation_type=model.observation_type,
        content=model.content,
        metadata=model.metadata_json,
        observed_at=model.observed_at,
        consumed_at=model.consumed_at,
        created_at=model.created_at,
    )
