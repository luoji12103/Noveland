from __future__ import annotations

import asyncio
import base64
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from fastapi.encoders import jsonable_encoder
from noveland.adapters import ProviderProfileService
from noveland.adapters.models import ProviderProfile
from noveland.agents.models import AgentRuntimeRun
from noveland.auth import AuthenticatedSubject, AuthSessionService
from noveland.auth.errors import InvalidSessionError
from noveland.conversations import ConversationSeed, ConversationService
from noveland.conversations.errors import ConversationStateError, ConversationValidationError
from noveland.conversations.models import ConversationSession, ConversationTurn
from noveland.core.models import RuntimeControlState
from noveland.core.settings import load_settings
from noveland.memory import MemoryService
from noveland.narrative.models import NarrativeArtifact
from noveland.observability import DiagnosticComponent, DiagnosticSeverity
from noveland.observability.models import RuntimeDiagnosticEvent
from noveland.services.api.authorization import (
    require_platform_admin,
    require_world_admin,
    require_world_member,
)
from noveland.services.api.dependencies import get_session_factory
from noveland.services.runtime import ConversationRuntimeOrchestrator
from noveland.services.runtime.daemon import get_runtime_control_view
from noveland.worlds.clock_service import WorldClockService
from sqlalchemy import and_, func, or_, select
from starlette.responses import StreamingResponse

router = APIRouter(tags=["realtime"])

STREAM_POLL_INTERVAL_SECONDS = 1.0
STREAM_KEEPALIVE_SECONDS = 15.0


@router.get("/runtime/stream")
async def runtime_stream(request: Request) -> StreamingResponse:
    _authenticate_runtime_request(request)
    return _stream_response(
        request,
        lambda cursor: collect_runtime_stream_delta(cursor),
    )


@router.get("/worlds/{world_id}/stream")
async def world_stream(world_id: uuid.UUID, request: Request) -> StreamingResponse:
    _authenticate_world_request(request, world_id)
    return _stream_response(
        request,
        lambda cursor: collect_world_stream_delta(world_id, cursor),
    )


@router.get("/worlds/{world_id}/conversations/{conversation_id}/stream")
async def conversation_stream(
    world_id: uuid.UUID,
    conversation_id: uuid.UUID,
    request: Request,
) -> StreamingResponse:
    _authenticate_world_request(request, world_id)
    return _stream_response(
        request,
        lambda cursor: collect_conversation_stream_delta(world_id, conversation_id, cursor),
    )


@router.websocket("/worlds/{world_id}/conversations/{conversation_id}/live")
async def conversation_live(
    websocket: WebSocket,
    world_id: uuid.UUID,
    conversation_id: uuid.UUID,
) -> None:
    if not _origin_allowed(websocket.headers.get("origin"), str(websocket.url)):
        await websocket.close(code=4403, reason="Forbidden")
        return

    try:
        subject = _authenticate_websocket(websocket)
    except HTTPException as exc:
        await websocket.close(code=_websocket_close_code(exc.status_code), reason=exc.detail)
        return

    try:
        with get_session_factory()() as session:
            require_world_member(session, subject, world_id)
            can_manage = False
            try:
                require_world_admin(session, subject, world_id)
                can_manage = True
            except HTTPException:
                can_manage = False
            snapshot = _conversation_snapshot(session, world_id, conversation_id)
            session.commit()
    except HTTPException as exc:
        await websocket.close(code=_websocket_close_code(exc.status_code), reason=exc.detail)
        return
    except LookupError:
        await websocket.close(code=4404, reason="Not found")
        return

    await websocket.accept()
    await websocket.send_json(
        _socket_message("session_snapshot", payload=snapshot),
    )

    try:
        while True:
            raw_message = await websocket.receive_json()
            request_id = (
                raw_message.get("request_id")
                if isinstance(raw_message.get("request_id"), str)
                else None
            )
            command = (
                raw_message.get("command")
                if isinstance(raw_message.get("command"), str)
                else ""
            )
            payload = raw_message.get("payload")
            if not isinstance(payload, dict):
                payload = {}

            if not can_manage:
                await websocket.send_json(
                    _socket_message(
                        "error",
                        request_id=request_id,
                        payload={"message": "Forbidden"},
                    ),
                )
                continue

            try:
                messages = _handle_live_command(
                    world_id=world_id,
                    conversation_id=conversation_id,
                    subject=subject,
                    command=command,
                    request_id=request_id,
                    payload=payload,
                )
            except HTTPException as exc:
                await websocket.send_json(
                    _socket_message(
                        "error",
                        request_id=request_id,
                        payload={"message": exc.detail},
                    ),
                )
                continue

            for message in messages:
                await websocket.send_json(message)
    except WebSocketDisconnect:
        return


