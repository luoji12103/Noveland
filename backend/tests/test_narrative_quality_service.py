from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import cast

from noveland.adapters.models import ProviderProfile
from noveland.agents.models import Agent, AgentRelationshipEdge, AgentRuntimeRun
from noveland.asset_generation.models import (
    AssetGenerationPolicy,
    AssetGenerationProposal,
    AssetGenerationRun,
)
from noveland.auth.models import User
from noveland.calendar.models import AgentCalendarEntry, WorldScheduleRule
from noveland.conversations import ConversationService
from noveland.conversations.contracts import (
    ConversationErrorPolicy,
    ConversationMemoryConfig,
    ConversationMode,
    ConversationParticipantDefinition,
    ConversationPolicyConfig,
    ConversationScopeType,
    ConversationSeed,
    ConversationSessionCreate,
    ConversationSpeakerPolicyMode,
    ConversationWriterConfig,
)
from noveland.conversations.models import (
    ConversationParticipant,
    ConversationSession,
    ConversationTurn,
    ConversationTurnPresentation,
)
from noveland.events.models import WorldEventModel, WorldSnapshotModel
from noveland.invocations.models import (
    AgentRuntimeRunModelInvocation,
    ModelInvocation,
    ModelInvocationTag,
    PromptSnapshot,
    PromptTemplate,
)
from noveland.media.models import MediaAsset, MediaJob
from noveland.memory.models import (
    AgentMemoryItem,
    AgentProfileSnapshotModel,
    MemoryBackendProfile,
    MemoryRetrievalLog,
    MemoryWriteJob,
    MemoryWriteLog,
)
from noveland.narrative.contracts import NarrativeArtifactKind
from noveland.narrative.models import NarrativeArtifact, NarrativePublication
from noveland.narrative_quality.contracts import (
    NarrativeQualityContextKind,
    NarrativeQualityContextPreviewRequest,
    NarrativeQualityContinuityReviewRequest,
    NarrativeQualityDialogueReviewRequest,
    NarrativeQualityGMProposalGenerateRequest,
    NarrativeQualityLongRunEvalRunRequest,
    NarrativeQualityPacingReviewRequest,
    NarrativeQualityPresentationAlignmentRequest,
    NarrativeQualityProgressionReviewRequest,
    NarrativeQualityWriterGenerateRequest,
)
from noveland.narrative_quality.service import (
    NarrativeQualityService,
    NarrativeQualityValidationError,
)
from noveland.observability.models import RuntimeDiagnosticEvent
from noveland.providers.contracts import (
    ProviderAdapterKind,
    ProviderIntegrationCreate,
    ProviderKind,
    ProviderScopeKind,
)
from noveland.providers.models import ProviderCapability, ProviderHealthCheck, ProviderIntegration
from noveland.providers.registry import ProviderRegistryService
from noveland.speech.models import AgentVoiceProfileBinding, SpeechStyleMapping, VoiceProfile
from noveland.visual.models import CharacterSpriteSet, CharacterSpriteVariant
from noveland.worlds.models import (
    CharacterEmotionalState,
    CharacterKnowledgeFact,
    DailyLifeEventCandidate,
    EndingCandidate,
    FactionProgressTrack,
    GMAgenda,
    GMEventProposal,
    GMStyleReview,
    InWorldNotification,
    LongRunEvalRun,
    NarrativeContinuityReview,
    OffscreenEventQueueItem,
    OrganizationMembership,
    PlayerActorProfile,
    PlayerChoiceRecord,
    PlayerInterventionRecord,
    PlayerJournalEntry,
    PlotThread,
    RouteAffinity,
    RouteMilestone,
    Scene,
    SecretRecord,
    StoryHook,
    World,
    WorldBible,
    Worldline,
    WorldOrganization,
)
from noveland.worlds.worldlines import ensure_primary_worldline
from sqlalchemy import Table, create_engine, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_agent_runtime_context_uses_living_world_selector() -> None:
    engine = _engine()
    world_id, worldline_id, agent_id = _seed_world_agent_and_fact(engine, "The bell rings at dusk.")

    with Session(engine) as session:
        preview = NarrativeQualityService(session).preview_context(
            world_id,
            NarrativeQualityContextPreviewRequest(
                worldline_id=worldline_id,
                context_kind=NarrativeQualityContextKind.AGENT,
                agent_id=agent_id,
            ),
        )

    assert preview.worldline_id == worldline_id
    assert preview.context_kind == NarrativeQualityContextKind.AGENT
    assert "The bell rings at dusk." in preview.prompt_text
    assert preview.metadata["context_sections"]["public_fact_count"] == 1
    assert preview.diagnostics["public_fact_count"] == 1


def test_conversation_runtime_context_is_worldline_scoped_and_sanitized() -> None:
    engine = _engine()
    world_id, worldline_id, agent_id = _seed_world_agent_and_fact(
        engine,
        "storage_uri=media://leaky/path",
    )
    conversation_id = _seed_conversation(engine, world_id, worldline_id, agent_id)

    with Session(engine) as session:
        preview = NarrativeQualityService(session).preview_context(
            world_id,
            NarrativeQualityContextPreviewRequest(
                worldline_id=worldline_id,
                context_kind=NarrativeQualityContextKind.CONVERSATION,
                conversation_id=conversation_id,
            ),
        )

    serialized = preview.model_dump_json()
    assert preview.subject_ref == f"conversation:{conversation_id}"
    assert preview.metadata["conversation_id"] == str(conversation_id)
    assert preview.metadata["turn_count"] == 1
    assert "storage_uri" not in serialized
    assert "media://" not in serialized


def test_conversation_context_rejects_cross_worldline_session() -> None:
    engine = _engine()
    world_id, worldline_id, agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    conversation_id = _seed_conversation(engine, world_id, worldline_id, agent_id)
    with Session(engine) as session:
        other_worldline = ensure_primary_worldline(session, world_id)
        fork_id = uuid.uuid4()
        session.add(
            type(other_worldline)(
                id=fork_id,
                world_id=world_id,
                worldline_key=f"fork-{fork_id.hex[:8]}",
                name="Fork",
                status="active",
                created_by_actor_ref="test",
                metadata_json={},
            )
        )
        session.commit()

    with Session(engine) as session:
        try:
            NarrativeQualityService(session).preview_context(
                world_id,
                NarrativeQualityContextPreviewRequest(
                    worldline_id=fork_id,
                    context_kind=NarrativeQualityContextKind.CONVERSATION,
                    conversation_id=conversation_id,
                ),
            )
        except NarrativeQualityValidationError as exc:
            assert "worldline" in str(exc)
        else:
            raise AssertionError("expected cross-worldline conversation rejection")


def test_gm_narrative_and_eval_contexts_return_safe_worldline_previews() -> None:
    engine = _engine()
    world_id, worldline_id, _agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")

    with Session(engine) as session:
        for kind in (
            NarrativeQualityContextKind.GM,
            NarrativeQualityContextKind.NARRATIVE,
            NarrativeQualityContextKind.EVAL,
        ):
            preview = NarrativeQualityService(session).preview_context(
                world_id,
                NarrativeQualityContextPreviewRequest(
                    worldline_id=worldline_id,
                    context_kind=kind,
                ),
            )
            assert preview.worldline_id == worldline_id
            assert preview.subject_ref == f"{kind.value}:{worldline_id}"
            assert "storage_uri" not in preview.model_dump_json()


def test_provider_backed_gm_generation_creates_proposal_and_invocation() -> None:
    engine = _engine()
    world_id, worldline_id, _agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    provider_id = _seed_text_provider(engine, world_id)

    with Session(engine) as session:
        result = NarrativeQualityService(session).generate_gm_proposal(
            world_id,
            NarrativeQualityGMProposalGenerateRequest(
                worldline_id=worldline_id,
                provider_id=provider_id,
                prompt_goal="Suggest a quiet daily event.",
                title="Quiet daily event",
                event_name="gm.daily_quiet_event",
                payload_json={"kind": "daily"},
            ),
            actor_ref="test",
        )
        session.commit()

    with Session(engine) as session:
        proposal = session.get(GMEventProposal, result.proposal.id)
        invocation = session.get(ModelInvocation, result.invocation.id)
        snapshot = session.scalars(
            select(PromptSnapshot).where(PromptSnapshot.invocation_id == result.invocation.id)
        ).one()
        event_count = session.scalar(select(func.count(WorldEventModel.id)))

    assert result.dry_run is False
    assert result.provider.provider_kind == ProviderKind.TEXT_GENERATION
    assert result.invocation.status == "succeeded"
    assert proposal is not None
    assert proposal.worldline_id == worldline_id
    assert proposal.status == "proposed"
    assert proposal.source_context["model_invocation_id"] == str(result.invocation.id)
    assert proposal.proposed_payload == {
        "kind": "daily",
        "source": "provider_backed_gm_proposal",
        "goal": "Suggest a quiet daily event.",
    }
    assert invocation is not None
    assert invocation.worldline_id == worldline_id
    assert snapshot.raw_request_json is not None
    assert snapshot.raw_request_json["request_json"]["context_kind"] == "gm"
    assert event_count == 0


