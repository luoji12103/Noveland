from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

from noveland.agents.models import Agent
from noveland.conversations.contracts import (
    ConversationAdvanceResult,
    ConversationErrorPolicy,
    ConversationMemoryConfig,
    ConversationMode,
    ConversationParticipantDefinition,
    ConversationParticipantRecord,
    ConversationPolicyConfig,
    ConversationScopeType,
    ConversationSeed,
    ConversationSessionCreate,
    ConversationSessionRecord,
    ConversationSessionStatus,
    ConversationSessionUpdate,
    ConversationSpeakerCandidate,
    ConversationSpeakerKind,
    ConversationSpeakerPolicyMode,
    ConversationSpeakerPreview,
    ConversationTerminalReason,
    ConversationTurnRecord,
    ConversationTurnStatus,
    ConversationWriterConfig,
    PreparedConversationTurn,
)
from noveland.conversations.errors import (
    ConversationStateError,
    ConversationValidationError,
)
from noveland.conversations.models import (
    ConversationParticipant,
    ConversationSession,
    ConversationTurn,
)
from noveland.events import WorldEventAppend, WorldEventStore
from noveland.observability import (
    DiagnosticComponent,
    DiagnosticSeverity,
    RuntimeDiagnosticCreate,
    RuntimeDiagnosticRecord,
    RuntimeDiagnosticsService,
)
from noveland.worlds.models import Worldline
from noveland.worlds.worldlines import ensure_primary_worldline
from sqlalchemy import func, select
from sqlalchemy.orm import Session

CONVERSATION_SESSION_STARTED_EVENT_NAME = "conversation.session_started"
CONVERSATION_TURN_COMPLETED_EVENT_NAME = "conversation.turn_completed"
CONVERSATION_TURN_SKIPPED_EVENT_NAME = "conversation.turn_skipped"
CONVERSATION_TURN_FAILED_EVENT_NAME = "conversation.turn_failed"
CONVERSATION_SESSION_STOPPED_EVENT_NAME = "conversation.session_stopped"
CONVERSATION_SESSION_FAILED_EVENT_NAME = "conversation.session_failed"
CONVERSATION_SESSION_COMPLETED_EVENT_NAME = "conversation.session_completed"
TRANSCRIPT_WINDOW = 8
SYSTEM_ACTOR_REF = "system:conversation"
_WHITESPACE_RE = re.compile(r"\s+")