def collect_runtime_stream_delta(cursor: str | None) -> dict[str, Any] | None:
    parsed = _decode_cursor(cursor)
    with get_session_factory()() as session:
        settings = load_settings()
        view = get_runtime_control_view(session)
        control_model = session.scalars(
            select(RuntimeControlState).where(RuntimeControlState.control_key == "default"),
        ).one_or_none()
        diagnostics = _runtime_diagnostics_since(session, parsed.get("runtime_diagnostic"))
        provider_profiles = _provider_profiles_since(session, parsed.get("provider_test"))
        control_updated_at = None if control_model is None else _isoformat(control_model.updated_at)
        control_changed = cursor is None or parsed.get("runtime_control") != control_updated_at
        has_changes = control_changed or diagnostics or provider_profiles
        if not has_changes:
            session.commit()
            return None

        payload: dict[str, Any] = {
            "diagnostics": [_diagnostic_payload(record) for record in diagnostics],
            "provider_profiles": [_provider_profile_payload(model) for model in provider_profiles],
        }
        if control_changed:
            payload["runtime_control"] = _runtime_control_payload(view)
            payload["runtime_status"] = _runtime_status_payload(view, settings, session)

        next_cursor = _encode_cursor(
            {
                "runtime_control": control_updated_at,
                "runtime_diagnostic": _last_cursor_key(
                    diagnostics,
                    lambda item: item.occurred_at,
                    lambda item: item.id,
                    parsed.get("runtime_diagnostic"),
                ),
                "provider_test": _last_cursor_key(
                    provider_profiles,
                    lambda item: item.last_tested_at,
                    lambda item: item.id,
                    parsed.get("provider_test"),
                ),
            },
        )
        session.commit()
    return _stream_envelope(
        cursor=next_cursor,
        event_type="runtime.delta",
        payload=payload,
    )


def collect_world_stream_delta(world_id: uuid.UUID, cursor: str | None) -> dict[str, Any] | None:
    parsed = _decode_cursor(cursor)
    with get_session_factory()() as session:
        clock_view = WorldClockService(session).view(world_id)
        diagnostics = _world_diagnostics_since(
            session,
            world_id,
            parsed.get("world_diagnostic"),
        )
        agent_runs = _world_agent_runs_since(session, world_id, parsed.get("agent_run"))
        artifacts = _world_narrative_artifacts_since(
            session,
            world_id,
            parsed.get("narrative_artifact"),
        )
        conversations = _world_conversations_since(
            session,
            world_id,
            parsed.get("conversation_session"),
        )
        clock_revision = clock_view.state.revision
        clock_changed = cursor is None or parsed.get("clock_revision") != clock_revision
        has_changes = clock_changed or diagnostics or agent_runs or artifacts or conversations
        if not has_changes:
            session.commit()
            return None

        payload: dict[str, Any] = {
            "diagnostics": [_diagnostic_payload(record) for record in diagnostics],
            "agent_runs": [_agent_run_payload(model) for model in agent_runs],
            "narrative_artifacts": [_narrative_artifact_payload(model) for model in artifacts],
            "conversations": [_conversation_session_payload(model) for model in conversations],
        }
        if clock_changed:
            payload["clock"] = _world_clock_payload(clock_view)

        next_cursor = _encode_cursor(
            {
                "clock_revision": clock_revision,
                "world_diagnostic": _last_cursor_key(
                    diagnostics,
                    lambda item: item.occurred_at,
                    lambda item: item.id,
                    parsed.get("world_diagnostic"),
                ),
                "agent_run": _last_cursor_key(
                    agent_runs,
                    lambda item: item.started_at,
                    lambda item: item.id,
                    parsed.get("agent_run"),
                ),
                "narrative_artifact": _last_cursor_key(
                    artifacts,
                    lambda item: item.created_at,
                    lambda item: item.id,
                    parsed.get("narrative_artifact"),
                ),
                "conversation_session": _last_cursor_key(
                    conversations,
                    lambda item: item.updated_at,
                    lambda item: item.id,
                    parsed.get("conversation_session"),
                ),
            },
        )
        session.commit()
    return _stream_envelope(
        cursor=next_cursor,
        event_type="world.delta",
        payload=payload,
        world_id=world_id,
    )