def test_provider_backed_gm_generation_dry_run_writes_no_proposal() -> None:
    engine = _engine()
    world_id, worldline_id, _agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    provider_id = _seed_text_provider(engine, world_id)

    with Session(engine) as session:
        result = NarrativeQualityService(session).generate_gm_proposal(
            world_id,
            NarrativeQualityGMProposalGenerateRequest(
                worldline_id=worldline_id,
                provider_id=provider_id,
                prompt_goal="Preview only.",
                dry_run=True,
            ),
            actor_ref="test",
        )
        proposal_count = session.scalar(select(func.count(GMEventProposal.id)))
        invocation_count = session.scalar(select(func.count(ModelInvocation.id)))

    assert result.dry_run is True
    assert result.proposal.id is None
    assert result.proposal.status == "preview"
    assert proposal_count == 0
    assert invocation_count == 1


def test_provider_backed_gm_generation_rejects_non_text_provider() -> None:
    engine = _engine()
    world_id, worldline_id, _agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    provider_id = _seed_provider(engine, world_id, ProviderKind.IMAGE_GENERATION)

    with Session(engine) as session:
        try:
            NarrativeQualityService(session).generate_gm_proposal(
                world_id,
                NarrativeQualityGMProposalGenerateRequest(
                    worldline_id=worldline_id,
                    provider_id=provider_id,
                    prompt_goal="This should not run.",
                ),
                actor_ref="test",
            )
        except NarrativeQualityValidationError as exc:
            assert "text_generation" in str(exc)
        else:
            raise AssertionError("expected non-text provider rejection")
        assert session.scalar(select(func.count(GMEventProposal.id))) == 0
        assert session.scalar(select(func.count(ModelInvocation.id))) == 0


def test_provider_backed_gm_generation_sanitizes_proposal_traceability() -> None:
    engine = _engine()
    world_id, worldline_id, _agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    provider_id = _seed_text_provider(engine, world_id)

    with Session(engine) as session:
        result = NarrativeQualityService(session).generate_gm_proposal(
            world_id,
            NarrativeQualityGMProposalGenerateRequest(
                worldline_id=worldline_id,
                provider_id=provider_id,
                prompt_goal="storage_uri=media://hidden/object base64,AAAA",
                payload_json={"storage_uri": "media://hidden/object"},
            ),
            actor_ref="test",
        )
        serialized = result.model_dump_json()
        proposal = session.get(GMEventProposal, result.proposal.id)

    assert "storage_uri" not in serialized
    assert "media://" not in serialized
    assert "base64" not in serialized.lower()
    assert proposal is not None
    assert "storage_uri" not in proposal.proposed_payload
    assert "model_invocation_id" in proposal.source_context


def test_dialogue_review_existing_turn_uses_speaker_profile() -> None:
    engine = _engine()
    world_id, worldline_id, agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    conversation_id = _seed_conversation(engine, world_id, worldline_id, agent_id)
    turn_id = _seed_agent_turn(
        engine,
        conversation_id,
        agent_id,
        output_text="I will keep the quiet lantern safe.",
    )

    with Session(engine) as session:
        result = NarrativeQualityService(session).review_dialogue(
            world_id,
            NarrativeQualityDialogueReviewRequest(
                worldline_id=worldline_id,
                conversation_id=conversation_id,
                turn_id=turn_id,
            ),
        )
        original_turn = session.get(ConversationTurn, turn_id)

    assert result.review_status in {"pass", "warning"}
    assert result.speaker_agent_id == agent_id
    assert result.turn_id == turn_id
    assert result.reviewed_text == "I will keep the quiet lantern safe."
    assert original_turn is not None
    assert original_turn.output_text == "I will keep the quiet lantern safe."


def test_dialogue_review_redacts_unsafe_text_and_writes_no_event() -> None:
    engine = _engine()
    world_id, worldline_id, agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    conversation_id = _seed_conversation(engine, world_id, worldline_id, agent_id)

    with Session(engine) as session:
        result = NarrativeQualityService(session).review_dialogue(
            world_id,
            NarrativeQualityDialogueReviewRequest(
                worldline_id=worldline_id,
                conversation_id=conversation_id,
                speaker_agent_id=agent_id,
                text="storage_uri=media://hidden/object base64,AAAA",
            ),
        )
        event_count = session.scalar(select(func.count(WorldEventModel.id)))

    serialized = result.model_dump_json()
    assert result.review_status == "fail"
    assert any(finding.code == "unsafe_text_leak" for finding in result.findings)
    assert "storage_uri" not in serialized
    assert "media://" not in serialized
    assert "base64" not in serialized.lower()
    assert event_count == 0


def test_dialogue_review_rejects_cross_worldline_conversation() -> None:
    engine = _engine()
    world_id, worldline_id, agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    conversation_id = _seed_conversation(engine, world_id, worldline_id, agent_id)
    with Session(engine) as session:
        fork_id = uuid.uuid4()
        session.add(
            Worldline(
                id=fork_id,
                world_id=world_id,
                worldline_key=f"fork-{fork_id.hex[:8]}",
                name="Fork",
                status="active",
                created_by_actor_ref="test",
                metadata_json={},
            )
        )
        session.commit()

    with Session(engine) as session:
        try:
            NarrativeQualityService(session).review_dialogue(
                world_id,
                NarrativeQualityDialogueReviewRequest(
                    worldline_id=fork_id,
                    conversation_id=conversation_id,
                    text="Hello there.",
                ),
            )
        except NarrativeQualityValidationError as exc:
            assert "worldline" in str(exc)
        else:
            raise AssertionError("expected cross-worldline rejection")


def test_presentation_alignment_passes_for_matching_emotion_sprite_and_voice() -> None:
    engine = _engine()
    world_id, worldline_id, agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    conversation_id = _seed_conversation(engine, world_id, worldline_id, agent_id)
    turn_id = _seed_agent_turn(
        engine,
        conversation_id,
        agent_id,
        output_text="I sound happy.",
    )
    _seed_aligned_presentation(
        engine,
        world_id,
        worldline_id,
        agent_id,
        conversation_id,
        turn_id,
    )

    with Session(engine) as session:
        result = NarrativeQualityService(session).review_presentation_alignment(
            world_id,
            NarrativeQualityPresentationAlignmentRequest(
                worldline_id=worldline_id,
                conversation_id=conversation_id,
                turn_id=turn_id,
            ),
        )
        event_count = session.scalar(select(func.count(WorldEventModel.id)))

    assert result.alignment_status == "pass"
    assert result.emotion_key == "happy"
    assert result.sprite_variant_id is not None
    assert result.voice_profile_id is not None
    assert result.findings == []
    assert result.diagnostics["speech_style_mapping_available"] is True
    assert "storage_uri" not in result.model_dump_json()
    assert event_count == 0


def test_presentation_alignment_detects_sprite_emotion_mismatch() -> None:
    engine = _engine()
    world_id, worldline_id, agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    conversation_id = _seed_conversation(engine, world_id, worldline_id, agent_id)
    turn_id = _seed_agent_turn(
        engine,
        conversation_id,
        agent_id,
        output_text="I sound happy.",
    )
    _seed_aligned_presentation(
        engine,
        world_id,
        worldline_id,
        agent_id,
        conversation_id,
        turn_id,
        variant_expression="sad",
    )

    with Session(engine) as session:
        result = NarrativeQualityService(session).review_presentation_alignment(
            world_id,
            NarrativeQualityPresentationAlignmentRequest(
                worldline_id=worldline_id,
                conversation_id=conversation_id,
                turn_id=turn_id,
            ),
        )

    assert result.alignment_status == "warning"
    assert any(finding.code == "sprite_emotion_mismatch" for finding in result.findings)
    assert any(fix.code == "use_matching_sprite_variant" for fix in result.suggested_fixes)


def test_presentation_alignment_detects_missing_voice_profile_and_binding() -> None:
    engine = _engine()
    world_id, worldline_id, agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    conversation_id = _seed_conversation(engine, world_id, worldline_id, agent_id)
    turn_id = _seed_agent_turn(
        engine,
        conversation_id,
        agent_id,
        output_text="I sound happy.",
    )
    _seed_aligned_presentation(
        engine,
        world_id,
        worldline_id,
        agent_id,
        conversation_id,
        turn_id,
        include_voice=False,
    )

    with Session(engine) as session:
        result = NarrativeQualityService(session).review_presentation_alignment(
            world_id,
            NarrativeQualityPresentationAlignmentRequest(
                worldline_id=worldline_id,
                conversation_id=conversation_id,
                turn_id=turn_id,
            ),
        )

    assert result.alignment_status == "warning"
    assert any(finding.code == "missing_voice_profile" for finding in result.findings)
    assert any(finding.code == "missing_voice_binding" for finding in result.findings)