class ConversationService:
    def __init__(self, session: Session, actor_ref: str = SYSTEM_ACTOR_REF) -> None:
        self._session = session
        self._diagnostics = RuntimeDiagnosticsService(session)
        self._actor_ref = actor_ref

    def list_sessions(self, world_id: uuid.UUID) -> list[ConversationSessionRecord]:
        return [
            _session_record(model)
            for model in self._session.scalars(
                select(ConversationSession)
                .where(ConversationSession.world_id == world_id)
                .order_by(ConversationSession.updated_at.desc(), ConversationSession.session_key),
            ).all()
        ]

    def list_running_auto_sessions(self, limit: int) -> list[ConversationSessionRecord]:
        safe_limit = max(1, min(limit, 100))
        return [
            _session_record(model)
            for model in self._session.scalars(
                select(ConversationSession)
                .where(
                    ConversationSession.mode == ConversationMode.AUTO_DIALOGUE.value
                )
                .where(ConversationSession.status == ConversationSessionStatus.RUNNING.value)
                .order_by(
                    ConversationSession.updated_at.asc(),
                    ConversationSession.created_at.asc(),
                )
                .limit(safe_limit),
            ).all()
        ]

    def get_session(
        self,
        world_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> ConversationSessionRecord:
        return _session_record(self._session_model(world_id, session_id))

    def create_session(self, conversation: ConversationSessionCreate) -> ConversationSessionRecord:
        if self._session_key_exists(conversation.world_id, conversation.session_key):
            raise ConversationValidationError("Conversation session key already exists")
        worldline_id = self._worldline_id(conversation.world_id, conversation.worldline_id)
        model = ConversationSession(
            id=uuid.uuid4(),
            world_id=conversation.world_id,
            worldline_id=worldline_id,
            scene_id=conversation.scene_id,
            session_key=conversation.session_key,
            title=conversation.title,
            scope_type=conversation.scope_type.value,
            mode=conversation.mode.value,
            status=ConversationSessionStatus.DRAFT.value,
            objective=conversation.objective,
            opening_prompt=conversation.opening_prompt,
            max_turns=conversation.max_turns,
            next_turn_index=0,
            policy_config=conversation.policy.model_dump(mode="json"),
            writer_config=conversation.writer_config.model_dump(mode="json"),
            memory_config=conversation.memory_config.model_dump(mode="json"),
            terminal_reason=None,
        )
        self._session.add(model)
        self._session.flush()
        return _session_record(model)

    def update_session(
        self,
        world_id: uuid.UUID,
        session_id: uuid.UUID,
        update: ConversationSessionUpdate,
    ) -> ConversationSessionRecord:
        model = self._session_model(world_id, session_id)
        if model.status in {
            ConversationSessionStatus.COMPLETED.value,
            ConversationSessionStatus.STOPPED.value,
            ConversationSessionStatus.FAILED.value,
        }:
            raise ConversationStateError("Conversation session is no longer editable")
        if "title" in update.model_fields_set and update.title is not None:
            model.title = update.title
        if "objective" in update.model_fields_set and update.objective is not None:
            model.objective = update.objective
        if "opening_prompt" in update.model_fields_set and update.opening_prompt is not None:
            model.opening_prompt = update.opening_prompt
        if "max_turns" in update.model_fields_set and update.max_turns is not None:
            if self._agent_turn_count(model.id) > update.max_turns:
                raise ConversationStateError("max_turns cannot be lower than existing agent turns")
            model.max_turns = update.max_turns
        if "policy" in update.model_fields_set and update.policy is not None:
            model.policy_config = update.policy.model_dump(mode="json")
        if "writer_config" in update.model_fields_set and update.writer_config is not None:
            model.writer_config = update.writer_config.model_dump(mode="json")
        if "memory_config" in update.model_fields_set and update.memory_config is not None:
            model.memory_config = update.memory_config.model_dump(mode="json")
        self._session.flush()
        return _session_record(model)

    def list_participants(
        self,
        world_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> list[ConversationParticipantRecord]:
        self._session_model(world_id, session_id)
        return self._participant_records(session_id)

    def replace_participants(
        self,
        world_id: uuid.UUID,
        session_id: uuid.UUID,
        participants: list[ConversationParticipantDefinition],
    ) -> list[ConversationParticipantRecord]:
        session_model = self._session_model(world_id, session_id)
        if session_model.status in {
            ConversationSessionStatus.COMPLETED.value,
            ConversationSessionStatus.STOPPED.value,
            ConversationSessionStatus.FAILED.value,
        }:
            raise ConversationStateError(
                "Completed, stopped, or failed conversation sessions cannot change participants",
            )

        agent_ids = [definition.agent_id for definition in participants]
        if len(set(agent_ids)) != len(agent_ids):
            raise ConversationValidationError("Conversation participants must be unique by agent")
        turn_orders = [definition.turn_order for definition in participants]
        if len(set(turn_orders)) != len(turn_orders):
            raise ConversationValidationError(
                "Conversation participants must be unique by turn order",
            )

        agents_by_id = self._agents_for_world(world_id, agent_ids)
        if len(agents_by_id) != len(agent_ids):
            raise ConversationValidationError("Conversation participants must belong to the world")

        if session_model.scope_type == ConversationScopeType.SCENE.value:
            for agent in agents_by_id.values():
                if agent.home_scene_id != session_model.scene_id:
                    raise ConversationValidationError(
                        "Scene-scoped conversation participants must belong to the session scene",
                    )

        existing_models = list(
            self._session.scalars(
                select(ConversationParticipant).where(
                    ConversationParticipant.session_id == session_id,
                ),
            ).all()
        )
        existing_by_agent = {model.agent_id: model for model in existing_models}
        seen_agent_ids: set[uuid.UUID] = set()

        for definition in participants:
            seen_agent_ids.add(definition.agent_id)
            model = existing_by_agent.get(definition.agent_id)
            if model is None:
                model = ConversationParticipant(
                    id=uuid.uuid4(),
                    session_id=session_id,
                    agent_id=definition.agent_id,
                    turn_order=definition.turn_order,
                    is_enabled=definition.is_enabled,
                )
                self._session.add(model)
            else:
                model.turn_order = definition.turn_order
                model.is_enabled = definition.is_enabled

        for model in existing_models:
            if model.agent_id not in seen_agent_ids:
                self._session.delete(model)

        self._session.flush()
        return self._participant_records(session_id)

    def list_turns(
        self,
        world_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> list[ConversationTurnRecord]:
        self._session_model(world_id, session_id)
        return self._turn_records(session_id)

    def list_diagnostics(
        self,
        world_id: uuid.UUID,
        session_id: uuid.UUID,
        *,
        limit: int = 20,
    ) -> list[RuntimeDiagnosticRecord]:
        self._session_model(world_id, session_id)
        records = self._diagnostics.list_for_world(
            world_id,
            component=DiagnosticComponent.CONVERSATION,
            limit=max(limit * 5, limit),
        )
        matches = [
            record
            for record in records
            if record.details.get("conversation_id") == str(session_id)
        ]
        return matches[: max(1, min(limit, 100))]

    def preview_next_speaker(
        self,
        world_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> ConversationSpeakerPreview:
        session_model = self._session_model(world_id, session_id)
        policy = _policy_config(session_model.policy_config)
        participants = self._available_participants(session_model)
        return self._speaker_preview(session_model, participants, policy)

    def seed_session(
        self,
        world_id: uuid.UUID,
        session_id: uuid.UUID,
        seed: ConversationSeed,
    ) -> ConversationTurnRecord:
        session_model = self._session_model(world_id, session_id)
        self._ensure_not_finished(session_model)
        if self._turn_count(session_id) > 0:
            raise ConversationStateError("Conversation session has already been seeded")
        turn = ConversationTurn(
            id=uuid.uuid4(),
            session_id=session_id,
            turn_index=0,
            speaker_kind=ConversationSpeakerKind.OPERATOR.value,
            speaker_agent_id=None,
            input_text=seed.input_text.strip(),
            output_text=seed.input_text.strip(),
            status=ConversationTurnStatus.SUCCEEDED.value,
            run_id=None,
            error_text=None,
        )
        self._session.add(turn)
        self._session.flush()
        return _turn_record(turn)

    def start_session(
        self,
        world_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> ConversationSessionRecord:
        model = self._session_model(world_id, session_id)
        if model.mode != ConversationMode.AUTO_DIALOGUE.value:
            raise ConversationStateError("Only auto dialogue sessions can be started")
        if model.status not in {
            ConversationSessionStatus.DRAFT.value,
            ConversationSessionStatus.PAUSED.value,
        }:
            raise ConversationStateError("Conversation session cannot be started from this state")
        if model.status == ConversationSessionStatus.DRAFT.value:
            self._append_event(
                world_id=model.world_id,
                worldline_id=model.worldline_id,
                event_name=CONVERSATION_SESSION_STARTED_EVENT_NAME,
                payload={
                    "conversation_id": str(model.id),
                    "mode": model.mode,
                    "scope_type": model.scope_type,
                },
            )
        model.status = ConversationSessionStatus.RUNNING.value
        model.terminal_reason = None
        self._session.flush()
        return _session_record(model)

    def pause_session(
        self,
        world_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> ConversationSessionRecord:
        model = self._session_model(world_id, session_id)
        if model.mode != ConversationMode.AUTO_DIALOGUE.value:
            raise ConversationStateError("Only auto dialogue sessions can be paused")
        if model.status != ConversationSessionStatus.RUNNING.value:
            raise ConversationStateError("Conversation session is not running")
        model.status = ConversationSessionStatus.PAUSED.value
        self._session.flush()
        return _session_record(model)

    def resume_session(
        self,
        world_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> ConversationSessionRecord:
        model = self._session_model(world_id, session_id)
        if model.mode != ConversationMode.AUTO_DIALOGUE.value:
            raise ConversationStateError("Only auto dialogue sessions can be resumed")
        if model.status != ConversationSessionStatus.PAUSED.value:
            raise ConversationStateError("Conversation session is not paused")
        model.status = ConversationSessionStatus.RUNNING.value
        self._session.flush()
        return _session_record(model)

    def stop_session(
        self,
        world_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> ConversationSessionRecord:
        model = self._session_model(world_id, session_id)
        if model.status in {
            ConversationSessionStatus.COMPLETED.value,
            ConversationSessionStatus.STOPPED.value,
            ConversationSessionStatus.FAILED.value,
        }:
            raise ConversationStateError("Conversation session is no longer active")
        self._mark_session_stopped(
            model,
            terminal_reason=ConversationTerminalReason.OPERATOR_STOPPED,
            event_name=CONVERSATION_SESSION_STOPPED_EVENT_NAME,
            message="Conversation session stopped by operator.",
            details={"conversation_id": str(model.id), "stop_source": "operator"},
        )
        self._session.flush()
        return _session_record(model)

    def prepare_next_turn(
        self,
        world_id: uuid.UUID,
        session_id: uuid.UUID,
        *,
        allow_running_auto: bool = False,
    ) -> PreparedConversationTurn:
        session_model = self._session_model(world_id, session_id)
        self._ensure_not_finished(session_model)
        if session_model.mode == ConversationMode.MANUAL_CHAIN.value:
            if session_model.status != ConversationSessionStatus.DRAFT.value:
                raise ConversationStateError("Manual chain session is not advanceable")
        else:
            if session_model.status == ConversationSessionStatus.PAUSED.value:
                pass
            elif (
                allow_running_auto
                and session_model.status == ConversationSessionStatus.RUNNING.value
            ):
                pass
            else:
                raise ConversationStateError("Auto dialogue session must be paused or running")

        policy = _policy_config(session_model.policy_config)
        participants = self._available_participants(session_model)
        if not participants:
            self._mark_session_failed(
                session_model,
                terminal_reason=ConversationTerminalReason.NO_ENABLED_PARTICIPANTS,
                turn_index=None,
                speaker_agent_id=None,
                error_text="Conversation session has no enabled participants",
            )
            self._session.flush()
            raise ConversationStateError("Conversation session has no enabled participants")

        agent_turn_count = self._agent_turn_count(session_model.id)
        max_turn_budget = policy.max_turn_budget or session_model.max_turns
        if agent_turn_count >= max_turn_budget:
            self._mark_session_completed(session_model)
            self._session.flush()
            raise ConversationStateError("Conversation session has reached max turns")

        if len(participants) < policy.min_enabled_participants:
            self._mark_session_failed(
                session_model,
                terminal_reason=ConversationTerminalReason.NO_ENABLED_PARTICIPANTS,
                turn_index=None,
                speaker_agent_id=None,
                error_text="Conversation session does not meet minimum enabled participants",
            )
            self._session.flush()
            raise ConversationStateError(
                "Conversation session does not meet minimum enabled participants",
            )

        preview = self._speaker_preview(session_model, participants, policy)
        if preview.selected_agent_id is None:
            raise ConversationStateError("Conversation session has no selectable speaker")
        participant_by_agent_id = {
            participant.agent_id: participant for participant in participants
        }
        participant = participant_by_agent_id[preview.selected_agent_id]
        participant_index = participants.index(participant)
        turn_index = self._next_turn_index(session_model.id)
        emit_started_event = (
            session_model.mode == ConversationMode.MANUAL_CHAIN.value
            and agent_turn_count == 0
        )
        if emit_started_event:
            self._append_event(
                world_id=session_model.world_id,
                worldline_id=session_model.worldline_id,
                event_name=CONVERSATION_SESSION_STARTED_EVENT_NAME,
                payload={
                    "conversation_id": str(session_model.id),
                    "mode": session_model.mode,
                    "scope_type": session_model.scope_type,
                },
            )
        prompt_text = self._build_prompt(session_model, participant.agent_id)
        self._session.flush()
        return PreparedConversationTurn(
            session=_session_record(session_model),
            speaker_agent_id=participant.agent_id,
            turn_index=turn_index,
            participant_index=participant_index,
            available_participant_count=len(participants),
            prompt_text=prompt_text,
            emit_started_event=emit_started_event,
        )

    def finalize_turn(
        self,
        prepared: PreparedConversationTurn,
        *,
        response_text: str | None,
        run_id: uuid.UUID | None,
        diagnostics: dict[str, object],
        succeeded: bool,
        error_text: str | None = None,
    ) -> ConversationAdvanceResult:
        session_model = self._session_model(prepared.session.world_id, prepared.session.id)
        policy = _policy_config(session_model.policy_config)
        prior_agent_turn_count = self._agent_turn_count(session_model.id)

        if succeeded:
            turn = ConversationTurn(
                id=uuid.uuid4(),
                session_id=prepared.session.id,
                turn_index=prepared.turn_index,
                speaker_kind=ConversationSpeakerKind.AGENT.value,
                speaker_agent_id=prepared.speaker_agent_id,
                input_text=prepared.prompt_text,
                output_text=response_text,
                status=ConversationTurnStatus.SUCCEEDED.value,
                run_id=run_id,
                error_text=None,
            )
            self._session.add(turn)
            session_model.next_turn_index += 1
            self._append_event(
                world_id=session_model.world_id,
                worldline_id=session_model.worldline_id,
                event_name=CONVERSATION_TURN_COMPLETED_EVENT_NAME,
                payload={
                    "conversation_id": str(session_model.id),
                    "turn_index": prepared.turn_index,
                    "speaker_agent_id": str(prepared.speaker_agent_id),
                    "run_id": None if run_id is None else str(run_id),
                },
            )

            completed_turn_count = prior_agent_turn_count + 1
            if completed_turn_count >= session_model.max_turns:
                self._mark_session_completed(session_model)
            elif self._loop_guard_triggered(session_model.id, policy=policy):
                self._mark_session_stopped(
                    session_model,
                    terminal_reason=ConversationTerminalReason.LOOP_GUARD_REPEATED_OUTPUT,
                    event_name=CONVERSATION_SESSION_STOPPED_EVENT_NAME,
                    message="Conversation session stopped by loop guard.",
                    details={
                        "conversation_id": str(session_model.id),
                        "turn_index": prepared.turn_index,
                        "speaker_agent_id": str(prepared.speaker_agent_id),
                        "reason": ConversationTerminalReason.LOOP_GUARD_REPEATED_OUTPUT.value,
                    },
                )
            self._session.flush()
            return ConversationAdvanceResult(
                session=_session_record(session_model),
                turn=_turn_record(turn),
            )

        should_skip = policy.error_policy in {
            ConversationErrorPolicy.SKIP_TURN,
            ConversationErrorPolicy.RETRY_ONCE_THEN_SKIP,
        }
        turn_status = (
            ConversationTurnStatus.SKIPPED if should_skip else ConversationTurnStatus.FAILED
        )
        turn = ConversationTurn(
            id=uuid.uuid4(),
            session_id=prepared.session.id,
            turn_index=prepared.turn_index,
            speaker_kind=ConversationSpeakerKind.AGENT.value,
            speaker_agent_id=prepared.speaker_agent_id,
            input_text=prepared.prompt_text,
            output_text=response_text,
            status=turn_status.value,
            run_id=run_id,
            error_text=error_text,
        )
        self._session.add(turn)

        if should_skip:
            session_model.next_turn_index += 1
            self._append_event(
                world_id=session_model.world_id,
                worldline_id=session_model.worldline_id,
                event_name=CONVERSATION_TURN_SKIPPED_EVENT_NAME,
                payload={
                    "conversation_id": str(session_model.id),
                    "turn_index": prepared.turn_index,
                    "speaker_agent_id": str(prepared.speaker_agent_id),
                    "run_id": None if run_id is None else str(run_id),
                    "error": error_text or diagnostics.get("error") or "Unknown conversation error",
                },
            )
            self._record_conversation_diagnostic(
                session_model,
                severity=DiagnosticSeverity.WARNING,
                event_type="conversation.turn_skipped",
                message="Conversation turn skipped after speaker failure.",
                details={
                    "conversation_id": str(session_model.id),
                    "turn_index": prepared.turn_index,
                    "speaker_agent_id": str(prepared.speaker_agent_id),
                    "run_id": None if run_id is None else str(run_id),
                    "error": error_text or diagnostics.get("error") or "Unknown conversation error",
                    "error_policy": policy.error_policy.value,
                },
                agent_id=prepared.speaker_agent_id,
                run_id=run_id,
            )
            if (
                self._consecutive_failed_turns(session_model.id)
                >= policy.max_consecutive_failed_turns
            ):
                self._mark_session_failed(
                    session_model,
                    terminal_reason=ConversationTerminalReason.CONSECUTIVE_FAILURES_EXCEEDED,
                    turn_index=prepared.turn_index,
                    speaker_agent_id=prepared.speaker_agent_id,
                    error_text=error_text or "Conversation session exceeded failure threshold",
                    run_id=run_id,
                )
        else:
            self._append_event(
                world_id=session_model.world_id,
                worldline_id=session_model.worldline_id,
                event_name=CONVERSATION_TURN_FAILED_EVENT_NAME,
                payload={
                    "conversation_id": str(session_model.id),
                    "turn_index": prepared.turn_index,
                    "speaker_agent_id": str(prepared.speaker_agent_id),
                    "run_id": None if run_id is None else str(run_id),
                    "error": error_text or diagnostics.get("error") or "Unknown conversation error",
                },
            )
            self._mark_session_failed(
                session_model,
                terminal_reason=ConversationTerminalReason.SPEAKER_ERROR,
                turn_index=prepared.turn_index,
                speaker_agent_id=prepared.speaker_agent_id,
                error_text=error_text or "Conversation turn failed",
                run_id=run_id,
            )

        self._session.flush()
        return ConversationAdvanceResult(
            session=_session_record(session_model),
            turn=_turn_record(turn),
        )

    def _build_prompt(self, session_model: ConversationSession, speaker_agent_id: uuid.UUID) -> str:
        turns = self._turn_records(session_model.id)
        participants = self._participant_records(session_model.id)
        participant_lines = []
        agents_by_id = self._agents_for_world(
            session_model.world_id,
            [participant.agent_id for participant in participants],
        )
        for participant in participants:
            agent = agents_by_id.get(participant.agent_id)
            if agent is None:
                continue
            participant_lines.append(
                f"- {agent.display_name} ({agent.agent_key}) order={participant.turn_order}"
            )

        transcript_lines = []
        memory_config = _memory_config(session_model.memory_config)
        if memory_config.include_recent_turns:
            transcript_window = min(memory_config.query_window, TRANSCRIPT_WINDOW)
            for turn in turns[-transcript_window:]:
                speaker = "operator"
                if turn.speaker_agent_id is not None:
                    agent = agents_by_id.get(turn.speaker_agent_id)
                    speaker = (
                        agent.display_name
                        if agent is not None
                        else f"agent:{turn.speaker_agent_id}"
                    )
                content = turn.output_text or turn.error_text or turn.input_text
                transcript_lines.append(f"{speaker}: {content}")

        speaker_agent = agents_by_id.get(speaker_agent_id)
        speaker_name = "Unknown agent" if speaker_agent is None else speaker_agent.display_name
        previous_output = ""
        if turns:
            previous_turn = turns[-1]
            previous_output = (
                previous_turn.output_text or previous_turn.error_text or previous_turn.input_text
            )

        scope_metadata = (
            f"scope=scene scene_id={session_model.scene_id}"
            if session_model.scope_type == ConversationScopeType.SCENE.value
            else "scope=world"
        )

        lines = [
            f"Conversation session: {session_model.title} ({session_model.session_key}).",
            f"Objective: {session_model.objective or 'No explicit objective.'}",
            f"Opening prompt: {session_model.opening_prompt or 'No opening prompt.'}",
            f"Scope metadata: {scope_metadata}",
            f"Turn speaker: {speaker_name}.",
            "Participants:",
            *(participant_lines or ["- none"]),
            "Recent transcript:",
            *(transcript_lines or ["- none"]),
            f"Previous turn output: {previous_output or 'No previous turn output.'}",
            (
                "Continue the conversation. Respond as the current speaker and move the "
                "dialogue forward."
            ),
        ]
        return "\n".join(lines)

    def _speaker_preview(
        self,
        session_model: ConversationSession,
        participants: list[ConversationParticipant],
        policy: ConversationPolicyConfig,
    ) -> ConversationSpeakerPreview:
        turns = self._turn_records(session_model.id)
        agents_by_id = self._agents_for_world(
            session_model.world_id,
            [participant.agent_id for participant in participants],
        )
        last_spoke_by_agent: dict[uuid.UUID, int] = {}
        for turn in turns:
            if turn.speaker_agent_id is not None:
                last_spoke_by_agent[turn.speaker_agent_id] = turn.turn_index

        recent_speaker_ids = [
            turn.speaker_agent_id
            for turn in reversed(turns)
            if turn.speaker_agent_id is not None
        ][: policy.participant_repeat_cooldown]
        cooldown_agent_ids = set(recent_speaker_ids)

        candidates: list[ConversationSpeakerCandidate] = []
        for index, participant in enumerate(participants):
            agent = agents_by_id.get(participant.agent_id)
            score = 0.0
            reasons: list[str] = []
            if (
                participant.agent_id in cooldown_agent_ids
                and len(participants) > len(cooldown_agent_ids)
            ):
                score -= 100.0
                reasons.append("inside repeat cooldown")

            if policy.speaker_policy == ConversationSpeakerPolicyMode.ROUND_ROBIN:
                target_index = session_model.next_turn_index % len(participants)
                score += 100.0 if index == target_index else 0.0
                reasons.append("round-robin turn order")
            elif policy.speaker_policy == ConversationSpeakerPolicyMode.LEAST_RECENT:
                last_spoke = last_spoke_by_agent.get(participant.agent_id)
                score += 10_000.0 if last_spoke is None else float(-last_spoke)
                reasons.append("least recent speaker")
            elif policy.speaker_policy == ConversationSpeakerPolicyMode.PRIORITY_ORDER:
                score += float(10_000 - participant.turn_order)
                reasons.append("priority turn order")
            elif policy.speaker_policy == ConversationSpeakerPolicyMode.MANUAL_NEXT:
                if participant.agent_id == policy.manual_next_agent_id:
                    score += 10_000.0
                    reasons.append("manual next speaker")
                else:
                    reasons.append("not selected by manual next policy")

            candidates.append(
                ConversationSpeakerCandidate(
                    agent_id=participant.agent_id,
                    display_name=(
                        agent.display_name if agent is not None else str(participant.agent_id)
                    ),
                    turn_order=participant.turn_order,
                    is_enabled=participant.is_enabled,
                    score=score,
                    reasons=reasons,
                    last_spoke_turn_index=last_spoke_by_agent.get(participant.agent_id),
                ),
            )

        sorted_candidates = sorted(
            candidates,
            key=lambda candidate: (-candidate.score, candidate.turn_order, candidate.display_name),
        )
        selected = sorted_candidates[0] if sorted_candidates else None
        if (
            policy.speaker_policy == ConversationSpeakerPolicyMode.MANUAL_NEXT
            and policy.manual_next_agent_id is not None
            and selected is not None
            and selected.agent_id != policy.manual_next_agent_id
        ):
            selected = None
        selected_reason = (
            "no selectable speaker"
            if selected is None
            else ", ".join(selected.reasons) or policy.speaker_policy.value
        )
        return ConversationSpeakerPreview(
            session_id=session_model.id,
            policy_mode=policy.speaker_policy,
            selected_agent_id=None if selected is None else selected.agent_id,
            selected_reason=selected_reason,
            candidates=sorted_candidates,
        )

    def _participant_records(
        self,
        session_id: uuid.UUID,
    ) -> list[ConversationParticipantRecord]:
        return [
            _participant_record(model)
            for model in self._session.scalars(
                select(ConversationParticipant)
                .where(ConversationParticipant.session_id == session_id)
                .order_by(
                    ConversationParticipant.turn_order.asc(),
                    ConversationParticipant.created_at.asc(),
                ),
            ).all()
        ]

    def _turn_records(self, session_id: uuid.UUID) -> list[ConversationTurnRecord]:
        return [
            _turn_record(model)
            for model in self._session.scalars(
                select(ConversationTurn)
                .where(ConversationTurn.session_id == session_id)
                .order_by(ConversationTurn.turn_index.asc(), ConversationTurn.created_at.asc()),
            ).all()
        ]

    def _available_participants(
        self,
        session_model: ConversationSession,
    ) -> list[ConversationParticipant]:
        return list(
            self._session.scalars(
                select(ConversationParticipant)
                .join(Agent, Agent.id == ConversationParticipant.agent_id)
                .where(
                    ConversationParticipant.session_id == session_model.id,
                    ConversationParticipant.is_enabled.is_(True),
                    Agent.is_enabled.is_(True),
                )
                .order_by(
                    ConversationParticipant.turn_order.asc(),
                    ConversationParticipant.created_at.asc(),
                ),
            ).all()
        )

    def _session_model(self, world_id: uuid.UUID, session_id: uuid.UUID) -> ConversationSession:
        model = self._session.get(ConversationSession, session_id)
        if model is None or model.world_id != world_id:
            raise LookupError("Conversation session not found")
        return model

    def _session_key_exists(self, world_id: uuid.UUID, session_key: str) -> bool:
        return (
            self._session.scalars(
                select(ConversationSession.id).where(
                    ConversationSession.world_id == world_id,
                    ConversationSession.session_key == session_key,
                ),
            ).first()
            is not None
        )

    def _turn_count(self, session_id: uuid.UUID) -> int:
        count = self._session.scalar(
            select(func.count()).select_from(ConversationTurn).where(
                ConversationTurn.session_id == session_id,
            ),
        )
        return int(count or 0)

    def _agent_turn_count(self, session_id: uuid.UUID) -> int:
        count = self._session.scalar(
            select(func.count()).select_from(ConversationTurn).where(
                ConversationTurn.session_id == session_id,
                ConversationTurn.speaker_kind == ConversationSpeakerKind.AGENT.value,
            ),
        )
        return int(count or 0)

    def _next_turn_index(self, session_id: uuid.UUID) -> int:
        latest = self._session.scalar(
            select(func.max(ConversationTurn.turn_index)).where(
                ConversationTurn.session_id == session_id,
            ),
        )
        return 0 if latest is None else int(latest) + 1

    def _consecutive_failed_turns(self, session_id: uuid.UUID) -> int:
        count = 0
        for turn in reversed(self._turn_records(session_id)):
            if turn.speaker_kind != ConversationSpeakerKind.AGENT:
                continue
            if turn.status == ConversationTurnStatus.SUCCEEDED:
                break
            count += 1
        return count

    def _loop_guard_triggered(
        self,
        session_id: uuid.UUID,
        *,
        policy: ConversationPolicyConfig,
    ) -> bool:
        normalized_outputs = [
            _normalize_loop_text(turn.output_text or "")
            for turn in self._turn_records(session_id)
            if turn.speaker_kind == ConversationSpeakerKind.AGENT
            and turn.status == ConversationTurnStatus.SUCCEEDED
            and (turn.output_text or "") != ""
        ]
        if not normalized_outputs:
            return False
        recent_outputs = normalized_outputs[-policy.loop_guard_window :]
        return recent_outputs.count(recent_outputs[-1]) >= policy.repeat_output_threshold

    def _agents_for_world(
        self,
        world_id: uuid.UUID,
        agent_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, Agent]:
        if not agent_ids:
            return {}
        agents = list(
            self._session.scalars(
                select(Agent).where(
                    Agent.world_id == world_id,
                    Agent.id.in_(agent_ids),
                ),
            ).all()
        )
        return {agent.id: agent for agent in agents}

    def _ensure_not_finished(self, session_model: ConversationSession) -> None:
        if session_model.status in {
            ConversationSessionStatus.COMPLETED.value,
            ConversationSessionStatus.STOPPED.value,
            ConversationSessionStatus.FAILED.value,
        }:
            raise ConversationStateError("Conversation session is no longer active")

    def _mark_session_completed(self, session_model: ConversationSession) -> None:
        if session_model.status == ConversationSessionStatus.COMPLETED.value:
            return
        session_model.status = ConversationSessionStatus.COMPLETED.value
        session_model.terminal_reason = ConversationTerminalReason.MAX_TURNS_REACHED.value
        self._append_event(
            world_id=session_model.world_id,
            worldline_id=session_model.worldline_id,
            event_name=CONVERSATION_SESSION_COMPLETED_EVENT_NAME,
            payload={
                "conversation_id": str(session_model.id),
                "max_turns": session_model.max_turns,
                "terminal_reason": ConversationTerminalReason.MAX_TURNS_REACHED.value,
            },
        )

    def _mark_session_stopped(
        self,
        session_model: ConversationSession,
        *,
        terminal_reason: ConversationTerminalReason,
        event_name: str,
        message: str,
        details: dict[str, object],
    ) -> None:
        if session_model.status == ConversationSessionStatus.STOPPED.value:
            return
        session_model.status = ConversationSessionStatus.STOPPED.value
        session_model.terminal_reason = terminal_reason.value
        self._append_event(
            world_id=session_model.world_id,
            worldline_id=session_model.worldline_id,
            event_name=event_name,
            payload={
                **details,
                "terminal_reason": terminal_reason.value,
            },
        )
        self._record_conversation_diagnostic(
            session_model,
            severity=DiagnosticSeverity.WARNING,
            event_type=event_name,
            message=message,
            details={
                **details,
                "terminal_reason": terminal_reason.value,
            },
        )

    def _mark_session_failed(
        self,
        session_model: ConversationSession,
        *,
        terminal_reason: ConversationTerminalReason,
        turn_index: int | None,
        speaker_agent_id: uuid.UUID | None,
        error_text: str,
        run_id: uuid.UUID | None = None,
    ) -> None:
        if session_model.status == ConversationSessionStatus.FAILED.value:
            return
        session_model.status = ConversationSessionStatus.FAILED.value
        session_model.terminal_reason = terminal_reason.value
        payload: dict[str, object] = {
            "conversation_id": str(session_model.id),
            "turn_index": turn_index,
            "speaker_agent_id": None if speaker_agent_id is None else str(speaker_agent_id),
            "run_id": None if run_id is None else str(run_id),
            "error": error_text,
            "terminal_reason": terminal_reason.value,
        }
        self._append_event(
            world_id=session_model.world_id,
            worldline_id=session_model.worldline_id,
            event_name=CONVERSATION_SESSION_FAILED_EVENT_NAME,
            payload=payload,
        )
        self._record_conversation_diagnostic(
            session_model,
            severity=DiagnosticSeverity.ERROR,
            event_type="conversation.session_failed",
            message="Conversation session failed.",
            details=payload,
            agent_id=speaker_agent_id,
            run_id=run_id,
        )

    def _record_conversation_diagnostic(
        self,
        session_model: ConversationSession,
        *,
        severity: DiagnosticSeverity,
        event_type: str,
        message: str,
        details: dict[str, object],
        agent_id: uuid.UUID | None = None,
        run_id: uuid.UUID | None = None,
    ) -> None:
        self._diagnostics.record(
            RuntimeDiagnosticCreate(
                severity=severity,
                component=DiagnosticComponent.CONVERSATION,
                event_type=event_type,
                message=message,
                details=details,
                world_id=session_model.world_id,
                agent_id=agent_id,
                run_id=run_id,
            ),
        )

    def _append_event(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None = None,
        event_name: str,
        payload: dict[str, object],
    ) -> None:
        WorldEventStore(self._session).append_event(
            WorldEventAppend(
                world_id=world_id,
                worldline_id=worldline_id,
                event_name=event_name,
                payload=payload,
                wall_time=datetime.now(UTC),
                actor_ref=self._actor_ref,
            ),
        )

    def _worldline_id(self, world_id: uuid.UUID, worldline_id: uuid.UUID | None) -> uuid.UUID:
        if worldline_id is None:
            return ensure_primary_worldline(self._session, world_id).id
        worldline = self._session.get(Worldline, worldline_id)
        if worldline is None or worldline.world_id != world_id:
            raise ConversationValidationError("Conversation worldline must belong to the world")
        return worldline.id


def _session_record(model: ConversationSession) -> ConversationSessionRecord:
    terminal_reason = (
        None
        if model.terminal_reason is None
        else ConversationTerminalReason(model.terminal_reason)
    )
    return ConversationSessionRecord(
        id=model.id,
        world_id=model.world_id,
        worldline_id=model.worldline_id,
        scene_id=model.scene_id,
        session_key=model.session_key,
        title=model.title,
        scope_type=ConversationScopeType(model.scope_type),
        mode=ConversationMode(model.mode),
        status=ConversationSessionStatus(model.status),
        objective=model.objective,
        opening_prompt=model.opening_prompt,
        max_turns=model.max_turns,
        next_turn_index=model.next_turn_index,
        policy=_policy_config(model.policy_config),
        writer_config=_writer_config(model.writer_config),
        memory_config=_memory_config(model.memory_config),
        terminal_reason=terminal_reason,
        created_at=_utc(model.created_at),
        updated_at=_utc(model.updated_at),
    )


def _participant_record(model: ConversationParticipant) -> ConversationParticipantRecord:
    return ConversationParticipantRecord(
        id=model.id,
        session_id=model.session_id,
        agent_id=model.agent_id,
        turn_order=model.turn_order,
        is_enabled=model.is_enabled,
        created_at=_utc(model.created_at),
        updated_at=_utc(model.updated_at),
    )


def _turn_record(model: ConversationTurn) -> ConversationTurnRecord:
    return ConversationTurnRecord(
        id=model.id,
        session_id=model.session_id,
        turn_index=model.turn_index,
        speaker_kind=ConversationSpeakerKind(model.speaker_kind),
        speaker_agent_id=model.speaker_agent_id,
        input_text=model.input_text,
        output_text=model.output_text,
        status=ConversationTurnStatus(model.status),
        run_id=model.run_id,
        error_text=model.error_text,
        created_at=_utc(model.created_at),
        updated_at=_utc(model.updated_at),
    )


def _policy_config(value: dict[str, object]) -> ConversationPolicyConfig:
    normalized = {
        "speaker_policy": ConversationSpeakerPolicyMode.ROUND_ROBIN.value,
        "manual_next_agent_id": None,
        "participant_repeat_cooldown": 0,
        "min_enabled_participants": 1,
        "max_turn_budget": None,
        **value,
    }
    return ConversationPolicyConfig.model_validate(normalized)


def _writer_config(value: dict[str, object]) -> ConversationWriterConfig:
    normalized = {
        "style_guide": "",
        "target_length": "standard",
        "source_constraints": "",
        "include_prompt_preview": True,
        **value,
    }
    return ConversationWriterConfig.model_validate(normalized)


def _memory_config(value: dict[str, object]) -> ConversationMemoryConfig:
    normalized = {
        "include_recent_turns": True,
        "include_agent_observations": True,
        "memory_query_strategy": "prompt",
        **value,
    }
    return ConversationMemoryConfig.model_validate(normalized)


def _normalize_loop_text(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", value.strip().lower())


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