def collect_conversation_stream_delta(
    world_id: uuid.UUID,
    conversation_id: uuid.UUID,
    cursor: str | None,
) -> dict[str, Any] | None:
    parsed = _decode_cursor(cursor)
    with get_session_factory()() as session:
        conversation_service = ConversationService(session)
        session_record = conversation_service.get_session(world_id, conversation_id)
        turns = _conversation_turns_since(
            session,
            conversation_id,
            parsed.get("turn_index"),
        )
        diagnostics = _conversation_diagnostics_since(
            session,
            world_id,
            conversation_id,
            parsed.get("conversation_diagnostic"),
        )
        session_key = _entity_key(session_record.updated_at, session_record.id)
        session_changed = cursor is None or parsed.get("conversation_session") != session_key
        has_changes = session_changed or turns or diagnostics
        if not has_changes:
            session.commit()
            return None

        payload: dict[str, Any] = {
            "turns": [_conversation_turn_payload(turn) for turn in turns],
            "diagnostics": [_diagnostic_payload(record) for record in diagnostics],
        }
        if session_changed:
            payload["session"] = jsonable_encoder(session_record.model_dump(mode="json"))

        next_cursor = _encode_cursor(
            {
                "conversation_session": session_key,
                "turn_index": turns[-1].turn_index if turns else parsed.get("turn_index", -1),
                "conversation_diagnostic": _last_cursor_key(
                    diagnostics,
                    lambda item: item.occurred_at,
                    lambda item: item.id,
                    parsed.get("conversation_diagnostic"),
                ),
            },
        )
        session.commit()
    return _stream_envelope(
        cursor=next_cursor,
        event_type="conversation.delta",
        payload=payload,
        world_id=world_id,
        conversation_id=conversation_id,
    )