def test_presentation_alignment_rejects_cross_worldline_request() -> None:
    engine = _engine()
    world_id, worldline_id, agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    conversation_id = _seed_conversation(engine, world_id, worldline_id, agent_id)
    turn_id = _seed_agent_turn(
        engine,
        conversation_id,
        agent_id,
        output_text="I sound happy.",
    )
    _seed_aligned_presentation(
        engine,
        world_id,
        worldline_id,
        agent_id,
        conversation_id,
        turn_id,
    )
    fork_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            Worldline(
                id=fork_id,
                world_id=world_id,
                worldline_key=f"fork-{fork_id.hex[:8]}",
                name="Fork",
                status="active",
                created_by_actor_ref="test",
                metadata_json={},
            )
        )
        session.commit()

    with Session(engine) as session:
        try:
            NarrativeQualityService(session).review_presentation_alignment(
                world_id,
                NarrativeQualityPresentationAlignmentRequest(
                    worldline_id=fork_id,
                    conversation_id=conversation_id,
                    turn_id=turn_id,
                ),
            )
        except NarrativeQualityValidationError as exc:
            assert "worldline" in str(exc)
        else:
            raise AssertionError("expected cross-worldline rejection")


def test_narrative_writer_v2_creates_worldline_scoped_draft_and_invocation() -> None:
    engine = _engine()
    world_id, worldline_id, agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    conversation_id = _seed_conversation(engine, world_id, worldline_id, agent_id)
    provider_id = _seed_text_provider(engine, world_id)

    with Session(engine) as session:
        result = NarrativeQualityService(session).generate_narrative_v2(
            world_id,
            NarrativeQualityWriterGenerateRequest(
                worldline_id=worldline_id,
                conversation_id=conversation_id,
                provider_id=provider_id,
                artifact_kind=NarrativeArtifactKind.CHAPTER_DRAFT,
                title="Quiet chapter",
                prompt_goal="Draft a quiet reader-safe chapter.",
            ),
            actor_ref="test",
        )
        session.commit()

    assert result.dry_run is False
    assert result.provider.provider_kind == ProviderKind.TEXT_GENERATION
    assert result.invocation.status == "succeeded"
    assert result.artifact is not None
    assert result.artifact.worldline_id == worldline_id
    assert result.artifact.source_conversation_id == conversation_id
    assert result.artifact.title == "Quiet chapter"
    assert result.artifact.metadata["source"] == "narrative_writer_v2"
    assert result.artifact.metadata["model_invocation_id"] == str(result.invocation.id)
    assert "fake text:" in result.artifact.content
    with Session(engine) as session:
        artifact = session.get(NarrativeArtifact, result.artifact.id)
        invocation = session.get(ModelInvocation, result.invocation.id)
        snapshot = session.scalars(
            select(PromptSnapshot).where(PromptSnapshot.invocation_id == result.invocation.id)
        ).one()
        publication_count = session.scalar(select(func.count(NarrativePublication.id)))
        event_count = session.scalar(select(func.count(WorldEventModel.id)))

    assert artifact is not None
    assert artifact.worldline_id == worldline_id
    assert invocation is not None
    assert invocation.worldline_id == worldline_id
    assert snapshot.raw_request_json is not None
    assert snapshot.raw_request_json["request_json"]["context_kind"] == "narrative"
    assert snapshot.raw_request_json["request_json"]["operation"] == (
        "narrative_writer_v2_generation"
    )
    assert publication_count == 0
    assert event_count == 0


def test_narrative_writer_v2_dry_run_writes_invocation_but_no_artifact() -> None:
    engine = _engine()
    world_id, worldline_id, _agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    provider_id = _seed_text_provider(engine, world_id)

    with Session(engine) as session:
        result = NarrativeQualityService(session).generate_narrative_v2(
            world_id,
            NarrativeQualityWriterGenerateRequest(
                worldline_id=worldline_id,
                provider_id=provider_id,
                prompt_goal="Preview a world summary.",
                artifact_kind=NarrativeArtifactKind.CONVERSATION_SUMMARY,
                dry_run=True,
            ),
            actor_ref="test",
        )
        artifact_count = session.scalar(select(func.count(NarrativeArtifact.id)))
        invocation_count = session.scalar(select(func.count(ModelInvocation.id)))

    assert result.dry_run is True
    assert result.artifact is None
    assert result.diagnostics["artifact_persisted"] is False
    assert artifact_count == 0
    assert invocation_count == 1


def test_narrative_writer_v2_rejects_cross_worldline_conversation() -> None:
    engine = _engine()
    world_id, worldline_id, agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    conversation_id = _seed_conversation(engine, world_id, worldline_id, agent_id)
    provider_id = _seed_text_provider(engine, world_id)
    with Session(engine) as session:
        fork_id = uuid.uuid4()
        session.add(
            Worldline(
                id=fork_id,
                world_id=world_id,
                worldline_key=f"fork-{fork_id.hex[:8]}",
                name="Fork",
                status="active",
                created_by_actor_ref="test",
                metadata_json={},
            )
        )
        session.commit()

    with Session(engine) as session:
        try:
            NarrativeQualityService(session).generate_narrative_v2(
                world_id,
                NarrativeQualityWriterGenerateRequest(
                    worldline_id=fork_id,
                    conversation_id=conversation_id,
                    provider_id=provider_id,
                    prompt_goal="This should not run.",
                ),
                actor_ref="test",
            )
        except NarrativeQualityValidationError as exc:
            assert "worldline" in str(exc)
        else:
            raise AssertionError("expected cross-worldline rejection")
        assert session.scalar(select(func.count(NarrativeArtifact.id))) == 0
        assert session.scalar(select(func.count(ModelInvocation.id))) == 0


def test_narrative_writer_v2_rejects_non_text_provider() -> None:
    engine = _engine()
    world_id, worldline_id, _agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    provider_id = _seed_provider(engine, world_id, ProviderKind.IMAGE_GENERATION)

    with Session(engine) as session:
        try:
            NarrativeQualityService(session).generate_narrative_v2(
                world_id,
                NarrativeQualityWriterGenerateRequest(
                    worldline_id=worldline_id,
                    provider_id=provider_id,
                    prompt_goal="This should not run.",
                ),
                actor_ref="test",
            )
        except NarrativeQualityValidationError as exc:
            assert "text_generation" in str(exc)
        else:
            raise AssertionError("expected non-text provider rejection")
        assert session.scalar(select(func.count(NarrativeArtifact.id))) == 0
        assert session.scalar(select(func.count(ModelInvocation.id))) == 0


def test_narrative_writer_v2_rejects_sensitive_request_json() -> None:
    engine = _engine()
    world_id, worldline_id, _agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    provider_id = _seed_text_provider(engine, world_id)

    with Session(engine) as session:
        try:
            NarrativeQualityService(session).generate_narrative_v2(
                world_id,
                NarrativeQualityWriterGenerateRequest(
                    worldline_id=worldline_id,
                    provider_id=provider_id,
                    prompt_goal="This should not run.",
                    provider_request_json={"nested": {"api_key": "sk-secret"}},
                ),
                actor_ref="test",
            )
        except ValueError as exc:
            assert "api_key" in str(exc)
        else:
            raise AssertionError("expected sensitive request rejection")
        assert session.scalar(select(func.count(NarrativeArtifact.id))) == 0
        assert session.scalar(select(func.count(ModelInvocation.id))) == 0


def test_narrative_writer_v2_sanitizes_result_and_artifact_metadata() -> None:
    engine = _engine()
    world_id, worldline_id, _agent_id = _seed_world_agent_and_fact(
        engine,
        "storage_uri=media://hidden/object base64,AAAA",
    )
    provider_id = _seed_text_provider(engine, world_id)

    with Session(engine) as session:
        result = NarrativeQualityService(session).generate_narrative_v2(
            world_id,
            NarrativeQualityWriterGenerateRequest(
                worldline_id=worldline_id,
                provider_id=provider_id,
                title="Leaky preview",
                prompt_goal="storage_uri=media://hidden/object base64,AAAA",
            ),
            actor_ref="test",
        )
        artifact = session.get(NarrativeArtifact, result.artifact.id if result.artifact else None)

    serialized = result.model_dump_json()
    assert result.artifact is not None
    assert artifact is not None
    assert "storage_uri" not in serialized
    assert "media://" not in serialized
    assert "base64" not in serialized.lower()
    assert "storage_uri" not in str(artifact.artifact_metadata)
    assert "media://" not in str(artifact.artifact_metadata)


def test_continuity_review_v2_reviews_artifact_content_and_persists_review() -> None:
    engine = _engine()
    world_id, worldline_id, _agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    artifact_id = _seed_narrative_artifact(
        engine,
        world_id,
        worldline_id,
        content="The daily scene stays in canon.",
    )

    with Session(engine) as session:
        result = NarrativeQualityService(session).review_continuity_v2(
            world_id,
            NarrativeQualityContinuityReviewRequest(
                worldline_id=worldline_id,
                artifact_id=artifact_id,
                source_kind="artifact",
                source_ref=str(artifact_id),
            ),
        )
        review = session.get(NarrativeContinuityReview, result.review_id)
        event_count = session.scalar(select(func.count(WorldEventModel.id)))

    assert result.worldline_id == worldline_id
    assert result.artifact_id == artifact_id
    assert result.review_status in {"pass", "warning"}
    assert review is not None
    assert review.artifact_id == artifact_id
    assert review.worldline_id == worldline_id
    assert event_count == 0


