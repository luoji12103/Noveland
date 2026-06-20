from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast

from noveland.adapters import (
    ProviderCompletion,
    ProviderConfigurationError,
    ProviderError,
    ProviderProfileRecord,
    ProviderProfileService,
)
from noveland.agents import (
    AgentObservationRecord,
    AgentObservationService,
    AgentPersonaRecord,
    AgentPersonaService,
)
from noveland.agents.models import Agent, AgentRuntimeRun
from noveland.calendar import CalendarEntryRecord, CalendarService, ScheduleRuleRecord
from noveland.core.settings import AppSettings
from noveland.events import WorldEventAppend, WorldEventStore
from noveland.invocations import (
    AgentRuntimeRunInvocationLinkCreate,
    InvocationLedgerService,
    InvocationRecordCreate,
    InvocationStatusUpdate,
    PromptSnapshotCreate,
    PromptSnapshotService,
)
from noveland.invocations.contracts import (
    InvocationActorKind,
    InvocationKind,
    InvocationProviderKind,
    InvocationRedactionStatus,
    InvocationRetentionPolicy,
    InvocationRole,
    InvocationStatus,
    InvocationVisibility,
    PromptSnapshotUpdate,
)
from noveland.invocations.models import AgentRuntimeRunModelInvocation, ModelInvocation
from noveland.memory import MemoryContext, MemoryMessage, MemoryService, MemoryTurn
from noveland.narrative import (
    NarrativeArtifactCreate,
    NarrativeArtifactKind,
    NarrativeArtifactRecord,
    NarrativeArtifactService,
)
from noveland.observability import (
    DiagnosticComponent,
    DiagnosticSeverity,
    RuntimeDiagnosticCreate,
    RuntimeDiagnosticsService,
)
from noveland.plugins.builtins import (
    PersonaPolicyPlugin,
    WorldRulesPlugin,
    get_builtin_plugin_registry,
)
from noveland.plugins.categories import PluginCategory
from noveland.plugins.constants import BUILTIN_DEFAULT_PERSONA_POLICY
from noveland.plugins.errors import (
    PluginConfigValidationError,
    PluginFactoryError,
    PluginNotFoundError,
)
from noveland.providers.contracts import (
    ProviderExecutionRequest,
    ProviderIntegrationRead,
    ProviderKind,
)
from noveland.providers.registry import ProviderNotFoundError, ProviderRegistryService
from noveland.providers.routing import invocation_provider_kind_for_adapter
from noveland.providers.service import ProviderExecutionError, ProviderExecutionService
from noveland.services.runtime.identity import RUNTIME_ACTOR_REF
from noveland.worlds.clock_service import WorldClockService
from noveland.worlds.living_context import LivingWorldContextSelector
from noveland.worlds.models import World, Worldline
from noveland.worlds.worldlines import ensure_primary_worldline
from sqlalchemy import inspect as inspect_sqlalchemy
from sqlalchemy import select
from sqlalchemy.orm import Session

CALENDAR_ENTRY_DUE_EVENT_NAME = "calendar.entry_due"
AGENT_RUN_STARTED_EVENT_NAME = "agent.run_started"
AGENT_RUN_COMPLETED_EVENT_NAME = "agent.run_completed"
AGENT_RUN_FAILED_EVENT_NAME = "agent.run_failed"
MEMORY_ITEM_CREATED_EVENT_NAME = "memory.item_created"
NARRATIVE_ARTIFACT_CREATED_EVENT_NAME = "narrative.artifact_created"


@dataclass(frozen=True, slots=True)
class AgentRunExecution:
    run_id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    agent_id: uuid.UUID
    status: str
    prompt_text: str
    response_text: str | None
    provider_profile_id: uuid.UUID | None
    trigger_source: str
    source_calendar_entry_id: uuid.UUID | None
    source_schedule_rule_id: uuid.UUID | None
    created_event_id: uuid.UUID | None
    diagnostics: dict[str, Any]
    started_at: datetime
    finished_at: datetime | None


@dataclass(frozen=True, slots=True)
class DueRunBatchResult:
    executed_runs: int


@dataclass(frozen=True, slots=True)
class _ResolvedRuntimeProvider:
    id: uuid.UUID
    provider_key: str
    legacy_profile: ProviderProfileRecord | None = None
    provider_integration: ProviderIntegrationRead | None = None

    @property
    def uses_provider_execution(self) -> bool:
        return self.provider_integration is not None