def _handle_live_command(
    *,
    world_id: uuid.UUID,
    conversation_id: uuid.UUID,
    subject: AuthenticatedSubject,
    command: str,
    request_id: str | None,
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    with get_session_factory()() as session:
        require_world_admin(session, subject, world_id)
        conversation_service = ConversationService(session)
        profile_service = ProviderProfileService(session, load_settings())
        messages: list[dict[str, Any]] = []
        try:
            if command == "seed":
                input_text = payload.get("input_text")
                if not isinstance(input_text, str) or input_text.strip() == "":
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail="input_text is required",
                    )
                turn = conversation_service.seed_session(
                    world_id,
                    conversation_id,
                    ConversationSeed(input_text=input_text),
                )
                session_record = conversation_service.get_session(world_id, conversation_id)
                messages.extend(
                    [
                        _socket_message("ack", request_id=request_id, payload={"command": command}),
                        _socket_message(
                            "turn_appended",
                            request_id=request_id,
                            payload=jsonable_encoder(turn.model_dump(mode="json")),
                        ),
                        _socket_message(
                            "session_snapshot",
                            request_id=request_id,
                            payload=_conversation_snapshot_from_service(
                                conversation_service,
                                session_record,
                            ),
                        ),
                    ]
                )
            elif command == "advance":
                result = ConversationRuntimeOrchestrator(
                    session,
                    profile_service,
                    load_settings(),
                ).advance_session(
                    world_id,
                    conversation_id,
                    allow_running_auto=False,
                    trigger_source="manual",
                )
                messages.extend(
                    [
                        _socket_message("ack", request_id=request_id, payload={"command": command}),
                        _socket_message(
                            "turn_appended",
                            request_id=request_id,
                            payload=jsonable_encoder(result.turn.model_dump(mode="json")),
                        ),
                        _socket_message(
                            "status_changed",
                            request_id=request_id,
                            payload=jsonable_encoder(result.session.model_dump(mode="json")),
                        ),
                    ]
                )
            elif command == "start":
                session_record = conversation_service.start_session(world_id, conversation_id)
                messages.extend(
                    [
                        _socket_message("ack", request_id=request_id, payload={"command": command}),
                        _socket_message(
                            "status_changed",
                            request_id=request_id,
                            payload=jsonable_encoder(session_record.model_dump(mode="json")),
                        ),
                    ]
                )
            elif command == "pause":
                session_record = conversation_service.pause_session(world_id, conversation_id)
                messages.extend(
                    [
                        _socket_message("ack", request_id=request_id, payload={"command": command}),
                        _socket_message(
                            "status_changed",
                            request_id=request_id,
                            payload=jsonable_encoder(session_record.model_dump(mode="json")),
                        ),
                    ]
                )
            elif command == "resume":
                session_record = conversation_service.resume_session(world_id, conversation_id)
                messages.extend(
                    [
                        _socket_message("ack", request_id=request_id, payload={"command": command}),
                        _socket_message(
                            "status_changed",
                            request_id=request_id,
                            payload=jsonable_encoder(session_record.model_dump(mode="json")),
                        ),
                    ]
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Unsupported live conversation command",
                )
        except (ConversationStateError, ConversationValidationError) as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from exc
        session.commit()
        return messages


def _conversation_snapshot(
    session: Any,
    world_id: uuid.UUID,
    conversation_id: uuid.UUID,
) -> dict[str, Any]:
    service = ConversationService(session)
    session_record = service.get_session(world_id, conversation_id)
    return _conversation_snapshot_from_service(service, session_record)


def _conversation_snapshot_from_service(
    service: ConversationService,
    session_record: Any,
) -> dict[str, Any]:
    return {
        "session": jsonable_encoder(session_record.model_dump(mode="json")),
        "participants": [
            jsonable_encoder(participant.model_dump(mode="json"))
            for participant in service.list_participants(session_record.world_id, session_record.id)
        ],
        "turns": [
            jsonable_encoder(turn.model_dump(mode="json"))
            for turn in service.list_turns(session_record.world_id, session_record.id)
        ],
        "diagnostics": [
            _diagnostic_payload(record)
            for record in service.list_diagnostics(session_record.world_id, session_record.id)
        ],
    }


def _authenticate_runtime_request(request: Request) -> AuthenticatedSubject:
    subject = _authenticate_http_subject(request)
    require_platform_admin(subject)
    return subject


def _authenticate_world_request(request: Request, world_id: uuid.UUID) -> AuthenticatedSubject:
    subject = _authenticate_http_subject(request)
    with get_session_factory()() as session:
        require_world_member(session, subject, world_id)
        session.commit()
    return subject


def _authenticate_http_subject(request: Request) -> AuthenticatedSubject:
    token = request.cookies.get("noveland_session")
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing session",
        )
    with get_session_factory()() as session:
        try:
            subject = AuthSessionService(session).authenticate_session(token)
        except InvalidSessionError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing session",
            ) from exc
        session.commit()
        return subject


def _authenticate_websocket(websocket: WebSocket) -> AuthenticatedSubject:
    token = websocket.cookies.get("noveland_session")
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing session",
        )
    with get_session_factory()() as session:
        try:
            subject = AuthSessionService(session).authenticate_session(token)
        except InvalidSessionError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing session",
            ) from exc
        session.commit()
        return subject