def test_continuity_review_v2_reviews_explicit_text_without_artifact() -> None:
    engine = _engine()
    world_id, worldline_id, _agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")

    with Session(engine) as session:
        result = NarrativeQualityService(session).review_continuity_v2(
            world_id,
            NarrativeQualityContinuityReviewRequest(
                worldline_id=worldline_id,
                source_kind="manual",
                reviewed_text="Everyone knows the same time paradox happened on this route.",
            ),
        )

    assert result.artifact_id is None
    assert result.review_status == "warning"
    codes = {finding.code for finding in result.findings}
    assert "knowledge_leak_risk" in codes
    assert "time_contradiction_risk" in codes
    assert any(report.code == "route_context_missing" for report in result.conflict_reports)


def test_continuity_review_v2_detects_hidden_secret_leak() -> None:
    engine = _engine()
    world_id, worldline_id, agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    _seed_hidden_secret(engine, world_id, worldline_id, "The locked diary is under the desk.")

    with Session(engine) as session:
        result = NarrativeQualityService(session).review_continuity_v2(
            world_id,
            NarrativeQualityContinuityReviewRequest(
                worldline_id=worldline_id,
                source_kind="manual",
                reviewed_text="The locked diary is under the desk.",
                metadata={"agent_id": str(agent_id)},
            ),
        )

    assert result.review_status == "fail"
    assert any(finding.code == "hidden_secret_leak" for finding in result.findings)
    serialized = result.model_dump_json()
    assert "locked diary" not in serialized.lower()
    assert "secret_id" not in serialized


def test_continuity_review_v2_detects_relationship_jump_from_metadata() -> None:
    engine = _engine()
    world_id, worldline_id, _agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")

    with Session(engine) as session:
        result = NarrativeQualityService(session).review_continuity_v2(
            world_id,
            NarrativeQualityContinuityReviewRequest(
                worldline_id=worldline_id,
                source_kind="manual",
                reviewed_text="They decide to trust each other after one scene.",
                metadata={"relationship_delta": {"trust": 75}},
            ),
        )

    assert result.review_status == "pass"
    assert any(report.code == "relationship_jump" for report in result.conflict_reports)
    assert any(fix.code == "add_relationship_transition" for fix in result.repair_suggestions)


def test_continuity_review_v2_does_not_flag_route_when_active_route_exists() -> None:
    engine = _engine()
    world_id, worldline_id, agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    _seed_active_route(engine, world_id, worldline_id, agent_id)

    with Session(engine) as session:
        result = NarrativeQualityService(session).review_continuity_v2(
            world_id,
            NarrativeQualityContinuityReviewRequest(
                worldline_id=worldline_id,
                source_kind="manual",
                reviewed_text="This route scene moves forward quietly.",
            ),
        )

    assert not any(report.code == "route_context_missing" for report in result.conflict_reports)


def test_continuity_review_v2_rejects_cross_worldline_artifact() -> None:
    engine = _engine()
    world_id, worldline_id, _agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    fork_id = _seed_worldline(engine, world_id)
    artifact_id = _seed_narrative_artifact(
        engine,
        world_id,
        worldline_id,
        content="Original worldline artifact.",
    )

    with Session(engine) as session:
        try:
            NarrativeQualityService(session).review_continuity_v2(
                world_id,
                NarrativeQualityContinuityReviewRequest(
                    worldline_id=fork_id,
                    artifact_id=artifact_id,
                    source_kind="artifact",
                ),
            )
        except NarrativeQualityValidationError as exc:
            assert "worldline" in str(exc)
        else:
            raise AssertionError("expected cross-worldline artifact rejection")
        assert session.scalar(select(func.count(NarrativeContinuityReview.id))) == 0


def test_continuity_review_v2_rejects_sensitive_metadata() -> None:
    engine = _engine()
    world_id, worldline_id, _agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")

    with Session(engine) as session:
        try:
            NarrativeQualityService(session).review_continuity_v2(
                world_id,
                NarrativeQualityContinuityReviewRequest(
                    worldline_id=worldline_id,
                    source_kind="manual",
                    reviewed_text="Safe text.",
                    metadata={"nested": {"api_key": "sk-secret"}},
                ),
            )
        except ValueError as exc:
            assert "api_key" in str(exc)
        else:
            raise AssertionError("expected sensitive metadata rejection")
        assert session.scalar(select(func.count(NarrativeContinuityReview.id))) == 0


def test_continuity_review_v2_sanitizes_response() -> None:
    engine = _engine()
    world_id, worldline_id, _agent_id = _seed_world_agent_and_fact(
        engine,
        "storage_uri=media://hidden/object base64,AAAA",
    )

    with Session(engine) as session:
        result = NarrativeQualityService(session).review_continuity_v2(
            world_id,
            NarrativeQualityContinuityReviewRequest(
                worldline_id=worldline_id,
                source_kind="manual",
                reviewed_text="storage_uri=media://hidden/object base64,AAAA",
                metadata={"notes": "file:///tmp/secret.txt"},
            ),
        )

    serialized = result.model_dump_json().lower()
    assert "storage_uri" not in serialized
    assert "media://" not in serialized
    assert "base64" not in serialized
    assert "file://" not in serialized
    assert "raw_prompt" not in serialized
    assert "raw_output" not in serialized


def test_runtime_pacing_review_summarizes_policy_and_pending_jobs() -> None:
    engine = _engine()
    world_id, worldline_id, agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    conversation_id = _seed_conversation(engine, world_id, worldline_id, agent_id)
    turn_id = _seed_agent_turn(
        engine,
        conversation_id,
        agent_id,
        output_text="Current line.",
    )
    policy_id = _seed_pacing_policy(
        engine,
        world_id,
        worldline_id,
        max_pending_jobs=3,
        max_pending_cost=1.0,
    )
    _seed_media_job(engine, world_id, worldline_id, conversation_id, turn_id, priority=0)

    with Session(engine) as session:
        result = NarrativeQualityService(session).review_runtime_pacing(
            world_id,
            NarrativeQualityPacingReviewRequest(
                worldline_id=worldline_id,
                conversation_id=conversation_id,
                current_turn_id=turn_id,
                policy_id=policy_id,
            ),
        )
        event_count = session.scalar(select(func.count(WorldEventModel.id)))
        media_job_count = session.scalar(select(func.count(MediaJob.id)))

    assert result.pacing_status == "warning"
    assert result.policy_id == policy_id
    assert result.queue_summary["pending_job_count"] == 1
    assert result.budget_summary["max_pending_cost"] == 1.0
    assert event_count == 0
    assert media_job_count == 1


def test_runtime_pacing_review_flags_job_limit_and_superseded_jobs() -> None:
    engine = _engine()
    world_id, worldline_id, agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    conversation_id = _seed_conversation(engine, world_id, worldline_id, agent_id)
    turn_id = _seed_agent_turn(
        engine,
        conversation_id,
        agent_id,
        output_text="Current line.",
    )
    _seed_media_job(
        engine,
        world_id,
        worldline_id,
        conversation_id,
        turn_id,
        invalidation_key="turn:shared",
    )
    _seed_media_job(
        engine,
        world_id,
        worldline_id,
        conversation_id,
        turn_id,
        invalidation_key="turn:shared",
    )

    with Session(engine) as session:
        result = NarrativeQualityService(session).review_runtime_pacing(
            world_id,
            NarrativeQualityPacingReviewRequest(
                worldline_id=worldline_id,
                conversation_id=conversation_id,
                current_turn_id=turn_id,
                max_pending_jobs=1,
            ),
        )
        running_count = session.scalar(
            select(func.count(MediaJob.id)).where(MediaJob.status == "queued")
        )

    assert result.pacing_status == "warning"
    assert result.queue_summary["duplicate_invalidation_key_count"] == 1
    assert any(finding.code == "pending_media_job_limit_exceeded" for finding in result.findings)
    assert any(finding.code == "superseded_media_jobs_detected" for finding in result.findings)
    assert any(rec.code == "cancel_superseded_media_jobs" for rec in result.recommendations)
    assert running_count == 2


def test_runtime_pacing_review_flags_budget_overflow_and_current_turn_missing_assets() -> None:
    engine = _engine()
    world_id, worldline_id, agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    conversation_id = _seed_conversation(engine, world_id, worldline_id, agent_id)
    turn_id = _seed_agent_turn(
        engine,
        conversation_id,
        agent_id,
        output_text="Current line.",
    )
    _seed_asset_generation_run_and_proposal(
        engine,
        world_id,
        worldline_id,
        conversation_id,
        turn_id,
        estimated_cost=2.5,
    )

    with Session(engine) as session:
        result = NarrativeQualityService(session).review_runtime_pacing(
            world_id,
            NarrativeQualityPacingReviewRequest(
                worldline_id=worldline_id,
                conversation_id=conversation_id,
                current_turn_id=turn_id,
                max_pending_cost=1.0,
            ),
        )
        proposal_count = session.scalar(select(func.count(AssetGenerationProposal.id)))

    assert result.pacing_status == "warning"
    assert result.budget_summary["estimated_pending_cost"] == 2.5
    assert result.lookahead_summary["current_turn_missing_assets"] is True
    assert any(finding.code == "asset_generation_budget_exceeded" for finding in result.findings)
    assert any(finding.code == "current_turn_missing_assets" for finding in result.findings)
    assert any(rec.code == "prioritize_current_visible_turn" for rec in result.recommendations)
    assert proposal_count == 1


