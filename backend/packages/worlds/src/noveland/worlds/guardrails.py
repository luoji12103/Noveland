from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from noveland.agents.models import Agent, AgentRelationshipEdge
from noveland.core.settings import AppSettings
from noveland.events import WorldEventAppend, WorldEventImportance, WorldEventStore
from noveland.memory import MemoryService
from noveland.worlds.models import (
    CharacterEmotionalState,
    CharacterKnowledgeFact,
    FactionProgressTrack,
    GMStyleReview,
    InWorldNotification,
    NarrativeContinuityReview,
    PlayerActorProfile,
    PlayerChoiceRecord,
    PlayerInterventionRecord,
    PlayerJournalEntry,
    RelationshipRepairRecord,
    RouteAffinity,
    SecretRecord,
    StoryHook,
    WorldBible,
    Worldline,
)
from noveland.worlds.worldlines import worldline_or_404
from sqlalchemy import select
from sqlalchemy.orm import Session


@dataclass(frozen=True, slots=True)
class LivingWorldDashboard:
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    knowledge_count: int
    hidden_secret_count: int
    emotional_state_count: int
    open_hook_count: int
    unread_notification_count: int
    pending_intervention_count: int
    active_route_count: int
    pressure_summary: dict[str, int]


class LivingWorldGuardrailService:
    def __init__(self, session: Session, settings: AppSettings | None = None) -> None:
        self._session = session
        self._settings = settings or AppSettings()

    def worldline_or_404(self, world_id: uuid.UUID, worldline_id: uuid.UUID | None) -> Worldline:
        return worldline_or_404(self._session, world_id, worldline_id)

    def upsert_knowledge_fact(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        agent_id: uuid.UUID,
        fact_key: str,
        knowledge_kind: str,
        content: str,
        confidence: int,
        visibility: str,
        source_event_id: uuid.UUID | None,
        source_ref: str | None,
        metadata: dict[str, Any],
    ) -> CharacterKnowledgeFact:
        worldline = self.worldline_or_404(world_id, worldline_id)
        fact = self._session.scalars(
            select(CharacterKnowledgeFact).where(
                CharacterKnowledgeFact.world_id == world_id,
                CharacterKnowledgeFact.worldline_id == worldline.id,
                CharacterKnowledgeFact.agent_id == agent_id,
                CharacterKnowledgeFact.fact_key == fact_key,
            ),
        ).one_or_none()
        if fact is None:
            fact = CharacterKnowledgeFact(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline.id,
                agent_id=agent_id,
                fact_key=fact_key,
            )
            self._session.add(fact)
        fact.knowledge_kind = knowledge_kind
        fact.content = content
        fact.confidence = _bounded(confidence, 0, 100)
        fact.visibility = visibility
        fact.source_event_id = source_event_id
        fact.source_ref = source_ref
        fact.metadata_json = metadata
        fact.is_active = True
        self._session.flush()
        return fact

    def list_agent_knowledge(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        agent_id: uuid.UUID | None,
        include_inactive: bool = False,
        limit: int = 100,
    ) -> list[CharacterKnowledgeFact]:
        worldline = self.worldline_or_404(world_id, worldline_id)
        statement = select(CharacterKnowledgeFact).where(
            CharacterKnowledgeFact.world_id == world_id,
            CharacterKnowledgeFact.worldline_id == worldline.id,
        )
        if agent_id is not None:
            statement = statement.where(CharacterKnowledgeFact.agent_id == agent_id)
        if not include_inactive:
            statement = statement.where(CharacterKnowledgeFact.is_active.is_(True))
        return list(
            self._session.scalars(
                statement.order_by(CharacterKnowledgeFact.updated_at.desc()).limit(limit),
            ).all()
        )

    def create_secret(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        secret_key: str,
        title: str,
        content: str,
        holder_agent_ids: list[str],
        reveal_conditions: dict[str, Any],
        consequence_metadata: dict[str, Any],
        visibility: str,
        metadata: dict[str, Any],
    ) -> SecretRecord:
        worldline = self.worldline_or_404(world_id, worldline_id)
        if (
            self._session.scalars(
                select(SecretRecord).where(
                    SecretRecord.world_id == world_id,
                    SecretRecord.worldline_id == worldline.id,
                    SecretRecord.secret_key == secret_key,
                ),
            ).first()
            is not None
        ):
            raise ValueError("secret key already exists")
        secret = SecretRecord(
            id=uuid.uuid4(),
            world_id=world_id,
            worldline_id=worldline.id,
            secret_key=secret_key,
            title=title,
            content=content,
            holder_agent_ids=holder_agent_ids,
            reveal_conditions=reveal_conditions,
            consequence_metadata=consequence_metadata,
            visibility=visibility,
            status="hidden",
            metadata_json=metadata,
        )
        self._session.add(secret)
        self._session.flush()
        return secret

    def reveal_secret(
        self,
        *,
        world_id: uuid.UUID,
        secret_id: uuid.UUID,
        actor_ref: str,
    ) -> SecretRecord:
        secret = self._secret_or_404(world_id, secret_id)
        event = WorldEventStore(self._session).append_event(
            WorldEventAppend(
                world_id=secret.world_id,
                worldline_id=secret.worldline_id,
                event_name="secret.revealed",
                payload={
                    "secret_id": str(secret.id),
                    "secret_key": secret.secret_key,
                    "title": secret.title,
                    "consequence_metadata": secret.consequence_metadata,
                },
                importance=WorldEventImportance.ROUTE,
                wall_time=datetime.now(UTC),
                actor_ref=actor_ref,
            ),
        )
        secret.status = "revealed"
        secret.revealed_event_id = event.id
        for holder_id in secret.holder_agent_ids:
            agent_id = _uuid_or_none(holder_id)
            if agent_id is None:
                continue
            self.upsert_knowledge_fact(
                world_id=world_id,
                worldline_id=secret.worldline_id,
                agent_id=agent_id,
                fact_key=f"secret:{secret.secret_key}",
                knowledge_kind="secret",
                content=secret.content,
                confidence=100,
                visibility="private",
                source_event_id=event.id,
                source_ref=str(secret.id),
                metadata={"secret_id": str(secret.id), "revealed": True},
            )
        self._session.flush()
        return secret

    def upsert_emotional_state(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        agent_id: uuid.UUID,
        mood: str,
        stress: int,
        fatigue: int,
        anticipation: int,
        jealousy: int,
        anger: int,
        source_event_id: uuid.UUID | None,
        expires_at: datetime | None,
        metadata: dict[str, Any],
    ) -> CharacterEmotionalState:
        worldline = self.worldline_or_404(world_id, worldline_id)
        state = self._session.scalars(
            select(CharacterEmotionalState).where(
                CharacterEmotionalState.world_id == world_id,
                CharacterEmotionalState.worldline_id == worldline.id,
                CharacterEmotionalState.agent_id == agent_id,
            ),
        ).one_or_none()
        if state is None:
            state = CharacterEmotionalState(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline.id,
                agent_id=agent_id,
            )
            self._session.add(state)
        state.mood = mood
        state.stress = _bounded(stress, 0, 100)
        state.fatigue = _bounded(fatigue, 0, 100)
        state.anticipation = _bounded(anticipation, 0, 100)
        state.jealousy = _bounded(jealousy, 0, 100)
        state.anger = _bounded(anger, 0, 100)
        state.source_event_id = source_event_id
        state.expires_at = expires_at
        state.metadata_json = metadata
        self._session.flush()
        return state

    def propose_relationship_repair(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        relationship_id: uuid.UUID,
        repair_kind: str,
        reason: str,
        score_delta: dict[str, Any],
        metadata: dict[str, Any],
    ) -> RelationshipRepairRecord:
        worldline = self.worldline_or_404(world_id, worldline_id)
        relationship = self._session.get(AgentRelationshipEdge, relationship_id)
        if (
            relationship is None
            or relationship.world_id != world_id
            or relationship.worldline_id != worldline.id
        ):
            raise ValueError("relationship not found")
        record = RelationshipRepairRecord(
            id=uuid.uuid4(),
            world_id=world_id,
            worldline_id=worldline.id,
            relationship_id=relationship_id,
            repair_kind=repair_kind,
            reason=reason,
            score_delta=score_delta,
            status="proposed",
            metadata_json=metadata,
        )
        self._session.add(record)
        self._session.flush()
        return record

    def apply_relationship_repair(
        self,
        *,
        world_id: uuid.UUID,
        repair_id: uuid.UUID,
        actor_ref: str,
    ) -> RelationshipRepairRecord:
        record = self._relationship_repair_or_404(world_id, repair_id)
        relationship = self._session.get(AgentRelationshipEdge, record.relationship_id)
        if relationship is None or relationship.world_id != world_id:
            raise ValueError("relationship not found")
        for field in (
            "affection",
            "trust",
            "hostility",
            "intimacy",
            "obligation",
            "rivalry",
            "debt",
        ):
            delta = _optional_int(record.score_delta.get(field))
            if delta is None:
                continue
            current = int(getattr(relationship, field))
            setattr(relationship, field, _bounded_relationship_score(field, current + delta))
        event = WorldEventStore(self._session).append_event(
            WorldEventAppend(
                world_id=world_id,
                worldline_id=record.worldline_id,
                event_name="relationship.repair_applied",
                payload={
                    "repair_id": str(record.id),
                    "relationship_id": str(record.relationship_id),
                    "repair_kind": record.repair_kind,
                    "score_delta": record.score_delta,
                },
                importance=WorldEventImportance.RELATIONSHIP,
                wall_time=datetime.now(UTC),
                actor_ref=actor_ref,
            ),
        )
        record.status = "applied"
        record.applied_event_id = event.id
        self._record_relationship_memory(record, relationship, event.id)
        self._session.flush()
        return record

    def create_journal_entry(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        user_id: uuid.UUID,
        player_actor_id: uuid.UUID | None,
        entry_kind: str,
        title: str,
        body: str,
        source_event_id: uuid.UUID | None,
        source_ref: str | None,
        visibility: str,
        metadata: dict[str, Any],
    ) -> PlayerJournalEntry:
        worldline = self.worldline_or_404(world_id, worldline_id)
        entry = PlayerJournalEntry(
            id=uuid.uuid4(),
            world_id=world_id,
            worldline_id=worldline.id,
            user_id=user_id,
            player_actor_id=player_actor_id,
            entry_kind=entry_kind,
            title=title,
            body=body,
            source_event_id=source_event_id,
            source_ref=source_ref,
            visibility=visibility,
            metadata_json=metadata,
        )
        self._session.add(entry)
        self._session.flush()
        return entry

    def create_notification(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        user_id: uuid.UUID,
        notification_kind: str,
        title: str,
        body: str,
        source_event_id: uuid.UUID | None,
        source_ref: str | None,
        metadata: dict[str, Any],
    ) -> InWorldNotification:
        worldline = self.worldline_or_404(world_id, worldline_id)
        notification = InWorldNotification(
            id=uuid.uuid4(),
            world_id=world_id,
            worldline_id=worldline.id,
            user_id=user_id,
            notification_kind=notification_kind,
            title=title,
            body=body,
            source_event_id=source_event_id,
            source_ref=source_ref,
            status="unread",
            metadata_json=metadata,
        )
        self._session.add(notification)
        self._session.flush()
        return notification

    def record_intervention(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        user_id: uuid.UUID,
        player_actor_id: uuid.UUID,
        intervention_kind: str,
        target_agent_id: uuid.UUID | None,
        target_scene_id: uuid.UUID | None,
        prompt: str,
        metadata: dict[str, Any],
        actor_ref: str,
    ) -> PlayerInterventionRecord:
        worldline = self.worldline_or_404(world_id, worldline_id)
        actor = self._session.get(PlayerActorProfile, player_actor_id)
        if actor is None or actor.world_id != world_id or actor.worldline_id != worldline.id:
            raise ValueError("player actor not found")
        event = WorldEventStore(self._session).append_event(
            WorldEventAppend(
                world_id=world_id,
                worldline_id=worldline.id,
                event_name="player.intervention_recorded",
                payload={
                    "player_actor_id": str(player_actor_id),
                    "intervention_kind": intervention_kind,
                    "target_agent_id": None if target_agent_id is None else str(target_agent_id),
                    "target_scene_id": None if target_scene_id is None else str(target_scene_id),
                    "prompt": prompt,
                },
                importance=WorldEventImportance.ROUTE,
                wall_time=datetime.now(UTC),
                actor_ref=actor_ref,
            ),
        )
        choice = PlayerChoiceRecord(
            id=uuid.uuid4(),
            world_id=world_id,
            worldline_id=worldline.id,
            user_id=user_id,
            player_actor_id=player_actor_id,
            choice_key=f"intervention-{event.sequence}",
            choice_kind="intervention",
            prompt=prompt,
            selected_option=intervention_kind,
            context_json={
                "intervention_kind": intervention_kind,
                "event_id": str(event.id),
            },
            consequence_preview={"diagnostics": ["intervention recorded"]},
            applied_event_id=event.id,
        )
        self._session.add(choice)
        intervention = PlayerInterventionRecord(
            id=uuid.uuid4(),
            world_id=world_id,
            worldline_id=worldline.id,
            user_id=user_id,
            player_actor_id=player_actor_id,
            intervention_kind=intervention_kind,
            target_agent_id=target_agent_id,
            target_scene_id=target_scene_id,
            prompt=prompt,
            choice_id=choice.id,
            event_id=event.id,
            status="recorded",
            metadata_json=metadata,
        )
        self._session.add(intervention)
        self.create_journal_entry(
            world_id=world_id,
            worldline_id=worldline.id,
            user_id=user_id,
            player_actor_id=player_actor_id,
            entry_kind="choice",
            title=f"Intervention: {intervention_kind}",
            body=prompt,
            source_event_id=event.id,
            source_ref=str(intervention.id),
            visibility="player_private",
            metadata={"intervention_id": str(intervention.id)},
        )
        self._session.flush()
        return intervention

    def review_gm_style(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        source_kind: str,
        source_ref: str | None,
        reviewed_text: str,
        metadata: dict[str, Any],
    ) -> GMStyleReview:
        worldline = self.worldline_or_404(world_id, worldline_id)
        diagnostics = _style_diagnostics(reviewed_text, metadata)
        review = GMStyleReview(
            id=uuid.uuid4(),
            world_id=world_id,
            worldline_id=worldline.id,
            source_kind=source_kind,
            source_ref=source_ref,
            reviewed_text=reviewed_text,
            status=_review_status(diagnostics),
            diagnostics=diagnostics,
            metadata_json=metadata,
        )
        self._session.add(review)
        self._session.flush()
        return review

    def review_narrative_continuity(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        artifact_id: uuid.UUID | None,
        source_kind: str,
        source_ref: str | None,
        reviewed_text: str,
        metadata: dict[str, Any],
    ) -> NarrativeContinuityReview:
        worldline = self.worldline_or_404(world_id, worldline_id)
        issues = self._continuity_issues(world_id, worldline.id, reviewed_text, metadata)
        review = NarrativeContinuityReview(
            id=uuid.uuid4(),
            world_id=world_id,
            worldline_id=worldline.id,
            artifact_id=artifact_id,
            source_kind=source_kind,
            source_ref=source_ref,
            reviewed_text=reviewed_text,
            status=_review_status(issues),
            issues=issues,
            metadata_json=metadata,
        )
        self._session.add(review)
        self._session.flush()
        return review

    def dashboard(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        user_id: uuid.UUID | None = None,
    ) -> LivingWorldDashboard:
        worldline = self.worldline_or_404(world_id, worldline_id)
        pressure_rows = self._session.scalars(
            select(FactionProgressTrack).where(
                FactionProgressTrack.world_id == world_id,
                FactionProgressTrack.worldline_id == worldline.id,
            ),
        ).all()
        pressure_summary = {
            "track_count": len(pressure_rows),
            "max_pressure": max((track.pressure for track in pressure_rows), default=0),
            "max_progress": max((track.progress for track in pressure_rows), default=0),
        }
        notification_query = select(InWorldNotification).where(
            InWorldNotification.world_id == world_id,
            InWorldNotification.worldline_id == worldline.id,
            InWorldNotification.status == "unread",
        )
        if user_id is not None:
            notification_query = notification_query.where(InWorldNotification.user_id == user_id)
        return LivingWorldDashboard(
            world_id=world_id,
            worldline_id=worldline.id,
            knowledge_count=_count(
                self._session,
                select(CharacterKnowledgeFact.id).where(
                    CharacterKnowledgeFact.world_id == world_id,
                    CharacterKnowledgeFact.worldline_id == worldline.id,
                    CharacterKnowledgeFact.is_active.is_(True),
                ),
            ),
            hidden_secret_count=_count(
                self._session,
                select(SecretRecord.id).where(
                    SecretRecord.world_id == world_id,
                    SecretRecord.worldline_id == worldline.id,
                    SecretRecord.status == "hidden",
                ),
            ),
            emotional_state_count=_count(
                self._session,
                select(CharacterEmotionalState.id).where(
                    CharacterEmotionalState.world_id == world_id,
                    CharacterEmotionalState.worldline_id == worldline.id,
                ),
            ),
            open_hook_count=_count(
                self._session,
                select(StoryHook.id).where(
                    StoryHook.world_id == world_id,
                    StoryHook.worldline_id == worldline.id,
                    StoryHook.status == "open",
                ),
            ),
            unread_notification_count=_count(self._session, notification_query),
            pending_intervention_count=_count(
                self._session,
                select(PlayerInterventionRecord.id).where(
                    PlayerInterventionRecord.world_id == world_id,
                    PlayerInterventionRecord.worldline_id == worldline.id,
                    PlayerInterventionRecord.status == "recorded",
                ),
            ),
            active_route_count=_count(
                self._session,
                select(RouteAffinity.id).where(
                    RouteAffinity.world_id == world_id,
                    RouteAffinity.worldline_id == worldline.id,
                    RouteAffinity.status == "active",
                ),
            ),
            pressure_summary=pressure_summary,
        )

    def _secret_or_404(self, world_id: uuid.UUID, secret_id: uuid.UUID) -> SecretRecord:
        secret = self._session.get(SecretRecord, secret_id)
        if secret is None or secret.world_id != world_id:
            raise ValueError("secret not found")
        return secret

    def _relationship_repair_or_404(
        self, world_id: uuid.UUID, repair_id: uuid.UUID
    ) -> RelationshipRepairRecord:
        record = self._session.get(RelationshipRepairRecord, repair_id)
        if record is None or record.world_id != world_id:
            raise ValueError("relationship repair not found")
        return record

    def _continuity_issues(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        reviewed_text: str,
        metadata: dict[str, Any],
    ) -> list[dict[str, Any]]:
        issues = _continuity_text_issues(reviewed_text)
        bible = self._session.scalars(
            select(WorldBible).where(WorldBible.world_id == world_id),
        ).one_or_none()
        if bible is not None:
            forbidden = [
                str(item.get("label") or item.get("text") or item)
                for item in bible.forbidden_changes
            ]
            for rule in forbidden:
                if rule and rule.lower() in reviewed_text.lower():
                    issues.append(
                        {
                            "severity": "warning",
                            "code": "forbidden_change",
                            "message": f"Text appears to touch forbidden change: {rule}",
                        }
                    )
            if bible.source_material and "canon" not in metadata:
                issues.append(
                    {
                        "severity": "info",
                        "code": "canon_context_available",
                        "message": "World bible canon context is available for review.",
                    }
                )
        open_hooks = self._session.scalars(
            select(StoryHook).where(
                StoryHook.world_id == world_id,
                StoryHook.worldline_id == worldline_id,
                StoryHook.status == "open",
            ),
        ).all()
        if open_hooks and not any(hook.hook_key in reviewed_text for hook in open_hooks):
            issues.append(
                {
                    "severity": "info",
                    "code": "unresolved_hooks_available",
                    "message": (
                        f"{len(open_hooks)} unresolved hook(s) are available for continuity checks."
                    ),
                }
            )
        return issues

    def _record_relationship_memory(
        self,
        record: RelationshipRepairRecord,
        relationship: AgentRelationshipEdge,
        event_id: uuid.UUID,
    ) -> None:
        source_agent = self._session.get(Agent, relationship.source_agent_id)
        target_agent = self._session.get(Agent, relationship.target_agent_id)
        if source_agent is None or target_agent is None:
            return
        summary = (
            f"{source_agent.display_name} and {target_agent.display_name} relationship "
            f"changed through {record.repair_kind}: affection {relationship.affection}, "
            f"trust {relationship.trust}, hostility {relationship.hostility}, "
            f"intimacy {relationship.intimacy}, obligation {relationship.obligation}, "
            f"rivalry {relationship.rivalry}, debt {relationship.debt}."
        )
        MemoryService(self._session, self._settings).record_relationship_change(
            world_id=record.world_id,
            worldline_id=record.worldline_id,
            source_agent_id=relationship.source_agent_id,
            target_agent_id=relationship.target_agent_id,
            relationship_id=relationship.id,
            relationship_type=relationship.relationship_type,
            summary=summary,
            metadata={
                "source": "relationship_repair",
                "repair_id": str(record.id),
                "source_event_id": str(event_id),
            },
            dedupe_suffix=f"repair:{record.id}:{event_id}",
        )


