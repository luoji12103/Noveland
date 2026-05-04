from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Protocol, cast

from noveland.adapters import (
    ProviderCompletion,
    ProviderConfigurationError,
    ProviderProfileRecord,
)
from noveland.agents.models import Agent
from noveland.conversations import ConversationService, ConversationSessionStatus
from noveland.conversations.contracts import (
    ConversationSessionRecord,
    ConversationTurnRecord,
)
from noveland.narrative.contracts import (
    ConversationNarrativeArtifactSet,
    ConversationNarrativeGenerate,
    ConversationNarrativePromptPreview,
    NarrativeArtifactCreate,
    NarrativeArtifactKind,
    NarrativeArtifactRecord,
    NarrativeArtifactWithPublication,
    NarrativeGenerationMode,
    NarrativePublicationRecord,
    NarrativePublicationStatus,
)
from noveland.narrative.models import NarrativeArtifact, NarrativePublication
from noveland.plugins.builtins import NarrativeWriterPlugin, get_builtin_plugin_registry
from noveland.plugins.categories import PluginCategory
from noveland.plugins.errors import (
    PluginConfigValidationError,
    PluginFactoryError,
    PluginNotFoundError,
)
from sqlalchemy import or_, select
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

    def list_artifacts_with_publications(
        self,
        world_id: uuid.UUID,
        *,
        artifact_kind: NarrativeArtifactKind | None = None,
        source_conversation_id: uuid.UUID | None = None,
        search_text: str | None = None,
        source_kind: str | None = None,
        publication_status: str | None = None,
        limit: int | None = None,
        published_only: bool = False,
    ) -> list[NarrativeArtifactWithPublication]:
        statement = (
            select(NarrativeArtifact, NarrativePublication)
            .outerjoin(
                NarrativePublication,
                NarrativePublication.artifact_id == NarrativeArtifact.id,
            )
            .where(NarrativeArtifact.world_id == world_id)
            .order_by(NarrativeArtifact.created_at.desc())
        )
        if artifact_kind is not None:
            statement = statement.where(NarrativeArtifact.artifact_kind == artifact_kind.value)
        if source_conversation_id is not None:
            statement = statement.where(
                NarrativeArtifact.source_conversation_id == source_conversation_id,
            )
        if source_kind == "conversation":
            statement = statement.where(NarrativeArtifact.source_conversation_id.is_not(None))
        elif source_kind == "agent_run":
            statement = statement.where(NarrativeArtifact.source_run_id.is_not(None))
        elif source_kind == "agent":
            statement = statement.where(
                NarrativeArtifact.agent_id.is_not(None),
                NarrativeArtifact.source_run_id.is_(None),
            )
        elif source_kind == "world":
            statement = statement.where(
                NarrativeArtifact.agent_id.is_(None),
                NarrativeArtifact.source_run_id.is_(None),
                NarrativeArtifact.source_conversation_id.is_(None),
            )
        if search_text:
            like_pattern = f"%{search_text.lower()}%"
            statement = statement.where(
                or_(
                    NarrativeArtifact.title.ilike(like_pattern),
                    NarrativeArtifact.content.ilike(like_pattern),
                ),
            )
        if published_only:
            statement = statement.where(
                NarrativePublication.status == NarrativePublicationStatus.PUBLISHED.value,
                NarrativePublication.reader_visible.is_(True),
            )
        elif publication_status == "published":
            statement = statement.where(
                NarrativePublication.status == NarrativePublicationStatus.PUBLISHED.value,
                NarrativePublication.reader_visible.is_(True),
            )
        elif publication_status == "draft":
            statement = statement.where(
                or_(
                    NarrativePublication.id.is_(None),
                    NarrativePublication.status != NarrativePublicationStatus.PUBLISHED.value,
                    NarrativePublication.reader_visible.is_(False),
                ),
            )
        if limit is not None:
            statement = statement.limit(max(1, min(limit, 200)))
        return [
            NarrativeArtifactWithPublication(
                artifact=_record(artifact),
                publication=None if publication is None else _publication_record(publication),
            )
            for artifact, publication in self._session.execute(statement).all()
        ]

    def get_artifact(
        self,
        world_id: uuid.UUID,
        artifact_id: uuid.UUID,
    ) -> NarrativeArtifactRecord | None:
        model = self._session.get(NarrativeArtifact, artifact_id)
        if model is None or model.world_id != world_id:
            return None
        return _record(model)

    def get_artifact_with_publication(
        self,
        world_id: uuid.UUID,
        artifact_id: uuid.UUID,
        *,
        published_only: bool = False,
    ) -> NarrativeArtifactWithPublication | None:
        model = self._session.get(NarrativeArtifact, artifact_id)
        if model is None or model.world_id != world_id:
            return None
        publication = self._publication_for_artifact(world_id, artifact_id)
        if published_only and (
            publication is None
            or publication.status != NarrativePublicationStatus.PUBLISHED.value
            or not publication.reader_visible
        ):
            return None
        return NarrativeArtifactWithPublication(
            artifact=_record(model),
            publication=None if publication is None else _publication_record(publication),
        )

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

    def publish_artifact(
        self,
        world_id: uuid.UUID,
        artifact_id: uuid.UUID,
        *,
        actor_user_id: uuid.UUID | None,
        reader_visible: bool = True,
        metadata: dict[str, object] | None = None,
    ) -> NarrativePublicationRecord:
        artifact = self._session.get(NarrativeArtifact, artifact_id)
        if artifact is None or artifact.world_id != world_id:
            raise NarrativeArtifactNotFoundError

        now = datetime.now(UTC)
        publication = self._publication_for_artifact(world_id, artifact_id)
        if publication is None:
            publication = NarrativePublication(
                world_id=world_id,
                artifact_id=artifact_id,
                source_draft_id=artifact_id,
                status=NarrativePublicationStatus.PUBLISHED.value,
                reader_visible=reader_visible,
                published_metadata=metadata or {},
                published_at=now,
                unpublished_at=None,
                published_by_user_id=actor_user_id,
            )
            self._session.add(publication)
        else:
            publication.status = NarrativePublicationStatus.PUBLISHED.value
            publication.reader_visible = reader_visible
            publication.published_metadata = metadata or publication.published_metadata or {}
            publication.published_at = now
            publication.unpublished_at = None
            publication.published_by_user_id = actor_user_id
        self._session.flush()
        return _publication_record(publication)

    def unpublish_artifact(
        self,
        world_id: uuid.UUID,
        artifact_id: uuid.UUID,
        *,
        metadata: dict[str, object] | None = None,
    ) -> NarrativePublicationRecord:
        artifact = self._session.get(NarrativeArtifact, artifact_id)
        if artifact is None or artifact.world_id != world_id:
            raise NarrativeArtifactNotFoundError
        publication = self._publication_for_artifact(world_id, artifact_id)
        if publication is None:
            raise NarrativePublicationNotFoundError

        publication.status = NarrativePublicationStatus.UNPUBLISHED.value
        publication.reader_visible = False
        publication.unpublished_at = datetime.now(UTC)
        if metadata:
            publication.published_metadata = {
                **(publication.published_metadata or {}),
                **metadata,
            }
        self._session.flush()
        return _publication_record(publication)

    def _publication_for_artifact(
        self,
        world_id: uuid.UUID,
        artifact_id: uuid.UUID,
    ) -> NarrativePublication | None:
        return self._session.scalars(
            select(NarrativePublication).where(
                NarrativePublication.world_id == world_id,
                NarrativePublication.artifact_id == artifact_id,
            ),
        ).one_or_none()


