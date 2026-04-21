from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from noveland.adapters import ProviderProfileService
from noveland.agents.models import Agent
from noveland.conversations import (
    ConversationMode,
    ConversationParticipantDefinition,
    ConversationParticipantRecord,
    ConversationScopeType,
    ConversationSeed,
    ConversationService,
    ConversationSessionCreate,
    ConversationSessionRecord,
    ConversationSessionStatus,
    ConversationSessionUpdate,
    ConversationTurnRecord,
)
from noveland.conversations.errors import ConversationStateError, ConversationValidationError
from noveland.core.settings import load_settings
from noveland.services.api.csrf import require_csrf
from noveland.services.api.dependencies import (
    WorldAccessContext,
    get_db_session,
    get_world_admin_context,
    get_world_member_context,
)
from noveland.services.runtime import ConversationRuntimeOrchestrator
from noveland.worlds.models import Scene, World
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

router = APIRouter(prefix="/worlds/{world_id}/conversations", tags=["conversations"])


class _RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConversationCreateRequest(_RequestModel):
    session_key: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,78}[a-z0-9]$", max_length=80)
    title: str = Field(min_length=1, max_length=160)
    scope_type: Literal["scene", "world"]
    mode: Literal["manual_chain", "auto_dialogue"]
    scene_id: uuid.UUID | None = None
    objective: str = Field(default="", max_length=8_000)
    opening_prompt: str = Field(default="", max_length=12_000)
    max_turns: int = Field(default=12, ge=1, le=200)

    @model_validator(mode="after")
    def validate_scope(self) -> ConversationCreateRequest:
        if self.scope_type == "scene" and self.scene_id is None:
            raise ValueError("scene_id is required for scene-scoped conversations")
        if self.scope_type == "world" and self.scene_id is not None:
            raise ValueError("scene_id is not allowed for world-scoped conversations")
        return self