def test_runtime_pacing_review_rejects_cross_worldline_turn() -> None:
    engine = _engine()
    world_id, worldline_id, agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    conversation_id = _seed_conversation(engine, world_id, worldline_id, agent_id)
    turn_id = _seed_agent_turn(
        engine,
        conversation_id,
        agent_id,
        output_text="Current line.",
    )
    fork_id = _seed_worldline(engine, world_id)

    with Session(engine) as session:
        try:
            NarrativeQualityService(session).review_runtime_pacing(
                world_id,
                NarrativeQualityPacingReviewRequest(
                    worldline_id=fork_id,
                    current_turn_id=turn_id,
                ),
            )
        except NarrativeQualityValidationError as exc:
            assert "turn" in str(exc)
        else:
            raise AssertionError("expected cross-worldline turn rejection")


def test_runtime_pacing_review_sanitizes_response() -> None:
    engine = _engine()
    world_id, worldline_id, agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    conversation_id = _seed_conversation(engine, world_id, worldline_id, agent_id)
    turn_id = _seed_agent_turn(
        engine,
        conversation_id,
        agent_id,
        output_text="Current line.",
    )
    _seed_media_job(
        engine,
        world_id,
        worldline_id,
        conversation_id,
        turn_id,
        request_json={"storage_uri": "media://hidden/object", "safe": True},
    )

    with Session(engine) as session:
        result = NarrativeQualityService(session).review_runtime_pacing(
            world_id,
            NarrativeQualityPacingReviewRequest(
                worldline_id=worldline_id,
                conversation_id=conversation_id,
                current_turn_id=turn_id,
            ),
        )

    serialized = result.model_dump_json().lower()
    assert "storage_uri" not in serialized
    assert "media://" not in serialized
    assert "base64" not in serialized
    assert "raw_prompt" not in serialized
    assert "raw_output" not in serialized


def test_route_relationship_progression_review_summarizes_records() -> None:
    engine = _engine()
    world_id, worldline_id, agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    route_id = _seed_progression_fixture(
        engine,
        world_id,
        worldline_id,
        agent_id,
        include_milestone=True,
        include_choice=True,
    )

    with Session(engine) as session:
        result = NarrativeQualityService(session).review_route_relationship_progression(
            world_id,
            NarrativeQualityProgressionReviewRequest(
                worldline_id=worldline_id,
                agent_id=agent_id,
                route_affinity_id=route_id,
            ),
        )

    assert result.progression_status == "warning"
    assert result.relationship_summary["relationship_count"] == 1
    assert result.route_summary["route_count"] == 1
    assert result.route_summary["milestone_count"] == 1
    assert result.route_summary["route_choice_count"] == 1
    assert result.event_summary["recent_event_count"] == 1
    assert result.proposal_summary["open_proposal_count"] == 1
    assert any(
        finding.code == "relationship_metric_contradiction"
        for finding in result.findings
    )
    assert any(
        recommendation.action_json.get("mutates_state") is False
        for recommendation in result.recommendations
    )
    with Session(engine) as session:
        assert session.scalar(select(func.count(WorldEventModel.id))) == 1
        assert session.scalar(select(func.count(RouteAffinity.id))) == 1


def test_route_relationship_progression_review_flags_route_gaps() -> None:
    engine = _engine()
    world_id, worldline_id, agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    route_id = _seed_progression_fixture(
        engine,
        world_id,
        worldline_id,
        agent_id,
        route_stage=1,
        milestone_stage=3,
        include_choice=False,
    )

    with Session(engine) as session:
        result = NarrativeQualityService(session).review_route_relationship_progression(
            world_id,
            NarrativeQualityProgressionReviewRequest(
                worldline_id=worldline_id,
                route_affinity_id=route_id,
            ),
        )

    codes = {finding.code for finding in result.findings}
    assert result.progression_status == "warning"
    assert "route_stage_milestone_mismatch" in codes
    assert "ending_requirements_unsatisfied" in codes
    assert "route_choice_trace_missing" in codes


def test_route_relationship_progression_review_rejects_cross_worldline_route() -> None:
    engine = _engine()
    world_id, worldline_id, agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    fork_id = _seed_worldline(engine, world_id)
    route_id = _seed_active_route(engine, world_id, fork_id, agent_id)

    with Session(engine) as session:
        try:
            NarrativeQualityService(session).review_route_relationship_progression(
                world_id,
                NarrativeQualityProgressionReviewRequest(
                    worldline_id=worldline_id,
                    route_affinity_id=route_id,
                ),
            )
        except NarrativeQualityValidationError as exc:
            assert "route affinity" in str(exc)
        else:
            raise AssertionError("expected cross-worldline route rejection")


def test_route_relationship_progression_review_sanitizes_response() -> None:
    engine = _engine()
    world_id, worldline_id, agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    route_id = _seed_progression_fixture(
        engine,
        world_id,
        worldline_id,
        agent_id,
        event_payload={"storage_uri": "media://hidden/object", "safe": True},
    )

    with Session(engine) as session:
        result = NarrativeQualityService(session).review_route_relationship_progression(
            world_id,
            NarrativeQualityProgressionReviewRequest(
                worldline_id=worldline_id,
                route_affinity_id=route_id,
            ),
        )

    serialized = result.model_dump_json().lower()
    assert "storage_uri" not in serialized
    assert "media://" not in serialized
    assert "base64" not in serialized
    assert "raw_prompt" not in serialized
    assert "raw_output" not in serialized
    assert any(finding.code == "unsafe_progression_event_payload" for finding in result.findings)


def test_long_living_world_eval_reuses_long_run_eval_records() -> None:
    engine = _engine()
    world_id, worldline_id, agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    _seed_long_run_eval_evidence(engine, world_id, worldline_id, agent_id)

    with Session(engine) as session:
        result = NarrativeQualityService(session).run_long_living_world_eval(
            world_id,
            NarrativeQualityLongRunEvalRunRequest(
                worldline_id=worldline_id,
                eval_key="narrative-quality-seven-day",
                horizon_days=7,
                metadata={"operator_note": "safe"},
            ),
        )
        eval_count = session.scalar(select(func.count(LongRunEvalRun.id)))
        event_count = session.scalar(select(func.count(WorldEventModel.id)))
        invocation_count = session.scalar(select(func.count(ModelInvocation.id)))

    assert result.worldline_id == worldline_id
    assert result.eval_key == "narrative-quality-seven-day"
    assert result.horizon_days == 7
    assert result.status in {"completed", "warning", "failed"}
    assert result.drift_metrics["event_count"] == 1
    assert result.drift_metrics["relationships"] == 1
    assert result.diagnostics["provider_call_count"] == 0
    assert result.diagnostics["daemon_run"] is False
    assert result.diagnostics["world_event_written"] is False
    assert eval_count == 1
    assert event_count == 1
    assert invocation_count == 0


def test_long_living_world_eval_lists_and_gets_worldline_scoped_runs() -> None:
    engine = _engine()
    world_id, worldline_id, agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    _seed_long_run_eval_evidence(engine, world_id, worldline_id, agent_id)
    fork_id = _seed_worldline(engine, world_id)
    with Session(engine) as session:
        service = NarrativeQualityService(session)
        first = service.run_long_living_world_eval(
            world_id,
            NarrativeQualityLongRunEvalRunRequest(
                worldline_id=worldline_id,
                eval_key="primary-run",
            ),
        )
        service.run_long_living_world_eval(
            world_id,
            NarrativeQualityLongRunEvalRunRequest(
                worldline_id=fork_id,
                eval_key="fork-run",
            ),
        )
        primary_runs = service.list_long_living_world_evals(
            world_id,
            worldline_id,
            limit=10,
        )
        loaded = service.get_long_living_world_eval(world_id, worldline_id, first.run_id)

    assert [run.eval_key for run in primary_runs] == ["primary-run"]
    assert loaded.run_id == first.run_id
    assert loaded.worldline_id == worldline_id

    with Session(engine) as session:
        try:
            NarrativeQualityService(session).get_long_living_world_eval(
                world_id,
                fork_id,
                first.run_id,
            )
        except NarrativeQualityValidationError as exc:
            assert "worldline" in str(exc)
        else:
            raise AssertionError("expected cross-worldline long-run eval rejection")


def test_long_living_world_eval_rejects_sensitive_metadata() -> None:
    engine = _engine()
    world_id, worldline_id, _agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")

    with Session(engine) as session:
        try:
            NarrativeQualityService(session).run_long_living_world_eval(
                world_id,
                NarrativeQualityLongRunEvalRunRequest(
                    worldline_id=worldline_id,
                    metadata={"nested": {"api_key": "sk-secret"}},
                ),
            )
        except NarrativeQualityValidationError as exc:
            assert "api_key" in str(exc)
        else:
            raise AssertionError("expected sensitive metadata rejection")
        assert session.scalar(select(func.count(LongRunEvalRun.id))) == 0