class AgentRuntimeOrchestrator:
    def __init__(
        self,
        session: Session,
        profile_service: ProviderProfileService,
        settings: AppSettings,
    ) -> None:
        self._session = session
        self._profile_service = profile_service
        self._settings = settings

    def list_runs(
        self,
        world_id: uuid.UUID,
        agent_id: uuid.UUID,
        worldline_id: uuid.UUID | None = None,
    ) -> list[AgentRunExecution]:
        resolved_worldline_id = self._worldline_id(world_id, worldline_id)
        return [
            _run_record(model)
            for model in self._session.scalars(
                select(AgentRuntimeRun)
                .where(
                    AgentRuntimeRun.world_id == world_id,
                    AgentRuntimeRun.worldline_id == resolved_worldline_id,
                    AgentRuntimeRun.agent_id == agent_id,
                )
                .order_by(AgentRuntimeRun.started_at.desc()),
            ).all()
        ]

    def get_run(
        self,
        world_id: uuid.UUID,
        agent_id: uuid.UUID,
        run_id: uuid.UUID,
        worldline_id: uuid.UUID | None = None,
    ) -> AgentRunExecution | None:
        resolved_worldline_id = self._worldline_id(world_id, worldline_id)
        model = self._session.scalars(
            select(AgentRuntimeRun).where(
                AgentRuntimeRun.id == run_id,
                AgentRuntimeRun.world_id == world_id,
                AgentRuntimeRun.worldline_id == resolved_worldline_id,
                AgentRuntimeRun.agent_id == agent_id,
            ),
        ).one_or_none()
        return None if model is None else _run_record(model)

    def run_agent(
        self,
        world_id: uuid.UUID,
        agent_id: uuid.UUID,
        prompt_text: str,
        trigger_source: str,
        worldline_id: uuid.UUID | None = None,
        provider_profile_id: uuid.UUID | None = None,
        source_calendar_entry_id: uuid.UUID | None = None,
        source_schedule_rule_id: uuid.UUID | None = None,
        create_memory: bool = True,
        retrieve_memory: bool = True,
        memory_query_text: str | None = None,
        max_context_items: int = 5,
        create_narrative_artifact: bool = True,
    ) -> AgentRunExecution:
        resolved_worldline_id = self._worldline_id(world_id, worldline_id)
        started_at = datetime.now(UTC)
        agent = self._agent_or_404(world_id, agent_id)
        observation_service = AgentObservationService(self._session)
        observation_service.refresh_from_events(world_id, agent_id)
        persona = AgentPersonaService(self._session).get(world_id, agent_id)
        observations = observation_service.list(world_id, agent_id, limit=8)
        memory_service = MemoryService(self._session, self._settings)
        memory_context = (
            memory_service.build_context(
                world_id=world_id,
                worldline_id=resolved_worldline_id,
                agent_id=agent_id,
                query_text=memory_query_text or prompt_text,
                max_context_items=max_context_items,
            )
            if retrieve_memory
            else None
        )
        context_selector = LivingWorldContextSelector(self._session)
        living_context = context_selector.select_for_agent_prompt(
            world_id=world_id,
            worldline_id=resolved_worldline_id,
            agent_id=agent_id,
        )
        living_context_pack = context_selector.select_context_pack(
            world_id=world_id,
            worldline_id=resolved_worldline_id,
        )
        provider_prompt = self._build_agent_prompt(
            agent,
            prompt_text,
            persona,
            observations,
            memory_context=_join_prompt_contexts(
                _memory_context_text(memory_context),
                living_context.to_prompt_text(),
                living_context_pack.to_prompt_text(),
            ),
        )
        prompt_context = {
            "persona_enabled": persona is not None and persona.is_enabled,
            "observation_ids": [str(observation.id) for observation in observations],
            "observation_count": len(observations),
            "memory_retrieval_enabled": retrieve_memory,
            "worldline_id": str(resolved_worldline_id),
            "memory_backend": None if memory_context is None else memory_context.backend,
            "memory_hit_count": 0 if memory_context is None else len(memory_context.items),
            "living_context": living_context.diagnostics,
            "living_context_pack": living_context_pack.diagnostics,
        }
        provider = self._resolve_provider(agent, provider_profile_id, world_id=world_id)
        provider_metadata = _runtime_provider_metadata(provider)
        run_model = AgentRuntimeRun(
            world_id=world_id,
            worldline_id=resolved_worldline_id,
            agent_id=agent_id,
            provider_profile_id=_runtime_provider_profile_id(provider),
            source_calendar_entry_id=source_calendar_entry_id,
            source_schedule_rule_id=source_schedule_rule_id,
            status="running",
            trigger_source=trigger_source,
            prompt_text=_runtime_prompt_summary(prompt_text),
            diagnostics={},
            started_at=started_at,
        )
        self._session.add(run_model)
        self._session.flush()

        self._append_event(
            world_id=world_id,
            worldline_id=resolved_worldline_id,
            event_name=AGENT_RUN_STARTED_EVENT_NAME,
            payload={
                "agent_id": str(agent_id),
                "run_id": str(run_model.id),
                "trigger_source": trigger_source,
            },
            actor_ref=RUNTIME_ACTOR_REF,
        )

        trace_id = uuid.uuid4()
        invocation_id: uuid.UUID | None = None
        if provider.legacy_profile is not None:
            invocation = InvocationLedgerService(self._session).record(
                InvocationRecordCreate(
                    world_id=world_id,
                    worldline_id=resolved_worldline_id,
                    trace_id=trace_id,
                    invocation_kind=InvocationKind.AGENT_RUNTIME,
                    actor_kind=InvocationActorKind.RUNTIME,
                    actor_ref=RUNTIME_ACTOR_REF,
                    agent_id=agent_id,
                    provider_kind=_invocation_provider_kind(provider),
                    provider_profile_id=provider.legacy_profile.id,
                    model_name=provider.legacy_profile.model_name,
                    input_text=_runtime_prompt_summary(prompt_text),
                    request_params_json={
                        "trigger_source": trigger_source,
                        "retrieve_memory": retrieve_memory,
                        "max_context_items": max_context_items,
                        "create_memory": create_memory,
                        "create_narrative_artifact": create_narrative_artifact,
                        **provider_metadata,
                    },
                    status=InvocationStatus.RUNNING,
                    visibility=InvocationVisibility.WORLD_ADMIN,
                    redaction_status=InvocationRedactionStatus.RAW,
                    retention_policy=InvocationRetentionPolicy.LOCAL_DEBUG,
                    contains_sensitive_context=_contains_sensitive_context(prompt_context),
                    prompt_snapshot=PromptSnapshotCreate(
                        raw_prompt_text=provider_prompt,
                        raw_request_json=_runtime_provider_prompt_json(provider),
                        prompt_context_snapshot_json=prompt_context,
                        visibility=InvocationVisibility.WORLD_ADMIN,
                        redaction_status=InvocationRedactionStatus.RAW,
                        contains_sensitive_context=_contains_sensitive_context(prompt_context),
                    ),
                )
            )
            invocation_id = invocation.id
            InvocationLedgerService(self._session).link_runtime_run(
                AgentRuntimeRunInvocationLinkCreate(
                    world_id=world_id,
                    worldline_id=resolved_worldline_id,
                    agent_runtime_run_id=run_model.id,
                    model_invocation_id=invocation.id,
                    invocation_role=InvocationRole.PRIMARY,
                    sequence_index=0,
                )
            )

        try:
            provider_started_at = datetime.now(UTC)
            if provider.legacy_profile is not None:
                completion = self._profile_service.invoke_profile(
                    provider.legacy_profile,
                    provider_prompt,
                )
                if invocation_id is None:
                    raise ProviderConfigurationError("Runtime invocation was not recorded")
                InvocationLedgerService(self._session).update_status(
                    world_id,
                    invocation_id,
                    InvocationStatusUpdate(
                        status=InvocationStatus.SUCCEEDED,
                        output_text=completion.text,
                        response_metadata_json=completion.raw_response,
                        latency_ms=_latency_ms(provider_started_at),
                    ),
                )
                PromptSnapshotService(self._session).update_snapshot_for_invocation(
                    invocation_id,
                    PromptSnapshotUpdate(
                        raw_response_json=completion.raw_response,
                        raw_output_text=completion.text,
                    ),
                )
            else:
                result = ProviderExecutionService(self._session).execute(
                    ProviderExecutionRequest(
                        world_id=world_id,
                        worldline_id=resolved_worldline_id,
                        trace_id=trace_id,
                        provider_id=provider.id,
                        provider_kind=ProviderKind.TEXT_GENERATION,
                        capability_key="text.generate",
                        input_text=provider_prompt,
                        input_json={
                            "trigger_source": trigger_source,
                            "worldline_id": str(resolved_worldline_id),
                        },
                        request_json={
                            "operation": "agent_runtime",
                            "trigger_source": trigger_source,
                            "retrieve_memory": retrieve_memory,
                            "max_context_items": max_context_items,
                            "create_memory": create_memory,
                            "create_narrative_artifact": create_narrative_artifact,
                            **provider_metadata,
                        },
                        invocation_kind=InvocationKind.AGENT_RUNTIME,
                        actor_kind=InvocationActorKind.RUNTIME,
                        agent_id=agent_id,
                        actor_ref=RUNTIME_ACTOR_REF,
                    )
                )
                invocation_id = result.invocation.id
                text = (result.output_text or "").strip()
                if text == "":
                    raise ProviderConfigurationError("Runtime provider returned no text")
                completion = ProviderCompletion(text=text, raw_response=result.output_json)
                InvocationLedgerService(self._session).link_runtime_run(
                    AgentRuntimeRunInvocationLinkCreate(
                        world_id=world_id,
                        worldline_id=resolved_worldline_id,
                        agent_runtime_run_id=run_model.id,
                        model_invocation_id=invocation_id,
                        invocation_role=InvocationRole.PRIMARY,
                        sequence_index=0,
                    )
                )
            latency_ms = _latency_ms(provider_started_at)
            run_model.status = "succeeded"
            run_model.response_text = completion.text
            run_model.finished_at = datetime.now(UTC)
            run_model.diagnostics = {
                **provider_metadata,
                "model_invocation_id": None if invocation_id is None else str(invocation_id),
                "latency_ms": latency_ms,
                **prompt_context,
            }
            self._record_diagnostic(
                severity=DiagnosticSeverity.INFO,
                component=DiagnosticComponent.AGENT,
                event_type="agent.run_succeeded",
                message="Agent runtime run succeeded.",
                details={
                    "trigger_source": trigger_source,
                    **provider_metadata,
                    **prompt_context,
                },
                world_id=world_id,
                agent_id=agent_id,
                run_id=run_model.id,
                provider_profile_id=_runtime_provider_profile_id(provider),
            )
            created_event = self._append_event(
                world_id=world_id,
                worldline_id=resolved_worldline_id,
                event_name=AGENT_RUN_COMPLETED_EVENT_NAME,
                payload={
                    "agent_id": str(agent_id),
                    "run_id": str(run_model.id),
                    **provider_metadata,
                },
                actor_ref=RUNTIME_ACTOR_REF,
            )
            run_model.created_event_id = created_event.id

            if create_memory:
                try:
                    memory_job = memory_service.record_turn(
                        MemoryTurn(
                            world_id=world_id,
                            worldline_id=resolved_worldline_id,
                            agent_id=agent_id,
                            run_id=run_model.id,
                            source_event_id=created_event.id,
                            trigger_source=trigger_source,
                            messages=[
                                MemoryMessage(role="assistant", content=completion.text),
                            ],
                            metadata={
                                "run_id": str(run_model.id),
                                "trigger_source": trigger_source,
                                "prompt_text": prompt_text,
                                "source_calendar_entry_id": None
                                if source_calendar_entry_id is None
                                else str(source_calendar_entry_id),
                                "source_schedule_rule_id": None
                                if source_schedule_rule_id is None
                                else str(source_schedule_rule_id),
                            },
                            dedupe_key=f"agent-run:{run_model.id}",
                        ),
                    )
                    self._append_event(
                        world_id=world_id,
                        worldline_id=resolved_worldline_id,
                        event_name=MEMORY_ITEM_CREATED_EVENT_NAME,
                        payload={
                            "agent_id": str(agent_id),
                            "memory_job_id": str(memory_job.id),
                            "run_id": str(run_model.id),
                        },
                        actor_ref=RUNTIME_ACTOR_REF,
                    )
                except Exception as exc:
                    self._record_diagnostic(
                        severity=DiagnosticSeverity.WARNING,
                        component=DiagnosticComponent.AGENT,
                        event_type="memory.write_enqueue_failed",
                        message="Long-term memory write enqueue failed.",
                        details={
                            "run_id": str(run_model.id),
                            "error": str(exc),
                            "error_type": type(exc).__name__,
                        },
                        world_id=world_id,
                        agent_id=agent_id,
                        run_id=run_model.id,
                        provider_profile_id=_runtime_provider_profile_id(provider),
                    )

            if create_narrative_artifact:
                artifact = NarrativeArtifactService(self._session).create_artifact(
                    NarrativeArtifactCreate(
                        world_id=world_id,
                        agent_id=agent_id,
                        source_run_id=run_model.id,
                        title=f"{agent.display_name} runtime note",
                        content=completion.text,
                        artifact_kind=NarrativeArtifactKind.AGENT_NOTE,
                        metadata={
                            "trigger_source": trigger_source,
                            "worldline_id": str(resolved_worldline_id),
                            "living_context_pack": living_context_pack.to_metadata(),
                        },
                    ),
                )
                self._append_event(
                    world_id=world_id,
                    worldline_id=resolved_worldline_id,
                    event_name=NARRATIVE_ARTIFACT_CREATED_EVENT_NAME,
                    payload={
                        "artifact_id": str(artifact.id),
                        "agent_id": str(agent_id),
                        "run_id": str(run_model.id),
                    },
                    actor_ref=RUNTIME_ACTOR_REF,
                )
        except Exception as exc:
            run_model.status = "failed"
            run_model.finished_at = datetime.now(UTC)
            if invocation_id is None:
                invocation_id = self._invocation_id_for_trace(world_id, trace_id)
            if invocation_id is not None:
                InvocationLedgerService(self._session).update_status(
                    world_id,
                    invocation_id,
                    InvocationStatusUpdate(
                        status=InvocationStatus.FAILED,
                        error_text=str(exc),
                        latency_ms=_latency_ms(started_at),
                    ),
                )
                if provider.uses_provider_execution:
                    self._link_runtime_invocation(
                        world_id=world_id,
                        worldline_id=resolved_worldline_id,
                        run_id=run_model.id,
                        invocation_id=invocation_id,
                    )
            run_model.diagnostics = {
                "error": str(exc),
                **provider_metadata,
                "model_invocation_id": None if invocation_id is None else str(invocation_id),
                **prompt_context,
            }
            self._record_diagnostic(
                severity=DiagnosticSeverity.ERROR,
                component=DiagnosticComponent.AGENT,
                event_type="agent.run_failed",
                message="Agent runtime run failed.",
                details={
                    "trigger_source": trigger_source,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    **provider_metadata,
                    **prompt_context,
                },
                world_id=world_id,
                agent_id=agent_id,
                run_id=run_model.id,
                provider_profile_id=_runtime_provider_profile_id(provider),
            )
            if isinstance(exc, ProviderError | ProviderExecutionError):
                self._record_diagnostic(
                    severity=DiagnosticSeverity.ERROR,
                    component=DiagnosticComponent.PROVIDER,
                    event_type="provider.invocation_failed",
                    message="Provider configuration or invocation failed.",
                    details={
                        "trigger_source": trigger_source,
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                        **provider_metadata,
                    },
                    world_id=world_id,
                    agent_id=agent_id,
                    run_id=run_model.id,
                    provider_profile_id=_runtime_provider_profile_id(provider),
                )
            failed_event = self._append_event(
                world_id=world_id,
                worldline_id=resolved_worldline_id,
                event_name=AGENT_RUN_FAILED_EVENT_NAME,
                payload={
                    "agent_id": str(agent_id),
                    "run_id": str(run_model.id),
                    "error": str(exc),
                },
                actor_ref=RUNTIME_ACTOR_REF,
            )
            run_model.created_event_id = failed_event.id

        observation_service.mark_consumed(
            [observation.id for observation in observations],
            run_id=run_model.id,
        )
        self._session.flush()
        return _run_record(run_model)

    def run_due_agents(
        self,
        world_ids: list[uuid.UUID],
        wall_time: datetime,
        batch_limit: int,
    ) -> DueRunBatchResult:
        executed_runs = 0
        calendar_service = CalendarService(self._session)

        for world_id in world_ids:
            if executed_runs >= batch_limit:
                break

            world_time = (
                WorldClockService(self._session)
                .view(
                    world_id,
                    wall_time,
                )
                .effective_world_time
            )
            due_entries = calendar_service.due_entries(world_id, world_time)
            due_rules = self._due_rules_plugin(world_id).due_rules(
                calendar_service.list_rules(world_id),
                world_time,
            )
            enabled_agents = self._enabled_agents(world_id)
            due_entries_by_agent = _entries_by_agent(due_entries)
            primary_worldline_id = ensure_primary_worldline(self._session, world_id).id

            for agent in enabled_agents:
                if executed_runs >= batch_limit:
                    break
                agent_due_entries = due_entries_by_agent.get(agent.id, [])
                if not agent_due_entries and not due_rules:
                    continue

                self._append_event(
                    world_id=world_id,
                    worldline_id=primary_worldline_id,
                    event_name=CALENDAR_ENTRY_DUE_EVENT_NAME,
                    payload={
                        "agent_id": str(agent.id),
                        "calendar_entry_ids": [str(entry.id) for entry in agent_due_entries],
                        "schedule_rule_keys": [rule.rule_key for rule in due_rules],
                    },
                    actor_ref=RUNTIME_ACTOR_REF,
                )
                first_entry_id = agent_due_entries[0].id if agent_due_entries else None
                first_rule_id = due_rules[0].id if due_rules else None
                self.run_agent(
                    world_id=world_id,
                    worldline_id=primary_worldline_id,
                    agent_id=agent.id,
                    prompt_text=_due_prompt(agent, world_time, agent_due_entries, due_rules),
                    trigger_source="runtime_tick",
                    source_calendar_entry_id=first_entry_id,
                    source_schedule_rule_id=first_rule_id,
                )
                executed_runs += 1

        return DueRunBatchResult(executed_runs=executed_runs)

    def create_narrative_artifact(
        self,
        world_id: uuid.UUID,
        title: str,
        content: str,
        artifact_kind: NarrativeArtifactKind,
        agent_id: uuid.UUID | None = None,
    ) -> NarrativeArtifactRecord:
        worldline_id = ensure_primary_worldline(self._session, world_id).id
        artifact = NarrativeArtifactService(self._session).create_artifact(
            NarrativeArtifactCreate(
                world_id=world_id,
                agent_id=agent_id,
                title=title,
                content=content,
                artifact_kind=artifact_kind,
            ),
        )
        self._append_event(
            world_id=world_id,
            worldline_id=worldline_id,
            event_name=NARRATIVE_ARTIFACT_CREATED_EVENT_NAME,
            payload={
                "artifact_id": str(artifact.id),
                "agent_id": None if agent_id is None else str(agent_id),
            },
            actor_ref=RUNTIME_ACTOR_REF,
        )
        return artifact

    def _enabled_agents(self, world_id: uuid.UUID) -> list[Agent]:
        return list(
            self._session.scalars(
                select(Agent)
                .where(
                    Agent.world_id == world_id,
                    Agent.is_enabled.is_(True),
                )
                .order_by(Agent.agent_key),
            ).all()
        )

    def _agent_or_404(self, world_id: uuid.UUID, agent_id: uuid.UUID) -> Agent:
        agent = self._session.get(Agent, agent_id)
        if agent is None or agent.world_id != world_id:
            raise LookupError("Agent not found")
        return agent

    def _resolve_provider(
        self,
        agent: Agent,
        provider_profile_id: uuid.UUID | None,
        *,
        world_id: uuid.UUID,
    ) -> _ResolvedRuntimeProvider:
        profile_from_agent = agent.config.get("provider_profile_id")
        resolved_provider_id = provider_profile_id
        if resolved_provider_id is None and isinstance(profile_from_agent, str):
            try:
                resolved_provider_id = uuid.UUID(profile_from_agent)
            except ValueError:
                resolved_provider_id = None
        if resolved_provider_id is not None:
            profile = self._profile_service.get_profile(resolved_provider_id)
            if profile is not None:
                return _ResolvedRuntimeProvider(
                    id=profile.id,
                    provider_key=profile.profile_key,
                    legacy_profile=profile,
                )
            provider = ProviderRegistryService(self._session).get_provider(
                world_id,
                resolved_provider_id,
                platform_admin=True,
                include_hidden=True,
            )
            if provider is None:
                raise ProviderConfigurationError("Configured runtime provider was not found")
            if provider.provider_kind != ProviderKind.TEXT_GENERATION:
                raise ProviderConfigurationError(
                    "Runtime provider must have provider_kind=text_generation",
                )
            return _ResolvedRuntimeProvider(
                id=provider.id,
                provider_key=provider.provider_key,
                provider_integration=provider,
            )
        try:
            provider = ProviderRegistryService(self._session).resolve_provider_for_capability(
                world_id,
                provider_kind=ProviderKind.TEXT_GENERATION,
                capability_key="text.generate",
                platform_admin=True,
                include_hidden=True,
            )
        except ProviderNotFoundError as exc:
            profile = self._profile_service.first_enabled_profile()
            if profile is not None:
                return _ResolvedRuntimeProvider(
                    id=profile.id,
                    provider_key=profile.profile_key,
                    legacy_profile=profile,
                )
            raise ProviderConfigurationError("No enabled runtime provider is available") from exc
        return _ResolvedRuntimeProvider(
            id=provider.id,
            provider_key=provider.provider_key,
            provider_integration=provider,
        )

    def _link_runtime_invocation(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        run_id: uuid.UUID,
        invocation_id: uuid.UUID,
    ) -> None:
        existing = self._session.scalars(
            select(AgentRuntimeRunModelInvocation).where(
                AgentRuntimeRunModelInvocation.agent_runtime_run_id == run_id,
                AgentRuntimeRunModelInvocation.model_invocation_id == invocation_id,
            )
        ).one_or_none()
        if existing is not None:
            return
        InvocationLedgerService(self._session).link_runtime_run(
            AgentRuntimeRunInvocationLinkCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                agent_runtime_run_id=run_id,
                model_invocation_id=invocation_id,
                invocation_role=InvocationRole.PRIMARY,
                sequence_index=0,
            )
        )

    def _invocation_id_for_trace(
        self,
        world_id: uuid.UUID,
        trace_id: uuid.UUID,
    ) -> uuid.UUID | None:
        model = self._session.scalars(
            select(ModelInvocation).where(
                ModelInvocation.world_id == world_id,
                ModelInvocation.trace_id == trace_id,
            )
        ).one_or_none()
        return None if model is None else model.id

    def _due_rules_plugin(self, world_id: uuid.UUID) -> WorldRulesPlugin:
        world = self._world_or_404(world_id)
        return cast(
            WorldRulesPlugin,
            self._plugin_instance(
                category=PluginCategory.WORLD_RULES,
                identifier=world.world_rules_plugin_identifier,
                raw_config=world.world_rules_plugin_config,
            ),
        )

    def _build_agent_prompt(
        self,
        agent: Agent,
        task_prompt: str,
        persona: AgentPersonaRecord | None,
        observations: list[AgentObservationRecord],
        *,
        memory_context: str | None = None,
    ) -> str:
        identifier = (
            BUILTIN_DEFAULT_PERSONA_POLICY if persona is None else persona.policy_plugin_identifier
        )
        raw_config = {} if persona is None else persona.policy_plugin_config
        plugin = cast(
            PersonaPolicyPlugin,
            self._plugin_instance(
                category=PluginCategory.PERSONA_POLICY,
                identifier=identifier,
                raw_config=raw_config,
            ),
        )
        return plugin.build_prompt(
            agent=agent,
            task_prompt=task_prompt,
            persona=persona,
            observations=observations,
            memory_context=memory_context,
        )

    def _world_or_404(self, world_id: uuid.UUID) -> World:
        world = self._session.get(World, world_id)
        if world is None:
            raise LookupError("World not found")
        return world

    def _worldline_id(self, world_id: uuid.UUID, worldline_id: uuid.UUID | None) -> uuid.UUID:
        if worldline_id is None:
            return ensure_primary_worldline(self._session, world_id).id
        worldline = self._session.get(Worldline, worldline_id)
        if worldline is None or worldline.world_id != world_id:
            raise LookupError("Worldline not found")
        return worldline.id

    def _plugin_instance(
        self,
        *,
        category: PluginCategory,
        identifier: str,
        raw_config: dict[str, Any],
    ) -> object:
        registry = get_builtin_plugin_registry()
        definition = registry.get(identifier)
        if definition.manifest.category is not category:
            raise RuntimeError(
                f"Plugin binding {identifier} does not match expected category {category.value}",
            )
        try:
            return registry.create(identifier, raw_config)
        except PluginNotFoundError as exc:
            raise RuntimeError(str(exc)) from exc
        except PluginConfigValidationError as exc:
            raise RuntimeError(str(exc)) from exc
        except PluginFactoryError as exc:
            raise RuntimeError(str(exc)) from exc

    def _append_event(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None = None,
        event_name: str,
        payload: dict[str, Any],
        actor_ref: str,
    ) -> Any:
        return WorldEventStore(self._session).append_event(
            WorldEventAppend(
                world_id=world_id,
                worldline_id=worldline_id,
                event_name=event_name,
                payload=payload,
                wall_time=datetime.now(UTC),
                actor_ref=actor_ref,
            ),
        )

    def _record_diagnostic(
        self,
        *,
        severity: DiagnosticSeverity,
        component: DiagnosticComponent,
        event_type: str,
        message: str,
        details: dict[str, Any],
        world_id: uuid.UUID,
        agent_id: uuid.UUID,
        run_id: uuid.UUID,
        provider_profile_id: uuid.UUID | None,
    ) -> None:
        RuntimeDiagnosticsService(self._session).record(
            RuntimeDiagnosticCreate(
                severity=severity,
                component=component,
                event_type=event_type,
                message=message,
                details=details,
                world_id=world_id,
                agent_id=agent_id,
                run_id=run_id,
                provider_profile_id=provider_profile_id,
            ),
        )