class ConversationUpdateRequest(_RequestModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    objective: str | None = Field(default=None, max_length=8_000)
    opening_prompt: str | None = Field(default=None, max_length=12_000)
    max_turns: int | None = Field(default=None, ge=1, le=200)


class ConversationParticipantRequest(_RequestModel):
    agent_id: uuid.UUID
    turn_order: int = Field(ge=0, le=10_000)
    is_enabled: bool = True


class ConversationSeedRequest(_RequestModel):
    input_text: str = Field(min_length=1, max_length=12_000)


class ConversationSessionResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    scene_id: uuid.UUID | None
    session_key: str
    title: str
    scope_type: str
    mode: str
    status: str
    objective: str
    opening_prompt: str
    max_turns: int
    next_turn_index: int
    created_at: str
    updated_at: str


class ConversationParticipantResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    agent_id: uuid.UUID
    turn_order: int
    is_enabled: bool
    created_at: str
    updated_at: str


class ConversationTurnResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    turn_index: int
    speaker_kind: str
    speaker_agent_id: uuid.UUID | None
    input_text: str
    output_text: str | None
    status: str
    run_id: uuid.UUID | None
    error_text: str | None
    created_at: str
    updated_at: str


class ConversationAdvanceResponse(BaseModel):
    session: ConversationSessionResponse
    turn: ConversationTurnResponse


@router.get("", response_model=list[ConversationSessionResponse])
def list_conversations(
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[ConversationSessionResponse]:
    _world_or_404(db_session, context.world_id)
    return [
        _session_response(session)
        for session in ConversationService(db_session).list_sessions(context.world_id)
    ]


@router.post("", response_model=ConversationSessionResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    conversation_create: ConversationCreateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ConversationSessionResponse:
    require_csrf(request)
    _validate_scene_reference(db_session, context.world_id, conversation_create.scene_id)
    try:
        session = ConversationService(db_session).create_session(
            ConversationSessionCreate(
                world_id=context.world_id,
                scene_id=conversation_create.scene_id,
                session_key=conversation_create.session_key,
                title=conversation_create.title,
                scope_type=ConversationScopeType(conversation_create.scope_type),
                mode=ConversationMode(conversation_create.mode),
                objective=conversation_create.objective,
                opening_prompt=conversation_create.opening_prompt,
                max_turns=conversation_create.max_turns,
            ),
        )
    except ConversationValidationError as exc:
        raise _http_error_for_conversation_error(str(exc)) from exc
    return _session_response(session)


@router.get("/{conversation_id}", response_model=ConversationSessionResponse)
def get_conversation(
    conversation_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ConversationSessionResponse:
    try:
        session = ConversationService(db_session).get_session(context.world_id, conversation_id)
    except LookupError as exc:
        raise _not_found() from exc
    return _session_response(session)


@router.patch("/{conversation_id}", response_model=ConversationSessionResponse)
def update_conversation(
    conversation_id: uuid.UUID,
    conversation_update: ConversationUpdateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ConversationSessionResponse:
    require_csrf(request)
    try:
        session = ConversationService(db_session).update_session(
            context.world_id,
            conversation_id,
            ConversationSessionUpdate.model_validate(conversation_update.model_dump(exclude_none=False)),
        )
    except LookupError as exc:
        raise _not_found() from exc
    except (ConversationValidationError, ConversationStateError) as exc:
        raise _http_error_for_conversation_error(str(exc)) from exc
    return _session_response(session)


@router.get("/{conversation_id}/participants", response_model=list[ConversationParticipantResponse])
def list_participants(
    conversation_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[ConversationParticipantResponse]:
    try:
        participants = ConversationService(db_session).list_participants(
            context.world_id,
            conversation_id,
        )
    except LookupError as exc:
        raise _not_found() from exc
    return [_participant_response(participant) for participant in participants]


@router.put("/{conversation_id}/participants", response_model=list[ConversationParticipantResponse])
def replace_participants(
    conversation_id: uuid.UUID,
    participants: list[ConversationParticipantRequest],
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[ConversationParticipantResponse]:
    require_csrf(request)
    service = ConversationService(db_session)
    try:
        session = service.get_session(context.world_id, conversation_id)
    except LookupError as exc:
        raise _not_found() from exc

    for participant in participants:
        agent = _agent_or_404(db_session, context.world_id, participant.agent_id)
        if (
            session.scope_type == ConversationScopeType.SCENE
            and agent.home_scene_id != session.scene_id
        ):
            raise _not_found("Agent scene does not match conversation scope")

    try:
        records = service.replace_participants(
            context.world_id,
            conversation_id,
            [
                ConversationParticipantDefinition(
                    agent_id=participant.agent_id,
                    turn_order=participant.turn_order,
                    is_enabled=participant.is_enabled,
                )
                for participant in participants
            ],
        )
    except ConversationValidationError as exc:
        raise _http_error_for_conversation_error(str(exc)) from exc
    return [_participant_response(participant) for participant in records]


@router.get("/{conversation_id}/turns", response_model=list[ConversationTurnResponse])
def list_turns(
    conversation_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[ConversationTurnResponse]:
    try:
        turns = ConversationService(db_session).list_turns(context.world_id, conversation_id)
    except LookupError as exc:
        raise _not_found() from exc
    return [_turn_response(turn) for turn in turns]


@router.post("/{conversation_id}/seed", response_model=ConversationTurnResponse)
def seed_conversation(
    conversation_id: uuid.UUID,
    seed_request: ConversationSeedRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ConversationTurnResponse:
    require_csrf(request)
    try:
        turn = ConversationService(db_session).seed_session(
            context.world_id,
            conversation_id,
            ConversationSeed(input_text=seed_request.input_text),
        )
    except LookupError as exc:
        raise _not_found() from exc
    except (ConversationValidationError, ConversationStateError) as exc:
        raise _http_error_for_conversation_error(str(exc)) from exc
    return _turn_response(turn)


@router.post("/{conversation_id}/advance", response_model=ConversationAdvanceResponse)
def advance_conversation(
    conversation_id: uuid.UUID,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ConversationAdvanceResponse:
    require_csrf(request)
    service = ConversationService(db_session)
    try:
        session = service.get_session(context.world_id, conversation_id)
    except LookupError as exc:
        raise _not_found() from exc
    if (
        session.mode == ConversationMode.AUTO_DIALOGUE
        and session.status != ConversationSessionStatus.PAUSED
    ):
        raise _conflict("Auto dialogue sessions can only advance manually while paused")
    try:
        result = ConversationRuntimeOrchestrator(
            db_session,
            ProviderProfileService(db_session, load_settings()),
        ).advance_session(
            context.world_id,
            conversation_id,
            allow_running_auto=False,
            trigger_source="manual",
        )
    except LookupError as exc:
        raise _not_found() from exc
    except (ConversationValidationError, ConversationStateError) as exc:
        raise _http_error_for_conversation_error(str(exc)) from exc
    return ConversationAdvanceResponse(
        session=_session_response(result.session),
        turn=_turn_response(result.turn),
    )


@router.post("/{conversation_id}/start", response_model=ConversationSessionResponse)
def start_conversation(
    conversation_id: uuid.UUID,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ConversationSessionResponse:
    require_csrf(request)
    try:
        session = ConversationService(db_session).start_session(context.world_id, conversation_id)
    except LookupError as exc:
        raise _not_found() from exc
    except (ConversationValidationError, ConversationStateError) as exc:
        raise _http_error_for_conversation_error(str(exc)) from exc
    return _session_response(session)


@router.post("/{conversation_id}/pause", response_model=ConversationSessionResponse)
def pause_conversation(
    conversation_id: uuid.UUID,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ConversationSessionResponse:
    require_csrf(request)
    try:
        session = ConversationService(db_session).pause_session(context.world_id, conversation_id)
    except LookupError as exc:
        raise _not_found() from exc
    except (ConversationValidationError, ConversationStateError) as exc:
        raise _http_error_for_conversation_error(str(exc)) from exc
    return _session_response(session)


@router.post("/{conversation_id}/resume", response_model=ConversationSessionResponse)
def resume_conversation(
    conversation_id: uuid.UUID,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ConversationSessionResponse:
    require_csrf(request)
    try:
        session = ConversationService(db_session).resume_session(context.world_id, conversation_id)
    except LookupError as exc:
        raise _not_found() from exc
    except (ConversationValidationError, ConversationStateError) as exc:
        raise _http_error_for_conversation_error(str(exc)) from exc
    return _session_response(session)


def _session_response(session: ConversationSessionRecord) -> ConversationSessionResponse:
    return ConversationSessionResponse(
        id=session.id,
        world_id=session.world_id,
        scene_id=session.scene_id,
        session_key=session.session_key,
        title=session.title,
        scope_type=session.scope_type.value,
        mode=session.mode.value,
        status=session.status.value,
        objective=session.objective,
        opening_prompt=session.opening_prompt,
        max_turns=session.max_turns,
        next_turn_index=session.next_turn_index,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
    )


def _participant_response(
    participant: ConversationParticipantRecord,
) -> ConversationParticipantResponse:
    return ConversationParticipantResponse(
        id=participant.id,
        session_id=participant.session_id,
        agent_id=participant.agent_id,
        turn_order=participant.turn_order,
        is_enabled=participant.is_enabled,
        created_at=participant.created_at.isoformat(),
        updated_at=participant.updated_at.isoformat(),
    )


def _turn_response(turn: ConversationTurnRecord) -> ConversationTurnResponse:
    return ConversationTurnResponse(
        id=turn.id,
        session_id=turn.session_id,
        turn_index=turn.turn_index,
        speaker_kind=turn.speaker_kind.value,
        speaker_agent_id=turn.speaker_agent_id,
        input_text=turn.input_text,
        output_text=turn.output_text,
        status=turn.status.value,
        run_id=turn.run_id,
        error_text=turn.error_text,
        created_at=turn.created_at.isoformat(),
        updated_at=turn.updated_at.isoformat(),
    )


def _validate_scene_reference(
    db_session: Session,
    world_id: uuid.UUID,
    scene_id: uuid.UUID | None,
) -> None:
    if scene_id is None:
        return
    scene = db_session.get(Scene, scene_id)
    if scene is None or scene.world_id != world_id:
        raise _not_found("Scene not found")


def _world_or_404(db_session: Session, world_id: uuid.UUID) -> World:
    world = db_session.get(World, world_id)
    if world is None:
        raise _not_found()
    return world


def _agent_or_404(db_session: Session, world_id: uuid.UUID, agent_id: uuid.UUID) -> Agent:
    agent = db_session.get(Agent, agent_id)
    if agent is None or agent.world_id != world_id:
        raise _not_found("Agent not found")
    return agent


def _not_found(detail: str = "Conversation not found") -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _http_error_for_conversation_error(detail: str) -> HTTPException:
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    if (
        "already exists" in detail
        or "cannot" in detail
        or "no longer" in detail
        or "already" in detail
        or "paused" in detail
    ):
        status_code = status.HTTP_409_CONFLICT
    return HTTPException(status_code=status_code, detail=detail)