def _style_diagnostics(reviewed_text: str, metadata: dict[str, Any]) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    lowered = reviewed_text.lower()
    if not any(token in lowered for token in ("scene", "choice", "after school", "daily", "route")):
        diagnostics.append(
            {
                "severity": "warning",
                "code": "galgame_style_weak",
                "message": (
                    "Text does not clearly signal scene, choice, daily-life, or route structure."
                ),
            }
        )
    if any(token in lowered for token in ("as an ai", "language model", "chatbot")):
        diagnostics.append(
            {
                "severity": "warning",
                "code": "generic_chatbot_drift",
                "message": "Text appears to drift toward generic chatbot framing.",
            }
        )
    if "continuity" not in metadata:
        diagnostics.append(
            {
                "severity": "info",
                "code": "continuity_context_missing",
                "message": "No explicit continuity context was provided for this review.",
            }
        )
    return diagnostics


def _continuity_text_issues(reviewed_text: str) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    lowered = reviewed_text.lower()
    if "out of character" in lowered or "ooc" in lowered:
        issues.append(
            {
                "severity": "warning",
                "code": "ooc_marker",
                "message": "Text contains an OOC marker.",
            }
        )
    if "everyone knows" in lowered or "all characters know" in lowered:
        issues.append(
            {
                "severity": "warning",
                "code": "knowledge_leak_risk",
                "message": "Text may leak knowledge globally.",
            }
        )
    if "time paradox" in lowered or "same time" in lowered:
        issues.append(
            {
                "severity": "warning",
                "code": "time_contradiction_risk",
                "message": "Text may contain a time contradiction.",
            }
        )
    return issues


def _review_status(items: list[dict[str, Any]]) -> str:
    if any(item.get("severity") == "error" for item in items):
        return "fail"
    if any(item.get("severity") == "warning" for item in items):
        return "warning"
    return "pass"


def _bounded(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def _bounded_relationship_score(field: str, value: int) -> int:
    if field in {"affection", "trust"}:
        return _bounded(value, -100, 100)
    return _bounded(value, 0, 100)


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


def _count(session: Session, statement: Any) -> int:
    return len(session.scalars(statement).all())