def _entries_by_agent(
    entries: list[CalendarEntryRecord],
) -> dict[uuid.UUID, list[CalendarEntryRecord]]:
    grouped: dict[uuid.UUID, list[CalendarEntryRecord]] = {}
    for entry in entries:
        grouped.setdefault(entry.agent_id, []).append(entry)
    return grouped


def _run_record(model: AgentRuntimeRun) -> AgentRunExecution:
    worldline_id = model.worldline_id
    if worldline_id is None:
        session = inspect_sqlalchemy(model).session
        if session is None:
            raise RuntimeError("Agent runtime run is detached and missing worldline_id")
        worldline_id = ensure_primary_worldline(session, model.world_id).id
    return AgentRunExecution(
        run_id=model.id,
        world_id=model.world_id,
        worldline_id=worldline_id,
        agent_id=model.agent_id,
        status=model.status,
        prompt_text=model.prompt_text,
        response_text=model.response_text,
        provider_profile_id=model.provider_profile_id,
        trigger_source=model.trigger_source,
        source_calendar_entry_id=model.source_calendar_entry_id,
        source_schedule_rule_id=model.source_schedule_rule_id,
        created_event_id=model.created_event_id,
        diagnostics=model.diagnostics,
        started_at=model.started_at,
        finished_at=model.finished_at,
    )


