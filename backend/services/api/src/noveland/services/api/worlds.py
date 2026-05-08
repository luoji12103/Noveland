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
from noveland.agents.models import Agent, AgentPreset, AgentRelationshipEdge
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
    WorldEventAppend,
    WorldEventImportance,
    WorldEventStore,
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
    NarrativePublicationBlockedError,
    NarrativePublicationNotFoundError,
    NarrativePublicationRecord,
)
from noveland.narrative.models import NarrativeArtifact
from noveland.observability import (
    DiagnosticComponent,
    DiagnosticSeverity,
    RuntimeDiagnosticCreate,
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
from noveland.worlds.autonomous import LivingWorldAutonomyService
from noveland.worlds.beta import EndingDryRun, LivingWorldBetaService
from noveland.worlds.clock import WorldClockError
from noveland.worlds.clock_service import WorldClockService, WorldClockView
from noveland.worlds.gm import LivingWorldGMService, ResolutionRuleDryRun, WorldlineComparison
from noveland.worlds.guardrails import LivingWorldDashboard, LivingWorldGuardrailService
from noveland.worlds.models import (
    AgentPresenceState,
    AuthoringImportJob,
    AuthoringTemplate,
    BetaChecklistItem,
    BetaChecklistRun,
    CharacterEmotionalState,
    CharacterKnowledgeFact,
    DailyEpisodeDraft,
    DailyLifeEventCandidate,
    EndingCandidate,
    EventResolutionRule,
    EventTriggerCondition,
    FactionProgressTrack,
    GMAgenda,
    GMEventProposal,
    GMStyleReview,
    GroupInteractionContext,
    InWorldNotification,
    LivingWorldReleaseProfile,
    LongRunEvalRun,
    NarrativeContinuityReview,
    OffscreenEventQueueItem,
    OrganizationConflictEvent,
    OrganizationMembership,
    PlayerActorProfile,
    PlayerChoiceRecord,
    PlayerInterventionRecord,
    PlayerJournalEntry,
    PlotThread,
    RelationshipEventSuggestion,
    RelationshipRepairRecord,
    RouteAffinity,
    RouteMilestone,
    RumorPropagation,
    RumorRecord,
    Scene,
    SceneBeatDraft,
    SceneLocationEdge,
    SecretRecord,
    StoryHook,
    World,
    WorldBible,
    WorldClockTransitionModel,
    Worldline,
    WorldMembership,
    WorldOrganization,
)
from noveland.worlds.plot import LivingWorldPlotService, TriggerDryRun
from noveland.worlds.worldlines import ensure_primary_worldline
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

SLUG_PATTERN = r"^[a-z0-9][a-z0-9-]{1,78}[a-z0-9]$"
SLUG_RE = re.compile(SLUG_PATTERN)

WorldRole = Literal["world_admin", "human_user"]
AgentKind = Literal["role_agent", "narrative_agent"]
ContinuityStatus = Literal["canon", "post_canon", "alternate", "original_expansion"]
NarrativeRole = Literal[
    "protagonist",
    "main_character",
    "side_character",
    "supporting_cast",
    "ordinary_member",
    "organization_member",
    "original_character",
    "narrative_agent",
]
CharacterImportance = Literal["lead", "major", "minor", "background"]
CharacterCategory = Literal[
    "player",
    "main_character",
    "side_character",
    "ordinary_member",
    "organization_member",
    "original_character",
    "narrative_agent",
]
RelationshipType = Literal[
    "affection",
    "friendship",
    "rivalry",
    "family",
    "alliance",
    "hostility",
    "obligation",
    "debt",
    "secret",
    "custom",
]
OrganizationType = Literal[
    "school", "club", "family", "company", "faction", "secret_group", "other"
]
OrganizationVisibility = Literal["public", "hidden"]
FactionTrackType = Literal["goal", "conflict", "resource", "reputation", "risk"]
PresenceVisibilityStatus = Literal["visible", "offscreen", "hidden", "unavailable"]
EventImportance = Literal["system", "daily", "relationship", "organization", "route", "main_plot"]
OffscreenEventStatus = Literal["pending", "resolved", "cancelled", "failed"]
DailyLifeCandidateStatus = Literal["candidate", "queued", "dismissed"]
WorldlineStatus = Literal["active", "archived"]
GMAgendaStatus = Literal["active", "paused", "completed", "archived"]
GMProposalStatus = Literal["proposed", "accepted", "rejected", "resolved"]
ResolutionRuleStatus = Literal["active", "inactive"]
PlayerChoiceKind = Literal["dialogue", "travel", "contact", "intervention", "route"]
StoryHookType = Literal["promise", "foreshadowing", "mystery", "agreement", "flag"]
StoryHookStatus = Literal["open", "resolved", "cancelled"]
PlotThreadType = Literal["personal", "organization", "daily", "main", "hidden"]
PlotThreadStatus = Literal["active", "dormant", "completed", "archived"]
RouteStatus = Literal["locked", "available", "active", "completed", "blocked"]
TriggerConditionStatus = Literal["active", "inactive"]
SceneBeatStatus = Literal["draft", "approved", "published", "archived"]
DailyEpisodeStatus = Literal["draft", "queued", "published", "archived"]
GroupInteractionType = Literal["club", "class", "organization_meeting", "conflict", "casual"]
GroupInteractionStatus = Literal["planned", "active", "completed", "archived"]
SuggestionStatus = Literal["suggested", "accepted", "dismissed"]
OrganizationConflictStatus = Literal["proposed", "resolved", "dismissed"]
RumorStatus = Literal["active", "resolved", "false", "archived"]
RumorVisibility = Literal["private", "group", "public"]
RumorPropagationStatus = Literal["pending", "delivered", "blocked"]
KnowledgeKind = Literal["fact", "secret", "guess", "misbelief"]
KnowledgeVisibility = Literal["private", "shared", "public"]
SecretVisibility = Literal["private", "holders", "public"]
SecretStatus = Literal["hidden", "revealed", "archived"]
RelationshipRepairKind = Literal[
    "decay", "repair", "conflict", "apology", "kept_promise", "shared_event"
]
RelationshipRepairStatus = Literal["proposed", "applied", "dismissed"]
JournalEntryKind = Literal["choice", "relationship", "event", "narrative", "private_note"]
JournalVisibility = Literal["player_private", "world_admin"]
NotificationKind = Literal["message", "invitation", "rumor", "promise", "incident", "intervention"]
NotificationStatus = Literal["unread", "read", "archived"]
InterventionKind = Literal["observe", "reply", "travel", "contact", "push_event"]
InterventionStatus = Literal["recorded", "resolved", "cancelled"]
ReviewStatus = Literal["pass", "warning", "fail"]
RouteMilestoneStatus = Literal["planned", "active", "completed", "blocked"]
EndingType = Literal["normal", "bad", "hidden", "epilogue"]
EndingStatus = Literal["planned", "available", "locked", "achieved", "retired"]
LongRunEvalStatus = Literal["completed", "warning", "failed"]
AuthoringTemplateKind = Literal["source_notes", "character", "event", "route", "world_bundle"]
AuthoringImportStatus = Literal["preview", "applied", "failed"]
ReleaseProfileStatus = Literal["draft", "ready", "blocked", "released"]
BetaChecklistStatus = Literal["pending", "passed", "warning", "blocked"]
BetaChecklistItemStatus = Literal["pending", "passed", "warning", "blocked"]

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
    region_key: str | None = Field(default=None, max_length=80)
    location_tags: list[str] = Field(default_factory=list, max_length=20)
    opening_rules: dict[str, Any] = Field(default_factory=dict)


class SceneUpdateRequest(_RequestModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    region_key: str | None = Field(default=None, max_length=80)
    location_tags: list[str] | None = None
    opening_rules: dict[str, Any] | None = None
    is_active: bool | None = None


class SceneLocationEdgeCreateRequest(_RequestModel):
    source_scene_id: uuid.UUID
    target_scene_id: uuid.UUID
    travel_label: str | None = Field(default=None, max_length=120)
    traversal_rules: dict[str, Any] = Field(default_factory=dict)


class SceneLocationEdgeUpdateRequest(_RequestModel):
    travel_label: str | None = Field(default=None, max_length=120)
    traversal_rules: dict[str, Any] | None = None


class OrganizationCreateRequest(_RequestModel):
    organization_key: str = Field(pattern=SLUG_PATTERN, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    organization_type: OrganizationType
    description: str | None = None
    public_summary: str | None = None
    hidden_summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class OrganizationUpdateRequest(_RequestModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    organization_type: OrganizationType | None = None
    description: str | None = None
    public_summary: str | None = None
    hidden_summary: str | None = None
    metadata: dict[str, Any] | None = None
    is_active: bool | None = None


class OrganizationMembershipCreateRequest(_RequestModel):
    agent_id: uuid.UUID
    role_title: str | None = Field(default=None, max_length=120)
    visibility: OrganizationVisibility = "public"
    loyalty: int = Field(default=50, ge=0, le=100)
    influence: int = Field(default=50, ge=0, le=100)
    responsibilities: list[str] = Field(default_factory=list, max_length=20)
    metadata: dict[str, Any] = Field(default_factory=dict)


class OrganizationMembershipUpdateRequest(_RequestModel):
    role_title: str | None = Field(default=None, max_length=120)
    visibility: OrganizationVisibility | None = None
    loyalty: int | None = Field(default=None, ge=0, le=100)
    influence: int | None = Field(default=None, ge=0, le=100)
    responsibilities: list[str] | None = None
    metadata: dict[str, Any] | None = None


class FactionProgressTrackCreateRequest(_RequestModel):
    worldline_id: uuid.UUID | None = None
    track_key: str = Field(pattern=SLUG_PATTERN, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    track_type: FactionTrackType
    progress: int = Field(default=0, ge=0, le=100)
    pressure: int = Field(default=0, ge=0, le=100)
    summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class FactionProgressTrackUpdateRequest(_RequestModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    track_type: FactionTrackType | None = None
    progress: int | None = Field(default=None, ge=0, le=100)
    pressure: int | None = Field(default=None, ge=0, le=100)
    summary: str | None = None
    metadata: dict[str, Any] | None = None


class AgentPresenceUpdateRequest(_RequestModel):
    worldline_id: uuid.UUID | None = None
    current_scene_id: uuid.UUID | None = None
    visibility_status: PresenceVisibilityStatus = "visible"
    encounter_eligible: bool = True
    scheduled_movement: dict[str, Any] = Field(default_factory=dict)


class DailyLifeGenerateRequest(_RequestModel):
    worldline_id: uuid.UUID | None = None
    horizon_hours: int = Field(default=24, ge=1, le=168)
    limit: int = Field(default=20, ge=1, le=100)


class OffscreenQueueCreateRequest(_RequestModel):
    candidate_id: uuid.UUID | None = None
    worldline_id: uuid.UUID | None = None
    event_name: str = Field(default="living_world.offscreen_event", min_length=3, max_length=120)
    title: str = Field(min_length=1, max_length=160)
    payload: dict[str, Any] = Field(default_factory=dict)
    due_at: datetime
    importance: Literal["daily", "relationship", "organization", "route", "main_plot"] = "daily"

    @field_validator("due_at", mode="after")
    @classmethod
    def due_at_must_be_timezone_aware(cls, value: datetime) -> datetime:
        return _timezone_aware(value, "due_at")


class WorldBibleUpsertRequest(_RequestModel):
    source_material: str = Field(default="", max_length=80_000)
    canon_timeline: list[dict[str, Any]] = Field(default_factory=list)
    setting_rules: dict[str, Any] = Field(default_factory=dict)
    forbidden_changes: list[dict[str, Any]] = Field(default_factory=list)
    sequel_boundaries: dict[str, Any] = Field(default_factory=dict)
    continuity_config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("continuity_config", mode="after")
    @classmethod
    def continuity_config_status_is_known(cls, value: dict[str, Any]) -> dict[str, Any]:
        _validate_continuity_metadata(value, "continuity_config")
        return value


class WorldlineForkRequest(_RequestModel):
    source_worldline_id: uuid.UUID | None = None
    worldline_key: str = Field(pattern=SLUG_PATTERN, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    forked_from_snapshot_id: uuid.UUID | None = None
    fork_event_sequence: int | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GMAgendaCreateRequest(_RequestModel):
    worldline_id: uuid.UUID | None = None
    title: str = Field(min_length=1, max_length=160)
    summary: str = Field(min_length=1, max_length=12_000)
    priority: int = Field(default=50, ge=0, le=100)
    focus_agents: list[str] = Field(default_factory=list, max_length=50)
    focus_organizations: list[str] = Field(default_factory=list, max_length=50)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GMAgendaUpdateRequest(_RequestModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    summary: str | None = Field(default=None, min_length=1, max_length=12_000)
    priority: int | None = Field(default=None, ge=0, le=100)
    status: GMAgendaStatus | None = None
    focus_agents: list[str] | None = None
    focus_organizations: list[str] | None = None
    metadata: dict[str, Any] | None = None


class GMProposalCreateRequest(_RequestModel):
    worldline_id: uuid.UUID | None = None
    agenda_id: uuid.UUID | None = None
    title: str = Field(min_length=1, max_length=160)
    reason: str = Field(min_length=1, max_length=12_000)
    event_name: str = Field(min_length=3, max_length=120)
    proposed_payload: dict[str, Any] = Field(default_factory=dict)
    importance: Literal["daily", "relationship", "organization", "route", "main_plot"] = "daily"
    risk_score: int = Field(default=0, ge=0, le=100)
    affected_agents: list[str] = Field(default_factory=list, max_length=50)
    affected_organizations: list[str] = Field(default_factory=list, max_length=50)
    source_context: dict[str, Any] = Field(default_factory=dict)


class GMProposalReviewRequest(_RequestModel):
    status: GMProposalStatus
    review_note: str | None = Field(default=None, max_length=2000)


class EventResolutionRuleCreateRequest(_RequestModel):
    rule_key: str = Field(pattern=SLUG_PATTERN, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    priority: int = Field(default=50, ge=0, le=100)
    conditions: dict[str, Any] = Field(default_factory=dict)
    effects: dict[str, Any] = Field(default_factory=dict)


class EventResolutionRuleUpdateRequest(_RequestModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    priority: int | None = Field(default=None, ge=0, le=100)
    status: ResolutionRuleStatus | None = None
    conditions: dict[str, Any] | None = None
    effects: dict[str, Any] | None = None


class PlayerActorBindRequest(_RequestModel):
    worldline_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    display_name: str = Field(min_length=1, max_length=160)
    current_scene_id: uuid.UUID | None = None
    profile: dict[str, Any] = Field(default_factory=dict)


class PlayerChoiceCreateRequest(_RequestModel):
    worldline_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    player_actor_id: uuid.UUID
    choice_key: str = Field(min_length=1, max_length=120)
    choice_kind: PlayerChoiceKind
    prompt: str = Field(min_length=1, max_length=12_000)
    selected_option: str = Field(min_length=1, max_length=12_000)
    context: dict[str, Any] = Field(default_factory=dict)
    effects: dict[str, Any] = Field(default_factory=dict)
    apply: bool = True


class StoryHookCreateRequest(_RequestModel):
    worldline_id: uuid.UUID | None = None
    hook_key: str = Field(pattern=SLUG_PATTERN, max_length=120)
    title: str = Field(min_length=1, max_length=160)
    hook_type: StoryHookType
    summary: str = Field(min_length=1, max_length=12_000)
    priority: int = Field(default=50, ge=0, le=100)
    owner_agent_id: uuid.UUID | None = None
    target_agent_id: uuid.UUID | None = None
    due_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("due_at", mode="after")
    @classmethod
    def due_at_must_be_timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return _timezone_aware(value, "due_at")


class StoryHookUpdateRequest(_RequestModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    summary: str | None = Field(default=None, min_length=1, max_length=12_000)
    status: StoryHookStatus | None = None
    priority: int | None = Field(default=None, ge=0, le=100)
    owner_agent_id: uuid.UUID | None = None
    target_agent_id: uuid.UUID | None = None
    due_at: datetime | None = None
    resolution: str | None = Field(default=None, max_length=12_000)
    metadata: dict[str, Any] | None = None

    @field_validator("due_at", mode="after")
    @classmethod
    def due_at_must_be_timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return _timezone_aware(value, "due_at")


class PlotThreadCreateRequest(_RequestModel):
    worldline_id: uuid.UUID | None = None
    thread_key: str = Field(pattern=SLUG_PATTERN, max_length=120)
    title: str = Field(min_length=1, max_length=160)
    thread_type: PlotThreadType
    summary: str = Field(min_length=1, max_length=12_000)
    stakes: str | None = Field(default=None, max_length=12_000)
    next_beats: list[str] = Field(default_factory=list, max_length=50)
    participant_agent_ids: list[str] = Field(default_factory=list, max_length=50)
    organization_ids: list[str] = Field(default_factory=list, max_length=50)
    priority: int = Field(default=50, ge=0, le=100)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlotThreadUpdateRequest(_RequestModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    thread_type: PlotThreadType | None = None
    status: PlotThreadStatus | None = None
    summary: str | None = Field(default=None, min_length=1, max_length=12_000)
    stakes: str | None = Field(default=None, max_length=12_000)
    next_beats: list[str] | None = None
    participant_agent_ids: list[str] | None = None
    organization_ids: list[str] | None = None
    related_event_ids: list[str] | None = None
    priority: int | None = Field(default=None, ge=0, le=100)
    metadata: dict[str, Any] | None = None


class RouteAffinityUpsertRequest(_RequestModel):
    worldline_id: uuid.UUID | None = None
    agent_id: uuid.UUID
    route_key: str = Field(pattern=SLUG_PATTERN, max_length=120)
    status: RouteStatus = "available"
    affinity: int = Field(default=0, ge=-100, le=100)
    stage: int = Field(default=0, ge=0)
    flags: list[str] = Field(default_factory=list, max_length=50)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EventTriggerConditionCreateRequest(_RequestModel):
    condition_key: str = Field(pattern=SLUG_PATTERN, max_length=120)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    priority: int = Field(default=50, ge=0, le=100)
    conditions: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EventTriggerConditionUpdateRequest(_RequestModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    status: TriggerConditionStatus | None = None
    priority: int | None = Field(default=None, ge=0, le=100)
    conditions: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class SceneBeatDraftCreateRequest(_RequestModel):
    worldline_id: uuid.UUID | None = None
    source_kind: Literal["event", "proposal", "daily_episode", "manual"] = "manual"
    source_ref: str | None = Field(default=None, max_length=160)
    title: str = Field(min_length=1, max_length=160)
    participant_agent_ids: list[str] = Field(default_factory=list, max_length=50)
    scene_id: uuid.UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SceneBeatDraftUpdateRequest(_RequestModel):
    status: SceneBeatStatus | None = None
    metadata: dict[str, Any] | None = None


class DailyEpisodeDraftCreateRequest(_RequestModel):
    worldline_id: uuid.UUID | None = None
    source_candidate_id: uuid.UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=160)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DailyEpisodeDraftUpdateRequest(_RequestModel):
    status: DailyEpisodeStatus | None = None
    metadata: dict[str, Any] | None = None


class GroupInteractionCreateRequest(_RequestModel):
    worldline_id: uuid.UUID | None = None
    context_key: str = Field(pattern=SLUG_PATTERN, max_length=120)
    title: str = Field(min_length=1, max_length=160)
    interaction_type: GroupInteractionType
    scene_id: uuid.UUID | None = None
    organization_id: uuid.UUID | None = None
    participant_agent_ids: list[str] = Field(default_factory=list, max_length=50)
    participant_roles: dict[str, Any] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GroupInteractionUpdateRequest(_RequestModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    interaction_type: GroupInteractionType | None = None
    scene_id: uuid.UUID | None = None
    organization_id: uuid.UUID | None = None
    participant_agent_ids: list[str] | None = None
    participant_roles: dict[str, Any] | None = None
    constraints: dict[str, Any] | None = None
    status: GroupInteractionStatus | None = None
    metadata: dict[str, Any] | None = None


class RelationshipSuggestionUpdateRequest(_RequestModel):
    status: SuggestionStatus | None = None
    metadata: dict[str, Any] | None = None


class OrganizationConflictCreateRequest(_RequestModel):
    worldline_id: uuid.UUID | None = None
    organization_id: uuid.UUID
    faction_track_id: uuid.UUID | None = None
    title: str = Field(min_length=1, max_length=160)
    summary: str = Field(min_length=1, max_length=12_000)
    pressure_delta: int = Field(default=0, ge=-100, le=100)
    progress_delta: int = Field(default=0, ge=-100, le=100)
    metadata: dict[str, Any] = Field(default_factory=dict)


class OrganizationConflictUpdateRequest(_RequestModel):
    status: OrganizationConflictStatus | None = None
    metadata: dict[str, Any] | None = None


class RumorCreateRequest(_RequestModel):
    worldline_id: uuid.UUID | None = None
    rumor_key: str = Field(pattern=SLUG_PATTERN, max_length=120)
    title: str = Field(min_length=1, max_length=160)
    content: str = Field(min_length=1, max_length=12_000)
    source_agent_id: uuid.UUID | None = None
    source_organization_id: uuid.UUID | None = None
    visibility: RumorVisibility = "private"
    known_agent_ids: list[str] = Field(default_factory=list, max_length=100)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RumorUpdateRequest(_RequestModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    content: str | None = Field(default=None, min_length=1, max_length=12_000)
    visibility: RumorVisibility | None = None
    known_agent_ids: list[str] | None = None
    status: RumorStatus | None = None
    metadata: dict[str, Any] | None = None


class RumorPropagationCreateRequest(_RequestModel):
    worldline_id: uuid.UUID | None = None
    rumor_id: uuid.UUID
    source_agent_id: uuid.UUID | None = None
    target_agent_id: uuid.UUID | None = None
    target_organization_id: uuid.UUID | None = None
    propagation_reason: str = Field(min_length=1, max_length=12_000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RumorPropagationUpdateRequest(_RequestModel):
    status: RumorPropagationStatus | None = None
    metadata: dict[str, Any] | None = None


class KnowledgeFactUpsertRequest(_RequestModel):
    worldline_id: uuid.UUID | None = None
    agent_id: uuid.UUID
    fact_key: str = Field(pattern=SLUG_PATTERN, max_length=120)
    knowledge_kind: KnowledgeKind = "fact"
    content: str = Field(min_length=1, max_length=12_000)
    confidence: int = Field(default=80, ge=0, le=100)
    visibility: KnowledgeVisibility = "private"
    source_event_id: uuid.UUID | None = None
    source_ref: str | None = Field(default=None, max_length=160)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SecretCreateRequest(_RequestModel):
    worldline_id: uuid.UUID | None = None
    secret_key: str = Field(pattern=SLUG_PATTERN, max_length=120)
    title: str = Field(min_length=1, max_length=160)
    content: str = Field(min_length=1, max_length=12_000)
    holder_agent_ids: list[str] = Field(default_factory=list, max_length=100)
    reveal_conditions: dict[str, Any] = Field(default_factory=dict)
    consequence_metadata: dict[str, Any] = Field(default_factory=dict)
    visibility: SecretVisibility = "holders"
    metadata: dict[str, Any] = Field(default_factory=dict)


class EmotionalStateUpsertRequest(_RequestModel):
    worldline_id: uuid.UUID | None = None
    agent_id: uuid.UUID
    mood: str = Field(default="neutral", min_length=1, max_length=80)
    stress: int = Field(default=0, ge=0, le=100)
    fatigue: int = Field(default=0, ge=0, le=100)
    anticipation: int = Field(default=0, ge=0, le=100)
    jealousy: int = Field(default=0, ge=0, le=100)
    anger: int = Field(default=0, ge=0, le=100)
    source_event_id: uuid.UUID | None = None
    expires_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("expires_at", mode="after")
    @classmethod
    def expires_at_must_be_timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return _timezone_aware(value, "expires_at")


class RelationshipRepairCreateRequest(_RequestModel):
    worldline_id: uuid.UUID | None = None
    relationship_id: uuid.UUID
    repair_kind: RelationshipRepairKind
    reason: str = Field(min_length=1, max_length=12_000)
    score_delta: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class JournalEntryCreateRequest(_RequestModel):
    worldline_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    player_actor_id: uuid.UUID | None = None
    entry_kind: JournalEntryKind
    title: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=12_000)
    source_event_id: uuid.UUID | None = None
    source_ref: str | None = Field(default=None, max_length=160)
    visibility: JournalVisibility = "player_private"
    metadata: dict[str, Any] = Field(default_factory=dict)


class NotificationCreateRequest(_RequestModel):
    worldline_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    notification_kind: NotificationKind
    title: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=12_000)
    source_event_id: uuid.UUID | None = None
    source_ref: str | None = Field(default=None, max_length=160)
    metadata: dict[str, Any] = Field(default_factory=dict)


class InterventionCreateRequest(_RequestModel):
    worldline_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    player_actor_id: uuid.UUID
    intervention_kind: InterventionKind
    target_agent_id: uuid.UUID | None = None
    target_scene_id: uuid.UUID | None = None
    prompt: str = Field(min_length=1, max_length=12_000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GMStyleReviewCreateRequest(_RequestModel):
    worldline_id: uuid.UUID | None = None
    source_kind: str = Field(min_length=1, max_length=40)
    source_ref: str | None = Field(default=None, max_length=160)
    reviewed_text: str = Field(min_length=1, max_length=80_000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class NarrativeContinuityReviewCreateRequest(_RequestModel):
    worldline_id: uuid.UUID | None = None
    artifact_id: uuid.UUID | None = None
    source_kind: str = Field(min_length=1, max_length=40)
    source_ref: str | None = Field(default=None, max_length=160)
    reviewed_text: str = Field(min_length=1, max_length=80_000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RouteMilestoneCreateRequest(_RequestModel):
    worldline_id: uuid.UUID | None = None
    milestone_key: str = Field(pattern=SLUG_PATTERN, max_length=120)
    title: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=12_000)
    stage: int = Field(default=0, ge=0)
    status: RouteMilestoneStatus = "planned"
    route_affinity_id: uuid.UUID | None = None
    plot_thread_id: uuid.UUID | None = None
    agent_id: uuid.UUID | None = None
    conditions: dict[str, Any] = Field(default_factory=dict)
    evidence_metadata: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EndingCandidateCreateRequest(_RequestModel):
    worldline_id: uuid.UUID | None = None
    ending_key: str = Field(pattern=SLUG_PATTERN, max_length=120)
    title: str = Field(min_length=1, max_length=160)
    ending_type: EndingType
    status: EndingStatus = "planned"
    route_affinity_id: uuid.UUID | None = None
    plot_thread_id: uuid.UUID | None = None
    agent_id: uuid.UUID | None = None
    requirements: dict[str, Any] = Field(default_factory=dict)
    outcome_summary: str | None = Field(default=None, max_length=12_000)
    evidence_metadata: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LongRunEvalCreateRequest(_RequestModel):
    worldline_id: uuid.UUID | None = None
    eval_key: str = Field(pattern=SLUG_PATTERN, max_length=120)
    horizon_days: int = Field(default=7, ge=1, le=90)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuthoringTemplateCreateRequest(_RequestModel):
    template_key: str = Field(pattern=SLUG_PATTERN, max_length=120)
    template_kind: AuthoringTemplateKind
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=12_000)
    content: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuthoringTemplateApplyRequest(_RequestModel):
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReleaseProfileUpsertRequest(_RequestModel):
    profile_key: str = Field(default="default", pattern=SLUG_PATTERN, max_length=120)
    status: ReleaseProfileStatus = "draft"
    branch_policy: dict[str, Any] = Field(default_factory=dict)
    backup_policy: dict[str, Any] = Field(default_factory=dict)
    content_review_policy: dict[str, Any] = Field(default_factory=dict)
    player_permission_policy: dict[str, Any] = Field(default_factory=dict)
    worldline_policy: dict[str, Any] = Field(default_factory=dict)
    checklist: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BetaChecklistRunCreateRequest(_RequestModel):
    worldline_id: uuid.UUID | None = None
    run_key: str = Field(default="beta-readiness", pattern=SLUG_PATTERN, max_length=120)
    metadata: dict[str, Any] = Field(default_factory=dict)


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
    narrative_role: NarrativeRole | None = None
    importance: CharacterImportance | None = None
    canon_status: ContinuityStatus | None = None
    character_category: CharacterCategory | None = None
    character_profile: dict[str, Any] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)


class AgentUpdateRequest(_RequestModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    kind: AgentKind | None = None
    home_scene_id: uuid.UUID | None = None
    provider_profile_id: uuid.UUID | None = None
    narrative_role: NarrativeRole | None = None
    importance: CharacterImportance | None = None
    canon_status: ContinuityStatus | None = None
    character_category: CharacterCategory | None = None
    character_profile: dict[str, Any] | None = None
    config: dict[str, Any] | None = None
    is_enabled: bool | None = None


class AgentRelationshipCreateRequest(_RequestModel):
    worldline_id: uuid.UUID | None = None
    source_agent_id: uuid.UUID
    target_agent_id: uuid.UUID
    relationship_type: RelationshipType
    affection: int = Field(default=0, ge=-100, le=100)
    trust: int = Field(default=0, ge=-100, le=100)
    hostility: int = Field(default=0, ge=0, le=100)
    intimacy: int = Field(default=0, ge=0, le=100)
    obligation: int = Field(default=0, ge=0, le=100)
    rivalry: int = Field(default=0, ge=0, le=100)
    debt: int = Field(default=0, ge=0, le=100)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentRelationshipUpdateRequest(_RequestModel):
    affection: int | None = Field(default=None, ge=-100, le=100)
    trust: int | None = Field(default=None, ge=-100, le=100)
    hostility: int | None = Field(default=None, ge=0, le=100)
    intimacy: int | None = Field(default=None, ge=0, le=100)
    obligation: int | None = Field(default=None, ge=0, le=100)
    rivalry: int | None = Field(default=None, ge=0, le=100)
    debt: int | None = Field(default=None, ge=0, le=100)
    metadata: dict[str, Any] | None = None


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
    worldline_id: uuid.UUID | None = None
    query_text: str = Field(min_length=1, max_length=8_000)
    limit: int = Field(default=10, ge=1, le=50)


class AgentRunRequest(_RequestModel):
    worldline_id: uuid.UUID | None = None
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
    continuity_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("continuity_metadata", mode="after")
    @classmethod
    def continuity_metadata_status_is_known(cls, value: dict[str, Any]) -> dict[str, Any]:
        _validate_continuity_metadata(value, "continuity_metadata")
        return value


class NarrativePublicationRequest(_RequestModel):
    reader_visible: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
    override_style_warning: bool = False


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
    region_key: str | None
    location_tags: list[str]
    opening_rules: dict[str, Any]
    is_active: bool


class SceneLocationEdgeResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    source_scene_id: uuid.UUID
    target_scene_id: uuid.UUID
    source_scene_key: str
    target_scene_key: str
    travel_label: str | None
    traversal_rules: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class OrganizationResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    organization_key: str
    name: str
    organization_type: OrganizationType
    description: str | None
    public_summary: str | None
    hidden_summary: str | None
    metadata: dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class OrganizationMembershipResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    organization_id: uuid.UUID
    organization_key: str
    organization_name: str
    agent_id: uuid.UUID
    agent_key: str
    agent_display_name: str
    role_title: str | None
    visibility: OrganizationVisibility
    loyalty: int
    influence: int
    responsibilities: list[str]
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class FactionProgressTrackResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None = None
    organization_id: uuid.UUID
    organization_key: str
    organization_name: str
    track_key: str
    name: str
    track_type: FactionTrackType
    progress: int
    pressure: int
    summary: str | None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class AgentPresenceResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None = None
    agent_id: uuid.UUID
    agent_key: str
    agent_display_name: str
    current_scene_id: uuid.UUID | None
    current_scene_key: str | None
    current_scene_name: str | None
    visibility_status: PresenceVisibilityStatus
    encounter_eligible: bool
    scheduled_movement: dict[str, Any]
    last_event_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class DailyLifeEventCandidateResponse(BaseModel):
    id: uuid.UUID | None
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None = None
    agent_id: uuid.UUID | None
    agent_display_name: str | None
    scene_id: uuid.UUID | None
    scene_name: str | None
    title: str
    summary: str
    importance: Literal["daily", "relationship", "organization"]
    starts_at: datetime
    source_kind: str
    source_ref: str | None
    status: DailyLifeCandidateStatus
    metadata: dict[str, Any]
    created_at: datetime | None
    updated_at: datetime | None


class DailyLifePreviewResponse(BaseModel):
    world_id: uuid.UUID
    start_world_time: datetime
    horizon_hours: int
    candidate_count: int
    candidates: list[DailyLifeEventCandidateResponse]


class OffscreenEventQueueResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None = None
    source_candidate_id: uuid.UUID | None
    event_name: str
    title: str
    payload: dict[str, Any]
    due_at: datetime
    importance: Literal["daily", "relationship", "organization", "route", "main_plot"]
    status: OffscreenEventStatus
    resolved_event_id: uuid.UUID | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class OffscreenResolutionResponse(BaseModel):
    processed_count: int
    resolved_count: int
    failed_count: int
    event_ids: list[uuid.UUID]


class WorldlineResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_key: str
    name: str
    description: str | None
    parent_worldline_id: uuid.UUID | None
    forked_from_snapshot_id: uuid.UUID | None
    fork_event_sequence: int | None
    status: WorldlineStatus
    created_by_actor_ref: str
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class WorldlineComparisonResponse(BaseModel):
    base_worldline_id: uuid.UUID
    compare_worldline_id: uuid.UUID
    fork_event_sequence: int | None
    divergent_event_count: int
    relationship_delta_count: int
    faction_delta_count: int
    choice_delta_count: int


class GMAgendaResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    title: str
    summary: str
    priority: int
    status: GMAgendaStatus
    focus_agents: list[str]
    focus_organizations: list[str]
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class GMProposalResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    agenda_id: uuid.UUID | None
    title: str
    reason: str
    event_name: str
    proposed_payload: dict[str, Any]
    importance: Literal["daily", "relationship", "organization", "route", "main_plot"]
    risk_score: int
    affected_agents: list[str]
    affected_organizations: list[str]
    source_context: dict[str, Any]
    status: GMProposalStatus
    review_note: str | None
    resolved_event_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class EventResolutionRuleResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    rule_key: str
    name: str
    description: str | None
    priority: int
    status: ResolutionRuleStatus
    conditions: dict[str, Any]
    effects: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ResolutionRuleDryRunResponse(BaseModel):
    rule_id: uuid.UUID
    rule_key: str
    matched: bool
    reasons: list[str]
    effects: dict[str, Any]


class ChoiceConsequencePreviewResponse(BaseModel):
    relationship_updates: list[dict[str, Any]]
    faction_updates: list[dict[str, Any]]
    offscreen_events: list[dict[str, Any]]
    diagnostics: list[str]


class PlayerActorResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    user_id: uuid.UUID
    actor_ref: str
    display_name: str
    current_scene_id: uuid.UUID | None
    profile: dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PlayerChoiceResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    user_id: uuid.UUID
    player_actor_id: uuid.UUID
    choice_key: str
    choice_kind: PlayerChoiceKind
    prompt: str
    selected_option: str
    context: dict[str, Any]
    consequence_preview: dict[str, Any]
    applied_event_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class StoryHookResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    hook_key: str
    title: str
    hook_type: StoryHookType
    summary: str
    status: StoryHookStatus
    priority: int
    owner_agent_id: uuid.UUID | None
    owner_agent_key: str | None
    owner_agent_display_name: str | None
    target_agent_id: uuid.UUID | None
    target_agent_key: str | None
    target_agent_display_name: str | None
    source_event_id: uuid.UUID | None
    due_at: datetime | None
    resolution: str | None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class PlotThreadResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    thread_key: str
    title: str
    thread_type: PlotThreadType
    status: PlotThreadStatus
    summary: str
    stakes: str | None
    next_beats: list[str]
    participant_agent_ids: list[str]
    organization_ids: list[str]
    related_event_ids: list[str]
    priority: int
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class RouteAffinityResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    agent_id: uuid.UUID
    agent_key: str
    agent_display_name: str
    route_key: str
    status: RouteStatus
    affinity: int
    stage: int
    flags: list[str]
    last_choice_id: uuid.UUID | None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class EventTriggerConditionResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    condition_key: str
    name: str
    description: str | None
    status: TriggerConditionStatus
    priority: int
    conditions: dict[str, Any]
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class TriggerConditionDryRunResponse(BaseModel):
    condition_id: uuid.UUID
    condition_key: str
    matched: bool
    satisfied: list[str]
    unsatisfied: list[str]


class SceneBeatDraftResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    source_kind: Literal["event", "proposal", "daily_episode", "manual"]
    source_ref: str | None
    title: str
    setup: str
    dialogue_beats: list[dict[str, Any]]
    choice_points: list[dict[str, Any]]
    aftermath: str
    participant_agent_ids: list[str]
    scene_id: uuid.UUID | None
    scene_key: str | None
    scene_name: str | None
    status: SceneBeatStatus
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class DailyEpisodeDraftResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    source_candidate_id: uuid.UUID | None
    title: str
    summary: str
    scene_beat_draft_id: uuid.UUID | None
    participant_agent_ids: list[str]
    status: DailyEpisodeStatus
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class GroupInteractionContextResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    context_key: str
    title: str
    interaction_type: GroupInteractionType
    scene_id: uuid.UUID | None
    scene_key: str | None
    scene_name: str | None
    organization_id: uuid.UUID | None
    organization_key: str | None
    organization_name: str | None
    participant_agent_ids: list[str]
    participant_roles: dict[str, Any]
    constraints: dict[str, Any]
    status: GroupInteractionStatus
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class RelationshipEventSuggestionResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    relationship_id: uuid.UUID | None
    source_agent_id: uuid.UUID | None
    source_agent_display_name: str | None
    target_agent_id: uuid.UUID | None
    target_agent_display_name: str | None
    title: str
    reason: str
    suggested_event_name: str
    score: int
    status: SuggestionStatus
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class OrganizationConflictResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    organization_id: uuid.UUID
    organization_key: str
    organization_name: str
    faction_track_id: uuid.UUID | None
    faction_track_key: str | None
    title: str
    summary: str
    pressure_delta: int
    progress_delta: int
    status: OrganizationConflictStatus
    resolved_event_id: uuid.UUID | None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class RumorResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    rumor_key: str
    title: str
    content: str
    source_agent_id: uuid.UUID | None
    source_agent_display_name: str | None
    source_organization_id: uuid.UUID | None
    source_organization_name: str | None
    visibility: RumorVisibility
    known_agent_ids: list[str]
    status: RumorStatus
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class RumorPropagationResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    rumor_id: uuid.UUID
    rumor_title: str
    source_agent_id: uuid.UUID | None
    source_agent_display_name: str | None
    target_agent_id: uuid.UUID | None
    target_agent_display_name: str | None
    target_organization_id: uuid.UUID | None
    target_organization_name: str | None
    propagation_reason: str
    status: RumorPropagationStatus
    delivered_event_id: uuid.UUID | None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class KnowledgeFactResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    agent_id: uuid.UUID
    agent_key: str
    agent_display_name: str
    fact_key: str
    knowledge_kind: KnowledgeKind
    content: str
    source_event_id: uuid.UUID | None
    source_ref: str | None
    confidence: int
    visibility: KnowledgeVisibility
    is_active: bool
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class SecretResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    secret_key: str
    title: str
    content: str
    holder_agent_ids: list[str]
    reveal_conditions: dict[str, Any]
    consequence_metadata: dict[str, Any]
    visibility: SecretVisibility
    status: SecretStatus
    revealed_event_id: uuid.UUID | None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class EmotionalStateResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    agent_id: uuid.UUID
    agent_key: str
    agent_display_name: str
    mood: str
    stress: int
    fatigue: int
    anticipation: int
    jealousy: int
    anger: int
    source_event_id: uuid.UUID | None
    expires_at: datetime | None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class RelationshipRepairResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    relationship_id: uuid.UUID
    repair_kind: RelationshipRepairKind
    reason: str
    score_delta: dict[str, Any]
    status: RelationshipRepairStatus
    applied_event_id: uuid.UUID | None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class JournalEntryResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    user_id: uuid.UUID
    player_actor_id: uuid.UUID | None
    entry_kind: JournalEntryKind
    title: str
    body: str
    source_event_id: uuid.UUID | None
    source_ref: str | None
    visibility: JournalVisibility
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class InWorldNotificationResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    user_id: uuid.UUID
    notification_kind: NotificationKind
    title: str
    body: str
    source_event_id: uuid.UUID | None
    source_ref: str | None
    status: NotificationStatus
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class PlayerInterventionResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    user_id: uuid.UUID
    player_actor_id: uuid.UUID
    intervention_kind: InterventionKind
    target_agent_id: uuid.UUID | None
    target_scene_id: uuid.UUID | None
    prompt: str
    choice_id: uuid.UUID | None
    event_id: uuid.UUID | None
    status: InterventionStatus
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class GMStyleReviewResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    source_kind: str
    source_ref: str | None
    reviewed_text: str
    status: ReviewStatus
    diagnostics: list[dict[str, Any]]
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class NarrativeContinuityReviewResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    artifact_id: uuid.UUID | None
    source_kind: str
    source_ref: str | None
    reviewed_text: str
    status: ReviewStatus
    issues: list[dict[str, Any]]
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class LivingWorldDashboardResponse(BaseModel):
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    knowledge_count: int
    hidden_secret_count: int
    emotional_state_count: int
    open_hook_count: int
    unread_notification_count: int
    pending_intervention_count: int
    active_route_count: int
    pressure_summary: dict[str, int]


class RouteMilestoneResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    route_affinity_id: uuid.UUID | None
    plot_thread_id: uuid.UUID | None
    agent_id: uuid.UUID | None
    agent_key: str | None
    agent_display_name: str | None
    milestone_key: str
    title: str
    description: str | None
    stage: int
    status: RouteMilestoneStatus
    conditions: dict[str, Any]
    evidence_metadata: dict[str, Any]
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class EndingCandidateResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    route_affinity_id: uuid.UUID | None
    plot_thread_id: uuid.UUID | None
    agent_id: uuid.UUID | None
    agent_key: str | None
    agent_display_name: str | None
    ending_key: str
    title: str
    ending_type: EndingType
    status: EndingStatus
    requirements: dict[str, Any]
    outcome_summary: str | None
    evidence_metadata: dict[str, Any]
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class EndingDryRunResponse(BaseModel):
    ending_id: uuid.UUID
    ending_key: str
    matched: bool
    satisfied: list[str]
    unsatisfied: list[str]
    evidence: dict[str, Any]


class LongRunEvalResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    eval_key: str
    horizon_days: int
    status: LongRunEvalStatus
    started_at: datetime
    finished_at: datetime
    metrics: dict[str, Any]
    recommendations: list[dict[str, Any]]
    blockers: list[dict[str, Any]]
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class AuthoringTemplateResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    template_key: str
    template_kind: AuthoringTemplateKind
    name: str
    description: str | None
    content: dict[str, Any]
    validation_issues: list[dict[str, Any]]
    is_active: bool
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class AuthoringImportJobResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    template_id: uuid.UUID | None
    status: AuthoringImportStatus
    preview_summary: dict[str, Any]
    applied_refs: dict[str, Any]
    validation_issues: list[dict[str, Any]]
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ReleaseProfileResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    profile_key: str
    status: ReleaseProfileStatus
    branch_policy: dict[str, Any]
    backup_policy: dict[str, Any]
    content_review_policy: dict[str, Any]
    player_permission_policy: dict[str, Any]
    worldline_policy: dict[str, Any]
    checklist: dict[str, Any]
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class BetaChecklistRunResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    run_key: str
    status: BetaChecklistStatus
    summary: str
    evidence: dict[str, Any]
    blocker_count: int
    created_by_actor_ref: str
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class BetaChecklistItemResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    item_key: str
    title: str
    status: BetaChecklistItemStatus
    evidence: dict[str, Any]
    recommendation: str | None
    created_at: datetime
    updated_at: datetime


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


class WorldAccessReviewMemberResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    display_name: str
    is_active: bool
    role: WorldRole
    membership_created_at: datetime
    membership_updated_at: datetime


class WorldAccessReviewResponse(BaseModel):
    world_id: uuid.UUID
    owner_user_id: uuid.UUID
    member_count: int
    world_admin_count: int
    inactive_member_count: int
    final_admin_risk: bool
    members: list[WorldAccessReviewMemberResponse]


class WorldBibleResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    source_material: str
    canon_timeline: list[dict[str, Any]]
    setting_rules: dict[str, Any]
    forbidden_changes: list[dict[str, Any]]
    sequel_boundaries: dict[str, Any]
    continuity_config: dict[str, Any]
    metadata: dict[str, Any]
    continuity_status: ContinuityStatus | None
    created_at: datetime
    updated_at: datetime


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
    narrative_role: NarrativeRole | None
    importance: CharacterImportance | None
    canon_status: ContinuityStatus | None
    character_category: CharacterCategory | None
    character_profile: dict[str, Any]
    config: dict[str, Any]
    is_enabled: bool


class AgentRelationshipResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None = None
    source_agent_id: uuid.UUID
    source_agent_key: str
    source_display_name: str
    target_agent_id: uuid.UUID
    target_agent_key: str
    target_display_name: str
    relationship_type: RelationshipType
    affection: int
    trust: int
    hostility: int
    intimacy: int
    obligation: int
    rivalry: int
    debt: int
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


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
    narrative_role: NarrativeRole | None = None
    importance: CharacterImportance | None = None
    canon_status: ContinuityStatus | None = None
    character_category: CharacterCategory | None = None
    character_profile: dict[str, Any] = Field(default_factory=dict)
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
    worldline_id: uuid.UUID | None
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
    continuity_metadata: dict[str, Any]
    continuity_status: ContinuityStatus | None
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
    publication_gate: dict[str, Any] | None = None


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
    worldline_id: uuid.UUID | None = None
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
    worldline_id: uuid.UUID | None = None
    sequence: int
    event_name: str
    importance: EventImportance
    payload: dict[str, Any]
    wall_time: datetime
    world_time: datetime | None
    actor_ref: str
    continuity_metadata: dict[str, Any]
    continuity_status: ContinuityStatus | None
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
        select(Agent).where(Agent.source_preset_id == preset_id).order_by(Agent.agent_key),
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
            issue.model_dump() for issue in validation.issues if issue.severity == "blocking"
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
    ensure_primary_worldline(db_session, world.id, actor_ref=f"user:{owner.id}")
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
            narrative_role=exported_agent.narrative_role,
            importance=exported_agent.importance,
            canon_status=exported_agent.canon_status,
            character_category=exported_agent.character_category,
            character_profile=exported_agent.character_profile,
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
    ensure_primary_worldline(db_session, world.id, actor_ref=_actor_ref(subject))
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


@router.get("/{world_id}/bible", response_model=WorldBibleResponse | None)
def get_world_bible(
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorldBibleResponse | None:
    _world_or_404(db_session, context.world_id)
    bible = db_session.scalars(
        select(WorldBible).where(WorldBible.world_id == context.world_id),
    ).one_or_none()
    return None if bible is None else _world_bible_response(bible)


@router.put("/{world_id}/bible", response_model=WorldBibleResponse)
def upsert_world_bible(
    bible_upsert: WorldBibleUpsertRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorldBibleResponse:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    bible = db_session.scalars(
        select(WorldBible).where(WorldBible.world_id == context.world_id),
    ).one_or_none()
    if bible is None:
        bible = WorldBible(id=uuid.uuid4(), world_id=context.world_id)
        db_session.add(bible)
    bible.source_material = bible_upsert.source_material
    bible.canon_timeline = bible_upsert.canon_timeline
    bible.setting_rules = bible_upsert.setting_rules
    bible.forbidden_changes = bible_upsert.forbidden_changes
    bible.sequel_boundaries = bible_upsert.sequel_boundaries
    bible.continuity_config = bible_upsert.continuity_config
    bible.metadata_json = bible_upsert.metadata
    db_session.flush()
    return _world_bible_response(bible)


@router.get("/{world_id}/worldlines", response_model=list[WorldlineResponse])
def list_worldlines(
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[WorldlineResponse]:
    _world_or_404(db_session, context.world_id)
    ensure_primary_worldline(db_session, context.world_id)
    worldlines = db_session.scalars(
        select(Worldline)
        .where(Worldline.world_id == context.world_id)
        .order_by(Worldline.parent_worldline_id.is_not(None), Worldline.created_at),
    ).all()
    return [_worldline_response(worldline) for worldline in worldlines]


@router.post(
    "/{world_id}/worldlines/fork",
    response_model=WorldlineResponse,
    status_code=status.HTTP_201_CREATED,
)
def fork_worldline(
    fork_request: WorldlineForkRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorldlineResponse:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    try:
        worldline = LivingWorldGMService(db_session).fork_worldline(
            world_id=context.world_id,
            source_worldline_id=fork_request.source_worldline_id,
            worldline_key=fork_request.worldline_key,
            name=fork_request.name,
            description=fork_request.description,
            forked_from_snapshot_id=fork_request.forked_from_snapshot_id,
            fork_event_sequence=fork_request.fork_event_sequence,
            actor_ref=_actor_ref(context.subject),
            metadata=fork_request.metadata,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return _worldline_response(worldline)


@router.get(
    "/{world_id}/worldlines/{base_worldline_id}/compare/{compare_worldline_id}",
    response_model=WorldlineComparisonResponse,
)
def compare_worldlines(
    base_worldline_id: uuid.UUID,
    compare_worldline_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorldlineComparisonResponse:
    _world_or_404(db_session, context.world_id)
    try:
        comparison = LivingWorldGMService(db_session).compare_worldlines(
            world_id=context.world_id,
            base_worldline_id=base_worldline_id,
            compare_worldline_id=compare_worldline_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _worldline_comparison_response(comparison)


@router.get("/{world_id}/gm/agendas", response_model=list[GMAgendaResponse])
def list_gm_agendas(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
) -> list[GMAgendaResponse]:
    _world_or_404(db_session, context.world_id)
    resolved_worldline = LivingWorldGMService(db_session).worldline_or_404(
        context.world_id,
        worldline_id,
    )
    agendas = db_session.scalars(
        select(GMAgenda)
        .where(
            GMAgenda.world_id == context.world_id, GMAgenda.worldline_id == resolved_worldline.id
        )
        .order_by(GMAgenda.priority.desc(), GMAgenda.created_at.desc()),
    ).all()
    return [_gm_agenda_response(agenda) for agenda in agendas]


@router.post(
    "/{world_id}/gm/agendas", response_model=GMAgendaResponse, status_code=status.HTTP_201_CREATED
)
def create_gm_agenda(
    agenda_create: GMAgendaCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> GMAgendaResponse:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    agenda = LivingWorldGMService(db_session).create_agenda(
        world_id=context.world_id,
        worldline_id=agenda_create.worldline_id,
        title=agenda_create.title,
        summary=agenda_create.summary,
        priority=agenda_create.priority,
        focus_agents=agenda_create.focus_agents,
        focus_organizations=agenda_create.focus_organizations,
        metadata=agenda_create.metadata,
    )
    return _gm_agenda_response(agenda)


@router.patch("/{world_id}/gm/agendas/{agenda_id}", response_model=GMAgendaResponse)
def update_gm_agenda(
    agenda_id: uuid.UUID,
    agenda_update: GMAgendaUpdateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> GMAgendaResponse:
    require_csrf(request)
    agenda = _gm_agenda_or_404(db_session, context.world_id, agenda_id)
    for field_name in ("title", "summary", "priority", "status"):
        if field_name in agenda_update.model_fields_set:
            next_value = getattr(agenda_update, field_name)
            if next_value is not None:
                setattr(agenda, field_name, next_value)
    if "focus_agents" in agenda_update.model_fields_set:
        agenda.focus_agents = agenda_update.focus_agents or []
    if "focus_organizations" in agenda_update.model_fields_set:
        agenda.focus_organizations = agenda_update.focus_organizations or []
    if "metadata" in agenda_update.model_fields_set:
        agenda.metadata_json = agenda_update.metadata or {}
    db_session.flush()
    return _gm_agenda_response(agenda)


@router.get("/{world_id}/gm/proposals", response_model=list[GMProposalResponse])
def list_gm_proposals(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
    status_filter: Annotated[GMProposalStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[GMProposalResponse]:
    _world_or_404(db_session, context.world_id)
    resolved_worldline = LivingWorldGMService(db_session).worldline_or_404(
        context.world_id,
        worldline_id,
    )
    statement = select(GMEventProposal).where(
        GMEventProposal.world_id == context.world_id,
        GMEventProposal.worldline_id == resolved_worldline.id,
    )
    if status_filter is not None:
        statement = statement.where(GMEventProposal.status == status_filter)
    proposals = db_session.scalars(
        statement.order_by(GMEventProposal.created_at.desc()).limit(limit),
    ).all()
    return [_gm_proposal_response(proposal) for proposal in proposals]


@router.post(
    "/{world_id}/gm/proposals",
    response_model=GMProposalResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_gm_proposal(
    proposal_create: GMProposalCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> GMProposalResponse:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    try:
        proposal = LivingWorldGMService(db_session).create_proposal(
            world_id=context.world_id,
            worldline_id=proposal_create.worldline_id,
            agenda_id=proposal_create.agenda_id,
            title=proposal_create.title,
            reason=proposal_create.reason,
            event_name=proposal_create.event_name,
            proposed_payload=proposal_create.proposed_payload,
            importance=proposal_create.importance,
            risk_score=proposal_create.risk_score,
            affected_agents=proposal_create.affected_agents,
            affected_organizations=proposal_create.affected_organizations,
            source_context=proposal_create.source_context,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _gm_proposal_response(proposal)


@router.post("/{world_id}/gm/proposals/{proposal_id}/review", response_model=GMProposalResponse)
def review_gm_proposal(
    proposal_id: uuid.UUID,
    review_request: GMProposalReviewRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> GMProposalResponse:
    require_csrf(request)
    try:
        proposal = LivingWorldGMService(db_session).review_proposal(
            world_id=context.world_id,
            proposal_id=proposal_id,
            status=review_request.status,
            review_note=review_request.review_note,
            actor_ref=_actor_ref(context.subject),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _gm_proposal_response(proposal)


@router.get("/{world_id}/resolution-rules", response_model=list[EventResolutionRuleResponse])
def list_resolution_rules(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[EventResolutionRuleResponse]:
    _world_or_404(db_session, context.world_id)
    rules = db_session.scalars(
        select(EventResolutionRule)
        .where(EventResolutionRule.world_id == context.world_id)
        .order_by(EventResolutionRule.priority.desc(), EventResolutionRule.rule_key),
    ).all()
    return [_resolution_rule_response(rule) for rule in rules]


@router.post(
    "/{world_id}/resolution-rules",
    response_model=EventResolutionRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_resolution_rule(
    rule_create: EventResolutionRuleCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> EventResolutionRuleResponse:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    try:
        rule = LivingWorldGMService(db_session).create_rule(
            world_id=context.world_id,
            rule_key=rule_create.rule_key,
            name=rule_create.name,
            description=rule_create.description,
            priority=rule_create.priority,
            conditions=rule_create.conditions,
            effects=rule_create.effects,
        )
    except ValueError as exc:
        raise _conflict(str(exc)) from exc
    return _resolution_rule_response(rule)


@router.patch("/{world_id}/resolution-rules/{rule_id}", response_model=EventResolutionRuleResponse)
def update_resolution_rule(
    rule_id: uuid.UUID,
    rule_update: EventResolutionRuleUpdateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> EventResolutionRuleResponse:
    require_csrf(request)
    rule = _resolution_rule_or_404(db_session, context.world_id, rule_id)
    for field_name in ("name", "description", "priority", "status"):
        if field_name in rule_update.model_fields_set:
            next_value = getattr(rule_update, field_name)
            if next_value is not None or field_name == "description":
                setattr(rule, field_name, next_value)
    if "conditions" in rule_update.model_fields_set:
        rule.conditions_json = rule_update.conditions or {}
    if "effects" in rule_update.model_fields_set:
        rule.effects_json = rule_update.effects or {}
    db_session.flush()
    return _resolution_rule_response(rule)


@router.post(
    "/{world_id}/resolution-rules/{rule_id}/dry-run",
    response_model=ResolutionRuleDryRunResponse,
)
def dry_run_resolution_rule(
    rule_id: uuid.UUID,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
) -> ResolutionRuleDryRunResponse:
    require_csrf(request)
    rule = _resolution_rule_or_404(db_session, context.world_id, rule_id)
    result = LivingWorldGMService(db_session).dry_run_rule(
        world_id=context.world_id,
        rule=rule,
        worldline_id=worldline_id,
    )
    return _resolution_rule_dry_run_response(result)


@router.get("/{world_id}/player-actors", response_model=list[PlayerActorResponse])
def list_player_actors(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
) -> list[PlayerActorResponse]:
    _world_or_404(db_session, context.world_id)
    resolved_worldline = LivingWorldGMService(db_session).worldline_or_404(
        context.world_id,
        worldline_id,
    )
    actors = db_session.scalars(
        select(PlayerActorProfile)
        .where(
            PlayerActorProfile.world_id == context.world_id,
            PlayerActorProfile.worldline_id == resolved_worldline.id,
        )
        .order_by(PlayerActorProfile.display_name),
    ).all()
    return [_player_actor_response(actor) for actor in actors]


@router.put("/{world_id}/player-actors", response_model=PlayerActorResponse)
def bind_player_actor(
    actor_bind: PlayerActorBindRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> PlayerActorResponse:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    user_id = actor_bind.user_id or context.subject.user_id
    _user_or_404(db_session, user_id)
    if actor_bind.current_scene_id is not None:
        _scene_or_404(db_session, context.world_id, actor_bind.current_scene_id)
    actor = LivingWorldGMService(db_session).bind_player_actor(
        world_id=context.world_id,
        worldline_id=actor_bind.worldline_id,
        user_id=user_id,
        display_name=actor_bind.display_name,
        current_scene_id=actor_bind.current_scene_id,
        profile=actor_bind.profile,
    )
    return _player_actor_response(actor)


@router.get("/{world_id}/player-choices", response_model=list[PlayerChoiceResponse])
def list_player_choices(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[PlayerChoiceResponse]:
    _world_or_404(db_session, context.world_id)
    resolved_worldline = LivingWorldGMService(db_session).worldline_or_404(
        context.world_id,
        worldline_id,
    )
    statement = select(PlayerChoiceRecord).where(
        PlayerChoiceRecord.world_id == context.world_id,
        PlayerChoiceRecord.worldline_id == resolved_worldline.id,
    )
    if user_id is not None:
        statement = statement.where(PlayerChoiceRecord.user_id == user_id)
    choices = db_session.scalars(
        statement.order_by(PlayerChoiceRecord.created_at.desc()).limit(limit),
    ).all()
    return [_player_choice_response(choice) for choice in choices]


@router.post(
    "/{world_id}/player-choices",
    response_model=PlayerChoiceResponse,
    status_code=status.HTTP_201_CREATED,
)
def record_player_choice(
    choice_create: PlayerChoiceCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> PlayerChoiceResponse:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    user_id = choice_create.user_id or context.subject.user_id
    try:
        choice = LivingWorldGMService(db_session).record_player_choice(
            world_id=context.world_id,
            worldline_id=choice_create.worldline_id,
            user_id=user_id,
            player_actor_id=choice_create.player_actor_id,
            choice_key=choice_create.choice_key,
            choice_kind=choice_create.choice_kind,
            prompt=choice_create.prompt,
            selected_option=choice_create.selected_option,
            context=choice_create.context,
            effects=choice_create.effects,
            actor_ref=_actor_ref(context.subject),
            apply=choice_create.apply,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return _player_choice_response(choice)


@router.post(
    "/{world_id}/player-choices/preview",
    response_model=ChoiceConsequencePreviewResponse,
)
def preview_player_choice_consequences(
    choice_create: PlayerChoiceCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ChoiceConsequencePreviewResponse:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    preview = LivingWorldGMService(db_session).choice_consequence_preview(
        world_id=context.world_id,
        worldline_id=choice_create.worldline_id,
        effects=choice_create.effects,
    )
    return ChoiceConsequencePreviewResponse(
        relationship_updates=preview.relationship_updates,
        faction_updates=preview.faction_updates,
        offscreen_events=preview.offscreen_events,
        diagnostics=preview.diagnostics,
    )


@router.get("/{world_id}/story-hooks", response_model=list[StoryHookResponse])
def list_story_hooks(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
    status_filter: Annotated[StoryHookStatus | None, Query(alias="status")] = None,
    hook_type: StoryHookType | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[StoryHookResponse]:
    _world_or_404(db_session, context.world_id)
    resolved_worldline = LivingWorldPlotService(db_session).worldline_or_404(
        context.world_id,
        worldline_id,
    )
    statement = select(StoryHook).where(
        StoryHook.world_id == context.world_id,
        StoryHook.worldline_id == resolved_worldline.id,
    )
    if status_filter is not None:
        statement = statement.where(StoryHook.status == status_filter)
    if hook_type is not None:
        statement = statement.where(StoryHook.hook_type == hook_type)
    hooks = db_session.scalars(
        statement.order_by(StoryHook.priority.desc(), StoryHook.created_at.desc()).limit(limit),
    ).all()
    return [_story_hook_response(db_session, hook) for hook in hooks]


@router.post(
    "/{world_id}/story-hooks",
    response_model=StoryHookResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_story_hook(
    hook_create: StoryHookCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> StoryHookResponse:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    if hook_create.owner_agent_id is not None:
        _agent_or_404(db_session, context.world_id, hook_create.owner_agent_id)
    if hook_create.target_agent_id is not None:
        _agent_or_404(db_session, context.world_id, hook_create.target_agent_id)
    try:
        hook = LivingWorldPlotService(db_session).create_story_hook(
            world_id=context.world_id,
            worldline_id=hook_create.worldline_id,
            hook_key=hook_create.hook_key,
            title=hook_create.title,
            hook_type=hook_create.hook_type,
            summary=hook_create.summary,
            priority=hook_create.priority,
            owner_agent_id=hook_create.owner_agent_id,
            target_agent_id=hook_create.target_agent_id,
            due_at=hook_create.due_at,
            metadata=hook_create.metadata,
        )
    except ValueError as exc:
        raise _conflict(str(exc)) from exc
    return _story_hook_response(db_session, hook)


@router.patch("/{world_id}/story-hooks/{hook_id}", response_model=StoryHookResponse)
def update_story_hook(
    hook_id: uuid.UUID,
    hook_update: StoryHookUpdateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> StoryHookResponse:
    require_csrf(request)
    hook = _story_hook_or_404(db_session, context.world_id, hook_id)
    for field_name in ("title", "summary", "status", "priority", "due_at", "resolution"):
        if field_name in hook_update.model_fields_set:
            next_value = getattr(hook_update, field_name)
            if next_value is not None or field_name in ("due_at", "resolution"):
                setattr(hook, field_name, next_value)
    if "owner_agent_id" in hook_update.model_fields_set:
        if hook_update.owner_agent_id is not None:
            _agent_or_404(db_session, context.world_id, hook_update.owner_agent_id)
        hook.owner_agent_id = hook_update.owner_agent_id
    if "target_agent_id" in hook_update.model_fields_set:
        if hook_update.target_agent_id is not None:
            _agent_or_404(db_session, context.world_id, hook_update.target_agent_id)
        hook.target_agent_id = hook_update.target_agent_id
    if "metadata" in hook_update.model_fields_set:
        hook.metadata_json = hook_update.metadata or {}
    db_session.flush()
    return _story_hook_response(db_session, hook)


@router.get("/{world_id}/plot-threads", response_model=list[PlotThreadResponse])
def list_plot_threads(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
    status_filter: Annotated[PlotThreadStatus | None, Query(alias="status")] = None,
    thread_type: PlotThreadType | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[PlotThreadResponse]:
    _world_or_404(db_session, context.world_id)
    resolved_worldline = LivingWorldPlotService(db_session).worldline_or_404(
        context.world_id,
        worldline_id,
    )
    statement = select(PlotThread).where(
        PlotThread.world_id == context.world_id,
        PlotThread.worldline_id == resolved_worldline.id,
    )
    if status_filter is not None:
        statement = statement.where(PlotThread.status == status_filter)
    if thread_type is not None:
        statement = statement.where(PlotThread.thread_type == thread_type)
    threads = db_session.scalars(
        statement.order_by(PlotThread.priority.desc(), PlotThread.updated_at.desc()).limit(limit),
    ).all()
    return [_plot_thread_response(thread) for thread in threads]


@router.post(
    "/{world_id}/plot-threads",
    response_model=PlotThreadResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_plot_thread(
    thread_create: PlotThreadCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> PlotThreadResponse:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    _ensure_agent_string_refs(db_session, context.world_id, thread_create.participant_agent_ids)
    _ensure_organization_string_refs(db_session, context.world_id, thread_create.organization_ids)
    try:
        thread = LivingWorldPlotService(db_session).create_plot_thread(
            world_id=context.world_id,
            worldline_id=thread_create.worldline_id,
            thread_key=thread_create.thread_key,
            title=thread_create.title,
            thread_type=thread_create.thread_type,
            summary=thread_create.summary,
            stakes=thread_create.stakes,
            next_beats=thread_create.next_beats,
            participant_agent_ids=thread_create.participant_agent_ids,
            organization_ids=thread_create.organization_ids,
            priority=thread_create.priority,
            metadata=thread_create.metadata,
        )
    except ValueError as exc:
        raise _conflict(str(exc)) from exc
    return _plot_thread_response(thread)


@router.patch("/{world_id}/plot-threads/{thread_id}", response_model=PlotThreadResponse)
def update_plot_thread(
    thread_id: uuid.UUID,
    thread_update: PlotThreadUpdateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> PlotThreadResponse:
    require_csrf(request)
    thread = _plot_thread_or_404(db_session, context.world_id, thread_id)
    for field_name in ("title", "thread_type", "status", "summary", "stakes", "priority"):
        if field_name in thread_update.model_fields_set:
            next_value = getattr(thread_update, field_name)
            if next_value is not None or field_name == "stakes":
                setattr(thread, field_name, next_value)
    if "next_beats" in thread_update.model_fields_set:
        thread.next_beats = thread_update.next_beats or []
    if "participant_agent_ids" in thread_update.model_fields_set:
        participant_ids = thread_update.participant_agent_ids or []
        _ensure_agent_string_refs(db_session, context.world_id, participant_ids)
        thread.participant_agent_ids = participant_ids
    if "organization_ids" in thread_update.model_fields_set:
        organization_ids = thread_update.organization_ids or []
        _ensure_organization_string_refs(db_session, context.world_id, organization_ids)
        thread.organization_ids = organization_ids
    if "related_event_ids" in thread_update.model_fields_set:
        thread.related_event_ids = thread_update.related_event_ids or []
    if "metadata" in thread_update.model_fields_set:
        thread.metadata_json = thread_update.metadata or {}
    db_session.flush()
    return _plot_thread_response(thread)


@router.get("/{world_id}/route-affinities", response_model=list[RouteAffinityResponse])
def list_route_affinities(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
    agent_id: uuid.UUID | None = None,
    status_filter: Annotated[RouteStatus | None, Query(alias="status")] = None,
) -> list[RouteAffinityResponse]:
    _world_or_404(db_session, context.world_id)
    resolved_worldline = LivingWorldPlotService(db_session).worldline_or_404(
        context.world_id,
        worldline_id,
    )
    statement = select(RouteAffinity).where(
        RouteAffinity.world_id == context.world_id,
        RouteAffinity.worldline_id == resolved_worldline.id,
    )
    if agent_id is not None:
        _agent_or_404(db_session, context.world_id, agent_id)
        statement = statement.where(RouteAffinity.agent_id == agent_id)
    if status_filter is not None:
        statement = statement.where(RouteAffinity.status == status_filter)
    routes = db_session.scalars(
        statement.order_by(RouteAffinity.route_key, RouteAffinity.updated_at.desc()),
    ).all()
    return [_route_affinity_response(db_session, route) for route in routes]


@router.put("/{world_id}/route-affinities", response_model=RouteAffinityResponse)
def upsert_route_affinity(
    route_upsert: RouteAffinityUpsertRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> RouteAffinityResponse:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    _agent_or_404(db_session, context.world_id, route_upsert.agent_id)
    route = LivingWorldPlotService(db_session).upsert_route_affinity(
        world_id=context.world_id,
        worldline_id=route_upsert.worldline_id,
        agent_id=route_upsert.agent_id,
        route_key=route_upsert.route_key,
        status=route_upsert.status,
        affinity=route_upsert.affinity,
        stage=route_upsert.stage,
        flags=route_upsert.flags,
        metadata=route_upsert.metadata,
    )
    return _route_affinity_response(db_session, route)


@router.get(
    "/{world_id}/event-trigger-conditions",
    response_model=list[EventTriggerConditionResponse],
)
def list_event_trigger_conditions(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    status_filter: Annotated[TriggerConditionStatus | None, Query(alias="status")] = None,
) -> list[EventTriggerConditionResponse]:
    _world_or_404(db_session, context.world_id)
    statement = select(EventTriggerCondition).where(
        EventTriggerCondition.world_id == context.world_id
    )
    if status_filter is not None:
        statement = statement.where(EventTriggerCondition.status == status_filter)
    conditions = db_session.scalars(
        statement.order_by(
            EventTriggerCondition.priority.desc(), EventTriggerCondition.condition_key
        ),
    ).all()
    return [_trigger_condition_response(condition) for condition in conditions]


@router.post(
    "/{world_id}/event-trigger-conditions",
    response_model=EventTriggerConditionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_event_trigger_condition(
    condition_create: EventTriggerConditionCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> EventTriggerConditionResponse:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    try:
        condition = LivingWorldPlotService(db_session).create_trigger_condition(
            world_id=context.world_id,
            condition_key=condition_create.condition_key,
            name=condition_create.name,
            description=condition_create.description,
            priority=condition_create.priority,
            conditions=condition_create.conditions,
            metadata=condition_create.metadata,
        )
    except ValueError as exc:
        raise _conflict(str(exc)) from exc
    return _trigger_condition_response(condition)


@router.patch(
    "/{world_id}/event-trigger-conditions/{condition_id}",
    response_model=EventTriggerConditionResponse,
)
def update_event_trigger_condition(
    condition_id: uuid.UUID,
    condition_update: EventTriggerConditionUpdateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> EventTriggerConditionResponse:
    require_csrf(request)
    condition = _trigger_condition_or_404(db_session, context.world_id, condition_id)
    for field_name in ("name", "description", "status", "priority"):
        if field_name in condition_update.model_fields_set:
            next_value = getattr(condition_update, field_name)
            if next_value is not None or field_name == "description":
                setattr(condition, field_name, next_value)
    if "conditions" in condition_update.model_fields_set:
        condition.conditions_json = condition_update.conditions or {}
    if "metadata" in condition_update.model_fields_set:
        condition.metadata_json = condition_update.metadata or {}
    db_session.flush()
    return _trigger_condition_response(condition)


@router.post(
    "/{world_id}/event-trigger-conditions/{condition_id}/dry-run",
    response_model=TriggerConditionDryRunResponse,
)
def dry_run_event_trigger_condition(
    condition_id: uuid.UUID,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
) -> TriggerConditionDryRunResponse:
    require_csrf(request)
    condition = _trigger_condition_or_404(db_session, context.world_id, condition_id)
    result = LivingWorldPlotService(db_session).dry_run_trigger_condition(
        world_id=context.world_id,
        worldline_id=worldline_id,
        condition=condition,
    )
    return _trigger_dry_run_response(result)


@router.get("/{world_id}/scene-beats", response_model=list[SceneBeatDraftResponse])
def list_scene_beats(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
    status_filter: Annotated[SceneBeatStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[SceneBeatDraftResponse]:
    _world_or_404(db_session, context.world_id)
    resolved_worldline = LivingWorldPlotService(db_session).worldline_or_404(
        context.world_id,
        worldline_id,
    )
    statement = select(SceneBeatDraft).where(
        SceneBeatDraft.world_id == context.world_id,
        SceneBeatDraft.worldline_id == resolved_worldline.id,
    )
    if status_filter is not None:
        statement = statement.where(SceneBeatDraft.status == status_filter)
    beats = db_session.scalars(
        statement.order_by(SceneBeatDraft.updated_at.desc()).limit(limit),
    ).all()
    return [_scene_beat_response(db_session, beat) for beat in beats]


@router.post(
    "/{world_id}/scene-beats",
    response_model=SceneBeatDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_scene_beat(
    beat_create: SceneBeatDraftCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> SceneBeatDraftResponse:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    if beat_create.scene_id is not None:
        _scene_or_404(db_session, context.world_id, beat_create.scene_id)
    _ensure_agent_string_refs(db_session, context.world_id, beat_create.participant_agent_ids)
    beat = LivingWorldPlotService(db_session).compose_scene_beat(
        world_id=context.world_id,
        worldline_id=beat_create.worldline_id,
        source_kind=beat_create.source_kind,
        source_ref=beat_create.source_ref,
        title=beat_create.title,
        participant_agent_ids=beat_create.participant_agent_ids,
        scene_id=beat_create.scene_id,
        metadata=beat_create.metadata,
    )
    return _scene_beat_response(db_session, beat)


@router.patch("/{world_id}/scene-beats/{beat_id}", response_model=SceneBeatDraftResponse)
def update_scene_beat(
    beat_id: uuid.UUID,
    beat_update: SceneBeatDraftUpdateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> SceneBeatDraftResponse:
    require_csrf(request)
    beat = _scene_beat_or_404(db_session, context.world_id, beat_id)
    if "status" in beat_update.model_fields_set and beat_update.status is not None:
        beat.status = beat_update.status
    if "metadata" in beat_update.model_fields_set:
        beat.metadata_json = beat_update.metadata or {}
    db_session.flush()
    return _scene_beat_response(db_session, beat)


@router.get("/{world_id}/daily-episodes", response_model=list[DailyEpisodeDraftResponse])
def list_daily_episodes(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
    status_filter: Annotated[DailyEpisodeStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[DailyEpisodeDraftResponse]:
    _world_or_404(db_session, context.world_id)
    resolved_worldline = LivingWorldPlotService(db_session).worldline_or_404(
        context.world_id,
        worldline_id,
    )
    statement = select(DailyEpisodeDraft).where(
        DailyEpisodeDraft.world_id == context.world_id,
        DailyEpisodeDraft.worldline_id == resolved_worldline.id,
    )
    if status_filter is not None:
        statement = statement.where(DailyEpisodeDraft.status == status_filter)
    drafts = db_session.scalars(
        statement.order_by(DailyEpisodeDraft.updated_at.desc()).limit(limit),
    ).all()
    return [_daily_episode_response(draft) for draft in drafts]


@router.post(
    "/{world_id}/daily-episodes",
    response_model=DailyEpisodeDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_daily_episode(
    episode_create: DailyEpisodeDraftCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> DailyEpisodeDraftResponse:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    try:
        episode = LivingWorldPlotService(db_session).generate_daily_episode(
            world_id=context.world_id,
            worldline_id=episode_create.worldline_id,
            source_candidate_id=episode_create.source_candidate_id,
            title=episode_create.title,
            metadata=episode_create.metadata,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return _daily_episode_response(episode)


@router.patch(
    "/{world_id}/daily-episodes/{episode_id}",
    response_model=DailyEpisodeDraftResponse,
)
def update_daily_episode(
    episode_id: uuid.UUID,
    episode_update: DailyEpisodeDraftUpdateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> DailyEpisodeDraftResponse:
    require_csrf(request)
    episode = _daily_episode_or_404(db_session, context.world_id, episode_id)
    if "status" in episode_update.model_fields_set and episode_update.status is not None:
        episode.status = episode_update.status
    if "metadata" in episode_update.model_fields_set:
        episode.metadata_json = episode_update.metadata or {}
    db_session.flush()
    return _daily_episode_response(episode)


@router.get("/{world_id}/group-interactions", response_model=list[GroupInteractionContextResponse])
def list_group_interactions(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
    status_filter: Annotated[GroupInteractionStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[GroupInteractionContextResponse]:
    _world_or_404(db_session, context.world_id)
    resolved_worldline = LivingWorldPlotService(db_session).worldline_or_404(
        context.world_id,
        worldline_id,
    )
    statement = select(GroupInteractionContext).where(
        GroupInteractionContext.world_id == context.world_id,
        GroupInteractionContext.worldline_id == resolved_worldline.id,
    )
    if status_filter is not None:
        statement = statement.where(GroupInteractionContext.status == status_filter)
    contexts = db_session.scalars(
        statement.order_by(GroupInteractionContext.updated_at.desc()).limit(limit),
    ).all()
    return [_group_context_response(db_session, group_context) for group_context in contexts]


@router.post(
    "/{world_id}/group-interactions",
    response_model=GroupInteractionContextResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_group_interaction(
    group_create: GroupInteractionCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> GroupInteractionContextResponse:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    resolved_worldline = LivingWorldPlotService(db_session).worldline_or_404(
        context.world_id,
        group_create.worldline_id,
    )
    if group_create.scene_id is not None:
        _scene_or_404(db_session, context.world_id, group_create.scene_id)
    if group_create.organization_id is not None:
        _organization_or_404(db_session, context.world_id, group_create.organization_id)
    _ensure_agent_string_refs(db_session, context.world_id, group_create.participant_agent_ids)
    existing = db_session.scalars(
        select(GroupInteractionContext).where(
            GroupInteractionContext.world_id == context.world_id,
            GroupInteractionContext.worldline_id == resolved_worldline.id,
            GroupInteractionContext.context_key == group_create.context_key,
        ),
    ).one_or_none()
    if existing is not None:
        raise _conflict("Group interaction context key already exists")
    group_context = GroupInteractionContext(
        id=uuid.uuid4(),
        world_id=context.world_id,
        worldline_id=resolved_worldline.id,
        context_key=group_create.context_key,
        title=group_create.title,
        interaction_type=group_create.interaction_type,
        scene_id=group_create.scene_id,
        organization_id=group_create.organization_id,
        participant_agent_ids=group_create.participant_agent_ids,
        participant_roles=group_create.participant_roles,
        constraints=group_create.constraints,
        status="planned",
        metadata_json=group_create.metadata,
    )
    db_session.add(group_context)
    db_session.flush()
    return _group_context_response(db_session, group_context)


@router.patch(
    "/{world_id}/group-interactions/{context_id}",
    response_model=GroupInteractionContextResponse,
)
def update_group_interaction(
    context_id: uuid.UUID,
    group_update: GroupInteractionUpdateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> GroupInteractionContextResponse:
    require_csrf(request)
    group_context = _group_context_or_404(db_session, context.world_id, context_id)
    for field_name in ("title", "interaction_type", "scene_id", "organization_id", "status"):
        if field_name in group_update.model_fields_set:
            next_value = getattr(group_update, field_name)
            if field_name == "scene_id" and next_value is not None:
                _scene_or_404(db_session, context.world_id, next_value)
            if field_name == "organization_id" and next_value is not None:
                _organization_or_404(db_session, context.world_id, next_value)
            if next_value is not None or field_name in ("scene_id", "organization_id"):
                setattr(group_context, field_name, next_value)
    if "participant_agent_ids" in group_update.model_fields_set:
        participant_ids = group_update.participant_agent_ids or []
        _ensure_agent_string_refs(db_session, context.world_id, participant_ids)
        group_context.participant_agent_ids = participant_ids
    if "participant_roles" in group_update.model_fields_set:
        group_context.participant_roles = group_update.participant_roles or {}
    if "constraints" in group_update.model_fields_set:
        group_context.constraints = group_update.constraints or {}
    if "metadata" in group_update.model_fields_set:
        group_context.metadata_json = group_update.metadata or {}
    db_session.flush()
    return _group_context_response(db_session, group_context)


@router.get(
    "/{world_id}/relationship-suggestions",
    response_model=list[RelationshipEventSuggestionResponse],
)
def list_relationship_suggestions(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
    status_filter: Annotated[SuggestionStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[RelationshipEventSuggestionResponse]:
    _world_or_404(db_session, context.world_id)
    resolved_worldline = LivingWorldPlotService(db_session).worldline_or_404(
        context.world_id,
        worldline_id,
    )
    statement = select(RelationshipEventSuggestion).where(
        RelationshipEventSuggestion.world_id == context.world_id,
        RelationshipEventSuggestion.worldline_id == resolved_worldline.id,
    )
    if status_filter is not None:
        statement = statement.where(RelationshipEventSuggestion.status == status_filter)
    suggestions = db_session.scalars(
        statement.order_by(RelationshipEventSuggestion.score.desc()).limit(limit),
    ).all()
    return [_relationship_suggestion_response(db_session, item) for item in suggestions]


@router.post(
    "/{world_id}/relationship-suggestions/generate",
    response_model=list[RelationshipEventSuggestionResponse],
)
def generate_relationship_suggestions(
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[RelationshipEventSuggestionResponse]:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    suggestions = LivingWorldPlotService(db_session).generate_relationship_suggestions(
        world_id=context.world_id,
        worldline_id=worldline_id,
        limit=limit,
    )
    return [_relationship_suggestion_response(db_session, item) for item in suggestions]


@router.patch(
    "/{world_id}/relationship-suggestions/{suggestion_id}",
    response_model=RelationshipEventSuggestionResponse,
)
def update_relationship_suggestion(
    suggestion_id: uuid.UUID,
    suggestion_update: RelationshipSuggestionUpdateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> RelationshipEventSuggestionResponse:
    require_csrf(request)
    suggestion = _relationship_suggestion_or_404(db_session, context.world_id, suggestion_id)
    if "status" in suggestion_update.model_fields_set and suggestion_update.status is not None:
        suggestion.status = suggestion_update.status
    if "metadata" in suggestion_update.model_fields_set:
        suggestion.metadata_json = suggestion_update.metadata or {}
    db_session.flush()
    return _relationship_suggestion_response(db_session, suggestion)


@router.get(
    "/{world_id}/organization-conflicts",
    response_model=list[OrganizationConflictResponse],
)
def list_organization_conflicts(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
    status_filter: Annotated[OrganizationConflictStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[OrganizationConflictResponse]:
    _world_or_404(db_session, context.world_id)
    resolved_worldline = LivingWorldPlotService(db_session).worldline_or_404(
        context.world_id,
        worldline_id,
    )
    statement = select(OrganizationConflictEvent).where(
        OrganizationConflictEvent.world_id == context.world_id,
        OrganizationConflictEvent.worldline_id == resolved_worldline.id,
    )
    if status_filter is not None:
        statement = statement.where(OrganizationConflictEvent.status == status_filter)
    conflicts = db_session.scalars(
        statement.order_by(OrganizationConflictEvent.updated_at.desc()).limit(limit),
    ).all()
    return [_organization_conflict_response(db_session, item) for item in conflicts]


@router.post(
    "/{world_id}/organization-conflicts",
    response_model=OrganizationConflictResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_organization_conflict(
    conflict_create: OrganizationConflictCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> OrganizationConflictResponse:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    resolved_worldline = LivingWorldPlotService(db_session).worldline_or_404(
        context.world_id,
        conflict_create.worldline_id,
    )
    _organization_or_404(db_session, context.world_id, conflict_create.organization_id)
    if conflict_create.faction_track_id is not None:
        track = db_session.get(FactionProgressTrack, conflict_create.faction_track_id)
        if (
            track is None
            or track.world_id != context.world_id
            or track.worldline_id != resolved_worldline.id
            or track.organization_id != conflict_create.organization_id
        ):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Track not found")
    conflict = OrganizationConflictEvent(
        id=uuid.uuid4(),
        world_id=context.world_id,
        worldline_id=resolved_worldline.id,
        organization_id=conflict_create.organization_id,
        faction_track_id=conflict_create.faction_track_id,
        title=conflict_create.title,
        summary=conflict_create.summary,
        pressure_delta=conflict_create.pressure_delta,
        progress_delta=conflict_create.progress_delta,
        status="proposed",
        metadata_json=conflict_create.metadata,
    )
    db_session.add(conflict)
    db_session.flush()
    return _organization_conflict_response(db_session, conflict)


@router.patch(
    "/{world_id}/organization-conflicts/{conflict_id}",
    response_model=OrganizationConflictResponse,
)
def update_organization_conflict(
    conflict_id: uuid.UUID,
    conflict_update: OrganizationConflictUpdateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> OrganizationConflictResponse:
    require_csrf(request)
    conflict = _organization_conflict_or_404(db_session, context.world_id, conflict_id)
    if "status" in conflict_update.model_fields_set and conflict_update.status is not None:
        conflict.status = conflict_update.status
    if "metadata" in conflict_update.model_fields_set:
        conflict.metadata_json = conflict_update.metadata or {}
    db_session.flush()
    return _organization_conflict_response(db_session, conflict)


@router.post(
    "/{world_id}/organization-conflicts/{conflict_id}/resolve",
    response_model=OrganizationConflictResponse,
)
def resolve_organization_conflict(
    conflict_id: uuid.UUID,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> OrganizationConflictResponse:
    require_csrf(request)
    try:
        conflict = LivingWorldPlotService(db_session).resolve_organization_conflict(
            world_id=context.world_id,
            conflict_id=conflict_id,
            actor_ref=_actor_ref(context.subject),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _organization_conflict_response(db_session, conflict)


@router.get("/{world_id}/rumors", response_model=list[RumorResponse])
def list_rumors(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
    status_filter: Annotated[RumorStatus | None, Query(alias="status")] = None,
    visibility: RumorVisibility | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[RumorResponse]:
    _world_or_404(db_session, context.world_id)
    resolved_worldline = LivingWorldPlotService(db_session).worldline_or_404(
        context.world_id,
        worldline_id,
    )
    statement = select(RumorRecord).where(
        RumorRecord.world_id == context.world_id,
        RumorRecord.worldline_id == resolved_worldline.id,
    )
    if status_filter is not None:
        statement = statement.where(RumorRecord.status == status_filter)
    if visibility is not None:
        statement = statement.where(RumorRecord.visibility == visibility)
    rumors = db_session.scalars(
        statement.order_by(RumorRecord.updated_at.desc()).limit(limit),
    ).all()
    return [_rumor_response(db_session, rumor) for rumor in rumors]


@router.post(
    "/{world_id}/rumors",
    response_model=RumorResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_rumor(
    rumor_create: RumorCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> RumorResponse:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    resolved_worldline = LivingWorldPlotService(db_session).worldline_or_404(
        context.world_id,
        rumor_create.worldline_id,
    )
    if rumor_create.source_agent_id is not None:
        _agent_or_404(db_session, context.world_id, rumor_create.source_agent_id)
    if rumor_create.source_organization_id is not None:
        _organization_or_404(db_session, context.world_id, rumor_create.source_organization_id)
    _ensure_agent_string_refs(db_session, context.world_id, rumor_create.known_agent_ids)
    existing = db_session.scalars(
        select(RumorRecord).where(
            RumorRecord.world_id == context.world_id,
            RumorRecord.worldline_id == resolved_worldline.id,
            RumorRecord.rumor_key == rumor_create.rumor_key,
        ),
    ).one_or_none()
    if existing is not None:
        raise _conflict("Rumor key already exists")
    rumor = RumorRecord(
        id=uuid.uuid4(),
        world_id=context.world_id,
        worldline_id=resolved_worldline.id,
        rumor_key=rumor_create.rumor_key,
        title=rumor_create.title,
        content=rumor_create.content,
        source_agent_id=rumor_create.source_agent_id,
        source_organization_id=rumor_create.source_organization_id,
        visibility=rumor_create.visibility,
        known_agent_ids=rumor_create.known_agent_ids,
        status="active",
        metadata_json=rumor_create.metadata,
    )
    db_session.add(rumor)
    db_session.flush()
    return _rumor_response(db_session, rumor)


@router.patch("/{world_id}/rumors/{rumor_id}", response_model=RumorResponse)
def update_rumor(
    rumor_id: uuid.UUID,
    rumor_update: RumorUpdateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> RumorResponse:
    require_csrf(request)
    rumor = _rumor_or_404(db_session, context.world_id, rumor_id)
    for field_name in ("title", "content", "visibility", "status"):
        if field_name in rumor_update.model_fields_set:
            next_value = getattr(rumor_update, field_name)
            if next_value is not None:
                setattr(rumor, field_name, next_value)
    if "known_agent_ids" in rumor_update.model_fields_set:
        known_agent_ids = rumor_update.known_agent_ids or []
        _ensure_agent_string_refs(db_session, context.world_id, known_agent_ids)
        rumor.known_agent_ids = known_agent_ids
    if "metadata" in rumor_update.model_fields_set:
        rumor.metadata_json = rumor_update.metadata or {}
    db_session.flush()
    return _rumor_response(db_session, rumor)


@router.get(
    "/{world_id}/rumor-propagations",
    response_model=list[RumorPropagationResponse],
)
def list_rumor_propagations(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
    status_filter: Annotated[RumorPropagationStatus | None, Query(alias="status")] = None,
    target_agent_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[RumorPropagationResponse]:
    _world_or_404(db_session, context.world_id)
    resolved_worldline = LivingWorldPlotService(db_session).worldline_or_404(
        context.world_id,
        worldline_id,
    )
    statement = select(RumorPropagation).where(
        RumorPropagation.world_id == context.world_id,
        RumorPropagation.worldline_id == resolved_worldline.id,
    )
    if status_filter is not None:
        statement = statement.where(RumorPropagation.status == status_filter)
    if target_agent_id is not None:
        _agent_or_404(db_session, context.world_id, target_agent_id)
        statement = statement.where(RumorPropagation.target_agent_id == target_agent_id)
    propagations = db_session.scalars(
        statement.order_by(RumorPropagation.updated_at.desc()).limit(limit),
    ).all()
    return [_rumor_propagation_response(db_session, item) for item in propagations]


@router.post(
    "/{world_id}/rumor-propagations",
    response_model=RumorPropagationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_rumor_propagation(
    propagation_create: RumorPropagationCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> RumorPropagationResponse:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    resolved_worldline = LivingWorldPlotService(db_session).worldline_or_404(
        context.world_id,
        propagation_create.worldline_id,
    )
    rumor = _rumor_or_404(db_session, context.world_id, propagation_create.rumor_id)
    if rumor.worldline_id != resolved_worldline.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rumor not found")
    if propagation_create.source_agent_id is not None:
        _agent_or_404(db_session, context.world_id, propagation_create.source_agent_id)
    if propagation_create.target_agent_id is not None:
        _agent_or_404(db_session, context.world_id, propagation_create.target_agent_id)
    if propagation_create.target_organization_id is not None:
        _organization_or_404(
            db_session,
            context.world_id,
            propagation_create.target_organization_id,
        )
    propagation = RumorPropagation(
        id=uuid.uuid4(),
        world_id=context.world_id,
        worldline_id=resolved_worldline.id,
        rumor_id=rumor.id,
        source_agent_id=propagation_create.source_agent_id,
        target_agent_id=propagation_create.target_agent_id,
        target_organization_id=propagation_create.target_organization_id,
        propagation_reason=propagation_create.propagation_reason,
        status="pending",
        metadata_json=propagation_create.metadata,
    )
    db_session.add(propagation)
    db_session.flush()
    return _rumor_propagation_response(db_session, propagation)


@router.patch(
    "/{world_id}/rumor-propagations/{propagation_id}",
    response_model=RumorPropagationResponse,
)
def update_rumor_propagation(
    propagation_id: uuid.UUID,
    propagation_update: RumorPropagationUpdateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> RumorPropagationResponse:
    require_csrf(request)
    propagation = _rumor_propagation_or_404(db_session, context.world_id, propagation_id)
    if "status" in propagation_update.model_fields_set and propagation_update.status is not None:
        propagation.status = propagation_update.status
    if "metadata" in propagation_update.model_fields_set:
        propagation.metadata_json = propagation_update.metadata or {}
    db_session.flush()
    return _rumor_propagation_response(db_session, propagation)


@router.post(
    "/{world_id}/rumor-propagations/{propagation_id}/deliver",
    response_model=RumorPropagationResponse,
)
def deliver_rumor_propagation(
    propagation_id: uuid.UUID,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> RumorPropagationResponse:
    require_csrf(request)
    try:
        propagation = LivingWorldPlotService(db_session).deliver_rumor(
            world_id=context.world_id,
            propagation_id=propagation_id,
            actor_ref=_actor_ref(context.subject),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _rumor_propagation_response(db_session, propagation)


@router.get("/{world_id}/living-world-dashboard", response_model=LivingWorldDashboardResponse)
def get_living_world_dashboard(
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
) -> LivingWorldDashboardResponse:
    _world_or_404(db_session, context.world_id)
    dashboard = LivingWorldGuardrailService(db_session).dashboard(
        world_id=context.world_id,
        worldline_id=worldline_id,
        user_id=context.subject.user_id,
    )
    return _living_world_dashboard_response(dashboard)


@router.get("/{world_id}/knowledge", response_model=list[KnowledgeFactResponse])
def list_knowledge_facts(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
    agent_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[KnowledgeFactResponse]:
    _world_or_404(db_session, context.world_id)
    if agent_id is not None:
        _agent_or_404(db_session, context.world_id, agent_id)
    facts = LivingWorldGuardrailService(db_session).list_agent_knowledge(
        world_id=context.world_id,
        worldline_id=worldline_id,
        agent_id=agent_id,
        limit=limit,
    )
    return [_knowledge_fact_response(db_session, fact) for fact in facts]


@router.put("/{world_id}/knowledge", response_model=KnowledgeFactResponse)
def upsert_knowledge_fact(
    knowledge_upsert: KnowledgeFactUpsertRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> KnowledgeFactResponse:
    require_csrf(request)
    _agent_or_404(db_session, context.world_id, knowledge_upsert.agent_id)
    fact = LivingWorldGuardrailService(db_session).upsert_knowledge_fact(
        world_id=context.world_id,
        worldline_id=knowledge_upsert.worldline_id,
        agent_id=knowledge_upsert.agent_id,
        fact_key=knowledge_upsert.fact_key,
        knowledge_kind=knowledge_upsert.knowledge_kind,
        content=knowledge_upsert.content,
        confidence=knowledge_upsert.confidence,
        visibility=knowledge_upsert.visibility,
        source_event_id=knowledge_upsert.source_event_id,
        source_ref=knowledge_upsert.source_ref,
        metadata=knowledge_upsert.metadata,
    )
    return _knowledge_fact_response(db_session, fact)


@router.get("/{world_id}/secrets", response_model=list[SecretResponse])
def list_secrets(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
    status_filter: Annotated[SecretStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[SecretResponse]:
    _world_or_404(db_session, context.world_id)
    resolved_worldline = LivingWorldGuardrailService(db_session).worldline_or_404(
        context.world_id,
        worldline_id,
    )
    statement = select(SecretRecord).where(
        SecretRecord.world_id == context.world_id,
        SecretRecord.worldline_id == resolved_worldline.id,
    )
    if status_filter is not None:
        statement = statement.where(SecretRecord.status == status_filter)
    secrets = db_session.scalars(
        statement.order_by(SecretRecord.updated_at.desc()).limit(limit)
    ).all()
    return [_secret_response(secret) for secret in secrets]


@router.post(
    "/{world_id}/secrets", response_model=SecretResponse, status_code=status.HTTP_201_CREATED
)
def create_secret(
    secret_create: SecretCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> SecretResponse:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    _ensure_agent_string_refs(db_session, context.world_id, secret_create.holder_agent_ids)
    try:
        secret = LivingWorldGuardrailService(db_session).create_secret(
            world_id=context.world_id,
            worldline_id=secret_create.worldline_id,
            secret_key=secret_create.secret_key,
            title=secret_create.title,
            content=secret_create.content,
            holder_agent_ids=secret_create.holder_agent_ids,
            reveal_conditions=secret_create.reveal_conditions,
            consequence_metadata=secret_create.consequence_metadata,
            visibility=secret_create.visibility,
            metadata=secret_create.metadata,
        )
    except ValueError as exc:
        raise _conflict(str(exc)) from exc
    return _secret_response(secret)


@router.post("/{world_id}/secrets/{secret_id}/reveal", response_model=SecretResponse)
def reveal_secret(
    secret_id: uuid.UUID,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> SecretResponse:
    require_csrf(request)
    try:
        secret = LivingWorldGuardrailService(db_session).reveal_secret(
            world_id=context.world_id,
            secret_id=secret_id,
            actor_ref=_actor_ref(context.subject),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _secret_response(secret)


@router.get("/{world_id}/emotional-states", response_model=list[EmotionalStateResponse])
def list_emotional_states(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
    agent_id: uuid.UUID | None = None,
) -> list[EmotionalStateResponse]:
    _world_or_404(db_session, context.world_id)
    resolved_worldline = LivingWorldGuardrailService(db_session).worldline_or_404(
        context.world_id,
        worldline_id,
    )
    statement = select(CharacterEmotionalState).where(
        CharacterEmotionalState.world_id == context.world_id,
        CharacterEmotionalState.worldline_id == resolved_worldline.id,
    )
    if agent_id is not None:
        _agent_or_404(db_session, context.world_id, agent_id)
        statement = statement.where(CharacterEmotionalState.agent_id == agent_id)
    states = db_session.scalars(statement.order_by(CharacterEmotionalState.updated_at.desc())).all()
    return [_emotional_state_response(db_session, state_item) for state_item in states]


@router.put("/{world_id}/emotional-states", response_model=EmotionalStateResponse)
def upsert_emotional_state(
    state_upsert: EmotionalStateUpsertRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> EmotionalStateResponse:
    require_csrf(request)
    _agent_or_404(db_session, context.world_id, state_upsert.agent_id)
    state_item = LivingWorldGuardrailService(db_session).upsert_emotional_state(
        world_id=context.world_id,
        worldline_id=state_upsert.worldline_id,
        agent_id=state_upsert.agent_id,
        mood=state_upsert.mood,
        stress=state_upsert.stress,
        fatigue=state_upsert.fatigue,
        anticipation=state_upsert.anticipation,
        jealousy=state_upsert.jealousy,
        anger=state_upsert.anger,
        source_event_id=state_upsert.source_event_id,
        expires_at=state_upsert.expires_at,
        metadata=state_upsert.metadata,
    )
    return _emotional_state_response(db_session, state_item)


@router.get("/{world_id}/relationship-repairs", response_model=list[RelationshipRepairResponse])
def list_relationship_repairs(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
    status_filter: Annotated[RelationshipRepairStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[RelationshipRepairResponse]:
    _world_or_404(db_session, context.world_id)
    resolved_worldline = LivingWorldGuardrailService(db_session).worldline_or_404(
        context.world_id,
        worldline_id,
    )
    statement = select(RelationshipRepairRecord).where(
        RelationshipRepairRecord.world_id == context.world_id,
        RelationshipRepairRecord.worldline_id == resolved_worldline.id,
    )
    if status_filter is not None:
        statement = statement.where(RelationshipRepairRecord.status == status_filter)
    records = db_session.scalars(
        statement.order_by(RelationshipRepairRecord.created_at.desc()).limit(limit),
    ).all()
    return [_relationship_repair_response(record) for record in records]


@router.post(
    "/{world_id}/relationship-repairs",
    response_model=RelationshipRepairResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_relationship_repair(
    repair_create: RelationshipRepairCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> RelationshipRepairResponse:
    require_csrf(request)
    try:
        repair = LivingWorldGuardrailService(db_session).propose_relationship_repair(
            world_id=context.world_id,
            worldline_id=repair_create.worldline_id,
            relationship_id=repair_create.relationship_id,
            repair_kind=repair_create.repair_kind,
            reason=repair_create.reason,
            score_delta=repair_create.score_delta,
            metadata=repair_create.metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _relationship_repair_response(repair)


@router.post(
    "/{world_id}/relationship-repairs/{repair_id}/apply",
    response_model=RelationshipRepairResponse,
)
def apply_relationship_repair(
    repair_id: uuid.UUID,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> RelationshipRepairResponse:
    require_csrf(request)
    try:
        repair = LivingWorldGuardrailService(db_session, load_settings()).apply_relationship_repair(
            world_id=context.world_id,
            repair_id=repair_id,
            actor_ref=_actor_ref(context.subject),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _relationship_repair_response(repair)


@router.get("/{world_id}/player-journal", response_model=list[JournalEntryResponse])
def list_player_journal(
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[JournalEntryResponse]:
    _world_or_404(db_session, context.world_id)
    resolved_worldline = LivingWorldGuardrailService(db_session).worldline_or_404(
        context.world_id,
        worldline_id,
    )
    requested_user_id = user_id or context.subject.user_id
    if requested_user_id != context.subject.user_id and context.role != AuthRole.WORLD_ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    statement = select(PlayerJournalEntry).where(
        PlayerJournalEntry.world_id == context.world_id,
        PlayerJournalEntry.worldline_id == resolved_worldline.id,
        PlayerJournalEntry.user_id == requested_user_id,
    )
    entries = db_session.scalars(
        statement.order_by(PlayerJournalEntry.created_at.desc()).limit(limit)
    ).all()
    return [_journal_entry_response(entry) for entry in entries]


@router.post(
    "/{world_id}/player-journal",
    response_model=JournalEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_player_journal_entry(
    entry_create: JournalEntryCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> JournalEntryResponse:
    require_csrf(request)
    user_id = entry_create.user_id or context.subject.user_id
    _user_or_404(db_session, user_id)
    entry = LivingWorldGuardrailService(db_session).create_journal_entry(
        world_id=context.world_id,
        worldline_id=entry_create.worldline_id,
        user_id=user_id,
        player_actor_id=entry_create.player_actor_id,
        entry_kind=entry_create.entry_kind,
        title=entry_create.title,
        body=entry_create.body,
        source_event_id=entry_create.source_event_id,
        source_ref=entry_create.source_ref,
        visibility=entry_create.visibility,
        metadata=entry_create.metadata,
    )
    return _journal_entry_response(entry)


@router.get("/{world_id}/notifications", response_model=list[InWorldNotificationResponse])
def list_notifications(
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
    status_filter: Annotated[NotificationStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[InWorldNotificationResponse]:
    _world_or_404(db_session, context.world_id)
    resolved_worldline = LivingWorldGuardrailService(db_session).worldline_or_404(
        context.world_id,
        worldline_id,
    )
    statement = select(InWorldNotification).where(
        InWorldNotification.world_id == context.world_id,
        InWorldNotification.worldline_id == resolved_worldline.id,
        InWorldNotification.user_id == context.subject.user_id,
    )
    if context.role == AuthRole.WORLD_ADMIN.value:
        statement = select(InWorldNotification).where(
            InWorldNotification.world_id == context.world_id,
            InWorldNotification.worldline_id == resolved_worldline.id,
        )
    if status_filter is not None:
        statement = statement.where(InWorldNotification.status == status_filter)
    notifications = db_session.scalars(
        statement.order_by(InWorldNotification.created_at.desc()).limit(limit)
    ).all()
    return [_notification_response(notification) for notification in notifications]


@router.post(
    "/{world_id}/notifications",
    response_model=InWorldNotificationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_notification(
    notification_create: NotificationCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> InWorldNotificationResponse:
    require_csrf(request)
    user_id = notification_create.user_id or context.subject.user_id
    _user_or_404(db_session, user_id)
    notification = LivingWorldGuardrailService(db_session).create_notification(
        world_id=context.world_id,
        worldline_id=notification_create.worldline_id,
        user_id=user_id,
        notification_kind=notification_create.notification_kind,
        title=notification_create.title,
        body=notification_create.body,
        source_event_id=notification_create.source_event_id,
        source_ref=notification_create.source_ref,
        metadata=notification_create.metadata,
    )
    return _notification_response(notification)


@router.get("/{world_id}/interventions", response_model=list[PlayerInterventionResponse])
def list_interventions(
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    status_filter: Annotated[InterventionStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[PlayerInterventionResponse]:
    _world_or_404(db_session, context.world_id)
    resolved_worldline = LivingWorldGuardrailService(db_session).worldline_or_404(
        context.world_id,
        worldline_id,
    )
    requested_user_id = user_id or context.subject.user_id
    if requested_user_id != context.subject.user_id and context.role != AuthRole.WORLD_ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    statement = select(PlayerInterventionRecord).where(
        PlayerInterventionRecord.world_id == context.world_id,
        PlayerInterventionRecord.worldline_id == resolved_worldline.id,
        PlayerInterventionRecord.user_id == requested_user_id,
    )
    if context.role == AuthRole.WORLD_ADMIN.value and user_id is None:
        statement = select(PlayerInterventionRecord).where(
            PlayerInterventionRecord.world_id == context.world_id,
            PlayerInterventionRecord.worldline_id == resolved_worldline.id,
        )
    if status_filter is not None:
        statement = statement.where(PlayerInterventionRecord.status == status_filter)
    interventions = db_session.scalars(
        statement.order_by(PlayerInterventionRecord.created_at.desc()).limit(limit),
    ).all()
    return [_intervention_response(intervention) for intervention in interventions]


@router.post(
    "/{world_id}/interventions",
    response_model=PlayerInterventionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_intervention(
    intervention_create: InterventionCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> PlayerInterventionResponse:
    require_csrf(request)
    user_id = intervention_create.user_id or context.subject.user_id
    if user_id != context.subject.user_id and context.role != AuthRole.WORLD_ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if intervention_create.target_agent_id is not None:
        _agent_or_404(db_session, context.world_id, intervention_create.target_agent_id)
    if intervention_create.target_scene_id is not None:
        _scene_or_404(db_session, context.world_id, intervention_create.target_scene_id)
    try:
        intervention = LivingWorldGuardrailService(db_session).record_intervention(
            world_id=context.world_id,
            worldline_id=intervention_create.worldline_id,
            user_id=user_id,
            player_actor_id=intervention_create.player_actor_id,
            intervention_kind=intervention_create.intervention_kind,
            target_agent_id=intervention_create.target_agent_id,
            target_scene_id=intervention_create.target_scene_id,
            prompt=intervention_create.prompt,
            metadata=intervention_create.metadata,
            actor_ref=_actor_ref(context.subject),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    return _intervention_response(intervention)


@router.get("/{world_id}/gm-style-reviews", response_model=list[GMStyleReviewResponse])
def list_gm_style_reviews(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
    status_filter: Annotated[ReviewStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[GMStyleReviewResponse]:
    _world_or_404(db_session, context.world_id)
    resolved_worldline = LivingWorldGuardrailService(db_session).worldline_or_404(
        context.world_id,
        worldline_id,
    )
    statement = select(GMStyleReview).where(
        GMStyleReview.world_id == context.world_id,
        GMStyleReview.worldline_id == resolved_worldline.id,
    )
    if status_filter is not None:
        statement = statement.where(GMStyleReview.status == status_filter)
    reviews = db_session.scalars(
        statement.order_by(GMStyleReview.created_at.desc()).limit(limit),
    ).all()
    return [_gm_style_review_response(review) for review in reviews]


@router.post(
    "/{world_id}/gm-style-reviews",
    response_model=GMStyleReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_gm_style_review(
    review_create: GMStyleReviewCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> GMStyleReviewResponse:
    require_csrf(request)
    review = LivingWorldGuardrailService(db_session).review_gm_style(
        world_id=context.world_id,
        worldline_id=review_create.worldline_id,
        source_kind=review_create.source_kind,
        source_ref=review_create.source_ref,
        reviewed_text=review_create.reviewed_text,
        metadata=review_create.metadata,
    )
    return _gm_style_review_response(review)


@router.get(
    "/{world_id}/narrative-continuity-reviews",
    response_model=list[NarrativeContinuityReviewResponse],
)
def list_narrative_continuity_reviews(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
    status_filter: Annotated[ReviewStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[NarrativeContinuityReviewResponse]:
    _world_or_404(db_session, context.world_id)
    resolved_worldline = LivingWorldGuardrailService(db_session).worldline_or_404(
        context.world_id,
        worldline_id,
    )
    statement = select(NarrativeContinuityReview).where(
        NarrativeContinuityReview.world_id == context.world_id,
        NarrativeContinuityReview.worldline_id == resolved_worldline.id,
    )
    if status_filter is not None:
        statement = statement.where(NarrativeContinuityReview.status == status_filter)
    reviews = db_session.scalars(
        statement.order_by(NarrativeContinuityReview.created_at.desc()).limit(limit),
    ).all()
    return [_narrative_continuity_review_response(review) for review in reviews]


@router.post(
    "/{world_id}/narrative-continuity-reviews",
    response_model=NarrativeContinuityReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_narrative_continuity_review(
    review_create: NarrativeContinuityReviewCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> NarrativeContinuityReviewResponse:
    require_csrf(request)
    if review_create.artifact_id is not None:
        artifact = db_session.get(NarrativeArtifact, review_create.artifact_id)
        if artifact is None or artifact.world_id != context.world_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    review = LivingWorldGuardrailService(db_session).review_narrative_continuity(
        world_id=context.world_id,
        worldline_id=review_create.worldline_id,
        artifact_id=review_create.artifact_id,
        source_kind=review_create.source_kind,
        source_ref=review_create.source_ref,
        reviewed_text=review_create.reviewed_text,
        metadata=review_create.metadata,
    )
    return _narrative_continuity_review_response(review)


@router.get("/{world_id}/route-milestones", response_model=list[RouteMilestoneResponse])
def list_route_milestones(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
    status_filter: Annotated[RouteMilestoneStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[RouteMilestoneResponse]:
    _world_or_404(db_session, context.world_id)
    resolved_worldline = LivingWorldBetaService(db_session).worldline_or_404(
        context.world_id,
        worldline_id,
    )
    statement = select(RouteMilestone).where(
        RouteMilestone.world_id == context.world_id,
        RouteMilestone.worldline_id == resolved_worldline.id,
    )
    if status_filter is not None:
        statement = statement.where(RouteMilestone.status == status_filter)
    milestones = db_session.scalars(
        statement.order_by(RouteMilestone.stage, RouteMilestone.created_at.desc()).limit(limit),
    ).all()
    return [_route_milestone_response(db_session, milestone) for milestone in milestones]


@router.post(
    "/{world_id}/route-milestones",
    response_model=RouteMilestoneResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_route_milestone(
    milestone_create: RouteMilestoneCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> RouteMilestoneResponse:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    try:
        milestone = LivingWorldBetaService(db_session).create_route_milestone(
            world_id=context.world_id,
            worldline_id=milestone_create.worldline_id,
            milestone_key=milestone_create.milestone_key,
            title=milestone_create.title,
            description=milestone_create.description,
            stage=milestone_create.stage,
            status=milestone_create.status,
            route_affinity_id=milestone_create.route_affinity_id,
            plot_thread_id=milestone_create.plot_thread_id,
            agent_id=milestone_create.agent_id,
            conditions=milestone_create.conditions,
            evidence_metadata=milestone_create.evidence_metadata,
            metadata=milestone_create.metadata,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return _route_milestone_response(db_session, milestone)


@router.get("/{world_id}/ending-candidates", response_model=list[EndingCandidateResponse])
def list_ending_candidates(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
    status_filter: Annotated[EndingStatus | None, Query(alias="status")] = None,
    ending_type: EndingType | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[EndingCandidateResponse]:
    _world_or_404(db_session, context.world_id)
    resolved_worldline = LivingWorldBetaService(db_session).worldline_or_404(
        context.world_id,
        worldline_id,
    )
    statement = select(EndingCandidate).where(
        EndingCandidate.world_id == context.world_id,
        EndingCandidate.worldline_id == resolved_worldline.id,
    )
    if status_filter is not None:
        statement = statement.where(EndingCandidate.status == status_filter)
    if ending_type is not None:
        statement = statement.where(EndingCandidate.ending_type == ending_type)
    endings = db_session.scalars(
        statement.order_by(EndingCandidate.ending_type, EndingCandidate.updated_at.desc()).limit(
            limit
        ),
    ).all()
    return [_ending_candidate_response(db_session, ending) for ending in endings]


@router.post(
    "/{world_id}/ending-candidates",
    response_model=EndingCandidateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_ending_candidate(
    ending_create: EndingCandidateCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> EndingCandidateResponse:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    try:
        ending = LivingWorldBetaService(db_session).create_ending_candidate(
            world_id=context.world_id,
            worldline_id=ending_create.worldline_id,
            ending_key=ending_create.ending_key,
            title=ending_create.title,
            ending_type=ending_create.ending_type,
            status=ending_create.status,
            route_affinity_id=ending_create.route_affinity_id,
            plot_thread_id=ending_create.plot_thread_id,
            agent_id=ending_create.agent_id,
            requirements=ending_create.requirements,
            outcome_summary=ending_create.outcome_summary,
            evidence_metadata=ending_create.evidence_metadata,
            metadata=ending_create.metadata,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return _ending_candidate_response(db_session, ending)


@router.post(
    "/{world_id}/ending-candidates/{ending_id}/dry-run",
    response_model=EndingDryRunResponse,
)
def dry_run_ending_candidate(
    ending_id: uuid.UUID,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
) -> EndingDryRunResponse:
    require_csrf(request)
    ending = _ending_candidate_or_404(db_session, context.world_id, ending_id)
    try:
        dry_run = LivingWorldBetaService(db_session).dry_run_ending(
            world_id=context.world_id,
            worldline_id=worldline_id,
            ending=ending,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _ending_dry_run_response(dry_run)


@router.get("/{world_id}/long-run-evals", response_model=list[LongRunEvalResponse])
def list_long_run_evals(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[LongRunEvalResponse]:
    _world_or_404(db_session, context.world_id)
    resolved_worldline = LivingWorldBetaService(db_session).worldline_or_404(
        context.world_id,
        worldline_id,
    )
    runs = db_session.scalars(
        select(LongRunEvalRun)
        .where(
            LongRunEvalRun.world_id == context.world_id,
            LongRunEvalRun.worldline_id == resolved_worldline.id,
        )
        .order_by(LongRunEvalRun.created_at.desc())
        .limit(limit),
    ).all()
    return [_long_run_eval_response(run) for run in runs]


@router.post(
    "/{world_id}/long-run-evals",
    response_model=LongRunEvalResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_long_run_eval(
    eval_create: LongRunEvalCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> LongRunEvalResponse:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    run = LivingWorldBetaService(db_session).run_long_eval(
        world_id=context.world_id,
        worldline_id=eval_create.worldline_id,
        eval_key=eval_create.eval_key,
        horizon_days=eval_create.horizon_days,
        metadata=eval_create.metadata,
    )
    return _long_run_eval_response(run)


@router.get("/{world_id}/authoring-templates", response_model=list[AuthoringTemplateResponse])
def list_authoring_templates(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    template_kind: AuthoringTemplateKind | None = None,
) -> list[AuthoringTemplateResponse]:
    _world_or_404(db_session, context.world_id)
    statement = select(AuthoringTemplate).where(AuthoringTemplate.world_id == context.world_id)
    if template_kind is not None:
        statement = statement.where(AuthoringTemplate.template_kind == template_kind)
    templates = db_session.scalars(
        statement.order_by(AuthoringTemplate.template_kind, AuthoringTemplate.template_key),
    ).all()
    return [_authoring_template_response(template) for template in templates]


@router.post(
    "/{world_id}/authoring-templates",
    response_model=AuthoringTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_authoring_template(
    template_create: AuthoringTemplateCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AuthoringTemplateResponse:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    try:
        template = LivingWorldBetaService(db_session).create_authoring_template(
            world_id=context.world_id,
            template_key=template_create.template_key,
            template_kind=template_create.template_kind,
            name=template_create.name,
            description=template_create.description,
            content=template_create.content,
            metadata=template_create.metadata,
        )
    except ValueError as exc:
        raise _conflict(str(exc)) from exc
    return _authoring_template_response(template)


@router.post(
    "/{world_id}/authoring-templates/{template_id}/preview",
    response_model=AuthoringImportJobResponse,
)
def preview_authoring_template(
    template_id: uuid.UUID,
    preview_create: AuthoringTemplateApplyRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AuthoringImportJobResponse:
    require_csrf(request)
    template = _authoring_template_or_404(db_session, context.world_id, template_id)
    try:
        job = LivingWorldBetaService(db_session).preview_authoring_template(
            world_id=context.world_id,
            template=template,
            metadata=preview_create.metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _authoring_import_job_response(job)


@router.post(
    "/{world_id}/authoring-templates/{template_id}/apply",
    response_model=AuthoringImportJobResponse,
)
def apply_authoring_template(
    template_id: uuid.UUID,
    apply_create: AuthoringTemplateApplyRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AuthoringImportJobResponse:
    require_csrf(request)
    template = _authoring_template_or_404(db_session, context.world_id, template_id)
    try:
        job = LivingWorldBetaService(db_session).apply_authoring_template(
            world_id=context.world_id,
            template=template,
            metadata=apply_create.metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _authoring_import_job_response(job)


@router.get("/{world_id}/release-profile", response_model=ReleaseProfileResponse | None)
def get_release_profile(
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ReleaseProfileResponse | None:
    _world_or_404(db_session, context.world_id)
    profile = LivingWorldBetaService(db_session).get_release_profile(world_id=context.world_id)
    return None if profile is None else _release_profile_response(profile)


@router.put("/{world_id}/release-profile", response_model=ReleaseProfileResponse)
def upsert_release_profile(
    profile_upsert: ReleaseProfileUpsertRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ReleaseProfileResponse:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    profile = LivingWorldBetaService(db_session).upsert_release_profile(
        world_id=context.world_id,
        profile_key=profile_upsert.profile_key,
        status=profile_upsert.status,
        branch_policy=profile_upsert.branch_policy,
        backup_policy=profile_upsert.backup_policy,
        content_review_policy=profile_upsert.content_review_policy,
        player_permission_policy=profile_upsert.player_permission_policy,
        worldline_policy=profile_upsert.worldline_policy,
        checklist=profile_upsert.checklist,
        metadata=profile_upsert.metadata,
    )
    return _release_profile_response(profile)


@router.get("/{world_id}/beta-checklists", response_model=list[BetaChecklistRunResponse])
def list_beta_checklists(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[BetaChecklistRunResponse]:
    _world_or_404(db_session, context.world_id)
    resolved_worldline = LivingWorldBetaService(db_session).worldline_or_404(
        context.world_id,
        worldline_id,
    )
    runs = db_session.scalars(
        select(BetaChecklistRun)
        .where(
            BetaChecklistRun.world_id == context.world_id,
            BetaChecklistRun.worldline_id == resolved_worldline.id,
        )
        .order_by(BetaChecklistRun.created_at.desc())
        .limit(limit),
    ).all()
    return [_beta_checklist_run_response(run) for run in runs]


@router.post(
    "/{world_id}/beta-checklists",
    response_model=BetaChecklistRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_beta_checklist(
    checklist_create: BetaChecklistRunCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> BetaChecklistRunResponse:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    run = LivingWorldBetaService(db_session).run_beta_checklist(
        world_id=context.world_id,
        worldline_id=checklist_create.worldline_id,
        run_key=checklist_create.run_key,
        actor_ref=_actor_ref(context.subject),
        metadata=checklist_create.metadata,
    )
    return _beta_checklist_run_response(run)


@router.get(
    "/{world_id}/beta-checklists/{run_id}/items",
    response_model=list[BetaChecklistItemResponse],
)
def list_beta_checklist_items(
    run_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[BetaChecklistItemResponse]:
    _world_or_404(db_session, context.world_id)
    run = _beta_checklist_run_or_404(db_session, context.world_id, run_id)
    items = db_session.scalars(
        select(BetaChecklistItem)
        .where(BetaChecklistItem.run_id == run.id)
        .order_by(BetaChecklistItem.item_key),
    ).all()
    return [_beta_checklist_item_response(item) for item in items]


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
            narrative_role=cast(NarrativeRole | None, agent.narrative_role),
            importance=cast(CharacterImportance | None, agent.importance),
            canon_status=cast(ContinuityStatus | None, agent.canon_status),
            character_category=cast(CharacterCategory | None, agent.character_category),
            character_profile=agent.character_profile,
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
    worldline_id: uuid.UUID | None = None,
) -> WorldReplayState:
    _world_or_404(db_session, context.world_id)
    return WorldReplayService(db_session, load_settings()).replay_state(
        context.world_id,
        worldline_id=worldline_id,
    )


@router.get("/{world_id}/snapshots/latest", response_model=WorldSnapshotResponse | None)
def latest_snapshot(
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
) -> WorldSnapshotResponse | None:
    _world_or_404(db_session, context.world_id)
    snapshot = WorldReplayService(db_session, load_settings()).latest_snapshot(
        context.world_id,
        worldline_id=worldline_id,
    )
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
    worldline_id: uuid.UUID | None = None,
) -> WorldSnapshotIntegrityReport:
    _world_or_404(db_session, context.world_id)
    return WorldReplayService(db_session, load_settings()).snapshot_integrity(
        context.world_id,
        worldline_id=worldline_id,
    )


@router.get("/{world_id}/events", response_model=list[WorldEventResponse])
def list_world_events(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    event_name: Annotated[str | None, Query(min_length=3, max_length=120)] = None,
    actor_ref: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
    sequence_after: Annotated[int | None, Query(ge=0)] = None,
    sequence_before: Annotated[int | None, Query(ge=1)] = None,
    importance: Annotated[EventImportance | None, Query()] = None,
    worldline_id: uuid.UUID | None = None,
    wall_time_from: datetime | None = None,
    wall_time_to: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[WorldEventResponse]:
    _world_or_404(db_session, context.world_id)
    wall_time_from = _optional_query_time(wall_time_from, "wall_time_from")
    wall_time_to = _optional_query_time(wall_time_to, "wall_time_to")
    statement = select(WorldEventModel).where(WorldEventModel.world_id == context.world_id)
    resolved_worldline = LivingWorldGMService(db_session).worldline_or_404(
        context.world_id,
        worldline_id,
    )
    statement = statement.where(
        or_(
            WorldEventModel.worldline_id == resolved_worldline.id,
            WorldEventModel.worldline_id.is_(None),
        )
        if resolved_worldline.parent_worldline_id is None
        else WorldEventModel.worldline_id == resolved_worldline.id
    )
    if event_name is not None:
        statement = statement.where(WorldEventModel.event_name == event_name)
    if actor_ref is not None:
        statement = statement.where(WorldEventModel.actor_ref == actor_ref)
    if importance is not None:
        statement = statement.where(WorldEventModel.importance == importance)
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
    start_time = (
        start_world_time
        or WorldClockService(db_session)
        .view(
            context.world_id,
        )
        .effective_world_time
    )
    return _calendar_conflict_report_response(
        CalendarService(db_session).detect_conflicts(
            world_id=context.world_id,
            start_world_time=start_time,
            horizon_hours=horizon_hours,
            limit=limit,
        ),
    )


@router.get("/{world_id}/daily-life/preview", response_model=DailyLifePreviewResponse)
def preview_daily_life(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    start_world_time: Annotated[datetime | None, Query()] = None,
    horizon_hours: Annotated[int, Query(ge=1, le=168)] = 24,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    worldline_id: uuid.UUID | None = None,
) -> DailyLifePreviewResponse:
    _world_or_404(db_session, context.world_id)
    if start_world_time is not None:
        start_world_time = _timezone_aware(start_world_time, "start_world_time")
    preview = LivingWorldAutonomyService(db_session).preview_daily_life(
        world_id=context.world_id,
        start_world_time=start_world_time,
        horizon_hours=horizon_hours,
        limit=limit,
        worldline_id=worldline_id,
    )
    return DailyLifePreviewResponse(
        world_id=preview.world_id,
        start_world_time=preview.start_world_time,
        horizon_hours=preview.horizon_hours,
        candidate_count=preview.candidate_count,
        candidates=[
            _daily_life_candidate_response(db_session, item) for item in preview.candidates
        ],
    )


@router.post(
    "/{world_id}/daily-life/generate",
    response_model=list[DailyLifeEventCandidateResponse],
)
def generate_daily_life_candidates(
    generate_request: DailyLifeGenerateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[DailyLifeEventCandidateResponse]:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    candidates = LivingWorldAutonomyService(db_session).generate_daily_life_candidates(
        world_id=context.world_id,
        horizon_hours=generate_request.horizon_hours,
        limit=generate_request.limit,
        worldline_id=generate_request.worldline_id,
    )
    return [_daily_life_candidate_response(db_session, item) for item in candidates]


@router.get(
    "/{world_id}/daily-life/candidates",
    response_model=list[DailyLifeEventCandidateResponse],
)
def list_daily_life_candidates(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    status_filter: Annotated[DailyLifeCandidateStatus | None, Query(alias="status")] = None,
    worldline_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[DailyLifeEventCandidateResponse]:
    _world_or_404(db_session, context.world_id)
    resolved_worldline = LivingWorldGMService(db_session).worldline_or_404(
        context.world_id,
        worldline_id,
    )
    statement = select(DailyLifeEventCandidate).where(
        DailyLifeEventCandidate.world_id == context.world_id,
        DailyLifeEventCandidate.worldline_id == resolved_worldline.id,
    )
    if status_filter is not None:
        statement = statement.where(DailyLifeEventCandidate.status == status_filter)
    candidates = db_session.scalars(
        statement.order_by(DailyLifeEventCandidate.starts_at.desc()).limit(limit),
    ).all()
    return [_daily_life_candidate_response(db_session, item) for item in candidates]


@router.post(
    "/{world_id}/offscreen-events",
    response_model=OffscreenEventQueueResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_offscreen_event(
    queue_create: OffscreenQueueCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> OffscreenEventQueueResponse:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    if queue_create.candidate_id is not None:
        candidate = db_session.get(DailyLifeEventCandidate, queue_create.candidate_id)
        if candidate is None or candidate.world_id != context.world_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
        item = LivingWorldAutonomyService(db_session).queue_candidate(
            candidate_id=queue_create.candidate_id,
            event_name=queue_create.event_name,
        )
        return _offscreen_queue_response(item)
    item = OffscreenEventQueueItem(
        world_id=context.world_id,
        worldline_id=(
            LivingWorldGMService(db_session)
            .worldline_or_404(context.world_id, queue_create.worldline_id)
            .id
        ),
        event_name=queue_create.event_name,
        title=queue_create.title,
        payload_json=queue_create.payload,
        due_at=queue_create.due_at,
        importance=queue_create.importance,
        status="pending",
    )
    db_session.add(item)
    db_session.flush()
    return _offscreen_queue_response(item)


@router.get("/{world_id}/offscreen-events", response_model=list[OffscreenEventQueueResponse])
def list_offscreen_events(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    status_filter: Annotated[OffscreenEventStatus | None, Query(alias="status")] = None,
    worldline_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[OffscreenEventQueueResponse]:
    _world_or_404(db_session, context.world_id)
    resolved_worldline = LivingWorldGMService(db_session).worldline_or_404(
        context.world_id,
        worldline_id,
    )
    statement = select(OffscreenEventQueueItem).where(
        OffscreenEventQueueItem.world_id == context.world_id,
        OffscreenEventQueueItem.worldline_id == resolved_worldline.id,
    )
    if status_filter is not None:
        statement = statement.where(OffscreenEventQueueItem.status == status_filter)
    items = db_session.scalars(
        statement.order_by(OffscreenEventQueueItem.due_at.desc()).limit(limit),
    ).all()
    return [_offscreen_queue_response(item) for item in items]


@router.post("/{world_id}/offscreen-events/resolve", response_model=OffscreenResolutionResponse)
def resolve_offscreen_events(
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    worldline_id: uuid.UUID | None = None,
) -> OffscreenResolutionResponse:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    result = LivingWorldAutonomyService(db_session).resolve_due_offscreen_events(
        world_id=context.world_id,
        wall_time=datetime.now(UTC),
        limit=limit,
        actor_ref=_actor_ref(context.subject),
        worldline_id=worldline_id,
    )
    RuntimeDiagnosticsService(db_session).record(
        RuntimeDiagnosticCreate(
            severity=DiagnosticSeverity.INFO,
            component=DiagnosticComponent.RUNTIME,
            event_type="gm.offscreen_events_resolved",
            message="GM world engine resolved due offscreen events.",
            details={
                "processed_count": result.processed_count,
                "resolved_count": result.resolved_count,
                "failed_count": result.failed_count,
            },
            world_id=context.world_id,
        ),
    )
    return _offscreen_resolution_response(result)


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
    worldline_id: uuid.UUID | None = None,
) -> WorldSnapshotResponse:
    require_csrf(request)
    _world_or_404(db_session, context.world_id)
    snapshot = WorldReplayService(db_session, load_settings()).create_snapshot(
        context.world_id,
        actor_ref=_actor_ref(context.subject),
        worldline_id=worldline_id,
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
        region_key=scene_create.region_key,
        location_tags=scene_create.location_tags,
        opening_rules=scene_create.opening_rules,
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
    if "region_key" in scene_update.model_fields_set:
        scene.region_key = scene_update.region_key
    if "location_tags" in scene_update.model_fields_set:
        scene.location_tags = scene_update.location_tags or []
    if "opening_rules" in scene_update.model_fields_set:
        scene.opening_rules = scene_update.opening_rules or {}
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


@router.get("/{world_id}/location-edges", response_model=list[SceneLocationEdgeResponse])
def list_location_edges(
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[SceneLocationEdgeResponse]:
    _world_or_404(db_session, context.world_id)
    edges = db_session.scalars(
        select(SceneLocationEdge)
        .where(SceneLocationEdge.world_id == context.world_id)
        .order_by(SceneLocationEdge.created_at),
    ).all()
    return [_location_edge_response(db_session, edge) for edge in edges]


@router.post(
    "/{world_id}/location-edges",
    response_model=SceneLocationEdgeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_location_edge(
    edge_create: SceneLocationEdgeCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> SceneLocationEdgeResponse:
    require_csrf(request)
    _scene_or_404(db_session, context.world_id, edge_create.source_scene_id)
    _scene_or_404(db_session, context.world_id, edge_create.target_scene_id)
    if edge_create.source_scene_id == edge_create.target_scene_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="location edge endpoints must connect two distinct scenes",
        )
    existing = db_session.scalars(
        select(SceneLocationEdge).where(
            SceneLocationEdge.source_scene_id == edge_create.source_scene_id,
            SceneLocationEdge.target_scene_id == edge_create.target_scene_id,
        ),
    ).one_or_none()
    if existing is not None:
        raise _conflict("Location edge already exists")
    edge = SceneLocationEdge(
        world_id=context.world_id,
        source_scene_id=edge_create.source_scene_id,
        target_scene_id=edge_create.target_scene_id,
        travel_label=edge_create.travel_label,
        traversal_rules=edge_create.traversal_rules,
    )
    db_session.add(edge)
    db_session.flush()
    return _location_edge_response(db_session, edge)


@router.patch(
    "/{world_id}/location-edges/{edge_id}",
    response_model=SceneLocationEdgeResponse,
)
def update_location_edge(
    edge_id: uuid.UUID,
    edge_update: SceneLocationEdgeUpdateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> SceneLocationEdgeResponse:
    require_csrf(request)
    edge = _location_edge_or_404(db_session, context.world_id, edge_id)
    if "travel_label" in edge_update.model_fields_set:
        edge.travel_label = edge_update.travel_label
    if "traversal_rules" in edge_update.model_fields_set:
        edge.traversal_rules = edge_update.traversal_rules or {}
    db_session.flush()
    return _location_edge_response(db_session, edge)


@router.get("/{world_id}/organizations", response_model=list[OrganizationResponse])
def list_organizations(
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[OrganizationResponse]:
    organizations = db_session.scalars(
        select(WorldOrganization)
        .where(WorldOrganization.world_id == context.world_id)
        .order_by(WorldOrganization.organization_key),
    ).all()
    return [_organization_response(organization) for organization in organizations]


@router.post(
    "/{world_id}/organizations",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_organization(
    organization_create: OrganizationCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> OrganizationResponse:
    require_csrf(request)
    existing = db_session.scalars(
        select(WorldOrganization).where(
            WorldOrganization.world_id == context.world_id,
            WorldOrganization.organization_key == organization_create.organization_key,
        ),
    ).one_or_none()
    if existing is not None:
        raise _conflict("Organization key already exists")
    organization = WorldOrganization(
        world_id=context.world_id,
        organization_key=organization_create.organization_key,
        name=organization_create.name,
        organization_type=organization_create.organization_type,
        description=organization_create.description,
        public_summary=organization_create.public_summary,
        hidden_summary=organization_create.hidden_summary,
        metadata_json=organization_create.metadata,
        is_active=True,
    )
    db_session.add(organization)
    db_session.flush()
    return _organization_response(organization)


@router.patch("/{world_id}/organizations/{organization_id}", response_model=OrganizationResponse)
def update_organization(
    organization_id: uuid.UUID,
    organization_update: OrganizationUpdateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> OrganizationResponse:
    require_csrf(request)
    organization = _organization_or_404(db_session, context.world_id, organization_id)
    for field_name in (
        "name",
        "organization_type",
        "description",
        "public_summary",
        "hidden_summary",
    ):
        if field_name in organization_update.model_fields_set:
            next_value = getattr(organization_update, field_name)
            if next_value is not None or field_name in (
                "description",
                "public_summary",
                "hidden_summary",
            ):
                setattr(organization, field_name, next_value)
    if "metadata" in organization_update.model_fields_set:
        organization.metadata_json = organization_update.metadata or {}
    if "is_active" in organization_update.model_fields_set:
        organization.is_active = bool(organization_update.is_active)
    db_session.flush()
    return _organization_response(organization)


@router.get(
    "/{world_id}/organizations/{organization_id}/memberships",
    response_model=list[OrganizationMembershipResponse],
)
def list_organization_memberships(
    organization_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[OrganizationMembershipResponse]:
    _organization_or_404(db_session, context.world_id, organization_id)
    memberships = db_session.scalars(
        select(OrganizationMembership)
        .where(
            OrganizationMembership.world_id == context.world_id,
            OrganizationMembership.organization_id == organization_id,
        )
        .order_by(OrganizationMembership.created_at),
    ).all()
    return [_organization_membership_response(db_session, membership) for membership in memberships]


@router.post(
    "/{world_id}/organizations/{organization_id}/memberships",
    response_model=OrganizationMembershipResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_organization_membership(
    organization_id: uuid.UUID,
    membership_create: OrganizationMembershipCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> OrganizationMembershipResponse:
    require_csrf(request)
    _organization_or_404(db_session, context.world_id, organization_id)
    _agent_or_404(db_session, context.world_id, membership_create.agent_id)
    existing = db_session.scalars(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.agent_id == membership_create.agent_id,
        ),
    ).one_or_none()
    if existing is not None:
        raise _conflict("Organization membership already exists")
    membership = OrganizationMembership(
        world_id=context.world_id,
        organization_id=organization_id,
        agent_id=membership_create.agent_id,
        role_title=membership_create.role_title,
        visibility=membership_create.visibility,
        loyalty=membership_create.loyalty,
        influence=membership_create.influence,
        responsibilities=membership_create.responsibilities,
        metadata_json=membership_create.metadata,
    )
    db_session.add(membership)
    db_session.flush()
    return _organization_membership_response(db_session, membership)


@router.patch(
    "/{world_id}/organizations/{organization_id}/memberships/{membership_id}",
    response_model=OrganizationMembershipResponse,
)
def update_organization_membership(
    organization_id: uuid.UUID,
    membership_id: uuid.UUID,
    membership_update: OrganizationMembershipUpdateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> OrganizationMembershipResponse:
    require_csrf(request)
    _organization_or_404(db_session, context.world_id, organization_id)
    membership = _organization_membership_or_404(
        db_session,
        context.world_id,
        organization_id,
        membership_id,
    )
    for field_name in ("role_title", "visibility", "loyalty", "influence"):
        if field_name in membership_update.model_fields_set:
            setattr(membership, field_name, getattr(membership_update, field_name))
    if "responsibilities" in membership_update.model_fields_set:
        membership.responsibilities = membership_update.responsibilities or []
    if "metadata" in membership_update.model_fields_set:
        membership.metadata_json = membership_update.metadata or {}
    db_session.flush()
    return _organization_membership_response(db_session, membership)


@router.get(
    "/{world_id}/organizations/{organization_id}/faction-tracks",
    response_model=list[FactionProgressTrackResponse],
)
def list_faction_tracks(
    organization_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
) -> list[FactionProgressTrackResponse]:
    _organization_or_404(db_session, context.world_id, organization_id)
    resolved_worldline = LivingWorldGMService(db_session).worldline_or_404(
        context.world_id,
        worldline_id,
    )
    tracks = db_session.scalars(
        select(FactionProgressTrack)
        .where(
            FactionProgressTrack.world_id == context.world_id,
            FactionProgressTrack.worldline_id == resolved_worldline.id,
            FactionProgressTrack.organization_id == organization_id,
        )
        .order_by(FactionProgressTrack.track_key),
    ).all()
    return [_faction_track_response(db_session, track) for track in tracks]


@router.post(
    "/{world_id}/organizations/{organization_id}/faction-tracks",
    response_model=FactionProgressTrackResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_faction_track(
    organization_id: uuid.UUID,
    track_create: FactionProgressTrackCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> FactionProgressTrackResponse:
    require_csrf(request)
    _organization_or_404(db_session, context.world_id, organization_id)
    resolved_worldline = LivingWorldGMService(db_session).worldline_or_404(
        context.world_id,
        track_create.worldline_id,
    )
    existing = db_session.scalars(
        select(FactionProgressTrack).where(
            FactionProgressTrack.organization_id == organization_id,
            FactionProgressTrack.worldline_id == resolved_worldline.id,
            FactionProgressTrack.track_key == track_create.track_key,
        ),
    ).one_or_none()
    if existing is not None:
        raise _conflict("Faction progress track already exists")
    track = FactionProgressTrack(
        world_id=context.world_id,
        worldline_id=resolved_worldline.id,
        organization_id=organization_id,
        track_key=track_create.track_key,
        name=track_create.name,
        track_type=track_create.track_type,
        progress=track_create.progress,
        pressure=track_create.pressure,
        summary=track_create.summary,
        metadata_json=track_create.metadata,
    )
    db_session.add(track)
    db_session.flush()
    return _faction_track_response(db_session, track)


@router.patch(
    "/{world_id}/organizations/{organization_id}/faction-tracks/{track_id}",
    response_model=FactionProgressTrackResponse,
)
def update_faction_track(
    organization_id: uuid.UUID,
    track_id: uuid.UUID,
    track_update: FactionProgressTrackUpdateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> FactionProgressTrackResponse:
    require_csrf(request)
    _organization_or_404(db_session, context.world_id, organization_id)
    track = _faction_track_or_404(db_session, context.world_id, organization_id, track_id)
    previous_progress = track.progress
    for field_name in ("name", "track_type", "progress", "pressure", "summary"):
        if field_name in track_update.model_fields_set:
            next_value = getattr(track_update, field_name)
            if next_value is not None or field_name == "summary":
                setattr(track, field_name, next_value)
    if "metadata" in track_update.model_fields_set:
        track.metadata_json = track_update.metadata or {}
    if track.progress != previous_progress:
        event = WorldEventStore(db_session).append_event(
            WorldEventAppend(
                world_id=context.world_id,
                worldline_id=track.worldline_id,
                event_name="organization.faction_progress_updated",
                importance=WorldEventImportance.ORGANIZATION,
                payload={
                    "organization_id": str(organization_id),
                    "track_id": str(track.id),
                    "track_key": track.track_key,
                    "previous_progress": previous_progress,
                    "progress": track.progress,
                },
                wall_time=datetime.now(UTC),
                actor_ref=_actor_ref(context.subject),
            ),
        )
        RuntimeDiagnosticsService(db_session).record(
            RuntimeDiagnosticCreate(
                severity=DiagnosticSeverity.INFO,
                component=DiagnosticComponent.API,
                event_type="organization.faction_progress_updated",
                message="Faction progress track was updated.",
                details={"event_id": str(event.id), "track_id": str(track.id)},
                world_id=context.world_id,
            ),
        )
    db_session.flush()
    return _faction_track_response(db_session, track)


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


@router.get("/{world_id}/access-review", response_model=WorldAccessReviewResponse)
def get_world_access_review(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorldAccessReviewResponse:
    world = _world_or_404(db_session, context.world_id)
    rows = db_session.execute(
        select(WorldMembership, User)
        .join(User, User.id == WorldMembership.user_id)
        .where(WorldMembership.world_id == context.world_id)
        .order_by(WorldMembership.role, User.email),
    ).all()
    members = [
        WorldAccessReviewMemberResponse(
            user_id=user.id,
            email=user.email,
            display_name=user.display_name,
            is_active=user.is_active,
            role=cast(WorldRole, membership.role),
            membership_created_at=membership.created_at,
            membership_updated_at=membership.updated_at,
        )
        for membership, user in rows
    ]
    world_admin_count = sum(1 for member in members if member.role == AuthRole.WORLD_ADMIN.value)
    inactive_member_count = sum(1 for member in members if not member.is_active)
    return WorldAccessReviewResponse(
        world_id=world.id,
        owner_user_id=world.owner_user_id,
        member_count=len(members),
        world_admin_count=world_admin_count,
        inactive_member_count=inactive_member_count,
        final_admin_risk=world_admin_count <= 1,
        members=members,
    )


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
    _record_access_diagnostic(
        db_session,
        context=context,
        event_type="world.membership_upserted",
        message="World membership was created or updated.",
        target_user_id=user_id,
        role=membership_upsert.role,
    )
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
    deleted_role = membership.role
    db_session.delete(membership)
    _record_access_diagnostic(
        db_session,
        context=context,
        event_type="world.membership_deleted",
        message="World membership was deleted.",
        target_user_id=user_id,
        role=cast(WorldRole, deleted_role),
    )
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
    "/{world_id}/agents/{agent_id}/relationships",
    response_model=list[AgentRelationshipResponse],
)
def list_agent_relationships(
    agent_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
) -> list[AgentRelationshipResponse]:
    _agent_or_404(db_session, context.world_id, agent_id)
    resolved_worldline = LivingWorldGMService(db_session).worldline_or_404(
        context.world_id,
        worldline_id,
    )
    edges = db_session.scalars(
        select(AgentRelationshipEdge)
        .where(
            AgentRelationshipEdge.world_id == context.world_id,
            AgentRelationshipEdge.worldline_id == resolved_worldline.id,
            AgentRelationshipEdge.source_agent_id == agent_id,
        )
        .order_by(AgentRelationshipEdge.relationship_type, AgentRelationshipEdge.created_at),
    ).all()
    return [_agent_relationship_response(db_session, edge) for edge in edges]


@router.get(
    "/{world_id}/agents/{agent_id}/presence",
    response_model=AgentPresenceResponse | None,
)
def get_agent_presence(
    agent_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
) -> AgentPresenceResponse | None:
    _agent_or_404(db_session, context.world_id, agent_id)
    resolved_worldline = LivingWorldGMService(db_session).worldline_or_404(
        context.world_id,
        worldline_id,
    )
    presence = db_session.scalars(
        select(AgentPresenceState).where(
            AgentPresenceState.world_id == context.world_id,
            AgentPresenceState.worldline_id == resolved_worldline.id,
            AgentPresenceState.agent_id == agent_id,
        ),
    ).one_or_none()
    return None if presence is None else _presence_response(db_session, presence)


@router.put(
    "/{world_id}/agents/{agent_id}/presence",
    response_model=AgentPresenceResponse,
)
def upsert_agent_presence(
    agent_id: uuid.UUID,
    presence_update: AgentPresenceUpdateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AgentPresenceResponse:
    require_csrf(request)
    _agent_or_404(db_session, context.world_id, agent_id)
    if presence_update.current_scene_id is not None:
        _scene_or_404(db_session, context.world_id, presence_update.current_scene_id)
    resolved_worldline = LivingWorldGMService(db_session).worldline_or_404(
        context.world_id,
        presence_update.worldline_id,
    )
    presence = db_session.scalars(
        select(AgentPresenceState).where(
            AgentPresenceState.world_id == context.world_id,
            AgentPresenceState.worldline_id == resolved_worldline.id,
            AgentPresenceState.agent_id == agent_id,
        ),
    ).one_or_none()
    if presence is None:
        presence = AgentPresenceState(
            world_id=context.world_id,
            worldline_id=resolved_worldline.id,
            agent_id=agent_id,
        )
        db_session.add(presence)
    presence.current_scene_id = presence_update.current_scene_id
    presence.visibility_status = presence_update.visibility_status
    presence.encounter_eligible = presence_update.encounter_eligible
    presence.scheduled_movement = presence_update.scheduled_movement
    db_session.flush()
    return _presence_response(db_session, presence)


@router.post(
    "/{world_id}/agents/{agent_id}/relationships",
    response_model=AgentRelationshipResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_agent_relationship(
    agent_id: uuid.UUID,
    relationship_create: AgentRelationshipCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AgentRelationshipResponse:
    require_csrf(request)
    if relationship_create.source_agent_id != agent_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="source_agent_id must match route agent_id",
        )
    _agent_or_404(db_session, context.world_id, relationship_create.source_agent_id)
    _agent_or_404(db_session, context.world_id, relationship_create.target_agent_id)
    resolved_worldline = LivingWorldGMService(db_session).worldline_or_404(
        context.world_id,
        relationship_create.worldline_id,
    )
    if relationship_create.source_agent_id == relationship_create.target_agent_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="relationship endpoints must connect two distinct agents",
        )
    existing = db_session.scalars(
        select(AgentRelationshipEdge).where(
            AgentRelationshipEdge.source_agent_id == relationship_create.source_agent_id,
            AgentRelationshipEdge.target_agent_id == relationship_create.target_agent_id,
            AgentRelationshipEdge.worldline_id == resolved_worldline.id,
            AgentRelationshipEdge.relationship_type == relationship_create.relationship_type,
        ),
    ).one_or_none()
    if existing is not None:
        raise _conflict("Relationship edge already exists")
    edge = AgentRelationshipEdge(
        id=uuid.uuid4(),
        world_id=context.world_id,
        worldline_id=resolved_worldline.id,
        source_agent_id=relationship_create.source_agent_id,
        target_agent_id=relationship_create.target_agent_id,
        relationship_type=relationship_create.relationship_type,
        affection=relationship_create.affection,
        trust=relationship_create.trust,
        hostility=relationship_create.hostility,
        intimacy=relationship_create.intimacy,
        obligation=relationship_create.obligation,
        rivalry=relationship_create.rivalry,
        debt=relationship_create.debt,
        metadata_json=relationship_create.metadata,
    )
    db_session.add(edge)
    db_session.flush()
    relationship_event = WorldEventStore(db_session).append_event(
        WorldEventAppend(
            world_id=context.world_id,
            worldline_id=edge.worldline_id,
            event_name="relationship.edge_created",
            importance=WorldEventImportance.RELATIONSHIP,
            payload={
                "relationship_id": str(edge.id),
                "source_agent_id": str(edge.source_agent_id),
                "target_agent_id": str(edge.target_agent_id),
                "relationship_type": edge.relationship_type,
            },
            wall_time=datetime.now(UTC),
            actor_ref=_actor_ref(context.subject),
        ),
    )
    _record_relationship_memory(
        db_session, context.world_id, edge, relationship_event.id, "created"
    )
    return _agent_relationship_response(db_session, edge)


@router.patch(
    "/{world_id}/agents/{agent_id}/relationships/{relationship_id}",
    response_model=AgentRelationshipResponse,
)
def update_agent_relationship(
    agent_id: uuid.UUID,
    relationship_id: uuid.UUID,
    relationship_update: AgentRelationshipUpdateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AgentRelationshipResponse:
    require_csrf(request)
    _agent_or_404(db_session, context.world_id, agent_id)
    edge = _relationship_or_404(db_session, context.world_id, agent_id, relationship_id)
    for field_name in (
        "affection",
        "trust",
        "hostility",
        "intimacy",
        "obligation",
        "rivalry",
        "debt",
    ):
        if field_name in relationship_update.model_fields_set:
            next_value = getattr(relationship_update, field_name)
            if next_value is not None:
                setattr(edge, field_name, next_value)
    if "metadata" in relationship_update.model_fields_set:
        edge.metadata_json = relationship_update.metadata or {}
    db_session.flush()
    relationship_event = WorldEventStore(db_session).append_event(
        WorldEventAppend(
            world_id=context.world_id,
            worldline_id=edge.worldline_id,
            event_name="relationship.edge_updated",
            importance=WorldEventImportance.RELATIONSHIP,
            payload={
                "relationship_id": str(edge.id),
                "source_agent_id": str(edge.source_agent_id),
                "target_agent_id": str(edge.target_agent_id),
                "relationship_type": edge.relationship_type,
            },
            wall_time=datetime.now(UTC),
            actor_ref=_actor_ref(context.subject),
        ),
    )
    _record_relationship_memory(
        db_session, context.world_id, edge, relationship_event.id, "updated"
    )
    return _agent_relationship_response(db_session, edge)


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
    worldline_id: uuid.UUID | None = None,
) -> list[MemoryItemResponse]:
    _agent_or_404(db_session, context.world_id, agent_id)
    memory_service = MemoryService(db_session, load_settings())
    return [
        _memory_item_response(item)
        for item in memory_service.list_memories(context.world_id, agent_id, worldline_id)
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
                worldline_id=search_request.worldline_id,
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
    worldline_id: uuid.UUID | None = None,
) -> MemoryProfileSnapshotResponse | None:
    _agent_or_404(db_session, context.world_id, agent_id)
    snapshot = MemoryService(db_session, load_settings()).get_profile_snapshot(
        context.world_id,
        agent_id,
        worldline_id,
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
    worldline_id: uuid.UUID | None = None,
) -> MemoryProfileSnapshotResponse:
    require_csrf(request)
    _agent_or_404(db_session, context.world_id, agent_id)
    snapshot = MemoryService(db_session, load_settings()).refresh_profile_snapshot(
        context.world_id,
        agent_id,
        worldline_id,
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
    worldline_id: uuid.UUID | None = None,
) -> MemoryDeleteResponse:
    require_csrf(request)
    _agent_or_404(db_session, context.world_id, agent_id)
    result = MemoryService(db_session, load_settings()).delete_scope(
        MemoryDeleteScope(
            world_id=context.world_id,
            worldline_id=worldline_id,
            agent_id=agent_id,
        ),
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
    worldline_id: uuid.UUID | None = None,
) -> list[AgentRunResponse]:
    _agent_or_404(db_session, context.world_id, agent_id)
    settings = load_settings()
    orchestrator = AgentRuntimeOrchestrator(
        db_session,
        ProviderProfileService(db_session, settings),
        settings,
    )
    return [
        _agent_run_response(run)
        for run in orchestrator.list_runs(context.world_id, agent_id, worldline_id)
    ]


@router.get(
    "/{world_id}/agents/{agent_id}/runs/{run_id}",
    response_model=AgentRunDetailResponse,
)
def get_agent_run_detail(
    agent_id: uuid.UUID,
    run_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: uuid.UUID | None = None,
) -> AgentRunDetailResponse:
    _agent_or_404(db_session, context.world_id, agent_id)
    settings = load_settings()
    orchestrator = AgentRuntimeOrchestrator(
        db_session,
        ProviderProfileService(db_session, settings),
        settings,
    )
    run = orchestrator.get_run(context.world_id, agent_id, run_id, worldline_id)
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
            worldline_id=run_request.worldline_id,
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
    orchestrator = AgentRuntimeOrchestrator(
        db_session,
        ProviderProfileService(db_session, settings),
        settings,
    )
    artifact = orchestrator.create_narrative_artifact(
        world_id=context.world_id,
        agent_id=artifact_create.agent_id,
        title=artifact_create.title,
        content=artifact_create.content,
        artifact_kind=NarrativeArtifactKind(artifact_create.artifact_kind),
    )
    if artifact_create.continuity_metadata:
        artifact_model = db_session.get(NarrativeArtifact, artifact.id)
        if artifact_model is not None:
            artifact_model.artifact_metadata = {
                **(artifact_model.artifact_metadata or {}),
                "continuity": artifact_create.continuity_metadata,
            }
            db_session.flush()
            artifact = (
                NarrativeArtifactService(db_session).get_artifact(
                    context.world_id,
                    artifact.id,
                )
                or artifact
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
            metadata={
                **publication_request.metadata,
                "override_style_warning": publication_request.override_style_warning,
            },
        )
    except NarrativeArtifactNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Narrative artifact not found",
        ) from exc
    except NarrativePublicationBlockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": str(exc),
                "review_id": str(exc.review_id),
                "review_status": exc.review_status,
                "issues": exc.issues,
            },
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
        narrative_role=agent_create.narrative_role,
        importance=agent_create.importance,
        canon_status=agent_create.canon_status,
        character_category=agent_create.character_category,
        character_profile=agent_create.character_profile,
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
    if "narrative_role" in agent_update.model_fields_set:
        agent.narrative_role = agent_update.narrative_role
    if "importance" in agent_update.model_fields_set:
        agent.importance = agent_update.importance
    if "canon_status" in agent_update.model_fields_set:
        agent.canon_status = agent_update.canon_status
    if "character_category" in agent_update.model_fields_set:
        agent.character_category = agent_update.character_category
    if "character_profile" in agent_update.model_fields_set:
        agent.character_profile = agent_update.character_profile or {}
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
        region_key=scene.region_key,
        location_tags=scene.location_tags,
        opening_rules=scene.opening_rules,
        is_active=scene.is_active,
    )


def _location_edge_response(
    db_session: Session,
    edge: SceneLocationEdge,
) -> SceneLocationEdgeResponse:
    source_scene = _scene_or_404(db_session, edge.world_id, edge.source_scene_id)
    target_scene = _scene_or_404(db_session, edge.world_id, edge.target_scene_id)
    return SceneLocationEdgeResponse(
        id=edge.id,
        world_id=edge.world_id,
        source_scene_id=edge.source_scene_id,
        target_scene_id=edge.target_scene_id,
        source_scene_key=source_scene.scene_key,
        target_scene_key=target_scene.scene_key,
        travel_label=edge.travel_label,
        traversal_rules=edge.traversal_rules,
        created_at=edge.created_at,
        updated_at=edge.updated_at,
    )


def _organization_response(organization: WorldOrganization) -> OrganizationResponse:
    return OrganizationResponse(
        id=organization.id,
        world_id=organization.world_id,
        organization_key=organization.organization_key,
        name=organization.name,
        organization_type=cast(OrganizationType, organization.organization_type),
        description=organization.description,
        public_summary=organization.public_summary,
        hidden_summary=organization.hidden_summary,
        metadata=organization.metadata_json,
        is_active=organization.is_active,
        created_at=organization.created_at,
        updated_at=organization.updated_at,
    )


def _organization_membership_response(
    db_session: Session,
    membership: OrganizationMembership,
) -> OrganizationMembershipResponse:
    organization = _organization_or_404(db_session, membership.world_id, membership.organization_id)
    agent = _agent_or_404(db_session, membership.world_id, membership.agent_id)
    return OrganizationMembershipResponse(
        id=membership.id,
        world_id=membership.world_id,
        organization_id=membership.organization_id,
        organization_key=organization.organization_key,
        organization_name=organization.name,
        agent_id=membership.agent_id,
        agent_key=agent.agent_key,
        agent_display_name=agent.display_name,
        role_title=membership.role_title,
        visibility=cast(OrganizationVisibility, membership.visibility),
        loyalty=membership.loyalty,
        influence=membership.influence,
        responsibilities=membership.responsibilities,
        metadata=membership.metadata_json,
        created_at=membership.created_at,
        updated_at=membership.updated_at,
    )


def _faction_track_response(
    db_session: Session,
    track: FactionProgressTrack,
) -> FactionProgressTrackResponse:
    organization = _organization_or_404(db_session, track.world_id, track.organization_id)
    return FactionProgressTrackResponse(
        id=track.id,
        world_id=track.world_id,
        worldline_id=track.worldline_id,
        organization_id=track.organization_id,
        organization_key=organization.organization_key,
        organization_name=organization.name,
        track_key=track.track_key,
        name=track.name,
        track_type=cast(FactionTrackType, track.track_type),
        progress=track.progress,
        pressure=track.pressure,
        summary=track.summary,
        metadata=track.metadata_json,
        created_at=track.created_at,
        updated_at=track.updated_at,
    )


def _presence_response(db_session: Session, presence: AgentPresenceState) -> AgentPresenceResponse:
    agent = _agent_or_404(db_session, presence.world_id, presence.agent_id)
    scene = (
        None
        if presence.current_scene_id is None
        else _scene_or_404(db_session, presence.world_id, presence.current_scene_id)
    )
    return AgentPresenceResponse(
        id=presence.id,
        world_id=presence.world_id,
        worldline_id=presence.worldline_id,
        agent_id=presence.agent_id,
        agent_key=agent.agent_key,
        agent_display_name=agent.display_name,
        current_scene_id=presence.current_scene_id,
        current_scene_key=None if scene is None else scene.scene_key,
        current_scene_name=None if scene is None else scene.name,
        visibility_status=cast(PresenceVisibilityStatus, presence.visibility_status),
        encounter_eligible=presence.encounter_eligible,
        scheduled_movement=presence.scheduled_movement,
        last_event_id=presence.last_event_id,
        created_at=presence.created_at,
        updated_at=presence.updated_at,
    )


def _daily_life_candidate_response(
    db_session: Session,
    candidate: DailyLifeEventCandidate,
) -> DailyLifeEventCandidateResponse:
    agent = None if candidate.agent_id is None else db_session.get(Agent, candidate.agent_id)
    scene = None if candidate.scene_id is None else db_session.get(Scene, candidate.scene_id)
    return DailyLifeEventCandidateResponse(
        id=candidate.id,
        world_id=candidate.world_id,
        worldline_id=candidate.worldline_id,
        agent_id=candidate.agent_id,
        agent_display_name=None if agent is None else agent.display_name,
        scene_id=candidate.scene_id,
        scene_name=None if scene is None else scene.name,
        title=candidate.title,
        summary=candidate.summary,
        importance=cast(Literal["daily", "relationship", "organization"], candidate.importance),
        starts_at=candidate.starts_at,
        source_kind=candidate.source_kind,
        source_ref=candidate.source_ref,
        status=cast(DailyLifeCandidateStatus, candidate.status),
        metadata=candidate.metadata_json,
        created_at=candidate.created_at,
        updated_at=candidate.updated_at,
    )


def _offscreen_queue_response(item: OffscreenEventQueueItem) -> OffscreenEventQueueResponse:
    return OffscreenEventQueueResponse(
        id=item.id,
        world_id=item.world_id,
        worldline_id=item.worldline_id,
        source_candidate_id=item.source_candidate_id,
        event_name=item.event_name,
        title=item.title,
        payload=item.payload_json,
        due_at=item.due_at,
        importance=cast(
            Literal["daily", "relationship", "organization", "route", "main_plot"],
            item.importance,
        ),
        status=cast(OffscreenEventStatus, item.status),
        resolved_event_id=item.resolved_event_id,
        last_error=item.last_error,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _offscreen_resolution_response(result: Any) -> OffscreenResolutionResponse:
    return OffscreenResolutionResponse(
        processed_count=result.processed_count,
        resolved_count=result.resolved_count,
        failed_count=result.failed_count,
        event_ids=result.event_ids,
    )


def _worldline_response(worldline: Worldline) -> WorldlineResponse:
    return WorldlineResponse(
        id=worldline.id,
        world_id=worldline.world_id,
        worldline_key=worldline.worldline_key,
        name=worldline.name,
        description=worldline.description,
        parent_worldline_id=worldline.parent_worldline_id,
        forked_from_snapshot_id=worldline.forked_from_snapshot_id,
        fork_event_sequence=worldline.fork_event_sequence,
        status=cast(WorldlineStatus, worldline.status),
        created_by_actor_ref=worldline.created_by_actor_ref,
        metadata=worldline.metadata_json,
        created_at=worldline.created_at,
        updated_at=worldline.updated_at,
    )


def _worldline_comparison_response(
    comparison: WorldlineComparison,
) -> WorldlineComparisonResponse:
    return WorldlineComparisonResponse(
        base_worldline_id=comparison.base_worldline_id,
        compare_worldline_id=comparison.compare_worldline_id,
        fork_event_sequence=comparison.fork_event_sequence,
        divergent_event_count=comparison.divergent_event_count,
        relationship_delta_count=comparison.relationship_delta_count,
        faction_delta_count=comparison.faction_delta_count,
        choice_delta_count=comparison.choice_delta_count,
    )


def _gm_agenda_response(agenda: GMAgenda) -> GMAgendaResponse:
    return GMAgendaResponse(
        id=agenda.id,
        world_id=agenda.world_id,
        worldline_id=agenda.worldline_id,
        title=agenda.title,
        summary=agenda.summary,
        priority=agenda.priority,
        status=cast(GMAgendaStatus, agenda.status),
        focus_agents=agenda.focus_agents,
        focus_organizations=agenda.focus_organizations,
        metadata=agenda.metadata_json,
        created_at=agenda.created_at,
        updated_at=agenda.updated_at,
    )


def _gm_proposal_response(proposal: GMEventProposal) -> GMProposalResponse:
    return GMProposalResponse(
        id=proposal.id,
        world_id=proposal.world_id,
        worldline_id=proposal.worldline_id,
        agenda_id=proposal.agenda_id,
        title=proposal.title,
        reason=proposal.reason,
        event_name=proposal.event_name,
        proposed_payload=proposal.proposed_payload,
        importance=cast(
            Literal["daily", "relationship", "organization", "route", "main_plot"],
            proposal.importance,
        ),
        risk_score=proposal.risk_score,
        affected_agents=proposal.affected_agents,
        affected_organizations=proposal.affected_organizations,
        source_context=proposal.source_context,
        status=cast(GMProposalStatus, proposal.status),
        review_note=proposal.review_note,
        resolved_event_id=proposal.resolved_event_id,
        created_at=proposal.created_at,
        updated_at=proposal.updated_at,
    )


def _resolution_rule_response(rule: EventResolutionRule) -> EventResolutionRuleResponse:
    return EventResolutionRuleResponse(
        id=rule.id,
        world_id=rule.world_id,
        rule_key=rule.rule_key,
        name=rule.name,
        description=rule.description,
        priority=rule.priority,
        status=cast(ResolutionRuleStatus, rule.status),
        conditions=rule.conditions_json,
        effects=rule.effects_json,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


def _resolution_rule_dry_run_response(
    dry_run: ResolutionRuleDryRun,
) -> ResolutionRuleDryRunResponse:
    return ResolutionRuleDryRunResponse(
        rule_id=dry_run.rule_id,
        rule_key=dry_run.rule_key,
        matched=dry_run.matched,
        reasons=dry_run.reasons,
        effects=dry_run.effects,
    )


def _player_actor_response(actor: PlayerActorProfile) -> PlayerActorResponse:
    return PlayerActorResponse(
        id=actor.id,
        world_id=actor.world_id,
        worldline_id=actor.worldline_id,
        user_id=actor.user_id,
        actor_ref=actor.actor_ref,
        display_name=actor.display_name,
        current_scene_id=actor.current_scene_id,
        profile=actor.profile_json,
        is_active=actor.is_active,
        created_at=actor.created_at,
        updated_at=actor.updated_at,
    )


def _player_choice_response(choice: PlayerChoiceRecord) -> PlayerChoiceResponse:
    return PlayerChoiceResponse(
        id=choice.id,
        world_id=choice.world_id,
        worldline_id=choice.worldline_id,
        user_id=choice.user_id,
        player_actor_id=choice.player_actor_id,
        choice_key=choice.choice_key,
        choice_kind=cast(PlayerChoiceKind, choice.choice_kind),
        prompt=choice.prompt,
        selected_option=choice.selected_option,
        context=choice.context_json,
        consequence_preview=choice.consequence_preview,
        applied_event_id=choice.applied_event_id,
        created_at=choice.created_at,
        updated_at=choice.updated_at,
    )


def _story_hook_response(db_session: Session, hook: StoryHook) -> StoryHookResponse:
    owner = None if hook.owner_agent_id is None else db_session.get(Agent, hook.owner_agent_id)
    target = None if hook.target_agent_id is None else db_session.get(Agent, hook.target_agent_id)
    return StoryHookResponse(
        id=hook.id,
        world_id=hook.world_id,
        worldline_id=hook.worldline_id,
        hook_key=hook.hook_key,
        title=hook.title,
        hook_type=cast(StoryHookType, hook.hook_type),
        summary=hook.summary,
        status=cast(StoryHookStatus, hook.status),
        priority=hook.priority,
        owner_agent_id=hook.owner_agent_id,
        owner_agent_key=None if owner is None else owner.agent_key,
        owner_agent_display_name=None if owner is None else owner.display_name,
        target_agent_id=hook.target_agent_id,
        target_agent_key=None if target is None else target.agent_key,
        target_agent_display_name=None if target is None else target.display_name,
        source_event_id=hook.source_event_id,
        due_at=hook.due_at,
        resolution=hook.resolution,
        metadata=hook.metadata_json,
        created_at=hook.created_at,
        updated_at=hook.updated_at,
    )


def _plot_thread_response(thread: PlotThread) -> PlotThreadResponse:
    return PlotThreadResponse(
        id=thread.id,
        world_id=thread.world_id,
        worldline_id=thread.worldline_id,
        thread_key=thread.thread_key,
        title=thread.title,
        thread_type=cast(PlotThreadType, thread.thread_type),
        status=cast(PlotThreadStatus, thread.status),
        summary=thread.summary,
        stakes=thread.stakes,
        next_beats=thread.next_beats,
        participant_agent_ids=thread.participant_agent_ids,
        organization_ids=thread.organization_ids,
        related_event_ids=thread.related_event_ids,
        priority=thread.priority,
        metadata=thread.metadata_json,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
    )


def _route_affinity_response(db_session: Session, route: RouteAffinity) -> RouteAffinityResponse:
    agent = _agent_or_404(db_session, route.world_id, route.agent_id)
    return RouteAffinityResponse(
        id=route.id,
        world_id=route.world_id,
        worldline_id=route.worldline_id,
        agent_id=route.agent_id,
        agent_key=agent.agent_key,
        agent_display_name=agent.display_name,
        route_key=route.route_key,
        status=cast(RouteStatus, route.status),
        affinity=route.affinity,
        stage=route.stage,
        flags=route.flags,
        last_choice_id=route.last_choice_id,
        metadata=route.metadata_json,
        created_at=route.created_at,
        updated_at=route.updated_at,
    )


def _trigger_condition_response(
    condition: EventTriggerCondition,
) -> EventTriggerConditionResponse:
    return EventTriggerConditionResponse(
        id=condition.id,
        world_id=condition.world_id,
        condition_key=condition.condition_key,
        name=condition.name,
        description=condition.description,
        status=cast(TriggerConditionStatus, condition.status),
        priority=condition.priority,
        conditions=condition.conditions_json,
        metadata=condition.metadata_json,
        created_at=condition.created_at,
        updated_at=condition.updated_at,
    )


def _trigger_dry_run_response(dry_run: TriggerDryRun) -> TriggerConditionDryRunResponse:
    return TriggerConditionDryRunResponse(
        condition_id=dry_run.condition_id,
        condition_key=dry_run.condition_key,
        matched=dry_run.matched,
        satisfied=dry_run.satisfied,
        unsatisfied=dry_run.unsatisfied,
    )


def _scene_beat_response(db_session: Session, beat: SceneBeatDraft) -> SceneBeatDraftResponse:
    scene = None if beat.scene_id is None else db_session.get(Scene, beat.scene_id)
    return SceneBeatDraftResponse(
        id=beat.id,
        world_id=beat.world_id,
        worldline_id=beat.worldline_id,
        source_kind=cast(Literal["event", "proposal", "daily_episode", "manual"], beat.source_kind),
        source_ref=beat.source_ref,
        title=beat.title,
        setup=beat.setup,
        dialogue_beats=beat.dialogue_beats,
        choice_points=beat.choice_points,
        aftermath=beat.aftermath,
        participant_agent_ids=beat.participant_agent_ids,
        scene_id=beat.scene_id,
        scene_key=None if scene is None else scene.scene_key,
        scene_name=None if scene is None else scene.name,
        status=cast(SceneBeatStatus, beat.status),
        metadata=beat.metadata_json,
        created_at=beat.created_at,
        updated_at=beat.updated_at,
    )


def _daily_episode_response(draft: DailyEpisodeDraft) -> DailyEpisodeDraftResponse:
    return DailyEpisodeDraftResponse(
        id=draft.id,
        world_id=draft.world_id,
        worldline_id=draft.worldline_id,
        source_candidate_id=draft.source_candidate_id,
        title=draft.title,
        summary=draft.summary,
        scene_beat_draft_id=draft.scene_beat_draft_id,
        participant_agent_ids=draft.participant_agent_ids,
        status=cast(DailyEpisodeStatus, draft.status),
        metadata=draft.metadata_json,
        created_at=draft.created_at,
        updated_at=draft.updated_at,
    )


def _group_context_response(
    db_session: Session,
    group_context: GroupInteractionContext,
) -> GroupInteractionContextResponse:
    scene = (
        None if group_context.scene_id is None else db_session.get(Scene, group_context.scene_id)
    )
    organization = (
        None
        if group_context.organization_id is None
        else db_session.get(WorldOrganization, group_context.organization_id)
    )
    return GroupInteractionContextResponse(
        id=group_context.id,
        world_id=group_context.world_id,
        worldline_id=group_context.worldline_id,
        context_key=group_context.context_key,
        title=group_context.title,
        interaction_type=cast(GroupInteractionType, group_context.interaction_type),
        scene_id=group_context.scene_id,
        scene_key=None if scene is None else scene.scene_key,
        scene_name=None if scene is None else scene.name,
        organization_id=group_context.organization_id,
        organization_key=None if organization is None else organization.organization_key,
        organization_name=None if organization is None else organization.name,
        participant_agent_ids=group_context.participant_agent_ids,
        participant_roles=group_context.participant_roles,
        constraints=group_context.constraints,
        status=cast(GroupInteractionStatus, group_context.status),
        metadata=group_context.metadata_json,
        created_at=group_context.created_at,
        updated_at=group_context.updated_at,
    )


def _relationship_suggestion_response(
    db_session: Session,
    suggestion: RelationshipEventSuggestion,
) -> RelationshipEventSuggestionResponse:
    source = (
        None
        if suggestion.source_agent_id is None
        else db_session.get(Agent, suggestion.source_agent_id)
    )
    target = (
        None
        if suggestion.target_agent_id is None
        else db_session.get(Agent, suggestion.target_agent_id)
    )
    return RelationshipEventSuggestionResponse(
        id=suggestion.id,
        world_id=suggestion.world_id,
        worldline_id=suggestion.worldline_id,
        relationship_id=suggestion.relationship_id,
        source_agent_id=suggestion.source_agent_id,
        source_agent_display_name=None if source is None else source.display_name,
        target_agent_id=suggestion.target_agent_id,
        target_agent_display_name=None if target is None else target.display_name,
        title=suggestion.title,
        reason=suggestion.reason,
        suggested_event_name=suggestion.suggested_event_name,
        score=suggestion.score,
        status=cast(SuggestionStatus, suggestion.status),
        metadata=suggestion.metadata_json,
        created_at=suggestion.created_at,
        updated_at=suggestion.updated_at,
    )


def _organization_conflict_response(
    db_session: Session,
    conflict: OrganizationConflictEvent,
) -> OrganizationConflictResponse:
    organization = _organization_or_404(db_session, conflict.world_id, conflict.organization_id)
    track = (
        None
        if conflict.faction_track_id is None
        else db_session.get(FactionProgressTrack, conflict.faction_track_id)
    )
    return OrganizationConflictResponse(
        id=conflict.id,
        world_id=conflict.world_id,
        worldline_id=conflict.worldline_id,
        organization_id=conflict.organization_id,
        organization_key=organization.organization_key,
        organization_name=organization.name,
        faction_track_id=conflict.faction_track_id,
        faction_track_key=None if track is None else track.track_key,
        title=conflict.title,
        summary=conflict.summary,
        pressure_delta=conflict.pressure_delta,
        progress_delta=conflict.progress_delta,
        status=cast(OrganizationConflictStatus, conflict.status),
        resolved_event_id=conflict.resolved_event_id,
        metadata=conflict.metadata_json,
        created_at=conflict.created_at,
        updated_at=conflict.updated_at,
    )


def _rumor_response(db_session: Session, rumor: RumorRecord) -> RumorResponse:
    source_agent = (
        None if rumor.source_agent_id is None else db_session.get(Agent, rumor.source_agent_id)
    )
    source_organization = (
        None
        if rumor.source_organization_id is None
        else db_session.get(WorldOrganization, rumor.source_organization_id)
    )
    return RumorResponse(
        id=rumor.id,
        world_id=rumor.world_id,
        worldline_id=rumor.worldline_id,
        rumor_key=rumor.rumor_key,
        title=rumor.title,
        content=rumor.content,
        source_agent_id=rumor.source_agent_id,
        source_agent_display_name=None if source_agent is None else source_agent.display_name,
        source_organization_id=rumor.source_organization_id,
        source_organization_name=(
            None if source_organization is None else source_organization.name
        ),
        visibility=cast(RumorVisibility, rumor.visibility),
        known_agent_ids=rumor.known_agent_ids,
        status=cast(RumorStatus, rumor.status),
        metadata=rumor.metadata_json,
        created_at=rumor.created_at,
        updated_at=rumor.updated_at,
    )


def _rumor_propagation_response(
    db_session: Session,
    propagation: RumorPropagation,
) -> RumorPropagationResponse:
    rumor = _rumor_or_404(db_session, propagation.world_id, propagation.rumor_id)
    source_agent = (
        None
        if propagation.source_agent_id is None
        else db_session.get(Agent, propagation.source_agent_id)
    )
    target_agent = (
        None
        if propagation.target_agent_id is None
        else db_session.get(Agent, propagation.target_agent_id)
    )
    target_organization = (
        None
        if propagation.target_organization_id is None
        else db_session.get(WorldOrganization, propagation.target_organization_id)
    )
    return RumorPropagationResponse(
        id=propagation.id,
        world_id=propagation.world_id,
        worldline_id=propagation.worldline_id,
        rumor_id=propagation.rumor_id,
        rumor_title=rumor.title,
        source_agent_id=propagation.source_agent_id,
        source_agent_display_name=None if source_agent is None else source_agent.display_name,
        target_agent_id=propagation.target_agent_id,
        target_agent_display_name=None if target_agent is None else target_agent.display_name,
        target_organization_id=propagation.target_organization_id,
        target_organization_name=(
            None if target_organization is None else target_organization.name
        ),
        propagation_reason=propagation.propagation_reason,
        status=cast(RumorPropagationStatus, propagation.status),
        delivered_event_id=propagation.delivered_event_id,
        metadata=propagation.metadata_json,
        created_at=propagation.created_at,
        updated_at=propagation.updated_at,
    )


def _knowledge_fact_response(
    db_session: Session,
    fact: CharacterKnowledgeFact,
) -> KnowledgeFactResponse:
    agent = _agent_or_404(db_session, fact.world_id, fact.agent_id)
    return KnowledgeFactResponse(
        id=fact.id,
        world_id=fact.world_id,
        worldline_id=fact.worldline_id,
        agent_id=fact.agent_id,
        agent_key=agent.agent_key,
        agent_display_name=agent.display_name,
        fact_key=fact.fact_key,
        knowledge_kind=cast(KnowledgeKind, fact.knowledge_kind),
        content=fact.content,
        source_event_id=fact.source_event_id,
        source_ref=fact.source_ref,
        confidence=fact.confidence,
        visibility=cast(KnowledgeVisibility, fact.visibility),
        is_active=fact.is_active,
        metadata=fact.metadata_json,
        created_at=fact.created_at,
        updated_at=fact.updated_at,
    )


def _secret_response(secret: SecretRecord) -> SecretResponse:
    return SecretResponse(
        id=secret.id,
        world_id=secret.world_id,
        worldline_id=secret.worldline_id,
        secret_key=secret.secret_key,
        title=secret.title,
        content=secret.content,
        holder_agent_ids=secret.holder_agent_ids,
        reveal_conditions=secret.reveal_conditions,
        consequence_metadata=secret.consequence_metadata,
        visibility=cast(SecretVisibility, secret.visibility),
        status=cast(SecretStatus, secret.status),
        revealed_event_id=secret.revealed_event_id,
        metadata=secret.metadata_json,
        created_at=secret.created_at,
        updated_at=secret.updated_at,
    )


def _emotional_state_response(
    db_session: Session,
    state_item: CharacterEmotionalState,
) -> EmotionalStateResponse:
    agent = _agent_or_404(db_session, state_item.world_id, state_item.agent_id)
    return EmotionalStateResponse(
        id=state_item.id,
        world_id=state_item.world_id,
        worldline_id=state_item.worldline_id,
        agent_id=state_item.agent_id,
        agent_key=agent.agent_key,
        agent_display_name=agent.display_name,
        mood=state_item.mood,
        stress=state_item.stress,
        fatigue=state_item.fatigue,
        anticipation=state_item.anticipation,
        jealousy=state_item.jealousy,
        anger=state_item.anger,
        source_event_id=state_item.source_event_id,
        expires_at=state_item.expires_at,
        metadata=state_item.metadata_json,
        created_at=state_item.created_at,
        updated_at=state_item.updated_at,
    )


def _relationship_repair_response(repair: RelationshipRepairRecord) -> RelationshipRepairResponse:
    return RelationshipRepairResponse(
        id=repair.id,
        world_id=repair.world_id,
        worldline_id=repair.worldline_id,
        relationship_id=repair.relationship_id,
        repair_kind=cast(RelationshipRepairKind, repair.repair_kind),
        reason=repair.reason,
        score_delta=repair.score_delta,
        status=cast(RelationshipRepairStatus, repair.status),
        applied_event_id=repair.applied_event_id,
        metadata=repair.metadata_json,
        created_at=repair.created_at,
        updated_at=repair.updated_at,
    )


def _journal_entry_response(entry: PlayerJournalEntry) -> JournalEntryResponse:
    return JournalEntryResponse(
        id=entry.id,
        world_id=entry.world_id,
        worldline_id=entry.worldline_id,
        user_id=entry.user_id,
        player_actor_id=entry.player_actor_id,
        entry_kind=cast(JournalEntryKind, entry.entry_kind),
        title=entry.title,
        body=entry.body,
        source_event_id=entry.source_event_id,
        source_ref=entry.source_ref,
        visibility=cast(JournalVisibility, entry.visibility),
        metadata=entry.metadata_json,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


def _notification_response(notification: InWorldNotification) -> InWorldNotificationResponse:
    return InWorldNotificationResponse(
        id=notification.id,
        world_id=notification.world_id,
        worldline_id=notification.worldline_id,
        user_id=notification.user_id,
        notification_kind=cast(NotificationKind, notification.notification_kind),
        title=notification.title,
        body=notification.body,
        source_event_id=notification.source_event_id,
        source_ref=notification.source_ref,
        status=cast(NotificationStatus, notification.status),
        metadata=notification.metadata_json,
        created_at=notification.created_at,
        updated_at=notification.updated_at,
    )


def _intervention_response(intervention: PlayerInterventionRecord) -> PlayerInterventionResponse:
    return PlayerInterventionResponse(
        id=intervention.id,
        world_id=intervention.world_id,
        worldline_id=intervention.worldline_id,
        user_id=intervention.user_id,
        player_actor_id=intervention.player_actor_id,
        intervention_kind=cast(InterventionKind, intervention.intervention_kind),
        target_agent_id=intervention.target_agent_id,
        target_scene_id=intervention.target_scene_id,
        prompt=intervention.prompt,
        choice_id=intervention.choice_id,
        event_id=intervention.event_id,
        status=cast(InterventionStatus, intervention.status),
        metadata=intervention.metadata_json,
        created_at=intervention.created_at,
        updated_at=intervention.updated_at,
    )


def _gm_style_review_response(review: GMStyleReview) -> GMStyleReviewResponse:
    return GMStyleReviewResponse(
        id=review.id,
        world_id=review.world_id,
        worldline_id=review.worldline_id,
        source_kind=review.source_kind,
        source_ref=review.source_ref,
        reviewed_text=review.reviewed_text,
        status=cast(ReviewStatus, review.status),
        diagnostics=review.diagnostics,
        metadata=review.metadata_json,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


def _narrative_continuity_review_response(
    review: NarrativeContinuityReview,
) -> NarrativeContinuityReviewResponse:
    return NarrativeContinuityReviewResponse(
        id=review.id,
        world_id=review.world_id,
        worldline_id=review.worldline_id,
        artifact_id=review.artifact_id,
        source_kind=review.source_kind,
        source_ref=review.source_ref,
        reviewed_text=review.reviewed_text,
        status=cast(ReviewStatus, review.status),
        issues=review.issues,
        metadata=review.metadata_json,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


def _living_world_dashboard_response(
    dashboard: LivingWorldDashboard,
) -> LivingWorldDashboardResponse:
    return LivingWorldDashboardResponse(
        world_id=dashboard.world_id,
        worldline_id=dashboard.worldline_id,
        knowledge_count=dashboard.knowledge_count,
        hidden_secret_count=dashboard.hidden_secret_count,
        emotional_state_count=dashboard.emotional_state_count,
        open_hook_count=dashboard.open_hook_count,
        unread_notification_count=dashboard.unread_notification_count,
        pending_intervention_count=dashboard.pending_intervention_count,
        active_route_count=dashboard.active_route_count,
        pressure_summary=dashboard.pressure_summary,
    )


def _route_milestone_response(
    db_session: Session,
    milestone: RouteMilestone,
) -> RouteMilestoneResponse:
    agent = None if milestone.agent_id is None else db_session.get(Agent, milestone.agent_id)
    return RouteMilestoneResponse(
        id=milestone.id,
        world_id=milestone.world_id,
        worldline_id=milestone.worldline_id,
        route_affinity_id=milestone.route_affinity_id,
        plot_thread_id=milestone.plot_thread_id,
        agent_id=milestone.agent_id,
        agent_key=None if agent is None else agent.agent_key,
        agent_display_name=None if agent is None else agent.display_name,
        milestone_key=milestone.milestone_key,
        title=milestone.title,
        description=milestone.description,
        stage=milestone.stage,
        status=cast(RouteMilestoneStatus, milestone.status),
        conditions=milestone.conditions,
        evidence_metadata=milestone.evidence_metadata,
        metadata=milestone.metadata_json,
        created_at=milestone.created_at,
        updated_at=milestone.updated_at,
    )


def _ending_candidate_response(
    db_session: Session,
    ending: EndingCandidate,
) -> EndingCandidateResponse:
    agent = None if ending.agent_id is None else db_session.get(Agent, ending.agent_id)
    return EndingCandidateResponse(
        id=ending.id,
        world_id=ending.world_id,
        worldline_id=ending.worldline_id,
        route_affinity_id=ending.route_affinity_id,
        plot_thread_id=ending.plot_thread_id,
        agent_id=ending.agent_id,
        agent_key=None if agent is None else agent.agent_key,
        agent_display_name=None if agent is None else agent.display_name,
        ending_key=ending.ending_key,
        title=ending.title,
        ending_type=cast(EndingType, ending.ending_type),
        status=cast(EndingStatus, ending.status),
        requirements=ending.requirements,
        outcome_summary=ending.outcome_summary,
        evidence_metadata=ending.evidence_metadata,
        metadata=ending.metadata_json,
        created_at=ending.created_at,
        updated_at=ending.updated_at,
    )


def _ending_dry_run_response(dry_run: EndingDryRun) -> EndingDryRunResponse:
    return EndingDryRunResponse(
        ending_id=dry_run.ending_id,
        ending_key=dry_run.ending_key,
        matched=dry_run.matched,
        satisfied=dry_run.satisfied,
        unsatisfied=dry_run.unsatisfied,
        evidence=dry_run.evidence,
    )


def _long_run_eval_response(run: LongRunEvalRun) -> LongRunEvalResponse:
    return LongRunEvalResponse(
        id=run.id,
        world_id=run.world_id,
        worldline_id=run.worldline_id,
        eval_key=run.eval_key,
        horizon_days=run.horizon_days,
        status=cast(LongRunEvalStatus, run.status),
        started_at=run.started_at,
        finished_at=run.finished_at,
        metrics=run.metrics,
        recommendations=run.recommendations,
        blockers=run.blockers,
        metadata=run.metadata_json,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


def _authoring_template_response(template: AuthoringTemplate) -> AuthoringTemplateResponse:
    return AuthoringTemplateResponse(
        id=template.id,
        world_id=template.world_id,
        template_key=template.template_key,
        template_kind=cast(AuthoringTemplateKind, template.template_kind),
        name=template.name,
        description=template.description,
        content=template.content,
        validation_issues=template.validation_issues,
        is_active=template.is_active,
        metadata=template.metadata_json,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


def _authoring_import_job_response(job: AuthoringImportJob) -> AuthoringImportJobResponse:
    return AuthoringImportJobResponse(
        id=job.id,
        world_id=job.world_id,
        template_id=job.template_id,
        status=cast(AuthoringImportStatus, job.status),
        preview_summary=job.preview_summary,
        applied_refs=job.applied_refs,
        validation_issues=job.validation_issues,
        metadata=job.metadata_json,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def _release_profile_response(profile: LivingWorldReleaseProfile) -> ReleaseProfileResponse:
    return ReleaseProfileResponse(
        id=profile.id,
        world_id=profile.world_id,
        profile_key=profile.profile_key,
        status=cast(ReleaseProfileStatus, profile.status),
        branch_policy=profile.branch_policy,
        backup_policy=profile.backup_policy,
        content_review_policy=profile.content_review_policy,
        player_permission_policy=profile.player_permission_policy,
        worldline_policy=profile.worldline_policy,
        checklist=profile.checklist,
        metadata=profile.metadata_json,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def _beta_checklist_run_response(run: BetaChecklistRun) -> BetaChecklistRunResponse:
    return BetaChecklistRunResponse(
        id=run.id,
        world_id=run.world_id,
        worldline_id=run.worldline_id,
        run_key=run.run_key,
        status=cast(BetaChecklistStatus, run.status),
        summary=run.summary,
        evidence=run.evidence,
        blocker_count=run.blocker_count,
        created_by_actor_ref=run.created_by_actor_ref,
        metadata=run.metadata_json,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


def _beta_checklist_item_response(item: BetaChecklistItem) -> BetaChecklistItemResponse:
    return BetaChecklistItemResponse(
        id=item.id,
        run_id=item.run_id,
        item_key=item.item_key,
        title=item.title,
        status=cast(BetaChecklistItemStatus, item.status),
        evidence=item.evidence,
        recommendation=item.recommendation,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _world_bible_response(bible: WorldBible) -> WorldBibleResponse:
    return WorldBibleResponse(
        id=bible.id,
        world_id=bible.world_id,
        source_material=bible.source_material,
        canon_timeline=bible.canon_timeline,
        setting_rules=bible.setting_rules,
        forbidden_changes=bible.forbidden_changes,
        sequel_boundaries=bible.sequel_boundaries,
        continuity_config=bible.continuity_config,
        metadata=bible.metadata_json,
        continuity_status=_continuity_status_from_metadata(bible.continuity_config),
        created_at=bible.created_at,
        updated_at=bible.updated_at,
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
        narrative_role=cast(NarrativeRole | None, agent.narrative_role),
        importance=cast(CharacterImportance | None, agent.importance),
        canon_status=cast(ContinuityStatus | None, agent.canon_status),
        character_category=cast(CharacterCategory | None, agent.character_category),
        character_profile=agent.character_profile,
        config=agent.config,
        is_enabled=agent.is_enabled,
    )


def _agent_relationship_response(
    db_session: Session,
    edge: AgentRelationshipEdge,
) -> AgentRelationshipResponse:
    source_agent = _agent_or_404(db_session, edge.world_id, edge.source_agent_id)
    target_agent = _agent_or_404(db_session, edge.world_id, edge.target_agent_id)
    return AgentRelationshipResponse(
        id=edge.id,
        world_id=edge.world_id,
        worldline_id=edge.worldline_id,
        source_agent_id=edge.source_agent_id,
        source_agent_key=source_agent.agent_key,
        source_display_name=source_agent.display_name,
        target_agent_id=edge.target_agent_id,
        target_agent_key=target_agent.agent_key,
        target_display_name=target_agent.display_name,
        relationship_type=cast(RelationshipType, edge.relationship_type),
        affection=edge.affection,
        trust=edge.trust,
        hostility=edge.hostility,
        intimacy=edge.intimacy,
        obligation=edge.obligation,
        rivalry=edge.rivalry,
        debt=edge.debt,
        metadata=edge.metadata_json,
        created_at=edge.created_at,
        updated_at=edge.updated_at,
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
        conflicts=[_calendar_conflict_response(conflict) for conflict in report.conflicts],
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
        worldline_id=run.worldline_id,
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
        continuity_metadata=_continuity_metadata(artifact_record.metadata),
        continuity_status=_continuity_status_from_metadata(artifact_record.metadata),
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
        publication_gate=publication.metadata.get("publication_gate"),
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
        worldline_id=event.worldline_id,
        sequence=event.sequence,
        event_name=event.event_name,
        importance=cast(EventImportance, event.importance),
        payload=event.payload,
        wall_time=event.wall_time,
        world_time=event.world_time,
        actor_ref=event.actor_ref,
        continuity_metadata=_continuity_metadata(event.payload),
        continuity_status=_continuity_status_from_metadata(event.payload),
        causation_event_id=event.causation_event_id,
        correlation_id=event.correlation_id,
        created_at=event.created_at,
    )


def _snapshot_response(snapshot: WorldSnapshotRecord) -> WorldSnapshotResponse:
    return WorldSnapshotResponse(
        id=snapshot.id,
        world_id=snapshot.world_id,
        worldline_id=snapshot.worldline_id,
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


def _relationship_or_404(
    db_session: Session,
    world_id: uuid.UUID,
    source_agent_id: uuid.UUID,
    relationship_id: uuid.UUID,
) -> AgentRelationshipEdge:
    edge = db_session.get(AgentRelationshipEdge, relationship_id)
    if edge is None or edge.world_id != world_id or edge.source_agent_id != source_agent_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relationship not found")
    return edge


def _location_edge_or_404(
    db_session: Session,
    world_id: uuid.UUID,
    edge_id: uuid.UUID,
) -> SceneLocationEdge:
    edge = db_session.get(SceneLocationEdge, edge_id)
    if edge is None or edge.world_id != world_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location edge not found")
    return edge


def _organization_or_404(
    db_session: Session,
    world_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> WorldOrganization:
    organization = db_session.get(WorldOrganization, organization_id)
    if organization is None or organization.world_id != world_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return organization


def _organization_membership_or_404(
    db_session: Session,
    world_id: uuid.UUID,
    organization_id: uuid.UUID,
    membership_id: uuid.UUID,
) -> OrganizationMembership:
    membership = db_session.get(OrganizationMembership, membership_id)
    if (
        membership is None
        or membership.world_id != world_id
        or membership.organization_id != organization_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization membership not found",
        )
    return membership


def _gm_agenda_or_404(
    db_session: Session,
    world_id: uuid.UUID,
    agenda_id: uuid.UUID,
) -> GMAgenda:
    agenda = db_session.get(GMAgenda, agenda_id)
    if agenda is None or agenda.world_id != world_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return agenda


def _resolution_rule_or_404(
    db_session: Session,
    world_id: uuid.UUID,
    rule_id: uuid.UUID,
) -> EventResolutionRule:
    rule = db_session.get(EventResolutionRule, rule_id)
    if rule is None or rule.world_id != world_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return rule


def _story_hook_or_404(
    db_session: Session,
    world_id: uuid.UUID,
    hook_id: uuid.UUID,
) -> StoryHook:
    hook = db_session.get(StoryHook, hook_id)
    if hook is None or hook.world_id != world_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story hook not found")
    return hook


def _plot_thread_or_404(
    db_session: Session,
    world_id: uuid.UUID,
    thread_id: uuid.UUID,
) -> PlotThread:
    thread = db_session.get(PlotThread, thread_id)
    if thread is None or thread.world_id != world_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plot thread not found")
    return thread


def _trigger_condition_or_404(
    db_session: Session,
    world_id: uuid.UUID,
    condition_id: uuid.UUID,
) -> EventTriggerCondition:
    condition = db_session.get(EventTriggerCondition, condition_id)
    if condition is None or condition.world_id != world_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trigger condition not found",
        )
    return condition


def _scene_beat_or_404(
    db_session: Session,
    world_id: uuid.UUID,
    beat_id: uuid.UUID,
) -> SceneBeatDraft:
    beat = db_session.get(SceneBeatDraft, beat_id)
    if beat is None or beat.world_id != world_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene beat not found")
    return beat


def _daily_episode_or_404(
    db_session: Session,
    world_id: uuid.UUID,
    episode_id: uuid.UUID,
) -> DailyEpisodeDraft:
    episode = db_session.get(DailyEpisodeDraft, episode_id)
    if episode is None or episode.world_id != world_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Daily episode not found",
        )
    return episode


def _group_context_or_404(
    db_session: Session,
    world_id: uuid.UUID,
    context_id: uuid.UUID,
) -> GroupInteractionContext:
    group_context = db_session.get(GroupInteractionContext, context_id)
    if group_context is None or group_context.world_id != world_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group interaction context not found",
        )
    return group_context


def _relationship_suggestion_or_404(
    db_session: Session,
    world_id: uuid.UUID,
    suggestion_id: uuid.UUID,
) -> RelationshipEventSuggestion:
    suggestion = db_session.get(RelationshipEventSuggestion, suggestion_id)
    if suggestion is None or suggestion.world_id != world_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relationship suggestion not found",
        )
    return suggestion


def _organization_conflict_or_404(
    db_session: Session,
    world_id: uuid.UUID,
    conflict_id: uuid.UUID,
) -> OrganizationConflictEvent:
    conflict = db_session.get(OrganizationConflictEvent, conflict_id)
    if conflict is None or conflict.world_id != world_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization conflict not found",
        )
    return conflict


def _rumor_or_404(
    db_session: Session,
    world_id: uuid.UUID,
    rumor_id: uuid.UUID,
) -> RumorRecord:
    rumor = db_session.get(RumorRecord, rumor_id)
    if rumor is None or rumor.world_id != world_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rumor not found")
    return rumor


def _rumor_propagation_or_404(
    db_session: Session,
    world_id: uuid.UUID,
    propagation_id: uuid.UUID,
) -> RumorPropagation:
    propagation = db_session.get(RumorPropagation, propagation_id)
    if propagation is None or propagation.world_id != world_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rumor propagation not found",
        )
    return propagation


def _ending_candidate_or_404(
    db_session: Session,
    world_id: uuid.UUID,
    ending_id: uuid.UUID,
) -> EndingCandidate:
    ending = db_session.get(EndingCandidate, ending_id)
    if ending is None or ending.world_id != world_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ending candidate not found",
        )
    return ending


def _authoring_template_or_404(
    db_session: Session,
    world_id: uuid.UUID,
    template_id: uuid.UUID,
) -> AuthoringTemplate:
    template = db_session.get(AuthoringTemplate, template_id)
    if template is None or template.world_id != world_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authoring template not found",
        )
    return template


def _beta_checklist_run_or_404(
    db_session: Session,
    world_id: uuid.UUID,
    run_id: uuid.UUID,
) -> BetaChecklistRun:
    run = db_session.get(BetaChecklistRun, run_id)
    if run is None or run.world_id != world_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Beta checklist run not found",
        )
    return run


def _ensure_agent_string_refs(
    db_session: Session,
    world_id: uuid.UUID,
    agent_ids: Sequence[str],
) -> None:
    for raw_agent_id in agent_ids:
        agent_id = _uuid_or_none(raw_agent_id)
        if agent_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Invalid agent id: {raw_agent_id}",
            )
        _agent_or_404(db_session, world_id, agent_id)


def _ensure_organization_string_refs(
    db_session: Session,
    world_id: uuid.UUID,
    organization_ids: Sequence[str],
) -> None:
    for raw_organization_id in organization_ids:
        organization_id = _uuid_or_none(raw_organization_id)
        if organization_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Invalid organization id: {raw_organization_id}",
            )
        _organization_or_404(db_session, world_id, organization_id)


def _faction_track_or_404(
    db_session: Session,
    world_id: uuid.UUID,
    organization_id: uuid.UUID,
    track_id: uuid.UUID,
) -> FactionProgressTrack:
    track = db_session.get(FactionProgressTrack, track_id)
    if track is None or track.world_id != world_id or track.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Faction progress track not found",
        )
    return track


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


def _record_access_diagnostic(
    db_session: Session,
    *,
    context: WorldAccessContext,
    event_type: str,
    message: str,
    target_user_id: uuid.UUID,
    role: WorldRole,
) -> None:
    RuntimeDiagnosticsService(db_session).record(
        RuntimeDiagnosticCreate(
            severity=DiagnosticSeverity.INFO,
            component=DiagnosticComponent.API,
            event_type=event_type,
            message=message,
            details={
                "world_id": str(context.world_id),
                "actor_user_id": str(context.subject.user_id),
                "target_user_id": str(target_user_id),
                "role": role,
            },
            world_id=context.world_id,
        ),
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


def _relationship_memory_summary(db_session: Session, edge: AgentRelationshipEdge) -> str:
    source_agent = _agent_or_404(db_session, edge.world_id, edge.source_agent_id)
    target_agent = _agent_or_404(db_session, edge.world_id, edge.target_agent_id)
    return (
        f"{source_agent.display_name} and {target_agent.display_name} have a "
        f"{edge.relationship_type} relationship: affection {edge.affection}, trust {edge.trust}, "
        f"hostility {edge.hostility}, intimacy {edge.intimacy}, obligation {edge.obligation}, "
        f"rivalry {edge.rivalry}, debt {edge.debt}."
    )


def _record_relationship_memory(
    db_session: Session,
    world_id: uuid.UUID,
    edge: AgentRelationshipEdge,
    event_id: uuid.UUID,
    action: str,
) -> None:
    try:
        MemoryService(db_session, load_settings()).record_relationship_change(
            world_id=world_id,
            worldline_id=edge.worldline_id,
            source_agent_id=edge.source_agent_id,
            target_agent_id=edge.target_agent_id,
            relationship_id=edge.id,
            relationship_type=edge.relationship_type,
            summary=_relationship_memory_summary(db_session, edge),
            metadata={"source_event_id": str(event_id), "action": action},
            dedupe_suffix=f"{action}:{event_id}",
        )
    except Exception as exc:
        RuntimeDiagnosticsService(db_session).record(
            RuntimeDiagnosticCreate(
                severity=DiagnosticSeverity.WARNING,
                component=DiagnosticComponent.API,
                event_type="relationship.memory_write_skipped",
                message="Relationship memory write was skipped.",
                details={"error": str(exc), "relationship_id": str(edge.id), "action": action},
                world_id=world_id,
            ),
        )


def _continuity_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    raw_nested = metadata.get("continuity")
    if isinstance(raw_nested, dict):
        return raw_nested
    if _continuity_status_from_metadata(metadata) is not None:
        return {
            key: value
            for key, value in metadata.items()
            if key.startswith("continuity_") or key == "canon_status"
        }
    return {}


def _continuity_status_from_metadata(metadata: dict[str, Any]) -> ContinuityStatus | None:
    raw_nested = metadata.get("continuity")
    raw_status = None
    if isinstance(raw_nested, dict):
        raw_status = raw_nested.get("status")
    if raw_status is None:
        raw_status = (
            metadata.get("status")
            or metadata.get("continuity_status")
            or metadata.get("canon_status")
        )
    if raw_status in {"canon", "post_canon", "alternate", "original_expansion"}:
        return cast(ContinuityStatus, raw_status)
    return None


def _validate_continuity_metadata(metadata: dict[str, Any], field_name: str) -> None:
    raw_nested = metadata.get("continuity")
    raw_status = None
    if isinstance(raw_nested, dict):
        raw_status = raw_nested.get("status")
    if raw_status is None:
        raw_status = (
            metadata.get("status")
            or metadata.get("continuity_status")
            or metadata.get("canon_status")
        )
    if raw_status is None:
        return
    if raw_status not in {"canon", "post_canon", "alternate", "original_expansion"}:
        raise ValueError(
            f"{field_name} continuity status must be one of "
            "canon, post_canon, alternate, original_expansion",
        )


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


def _uuid_or_none(value: object) -> uuid.UUID | None:
    if isinstance(value, uuid.UUID):
        return value
    if isinstance(value, str):
        try:
            return uuid.UUID(value)
        except ValueError:
            return None
    return None
