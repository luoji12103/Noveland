from __future__ import annotations

import re
import uuid
from typing import Annotated, Any, Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Response, status
from noveland.agents.models import Agent
from noveland.auth import AuthenticatedSubject, AuthRole
from noveland.auth.models import User
from noveland.services.api.authorization import is_platform_admin
from noveland.services.api.dependencies import (
    WorldAccessContext,
    get_current_subject,
    get_db_session,
    get_platform_admin_subject,
    get_world_admin_context,
    get_world_member_context,
)
from noveland.worlds.models import Scene, World, WorldMembership
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
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


class MembershipResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    user_id: uuid.UUID
    role: WorldRole


class AgentResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    home_scene_id: uuid.UUID | None
    agent_key: str
    display_name: str
    kind: AgentKind
    config: dict[str, Any]
    is_enabled: bool


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
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorldResponse:
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
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> WorldResponse:
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
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> SceneResponse:
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
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> SceneResponse:
    scene = _scene_or_404(db_session, context.world_id, scene_id)
    if "name" in scene_update.model_fields_set:
        scene.name = scene_update.name or scene.name
    if "description" in scene_update.model_fields_set:
        scene.description = scene_update.description
    if "is_active" in scene_update.model_fields_set:
        scene.is_active = bool(scene_update.is_active)
    db_session.flush()
    return _scene_response(scene)


@router.get("/{world_id}/memberships", response_model=list[MembershipResponse])
def list_memberships(
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[MembershipResponse]:
    memberships = db_session.scalars(
        select(WorldMembership)
        .where(WorldMembership.world_id == context.world_id)
        .order_by(WorldMembership.role, WorldMembership.user_id),
    ).all()
    return [_membership_response(membership) for membership in memberships]


@router.put("/{world_id}/memberships/{user_id}", response_model=MembershipResponse)
def upsert_membership(
    user_id: uuid.UUID,
    membership_upsert: MembershipUpsertRequest,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MembershipResponse:
    if user_id != membership_upsert.user_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="user_id mismatch",
        )
    _user_or_404(db_session, user_id)
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
    return _membership_response(membership)


@router.delete("/{world_id}/memberships/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_membership(
    user_id: uuid.UUID,
    response: Response,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> None:
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


@router.post(
    "/{world_id}/agents",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_agent(
    agent_create: AgentCreateRequest,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AgentResponse:
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
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AgentResponse:
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


def _membership_response(membership: WorldMembership) -> MembershipResponse:
    return MembershipResponse(
        id=membership.id,
        world_id=membership.world_id,
        user_id=membership.user_id,
        role=cast(WorldRole, membership.role),
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


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
