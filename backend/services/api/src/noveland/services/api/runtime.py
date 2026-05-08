from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import PlainTextResponse
from noveland.adapters import (
    ProviderConfigurationError,
    ProviderHealthStatus,
    ProviderInvocationResult,
    ProviderProfileCreate,
    ProviderProfileHealthRecord,
    ProviderProfileRecord,
    ProviderProfileService,
    ProviderProfileUpdate,
    ProviderSecretRefStatus,
    ProviderType,
)
from noveland.adapters.models import ProviderProfile
from noveland.agents.models import AgentPersona, AgentRuntimeRun
from noveland.auth import AuthenticatedSubject
from noveland.conversations.models import ConversationSession
from noveland.core.settings import load_settings
from noveland.events.models import WorldEventModel, WorldSnapshotModel
from noveland.memory import (
    MemoryBackendHealth,
    MemoryBackendKind,
    MemoryBackendProfileCreate,
    MemoryBackendProfileRecord,
    MemoryBackendProfileService,
    MemoryBackendProfileUpdate,
    MemoryBackfillDryRunResult,
    MemoryBackfillExecutionResult,
    MemoryBackfillSourceSummary,
    MemoryBackfillWorldSummary,
    MemoryEvalResult,
    MemoryQueueReadinessReport,
    MemoryRetrievalLogRecord,
    MemoryService,
    MemoryWriteJobRecord,
    MemoryWriteJobStatus,
    MemoryWriteJobStatusSummary,
    MemoryWriteLogRecord,
)
from noveland.memory.errors import MemoryValidationError
from noveland.memory.models import MemoryBackendProfile
from noveland.observability import (
    DiagnosticComponent,
    DiagnosticRetentionDryRun,
    DiagnosticRetentionPruneResult,
    DiagnosticSeverity,
    RuntimeDiagnosticCreate,
    RuntimeDiagnosticRecord,
    RuntimeDiagnosticsService,
)
from noveland.observability.models import RuntimeDiagnosticEvent
from noveland.plugins.builtins import get_builtin_plugin_registry
from noveland.plugins.categories import PluginCategory
from noveland.plugins.errors import (
    PluginConfigValidationError,
    PluginNotFoundError,
)
from noveland.plugins.manifest import PluginManifest
from noveland.services.api.csrf import require_csrf
from noveland.services.api.dependencies import (
    get_current_subject,
    get_db_session,
    get_platform_admin_subject,
)
from noveland.services.runtime.daemon import get_runtime_control_view, set_runtime_desired_state
from noveland.worlds.models import World
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

router = APIRouter(prefix="", tags=["runtime"])


class RuntimeControlResponse(BaseModel):
    desired_state: Literal["running", "stopped"]
    last_heartbeat_at: datetime | None
    last_run_started_at: datetime | None
    last_run_finished_at: datetime | None
    last_error: str | None


class MemoryWriteJobStatusSummaryResponse(BaseModel):
    pending_count: int
    processing_count: int
    succeeded_count: int
    failed_count: int
    due_count: int
    retryable_failed_count: int
    terminal_failed_count: int
    stalled_processing_count: int


class RuntimeHealthResponse(BaseModel):
    status: Literal["healthy", "stopped", "degraded", "failed"]
    reason: str
    recent_diagnostic_count: int
    recent_error_count: int
    heartbeat_age_seconds: int | None


class RuntimeStatusResponse(RuntimeControlResponse):
    runtime_loop_interval_seconds: int
    runtime_batch_limit: int
    memory_write_jobs: MemoryWriteJobStatusSummaryResponse
    runtime_health: RuntimeHealthResponse


class RuntimeSupervisionResponse(BaseModel):
    api_status: Literal["ok"]
    database_status: Literal["ok", "error"]
    desired_state: Literal["running", "stopped"]
    runtime_health: RuntimeHealthResponse
    runtime_process_expected: bool
    runtime_process_observed: bool
    heartbeat_stale: bool
    last_error: str | None


class ExternalToolPolicyResponse(BaseModel):
    policy_mode: Literal["policy_only"]
    execution_enabled: bool
    runtime_execution_enabled: bool
    supported_permission_modes: list[str]
    default_permission_mode: str
    deny_reasons: list[str]
    audit_fields: list[str]
    secret_handling: list[str]
    data_exposure_rules: list[str]
    operator_message: str


class ScaleReadinessSectionResponse(BaseModel):
    area: str
    status: Literal["ok", "watch", "blocked"]
    summary: str
    metrics: dict[str, int | bool | str | None]
    blockers: list[str]
    recommendations: list[str]


class ScaleReadinessResponse(BaseModel):
    status: Literal["ok", "watch", "blocked"]
    section_count: int
    blocker_count: int
    generated_at: datetime
    sections: list[ScaleReadinessSectionResponse]


class RuntimeControlUpdateRequest(BaseModel):
    desired_state: Literal["running", "stopped"]


class ProviderProfileCreateRequest(BaseModel):
    profile_key: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,78}[a-z0-9]$", max_length=80)
    name: str = Field(min_length=1, max_length=160)
    provider_type: ProviderType
    plugin_identifier: str | None = Field(default=None, min_length=1, max_length=120)
    plugin_config: dict[str, Any] = Field(default_factory=dict)
    base_url: str = Field(min_length=1, max_length=500)
    model_name: str = Field(min_length=1, max_length=200)
    capabilities: dict[str, Any] = Field(default_factory=dict)
    api_key_ref: str = Field(min_length=1, max_length=120)
    timeout_seconds: int = Field(default=20, ge=1, le=120)
    retry_attempts: int = Field(default=1, ge=0, le=5)
    rate_limit_per_minute: int | None = Field(default=None, ge=1, le=600)


class ProviderProfileUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    plugin_identifier: str | None = Field(default=None, min_length=1, max_length=120)
    plugin_config: dict[str, Any] | None = None
    base_url: str | None = Field(default=None, min_length=1, max_length=500)
    model_name: str | None = Field(default=None, min_length=1, max_length=200)
    capabilities: dict[str, Any] | None = None
    api_key_ref: str | None = Field(default=None, min_length=1, max_length=120)
    timeout_seconds: int | None = Field(default=None, ge=1, le=120)
    retry_attempts: int | None = Field(default=None, ge=0, le=5)
    rate_limit_per_minute: int | None = Field(default=None, ge=1, le=600)
    is_enabled: bool | None = None


class ProviderTestCallRequest(BaseModel):
    prompt: str = Field(default="Reply with OK.", min_length=1, max_length=1000)


class ProviderProfileResponse(BaseModel):
    id: uuid.UUID
    profile_key: str
    name: str
    provider_type: ProviderType
    plugin_identifier: str
    plugin_config: dict[str, Any]
    base_url: str
    model_name: str
    capabilities: dict[str, Any]
    api_key_ref: str
    timeout_seconds: int
    retry_attempts: int
    rate_limit_per_minute: int | None
    last_tested_at: datetime | None
    last_test_status: str | None
    last_test_error: str | None
    is_enabled: bool


class ProviderTestCallResponse(BaseModel):
    status: str
    latency_ms: int
    text_preview: str | None = None
    error_code: str | None = None
    error_message: str | None = None


class ProviderHealthResponse(BaseModel):
    id: uuid.UUID
    profile_key: str
    name: str
    provider_type: ProviderType
    is_enabled: bool
    health: ProviderHealthStatus
    api_key_ref: str
    secret_ref_status: ProviderSecretRefStatus
    secret_ref_message: str | None
    last_tested_at: datetime | None
    last_test_status: str | None
    last_test_error: str | None
    missing_secret_ref: bool
    recent_diagnostic_count: int
    recent_error_count: int


