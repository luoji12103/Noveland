from __future__ import annotations

import uuid
from dataclasses import dataclass, replace

from noveland.adapters import ProviderProfileService
from noveland.conversations import (
    ConversationAdvanceResult,
    ConversationErrorPolicy,
    ConversationMemoryConfig,
    ConversationService,
    ConversationSessionStatus,
)
from noveland.conversations.errors import ConversationStateError
from noveland.core.settings import AppSettings
from noveland.narrative import ConversationNarrativeWriterService
from noveland.services.runtime.agent_loop import AgentRunExecution, AgentRuntimeOrchestrator
from sqlalchemy.orm import Session


@dataclass(frozen=True, slots=True)
class ConversationBatchResult:
    executed_turns: int


class ConversationRuntimeOrchestrator:
    def __init__(
        self,
        session: Session,
        profile_service: ProviderProfileService,
        settings: AppSettings,
    ) -> None:
        self._session = session
        self._profile_service = profile_service
        self._settings = settings
        self._conversation_service = ConversationService(session)
        self._agent_orchestrator = AgentRuntimeOrchestrator(session, profile_service, settings)

    def advance_session(
        self,
        world_id: uuid.UUID,
        session_id: uuid.UUID,
        *,
        allow_running_auto: bool,
        trigger_source: str,
    ) -> ConversationAdvanceResult:
        prepared = self._conversation_service.prepare_next_turn(
            world_id,
            session_id,
            allow_running_auto=allow_running_auto,
        )
        policy = prepared.session.policy
        run = self._run_agent_turn(
            world_id=world_id,
            agent_id=prepared.speaker_agent_id,
            prompt_text=prepared.prompt_text,
            trigger_source=trigger_source,
            memory_config=prepared.session.memory_config,
            objective=prepared.session.objective,
        )
        if run.status != "succeeded" and policy.error_policy in {
            ConversationErrorPolicy.RETRY_ONCE_THEN_FAIL,
            ConversationErrorPolicy.RETRY_ONCE_THEN_SKIP,
        }:
            retry_run = self._run_agent_turn(
                world_id=world_id,
                    agent_id=prepared.speaker_agent_id,
                    prompt_text=prepared.prompt_text,
                    trigger_source=f"{trigger_source}:retry",
                    memory_config=prepared.session.memory_config,
                    objective=prepared.session.objective,
                )
            retry_diagnostics = dict(retry_run.diagnostics)
            retry_diagnostics["attempt_count"] = 2
            retry_diagnostics["initial_error"] = _error_text(run.diagnostics)
            run = replace(retry_run, diagnostics=retry_diagnostics)
        else:
            run = replace(run, diagnostics={**run.diagnostics, "attempt_count": 1})
        result = self._conversation_service.finalize_turn(
            prepared,
            response_text=run.response_text,
            run_id=run.run_id,
            diagnostics=run.diagnostics,
            succeeded=run.status == "succeeded",
            error_text=None if run.status == "succeeded" else _error_text(run.diagnostics),
        )
        if result.session.status == ConversationSessionStatus.COMPLETED:
            ConversationNarrativeWriterService(
                self._session,
                self._profile_service,
            ).auto_generate_for_completed_conversation(world_id, session_id)
        return result

    def _run_agent_turn(
        self,
        *,
        world_id: uuid.UUID,
        agent_id: uuid.UUID,
        prompt_text: str,
        trigger_source: str,
        memory_config: ConversationMemoryConfig,
        objective: str,
    ) -> AgentRunExecution:
        memory_query_text = prompt_text
        if memory_config.memory_query_strategy == "objective":
            memory_query_text = objective or prompt_text
        elif memory_config.memory_query_strategy == "transcript":
            memory_query_text = prompt_text[-2_000:]
        return self._agent_orchestrator.run_agent(
            world_id=world_id,
            agent_id=agent_id,
            prompt_text=prompt_text,
            trigger_source=trigger_source,
            create_memory=memory_config.write_turn_memory,
            retrieve_memory=memory_config.retrieve_memory,
            memory_query_text=memory_query_text,
            max_context_items=memory_config.max_context_items,
            create_narrative_artifact=False,
        )

    def advance_running_sessions(self, limit: int) -> ConversationBatchResult:
        safe_limit = max(0, limit)
        executed_turns = 0
        if safe_limit == 0:
            return ConversationBatchResult(executed_turns=0)

        for session in self._conversation_service.list_running_auto_sessions(safe_limit):
            if executed_turns >= safe_limit:
                break
            try:
                self.advance_session(
                    session.world_id,
                    session.id,
                    allow_running_auto=True,
                    trigger_source="runtime_tick",
                )
            except ConversationStateError:
                continue
            executed_turns += 1

        return ConversationBatchResult(executed_turns=executed_turns)


def _error_text(diagnostics: dict[str, object]) -> str:
    error = diagnostics.get("error")
    return str(error) if error is not None else "Conversation turn failed"