def _invocation_provider_kind(provider: _ResolvedRuntimeProvider) -> InvocationProviderKind:
    if provider.provider_integration is not None:
        return invocation_provider_kind_for_adapter(
            provider.provider_integration.provider_kind,
            provider.provider_integration.adapter_kind,
        )
    provider_profile = provider.legacy_profile
    if provider_profile is None:
        return InvocationProviderKind.OTHER
    try:
        return InvocationProviderKind(provider_profile.provider_type.value)
    except ValueError:
        return InvocationProviderKind.OTHER


def _runtime_provider_profile_id(provider: _ResolvedRuntimeProvider) -> uuid.UUID | None:
    return None if provider.legacy_profile is None else provider.legacy_profile.id


def _runtime_provider_metadata(provider: _ResolvedRuntimeProvider) -> dict[str, str]:
    if provider.provider_integration is not None:
        return {
            "provider_source": "provider_integration",
            "provider_integration_id": str(provider.provider_integration.id),
            "provider_key": provider.provider_integration.provider_key,
            "provider_kind": provider.provider_integration.provider_kind.value,
            "adapter_kind": provider.provider_integration.adapter_kind.value,
        }
    if provider.legacy_profile is not None:
        return {
            "provider_source": "legacy_profile",
            "provider_profile_id": str(provider.legacy_profile.id),
            "provider_key": provider.legacy_profile.profile_key,
            "provider_type": provider.legacy_profile.provider_type.value,
        }
    return {"provider_source": "unresolved"}