def test_long_living_world_eval_sanitizes_response_metadata_and_blockers() -> None:
    engine = _engine()
    world_id, worldline_id, _agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")

    with Session(engine) as session:
        result = NarrativeQualityService(session).run_long_living_world_eval(
            world_id,
            NarrativeQualityLongRunEvalRunRequest(
                worldline_id=worldline_id,
                metadata={
                    "note": "storage_uri=media://hidden/object base64,AAAA",
                    "path": "file:///tmp/hidden.txt",
                },
            ),
        )

    serialized = result.model_dump_json().lower()
    assert result.status == "failed"
    assert any(report.code == "no_worldline_events" for report in result.failure_reports)
    assert "storage_uri" not in serialized
    assert "media://" not in serialized
    assert "base64" not in serialized
    assert "file://" not in serialized
    assert "raw_prompt" not in serialized
    assert "raw_output" not in serialized


def test_narrative_quality_dashboard_summarizes_read_only_metrics() -> None:
    engine = _engine()
    world_id, worldline_id, agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    _seed_text_provider(engine, world_id)
    conversation_id = _seed_conversation(engine, world_id, worldline_id, agent_id)
    turn_id = _seed_agent_turn(
        engine,
        conversation_id,
        agent_id,
        output_text="I will keep the quiet lantern safe.",
    )
    _seed_aligned_presentation(
        engine,
        world_id,
        worldline_id,
        agent_id,
        conversation_id,
        turn_id,
    )
    _seed_long_run_eval_evidence(engine, world_id, worldline_id, agent_id)
    with Session(engine) as session:
        NarrativeQualityService(session).run_long_living_world_eval(
            world_id,
            NarrativeQualityLongRunEvalRunRequest(worldline_id=worldline_id),
        )
        session.commit()

    with Session(engine) as session:
        before_invocations = session.scalar(select(func.count(ModelInvocation.id)))
        before_events = session.scalar(select(func.count(WorldEventModel.id)))
        before_evals = session.scalar(select(func.count(LongRunEvalRun.id)))
        result = NarrativeQualityService(session).dashboard_summary(world_id, worldline_id)
        after_invocations = session.scalar(select(func.count(ModelInvocation.id)))
        after_events = session.scalar(select(func.count(WorldEventModel.id)))
        after_evals = session.scalar(select(func.count(LongRunEvalRun.id)))

    assert result.worldline_id == worldline_id
    assert result.quality_status in {"pass", "warning"}
    assert result.metrics["providers"]["active_text_provider_count"] == 1
    assert result.metrics["dialogue"]["turn_count"] >= 1
    assert result.metrics["presentation_alignment"]["presentation_count"] == 1
    assert result.metrics["long_run"]["run_count"] == 1
    assert result.diagnostics["provider_call_count"] == 0
    assert result.diagnostics["mutation_count"] == 0
    assert before_invocations == after_invocations
    assert before_events == after_events
    assert before_evals == after_evals
    serialized = result.model_dump_json().lower()
    assert "storage_uri" not in serialized
    assert "media://" not in serialized
    assert "raw_prompt" not in serialized


def test_narrative_quality_dashboard_detects_blockers_and_sanitizes_evidence() -> None:
    engine = _engine()
    world_id, worldline_id, _agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    provider_id = _seed_text_provider(engine, world_id)
    _seed_provider_health(
        engine,
        provider_id,
        status="unhealthy",
        metadata={"nested": {"api_key": "sk-secret"}},
        error_text="auth failed for sk-secret",
    )
    with Session(engine) as session:
        session.add(
            NarrativeContinuityReview(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                artifact_id=None,
                source_kind="manual",
                source_ref=None,
                reviewed_text="storage_uri=media://hidden/object",
                status="fail",
                issues=[
                    {
                        "code": "knowledge_leak_risk",
                        "severity": "error",
                        "message": "storage_uri=media://hidden/object",
                    }
                ],
                metadata_json={"safe": True},
            )
        )
        session.add(
            WorldEventModel(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                sequence=1,
                event_name="system.audit",
                importance="system",
                payload={"storage_uri": "media://hidden/object", "safe": True},
                wall_time=datetime.now(UTC),
                actor_ref="test",
            )
        )
        session.commit()

    with Session(engine) as session:
        result = NarrativeQualityService(session).dashboard_summary(world_id, worldline_id)

    codes = {signal.code for signal in result.blockers}
    assert result.quality_status == "fail"
    assert "continuity_review_failures" in codes
    assert "unsafe_world_event_payload" in codes
    assert "unsafe_provider_health_metadata" in codes
    serialized = result.model_dump_json().lower()
    assert "storage_uri" not in serialized
    assert "media://" not in serialized
    assert "sk-secret" not in serialized
    assert "raw_prompt" not in serialized


def test_narrative_quality_dashboard_rejects_foreign_worldline() -> None:
    engine = _engine()
    world_id, _worldline_id, _agent_id = _seed_world_agent_and_fact(engine, "Safe fact.")
    other_world_id, other_worldline_id, _other_agent_id = _seed_world_agent_and_fact(
        engine,
        "Other fact.",
    )
    assert other_world_id != world_id

    with Session(engine) as session:
        try:
            NarrativeQualityService(session).dashboard_summary(world_id, other_worldline_id)
        except ValueError as exc:
            assert "worldline" in str(exc)
        else:
            raise AssertionError("expected foreign worldline rejection")


def _engine() -> Engine:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    _create_tables(engine)
    return engine


def _create_tables(engine: Engine) -> None:
    for table in (
        cast(Table, User.__table__),
        cast(Table, World.__table__),
        cast(Table, Worldline.__table__),
        cast(Table, Scene.__table__),
        cast(Table, Agent.__table__),
        cast(Table, WorldOrganization.__table__),
        cast(Table, OrganizationMembership.__table__),
        cast(Table, FactionProgressTrack.__table__),
        cast(Table, AgentRelationshipEdge.__table__),
        cast(Table, AgentCalendarEntry.__table__),
        cast(Table, WorldScheduleRule.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, WorldSnapshotModel.__table__),
        cast(Table, WorldBible.__table__),
        cast(Table, SecretRecord.__table__),
        cast(Table, CharacterKnowledgeFact.__table__),
        cast(Table, CharacterEmotionalState.__table__),
        cast(Table, DailyLifeEventCandidate.__table__),
        cast(Table, OffscreenEventQueueItem.__table__),
        cast(Table, StoryHook.__table__),
        cast(Table, PlotThread.__table__),
        cast(Table, RouteAffinity.__table__),
        cast(Table, RouteMilestone.__table__),
        cast(Table, EndingCandidate.__table__),
        cast(Table, PlayerActorProfile.__table__),
        cast(Table, PlayerChoiceRecord.__table__),
        cast(Table, PlayerInterventionRecord.__table__),
        cast(Table, PlayerJournalEntry.__table__),
        cast(Table, InWorldNotification.__table__),
        cast(Table, NarrativeArtifact.__table__),
        cast(Table, NarrativePublication.__table__),
        cast(Table, GMStyleReview.__table__),
        cast(Table, NarrativeContinuityReview.__table__),
        cast(Table, AssetGenerationPolicy.__table__),
        cast(Table, AssetGenerationRun.__table__),
        cast(Table, AssetGenerationProposal.__table__),
        cast(Table, GMAgenda.__table__),
        cast(Table, GMEventProposal.__table__),
        cast(Table, MemoryBackendProfile.__table__),
        cast(Table, AgentMemoryItem.__table__),
        cast(Table, MemoryWriteJob.__table__),
        cast(Table, MemoryWriteLog.__table__),
        cast(Table, MemoryRetrievalLog.__table__),
        cast(Table, AgentProfileSnapshotModel.__table__),
        cast(Table, ProviderProfile.__table__),
        cast(Table, ProviderIntegration.__table__),
        cast(Table, ProviderCapability.__table__),
        cast(Table, ProviderHealthCheck.__table__),
        cast(Table, MediaAsset.__table__),
        cast(Table, MediaJob.__table__),
        cast(Table, AgentRuntimeRun.__table__),
        cast(Table, ModelInvocation.__table__),
        cast(Table, PromptTemplate.__table__),
        cast(Table, PromptSnapshot.__table__),
        cast(Table, AgentRuntimeRunModelInvocation.__table__),
        cast(Table, ModelInvocationTag.__table__),
        cast(Table, ConversationSession.__table__),
        cast(Table, ConversationParticipant.__table__),
        cast(Table, ConversationTurn.__table__),
        cast(Table, VoiceProfile.__table__),
        cast(Table, AgentVoiceProfileBinding.__table__),
        cast(Table, SpeechStyleMapping.__table__),
        cast(Table, CharacterSpriteSet.__table__),
        cast(Table, CharacterSpriteVariant.__table__),
        cast(Table, ConversationTurnPresentation.__table__),
        cast(Table, LongRunEvalRun.__table__),
        cast(Table, RuntimeDiagnosticEvent.__table__),
    ):
        table.create(engine)


