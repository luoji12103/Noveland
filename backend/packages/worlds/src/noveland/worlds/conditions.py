from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from noveland.agents.models import AgentRelationshipEdge
from noveland.worlds.models import (
    AgentPresenceState,
    CharacterKnowledgeFact,
    FactionProgressTrack,
    GMEventProposal,
    PlayerChoiceRecord,
    PlotThread,
    RouteAffinity,
    RouteMilestone,
    SecretRecord,
    StoryHook,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session


@dataclass(frozen=True, slots=True)
class ConditionEvaluationResult:
    matched: bool
    satisfied: list[str]
    unsatisfied: list[str]
    evidence: dict[str, Any]


def evaluate_world_conditions(
    session: Session,
    *,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    conditions: dict[str, Any],
    route_affinity_id: uuid.UUID | None = None,
    plot_thread_id: uuid.UUID | None = None,
    now: datetime | None = None,
) -> ConditionEvaluationResult:
    satisfied: list[str] = []
    unsatisfied: list[str] = []
    evidence: dict[str, Any] = {}
    current_time = _utc(now)
    if not conditions:
        satisfied.append("No conditions configured.")
        return ConditionEvaluationResult(
            matched=True,
            satisfied=satisfied,
            unsatisfied=unsatisfied,
            evidence={"evaluated_at": current_time.isoformat()},
        )

    min_open_hooks = _optional_int(conditions.get("min_open_hooks"))
    if min_open_hooks is not None:
        count = _count(
            session,
            select(func.count(StoryHook.id)).where(
                StoryHook.world_id == world_id,
                StoryHook.worldline_id == worldline_id,
                StoryHook.status == "open",
            ),
        )
        evidence["open_hook_count"] = count
        _record_threshold("open hooks", count, min_open_hooks, satisfied, unsatisfied)

    hook_type = _optional_str(conditions.get("hook_type"))
    if hook_type:
        count = _count(
            session,
            select(func.count(StoryHook.id)).where(
                StoryHook.world_id == world_id,
                StoryHook.worldline_id == worldline_id,
                StoryHook.status == "open",
                StoryHook.hook_type == hook_type,
            ),
        )
        evidence["open_hook_type_count"] = count
        if count <= 0:
            unsatisfied.append(f"no open {hook_type} hook.")
        else:
            satisfied.append(f"open {hook_type} hook exists.")

    hook_due_before_now = _optional_bool(conditions.get("hook_due_before_now"))
    if hook_due_before_now:
        count = _count(
            session,
            select(func.count(StoryHook.id)).where(
                StoryHook.world_id == world_id,
                StoryHook.worldline_id == worldline_id,
                StoryHook.status == "open",
                StoryHook.due_at.is_not(None),
                StoryHook.due_at <= current_time,
            ),
        )
        evidence["overdue_open_hook_count"] = count
        if count <= 0:
            unsatisfied.append("no overdue open hook.")
        else:
            satisfied.append("overdue open hook exists.")

    time_window = conditions.get("time_window")
    if isinstance(time_window, dict):
        start = _datetime_or_none(time_window.get("start"))
        end = _datetime_or_none(time_window.get("end"))
        evidence["time_window"] = {
            "now": current_time.isoformat(),
            "start": None if start is None else start.isoformat(),
            "end": None if end is None else end.isoformat(),
        }
        if (start is None or current_time >= start) and (end is None or current_time <= end):
            satisfied.append("time window is active.")
        else:
            unsatisfied.append("time window is not active.")

    min_route_affinity = _optional_int(conditions.get("min_route_affinity"))
    if min_route_affinity is not None:
        route = _route_for_conditions(
            session,
            world_id,
            worldline_id,
            conditions,
            route_affinity_id,
        )
        value = None if route is None else route.affinity
        evidence["route_affinity"] = value
        _record_threshold("route affinity", value, min_route_affinity, satisfied, unsatisfied)

    min_route_stage = _optional_int(conditions.get("min_route_stage"))
    if min_route_stage is not None:
        route = _route_for_conditions(
            session,
            world_id,
            worldline_id,
            conditions,
            route_affinity_id,
        )
        value = None if route is None else route.stage
        evidence["route_stage"] = value
        _record_threshold("route stage", value, min_route_stage, satisfied, unsatisfied)

    required_flags = _list_of_strings(conditions.get("required_flags"))
    if required_flags:
        route = _route_for_conditions(
            session,
            world_id,
            worldline_id,
            conditions,
            route_affinity_id,
        )
        route_flags = set() if route is None else set(route.flags)
        missing = sorted(set(required_flags) - route_flags)
        evidence["required_flags_missing"] = missing
        if missing:
            unsatisfied.append(f"route flags missing: {', '.join(missing)}.")
        else:
            satisfied.append("required route flags are present.")

    plot_thread_status = _optional_str(conditions.get("plot_thread_status"))
    if plot_thread_status:
        thread = _plot_thread_for_conditions(
            session,
            world_id,
            worldline_id,
            conditions,
            plot_thread_id,
        )
        thread_status = None if thread is None else thread.status
        evidence["plot_thread_status"] = thread_status
        if thread_status != plot_thread_status:
            unsatisfied.append(f"plot thread status is not {plot_thread_status}.")
        else:
            satisfied.append(f"plot thread status is {plot_thread_status}.")

    min_completed_milestones = _optional_int(conditions.get("min_completed_milestones"))
    if min_completed_milestones is not None:
        statement = select(func.count(RouteMilestone.id)).where(
            RouteMilestone.world_id == world_id,
            RouteMilestone.worldline_id == worldline_id,
            RouteMilestone.status == "completed",
        )
        if route_affinity_id is not None:
            statement = statement.where(RouteMilestone.route_affinity_id == route_affinity_id)
        if plot_thread_id is not None:
            statement = statement.where(RouteMilestone.plot_thread_id == plot_thread_id)
        count = _count(session, statement)
        evidence["completed_milestone_count"] = count
        _record_threshold(
            "completed milestones",
            count,
            min_completed_milestones,
            satisfied,
            unsatisfied,
        )

    min_relationship_tension = _optional_int(conditions.get("min_relationship_tension"))
    if min_relationship_tension is not None:
        relationship = session.scalars(
            select(AgentRelationshipEdge)
            .where(
                AgentRelationshipEdge.world_id == world_id,
                AgentRelationshipEdge.worldline_id == worldline_id,
            )
            .order_by(AgentRelationshipEdge.hostility.desc(), AgentRelationshipEdge.rivalry.desc())
        ).first()
        value = None if relationship is None else max(relationship.hostility, relationship.rivalry)
        evidence["relationship_tension"] = value
        _record_threshold(
            "relationship tension",
            value,
            min_relationship_tension,
            satisfied,
            unsatisfied,
        )

    min_relationship_trust = _optional_int(conditions.get("min_relationship_trust"))
    if min_relationship_trust is not None:
        relationship = session.scalars(
            select(AgentRelationshipEdge)
            .where(
                AgentRelationshipEdge.world_id == world_id,
                AgentRelationshipEdge.worldline_id == worldline_id,
            )
            .order_by(AgentRelationshipEdge.trust.desc())
        ).first()
        value = None if relationship is None else relationship.trust
        evidence["relationship_trust"] = value
        _record_threshold(
            "relationship trust",
            value,
            min_relationship_trust,
            satisfied,
            unsatisfied,
        )

    min_pending_proposals = _optional_int(conditions.get("min_pending_proposals"))
    if min_pending_proposals is not None:
        count = _count(
            session,
            select(func.count(GMEventProposal.id)).where(
                GMEventProposal.world_id == world_id,
                GMEventProposal.worldline_id == worldline_id,
                GMEventProposal.status == "proposed",
            ),
        )
        evidence["pending_proposal_count"] = count
        _record_threshold("pending proposals", count, min_pending_proposals, satisfied, unsatisfied)

    min_faction_pressure = _optional_int(conditions.get("min_faction_pressure"))
    if min_faction_pressure is not None:
        track = session.scalars(
            select(FactionProgressTrack)
            .where(
                FactionProgressTrack.world_id == world_id,
                FactionProgressTrack.worldline_id == worldline_id,
            )
            .order_by(FactionProgressTrack.pressure.desc())
        ).first()
        value = None if track is None else track.pressure
        evidence["faction_pressure"] = value
        _record_threshold("faction pressure", value, min_faction_pressure, satisfied, unsatisfied)

    required_scene_id = _uuid_or_none(conditions.get("scene_id"))
    if required_scene_id is not None:
        presence_count = _count(
            session,
            select(func.count(AgentPresenceState.id)).where(
                AgentPresenceState.world_id == world_id,
                AgentPresenceState.worldline_id == worldline_id,
                AgentPresenceState.current_scene_id == required_scene_id,
            ),
        )
        evidence["scene_presence_count"] = presence_count
        if presence_count <= 0:
            unsatisfied.append("No eligible agent is present at the required scene.")
        else:
            satisfied.append("At least one agent is present at the required scene.")

    min_player_choices = _optional_int(conditions.get("min_player_choices"))
    if min_player_choices is not None:
        count = _count(
            session,
            select(func.count(PlayerChoiceRecord.id)).where(
                PlayerChoiceRecord.world_id == world_id,
                PlayerChoiceRecord.worldline_id == worldline_id,
            ),
        )
        evidence["player_choice_count"] = count
        _record_threshold("player choices", count, min_player_choices, satisfied, unsatisfied)

    min_known_facts = _optional_int(conditions.get("min_known_facts"))
    if min_known_facts is not None:
        count = _count(
            session,
            select(func.count(CharacterKnowledgeFact.id)).where(
                CharacterKnowledgeFact.world_id == world_id,
                CharacterKnowledgeFact.worldline_id == worldline_id,
                CharacterKnowledgeFact.is_active.is_(True),
            ),
        )
        evidence["known_fact_count"] = count
        _record_threshold("known facts", count, min_known_facts, satisfied, unsatisfied)

    max_hidden_secrets = _optional_int(conditions.get("max_hidden_secrets"))
    if max_hidden_secrets is not None:
        count = _count(
            session,
            select(func.count(SecretRecord.id)).where(
                SecretRecord.world_id == world_id,
                SecretRecord.worldline_id == worldline_id,
                SecretRecord.status == "hidden",
            ),
        )
        evidence["hidden_secret_count"] = count
        if count > max_hidden_secrets:
            unsatisfied.append(f"hidden secrets above {max_hidden_secrets}.")
        else:
            satisfied.append(f"hidden secrets within {max_hidden_secrets}.")

    evidence["evaluated_at"] = current_time.isoformat()
    return ConditionEvaluationResult(
        matched=not unsatisfied,
        satisfied=satisfied,
        unsatisfied=unsatisfied,
        evidence=evidence,
    )


def _route_for_conditions(
    session: Session,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    conditions: dict[str, Any],
    route_affinity_id: uuid.UUID | None,
) -> RouteAffinity | None:
    route_key = _optional_str(conditions.get("route_key"))
    statement = select(RouteAffinity).where(
        RouteAffinity.world_id == world_id,
        RouteAffinity.worldline_id == worldline_id,
    )
    if route_affinity_id is not None:
        statement = statement.where(RouteAffinity.id == route_affinity_id)
    if route_key is not None:
        statement = statement.where(RouteAffinity.route_key == route_key)
    return session.scalars(
        statement.order_by(RouteAffinity.stage.desc(), RouteAffinity.affinity.desc()),
    ).first()


def _plot_thread_for_conditions(
    session: Session,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    conditions: dict[str, Any],
    plot_thread_id: uuid.UUID | None,
) -> PlotThread | None:
    thread_key = _optional_str(conditions.get("plot_thread_key"))
    statement = select(PlotThread).where(
        PlotThread.world_id == world_id,
        PlotThread.worldline_id == worldline_id,
    )
    if plot_thread_id is not None:
        statement = statement.where(PlotThread.id == plot_thread_id)
    if thread_key is not None:
        statement = statement.where(PlotThread.thread_key == thread_key)
    return session.scalars(statement.order_by(PlotThread.priority.desc())).first()


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


def _count(session: Session, statement: Any) -> int:
    value = session.scalar(statement)
    return 0 if value is None else int(value)


def _utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _datetime_or_none(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return _utc(value)
    if isinstance(value, str):
        try:
            return _utc(datetime.fromisoformat(value))
        except ValueError:
            return None
    return None


def _list_of_strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]


def _optional_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
    return None


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


def _optional_str(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
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
