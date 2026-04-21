from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Protocol

from noveland.adapters import (
    ProviderCompletion,
    ProviderConfigurationError,
    ProviderProfileRecord,
)
from noveland.agents.models import Agent
from noveland.conversations import ConversationService, ConversationSessionStatus
from noveland.conversations.contracts import (
    ConversationParticipantRecord,
    ConversationSessionRecord,
    ConversationSpeakerKind,
    ConversationTurnRecord,
)
from noveland.narrative.contracts import (
    ConversationNarrativeArtifactSet,
    ConversationNarrativeGenerate,
    NarrativeArtifactCreate,
    NarrativeArtifactKind,
    NarrativeArtifactRecord,
    NarrativeGenerationMode,
)
from noveland.narrative.models import NarrativeArtifact
from sqlalchemy import select
from sqlalchemy.orm import Session


class NarrativeProviderService(Protocol):
    def get_profile(self, profile_id: uuid.UUID) -> ProviderProfileRecord | None: ...

    def first_enabled_profile(self) -> ProviderProfileRecord | None: ...

    def invoke_profile(
        self,
        profile: ProviderProfileRecord,
        prompt: str,
    ) -> ProviderCompletion: ...


class NarrativeArtifactService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_artifacts(
        self,
        world_id: uuid.UUID,
        *,
        artifact_kind: NarrativeArtifactKind | None = None,
        source_conversation_id: uuid.UUID | None = None,
        limit: int | None = None,
    ) -> list[NarrativeArtifactRecord]:
        statement = (
            select(NarrativeArtifact)
            .where(NarrativeArtifact.world_id == world_id)
            .order_by(NarrativeArtifact.created_at.desc())
        )
        if artifact_kind is not None:
            statement = statement.where(NarrativeArtifact.artifact_kind == artifact_kind.value)
        if source_conversation_id is not None:
            statement = statement.where(
                NarrativeArtifact.source_conversation_id == source_conversation_id,
            )
        if limit is not None:
            statement = statement.limit(max(1, min(limit, 200)))
        return [_record(model) for model in self._session.scalars(statement).all()]

    def get_artifact(
        self,
        world_id: uuid.UUID,
        artifact_id: uuid.UUID,
    ) -> NarrativeArtifactRecord | None:
        model = self._session.get(NarrativeArtifact, artifact_id)
        if model is None or model.world_id != world_id:
            return None
        return _record(model)

    def get_conversation_artifact(
        self,
        world_id: uuid.UUID,
        conversation_id: uuid.UUID,
        artifact_kind: NarrativeArtifactKind,
    ) -> NarrativeArtifactRecord | None:
        model = self._session.scalars(
            select(NarrativeArtifact)
            .where(
                NarrativeArtifact.world_id == world_id,
                NarrativeArtifact.source_conversation_id == conversation_id,
                NarrativeArtifact.artifact_kind == artifact_kind.value,
            )
            .order_by(NarrativeArtifact.created_at.desc()),
        ).first()
        return None if model is None else _record(model)

    def create_artifact(
        self,
        artifact_create: NarrativeArtifactCreate,
    ) -> NarrativeArtifactRecord:
        model = NarrativeArtifact(
            world_id=artifact_create.world_id,
            agent_id=artifact_create.agent_id,
            source_run_id=artifact_create.source_run_id,
            source_conversation_id=artifact_create.source_conversation_id,
            title=artifact_create.title,
            content=artifact_create.content,
            artifact_kind=artifact_create.artifact_kind.value,
            artifact_metadata=artifact_create.metadata,
        )
        self._session.add(model)
        self._session.flush()
        return _record(model)