def _stream_response(
    request: Request,
    collector: Any,
) -> StreamingResponse:
    last_event_id = request.headers.get("last-event-id")

    async def event_generator() -> Any:
        cursor = last_event_id
        last_keepalive = datetime.now(UTC)
        while not await request.is_disconnected():
            envelope = collector(cursor)
            if envelope is not None:
                cursor = envelope["cursor"]
                yield _format_sse(envelope)
                last_keepalive = datetime.now(UTC)
            elif (datetime.now(UTC) - last_keepalive).total_seconds() >= STREAM_KEEPALIVE_SECONDS:
                yield ": keepalive\n\n"
                last_keepalive = datetime.now(UTC)
            await asyncio.sleep(STREAM_POLL_INTERVAL_SECONDS)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "cache-control": "no-store",
            "connection": "keep-alive",
            "x-accel-buffering": "no",
        },
    )


def _runtime_diagnostics_since(
    session: Any,
    cursor: dict[str, str] | None,
) -> list[RuntimeDiagnosticEvent]:
    statement = select(RuntimeDiagnosticEvent)
    if cursor is not None and cursor.get("at") and cursor.get("id"):
        occurred_at = _parse_datetime(cursor["at"])
        identifier = uuid.UUID(cursor["id"])
        statement = statement.where(
            or_(
                RuntimeDiagnosticEvent.occurred_at > occurred_at,
                and_(
                    RuntimeDiagnosticEvent.occurred_at == occurred_at,
                    RuntimeDiagnosticEvent.id > identifier,
                ),
            ),
        )
    return list(
        session.scalars(
            statement.order_by(
                RuntimeDiagnosticEvent.occurred_at,
                RuntimeDiagnosticEvent.id,
            ).limit(50),
        ).all()
    )


def _world_diagnostics_since(
    session: Any,
    world_id: uuid.UUID,
    cursor: dict[str, str] | None,
) -> list[RuntimeDiagnosticEvent]:
    statement = select(RuntimeDiagnosticEvent).where(RuntimeDiagnosticEvent.world_id == world_id)
    if cursor is not None and cursor.get("at") and cursor.get("id"):
        occurred_at = _parse_datetime(cursor["at"])
        identifier = uuid.UUID(cursor["id"])
        statement = statement.where(
            or_(
                RuntimeDiagnosticEvent.occurred_at > occurred_at,
                and_(
                    RuntimeDiagnosticEvent.occurred_at == occurred_at,
                    RuntimeDiagnosticEvent.id > identifier,
                ),
            ),
        )
    return list(
        session.scalars(
            statement.order_by(
                RuntimeDiagnosticEvent.occurred_at,
                RuntimeDiagnosticEvent.id,
            ).limit(50),
        ).all()
    )


def _provider_profiles_since(
    session: Any,
    cursor: dict[str, str] | None,
) -> list[ProviderProfile]:
    statement = select(ProviderProfile)
    if cursor is None or cursor.get("at") is None or cursor.get("id") is None:
        return list(session.scalars(statement.order_by(ProviderProfile.profile_key)).all())
    tested_at = _parse_datetime(cursor["at"])
    identifier = uuid.UUID(cursor["id"])
    return list(
        session.scalars(
            statement.where(
                ProviderProfile.last_tested_at.is_not(None),
                or_(
                    ProviderProfile.last_tested_at > tested_at,
                    and_(
                        ProviderProfile.last_tested_at == tested_at,
                        ProviderProfile.id > identifier,
                    ),
                ),
            )
            .order_by(ProviderProfile.last_tested_at, ProviderProfile.id)
            .limit(50),
        ).all()
    )


def _world_agent_runs_since(
    session: Any,
    world_id: uuid.UUID,
    cursor: dict[str, str] | None,
) -> list[AgentRuntimeRun]:
    statement = select(AgentRuntimeRun).where(AgentRuntimeRun.world_id == world_id)
    if cursor is None or cursor.get("at") is None or cursor.get("id") is None:
        return list(
            session.scalars(
                statement.order_by(AgentRuntimeRun.started_at.desc()).limit(10),
            ).all()
        )[::-1]
    started_at = _parse_datetime(cursor["at"])
    identifier = uuid.UUID(cursor["id"])
    return list(
        session.scalars(
            statement.where(
                or_(
                    AgentRuntimeRun.started_at > started_at,
                    and_(
                        AgentRuntimeRun.started_at == started_at,
                        AgentRuntimeRun.id > identifier,
                    ),
                ),
            )
            .order_by(AgentRuntimeRun.started_at, AgentRuntimeRun.id)
            .limit(50),
        ).all()
    )


