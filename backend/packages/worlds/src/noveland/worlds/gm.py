from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from noveland.agents.models import AgentRelationshipEdge
from noveland.events import (
    WorldEventAppend,
    WorldEventImportance,
    WorldEventRecord,
    WorldEventStore,
)
from noveland.events.models import WorldSnapshotModel
from noveland.worlds.conditions import evaluate_world_conditions
from noveland.worlds.models import (
    AgentPresenceState,
    DailyEpisodeDraft,
    DailyLifeEventCandidate,
    EventResolutionRule,
    FactionProgressTrack,
    GMAgenda,
    GMEventProposal,
    GroupInteractionContext,
    OffscreenEventQueueItem,
    OrganizationConflictEvent,
    PlayerActorProfile,
    PlayerChoiceRecord,
    PlotThread,
    RelationshipEventSuggestion,
    RouteAffinity,
    RumorPropagation,
    RumorRecord,
    SceneBeatDraft,
    StoryHook,
    Worldline,
)
from noveland.worlds.plot import LivingWorldPlotService
from noveland.worlds.worldlines import ensure_primary_worldline, worldline_or_404
from sqlalchemy import select
from sqlalchemy.orm import Session


@dataclass(frozen=True, slots=True)
class ResolutionRuleDryRun:
    rule_id: uuid.UUID
    rule_key: str
    matched: bool
    reasons: list[str]
    effects: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ChoiceConsequencePreview:
    relationship_updates: list[dict[str, Any]]
    faction_updates: list[dict[str, Any]]
    offscreen_events: list[dict[str, Any]]
    diagnostics: list[str]


@dataclass(frozen=True, slots=True)
class WorldlineComparison:
    base_worldline_id: uuid.UUID
    compare_worldline_id: uuid.UUID
    fork_event_sequence: int | None
    divergent_event_count: int
    relationship_delta_count: int
    faction_delta_count: int
    choice_delta_count: int


@dataclass(frozen=True, slots=True)
class GMMacroPlanItem:
    item_kind: str
    rule_id: uuid.UUID
    rule_key: str
    priority: int
    title: str
    payload: dict[str, Any]
    source_context: dict[str, Any]


@dataclass(frozen=True, slots=True)
class GMMacroPlanResult:
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    planned_items: list[GMMacroPlanItem]
    diagnostics: list[str]


@dataclass(frozen=True, slots=True)
class GMMacroExecutionResult:
    proposal_count: int
    offscreen_event_count: int
    proposal_ids: list[uuid.UUID]
    offscreen_event_ids: list[uuid.UUID]


