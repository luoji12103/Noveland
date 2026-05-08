from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from noveland.agents.models import Agent, AgentRelationshipEdge
from noveland.worlds.models import (
    CharacterEmotionalState,
    CharacterKnowledgeFact,
    SecretRecord,
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


def _agent_is_holder(secret: SecretRecord, agent_id: uuid.UUID | None) -> bool:
    return agent_id is not None and str(agent_id) in set(secret.holder_agent_ids or [])


def _truncate(value: str, limit: int = 320) -> str:
    stripped = " ".join(value.split())
    if len(stripped) <= limit:
        return stripped
    return f"{stripped[: limit - 3]}..."
