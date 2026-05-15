from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any

from noveland.agents.models import Agent
from noveland.conversations import ConversationService
from noveland.conversations.contracts import ConversationSessionRecord, ConversationTurnRecord
from noveland.narrative.models import NarrativeArtifact
from noveland.providers.contracts import (
    ProviderAdapterKind,
    ProviderExecutionRequest,
    ProviderIntegrationRead,
    ProviderKind,
)
from noveland.providers.registry import (
    ProviderNotFoundError,
    ProviderRegistryService,
    ProviderValidationError,
)
from noveland.providers.secrets import REDACTED, SENSITIVE_KEYS, reject_sensitive_config
from noveland.providers.service import ProviderExecutionService
from noveland.worlds.gm import LivingWorldGMService
from noveland.worlds.living_context import LivingWorldContextPack, LivingWorldContextSelector
from noveland.worlds.models import GMEventProposal, LongRunEvalRun, Worldline
from noveland.worlds.worldlines import worldline_or_404
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .contracts import (
    NarrativeQualityContextKind,
    NarrativeQualityContextPreview,
    NarrativeQualityContextPreviewRequest,
    NarrativeQualityDialogueFinding,
    NarrativeQualityDialogueReviewRequest,
    NarrativeQualityDialogueReviewResult,
    NarrativeQualityEvidenceRef,
    NarrativeQualityGMImportance,
    NarrativeQualityGMProposalCandidate,
    NarrativeQualityGMProposalGenerateRequest,
    NarrativeQualityGMProposalGenerationResult,
    NarrativeQualityInvocationRef,
    NarrativeQualityProviderRef,
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

    def generate_gm_proposal(
        self,
        world_id: uuid.UUID,
        request: NarrativeQualityGMProposalGenerateRequest,
        *,
        actor_ref: str,
    ) -> NarrativeQualityGMProposalGenerationResult:
        worldline = worldline_or_404(self._session, world_id, request.worldline_id)
        reject_sensitive_config(request.payload_json, field_name="payload_json")
        reject_sensitive_config(
            request.provider_request_json,
            field_name="provider_request_json",
        )
        provider = self._resolve_text_provider(world_id, request)
        self._validate_text_provider(provider)
        context_pack = self._context_pack(world_id, worldline.id, request.context_limit)
        prompt_text = _gm_generation_prompt(request, context_pack)
        result = ProviderExecutionService(self._session).execute(
            ProviderExecutionRequest(
                world_id=world_id,
                worldline_id=worldline.id,
                provider_id=provider.id,
                provider_kind=ProviderKind.TEXT_GENERATION,
                capability_key=request.capability_key,
                model_name=request.model_name,
                input_text=prompt_text,
                input_json={
                    "context_kind": "gm",
                    "prompt_goal": _safe_text(request.prompt_goal),
                    "worldline_id": str(worldline.id),
                },
                request_json={
                    **dict(request.provider_request_json),
                    "operation": "gm_proposal_generation",
                    "context_kind": "gm",
                    "context_limit": request.context_limit,
                    "narrative_quality_phase": "v0.6.2",
                },
                actor_ref=actor_ref,
            )
        )
        candidate = _candidate_from_provider_output(
            request,
            provider=provider,
            invocation_id=result.invocation.id,
            output_text=result.output_text,
            output_json=result.output_json,
        )
        proposal_model: GMEventProposal | None = None
        if not request.dry_run:
            proposal_model = LivingWorldGMService(self._session).create_proposal(
                world_id=world_id,
                worldline_id=worldline.id,
                agenda_id=None,
                title=candidate.title,
                reason=candidate.reason,
                event_name=candidate.event_name,
                proposed_payload=candidate.proposed_payload,
                importance=candidate.importance.value,
                risk_score=candidate.risk_score,
                affected_agents=candidate.affected_agents,
                affected_organizations=candidate.affected_organizations,
                source_context=candidate.source_context,
            )
            candidate = _proposal_candidate(proposal_model)
        return NarrativeQualityGMProposalGenerationResult(
            world_id=world_id,
            worldline_id=worldline.id,
            dry_run=request.dry_run,
            provider=NarrativeQualityProviderRef(
                id=provider.id,
                provider_kind=provider.provider_kind,
                adapter_kind=provider.adapter_kind,
                provider_key=provider.provider_key,
            ),
            invocation=NarrativeQualityInvocationRef(
                id=result.invocation.id,
                status=result.invocation.status.value,
                provider_kind=result.invocation.provider_kind.value,
                error_text=_safe_text(result.invocation.error_text)
                if result.invocation.error_text
                else None,
            ),
            proposal=candidate,
            diagnostics=_sanitize_json(
                {
                    "context_kind": "gm",
                    "context_limit": request.context_limit,
                    "proposal_persisted": proposal_model is not None,
                    "provider_output_available": bool(result.output_text or result.output_json),
                }
            ),
        )

    def review_dialogue(
        self,
        world_id: uuid.UUID,
        request: NarrativeQualityDialogueReviewRequest,
    ) -> NarrativeQualityDialogueReviewResult:
        worldline = worldline_or_404(self._session, world_id, request.worldline_id)
        conversation = self._conversation_session_or_error(
            world_id,
            worldline.id,
            request.conversation_id,
        )
        turn: ConversationTurnRecord | None = None
        if request.turn_id is not None:
            turn = self._turn_or_error(world_id, conversation.id, request.turn_id)
        speaker_agent_id = request.speaker_agent_id or (
            None if turn is None else turn.speaker_agent_id
        )
        text = request.text or _turn_dialogue_text(turn)
        if text is None or text.strip() == "":
            raise NarrativeQualityValidationError("dialogue review requires text")
        agent = (
            None
            if speaker_agent_id is None
            else self._agent_or_error(world_id, speaker_agent_id)
        )
        context = (
            None
            if speaker_agent_id is None
            else self._selector.select_for_agent_prompt(
                world_id=world_id,
                worldline_id=worldline.id,
                agent_id=speaker_agent_id,
                limit=request.context_limit,
            )
        )
        findings = _dialogue_findings(text, agent=agent, context=context)
        severity_penalty = sum(_finding_penalty(item) for item in findings)
        style_score = max(0, 100 - severity_penalty)
        ooc_risk_score = min(100, severity_penalty)
        relationship_summaries = [] if context is None else context.relationship_summaries
        relationship_score = 100
        if relationship_summaries:
            relationship_score = max(
                0,
                100
                - sum(
                    _finding_penalty(item)
                    for item in findings
                    if item.code.startswith("relationship")
                ),
            )
        review_status = "pass"
        if any(item.severity == "error" for item in findings):
            review_status = "fail"
        elif any(item.severity == "warning" for item in findings):
            review_status = "warning"
        evidence_refs = [NarrativeQualityEvidenceRef(kind="conversation", id=str(conversation.id))]
        if turn is not None:
            evidence_refs.append(NarrativeQualityEvidenceRef(kind="turn", id=str(turn.id)))
        if speaker_agent_id is not None:
            evidence_refs.append(
                NarrativeQualityEvidenceRef(kind="agent", id=str(speaker_agent_id))
            )
        return NarrativeQualityDialogueReviewResult(
            world_id=world_id,
            worldline_id=worldline.id,
            conversation_id=conversation.id,
            turn_id=None if turn is None else turn.id,
            speaker_agent_id=speaker_agent_id,
            review_status=review_status,
            style_score=style_score,
            ooc_risk_score=ooc_risk_score,
            relationship_consistency_score=relationship_score,
            reviewed_text=_safe_text(_clip(text, 1200)),
            findings=findings,
            evidence_refs=evidence_refs,
            diagnostics=_sanitize_json(
                {
                    "context_kind": "dialogue_review",
                    "context_limit": request.context_limit,
                    "has_agent_profile": agent is not None,
                    "relationship_summary_count": len(relationship_summaries),
                    "finding_count": len(findings),
                }
            ),
        )

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

    def _resolve_text_provider(
        self,
        world_id: uuid.UUID,
        request: NarrativeQualityGMProposalGenerateRequest,
    ) -> ProviderIntegrationRead:
        registry = ProviderRegistryService(self._session)
        try:
            if request.provider_id is not None:
                provider = registry.get_provider(
                    world_id,
                    request.provider_id,
                    platform_admin=True,
                    include_hidden=True,
                )
                if provider is None:
                    raise ProviderNotFoundError("provider integration not found")
                return provider
            return registry.resolve_provider_for_capability(
                world_id,
                provider_kind=ProviderKind.TEXT_GENERATION,
                capability_key=request.capability_key,
            )
        except (ProviderNotFoundError, ProviderValidationError) as exc:
            raise NarrativeQualityValidationError(str(exc)) from exc

    def _validate_text_provider(self, provider: ProviderIntegrationRead) -> None:
        if provider.provider_kind != ProviderKind.TEXT_GENERATION:
            raise NarrativeQualityValidationError(
                "provider-backed GM proposal requires provider_kind=text_generation"
            )
        if provider.adapter_kind not in {ProviderAdapterKind.FAKE, ProviderAdapterKind.LOCAL_STUB}:
            raise NarrativeQualityValidationError(
                "provider adapter does not support provider-kernel text generation yet"
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

    def _turn_or_error(
        self,
        world_id: uuid.UUID,
        conversation_id: uuid.UUID,
        turn_id: uuid.UUID,
    ) -> ConversationTurnRecord:
        turns = self._conversation_service.list_turns(world_id, conversation_id)
        for turn in turns:
            if turn.id == turn_id:
                return turn
        raise NarrativeQualityValidationError("turn not found")

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


def _gm_generation_prompt(
    request: NarrativeQualityGMProposalGenerateRequest,
    context_pack: LivingWorldContextPack,
) -> str:
    lines = [
        "Generate one GM proposal candidate.",
        f"Goal: {_clip(request.prompt_goal, 800)}",
        f"Importance: {request.importance.value}",
        f"Risk score target: {request.risk_score}",
    ]
    context_text = context_pack.to_prompt_text()
    if context_text:
        lines.extend(["Context:", context_text])
    lines.append(
        "Return a concise proposal reason. Do not include secrets, storage paths, "
        "base64, file paths, raw prompts, or raw outputs."
    )
    return "\n".join(lines)


def _candidate_from_provider_output(
    request: NarrativeQualityGMProposalGenerateRequest,
    *,
    provider: ProviderIntegrationRead,
    invocation_id: uuid.UUID,
    output_text: str | None,
    output_json: dict[str, Any],
) -> NarrativeQualityGMProposalCandidate:
    raw_proposal = output_json.get("proposal")
    proposal_json = raw_proposal if isinstance(raw_proposal, dict) else {}
    reason = _safe_text(
        _clip(
            str(proposal_json.get("reason") or output_text or output_json.get("text") or ""),
            1200,
        )
    )
    if not reason or reason == REDACTED:
        reason = "Provider generated a GM proposal candidate; details were redacted."
    title = _safe_text(
        _clip(
            str(proposal_json.get("title") or request.title or request.prompt_goal),
            160,
        )
    )
    if not title or title == REDACTED:
        title = "Provider-backed GM proposal"
    event_name = str(proposal_json.get("event_name") or request.event_name)
    proposed_payload = _sanitize_json(
        {
            **dict(request.payload_json),
            "source": "provider_backed_gm_proposal",
            "goal": _clip(request.prompt_goal, 500),
        }
    )
    source_context = _sanitize_json(
        {
            "source": "provider_backed_gm_proposal",
            "phase": "v0.6.2",
            "provider_id": str(provider.id),
            "provider_kind": provider.provider_kind.value,
            "adapter_kind": provider.adapter_kind.value,
            "model_invocation_id": str(invocation_id),
            "context_kind": "gm",
            "context_limit": request.context_limit,
        }
    )
    return NarrativeQualityGMProposalCandidate(
        status="preview" if request.dry_run else "proposed",
        title=title,
        reason=reason,
        event_name=_clip(event_name, 120),
        proposed_payload=proposed_payload,
        importance=request.importance,
        risk_score=request.risk_score,
        affected_agents=list(request.affected_agents),
        affected_organizations=list(request.affected_organizations),
        source_context=source_context,
    )


def _proposal_candidate(proposal: GMEventProposal) -> NarrativeQualityGMProposalCandidate:
    return NarrativeQualityGMProposalCandidate(
        id=proposal.id,
        status=proposal.status,
        title=_safe_text(proposal.title),
        reason=_safe_text(proposal.reason),
        event_name=proposal.event_name,
        proposed_payload=_sanitize_json(proposal.proposed_payload),
        importance=NarrativeQualityGMImportance(proposal.importance),
        risk_score=proposal.risk_score,
        affected_agents=list(proposal.affected_agents),
        affected_organizations=list(proposal.affected_organizations),
        source_context=_sanitize_json(proposal.source_context),
        created_at=proposal.created_at,
    )


def _turn_dialogue_text(turn: ConversationTurnRecord | None) -> str | None:
    if turn is None:
        return None
    return turn.output_text or turn.input_text


def _dialogue_findings(
    text: str,
    *,
    agent: Agent | None,
    context: object | None,
) -> list[NarrativeQualityDialogueFinding]:
    findings: list[NarrativeQualityDialogueFinding] = []
    if _safe_text(text) == REDACTED:
        findings.append(
            NarrativeQualityDialogueFinding(
                code="unsafe_text_leak",
                severity="error",
                message=(
                    "Dialogue text contains unsafe operational content such as "
                    "media references, encoded payloads, secrets, or raw prompt markers."
                ),
                suggested_action="Remove unsafe operational content before exposing this dialogue.",
            )
        )
    if agent is None:
        findings.append(
            NarrativeQualityDialogueFinding(
                code="missing_speaker_agent",
                severity="warning",
                message="Dialogue has no speaker agent profile to compare against.",
                suggested_action=(
                    "Attach a speaker agent before treating this review as style evidence."
                ),
            )
        )
    else:
        profile_text = _agent_profile_text(agent)
        if profile_text and not _shares_profile_token(text, profile_text):
            findings.append(
                NarrativeQualityDialogueFinding(
                    code="style_profile_weak_match",
                    severity="info",
                    message="Dialogue has weak lexical overlap with the speaker profile.",
                    evidence_refs=[NarrativeQualityEvidenceRef(kind="agent", id=str(agent.id))],
                    suggested_action="Review whether the line reflects the character voice.",
                )
            )
        forbidden_terms = _profile_list(agent.character_profile, "forbidden_terms")
        matched_forbidden = [term for term in forbidden_terms if term.lower() in text.lower()]
        if matched_forbidden:
            findings.append(
                NarrativeQualityDialogueFinding(
                    code="style_forbidden_term",
                    severity="warning",
                    message="Dialogue uses a term marked as disallowed for this speaker.",
                    evidence_refs=[NarrativeQualityEvidenceRef(kind="agent", id=str(agent.id))],
                    suggested_action=(
                        "Rewrite the line or update the character profile if this is intentional."
                    ),
                )
            )
    if len(text.strip()) < 8:
        findings.append(
            NarrativeQualityDialogueFinding(
                code="low_confidence_short_text",
                severity="info",
                message="Dialogue is too short for high-confidence style review.",
                suggested_action="Review with surrounding turns if this line matters.",
            )
        )
    relationship_summaries = getattr(context, "relationship_summaries", [])
    if isinstance(relationship_summaries, list) and relationship_summaries:
        hostile_context = any(
            isinstance(item, str) and "hostility" in item and not item.endswith("hostility 0")
            for item in relationship_summaries
        )
        intimate_language = any(term in text.lower() for term in ("love", "trust you", "dear"))
        if hostile_context and intimate_language:
            findings.append(
                NarrativeQualityDialogueFinding(
                    code="relationship_tone_jump",
                    severity="warning",
                    message="Dialogue tone may jump ahead of current relationship context.",
                    suggested_action=(
                        "Check whether a relationship repair or affection event should "
                        "precede this line."
                    ),
                )
            )
    return findings


def _agent_profile_text(agent: Agent) -> str:
    profile = agent.character_profile or {}
    chunks = [
        agent.display_name,
        str(agent.narrative_role or ""),
        str(profile.get("personality") or ""),
        str(profile.get("speech_style") or ""),
        str(profile.get("style_notes") or ""),
    ]
    return " ".join(item for item in chunks if item)


def _shares_profile_token(text: str, profile_text: str) -> bool:
    text_tokens = _signal_tokens(text)
    profile_tokens = _signal_tokens(profile_text)
    return bool(text_tokens & profile_tokens)


def _signal_tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[A-Za-z0-9_']+", value.lower())
        if len(token) >= 4
    }


def _profile_list(profile: dict[str, Any], key: str) -> list[str]:
    value = profile.get(key)
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _finding_penalty(finding: NarrativeQualityDialogueFinding) -> int:
    if finding.severity == "error":
        return 60
    if finding.severity == "warning":
        return 25
    return 8


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
                sanitized[f"redacted_{len(sanitized) + 1}"] = REDACTED
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
