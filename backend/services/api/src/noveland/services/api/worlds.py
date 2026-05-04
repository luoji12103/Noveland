from __future__ import annotations

import re
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from noveland.adapters import ProviderProfileService
from noveland.adapters.models import ProviderProfile
from noveland.agents import (
    AgentObservationCreate,
    AgentObservationRecord,
    AgentObservationService,
    AgentPersonaRecord,
    AgentPersonaService,
    AgentPersonaUpsert,
    AgentPresetCalendarEntry,
    AgentPresetRecord,
    AgentPresetService,
    AgentPresetUpsert,
)
from noveland.agents.models import Agent, AgentPreset
from noveland.auth import AuthenticatedSubject, AuthRole
from noveland.auth.models import User
from noveland.calendar import (
    CalendarConflictRecord,
    CalendarConflictReport,
    CalendarConflictSource,
    CalendarEntryCreate,
    CalendarEntryStatus,
    CalendarEntryUpdate,
    CalendarService,
    ScheduleRuleCreate,
    ScheduleRuleKind,
    ScheduleRulePreviewResult,
    ScheduleRuleUpdate,
)
from noveland.calendar.models import AgentCalendarEntry, WorldScheduleRule
from noveland.conversations.models import ConversationTurn
from noveland.core.settings import load_settings
from noveland.events import (
    WorldReplayService,
    WorldReplayState,
    WorldSnapshotIntegrityReport,
    WorldSnapshotRecord,
)
from noveland.events.models import WorldEventModel
from noveland.memory import (
    MemoryBackendProfileService,
    MemoryDeleteScope,
    MemoryItemRecord,
    MemoryProfileSnapshotRecord,
    MemoryService,
)
from noveland.memory import (
    MemorySearchRequest as MemoryLookupRequest,
)
from noveland.memory.models import MemoryBackendProfile
from noveland.narrative import (
    NarrativeArtifactKind,
    NarrativeArtifactNotFoundError,
    NarrativeArtifactRecord,
    NarrativeArtifactService,
    NarrativeArtifactWithPublication,
    NarrativePublicationNotFoundError,
    NarrativePublicationRecord,
)
from noveland.observability import (
    DiagnosticComponent,
    DiagnosticSeverity,
    RuntimeDiagnosticRecord,
    RuntimeDiagnosticsService,
    redact_diagnostic_details,
)
from noveland.plugins.builtins import get_builtin_plugin_registry
from noveland.plugins.categories import PluginCategory
from noveland.plugins.constants import (
    BUILTIN_DEFAULT_PERSONA_POLICY,
    BUILTIN_DEFAULT_WORLD_RULES,
    BUILTIN_MEM0_OSS_MEMORY,
)
from noveland.plugins.errors import (
    PluginConfigValidationError,
    PluginNotFoundError,
)
from noveland.services.api.authorization import is_platform_admin
from noveland.services.api.csrf import require_csrf
from noveland.services.api.dependencies import (
    WorldAccessContext,
    get_current_subject,
    get_db_session,
    get_platform_admin_subject,
    get_world_admin_context,
    get_world_member_context,
)
from noveland.services.runtime import AgentRunExecution, AgentRuntimeOrchestrator
from noveland.worlds.clock import WorldClockError
from noveland.worlds.clock_service import WorldClockService, WorldClockView
from noveland.worlds.models import Scene, World, WorldClockTransitionModel, WorldMembership
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

SLUG_PATTERN = r"^[a-z0-9][a-z0-9-]{1,78}[a-z0-9]$"
SLUG_RE = re.compile(SLUG_PATTERN)

WorldRole = Literal["world_admin", "human_user"]
AgentKind = Literal["role_agent", "narrative_agent"]

router = APIRouter(prefix="/worlds", tags=["worlds"])
root_router = APIRouter(tags=["worlds"])