def _runtime_provider_prompt_json(provider: _ResolvedRuntimeProvider) -> dict[str, object]:
    if provider.provider_integration is not None:
        return {
            "provider_integration_id": str(provider.provider_integration.id),
            "provider_kind": provider.provider_integration.provider_kind.value,
            "adapter_kind": provider.provider_integration.adapter_kind.value,
            "model_name": provider.provider_integration.default_params_json.get("model")
            or provider.provider_integration.default_params_json.get("model_name"),
        }
    if provider.legacy_profile is not None:
        return {
            "provider_profile_id": str(provider.legacy_profile.id),
            "provider_type": provider.legacy_profile.provider_type.value,
            "model_name": provider.legacy_profile.model_name,
        }
    return {}


def _runtime_prompt_summary(prompt_text: str) -> str:
    normalized = " ".join(prompt_text.split())
    if len(normalized) <= 220:
        return normalized
    return f"{normalized[:217]}..."


def _contains_sensitive_context(prompt_context: dict[str, Any]) -> bool:
    living_context = prompt_context.get("living_context")
    living_context_pack = prompt_context.get("living_context_pack")
    return _has_positive_count(living_context, "visible_secret_count") or _has_positive_count(
        living_context_pack,
        "visible_secret_count",
    )


def _has_positive_count(value: object, key: str) -> bool:
    if not isinstance(value, dict):
        return False
    count = value.get(key)
    return isinstance(count, int) and count > 0