class MemoryBackendProfileCreateRequest(BaseModel):
    profile_key: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,78}[a-z0-9]$", max_length=80)
    name: str = Field(min_length=1, max_length=160)
    backend_kind: MemoryBackendKind
    vector_store_config: dict[str, Any] = Field(default_factory=dict)
    llm_config: dict[str, Any] = Field(default_factory=dict)
    embedder_config: dict[str, Any] = Field(default_factory=dict)
    reranker_config: dict[str, Any] = Field(default_factory=dict)
    secret_refs: dict[str, str] = Field(default_factory=dict)
    is_enabled: bool = True


class MemoryBackendProfileUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    vector_store_config: dict[str, Any] | None = None
    llm_config: dict[str, Any] | None = None
    embedder_config: dict[str, Any] | None = None
    reranker_config: dict[str, Any] | None = None
    secret_refs: dict[str, str] | None = None
    is_enabled: bool | None = None


class MemoryBackendProfileResponse(BaseModel):
    id: uuid.UUID
    profile_key: str
    name: str
    backend_kind: MemoryBackendKind
    vector_store_config: dict[str, Any]
    llm_config: dict[str, Any]
    embedder_config: dict[str, Any]
    reranker_config: dict[str, Any]
    secret_refs: dict[str, str]
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


class MemoryBackendHealthResponse(BaseModel):
    backend: str
    status: str
    details: dict[str, Any]


class MemoryWriteLogResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    backend: str
    success: bool
    latency_ms: int | None
    request_summary: dict[str, Any]
    response_summary: dict[str, Any]
    correlation_ids: dict[str, Any]
    occurred_at: datetime


class MemoryRetrievalLogResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None
    agent_id: uuid.UUID
    backend_profile_id: uuid.UUID | None
    backend: str
    query_text: str
    hit_count: int
    selected_item_ids: list[str]
    latency_ms: int | None
    context_item_count: int
    occurred_at: datetime


class MemoryBackendLogsResponse(BaseModel):
    write_logs: list[MemoryWriteLogResponse]
    retrieval_logs: list[MemoryRetrievalLogResponse]


class MemoryWriteJobResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None
    agent_id: uuid.UUID
    backend_profile_id: uuid.UUID
    backend_profile_key: str
    backend_profile_name: str
    backend_kind: MemoryBackendKind
    source_kind: str
    source_id: uuid.UUID
    dedupe_key: str
    status: MemoryWriteJobStatus
    attempt_count: int
    next_attempt_at: datetime
    last_error: str | None
    processed_at: datetime | None
    is_retryable: bool
    terminal_reason: str | None
    last_log_success: bool | None
    age_seconds: int
    created_at: datetime
    updated_at: datetime


class MemoryWriteJobListResponse(BaseModel):
    jobs: list[MemoryWriteJobResponse]


class MemoryBackfillSourceSummaryResponse(BaseModel):
    source_kind: str
    candidate_count: int
    skipped_existing_count: int
    skipped_no_profile_count: int
    skipped_disabled_profile_count: int


class MemoryBackfillWorldSummaryResponse(BaseModel):
    world_id: uuid.UUID
    backend_profile_id: uuid.UUID | None
    backend_profile_key: str | None
    candidate_count: int
    skipped_existing_count: int
    skipped_no_profile_count: int
    skipped_disabled_profile_count: int


class MemoryBackfillDryRunResponse(BaseModel):
    candidate_count: int
    skipped_existing_count: int
    skipped_no_profile_count: int
    skipped_disabled_profile_count: int
    source_summaries: list[MemoryBackfillSourceSummaryResponse]
    world_summaries: list[MemoryBackfillWorldSummaryResponse]


class MemoryBackfillExecutionResponse(BaseModel):
    enqueued_count: int
    skipped_existing_count: int
    skipped_no_profile_count: int
    skipped_disabled_profile_count: int
    batch_limit: int
    dry_run_before: MemoryBackfillDryRunResponse


class MemoryEvalCaseResponse(BaseModel):
    label: str
    query_text: str
    backend: str
    hit_count: int
    context_item_count: int
    latency_ms: int | None


class MemoryEvalResponse(BaseModel):
    backend: str
    case_count: int
    hit_case_count: int
    average_latency_ms: int | None
    average_context_items: float
    recommendations: list[str]
    cases: list[MemoryEvalCaseResponse]


class MemoryQueueReadinessResponse(BaseModel):
    status: str
    pending_count: int
    processing_count: int
    failed_count: int
    retryable_failed_count: int
    terminal_failed_count: int
    stalled_processing_count: int
    due_count: int
    max_attempts: int
    stalled_after_seconds: int
    external_queue_ready: bool
    issues: list[str]


class PluginCatalogResponse(BaseModel):
    identifier: str
    category: PluginCategory
    version: str
    config_schema: dict[str, Any]
    capabilities: tuple[str, ...]
    built_in: bool


class PluginBindingResponse(BaseModel):
    owner_kind: Literal[
        "provider_profile",
        "world_memory",
        "world_rules",
        "agent_persona",
        "conversation_writer",
    ]
    owner_id: uuid.UUID
    owner_key: str
    world_id: uuid.UUID | None
    agent_id: uuid.UUID | None
    conversation_id: uuid.UUID | None
    provider_profile_id: uuid.UUID | None
    plugin_identifier: str
    category: PluginCategory
    config_present: bool
    validation_status: Literal["ok", "missing_plugin", "category_mismatch", "invalid_config"]
    issue_message: str | None


class RuntimeDiagnosticResponse(BaseModel):
    id: uuid.UUID
    severity: DiagnosticSeverity
    component: DiagnosticComponent
    event_type: str
    message: str
    details: dict[str, Any]
    occurred_at: datetime
    world_id: uuid.UUID | None
    agent_id: uuid.UUID | None
    run_id: uuid.UUID | None
    provider_profile_id: uuid.UUID | None
    created_at: datetime


class DiagnosticRetentionResponse(BaseModel):
    retention_days: int
    cutoff: datetime
    pruneable_count: int
    retained_count: int
    pruned_count: int | None = None