class _RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WorldCreateRequest(_RequestModel):
    slug: str = Field(pattern=SLUG_PATTERN, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    rules_config: dict[str, Any] = Field(default_factory=dict)
    memory_plugin_identifier: str = Field(
        default=BUILTIN_MEM0_OSS_MEMORY,
        min_length=1,
        max_length=120,
    )
    memory_backend_profile_id: uuid.UUID | None = None
    memory_plugin_config: dict[str, Any] = Field(default_factory=dict)
    world_rules_plugin_identifier: str = Field(
        default=BUILTIN_DEFAULT_WORLD_RULES,
        min_length=1,
        max_length=120,
    )
    world_rules_plugin_config: dict[str, Any] = Field(default_factory=dict)


class WorldUpdateRequest(_RequestModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    rules_config: dict[str, Any] | None = None
    memory_plugin_identifier: str | None = Field(default=None, min_length=1, max_length=120)
    memory_backend_profile_id: uuid.UUID | None = None
    memory_plugin_config: dict[str, Any] | None = None
    world_rules_plugin_identifier: str | None = Field(default=None, min_length=1, max_length=120)
    world_rules_plugin_config: dict[str, Any] | None = None
    is_active: bool | None = None


class SceneCreateRequest(_RequestModel):
    scene_key: str = Field(pattern=SLUG_PATTERN, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None


class SceneUpdateRequest(_RequestModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    is_active: bool | None = None


class MembershipUpsertRequest(_RequestModel):
    user_id: uuid.UUID
    role: WorldRole


class AgentCreateRequest(_RequestModel):
    agent_key: str = Field(pattern=SLUG_PATTERN, max_length=80)
    display_name: str = Field(min_length=1, max_length=120)
    kind: AgentKind | None = None
    home_scene_id: uuid.UUID | None = None
    preset_id: uuid.UUID | None = None
    provider_profile_id: uuid.UUID | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class AgentUpdateRequest(_RequestModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    kind: AgentKind | None = None
    home_scene_id: uuid.UUID | None = None
    provider_profile_id: uuid.UUID | None = None
    config: dict[str, Any] | None = None
    is_enabled: bool | None = None


class CalendarEntryCreateRequest(_RequestModel):
    title: str = Field(min_length=1, max_length=160)
    description: str | None = None
    starts_at: datetime
    ends_at: datetime | None = None
    recurrence_rule: str | None = Field(default=None, max_length=240)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("starts_at", "ends_at", mode="after")
    @classmethod
    def calendar_times_must_be_timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return _timezone_aware(value, "calendar time")


class CalendarEntryUpdateRequest(_RequestModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    recurrence_rule: str | None = Field(default=None, max_length=240)
    status: Literal["active", "cancelled"] | None = None
    metadata: dict[str, Any] | None = None

    @field_validator("starts_at", "ends_at", mode="after")
    @classmethod
    def calendar_times_must_be_timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return _timezone_aware(value, "calendar time")


class ScheduleRuleCreateRequest(_RequestModel):
    rule_key: str = Field(pattern=SLUG_PATTERN, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    kind: Literal["weekday", "weekend", "timetable"]
    config: dict[str, Any] = Field(default_factory=dict)


class ScheduleRuleUpdateRequest(_RequestModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    kind: Literal["weekday", "weekend", "timetable"] | None = None
    config: dict[str, Any] | None = None
    is_enabled: bool | None = None


class ScheduleRulePreviewRequest(_RequestModel):
    kind: Literal["weekday", "weekend", "timetable"]
    config: dict[str, Any] = Field(default_factory=dict)
    start_world_time: datetime | None = None
    horizon_hours: int = Field(default=48, ge=1, le=168)
    limit: int = Field(default=10, ge=1, le=50)

    @field_validator("start_world_time", mode="after")
    @classmethod
    def start_world_time_must_be_timezone_aware(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is None:
            return None
        return _timezone_aware(value, "start_world_time")


class MemorySearchRequest(_RequestModel):
    query_text: str = Field(min_length=1, max_length=8_000)
    limit: int = Field(default=10, ge=1, le=50)


class AgentRunRequest(_RequestModel):
    prompt: str | None = None
    provider_profile_id: uuid.UUID | None = None
    create_memory: bool = True
    create_narrative_artifact: bool = True


class AgentPersonaUpdateRequest(_RequestModel):
    persona_text: str = Field(default="", max_length=12_000)
    behavior_policy: dict[str, Any] = Field(default_factory=dict)
    policy_plugin_identifier: str = Field(
        default=BUILTIN_DEFAULT_PERSONA_POLICY,
        min_length=1,
        max_length=120,
    )
    policy_plugin_config: dict[str, Any] = Field(default_factory=dict)
    is_enabled: bool = True


class PersonaPolicyValidationIssue(BaseModel):
    field: str
    message: str


class PersonaPolicyValidationResponse(BaseModel):
    valid: bool
    issues: list[PersonaPolicyValidationIssue]


class AgentObservationCreateRequest(_RequestModel):
    observation_type: str = Field(default="manual", min_length=1, max_length=80)
    content: str = Field(min_length=1, max_length=12_000)
    metadata: dict[str, Any] = Field(default_factory=dict)
    observed_at: datetime | None = None
    confidence_score: float | None = Field(default=None, ge=0, le=1)
    review_status: Literal["unreviewed", "approved", "rejected"] = "unreviewed"

    @field_validator("observed_at", mode="after")
    @classmethod
    def observed_at_must_be_timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return _timezone_aware(value, "observed_at")


class NarrativeArtifactCreateRequest(_RequestModel):
    title: str = Field(min_length=1, max_length=160)
    content: str = Field(min_length=1)
    artifact_kind: Literal["agent_note", "world_summary"] = "world_summary"
    agent_id: uuid.UUID | None = None


class NarrativePublicationRequest(_RequestModel):
    reader_visible: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClockTransitionRequest(_RequestModel):
    reason: str | None = Field(default=None, max_length=500)


class ClockResumeRequest(ClockTransitionRequest):
    speed_multiplier: Decimal | None = Field(default=None, gt=0)


class ClockSkipRequest(ClockTransitionRequest):
    target_world_time: datetime

    @field_validator("target_world_time", mode="after")
    @classmethod
    def target_world_time_must_be_timezone_aware(cls, value: datetime) -> datetime:
        return _timezone_aware(value, "target_world_time")


class WorldResponse(BaseModel):
    id: uuid.UUID
    owner_user_id: uuid.UUID
    slug: str
    name: str
    description: str | None
    rules_config: dict[str, Any]
    memory_plugin_identifier: str
    memory_backend_profile_id: uuid.UUID | None
    memory_plugin_config: dict[str, Any]
    world_rules_plugin_identifier: str
    world_rules_plugin_config: dict[str, Any]
    is_active: bool


class SceneResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    scene_key: str
    name: str
    description: str | None
    is_active: bool


class UserSummaryResponse(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    is_active: bool


class MemberCandidateResponse(UserSummaryResponse):
    role: WorldRole | None = None


class MembershipResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    user_id: uuid.UUID
    role: WorldRole
    user: UserSummaryResponse


class AgentResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    home_scene_id: uuid.UUID | None
    source_preset_id: uuid.UUID | None
    source_preset_version: int | None
    agent_key: str
    display_name: str
    kind: AgentKind
    provider_profile_id: uuid.UUID | None
    config: dict[str, Any]
    is_enabled: bool


class AgentPresetCalendarEntryRequest(_RequestModel):
    title: str = Field(min_length=1, max_length=160)
    description: str | None = None
    starts_at: datetime
    ends_at: datetime | None = None
    recurrence_rule: str | None = Field(default=None, max_length=240)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("starts_at", "ends_at", mode="after")
    @classmethod
    def preset_calendar_times_must_be_timezone_aware(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is None:
            return None
        return _timezone_aware(value, "preset calendar time")


class AgentPresetCreateRequest(_RequestModel):
    preset_key: str = Field(pattern=SLUG_PATTERN, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    default_kind: AgentKind
    default_provider_profile_key: str | None = Field(default=None, max_length=80)
    persona_text: str = Field(default="", max_length=12_000)
    behavior_policy: dict[str, Any] = Field(default_factory=dict)
    calendar_blueprint: list[AgentPresetCalendarEntryRequest] = Field(default_factory=list)
    advanced_config: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class AgentPresetUpdateRequest(_RequestModel):
    preset_key: str | None = Field(default=None, pattern=SLUG_PATTERN, max_length=80)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    default_kind: AgentKind | None = None
    default_provider_profile_key: str | None = Field(default=None, max_length=80)
    persona_text: str | None = Field(default=None, max_length=12_000)
    behavior_policy: dict[str, Any] | None = None
    calendar_blueprint: list[AgentPresetCalendarEntryRequest] | None = None
    advanced_config: dict[str, Any] | None = None
    is_active: bool | None = None


class AgentPresetCalendarEntryResponse(BaseModel):
    title: str
    description: str | None
    starts_at: datetime
    ends_at: datetime | None
    recurrence_rule: str | None
    metadata: dict[str, Any]


class AgentPresetResponse(BaseModel):
    id: uuid.UUID
    preset_key: str
    name: str
    description: str | None
    default_kind: AgentKind
    default_provider_profile_key: str | None
    persona_text: str
    behavior_policy: dict[str, Any]
    calendar_blueprint: list[AgentPresetCalendarEntryResponse]
    advanced_config: dict[str, Any]
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AgentPresetUpdatePreviewAgent(BaseModel):
    agent_id: uuid.UUID
    world_id: uuid.UUID
    agent_key: str
    display_name: str
    source_preset_version: int | None
    status: Literal["current", "stale", "unversioned"]
    changed_fields: list[str]


class AgentPresetUpdatePreviewResponse(BaseModel):
    preset_id: uuid.UUID
    preset_key: str
    current_version: int
    stale_agent_count: int
    current_agent_count: int
    unversioned_agent_count: int
    agents: list[AgentPresetUpdatePreviewAgent]


class WorldCompositionWorldResponse(BaseModel):
    slug: str
    name: str
    description: str | None
    rules_config: dict[str, Any]
    memory_backend_profile_key: str | None = None
    memory_plugin_identifier: str | None = None
    memory_plugin_config: dict[str, Any] = Field(default_factory=dict)
    world_rules_plugin_identifier: str | None = None
    world_rules_plugin_config: dict[str, Any] = Field(default_factory=dict)
    is_active: bool


class WorldCompositionSceneResponse(BaseModel):
    scene_key: str
    name: str
    description: str | None
    is_active: bool


class WorldCompositionAgentResponse(BaseModel):
    agent_key: str
    display_name: str
    kind: AgentKind
    home_scene_key: str | None
    source_preset_key: str | None
    source_preset_version: int | None = None
    provider_profile_key: str | None
    config: dict[str, Any]
    is_enabled: bool


class WorldCompositionScheduleRuleResponse(BaseModel):
    rule_key: str
    name: str
    kind: Literal["weekday", "weekend", "timetable"]
    config: dict[str, Any]
    is_enabled: bool


class WorldCompositionPresetReferenceResponse(BaseModel):
    preset_key: str
    name: str
    default_kind: AgentKind
    default_provider_profile_key: str | None
    version: int = 1
    is_active: bool


class WorldCompositionValidationIssue(BaseModel):
    severity: Literal["blocking", "warning"]
    code: str
    field: str
    message: str


class WorldCompositionExportResponse(BaseModel):
    world: WorldCompositionWorldResponse
    scenes: list[WorldCompositionSceneResponse]
    agents: list[WorldCompositionAgentResponse]
    schedule_rules: list[WorldCompositionScheduleRuleResponse]
    preset_references: list[WorldCompositionPresetReferenceResponse]


class WorldCompositionValidationResponse(BaseModel):
    valid: bool
    blocking_issue_count: int
    warning_issue_count: int
    issues: list[WorldCompositionValidationIssue]


class WorldCompositionImportRequest(_RequestModel):
    slug: str = Field(pattern=SLUG_PATTERN, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    owner_user_id: uuid.UUID
    description: str | None = None
    rules_config: dict[str, Any] | None = None
    composition: WorldCompositionExportResponse


class WorldCompositionValidationRequest(WorldCompositionImportRequest):
    pass


class CalendarEntryResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    agent_id: uuid.UUID
    title: str
    description: str | None
    starts_at: datetime
    ends_at: datetime | None
    recurrence_rule: str | None
    status: str
    metadata: dict[str, Any]


class ScheduleRuleResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    rule_key: str
    name: str
    kind: str
    config: dict[str, Any]
    is_enabled: bool


class ScheduleRulePreviewMatchResponse(BaseModel):
    world_time: datetime
    reason: str
    affected_agent_count: int
    affected_agent_ids: list[uuid.UUID]


class ScheduleRulePreviewResponse(BaseModel):
    world_id: uuid.UUID
    kind: str
    config: dict[str, Any]
    start_world_time: datetime
    horizon_hours: int
    match_count: int
    affected_agent_count: int
    affected_agent_ids: list[uuid.UUID]
    matches: list[ScheduleRulePreviewMatchResponse]


class CalendarConflictSourceResponse(BaseModel):
    source_kind: str
    source_id: uuid.UUID
    agent_id: uuid.UUID | None
    label: str


class CalendarConflictResponse(BaseModel):
    conflict_type: str
    world_id: uuid.UUID
    agent_id: uuid.UUID | None
    starts_at: datetime
    ends_at: datetime
    reason: str
    sources: list[CalendarConflictSourceResponse]


class CalendarConflictReportResponse(BaseModel):
    world_id: uuid.UUID
    start_world_time: datetime
    horizon_hours: int
    conflict_count: int
    conflicts: list[CalendarConflictResponse]


class MemoryItemResponse(BaseModel):
    id: str
    world_id: uuid.UUID
    agent_id: uuid.UUID
    content: str
    metadata: dict[str, Any]
    backend: str
    created_at: datetime | None
    score: float | None = None


class MemoryProfileSnapshotResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    agent_id: uuid.UUID
    aliases: list[str]
    identity_notes: list[str]
    durable_preferences: list[str]
    long_lived_goals: list[str]
    language_style_preferences: list[str]
    refreshed_at: datetime
    created_at: datetime
    updated_at: datetime


class MemoryDeleteResponse(BaseModel):
    backend: str
    deleted_count: int | None = None


class AgentRunResponse(BaseModel):
    run_id: uuid.UUID
    world_id: uuid.UUID
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


class AgentRunProviderSummaryResponse(BaseModel):
    id: uuid.UUID
    profile_key: str
    name: str
    provider_type: str
    model_name: str
    is_enabled: bool


class AgentRunConversationTurnResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    turn_index: int
    speaker_kind: str
    speaker_agent_id: uuid.UUID | None
    status: str
    error_text: str | None
    created_at: datetime


class AgentRunDetailResponse(BaseModel):
    run: AgentRunResponse
    provider_profile: AgentRunProviderSummaryResponse | None
    conversation_turns: list[AgentRunConversationTurnResponse]


class AgentPersonaResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    agent_id: uuid.UUID
    persona_text: str
    behavior_policy: dict[str, Any]
    policy_plugin_identifier: str
    policy_plugin_config: dict[str, Any]
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


class AgentObservationResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    agent_id: uuid.UUID
    source_event_id: uuid.UUID | None
    observation_type: str
    content: str
    metadata: dict[str, Any]
    observed_at: datetime
    consumed_at: datetime | None
    confidence_score: float | None
    review_status: str
    runtime_use_count: int
    last_used_run_id: uuid.UUID | None
    created_at: datetime


class NarrativeArtifactResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    agent_id: uuid.UUID | None
    source_run_id: uuid.UUID | None
    source_conversation_id: uuid.UUID | None
    title: str
    content: str
    artifact_kind: str
    metadata: dict[str, Any]
    created_at: datetime
    publication: NarrativePublicationResponse | None = None


class NarrativePublicationResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    artifact_id: uuid.UUID
    source_draft_id: uuid.UUID | None
    status: str
    reader_visible: bool
    metadata: dict[str, Any]
    published_at: datetime | None
    unpublished_at: datetime | None
    published_by_user_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class WorldClockResponse(BaseModel):
    world_id: uuid.UUID
    status: str
    current_world_time: datetime
    effective_world_time: datetime
    wall_time_anchor: datetime | None
    speed_multiplier: str
    revision: int


class WorldClockTransitionResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    transition_type: str
    previous_status: str | None
    new_status: str
    previous_world_time: datetime | None
    new_world_time: datetime
    wall_time: datetime
    previous_revision: int | None
    new_revision: int
    actor_ref: str | None
    correlation_id: str | None
    reason: str | None
    created_at: datetime


class WorldSnapshotResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    covers_event_sequence: int
    schema_version: str
    status: str
    payload: dict[str, Any] | None
    payload_uri: str | None
    payload_location: str | None
    metadata: dict[str, Any]
    created_by_event_id: uuid.UUID
    created_at: datetime


class WorldEventResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    sequence: int
    event_name: str
    payload: dict[str, Any]
    wall_time: datetime
    world_time: datetime | None
    actor_ref: str
    causation_event_id: uuid.UUID | None
    correlation_id: uuid.UUID | None
    created_at: datetime


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


@router.get("", response_model=list[WorldResponse])
def list_worlds(
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[WorldResponse]:
    if is_platform_admin(subject):
        worlds = db_session.scalars(select(World).order_by(World.slug)).all()
    else:
        worlds = db_session.scalars(
            select(World)
            .join(WorldMembership, WorldMembership.world_id == World.id)
            .where(WorldMembership.user_id == subject.user_id)
            .order_by(World.slug),
        ).all()
    return [_world_response(world) for world in worlds]


@root_router.get("/agent-presets", response_model=list[AgentPresetResponse])
def list_agent_presets(
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[AgentPresetResponse]:
    preset_service = AgentPresetService(db_session)
    include_inactive = is_platform_admin(subject)
    return [
        _agent_preset_response(record)
        for record in preset_service.list(include_inactive=include_inactive)
    ]


@root_router.post(
    "/agent-presets",
    response_model=AgentPresetResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_agent_preset(
    preset_create: AgentPresetCreateRequest,
    request: Request,
    _subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AgentPresetResponse:
    require_csrf(request)
    _ensure_preset_key_available(db_session, preset_create.preset_key)
    record = AgentPresetService(db_session).create(_agent_preset_upsert(preset_create))
    return _agent_preset_response(record)


@root_router.patch("/agent-presets/{preset_id}", response_model=AgentPresetResponse)
def update_agent_preset(
    preset_id: uuid.UUID,
    preset_update: AgentPresetUpdateRequest,
    request: Request,
    _subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AgentPresetResponse:
    require_csrf(request)
    preset_service = AgentPresetService(db_session)
    existing = preset_service.get(preset_id, include_inactive=True)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    next_record = AgentPresetUpsert(
        preset_key=preset_update.preset_key or existing.preset_key,
        name=preset_update.name or existing.name,
        description=(
            preset_update.description
            if "description" in preset_update.model_fields_set
            else existing.description
        ),
        default_kind=preset_update.default_kind or existing.default_kind,
        default_provider_profile_key=(
            preset_update.default_provider_profile_key
            if "default_provider_profile_key" in preset_update.model_fields_set
            else existing.default_provider_profile_key
        ),
        persona_text=(
            preset_update.persona_text
            if preset_update.persona_text is not None
            else existing.persona_text
        ),
        behavior_policy=(
            preset_update.behavior_policy
            if preset_update.behavior_policy is not None
            else existing.behavior_policy
        ),
        calendar_blueprint=(
            _preset_calendar_blueprint(preset_update.calendar_blueprint)
            if preset_update.calendar_blueprint is not None
            else existing.calendar_blueprint
        ),
        advanced_config=(
            preset_update.advanced_config
            if preset_update.advanced_config is not None
            else existing.advanced_config
        ),
        is_active=(
            existing.is_active if preset_update.is_active is None else preset_update.is_active
        ),
    )
    _ensure_preset_key_available(db_session, next_record.preset_key, preset_id=preset_id)
    updated = preset_service.update(preset_id, next_record)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return _agent_preset_response(updated)


@root_router.get(
    "/agent-presets/{preset_id}/update-preview",
    response_model=AgentPresetUpdatePreviewResponse,
)
def preview_agent_preset_update(
    preset_id: uuid.UUID,
    _subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AgentPresetUpdatePreviewResponse:
    preset = AgentPresetService(db_session).get(preset_id, include_inactive=True)
    if preset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    agents = db_session.scalars(
        select(Agent)
        .where(Agent.source_preset_id == preset_id)
        .order_by(Agent.agent_key),
    ).all()
    return _agent_preset_update_preview_response(preset, agents)


@root_router.delete("/agent-presets/{preset_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_agent_preset(
    preset_id: uuid.UUID,
    request: Request,
    _subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> None:
    require_csrf(request)
    if AgentPresetService(db_session).deactivate(preset_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


@root_router.post(
    "/world-compositions/validate",
    response_model=WorldCompositionValidationResponse,
)
def validate_world_composition_import(
    validation_request: WorldCompositionValidationRequest,
    _subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorldCompositionValidationResponse:
    return _validate_world_composition_import(db_session, validation_request)


@root_router.post(
    "/world-compositions/import",
    response_model=WorldResponse,
    status_code=status.HTTP_201_CREATED,
)
def import_world_composition(
    import_request: WorldCompositionImportRequest,
    request: Request,
    _subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorldResponse:
    require_csrf(request)
    validation = _validate_world_composition_import(db_session, import_request)
    if not validation.valid:
        blocking_issues = [
            issue.model_dump()
            for issue in validation.issues
            if issue.severity == "blocking"
        ]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=blocking_issues,
        )
    owner = db_session.get(User, import_request.owner_user_id)
    if owner is None or not owner.is_active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=[
                WorldCompositionValidationIssue(
                    severity="blocking",
                    code="unknown_owner",
                    field="owner_user_id",
                    message="Owner user does not exist or is inactive.",
                ).model_dump()
            ],
        )

    world = World(
        id=uuid.uuid4(),
        owner_user_id=owner.id,
        slug=import_request.slug,
        name=import_request.name,
        description=(
            import_request.description
            if "description" in import_request.model_fields_set
            else import_request.composition.world.description
        ),
        rules_config=(
            import_request.rules_config
            if import_request.rules_config is not None
            else import_request.composition.world.rules_config
        ),
        memory_backend_profile_id=_memory_backend_profile_id_from_profile_key(
            db_session,
            import_request.composition.world.memory_backend_profile_key,
        ),
        memory_plugin_identifier=(
            import_request.composition.world.memory_plugin_identifier or BUILTIN_MEM0_OSS_MEMORY
        ),
        memory_plugin_config=import_request.composition.world.memory_plugin_config,
        world_rules_plugin_identifier=(
            import_request.composition.world.world_rules_plugin_identifier
            or BUILTIN_DEFAULT_WORLD_RULES
        ),
        world_rules_plugin_config=import_request.composition.world.world_rules_plugin_config,
        is_active=import_request.composition.world.is_active,
    )
    db_session.add(world)
    db_session.flush()
    _upsert_membership(db_session, world.id, owner.id, AuthRole.WORLD_ADMIN.value)
    WorldClockService(db_session).ensure_initialized(
        world.id,
        actor_ref=f"user:{owner.id}",
        reason="world composition imported",
    )

    preset_service = AgentPresetService(db_session)
    preset_map: dict[str, AgentPresetRecord] = {}
    for preset_reference in import_request.composition.preset_references:
        preset = preset_service.get_by_key(
            preset_reference.preset_key,
            include_inactive=True,
        )
        if preset is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Unknown agent preset: {preset_reference.preset_key}",
            )
        preset_map[preset.preset_key] = preset

    scene_key_to_id: dict[str, uuid.UUID] = {}
    for scene in import_request.composition.scenes:
        model = Scene(
            id=uuid.uuid4(),
            world_id=world.id,
            scene_key=scene.scene_key,
            name=scene.name,
            description=scene.description,
            is_active=scene.is_active,
        )
        db_session.add(model)
        db_session.flush()
        scene_key_to_id[scene.scene_key] = model.id

    for rule in import_request.composition.schedule_rules:
        db_session.add(
            WorldScheduleRule(
                id=uuid.uuid4(),
                world_id=world.id,
                rule_key=rule.rule_key,
                name=rule.name,
                kind=rule.kind,
                config=rule.config,
                is_enabled=rule.is_enabled,
            )
        )
    db_session.flush()

    for exported_agent in import_request.composition.agents:
        preset = (
            None
            if exported_agent.source_preset_key is None
            else preset_map.get(exported_agent.source_preset_key)
        )
        preset_provider_profile_id = (
            None
            if preset is None
            else _provider_profile_id_from_profile_key(
                db_session,
                preset.default_provider_profile_key,
            )
        )
        explicit_provider_profile_id = _provider_profile_id_from_profile_key(
            db_session,
            exported_agent.provider_profile_key,
        )
        home_scene_id = (
            None
            if exported_agent.home_scene_key is None
            else scene_key_to_id.get(exported_agent.home_scene_key)
        )
        effective_config = dict(preset.advanced_config if preset is not None else {})
        effective_config.update(exported_agent.config)
        provider_profile_id = explicit_provider_profile_id or preset_provider_profile_id
        agent = Agent(
            id=uuid.uuid4(),
            world_id=world.id,
            home_scene_id=home_scene_id,
            source_preset_id=None if preset is None else preset.id,
            source_preset_version=None if preset is None else preset.version,
            agent_key=exported_agent.agent_key,
            display_name=exported_agent.display_name,
            kind=exported_agent.kind,
            config=_agent_config_with_provider_profile_id(effective_config, provider_profile_id),
            is_enabled=exported_agent.is_enabled,
        )
        db_session.add(agent)
        db_session.flush()
        if preset is not None:
            AgentPersonaService(db_session).upsert(
                AgentPersonaUpsert(
                    world_id=world.id,
                    agent_id=agent.id,
                    persona_text=preset.persona_text,
                    behavior_policy=preset.behavior_policy,
                    is_enabled=True,
                )
            )
            preset_service.materialize_calendar_blueprint(
                world_id=world.id,
                agent_id=agent.id,
                blueprint=preset.calendar_blueprint,
            )

    db_session.flush()
    return _world_response(world)


@router.post("", response_model=WorldResponse, status_code=status.HTTP_201_CREATED)
def create_world(
    world_create: WorldCreateRequest,
    request: Request,
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorldResponse:
    require_csrf(request)
    _ensure_slug_available(db_session, world_create.slug)
    _validate_world_plugin_bindings(
        memory_plugin_identifier=world_create.memory_plugin_identifier,
        memory_plugin_config=world_create.memory_plugin_config,
        world_rules_plugin_identifier=world_create.world_rules_plugin_identifier,
        world_rules_plugin_config=world_create.world_rules_plugin_config,
    )
    memory_backend_profile_id = _resolved_memory_backend_profile_id(
        db_session,
        world_create.memory_plugin_identifier,
        world_create.memory_backend_profile_id,
    )
    world = World(
        id=uuid.uuid4(),
        owner_user_id=subject.user_id,
        slug=world_create.slug,
        name=world_create.name,
        description=world_create.description,
        rules_config=world_create.rules_config,
        memory_backend_profile_id=memory_backend_profile_id,
        memory_plugin_identifier=world_create.memory_plugin_identifier,
        memory_plugin_config=world_create.memory_plugin_config,
        world_rules_plugin_identifier=world_create.world_rules_plugin_identifier,
        world_rules_plugin_config=world_create.world_rules_plugin_config,
        is_active=True,
    )
    db_session.add(world)
    db_session.flush()
    _upsert_membership(db_session, world.id, subject.user_id, AuthRole.WORLD_ADMIN.value)
    WorldClockService(db_session).ensure_initialized(
        world.id,
        actor_ref=_actor_ref(subject),
        reason="world created",
    )
    db_session.flush()
    return _world_response(world)


@router.get("/{world_id}", response_model=WorldResponse)
def get_world(
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorldResponse:
    return _world_response(_world_or_404(db_session, context.world_id))


@router.get("/{world_id}/composition-export", response_model=WorldCompositionExportResponse)
def export_world_composition(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorldCompositionExportResponse:
    world = _world_or_404(db_session, context.world_id)
    scenes = db_session.scalars(
        select(Scene).where(Scene.world_id == context.world_id).order_by(Scene.scene_key),
    ).all()
    agents = db_session.scalars(
        select(Agent).where(Agent.world_id == context.world_id).order_by(Agent.agent_key),
    ).all()
    schedule_rules = db_session.scalars(
        select(WorldScheduleRule)
        .where(WorldScheduleRule.world_id == context.world_id)
        .order_by(WorldScheduleRule.rule_key),
    ).all()

    provider_profile_ids = [
        profile_id
        for profile_id in (_provider_profile_id_from_config(agent.config) for agent in agents)
        if profile_id is not None
    ]
    profile_map = _provider_profile_key_map(db_session, provider_profile_ids)
    preset_ids = {agent.source_preset_id for agent in agents if agent.source_preset_id is not None}
    preset_models = (
        []
        if not preset_ids
        else db_session.scalars(
            select(AgentPreset)
            .where(AgentPreset.id.in_(preset_ids))
            .order_by(AgentPreset.preset_key),
        ).all()
    )
    preset_map = {preset.id: preset for preset in preset_models}
    scene_map = {scene.id: scene.scene_key for scene in scenes}
    exported_agents = [
        WorldCompositionAgentResponse(
            agent_key=agent.agent_key,
            display_name=agent.display_name,
            kind=cast(AgentKind, agent.kind),
            home_scene_key=(
                None if agent.home_scene_id is None else scene_map.get(agent.home_scene_id)
            ),
            source_preset_key=_source_preset_key(preset_map, agent.source_preset_id),
            source_preset_version=agent.source_preset_version,
            provider_profile_key=_provider_profile_key_from_config(profile_map, agent.config),
            config=agent.config,
            is_enabled=agent.is_enabled,
        )
        for agent in agents
    ]

    return WorldCompositionExportResponse(
        world=WorldCompositionWorldResponse(
            slug=world.slug,
            name=world.name,
            description=world.description,
            rules_config=world.rules_config,
            memory_backend_profile_key=_memory_backend_profile_key(
                db_session,
                world.memory_backend_profile_id,
            ),
            memory_plugin_identifier=world.memory_plugin_identifier,
            memory_plugin_config=world.memory_plugin_config,
            world_rules_plugin_identifier=world.world_rules_plugin_identifier,
            world_rules_plugin_config=world.world_rules_plugin_config,
            is_active=world.is_active,
        ),
        scenes=[
            WorldCompositionSceneResponse(
                scene_key=scene.scene_key,
                name=scene.name,
                description=scene.description,
                is_active=scene.is_active,
            )
            for scene in scenes
        ],
        agents=exported_agents,
        schedule_rules=[
            WorldCompositionScheduleRuleResponse(
                rule_key=rule.rule_key,
                name=rule.name,
                kind=cast(Literal["weekday", "weekend", "timetable"], rule.kind),
                config=rule.config,
                is_enabled=rule.is_enabled,
            )
            for rule in schedule_rules
        ],
        preset_references=[
            WorldCompositionPresetReferenceResponse(
                preset_key=preset.preset_key,
                name=preset.name,
                default_kind=cast(AgentKind, preset.default_kind),
                default_provider_profile_key=preset.default_provider_profile_key,
                version=preset.version,
                is_active=preset.is_active,
            )
            for preset in preset_models
        ],
    )


@router.patch("/{world_id}", response_model=WorldResponse)
def update_world(
    world_update: WorldUpdateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorldResponse:
    require_csrf(request)
    world = _world_or_404(db_session, context.world_id)
    next_memory_plugin_identifier = (
        world.memory_plugin_identifier
        if "memory_plugin_identifier" not in world_update.model_fields_set
        or world_update.memory_plugin_identifier is None
        else world_update.memory_plugin_identifier
    )
    next_memory_backend_profile_id = (
        world.memory_backend_profile_id
        if "memory_backend_profile_id" not in world_update.model_fields_set
        else _resolved_memory_backend_profile_id(
            db_session,
            next_memory_plugin_identifier,
            world_update.memory_backend_profile_id,
        )
    )
    next_memory_plugin_config = (
        world.memory_plugin_config
        if "memory_plugin_config" not in world_update.model_fields_set
        else world_update.memory_plugin_config or {}
    )
    next_world_rules_plugin_identifier = (
        world.world_rules_plugin_identifier
        if "world_rules_plugin_identifier" not in world_update.model_fields_set
        or world_update.world_rules_plugin_identifier is None
        else world_update.world_rules_plugin_identifier
    )
    next_world_rules_plugin_config = (
        world.world_rules_plugin_config
        if "world_rules_plugin_config" not in world_update.model_fields_set
        else world_update.world_rules_plugin_config or {}
    )
    _validate_world_plugin_bindings(
        memory_plugin_identifier=next_memory_plugin_identifier,
        memory_plugin_config=next_memory_plugin_config,
        world_rules_plugin_identifier=next_world_rules_plugin_identifier,
        world_rules_plugin_config=next_world_rules_plugin_config,
    )
    if "name" in world_update.model_fields_set:
        world.name = world_update.name or world.name
    if "description" in world_update.model_fields_set:
        world.description = world_update.description
    if "rules_config" in world_update.model_fields_set:
        world.rules_config = world_update.rules_config or {}
    if "memory_backend_profile_id" in world_update.model_fields_set:
        world.memory_backend_profile_id = next_memory_backend_profile_id
    if "memory_plugin_identifier" in world_update.model_fields_set:
        world.memory_plugin_identifier = next_memory_plugin_identifier
    if "memory_plugin_config" in world_update.model_fields_set:
        world.memory_plugin_config = next_memory_plugin_config
    if "world_rules_plugin_identifier" in world_update.model_fields_set:
        world.world_rules_plugin_identifier = next_world_rules_plugin_identifier
    if "world_rules_plugin_config" in world_update.model_fields_set:
        world.world_rules_plugin_config = next_world_rules_plugin_config
    if "is_active" in world_update.model_fields_set:
        world.is_active = bool(world_update.is_active)
    db_session.flush()
    return _world_response(world)


@router.delete("/{world_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_world(
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> None:
    require_csrf(request)
    world = _world_or_404(db_session, context.world_id)
    world.is_active = False
    db_session.flush()


@router.get("/{world_id}/clock", response_model=WorldClockResponse)
def get_clock(
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorldClockResponse:
    _world_or_404(db_session, context.world_id)
    return _clock_response(WorldClockService(db_session).view(context.world_id))


@router.get("/{world_id}/clock/transitions", response_model=list[WorldClockTransitionResponse])
def list_clock_transitions(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[WorldClockTransitionResponse]:
    _world_or_404(db_session, context.world_id)
    return [
        _clock_transition_response(transition)
        for transition in db_session.scalars(
            select(WorldClockTransitionModel)
            .where(WorldClockTransitionModel.world_id == context.world_id)
            .order_by(WorldClockTransitionModel.new_revision.desc())
            .limit(limit),
        ).all()
    ]


@router.post("/{world_id}/clock/pause", response_model=WorldClockResponse)
def pause_clock_endpoint(
    clock_request: ClockTransitionRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorldClockResponse:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    try:
        return _clock_response(
            WorldClockService(db_session).pause(
                context.world_id,
                actor_ref=_actor_ref(context.subject),
                reason=clock_request.reason,
            ),
        )
    except WorldClockError as exc:
        raise _clock_conflict(exc) from exc


@router.post("/{world_id}/clock/resume", response_model=WorldClockResponse)
def resume_clock_endpoint(
    clock_request: ClockResumeRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorldClockResponse:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    try:
        return _clock_response(
            WorldClockService(db_session).resume(
                context.world_id,
                speed_multiplier=clock_request.speed_multiplier,
                actor_ref=_actor_ref(context.subject),
                reason=clock_request.reason,
            ),
        )
    except WorldClockError as exc:
        raise _clock_conflict(exc) from exc


@router.post("/{world_id}/clock/advance", response_model=WorldClockResponse)
def advance_clock_endpoint(
    clock_request: ClockTransitionRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorldClockResponse:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    try:
        return _clock_response(
            WorldClockService(db_session).advance(
                context.world_id,
                actor_ref=_actor_ref(context.subject),
                reason=clock_request.reason,
            ),
        )
    except WorldClockError as exc:
        raise _clock_conflict(exc) from exc


@router.post("/{world_id}/clock/skip", response_model=WorldClockResponse)
def skip_clock_endpoint(
    clock_request: ClockSkipRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorldClockResponse:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    try:
        return _clock_response(
            WorldClockService(db_session).skip(
                context.world_id,
                target_world_time=clock_request.target_world_time,
                actor_ref=_actor_ref(context.subject),
                reason=clock_request.reason,
            ),
        )
    except WorldClockError as exc:
        raise _clock_conflict(exc) from exc


@router.get("/{world_id}/replay/state", response_model=WorldReplayState)
def replay_state(
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorldReplayState:
    _world_or_404(db_session, context.world_id)
    return WorldReplayService(db_session, load_settings()).replay_state(context.world_id)


@router.get("/{world_id}/snapshots/latest", response_model=WorldSnapshotResponse | None)
def latest_snapshot(
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorldSnapshotResponse | None:
    _world_or_404(db_session, context.world_id)
    snapshot = WorldReplayService(db_session, load_settings()).latest_snapshot(context.world_id)
    if snapshot is None:
        return None
    return _snapshot_response(snapshot)


@router.get(
    "/{world_id}/snapshots/integrity",
    response_model=WorldSnapshotIntegrityReport,
)
def snapshot_integrity(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorldSnapshotIntegrityReport:
    _world_or_404(db_session, context.world_id)
    return WorldReplayService(db_session, load_settings()).snapshot_integrity(context.world_id)


@router.get("/{world_id}/events", response_model=list[WorldEventResponse])
def list_world_events(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    event_name: Annotated[str | None, Query(min_length=3, max_length=120)] = None,
    actor_ref: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
    sequence_after: Annotated[int | None, Query(ge=0)] = None,
    sequence_before: Annotated[int | None, Query(ge=1)] = None,
    wall_time_from: datetime | None = None,
    wall_time_to: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[WorldEventResponse]:
    _world_or_404(db_session, context.world_id)
    wall_time_from = _optional_query_time(wall_time_from, "wall_time_from")
    wall_time_to = _optional_query_time(wall_time_to, "wall_time_to")
    statement = select(WorldEventModel).where(WorldEventModel.world_id == context.world_id)
    if event_name is not None:
        statement = statement.where(WorldEventModel.event_name == event_name)
    if actor_ref is not None:
        statement = statement.where(WorldEventModel.actor_ref == actor_ref)
    if sequence_after is not None:
        statement = statement.where(WorldEventModel.sequence > sequence_after)
    if sequence_before is not None:
        statement = statement.where(WorldEventModel.sequence < sequence_before)
    if wall_time_from is not None:
        statement = statement.where(WorldEventModel.wall_time >= wall_time_from)
    if wall_time_to is not None:
        statement = statement.where(WorldEventModel.wall_time <= wall_time_to)
    return [
        _world_event_response(event)
        for event in db_session.scalars(
            statement.order_by(WorldEventModel.sequence.desc()).limit(limit),
        ).all()
    ]


@router.get("/{world_id}/schedule-rules", response_model=list[ScheduleRuleResponse])
def list_schedule_rules(
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[ScheduleRuleResponse]:
    _world_or_404(db_session, context.world_id)
    return [
        _schedule_rule_response(rule)
        for rule in CalendarService(db_session).list_rules(context.world_id)
    ]


@router.get(
    "/{world_id}/calendar/conflicts",
    response_model=CalendarConflictReportResponse,
)
def list_calendar_conflicts(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    start_world_time: Annotated[datetime | None, Query()] = None,
    horizon_hours: Annotated[int, Query(ge=1, le=720)] = 168,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> CalendarConflictReportResponse:
    _world_or_404(db_session, context.world_id)
    if start_world_time is not None:
        start_world_time = _timezone_aware(start_world_time, "start_world_time")
    start_time = start_world_time or WorldClockService(db_session).view(
        context.world_id,
    ).effective_world_time
    return _calendar_conflict_report_response(
        CalendarService(db_session).detect_conflicts(
            world_id=context.world_id,
            start_world_time=start_time,
            horizon_hours=horizon_hours,
            limit=limit,
        ),
    )


@router.post(
    "/{world_id}/schedule-rules/preview",
    response_model=ScheduleRulePreviewResponse,
)
def preview_schedule_rule(
    preview_request: ScheduleRulePreviewRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ScheduleRulePreviewResponse:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    start_world_time = (
        preview_request.start_world_time
        or WorldClockService(db_session).view(context.world_id).effective_world_time
    )
    preview = CalendarService(db_session).preview_rule(
        kind=ScheduleRuleKind(preview_request.kind),
        config=preview_request.config,
        start_world_time=start_world_time,
        horizon_hours=preview_request.horizon_hours,
        limit=preview_request.limit,
    )
    affected_agent_ids = [
        agent_id
        for agent_id in db_session.scalars(
            select(Agent.id)
            .where(Agent.world_id == context.world_id, Agent.is_enabled.is_(True))
            .order_by(Agent.agent_key),
        ).all()
    ]
    return _schedule_rule_preview_response(context.world_id, preview, affected_agent_ids)


@router.post(
    "/{world_id}/schedule-rules",
    response_model=ScheduleRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_schedule_rule(
    rule_create: ScheduleRuleCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ScheduleRuleResponse:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    _ensure_schedule_rule_key_available(db_session, context.world_id, rule_create.rule_key)
    return _schedule_rule_response(
        CalendarService(db_session).create_rule(
            ScheduleRuleCreate(
                world_id=context.world_id,
                rule_key=rule_create.rule_key,
                name=rule_create.name,
                kind=ScheduleRuleKind(rule_create.kind),
                config=rule_create.config,
            ),
        ),
    )


@router.patch("/{world_id}/schedule-rules/{rule_id}", response_model=ScheduleRuleResponse)
def update_schedule_rule(
    rule_id: uuid.UUID,
    rule_update: ScheduleRuleUpdateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ScheduleRuleResponse:
    require_csrf(request)
    rule = _schedule_rule_or_404(db_session, context.world_id, rule_id)
    return _schedule_rule_response(
        CalendarService(db_session).update_rule(
            rule,
            ScheduleRuleUpdate(
                name=rule_update.name,
                kind=None if rule_update.kind is None else ScheduleRuleKind(rule_update.kind),
                config=rule_update.config,
                is_enabled=rule_update.is_enabled,
            ),
        ),
    )


@router.delete("/{world_id}/schedule-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def disable_schedule_rule(
    rule_id: uuid.UUID,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> None:
    require_csrf(request)
    CalendarService(db_session).disable_rule(
        _schedule_rule_or_404(db_session, context.world_id, rule_id),
    )


@router.post(
    "/{world_id}/snapshots",
    response_model=WorldSnapshotResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_snapshot(
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorldSnapshotResponse:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    snapshot = WorldReplayService(db_session, load_settings()).create_snapshot(
        context.world_id,
        actor_ref=_actor_ref(context.subject),
    )
    return _snapshot_response(snapshot)


@router.get("/{world_id}/diagnostics", response_model=list[RuntimeDiagnosticResponse])
def list_world_diagnostics(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    agent_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[RuntimeDiagnosticResponse]:
    _world_or_404(db_session, context.world_id)
    if agent_id is not None:
        _agent_or_404(db_session, context.world_id, agent_id)
    return [
        _diagnostic_response(record)
        for record in RuntimeDiagnosticsService(db_session).list_for_world(
            context.world_id,
            agent_id=agent_id,
            limit=limit,
        )
    ]


@router.get("/{world_id}/scenes", response_model=list[SceneResponse])
def list_scenes(
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[SceneResponse]:
    scenes = db_session.scalars(
        select(Scene).where(Scene.world_id == context.world_id).order_by(Scene.scene_key),
    ).all()
    return [_scene_response(scene) for scene in scenes]


@router.post(
    "/{world_id}/scenes",
    response_model=SceneResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_scene(
    scene_create: SceneCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> SceneResponse:
    require_csrf(request)
    _ensure_scene_key_available(db_session, context.world_id, scene_create.scene_key)
    scene = Scene(
        id=uuid.uuid4(),
        world_id=context.world_id,
        scene_key=scene_create.scene_key,
        name=scene_create.name,
        description=scene_create.description,
        is_active=True,
    )
    db_session.add(scene)
    db_session.flush()
    return _scene_response(scene)


@router.patch("/{world_id}/scenes/{scene_id}", response_model=SceneResponse)
def update_scene(
    scene_id: uuid.UUID,
    scene_update: SceneUpdateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> SceneResponse:
    require_csrf(request)
    scene = _scene_or_404(db_session, context.world_id, scene_id)
    if "name" in scene_update.model_fields_set:
        scene.name = scene_update.name or scene.name
    if "description" in scene_update.model_fields_set:
        scene.description = scene_update.description
    if "is_active" in scene_update.model_fields_set:
        scene.is_active = bool(scene_update.is_active)
    db_session.flush()
    return _scene_response(scene)


@router.delete("/{world_id}/scenes/{scene_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_scene(
    scene_id: uuid.UUID,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> None:
    require_csrf(request)
    scene = _scene_or_404(db_session, context.world_id, scene_id)
    scene.is_active = False
    db_session.flush()


@router.get("/{world_id}/memberships", response_model=list[MembershipResponse])
def list_memberships(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[MembershipResponse]:
    rows = db_session.execute(
        select(WorldMembership, User)
        .join(User, User.id == WorldMembership.user_id)
        .where(WorldMembership.world_id == context.world_id)
        .order_by(WorldMembership.role, WorldMembership.user_id),
    ).all()
    return [_membership_response(membership, user) for membership, user in rows]


@router.get("/{world_id}/member-candidates", response_model=list[MemberCandidateResponse])
def list_member_candidates(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    query: Annotated[str | None, Query(max_length=160)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[MemberCandidateResponse]:
    statement = (
        select(User, WorldMembership.role)
        .outerjoin(
            WorldMembership,
            (WorldMembership.user_id == User.id) & (WorldMembership.world_id == context.world_id),
        )
        .where(User.is_active.is_(True))
        .order_by(User.email)
        .limit(limit)
    )
    normalized_query = query.strip() if query is not None else ""
    if normalized_query:
        pattern = f"%{normalized_query}%"
        statement = statement.where(
            or_(User.email.ilike(pattern), User.display_name.ilike(pattern)),
        )

    return [
        MemberCandidateResponse(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            is_active=user.is_active,
            role=cast(WorldRole | None, role),
        )
        for user, role in db_session.execute(statement).all()
    ]


@router.put("/{world_id}/memberships/{user_id}", response_model=MembershipResponse)
def upsert_membership(
    user_id: uuid.UUID,
    membership_upsert: MembershipUpsertRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MembershipResponse:
    require_csrf(request)
    if user_id != membership_upsert.user_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="user_id mismatch",
        )
    user = _user_or_404(db_session, user_id)
    existing = _membership_or_none(db_session, context.world_id, user_id)
    if (
        existing is not None
        and existing.role == AuthRole.WORLD_ADMIN.value
        and membership_upsert.role != AuthRole.WORLD_ADMIN.value
        and _world_admin_count(db_session, context.world_id) <= 1
    ):
        raise _conflict("Cannot remove the final world admin")
    membership = _upsert_membership(db_session, context.world_id, user_id, membership_upsert.role)
    db_session.flush()
    return _membership_response(membership, user)


@router.delete("/{world_id}/memberships/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_membership(
    user_id: uuid.UUID,
    request: Request,
    response: Response,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> None:
    require_csrf(request)
    membership = _membership_or_404(db_session, context.world_id, user_id)
    if (
        membership.role == AuthRole.WORLD_ADMIN.value
        and _world_admin_count(
            db_session,
            context.world_id,
        )
        <= 1
    ):
        raise _conflict("Cannot remove the final world admin")
    db_session.delete(membership)
    response.status_code = status.HTTP_204_NO_CONTENT


@router.get("/{world_id}/agents", response_model=list[AgentResponse])
def list_agents(
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[AgentResponse]:
    agents = db_session.scalars(
        select(Agent).where(Agent.world_id == context.world_id).order_by(Agent.agent_key),
    ).all()
    return [_agent_response(agent) for agent in agents]


@router.get(
    "/{world_id}/agents/{agent_id}/calendar",
    response_model=list[CalendarEntryResponse],
)
def list_agent_calendar(
    agent_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[CalendarEntryResponse]:
    _agent_or_404(db_session, context.world_id, agent_id)
    return [
        _calendar_entry_response(entry)
        for entry in CalendarService(db_session).list_entries(context.world_id, agent_id)
    ]


@router.post(
    "/{world_id}/agents/{agent_id}/calendar",
    response_model=CalendarEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_agent_calendar_entry(
    agent_id: uuid.UUID,
    entry_create: CalendarEntryCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> CalendarEntryResponse:
    require_csrf(request)
    _agent_or_404(db_session, context.world_id, agent_id)
    return _calendar_entry_response(
        CalendarService(db_session).create_entry(
            CalendarEntryCreate(
                world_id=context.world_id,
                agent_id=agent_id,
                title=entry_create.title,
                description=entry_create.description,
                starts_at=entry_create.starts_at,
                ends_at=entry_create.ends_at,
                recurrence_rule=entry_create.recurrence_rule,
                metadata=entry_create.metadata,
            ),
        ),
    )


@router.patch(
    "/{world_id}/agents/{agent_id}/calendar/{entry_id}",
    response_model=CalendarEntryResponse,
)
def update_agent_calendar_entry(
    agent_id: uuid.UUID,
    entry_id: uuid.UUID,
    entry_update: CalendarEntryUpdateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> CalendarEntryResponse:
    require_csrf(request)
    _agent_or_404(db_session, context.world_id, agent_id)
    entry = _calendar_entry_or_404(db_session, context.world_id, agent_id, entry_id)
    try:
        return _calendar_entry_response(
            CalendarService(db_session).update_entry(
                entry,
                CalendarEntryUpdate(
                    title=entry_update.title,
                    description=entry_update.description,
                    starts_at=entry_update.starts_at,
                    ends_at=entry_update.ends_at,
                    recurrence_rule=entry_update.recurrence_rule,
                    status=None
                    if entry_update.status is None
                    else CalendarEntryStatus(entry_update.status),
                    metadata=entry_update.metadata,
                ),
            ),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{world_id}/agents/{agent_id}/calendar/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def cancel_agent_calendar_entry(
    agent_id: uuid.UUID,
    entry_id: uuid.UUID,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> None:
    require_csrf(request)
    _agent_or_404(db_session, context.world_id, agent_id)
    CalendarService(db_session).cancel_entry(
        _calendar_entry_or_404(db_session, context.world_id, agent_id, entry_id),
    )


@router.get(
    "/{world_id}/agents/{agent_id}/memory",
    response_model=list[MemoryItemResponse],
)
def list_agent_memory(
    agent_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[MemoryItemResponse]:
    _agent_or_404(db_session, context.world_id, agent_id)
    memory_service = MemoryService(db_session, load_settings())
    return [
        _memory_item_response(item)
        for item in memory_service.list_memories(context.world_id, agent_id)
    ]


@router.post(
    "/{world_id}/agents/{agent_id}/memory/search",
    response_model=list[MemoryItemResponse],
)
def search_agent_memory(
    agent_id: uuid.UUID,
    search_request: MemorySearchRequest,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[MemoryItemResponse]:
    _agent_or_404(db_session, context.world_id, agent_id)
    memory_service = MemoryService(db_session, load_settings())
    return [
        _memory_item_response(item)
        for item in memory_service.search(
            MemoryLookupRequest(
                world_id=context.world_id,
                agent_id=agent_id,
                query_text=search_request.query_text,
                limit=search_request.limit,
            )
        ).items
    ]


@router.get(
    "/{world_id}/agents/{agent_id}/memory/profile-snapshot",
    response_model=MemoryProfileSnapshotResponse | None,
)
def get_agent_memory_profile_snapshot(
    agent_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MemoryProfileSnapshotResponse | None:
    _agent_or_404(db_session, context.world_id, agent_id)
    snapshot = MemoryService(db_session, load_settings()).get_profile_snapshot(
        context.world_id,
        agent_id,
    )
    return None if snapshot is None else _memory_profile_snapshot_response(snapshot)


@router.post(
    "/{world_id}/agents/{agent_id}/memory/profile-snapshot/refresh",
    response_model=MemoryProfileSnapshotResponse,
)
def refresh_agent_memory_profile_snapshot(
    agent_id: uuid.UUID,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MemoryProfileSnapshotResponse:
    require_csrf(request)
    _agent_or_404(db_session, context.world_id, agent_id)
    snapshot = MemoryService(db_session, load_settings()).refresh_profile_snapshot(
        context.world_id,
        agent_id,
    )
    return _memory_profile_snapshot_response(snapshot)


@router.post(
    "/{world_id}/agents/{agent_id}/memory/forget",
    response_model=MemoryDeleteResponse,
)
def forget_agent_memory(
    agent_id: uuid.UUID,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MemoryDeleteResponse:
    require_csrf(request)
    _agent_or_404(db_session, context.world_id, agent_id)
    result = MemoryService(db_session, load_settings()).delete_scope(
        MemoryDeleteScope(world_id=context.world_id, agent_id=agent_id),
    )
    return MemoryDeleteResponse(backend=result.backend, deleted_count=result.deleted_count)


@router.get(
    "/{world_id}/agents/{agent_id}/persona",
    response_model=AgentPersonaResponse | None,
)
def get_agent_persona(
    agent_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AgentPersonaResponse | None:
    _agent_or_404(db_session, context.world_id, agent_id)
    persona = AgentPersonaService(db_session).get(context.world_id, agent_id)
    return None if persona is None else _agent_persona_response(persona)


@router.patch(
    "/{world_id}/agents/{agent_id}/persona",
    response_model=AgentPersonaResponse,
)
def upsert_agent_persona(
    agent_id: uuid.UUID,
    persona_update: AgentPersonaUpdateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AgentPersonaResponse:
    require_csrf(request)
    _agent_or_404(db_session, context.world_id, agent_id)
    validation = _validate_persona_policy(persona_update)
    if not validation.valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=[issue.model_dump() for issue in validation.issues],
        )
    return _agent_persona_response(
        AgentPersonaService(db_session).upsert(
            AgentPersonaUpsert(
                world_id=context.world_id,
                agent_id=agent_id,
                persona_text=persona_update.persona_text,
                behavior_policy=persona_update.behavior_policy,
                policy_plugin_identifier=persona_update.policy_plugin_identifier,
                policy_plugin_config=persona_update.policy_plugin_config,
                is_enabled=persona_update.is_enabled,
            ),
        ),
    )


@router.post(
    "/{world_id}/agents/{agent_id}/persona/validate",
    response_model=PersonaPolicyValidationResponse,
)
def validate_agent_persona(
    agent_id: uuid.UUID,
    persona_update: AgentPersonaUpdateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> PersonaPolicyValidationResponse:
    require_csrf(request)
    _agent_or_404(db_session, context.world_id, agent_id)
    return _validate_persona_policy(persona_update)


@router.get(
    "/{world_id}/agents/{agent_id}/observations",
    response_model=list[AgentObservationResponse],
)
def list_agent_observations(
    agent_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[AgentObservationResponse]:
    _agent_or_404(db_session, context.world_id, agent_id)
    return [
        _agent_observation_response(observation)
        for observation in AgentObservationService(db_session).list(
            context.world_id,
            agent_id,
            limit=limit,
        )
    ]


@router.post(
    "/{world_id}/agents/{agent_id}/observations",
    response_model=AgentObservationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_agent_observation(
    agent_id: uuid.UUID,
    observation_create: AgentObservationCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AgentObservationResponse:
    require_csrf(request)
    _agent_or_404(db_session, context.world_id, agent_id)
    return _agent_observation_response(
        AgentObservationService(db_session).create(
            AgentObservationCreate(
                world_id=context.world_id,
                agent_id=agent_id,
                observation_type=observation_create.observation_type,
                content=observation_create.content,
                metadata=observation_create.metadata,
                observed_at=observation_create.observed_at or datetime.now(UTC),
                confidence_score=observation_create.confidence_score,
                review_status=observation_create.review_status,
            ),
        ),
    )


@router.post(
    "/{world_id}/agents/{agent_id}/observations/refresh",
    response_model=list[AgentObservationResponse],
)
def refresh_agent_observations(
    agent_id: uuid.UUID,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[AgentObservationResponse]:
    require_csrf(request)
    _agent_or_404(db_session, context.world_id, agent_id)
    result = AgentObservationService(db_session).refresh_from_events(context.world_id, agent_id)
    return [_agent_observation_response(observation) for observation in result.observations]


@router.get(
    "/{world_id}/agents/{agent_id}/runs",
    response_model=list[AgentRunResponse],
)
def list_agent_runs(
    agent_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[AgentRunResponse]:
    _agent_or_404(db_session, context.world_id, agent_id)
    settings = load_settings()
    orchestrator = AgentRuntimeOrchestrator(
        db_session,
        ProviderProfileService(db_session, settings),
        settings,
    )
    return [_agent_run_response(run) for run in orchestrator.list_runs(context.world_id, agent_id)]


@router.get(
    "/{world_id}/agents/{agent_id}/runs/{run_id}",
    response_model=AgentRunDetailResponse,
)
def get_agent_run_detail(
    agent_id: uuid.UUID,
    run_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AgentRunDetailResponse:
    _agent_or_404(db_session, context.world_id, agent_id)
    settings = load_settings()
    orchestrator = AgentRuntimeOrchestrator(
        db_session,
        ProviderProfileService(db_session, settings),
        settings,
    )
    run = orchestrator.get_run(context.world_id, agent_id, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    provider_profile = (
        None
        if run.provider_profile_id is None
        else ProviderProfileService(db_session, settings).get_profile(run.provider_profile_id)
    )
    turns = db_session.scalars(
        select(ConversationTurn)
        .where(ConversationTurn.run_id == run.run_id)
        .order_by(ConversationTurn.created_at.asc()),
    ).all()
    return AgentRunDetailResponse(
        run=_agent_run_response(run),
        provider_profile=None
        if provider_profile is None
        else AgentRunProviderSummaryResponse(
            id=provider_profile.id,
            profile_key=provider_profile.profile_key,
            name=provider_profile.name,
            provider_type=provider_profile.provider_type.value,
            model_name=provider_profile.model_name,
            is_enabled=provider_profile.is_enabled,
        ),
        conversation_turns=[
            AgentRunConversationTurnResponse(
                id=turn.id,
                session_id=turn.session_id,
                turn_index=turn.turn_index,
                speaker_kind=turn.speaker_kind,
                speaker_agent_id=turn.speaker_agent_id,
                status=turn.status,
                error_text=turn.error_text,
                created_at=turn.created_at,
            )
            for turn in turns
        ],
    )


@router.post(
    "/{world_id}/agents/{agent_id}/run",
    response_model=AgentRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def run_agent(
    agent_id: uuid.UUID,
    run_request: AgentRunRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AgentRunResponse:
    require_csrf(request)
    agent = _agent_or_404(db_session, context.world_id, agent_id)
    settings = load_settings()
    orchestrator = AgentRuntimeOrchestrator(
        db_session,
        ProviderProfileService(db_session, settings),
        settings,
    )
    prompt = run_request.prompt or (
        f"Manual operator run for {agent.display_name}. "
        "Provide one concise operational and narrative update."
    )
    return _agent_run_response(
        orchestrator.run_agent(
            world_id=context.world_id,
            agent_id=agent_id,
            prompt_text=prompt,
            trigger_source="manual",
            provider_profile_id=run_request.provider_profile_id,
            create_memory=run_request.create_memory,
            create_narrative_artifact=run_request.create_narrative_artifact,
        ),
    )


@router.get(
    "/{world_id}/narrative-artifacts",
    response_model=list[NarrativeArtifactResponse],
)
def list_narrative_artifacts(
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    artifact_kind: Annotated[
        Literal["agent_note", "world_summary", "conversation_summary", "chapter_draft"] | None,
        Query(),
    ] = None,
    source_conversation_id: uuid.UUID | None = None,
    q: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    source_kind: Annotated[
        Literal["world", "agent", "agent_run", "conversation"] | None,
        Query(),
    ] = None,
    publication_status: Annotated[Literal["draft", "published"] | None, Query()] = None,
    order_by: Annotated[Literal["created_at", "published_at"], Query()] = "created_at",
    limit: Annotated[int | None, Query(ge=1, le=100)] = None,
) -> list[NarrativeArtifactResponse]:
    can_manage = context.is_platform_admin or context.role == AuthRole.WORLD_ADMIN.value
    return [
        _narrative_artifact_response(artifact)
        for artifact in NarrativeArtifactService(db_session).list_artifacts_with_publications(
            context.world_id,
            artifact_kind=None if artifact_kind is None else NarrativeArtifactKind(artifact_kind),
            source_conversation_id=source_conversation_id,
            search_text=q,
            source_kind=source_kind,
            publication_status=publication_status if can_manage else None,
            order_by=order_by,
            limit=limit,
            published_only=not can_manage,
        )
    ]


@router.get(
    "/{world_id}/narrative-artifacts/{artifact_id}",
    response_model=NarrativeArtifactResponse,
)
def get_narrative_artifact(
    artifact_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> NarrativeArtifactResponse:
    can_manage = context.is_platform_admin or context.role == AuthRole.WORLD_ADMIN.value
    artifact = NarrativeArtifactService(db_session).get_artifact_with_publication(
        context.world_id,
        artifact_id,
        published_only=not can_manage,
    )
    if artifact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Narrative artifact not found",
        )
    return _narrative_artifact_response(artifact)


@router.post(
    "/{world_id}/narrative-artifacts",
    response_model=NarrativeArtifactResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_narrative_artifact(
    artifact_create: NarrativeArtifactCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> NarrativeArtifactResponse:
    require_csrf(request)
    if artifact_create.agent_id is not None:
        _agent_or_404(db_session, context.world_id, artifact_create.agent_id)
    settings = load_settings()
    artifact = AgentRuntimeOrchestrator(
        db_session,
        ProviderProfileService(db_session, settings),
        settings,
    ).create_narrative_artifact(
        world_id=context.world_id,
        agent_id=artifact_create.agent_id,
        title=artifact_create.title,
        content=artifact_create.content,
        artifact_kind=NarrativeArtifactKind(artifact_create.artifact_kind),
    )
    return _narrative_artifact_response(artifact)


@router.post(
    "/{world_id}/narrative-artifacts/{artifact_id}/publish",
    response_model=NarrativePublicationResponse,
)
def publish_narrative_artifact(
    artifact_id: uuid.UUID,
    publication_request: NarrativePublicationRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> NarrativePublicationResponse:
    require_csrf(request)
    try:
        publication = NarrativeArtifactService(db_session).publish_artifact(
            context.world_id,
            artifact_id,
            actor_user_id=context.subject.user_id,
            reader_visible=publication_request.reader_visible,
            metadata=publication_request.metadata,
        )
    except NarrativeArtifactNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Narrative artifact not found",
        ) from exc
    return _narrative_publication_response(publication)


@router.post(
    "/{world_id}/narrative-artifacts/{artifact_id}/unpublish",
    response_model=NarrativePublicationResponse,
)
def unpublish_narrative_artifact(
    artifact_id: uuid.UUID,
    publication_request: NarrativePublicationRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> NarrativePublicationResponse:
    require_csrf(request)
    try:
        publication = NarrativeArtifactService(db_session).unpublish_artifact(
            context.world_id,
            artifact_id,
            metadata=publication_request.metadata,
        )
    except NarrativeArtifactNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Narrative artifact not found",
        ) from exc
    except NarrativePublicationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Narrative publication not found",
        ) from exc
    return _narrative_publication_response(publication)


@router.post(
    "/{world_id}/agents",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_agent(
    agent_create: AgentCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AgentResponse:
    require_csrf(request)
    _ensure_agent_key_available(db_session, context.world_id, agent_create.agent_key)
    if agent_create.home_scene_id is not None:
        _scene_or_404(db_session, context.world_id, agent_create.home_scene_id)
    preset_service = AgentPresetService(db_session)
    preset = _preset_for_agent_create(
        db_session,
        preset_service,
        agent_create.preset_id,
        context.is_platform_admin,
    )
    effective_kind = agent_create.kind or (
        None if preset is None else cast(AgentKind, preset.default_kind)
    )
    if effective_kind is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="kind is required when no preset is supplied",
        )
    preset_provider_profile_id = (
        None
        if preset is None
        else _provider_profile_id_from_profile_key(db_session, preset.default_provider_profile_key)
    )
    if (
        preset is not None
        and preset.default_provider_profile_key is not None
        and preset_provider_profile_id is None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unknown provider profile: {preset.default_provider_profile_key}",
        )
    explicit_provider_profile_id = agent_create.provider_profile_id
    if explicit_provider_profile_id is not None:
        _provider_profile_or_404(db_session, explicit_provider_profile_id)
    agent = Agent(
        id=uuid.uuid4(),
        world_id=context.world_id,
        home_scene_id=agent_create.home_scene_id,
        source_preset_id=None if preset is None else preset.id,
        source_preset_version=None if preset is None else preset.version,
        agent_key=agent_create.agent_key,
        display_name=agent_create.display_name,
        kind=effective_kind,
        config=_agent_config_with_provider_profile_id(
            _materialize_agent_config(preset, agent_create.config),
            explicit_provider_profile_id or preset_provider_profile_id,
        ),
        is_enabled=True,
    )
    db_session.add(agent)
    db_session.flush()
    if preset is not None:
        AgentPersonaService(db_session).upsert(
            AgentPersonaUpsert(
                world_id=context.world_id,
                agent_id=agent.id,
                persona_text=preset.persona_text,
                behavior_policy=preset.behavior_policy,
                is_enabled=True,
            )
        )
        preset_service.materialize_calendar_blueprint(
            world_id=context.world_id,
            agent_id=agent.id,
            blueprint=preset.calendar_blueprint,
        )
    return _agent_response(agent)


@router.patch("/{world_id}/agents/{agent_id}", response_model=AgentResponse)
def update_agent(
    agent_id: uuid.UUID,
    agent_update: AgentUpdateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AgentResponse:
    require_csrf(request)
    agent = _agent_or_404(db_session, context.world_id, agent_id)
    if "display_name" in agent_update.model_fields_set:
        agent.display_name = agent_update.display_name or agent.display_name
    if "kind" in agent_update.model_fields_set and agent_update.kind is not None:
        agent.kind = agent_update.kind
    if "home_scene_id" in agent_update.model_fields_set:
        if agent_update.home_scene_id is not None:
            _scene_or_404(db_session, context.world_id, agent_update.home_scene_id)
        agent.home_scene_id = agent_update.home_scene_id
    if "config" in agent_update.model_fields_set:
        agent.config = agent_update.config or {}
    if "provider_profile_id" in agent_update.model_fields_set:
        if agent_update.provider_profile_id is not None:
            _provider_profile_or_404(db_session, agent_update.provider_profile_id)
        agent.config = _agent_config_with_provider_profile_id(
            agent.config,
            agent_update.provider_profile_id,
        )
    if "is_enabled" in agent_update.model_fields_set:
        agent.is_enabled = bool(agent_update.is_enabled)
    db_session.flush()
    return _agent_response(agent)


@router.delete("/{world_id}/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_agent(
    agent_id: uuid.UUID,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> None:
    require_csrf(request)
    agent = _agent_or_404(db_session, context.world_id, agent_id)
    agent.is_enabled = False
    db_session.flush()


def _world_response(world: World) -> WorldResponse:
    return WorldResponse(
        id=world.id,
        owner_user_id=world.owner_user_id,
        slug=world.slug,
        name=world.name,
        description=world.description,
        rules_config=world.rules_config,
        memory_plugin_identifier=world.memory_plugin_identifier,
        memory_backend_profile_id=world.memory_backend_profile_id,
        memory_plugin_config=world.memory_plugin_config,
        world_rules_plugin_identifier=world.world_rules_plugin_identifier,
        world_rules_plugin_config=world.world_rules_plugin_config,
        is_active=world.is_active,
    )


def _scene_response(scene: Scene) -> SceneResponse:
    return SceneResponse(
        id=scene.id,
        world_id=scene.world_id,
        scene_key=scene.scene_key,
        name=scene.name,
        description=scene.description,
        is_active=scene.is_active,
    )


def _membership_response(membership: WorldMembership, user: User) -> MembershipResponse:
    return MembershipResponse(
        id=membership.id,
        world_id=membership.world_id,
        user_id=membership.user_id,
        role=cast(WorldRole, membership.role),
        user=_user_summary_response(user),
    )


def _user_summary_response(user: User) -> UserSummaryResponse:
    return UserSummaryResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
    )


def _agent_response(agent: Agent) -> AgentResponse:
    return AgentResponse(
        id=agent.id,
        world_id=agent.world_id,
        home_scene_id=agent.home_scene_id,
        source_preset_id=agent.source_preset_id,
        source_preset_version=agent.source_preset_version,
        agent_key=agent.agent_key,
        display_name=agent.display_name,
        kind=cast(AgentKind, agent.kind),
        provider_profile_id=_provider_profile_id_from_config(agent.config),
        config=agent.config,
        is_enabled=agent.is_enabled,
    )


def _agent_preset_response(record: AgentPresetRecord) -> AgentPresetResponse:
    return AgentPresetResponse(
        id=record.id,
        preset_key=record.preset_key,
        name=record.name,
        description=record.description,
        default_kind=cast(AgentKind, record.default_kind),
        default_provider_profile_key=record.default_provider_profile_key,
        persona_text=record.persona_text,
        behavior_policy=record.behavior_policy,
        calendar_blueprint=[
            AgentPresetCalendarEntryResponse(
                title=entry.title,
                description=entry.description,
                starts_at=entry.starts_at,
                ends_at=entry.ends_at,
                recurrence_rule=entry.recurrence_rule,
                metadata=entry.metadata,
            )
            for entry in record.calendar_blueprint
        ],
        advanced_config=record.advanced_config,
        version=record.version,
        is_active=record.is_active,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _agent_preset_update_preview_response(
    preset: AgentPresetRecord,
    agents: Sequence[Agent],
) -> AgentPresetUpdatePreviewResponse:
    agent_rows = [_agent_preset_preview_agent(preset, agent) for agent in agents]
    return AgentPresetUpdatePreviewResponse(
        preset_id=preset.id,
        preset_key=preset.preset_key,
        current_version=preset.version,
        stale_agent_count=sum(1 for row in agent_rows if row.status == "stale"),
        current_agent_count=sum(1 for row in agent_rows if row.status == "current"),
        unversioned_agent_count=sum(1 for row in agent_rows if row.status == "unversioned"),
        agents=agent_rows,
    )


def _agent_preset_preview_agent(
    preset: AgentPresetRecord,
    agent: Agent,
) -> AgentPresetUpdatePreviewAgent:
    if agent.source_preset_version is None:
        preview_status: Literal["current", "stale", "unversioned"] = "unversioned"
    elif agent.source_preset_version < preset.version:
        preview_status = "stale"
    else:
        preview_status = "current"
    return AgentPresetUpdatePreviewAgent(
        agent_id=agent.id,
        world_id=agent.world_id,
        agent_key=agent.agent_key,
        display_name=agent.display_name,
        source_preset_version=agent.source_preset_version,
        status=preview_status,
        changed_fields=_agent_preset_preview_changed_fields(preset, agent),
    )


def _agent_preset_preview_changed_fields(
    preset: AgentPresetRecord,
    agent: Agent,
) -> list[str]:
    fields: list[str] = []
    if agent.kind != preset.default_kind:
        fields.append("kind")
    if _provider_profile_id_from_config(agent.config) is not None:
        fields.append("provider_profile")
    for key, value in preset.advanced_config.items():
        if agent.config.get(key) != value:
            fields.append(f"config.{key}")
    return fields


def _agent_preset_upsert(request: AgentPresetCreateRequest) -> AgentPresetUpsert:
    return AgentPresetUpsert(
        preset_key=request.preset_key,
        name=request.name,
        description=request.description,
        default_kind=request.default_kind,
        default_provider_profile_key=request.default_provider_profile_key,
        persona_text=request.persona_text,
        behavior_policy=request.behavior_policy,
        calendar_blueprint=_preset_calendar_blueprint(request.calendar_blueprint),
        advanced_config=request.advanced_config,
        is_active=request.is_active,
    )


def _preset_calendar_blueprint(
    blueprint: list[AgentPresetCalendarEntryRequest],
) -> list[AgentPresetCalendarEntry]:
    return [
        AgentPresetCalendarEntry(
            title=entry.title,
            description=entry.description,
            starts_at=entry.starts_at,
            ends_at=entry.ends_at,
            recurrence_rule=entry.recurrence_rule,
            metadata=entry.metadata,
        )
        for entry in blueprint
    ]


def _provider_profile_id_from_config(config: dict[str, Any]) -> uuid.UUID | None:
    raw_value = config.get("provider_profile_id")
    if isinstance(raw_value, str):
        try:
            return uuid.UUID(raw_value)
        except ValueError:
            return None
    return None


def _provider_profile_id_from_profile_key(
    db_session: Session,
    profile_key: str | None,
) -> uuid.UUID | None:
    if profile_key is None or profile_key == "":
        return None
    profile = db_session.scalars(
        select(ProviderProfile).where(ProviderProfile.profile_key == profile_key),
    ).one_or_none()
    return None if profile is None else profile.id


def _memory_backend_profile_id_from_profile_key(
    db_session: Session,
    profile_key: str | None,
) -> uuid.UUID | None:
    if profile_key is None or profile_key == "":
        return None
    return db_session.scalars(
        select(MemoryBackendProfile.id).where(MemoryBackendProfile.profile_key == profile_key),
    ).one_or_none()


def _memory_backend_profile_key(
    db_session: Session,
    profile_id: uuid.UUID | None,
) -> str | None:
    if profile_id is None:
        return None
    profile = MemoryBackendProfileService(db_session).get_profile(profile_id)
    return None if profile is None else profile.profile_key


def _validate_world_composition_import(
    db_session: Session,
    import_request: WorldCompositionImportRequest,
) -> WorldCompositionValidationResponse:
    issues: list[WorldCompositionValidationIssue] = []

    def issue(
        severity: Literal["blocking", "warning"],
        code: str,
        field: str,
        message: str,
    ) -> None:
        issues.append(
            WorldCompositionValidationIssue(
                severity=severity,
                code=code,
                field=field,
                message=message,
            )
        )

    if (
        db_session.scalars(select(World.id).where(World.slug == import_request.slug)).first()
        is not None
    ):
        issue("blocking", "slug_collision", "slug", "World slug already exists.")
    owner = db_session.get(User, import_request.owner_user_id)
    if owner is None or not owner.is_active:
        issue(
            "blocking",
            "unknown_owner",
            "owner_user_id",
            "Owner user does not exist or is inactive.",
        )

    world = import_request.composition.world
    if world.memory_backend_profile_key is not None and (
        _memory_backend_profile_id_from_profile_key(db_session, world.memory_backend_profile_key)
        is None
    ):
        issue(
            "blocking",
            "unknown_memory_backend_profile",
            "composition.world.memory_backend_profile_key",
            f"Unknown memory backend profile: {world.memory_backend_profile_key}.",
        )
    if world.memory_plugin_identifier is not None:
        _append_plugin_validation_issue(
            issues,
            category=PluginCategory.MEMORY_BACKEND,
            identifier=world.memory_plugin_identifier,
            raw_config=world.memory_plugin_config,
            field="composition.world.memory_plugin_identifier",
            code_prefix="memory_plugin",
        )
    if world.world_rules_plugin_identifier is not None:
        _append_plugin_validation_issue(
            issues,
            category=PluginCategory.WORLD_RULES,
            identifier=world.world_rules_plugin_identifier,
            raw_config=world.world_rules_plugin_config,
            field="composition.world.world_rules_plugin_identifier",
            code_prefix="world_rules_plugin",
        )

    scene_keys: set[str] = set()
    for index, scene in enumerate(import_request.composition.scenes):
        field = f"composition.scenes[{index}].scene_key"
        if scene.scene_key in scene_keys:
            issue(
                "blocking",
                "duplicate_scene_key",
                field,
                f"Duplicate scene key: {scene.scene_key}.",
            )
        scene_keys.add(scene.scene_key)

    rule_keys: set[str] = set()
    for index, rule in enumerate(import_request.composition.schedule_rules):
        field = f"composition.schedule_rules[{index}].rule_key"
        if rule.rule_key in rule_keys:
            issue(
                "blocking",
                "duplicate_schedule_rule_key",
                field,
                f"Duplicate schedule rule key: {rule.rule_key}.",
            )
        rule_keys.add(rule.rule_key)

    preset_service = AgentPresetService(db_session)
    preset_map: dict[str, AgentPresetRecord] = {}
    for index, preset_reference in enumerate(import_request.composition.preset_references):
        field = f"composition.preset_references[{index}].preset_key"
        preset = preset_service.get_by_key(preset_reference.preset_key, include_inactive=True)
        if preset is None:
            issue(
                "blocking",
                "missing_preset",
                field,
                f"Unknown agent preset: {preset_reference.preset_key}.",
            )
            continue
        preset_map[preset.preset_key] = preset
        if not preset.is_active:
            issue(
                "warning",
                "inactive_preset",
                field,
                f"Agent preset is inactive: {preset_reference.preset_key}.",
            )
        if preset_reference.default_provider_profile_key is not None and (
            _provider_profile_id_from_profile_key(
                db_session,
                preset_reference.default_provider_profile_key,
            )
            is None
        ):
            issue(
                "blocking",
                "unknown_provider_profile",
                f"composition.preset_references[{index}].default_provider_profile_key",
                f"Unknown provider profile: {preset_reference.default_provider_profile_key}.",
            )

    agent_keys: set[str] = set()
    for index, exported_agent in enumerate(import_request.composition.agents):
        if exported_agent.agent_key in agent_keys:
            issue(
                "blocking",
                "duplicate_agent_key",
                f"composition.agents[{index}].agent_key",
                f"Duplicate agent key: {exported_agent.agent_key}.",
            )
        agent_keys.add(exported_agent.agent_key)
        if (
            exported_agent.home_scene_key is not None
            and exported_agent.home_scene_key not in scene_keys
        ):
            issue(
                "blocking",
                "unknown_scene_key",
                f"composition.agents[{index}].home_scene_key",
                f"Unknown scene key: {exported_agent.home_scene_key}.",
            )
        if (
            exported_agent.source_preset_key is not None
            and exported_agent.source_preset_key not in preset_map
        ):
            issue(
                "blocking",
                "missing_preset",
                f"composition.agents[{index}].source_preset_key",
                f"Unknown agent preset: {exported_agent.source_preset_key}.",
            )
        if exported_agent.provider_profile_key is not None and (
            _provider_profile_id_from_profile_key(db_session, exported_agent.provider_profile_key)
            is None
        ):
            issue(
                "blocking",
                "unknown_provider_profile",
                f"composition.agents[{index}].provider_profile_key",
                f"Unknown provider profile: {exported_agent.provider_profile_key}.",
            )

    blocking_issue_count = sum(1 for item in issues if item.severity == "blocking")
    warning_issue_count = len(issues) - blocking_issue_count
    return WorldCompositionValidationResponse(
        valid=blocking_issue_count == 0,
        blocking_issue_count=blocking_issue_count,
        warning_issue_count=warning_issue_count,
        issues=issues,
    )


def _append_plugin_validation_issue(
    issues: list[WorldCompositionValidationIssue],
    *,
    category: PluginCategory,
    identifier: str,
    raw_config: dict[str, Any],
    field: str,
    code_prefix: str,
) -> None:
    try:
        _validate_named_plugin_binding(
            category=category,
            identifier=identifier,
            raw_config=raw_config,
            missing_detail="Plugin is not registered",
            invalid_detail="Plugin config is invalid",
        )
    except HTTPException as exc:
        issues.append(
            WorldCompositionValidationIssue(
                severity="blocking",
                code=(
                    f"{code_prefix}_missing"
                    if exc.status_code == status.HTTP_404_NOT_FOUND
                    else f"{code_prefix}_invalid"
                ),
                field=field,
                message=str(exc.detail),
            )
        )


def _provider_profile_key_map(
    db_session: Session,
    profile_ids: list[uuid.UUID],
) -> dict[uuid.UUID, str]:
    if not profile_ids:
        return {}
    profiles = db_session.scalars(
        select(ProviderProfile).where(ProviderProfile.id.in_(profile_ids)),
    ).all()
    return {profile.id: profile.profile_key for profile in profiles}


def _provider_profile_key_from_config(
    profile_map: dict[uuid.UUID, str],
    config: dict[str, Any],
) -> str | None:
    profile_id = _provider_profile_id_from_config(config)
    if profile_id is None:
        return None
    return profile_map.get(profile_id)


def _source_preset_key(
    preset_map: dict[uuid.UUID, AgentPreset],
    source_preset_id: uuid.UUID | None,
) -> str | None:
    if source_preset_id is None:
        return None
    preset = preset_map.get(source_preset_id)
    return None if preset is None else preset.preset_key


def _provider_profile_or_404(
    db_session: Session,
    profile_id: uuid.UUID,
) -> ProviderProfile:
    profile = db_session.get(ProviderProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return profile


def _validate_world_plugin_bindings(
    *,
    memory_plugin_identifier: str,
    memory_plugin_config: dict[str, Any],
    world_rules_plugin_identifier: str,
    world_rules_plugin_config: dict[str, Any],
) -> None:
    _validate_named_plugin_binding(
        category=PluginCategory.MEMORY_BACKEND,
        identifier=memory_plugin_identifier,
        raw_config=memory_plugin_config,
        missing_detail="Memory backend plugin is not registered",
        invalid_detail="Memory backend plugin config is invalid",
    )
    _validate_named_plugin_binding(
        category=PluginCategory.WORLD_RULES,
        identifier=world_rules_plugin_identifier,
        raw_config=world_rules_plugin_config,
        missing_detail="World rules plugin is not registered",
        invalid_detail="World rules plugin config is invalid",
    )


def _resolved_memory_backend_profile_id(
    db_session: Session,
    plugin_identifier: str,
    profile_id: uuid.UUID | None,
) -> uuid.UUID | None:
    service = MemoryBackendProfileService(db_session)
    if profile_id is not None:
        profile = service.get_profile(profile_id)
        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Memory backend profile not found",
            )
        if not profile.is_enabled:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Memory backend profile is disabled",
            )
        return cast(uuid.UUID, profile.id)
    if plugin_identifier == BUILTIN_MEM0_OSS_MEMORY:
        profile = service.first_enabled_profile()
        return None if profile is None else cast(uuid.UUID, profile.id)
    return None


def _validate_named_plugin_binding(
    *,
    category: PluginCategory,
    identifier: str,
    raw_config: dict[str, Any],
    missing_detail: str,
    invalid_detail: str,
) -> None:
    registry = get_builtin_plugin_registry()
    try:
        definition = registry.get(identifier)
    except PluginNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=missing_detail) from exc
    if definition.manifest.category is not category:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=invalid_detail,
        )
    try:
        registry.validate_config(identifier, raw_config)
    except PluginConfigValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=invalid_detail,
        ) from exc


def _validate_persona_policy(
    persona_update: AgentPersonaUpdateRequest,
) -> PersonaPolicyValidationResponse:
    issues: list[PersonaPolicyValidationIssue] = []
    if persona_update.is_enabled and persona_update.persona_text.strip() == "":
        issues.append(
            PersonaPolicyValidationIssue(
                field="persona_text",
                message="Enabled persona policy requires persona text.",
            ),
        )
    disabled = persona_update.behavior_policy.get("disabled")
    required = persona_update.behavior_policy.get("required")
    if isinstance(disabled, list) and isinstance(required, list):
        overlap = {str(item) for item in disabled} & {str(item) for item in required}
        if overlap:
            issues.append(
                PersonaPolicyValidationIssue(
                    field="behavior_policy",
                    message=(
                        "Behavior policy has contradictory disabled/required values: "
                        f"{sorted(overlap)}."
                    ),
                ),
            )
    try:
        _validate_named_plugin_binding(
            category=PluginCategory.PERSONA_POLICY,
            identifier=persona_update.policy_plugin_identifier,
            raw_config=persona_update.policy_plugin_config,
            missing_detail="Persona policy plugin is not registered",
            invalid_detail="Persona policy plugin config is invalid",
        )
    except HTTPException as exc:
        issues.append(
            PersonaPolicyValidationIssue(
                field="policy_plugin_identifier",
                message=str(exc.detail),
            ),
        )
    return PersonaPolicyValidationResponse(valid=len(issues) == 0, issues=issues)


def _create_plugin_binding(
    *,
    category: PluginCategory,
    identifier: str,
    raw_config: dict[str, Any],
    missing_detail: str,
    invalid_detail: str,
) -> object:
    _validate_named_plugin_binding(
        category=category,
        identifier=identifier,
        raw_config=raw_config,
        missing_detail=missing_detail,
        invalid_detail=invalid_detail,
    )
    return get_builtin_plugin_registry().create(identifier, raw_config)


def _preset_for_agent_create(
    db_session: Session,
    preset_service: AgentPresetService,
    preset_id: uuid.UUID | None,
    include_inactive: bool,
) -> AgentPresetRecord | None:
    if preset_id is None:
        return None
    preset = preset_service.get(preset_id, include_inactive=include_inactive)
    if preset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return preset


def _materialize_agent_config(
    preset: AgentPresetRecord | None,
    explicit_config: dict[str, Any],
) -> dict[str, Any]:
    next_config = dict(preset.advanced_config if preset is not None else {})
    next_config.update(explicit_config)
    return next_config


def _agent_config_with_provider_profile_id(
    config: dict[str, Any],
    provider_profile_id: uuid.UUID | None,
) -> dict[str, Any]:
    next_config = dict(config)
    if provider_profile_id is None:
        next_config.pop("provider_profile_id", None)
    else:
        next_config["provider_profile_id"] = str(provider_profile_id)
    return next_config


def _calendar_entry_response(entry: CalendarEntryResponse | Any) -> CalendarEntryResponse:
    return CalendarEntryResponse(
        id=entry.id,
        world_id=entry.world_id,
        agent_id=entry.agent_id,
        title=entry.title,
        description=entry.description,
        starts_at=entry.starts_at,
        ends_at=entry.ends_at,
        recurrence_rule=entry.recurrence_rule,
        status=entry.status.value if hasattr(entry.status, "value") else str(entry.status),
        metadata=entry.metadata,
    )


def _schedule_rule_response(rule: ScheduleRuleResponse | Any) -> ScheduleRuleResponse:
    return ScheduleRuleResponse(
        id=rule.id,
        world_id=rule.world_id,
        rule_key=rule.rule_key,
        name=rule.name,
        kind=rule.kind.value if hasattr(rule.kind, "value") else str(rule.kind),
        config=rule.config,
        is_enabled=rule.is_enabled,
    )


def _schedule_rule_preview_response(
    world_id: uuid.UUID,
    preview: ScheduleRulePreviewResult,
    affected_agent_ids: list[uuid.UUID],
) -> ScheduleRulePreviewResponse:
    return ScheduleRulePreviewResponse(
        world_id=world_id,
        kind=preview.kind.value,
        config=preview.config,
        start_world_time=preview.start_world_time,
        horizon_hours=preview.horizon_hours,
        match_count=preview.match_count,
        affected_agent_count=len(affected_agent_ids),
        affected_agent_ids=affected_agent_ids,
        matches=[
            ScheduleRulePreviewMatchResponse(
                world_time=match.world_time,
                reason=match.reason,
                affected_agent_count=len(affected_agent_ids),
                affected_agent_ids=affected_agent_ids,
            )
            for match in preview.matches
        ],
    )


def _calendar_conflict_report_response(
    report: CalendarConflictReport,
) -> CalendarConflictReportResponse:
    return CalendarConflictReportResponse(
        world_id=report.world_id,
        start_world_time=report.start_world_time,
        horizon_hours=report.horizon_hours,
        conflict_count=report.conflict_count,
        conflicts=[
            _calendar_conflict_response(conflict)
            for conflict in report.conflicts
        ],
    )


def _calendar_conflict_response(
    conflict: CalendarConflictRecord,
) -> CalendarConflictResponse:
    return CalendarConflictResponse(
        conflict_type=conflict.conflict_type,
        world_id=conflict.world_id,
        agent_id=conflict.agent_id,
        starts_at=conflict.starts_at,
        ends_at=conflict.ends_at,
        reason=conflict.reason,
        sources=[_calendar_conflict_source_response(source) for source in conflict.sources],
    )


def _calendar_conflict_source_response(
    source: CalendarConflictSource,
) -> CalendarConflictSourceResponse:
    return CalendarConflictSourceResponse(
        source_kind=source.source_kind,
        source_id=source.source_id,
        agent_id=source.agent_id,
        label=source.label,
    )


def _memory_item_response(item: MemoryItemRecord) -> MemoryItemResponse:
    return MemoryItemResponse(
        id=item.id,
        world_id=item.world_id,
        agent_id=item.agent_id,
        content=item.content,
        metadata=item.metadata,
        backend=item.backend,
        created_at=item.created_at,
        score=item.score,
    )


def _memory_profile_snapshot_response(
    snapshot: MemoryProfileSnapshotRecord,
) -> MemoryProfileSnapshotResponse:
    return MemoryProfileSnapshotResponse(**snapshot.model_dump())


def _agent_run_response(run: AgentRunExecution) -> AgentRunResponse:
    return AgentRunResponse(
        run_id=run.run_id,
        world_id=run.world_id,
        agent_id=run.agent_id,
        status=run.status,
        prompt_text=run.prompt_text,
        response_text=run.response_text,
        provider_profile_id=run.provider_profile_id,
        trigger_source=run.trigger_source,
        source_calendar_entry_id=run.source_calendar_entry_id,
        source_schedule_rule_id=run.source_schedule_rule_id,
        created_event_id=run.created_event_id,
        diagnostics=redact_diagnostic_details(run.diagnostics),
        started_at=run.started_at,
        finished_at=run.finished_at,
    )


def _agent_persona_response(persona: AgentPersonaRecord) -> AgentPersonaResponse:
    return AgentPersonaResponse(**persona.model_dump())


def _agent_observation_response(observation: AgentObservationRecord) -> AgentObservationResponse:
    return AgentObservationResponse(**observation.model_dump())


def _narrative_artifact_response(
    artifact: NarrativeArtifactRecord | NarrativeArtifactWithPublication,
) -> NarrativeArtifactResponse:
    if isinstance(artifact, NarrativeArtifactWithPublication):
        publication = artifact.publication
        artifact_record = artifact.artifact
    else:
        publication = None
        artifact_record = artifact
    return NarrativeArtifactResponse(
        id=artifact_record.id,
        world_id=artifact_record.world_id,
        agent_id=artifact_record.agent_id,
        source_run_id=artifact_record.source_run_id,
        source_conversation_id=artifact_record.source_conversation_id,
        title=artifact_record.title,
        content=artifact_record.content,
        artifact_kind=artifact_record.artifact_kind.value,
        metadata=artifact_record.metadata,
        created_at=artifact_record.created_at,
        publication=None if publication is None else _narrative_publication_response(publication),
    )


def _narrative_publication_response(
    publication: NarrativePublicationRecord,
) -> NarrativePublicationResponse:
    return NarrativePublicationResponse(
        id=publication.id,
        world_id=publication.world_id,
        artifact_id=publication.artifact_id,
        source_draft_id=publication.source_draft_id,
        status=publication.status.value,
        reader_visible=publication.reader_visible,
        metadata=publication.metadata,
        published_at=publication.published_at,
        unpublished_at=publication.unpublished_at,
        published_by_user_id=publication.published_by_user_id,
        created_at=publication.created_at,
        updated_at=publication.updated_at,
    )


def _clock_response(clock_view: WorldClockView) -> WorldClockResponse:
    state = clock_view.state
    return WorldClockResponse(
        world_id=state.world_id,
        status=state.status.value,
        current_world_time=state.current_world_time,
        effective_world_time=clock_view.effective_world_time,
        wall_time_anchor=state.wall_time_anchor,
        speed_multiplier=str(state.speed_multiplier),
        revision=state.revision,
    )


def _clock_transition_response(
    transition: WorldClockTransitionModel,
) -> WorldClockTransitionResponse:
    return WorldClockTransitionResponse(
        id=transition.id,
        world_id=transition.world_id,
        transition_type=transition.transition_type,
        previous_status=transition.previous_status,
        new_status=transition.new_status,
        previous_world_time=transition.previous_world_time,
        new_world_time=transition.new_world_time,
        wall_time=transition.wall_time,
        previous_revision=transition.previous_revision,
        new_revision=transition.new_revision,
        actor_ref=transition.actor_ref,
        correlation_id=transition.correlation_id,
        reason=transition.reason,
        created_at=transition.created_at,
    )


def _diagnostic_response(record: RuntimeDiagnosticRecord) -> RuntimeDiagnosticResponse:
    return RuntimeDiagnosticResponse(**record.model_dump())


def _world_event_response(event: WorldEventModel) -> WorldEventResponse:
    return WorldEventResponse(
        id=event.id,
        world_id=event.world_id,
        sequence=event.sequence,
        event_name=event.event_name,
        payload=event.payload,
        wall_time=event.wall_time,
        world_time=event.world_time,
        actor_ref=event.actor_ref,
        causation_event_id=event.causation_event_id,
        correlation_id=event.correlation_id,
        created_at=event.created_at,
    )


def _snapshot_response(snapshot: WorldSnapshotRecord) -> WorldSnapshotResponse:
    return WorldSnapshotResponse(
        id=snapshot.id,
        world_id=snapshot.world_id,
        covers_event_sequence=snapshot.covers_event_sequence,
        schema_version=snapshot.schema_version,
        status=snapshot.status.value,
        payload=snapshot.payload,
        payload_uri=snapshot.payload_uri,
        payload_location=_snapshot_payload_location(snapshot),
        metadata=snapshot.metadata,
        created_by_event_id=snapshot.created_by_event_id,
        created_at=snapshot.created_at,
    )


def _snapshot_payload_location(snapshot: WorldSnapshotRecord) -> str | None:
    if snapshot.payload_uri is not None:
        return "object"
    if snapshot.payload is not None:
        return "inline"
    return None


def _world_or_404(db_session: Session, world_id: uuid.UUID) -> World:
    world = db_session.get(World, world_id)
    if world is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="World not found")
    return world


def _scene_or_404(db_session: Session, world_id: uuid.UUID, scene_id: uuid.UUID) -> Scene:
    scene = db_session.get(Scene, scene_id)
    if scene is None or scene.world_id != world_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene not found")
    return scene


def _agent_or_404(db_session: Session, world_id: uuid.UUID, agent_id: uuid.UUID) -> Agent:
    agent = db_session.get(Agent, agent_id)
    if agent is None or agent.world_id != world_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


def _calendar_entry_or_404(
    db_session: Session,
    world_id: uuid.UUID,
    agent_id: uuid.UUID,
    entry_id: uuid.UUID,
) -> AgentCalendarEntry:
    entry = db_session.get(AgentCalendarEntry, entry_id)
    if entry is None or entry.world_id != world_id or entry.agent_id != agent_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calendar entry not found",
        )
    return entry


def _schedule_rule_or_404(
    db_session: Session,
    world_id: uuid.UUID,
    rule_id: uuid.UUID,
) -> WorldScheduleRule:
    rule = db_session.get(WorldScheduleRule, rule_id)
    if rule is None or rule.world_id != world_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule rule not found")
    return rule


def _user_or_404(db_session: Session, user_id: uuid.UUID) -> User:
    user = db_session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def _membership_or_none(
    db_session: Session,
    world_id: uuid.UUID,
    user_id: uuid.UUID,
) -> WorldMembership | None:
    return db_session.scalars(
        select(WorldMembership).where(
            WorldMembership.world_id == world_id,
            WorldMembership.user_id == user_id,
        ),
    ).one_or_none()


def _membership_or_404(
    db_session: Session,
    world_id: uuid.UUID,
    user_id: uuid.UUID,
) -> WorldMembership:
    membership = _membership_or_none(db_session, world_id, user_id)
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found")
    return membership


def _upsert_membership(
    db_session: Session,
    world_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str,
) -> WorldMembership:
    membership = _membership_or_none(db_session, world_id, user_id)
    if membership is None:
        membership = WorldMembership(
            id=uuid.uuid4(),
            world_id=world_id,
            user_id=user_id,
            role=role,
        )
        db_session.add(membership)
    else:
        membership.role = role
    return membership


def _world_admin_count(db_session: Session, world_id: uuid.UUID) -> int:
    return (
        db_session.scalar(
            select(func.count())
            .select_from(WorldMembership)
            .where(
                WorldMembership.world_id == world_id,
                WorldMembership.role == AuthRole.WORLD_ADMIN.value,
            ),
        )
        or 0
    )


def _ensure_slug_available(db_session: Session, slug: str) -> None:
    if db_session.scalars(select(World.id).where(World.slug == slug)).first() is not None:
        raise _conflict("World slug already exists")


def _ensure_scene_key_available(db_session: Session, world_id: uuid.UUID, scene_key: str) -> None:
    if (
        db_session.scalars(
            select(Scene.id).where(Scene.world_id == world_id, Scene.scene_key == scene_key),
        ).first()
        is not None
    ):
        raise _conflict("Scene key already exists")


def _ensure_agent_key_available(db_session: Session, world_id: uuid.UUID, agent_key: str) -> None:
    if (
        db_session.scalars(
            select(Agent.id).where(Agent.world_id == world_id, Agent.agent_key == agent_key),
        ).first()
        is not None
    ):
        raise _conflict("Agent key already exists")


def _ensure_preset_key_available(
    db_session: Session,
    preset_key: str,
    *,
    preset_id: uuid.UUID | None = None,
) -> None:
    existing_id = db_session.scalars(
        select(AgentPreset.id).where(AgentPreset.preset_key == preset_key),
    ).one_or_none()
    if existing_id is not None and existing_id != preset_id:
        raise _conflict("Preset key already exists")


def _ensure_schedule_rule_key_available(
    db_session: Session,
    world_id: uuid.UUID,
    rule_key: str,
) -> None:
    if (
        db_session.scalars(
            select(WorldScheduleRule.id).where(
                WorldScheduleRule.world_id == world_id,
                WorldScheduleRule.rule_key == rule_key,
            ),
        ).first()
        is not None
    ):
        raise _conflict("Schedule rule key already exists")


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _clock_conflict(error: WorldClockError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


def _actor_ref(subject: AuthenticatedSubject) -> str:
    return f"user:{subject.user_id}"


def _timezone_aware(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _optional_query_time(value: datetime | None, field_name: str) -> datetime | None:
    if value is None:
        return None
    try:
        return _timezone_aware(value, field_name)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