def _latency_ms(started_at: datetime) -> int:
    return max(0, int((datetime.now(UTC) - started_at).total_seconds() * 1000))


def _due_prompt(
    agent: Agent,
    world_time: datetime,
    due_entries: list[CalendarEntryRecord],
    due_rules: list[ScheduleRuleRecord],
) -> str:
    entry_titles = ", ".join(entry.title for entry in due_entries) or "no calendar entries"
    rule_names = ", ".join(rule.name for rule in due_rules) or "no active rules"
    return (
        f"World time: {world_time.isoformat()}. "
        f"Agent: {agent.display_name}. "
        f"Due calendar entries: {entry_titles}. "
        f"Matching schedule rules: {rule_names}. "
        "Respond with one concise operational update."
    )


def _memory_context_text(context: MemoryContext | None) -> str | None:
    if context is None:
        return None
    items = context.items
    profile_snapshot = context.profile_snapshot
    lines: list[str] = []
    if profile_snapshot is not None:
        if profile_snapshot.aliases:
            lines.append(f"Aliases: {', '.join(profile_snapshot.aliases)}")
        if profile_snapshot.identity_notes:
            lines.append("Identity notes:")
            lines.extend(f"- {item}" for item in profile_snapshot.identity_notes[:5])
        if profile_snapshot.durable_preferences:
            lines.append("Durable preferences:")
            lines.extend(f"- {item}" for item in profile_snapshot.durable_preferences[:5])
        if profile_snapshot.long_lived_goals:
            lines.append("Long-lived goals:")
            lines.extend(f"- {item}" for item in profile_snapshot.long_lived_goals[:5])
        if profile_snapshot.language_style_preferences:
            lines.append("Language/style preferences:")
            lines.extend(f"- {item}" for item in profile_snapshot.language_style_preferences[:5])
    if items:
        lines.append("Retrieved memory items:")
        for item in items:
            score = getattr(item, "score", None)
            prefix = "- " if score is None else f"- [{score:.3f}] "
            lines.append(f"{prefix}{item.content}")
    return None if not lines else "\n".join(lines)


def _join_prompt_contexts(*contexts: str | None) -> str | None:
    present = [context for context in contexts if context]
    if not present:
        return None
    return "\n\n".join(present)
