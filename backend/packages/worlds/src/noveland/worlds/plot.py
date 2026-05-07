from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from noveland.agents.models import Agent, AgentRelationshipEdge
from noveland.events import WorldEventAppend, WorldEventImportance, WorldEventStore
from noveland.worlds.guardrails import LivingWorldGuardrailService
from noveland.worlds.models import (
    AgentPresenceState,
    CharacterKnowledgeFact,
    DailyEpisodeDraft,
    DailyLifeEventCandidate,
    EventTriggerCondition,
    FactionProgressTrack,
    OrganizationConflictEvent,
    PlotThread,
    RelationshipEventSuggestion,
    RouteAffinity,
    RumorPropagation,
    RumorRecord,
    SceneBeatDraft,
    SecretRecord,
    StoryHook,
    Worldline,
)
from noveland.worlds.worldlines import worldline_or_404
from sqlalchemy import select
from sqlalchemy.orm import Session


@dataclass(frozen=True, slots=True)
class TriggerDryRun:
    condition_id: uuid.UUID
    condition_key: str
    matched: bool
    satisfied: list[str]
    unsatisfied: list[str]


class LivingWorldPlotService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def worldline_or_404(self, world_id: uuid.UUID, worldline_id: uuid.UUID | None) -> Worldline:
        return worldline_or_404(self._session, world_id, worldline_id)

    def create_story_hook(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        hook_key: str,
        title: str,
        hook_type: str,
        summary: str,
        priority: int,
        owner_agent_id: uuid.UUID | None,
        target_agent_id: uuid.UUID | None,
        due_at: datetime | None,
        metadata: dict[str, Any],
    ) -> StoryHook:
        worldline = self.worldline_or_404(world_id, worldline_id)
        self._ensure_unique_story_key(world_id, worldline.id, hook_key)
        hook = StoryHook(
            id=uuid.uuid4(),
            world_id=world_id,
            worldline_id=worldline.id,
            hook_key=hook_key,
            title=title,
            hook_type=hook_type,
            summary=summary,
            status="open",
            priority=priority,
            owner_agent_id=owner_agent_id,
            target_agent_id=target_agent_id,
            due_at=due_at,
            metadata_json=metadata,
        )
        self._session.add(hook)
        self._session.flush()
        return hook

    def create_plot_thread(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        thread_key: str,
        title: str,
        thread_type: str,
        summary: str,
        stakes: str | None,
        next_beats: list[str],
        participant_agent_ids: list[str],
        organization_ids: list[str],
        priority: int,
        metadata: dict[str, Any],
    ) -> PlotThread:
        worldline = self.worldline_or_404(world_id, worldline_id)
        if (
            self._session.scalars(
                select(PlotThread).where(
                    PlotThread.world_id == world_id,
                    PlotThread.worldline_id == worldline.id,
                    PlotThread.thread_key == thread_key,
                ),
            ).first()
            is not None
        ):
            raise ValueError("plot thread key already exists")
        thread = PlotThread(
            id=uuid.uuid4(),
            world_id=world_id,
            worldline_id=worldline.id,
            thread_key=thread_key,
            title=title,
            thread_type=thread_type,
            status="active",
            summary=summary,
            stakes=stakes,
            next_beats=next_beats,
            participant_agent_ids=participant_agent_ids,
            organization_ids=organization_ids,
            related_event_ids=[],
            priority=priority,
            metadata_json=metadata,
        )
        self._session.add(thread)
        self._session.flush()
        return thread

    def upsert_route_affinity(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        agent_id: uuid.UUID,
        route_key: str,
        status: str,
        affinity: int,
        stage: int,
        flags: list[str],
        metadata: dict[str, Any],
    ) -> RouteAffinity:
        worldline = self.worldline_or_404(world_id, worldline_id)
        route = self._session.scalars(
            select(RouteAffinity).where(
                RouteAffinity.world_id == world_id,
                RouteAffinity.worldline_id == worldline.id,
                RouteAffinity.agent_id == agent_id,
                RouteAffinity.route_key == route_key,
            ),
        ).one_or_none()
        if route is None:
            route = RouteAffinity(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline.id,
                agent_id=agent_id,
                route_key=route_key,
            )
            self._session.add(route)
        route.status = status
        route.affinity = _bounded(affinity, -100, 100)
        route.stage = max(0, stage)
        route.flags = flags
        route.metadata_json = metadata
        self._session.flush()
        return route

    def create_trigger_condition(
        self,
        *,
        world_id: uuid.UUID,
        condition_key: str,
        name: str,
        description: str | None,
        priority: int,
        conditions: dict[str, Any],
        metadata: dict[str, Any],
    ) -> EventTriggerCondition:
        if (
            self._session.scalars(
                select(EventTriggerCondition).where(
                    EventTriggerCondition.world_id == world_id,
                    EventTriggerCondition.condition_key == condition_key,
                ),
            ).first()
            is not None
        ):
            raise ValueError("event trigger condition key already exists")
        condition = EventTriggerCondition(
            id=uuid.uuid4(),
            world_id=world_id,
            condition_key=condition_key,
            name=name,
            description=description,
            priority=priority,
            status="active",
            conditions_json=conditions,
            metadata_json=metadata,
        )
        self._session.add(condition)
        self._session.flush()
        return condition

    def dry_run_trigger_condition(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        condition: EventTriggerCondition,
    ) -> TriggerDryRun:
        worldline = self.worldline_or_404(world_id, worldline_id)
        checks = condition.conditions_json
        satisfied: list[str] = []
        unsatisfied: list[str] = []
        min_open_hooks = _optional_int(checks.get("min_open_hooks"))
        if min_open_hooks is not None:
            count = len(
                self._session.scalars(
                    select(StoryHook.id).where(
                        StoryHook.world_id == world_id,
                        StoryHook.worldline_id == worldline.id,
                        StoryHook.status == "open",
                    ),
                ).all(),
            )
            _record_threshold("open hooks", count, min_open_hooks, satisfied, unsatisfied)
        min_route_affinity = _optional_int(checks.get("min_route_affinity"))
        if min_route_affinity is not None:
            route = self._session.scalars(
                select(RouteAffinity)
                .where(
                    RouteAffinity.world_id == world_id,
                    RouteAffinity.worldline_id == worldline.id,
                )
                .order_by(RouteAffinity.affinity.desc()),
            ).first()
            value = None if route is None else route.affinity
            _record_threshold("route affinity", value, min_route_affinity, satisfied, unsatisfied)
        min_relationship_tension = _optional_int(checks.get("min_relationship_tension"))
        if min_relationship_tension is not None:
            relationship = self._session.scalars(
                select(AgentRelationshipEdge)
                .where(
                    AgentRelationshipEdge.world_id == world_id,
                    AgentRelationshipEdge.worldline_id == worldline.id,
                )
                .order_by(
                    AgentRelationshipEdge.hostility.desc(), AgentRelationshipEdge.rivalry.desc()
                ),
            ).first()
            value = (
                None if relationship is None else max(relationship.hostility, relationship.rivalry)
            )
            _record_threshold(
                "relationship tension",
                value,
                min_relationship_tension,
                satisfied,
                unsatisfied,
            )
        required_scene_id = _uuid_or_none(checks.get("scene_id"))
        if required_scene_id is not None:
            presence = self._session.scalars(
                select(AgentPresenceState).where(
                    AgentPresenceState.world_id == world_id,
                    AgentPresenceState.worldline_id == worldline.id,
                    AgentPresenceState.current_scene_id == required_scene_id,
                ),
            ).first()
            if presence is None:
                unsatisfied.append("No eligible agent is present at the required scene.")
            else:
                satisfied.append("At least one agent is present at the required scene.")
        min_faction_pressure = _optional_int(checks.get("min_faction_pressure"))
        if min_faction_pressure is not None:
            track = self._session.scalars(
                select(FactionProgressTrack)
                .where(
                    FactionProgressTrack.world_id == world_id,
                    FactionProgressTrack.worldline_id == worldline.id,
                )
                .order_by(FactionProgressTrack.pressure.desc()),
            ).first()
            value = None if track is None else track.pressure
            _record_threshold(
                "faction pressure",
                value,
                min_faction_pressure,
                satisfied,
                unsatisfied,
            )
        min_player_choices = _optional_int(checks.get("min_player_choices"))
        if min_player_choices is not None:
            from noveland.worlds.models import PlayerChoiceRecord

            count = len(
                self._session.scalars(
                    select(PlayerChoiceRecord.id).where(
                        PlayerChoiceRecord.world_id == world_id,
                        PlayerChoiceRecord.worldline_id == worldline.id,
                    ),
                ).all(),
            )
            _record_threshold("player choices", count, min_player_choices, satisfied, unsatisfied)
        min_known_facts = _optional_int(checks.get("min_known_facts"))
        if min_known_facts is not None:
            count = len(
                self._session.scalars(
                    select(CharacterKnowledgeFact.id).where(
                        CharacterKnowledgeFact.world_id == world_id,
                        CharacterKnowledgeFact.worldline_id == worldline.id,
                        CharacterKnowledgeFact.is_active.is_(True),
                    ),
                ).all(),
            )
            _record_threshold("known facts", count, min_known_facts, satisfied, unsatisfied)
        max_hidden_secrets = _optional_int(checks.get("max_hidden_secrets"))
        if max_hidden_secrets is not None:
            count = len(
                self._session.scalars(
                    select(SecretRecord.id).where(
                        SecretRecord.world_id == world_id,
                        SecretRecord.worldline_id == worldline.id,
                        SecretRecord.status == "hidden",
                    ),
                ).all(),
            )
            if count > max_hidden_secrets:
                unsatisfied.append(f"hidden secrets above {max_hidden_secrets}.")
            else:
                satisfied.append(f"hidden secrets within {max_hidden_secrets}.")
        if not checks:
            satisfied.append("No conditions configured.")
        return TriggerDryRun(
            condition_id=condition.id,
            condition_key=condition.condition_key,
            matched=not unsatisfied,
            satisfied=satisfied,
            unsatisfied=unsatisfied,
        )

    def compose_scene_beat(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        source_kind: str,
        source_ref: str | None,
        title: str,
        participant_agent_ids: list[str],
        scene_id: uuid.UUID | None,
        metadata: dict[str, Any],
    ) -> SceneBeatDraft:
        worldline = self.worldline_or_404(world_id, worldline_id)
        agents = self._agents_for_ids(world_id, participant_agent_ids)
        names = [agent.display_name for agent in agents] or ["The cast"]
        setup = f"{', '.join(names)} gather around {title}."
        draft = SceneBeatDraft(
            id=uuid.uuid4(),
            world_id=world_id,
            worldline_id=worldline.id,
            source_kind=source_kind,
            source_ref=source_ref,
            title=title,
            setup=setup,
            dialogue_beats=[
                {"speaker": name, "intent": "surface the current tension", "text": ""}
                for name in names[:4]
            ],
            choice_points=[
                {"prompt": "How should the player respond?", "options": ["Observe", "Intervene"]}
            ],
            aftermath=f"The scene leaves a follow-up beat for {names[0]}.",
            participant_agent_ids=participant_agent_ids,
            scene_id=scene_id,
            status="draft",
            metadata_json=metadata,
        )
        self._session.add(draft)
        self._session.flush()
        return draft

    def generate_daily_episode(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        source_candidate_id: uuid.UUID | None,
        title: str | None,
        metadata: dict[str, Any],
    ) -> DailyEpisodeDraft:
        worldline = self.worldline_or_404(world_id, worldline_id)
        candidate = (
            None
            if source_candidate_id is None
            else self._session.get(DailyLifeEventCandidate, source_candidate_id)
        )
        if candidate is not None and (
            candidate.world_id != world_id or candidate.worldline_id != worldline.id
        ):
            raise ValueError("daily candidate not found")
        episode_title = title or (candidate.title if candidate is not None else "Daily episode")
        participant_ids = (
            [] if candidate is None or candidate.agent_id is None else [str(candidate.agent_id)]
        )
        beat = self.compose_scene_beat(
            world_id=world_id,
            worldline_id=worldline.id,
            source_kind="daily_episode",
            source_ref=None if candidate is None else str(candidate.id),
            title=episode_title,
            participant_agent_ids=participant_ids,
            scene_id=None if candidate is None else candidate.scene_id,
            metadata={"daily_episode": True},
        )
        episode = DailyEpisodeDraft(
            id=uuid.uuid4(),
            world_id=world_id,
            worldline_id=worldline.id,
            source_candidate_id=source_candidate_id,
            title=episode_title,
            summary=(
                candidate.summary
                if candidate is not None
                else "A low-risk daily scene draft generated from current living-world state."
            ),
            scene_beat_draft_id=beat.id,
            participant_agent_ids=participant_ids,
            status="draft",
            metadata_json=metadata,
        )
        self._session.add(episode)
        self._session.flush()
        return episode

    def generate_relationship_suggestions(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        limit: int,
    ) -> list[RelationshipEventSuggestion]:
        worldline = self.worldline_or_404(world_id, worldline_id)
        relationships = self._session.scalars(
            select(AgentRelationshipEdge)
            .where(
                AgentRelationshipEdge.world_id == world_id,
                AgentRelationshipEdge.worldline_id == worldline.id,
            )
            .order_by(AgentRelationshipEdge.updated_at.desc()),
        ).all()
        suggestions: list[RelationshipEventSuggestion] = []
        for relationship in relationships[:limit]:
            score = max(
                relationship.hostility,
                relationship.rivalry,
                relationship.obligation,
                relationship.debt,
                abs(relationship.affection),
            )
            if score < 20:
                continue
            existing = self._session.scalars(
                select(RelationshipEventSuggestion).where(
                    RelationshipEventSuggestion.world_id == world_id,
                    RelationshipEventSuggestion.worldline_id == worldline.id,
                    RelationshipEventSuggestion.relationship_id == relationship.id,
                    RelationshipEventSuggestion.status == "suggested",
                ),
            ).first()
            if existing is not None:
                suggestions.append(existing)
                continue
            suggestion = RelationshipEventSuggestion(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline.id,
                relationship_id=relationship.id,
                source_agent_id=relationship.source_agent_id,
                target_agent_id=relationship.target_agent_id,
                title="Relationship tension scene",
                reason=_relationship_reason(relationship),
                suggested_event_name="relationship.suggested_event",
                score=score,
                status="suggested",
                metadata_json={},
            )
            self._session.add(suggestion)
            suggestions.append(suggestion)
        self._session.flush()
        return suggestions

    def resolve_organization_conflict(
        self,
        *,
        world_id: uuid.UUID,
        conflict_id: uuid.UUID,
        actor_ref: str,
    ) -> OrganizationConflictEvent:
        conflict = self._session.get(OrganizationConflictEvent, conflict_id)
        if conflict is None or conflict.world_id != world_id:
            raise ValueError("organization conflict not found")
        track = (
            None
            if conflict.faction_track_id is None
            else self._session.get(FactionProgressTrack, conflict.faction_track_id)
        )
        if track is not None and track.world_id == world_id:
            track.progress = _bounded(track.progress + conflict.progress_delta, 0, 100)
            track.pressure = _bounded(track.pressure + conflict.pressure_delta, 0, 100)
        event = WorldEventStore(self._session).append_event(
            WorldEventAppend(
                world_id=world_id,
                worldline_id=conflict.worldline_id,
                event_name="organization.conflict_resolved",
                payload={
                    "conflict_id": str(conflict.id),
                    "organization_id": str(conflict.organization_id),
                    "faction_track_id": None
                    if conflict.faction_track_id is None
                    else str(conflict.faction_track_id),
                    "title": conflict.title,
                    "pressure_delta": conflict.pressure_delta,
                    "progress_delta": conflict.progress_delta,
                },
                importance=WorldEventImportance.ORGANIZATION,
                wall_time=datetime.now(UTC),
                actor_ref=actor_ref,
            ),
        )
        conflict.resolved_event_id = event.id
        conflict.status = "resolved"
        self._session.flush()
        return conflict

    def deliver_rumor(
        self,
        *,
        world_id: uuid.UUID,
        propagation_id: uuid.UUID,
        actor_ref: str,
    ) -> RumorPropagation:
        propagation = self._session.get(RumorPropagation, propagation_id)
        if propagation is None or propagation.world_id != world_id:
            raise ValueError("rumor propagation not found")
        rumor = self._session.get(RumorRecord, propagation.rumor_id)
        if rumor is None or rumor.world_id != world_id:
            raise ValueError("rumor not found")
        if propagation.target_agent_id is not None:
            known = set(rumor.known_agent_ids)
            known.add(str(propagation.target_agent_id))
            rumor.known_agent_ids = sorted(known)
        event = WorldEventStore(self._session).append_event(
            WorldEventAppend(
                world_id=world_id,
                worldline_id=propagation.worldline_id,
                event_name="rumor.delivered",
                payload={
                    "rumor_id": str(rumor.id),
                    "propagation_id": str(propagation.id),
                    "target_agent_id": None
                    if propagation.target_agent_id is None
                    else str(propagation.target_agent_id),
                },
                importance=WorldEventImportance.DAILY,
                wall_time=datetime.now(UTC),
                actor_ref=actor_ref,
            ),
        )
        propagation.delivered_event_id = event.id
        propagation.status = "delivered"
        if propagation.target_agent_id is not None:
            LivingWorldGuardrailService(self._session).upsert_knowledge_fact(
                world_id=world_id,
                worldline_id=propagation.worldline_id,
                agent_id=propagation.target_agent_id,
                fact_key=f"rumor:{rumor.rumor_key}",
                knowledge_kind="guess",
                content=rumor.content,
                confidence=60,
                visibility="private",
                source_event_id=event.id,
                source_ref=str(rumor.id),
                metadata={
                    "rumor_id": str(rumor.id),
                    "propagation_id": str(propagation.id),
                    "source": "rumor_delivery",
                },
            )
        self._session.flush()
        return propagation

    def _ensure_unique_story_key(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        hook_key: str,
    ) -> None:
        if (
            self._session.scalars(
                select(StoryHook).where(
                    StoryHook.world_id == world_id,
                    StoryHook.worldline_id == worldline_id,
                    StoryHook.hook_key == hook_key,
                ),
            ).first()
            is not None
        ):
            raise ValueError("story hook key already exists")

    def _agents_for_ids(self, world_id: uuid.UUID, agent_ids: list[str]) -> list[Agent]:
        parsed_ids = [_uuid_or_none(agent_id) for agent_id in agent_ids]
        ids = [agent_id for agent_id in parsed_ids if agent_id is not None]
        if not ids:
            return []
        agents = self._session.scalars(
            select(Agent).where(Agent.world_id == world_id, Agent.id.in_(ids)),
        ).all()
        agents_by_id = {agent.id: agent for agent in agents}
        return [agents_by_id[agent_id] for agent_id in ids if agent_id in agents_by_id]


def _record_threshold(
    label: str,
    value: int | None,
    threshold: int,
    satisfied: list[str],
    unsatisfied: list[str],
) -> None:
    if value is None or value < threshold:
        unsatisfied.append(f"{label} below {threshold}.")
    else:
        satisfied.append(f"{label} meets {threshold}.")


def _relationship_reason(relationship: AgentRelationshipEdge) -> str:
    parts: list[str] = []
    if relationship.hostility >= 20:
        parts.append(f"hostility {relationship.hostility}")
    if relationship.rivalry >= 20:
        parts.append(f"rivalry {relationship.rivalry}")
    if relationship.obligation >= 20:
        parts.append(f"obligation {relationship.obligation}")
    if relationship.debt >= 20:
        parts.append(f"debt {relationship.debt}")
    if abs(relationship.affection) >= 20:
        parts.append(f"affection {relationship.affection}")
    return "Relationship pressure: " + ", ".join(parts or ["moderate tension"])


def _bounded(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def _optional_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _uuid_or_none(value: object) -> uuid.UUID | None:
    if isinstance(value, uuid.UUID):
        return value
    if isinstance(value, str):
        try:
            return uuid.UUID(value)
        except ValueError:
            return None
    return None