class NarrativeArtifactNotFoundError(Exception):
    pass


class NarrativePublicationNotFoundError(Exception):
    pass


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
        writer_plugin = self._resolve_writer_plugin(
            session.writer_config.writer_plugin_identifier,
            session.writer_config.writer_plugin_config,
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
                    _apply_writer_controls(
                        writer_plugin.build_summary_prompt(
                            session=session,
                            participants=participants,
                            turns=turns,
                            agents_by_id=agents_by_id,
                        ),
                        session=session,
                    ),
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
                _apply_writer_controls(
                    writer_plugin.build_summary_prompt(
                        session=session,
                        participants=participants,
                        turns=turns,
                        agents_by_id=agents_by_id,
                    ),
                    session=session,
                ),
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
                            _apply_writer_controls(
                                writer_plugin.build_chapter_prompt(
                                    session=session,
                                    participants=participants,
                                    turns=turns,
                                    agents_by_id=agents_by_id,
                                    summary_text=summary_text or "No summary available.",
                                ),
                                session=session,
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

    def preview_for_conversation(
        self,
        generate: ConversationNarrativeGenerate,
    ) -> ConversationNarrativePromptPreview:
        bundle = self._conversation_prompt_bundle(generate)
        prompt = bundle["summary_prompt"] if bundle["needs_summary"] else bundle["chapter_prompt"]
        assert isinstance(prompt, str)
        provider = cast(ProviderProfileRecord, bundle["provider"])
        session = cast(ConversationSessionRecord, bundle["session"])
        turns = cast(list[ConversationTurnRecord], bundle["turns"])
        existing_count = 0
        if bundle["summary_artifact"] is not None:
            existing_count += 1
        if bundle["chapter_artifact"] is not None:
            existing_count += 1
        warnings = []
        if not turns:
            warnings.append("conversation has no turns")
        if session.writer_config.source_constraints:
            warnings.append("source constraints are applied")
        return ConversationNarrativePromptPreview(
            world_id=generate.world_id,
            conversation_id=generate.conversation_id,
            artifact_set=generate.artifact_set,
            provider_profile_id=provider.id,
            provider_profile_key=provider.profile_key,
            writer_plugin_identifier=session.writer_config.writer_plugin_identifier,
            prompt_text=prompt,
            source_turn_count=len(turns),
            existing_artifact_count=existing_count,
            warnings=warnings,
        )

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

    def _resolve_writer_plugin(
        self,
        identifier: str,
        raw_config: dict[str, object],
    ) -> NarrativeWriterPlugin:
        registry = get_builtin_plugin_registry()
        definition = registry.get(identifier)
        if definition.manifest.category is not PluginCategory.NARRATIVE_WRITER:
            raise ProviderConfigurationError("Writer binding must use a narrative_writer plugin")
        try:
            return cast(
                NarrativeWriterPlugin,
                registry.create(identifier, raw_config),
            )
        except PluginNotFoundError as exc:
            raise ProviderConfigurationError(str(exc)) from exc
        except PluginConfigValidationError as exc:
            raise ProviderConfigurationError(str(exc)) from exc
        except PluginFactoryError as exc:
            raise ProviderConfigurationError(str(exc)) from exc

    def _conversation_prompt_bundle(
        self,
        generate: ConversationNarrativeGenerate,
    ) -> dict[str, object]:
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
        writer_plugin = self._resolve_writer_plugin(
            session.writer_config.writer_plugin_identifier,
            session.writer_config.writer_plugin_config,
        )
        summary_artifact = self._artifact_service.get_conversation_artifact(
            generate.world_id,
            generate.conversation_id,
            NarrativeArtifactKind.CONVERSATION_SUMMARY,
        )
        chapter_artifact = self._artifact_service.get_conversation_artifact(
            generate.world_id,
            generate.conversation_id,
            NarrativeArtifactKind.CHAPTER_DRAFT,
        )
        needs_summary = generate.artifact_set in {
            ConversationNarrativeArtifactSet.SUMMARY_AND_CHAPTER,
            ConversationNarrativeArtifactSet.SUMMARY_ONLY,
        }
        needs_chapter = generate.artifact_set in {
            ConversationNarrativeArtifactSet.SUMMARY_AND_CHAPTER,
            ConversationNarrativeArtifactSet.CHAPTER_ONLY,
        }
        summary_prompt = _apply_writer_controls(
            writer_plugin.build_summary_prompt(
                session=session,
                participants=participants,
                turns=turns,
                agents_by_id=agents_by_id,
            ),
            session=session,
        )
        chapter_prompt = _apply_writer_controls(
            writer_plugin.build_chapter_prompt(
                session=session,
                participants=participants,
                turns=turns,
                agents_by_id=agents_by_id,
                summary_text=(
                    summary_artifact.content
                    if summary_artifact is not None
                    else "No summary available."
                ),
            ),
            session=session,
        )
        return {
            "session": session,
            "participants": participants,
            "turns": turns,
            "agents_by_id": agents_by_id,
            "provider": provider,
            "summary_artifact": summary_artifact,
            "chapter_artifact": chapter_artifact,
            "needs_summary": needs_summary,
            "needs_chapter": needs_chapter,
            "summary_prompt": summary_prompt,
            "chapter_prompt": chapter_prompt,
        }

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
        "writer_target_length": session.writer_config.target_length,
        "writer_has_style_guide": bool(session.writer_config.style_guide),
        "writer_has_source_constraints": bool(session.writer_config.source_constraints),
    }


def _apply_writer_controls(prompt: str, *, session: ConversationSessionRecord) -> str:
    control_lines = [
        "Writer controls:",
        f"- Target length: {session.writer_config.target_length}",
    ]
    if session.writer_config.style_guide:
        control_lines.append(f"- Style guide: {session.writer_config.style_guide}")
    if session.writer_config.source_constraints:
        control_lines.append(f"- Source constraints: {session.writer_config.source_constraints}")
    return "\n".join([*control_lines, "", prompt])


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


def _publication_record(model: NarrativePublication) -> NarrativePublicationRecord:
    return NarrativePublicationRecord(
        id=model.id,
        world_id=model.world_id,
        artifact_id=model.artifact_id,
        source_draft_id=model.source_draft_id,
        status=NarrativePublicationStatus(model.status),
        reader_visible=model.reader_visible,
        metadata=model.published_metadata,
        published_at=None if model.published_at is None else _utc(model.published_at),
        unpublished_at=None if model.unpublished_at is None else _utc(model.unpublished_at),
        published_by_user_id=model.published_by_user_id,
        created_at=_utc(model.created_at),
        updated_at=_utc(model.updated_at),
    )


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
