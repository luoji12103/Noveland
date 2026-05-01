from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime

from noveland.adapters import ProviderProfileService
from noveland.core.database import create_engine_from_settings, create_session_factory
from noveland.core.models import RuntimeControlState
from noveland.core.settings import AppSettings
from noveland.events import WorldEventPublisher
from noveland.memory import MemoryService
from noveland.observability import (
    DiagnosticComponent,
    DiagnosticSeverity,
    RuntimeDiagnosticCreate,
    RuntimeDiagnosticsService,
)
from noveland.services.runtime.agent_loop import AgentRuntimeOrchestrator
from noveland.services.runtime.clock_tick import RuntimeClockTicker
from noveland.services.runtime.conversation_loop import ConversationRuntimeOrchestrator
from sqlalchemy import select
from sqlalchemy.orm import Session

LOGGER = logging.getLogger("noveland.runtime.daemon")


@dataclass(frozen=True, slots=True)
class RuntimeControlView:
    desired_state: str
    last_heartbeat_at: datetime | None
    last_run_started_at: datetime | None
    last_run_finished_at: datetime | None
    last_error: str | None


@dataclass(frozen=True, slots=True)
class RuntimeLoopResult:
    desired_state: str
    advanced_worlds: int
    executed_runs: int
    processed_memory_jobs: int


class RuntimeControlService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_or_create(self) -> RuntimeControlState:
        model = self._session.scalars(
            select(RuntimeControlState).where(RuntimeControlState.control_key == "default"),
        ).one_or_none()
        if model is not None:
            return model
        model = RuntimeControlState(control_key="default", desired_state="stopped")
        self._session.add(model)
        self._session.flush()
        return model

    def view(self) -> RuntimeControlView:
        return _control_view(self.get_or_create())

    def set_desired_state(self, desired_state: str) -> RuntimeControlView:
        model = self.get_or_create()
        model.desired_state = desired_state
        self._session.flush()
        return _control_view(model)

    def mark_heartbeat(self) -> RuntimeControlState:
        model = self.get_or_create()
        model.last_heartbeat_at = datetime.now(UTC)
        self._session.flush()
        return model

    def mark_loop_started(self) -> RuntimeControlState:
        model = self.mark_heartbeat()
        model.last_run_started_at = datetime.now(UTC)
        self._session.flush()
        return model

    def mark_loop_finished(self, error: str | None = None) -> RuntimeControlView:
        model = self.mark_heartbeat()
        model.last_run_finished_at = datetime.now(UTC)
        model.last_error = error
        self._session.flush()
        return _control_view(model)


class RuntimeDaemon:
    def __init__(
        self,
        settings: AppSettings,
        publisher: WorldEventPublisher,
    ) -> None:
        self._settings = settings
        engine = create_engine_from_settings(settings)
        self._session_factory = create_session_factory(engine)
        self._publisher = publisher

    def run_iteration(self) -> RuntimeLoopResult:
        with self._session_factory() as session:
            control_service = RuntimeControlService(session)
            diagnostics = RuntimeDiagnosticsService(session)
            control = control_service.get_or_create()
            if control.desired_state != "running":
                control_service.mark_heartbeat()
                diagnostics.record(
                    RuntimeDiagnosticCreate(
                        severity=DiagnosticSeverity.INFO,
                        component=DiagnosticComponent.RUNTIME,
                        event_type="runtime.iteration_skipped",
                        message="Runtime iteration skipped because desired state is stopped.",
                        details={"desired_state": control.desired_state},
                    ),
                )
                session.commit()
                return RuntimeLoopResult(
                    desired_state=control.desired_state,
                    advanced_worlds=0,
                    executed_runs=0,
                    processed_memory_jobs=0,
                )

            control_service.mark_loop_started()
            diagnostics.record(
                RuntimeDiagnosticCreate(
                    severity=DiagnosticSeverity.INFO,
                    component=DiagnosticComponent.RUNTIME,
                    event_type="runtime.iteration_started",
                    message="Runtime iteration started.",
                    details={"desired_state": control.desired_state},
                ),
            )
            try:
                wall_time = datetime.now(UTC)
                tick_result = RuntimeClockTicker(session, self._publisher).run_once(wall_time)
                world_ids = sorted({event.world_id for event in tick_result.events}, key=str)
                profile_service = ProviderProfileService(session, self._settings)
                executed_runs = (
                    AgentRuntimeOrchestrator(
                        session,
                        profile_service,
                        self._settings,
                    )
                    .run_due_agents(
                        world_ids,
                        wall_time=wall_time,
                        batch_limit=self._settings.runtime_batch_limit,
                    )
                    .executed_runs
                )
                remaining_capacity = max(self._settings.runtime_batch_limit - executed_runs, 0)
                conversation_turns = (
                    ConversationRuntimeOrchestrator(
                        session,
                        profile_service,
                        self._settings,
                    )
                    .advance_running_sessions(remaining_capacity)
                    .executed_turns
                )
                executed_runs += conversation_turns
                processed_memory_jobs = MemoryService(
                    session,
                    self._settings,
                ).process_due_jobs(self._settings.runtime_batch_limit)
                view = control_service.mark_loop_finished()
                diagnostics.record(
                    RuntimeDiagnosticCreate(
                        severity=DiagnosticSeverity.INFO,
                        component=DiagnosticComponent.RUNTIME,
                        event_type="runtime.iteration_finished",
                        message="Runtime iteration finished.",
                        details={
                            "advanced_worlds": tick_result.advanced_worlds,
                            "executed_runs": executed_runs,
                            "executed_conversation_turns": conversation_turns,
                            "processed_memory_jobs": processed_memory_jobs,
                            "published_events": tick_result.published_events,
                        },
                    ),
                )
                session.commit()
                return RuntimeLoopResult(
                    desired_state=view.desired_state,
                    advanced_worlds=tick_result.advanced_worlds,
                    executed_runs=executed_runs,
                    processed_memory_jobs=processed_memory_jobs,
                )
            except Exception as exc:
                view = control_service.mark_loop_finished(str(exc))
                diagnostics.record(
                    RuntimeDiagnosticCreate(
                        severity=DiagnosticSeverity.ERROR,
                        component=DiagnosticComponent.RUNTIME,
                        event_type="runtime.iteration_failed",
                        message="Runtime iteration failed.",
                        details={
                            "error": str(exc),
                            "error_type": type(exc).__name__,
                        },
                    ),
                )
                session.commit()
                LOGGER.exception("runtime iteration failed")
                return RuntimeLoopResult(
                    desired_state=view.desired_state,
                    advanced_worlds=0,
                    executed_runs=0,
                    processed_memory_jobs=0,
                )

    def run_loop(self, max_iterations: int | None = None) -> int:
        iteration = 0
        while max_iterations is None or iteration < max_iterations:
            self.run_iteration()
            iteration += 1
            time.sleep(self._settings.runtime_loop_interval_seconds)
        return 0


def get_runtime_control_view(session: Session) -> RuntimeControlView:
    return RuntimeControlService(session).view()


def set_runtime_desired_state(session: Session, desired_state: str) -> RuntimeControlView:
    return RuntimeControlService(session).set_desired_state(desired_state)


def _control_view(model: RuntimeControlState) -> RuntimeControlView:
    return RuntimeControlView(
        desired_state=model.desired_state,
        last_heartbeat_at=model.last_heartbeat_at,
        last_run_started_at=model.last_run_started_at,
        last_run_finished_at=model.last_run_finished_at,
        last_error=model.last_error,
    )
