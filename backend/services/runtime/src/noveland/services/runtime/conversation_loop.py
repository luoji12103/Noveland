from __future__ import annotations

import uuid
from dataclasses import dataclass

from noveland.adapters import ProviderProfileService
from noveland.conversations import ConversationAdvanceResult, ConversationService
from noveland.conversations.errors import ConversationStateError
from noveland.services.runtime.agent_loop import AgentRuntimeOrchestrator
from sqlalchemy.orm import Session


@dataclass(frozen=True, slots=True)
class ConversationBatchResult:
    executed_turns: int


class ConversationRuntimeOrchestrator:
    def __init__(
        self,
        session: Session,
        profile_service: ProviderProfileService,
    ) -> None:
        self._session = session
        self._profile_service = profile_service
        self._conversation_service = ConversationService(session)
        self._agent_orchestrator = AgentRuntimeOrchestrator(session, profile_service)

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
        run = self._agent_orchestrator.run_agent(
            world_id=world_id,
            agent_id=prepared.speaker_agent_id,
            prompt_text=prepared.prompt_text,
            trigger_source=trigger_source,
            create_memory=False,
            create_narrative_artifact=False,
        )
        return self._conversation_service.finalize_turn(
            prepared,
            response_text=run.response_text,
            run_id=run.run_id,
            diagnostics=run.diagnostics,
            succeeded=run.status == "succeeded",
            error_text=None if run.status == "succeeded" else _error_text(run.diagnostics),
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