class ConversationNarrativeWriterService:
    def __init__(
        self,
        session: Session,
        profile_service: NarrativeProviderService,
    ) -> None:
        self._session = session
        self._profile_service = profile_service
        self._conversation_service = ConversationService(session)
        self._artifact_service = NarrativeArtifactService(session)

    def list_conversation_artifacts(
        self,
        world_id: uuid.UUID,
        conversation_id: uuid.UUID,
    ) -> list[NarrativeArtifactRecord]:
        self._conversation_service.get_session(world_id, conversation_id)
        return self._artifact_service.list_artifacts(
            world_id,
            source_conversation_id=conversation_id,
            limit=50,
        )

    def generate_for_conversation(
        self,
        generate: ConversationNarrativeGenerate,
    ) -> list[NarrativeArtifactRecord]:
        session = self._conversation_service.get_session(
            generate.world_id,
            generate.conversation_id,
        )
        participants = self._conversation_service.list_participants(
            generate.world_id,
            generate.conversation_id,
        )
        turns = self._conversation_service.list_turns(generate.world_id, generate.conversation_id)
        agents_by_id = self._agents_by_id(
            generate.world_id,
            [participant.agent_id for participant in participants]
            + [
                turn.speaker_agent_id
                for turn in turns
                if turn.speaker_agent_id is not None
            ],
        )
        provider = self._resolve_provider(
            generate.provider_profile_id or session.writer_config.provider_profile_id,
        )

        artifacts: list[NarrativeArtifactRecord] = []
        summary_artifact = self._artifact_service.get_conversation_artifact(
            generate.world_id,
            generate.conversation_id,
            NarrativeArtifactKind.CONVERSATION_SUMMARY,
        )
        summary_text = summary_artifact.content if summary_artifact is not None else None

        needs_summary = generate.artifact_set in {
            ConversationNarrativeArtifactSet.SUMMARY_AND_CHAPTER,
            ConversationNarrativeArtifactSet.SUMMARY_ONLY,
        }
        needs_chapter = generate.artifact_set in {
            ConversationNarrativeArtifactSet.SUMMARY_AND_CHAPTER,
            ConversationNarrativeArtifactSet.CHAPTER_ONLY,
        }

        if needs_summary:
            if summary_artifact is None:
                summary_text = self._profile_service.invoke_profile(
                    provider,
                    _summary_prompt(session, participants, turns, agents_by_id),
                ).text.strip()
                summary_artifact = self._artifact_service.create_artifact(
                    NarrativeArtifactCreate(
                        world_id=generate.world_id,
                        source_conversation_id=generate.conversation_id,
                        title=f"{session.title} summary",
                        content=summary_text,
                        artifact_kind=NarrativeArtifactKind.CONVERSATION_SUMMARY,
                        metadata=_metadata(
                            session=session,
                            turns=turns,
                            provider=provider,
                            generation_mode=generate.generation_mode,
                        ),
                    ),
                )
            artifacts.append(summary_artifact)
        elif needs_chapter and summary_text is None:
            summary_text = self._profile_service.invoke_profile(
                provider,
                _summary_prompt(session, participants, turns, agents_by_id),
            ).text.strip()

        if needs_chapter:
            chapter_artifact = self._artifact_service.get_conversation_artifact(
                generate.world_id,
                generate.conversation_id,
                NarrativeArtifactKind.CHAPTER_DRAFT,
            )
            if chapter_artifact is None:
                chapter_artifact = self._artifact_service.create_artifact(
                    NarrativeArtifactCreate(
                        world_id=generate.world_id,
                        source_conversation_id=generate.conversation_id,
                        title=f"{session.title} chapter draft",
                        content=self._profile_service.invoke_profile(
                            provider,
                            _chapter_prompt(
                                session,
                                participants,
                                turns,
                                agents_by_id,
                                summary_text or "No summary available.",
                            ),
                        ).text.strip(),
                        artifact_kind=NarrativeArtifactKind.CHAPTER_DRAFT,
                        metadata=_metadata(
                            session=session,
                            turns=turns,
                            provider=provider,
                            generation_mode=generate.generation_mode,
                        ),
                    ),
                )
            artifacts.append(chapter_artifact)

        return artifacts

    def auto_generate_for_completed_conversation(
        self,
        world_id: uuid.UUID,
        conversation_id: uuid.UUID,
    ) -> list[NarrativeArtifactRecord]:
        session = self._conversation_service.get_session(world_id, conversation_id)
        if session.status != ConversationSessionStatus.COMPLETED:
            return []
        if not session.writer_config.auto_generate_on_complete:
            return []

        artifact_set = _artifact_set_from_writer_config(session)
        if artifact_set is None:
            return []

        return self.generate_for_conversation(
            ConversationNarrativeGenerate(
                world_id=world_id,
                conversation_id=conversation_id,
                artifact_set=artifact_set,
                provider_profile_id=session.writer_config.provider_profile_id,
                generation_mode=NarrativeGenerationMode.AUTO_ON_COMPLETE,
            ),
        )

    def _resolve_provider(
        self,
        provider_profile_id: uuid.UUID | None,
    ) -> ProviderProfileRecord:
        profile: ProviderProfileRecord | None
        if provider_profile_id is not None:
            profile = self._profile_service.get_profile(provider_profile_id)
            if profile is None:
                raise ProviderConfigurationError("Configured writer provider profile was not found")
            if not profile.is_enabled:
                raise ProviderConfigurationError(
                    "Configured writer provider profile is disabled",
                )
            return profile
        profile = self._profile_service.first_enabled_profile()
        if profile is None:
            raise ProviderConfigurationError("No enabled provider profile is available")
        return profile

    def _agents_by_id(
        self,
        world_id: uuid.UUID,
        agent_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, Agent]:
        if not agent_ids:
            return {}
        unique_ids = sorted(set(agent_ids), key=str)
        return {
            agent.id: agent
            for agent in self._session.scalars(
                select(Agent).where(Agent.world_id == world_id, Agent.id.in_(unique_ids)),
            ).all()
        }