class LivingWorldGMService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def primary_worldline(self, world_id: uuid.UUID) -> Worldline:
        return ensure_primary_worldline(self._session, world_id)

    def worldline_or_404(self, world_id: uuid.UUID, worldline_id: uuid.UUID | None) -> Worldline:
        return worldline_or_404(self._session, world_id, worldline_id)

    def fork_worldline(
        self,
        *,
        world_id: uuid.UUID,
        source_worldline_id: uuid.UUID | None,
        worldline_key: str,
        name: str,
        description: str | None,
        forked_from_snapshot_id: uuid.UUID | None,
        fork_event_sequence: int | None,
        actor_ref: str,
        metadata: dict[str, Any],
    ) -> Worldline:
        source = self.worldline_or_404(world_id, source_worldline_id)
        if (
            self._session.scalars(
                select(Worldline).where(
                    Worldline.world_id == world_id,
                    Worldline.worldline_key == worldline_key,
                ),
            ).first()
            is not None
        ):
            raise ValueError("worldline key already exists")
        fork_event_sequence = self._validated_current_fork_sequence(
            world_id=world_id,
            source=source,
            forked_from_snapshot_id=forked_from_snapshot_id,
            fork_event_sequence=fork_event_sequence,
        )
        fork = Worldline(
            id=uuid.uuid4(),
            world_id=world_id,
            worldline_key=worldline_key,
            name=name,
            description=description,
            parent_worldline_id=source.id,
            forked_from_snapshot_id=forked_from_snapshot_id,
            fork_event_sequence=fork_event_sequence,
            status="active",
            created_by_actor_ref=actor_ref,
            metadata_json={
                **metadata,
                "source_worldline_id": str(source.id),
            },
        )
        self._session.add(fork)
        self._session.flush()
        self._copy_worldline_state(world_id=world_id, source=source, target=fork)
        self._session.flush()
        return fork

    def _validated_current_fork_sequence(
        self,
        *,
        world_id: uuid.UUID,
        source: Worldline,
        forked_from_snapshot_id: uuid.UUID | None,
        fork_event_sequence: int | None,
    ) -> int:
        store = WorldEventStore(self._session)
        latest_sequence = store.latest_event_sequence(world_id, source.id)
        if forked_from_snapshot_id is not None:
            snapshot = self._session.get(WorldSnapshotModel, forked_from_snapshot_id)
            if (
                snapshot is None
                or snapshot.world_id != world_id
                or snapshot.worldline_id != source.id
            ):
                raise ValueError("fork snapshot not found")
            if snapshot.covers_event_sequence != latest_sequence:
                raise ValueError(
                    "historical snapshot fork reconstruction is not supported yet; "
                    "fork from the latest snapshot or latest event sequence"
                )
            if (
                fork_event_sequence is not None
                and fork_event_sequence != snapshot.covers_event_sequence
            ):
                raise ValueError("fork event sequence must match the selected snapshot")
            return int(snapshot.covers_event_sequence)
        if fork_event_sequence is not None and fork_event_sequence != latest_sequence:
            raise ValueError(
                "historical event fork reconstruction is not supported yet; "
                "fork from the latest event sequence"
            )
        return latest_sequence

    def create_agenda(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        title: str,
        summary: str,
        priority: int,
        focus_agents: list[str],
        focus_organizations: list[str],
        metadata: dict[str, Any],
    ) -> GMAgenda:
        worldline = self.worldline_or_404(world_id, worldline_id)
        agenda = GMAgenda(
            id=uuid.uuid4(),
            world_id=world_id,
            worldline_id=worldline.id,
            title=title,
            summary=summary,
            priority=priority,
            status="active",
            focus_agents=focus_agents,
            focus_organizations=focus_organizations,
            metadata_json=metadata,
        )
        self._session.add(agenda)
        self._session.flush()
        return agenda

    def create_rule(
        self,
        *,
        world_id: uuid.UUID,
        rule_key: str,
        name: str,
        description: str | None,
        priority: int,
        conditions: dict[str, Any],
        effects: dict[str, Any],
    ) -> EventResolutionRule:
        if (
            self._session.scalars(
                select(EventResolutionRule).where(
                    EventResolutionRule.world_id == world_id,
                    EventResolutionRule.rule_key == rule_key,
                ),
            ).first()
            is not None
        ):
            raise ValueError("rule key already exists")
        rule = EventResolutionRule(
            id=uuid.uuid4(),
            world_id=world_id,
            rule_key=rule_key,
            name=name,
            description=description,
            priority=priority,
            status="active",
            conditions_json=conditions,
            effects_json=effects,
        )
        self._session.add(rule)
        self._session.flush()
        return rule

    def bind_player_actor(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        user_id: uuid.UUID,
        display_name: str,
        current_scene_id: uuid.UUID | None,
        profile: dict[str, Any],
    ) -> PlayerActorProfile:
        worldline = self.worldline_or_404(world_id, worldline_id)
        actor = self._session.scalars(
            select(PlayerActorProfile).where(
                PlayerActorProfile.world_id == world_id,
                PlayerActorProfile.worldline_id == worldline.id,
                PlayerActorProfile.user_id == user_id,
            ),
        ).one_or_none()
        if actor is None:
            actor = PlayerActorProfile(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline.id,
                user_id=user_id,
                actor_ref=f"player:{user_id}:{worldline.worldline_key}",
                display_name=display_name,
                current_scene_id=current_scene_id,
                profile_json=profile,
                is_active=True,
            )
            self._session.add(actor)
        else:
            actor.display_name = display_name
            actor.current_scene_id = current_scene_id
            actor.profile_json = profile
            actor.is_active = True
        self._session.flush()
        return actor

    def record_player_choice(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        user_id: uuid.UUID,
        player_actor_id: uuid.UUID,
        choice_key: str,
        choice_kind: str,
        prompt: str,
        selected_option: str,
        context: dict[str, Any],
        effects: dict[str, Any],
        actor_ref: str,
        apply: bool,
    ) -> PlayerChoiceRecord:
        worldline = self.worldline_or_404(world_id, worldline_id)
        player_actor = self._session.get(PlayerActorProfile, player_actor_id)
        if (
            player_actor is None
            or player_actor.world_id != world_id
            or player_actor.worldline_id != worldline.id
            or player_actor.user_id != user_id
        ):
            raise ValueError("player actor not found")
        preview = self.choice_consequence_preview(
            world_id=world_id,
            worldline_id=worldline.id,
            effects=effects,
        )
        choice = PlayerChoiceRecord(
            id=uuid.uuid4(),
            world_id=world_id,
            worldline_id=worldline.id,
            user_id=user_id,
            player_actor_id=player_actor.id,
            choice_key=choice_key,
            choice_kind=choice_kind,
            prompt=prompt,
            selected_option=selected_option,
            context_json=context,
            consequence_preview={
                "relationship_updates": preview.relationship_updates,
                "faction_updates": preview.faction_updates,
                "offscreen_events": preview.offscreen_events,
                "diagnostics": preview.diagnostics,
            },
        )
        self._session.add(choice)
        self._session.flush()
        recorded_event = self._append_choice_recorded_event(
            world_id=world_id,
            worldline_id=worldline.id,
            player_actor=player_actor,
            choice=choice,
            actor_ref=actor_ref,
        )
        choice.applied_event_id = recorded_event.id
        if apply:
            self.apply_choice_consequences(
                world_id=world_id,
                worldline_id=worldline.id,
                player_actor=player_actor,
                choice=choice,
                effects=effects,
                actor_ref=actor_ref,
            )
        return choice

    def create_proposal(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        agenda_id: uuid.UUID | None,
        title: str,
        reason: str,
        event_name: str,
        proposed_payload: dict[str, Any],
        importance: str,
        risk_score: int,
        affected_agents: list[str],
        affected_organizations: list[str],
        source_context: dict[str, Any],
    ) -> GMEventProposal:
        worldline = self.worldline_or_404(world_id, worldline_id)
        if agenda_id is not None:
            agenda = self._session.get(GMAgenda, agenda_id)
            if agenda is None or agenda.world_id != world_id or agenda.worldline_id != worldline.id:
                raise ValueError("agenda not found")
        proposal = GMEventProposal(
            id=uuid.uuid4(),
            world_id=world_id,
            worldline_id=worldline.id,
            agenda_id=agenda_id,
            title=title,
            reason=reason,
            event_name=event_name,
            proposed_payload=proposed_payload,
            importance=importance,
            risk_score=risk_score,
            affected_agents=affected_agents,
            affected_organizations=affected_organizations,
            source_context=source_context,
            status="proposed",
        )
        self._session.add(proposal)
        self._session.flush()
        return proposal

    def review_proposal(
        self,
        *,
        world_id: uuid.UUID,
        proposal_id: uuid.UUID,
        status: str,
        review_note: str | None,
        actor_ref: str,
    ) -> GMEventProposal:
        proposal = self._proposal_or_404(world_id, proposal_id)
        if status == "resolved":
            event = WorldEventStore(self._session).append_event(
                WorldEventAppend(
                    world_id=proposal.world_id,
                    worldline_id=proposal.worldline_id,
                    event_name=proposal.event_name,
                    payload={
                        **proposal.proposed_payload,
                        "proposal_id": str(proposal.id),
                        "proposal_title": proposal.title,
                    },
                    importance=WorldEventImportance(proposal.importance),
                    wall_time=datetime.now(UTC),
                    actor_ref=actor_ref,
                ),
            )
            proposal.resolved_event_id = event.id
        proposal.status = status
        proposal.review_note = review_note
        self._session.flush()
        return proposal

    def dry_run_rule(
        self,
        *,
        world_id: uuid.UUID,
        rule: EventResolutionRule,
        worldline_id: uuid.UUID | None,
    ) -> ResolutionRuleDryRun:
        worldline = self.worldline_or_404(world_id, worldline_id)
        evaluation = evaluate_world_conditions(
            self._session,
            world_id=world_id,
            worldline_id=worldline.id,
            conditions=rule.conditions_json,
        )
        reasons = [*evaluation.satisfied, *evaluation.unsatisfied]
        if evaluation.matched:
            reasons.append("Rule conditions are satisfied.")
        return ResolutionRuleDryRun(
            rule_id=rule.id,
            rule_key=rule.rule_key,
            matched=evaluation.matched,
            reasons=reasons,
            effects=rule.effects_json,
        )

    def plan_macro_events(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        limit: int = 20,
    ) -> GMMacroPlanResult:
        worldline = self.worldline_or_404(world_id, worldline_id)
        rules = self._session.scalars(
            select(EventResolutionRule)
            .where(
                EventResolutionRule.world_id == world_id,
                EventResolutionRule.status == "active",
            )
            .order_by(EventResolutionRule.priority.desc(), EventResolutionRule.rule_key)
            .limit(max(1, min(limit, 100))),
        ).all()
        diagnostics: list[str] = []
        items: list[GMMacroPlanItem] = []
        remaining = max(1, min(limit, 100))
        for rule in rules:
            if remaining <= 0:
                break
            evaluation = evaluate_world_conditions(
                self._session,
                world_id=world_id,
                worldline_id=worldline.id,
                conditions=rule.conditions_json,
            )
            if not evaluation.matched:
                diagnostics.append(f"{rule.rule_key}: skipped; {', '.join(evaluation.unsatisfied)}")
                continue
            source_context = {
                "source": "gm_macro_planner",
                "rule_id": str(rule.id),
                "rule_key": rule.rule_key,
                "condition_evidence": evaluation.evidence,
                "satisfied": evaluation.satisfied,
            }
            for index, proposal in enumerate(_list_of_dicts(rule.effects_json.get("proposals"))):
                if remaining <= 0:
                    break
                items.append(
                    GMMacroPlanItem(
                        item_kind="proposal",
                        rule_id=rule.id,
                        rule_key=rule.rule_key,
                        priority=rule.priority,
                        title=str(proposal.get("title") or rule.name),
                        payload=proposal,
                        source_context={**source_context, "effect_index": index},
                    ),
                )
                remaining -= 1
            for index, offscreen in enumerate(
                _list_of_dicts(rule.effects_json.get("offscreen_events"))
            ):
                if remaining <= 0:
                    break
                items.append(
                    GMMacroPlanItem(
                        item_kind="offscreen_event",
                        rule_id=rule.id,
                        rule_key=rule.rule_key,
                        priority=rule.priority,
                        title=str(offscreen.get("title") or rule.name),
                        payload=offscreen,
                        source_context={**source_context, "effect_index": index},
                    ),
                )
                remaining -= 1
        return GMMacroPlanResult(
            world_id=world_id,
            worldline_id=worldline.id,
            planned_items=items,
            diagnostics=diagnostics,
        )

    def execute_macro_plan(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        plan: GMMacroPlanResult | None = None,
        actor_ref: str,
        limit: int = 20,
    ) -> GMMacroExecutionResult:
        worldline = self.worldline_or_404(world_id, worldline_id)
        plan = plan or self.plan_macro_events(
            world_id=world_id,
            worldline_id=worldline.id,
            limit=limit,
        )
        proposal_ids: list[uuid.UUID] = []
        offscreen_event_ids: list[uuid.UUID] = []
        for item in plan.planned_items[: max(1, min(limit, 100))]:
            if item.item_kind == "proposal":
                proposal = self.create_proposal(
                    world_id=world_id,
                    worldline_id=worldline.id,
                    agenda_id=_uuid_or_none(item.payload.get("agenda_id")),
                    title=item.title,
                    reason=str(item.payload.get("reason") or f"Matched GM rule {item.rule_key}."),
                    event_name=str(item.payload.get("event_name") or "gm.macro_proposal"),
                    proposed_payload=_dict_or_empty(item.payload.get("proposed_payload")),
                    importance=str(item.payload.get("importance") or "daily"),
                    risk_score=_bounded_percent(_optional_int(item.payload.get("risk_score")) or 0),
                    affected_agents=_list_of_strings(item.payload.get("affected_agents")),
                    affected_organizations=_list_of_strings(
                        item.payload.get("affected_organizations")
                    ),
                    source_context=item.source_context,
                )
                proposal_ids.append(proposal.id)
                continue
            if item.item_kind == "offscreen_event":
                due_at = _datetime_or_now(item.payload.get("due_at"))
                offscreen = OffscreenEventQueueItem(
                    id=uuid.uuid4(),
                    world_id=world_id,
                    worldline_id=worldline.id,
                    event_name=str(item.payload.get("event_name") or "gm.offscreen_event"),
                    title=item.title,
                    payload_json={
                        **_dict_or_empty(item.payload.get("payload")),
                        "source_context": item.source_context,
                        "actor_ref": actor_ref,
                    },
                    due_at=due_at,
                    importance=str(item.payload.get("importance") or "daily"),
                    status="pending",
                )
                self._session.add(offscreen)
                self._session.flush()
                offscreen_event_ids.append(offscreen.id)
        self._session.flush()
        return GMMacroExecutionResult(
            proposal_count=len(proposal_ids),
            offscreen_event_count=len(offscreen_event_ids),
            proposal_ids=proposal_ids,
            offscreen_event_ids=offscreen_event_ids,
        )

    def create_daily_draft_from_low_risk_proposal(
        self,
        *,
        world_id: uuid.UUID,
        proposal_id: uuid.UUID,
    ) -> SceneBeatDraft | DailyEpisodeDraft:
        proposal = self._proposal_or_404(world_id, proposal_id)
        if proposal.worldline_id is None:
            raise ValueError("proposal worldline is required")
        if proposal.risk_score > 25 or proposal.importance != "daily":
            raise ValueError("only low-risk daily proposals can become deterministic drafts")
        payload = proposal.proposed_payload or {}
        participant_agent_ids = _list_of_strings(payload.get("participant_agent_ids"))
        scene_id = _uuid_or_none(payload.get("scene_id"))
        candidate_id = _uuid_or_none(payload.get("source_candidate_id"))
        plot_service = LivingWorldPlotService(self._session)
        if candidate_id is not None:
            return plot_service.generate_daily_episode(
                world_id=world_id,
                worldline_id=proposal.worldline_id,
                source_candidate_id=candidate_id,
                title=proposal.title,
                metadata={
                    "source": "gm_low_risk_proposal",
                    "proposal_id": str(proposal.id),
                },
            )
        return plot_service.compose_scene_beat(
            world_id=world_id,
            worldline_id=proposal.worldline_id,
            source_kind="proposal",
            source_ref=str(proposal.id),
            title=proposal.title,
            participant_agent_ids=participant_agent_ids,
            scene_id=scene_id,
            metadata={
                "source": "gm_low_risk_proposal",
                "proposal_id": str(proposal.id),
                "importance": proposal.importance,
            },
        )

    def choice_consequence_preview(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        effects: dict[str, Any],
    ) -> ChoiceConsequencePreview:
        self.worldline_or_404(world_id, worldline_id)
        relationship_updates = _list_of_dicts(effects.get("relationship_updates"))
        faction_updates = _list_of_dicts(effects.get("faction_updates"))
        offscreen_events = _list_of_dicts(effects.get("offscreen_events"))
        diagnostics = [
            f"{len(relationship_updates)} relationship update(s)",
            f"{len(faction_updates)} faction update(s)",
            f"{len(offscreen_events)} offscreen event(s)",
        ]
        return ChoiceConsequencePreview(
            relationship_updates=relationship_updates,
            faction_updates=faction_updates,
            offscreen_events=offscreen_events,
            diagnostics=diagnostics,
        )

    def apply_choice_consequences(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        player_actor: PlayerActorProfile,
        choice: PlayerChoiceRecord,
        effects: dict[str, Any],
        actor_ref: str,
    ) -> ChoiceConsequencePreview:
        worldline = self.worldline_or_404(world_id, worldline_id)
        preview = self.choice_consequence_preview(
            world_id=world_id,
            worldline_id=worldline.id,
            effects=effects,
        )
        for update in preview.relationship_updates:
            relationship_id = _uuid_or_none(update.get("relationship_id"))
            if relationship_id is None:
                continue
            relationship = self._session.get(AgentRelationshipEdge, relationship_id)
            if (
                relationship is None
                or relationship.world_id != world_id
                or relationship.worldline_id != worldline.id
            ):
                continue
            for field in (
                "affection",
                "trust",
                "hostility",
                "intimacy",
                "obligation",
                "rivalry",
                "debt",
            ):
                delta = _optional_int(update.get(f"{field}_delta"))
                if delta is not None:
                    current = int(getattr(relationship, field))
                    setattr(relationship, field, _bounded_score(field, current + delta))
        for update in preview.faction_updates:
            track_id = _uuid_or_none(update.get("track_id"))
            if track_id is None:
                continue
            track = self._session.get(FactionProgressTrack, track_id)
            if track is None or track.world_id != world_id or track.worldline_id != worldline.id:
                continue
            track.progress = _bounded_percent(
                track.progress + (_optional_int(update.get("progress_delta")) or 0)
            )
            track.pressure = _bounded_percent(
                track.pressure + (_optional_int(update.get("pressure_delta")) or 0)
            )
        for queued in preview.offscreen_events:
            title = str(queued.get("title") or "Player consequence")
            event_name = str(queued.get("event_name") or "player.choice_consequence")
            payload = queued.get("payload")
            self._session.add(
                OffscreenEventQueueItem(
                    id=uuid.uuid4(),
                    world_id=world_id,
                    worldline_id=worldline.id,
                    event_name=event_name,
                    title=title,
                    payload_json=dict(payload) if isinstance(payload, dict) else {},
                    due_at=datetime.now(UTC),
                    importance=str(queued.get("importance") or "relationship"),
                    status="pending",
                ),
            )
        self._session.flush()
        return preview

    def _append_choice_recorded_event(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        player_actor: PlayerActorProfile,
        choice: PlayerChoiceRecord,
        actor_ref: str,
    ) -> WorldEventRecord:
        return WorldEventStore(self._session).append_event(
            WorldEventAppend(
                world_id=world_id,
                worldline_id=worldline_id,
                event_name="player.choice_recorded",
                payload={
                    "choice_id": str(choice.id),
                    "player_actor_id": str(player_actor.id),
                    "choice_key": choice.choice_key,
                    "selected_option": choice.selected_option,
                    "consequences": choice.consequence_preview,
                },
                importance=WorldEventImportance.ROUTE,
                wall_time=datetime.now(UTC),
                actor_ref=actor_ref,
            ),
        )

    def compare_worldlines(
        self,
        *,
        world_id: uuid.UUID,
        base_worldline_id: uuid.UUID,
        compare_worldline_id: uuid.UUID,
    ) -> WorldlineComparison:
        base = self.worldline_or_404(world_id, base_worldline_id)
        compare = self.worldline_or_404(world_id, compare_worldline_id)
        event_count = len(
            WorldEventStore(self._session).list_events_after(
                world_id,
                0,
                worldline_id=compare.id,
            ),
        )
        relationship_delta_count = self._relationship_delta_count(
            world_id=world_id,
            base_worldline_id=base.id,
            compare_worldline_id=compare.id,
        )
        faction_delta_count = self._faction_delta_count(
            world_id=world_id,
            base_worldline_id=base.id,
            compare_worldline_id=compare.id,
        )
        choice_delta_count = len(
            [
                choice_id
                for choice_id, context in self._session.execute(
                    select(PlayerChoiceRecord.id, PlayerChoiceRecord.context_json).where(
                        PlayerChoiceRecord.world_id == world_id,
                        PlayerChoiceRecord.worldline_id == compare.id,
                    ),
                ).all()
                if not isinstance(context, dict) or "forked_from_choice_id" not in context
            ],
        )
        return WorldlineComparison(
            base_worldline_id=base.id,
            compare_worldline_id=compare.id,
            fork_event_sequence=compare.fork_event_sequence,
            divergent_event_count=event_count,
            relationship_delta_count=relationship_delta_count,
            faction_delta_count=faction_delta_count,
            choice_delta_count=choice_delta_count,
        )

    def _proposal_or_404(self, world_id: uuid.UUID, proposal_id: uuid.UUID) -> GMEventProposal:
        proposal = self._session.get(GMEventProposal, proposal_id)
        if proposal is None or proposal.world_id != world_id:
            raise ValueError("proposal not found")
        return proposal

    def _copy_worldline_state(
        self,
        *,
        world_id: uuid.UUID,
        source: Worldline,
        target: Worldline,
    ) -> None:
        for agenda in self._session.scalars(
            select(GMAgenda).where(
                GMAgenda.world_id == world_id,
                GMAgenda.worldline_id == source.id,
            ),
        ).all():
            self._session.add(
                GMAgenda(
                    id=uuid.uuid4(),
                    world_id=world_id,
                    worldline_id=target.id,
                    title=agenda.title,
                    summary=agenda.summary,
                    priority=agenda.priority,
                    status=agenda.status,
                    focus_agents=agenda.focus_agents,
                    focus_organizations=agenda.focus_organizations,
                    metadata_json={**agenda.metadata_json, "forked_from_agenda_id": str(agenda.id)},
                ),
            )
        for proposal in self._session.scalars(
            select(GMEventProposal).where(
                GMEventProposal.world_id == world_id,
                GMEventProposal.worldline_id == source.id,
                GMEventProposal.status.in_(["proposed", "accepted"]),
            ),
        ).all():
            self._session.add(
                GMEventProposal(
                    id=uuid.uuid4(),
                    world_id=world_id,
                    worldline_id=target.id,
                    agenda_id=None,
                    title=proposal.title,
                    reason=proposal.reason,
                    event_name=proposal.event_name,
                    proposed_payload=proposal.proposed_payload,
                    importance=proposal.importance,
                    risk_score=proposal.risk_score,
                    affected_agents=proposal.affected_agents,
                    affected_organizations=proposal.affected_organizations,
                    source_context={
                        **proposal.source_context,
                        "forked_from_proposal_id": str(proposal.id),
                    },
                    status=proposal.status,
                    review_note=proposal.review_note,
                ),
            )
        self._copy_player_actors(world_id=world_id, source=source, target=target)
        self._copy_relationships(world_id=world_id, source=source, target=target)
        self._copy_faction_tracks(world_id=world_id, source=source, target=target)
        self._copy_presence_states(world_id=world_id, source=source, target=target)
        self._copy_pending_autonomous_state(world_id=world_id, source=source, target=target)
        self._copy_plot_route_rumor_state(world_id=world_id, source=source, target=target)

    def _copy_player_actors(
        self,
        *,
        world_id: uuid.UUID,
        source: Worldline,
        target: Worldline,
    ) -> None:
        actor_id_map: dict[uuid.UUID, uuid.UUID] = {}
        for actor in self._session.scalars(
            select(PlayerActorProfile).where(
                PlayerActorProfile.world_id == world_id,
                PlayerActorProfile.worldline_id == source.id,
            ),
        ).all():
            copied = PlayerActorProfile(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=target.id,
                user_id=actor.user_id,
                actor_ref=f"player:{actor.user_id}:{target.worldline_key}",
                display_name=actor.display_name,
                current_scene_id=actor.current_scene_id,
                profile_json={**actor.profile_json, "forked_from_actor_id": str(actor.id)},
                is_active=actor.is_active,
            )
            actor_id_map[actor.id] = copied.id
            self._session.add(copied)
        self._session.flush()
        for choice in self._session.scalars(
            select(PlayerChoiceRecord).where(
                PlayerChoiceRecord.world_id == world_id,
                PlayerChoiceRecord.worldline_id == source.id,
            ),
        ).all():
            copied_actor_id = actor_id_map.get(choice.player_actor_id)
            if copied_actor_id is None:
                continue
            self._session.add(
                PlayerChoiceRecord(
                    id=uuid.uuid4(),
                    world_id=world_id,
                    worldline_id=target.id,
                    user_id=choice.user_id,
                    player_actor_id=copied_actor_id,
                    choice_key=choice.choice_key,
                    choice_kind=choice.choice_kind,
                    prompt=choice.prompt,
                    selected_option=choice.selected_option,
                    context_json={
                        **choice.context_json,
                        "forked_from_choice_id": str(choice.id),
                    },
                    consequence_preview=choice.consequence_preview,
                ),
            )

    def _copy_plot_route_rumor_state(
        self,
        *,
        world_id: uuid.UUID,
        source: Worldline,
        target: Worldline,
    ) -> None:
        hook_id_map: dict[uuid.UUID, uuid.UUID] = {}
        for hook in self._session.scalars(
            select(StoryHook).where(
                StoryHook.world_id == world_id,
                StoryHook.worldline_id == source.id,
                StoryHook.status == "open",
            ),
        ).all():
            copied = StoryHook(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=target.id,
                hook_key=hook.hook_key,
                title=hook.title,
                hook_type=hook.hook_type,
                summary=hook.summary,
                status=hook.status,
                priority=hook.priority,
                owner_agent_id=hook.owner_agent_id,
                target_agent_id=hook.target_agent_id,
                source_event_id=hook.source_event_id,
                due_at=hook.due_at,
                resolution=hook.resolution,
                metadata_json={**hook.metadata_json, "forked_from_hook_id": str(hook.id)},
            )
            hook_id_map[hook.id] = copied.id
            self._session.add(copied)
        for thread in self._session.scalars(
            select(PlotThread).where(
                PlotThread.world_id == world_id,
                PlotThread.worldline_id == source.id,
                PlotThread.status.in_(["active", "dormant"]),
            ),
        ).all():
            self._session.add(
                PlotThread(
                    id=uuid.uuid4(),
                    world_id=world_id,
                    worldline_id=target.id,
                    thread_key=thread.thread_key,
                    title=thread.title,
                    thread_type=thread.thread_type,
                    status=thread.status,
                    summary=thread.summary,
                    stakes=thread.stakes,
                    next_beats=thread.next_beats,
                    participant_agent_ids=thread.participant_agent_ids,
                    organization_ids=thread.organization_ids,
                    related_event_ids=thread.related_event_ids,
                    priority=thread.priority,
                    metadata_json={
                        **thread.metadata_json,
                        "forked_from_thread_id": str(thread.id),
                    },
                ),
            )
        for route in self._session.scalars(
            select(RouteAffinity).where(
                RouteAffinity.world_id == world_id,
                RouteAffinity.worldline_id == source.id,
            ),
        ).all():
            self._session.add(
                RouteAffinity(
                    id=uuid.uuid4(),
                    world_id=world_id,
                    worldline_id=target.id,
                    agent_id=route.agent_id,
                    route_key=route.route_key,
                    status=route.status,
                    affinity=route.affinity,
                    stage=route.stage,
                    flags=route.flags,
                    last_choice_id=None,
                    metadata_json={**route.metadata_json, "forked_from_route_id": str(route.id)},
                ),
            )
        for beat in self._session.scalars(
            select(SceneBeatDraft).where(
                SceneBeatDraft.world_id == world_id,
                SceneBeatDraft.worldline_id == source.id,
                SceneBeatDraft.status == "draft",
            ),
        ).all():
            self._session.add(
                SceneBeatDraft(
                    id=uuid.uuid4(),
                    world_id=world_id,
                    worldline_id=target.id,
                    source_kind=beat.source_kind,
                    source_ref=beat.source_ref,
                    title=beat.title,
                    setup=beat.setup,
                    dialogue_beats=beat.dialogue_beats,
                    choice_points=beat.choice_points,
                    aftermath=beat.aftermath,
                    participant_agent_ids=beat.participant_agent_ids,
                    scene_id=beat.scene_id,
                    status=beat.status,
                    metadata_json={**beat.metadata_json, "forked_from_beat_id": str(beat.id)},
                ),
            )
        self._copy_open_group_suggestions_conflicts(world_id=world_id, source=source, target=target)
        self._copy_active_rumors(world_id=world_id, source=source, target=target)

    def _copy_open_group_suggestions_conflicts(
        self,
        *,
        world_id: uuid.UUID,
        source: Worldline,
        target: Worldline,
    ) -> None:
        for context in self._session.scalars(
            select(GroupInteractionContext).where(
                GroupInteractionContext.world_id == world_id,
                GroupInteractionContext.worldline_id == source.id,
                GroupInteractionContext.status.in_(["planned", "active"]),
            ),
        ).all():
            self._session.add(
                GroupInteractionContext(
                    id=uuid.uuid4(),
                    world_id=world_id,
                    worldline_id=target.id,
                    context_key=context.context_key,
                    title=context.title,
                    interaction_type=context.interaction_type,
                    scene_id=context.scene_id,
                    organization_id=context.organization_id,
                    participant_agent_ids=context.participant_agent_ids,
                    participant_roles=context.participant_roles,
                    constraints=context.constraints,
                    status=context.status,
                    metadata_json={
                        **context.metadata_json,
                        "forked_from_context_id": str(context.id),
                    },
                ),
            )
        for suggestion in self._session.scalars(
            select(RelationshipEventSuggestion).where(
                RelationshipEventSuggestion.world_id == world_id,
                RelationshipEventSuggestion.worldline_id == source.id,
                RelationshipEventSuggestion.status == "suggested",
            ),
        ).all():
            self._session.add(
                RelationshipEventSuggestion(
                    id=uuid.uuid4(),
                    world_id=world_id,
                    worldline_id=target.id,
                    relationship_id=None,
                    source_agent_id=suggestion.source_agent_id,
                    target_agent_id=suggestion.target_agent_id,
                    title=suggestion.title,
                    reason=suggestion.reason,
                    suggested_event_name=suggestion.suggested_event_name,
                    score=suggestion.score,
                    status=suggestion.status,
                    metadata_json={
                        **suggestion.metadata_json,
                        "forked_from_suggestion_id": str(suggestion.id),
                    },
                ),
            )
        for conflict in self._session.scalars(
            select(OrganizationConflictEvent).where(
                OrganizationConflictEvent.world_id == world_id,
                OrganizationConflictEvent.worldline_id == source.id,
                OrganizationConflictEvent.status == "proposed",
            ),
        ).all():
            self._session.add(
                OrganizationConflictEvent(
                    id=uuid.uuid4(),
                    world_id=world_id,
                    worldline_id=target.id,
                    organization_id=conflict.organization_id,
                    faction_track_id=None,
                    title=conflict.title,
                    summary=conflict.summary,
                    pressure_delta=conflict.pressure_delta,
                    progress_delta=conflict.progress_delta,
                    status=conflict.status,
                    metadata_json={
                        **conflict.metadata_json,
                        "forked_from_conflict_id": str(conflict.id),
                    },
                ),
            )

    def _copy_active_rumors(
        self,
        *,
        world_id: uuid.UUID,
        source: Worldline,
        target: Worldline,
    ) -> None:
        rumor_id_map: dict[uuid.UUID, uuid.UUID] = {}
        for rumor in self._session.scalars(
            select(RumorRecord).where(
                RumorRecord.world_id == world_id,
                RumorRecord.worldline_id == source.id,
                RumorRecord.status == "active",
            ),
        ).all():
            copied = RumorRecord(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=target.id,
                rumor_key=rumor.rumor_key,
                title=rumor.title,
                content=rumor.content,
                source_agent_id=rumor.source_agent_id,
                source_organization_id=rumor.source_organization_id,
                visibility=rumor.visibility,
                known_agent_ids=rumor.known_agent_ids,
                status=rumor.status,
                metadata_json={**rumor.metadata_json, "forked_from_rumor_id": str(rumor.id)},
            )
            rumor_id_map[rumor.id] = copied.id
            self._session.add(copied)
        self._session.flush()
        for propagation in self._session.scalars(
            select(RumorPropagation).where(
                RumorPropagation.world_id == world_id,
                RumorPropagation.worldline_id == source.id,
                RumorPropagation.status == "pending",
            ),
        ).all():
            copied_rumor_id = rumor_id_map.get(propagation.rumor_id)
            if copied_rumor_id is None:
                continue
            self._session.add(
                RumorPropagation(
                    id=uuid.uuid4(),
                    world_id=world_id,
                    worldline_id=target.id,
                    rumor_id=copied_rumor_id,
                    source_agent_id=propagation.source_agent_id,
                    target_agent_id=propagation.target_agent_id,
                    target_organization_id=propagation.target_organization_id,
                    propagation_reason=propagation.propagation_reason,
                    status="pending",
                    metadata_json={
                        **propagation.metadata_json,
                        "forked_from_propagation_id": str(propagation.id),
                    },
                ),
            )

    def _copy_relationships(
        self,
        *,
        world_id: uuid.UUID,
        source: Worldline,
        target: Worldline,
    ) -> None:
        for edge in self._session.scalars(
            select(AgentRelationshipEdge).where(
                AgentRelationshipEdge.world_id == world_id,
                AgentRelationshipEdge.worldline_id == source.id,
            ),
        ).all():
            self._session.add(
                AgentRelationshipEdge(
                    id=uuid.uuid4(),
                    world_id=world_id,
                    worldline_id=target.id,
                    source_agent_id=edge.source_agent_id,
                    target_agent_id=edge.target_agent_id,
                    relationship_type=edge.relationship_type,
                    affection=edge.affection,
                    trust=edge.trust,
                    hostility=edge.hostility,
                    intimacy=edge.intimacy,
                    obligation=edge.obligation,
                    rivalry=edge.rivalry,
                    debt=edge.debt,
                    metadata_json={
                        **edge.metadata_json,
                        "forked_from_relationship_id": str(edge.id),
                    },
                ),
            )

    def _copy_faction_tracks(
        self,
        *,
        world_id: uuid.UUID,
        source: Worldline,
        target: Worldline,
    ) -> None:
        for track in self._session.scalars(
            select(FactionProgressTrack).where(
                FactionProgressTrack.world_id == world_id,
                FactionProgressTrack.worldline_id == source.id,
            ),
        ).all():
            self._session.add(
                FactionProgressTrack(
                    id=uuid.uuid4(),
                    world_id=world_id,
                    worldline_id=target.id,
                    organization_id=track.organization_id,
                    track_key=track.track_key,
                    name=track.name,
                    track_type=track.track_type,
                    progress=track.progress,
                    pressure=track.pressure,
                    summary=track.summary,
                    metadata_json={
                        **track.metadata_json,
                        "forked_from_track_id": str(track.id),
                    },
                ),
            )

    def _copy_presence_states(
        self,
        *,
        world_id: uuid.UUID,
        source: Worldline,
        target: Worldline,
    ) -> None:
        for presence in self._session.scalars(
            select(AgentPresenceState).where(
                AgentPresenceState.world_id == world_id,
                AgentPresenceState.worldline_id == source.id,
            ),
        ).all():
            self._session.add(
                AgentPresenceState(
                    id=uuid.uuid4(),
                    world_id=world_id,
                    worldline_id=target.id,
                    agent_id=presence.agent_id,
                    current_scene_id=presence.current_scene_id,
                    visibility_status=presence.visibility_status,
                    encounter_eligible=presence.encounter_eligible,
                    scheduled_movement={
                        **presence.scheduled_movement,
                        "forked_from_presence_id": str(presence.id),
                    },
                    last_event_id=presence.last_event_id,
                ),
            )

    def _copy_pending_autonomous_state(
        self,
        *,
        world_id: uuid.UUID,
        source: Worldline,
        target: Worldline,
    ) -> None:
        candidate_id_map: dict[uuid.UUID, uuid.UUID] = {}
        for candidate in self._session.scalars(
            select(DailyLifeEventCandidate).where(
                DailyLifeEventCandidate.world_id == world_id,
                DailyLifeEventCandidate.worldline_id == source.id,
                DailyLifeEventCandidate.status.in_(["candidate", "queued"]),
            ),
        ).all():
            copied = DailyLifeEventCandidate(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=target.id,
                agent_id=candidate.agent_id,
                scene_id=candidate.scene_id,
                title=candidate.title,
                summary=candidate.summary,
                importance=candidate.importance,
                starts_at=candidate.starts_at,
                source_kind=candidate.source_kind,
                source_ref=candidate.source_ref,
                status=candidate.status,
                metadata_json={
                    **candidate.metadata_json,
                    "forked_from_candidate_id": str(candidate.id),
                },
            )
            candidate_id_map[candidate.id] = copied.id
            self._session.add(copied)
        self._session.flush()
        for item in self._session.scalars(
            select(OffscreenEventQueueItem).where(
                OffscreenEventQueueItem.world_id == world_id,
                OffscreenEventQueueItem.worldline_id == source.id,
                OffscreenEventQueueItem.status == "pending",
            ),
        ).all():
            payload = {
                **item.payload_json,
                "forked_from_offscreen_event_id": str(item.id),
            }
            copied_candidate_id = (
                None
                if item.source_candidate_id is None
                else candidate_id_map.get(item.source_candidate_id)
            )
            self._session.add(
                OffscreenEventQueueItem(
                    id=uuid.uuid4(),
                    world_id=world_id,
                    worldline_id=target.id,
                    source_candidate_id=copied_candidate_id,
                    event_name=item.event_name,
                    title=item.title,
                    payload_json=payload,
                    due_at=item.due_at,
                    importance=item.importance,
                    status="pending",
                    last_error=None,
                ),
            )

    def _relationship_delta_count(
        self,
        *,
        world_id: uuid.UUID,
        base_worldline_id: uuid.UUID,
        compare_worldline_id: uuid.UUID,
    ) -> int:
        base_edges = {
            (edge.source_agent_id, edge.target_agent_id, edge.relationship_type): (
                edge.affection,
                edge.trust,
                edge.hostility,
                edge.intimacy,
                edge.obligation,
                edge.rivalry,
                edge.debt,
            )
            for edge in self._session.scalars(
                select(AgentRelationshipEdge).where(
                    AgentRelationshipEdge.world_id == world_id,
                    AgentRelationshipEdge.worldline_id == base_worldline_id,
                ),
            ).all()
        }
        deltas = 0
        for edge in self._session.scalars(
            select(AgentRelationshipEdge).where(
                AgentRelationshipEdge.world_id == world_id,
                AgentRelationshipEdge.worldline_id == compare_worldline_id,
            ),
        ).all():
            key = (edge.source_agent_id, edge.target_agent_id, edge.relationship_type)
            compare_scores = (
                edge.affection,
                edge.trust,
                edge.hostility,
                edge.intimacy,
                edge.obligation,
                edge.rivalry,
                edge.debt,
            )
            if base_edges.get(key) != compare_scores:
                deltas += 1
        return deltas

    def _faction_delta_count(
        self,
        *,
        world_id: uuid.UUID,
        base_worldline_id: uuid.UUID,
        compare_worldline_id: uuid.UUID,
    ) -> int:
        base_tracks = {
            (track.organization_id, track.track_key): (
                track.track_type,
                track.progress,
                track.pressure,
                track.summary,
            )
            for track in self._session.scalars(
                select(FactionProgressTrack).where(
                    FactionProgressTrack.world_id == world_id,
                    FactionProgressTrack.worldline_id == base_worldline_id,
                ),
            ).all()
        }
        deltas = 0
        for track in self._session.scalars(
            select(FactionProgressTrack).where(
                FactionProgressTrack.world_id == world_id,
                FactionProgressTrack.worldline_id == compare_worldline_id,
            ),
        ).all():
            key = (track.organization_id, track.track_key)
            compare_state = (
                track.track_type,
                track.progress,
                track.pressure,
                track.summary,
            )
            if base_tracks.get(key) != compare_state:
                deltas += 1
        return deltas


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


def _datetime_or_now(value: object) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
            return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
        except ValueError:
            return datetime.now(UTC)
    return datetime.now(UTC)


def _dict_or_empty(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list_of_dicts(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _list_of_strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]


def _bounded_percent(value: int) -> int:
    return max(0, min(100, value))


def _bounded_score(field: str, value: int) -> int:
    if field in {"affection", "trust"}:
        return max(-100, min(100, value))
    return _bounded_percent(value)
