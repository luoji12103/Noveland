from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any, cast

from noveland.agents.models import Agent, AgentPersona, AgentRelationshipEdge
from noveland.asset_generation.models import (
    AssetGenerationPolicy,
    AssetGenerationProposal,
)
from noveland.conversations import ConversationService
from noveland.conversations.contracts import ConversationSessionRecord, ConversationTurnRecord
from noveland.conversations.models import (
    ConversationParticipant,
    ConversationSession,
    ConversationTurn,
    ConversationTurnPresentation,
)
from noveland.conversations.presentation import ConversationPresentationService
from noveland.events.models import WorldEventModel
from noveland.invocations.models import ModelInvocation, PromptSnapshot
from noveland.media.models import MediaJob
from noveland.memory.models import AgentMemoryItem
from noveland.narrative.contracts import NarrativeArtifactCreate
from noveland.narrative.models import NarrativeArtifact
from noveland.narrative.services import NarrativeArtifactService
from noveland.providers.contracts import (
    ProviderAdapterKind,
    ProviderExecutionRequest,
    ProviderIntegrationRead,
    ProviderKind,
)
from noveland.providers.models import ProviderHealthCheck, ProviderIntegration
from noveland.providers.registry import (
    ProviderNotFoundError,
    ProviderRegistryService,
    ProviderValidationError,
)
from noveland.providers.secrets import REDACTED, SENSITIVE_KEYS, reject_sensitive_config
from noveland.providers.service import ProviderExecutionService
from noveland.speech.models import AgentVoiceProfileBinding, SpeechStyleMapping, VoiceProfile
from noveland.speech.voice_profiles import SpeechValidationError, VoiceProfileService
from noveland.visual.models import CharacterSpriteSet, CharacterSpriteVariant
from noveland.worlds.beta import LivingWorldBetaService
from noveland.worlds.gm import LivingWorldGMService
from noveland.worlds.guardrails import LivingWorldGuardrailService
from noveland.worlds.living_context import LivingWorldContextPack, LivingWorldContextSelector
from noveland.worlds.models import (
    EndingCandidate,
    GMEventProposal,
    LongRunEvalRun,
    NarrativeContinuityReview,
    PlayerChoiceRecord,
    RouteAffinity,
    RouteMilestone,
    Worldline,
)
from noveland.worlds.worldlines import worldline_or_404
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .contracts import (
    MemoryPersonaQAFinding,
    MemoryPersonaQAReport,
    MemoryPersonaQARequest,
    NarrativeQualityAlignmentFinding,
    NarrativeQualityConflictReport,
    NarrativeQualityContextKind,
    NarrativeQualityContextPreview,
    NarrativeQualityContextPreviewRequest,
    NarrativeQualityContinuityFinding,
    NarrativeQualityContinuityReviewRequest,
    NarrativeQualityContinuityReviewResult,
    NarrativeQualityDashboardRecommendation,
    NarrativeQualityDashboardSignal,
    NarrativeQualityDashboardSummary,
    NarrativeQualityDialogueFinding,
    NarrativeQualityDialogueReviewRequest,
    NarrativeQualityDialogueReviewResult,
    NarrativeQualityEvidenceRef,
    NarrativeQualityGMImportance,
    NarrativeQualityGMProposalCandidate,
    NarrativeQualityGMProposalGenerateRequest,
    NarrativeQualityGMProposalGenerationResult,
    NarrativeQualityInvocationRef,
    NarrativeQualityLongRunEvalResult,
    NarrativeQualityLongRunEvalRunRequest,
    NarrativeQualityLongRunFailureReport,
    NarrativeQualityPacingFinding,
    NarrativeQualityPacingRecommendation,
    NarrativeQualityPacingReviewRequest,
    NarrativeQualityPacingReviewResult,
    NarrativeQualityPresentationAlignmentRequest,
    NarrativeQualityPresentationAlignmentResult,
    NarrativeQualityProgressionFinding,
    NarrativeQualityProgressionRecommendation,
    NarrativeQualityProgressionReviewRequest,
    NarrativeQualityProgressionReviewResult,
    NarrativeQualityProviderRef,
    NarrativeQualityRepairSuggestion,
    NarrativeQualitySuggestedFix,
    NarrativeQualityWriterGenerateRequest,
    NarrativeQualityWriterGenerationResult,
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
PENDING_MEDIA_JOB_STATUSES = {"queued", "running"}


class NarrativeQualityValidationError(ValueError):
    pass


class NarrativeQualityService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._selector = LivingWorldContextSelector(session)
        self._conversation_service = ConversationService(session)
        self._presentation_service = ConversationPresentationService(session)

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
        provider = self._resolve_text_provider(
            world_id,
            provider_id=request.provider_id,
            capability_key=request.capability_key,
        )
        self._validate_text_provider(provider, source="provider-backed GM proposal")
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

    def review_presentation_alignment(
        self,
        world_id: uuid.UUID,
        request: NarrativeQualityPresentationAlignmentRequest,
    ) -> NarrativeQualityPresentationAlignmentResult:
        worldline = worldline_or_404(self._session, world_id, request.worldline_id)
        conversation = self._conversation_session_or_error(
            world_id,
            worldline.id,
            request.conversation_id,
        )
        turn = self._turn_or_error(world_id, conversation.id, request.turn_id)
        presentation = self._presentation_service.get_presentation(
            world_id,
            conversation.id,
            turn.id,
        )
        evidence_refs = [
            NarrativeQualityEvidenceRef(kind="conversation", id=str(conversation.id)),
            NarrativeQualityEvidenceRef(kind="turn", id=str(turn.id)),
            NarrativeQualityEvidenceRef(kind="worldline", id=str(worldline.id)),
        ]
        findings: list[NarrativeQualityAlignmentFinding] = []
        suggested_fixes: list[NarrativeQualitySuggestedFix] = []
        diagnostics: dict[str, Any] = {
            "context_kind": "presentation_alignment",
            "presentation_found": presentation is not None,
            "allow_missing_assets": request.allow_missing_assets,
        }
        if presentation is None:
            findings.append(
                _alignment_finding(
                    "missing_presentation",
                    "error",
                    "Conversation turn has no presentation record to align.",
                    evidence_refs=evidence_refs,
                )
            )
            suggested_fixes.append(
                NarrativeQualitySuggestedFix(
                    code="create_turn_presentation",
                    message="Create a turn presentation before running alignment diagnostics.",
                    target_ref=NarrativeQualityEvidenceRef(kind="turn", id=str(turn.id)),
                    patch_json={"turn_id": str(turn.id), "render_state": "draft"},
                )
            )
            return _alignment_result(
                world_id=world_id,
                worldline_id=worldline.id,
                conversation_id=conversation.id,
                turn_id=turn.id,
                findings=findings,
                suggested_fixes=suggested_fixes,
                evidence_refs=evidence_refs,
                diagnostics=diagnostics,
            )
        if presentation.worldline_id != worldline.id:
            raise NarrativeQualityValidationError("presentation does not belong to worldline")
        if presentation.speaker_agent_id is not None:
            evidence_refs.append(
                NarrativeQualityEvidenceRef(kind="agent", id=str(presentation.speaker_agent_id))
            )
        speaker_agent_id = presentation.speaker_agent_id or turn.speaker_agent_id
        emotion_key = _normalize_alignment_key(presentation.emotion_key)
        sprite_set: CharacterSpriteSet | None = None
        sprite_variant: CharacterSpriteVariant | None = None
        voice_profile: VoiceProfile | None = None
        voice_binding: AgentVoiceProfileBinding | None = None
        if emotion_key is None:
            findings.append(
                _missing_alignment_finding(
                    "missing_emotion",
                    request.allow_missing_assets,
                    "Presentation has no emotion key for visual or speech alignment.",
                    evidence_refs,
                )
            )
            suggested_fixes.append(
                NarrativeQualitySuggestedFix(
                    code="set_emotion_key",
                    message="Set emotion_key to a normalized value such as neutral.",
                    target_ref=NarrativeQualityEvidenceRef(
                        kind="presentation",
                        id=str(presentation.id),
                    ),
                    patch_json={"emotion_key": "neutral"},
                )
            )
        if presentation.speaker_agent_id is not None and turn.speaker_agent_id is not None:
            if presentation.speaker_agent_id != turn.speaker_agent_id:
                findings.append(
                    _alignment_finding(
                        "speaker_mismatch",
                        "error",
                        "Presentation speaker does not match the conversation turn speaker.",
                        evidence_refs=evidence_refs,
                    )
                )
        if presentation.sprite_set_id is None:
            findings.append(
                _missing_alignment_finding(
                    "missing_sprite_set",
                    request.allow_missing_assets,
                    "Presentation has no sprite set reference.",
                    evidence_refs,
                )
            )
        else:
            sprite_set = self._sprite_set_or_error(
                world_id,
                worldline.id,
                presentation.sprite_set_id,
            )
            evidence_refs.append(
                NarrativeQualityEvidenceRef(kind="sprite_set", id=str(sprite_set.id))
            )
            if speaker_agent_id is not None and sprite_set.agent_id != speaker_agent_id:
                findings.append(
                    _alignment_finding(
                        "sprite_set_agent_mismatch",
                        "error",
                        "Sprite set is bound to a different agent than the turn speaker.",
                        evidence_refs=[
                            NarrativeQualityEvidenceRef(kind="sprite_set", id=str(sprite_set.id)),
                            NarrativeQualityEvidenceRef(kind="agent", id=str(speaker_agent_id)),
                        ],
                    )
                )
        if presentation.sprite_variant_id is None:
            findings.append(
                _missing_alignment_finding(
                    "missing_sprite_variant",
                    request.allow_missing_assets,
                    "Presentation has no sprite variant reference.",
                    evidence_refs,
                )
            )
            if sprite_set is not None:
                fallback_id = sprite_set.default_variant_id or self._neutral_variant_id(
                    sprite_set.id,
                )
                if fallback_id is not None:
                    suggested_fixes.append(
                        NarrativeQualitySuggestedFix(
                            code="use_default_sprite_variant",
                            message="Use the sprite set default or neutral variant as fallback.",
                            target_ref=NarrativeQualityEvidenceRef(
                                kind="presentation",
                                id=str(presentation.id),
                            ),
                            patch_json={"sprite_variant_id": str(fallback_id)},
                        )
                    )
        else:
            sprite_variant = self._sprite_variant_or_error(
                world_id,
                worldline.id,
                presentation.sprite_variant_id,
            )
            evidence_refs.append(
                NarrativeQualityEvidenceRef(kind="sprite_variant", id=str(sprite_variant.id))
            )
            if sprite_set is not None and sprite_variant.sprite_set_id != sprite_set.id:
                findings.append(
                    _alignment_finding(
                        "sprite_variant_set_mismatch",
                        "error",
                        "Sprite variant does not belong to the presentation sprite set.",
                        evidence_refs=[
                            NarrativeQualityEvidenceRef(kind="sprite_set", id=str(sprite_set.id)),
                            NarrativeQualityEvidenceRef(
                                kind="sprite_variant",
                                id=str(sprite_variant.id),
                            ),
                        ],
                    )
                )
            if emotion_key is not None and not _sprite_covers_emotion(
                sprite_variant,
                emotion_key,
            ):
                findings.append(
                    _alignment_finding(
                        "sprite_emotion_mismatch",
                        "warning",
                        "Sprite variant expression or mood tags do not cover the emotion key.",
                        evidence_refs=[
                            NarrativeQualityEvidenceRef(
                                kind="sprite_variant",
                                id=str(sprite_variant.id),
                            )
                        ],
                    )
                )
                exact_variant_id = self._matching_variant_id(
                    world_id,
                    worldline.id,
                    sprite_variant.sprite_set_id,
                    emotion_key,
                )
                if exact_variant_id is not None:
                    suggested_fixes.append(
                        NarrativeQualitySuggestedFix(
                            code="use_matching_sprite_variant",
                            message=(
                                "Use a sprite variant whose expression or mood tags match "
                                "emotion_key."
                            ),
                            target_ref=NarrativeQualityEvidenceRef(
                                kind="presentation",
                                id=str(presentation.id),
                            ),
                            patch_json={"sprite_variant_id": str(exact_variant_id)},
                        )
                    )
        if presentation.voice_profile_id is None:
            findings.append(
                _missing_alignment_finding(
                    "missing_voice_profile",
                    request.allow_missing_assets,
                    "Presentation has no voice profile reference.",
                    evidence_refs,
                )
            )
            if speaker_agent_id is not None:
                try:
                    resolved_profile, binding = VoiceProfileService(
                        self._session
                    ).resolve_agent_default(
                        world_id,
                        speaker_agent_id,
                        worldline.id,
                    )
                except SpeechValidationError:
                    binding = None
                    resolved_profile = None
                if resolved_profile is None:
                    findings.append(
                        _missing_alignment_finding(
                            "missing_voice_binding",
                            request.allow_missing_assets,
                            "Turn speaker has no default voice binding for this worldline.",
                            evidence_refs,
                        )
                    )
                else:
                    voice_binding = (
                        None
                        if binding is None
                        else self._voice_binding_or_error(world_id, worldline.id, binding.id)
                    )
                    suggested_fixes.append(
                        NarrativeQualitySuggestedFix(
                            code="use_default_voice_profile",
                            message="Use the speaker default voice profile for this presentation.",
                            target_ref=NarrativeQualityEvidenceRef(
                                kind="presentation",
                                id=str(presentation.id),
                            ),
                            patch_json={"voice_profile_id": str(resolved_profile.id)},
                        )
                    )
        else:
            voice_profile = self._voice_profile_or_error(
                world_id,
                worldline.id,
                presentation.voice_profile_id,
            )
            evidence_refs.append(
                NarrativeQualityEvidenceRef(kind="voice_profile", id=str(voice_profile.id))
            )
            if voice_profile.status != "active":
                findings.append(
                    _alignment_finding(
                        "voice_profile_inactive",
                        "warning",
                        "Presentation voice profile is not active.",
                        evidence_refs=[
                            NarrativeQualityEvidenceRef(
                                kind="voice_profile",
                                id=str(voice_profile.id),
                            )
                        ],
                    )
                )
            if speaker_agent_id is not None:
                voice_binding = self._voice_binding_for_profile(
                    world_id,
                    worldline.id,
                    speaker_agent_id,
                    voice_profile.id,
                )
                if voice_binding is None:
                    findings.append(
                        _missing_alignment_finding(
                            "missing_voice_binding",
                            request.allow_missing_assets,
                            "Voice profile is not bound to the turn speaker in this worldline.",
                            evidence_refs,
                        )
                    )
                else:
                    evidence_refs.append(
                        NarrativeQualityEvidenceRef(
                            kind="voice_binding",
                            id=str(voice_binding.id),
                        )
                    )
        style_available = False
        if emotion_key is not None and request.expected_tts_provider_kind is not None:
            style_available = self._has_speech_style_mapping(
                world_id,
                provider_kind=request.expected_tts_provider_kind.value,
                emotion_key=emotion_key,
            )
            if not style_available:
                findings.append(
                    _alignment_finding(
                        "missing_speech_style_mapping",
                        "info",
                        "No speech style mapping exists for the expected TTS provider and emotion.",
                        evidence_refs=evidence_refs,
                    )
                )
        diagnostics.update(
            {
                "speaker_agent_id": None if speaker_agent_id is None else str(speaker_agent_id),
                "sprite_set_checked": sprite_set is not None,
                "sprite_variant_checked": sprite_variant is not None,
                "voice_profile_checked": voice_profile is not None,
                "voice_binding_checked": voice_binding is not None,
                "speech_style_mapping_available": style_available,
                "finding_count": len(findings),
            }
        )
        return _alignment_result(
            world_id=world_id,
            worldline_id=worldline.id,
            conversation_id=conversation.id,
            turn_id=turn.id,
            emotion_key=emotion_key,
            sprite_variant_id=presentation.sprite_variant_id,
            voice_profile_id=presentation.voice_profile_id,
            findings=findings,
            suggested_fixes=suggested_fixes,
            evidence_refs=evidence_refs,
            diagnostics=diagnostics,
        )

    def generate_narrative_v2(
        self,
        world_id: uuid.UUID,
        request: NarrativeQualityWriterGenerateRequest,
        *,
        actor_ref: str,
    ) -> NarrativeQualityWriterGenerationResult:
        worldline = worldline_or_404(self._session, world_id, request.worldline_id)
        reject_sensitive_config(
            request.provider_request_json,
            field_name="provider_request_json",
        )
        provider = self._resolve_text_provider(
            world_id,
            provider_id=request.provider_id,
            capability_key=request.capability_key,
        )
        self._validate_text_provider(provider, source="Narrative Writer v2")
        conversation: ConversationSessionRecord | None = None
        turns: list[ConversationTurnRecord] = []
        if request.conversation_id is not None:
            conversation = self._conversation_session_or_error(
                world_id,
                worldline.id,
                request.conversation_id,
            )
            turns = self._conversation_service.list_turns(world_id, conversation.id)
        context_pack = self._context_pack(world_id, worldline.id, request.context_limit)
        prompt_text = _narrative_writer_prompt(
            request,
            context_pack=context_pack,
            conversation=conversation,
            turns=turns[-request.context_limit :],
        )
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
                    "context_kind": "narrative",
                    "artifact_kind": request.artifact_kind.value,
                    "prompt_goal": _safe_text(request.prompt_goal),
                    "worldline_id": str(worldline.id),
                    "conversation_id": None
                    if conversation is None
                    else str(conversation.id),
                },
                request_json={
                    **dict(request.provider_request_json),
                    "operation": "narrative_writer_v2_generation",
                    "context_kind": "narrative",
                    "context_limit": request.context_limit,
                    "artifact_kind": request.artifact_kind.value,
                    "narrative_quality_phase": "v0.6.5",
                },
                actor_ref=actor_ref,
            )
        )
        content = _safe_generated_text(result.output_text, result.output_json)
        artifact = None
        if not request.dry_run:
            artifact = NarrativeArtifactService(self._session).create_artifact(
                NarrativeArtifactCreate(
                    world_id=world_id,
                    worldline_id=worldline.id,
                    source_conversation_id=None if conversation is None else conversation.id,
                    title=_narrative_writer_title(request, conversation),
                    content=content,
                    artifact_kind=request.artifact_kind,
                    metadata=_sanitize_json(
                        {
                            "source": "narrative_writer_v2",
                            "phase": "v0.6.5",
                            "worldline_id": str(worldline.id),
                            "conversation_id": None
                            if conversation is None
                            else str(conversation.id),
                            "model_invocation_id": str(result.invocation.id),
                            "provider_id": str(provider.id),
                            "provider_kind": provider.provider_kind.value,
                            "adapter_kind": provider.adapter_kind.value,
                            "artifact_kind": request.artifact_kind.value,
                            "source_turn_count": len(turns),
                            "context_limit": request.context_limit,
                            "dry_run": False,
                            "prompt_goal_summary": _safe_text(_clip(request.prompt_goal, 500)),
                        }
                    ),
                )
            )
        evidence_refs = [NarrativeQualityEvidenceRef(kind="worldline", id=str(worldline.id))]
        if conversation is not None:
            evidence_refs.append(
                NarrativeQualityEvidenceRef(kind="conversation", id=str(conversation.id))
            )
        evidence_refs.append(
            NarrativeQualityEvidenceRef(kind="invocation", id=str(result.invocation.id))
        )
        if artifact is not None:
            evidence_refs.append(
                NarrativeQualityEvidenceRef(kind="narrative_artifact", id=str(artifact.id))
            )
        return NarrativeQualityWriterGenerationResult(
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
            artifact=artifact,
            evidence_refs=evidence_refs,
            diagnostics=_sanitize_json(
                {
                    "context_kind": "narrative",
                    "artifact_persisted": artifact is not None,
                    "artifact_kind": request.artifact_kind.value,
                    "conversation_turn_count": len(turns),
                    "context_pack": context_pack.to_metadata(),
                    "provider_output_available": bool(result.output_text or result.output_json),
                    "publication_created": False,
                }
            ),
        )

    def review_continuity_v2(
        self,
        world_id: uuid.UUID,
        request: NarrativeQualityContinuityReviewRequest,
    ) -> NarrativeQualityContinuityReviewResult:
        worldline = worldline_or_404(self._session, world_id, request.worldline_id)
        try:
            reject_sensitive_config(request.metadata, field_name="metadata")
        except ValueError as exc:
            raise NarrativeQualityValidationError(str(exc)) from exc
        artifact = None
        if request.artifact_id is not None:
            artifact = self._artifact_or_error(world_id, worldline.id, request.artifact_id)
        reviewed_text = request.reviewed_text
        if reviewed_text is None and artifact is not None:
            reviewed_text = artifact.content
        if reviewed_text is None or reviewed_text.strip() == "":
            raise NarrativeQualityValidationError("continuity review requires text")
        metadata = _sanitize_json(
            {
                **dict(request.metadata),
                "source": "continuity_review_v2",
                "phase": "v0.6.6",
                "worldline_id": str(worldline.id),
                "context_limit": request.context_limit,
                "artifact_id": None if artifact is None else str(artifact.id),
                "artifact_worldline_id": None
                if artifact is None or artifact.worldline_id is None
                else str(artifact.worldline_id),
                "legacy_metadata_worldline_id": None
                if artifact is None
                else str(_metadata_worldline_id(artifact) or ""),
            }
        )
        review = LivingWorldGuardrailService(self._session).review_narrative_continuity(
            world_id=world_id,
            worldline_id=worldline.id,
            artifact_id=request.artifact_id,
            source_kind=request.source_kind,
            source_ref=request.source_ref,
            reviewed_text=reviewed_text,
            metadata=metadata,
        )
        evidence_refs = [
            NarrativeQualityEvidenceRef(kind="worldline", id=str(worldline.id)),
            NarrativeQualityEvidenceRef(kind="continuity_review", id=str(review.id)),
        ]
        if artifact is not None:
            evidence_refs.append(
                NarrativeQualityEvidenceRef(kind="narrative_artifact", id=str(artifact.id))
            )
        findings = _continuity_findings(review, evidence_refs=evidence_refs)
        conflict_reports = self._continuity_conflicts(
            review,
            world_id=world_id,
            worldline_id=worldline.id,
            reviewed_text=reviewed_text,
            metadata=request.metadata,
            evidence_refs=evidence_refs,
        )
        repair_suggestions = _continuity_repair_suggestions(
            findings,
            conflict_reports,
            evidence_refs=evidence_refs,
        )
        return NarrativeQualityContinuityReviewResult(
            world_id=world_id,
            worldline_id=worldline.id,
            review_id=review.id,
            artifact_id=review.artifact_id,
            source_kind=review.source_kind,
            source_ref=review.source_ref,
            review_status=review.status,
            findings=findings,
            conflict_reports=conflict_reports,
            repair_suggestions=repair_suggestions,
            evidence_refs=evidence_refs,
            diagnostics=_sanitize_json(
                {
                    "context_kind": "continuity_review",
                    "context_limit": request.context_limit,
                    "artifact_reviewed": artifact is not None,
                    "explicit_text_reviewed": request.reviewed_text is not None,
                    "finding_count": len(findings),
                    "conflict_count": len(conflict_reports),
                    "repair_suggestion_count": len(repair_suggestions),
                    "persisted_review_id": str(review.id),
                    "world_event_written": False,
                }
            ),
        )

    def review_runtime_pacing(
        self,
        world_id: uuid.UUID,
        request: NarrativeQualityPacingReviewRequest,
    ) -> NarrativeQualityPacingReviewResult:
        worldline = worldline_or_404(self._session, world_id, request.worldline_id)
        policy = None
        if request.policy_id is not None:
            policy = self._pacing_policy_or_error(world_id, worldline.id, request.policy_id)
        conversation = None
        if request.conversation_id is not None:
            conversation = self._conversation_model_or_error(
                world_id,
                worldline.id,
                request.conversation_id,
            )
        current_turn = None
        if request.current_turn_id is not None:
            current_turn = self._turn_model_or_error(
                world_id,
                worldline.id,
                request.current_turn_id,
            )
            if conversation is not None and current_turn.session_id != conversation.id:
                raise NarrativeQualityValidationError("turn does not belong to conversation")
        max_pending_jobs = _limit_from_policy(
            request.max_pending_jobs,
            policy.rules_json if policy is not None else None,
            "max_pending_jobs",
        )
        max_pending_cost = _float_limit_from_policy(
            request.max_pending_cost,
            policy.budget_json if policy is not None else None,
            "max_pending_cost",
            "max_total_estimated_cost",
        )
        media_jobs = self._pending_media_jobs(world_id, worldline.id, conversation, current_turn)
        proposals = self._pending_asset_proposals(world_id, worldline.id, conversation)
        queue_summary = _pacing_queue_summary(media_jobs)
        budget_summary = _pacing_budget_summary(proposals, max_pending_cost=max_pending_cost)
        lookahead_summary = self._pacing_lookahead_summary(
            world_id,
            worldline.id,
            conversation,
            current_turn,
            lookahead_turns=request.lookahead_turns,
        )
        offscreen_summary = self._pacing_offscreen_summary(
            world_id,
            worldline.id,
            conversation,
            include_offscreen=request.include_offscreen,
        )
        evidence_refs = [NarrativeQualityEvidenceRef(kind="worldline", id=str(worldline.id))]
        if policy is not None:
            evidence_refs.append(
                NarrativeQualityEvidenceRef(kind="pacing_policy", id=str(policy.id))
            )
        if conversation is not None:
            evidence_refs.append(
                NarrativeQualityEvidenceRef(kind="conversation", id=str(conversation.id))
            )
        if current_turn is not None:
            evidence_refs.append(NarrativeQualityEvidenceRef(kind="turn", id=str(current_turn.id)))
        findings = _pacing_findings(
            queue_summary=queue_summary,
            budget_summary=budget_summary,
            lookahead_summary=lookahead_summary,
            offscreen_summary=offscreen_summary,
            max_pending_jobs=max_pending_jobs,
            max_pending_cost=max_pending_cost,
            policy=policy,
            evidence_refs=evidence_refs,
        )
        recommendations = _pacing_recommendations(
            queue_summary=queue_summary,
            budget_summary=budget_summary,
            lookahead_summary=lookahead_summary,
            offscreen_summary=offscreen_summary,
            evidence_refs=evidence_refs,
        )
        status = "pass"
        if any(finding.severity == "error" for finding in findings):
            status = "fail"
        elif any(finding.severity == "warning" for finding in findings):
            status = "warning"
        return NarrativeQualityPacingReviewResult(
            world_id=world_id,
            worldline_id=worldline.id,
            conversation_id=None if conversation is None else conversation.id,
            current_turn_id=None if current_turn is None else current_turn.id,
            policy_id=None if policy is None else policy.id,
            pacing_status=status,
            queue_summary=_sanitize_json(queue_summary),
            budget_summary=_sanitize_json(budget_summary),
            lookahead_summary=_sanitize_json(lookahead_summary),
            offscreen_summary=_sanitize_json(offscreen_summary),
            findings=findings,
            recommendations=recommendations,
            evidence_refs=evidence_refs,
            diagnostics=_sanitize_json(
                {
                    "context_kind": "runtime_pacing",
                    "policy_status": None if policy is None else policy.status,
                    "media_job_mutation_count": 0,
                    "asset_generation_mutation_count": 0,
                    "provider_call_count": 0,
                    "world_event_written": False,
                }
            ),
        )

    def review_route_relationship_progression(
        self,
        world_id: uuid.UUID,
        request: NarrativeQualityProgressionReviewRequest,
    ) -> NarrativeQualityProgressionReviewResult:
        worldline = worldline_or_404(self._session, world_id, request.worldline_id)
        agent = None
        if request.agent_id is not None:
            agent = self._agent_or_error(world_id, request.agent_id)
        route = None
        if request.route_affinity_id is not None:
            route = self._route_affinity_or_error(
                world_id,
                worldline.id,
                request.route_affinity_id,
            )
            if agent is not None and route.agent_id != agent.id:
                raise NarrativeQualityValidationError("route does not belong to agent")
        relationships = (
            self._relationship_edges(world_id, worldline.id, agent)
            if request.include_relationships
            else []
        )
        routes = (
            self._route_affinities(world_id, worldline.id, agent, route)
            if request.include_routes
            else []
        )
        milestones = (
            self._route_milestones(world_id, worldline.id, agent, routes)
            if request.include_routes
            else []
        )
        endings = (
            self._ending_candidates(world_id, worldline.id, agent, routes)
            if request.include_routes
            else []
        )
        choices = (
            self._player_choice_records(world_id, worldline.id, routes)
            if request.include_routes
            else []
        )
        events = (
            self._recent_progression_events(
                world_id,
                worldline.id,
                limit=request.recent_event_limit,
            )
            if request.include_events
            else []
        )
        proposals = (
            self._progression_gm_proposals(world_id, worldline.id, agent)
            if request.include_proposals
            else []
        )
        evidence_refs = [NarrativeQualityEvidenceRef(kind="worldline", id=str(worldline.id))]
        if agent is not None:
            evidence_refs.append(NarrativeQualityEvidenceRef(kind="agent", id=str(agent.id)))
        if route is not None:
            evidence_refs.append(NarrativeQualityEvidenceRef(kind="route", id=str(route.id)))
        relationship_summary = _progression_relationship_summary(relationships)
        route_summary = _progression_route_summary(
            routes,
            milestones,
            endings,
            choices,
        )
        event_summary = _progression_event_summary(events)
        proposal_summary = _progression_proposal_summary(proposals)
        findings = _progression_findings(
            relationships=relationships,
            routes=routes,
            milestones=milestones,
            endings=endings,
            events=events,
            proposals=proposals,
            relationship_summary=relationship_summary,
            route_summary=route_summary,
            evidence_refs=evidence_refs,
        )
        recommendations = _progression_recommendations(
            findings,
            evidence_refs=evidence_refs,
        )
        status = "pass"
        if any(finding.severity == "error" for finding in findings):
            status = "fail"
        elif any(finding.severity == "warning" for finding in findings):
            status = "warning"
        return NarrativeQualityProgressionReviewResult(
            world_id=world_id,
            worldline_id=worldline.id,
            agent_id=None if agent is None else agent.id,
            route_affinity_id=None if route is None else route.id,
            progression_status=status,
            relationship_summary=_sanitize_json(relationship_summary),
            route_summary=_sanitize_json(route_summary),
            event_summary=_sanitize_json(event_summary),
            proposal_summary=_sanitize_json(proposal_summary),
            findings=findings,
            recommendations=recommendations,
            evidence_refs=evidence_refs,
            diagnostics=_sanitize_json(
                {
                    "context_kind": "route_relationship_progression",
                    "include_relationships": request.include_relationships,
                    "include_routes": request.include_routes,
                    "include_events": request.include_events,
                    "include_proposals": request.include_proposals,
                    "recent_event_limit": request.recent_event_limit,
                    "relationship_mutation_count": 0,
                    "route_mutation_count": 0,
                    "provider_call_count": 0,
                    "world_event_written": False,
                }
            ),
        )

    def run_long_living_world_eval(
        self,
        world_id: uuid.UUID,
        request: NarrativeQualityLongRunEvalRunRequest,
    ) -> NarrativeQualityLongRunEvalResult:
        worldline = worldline_or_404(self._session, world_id, request.worldline_id)
        try:
            reject_sensitive_config(request.metadata, field_name="metadata")
        except ValueError as exc:
            raise NarrativeQualityValidationError(str(exc)) from exc
        run = LivingWorldBetaService(self._session).run_long_eval(
            world_id=world_id,
            worldline_id=worldline.id,
            eval_key=request.eval_key,
            horizon_days=request.horizon_days,
            metadata=_sanitize_json(
                {
                    **dict(request.metadata),
                    "source": "narrative_quality_long_run_eval",
                    "phase": "v0.6.9",
                    "worldline_id": str(worldline.id),
                    "provider_call_count": 0,
                    "daemon_run": False,
                }
            ),
        )
        return _long_run_quality_result(run)

    def list_long_living_world_evals(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        *,
        limit: int,
    ) -> list[NarrativeQualityLongRunEvalResult]:
        worldline = worldline_or_404(self._session, world_id, worldline_id)
        runs = self._session.scalars(
            select(LongRunEvalRun)
            .where(
                LongRunEvalRun.world_id == world_id,
                LongRunEvalRun.worldline_id == worldline.id,
            )
            .order_by(LongRunEvalRun.created_at.desc())
            .limit(limit)
        ).all()
        return [_long_run_quality_result(run) for run in runs]

    def get_long_living_world_eval(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
        run_id: uuid.UUID,
    ) -> NarrativeQualityLongRunEvalResult:
        worldline = worldline_or_404(self._session, world_id, worldline_id)
        run = self._session.get(LongRunEvalRun, run_id)
        if run is None or run.world_id != world_id or run.worldline_id != worldline.id:
            raise NarrativeQualityValidationError("long-run eval not found in worldline")
        return _long_run_quality_result(run)

    def dashboard_summary(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
    ) -> NarrativeQualityDashboardSummary:
        worldline = worldline_or_404(self._session, world_id, worldline_id)
        evidence_refs = [NarrativeQualityEvidenceRef(kind="worldline", id=str(worldline.id))]
        metrics = _sanitize_json(
            {
                "providers": self._dashboard_provider_metrics(world_id),
                "invocations": self._dashboard_invocation_metrics(world_id, worldline.id),
                "gm_proposals": self._dashboard_gm_proposal_metrics(world_id, worldline.id),
                "dialogue": self._dashboard_dialogue_metrics(world_id, worldline.id),
                "presentation_alignment": self._dashboard_presentation_metrics(
                    world_id,
                    worldline.id,
                ),
                "narrative_writer": self._dashboard_narrative_writer_metrics(
                    world_id,
                    worldline.id,
                ),
                "continuity": self._dashboard_continuity_metrics(world_id, worldline.id),
                "pacing": self._dashboard_pacing_metrics(world_id, worldline.id),
                "progression": self._dashboard_progression_metrics(world_id, worldline.id),
                "long_run": self._dashboard_long_run_metrics(world_id, worldline.id),
                "world_events": self._dashboard_world_event_metrics(world_id, worldline.id),
            }
        )
        blockers = _dashboard_blockers(metrics, evidence_refs=evidence_refs)
        warnings = _dashboard_warnings(metrics, evidence_refs=evidence_refs)
        recommendations = _dashboard_recommendations(
            blockers,
            warnings,
            evidence_refs=evidence_refs,
        )
        quality_status = "pass"
        if blockers:
            quality_status = "fail"
        elif warnings:
            quality_status = "warning"
        summary = _sanitize_json(
            {
                "status": quality_status,
                "blocker_count": len(blockers),
                "warning_count": len(warnings),
                "recommendation_count": len(recommendations),
                "provider_ready": _int_value(
                    _dict_value(metrics.get("providers")).get("active_text_provider_count")
                )
                > 0,
                "long_run_eval_available": _dict_value(metrics.get("long_run")).get(
                    "latest_run_id"
                )
                is not None,
                "world_event_leak_count": _int_value(
                    _dict_value(metrics.get("world_events")).get("unsafe_payload_event_count")
                ),
                "provider_call_count": 0,
                "mutation_count": 0,
            }
        )
        return NarrativeQualityDashboardSummary(
            world_id=world_id,
            worldline_id=worldline.id,
            quality_status=quality_status,
            summary=summary,
            metrics=metrics,
            blockers=blockers,
            warnings=warnings,
            recommendations=recommendations,
            evidence_refs=evidence_refs,
            diagnostics=_sanitize_json(
                {
                    "context_kind": "narrative_quality_dashboard_api",
                    "source": "narrative_quality_dashboard_api",
                    "phase": "v0.6.10",
                    "provider_call_count": 0,
                    "mutation_count": 0,
                    "world_event_written": False,
                    "web_dashboard_required": False,
                }
            ),
            generated_at=datetime.now(UTC),
        )

    def run_memory_persona_qa(
        self,
        world_id: uuid.UUID,
        request: MemoryPersonaQARequest,
    ) -> MemoryPersonaQAReport:
        worldline = worldline_or_404(self._session, world_id, request.worldline_id)
        conversation = self._qa_conversation(world_id, worldline.id, request.conversation_id)
        agents = self._qa_agents(
            world_id,
            conversation_id=None if conversation is None else conversation.id,
            requested_agent_ids=request.agent_ids,
            limit=request.agent_limit,
        )
        findings: list[MemoryPersonaQAFinding] = []
        if not agents:
            findings.append(
                MemoryPersonaQAFinding(
                    code="no_agents_available",
                    severity="blocked",
                    summary="No enabled agents are available for memory/persona QA.",
                    suggested_repair_proposal_types=["persona_repair", "memory_repair"],
                    metadata={"checked_agent_count": 0},
                )
            )
        for agent in agents:
            findings.extend(
                self._qa_agent_findings(
                    world_id,
                    worldline.id,
                    agent,
                    conversation_id=None if conversation is None else conversation.id,
                    recent_turn_limit=request.recent_turn_limit,
                )
            )
        blocker_count = sum(1 for finding in findings if finding.severity == "blocked")
        warning_count = sum(1 for finding in findings if finding.severity == "warning")
        status_text = "blocked" if blocker_count else "watch" if warning_count else "ok"
        return MemoryPersonaQAReport(
            run_id=uuid.uuid4(),
            world_id=world_id,
            worldline_id=worldline.id,
            status=status_text,
            generated_at=datetime.now(UTC),
            finding_count=len(findings),
            blocker_count=blocker_count,
            warning_count=warning_count,
            checked_agent_count=len(agents),
            findings=findings,
            suppressed_fields=[
                "turn_text_bodies",
                "memory_content_bodies",
                "persona_text_bodies",
                "prompt_bodies",
                "provider_output_bodies",
                "prompt_snapshot_details",
                "provider_payloads",
                "storage_paths",
                "resolved_secrets",
            ],
            non_goals=[
                "automatic_persona_mutation",
                "automatic_memory_mutation",
                "reader_player_diagnostics",
                "duplicate_eval_framework",
            ],
        )

    def _qa_conversation(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        conversation_id: uuid.UUID | None,
    ) -> ConversationSession | None:
        if conversation_id is None:
            return None
        conversation = self._session.get(ConversationSession, conversation_id)
        if (
            conversation is None
            or conversation.world_id != world_id
            or conversation.worldline_id != worldline_id
        ):
            raise NarrativeQualityValidationError("conversation not found in worldline")
        return conversation

    def _qa_agents(
        self,
        world_id: uuid.UUID,
        *,
        conversation_id: uuid.UUID | None,
        requested_agent_ids: list[uuid.UUID],
        limit: int,
    ) -> list[Agent]:
        if requested_agent_ids:
            agents: list[Agent] = []
            for agent_id in requested_agent_ids:
                agent = self._session.get(Agent, agent_id)
                if agent is None or agent.world_id != world_id:
                    raise NarrativeQualityValidationError("agent not found in world")
                agents.append(agent)
            return agents[:limit]
        if conversation_id is not None:
            participants = self._session.scalars(
                select(ConversationParticipant)
                .where(
                    ConversationParticipant.session_id == conversation_id,
                    ConversationParticipant.is_enabled.is_(True),
                )
                .order_by(ConversationParticipant.turn_order)
                .limit(limit)
            ).all()
            participant_ids = [participant.agent_id for participant in participants]
            if participant_ids:
                return list(
                    self._session.scalars(
                        select(Agent)
                        .where(Agent.world_id == world_id, Agent.id.in_(participant_ids))
                        .order_by(Agent.agent_key)
                    ).all()
                )
        return list(
            self._session.scalars(
                select(Agent)
                .where(Agent.world_id == world_id, Agent.is_enabled.is_(True))
                .order_by(Agent.agent_key)
                .limit(limit)
            ).all()
        )

    def _qa_agent_findings(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        agent: Agent,
        *,
        conversation_id: uuid.UUID | None,
        recent_turn_limit: int,
    ) -> list[MemoryPersonaQAFinding]:
        persona = self._latest_persona(world_id, agent.id)
        memories = self._agent_memories(world_id, worldline_id, agent.id)
        turns = self._agent_recent_turns(
            world_id,
            worldline_id,
            agent.id,
            conversation_id=conversation_id,
            limit=recent_turn_limit,
        )
        findings: list[MemoryPersonaQAFinding] = []
        if persona is None:
            findings.append(
                _qa_finding(
                    code="persona_missing",
                    severity="blocked",
                    summary="Agent is missing an enabled persona card.",
                    agent_id=agent.id,
                    evidence_refs=[NarrativeQualityEvidenceRef(kind="agent", id=str(agent.id))],
                    suggested_repair_proposal_types=["persona_repair"],
                )
            )
        if not memories:
            findings.append(
                _qa_finding(
                    code="initial_memory_missing",
                    severity="blocked",
                    summary="Agent has no active memory in the selected worldline.",
                    agent_id=agent.id,
                    evidence_refs=[NarrativeQualityEvidenceRef(kind="agent", id=str(agent.id))],
                    suggested_repair_proposal_types=["memory_repair"],
                )
            )
        source_refs = _qa_persona_source_refs(persona)
        for memory in memories:
            source_refs.extend(_qa_memory_source_refs(memory))
        if not source_refs:
            findings.append(
                _qa_finding(
                    code="source_traceability_missing",
                    severity="warning",
                    summary="Persona and memory evidence lack source traceability references.",
                    agent_id=agent.id,
                    evidence_refs=[
                        NarrativeQualityEvidenceRef(kind="agent", id=str(agent.id)),
                    ],
                    suggested_repair_proposal_types=["persona_repair", "memory_repair"],
                )
            )
        contaminated_memories = [
            memory for memory in memories if _memory_contamination_detected(memory)
        ]
        if contaminated_memories:
            findings.append(
                _qa_finding(
                    code="memory_contamination",
                    severity="blocked",
                    summary="Active memory contains contamination markers or QA flags.",
                    agent_id=agent.id,
                    evidence_refs=[
                        NarrativeQualityEvidenceRef(kind="agent_memory_item", id=str(memory.id))
                        for memory in contaminated_memories[:5]
                    ],
                    source_traceability_refs=_dedupe_refs(
                        [
                            ref
                            for memory in contaminated_memories
                            for ref in _qa_memory_source_refs(memory)
                        ]
                    ),
                    suggested_repair_proposal_types=["memory_repair"],
                    metadata={"affected_memory_count": len(contaminated_memories)},
                )
            )
        worldline_contamination = [
            memory
            for memory in memories
            if _worldline_contamination_detected(memory, worldline_id)
        ]
        if worldline_contamination:
            findings.append(
                _qa_finding(
                    code="worldline_contamination",
                    severity="blocked",
                    summary="Active memory references another worldline.",
                    agent_id=agent.id,
                    evidence_refs=[
                        NarrativeQualityEvidenceRef(kind="agent_memory_item", id=str(memory.id))
                        for memory in worldline_contamination[:5]
                    ],
                    source_traceability_refs=_dedupe_refs(
                        [
                            ref
                            for memory in worldline_contamination
                            for ref in _qa_memory_source_refs(memory)
                        ]
                    ),
                    suggested_repair_proposal_types=["memory_repair"],
                    metadata={"affected_memory_count": len(worldline_contamination)},
                )
            )
        drift_turns = [turn for turn in turns if _turn_has_persona_drift_marker(turn)]
        if persona is not None and drift_turns:
            findings.append(
                _qa_finding(
                    code="persona_drift",
                    severity="warning",
                    summary="Recent dialogue includes persona drift markers.",
                    agent_id=agent.id,
                    evidence_refs=[
                        NarrativeQualityEvidenceRef(kind="conversation_turn", id=str(turn.id))
                        for turn in drift_turns[:5]
                    ],
                    source_traceability_refs=_dedupe_refs(source_refs),
                    suggested_repair_proposal_types=["persona_repair", "dialogue_style_repair"],
                    metadata={"affected_turn_count": len(drift_turns)},
                )
            )
        style_turns = [
            turn for turn in turns if persona is not None and _turn_has_style_drift(persona, turn)
        ]
        if style_turns:
            findings.append(
                _qa_finding(
                    code="dialogue_style_drift",
                    severity="warning",
                    summary="Recent dialogue diverges from persona style constraints.",
                    agent_id=agent.id,
                    evidence_refs=[
                        NarrativeQualityEvidenceRef(kind="conversation_turn", id=str(turn.id))
                        for turn in style_turns[:5]
                    ],
                    source_traceability_refs=_dedupe_refs(source_refs),
                    suggested_repair_proposal_types=["dialogue_style_repair"],
                    metadata={"affected_turn_count": len(style_turns)},
                )
            )
        relationship_drift = _relationship_drift_detected(memories, turns)
        if relationship_drift:
            findings.append(
                _qa_finding(
                    code="relationship_drift",
                    severity="warning",
                    summary="Memory or dialogue includes relationship drift markers.",
                    agent_id=agent.id,
                    evidence_refs=[
                        NarrativeQualityEvidenceRef(kind="agent", id=str(agent.id)),
                    ],
                    source_traceability_refs=_dedupe_refs(source_refs),
                    suggested_repair_proposal_types=["memory_repair", "relationship_repair"],
                    metadata={"detected": True},
                )
            )
        return findings

    def _latest_persona(self, world_id: uuid.UUID, agent_id: uuid.UUID) -> AgentPersona | None:
        return self._session.scalars(
            select(AgentPersona)
            .where(
                AgentPersona.world_id == world_id,
                AgentPersona.agent_id == agent_id,
                AgentPersona.is_enabled.is_(True),
                AgentPersona.persona_text != "",
            )
            .order_by(AgentPersona.updated_at.desc())
            .limit(1)
        ).one_or_none()

    def _agent_memories(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        agent_id: uuid.UUID,
    ) -> list[AgentMemoryItem]:
        return list(
            self._session.scalars(
                select(AgentMemoryItem)
                .where(
                    AgentMemoryItem.world_id == world_id,
                    AgentMemoryItem.worldline_id == worldline_id,
                    AgentMemoryItem.agent_id == agent_id,
                    AgentMemoryItem.is_active.is_(True),
                )
                .order_by(AgentMemoryItem.updated_at.desc())
            ).all()
        )

    def _agent_recent_turns(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        agent_id: uuid.UUID,
        *,
        conversation_id: uuid.UUID | None,
        limit: int,
    ) -> list[ConversationTurn]:
        statement = (
            select(ConversationTurn)
            .join(ConversationSession, ConversationSession.id == ConversationTurn.session_id)
            .where(
                ConversationSession.world_id == world_id,
                ConversationSession.worldline_id == worldline_id,
                ConversationTurn.speaker_agent_id == agent_id,
            )
            .order_by(ConversationTurn.created_at.desc())
            .limit(limit)
        )
        if conversation_id is not None:
            statement = statement.where(ConversationTurn.session_id == conversation_id)
        return list(self._session.scalars(statement).all())

    def _dashboard_provider_metrics(self, world_id: uuid.UUID) -> dict[str, Any]:
        providers = list(
            self._session.scalars(
                select(ProviderIntegration)
                .where(
                    (ProviderIntegration.world_id == world_id)
                    | (ProviderIntegration.scope_kind == "global"),
                    ProviderIntegration.status != "deleted",
                )
                .order_by(ProviderIntegration.provider_kind, ProviderIntegration.provider_key)
            ).all()
        )
        provider_ids = [provider.id for provider in providers]
        latest_health_by_provider: dict[uuid.UUID, ProviderHealthCheck] = {}
        if provider_ids:
            health_checks = self._session.scalars(
                select(ProviderHealthCheck)
                .where(ProviderHealthCheck.provider_integration_id.in_(provider_ids))
                .order_by(
                    ProviderHealthCheck.provider_integration_id,
                    ProviderHealthCheck.checked_at.desc(),
                )
            ).all()
            for check in health_checks:
                latest_health_by_provider.setdefault(check.provider_integration_id, check)
        status_counts: dict[str, int] = {}
        provider_kind_counts: dict[str, int] = {}
        adapter_kind_counts: dict[str, int] = {}
        health_status_counts: dict[str, int] = {}
        unsafe_config_count = 0
        unsafe_health_metadata_count = 0
        auth_ref_count = 0
        for provider in providers:
            status_counts[provider.status] = status_counts.get(provider.status, 0) + 1
            provider_kind_counts[provider.provider_kind] = (
                provider_kind_counts.get(provider.provider_kind, 0) + 1
            )
            adapter_kind_counts[provider.adapter_kind] = (
                adapter_kind_counts.get(provider.adapter_kind, 0) + 1
            )
            if provider.auth_ref:
                auth_ref_count += 1
            if _json_contains_leak(provider.config_json) or _json_contains_leak(
                provider.default_params_json
            ):
                unsafe_config_count += 1
            latest_health = latest_health_by_provider.get(provider.id)
            if latest_health is not None:
                health_status_counts[latest_health.status] = (
                    health_status_counts.get(latest_health.status, 0) + 1
                )
                if _json_contains_leak(latest_health.metadata_json) or (
                    latest_health.error_text is not None
                    and _json_contains_leak(latest_health.error_text)
                ):
                    unsafe_health_metadata_count += 1
        return {
            "provider_count": len(providers),
            "active_provider_count": status_counts.get("active", 0),
            "active_text_provider_count": sum(
                1
                for provider in providers
                if provider.status == "active"
                and provider.provider_kind == ProviderKind.TEXT_GENERATION.value
            ),
            "auth_ref_count": auth_ref_count,
            "status_counts": status_counts,
            "provider_kind_counts": provider_kind_counts,
            "adapter_kind_counts": adapter_kind_counts,
            "latest_health_status_counts": health_status_counts,
            "latest_unhealthy_count": health_status_counts.get("unhealthy", 0),
            "latest_degraded_count": health_status_counts.get("degraded", 0),
            "unsafe_provider_config_count": unsafe_config_count,
            "unsafe_health_metadata_count": unsafe_health_metadata_count,
        }

    def _dashboard_invocation_metrics(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
    ) -> dict[str, Any]:
        invocations = list(
            self._session.scalars(
                select(ModelInvocation)
                .where(
                    ModelInvocation.world_id == world_id,
                    ModelInvocation.worldline_id == worldline_id,
                )
                .order_by(ModelInvocation.created_at.desc())
                .limit(500)
            ).all()
        )
        status_counts: dict[str, int] = {}
        kind_counts: dict[str, int] = {}
        provider_kind_counts: dict[str, int] = {}
        estimated_cost = 0.0
        latency_values: list[int] = []
        unsafe_metadata_count = 0
        for invocation in invocations:
            status_counts[invocation.status] = status_counts.get(invocation.status, 0) + 1
            kind_counts[invocation.invocation_kind] = (
                kind_counts.get(invocation.invocation_kind, 0) + 1
            )
            provider_kind_counts[invocation.provider_kind] = (
                provider_kind_counts.get(invocation.provider_kind, 0) + 1
            )
            if invocation.estimated_cost is not None:
                estimated_cost += float(invocation.estimated_cost)
            if invocation.latency_ms is not None:
                latency_values.append(invocation.latency_ms)
            if (
                _json_contains_leak(invocation.request_params_json)
                or _json_contains_leak(invocation.response_metadata_json)
                or _json_contains_leak(invocation.input_json)
                or _json_contains_leak(invocation.output_json)
            ):
                unsafe_metadata_count += 1
        snapshots = list(
            self._session.scalars(
                select(PromptSnapshot)
                .join(ModelInvocation, PromptSnapshot.invocation_id == ModelInvocation.id)
                .where(
                    ModelInvocation.world_id == world_id,
                    ModelInvocation.worldline_id == worldline_id,
                )
                .limit(500)
            ).all()
        )
        return {
            "sampled_invocation_count": len(invocations),
            "status_counts": status_counts,
            "invocation_kind_counts": kind_counts,
            "provider_kind_counts": provider_kind_counts,
            "failed_invocation_count": status_counts.get("failed", 0),
            "estimated_cost_total": round(estimated_cost, 8),
            "average_latency_ms": (
                None if not latency_values else round(sum(latency_values) / len(latency_values))
            ),
            "unsafe_invocation_metadata_count": unsafe_metadata_count,
            "prompt_snapshot_count": len(snapshots),
            "sensitive_prompt_snapshot_count": sum(
                1 for snapshot in snapshots if snapshot.contains_sensitive_context
            ),
            "raw_sensitive_prompt_snapshot_count": sum(
                1
                for snapshot in snapshots
                if snapshot.contains_sensitive_context and snapshot.redaction_status == "raw"
            ),
        }

    def _dashboard_gm_proposal_metrics(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
    ) -> dict[str, Any]:
        proposals = list(
            self._session.scalars(
                select(GMEventProposal).where(
                    GMEventProposal.world_id == world_id,
                    GMEventProposal.worldline_id == worldline_id,
                )
            ).all()
        )
        status_counts: dict[str, int] = {}
        importance_counts: dict[str, int] = {}
        unsafe_payload_count = 0
        provider_backed_count = 0
        high_risk_open_count = 0
        for proposal in proposals:
            status_counts[proposal.status] = status_counts.get(proposal.status, 0) + 1
            importance_counts[proposal.importance] = (
                importance_counts.get(proposal.importance, 0) + 1
            )
            if proposal.status in {"proposed", "accepted"} and proposal.risk_score >= 70:
                high_risk_open_count += 1
            if "model_invocation_id" in proposal.source_context:
                provider_backed_count += 1
            if _json_contains_leak(proposal.proposed_payload) or _json_contains_leak(
                proposal.source_context
            ):
                unsafe_payload_count += 1
        return {
            "proposal_count": len(proposals),
            "status_counts": status_counts,
            "importance_counts": importance_counts,
            "provider_backed_proposal_count": provider_backed_count,
            "high_risk_open_proposal_count": high_risk_open_count,
            "unsafe_payload_count": unsafe_payload_count,
        }

    def _dashboard_dialogue_metrics(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
    ) -> dict[str, Any]:
        conversations = list(
            self._session.scalars(
                select(ConversationSession).where(
                    ConversationSession.world_id == world_id,
                    ConversationSession.worldline_id == worldline_id,
                )
            ).all()
        )
        conversation_ids = [conversation.id for conversation in conversations]
        turns: list[ConversationTurn] = []
        if conversation_ids:
            turns = list(
                self._session.scalars(
                    select(ConversationTurn).where(
                        ConversationTurn.session_id.in_(conversation_ids)
                    )
                ).all()
            )
        return {
            "conversation_count": len(conversations),
            "turn_count": len(turns),
            "agent_turn_count": sum(1 for turn in turns if turn.speaker_kind == "agent"),
            "failed_turn_count": sum(1 for turn in turns if turn.status == "failed"),
            "unsafe_turn_text_count": sum(
                1
                for turn in turns
                if _json_contains_leak(turn.input_text)
                or (turn.output_text is not None and _json_contains_leak(turn.output_text))
            ),
        }

    def _dashboard_presentation_metrics(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
    ) -> dict[str, Any]:
        presentations = list(
            self._session.scalars(
                select(ConversationTurnPresentation).where(
                    ConversationTurnPresentation.world_id == world_id,
                    ConversationTurnPresentation.worldline_id == worldline_id,
                )
            ).all()
        )
        sprite_sets = list(
            self._session.scalars(
                select(CharacterSpriteSet).where(
                    CharacterSpriteSet.world_id == world_id,
                    CharacterSpriteSet.worldline_id == worldline_id,
                    CharacterSpriteSet.status == "active",
                )
            ).all()
        )
        variants = list(
            self._session.scalars(
                select(CharacterSpriteVariant).where(
                    CharacterSpriteVariant.world_id == world_id,
                    CharacterSpriteVariant.worldline_id == worldline_id,
                    CharacterSpriteVariant.status == "active",
                )
            ).all()
        )
        agents = list(
            self._session.scalars(
                select(Agent).where(Agent.world_id == world_id, Agent.is_enabled.is_(True))
            ).all()
        )
        bindings = list(
            self._session.scalars(
                select(AgentVoiceProfileBinding).where(
                    AgentVoiceProfileBinding.world_id == world_id,
                    (
                        (AgentVoiceProfileBinding.worldline_id == worldline_id)
                        | (AgentVoiceProfileBinding.worldline_id.is_(None))
                    ),
                )
            ).all()
        )
        variants_by_set: dict[uuid.UUID, list[CharacterSpriteVariant]] = {}
        for variant in variants:
            variants_by_set.setdefault(variant.sprite_set_id, []).append(variant)
        sprite_sets_missing_default = 0
        for sprite_set in sprite_sets:
            if sprite_set.default_variant_id is not None:
                continue
            if not any(
                variant.expression_key == "neutral"
                for variant in variants_by_set.get(sprite_set.id, [])
            ):
                sprite_sets_missing_default += 1
        bound_agent_ids = {
            binding.agent_id
            for binding in bindings
            if binding.is_default and binding.binding_role == "default"
        }
        render_state_counts: dict[str, int] = {}
        for presentation in presentations:
            render_state_counts[presentation.render_state] = (
                render_state_counts.get(presentation.render_state, 0) + 1
            )
        return {
            "presentation_count": len(presentations),
            "missing_emotion_count": sum(1 for item in presentations if not item.emotion_key),
            "missing_sprite_variant_count": sum(
                1 for item in presentations if item.sprite_variant_id is None
            ),
            "missing_voice_profile_count": sum(
                1 for item in presentations if item.voice_profile_id is None
            ),
            "render_state_counts": render_state_counts,
            "active_sprite_set_count": len(sprite_sets),
            "active_sprite_variant_count": len(variants),
            "sprite_set_missing_default_count": sprite_sets_missing_default,
            "default_voice_binding_count": len(bound_agent_ids),
            "agent_missing_default_voice_binding_count": sum(
                1 for agent in agents if agent.id not in bound_agent_ids
            ),
        }

    def _dashboard_narrative_writer_metrics(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
    ) -> dict[str, Any]:
        artifacts = list(
            self._session.scalars(
                select(NarrativeArtifact)
                .where(
                    NarrativeArtifact.world_id == world_id,
                    NarrativeArtifact.worldline_id == worldline_id,
                )
                .order_by(NarrativeArtifact.created_at.desc())
                .limit(100)
            ).all()
        )
        kind_counts: dict[str, int] = {}
        writer_v2_count = 0
        unsafe_metadata_count = 0
        for artifact in artifacts:
            kind_counts[artifact.artifact_kind] = kind_counts.get(artifact.artifact_kind, 0) + 1
            metadata = artifact.artifact_metadata or {}
            if metadata.get("source") == "narrative_writer_v2":
                writer_v2_count += 1
            if _json_contains_leak(metadata):
                unsafe_metadata_count += 1
        return {
            "sampled_artifact_count": len(artifacts),
            "artifact_kind_counts": kind_counts,
            "writer_v2_artifact_count": writer_v2_count,
            "unsafe_artifact_metadata_count": unsafe_metadata_count,
        }

    def _dashboard_continuity_metrics(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
    ) -> dict[str, Any]:
        reviews = list(
            self._session.scalars(
                select(NarrativeContinuityReview)
                .where(
                    NarrativeContinuityReview.world_id == world_id,
                    NarrativeContinuityReview.worldline_id == worldline_id,
                )
                .order_by(NarrativeContinuityReview.created_at.desc())
                .limit(100)
            ).all()
        )
        status_counts: dict[str, int] = {}
        issue_counts: dict[str, int] = {}
        unsafe_metadata_count = 0
        for review in reviews:
            status_counts[review.status] = status_counts.get(review.status, 0) + 1
            if _json_contains_leak(review.metadata_json):
                unsafe_metadata_count += 1
            for issue in review.issues:
                code = str(issue.get("code") or "continuity_issue")
                issue_counts[code] = issue_counts.get(code, 0) + 1
        return {
            "review_count": len(reviews),
            "status_counts": status_counts,
            "failed_review_count": status_counts.get("fail", 0),
            "warning_review_count": status_counts.get("warning", 0),
            "issue_counts": issue_counts,
            "unsafe_review_metadata_count": unsafe_metadata_count,
        }

    def _dashboard_pacing_metrics(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
    ) -> dict[str, Any]:
        media_jobs = self._pending_media_jobs(world_id, worldline_id, None, None)
        proposals = self._pending_asset_proposals(world_id, worldline_id, None)
        queue_summary = _pacing_queue_summary(media_jobs)
        budget_summary = _pacing_budget_summary(proposals, max_pending_cost=None)
        return {
            "queue_summary": queue_summary,
            "budget_summary": budget_summary,
            "unsafe_media_job_json_count": sum(
                1
                for job in media_jobs
                if _json_contains_leak(job.provider_config_json)
                or _json_contains_leak(job.request_json)
                or _json_contains_leak(job.result_json)
            ),
            "unsafe_asset_proposal_json_count": sum(
                1
                for proposal in proposals
                if _json_contains_leak(proposal.evidence_json)
                or _json_contains_leak(proposal.request_json)
            ),
        }

    def _dashboard_progression_metrics(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
    ) -> dict[str, Any]:
        relationships = self._relationship_edges(world_id, worldline_id, None)
        routes = self._route_affinities(world_id, worldline_id, None, None)
        milestones = self._route_milestones(world_id, worldline_id, None, routes)
        endings = self._ending_candidates(world_id, worldline_id, None, routes)
        choices = self._player_choice_records(world_id, worldline_id, routes)
        events = self._recent_progression_events(world_id, worldline_id, limit=50)
        proposals = self._progression_gm_proposals(world_id, worldline_id, None)
        evidence_refs = [NarrativeQualityEvidenceRef(kind="worldline", id=str(worldline_id))]
        relationship_summary = _progression_relationship_summary(relationships)
        route_summary = _progression_route_summary(routes, milestones, endings, choices)
        event_summary = _progression_event_summary(events)
        proposal_summary = _progression_proposal_summary(proposals)
        findings = _progression_findings(
            relationships=relationships,
            routes=routes,
            milestones=milestones,
            endings=endings,
            events=events,
            proposals=proposals,
            relationship_summary=relationship_summary,
            route_summary=route_summary,
            evidence_refs=evidence_refs,
        )
        return {
            "relationship_summary": relationship_summary,
            "route_summary": route_summary,
            "event_summary": event_summary,
            "proposal_summary": proposal_summary,
            "finding_count": len(findings),
            "error_finding_count": sum(1 for finding in findings if finding.severity == "error"),
            "warning_finding_count": sum(
                1 for finding in findings if finding.severity == "warning"
            ),
        }

    def _dashboard_long_run_metrics(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
    ) -> dict[str, Any]:
        runs = list(
            self._session.scalars(
                select(LongRunEvalRun)
                .where(
                    LongRunEvalRun.world_id == world_id,
                    LongRunEvalRun.worldline_id == worldline_id,
                )
                .order_by(LongRunEvalRun.created_at.desc())
                .limit(20)
            ).all()
        )
        status_counts: dict[str, int] = {}
        for run in runs:
            status_counts[run.status] = status_counts.get(run.status, 0) + 1
        latest = runs[0] if runs else None
        latest_result = None if latest is None else _long_run_quality_result(latest)
        return {
            "run_count": len(runs),
            "status_counts": status_counts,
            "latest_run_id": None if latest is None else str(latest.id),
            "latest_status": None if latest is None else latest.status,
            "latest_eval_key": None if latest is None else _safe_text(latest.eval_key),
            "latest_drift_metrics": {}
            if latest_result is None
            else latest_result.drift_metrics,
            "latest_failure_report_count": 0
            if latest_result is None
            else len(latest_result.failure_reports),
        }

    def _dashboard_world_event_metrics(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
    ) -> dict[str, Any]:
        events = list(
            self._session.scalars(
                select(WorldEventModel)
                .where(
                    WorldEventModel.world_id == world_id,
                    WorldEventModel.worldline_id == worldline_id,
                )
                .order_by(WorldEventModel.sequence.desc())
                .limit(500)
            ).all()
        )
        importance_counts: dict[str, int] = {}
        unsafe_count = 0
        max_sequence = 0
        for event in events:
            importance_counts[event.importance] = importance_counts.get(event.importance, 0) + 1
            max_sequence = max(max_sequence, int(event.sequence))
            if _json_contains_leak(event.payload):
                unsafe_count += 1
        return {
            "sampled_event_count": len(events),
            "importance_counts": importance_counts,
            "latest_sequence": max_sequence,
            "unsafe_payload_event_count": unsafe_count,
        }

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
        *,
        provider_id: uuid.UUID | None,
        capability_key: str | None,
    ) -> ProviderIntegrationRead:
        registry = ProviderRegistryService(self._session)
        try:
            if provider_id is not None:
                provider = registry.get_provider(
                    world_id,
                    provider_id,
                    platform_admin=True,
                    include_hidden=True,
                )
                if provider is None:
                    raise ProviderNotFoundError("provider integration not found")
                return provider
            return registry.resolve_provider_for_capability(
                world_id,
                provider_kind=ProviderKind.TEXT_GENERATION,
                capability_key=capability_key,
            )
        except (ProviderNotFoundError, ProviderValidationError) as exc:
            raise NarrativeQualityValidationError(str(exc)) from exc

    def _validate_text_provider(self, provider: ProviderIntegrationRead, *, source: str) -> None:
        if provider.provider_kind != ProviderKind.TEXT_GENERATION:
            raise NarrativeQualityValidationError(
                f"{source} requires provider_kind=text_generation"
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

    def _artifact_or_error(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        artifact_id: uuid.UUID,
    ) -> NarrativeArtifact:
        artifact = self._session.get(NarrativeArtifact, artifact_id)
        if artifact is None or artifact.world_id != world_id:
            raise NarrativeQualityValidationError("narrative artifact not found")
        if artifact.worldline_id is not None and artifact.worldline_id != worldline_id:
            raise NarrativeQualityValidationError("narrative artifact does not belong to worldline")
        return artifact

    def _continuity_conflicts(
        self,
        review: NarrativeContinuityReview,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        reviewed_text: str,
        metadata: dict[str, Any],
        evidence_refs: list[NarrativeQualityEvidenceRef],
    ) -> list[NarrativeQualityConflictReport]:
        reports = _continuity_conflicts_from_review(review, evidence_refs=evidence_refs)
        reports.extend(_relationship_jump_conflicts(metadata, evidence_refs=evidence_refs))
        reports.extend(
            self._route_reference_conflicts(
                world_id,
                worldline_id,
                reviewed_text,
                evidence_refs=evidence_refs,
            )
        )
        return reports

    def _route_reference_conflicts(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        reviewed_text: str,
        *,
        evidence_refs: list[NarrativeQualityEvidenceRef],
    ) -> list[NarrativeQualityConflictReport]:
        if "route" not in reviewed_text.lower():
            return []
        active_route = self._session.scalars(
            select(RouteAffinity.id)
            .where(
                RouteAffinity.world_id == world_id,
                RouteAffinity.worldline_id == worldline_id,
                RouteAffinity.status == "active",
            )
            .limit(1)
        ).first()
        if active_route is not None:
            return []
        return [
            NarrativeQualityConflictReport(
                code="route_context_missing",
                severity="warning",
                summary="Text references route progression without an active route context.",
                evidence_refs=evidence_refs,
                details={"active_route_found": False},
            )
        ]

    def _pacing_policy_or_error(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        policy_id: uuid.UUID,
    ) -> AssetGenerationPolicy:
        policy = self._session.get(AssetGenerationPolicy, policy_id)
        if policy is None or policy.world_id != world_id or policy.worldline_id != worldline_id:
            raise NarrativeQualityValidationError("pacing policy not found in worldline")
        return policy

    def _conversation_model_or_error(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        conversation_id: uuid.UUID,
    ) -> ConversationSession:
        conversation = self._session.get(ConversationSession, conversation_id)
        if (
            conversation is None
            or conversation.world_id != world_id
            or conversation.worldline_id != worldline_id
        ):
            raise NarrativeQualityValidationError("conversation not found in worldline")
        return conversation

    def _turn_model_or_error(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        turn_id: uuid.UUID,
    ) -> ConversationTurn:
        row = self._session.execute(
            select(ConversationTurn, ConversationSession)
            .join(ConversationSession, ConversationTurn.session_id == ConversationSession.id)
            .where(ConversationTurn.id == turn_id)
        ).one_or_none()
        if row is None:
            raise NarrativeQualityValidationError("turn not found in worldline")
        turn = cast(ConversationTurn, row[0])
        conversation = cast(ConversationSession, row[1])
        if conversation.world_id != world_id or conversation.worldline_id != worldline_id:
            raise NarrativeQualityValidationError("turn not found in worldline")
        return turn

    def _pending_media_jobs(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        conversation: ConversationSession | None,
        current_turn: ConversationTurn | None,
    ) -> list[MediaJob]:
        statement = select(MediaJob).where(
            MediaJob.world_id == world_id,
            MediaJob.worldline_id == worldline_id,
            MediaJob.status.in_(PENDING_MEDIA_JOB_STATUSES),
        )
        if conversation is not None:
            statement = statement.where(MediaJob.conversation_id == conversation.id)
        if current_turn is not None:
            statement = statement.where(MediaJob.turn_id == current_turn.id)
        return list(self._session.scalars(statement.order_by(MediaJob.priority)).all())

    def _pending_asset_proposals(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        conversation: ConversationSession | None,
    ) -> list[AssetGenerationProposal]:
        statement = select(AssetGenerationProposal).where(
            AssetGenerationProposal.world_id == world_id,
            AssetGenerationProposal.worldline_id == worldline_id,
            AssetGenerationProposal.status == "proposed",
        )
        if conversation is not None:
            statement = statement.where(
                AssetGenerationProposal.request_json["conversation_id"].as_string()
                == str(conversation.id)
            )
        return list(
            self._session.scalars(
                statement.order_by(
                    AssetGenerationProposal.priority,
                    AssetGenerationProposal.created_at,
                )
            ).all()
        )

    def _pacing_lookahead_summary(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        conversation: ConversationSession | None,
        current_turn: ConversationTurn | None,
        *,
        lookahead_turns: int,
    ) -> dict[str, Any]:
        statement = (
            select(ConversationTurn, ConversationSession)
            .join(ConversationSession, ConversationTurn.session_id == ConversationSession.id)
            .where(
                ConversationSession.world_id == world_id,
                ConversationSession.worldline_id == worldline_id,
            )
        )
        if conversation is not None:
            statement = statement.where(ConversationSession.id == conversation.id)
        rows = self._session.execute(
            statement.order_by(ConversationSession.created_at.desc(), ConversationTurn.turn_index)
        ).all()
        current_index = None if current_turn is None else current_turn.turn_index
        within = 0
        beyond = 0
        current_missing_assets = False
        for turn, _session_model in rows:
            if current_turn is not None and turn.id == current_turn.id:
                presentation = self._presentation_for_turn(turn.id)
                current_missing_assets = presentation is None or (
                    presentation.sprite_variant_id is None
                    and presentation.tts_media_asset_id is None
                    and presentation.composite_scene_asset_id is None
                )
            if current_index is None:
                continue
            if current_turn is None:
                continue
            if turn.session_id != current_turn.session_id:
                continue
            if turn.turn_index <= current_index:
                continue
            if turn.turn_index <= current_index + lookahead_turns:
                within += 1
            else:
                beyond += 1
        return {
            "configured_lookahead_turns": lookahead_turns,
            "lookahead_turn_count": within,
            "beyond_lookahead_turn_count": beyond,
            "current_turn_missing_assets": current_missing_assets,
        }

    def _pacing_offscreen_summary(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        conversation: ConversationSession | None,
        *,
        include_offscreen: bool,
    ) -> dict[str, Any]:
        if not include_offscreen:
            return {"included": False, "offscreen_conversation_count": 0}
        statement = select(ConversationSession).where(
            ConversationSession.world_id == world_id,
            ConversationSession.worldline_id == worldline_id,
        )
        if conversation is not None:
            statement = statement.where(ConversationSession.id != conversation.id)
        sessions = list(self._session.scalars(statement).all())
        offscreen = [
            session
            for session in sessions
            if session.status in {"running", "paused", "completed"}
        ]
        return {
            "included": True,
            "offscreen_conversation_count": len(offscreen),
            "compressible_conversation_count": sum(
                1 for session in offscreen if session.status == "completed"
            ),
        }

    def _presentation_for_turn(
        self,
        turn_id: uuid.UUID,
    ) -> ConversationTurnPresentation | None:
        return self._session.scalars(
            select(ConversationTurnPresentation).where(
                ConversationTurnPresentation.turn_id == turn_id
            )
        ).one_or_none()

    def _route_affinity_or_error(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        route_affinity_id: uuid.UUID,
    ) -> RouteAffinity:
        route = self._session.get(RouteAffinity, route_affinity_id)
        if route is None or route.world_id != world_id or route.worldline_id != worldline_id:
            raise NarrativeQualityValidationError("route affinity not found in worldline")
        return route

    def _relationship_edges(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        agent: Agent | None,
    ) -> list[AgentRelationshipEdge]:
        statement = select(AgentRelationshipEdge).where(
            AgentRelationshipEdge.world_id == world_id,
            AgentRelationshipEdge.worldline_id == worldline_id,
        )
        if agent is not None:
            statement = statement.where(
                (AgentRelationshipEdge.source_agent_id == agent.id)
                | (AgentRelationshipEdge.target_agent_id == agent.id)
            )
        return list(
            self._session.scalars(
                statement.order_by(
                    AgentRelationshipEdge.source_agent_id,
                    AgentRelationshipEdge.target_agent_id,
                    AgentRelationshipEdge.relationship_type,
                )
            ).all()
        )

    def _route_affinities(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        agent: Agent | None,
        route: RouteAffinity | None,
    ) -> list[RouteAffinity]:
        if route is not None:
            return [route]
        statement = select(RouteAffinity).where(
            RouteAffinity.world_id == world_id,
            RouteAffinity.worldline_id == worldline_id,
        )
        if agent is not None:
            statement = statement.where(RouteAffinity.agent_id == agent.id)
        return list(
            self._session.scalars(
                statement.order_by(
                    RouteAffinity.stage.desc(),
                    RouteAffinity.affinity.desc(),
                    RouteAffinity.route_key,
                )
            ).all()
        )

    def _route_milestones(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        agent: Agent | None,
        routes: list[RouteAffinity],
    ) -> list[RouteMilestone]:
        statement = select(RouteMilestone).where(
            RouteMilestone.world_id == world_id,
            RouteMilestone.worldline_id == worldline_id,
        )
        route_ids = [route.id for route in routes]
        if route_ids:
            statement = statement.where(
                (RouteMilestone.route_affinity_id.in_(route_ids))
                | (RouteMilestone.route_affinity_id.is_(None))
            )
        if agent is not None:
            statement = statement.where(
                (RouteMilestone.agent_id == agent.id) | (RouteMilestone.agent_id.is_(None))
            )
        return list(
            self._session.scalars(
                statement.order_by(RouteMilestone.stage, RouteMilestone.created_at)
            ).all()
        )

    def _ending_candidates(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        agent: Agent | None,
        routes: list[RouteAffinity],
    ) -> list[EndingCandidate]:
        statement = select(EndingCandidate).where(
            EndingCandidate.world_id == world_id,
            EndingCandidate.worldline_id == worldline_id,
        )
        route_ids = [route.id for route in routes]
        if route_ids:
            statement = statement.where(
                (EndingCandidate.route_affinity_id.in_(route_ids))
                | (EndingCandidate.route_affinity_id.is_(None))
            )
        if agent is not None:
            statement = statement.where(
                (EndingCandidate.agent_id == agent.id) | (EndingCandidate.agent_id.is_(None))
            )
        return list(
            self._session.scalars(
                statement.order_by(EndingCandidate.status, EndingCandidate.ending_key)
            ).all()
        )

    def _player_choice_records(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        routes: list[RouteAffinity],
    ) -> list[PlayerChoiceRecord]:
        choice_ids = [route.last_choice_id for route in routes if route.last_choice_id is not None]
        statement = select(PlayerChoiceRecord).where(
            PlayerChoiceRecord.world_id == world_id,
            PlayerChoiceRecord.worldline_id == worldline_id,
        )
        if choice_ids:
            statement = statement.where(PlayerChoiceRecord.id.in_(choice_ids))
        else:
            statement = statement.where(PlayerChoiceRecord.choice_kind == "route")
        return list(
            self._session.scalars(
                statement.order_by(PlayerChoiceRecord.created_at.desc()).limit(50)
            ).all()
        )

    def _recent_progression_events(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        *,
        limit: int,
    ) -> list[WorldEventModel]:
        if limit == 0:
            return []
        return list(
            self._session.scalars(
                select(WorldEventModel)
                .where(
                    WorldEventModel.world_id == world_id,
                    WorldEventModel.worldline_id == worldline_id,
                    WorldEventModel.importance.in_(["relationship", "route", "main_plot"]),
                )
                .order_by(WorldEventModel.sequence.desc())
                .limit(limit)
            ).all()
        )

    def _progression_gm_proposals(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        agent: Agent | None,
    ) -> list[GMEventProposal]:
        statement = select(GMEventProposal).where(
            GMEventProposal.world_id == world_id,
            GMEventProposal.worldline_id == worldline_id,
            GMEventProposal.importance.in_(["relationship", "route", "main_plot"]),
            GMEventProposal.status.in_(["proposed", "accepted"]),
        )
        proposals = list(
            self._session.scalars(
                statement.order_by(GMEventProposal.risk_score.desc(), GMEventProposal.created_at)
            ).all()
        )
        if agent is None:
            return proposals
        agent_id_text = str(agent.id)
        agent_key = agent.agent_key
        return [
            proposal
            for proposal in proposals
            if agent_id_text in {str(item) for item in proposal.affected_agents}
            or agent_key in {str(item) for item in proposal.affected_agents}
        ]

    def _sprite_set_or_error(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        sprite_set_id: uuid.UUID,
    ) -> CharacterSpriteSet:
        model = self._session.get(CharacterSpriteSet, sprite_set_id)
        if (
            model is None
            or model.world_id != world_id
            or model.worldline_id != worldline_id
            or model.status == "deleted"
        ):
            raise NarrativeQualityValidationError("sprite set not found")
        return model

    def _sprite_variant_or_error(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        sprite_variant_id: uuid.UUID,
    ) -> CharacterSpriteVariant:
        model = self._session.get(CharacterSpriteVariant, sprite_variant_id)
        if (
            model is None
            or model.world_id != world_id
            or model.worldline_id != worldline_id
            or model.status == "deleted"
        ):
            raise NarrativeQualityValidationError("sprite variant not found")
        return model

    def _neutral_variant_id(self, sprite_set_id: uuid.UUID) -> uuid.UUID | None:
        model = self._session.scalars(
            select(CharacterSpriteVariant)
            .where(
                CharacterSpriteVariant.sprite_set_id == sprite_set_id,
                CharacterSpriteVariant.status == "active",
                CharacterSpriteVariant.expression_key == "neutral",
            )
            .order_by(CharacterSpriteVariant.priority, CharacterSpriteVariant.created_at)
            .limit(1)
        ).first()
        return None if model is None else model.id

    def _matching_variant_id(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        sprite_set_id: uuid.UUID,
        emotion_key: str,
    ) -> uuid.UUID | None:
        variants = self._session.scalars(
            select(CharacterSpriteVariant)
            .where(
                CharacterSpriteVariant.world_id == world_id,
                CharacterSpriteVariant.worldline_id == worldline_id,
                CharacterSpriteVariant.sprite_set_id == sprite_set_id,
                CharacterSpriteVariant.status == "active",
            )
            .order_by(
                CharacterSpriteVariant.is_default.desc(),
                CharacterSpriteVariant.priority,
                CharacterSpriteVariant.created_at,
            )
        ).all()
        match = next(
            (variant for variant in variants if _sprite_covers_emotion(variant, emotion_key)),
            None,
        )
        return None if match is None else match.id

    def _voice_profile_or_error(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        voice_profile_id: uuid.UUID,
    ) -> VoiceProfile:
        model = self._session.get(VoiceProfile, voice_profile_id)
        if model is None or model.world_id != world_id or model.status == "deleted":
            raise NarrativeQualityValidationError("voice profile not found")
        if model.worldline_id is not None and model.worldline_id != worldline_id:
            raise NarrativeQualityValidationError("voice profile does not belong to worldline")
        return model

    def _voice_binding_or_error(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        binding_id: uuid.UUID,
    ) -> AgentVoiceProfileBinding:
        model = self._session.get(AgentVoiceProfileBinding, binding_id)
        if model is None or model.world_id != world_id:
            raise NarrativeQualityValidationError("voice binding not found")
        if model.worldline_id is not None and model.worldline_id != worldline_id:
            raise NarrativeQualityValidationError("voice binding does not belong to worldline")
        return model

    def _voice_binding_for_profile(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        agent_id: uuid.UUID,
        voice_profile_id: uuid.UUID,
    ) -> AgentVoiceProfileBinding | None:
        return self._session.scalars(
            select(AgentVoiceProfileBinding)
            .where(
                AgentVoiceProfileBinding.world_id == world_id,
                AgentVoiceProfileBinding.agent_id == agent_id,
                AgentVoiceProfileBinding.voice_profile_id == voice_profile_id,
                (
                    (AgentVoiceProfileBinding.worldline_id == worldline_id)
                    | (AgentVoiceProfileBinding.worldline_id.is_(None))
                ),
            )
            .order_by(
                AgentVoiceProfileBinding.is_default.desc(),
                AgentVoiceProfileBinding.priority,
                AgentVoiceProfileBinding.created_at,
            )
            .limit(1)
        ).first()

    def _has_speech_style_mapping(
        self,
        world_id: uuid.UUID,
        *,
        provider_kind: str,
        emotion_key: str,
    ) -> bool:
        return (
            self._session.scalars(
                select(SpeechStyleMapping.id)
                .where(
                    SpeechStyleMapping.world_id == world_id,
                    SpeechStyleMapping.provider_kind == provider_kind,
                    SpeechStyleMapping.emotion_key == emotion_key,
                )
                .limit(1)
            ).first()
            is not None
        )

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


def _dashboard_blockers(
    metrics: dict[str, Any],
    *,
    evidence_refs: list[NarrativeQualityEvidenceRef],
) -> list[NarrativeQualityDashboardSignal]:
    provider = _dict_value(metrics.get("providers"))
    invocations = _dict_value(metrics.get("invocations"))
    gm = _dict_value(metrics.get("gm_proposals"))
    dialogue = _dict_value(metrics.get("dialogue"))
    narrative = _dict_value(metrics.get("narrative_writer"))
    continuity = _dict_value(metrics.get("continuity"))
    pacing = _dict_value(metrics.get("pacing"))
    progression = _dict_value(metrics.get("progression"))
    long_run = _dict_value(metrics.get("long_run"))
    events = _dict_value(metrics.get("world_events"))
    blockers: list[NarrativeQualityDashboardSignal] = []
    if _int_value(provider.get("unsafe_provider_config_count")) > 0:
        blockers.append(
            _dashboard_signal(
                "unsafe_provider_config",
                "error",
                "Provider configuration contains secret-like or unsafe operational data.",
                evidence_refs,
                {"count": provider.get("unsafe_provider_config_count")},
            )
        )
    if _int_value(provider.get("unsafe_health_metadata_count")) > 0:
        blockers.append(
            _dashboard_signal(
                "unsafe_provider_health_metadata",
                "error",
                "Provider health metadata contains secret-like or unsafe operational data.",
                evidence_refs,
                {"count": provider.get("unsafe_health_metadata_count")},
            )
        )
    if _int_value(invocations.get("unsafe_invocation_metadata_count")) > 0:
        blockers.append(
            _dashboard_signal(
                "unsafe_invocation_metadata",
                "error",
                "Invocation metadata contains unsafe operational data.",
                evidence_refs,
                {"count": invocations.get("unsafe_invocation_metadata_count")},
            )
        )
    if _int_value(invocations.get("raw_sensitive_prompt_snapshot_count")) > 0:
        blockers.append(
            _dashboard_signal(
                "raw_sensitive_prompt_snapshot",
                "error",
                "Sensitive prompt snapshots remain in raw redaction state.",
                evidence_refs,
                {"count": invocations.get("raw_sensitive_prompt_snapshot_count")},
            )
        )
    if _int_value(gm.get("unsafe_payload_count")) > 0:
        blockers.append(
            _dashboard_signal(
                "unsafe_gm_proposal_payload",
                "error",
                "GM proposal payload or source context contains unsafe operational data.",
                evidence_refs,
                {"count": gm.get("unsafe_payload_count")},
            )
        )
    if _int_value(dialogue.get("unsafe_turn_text_count")) > 0:
        blockers.append(
            _dashboard_signal(
                "unsafe_dialogue_text",
                "error",
                "Conversation turn text contains unsafe operational data.",
                evidence_refs,
                {"count": dialogue.get("unsafe_turn_text_count")},
            )
        )
    if _int_value(narrative.get("unsafe_artifact_metadata_count")) > 0:
        blockers.append(
            _dashboard_signal(
                "unsafe_narrative_artifact_metadata",
                "error",
                "Narrative artifact metadata contains unsafe operational data.",
                evidence_refs,
                {"count": narrative.get("unsafe_artifact_metadata_count")},
            )
        )
    if _int_value(continuity.get("failed_review_count")) > 0:
        blockers.append(
            _dashboard_signal(
                "continuity_review_failures",
                "error",
                "Failed continuity reviews are present in this worldline.",
                evidence_refs,
                {"count": continuity.get("failed_review_count")},
            )
        )
    if _int_value(continuity.get("unsafe_review_metadata_count")) > 0:
        blockers.append(
            _dashboard_signal(
                "unsafe_continuity_review_metadata",
                "error",
                "Continuity review metadata contains unsafe operational data.",
                evidence_refs,
                {"count": continuity.get("unsafe_review_metadata_count")},
            )
        )
    if _int_value(pacing.get("unsafe_media_job_json_count")) > 0:
        blockers.append(
            _dashboard_signal(
                "unsafe_media_job_json",
                "error",
                "Pending media job JSON contains unsafe operational data.",
                evidence_refs,
                {"count": pacing.get("unsafe_media_job_json_count")},
            )
        )
    if _int_value(pacing.get("unsafe_asset_proposal_json_count")) > 0:
        blockers.append(
            _dashboard_signal(
                "unsafe_asset_generation_proposal_json",
                "error",
                "Asset generation proposal JSON contains unsafe operational data.",
                evidence_refs,
                {"count": pacing.get("unsafe_asset_proposal_json_count")},
            )
        )
    if _int_value(progression.get("error_finding_count")) > 0:
        blockers.append(
            _dashboard_signal(
                "progression_error_findings",
                "error",
                "Route or relationship progression diagnostics contain error findings.",
                evidence_refs,
                {"count": progression.get("error_finding_count")},
            )
        )
    if long_run.get("latest_status") == "failed":
        blockers.append(
            _dashboard_signal(
                "latest_long_run_eval_failed",
                "error",
                "The latest long-run narrative quality eval failed.",
                evidence_refs,
                {"latest_run_id": long_run.get("latest_run_id")},
            )
        )
    if _int_value(events.get("unsafe_payload_event_count")) > 0:
        blockers.append(
            _dashboard_signal(
                "unsafe_world_event_payload",
                "error",
                "World event payloads contain storage paths, raw prompt markers, or secrets.",
                evidence_refs,
                {"count": events.get("unsafe_payload_event_count")},
            )
        )
    return blockers


def _dashboard_warnings(
    metrics: dict[str, Any],
    *,
    evidence_refs: list[NarrativeQualityEvidenceRef],
) -> list[NarrativeQualityDashboardSignal]:
    provider = _dict_value(metrics.get("providers"))
    invocations = _dict_value(metrics.get("invocations"))
    gm = _dict_value(metrics.get("gm_proposals"))
    dialogue = _dict_value(metrics.get("dialogue"))
    presentation = _dict_value(metrics.get("presentation_alignment"))
    continuity = _dict_value(metrics.get("continuity"))
    pacing = _dict_value(metrics.get("pacing"))
    progression = _dict_value(metrics.get("progression"))
    long_run = _dict_value(metrics.get("long_run"))
    warnings: list[NarrativeQualityDashboardSignal] = []
    if _int_value(provider.get("active_text_provider_count")) == 0:
        warnings.append(
            _dashboard_signal(
                "text_provider_missing",
                "warning",
                "No active text-generation provider is configured for narrative quality work.",
                evidence_refs,
                {},
            )
        )
    if _int_value(provider.get("latest_unhealthy_count")) > 0:
        warnings.append(
            _dashboard_signal(
                "provider_health_unhealthy",
                "warning",
                "Latest provider health checks include unhealthy providers.",
                evidence_refs,
                {"count": provider.get("latest_unhealthy_count")},
            )
        )
    if _int_value(provider.get("latest_degraded_count")) > 0:
        warnings.append(
            _dashboard_signal(
                "provider_health_degraded",
                "warning",
                "Latest provider health checks include degraded providers.",
                evidence_refs,
                {"count": provider.get("latest_degraded_count")},
            )
        )
    if _int_value(invocations.get("failed_invocation_count")) > 0:
        warnings.append(
            _dashboard_signal(
                "failed_invocations_present",
                "warning",
                "Failed model invocations are present in this worldline.",
                evidence_refs,
                {"count": invocations.get("failed_invocation_count")},
            )
        )
    if _int_value(gm.get("high_risk_open_proposal_count")) > 0:
        warnings.append(
            _dashboard_signal(
                "high_risk_gm_proposals_open",
                "warning",
                "High-risk GM proposals remain open for review.",
                evidence_refs,
                {"count": gm.get("high_risk_open_proposal_count")},
            )
        )
    turn_count = _int_value(dialogue.get("turn_count"))
    presentation_count = _int_value(presentation.get("presentation_count"))
    if turn_count > presentation_count:
        warnings.append(
            _dashboard_signal(
                "turn_presentation_coverage_gap",
                "warning",
                "Conversation turns exist without canonical presentation records.",
                evidence_refs,
                {"missing_count": turn_count - presentation_count},
            )
        )
    if _int_value(presentation.get("active_sprite_set_count")) == 0:
        warnings.append(
            _dashboard_signal(
                "sprite_sets_missing",
                "warning",
                "No active character sprite sets exist for this worldline.",
                evidence_refs,
                {},
            )
        )
    if _int_value(presentation.get("sprite_set_missing_default_count")) > 0:
        warnings.append(
            _dashboard_signal(
                "sprite_defaults_missing",
                "warning",
                "Active sprite sets are missing a default or neutral fallback.",
                evidence_refs,
                {"count": presentation.get("sprite_set_missing_default_count")},
            )
        )
    if _int_value(presentation.get("agent_missing_default_voice_binding_count")) > 0:
        warnings.append(
            _dashboard_signal(
                "voice_bindings_missing",
                "warning",
                "Enabled agents are missing default voice bindings for this worldline.",
                evidence_refs,
                {"count": presentation.get("agent_missing_default_voice_binding_count")},
            )
        )
    if _int_value(continuity.get("warning_review_count")) > 0:
        warnings.append(
            _dashboard_signal(
                "continuity_warnings_present",
                "warning",
                "Continuity reviews include warnings.",
                evidence_refs,
                {"count": continuity.get("warning_review_count")},
            )
        )
    queue = _dict_value(pacing.get("queue_summary"))
    budget = _dict_value(pacing.get("budget_summary"))
    if _int_value(queue.get("pending_job_count")) > 0:
        warnings.append(
            _dashboard_signal(
                "pending_media_jobs_present",
                "warning",
                "Pending media jobs may affect current-turn narrative quality readiness.",
                evidence_refs,
                {"count": queue.get("pending_job_count")},
            )
        )
    if _int_value(budget.get("proposed_asset_generation_count")) > 0:
        warnings.append(
            _dashboard_signal(
                "asset_generation_proposals_open",
                "warning",
                "Asset generation proposals remain proposed for admin review.",
                evidence_refs,
                {"count": budget.get("proposed_asset_generation_count")},
            )
        )
    if _int_value(progression.get("warning_finding_count")) > 0:
        warnings.append(
            _dashboard_signal(
                "progression_warnings_present",
                "warning",
                "Route or relationship progression diagnostics contain warnings.",
                evidence_refs,
                {"count": progression.get("warning_finding_count")},
            )
        )
    if _int_value(long_run.get("run_count")) == 0:
        warnings.append(
            _dashboard_signal(
                "long_run_eval_missing",
                "warning",
                "No long-run narrative quality eval exists for this worldline.",
                evidence_refs,
                {},
            )
        )
    elif long_run.get("latest_status") == "warning":
        warnings.append(
            _dashboard_signal(
                "latest_long_run_eval_warning",
                "warning",
                "The latest long-run narrative quality eval completed with warnings.",
                evidence_refs,
                {"latest_run_id": long_run.get("latest_run_id")},
            )
        )
    return warnings


def _dashboard_recommendations(
    blockers: list[NarrativeQualityDashboardSignal],
    warnings: list[NarrativeQualityDashboardSignal],
    *,
    evidence_refs: list[NarrativeQualityEvidenceRef],
) -> list[NarrativeQualityDashboardRecommendation]:
    codes = {signal.code for signal in blockers + warnings}
    recommendations: list[NarrativeQualityDashboardRecommendation] = []
    mapping = {
        "text_provider_missing": (
            "configure_text_provider",
            (
                "Configure an active provider-kernel text-generation provider before "
                "provider-backed quality generation."
            ),
        ),
        "unsafe_world_event_payload": (
            "audit_world_event_payloads",
            "Audit and sanitize world event payloads before relying on dashboard results.",
        ),
        "continuity_review_failures": (
            "resolve_continuity_failures",
            "Resolve failed continuity reviews before publication or route progression.",
        ),
        "turn_presentation_coverage_gap": (
            "complete_turn_presentations",
            "Create canonical turn presentations for existing conversation turns.",
        ),
        "sprite_defaults_missing": (
            "add_sprite_defaults",
            "Add default or neutral sprite variants for active sprite sets.",
        ),
        "voice_bindings_missing": (
            "add_voice_bindings",
            "Bind default voice profiles to enabled agents in this worldline.",
        ),
        "high_risk_gm_proposals_open": (
            "review_high_risk_gm_proposals",
            "Review or resolve high-risk GM proposals before advancing the route.",
        ),
        "pending_media_jobs_present": (
            "review_media_queue",
            "Review pending media jobs and reprioritize current visible turn needs.",
        ),
        "asset_generation_proposals_open": (
            "review_asset_generation_proposals",
            "Apply, dismiss, or defer asset generation proposals through explicit admin review.",
        ),
        "long_run_eval_missing": (
            "run_long_run_eval",
            "Run a long-run narrative quality eval for this worldline.",
        ),
    }
    for source_code, (recommendation_code, message) in mapping.items():
        if source_code not in codes:
            continue
        recommendations.append(
            NarrativeQualityDashboardRecommendation(
                code=recommendation_code,
                message=message,
                target_ref=evidence_refs[0] if evidence_refs else None,
                action_json={"mutates_state": False, "source_code": source_code},
            )
        )
    if any(code.startswith("unsafe_") or code.startswith("raw_") for code in codes):
        recommendations.append(
            NarrativeQualityDashboardRecommendation(
                code="review_redaction_boundaries",
                message="Review provider, invocation, media, and event redaction boundaries.",
                target_ref=evidence_refs[0] if evidence_refs else None,
                action_json={"mutates_state": False, "source_code": "unsafe_boundary"},
            )
        )
    return recommendations


def _dashboard_signal(
    code: str,
    severity: str,
    message: str,
    evidence_refs: list[NarrativeQualityEvidenceRef],
    details: dict[str, Any],
) -> NarrativeQualityDashboardSignal:
    return NarrativeQualityDashboardSignal(
        code=code,
        severity=severity,
        message=message,
        evidence_refs=evidence_refs,
        details=_sanitize_json(details),
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


def _alignment_result(
    *,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    conversation_id: uuid.UUID,
    turn_id: uuid.UUID,
    findings: list[NarrativeQualityAlignmentFinding],
    suggested_fixes: list[NarrativeQualitySuggestedFix],
    evidence_refs: list[NarrativeQualityEvidenceRef],
    diagnostics: dict[str, Any],
    emotion_key: str | None = None,
    sprite_variant_id: uuid.UUID | None = None,
    voice_profile_id: uuid.UUID | None = None,
) -> NarrativeQualityPresentationAlignmentResult:
    status = "pass"
    if any(finding.severity == "error" for finding in findings):
        status = "fail"
    elif any(finding.severity == "warning" for finding in findings):
        status = "warning"
    return NarrativeQualityPresentationAlignmentResult(
        world_id=world_id,
        worldline_id=worldline_id,
        conversation_id=conversation_id,
        turn_id=turn_id,
        alignment_status=status,
        emotion_key=emotion_key,
        sprite_variant_id=sprite_variant_id,
        voice_profile_id=voice_profile_id,
        findings=findings,
        suggested_fixes=suggested_fixes,
        evidence_refs=evidence_refs,
        diagnostics=_sanitize_json(diagnostics),
    )


def _alignment_finding(
    code: str,
    severity: str,
    message: str,
    *,
    evidence_refs: list[NarrativeQualityEvidenceRef],
) -> NarrativeQualityAlignmentFinding:
    return NarrativeQualityAlignmentFinding(
        code=code,
        severity=severity,
        message=message,
        evidence_refs=evidence_refs,
    )


def _missing_alignment_finding(
    code: str,
    allow_missing_assets: bool,
    message: str,
    evidence_refs: list[NarrativeQualityEvidenceRef],
) -> NarrativeQualityAlignmentFinding:
    return _alignment_finding(
        code,
        "info" if allow_missing_assets else "warning",
        message,
        evidence_refs=evidence_refs,
    )


def _normalize_alignment_key(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized or None


def _sprite_covers_emotion(
    sprite_variant: CharacterSpriteVariant,
    emotion_key: str,
) -> bool:
    normalized = emotion_key.strip().lower()
    expression_key = sprite_variant.expression_key.strip().lower()
    mood_tags = {
        str(item).strip().lower()
        for item in sprite_variant.mood_tags_json
        if str(item).strip()
    }
    return expression_key == normalized or normalized in mood_tags


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


def _narrative_writer_prompt(
    request: NarrativeQualityWriterGenerateRequest,
    *,
    context_pack: LivingWorldContextPack,
    conversation: ConversationSessionRecord | None,
    turns: list[ConversationTurnRecord],
) -> str:
    lines = [
        "Generate a reader-safe narrative draft.",
        f"Artifact kind: {request.artifact_kind.value}",
        f"Goal: {_clip(request.prompt_goal, 800)}",
        "Rules:",
        "- Preserve the supplied worldline context.",
        "- Filter hidden, developer-only, operational, and storage details.",
        (
            "- Do not include internal prompts, model outputs, storage details, "
            "encoded payloads, or secrets."
        ),
    ]
    context_text = context_pack.to_prompt_text()
    if context_text:
        lines.extend(["Context:", context_text])
    if conversation is not None:
        lines.extend(
            [
                "Conversation:",
                f"- Title: {_clip(conversation.title, 200)}",
                f"- Objective: {_clip(conversation.objective, 600)}",
            ]
        )
    turn_window = _turn_window_text(turns)
    if turn_window:
        lines.append(turn_window)
    return "\n".join(lines)


def _narrative_writer_title(
    request: NarrativeQualityWriterGenerateRequest,
    conversation: ConversationSessionRecord | None,
) -> str:
    if request.title:
        return _clip(request.title, 160)
    if conversation is not None:
        suffix = "summary" if request.artifact_kind.value == "conversation_summary" else "draft"
        return _clip(f"{conversation.title} {suffix}", 160)
    return "Narrative Writer v2 draft"


def _safe_generated_text(output_text: str | None, output_json: dict[str, Any]) -> str:
    text = output_text or str(output_json.get("text") or "")
    text = _safe_text(_clip(text, 20_000))
    if not text or text == REDACTED:
        return "Provider generated narrative draft text was redacted by safety filters."
    return text


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


def _continuity_findings(
    review: NarrativeContinuityReview,
    *,
    evidence_refs: list[NarrativeQualityEvidenceRef],
) -> list[NarrativeQualityContinuityFinding]:
    return [
        NarrativeQualityContinuityFinding(
            code=_safe_text(_clip(str(issue.get("code") or "continuity_issue"), 120)),
            severity=_safe_text(_clip(str(issue.get("severity") or "info"), 40)),
            message=_safe_text(
                _clip(str(issue.get("message") or "Continuity issue detected."), 400)
            ),
            evidence_refs=evidence_refs,
            suggested_action=_continuity_action(str(issue.get("code") or "")),
        )
        for issue in review.issues
    ]


def _continuity_conflicts_from_review(
    review: NarrativeContinuityReview,
    *,
    evidence_refs: list[NarrativeQualityEvidenceRef],
) -> list[NarrativeQualityConflictReport]:
    conflict_codes = {
        "hidden_secret_leak",
        "knowledge_leak_risk",
        "time_contradiction_risk",
        "forbidden_change",
        "ooc_marker",
    }
    reports: list[NarrativeQualityConflictReport] = []
    for issue in review.issues:
        code = str(issue.get("code") or "continuity_issue")
        if code not in conflict_codes:
            continue
        details = {
            key: value
            for key, value in issue.items()
            if key not in {"message"} and key != "secret_id"
        }
        if "secret_id" in issue:
            details["secret_ref_present"] = True
        reports.append(
            NarrativeQualityConflictReport(
                code=code,
                severity=str(issue.get("severity") or "warning"),
                summary=_safe_text(
                    _clip(str(issue.get("message") or "Continuity conflict detected."), 400)
                ),
                evidence_refs=evidence_refs,
                details=_sanitize_json(details),
            )
        )
    return reports


def _relationship_jump_conflicts(
    metadata: dict[str, Any],
    *,
    evidence_refs: list[NarrativeQualityEvidenceRef],
) -> list[NarrativeQualityConflictReport]:
    deltas = _relationship_deltas(metadata)
    reports: list[NarrativeQualityConflictReport] = []
    for field, delta in sorted(deltas.items()):
        if abs(delta) < 40:
            continue
        reports.append(
            NarrativeQualityConflictReport(
                code="relationship_jump",
                severity="warning",
                summary=(
                    f"Metadata claims a large relationship {field} delta without "
                    "reviewed transition evidence."
                ),
                evidence_refs=evidence_refs,
                details={"field": field, "delta": delta, "threshold": 40},
            )
        )
    return reports


def _relationship_deltas(metadata: dict[str, Any]) -> dict[str, int]:
    candidates: list[Any] = []
    for key in ("relationship_delta", "relationship_deltas", "relationship_changes"):
        if key in metadata:
            candidates.append(metadata[key])
    nested = metadata.get("relationship")
    if isinstance(nested, dict):
        for key in ("delta", "deltas", "changes"):
            if key in nested:
                candidates.append(nested[key])
    deltas: dict[str, int] = {}
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        for key, value in candidate.items():
            normalized = str(key).strip().lower()
            if normalized not in {
                "affection",
                "trust",
                "intimacy",
                "hostility",
                "obligation",
                "rivalry",
                "debt",
            }:
                continue
            parsed = _int_or_none(value)
            if parsed is not None:
                deltas[normalized] = parsed
    return deltas


def _continuity_repair_suggestions(
    findings: list[NarrativeQualityContinuityFinding],
    conflict_reports: list[NarrativeQualityConflictReport],
    *,
    evidence_refs: list[NarrativeQualityEvidenceRef],
) -> list[NarrativeQualityRepairSuggestion]:
    suggestions: list[NarrativeQualityRepairSuggestion] = []
    codes = {item.code for item in findings} | {item.code for item in conflict_reports}
    if "hidden_secret_leak" in codes:
        suggestions.append(
            NarrativeQualityRepairSuggestion(
                code="remove_hidden_secret_reference",
                message="Remove or obfuscate hidden secret material before publication.",
                target_ref=evidence_refs[0] if evidence_refs else None,
                patch_json={"action": "rewrite_secret_reference"},
            )
        )
    if "time_contradiction_risk" in codes:
        suggestions.append(
            NarrativeQualityRepairSuggestion(
                code="clarify_timeline_order",
                message="Add explicit timeline ordering or adjust the scene timing.",
                target_ref=evidence_refs[0] if evidence_refs else None,
                patch_json={"action": "add_timeline_bridge"},
            )
        )
    if "knowledge_leak_risk" in codes:
        suggestions.append(
            NarrativeQualityRepairSuggestion(
                code="scope_character_knowledge",
                message="Limit knowledge claims to agents who can plausibly know them.",
                target_ref=evidence_refs[0] if evidence_refs else None,
                patch_json={"action": "scope_knowledge_visibility"},
            )
        )
    if "relationship_jump" in codes:
        suggestions.append(
            NarrativeQualityRepairSuggestion(
                code="add_relationship_transition",
                message="Add an intermediate relationship beat before applying the large delta.",
                target_ref=evidence_refs[0] if evidence_refs else None,
                patch_json={"action": "insert_relationship_transition"},
            )
        )
    if "route_context_missing" in codes:
        suggestions.append(
            NarrativeQualityRepairSuggestion(
                code="attach_route_context",
                message="Attach an active route or rewrite the text to avoid route progression.",
                target_ref=evidence_refs[0] if evidence_refs else None,
                patch_json={"action": "attach_route_or_rewrite"},
            )
        )
    return suggestions


def _pacing_queue_summary(media_jobs: list[MediaJob]) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    kind_counts: dict[str, int] = {}
    priority_counts = {"p0": 0, "p1": 0, "p2_plus": 0}
    invalidation_counts: dict[str, int] = {}
    for job in media_jobs:
        status_counts[job.status] = status_counts.get(job.status, 0) + 1
        kind_counts[job.job_kind] = kind_counts.get(job.job_kind, 0) + 1
        if job.priority <= 0:
            priority_counts["p0"] += 1
        elif job.priority <= 10:
            priority_counts["p1"] += 1
        else:
            priority_counts["p2_plus"] += 1
        if job.invalidation_key:
            invalidation_counts[job.invalidation_key] = (
                invalidation_counts.get(job.invalidation_key, 0) + 1
            )
    duplicate_keys = sorted(
        key for key, count in invalidation_counts.items() if count > 1
    )
    return {
        "pending_job_count": len(media_jobs),
        "status_counts": status_counts,
        "job_kind_counts": kind_counts,
        "priority_counts": priority_counts,
        "duplicate_invalidation_key_count": len(duplicate_keys),
        "duplicate_invalidation_keys": duplicate_keys[:10],
    }


def _pacing_budget_summary(
    proposals: list[AssetGenerationProposal],
    *,
    max_pending_cost: float | None,
) -> dict[str, Any]:
    proposed_count = len(proposals)
    total_cost = sum(float(item.estimated_cost or 0.0) for item in proposals)
    kind_counts: dict[str, int] = {}
    for proposal in proposals:
        kind_counts[proposal.proposal_kind] = kind_counts.get(proposal.proposal_kind, 0) + 1
    return {
        "proposed_asset_generation_count": proposed_count,
        "estimated_pending_cost": round(total_cost, 4),
        "max_pending_cost": max_pending_cost,
        "proposal_kind_counts": kind_counts,
        "over_budget": max_pending_cost is not None and total_cost > max_pending_cost,
    }


def _pacing_findings(
    *,
    queue_summary: dict[str, Any],
    budget_summary: dict[str, Any],
    lookahead_summary: dict[str, Any],
    offscreen_summary: dict[str, Any],
    max_pending_jobs: int | None,
    max_pending_cost: float | None,
    policy: AssetGenerationPolicy | None,
    evidence_refs: list[NarrativeQualityEvidenceRef],
) -> list[NarrativeQualityPacingFinding]:
    findings: list[NarrativeQualityPacingFinding] = []
    pending_jobs = _int_value(queue_summary.get("pending_job_count"))
    if max_pending_jobs is not None and pending_jobs > max_pending_jobs:
        severity = "error" if max_pending_jobs == 0 else "warning"
        findings.append(
            NarrativeQualityPacingFinding(
                code="pending_media_job_limit_exceeded",
                severity=severity,
                message="Pending media jobs exceed the configured pacing limit.",
                evidence_refs=evidence_refs,
            )
        )
    if _int_value(queue_summary.get("duplicate_invalidation_key_count")) > 0:
        findings.append(
            NarrativeQualityPacingFinding(
                code="superseded_media_jobs_detected",
                severity="warning",
                message="Pending media jobs include duplicate invalidation keys.",
                evidence_refs=evidence_refs,
            )
        )
    if max_pending_cost is not None and bool(budget_summary.get("over_budget")):
        findings.append(
            NarrativeQualityPacingFinding(
                code="asset_generation_budget_exceeded",
                severity="warning",
                message="Pending asset generation proposals exceed the configured cost budget.",
                evidence_refs=evidence_refs,
            )
        )
    if bool(lookahead_summary.get("current_turn_missing_assets")):
        findings.append(
            NarrativeQualityPacingFinding(
                code="current_turn_missing_assets",
                severity="warning",
                message="Current visible turn is missing presentation assets.",
                evidence_refs=evidence_refs,
            )
        )
    if _int_value(offscreen_summary.get("compressible_conversation_count")) > 0:
        findings.append(
            NarrativeQualityPacingFinding(
                code="offscreen_compression_available",
                severity="info",
                message="Completed offscreen conversations are available for compression review.",
                evidence_refs=evidence_refs,
            )
        )
    if policy is None and (max_pending_jobs is None and max_pending_cost is None):
        findings.append(
            NarrativeQualityPacingFinding(
                code="pacing_policy_missing",
                severity="info",
                message="No pacing policy was provided; request limits are being used.",
                evidence_refs=evidence_refs,
            )
        )
    elif policy is not None and policy.status != "active":
        findings.append(
            NarrativeQualityPacingFinding(
                code="pacing_policy_disabled",
                severity="info",
                message="Selected pacing policy is not active.",
                evidence_refs=evidence_refs,
            )
        )
    return findings


def _pacing_recommendations(
    *,
    queue_summary: dict[str, Any],
    budget_summary: dict[str, Any],
    lookahead_summary: dict[str, Any],
    offscreen_summary: dict[str, Any],
    evidence_refs: list[NarrativeQualityEvidenceRef],
) -> list[NarrativeQualityPacingRecommendation]:
    recommendations: list[NarrativeQualityPacingRecommendation] = []
    duplicate_keys = queue_summary.get("duplicate_invalidation_keys")
    if isinstance(duplicate_keys, list) and duplicate_keys:
        recommendations.append(
            NarrativeQualityPacingRecommendation(
                code="cancel_superseded_media_jobs",
                message="Review duplicate invalidation keys and cancel superseded pending jobs.",
                target_ref=evidence_refs[0] if evidence_refs else None,
                action_json={"invalidation_keys": duplicate_keys, "mutates_state": False},
            )
        )
    if bool(budget_summary.get("over_budget")):
        recommendations.append(
            NarrativeQualityPacingRecommendation(
                code="reduce_asset_generation_budget_pressure",
                message="Dismiss or defer lower-priority asset generation proposals.",
                target_ref=evidence_refs[0] if evidence_refs else None,
                action_json={"mutates_state": False, "recommended_status": "defer"},
            )
        )
    if bool(lookahead_summary.get("current_turn_missing_assets")):
        recommendations.append(
            NarrativeQualityPacingRecommendation(
                code="prioritize_current_visible_turn",
                message=(
                    "Prioritize required assets for the current visible turn before "
                    "lookahead work."
                ),
                target_ref=evidence_refs[-1] if evidence_refs else None,
                action_json={"mutates_state": False, "priority_band": "p0"},
            )
        )
    if _int_value(offscreen_summary.get("compressible_conversation_count")) > 0:
        recommendations.append(
            NarrativeQualityPacingRecommendation(
                code="compress_offscreen_conversations",
                message="Use explicit admin review before compressing completed offscreen context.",
                target_ref=evidence_refs[0] if evidence_refs else None,
                action_json={"mutates_state": False, "mode": "review_only"},
            )
        )
    return recommendations


def _progression_relationship_summary(
    relationships: list[AgentRelationshipEdge],
) -> dict[str, Any]:
    type_counts: dict[str, int] = {}
    contradiction_count = 0
    one_way_count = 0
    pairs: dict[tuple[uuid.UUID, uuid.UUID], int] = {}
    for edge in relationships:
        type_counts[edge.relationship_type] = type_counts.get(edge.relationship_type, 0) + 1
        if _relationship_is_contradictory(edge):
            contradiction_count += 1
        source_id, target_id = sorted((edge.source_agent_id, edge.target_agent_id), key=str)
        ordered_pair = (source_id, target_id)
        pairs[ordered_pair] = pairs.get(ordered_pair, 0) + 1
    for count in pairs.values():
        if count == 1:
            one_way_count += 1
    return {
        "relationship_count": len(relationships),
        "relationship_type_counts": type_counts,
        "contradictory_relationship_count": contradiction_count,
        "one_way_pair_count": one_way_count,
    }


def _progression_route_summary(
    routes: list[RouteAffinity],
    milestones: list[RouteMilestone],
    endings: list[EndingCandidate],
    choices: list[PlayerChoiceRecord],
) -> dict[str, Any]:
    route_status_counts: dict[str, int] = {}
    milestone_status_counts: dict[str, int] = {}
    ending_status_counts: dict[str, int] = {}
    for route in routes:
        route_status_counts[route.status] = route_status_counts.get(route.status, 0) + 1
    for milestone in milestones:
        milestone_status_counts[milestone.status] = (
            milestone_status_counts.get(milestone.status, 0) + 1
        )
    for ending in endings:
        ending_status_counts[ending.status] = ending_status_counts.get(ending.status, 0) + 1
    return {
        "route_count": len(routes),
        "route_status_counts": route_status_counts,
        "active_route_count": sum(1 for route in routes if route.status == "active"),
        "blocked_route_count": sum(1 for route in routes if route.status == "blocked"),
        "milestone_count": len(milestones),
        "milestone_status_counts": milestone_status_counts,
        "ending_count": len(endings),
        "ending_status_counts": ending_status_counts,
        "route_choice_count": len(choices),
    }


def _progression_event_summary(events: list[WorldEventModel]) -> dict[str, Any]:
    importance_counts: dict[str, int] = {}
    event_name_counts: dict[str, int] = {}
    relationship_delta_count = 0
    leaky_payload_count = 0
    for event in events:
        importance_counts[event.importance] = importance_counts.get(event.importance, 0) + 1
        event_name_counts[event.event_name] = event_name_counts.get(event.event_name, 0) + 1
        if _relationship_deltas(event.payload):
            relationship_delta_count += 1
        if _json_contains_leak(event.payload):
            leaky_payload_count += 1
    return {
        "recent_event_count": len(events),
        "importance_counts": importance_counts,
        "event_name_counts": event_name_counts,
        "relationship_delta_event_count": relationship_delta_count,
        "unsafe_payload_event_count": leaky_payload_count,
    }


def _progression_proposal_summary(proposals: list[GMEventProposal]) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    importance_counts: dict[str, int] = {}
    high_risk_count = 0
    for proposal in proposals:
        status_counts[proposal.status] = status_counts.get(proposal.status, 0) + 1
        importance_counts[proposal.importance] = importance_counts.get(proposal.importance, 0) + 1
        if proposal.risk_score >= 70:
            high_risk_count += 1
    return {
        "open_proposal_count": len(proposals),
        "status_counts": status_counts,
        "importance_counts": importance_counts,
        "high_risk_open_proposal_count": high_risk_count,
    }


def _progression_findings(
    *,
    relationships: list[AgentRelationshipEdge],
    routes: list[RouteAffinity],
    milestones: list[RouteMilestone],
    endings: list[EndingCandidate],
    events: list[WorldEventModel],
    proposals: list[GMEventProposal],
    relationship_summary: dict[str, Any],
    route_summary: dict[str, Any],
    evidence_refs: list[NarrativeQualityEvidenceRef],
) -> list[NarrativeQualityProgressionFinding]:
    findings: list[NarrativeQualityProgressionFinding] = []
    if not relationships:
        findings.append(
            _progression_finding(
                "relationship_graph_sparse",
                "info",
                "No relationship edges are available for progression review.",
                evidence_refs,
            )
        )
    for edge in relationships:
        edge_refs = [
            *evidence_refs,
            NarrativeQualityEvidenceRef(kind="relationship", id=str(edge.id)),
        ]
        if _relationship_is_contradictory(edge):
            findings.append(
                _progression_finding(
                    "relationship_metric_contradiction",
                    "warning",
                    (
                        "Relationship edge combines high affection or trust with high "
                        "hostility or rivalry."
                    ),
                    edge_refs,
                )
            )
        if edge.worldline_id is None:
            findings.append(
                _progression_finding(
                    "relationship_worldline_missing",
                    "error",
                    (
                        "Relationship edge has no worldline and cannot be used for "
                        "v0.6 progression review."
                    ),
                    edge_refs,
                )
            )
    if _int_value(relationship_summary.get("one_way_pair_count")) > 0:
        findings.append(
            _progression_finding(
                "relationship_reciprocity_missing",
                "info",
                "Some relationship pairs only have one directed edge.",
                evidence_refs,
            )
        )
    if not routes:
        findings.append(
            _progression_finding(
                "route_graph_sparse",
                "info",
                "No route affinities are available for progression review.",
                evidence_refs,
            )
        )
    milestones_by_route: dict[uuid.UUID, list[RouteMilestone]] = {}
    for milestone in milestones:
        if milestone.route_affinity_id is not None:
            milestones_by_route.setdefault(milestone.route_affinity_id, []).append(milestone)
    for route in routes:
        route_refs = [*evidence_refs, NarrativeQualityEvidenceRef(kind="route", id=str(route.id))]
        route_milestones = milestones_by_route.get(route.id, [])
        if route.status == "active" and not route_milestones:
            findings.append(
                _progression_finding(
                    "active_route_missing_milestones",
                    "warning",
                    "Active route has no route milestones.",
                    route_refs,
                )
            )
        if route.status == "blocked" and not _route_block_reason(route):
            findings.append(
                _progression_finding(
                    "blocked_route_missing_reason",
                    "warning",
                    "Blocked route has no blocking reason in metadata or flags.",
                    route_refs,
                )
            )
        if route.status == "completed" and any(
            milestone.status != "completed" for milestone in route_milestones
        ):
            findings.append(
                _progression_finding(
                    "completed_route_has_open_milestones",
                    "warning",
                    "Completed route still has open milestones.",
                    route_refs,
                )
            )
        for milestone in route_milestones:
            if milestone.stage > route.stage and milestone.status in {"active", "completed"}:
                findings.append(
                    _progression_finding(
                        "route_stage_milestone_mismatch",
                        "warning",
                        "Route milestone stage is ahead of the route affinity stage.",
                        [
                            *route_refs,
                            NarrativeQualityEvidenceRef(
                                kind="route_milestone",
                                id=str(milestone.id),
                            ),
                        ],
                    )
                )
    for ending in endings:
        ending_route = next(
            (item for item in routes if item.id == ending.route_affinity_id),
            None,
        )
        issues = _ending_requirement_issues(ending, ending_route, milestones)
        if issues:
            findings.append(
                _progression_finding(
                    "ending_requirements_unsatisfied",
                    "warning",
                    "Ending candidate requirements are not currently satisfiable.",
                    [
                        *evidence_refs,
                        NarrativeQualityEvidenceRef(kind="ending_candidate", id=str(ending.id)),
                    ],
                )
            )
    if _int_value(route_summary.get("route_choice_count")) == 0 and routes:
        findings.append(
            _progression_finding(
                "route_choice_trace_missing",
                "info",
                "Route affinities have no associated route choice trace in this review scope.",
                evidence_refs,
            )
        )
    for proposal in proposals:
        if proposal.risk_score < 70:
            continue
        findings.append(
            _progression_finding(
                "high_risk_progression_proposal_open",
                "warning",
                "High-risk relationship or route GM proposal is still open for review.",
                [
                    *evidence_refs,
                    NarrativeQualityEvidenceRef(kind="gm_event_proposal", id=str(proposal.id)),
                ],
            )
        )
    for event in events:
        if _json_contains_leak(event.payload):
            findings.append(
                _progression_finding(
                    "unsafe_progression_event_payload",
                    "error",
                    "Recent route or relationship event payload contains unsafe operational data.",
                    [
                        *evidence_refs,
                        NarrativeQualityEvidenceRef(kind="world_event", id=str(event.id)),
                    ],
                )
            )
        for _field, delta in _relationship_deltas(event.payload).items():
            if abs(delta) >= 40:
                findings.append(
                    _progression_finding(
                        "relationship_delta_jump",
                        "warning",
                        "Recent event contains a large relationship delta.",
                        [
                            *evidence_refs,
                            NarrativeQualityEvidenceRef(kind="world_event", id=str(event.id)),
                        ],
                    )
                )
                break
    return findings


def _progression_recommendations(
    findings: list[NarrativeQualityProgressionFinding],
    *,
    evidence_refs: list[NarrativeQualityEvidenceRef],
) -> list[NarrativeQualityProgressionRecommendation]:
    recommendations: list[NarrativeQualityProgressionRecommendation] = []
    codes = {finding.code for finding in findings}
    if "relationship_metric_contradiction" in codes:
        recommendations.append(
            NarrativeQualityProgressionRecommendation(
                code="review_relationship_tension",
                message="Review whether contradictory relationship metrics are intended tension.",
                target_ref=evidence_refs[0] if evidence_refs else None,
                action_json={"mutates_state": False, "recommended_action": "review_relationship"},
            )
        )
    if "active_route_missing_milestones" in codes:
        recommendations.append(
            NarrativeQualityProgressionRecommendation(
                code="add_route_milestones",
                message="Add planned route milestones before relying on active route progression.",
                target_ref=evidence_refs[0] if evidence_refs else None,
                action_json={"mutates_state": False, "recommended_action": "plan_milestones"},
            )
        )
    if "route_stage_milestone_mismatch" in codes:
        recommendations.append(
            NarrativeQualityProgressionRecommendation(
                code="align_route_stage_and_milestones",
                message=(
                    "Review route stage and milestone statuses before applying more "
                    "route beats."
                ),
                target_ref=evidence_refs[0] if evidence_refs else None,
                action_json={"mutates_state": False, "recommended_action": "review_route_stage"},
            )
        )
    if "ending_requirements_unsatisfied" in codes:
        recommendations.append(
            NarrativeQualityProgressionRecommendation(
                code="review_ending_requirements",
                message="Review ending requirements against current route state and milestones.",
                target_ref=evidence_refs[0] if evidence_refs else None,
                action_json={
                    "mutates_state": False,
                    "recommended_action": "review_ending_requirements",
                },
            )
        )
    if "high_risk_progression_proposal_open" in codes:
        recommendations.append(
            NarrativeQualityProgressionRecommendation(
                code="resolve_high_risk_progression_proposals",
                message="Resolve high-risk route or relationship proposals before progressing.",
                target_ref=evidence_refs[0] if evidence_refs else None,
                action_json={"mutates_state": False, "recommended_action": "review_proposals"},
            )
        )
    if "unsafe_progression_event_payload" in codes:
        recommendations.append(
            NarrativeQualityProgressionRecommendation(
                code="sanitize_progression_events",
                message="Remove unsafe operational data from progression event payloads.",
                target_ref=evidence_refs[0] if evidence_refs else None,
                action_json={"mutates_state": False, "recommended_action": "audit_events"},
            )
        )
    return recommendations


def _long_run_quality_result(run: LongRunEvalRun) -> NarrativeQualityLongRunEvalResult:
    evidence_refs = [NarrativeQualityEvidenceRef(kind="worldline", id=str(run.worldline_id))]
    traceability = run.metrics.get("traceability")
    if isinstance(traceability, dict):
        refs = traceability.get("refs")
        if isinstance(refs, list):
            for ref in refs[:20]:
                if not isinstance(ref, dict):
                    continue
                kind = str(ref.get("kind") or "").strip()
                ref_id = str(ref.get("id") or "").strip()
                if kind and ref_id:
                    evidence_refs.append(NarrativeQualityEvidenceRef(kind=kind, id=ref_id))
    failure_reports = _long_run_failure_reports(run, evidence_refs=evidence_refs)
    return NarrativeQualityLongRunEvalResult(
        world_id=run.world_id,
        worldline_id=run.worldline_id,
        run_id=run.id,
        eval_key=_safe_text(run.eval_key),
        horizon_days=run.horizon_days,
        status=run.status,
        drift_metrics=_sanitize_json(_long_run_drift_metrics(run.metrics)),
        failure_reports=failure_reports,
        blockers=_sanitize_json(run.blockers),
        recommendations=_sanitize_json(run.recommendations),
        evidence_refs=evidence_refs,
        diagnostics=_sanitize_json(
            {
                "context_kind": "long_run_living_world_simulation_eval",
                "started_at": run.started_at.isoformat(),
                "finished_at": run.finished_at.isoformat(),
                "metadata": run.metadata_json,
                "provider_call_count": 0,
                "daemon_run": False,
                "world_event_written": False,
            }
        ),
    )


def _long_run_drift_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    distribution = metrics.get("distribution")
    traceability = metrics.get("traceability")
    review_warnings = metrics.get("review_warnings")
    return {
        "horizon_days": metrics.get("horizon_days"),
        "event_count": metrics.get("events"),
        "day_coverage": _dict_value(distribution).get("day_coverage"),
        "relationships": metrics.get("relationships"),
        "route_affinities": metrics.get("route_affinities"),
        "route_milestones": metrics.get("route_milestones"),
        "ending_candidates": metrics.get("ending_candidates"),
        "gm_proposals": metrics.get("gm_proposals"),
        "resolved_gm_proposals": metrics.get("resolved_gm_proposals"),
        "daily_candidates": metrics.get("daily_candidates"),
        "player_choices": metrics.get("player_choices"),
        "narrative_artifacts": metrics.get("narrative_artifacts"),
        "publications": metrics.get("publications"),
        "traceability_ref_count": _dict_value(traceability).get("event_ref_count", 0)
        + _dict_value(traceability).get("snapshot_ref_count", 0),
        "continuity_warning_count": _dict_value(review_warnings).get(
            "continuity_or_style_warning_count",
            0,
        ),
        "continuity_fail_count": _dict_value(review_warnings).get("continuity_fail_count", 0),
        "publication_gate_warning_count": _dict_value(review_warnings).get(
            "publication_gate_warning_count",
            0,
        ),
    }


def _long_run_failure_reports(
    run: LongRunEvalRun,
    *,
    evidence_refs: list[NarrativeQualityEvidenceRef],
) -> list[NarrativeQualityLongRunFailureReport]:
    reports: list[NarrativeQualityLongRunFailureReport] = []
    for blocker in run.blockers:
        reports.append(
            NarrativeQualityLongRunFailureReport(
                code=_safe_text(_clip(str(blocker.get("code") or "long_run_blocker"), 120)),
                severity="error",
                message=_safe_text(
                    _clip(str(blocker.get("message") or "Long-run eval blocker."), 400)
                ),
                evidence_refs=evidence_refs,
            )
        )
    metrics = _long_run_drift_metrics(run.metrics)
    if _int_value(metrics.get("event_count")) == 0:
        reports.append(
            NarrativeQualityLongRunFailureReport(
                code="no_worldline_events",
                severity="error",
                message="No worldline events are available for long-run evaluation.",
                evidence_refs=evidence_refs,
            )
        )
    if _int_value(metrics.get("relationships")) == 0:
        reports.append(
            NarrativeQualityLongRunFailureReport(
                code="relationship_graph_sparse",
                severity="warning",
                message="Relationship graph is sparse for long-run drift detection.",
                evidence_refs=evidence_refs,
            )
        )
    if _int_value(metrics.get("route_milestones")) == 0 or _int_value(
        metrics.get("ending_candidates")
    ) == 0:
        reports.append(
            NarrativeQualityLongRunFailureReport(
                code="route_endings_incomplete",
                severity="warning",
                message="Route milestones or ending candidates are missing from long-run evidence.",
                evidence_refs=evidence_refs,
            )
        )
    if _int_value(metrics.get("continuity_fail_count")) > 0:
        reports.append(
            NarrativeQualityLongRunFailureReport(
                code="continuity_failures_present",
                severity="error",
                message="Continuity review failures are present in the worldline.",
                evidence_refs=evidence_refs,
            )
        )
    return reports


def _dict_value(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _progression_finding(
    code: str,
    severity: str,
    message: str,
    evidence_refs: list[NarrativeQualityEvidenceRef],
) -> NarrativeQualityProgressionFinding:
    return NarrativeQualityProgressionFinding(
        code=code,
        severity=severity,
        message=message,
        evidence_refs=evidence_refs,
    )


def _relationship_is_contradictory(edge: AgentRelationshipEdge) -> bool:
    positive = edge.affection >= 70 or edge.trust >= 70 or edge.intimacy >= 70
    negative = edge.hostility >= 70 or edge.rivalry >= 70
    if not (positive and negative):
        return False
    metadata = edge.metadata_json or {}
    if bool(metadata.get("intentional_tension")) or bool(metadata.get("justified_tension")):
        return False
    return True


def _route_block_reason(route: RouteAffinity) -> str | None:
    metadata = route.metadata_json or {}
    for key in ("blocked_reason", "block_reason", "reason"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value
    for flag in route.flags:
        text = str(flag).strip().lower()
        if text.startswith("blocked:") or text.startswith("block_reason:"):
            return text
    return None


def _ending_requirement_issues(
    ending: EndingCandidate,
    route: RouteAffinity | None,
    milestones: list[RouteMilestone],
) -> list[str]:
    requirements = ending.requirements or {}
    issues: list[str] = []
    if route is None and any(
        key in requirements
        for key in (
            "min_route_affinity",
            "max_route_affinity",
            "min_route_stage",
            "max_route_stage",
            "required_route_flags",
            "forbidden_route_flags",
        )
    ):
        issues.append("route_missing")
        return issues
    if route is not None:
        min_affinity = _int_or_none(requirements.get("min_route_affinity"))
        if min_affinity is not None and route.affinity < min_affinity:
            issues.append("min_route_affinity")
        max_affinity = _int_or_none(requirements.get("max_route_affinity"))
        if max_affinity is not None and route.affinity > max_affinity:
            issues.append("max_route_affinity")
        min_stage = _int_or_none(requirements.get("min_route_stage"))
        if min_stage is not None and route.stage < min_stage:
            issues.append("min_route_stage")
        max_stage = _int_or_none(requirements.get("max_route_stage"))
        if max_stage is not None and route.stage > max_stage:
            issues.append("max_route_stage")
        flags = {str(flag) for flag in route.flags}
        required_flags = {
            str(flag) for flag in _list_value(requirements.get("required_route_flags"))
        }
        if required_flags and not required_flags.issubset(flags):
            issues.append("required_route_flags")
        forbidden_flags = {
            str(flag) for flag in _list_value(requirements.get("forbidden_route_flags"))
        }
        if forbidden_flags and forbidden_flags.intersection(flags):
            issues.append("forbidden_route_flags")
    completed_required = _int_or_none(requirements.get("min_completed_milestones"))
    if completed_required is not None:
        completed_count = sum(1 for milestone in milestones if milestone.status == "completed")
        if completed_count < completed_required:
            issues.append("min_completed_milestones")
    return issues


def _list_value(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _limit_from_policy(
    explicit: int | None,
    policy_json: dict[str, Any] | None,
    *keys: str,
) -> int | None:
    if explicit is not None:
        return explicit
    if policy_json is None:
        return None
    for key in keys:
        value = policy_json.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return None


def _float_limit_from_policy(
    explicit: float | None,
    policy_json: dict[str, Any] | None,
    *keys: str,
) -> float | None:
    if explicit is not None:
        return explicit
    if policy_json is None:
        return None
    for key in keys:
        value = policy_json.get(key)
        if isinstance(value, int | float) and not isinstance(value, bool):
            return float(value)
    return None


def _int_value(value: Any) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return 0


def _continuity_action(code: str) -> str | None:
    actions = {
        "hidden_secret_leak": "Remove hidden secret details or restrict visibility.",
        "knowledge_leak_risk": "Scope the claim to characters with valid knowledge.",
        "time_contradiction_risk": "Clarify the timeline before publication.",
        "forbidden_change": "Route this change through a canon review before use.",
        "ooc_marker": "Remove OOC framing from reader-facing narrative text.",
    }
    return actions.get(code)


def _turn_dialogue_text(turn: ConversationTurnRecord | None) -> str | None:
    if turn is None:
        return None
    return turn.output_text or turn.input_text


def _qa_finding(
    *,
    code: str,
    severity: str,
    summary: str,
    agent_id: uuid.UUID | None = None,
    evidence_refs: list[NarrativeQualityEvidenceRef] | None = None,
    source_traceability_refs: list[NarrativeQualityEvidenceRef] | None = None,
    suggested_repair_proposal_types: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> MemoryPersonaQAFinding:
    return MemoryPersonaQAFinding(
        code=code,
        severity=severity,
        summary=summary,
        agent_id=agent_id,
        evidence_refs=[] if evidence_refs is None else _dedupe_refs(evidence_refs),
        source_traceability_refs=[]
        if source_traceability_refs is None
        else _dedupe_refs(source_traceability_refs),
        suggested_repair_proposal_types=[]
        if suggested_repair_proposal_types is None
        else list(dict.fromkeys(suggested_repair_proposal_types)),
        metadata=_sanitize_json({} if metadata is None else metadata),
    )


def _qa_persona_source_refs(persona: AgentPersona | None) -> list[NarrativeQualityEvidenceRef]:
    if persona is None:
        return []
    refs = [NarrativeQualityEvidenceRef(kind="agent_persona", id=str(persona.id))]
    refs.extend(_source_refs_from_json(persona.behavior_policy.get("authoring")))
    refs.extend(_source_refs_from_json(persona.policy_plugin_config.get("authoring")))
    return _dedupe_refs(refs)


def _qa_memory_source_refs(memory: AgentMemoryItem) -> list[NarrativeQualityEvidenceRef]:
    refs = [NarrativeQualityEvidenceRef(kind="agent_memory_item", id=str(memory.id))]
    refs.extend(_source_refs_from_json(memory.metadata_json))
    if memory.source_event_id is not None:
        refs.append(NarrativeQualityEvidenceRef(kind="world_event", id=str(memory.source_event_id)))
    return _dedupe_refs(refs)


def _source_refs_from_json(value: Any) -> list[NarrativeQualityEvidenceRef]:
    if not isinstance(value, dict):
        return []
    candidates = (
        ("proposal_id", "authoring_proposal"),
        ("run_id", "authoring_import_run"),
        ("source_fragment_id", "authoring_source_fragment"),
        ("model_invocation_id", "model_invocation"),
        ("source_event_id", "world_event"),
    )
    refs: list[NarrativeQualityEvidenceRef] = []
    for key, kind in candidates:
        raw_value = value.get(key)
        if isinstance(raw_value, str) and raw_value:
            refs.append(NarrativeQualityEvidenceRef(kind=kind, id=raw_value))
    source_evidence = value.get("source_evidence")
    if isinstance(source_evidence, dict):
        refs.extend(_source_refs_from_json(source_evidence))
    return _dedupe_refs(refs)


def _memory_contamination_detected(memory: AgentMemoryItem) -> bool:
    metadata = memory.metadata_json or {}
    if _truthy_flag(metadata, "contaminated", "memory_contamination", "qa_contamination"):
        return True
    marker = str(metadata.get("qa_marker") or metadata.get("contamination_marker") or "")
    if marker.strip():
        return True
    content = memory.content.lower()
    return any(
        token in content
        for token in (
            "[contaminated]",
            "qa_contamination",
            "memory_contamination",
            "unsafe_memory_marker",
            "ooc memory",
        )
    )


def _worldline_contamination_detected(
    memory: AgentMemoryItem,
    worldline_id: uuid.UUID,
) -> bool:
    if memory.worldline_id is not None and memory.worldline_id != worldline_id:
        return True
    metadata = memory.metadata_json or {}
    for key in ("worldline_id", "source_worldline_id", "reference_worldline_id"):
        raw_value = metadata.get(key)
        if isinstance(raw_value, str) and raw_value:
            try:
                if uuid.UUID(raw_value) != worldline_id:
                    return True
            except ValueError:
                return True
    return False


def _turn_has_persona_drift_marker(turn: ConversationTurn) -> bool:
    text = f"{turn.input_text or ''} {turn.output_text or ''}".lower()
    return any(
        marker in text
        for marker in (
            "[ooc]",
            "ooc_marker",
            "persona_drift",
            "out of character",
            "generic chatbot",
        )
    )


def _turn_has_style_drift(persona: AgentPersona, turn: ConversationTurn) -> bool:
    text = f"{turn.input_text or ''} {turn.output_text or ''}".lower()
    behavior_policy = persona.behavior_policy or {}
    forbidden_terms = _json_string_list(behavior_policy.get("forbidden_terms"))
    forbidden_terms.extend(_json_string_list(behavior_policy.get("style_forbidden_terms")))
    if any(term.lower() in text for term in forbidden_terms):
        return True
    style_markers = _json_string_list(behavior_policy.get("required_style_markers"))
    if style_markers and not any(marker.lower() in text for marker in style_markers):
        return True
    return "style_drift" in text or "voice_drift" in text


def _relationship_drift_detected(
    memories: list[AgentMemoryItem],
    turns: list[ConversationTurn],
) -> bool:
    memory_text = " ".join(memory.content for memory in memories).lower()
    turn_text = " ".join(f"{turn.input_text or ''} {turn.output_text or ''}" for turn in turns)
    combined = f"{memory_text} {turn_text.lower()}"
    return any(
        marker in combined
        for marker in (
            "relationship_drift",
            "relationship contradiction",
            "trust suddenly reversed",
            "affection suddenly reversed",
        )
    )


def _truthy_flag(value: dict[str, Any], *keys: str) -> bool:
    for key in keys:
        flag = value.get(key)
        if flag is True:
            return True
        if isinstance(flag, str) and flag.strip().lower() in {"true", "yes", "1", "blocked"}:
            return True
    return False


def _json_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _dedupe_refs(refs: list[NarrativeQualityEvidenceRef]) -> list[NarrativeQualityEvidenceRef]:
    deduped: list[NarrativeQualityEvidenceRef] = []
    seen: set[tuple[str, str]] = set()
    for ref in refs:
        key = (ref.kind, ref.id)
        if key not in seen:
            seen.add(key)
            deduped.append(ref)
    return deduped


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


def _int_or_none(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
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


def _json_contains_leak(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if _is_leaky_key(str(key)) or _json_contains_leak(item):
                return True
        return False
    if isinstance(value, list | tuple):
        return any(_json_contains_leak(item) for item in value)
    if isinstance(value, str):
        return _LEAK_PATTERN.search(value) is not None
    return False
