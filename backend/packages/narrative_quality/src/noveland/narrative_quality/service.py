from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any

from noveland.agents.models import Agent
from noveland.conversations import ConversationService
from noveland.conversations.contracts import ConversationSessionRecord, ConversationTurnRecord
from noveland.narrative.models import NarrativeArtifact
from noveland.providers.secrets import REDACTED, SENSITIVE_KEYS
from noveland.worlds.living_context import LivingWorldContextPack, LivingWorldContextSelector
from noveland.worlds.models import GMEventProposal, LongRunEvalRun, Worldline
from noveland.worlds.worldlines import worldline_or_404
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .contracts import (
    NarrativeQualityContextKind,
    NarrativeQualityContextPreview,
    NarrativeQualityContextPreviewRequest,
    NarrativeQualityEvidenceRef,
)

_LEAK_KEYWORDS = {
    "storage_uri",
    "preview_uri",
    "thumbnail_uri",
    "raw_prompt_text",
    "raw_output_text",
    "raw_request_json",
    "raw_response_json",
    "filesystem_path",
    "file_path",
    "base64",
    "bytes",
}
_LEAK_PATTERN = re.compile(
    r"(storage_uri|media://|file://|/root/|/tmp/|base64,|BEGIN PRIVATE KEY|sk-[A-Za-z0-9])",
    re.IGNORECASE,
)
_WHITESPACE_RE = re.compile(r"\s+")


class NarrativeQualityValidationError(ValueError):
    pass