def _seed_world_agent_and_fact(
    engine: Engine,
    fact_text: str,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    world_id = uuid.uuid4()
    user_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            World(
                id=world_id,
                owner_user_id=user_id,
                slug=f"world-{world_id.hex[:8]}",
                name="World",
            )
        )
        worldline = ensure_primary_worldline(session, world_id)
        session.add(
            Agent(
                id=agent_id,
                world_id=world_id,
                agent_key=f"agent-{agent_id.hex[:8]}",
                display_name="Alice",
                kind="role_agent",
                character_profile={},
                config={},
            )
        )
        session.flush()
        session.add(
            CharacterKnowledgeFact(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline.id,
                agent_id=agent_id,
                fact_key="fact-1",
                knowledge_kind="fact",
                content=fact_text,
                confidence=90,
                visibility="public",
                is_active=True,
                metadata_json={},
            )
        )
        session.commit()
        return world_id, worldline.id, agent_id


def _seed_conversation(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    agent_id: uuid.UUID,
) -> uuid.UUID:
    with Session(engine) as session:
        service = ConversationService(session)
        created = service.create_session(
            ConversationSessionCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                session_key=f"session-{uuid.uuid4().hex[:8]}",
                title="Opening scene",
                scope_type=ConversationScopeType.WORLD,
                mode=ConversationMode.MANUAL_CHAIN,
                objective="Keep the scene quiet.",
                opening_prompt="Hello.",
                max_turns=4,
                policy=ConversationPolicyConfig(
                    error_policy=ConversationErrorPolicy.FAIL_SESSION,
                    max_consecutive_failed_turns=2,
                    loop_guard_window=3,
                    repeat_output_threshold=2,
                    speaker_policy=ConversationSpeakerPolicyMode.ROUND_ROBIN,
                ),
                writer_config=ConversationWriterConfig(),
                memory_config=ConversationMemoryConfig(),
            )
        )
        service.replace_participants(
            world_id,
            created.id,
            [ConversationParticipantDefinition(agent_id=agent_id, turn_order=0)],
        )
        service.seed_session(world_id, created.id, ConversationSeed(input_text="Operator seed"))
        session.commit()
        return created.id


def _seed_agent_turn(
    engine: Engine,
    conversation_id: uuid.UUID,
    agent_id: uuid.UUID,
    *,
    output_text: str,
) -> uuid.UUID:
    turn_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            ConversationTurn(
                id=turn_id,
                session_id=conversation_id,
                turn_index=99,
                speaker_kind="agent",
                speaker_agent_id=agent_id,
                input_text="Operator prompt",
                output_text=output_text,
                status="succeeded",
            )
        )
        session.commit()
        return turn_id


def _seed_aligned_presentation(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    agent_id: uuid.UUID,
    conversation_id: uuid.UUID,
    turn_id: uuid.UUID,
    *,
    variant_expression: str = "happy",
    include_voice: bool = True,
) -> None:
    sprite_set_id = uuid.uuid4()
    selected_variant_id = uuid.uuid4()
    matching_variant_id = uuid.uuid4()
    voice_profile_id = uuid.uuid4()
    sprite_asset_id = uuid.uuid4()
    voice_asset_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            MediaAsset(
                id=sprite_asset_id,
                world_id=world_id,
                worldline_id=worldline_id,
                asset_kind="image",
                asset_role="character_sprite",
                source_kind="test_fixture",
                status="available",
                visibility="world_admin",
                created_by_actor_ref="test",
                metadata_json={},
            )
        )
        session.add(
            MediaAsset(
                id=voice_asset_id,
                world_id=world_id,
                worldline_id=worldline_id,
                asset_kind="audio",
                asset_role="voice_sample",
                source_kind="test_fixture",
                status="available",
                visibility="world_admin",
                created_by_actor_ref="test",
                metadata_json={},
            )
        )
        session.add(
            CharacterSpriteSet(
                id=sprite_set_id,
                world_id=world_id,
                worldline_id=worldline_id,
                agent_id=agent_id,
                style_key="default",
                display_name="Default",
                default_variant_id=selected_variant_id,
                status="active",
                visibility="world_admin",
                metadata_json={},
            )
        )
        session.add(
            CharacterSpriteVariant(
                id=selected_variant_id,
                world_id=world_id,
                worldline_id=worldline_id,
                sprite_set_id=sprite_set_id,
                asset_id=sprite_asset_id,
                expression_key=variant_expression,
                mood_tags_json=[variant_expression],
                priority=10,
                is_default=True,
                status="active",
                visibility="world_admin",
                metadata_json={},
            )
        )
        if variant_expression != "happy":
            session.add(
                CharacterSpriteVariant(
                    id=matching_variant_id,
                    world_id=world_id,
                    worldline_id=worldline_id,
                    sprite_set_id=sprite_set_id,
                    asset_id=sprite_asset_id,
                    expression_key="happy",
                    mood_tags_json=["happy"],
                    priority=5,
                    is_default=False,
                    status="active",
                    visibility="world_admin",
                    metadata_json={},
                )
            )
        if include_voice:
            session.add(
                VoiceProfile(
                    id=voice_profile_id,
                    world_id=world_id,
                    worldline_id=worldline_id,
                    profile_key="alice",
                    display_name="Alice",
                    status="active",
                    visibility="world_admin",
                    owner_kind="agent",
                    owner_agent_id=agent_id,
                    default_language="en",
                    supported_languages_json=["en"],
                    voice_kind="preset",
                    reference_asset_id=voice_asset_id,
                    consent_status="not_required",
                    usage_policy_json={},
                    metadata_json={},
                )
            )
            session.add(
                AgentVoiceProfileBinding(
                    id=uuid.uuid4(),
                    world_id=world_id,
                    worldline_id=worldline_id,
                    agent_id=agent_id,
                    voice_profile_id=voice_profile_id,
                    binding_role="default",
                    priority=0,
                    is_default=True,
                    style_overrides_json={},
                )
            )
        session.add(
            SpeechStyleMapping(
                id=uuid.uuid4(),
                world_id=world_id,
                mapping_key="tts-happy",
                provider_kind="text_to_speech",
                emotion_key="happy",
                style_json={"style": "bright"},
            )
        )
        session.add(
            ConversationTurnPresentation(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                conversation_id=conversation_id,
                turn_id=turn_id,
                speaker_agent_id=agent_id,
                emotion_key="happy",
                emotion_intensity=1.0,
                sprite_set_id=sprite_set_id,
                sprite_variant_id=selected_variant_id,
                voice_profile_id=voice_profile_id if include_voice else None,
                presentation_json={"safe": True},
                render_state="speech_rendered",
            )
        )
        session.commit()


def _seed_text_provider(engine: Engine, world_id: uuid.UUID) -> uuid.UUID:
    return _seed_provider(engine, world_id, ProviderKind.TEXT_GENERATION)


def _seed_provider(
    engine: Engine,
    world_id: uuid.UUID,
    provider_kind: ProviderKind,
) -> uuid.UUID:
    with Session(engine) as session:
        provider = ProviderRegistryService(session).create_provider(
            ProviderIntegrationCreate(
                world_id=world_id,
                scope_kind=ProviderScopeKind.WORLD,
                provider_kind=provider_kind,
                adapter_kind=ProviderAdapterKind.FAKE,
                provider_key=f"fake-{provider_kind.value}",
                display_name=f"Fake {provider_kind.value}",
            )
        )
        session.commit()
        return provider.id


def _seed_provider_health(
    engine: Engine,
    provider_id: uuid.UUID,
    *,
    status: str,
    metadata: dict[str, object] | None = None,
    error_text: str | None = None,
) -> None:
    with Session(engine) as session:
        session.add(
            ProviderHealthCheck(
                id=uuid.uuid4(),
                provider_integration_id=provider_id,
                status=status,
                latency_ms=50,
                error_text=error_text,
                metadata_json=metadata or {},
            )
        )
        session.commit()


def _seed_worldline(engine: Engine, world_id: uuid.UUID) -> uuid.UUID:
    fork_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            Worldline(
                id=fork_id,
                world_id=world_id,
                worldline_key=f"fork-{fork_id.hex[:8]}",
                name="Fork",
                status="active",
                created_by_actor_ref="test",
                metadata_json={},
            )
        )
        session.commit()
        return fork_id


def _seed_narrative_artifact(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    *,
    content: str,
) -> uuid.UUID:
    artifact_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            NarrativeArtifact(
                id=artifact_id,
                world_id=world_id,
                worldline_id=worldline_id,
                title="Fixture artifact",
                content=content,
                artifact_kind=NarrativeArtifactKind.CHAPTER_DRAFT.value,
                artifact_metadata={"worldline_id": str(worldline_id)},
            )
        )
        session.commit()
        return artifact_id


def _seed_hidden_secret(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    content: str,
) -> uuid.UUID:
    secret_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            SecretRecord(
                id=secret_id,
                world_id=world_id,
                worldline_id=worldline_id,
                secret_key=f"secret-{secret_id.hex[:8]}",
                title="Hidden diary",
                content=content,
                status="hidden",
                visibility="holders",
                holder_agent_ids=[],
                reveal_conditions={},
                consequence_metadata={},
                metadata_json={},
            )
        )
        session.commit()
        return secret_id


def _seed_active_route(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    agent_id: uuid.UUID,
) -> uuid.UUID:
    route_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            RouteAffinity(
                id=route_id,
                world_id=world_id,
                worldline_id=worldline_id,
                agent_id=agent_id,
                route_key=f"route-{route_id.hex[:8]}",
                status="active",
                affinity=10,
                stage=1,
                flags=[],
                metadata_json={},
            )
        )
        session.commit()
        return route_id


