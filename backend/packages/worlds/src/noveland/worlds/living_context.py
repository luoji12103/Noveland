from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from noveland.agents.models import Agent, AgentRelationshipEdge
from noveland.worlds.models import (
    CharacterEmotionalState,
    CharacterKnowledgeFact,
    NarrativeContinuityReview,
    PlotThread,
    RouteAffinity,
    SecretRecord,
    StoryHook,
    WorldBible,
)
from noveland.worlds.worldlines import worldline_or_404
from sqlalchemy import or_, select
from sqlalchemy.orm import Session


@dataclass(frozen=True, slots=True)
class LivingWorldPromptContext:
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    agent_id: uuid.UUID | None
    public_facts: list[str]
    agent_knowledge: list[str]
    visible_secrets: list[str]
    emotional_state: str | None
    relationship_summaries: list[str]
    diagnostics: dict[str, Any]

    def to_prompt_text(self) -> str | None:
        sections: list[str] = []
        if self.public_facts:
            sections.append(_section("Public world facts", self.public_facts))
        if self.agent_knowledge:
            sections.append(_section("Agent-visible knowledge", self.agent_knowledge))
        if self.visible_secrets:
            sections.append(_section("Allowed secret context", self.visible_secrets))
        if self.emotional_state:
            sections.append(_section("Current emotional state", [self.emotional_state]))
        if self.relationship_summaries:
            sections.append(_section("Relationship context", self.relationship_summaries))
        if not sections:
            return None
        return "\n\n".join(["Living-world context:", *sections])


@dataclass(frozen=True, slots=True)
class LivingWorldContextPack:
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    bible_constraints: list[str]
    forbidden_changes: list[str]
    open_hooks: list[str]
    active_plot_threads: list[str]
    route_states: list[str]
    continuity_warnings: list[str]
    diagnostics: dict[str, Any]

    def to_prompt_text(self) -> str | None:
        sections: list[str] = []
        if self.bible_constraints:
            sections.append(_section("World bible constraints", self.bible_constraints))
        if self.forbidden_changes:
            sections.append(_section("Forbidden continuity changes", self.forbidden_changes))
        if self.open_hooks:
            sections.append(_section("Open story hooks", self.open_hooks))
        if self.active_plot_threads:
            sections.append(_section("Active plot threads", self.active_plot_threads))
        if self.route_states:
            sections.append(_section("Route state", self.route_states))
        if self.continuity_warnings:
            sections.append(_section("Continuity warnings", self.continuity_warnings))
        if not sections:
            return None
        return "\n\n".join(["Living-world execution context:", *sections])

    def to_metadata(self) -> dict[str, Any]:
        return {
            "world_id": str(self.world_id),
            "worldline_id": str(self.worldline_id),
            "diagnostics": self.diagnostics,
            "bible_constraints": self.bible_constraints,
            "forbidden_changes": self.forbidden_changes,
            "open_hooks": self.open_hooks,
            "active_plot_threads": self.active_plot_threads,
            "route_states": self.route_states,
            "continuity_warnings": self.continuity_warnings,
        }


