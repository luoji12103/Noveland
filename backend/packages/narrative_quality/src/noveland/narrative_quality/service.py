from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any, cast

from noveland.agents.models import Agent
from noveland.asset_generation.models import (
    AssetGenerationPolicy,
    AssetGenerationProposal,
)
from noveland.conversations import ConversationService
from noveland.conversations.contracts import ConversationSessionRecord, ConversationTurnRecord
from noveland.conversations.models import (
    ConversationSession,
    ConversationTurn,
    ConversationTurnPresentation,
)
from noveland.conversations.presentation import ConversationPresentationService
from noveland.media.models import MediaJob
from noveland.narrative.contracts import NarrativeArtifactCreate
from noveland.narrative.models import NarrativeArtifact
from noveland.narrative.services import NarrativeArtifactService
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
from noveland.speech.models import AgentVoiceProfileBinding, SpeechStyleMapping, VoiceProfile
from noveland.speech.voice_profiles import SpeechValidationError, VoiceProfileService
from noveland.visual.models import CharacterSpriteSet, CharacterSpriteVariant
from noveland.worlds.gm import LivingWorldGMService
from noveland.worlds.guardrails import LivingWorldGuardrailService
from noveland.worlds.living_context import LivingWorldContextPack, LivingWorldContextSelector
from noveland.worlds.models import (
    GMEventProposal,
    LongRunEvalRun,
    NarrativeContinuityReview,
    RouteAffinity,
    Worldline,
)
from noveland.worlds.worldlines import worldline_or_404
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .contracts import (
    NarrativeQualityAlignmentFinding,
    NarrativeQualityConflictReport,
    NarrativeQualityContextKind,
    NarrativeQualityContextPreview,
    NarrativeQualityContextPreviewRequest,
    NarrativeQualityContinuityFinding,
    NarrativeQualityContinuityReviewRequest,
    NarrativeQualityContinuityReviewResult,
    NarrativeQualityDialogueFinding,
    NarrativeQualityDialogueReviewRequest,
    NarrativeQualityDialogueReviewResult,
    NarrativeQualityEvidenceRef,
    NarrativeQualityGMImportance,
    NarrativeQualityGMProposalCandidate,
    NarrativeQualityGMProposalGenerateRequest,
    NarrativeQualityGMProposalGenerationResult,
    NarrativeQualityInvocationRef,
    NarrativeQualityPacingFinding,
    NarrativeQualityPacingRecommendation,
    NarrativeQualityPacingReviewRequest,
    NarrativeQualityPacingReviewResult,
    NarrativeQualityPresentationAlignmentRequest,
    NarrativeQualityPresentationAlignmentResult,
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