class NarrativeQualityService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._selector = LivingWorldContextSelector(session)
        self._conversation_service = ConversationService(session)

    def preview_context(
        self,
        world_id: uuid.UUID,
        request: NarrativeQualityContextPreviewRequest,
    ) -> NarrativeQualityContextPreview:
        worldline = worldline_or_404(self._session, world_id, request.worldline_id)
        if request.context_kind == NarrativeQualityContextKind.AGENT:
            return self._agent_context(world_id, worldline, request)
        if request.context_kind == NarrativeQualityContextKind.CONVERSATION:
            return self._conversation_context(world_id, worldline, request)
        if request.context_kind == NarrativeQualityContextKind.GM:
            return self._gm_context(world_id, worldline, request)
        if request.context_kind == NarrativeQualityContextKind.NARRATIVE:
            return self._narrative_context(world_id, worldline, request)
        if request.context_kind == NarrativeQualityContextKind.EVAL:
            return self._eval_context(world_id, worldline, request)
        raise NarrativeQualityValidationError("unsupported context kind")

    def _agent_context(
        self,
        world_id: uuid.UUID,
        worldline: Worldline,
        request: NarrativeQualityContextPreviewRequest,
    ) -> NarrativeQualityContextPreview:
        assert request.agent_id is not None
        agent = self._agent_or_error(world_id, request.agent_id)
        context = self._selector.select_for_agent_prompt(
            world_id=world_id,
            worldline_id=worldline.id,
            agent_id=agent.id,
            limit=request.limit,
        )
        metadata = {
            "agent_id": str(agent.id),
            "agent_key": agent.agent_key,
            "display_name": agent.display_name,
            "narrative_role": agent.narrative_role,
            "importance": agent.importance,
            "context_sections": {
                "public_fact_count": len(context.public_facts),
                "agent_knowledge_count": len(context.agent_knowledge),
                "visible_secret_count": len(context.visible_secrets),
                "relationship_summary_count": len(context.relationship_summaries),
                "emotional_state_included": context.emotional_state is not None,
            },
        }
        return self._preview(
            world_id=world_id,
            worldline_id=worldline.id,
            context_kind=NarrativeQualityContextKind.AGENT,
            subject_ref=f"agent:{agent.id}",
            prompt_text=context.to_prompt_text() or "",
            metadata=metadata,
            diagnostics=context.diagnostics,
            evidence_refs=[
                NarrativeQualityEvidenceRef(kind="agent", id=str(agent.id)),
                NarrativeQualityEvidenceRef(kind="worldline", id=str(worldline.id)),
            ],
        )

    def _conversation_context(
        self,
        world_id: uuid.UUID,
        worldline: Worldline,
        request: NarrativeQualityContextPreviewRequest,
    ) -> NarrativeQualityContextPreview:
        assert request.conversation_id is not None
        session = self._conversation_session_or_error(
            world_id,
            worldline.id,
            request.conversation_id,
        )
        participants = self._conversation_service.list_participants(world_id, session.id)
        turns = self._conversation_service.list_turns(world_id, session.id)
        recent_turns = turns[-request.limit :]
        context_pack = self._context_pack(world_id, worldline.id, request.limit)
        participant_diagnostics: list[dict[str, Any]] = []
        for participant in participants:
            context = self._selector.select_for_agent_prompt(
                world_id=world_id,
                worldline_id=worldline.id,
                agent_id=participant.agent_id,
                limit=min(request.limit, 5),
            )
            participant_diagnostics.append(
                {
                    "agent_id": str(participant.agent_id),
                    "is_enabled": participant.is_enabled,
                    "turn_order": participant.turn_order,
                    "diagnostics": context.diagnostics,
                }
            )
        prompt_text = "\n".join(
            item
            for item in (
                f"Conversation: {session.title}",
                f"Objective: {_clip(session.objective, 600)}" if session.objective else "",
                f"Opening prompt: {_clip(session.opening_prompt, 600)}"
                if session.opening_prompt
                else "",
                context_pack.to_prompt_text() or "",
                _turn_window_text(recent_turns),
            )
            if item
        )
        metadata = {
            "conversation_id": str(session.id),
            "scene_id": None if session.scene_id is None else str(session.scene_id),
            "status": session.status.value,
            "scope_type": session.scope_type.value,
            "mode": session.mode.value,
            "participant_count": len(participants),
            "turn_count": len(turns),
            "recent_turns": [_turn_metadata(turn) for turn in recent_turns],
            "context_pack": context_pack.to_metadata(),
        }
        diagnostics = {
            "participant_diagnostics": participant_diagnostics,
            "empty_conversation": len(turns) == 0,
            "disabled_participant_count": sum(1 for item in participants if not item.is_enabled),
        }
        return self._preview(
            world_id=world_id,
            worldline_id=worldline.id,
            context_kind=NarrativeQualityContextKind.CONVERSATION,
            subject_ref=f"conversation:{session.id}",
            prompt_text=prompt_text,
            metadata=metadata,
            diagnostics=diagnostics,
            evidence_refs=[
                NarrativeQualityEvidenceRef(kind="conversation_session", id=str(session.id)),
                NarrativeQualityEvidenceRef(kind="worldline", id=str(worldline.id)),
            ],
        )

    def _gm_context(
        self,
        world_id: uuid.UUID,
        worldline: Worldline,
        request: NarrativeQualityContextPreviewRequest,
    ) -> NarrativeQualityContextPreview:
        context_pack = self._context_pack(world_id, worldline.id, request.limit)
        proposal_counts: dict[str, int] = {
            str(row[0]): int(row[1])
            for row in self._session.execute(
                select(GMEventProposal.status, func.count(GMEventProposal.id))
                .where(
                    GMEventProposal.world_id == world_id,
                    GMEventProposal.worldline_id == worldline.id,
                )
                .group_by(GMEventProposal.status),
            ).all()
        }
        return self._preview(
            world_id=world_id,
            worldline_id=worldline.id,
            context_kind=NarrativeQualityContextKind.GM,
            subject_ref=f"gm:{worldline.id}",
            prompt_text=context_pack.to_prompt_text() or "",
            metadata={
                "context_pack": context_pack.to_metadata(),
                "proposal_status_counts": proposal_counts,
            },
            diagnostics=context_pack.diagnostics,
            evidence_refs=[NarrativeQualityEvidenceRef(kind="worldline", id=str(worldline.id))],
        )

    def _narrative_context(
        self,
        world_id: uuid.UUID,
        worldline: Worldline,
        request: NarrativeQualityContextPreviewRequest,
    ) -> NarrativeQualityContextPreview:
        context_pack = self._context_pack(world_id, worldline.id, request.limit)
        artifacts = self._session.scalars(
            select(NarrativeArtifact)
            .where(NarrativeArtifact.world_id == world_id)
            .order_by(NarrativeArtifact.created_at.desc())
            .limit(request.limit),
        ).all()
        matching_worldline_count = sum(
            1
            for artifact in artifacts
            if _metadata_worldline_id(artifact) == worldline.id
        )
        metadata = {
            "context_pack": context_pack.to_metadata(),
            "legacy_artifact_count_sampled": len(artifacts),
            "legacy_metadata_worldline_match_count": matching_worldline_count,
            "v2_worldline_strategy": (
                "v2-generated narrative artifacts/publications require first-class "
                "worldline persistence before write paths are added"
            ),
            "recent_artifacts": [
                {
                    "id": str(artifact.id),
                    "artifact_kind": artifact.artifact_kind,
                    "title": artifact.title,
                    "metadata_worldline_id": str(
                        (artifact.artifact_metadata or {}).get("worldline_id") or ""
                    )
                    or None,
                }
                for artifact in artifacts
            ],
        }
        return self._preview(
            world_id=world_id,
            worldline_id=worldline.id,
            context_kind=NarrativeQualityContextKind.NARRATIVE,
            subject_ref=f"narrative:{worldline.id}",
            prompt_text=context_pack.to_prompt_text() or "",
            metadata=metadata,
            diagnostics={
                **context_pack.diagnostics,
                "metadata_only_worldline_warning": True,
            },
            evidence_refs=[NarrativeQualityEvidenceRef(kind="worldline", id=str(worldline.id))],
        )

    def _eval_context(
        self,
        world_id: uuid.UUID,
        worldline: Worldline,
        request: NarrativeQualityContextPreviewRequest,
    ) -> NarrativeQualityContextPreview:
        context_pack = self._context_pack(world_id, worldline.id, request.limit)
        eval_counts: dict[str, int] = {
            str(row[0]): int(row[1])
            for row in self._session.execute(
                select(LongRunEvalRun.status, func.count(LongRunEvalRun.id))
                .where(
                    LongRunEvalRun.world_id == world_id,
                    LongRunEvalRun.worldline_id == worldline.id,
                )
                .group_by(LongRunEvalRun.status),
            ).all()
        }
        return self._preview(
            world_id=world_id,
            worldline_id=worldline.id,
            context_kind=NarrativeQualityContextKind.EVAL,
            subject_ref=f"eval:{worldline.id}",
            prompt_text=context_pack.to_prompt_text() or "",
            metadata={
                "context_pack": context_pack.to_metadata(),
                "long_run_eval_status_counts": eval_counts,
            },
            diagnostics=context_pack.diagnostics,
            evidence_refs=[NarrativeQualityEvidenceRef(kind="worldline", id=str(worldline.id))],
        )

    def _context_pack(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        limit: int,
    ) -> LivingWorldContextPack:
        return self._selector.select_context_pack(
            world_id=world_id,
            worldline_id=worldline_id,
            limit=limit,
        )

    def _agent_or_error(self, world_id: uuid.UUID, agent_id: uuid.UUID) -> Agent:
        agent = self._session.get(Agent, agent_id)
        if agent is None or agent.world_id != world_id:
            raise NarrativeQualityValidationError("agent not found")
        return agent

    def _conversation_session_or_error(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        conversation_id: uuid.UUID,
    ) -> ConversationSessionRecord:
        try:
            session = self._conversation_service.get_session(world_id, conversation_id)
        except Exception as exc:
            raise NarrativeQualityValidationError("conversation not found") from exc
        if session.worldline_id != worldline_id:
            raise NarrativeQualityValidationError("conversation does not belong to worldline")
        return session

    def _preview(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        context_kind: NarrativeQualityContextKind,
        subject_ref: str,
        prompt_text: str,
        metadata: dict[str, Any],
        diagnostics: dict[str, Any],
        evidence_refs: list[NarrativeQualityEvidenceRef],
    ) -> NarrativeQualityContextPreview:
        return NarrativeQualityContextPreview(
            world_id=world_id,
            worldline_id=worldline_id,
            context_kind=context_kind,
            subject_ref=subject_ref,
            prompt_text=_safe_text(prompt_text),
            metadata=_sanitize_json(metadata),
            diagnostics=_sanitize_json(diagnostics),
            evidence_refs=evidence_refs,
            generated_at=datetime.now(UTC),
        )


