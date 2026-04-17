from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from noveland.adapters import ProviderProfileService
from noveland.agents.models import Agent
from noveland.auth import AuthenticatedSubject, AuthRole
from noveland.auth.models import User
from noveland.calendar import (
    CalendarEntryCreate,
    CalendarEntryStatus,
    CalendarEntryUpdate,
    CalendarService,
    ScheduleRuleCreate,
    ScheduleRuleKind,
    ScheduleRuleUpdate,
)
from noveland.calendar.models import AgentCalendarEntry, WorldScheduleRule
from noveland.core.settings import load_settings
from noveland.events import WorldReplayService, WorldReplayState, WorldSnapshotRecord
from noveland.memory import (
    VECTOR_DIMENSIONS,
    LocalPgvectorMemoryBackend,
    MemoryItemCreate,
    MemoryItemRecord,
    MemorySearchQuery,
)
from noveland.memory.models import AgentMemoryItem
from noveland.narrative import (
    NarrativeArtifactKind,
    NarrativeArtifactRecord,
    NarrativeArtifactService,
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
from noveland.worlds.models import Scene, World, WorldMembership
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

SLUG_PATTERN = r"^[a-z0-9][a-z0-9-]{1,78}[a-z0-9]$"
SLUG_RE = re.compile(SLUG_PATTERN)

WorldRole = Literal["world_admin", "human_user"]
AgentKind = Literal["role_agent", "narrative_agent"]

router = APIRouter(prefix="/worlds", tags=["worlds"])


class _RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WorldCreateRequest(_RequestModel):
    slug: str = Field(pattern=SLUG_PATTERN, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    rules_config: dict[str, Any] = Field(default_factory=dict)


class WorldUpdateRequest(_RequestModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    rules_config: dict[str, Any] | None = None
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
    kind: AgentKind
    home_scene_id: uuid.UUID | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class AgentUpdateRequest(_RequestModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    home_scene_id: uuid.UUID | None = None
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


class MemoryItemCreateRequest(_RequestModel):
    content: str = Field(min_length=1)
    embedding: list[float]
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_event_id: uuid.UUID | None = None

    @field_validator("embedding", mode="after")
    @classmethod
    def embedding_must_match_dimensions(cls, value: list[float]) -> list[float]:
        if len(value) != VECTOR_DIMENSIONS:
            raise ValueError(f"embedding must have {VECTOR_DIMENSIONS} dimensions")
        return value


class MemorySearchRequest(_RequestModel):
    embedding: list[float]
    limit: int = Field(default=10, ge=1, le=50)

    @field_validator("embedding", mode="after")
    @classmethod
    def embedding_must_match_dimensions(cls, value: list[float]) -> list[float]:
        if len(value) != VECTOR_DIMENSIONS:
            raise ValueError(f"embedding must have {VECTOR_DIMENSIONS} dimensions")
        return value


class AgentRunRequest(_RequestModel):
    prompt: str | None = None
    provider_profile_id: uuid.UUID | None = None
    create_memory: bool = True
    create_narrative_artifact: bool = True


class NarrativeArtifactCreateRequest(_RequestModel):
    title: str = Field(min_length=1, max_length=160)
    content: str = Field(min_length=1)
    artifact_kind: Literal["agent_note", "world_summary"] = "world_summary"
    agent_id: uuid.UUID | None = None


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
    agent_key: str
    display_name: str
    kind: AgentKind
    config: dict[str, Any]
    is_enabled: bool


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


class MemoryItemResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    agent_id: uuid.UUID
    content: str
    metadata: dict[str, Any]
    embedding: list[float]
    visibility: str
    is_active: bool
    source_event_id: uuid.UUID | None
    score: float | None = None


class AgentRunResponse(BaseModel):
    run_id: uuid.UUID
    world_id: uuid.UUID
    agent_id: uuid.UUID
    status: str
    prompt_text: str
    response_text: str | None
    provider_profile_id: uuid.UUID | None
    diagnostics: dict[str, Any]
    started_at: datetime
    finished_at: datetime | None


class NarrativeArtifactResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    agent_id: uuid.UUID | None
    source_run_id: uuid.UUID | None
    title: str
    content: str
    artifact_kind: str
    metadata: dict[str, Any]
    created_at: datetime


class WorldClockResponse(BaseModel):
    world_id: uuid.UUID
    status: str
    current_world_time: datetime
    effective_world_time: datetime
    wall_time_anchor: datetime | None
    speed_multiplier: str
    revision: int


class WorldSnapshotResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    covers_event_sequence: int
    schema_version: str
    status: str
    payload: dict[str, Any] | None
    payload_uri: str | None
    metadata: dict[str, Any]
    created_by_event_id: uuid.UUID
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


@router.post("", response_model=WorldResponse, status_code=status.HTTP_201_CREATED)
def create_world(
    world_create: WorldCreateRequest,
    request: Request,
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorldResponse:
    require_csrf(request)
    _ensure_slug_available(db_session, world_create.slug)
    world = World(
        id=uuid.uuid4(),
        owner_user_id=subject.user_id,
        slug=world_create.slug,
        name=world_create.name,
        description=world_create.description,
        rules_config=world_create.rules_config,
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


@router.patch("/{world_id}", response_model=WorldResponse)
def update_world(
    world_update: WorldUpdateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorldResponse:
    require_csrf(request)
    world = _world_or_404(db_session, context.world_id)
    if "name" in world_update.model_fields_set:
        world.name = world_update.name or world.name
    if "description" in world_update.model_fields_set:
        world.description = world_update.description
    if "rules_config" in world_update.model_fields_set:
        world.rules_config = world_update.rules_config or {}
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
    return WorldReplayService(db_session).replay_state(context.world_id)


@router.get("/{world_id}/snapshots/latest", response_model=WorldSnapshotResponse | None)
def latest_snapshot(
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorldSnapshotResponse | None:
    _world_or_404(db_session, context.world_id)
    snapshot = WorldReplayService(db_session).latest_snapshot(context.world_id)
    if snapshot is None:
        return None
    return _snapshot_response(snapshot)


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
    snapshot = WorldReplayService(db_session).create_snapshot(
        context.world_id,
        actor_ref=_actor_ref(context.subject),
    )
    return _snapshot_response(snapshot)


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
            (WorldMembership.user_id == User.id)
            & (WorldMembership.world_id == context.world_id),
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
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
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
    if membership.role == AuthRole.WORLD_ADMIN.value and _world_admin_count(
        db_session,
        context.world_id,
    ) <= 1:
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
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
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
    return [
        _memory_item_response(item)
        for item in LocalPgvectorMemoryBackend(db_session).list(context.world_id, agent_id)
    ]


@router.post(
    "/{world_id}/agents/{agent_id}/memory",
    response_model=MemoryItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_agent_memory(
    agent_id: uuid.UUID,
    memory_create: MemoryItemCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MemoryItemResponse:
    require_csrf(request)
    _agent_or_404(db_session, context.world_id, agent_id)
    return _memory_item_response(
        LocalPgvectorMemoryBackend(db_session).add(
            MemoryItemCreate(
                world_id=context.world_id,
                agent_id=agent_id,
                content=memory_create.content,
                embedding=memory_create.embedding,
                metadata=memory_create.metadata,
                source_event_id=memory_create.source_event_id,
            ),
        ),
    )


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
    return [
        _memory_item_response(item)
        for item in LocalPgvectorMemoryBackend(db_session).search(
            MemorySearchQuery(
                world_id=context.world_id,
                agent_id=agent_id,
                embedding=search_request.embedding,
                limit=search_request.limit,
            ),
        )
    ]


@router.delete(
    "/{world_id}/agents/{agent_id}/memory/{memory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def disable_agent_memory(
    agent_id: uuid.UUID,
    memory_id: uuid.UUID,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> None:
    require_csrf(request)
    _agent_or_404(db_session, context.world_id, agent_id)
    _memory_item_or_404(db_session, context.world_id, agent_id, memory_id)
    LocalPgvectorMemoryBackend(db_session).disable(memory_id)


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
    orchestrator = AgentRuntimeOrchestrator(
        db_session,
        ProviderProfileService(db_session, load_settings()),
    )
    return [
        _agent_run_response(run)
        for run in orchestrator.list_runs(context.world_id, agent_id)
    ]


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
    orchestrator = AgentRuntimeOrchestrator(
        db_session,
        ProviderProfileService(db_session, load_settings()),
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
) -> list[NarrativeArtifactResponse]:
    return [
        _narrative_artifact_response(artifact)
        for artifact in NarrativeArtifactService(db_session).list_artifacts(context.world_id)
    ]


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
    artifact = AgentRuntimeOrchestrator(
        db_session,
        ProviderProfileService(db_session, load_settings()),
    ).create_narrative_artifact(
        world_id=context.world_id,
        agent_id=artifact_create.agent_id,
        title=artifact_create.title,
        content=artifact_create.content,
        artifact_kind=NarrativeArtifactKind(artifact_create.artifact_kind),
    )
    return _narrative_artifact_response(artifact)


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
    agent = Agent(
        id=uuid.uuid4(),
        world_id=context.world_id,
        home_scene_id=agent_create.home_scene_id,
        agent_key=agent_create.agent_key,
        display_name=agent_create.display_name,
        kind=agent_create.kind,
        config=agent_create.config,
        is_enabled=True,
    )
    db_session.add(agent)
    db_session.flush()
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
    if "home_scene_id" in agent_update.model_fields_set:
        if agent_update.home_scene_id is not None:
            _scene_or_404(db_session, context.world_id, agent_update.home_scene_id)
        agent.home_scene_id = agent_update.home_scene_id
    if "config" in agent_update.model_fields_set:
        agent.config = agent_update.config or {}
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
        agent_key=agent.agent_key,
        display_name=agent.display_name,
        kind=cast(AgentKind, agent.kind),
        config=agent.config,
        is_enabled=agent.is_enabled,
    )


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


def _memory_item_response(item: MemoryItemRecord) -> MemoryItemResponse:
    return MemoryItemResponse(
        id=item.id,
        world_id=item.world_id,
        agent_id=item.agent_id,
        content=item.content,
        metadata=item.metadata,
        embedding=item.embedding,
        visibility=item.visibility,
        is_active=item.is_active,
        source_event_id=item.source_event_id,
        score=item.score,
    )


def _agent_run_response(run: AgentRunExecution) -> AgentRunResponse:
    return AgentRunResponse(
        run_id=run.run_id,
        world_id=run.world_id,
        agent_id=run.agent_id,
        status=run.status,
        prompt_text=run.prompt_text,
        response_text=run.response_text,
        provider_profile_id=run.provider_profile_id,
        diagnostics=run.diagnostics,
        started_at=run.started_at,
        finished_at=run.finished_at,
    )


def _narrative_artifact_response(
    artifact: NarrativeArtifactRecord,
) -> NarrativeArtifactResponse:
    return NarrativeArtifactResponse(
        id=artifact.id,
        world_id=artifact.world_id,
        agent_id=artifact.agent_id,
        source_run_id=artifact.source_run_id,
        title=artifact.title,
        content=artifact.content,
        artifact_kind=artifact.artifact_kind.value,
        metadata=artifact.metadata,
        created_at=artifact.created_at,
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


def _snapshot_response(snapshot: WorldSnapshotRecord) -> WorldSnapshotResponse:
    return WorldSnapshotResponse(
        id=snapshot.id,
        world_id=snapshot.world_id,
        covers_event_sequence=snapshot.covers_event_sequence,
        schema_version=snapshot.schema_version,
        status=snapshot.status.value,
        payload=snapshot.payload,
        payload_uri=snapshot.payload_uri,
        metadata=snapshot.metadata,
        created_by_event_id=snapshot.created_by_event_id,
        created_at=snapshot.created_at,
    )


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


def _memory_item_or_404(
    db_session: Session,
    world_id: uuid.UUID,
    agent_id: uuid.UUID,
    memory_id: uuid.UUID,
) -> AgentMemoryItem:
    memory_item = db_session.get(AgentMemoryItem, memory_id)
    if (
        memory_item is None
        or memory_item.world_id != world_id
        or memory_item.agent_id != agent_id
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory item not found")
    return memory_item


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
    return db_session.scalar(
        select(func.count()).select_from(WorldMembership).where(
            WorldMembership.world_id == world_id,
            WorldMembership.role == AuthRole.WORLD_ADMIN.value,
        ),
    ) or 0


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