def _artifact_set_from_writer_config(
    session: ConversationSessionRecord,
) -> ConversationNarrativeArtifactSet | None:
    if session.writer_config.generate_summary and session.writer_config.generate_chapter:
        return ConversationNarrativeArtifactSet.SUMMARY_AND_CHAPTER
    if session.writer_config.generate_summary:
        return ConversationNarrativeArtifactSet.SUMMARY_ONLY
    if session.writer_config.generate_chapter:
        return ConversationNarrativeArtifactSet.CHAPTER_ONLY
    return None


def _summary_prompt(
    session: ConversationSessionRecord,
    participants: list[ConversationParticipantRecord],
    turns: list[ConversationTurnRecord],
    agents_by_id: dict[uuid.UUID, Agent],
) -> str:
    return "\n".join(
        [
            "Write a concise but complete conversation summary.",
            _conversation_context(session, participants, turns, agents_by_id),
            "Output plain text only.",
        ],
    )


def _chapter_prompt(
    session: ConversationSessionRecord,
    participants: list[ConversationParticipantRecord],
    turns: list[ConversationTurnRecord],
    agents_by_id: dict[uuid.UUID, Agent],
    summary_text: str,
) -> str:
    return "\n".join(
        [
            "Write a chapter draft based on this Noveland conversation.",
            _conversation_context(session, participants, turns, agents_by_id),
            "Conversation summary:",
            summary_text,
            "Output plain text only.",
        ],
    )


def _conversation_context(
    session: ConversationSessionRecord,
    participants: list[ConversationParticipantRecord],
    turns: list[ConversationTurnRecord],
    agents_by_id: dict[uuid.UUID, Agent],
) -> str:
    participant_lines = _participant_lines(participants, agents_by_id)
    transcript_lines = _transcript_lines(turns, agents_by_id)
    terminal_reason = (
        "None"
        if session.terminal_reason is None
        else session.terminal_reason.value
    )
    return "\n".join(
        [
            f"Session title: {session.title}",
            f"Objective: {session.objective or 'No explicit objective.'}",
            (
                f"Scope metadata: scope_type={session.scope_type.value}; "
                f"scene_id={session.scene_id}"
            ),
            f"Terminal status: {session.status.value}",
            f"Terminal reason: {terminal_reason}",
            "Participants:",
            *(participant_lines or ["- none"]),
            "Transcript:",
            *(transcript_lines or ["- no turns recorded"]),
        ],
    )


def _participant_lines(
    participants: list[ConversationParticipantRecord],
    agents_by_id: dict[uuid.UUID, Agent],
) -> list[str]:
    lines: list[str] = []
    for participant in participants:
        agent = agents_by_id.get(participant.agent_id)
        if agent is None:
            continue
        lines.append(
            f"- {agent.display_name} ({agent.agent_key}) order={participant.turn_order}",
        )
    return lines


def _transcript_lines(
    turns: list[ConversationTurnRecord],
    agents_by_id: dict[uuid.UUID, Agent],
) -> list[str]:
    lines: list[str] = []
    for turn in turns:
        speaker = "operator"
        if turn.speaker_kind == ConversationSpeakerKind.AGENT and turn.speaker_agent_id is not None:
            agent = agents_by_id.get(turn.speaker_agent_id)
            speaker = agent.display_name if agent is not None else str(turn.speaker_agent_id)
        body = turn.output_text or turn.error_text or turn.input_text
        lines.append(f"{turn.turn_index}. {speaker} [{turn.status.value}]: {body}")
    return lines


def _metadata(
    *,
    session: ConversationSessionRecord,
    turns: list[ConversationTurnRecord],
    provider: ProviderProfileRecord,
    generation_mode: NarrativeGenerationMode,
) -> dict[str, object]:
    return {
        "generation_mode": generation_mode.value,
        "source_turn_count": len(turns),
        "source_turn_end_index": None if not turns else turns[-1].turn_index,
        "scope_type": session.scope_type.value,
        "provider_profile_id": str(provider.id),
    }


def _record(model: NarrativeArtifact) -> NarrativeArtifactRecord:
    return NarrativeArtifactRecord(
        id=model.id,
        world_id=model.world_id,
        agent_id=model.agent_id,
        source_run_id=model.source_run_id,
        source_conversation_id=model.source_conversation_id,
        title=model.title,
        content=model.content,
        artifact_kind=NarrativeArtifactKind(model.artifact_kind),
        metadata=model.artifact_metadata,
        created_at=_utc(model.created_at),
    )


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