class LivingWorldContextSelector:
    def __init__(self, session: Session) -> None:
        self._session = session

    def select_for_agent_prompt(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        agent_id: uuid.UUID,
        limit: int = 6,
    ) -> LivingWorldPromptContext:
        resolved_worldline = worldline_or_404(self._session, world_id, worldline_id)
        agent = self._session.get(Agent, agent_id)
        if agent is None or agent.world_id != world_id:
            raise ValueError("agent not found")
        facts = self._knowledge_rows(
            world_id=world_id,
            worldline_id=resolved_worldline.id,
            agent_id=agent_id,
            limit=limit,
        )
        visible_secrets = self._visible_secret_rows(
            world_id=world_id,
            worldline_id=resolved_worldline.id,
            agent_id=agent_id,
            limit=limit,
        )
        emotional_state = self._emotional_state(
            world_id=world_id,
            worldline_id=resolved_worldline.id,
            agent_id=agent_id,
        )
        relationships = self._relationship_rows(
            world_id=world_id,
            worldline_id=resolved_worldline.id,
            agent_id=agent_id,
            limit=limit,
        )
        public_facts = [
            _truncate(fact.content)
            for fact in facts
            if fact.visibility == "public" and fact.knowledge_kind != "secret"
        ]
        agent_knowledge = [
            _knowledge_line(fact)
            for fact in facts
            if fact.visibility != "public" and fact.knowledge_kind != "secret"
        ]
        secret_lines = [_secret_line(secret) for secret in visible_secrets]
        hidden_secret_count = self._hidden_secret_count(
            world_id,
            resolved_worldline.id,
            agent_id=agent_id,
        )
        return LivingWorldPromptContext(
            world_id=world_id,
            worldline_id=resolved_worldline.id,
            agent_id=agent_id,
            public_facts=public_facts[:limit],
            agent_knowledge=agent_knowledge[:limit],
            visible_secrets=secret_lines[:limit],
            emotional_state=None if emotional_state is None else _emotion_line(emotional_state),
            relationship_summaries=[
                _relationship_line(self._agent_name(edge.target_agent_id), edge)
                for edge in relationships
            ],
            diagnostics={
                "public_fact_count": len(public_facts),
                "agent_knowledge_count": len(agent_knowledge),
                "visible_secret_count": len(secret_lines),
                "hidden_secret_count": hidden_secret_count,
                "relationship_summary_count": len(relationships),
                "emotional_state_included": emotional_state is not None,
            },
        )

    def select_for_review(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        reviewed_text: str,
        agent_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        resolved_worldline = worldline_or_404(self._session, world_id, worldline_id)
        hidden_secrets = self._hidden_secret_rows(
            world_id=world_id,
            worldline_id=resolved_worldline.id,
            agent_id=agent_id,
            limit=200,
        )
        lower_text = reviewed_text.lower()
        leak_matches: list[dict[str, Any]] = []
        for secret in hidden_secrets:
            matched_fields = []
            if secret.secret_key and secret.secret_key.lower() in lower_text:
                matched_fields.append("secret_key")
            if secret.title and secret.title.lower() in lower_text:
                matched_fields.append("title")
            if secret.content and secret.content.lower() in lower_text:
                matched_fields.append("content")
            if matched_fields:
                leak_matches.append(
                    {
                        "secret_id": str(secret.id),
                        "matched_fields": matched_fields,
                        "holder_visible": _agent_is_holder(secret, agent_id),
                    }
                )
        return {
            "world_id": str(world_id),
            "worldline_id": str(resolved_worldline.id),
            "agent_id": None if agent_id is None else str(agent_id),
            "hidden_secret_count": len(hidden_secrets),
            "hidden_secret_leak_count": len(leak_matches),
            "hidden_secret_leaks": leak_matches,
        }

    def select_context_pack(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        limit: int = 5,
    ) -> LivingWorldContextPack:
        resolved_worldline = worldline_or_404(self._session, world_id, worldline_id)
        row_limit = max(1, min(limit, 10))
        bible = self._session.scalars(
            select(WorldBible).where(WorldBible.world_id == world_id),
        ).one_or_none()
        bible_constraints: list[str] = []
        forbidden_changes: list[str] = []
        if bible is not None:
            bible_constraints = _bible_constraint_lines(bible, row_limit)
            forbidden_changes = _forbidden_change_lines(bible, row_limit)
        open_hooks = [
            _hook_line(hook)
            for hook in self._session.scalars(
                select(StoryHook)
                .where(
                    StoryHook.world_id == world_id,
                    StoryHook.worldline_id == resolved_worldline.id,
                    StoryHook.status == "open",
                )
                .order_by(StoryHook.priority.desc(), StoryHook.updated_at.desc())
                .limit(row_limit),
            ).all()
        ]
        active_threads = [
            _plot_thread_line(thread)
            for thread in self._session.scalars(
                select(PlotThread)
                .where(
                    PlotThread.world_id == world_id,
                    PlotThread.worldline_id == resolved_worldline.id,
                    PlotThread.status.in_(["active", "dormant"]),
                    PlotThread.thread_type != "hidden",
                )
                .order_by(PlotThread.priority.desc(), PlotThread.updated_at.desc())
                .limit(row_limit),
            ).all()
        ]
        route_states = [
            _route_line(route)
            for route in self._session.scalars(
                select(RouteAffinity)
                .where(
                    RouteAffinity.world_id == world_id,
                    RouteAffinity.worldline_id == resolved_worldline.id,
                    RouteAffinity.status.in_(["available", "active", "blocked"]),
                )
                .order_by(RouteAffinity.stage.desc(), RouteAffinity.affinity.desc())
                .limit(row_limit),
            ).all()
        ]
        continuity_warnings = [
            _continuity_warning_line(review)
            for review in self._session.scalars(
                select(NarrativeContinuityReview)
                .where(
                    NarrativeContinuityReview.world_id == world_id,
                    NarrativeContinuityReview.worldline_id == resolved_worldline.id,
                    NarrativeContinuityReview.status.in_(["warning", "fail"]),
                )
                .order_by(NarrativeContinuityReview.created_at.desc())
                .limit(row_limit),
            ).all()
        ]
        return LivingWorldContextPack(
            world_id=world_id,
            worldline_id=resolved_worldline.id,
            bible_constraints=bible_constraints,
            forbidden_changes=forbidden_changes,
            open_hooks=open_hooks,
            active_plot_threads=active_threads,
            route_states=route_states,
            continuity_warnings=continuity_warnings,
            diagnostics={
                "world_bible_included": bible is not None,
                "bible_constraint_count": len(bible_constraints),
                "forbidden_change_count": len(forbidden_changes),
                "open_hook_count": len(open_hooks),
                "active_plot_thread_count": len(active_threads),
                "route_state_count": len(route_states),
                "continuity_warning_count": len(continuity_warnings),
            },
        )

    def _knowledge_rows(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        agent_id: uuid.UUID,
        limit: int,
    ) -> list[CharacterKnowledgeFact]:
        return list(
            self._session.scalars(
                select(CharacterKnowledgeFact)
                .where(
                    CharacterKnowledgeFact.world_id == world_id,
                    CharacterKnowledgeFact.worldline_id == worldline_id,
                    CharacterKnowledgeFact.is_active.is_(True),
                    or_(
                        CharacterKnowledgeFact.agent_id == agent_id,
                        CharacterKnowledgeFact.visibility == "public",
                    ),
                )
                .order_by(CharacterKnowledgeFact.updated_at.desc())
                .limit(max(limit * 2, limit)),
            ).all()
        )

    def _visible_secret_rows(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        agent_id: uuid.UUID,
        limit: int,
    ) -> list[SecretRecord]:
        return [
            secret
            for secret in self._session.scalars(
                select(SecretRecord)
                .where(
                    SecretRecord.world_id == world_id,
                    SecretRecord.worldline_id == worldline_id,
                    SecretRecord.status != "archived",
                )
                .order_by(SecretRecord.updated_at.desc())
                .limit(max(limit * 3, limit)),
            ).all()
            if secret.status == "revealed"
            or secret.visibility == "public"
            or _agent_is_holder(secret, agent_id)
        ]

    def _hidden_secret_rows(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        agent_id: uuid.UUID | None,
        limit: int,
    ) -> list[SecretRecord]:
        rows = self._session.scalars(
            select(SecretRecord)
            .where(
                SecretRecord.world_id == world_id,
                SecretRecord.worldline_id == worldline_id,
                SecretRecord.status == "hidden",
            )
            .order_by(SecretRecord.updated_at.desc())
            .limit(limit),
        ).all()
        if agent_id is None:
            return list(rows)
        return [secret for secret in rows if not _agent_is_holder(secret, agent_id)]

    def _hidden_secret_count(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        *,
        agent_id: uuid.UUID,
    ) -> int:
        return len(
            self._hidden_secret_rows(
                world_id=world_id,
                worldline_id=worldline_id,
                agent_id=agent_id,
                limit=10_000,
            )
        )

    def _emotional_state(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        agent_id: uuid.UUID,
    ) -> CharacterEmotionalState | None:
        now = datetime.now(UTC)
        state = self._session.scalars(
            select(CharacterEmotionalState).where(
                CharacterEmotionalState.world_id == world_id,
                CharacterEmotionalState.worldline_id == worldline_id,
                CharacterEmotionalState.agent_id == agent_id,
            ),
        ).one_or_none()
        if state is None:
            return None
        if state.expires_at is not None:
            expires_at = (
                state.expires_at.replace(tzinfo=UTC)
                if state.expires_at.tzinfo is None
                else state.expires_at.astimezone(UTC)
            )
            if expires_at <= now:
                return None
        return state

    def _relationship_rows(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        agent_id: uuid.UUID,
        limit: int,
    ) -> list[AgentRelationshipEdge]:
        return list(
            self._session.scalars(
                select(AgentRelationshipEdge)
                .where(
                    AgentRelationshipEdge.world_id == world_id,
                    AgentRelationshipEdge.worldline_id == worldline_id,
                    AgentRelationshipEdge.source_agent_id == agent_id,
                )
                .order_by(AgentRelationshipEdge.updated_at.desc())
                .limit(limit),
            ).all()
        )

    def _agent_name(self, agent_id: uuid.UUID) -> str:
        agent = self._session.get(Agent, agent_id)
        if agent is None:
            return f"agent:{agent_id}"
        return agent.display_name


def _section(title: str, lines: list[str]) -> str:
    return "\n".join([f"{title}:", *[f"- {line}" for line in lines]])


def _knowledge_line(fact: CharacterKnowledgeFact) -> str:
    return (
        f"{fact.knowledge_kind}: {_truncate(fact.content)} "
        f"(confidence {fact.confidence}, visibility {fact.visibility})"
    )


def _secret_line(secret: SecretRecord) -> str:
    return f"{secret.title}: {_truncate(secret.content)}"


def _emotion_line(state: CharacterEmotionalState) -> str:
    return (
        f"mood {state.mood}; stress {state.stress}; fatigue {state.fatigue}; "
        f"anticipation {state.anticipation}; jealousy {state.jealousy}; anger {state.anger}"
    )


def _relationship_line(target_name: str, edge: AgentRelationshipEdge) -> str:
    return (
        f"toward {target_name}: {edge.relationship_type}; affection {edge.affection}; "
        f"trust {edge.trust}; hostility {edge.hostility}; intimacy {edge.intimacy}; "
        f"obligation {edge.obligation}; rivalry {edge.rivalry}; debt {edge.debt}"
    )


def _bible_constraint_lines(bible: WorldBible, limit: int) -> list[str]:
    lines: list[str] = []
    if bible.source_material:
        lines.append(f"source material: {_truncate(bible.source_material)}")
    setting_rules = bible.setting_rules or {}
    for key, value in list(setting_rules.items())[:limit]:
        lines.append(f"{key}: {_truncate(_stringify_metadata_value(value))}")
    sequel_boundaries = bible.sequel_boundaries or {}
    for key, value in list(sequel_boundaries.items())[: max(0, limit - len(lines))]:
        lines.append(f"sequel boundary {key}: {_truncate(_stringify_metadata_value(value))}")
    continuity_config = bible.continuity_config or {}
    for key, value in list(continuity_config.items())[: max(0, limit - len(lines))]:
        lines.append(f"continuity {key}: {_truncate(_stringify_metadata_value(value))}")
    return lines[:limit]


def _forbidden_change_lines(bible: WorldBible, limit: int) -> list[str]:
    lines: list[str] = []
    for change in (bible.forbidden_changes or [])[:limit]:
        if isinstance(change, dict):
            title = str(change.get("title") or change.get("key") or "forbidden change")
            reason = _stringify_metadata_value(
                change.get("reason") or change.get("description") or change
            )
            lines.append(f"{title}: {_truncate(reason)}")
        else:
            lines.append(_truncate(str(change)))
    return lines


def _hook_line(hook: StoryHook) -> str:
    due = "" if hook.due_at is None else f"; due {hook.due_at.isoformat()}"
    return (
        f"{hook.title} ({hook.hook_type}, priority {hook.priority}{due}): "
        f"{_truncate(hook.summary)}"
    )


def _plot_thread_line(thread: PlotThread) -> str:
    next_beats = "; next " + ", ".join(thread.next_beats[:2]) if thread.next_beats else ""
    return (
        f"{thread.title} ({thread.thread_type}, {thread.status}, priority {thread.priority}): "
        f"{_truncate(thread.summary)}{next_beats}"
    )


def _route_line(route: RouteAffinity) -> str:
    flags = ", ".join(route.flags[:4]) if route.flags else "no flags"
    return (
        f"{route.route_key}: {route.status}; stage {route.stage}; "
        f"affinity {route.affinity}; flags {flags}"
    )


def _continuity_warning_line(review: NarrativeContinuityReview) -> str:
    issue_count = len(review.issues or [])
    issue_types = sorted(
        {
            str(issue.get("type") or issue.get("code") or "issue")
            for issue in review.issues
            if isinstance(issue, dict)
        }
    )
    suffix = "" if not issue_types else f"; {', '.join(issue_types[:4])}"
    return f"{review.status} review from {review.source_kind}: {issue_count} issue(s){suffix}"


def _agent_is_holder(secret: SecretRecord, agent_id: uuid.UUID | None) -> bool:
    return agent_id is not None and str(agent_id) in set(secret.holder_agent_ids or [])


def _stringify_metadata_value(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return ", ".join(_stringify_metadata_value(item) for item in value[:6])
    if isinstance(value, dict):
        return ", ".join(
            f"{key}={_stringify_metadata_value(item)}" for key, item in list(value.items())[:6]
        )
    return str(value)


def _truncate(value: str, limit: int = 320) -> str:
    stripped = " ".join(value.split())
    if len(stripped) <= limit:
        return stripped
    return f"{stripped[: limit - 3]}..."