@router.get("/runtime/control", response_model=RuntimeControlResponse)
def get_runtime_control(
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> RuntimeControlResponse:
    del subject
    return _runtime_control_response(get_runtime_control_view(db_session))


@router.patch("/runtime/control", response_model=RuntimeControlResponse)
def update_runtime_control(
    control_update: RuntimeControlUpdateRequest,
    request: Request,
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> RuntimeControlResponse:
    del subject
    require_csrf(request)
    return _runtime_control_response(
        set_runtime_desired_state(db_session, control_update.desired_state),
    )


@router.get("/runtime/status", response_model=RuntimeStatusResponse)
def get_runtime_status(
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> RuntimeStatusResponse:
    del subject
    settings = load_settings()
    view = get_runtime_control_view(db_session)
    memory_summary = MemoryService(db_session, settings).write_job_status_summary()
    runtime_health = _runtime_health_response(db_session, view, memory_summary, settings)
    return RuntimeStatusResponse(
        runtime_loop_interval_seconds=settings.runtime_loop_interval_seconds,
        runtime_batch_limit=settings.runtime_batch_limit,
        memory_write_jobs=_memory_write_job_status_summary_response(memory_summary),
        runtime_health=runtime_health,
        **_runtime_control_response(view).model_dump(),
    )


@router.get("/runtime/supervision", response_model=RuntimeSupervisionResponse)
def get_runtime_supervision(
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> RuntimeSupervisionResponse:
    del subject
    settings = load_settings()
    view = get_runtime_control_view(db_session)
    memory_summary = MemoryService(db_session, settings).write_job_status_summary()
    runtime_health = _runtime_health_response(db_session, view, memory_summary, settings)
    heartbeat_stale = (
        runtime_health.heartbeat_age_seconds is None
        or runtime_health.heartbeat_age_seconds > settings.runtime_loop_interval_seconds * 3
    )
    return RuntimeSupervisionResponse(
        api_status="ok",
        database_status="ok",
        desired_state=cast(Literal["running", "stopped"], view.desired_state),
        runtime_health=runtime_health,
        runtime_process_expected=view.desired_state == "running",
        runtime_process_observed=not heartbeat_stale,
        heartbeat_stale=heartbeat_stale,
        last_error=view.last_error,
    )


@router.get("/runtime/tool-policy", response_model=ExternalToolPolicyResponse)
def get_external_tool_policy(
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
) -> ExternalToolPolicyResponse:
    del subject
    return ExternalToolPolicyResponse(
        policy_mode="policy_only",
        execution_enabled=False,
        runtime_execution_enabled=False,
        supported_permission_modes=[
            "disabled",
            "allowlist_required",
            "denylist_block",
            "manual_approval_required",
        ],
        default_permission_mode="disabled",
        deny_reasons=[
            "external_tool_execution_disabled",
            "tool_not_allowlisted",
            "missing_world_or_actor_context",
            "secret_exposure_risk",
            "network_or_process_sandbox_unavailable",
        ],
        audit_fields=[
            "world_id",
            "agent_id",
            "actor_ref",
            "tool_identifier",
            "permission_mode",
            "decision",
            "deny_reason",
            "correlation_id",
        ],
        secret_handling=[
            "Secret values must never be persisted in tool policy responses.",
            "Future tool credentials must be referenced by secret ref only.",
            "Diagnostics must redact token, key, password, and authorization-like fields.",
        ],
        data_exposure_rules=[
            "Policy inputs must include world and runtime actor context.",
            (
                "Future tool outputs must be bounded and attributable before entering memory "
                "or events."
            ),
            "No subprocess, network, or filesystem tool execution is enabled in v1.",
        ],
        operator_message=(
            "External tool policy is defined for audit and future integration only; "
            "runtime tool execution is disabled."
        ),
    )


@router.get("/runtime/scale-readiness", response_model=ScaleReadinessResponse)
def get_scale_readiness(
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ScaleReadinessResponse:
    del subject
    return _scale_readiness_response(db_session)


@router.get("/metrics", response_class=PlainTextResponse)
def get_runtime_metrics(
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> PlainTextResponse:
    del subject
    settings = load_settings()
    view = get_runtime_control_view(db_session)
    memory_summary = MemoryService(db_session, settings).write_job_status_summary()
    runtime_health = _runtime_health_response(db_session, view, memory_summary, settings)
    provider_health = ProviderProfileService(db_session, settings).health_records(
        _provider_diagnostic_counts(db_session),
    )
    lines = _metrics_lines(
        view=view,
        memory_summary=memory_summary,
        runtime_health=runtime_health,
        provider_health=provider_health,
    )
    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")


@router.get("/runtime/diagnostics", response_model=list[RuntimeDiagnosticResponse])
def list_runtime_diagnostics(
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
    severity: DiagnosticSeverity | None = None,
    component: DiagnosticComponent | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[RuntimeDiagnosticResponse]:
    del subject
    return [
        _diagnostic_response(record)
        for record in RuntimeDiagnosticsService(db_session).list(
            severity=severity,
            component=component,
            limit=limit,
        )
    ]


@router.get(
    "/runtime/diagnostics/retention",
    response_model=DiagnosticRetentionResponse,
)
def dry_run_runtime_diagnostic_retention(
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
    retention_days: Annotated[int, Query(ge=1, le=3650)] = 30,
) -> DiagnosticRetentionResponse:
    del subject
    result = RuntimeDiagnosticsService(db_session).dry_run_retention(
        retention_days=retention_days,
    )
    return _diagnostic_retention_response(result)


@router.post(
    "/runtime/diagnostics/prune",
    response_model=DiagnosticRetentionResponse,
)
def prune_runtime_diagnostics(
    request: Request,
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
    retention_days: Annotated[int, Query(ge=1, le=3650)] = 30,
    limit: Annotated[int, Query(ge=1, le=10000)] = 1000,
) -> DiagnosticRetentionResponse:
    del subject
    require_csrf(request)
    result = RuntimeDiagnosticsService(db_session).prune_retention(
        retention_days=retention_days,
        limit=limit,
    )
    return _diagnostic_retention_response(result)


@router.get("/plugins/catalog", response_model=list[PluginCatalogResponse])
def list_plugin_catalog(
    _subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    category: PluginCategory | None = None,
) -> list[PluginCatalogResponse]:
    registry = get_builtin_plugin_registry()
    definitions = registry.all() if category is None else registry.list_by_category(category)
    return [_plugin_catalog_response(definition.manifest) for definition in definitions]


@router.get("/plugins/bindings", response_model=list[PluginBindingResponse])
def list_plugin_bindings(
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
    category: PluginCategory | None = None,
) -> list[PluginBindingResponse]:
    del subject
    bindings: list[PluginBindingResponse] = []
    for profile in db_session.scalars(
        select(ProviderProfile).order_by(ProviderProfile.profile_key),
    ):
        bindings.append(
            _plugin_binding_response(
                owner_kind="provider_profile",
                owner_id=profile.id,
                owner_key=profile.profile_key,
                world_id=None,
                agent_id=None,
                conversation_id=None,
                provider_profile_id=profile.id,
                plugin_identifier=profile.plugin_identifier,
                category=PluginCategory.MODEL_PROVIDER,
                raw_config=profile.plugin_config,
            )
        )
    for world in db_session.scalars(select(World).order_by(World.slug)):
        bindings.extend(
            [
                _plugin_binding_response(
                    owner_kind="world_memory",
                    owner_id=world.id,
                    owner_key=world.slug,
                    world_id=world.id,
                    agent_id=None,
                    conversation_id=None,
                    provider_profile_id=None,
                    plugin_identifier=world.memory_plugin_identifier,
                    category=PluginCategory.MEMORY_BACKEND,
                    raw_config=world.memory_plugin_config,
                ),
                _plugin_binding_response(
                    owner_kind="world_rules",
                    owner_id=world.id,
                    owner_key=world.slug,
                    world_id=world.id,
                    agent_id=None,
                    conversation_id=None,
                    provider_profile_id=None,
                    plugin_identifier=world.world_rules_plugin_identifier,
                    category=PluginCategory.WORLD_RULES,
                    raw_config=world.world_rules_plugin_config,
                ),
            ]
        )
    for persona in db_session.scalars(select(AgentPersona).order_by(AgentPersona.created_at)):
        bindings.append(
            _plugin_binding_response(
                owner_kind="agent_persona",
                owner_id=persona.id,
                owner_key=str(persona.agent_id),
                world_id=persona.world_id,
                agent_id=persona.agent_id,
                conversation_id=None,
                provider_profile_id=None,
                plugin_identifier=persona.policy_plugin_identifier,
                category=PluginCategory.PERSONA_POLICY,
                raw_config=persona.policy_plugin_config,
            )
        )
    for session in db_session.scalars(
        select(ConversationSession).order_by(ConversationSession.updated_at.desc()),
    ):
        writer_config = session.writer_config
        plugin_identifier = str(
            writer_config.get("writer_plugin_identifier", "builtin.default_narrative_writer"),
        )
        raw_config = writer_config.get("writer_plugin_config", {})
        bindings.append(
            _plugin_binding_response(
                owner_kind="conversation_writer",
                owner_id=session.id,
                owner_key=session.session_key,
                world_id=session.world_id,
                agent_id=None,
                conversation_id=session.id,
                provider_profile_id=None,
                plugin_identifier=plugin_identifier,
                category=PluginCategory.NARRATIVE_WRITER,
                raw_config=raw_config if isinstance(raw_config, dict) else {},
            )
        )
    if category is not None:
        bindings = [binding for binding in bindings if binding.category == category]
    return bindings


@router.get("/provider-profiles", response_model=list[ProviderProfileResponse])
def list_provider_profiles(
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[ProviderProfileResponse]:
    del subject
    service = ProviderProfileService(db_session, load_settings())
    return [_provider_profile_response(profile) for profile in service.list_profiles()]


@router.get("/provider-profiles/health", response_model=list[ProviderHealthResponse])
def list_provider_profile_health(
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[ProviderHealthResponse]:
    del subject
    settings = load_settings()
    service = ProviderProfileService(db_session, settings)
    counts = _provider_diagnostic_counts(db_session)
    return [_provider_health_response(record) for record in service.health_records(counts)]


@router.get("/memory-backend-profiles", response_model=list[MemoryBackendProfileResponse])
def list_memory_backend_profiles(
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[MemoryBackendProfileResponse]:
    del subject
    service = MemoryBackendProfileService(db_session)
    return [_memory_backend_profile_response(profile) for profile in service.list_profiles()]


@router.post(
    "/memory-backend-profiles",
    response_model=MemoryBackendProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_memory_backend_profile(
    profile_create: MemoryBackendProfileCreateRequest,
    request: Request,
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MemoryBackendProfileResponse:
    del subject
    require_csrf(request)
    try:
        profile = MemoryBackendProfileService(db_session).create_profile(
            MemoryBackendProfileCreate(
                profile_key=profile_create.profile_key,
                name=profile_create.name,
                backend_kind=profile_create.backend_kind,
                vector_store_config=profile_create.vector_store_config,
                llm_config=profile_create.llm_config,
                embedder_config=profile_create.embedder_config,
                reranker_config=profile_create.reranker_config,
                secret_refs=profile_create.secret_refs,
                is_enabled=profile_create.is_enabled,
            ),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except MemoryValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return _memory_backend_profile_response(profile)


@router.patch(
    "/memory-backend-profiles/{profile_id}",
    response_model=MemoryBackendProfileResponse,
)
def update_memory_backend_profile(
    profile_id: uuid.UUID,
    profile_update: MemoryBackendProfileUpdateRequest,
    request: Request,
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MemoryBackendProfileResponse:
    del subject
    require_csrf(request)
    service = MemoryBackendProfileService(db_session)
    model = db_session.get(MemoryBackendProfile, profile_id)
    if model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    try:
        profile = service.update_profile(
            model,
            MemoryBackendProfileUpdate(
                name=profile_update.name,
                vector_store_config=profile_update.vector_store_config,
                llm_config=profile_update.llm_config,
                embedder_config=profile_update.embedder_config,
                reranker_config=profile_update.reranker_config,
                secret_refs=profile_update.secret_refs,
                is_enabled=profile_update.is_enabled,
            ),
        )
        return _memory_backend_profile_response(profile)
    except MemoryValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


@router.delete(
    "/memory-backend-profiles/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_memory_backend_profile(
    profile_id: uuid.UUID,
    request: Request,
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> None:
    del subject
    require_csrf(request)
    model = db_session.get(MemoryBackendProfile, profile_id)
    if model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    MemoryBackendProfileService(db_session).delete_profile(model)


@router.get(
    "/memory-backend-profiles/{profile_id}/health",
    response_model=MemoryBackendHealthResponse,
)
def get_memory_backend_profile_health(
    profile_id: uuid.UUID,
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MemoryBackendHealthResponse:
    del subject
    try:
        health = MemoryService(db_session, load_settings()).profile_health(profile_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _memory_backend_health_response(health)


@router.get(
    "/memory-backend-profiles/{profile_id}/logs",
    response_model=MemoryBackendLogsResponse,
)
def get_memory_backend_profile_logs(
    profile_id: uuid.UUID,
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> MemoryBackendLogsResponse:
    del subject
    service = MemoryService(db_session, load_settings())
    if MemoryBackendProfileService(db_session).get_profile(profile_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return MemoryBackendLogsResponse(
        write_logs=[
            _memory_write_log_response(record)
            for record in service.list_write_logs(profile_id=profile_id, limit=limit)
        ],
        retrieval_logs=[
            _memory_retrieval_log_response(record)
            for record in service.list_retrieval_logs(profile_id=profile_id, limit=limit)
        ],
    )


@router.get(
    "/memory-backend-profiles/{profile_id}/jobs",
    response_model=MemoryWriteJobListResponse,
)
def list_memory_backend_profile_jobs(
    profile_id: uuid.UUID,
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
    status_filter: Annotated[
        MemoryWriteJobStatus | None,
        Query(alias="status"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> MemoryWriteJobListResponse:
    del subject
    service = MemoryService(db_session, load_settings())
    if MemoryBackendProfileService(db_session).get_profile(profile_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return MemoryWriteJobListResponse(
        jobs=[
            _memory_write_job_response(record)
            for record in service.list_write_jobs(
                profile_id=profile_id,
                status=status_filter,
                limit=limit,
            )
        ],
    )


@router.post(
    "/memory-write-jobs/{job_id}/retry",
    response_model=MemoryWriteJobResponse,
)
def retry_memory_write_job(
    job_id: uuid.UUID,
    request: Request,
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MemoryWriteJobResponse:
    del subject
    require_csrf(request)
    service = MemoryService(db_session, load_settings())
    try:
        job = service.retry_write_job(job_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MemoryValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    RuntimeDiagnosticsService(db_session).record(
        RuntimeDiagnosticCreate(
            severity=DiagnosticSeverity.INFO,
            component=DiagnosticComponent.RUNTIME,
            event_type="memory.write_job_retry_requested",
            message="Memory write job retry requested.",
            details={
                "job_id": str(job.id),
                "backend_profile_id": str(job.backend_profile_id),
                "backend_profile_key": job.backend_profile_key,
                "source_kind": job.source_kind.value,
                "source_id": str(job.source_id),
                "attempt_count": job.attempt_count,
            },
            world_id=job.world_id,
            agent_id=job.agent_id,
        ),
    )
    return _memory_write_job_response(job)


@router.get("/memory-backfill/dry-run", response_model=MemoryBackfillDryRunResponse)
def dry_run_memory_backfill(
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=2000)] = 500,
) -> MemoryBackfillDryRunResponse:
    del subject
    result = MemoryService(db_session, load_settings()).dry_run_backfill(limit=limit)
    return _memory_backfill_dry_run_response(result)


@router.post("/memory-backfill/execute", response_model=MemoryBackfillExecutionResponse)
def execute_memory_backfill(
    request: Request,
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> MemoryBackfillExecutionResponse:
    del subject
    require_csrf(request)
    service = MemoryService(db_session, load_settings())
    result = service.execute_backfill(limit=limit)
    RuntimeDiagnosticsService(db_session).record(
        RuntimeDiagnosticCreate(
            severity=DiagnosticSeverity.INFO,
            component=DiagnosticComponent.RUNTIME,
            event_type="memory.backfill_executed",
            message="Memory backfill execution enqueued jobs.",
            details={
                "enqueued_count": result.enqueued_count,
                "batch_limit": result.batch_limit,
                "candidate_count": result.dry_run_before.candidate_count,
            },
        ),
    )
    return _memory_backfill_execution_response(result)


@router.get("/memory-queue/readiness", response_model=MemoryQueueReadinessResponse)
def get_memory_queue_readiness(
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MemoryQueueReadinessResponse:
    del subject
    result = MemoryService(db_session, load_settings()).queue_readiness_report()
    return _memory_queue_readiness_response(result)


@router.post(
    "/memory-backend-profiles/{profile_id}/eval-smoke",
    response_model=MemoryEvalResponse,
)
def run_memory_backend_profile_eval_smoke(
    profile_id: uuid.UUID,
    request: Request,
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MemoryEvalResponse:
    del subject
    require_csrf(request)
    try:
        result = MemoryService(db_session, load_settings()).run_eval_smoke(profile_id=profile_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _memory_eval_response(result)


@router.post(
    "/provider-profiles",
    response_model=ProviderProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_provider_profile(
    profile_create: ProviderProfileCreateRequest,
    request: Request,
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ProviderProfileResponse:
    del subject
    require_csrf(request)
    try:
        profile = ProviderProfileService(db_session, load_settings()).create_profile(
            ProviderProfileCreate(
                profile_key=profile_create.profile_key,
                name=profile_create.name,
                provider_type=profile_create.provider_type,
                plugin_identifier=profile_create.plugin_identifier,
                plugin_config=profile_create.plugin_config,
                base_url=profile_create.base_url,
                model_name=profile_create.model_name,
                capabilities=profile_create.capabilities,
                api_key_ref=profile_create.api_key_ref,
                timeout_seconds=profile_create.timeout_seconds,
                retry_attempts=profile_create.retry_attempts,
                rate_limit_per_minute=profile_create.rate_limit_per_minute,
            ),
        )
    except PluginNotFoundError as exc:
        _record_plugin_binding_diagnostic(
            db_session,
            event_type="plugin.binding_missing",
            message="Provider plugin binding references an unregistered plugin.",
            plugin_identifier=profile_create.plugin_identifier,
            category=PluginCategory.MODEL_PROVIDER,
            owner_kind="provider_profile",
            owner_key=profile_create.profile_key,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PluginConfigValidationError as exc:
        _record_plugin_binding_diagnostic(
            db_session,
            event_type="plugin.binding_invalid_config",
            message="Provider plugin binding config failed validation.",
            plugin_identifier=profile_create.plugin_identifier,
            category=PluginCategory.MODEL_PROVIDER,
            owner_kind="provider_profile",
            owner_key=profile_create.profile_key,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except ProviderConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return _provider_profile_response(profile)


@router.patch("/provider-profiles/{profile_id}", response_model=ProviderProfileResponse)
def update_provider_profile(
    profile_id: uuid.UUID,
    profile_update: ProviderProfileUpdateRequest,
    request: Request,
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ProviderProfileResponse:
    del subject
    require_csrf(request)
    model = _provider_profile_or_404(db_session, profile_id)
    try:
        profile = ProviderProfileService(db_session, load_settings()).update_profile(
            model,
            ProviderProfileUpdate(
                name=profile_update.name,
                plugin_identifier=profile_update.plugin_identifier,
                plugin_config=profile_update.plugin_config,
                base_url=profile_update.base_url,
                model_name=profile_update.model_name,
                capabilities=profile_update.capabilities,
                api_key_ref=profile_update.api_key_ref,
                timeout_seconds=profile_update.timeout_seconds,
                retry_attempts=profile_update.retry_attempts,
                rate_limit_per_minute=profile_update.rate_limit_per_minute,
                is_enabled=profile_update.is_enabled,
            ),
        )
    except PluginNotFoundError as exc:
        _record_plugin_binding_diagnostic(
            db_session,
            event_type="plugin.binding_missing",
            message="Provider plugin binding references an unregistered plugin.",
            plugin_identifier=profile_update.plugin_identifier or model.plugin_identifier,
            category=PluginCategory.MODEL_PROVIDER,
            owner_kind="provider_profile",
            owner_key=model.profile_key,
            provider_profile_id=model.id,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PluginConfigValidationError as exc:
        _record_plugin_binding_diagnostic(
            db_session,
            event_type="plugin.binding_invalid_config",
            message="Provider plugin binding config failed validation.",
            plugin_identifier=profile_update.plugin_identifier or model.plugin_identifier,
            category=PluginCategory.MODEL_PROVIDER,
            owner_kind="provider_profile",
            owner_key=model.profile_key,
            provider_profile_id=model.id,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except ProviderConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return _provider_profile_response(profile)


@router.post(
    "/provider-profiles/{profile_id}/test-call",
    response_model=ProviderTestCallResponse,
)
def test_provider_profile(
    profile_id: uuid.UUID,
    test_request: ProviderTestCallRequest,
    request: Request,
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ProviderTestCallResponse:
    del subject
    require_csrf(request)
    model = _provider_profile_or_404(db_session, profile_id)
    result = ProviderProfileService(db_session, load_settings()).test_profile(
        model,
        test_request.prompt,
    )
    RuntimeDiagnosticsService(db_session).record(
        RuntimeDiagnosticCreate(
            severity=DiagnosticSeverity.INFO
            if result.status.value == "success"
            else DiagnosticSeverity.ERROR,
            component=DiagnosticComponent.PROVIDER,
            event_type="provider.test_call_completed",
            message="Provider test call completed.",
            details={
                "status": result.status.value,
                "latency_ms": result.latency_ms,
                "error_code": None if result.error_code is None else result.error_code.value,
                "error_message": result.error_message,
            },
            provider_profile_id=model.id,
        ),
    )
    return _provider_test_call_response(result)


@router.delete("/provider-profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def disable_provider_profile(
    profile_id: uuid.UUID,
    request: Request,
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> Response:
    del subject
    require_csrf(request)
    ProviderProfileService(db_session, load_settings()).disable_profile(
        _provider_profile_or_404(db_session, profile_id),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _provider_profile_or_404(db_session: Session, profile_id: uuid.UUID) -> ProviderProfile:
    profile = db_session.get(ProviderProfile, profile_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider profile not found",
        )
    return profile


def _provider_profile_response(profile: ProviderProfileRecord) -> ProviderProfileResponse:
    return ProviderProfileResponse(**profile.model_dump())


def _provider_health_response(record: ProviderProfileHealthRecord) -> ProviderHealthResponse:
    return ProviderHealthResponse(**record.model_dump())


def _memory_backend_profile_response(
    profile: MemoryBackendProfileRecord,
) -> MemoryBackendProfileResponse:
    return MemoryBackendProfileResponse(**profile.model_dump())


def _memory_backend_health_response(
    health: MemoryBackendHealth,
) -> MemoryBackendHealthResponse:
    return MemoryBackendHealthResponse(
        backend=health.backend,
        status=health.status.value,
        details=health.details,
    )


def _memory_write_log_response(record: MemoryWriteLogRecord) -> MemoryWriteLogResponse:
    return MemoryWriteLogResponse(**record.model_dump())


def _memory_write_job_response(record: MemoryWriteJobRecord) -> MemoryWriteJobResponse:
    return MemoryWriteJobResponse(**record.model_dump())


def _memory_write_job_status_summary_response(
    summary: MemoryWriteJobStatusSummary,
) -> MemoryWriteJobStatusSummaryResponse:
    return MemoryWriteJobStatusSummaryResponse(**summary.model_dump())


def _memory_backfill_dry_run_response(
    result: MemoryBackfillDryRunResult,
) -> MemoryBackfillDryRunResponse:
    return MemoryBackfillDryRunResponse(
        candidate_count=result.candidate_count,
        skipped_existing_count=result.skipped_existing_count,
        skipped_no_profile_count=result.skipped_no_profile_count,
        skipped_disabled_profile_count=result.skipped_disabled_profile_count,
        source_summaries=[
            _memory_backfill_source_summary_response(summary)
            for summary in result.source_summaries
        ],
        world_summaries=[
            _memory_backfill_world_summary_response(summary)
            for summary in result.world_summaries
        ],
    )


def _memory_backfill_execution_response(
    result: MemoryBackfillExecutionResult,
) -> MemoryBackfillExecutionResponse:
    return MemoryBackfillExecutionResponse(
        enqueued_count=result.enqueued_count,
        skipped_existing_count=result.skipped_existing_count,
        skipped_no_profile_count=result.skipped_no_profile_count,
        skipped_disabled_profile_count=result.skipped_disabled_profile_count,
        batch_limit=result.batch_limit,
        dry_run_before=_memory_backfill_dry_run_response(result.dry_run_before),
    )


def _memory_backfill_source_summary_response(
    summary: MemoryBackfillSourceSummary,
) -> MemoryBackfillSourceSummaryResponse:
    return MemoryBackfillSourceSummaryResponse(
        source_kind=summary.source_kind.value,
        candidate_count=summary.candidate_count,
        skipped_existing_count=summary.skipped_existing_count,
        skipped_no_profile_count=summary.skipped_no_profile_count,
        skipped_disabled_profile_count=summary.skipped_disabled_profile_count,
    )


def _memory_backfill_world_summary_response(
    summary: MemoryBackfillWorldSummary,
) -> MemoryBackfillWorldSummaryResponse:
    return MemoryBackfillWorldSummaryResponse(**summary.model_dump())


def _memory_retrieval_log_response(
    record: MemoryRetrievalLogRecord,
) -> MemoryRetrievalLogResponse:
    return MemoryRetrievalLogResponse(**record.model_dump())


def _memory_eval_response(result: MemoryEvalResult) -> MemoryEvalResponse:
    return MemoryEvalResponse(
        backend=result.backend,
        case_count=result.case_count,
        hit_case_count=result.hit_case_count,
        average_latency_ms=result.average_latency_ms,
        average_context_items=result.average_context_items,
        recommendations=result.recommendations,
        cases=[MemoryEvalCaseResponse(**case.model_dump()) for case in result.cases],
    )


def _memory_queue_readiness_response(
    result: MemoryQueueReadinessReport,
) -> MemoryQueueReadinessResponse:
    return MemoryQueueReadinessResponse(**result.model_dump())


def _provider_test_call_response(result: ProviderInvocationResult) -> ProviderTestCallResponse:
    return ProviderTestCallResponse(
        status=result.status.value,
        latency_ms=result.latency_ms,
        text_preview=result.text_preview,
        error_code=None if result.error_code is None else result.error_code.value,
        error_message=result.error_message,
    )


def _plugin_catalog_response(manifest: PluginManifest) -> PluginCatalogResponse:
    return PluginCatalogResponse(
        identifier=manifest.identifier,
        category=manifest.category,
        version=manifest.version,
        config_schema=manifest.config_schema,
        capabilities=manifest.capabilities,
        built_in=manifest.identifier.startswith("builtin."),
    )


def _plugin_binding_response(
    *,
    owner_kind: Literal[
        "provider_profile",
        "world_memory",
        "world_rules",
        "agent_persona",
        "conversation_writer",
    ],
    owner_id: uuid.UUID,
    owner_key: str,
    world_id: uuid.UUID | None,
    agent_id: uuid.UUID | None,
    conversation_id: uuid.UUID | None,
    provider_profile_id: uuid.UUID | None,
    plugin_identifier: str,
    category: PluginCategory,
    raw_config: dict[str, Any],
) -> PluginBindingResponse:
    validation_status, issue_message = _plugin_binding_validation_status(
        identifier=plugin_identifier,
        category=category,
        raw_config=raw_config,
    )
    return PluginBindingResponse(
        owner_kind=owner_kind,
        owner_id=owner_id,
        owner_key=owner_key,
        world_id=world_id,
        agent_id=agent_id,
        conversation_id=conversation_id,
        provider_profile_id=provider_profile_id,
        plugin_identifier=plugin_identifier,
        category=category,
        config_present=bool(raw_config),
        validation_status=validation_status,
        issue_message=issue_message,
    )


def _plugin_binding_validation_status(
    *,
    identifier: str,
    category: PluginCategory,
    raw_config: dict[str, Any],
) -> tuple[Literal["ok", "missing_plugin", "category_mismatch", "invalid_config"], str | None]:
    registry = get_builtin_plugin_registry()
    try:
        definition = registry.get(identifier)
    except PluginNotFoundError:
        return "missing_plugin", f"{identifier} is not registered."
    if definition.manifest.category is not category:
        return (
            "category_mismatch",
            (
                f"{identifier} is registered as {definition.manifest.category.value}, "
                f"not {category.value}."
            ),
        )
    try:
        registry.validate_config(identifier, raw_config)
    except PluginConfigValidationError:
        return "invalid_config", f"{identifier} config is invalid."
    return "ok", None


def _record_plugin_binding_diagnostic(
    db_session: Session,
    *,
    event_type: str,
    message: str,
    plugin_identifier: str | None,
    category: PluginCategory,
    owner_kind: str,
    owner_key: str,
    world_id: uuid.UUID | None = None,
    agent_id: uuid.UUID | None = None,
    provider_profile_id: uuid.UUID | None = None,
) -> None:
    RuntimeDiagnosticsService(db_session).record(
        RuntimeDiagnosticCreate(
            severity=DiagnosticSeverity.ERROR,
            component=DiagnosticComponent.PLUGIN,
            event_type=event_type,
            message=message,
            details={
                "plugin_identifier": plugin_identifier,
                "category": category.value,
                "owner_kind": owner_kind,
                "owner_key": owner_key,
            },
            world_id=world_id,
            agent_id=agent_id,
            provider_profile_id=provider_profile_id,
        ),
    )
    db_session.commit()


def _runtime_control_response(view: Any) -> RuntimeControlResponse:
    return RuntimeControlResponse(
        desired_state=view.desired_state,
        last_heartbeat_at=view.last_heartbeat_at,
        last_run_started_at=view.last_run_started_at,
        last_run_finished_at=view.last_run_finished_at,
        last_error=view.last_error,
    )


def _runtime_health_response(
    db_session: Session,
    view: Any,
    memory_summary: MemoryWriteJobStatusSummary,
    settings: Any,
) -> RuntimeHealthResponse:
    recent_diagnostic_count, recent_error_count = _runtime_diagnostic_counts(db_session)
    heartbeat_age_seconds: int | None = None
    if view.last_heartbeat_at is not None:
        heartbeat_age_seconds = max(
            0,
            int((datetime.now(UTC) - _aware_datetime(view.last_heartbeat_at)).total_seconds()),
        )
    if view.desired_state == "stopped":
        status_value: Literal["healthy", "stopped", "degraded", "failed"] = "stopped"
        reason = "Runtime desired state is stopped."
    elif view.last_error is not None:
        status_value = "failed"
        reason = view.last_error
    elif heartbeat_age_seconds is None:
        status_value = "degraded"
        reason = "Runtime has not recorded a heartbeat."
    elif heartbeat_age_seconds > settings.runtime_loop_interval_seconds * 3:
        status_value = "degraded"
        reason = "Runtime heartbeat is stale."
    elif recent_error_count > 0:
        status_value = "degraded"
        reason = "Recent runtime errors were recorded."
    elif memory_summary.terminal_failed_count > 0 or memory_summary.stalled_processing_count > 0:
        status_value = "degraded"
        reason = "Memory queue has terminal failures or stalled jobs."
    else:
        status_value = "healthy"
        reason = "Runtime is running without recent blocking errors."
    return RuntimeHealthResponse(
        status=status_value,
        reason=reason,
        recent_diagnostic_count=recent_diagnostic_count,
        recent_error_count=recent_error_count,
        heartbeat_age_seconds=heartbeat_age_seconds,
    )


def _scale_readiness_response(db_session: Session) -> ScaleReadinessResponse:
    memory_summary = MemoryService(db_session, load_settings()).write_job_status_summary()
    provider_records = ProviderProfileService(
        db_session,
        load_settings(),
    ).health_records(_provider_diagnostic_counts(db_session))

    sections = [
        _database_scale_section(db_session),
        _realtime_scale_section(db_session),
        _memory_queue_scale_section(memory_summary),
        _provider_limit_scale_section(db_session, provider_records),
        _diagnostics_growth_scale_section(db_session),
        _snapshot_storage_scale_section(db_session),
    ]
    blocker_count = sum(len(section.blockers) for section in sections)
    if blocker_count > 0:
        status_value: Literal["ok", "watch", "blocked"] = "blocked"
    elif any(section.status == "watch" for section in sections):
        status_value = "watch"
    else:
        status_value = "ok"
    return ScaleReadinessResponse(
        status=status_value,
        section_count=len(sections),
        blocker_count=blocker_count,
        generated_at=datetime.now(UTC),
        sections=sections,
    )


def _database_scale_section(db_session: Session) -> ScaleReadinessSectionResponse:
    world_count = _table_count(db_session, World)
    event_count = _table_count(db_session, WorldEventModel)
    run_count = _table_count(db_session, AgentRuntimeRun)
    blockers: list[str] = []
    recommendations = [
        "Review query plans before multi-world fanout or high-volume event replay.",
        "Keep Alembic migration safety checks in the release gate.",
    ]
    status_value: Literal["ok", "watch", "blocked"] = "ok"
    if event_count > 10000 or run_count > 5000:
        status_value = "watch"
        recommendations.append("Add explicit index review for event/run listing hot paths.")
    return ScaleReadinessSectionResponse(
        area="database_indexes",
        status=status_value,
        summary="Core operational tables are available for derived scale review.",
        metrics={
            "world_count": world_count,
            "event_count": event_count,
            "agent_runtime_run_count": run_count,
        },
        blockers=blockers,
        recommendations=recommendations,
    )


def _realtime_scale_section(db_session: Session) -> ScaleReadinessSectionResponse:
    world_count = _table_count(db_session, World)
    active_world_count = int(
        db_session.scalar(select(func.count(World.id)).where(World.is_active.is_(True))) or 0,
    )
    status_value: Literal["ok", "watch", "blocked"] = "ok"
    blockers: list[str] = []
    recommendations = [
        "Keep SSE fanout scoped by world/runtime stream before adding many concurrent readers.",
    ]
    if active_world_count > 25:
        status_value = "watch"
        recommendations.append("Measure NATS/SSE fanout under active-world concurrency.")
    return ScaleReadinessSectionResponse(
        area="realtime_fanout",
        status=status_value,
        summary="Realtime remains single transport via existing SSE/proxy infrastructure.",
        metrics={
            "world_count": world_count,
            "active_world_count": active_world_count,
        },
        blockers=blockers,
        recommendations=recommendations,
    )


def _memory_queue_scale_section(
    memory_summary: MemoryWriteJobStatusSummary,
) -> ScaleReadinessSectionResponse:
    blockers: list[str] = []
    recommendations = [
        "Keep DB-backed queue until retryability, stalled jobs, and throughput stay healthy.",
    ]
    status_value: Literal["ok", "watch", "blocked"] = "ok"
    if memory_summary.terminal_failed_count > 0 or memory_summary.stalled_processing_count > 0:
        status_value = "blocked"
        blockers.append("Memory queue has terminal failed or stalled processing jobs.")
    elif memory_summary.failed_count > 0 or memory_summary.due_count > 100:
        status_value = "watch"
        recommendations.append("Drain failed/due jobs before scale testing.")
    return ScaleReadinessSectionResponse(
        area="memory_queue_throughput",
        status=status_value,
        summary="Memory writes continue through the database-backed queue.",
        metrics={
            "pending_count": memory_summary.pending_count,
            "processing_count": memory_summary.processing_count,
            "failed_count": memory_summary.failed_count,
            "due_count": memory_summary.due_count,
            "retryable_failed_count": memory_summary.retryable_failed_count,
            "terminal_failed_count": memory_summary.terminal_failed_count,
            "stalled_processing_count": memory_summary.stalled_processing_count,
        },
        blockers=blockers,
        recommendations=recommendations,
    )


def _provider_limit_scale_section(
    db_session: Session,
    provider_records: list[ProviderProfileHealthRecord],
) -> ScaleReadinessSectionResponse:
    missing_rate_limit_count = int(
        db_session.scalar(
            select(func.count(ProviderProfile.id)).where(
                ProviderProfile.is_enabled.is_(True),
                ProviderProfile.rate_limit_per_minute.is_(None),
            ),
        )
        or 0,
    )
    unhealthy_count = sum(
        1
        for record in provider_records
        if record.is_enabled and record.health.value in {"configuration_error", "degraded"}
    )
    blockers: list[str] = []
    recommendations = [
        "Set per-profile rate limits before concurrent multi-world runtime tests.",
    ]
    status_value: Literal["ok", "watch", "blocked"] = "ok"
    if unhealthy_count > 0:
        status_value = "blocked"
        blockers.append(
            "Enabled provider profiles include configuration errors or degraded health.",
        )
    elif missing_rate_limit_count > 0:
        status_value = "watch"
    return ScaleReadinessSectionResponse(
        area="provider_limits",
        status=status_value,
        summary="Provider readiness is derived from profile health and configured rate limits.",
        metrics={
            "provider_profile_count": len(provider_records),
            "enabled_profile_count": sum(1 for record in provider_records if record.is_enabled),
            "missing_rate_limit_count": missing_rate_limit_count,
            "unhealthy_enabled_profile_count": unhealthy_count,
        },
        blockers=blockers,
        recommendations=recommendations,
    )


def _diagnostics_growth_scale_section(db_session: Session) -> ScaleReadinessSectionResponse:
    diagnostic_count = _table_count(db_session, RuntimeDiagnosticEvent)
    old_count = int(
        db_session.scalar(
            select(func.count(RuntimeDiagnosticEvent.id)).where(
                RuntimeDiagnosticEvent.occurred_at < datetime.now(UTC) - timedelta(days=30),
            ),
        )
        or 0,
    )
    status_value: Literal["ok", "watch", "blocked"] = "ok"
    recommendations = [
        "Use diagnostic retention dry-run before pruning incident evidence.",
    ]
    if old_count > 0 or diagnostic_count > 10000:
        status_value = "watch"
        recommendations.append("Apply the diagnostic retention playbook before growth testing.")
    return ScaleReadinessSectionResponse(
        area="diagnostics_growth",
        status=status_value,
        summary="Diagnostic retention is available but operator-triggered.",
        metrics={
            "diagnostic_count": diagnostic_count,
            "older_than_30_days_count": old_count,
        },
        blockers=[],
        recommendations=recommendations,
    )


def _snapshot_storage_scale_section(db_session: Session) -> ScaleReadinessSectionResponse:
    snapshot_count = _table_count(db_session, WorldSnapshotModel)
    uri_snapshot_count = int(
        db_session.scalar(
            select(func.count(WorldSnapshotModel.id)).where(
                WorldSnapshotModel.payload_uri.is_not(None),
            ),
        )
        or 0,
    )
    inline_snapshot_count = snapshot_count - uri_snapshot_count
    status_value: Literal["ok", "watch", "blocked"] = "ok"
    recommendations = [
        "Keep object-storage backup verification in the deployment checklist.",
    ]
    if inline_snapshot_count > 0:
        status_value = "watch"
        recommendations.append("Legacy inline snapshots remain readable but should be monitored.")
    return ScaleReadinessSectionResponse(
        area="snapshot_storage",
        status=status_value,
        summary="New snapshots can use object storage while old inline snapshots remain readable.",
        metrics={
            "snapshot_count": snapshot_count,
            "uri_snapshot_count": uri_snapshot_count,
            "inline_snapshot_count": inline_snapshot_count,
        },
        blockers=[],
        recommendations=recommendations,
    )


def _table_count(db_session: Session, model: Any) -> int:
    return int(db_session.scalar(select(func.count(model.id))) or 0)


def _metrics_lines(
    *,
    view: Any,
    memory_summary: MemoryWriteJobStatusSummary,
    runtime_health: RuntimeHealthResponse,
    provider_health: list[ProviderProfileHealthRecord],
) -> list[str]:
    status_values = ("healthy", "stopped", "degraded", "failed")
    lines = [
        "# HELP noveland_runtime_desired_state Runtime desired state as 1 for running.",
        "# TYPE noveland_runtime_desired_state gauge",
        f"noveland_runtime_desired_state {_bool_metric(view.desired_state == 'running')}",
        "# HELP noveland_runtime_health Runtime health by state.",
        "# TYPE noveland_runtime_health gauge",
        *[
            (
                f'noveland_runtime_health{{status="{status_value}"}} '
                f"{_bool_metric(runtime_health.status == status_value)}"
            )
            for status_value in status_values
        ],
        "# HELP noveland_runtime_recent_errors Recent runtime error diagnostics.",
        "# TYPE noveland_runtime_recent_errors gauge",
        f"noveland_runtime_recent_errors {runtime_health.recent_error_count}",
        "# HELP noveland_memory_write_jobs Memory write jobs by status.",
        "# TYPE noveland_memory_write_jobs gauge",
        f'noveland_memory_write_jobs{{status="pending"}} {memory_summary.pending_count}',
        f'noveland_memory_write_jobs{{status="processing"}} {memory_summary.processing_count}',
        f'noveland_memory_write_jobs{{status="succeeded"}} {memory_summary.succeeded_count}',
        f'noveland_memory_write_jobs{{status="failed"}} {memory_summary.failed_count}',
        (
            'noveland_memory_write_jobs{status="retryable_failed"} '
            f"{memory_summary.retryable_failed_count}"
        ),
        (
            'noveland_memory_write_jobs{status="terminal_failed"} '
            f"{memory_summary.terminal_failed_count}"
        ),
        (
            'noveland_memory_write_jobs{status="stalled_processing"} '
            f"{memory_summary.stalled_processing_count}"
        ),
        "# HELP noveland_provider_profiles Provider profiles by derived health.",
        "# TYPE noveland_provider_profiles gauge",
    ]
    provider_counts: dict[str, int] = {}
    for record in provider_health:
        provider_counts[record.health.value] = provider_counts.get(record.health.value, 0) + 1
    for health_value in ("ok", "untested", "configuration_error", "degraded", "disabled"):
        lines.append(
            f'noveland_provider_profiles{{health="{health_value}"}} '
            f"{provider_counts.get(health_value, 0)}",
        )
    return lines


def _bool_metric(value: bool) -> int:
    return 1 if value else 0


def _runtime_diagnostic_counts(db_session: Session) -> tuple[int, int]:
    since = datetime.now(UTC) - timedelta(hours=1)
    rows = db_session.execute(
        select(RuntimeDiagnosticEvent.severity, func.count(RuntimeDiagnosticEvent.id))
        .where(
            RuntimeDiagnosticEvent.component == DiagnosticComponent.RUNTIME.value,
            RuntimeDiagnosticEvent.occurred_at >= since,
        )
        .group_by(RuntimeDiagnosticEvent.severity),
    ).all()
    counts = {str(severity): int(count) for severity, count in rows}
    return sum(counts.values()), counts.get(DiagnosticSeverity.ERROR.value, 0)


def _provider_diagnostic_counts(db_session: Session) -> dict[uuid.UUID, tuple[int, int]]:
    since = datetime.now(UTC) - timedelta(hours=24)
    rows = db_session.execute(
        select(
            RuntimeDiagnosticEvent.provider_profile_id,
            RuntimeDiagnosticEvent.severity,
            func.count(RuntimeDiagnosticEvent.id),
        )
        .where(
            RuntimeDiagnosticEvent.component == DiagnosticComponent.PROVIDER.value,
            RuntimeDiagnosticEvent.provider_profile_id.is_not(None),
            RuntimeDiagnosticEvent.occurred_at >= since,
        )
        .group_by(RuntimeDiagnosticEvent.provider_profile_id, RuntimeDiagnosticEvent.severity),
    ).all()
    totals: dict[uuid.UUID, list[int]] = {}
    for profile_id, severity, count in rows:
        if profile_id is None:
            continue
        bucket = totals.setdefault(profile_id, [0, 0])
        bucket[0] += int(count)
        if severity == DiagnosticSeverity.ERROR.value:
            bucket[1] += int(count)
    return {profile_id: (counts[0], counts[1]) for profile_id, counts in totals.items()}


def _aware_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _diagnostic_response(record: RuntimeDiagnosticRecord) -> RuntimeDiagnosticResponse:
    return RuntimeDiagnosticResponse(**record.model_dump())


def _diagnostic_retention_response(
    result: DiagnosticRetentionDryRun | DiagnosticRetentionPruneResult,
) -> DiagnosticRetentionResponse:
    pruned_count = (
        result.pruned_count if isinstance(result, DiagnosticRetentionPruneResult) else None
    )
    return DiagnosticRetentionResponse(
        retention_days=result.retention_days,
        cutoff=result.cutoff,
        pruneable_count=result.pruneable_count,
        retained_count=result.retained_count,
        pruned_count=pruned_count,
    )