def _turn_window_text(turns: list[ConversationTurnRecord]) -> str:
    if not turns:
        return ""
    lines = ["Recent turns:"]
    for turn in turns:
        speaker = (
            f"agent:{turn.speaker_agent_id}" if turn.speaker_agent_id else turn.speaker_kind.value
        )
        output_text = "" if turn.output_text is None else f" -> {_clip(turn.output_text, 500)}"
        lines.append(f"- #{turn.turn_index} {speaker}: {_clip(turn.input_text, 500)}{output_text}")
    return "\n".join(lines)


def _metadata_worldline_id(artifact: NarrativeArtifact) -> uuid.UUID | None:
    raw_worldline_id = (artifact.artifact_metadata or {}).get("worldline_id")
    if not isinstance(raw_worldline_id, str):
        return None
    try:
        return uuid.UUID(raw_worldline_id)
    except ValueError:
        return None


def _turn_metadata(turn: ConversationTurnRecord) -> dict[str, Any]:
    return {
        "id": str(turn.id),
        "turn_index": turn.turn_index,
        "speaker_kind": turn.speaker_kind.value,
        "speaker_agent_id": None if turn.speaker_agent_id is None else str(turn.speaker_agent_id),
        "status": turn.status.value,
        "input_text": _clip(turn.input_text, 500),
        "output_text": None if turn.output_text is None else _clip(turn.output_text, 500),
    }


def _clip(value: str, limit: int) -> str:
    collapsed = _WHITESPACE_RE.sub(" ", value).strip()
    if len(collapsed) <= limit:
        return collapsed
    return f"{collapsed[: max(0, limit - 1)]}..."


def _sanitize_json(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if _is_leaky_key(key_text):
                sanitized[key_text] = REDACTED
            else:
                sanitized[key_text] = _sanitize_json(item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_json(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_json(item) for item in value]
    if isinstance(value, str):
        return _safe_text(value)
    return value


def _is_leaky_key(key: str) -> bool:
    normalized = key.strip().lower()
    return normalized in SENSITIVE_KEYS or normalized in _LEAK_KEYWORDS


def _safe_text(value: str) -> str:
    if _LEAK_PATTERN.search(value):
        return REDACTED
    return value