def _seed_progression_fixture(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    agent_id: uuid.UUID,
    *,
    route_stage: int = 2,
    milestone_stage: int = 2,
    include_milestone: bool = True,
    include_choice: bool = False,
    event_payload: dict[str, object] | None = None,
) -> uuid.UUID:
    target_agent_id = uuid.uuid4()
    route_id = uuid.uuid4()
    milestone_id = uuid.uuid4()
    ending_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    user_id = uuid.uuid4()
    choice_id = uuid.uuid4() if include_choice else None
    with Session(engine) as session:
        player_email = f"player-{user_id.hex[:8]}@example.test"
        session.add(User(id=user_id, email=player_email, display_name=player_email))
        session.add(
            Agent(
                id=target_agent_id,
                world_id=world_id,
                agent_key=f"target-{target_agent_id.hex[:8]}",
                display_name="Bob",
                kind="role_agent",
                character_profile={},
                config={},
            )
        )
        session.add(
            AgentRelationshipEdge(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                source_agent_id=agent_id,
                target_agent_id=target_agent_id,
                relationship_type="affection",
                affection=85,
                trust=80,
                hostility=75,
                intimacy=30,
                obligation=0,
                rivalry=0,
                debt=0,
                metadata_json={},
            )
        )
        session.add(
            PlayerActorProfile(
                id=actor_id,
                world_id=world_id,
                worldline_id=worldline_id,
                user_id=user_id,
                actor_ref="test-player",
                display_name="Player",
                profile_json={},
                is_active=True,
            )
        )
        if choice_id is not None:
            session.add(
                PlayerChoiceRecord(
                    id=choice_id,
                    world_id=world_id,
                    worldline_id=worldline_id,
                    user_id=user_id,
                    player_actor_id=actor_id,
                    choice_key="route-choice",
                    choice_kind="route",
                    prompt="Choose route",
                    selected_option="Stay",
                    context_json={},
                    consequence_preview={},
                )
            )
        session.add(
            RouteAffinity(
                id=route_id,
                world_id=world_id,
                worldline_id=worldline_id,
                agent_id=agent_id,
                route_key=f"route-{route_id.hex[:8]}",
                status="active",
                affinity=20,
                stage=route_stage,
                flags=[],
                last_choice_id=choice_id,
                metadata_json={},
            )
        )
        if include_milestone:
            session.add(
                RouteMilestone(
                    id=milestone_id,
                    world_id=world_id,
                    worldline_id=worldline_id,
                    route_affinity_id=route_id,
                    agent_id=agent_id,
                    milestone_key="confession",
                    title="Confession",
                    description="Route beat",
                    stage=milestone_stage,
                    status="active",
                    conditions={},
                    evidence_metadata={},
                    metadata_json={},
                )
            )
        session.add(
            EndingCandidate(
                id=ending_id,
                world_id=world_id,
                worldline_id=worldline_id,
                route_affinity_id=route_id,
                agent_id=agent_id,
                ending_key="good-ending",
                title="Good Ending",
                ending_type="normal",
                status="available",
                requirements={
                    "min_route_affinity": 80,
                    "min_route_stage": 5,
                    "min_completed_milestones": 1,
                },
                outcome_summary=None,
                evidence_metadata={},
                metadata_json={},
            )
        )
        session.add(
            GMEventProposal(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                title="High risk route shift",
                reason="Review this route change.",
                event_name="gm.route_shift",
                proposed_payload={},
                importance="route",
                risk_score=80,
                affected_agents=[str(agent_id)],
                affected_organizations=[],
                source_context={},
                status="proposed",
            )
        )
        session.add(
            WorldEventModel(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                sequence=1,
                event_name="route.progression",
                importance="route",
                payload=event_payload or {"relationship_delta": {"affection": 45}},
                wall_time=datetime.now(UTC),
                actor_ref="test",
            )
        )
        session.commit()
        return route_id


def _seed_pacing_policy(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    *,
    max_pending_jobs: int,
    max_pending_cost: float,
) -> uuid.UUID:
    policy_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            AssetGenerationPolicy(
                id=policy_id,
                world_id=world_id,
                worldline_id=worldline_id,
                policy_key=f"pacing-{policy_id.hex[:8]}",
                status="active",
                budget_json={"max_pending_cost": max_pending_cost},
                lookahead_json={},
                provider_preferences_json={},
                rules_json={"max_pending_jobs": max_pending_jobs},
            )
        )
        session.commit()
        return policy_id


def _seed_media_job(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    conversation_id: uuid.UUID,
    turn_id: uuid.UUID,
    *,
    invalidation_key: str = "turn:one",
    priority: int = 10,
    request_json: dict[str, object] | None = None,
) -> uuid.UUID:
    job_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            MediaJob(
                id=job_id,
                world_id=world_id,
                worldline_id=worldline_id,
                conversation_id=conversation_id,
                turn_id=turn_id,
                job_kind="image_generation",
                provider_kind="image_generation",
                status="queued",
                priority=priority,
                cancel_policy="cancel_superseded",
                dedupe_key=invalidation_key,
                invalidation_key=invalidation_key,
                provider_config_json={},
                request_json=request_json or {"safe": True},
                result_json={},
                created_by_actor_ref="test",
            )
        )
        session.commit()
        return job_id


def _seed_asset_generation_run_and_proposal(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    conversation_id: uuid.UUID,
    turn_id: uuid.UUID,
    *,
    estimated_cost: float,
) -> tuple[uuid.UUID, uuid.UUID]:
    run_id = uuid.uuid4()
    proposal_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            AssetGenerationRun(
                id=run_id,
                world_id=world_id,
                worldline_id=worldline_id,
                policy_id=None,
                run_kind="preview",
                status="succeeded",
                summary_json={},
                created_by_actor_ref="test",
            )
        )
        session.add(
            AssetGenerationProposal(
                id=proposal_id,
                world_id=world_id,
                worldline_id=worldline_id,
                run_id=run_id,
                proposal_kind="composite_scene",
                target_ref_kind="conversation_turn",
                target_ref_id=turn_id,
                reason="missing composite scene",
                evidence_json={"conversation_id": str(conversation_id), "turn_id": str(turn_id)},
                priority=0,
                estimated_cost=estimated_cost,
                provider_kind=None,
                provider_id=None,
                request_json={
                    "action": "compose_scene",
                    "conversation_id": str(conversation_id),
                    "turn_id": str(turn_id),
                },
                status="proposed",
            )
        )
        session.commit()
        return run_id, proposal_id


def _seed_long_run_eval_evidence(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    agent_id: uuid.UUID,
) -> None:
    target_agent_id = uuid.uuid4()
    route_id = uuid.uuid4()
    event_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            Agent(
                id=target_agent_id,
                world_id=world_id,
                agent_key=f"target-{target_agent_id.hex[:8]}",
                display_name="Bob",
                kind="role_agent",
                character_profile={},
                config={},
            )
        )
        session.add(
            AgentRelationshipEdge(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                source_agent_id=agent_id,
                target_agent_id=target_agent_id,
                relationship_type="friendship",
                affection=40,
                trust=60,
                hostility=0,
                intimacy=10,
                obligation=0,
                rivalry=0,
                debt=0,
                metadata_json={},
            )
        )
        session.add(
            RouteAffinity(
                id=route_id,
                world_id=world_id,
                worldline_id=worldline_id,
                agent_id=agent_id,
                route_key=f"route-{route_id.hex[:8]}",
                status="active",
                affinity=30,
                stage=1,
                flags=[],
                metadata_json={},
            )
        )
        session.add(
            RouteMilestone(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                route_affinity_id=route_id,
                agent_id=agent_id,
                milestone_key="opening",
                title="Opening",
                description="Opening route beat",
                stage=1,
                status="completed",
                conditions={},
                evidence_metadata={},
                metadata_json={},
            )
        )
        session.add(
            EndingCandidate(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                route_affinity_id=route_id,
                agent_id=agent_id,
                ending_key="quiet-ending",
                title="Quiet Ending",
                ending_type="normal",
                status="available",
                requirements={"min_route_stage": 1},
                outcome_summary=None,
                evidence_metadata={},
                metadata_json={},
            )
        )
        session.add(
            GMEventProposal(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                title="Resolved daily beat",
                reason="Fixture proposal.",
                event_name="gm.daily_beat",
                proposed_payload={},
                importance="daily",
                risk_score=10,
                affected_agents=[str(agent_id)],
                affected_organizations=[],
                source_context={},
                status="resolved",
            )
        )
        session.add(
            WorldEventModel(
                id=event_id,
                world_id=world_id,
                worldline_id=worldline_id,
                sequence=1,
                event_name="gm.daily_beat",
                importance="daily",
                payload={"safe": True},
                wall_time=datetime.now(UTC),
                world_time=datetime(2030, 1, 1, tzinfo=UTC),
                actor_ref="gm:test",
            )
        )
        session.add(
            WorldSnapshotModel(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                covers_event_sequence=1,
                schema_version="test/v1",
                status="valid",
                payload={"safe": True},
                payload_uri=None,
                snapshot_metadata={},
                created_by_event_id=event_id,
            )
        )
        session.commit()