def _world_narrative_artifacts_since(
    session: Any,
    world_id: uuid.UUID,
    cursor: dict[str, str] | None,
) -> list[NarrativeArtifact]:
    statement = select(NarrativeArtifact).where(NarrativeArtifact.world_id == world_id)
    if cursor is None or cursor.get("at") is None or cursor.get("id") is None:
        return list(
            session.scalars(statement.order_by(NarrativeArtifact.created_at.desc()).limit(10)).all()
        )[::-1]
    created_at = _parse_datetime(cursor["at"])
    identifier = uuid.UUID(cursor["id"])
    return list(
        session.scalars(
            statement.where(
                or_(
                    NarrativeArtifact.created_at > created_at,
                    and_(
                        NarrativeArtifact.created_at == created_at,
                        NarrativeArtifact.id > identifier,
                    ),
                ),
            )
            .order_by(NarrativeArtifact.created_at, NarrativeArtifact.id)
            .limit(50),
        ).all()
    )


def _world_conversations_since(
    session: Any,
    world_id: uuid.UUID,
    cursor: dict[str, str] | None,
) -> list[ConversationSession]:
    statement = select(ConversationSession).where(ConversationSession.world_id == world_id)
    if cursor is None or cursor.get("at") is None or cursor.get("id") is None:
        return list(session.scalars(statement.order_by(ConversationSession.updated_at)).all())
    updated_at = _parse_datetime(cursor["at"])
    identifier = uuid.UUID(cursor["id"])
    return list(
        session.scalars(
            statement.where(
                or_(
                    ConversationSession.updated_at > updated_at,
                    and_(
                        ConversationSession.updated_at == updated_at,
                        ConversationSession.id > identifier,
                    ),
                ),
            )
            .order_by(ConversationSession.updated_at, ConversationSession.id)
            .limit(50),
        ).all()
    )


def _conversation_turns_since(
    session: Any,
    conversation_id: uuid.UUID,
    turn_index: int | None,
) -> list[Any]:
    statement = select(ConversationSession.id).where(ConversationSession.id == conversation_id)
    if session.scalar(statement) is None:
        raise LookupError
    turns = list(
        session.scalars(
            select(ConversationTurn)
            .where(ConversationTurn.session_id == conversation_id)
            .order_by(ConversationTurn.turn_index),
        ).all()
    )
    if turn_index is None:
        return turns
    return [turn for turn in turns if turn.turn_index > turn_index]


def _conversation_diagnostics_since(
    session: Any,
    world_id: uuid.UUID,
    conversation_id: uuid.UUID,
    cursor: dict[str, str] | None,
) -> list[Any]:
    service = ConversationService(session)
    diagnostics = service.list_diagnostics(world_id, conversation_id, limit=100)
    diagnostics = sorted(diagnostics, key=lambda record: (record.occurred_at, record.id))
    if cursor is None or cursor.get("at") is None or cursor.get("id") is None:
        return diagnostics
    occurred_at = _parse_datetime(cursor["at"])
    identifier = uuid.UUID(cursor["id"])
    return [
        record
        for record in diagnostics
        if (record.occurred_at, record.id) > (occurred_at, identifier)
    ]


def _world_clock_payload(view: Any) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        jsonable_encoder(
        {
            "world_id": view.state.world_id,
            "status": view.state.status.value,
            "current_world_time": view.state.current_world_time,
            "effective_world_time": view.effective_world_time,
            "wall_time_anchor": view.state.wall_time_anchor,
            "speed_multiplier": str(view.state.speed_multiplier),
            "revision": view.state.revision,
        },
        ),
    )


def _runtime_control_payload(view: Any) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        jsonable_encoder(
        {
            "desired_state": view.desired_state,
            "last_heartbeat_at": view.last_heartbeat_at,
            "last_run_started_at": view.last_run_started_at,
            "last_run_finished_at": view.last_run_finished_at,
            "last_error": view.last_error,
        },
        ),
    )


