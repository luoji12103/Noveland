from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from noveland.adapters.models import ProviderProfile
from noveland.agents.contracts import (
    AgentObservationCreate,
    AgentObservationRecord,
    AgentObservationRefreshResult,
    AgentPersonaRecord,
    AgentPersonaUpsert,
    AgentPresetCalendarEntry,
    AgentPresetRecord,
    AgentPresetUpsert,
)
from noveland.agents.models import AgentObservation, AgentPersona, AgentPreset
from noveland.calendar.models import AgentCalendarEntry
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
                policy_plugin_identifier=persona.policy_plugin_identifier,
                policy_plugin_config=persona.policy_plugin_config,
                is_enabled=persona.is_enabled,
            )
            self._session.add(model)
        else:
            model.persona_text = persona.persona_text
            model.behavior_policy = persona.behavior_policy
            model.policy_plugin_identifier = persona.policy_plugin_identifier
            model.policy_plugin_config = persona.policy_plugin_config
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
            confidence_score=observation.confidence_score,
            review_status=observation.review_status,
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
        run_id: uuid.UUID | None = None,
    ) -> int:
        if not observation_ids:
            return 0
        timestamp = datetime.now(UTC) if consumed_at is None else _as_utc(consumed_at)
        observations = self._session.scalars(
            select(AgentObservation).where(AgentObservation.id.in_(observation_ids)),
        ).all()
        for observation in observations:
            observation.consumed_at = timestamp
            observation.runtime_use_count += 1
            observation.last_used_run_id = run_id
        self._session.flush()
        return len(observations)


class AgentPresetService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self, *, include_inactive: bool) -> list[AgentPresetRecord]:
        statement = select(AgentPreset).order_by(AgentPreset.preset_key)
        if not include_inactive:
            statement = statement.where(AgentPreset.is_active.is_(True))
        return [_preset_record(model) for model in self._session.scalars(statement).all()]

    def get(
        self,
        preset_id: uuid.UUID,
        *,
        include_inactive: bool,
    ) -> AgentPresetRecord | None:
        statement = select(AgentPreset).where(AgentPreset.id == preset_id)
        if not include_inactive:
            statement = statement.where(AgentPreset.is_active.is_(True))
        model = self._session.scalars(statement).one_or_none()
        return None if model is None else _preset_record(model)

    def get_by_key(
        self,
        preset_key: str,
        *,
        include_inactive: bool,
    ) -> AgentPresetRecord | None:
        statement = select(AgentPreset).where(AgentPreset.preset_key == preset_key)
        if not include_inactive:
            statement = statement.where(AgentPreset.is_active.is_(True))
        model = self._session.scalars(statement).one_or_none()
        return None if model is None else _preset_record(model)

    def create(self, preset: AgentPresetUpsert) -> AgentPresetRecord:
        model = AgentPreset(
            preset_key=preset.preset_key,
            name=preset.name,
            description=preset.description,
            default_kind=preset.default_kind,
            default_provider_profile_key=preset.default_provider_profile_key,
            persona_text=preset.persona_text,
            behavior_policy=preset.behavior_policy,
            calendar_blueprint_json=_calendar_blueprint_json(preset.calendar_blueprint),
            advanced_config=preset.advanced_config,
            is_active=preset.is_active,
        )
        self._session.add(model)
        self._session.flush()
        return _preset_record(model)

    def update(self, preset_id: uuid.UUID, preset: AgentPresetUpsert) -> AgentPresetRecord | None:
        model = self._session.scalars(
            select(AgentPreset).where(AgentPreset.id == preset_id),
        ).one_or_none()
        if model is None:
            return None
        should_increment_version = _preset_has_material_change(model, preset)
        model.preset_key = preset.preset_key
        model.name = preset.name
        model.description = preset.description
        model.default_kind = preset.default_kind
        model.default_provider_profile_key = preset.default_provider_profile_key
        model.persona_text = preset.persona_text
        model.behavior_policy = preset.behavior_policy
        model.calendar_blueprint_json = _calendar_blueprint_json(preset.calendar_blueprint)
        model.advanced_config = preset.advanced_config
        model.is_active = preset.is_active
        if should_increment_version:
            model.version += 1
        self._session.flush()
        return _preset_record(model)

    def deactivate(self, preset_id: uuid.UUID) -> AgentPresetRecord | None:
        model = self._session.scalars(
            select(AgentPreset).where(AgentPreset.id == preset_id),
        ).one_or_none()
        if model is None:
            return None
        model.is_active = False
        self._session.flush()
        return _preset_record(model)

    def resolve_provider_profile_id(self, profile_key: str | None) -> uuid.UUID | None:
        if profile_key is None or profile_key == "":
            return None
        model = self._session.scalars(
            select(ProviderProfile).where(ProviderProfile.profile_key == profile_key),
        ).one_or_none()
        return None if model is None else model.id

    def materialize_calendar_blueprint(
        self,
        *,
        world_id: uuid.UUID,
        agent_id: uuid.UUID,
        blueprint: Sequence[AgentPresetCalendarEntry],
    ) -> Sequence[AgentCalendarEntry]:
        created: list[AgentCalendarEntry] = []
        for entry in blueprint:
            model = AgentCalendarEntry(
                world_id=world_id,
                agent_id=agent_id,
                title=entry.title,
                description=entry.description,
                starts_at=entry.starts_at,
                ends_at=entry.ends_at,
                recurrence_rule=entry.recurrence_rule,
                status="active",
                metadata_json=entry.metadata,
            )
            self._session.add(model)
            created.append(model)
        self._session.flush()
        return created


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
        policy_plugin_identifier=model.policy_plugin_identifier,
        policy_plugin_config=model.policy_plugin_config,
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
        confidence_score=model.confidence_score,
        review_status=model.review_status,
        runtime_use_count=model.runtime_use_count,
        last_used_run_id=model.last_used_run_id,
        created_at=model.created_at,
    )


def _preset_record(model: AgentPreset) -> AgentPresetRecord:
    return AgentPresetRecord(
        id=model.id,
        preset_key=model.preset_key,
        name=model.name,
        description=model.description,
        default_kind=model.default_kind,
        default_provider_profile_key=model.default_provider_profile_key,
        persona_text=model.persona_text,
        behavior_policy=model.behavior_policy,
        calendar_blueprint=[
            AgentPresetCalendarEntry.model_validate(entry)
            for entry in model.calendar_blueprint_json
        ],
        advanced_config=model.advanced_config,
        version=model.version,
        is_active=model.is_active,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _preset_has_material_change(model: AgentPreset, preset: AgentPresetUpsert) -> bool:
    return (
        model.preset_key != preset.preset_key
        or model.name != preset.name
        or model.description != preset.description
        or model.default_kind != preset.default_kind
        or model.default_provider_profile_key != preset.default_provider_profile_key
        or model.persona_text != preset.persona_text
        or model.behavior_policy != preset.behavior_policy
        or model.calendar_blueprint_json != _calendar_blueprint_json(preset.calendar_blueprint)
        or model.advanced_config != preset.advanced_config
    )


def _calendar_blueprint_json(
    blueprint: list[AgentPresetCalendarEntry],
) -> list[dict[str, Any]]:
    return [entry.model_dump(mode="json") for entry in blueprint]