def _runtime_status_payload(view: Any, settings: Any, session: Any | None = None) -> dict[str, Any]:
    payload = _runtime_control_payload(view)
    payload["runtime_loop_interval_seconds"] = settings.runtime_loop_interval_seconds
    payload["runtime_batch_limit"] = settings.runtime_batch_limit
    if session is not None:
        memory_summary = MemoryService(session, settings).write_job_status_summary()
        payload["memory_write_jobs"] = memory_summary.model_dump()
        payload["runtime_health"] = _runtime_health_payload(
            session,
            view,
            memory_summary,
            settings,
        )
    return payload


def _runtime_health_payload(
    session: Any,
    view: Any,
    memory_summary: Any,
    settings: Any,
) -> dict[str, Any]:
    recent_diagnostic_count, recent_error_count = _runtime_diagnostic_counts(session)
    heartbeat_age_seconds: int | None = None
    if view.last_heartbeat_at is not None:
        heartbeat_age_seconds = max(
            0,
            int((datetime.now(UTC) - _aware_datetime(view.last_heartbeat_at)).total_seconds()),
        )
    if view.desired_state == "stopped":
        status_value = "stopped"
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
    return {
        "status": status_value,
        "reason": reason,
        "recent_diagnostic_count": recent_diagnostic_count,
        "recent_error_count": recent_error_count,
        "heartbeat_age_seconds": heartbeat_age_seconds,
    }


def _runtime_diagnostic_counts(session: Any) -> tuple[int, int]:
    since = datetime.now(UTC) - timedelta(hours=1)
    rows = session.execute(
        select(RuntimeDiagnosticEvent.severity, func.count(RuntimeDiagnosticEvent.id))
        .where(
            RuntimeDiagnosticEvent.component == DiagnosticComponent.RUNTIME.value,
            RuntimeDiagnosticEvent.occurred_at >= since,
        )
        .group_by(RuntimeDiagnosticEvent.severity),
    ).all()
    counts = {str(severity): int(count) for severity, count in rows}
    return sum(counts.values()), counts.get(DiagnosticSeverity.ERROR.value, 0)


def _provider_profile_payload(model: ProviderProfile) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        jsonable_encoder(
        {
            "id": model.id,
            "profile_key": model.profile_key,
            "name": model.name,
            "provider_type": model.provider_type,
            "last_tested_at": model.last_tested_at,
            "last_test_status": model.last_test_status,
            "last_test_error": model.last_test_error,
            "is_enabled": model.is_enabled,
        },
        ),
    )


def _conversation_turn_payload(model: ConversationTurn) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        jsonable_encoder(
        {
            "id": model.id,
            "session_id": model.session_id,
            "turn_index": model.turn_index,
            "speaker_kind": model.speaker_kind,
            "speaker_agent_id": model.speaker_agent_id,
            "input_text": model.input_text,
            "output_text": model.output_text,
            "status": model.status,
            "run_id": model.run_id,
            "error_text": model.error_text,
            "created_at": model.created_at,
            "updated_at": model.updated_at,
        },
        ),
    )


def _diagnostic_payload(record: Any) -> dict[str, Any]:
    if hasattr(record, "model_dump"):
        return cast(
            dict[str, Any],
            jsonable_encoder(record.model_dump(mode="json")),
        )
    return cast(
        dict[str, Any],
        jsonable_encoder(
        {
            "id": record.id,
            "severity": record.severity,
            "component": record.component,
            "event_type": record.event_type,
            "message": record.message,
            "details": record.details,
            "occurred_at": record.occurred_at,
            "world_id": record.world_id,
            "agent_id": record.agent_id,
            "run_id": record.run_id,
            "provider_profile_id": record.provider_profile_id,
            "created_at": record.created_at,
        },
        ),
    )


def _agent_run_payload(model: AgentRuntimeRun) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        jsonable_encoder(
        {
            "run_id": model.id,
            "world_id": model.world_id,
            "agent_id": model.agent_id,
            "status": model.status,
            "prompt_text": model.prompt_text,
            "response_text": model.response_text,
            "provider_profile_id": model.provider_profile_id,
            "diagnostics": model.diagnostics,
            "started_at": model.started_at,
            "finished_at": model.finished_at,
        },
        ),
    )


def _narrative_artifact_payload(model: NarrativeArtifact) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        jsonable_encoder(
        {
            "id": model.id,
            "world_id": model.world_id,
            "agent_id": model.agent_id,
            "source_run_id": model.source_run_id,
            "source_conversation_id": model.source_conversation_id,
            "title": model.title,
            "content": model.content,
            "artifact_kind": model.artifact_kind,
            "metadata": model.artifact_metadata,
            "created_at": model.created_at,
        },
        ),
    )


def _conversation_session_payload(model: ConversationSession) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        jsonable_encoder(
        {
            "id": model.id,
            "world_id": model.world_id,
            "scene_id": model.scene_id,
            "session_key": model.session_key,
            "title": model.title,
            "scope_type": model.scope_type,
            "mode": model.mode,
            "status": model.status,
            "objective": model.objective,
            "opening_prompt": model.opening_prompt,
            "max_turns": model.max_turns,
            "next_turn_index": model.next_turn_index,
            "policy": model.policy_config,
            "writer_config": model.writer_config,
            "terminal_reason": model.terminal_reason,
            "created_at": model.created_at,
            "updated_at": model.updated_at,
        },
        ),
    )


def _stream_envelope(
    *,
    cursor: str,
    event_type: str,
    payload: dict[str, Any],
    world_id: uuid.UUID | None = None,
    conversation_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        jsonable_encoder(
        {
            "cursor": cursor,
            "event_type": event_type,
            "occurred_at": datetime.now(UTC),
            "world_id": world_id,
            "conversation_id": conversation_id,
            "payload": payload,
        },
        ),
    )


def _format_sse(envelope: dict[str, Any]) -> str:
    return f"id: {envelope['cursor']}\ndata: {json.dumps(envelope, separators=(',', ':'))}\n\n"


def _socket_message(
    message_type: str,
    *,
    request_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    message = {
        "type": message_type,
        "occurred_at": datetime.now(UTC).isoformat(),
        "payload": payload or {},
    }
    if request_id is not None:
        message["request_id"] = request_id
    return message


def _decode_cursor(cursor: str | None) -> dict[str, Any]:
    if cursor is None or cursor == "":
        return {}
    try:
        padding = "=" * (-len(cursor) % 4)
        return cast(
            dict[str, Any],
            json.loads(base64.urlsafe_b64decode(f"{cursor}{padding}").decode("utf-8")),
        )
    except Exception:
        return {}


def _encode_cursor(payload: dict[str, Any]) -> str:
    return base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"),
    ).decode("utf-8").rstrip("=")


def _entity_key(timestamp: datetime, identifier: uuid.UUID) -> dict[str, str]:
    return {"at": _isoformat(timestamp), "id": str(identifier)}


def _last_cursor_key(
    items: list[Any],
    timestamp_getter: Any,
    id_getter: Any,
    fallback: dict[str, str] | None,
) -> dict[str, str] | None:
    if not items:
        return fallback
    last_item = items[-1]
    timestamp = timestamp_getter(last_item)
    if timestamp is None:
        return fallback
    return {"at": _isoformat(timestamp), "id": str(id_getter(last_item))}


def _isoformat(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


def _isoformat_or_none(value: datetime | None) -> str | None:
    return None if value is None else _isoformat(value)


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _aware_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _origin_allowed(origin: str | None, request_url: str) -> bool:
    if origin is None:
        return False
    origin_url = urlparse(origin)
    request_parsed = urlparse(request_url)
    if origin_url.hostname is None or request_parsed.hostname is None:
        return False
    return origin_url.hostname == request_parsed.hostname


def _websocket_close_code(status_code: int) -> int:
    if status_code == status.HTTP_401_UNAUTHORIZED:
        return 4401
    if status_code == status.HTTP_404_NOT_FOUND:
        return 4404
    return 4403
