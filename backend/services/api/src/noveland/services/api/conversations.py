from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from noveland.adapters import ProviderProfileService
from noveland.adapters.models import ProviderProfile
from noveland.agents.models import Agent
from noveland.auth import AuthRole
from noveland.conversations import (
    ConversationErrorPolicy,
    ConversationMemoryConfig,
    ConversationMode,
    ConversationParticipantDefinition,
    ConversationParticipantRecord,
    ConversationPolicyConfig,
    ConversationScopeType,
    ConversationSeed,
    ConversationService,
    ConversationSessionCreate,
    ConversationSessionRecord,
    ConversationSessionStatus,
    ConversationSessionUpdate,
    ConversationSpeakerPolicyMode,
    ConversationSpeakerPreview,
    ConversationTurnRecord,
    ConversationWriterConfig,
)
from noveland.conversations.errors import ConversationStateError, ConversationValidationError
from noveland.core.settings import load_settings
from noveland.narrative import (
    ConversationNarrativeArtifactSet,
    ConversationNarrativeGenerate,
    ConversationNarrativePromptPreview,
    ConversationNarrativeWriterService,
    NarrativeArtifactRecord,
    NarrativeArtifactService,
    NarrativeArtifactWithPublication,
    NarrativeGenerationMode,
)
from noveland.observability import (
    DiagnosticComponent,
    DiagnosticSeverity,
    RuntimeDiagnosticRecord,
)
from noveland.observability.models import RuntimeDiagnosticEvent
from noveland.plugins.builtins import get_builtin_plugin_registry
from noveland.plugins.categories import PluginCategory
from noveland.plugins.constants import BUILTIN_DEFAULT_NARRATIVE_WRITER
from noveland.plugins.errors import PluginConfigValidationError, PluginNotFoundError
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
from sqlalchemy import select
from sqlalchemy.orm import Session

router = APIRouter(prefix="/worlds/{world_id}/conversations", tags=["conversations"])


class _RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConversationPolicyRequest(_RequestModel):
    error_policy: Literal[
        "fail_session",
        "skip_turn",
        "retry_once_then_fail",
        "retry_once_then_skip",
    ]
    max_consecutive_failed_turns: int = Field(ge=1, le=20)
    loop_guard_window: int = Field(ge=2, le=20)
    repeat_output_threshold: int = Field(ge=2, le=20)
    speaker_policy: Literal["round_robin", "least_recent", "priority_order", "manual_next"] = (
        "round_robin"
    )
    manual_next_agent_id: uuid.UUID | None = None
    participant_repeat_cooldown: int = Field(default=0, ge=0, le=20)
    min_enabled_participants: int = Field(default=1, ge=1, le=20)
    max_turn_budget: int | None = Field(default=None, ge=1, le=200)

    @model_validator(mode="after")
    def validate_thresholds(self) -> ConversationPolicyRequest:
        if self.repeat_output_threshold > self.loop_guard_window:
            raise ValueError("repeat_output_threshold cannot exceed loop_guard_window")
        return self


class ConversationCreateRequest(_RequestModel):
    session_key: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,78}[a-z0-9]$", max_length=80)
    worldline_id: uuid.UUID | None = None
    title: str = Field(min_length=1, max_length=160)
    scope_type: Literal["scene", "world"]
    mode: Literal["manual_chain", "auto_dialogue"]
    scene_id: uuid.UUID | None = None
    objective: str = Field(default="", max_length=8_000)
    opening_prompt: str = Field(default="", max_length=12_000)
    max_turns: int = Field(default=12, ge=1, le=200)
    policy: ConversationPolicyRequest
    writer_config: ConversationWriterConfigRequest
    memory_config: ConversationMemoryConfigRequest = Field(
        default_factory=lambda: ConversationMemoryConfigRequest(),
    )
    group_context: dict[str, Any] = Field(default_factory=dict)

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
    policy: ConversationPolicyRequest | None = None
    writer_config: ConversationWriterConfigRequest | None = None
    memory_config: ConversationMemoryConfigRequest | None = None
    group_context: dict[str, Any] | None = None


class ConversationParticipantRequest(_RequestModel):
    agent_id: uuid.UUID
    turn_order: int = Field(ge=0, le=10_000)
    is_enabled: bool = True


class ConversationSeedRequest(_RequestModel):
    input_text: str = Field(min_length=1, max_length=12_000)


class ConversationWriterConfigRequest(_RequestModel):
    provider_profile_id: uuid.UUID | None = None
    writer_plugin_identifier: str = Field(
        default=BUILTIN_DEFAULT_NARRATIVE_WRITER,
        min_length=1,
        max_length=120,
    )
    writer_plugin_config: dict[str, Any] = Field(default_factory=dict)
    auto_generate_on_complete: bool = False
    generate_summary: bool = True
    generate_chapter: bool = True
    style_guide: str = Field(default="", max_length=4_000)
    target_length: Literal["brief", "standard", "expanded"] = "standard"
    source_constraints: str = Field(default="", max_length=4_000)
    include_prompt_preview: bool = True


class ConversationMemoryConfigRequest(_RequestModel):
    write_turn_memory: bool = True
    retrieve_memory: bool = True
    max_context_items: int = Field(default=5, ge=1, le=20)
    query_window: int = Field(default=8, ge=1, le=50)
    include_recent_turns: bool = True
    include_agent_observations: bool = True
    memory_query_strategy: Literal["prompt", "objective", "transcript"] = "prompt"


class ConversationNarrativeGenerateRequest(_RequestModel):
    artifact_set: Literal["summary_and_chapter", "summary_only", "chapter_only"] = (
        "summary_and_chapter"
    )
    provider_profile_id: uuid.UUID | None = None


class ConversationPolicyResponse(BaseModel):
    error_policy: str
    max_consecutive_failed_turns: int
    loop_guard_window: int
    repeat_output_threshold: int
    speaker_policy: str
    manual_next_agent_id: uuid.UUID | None
    participant_repeat_cooldown: int
    min_enabled_participants: int
    max_turn_budget: int | None


class ConversationSpeakerCandidateResponse(BaseModel):
    agent_id: uuid.UUID
    display_name: str
    turn_order: int
    is_enabled: bool
    score: float
    reasons: list[str]
    last_spoke_turn_index: int | None


class ConversationSpeakerPreviewResponse(BaseModel):
    session_id: uuid.UUID
    policy_mode: str
    selected_agent_id: uuid.UUID | None
    selected_reason: str
    candidates: list[ConversationSpeakerCandidateResponse]


class ConversationWriterConfigResponse(BaseModel):
    provider_profile_id: uuid.UUID | None
    writer_plugin_identifier: str
    writer_plugin_config: dict[str, Any]
    auto_generate_on_complete: bool
    generate_summary: bool
    generate_chapter: bool
    style_guide: str
    target_length: str
    source_constraints: str
    include_prompt_preview: bool


class ConversationNarrativePromptPreviewResponse(BaseModel):
    world_id: uuid.UUID
    conversation_id: uuid.UUID
    artifact_set: str
    provider_profile_id: uuid.UUID
    provider_profile_key: str
    writer_plugin_identifier: str
    prompt_text: str
    source_turn_count: int
    existing_artifact_count: int
    warnings: list[str]
    living_world_context: dict[str, Any] = Field(default_factory=dict)


class ConversationMemoryConfigResponse(BaseModel):
    write_turn_memory: bool
    retrieve_memory: bool
    max_context_items: int
    query_window: int
    include_recent_turns: bool
    include_agent_observations: bool
    memory_query_strategy: str


class ConversationMemorySummaryResponse(BaseModel):
    retrieve_memory: bool
    write_turn_memory: bool
    max_context_items: int
    query_window: int
    include_recent_turns: bool
    include_agent_observations: bool
    memory_query_strategy: str
    latest_backend: str | None
    latest_hit_count: int
    latest_retrieval_enabled: bool
    latest_write_enabled: bool
    recent_memory_diagnostics: list[ConversationDiagnosticResponse]


class ConversationSessionResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    worldline_id: uuid.UUID | None
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
    policy: ConversationPolicyResponse
    writer_config: ConversationWriterConfigResponse
    memory_config: ConversationMemoryConfigResponse
    group_context: dict[str, Any]
    terminal_reason: str | None
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


class ConversationDiagnosticResponse(BaseModel):
    id: uuid.UUID
    severity: str
    component: str
    event_type: str
    message: str
    details: dict[str, Any]
    occurred_at: str
    world_id: uuid.UUID | None
    agent_id: uuid.UUID | None
    run_id: uuid.UUID | None
    provider_profile_id: uuid.UUID | None
    created_at: str


class ConversationDiagnosticsSummaryResponse(BaseModel):
    session_status: str
    terminal_reason: str | None
    last_turn_status: str | None
    last_turn_error: str | None
    provider_diagnostic_count: int
    memory_diagnostic_count: int
    recent_diagnostics: list[ConversationDiagnosticResponse]
    operator_message: str


class ConversationNarrativeArtifactResponse(BaseModel):
    id: uuid.UUID
    world_id: uuid.UUID
    agent_id: uuid.UUID | None
    source_run_id: uuid.UUID | None
    source_conversation_id: uuid.UUID | None
    title: str
    content: str
    artifact_kind: str
    metadata: dict[str, Any]
    created_at: str


class ConversationAdvanceResponse(BaseModel):
    session: ConversationSessionResponse
    turn: ConversationTurnResponse


@router.get("", response_model=list[ConversationSessionResponse])
def list_conversations(
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[ConversationSessionResponse]:
    _world_or_404(db_session, context.world_id)
    can_manage = context.is_platform_admin or context.role == AuthRole.WORLD_ADMIN.value
    return [
        _session_response(session, include_admin_fields=can_manage)
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
    _validate_writer_config_binding(db_session, conversation_create.writer_config)
    try:
        writer_config = _writer_config_with_group_context(
            conversation_create.writer_config,
            conversation_create.group_context,
        )
        session = ConversationService(db_session).create_session(
            ConversationSessionCreate(
                world_id=context.world_id,
                worldline_id=conversation_create.worldline_id,
                scene_id=conversation_create.scene_id,
                session_key=conversation_create.session_key,
                title=conversation_create.title,
                scope_type=ConversationScopeType(conversation_create.scope_type),
                mode=ConversationMode(conversation_create.mode),
                objective=conversation_create.objective,
                opening_prompt=conversation_create.opening_prompt,
                max_turns=conversation_create.max_turns,
                policy=_policy_contract(conversation_create.policy),
                writer_config=writer_config,
                memory_config=_memory_config_contract(conversation_create.memory_config),
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
    can_manage = context.is_platform_admin or context.role == AuthRole.WORLD_ADMIN.value
    return _session_response(session, include_admin_fields=can_manage)


@router.patch("/{conversation_id}", response_model=ConversationSessionResponse)
def update_conversation(
    conversation_id: uuid.UUID,
    conversation_update: ConversationUpdateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ConversationSessionResponse:
    require_csrf(request)
    if conversation_update.writer_config is not None:
        _validate_writer_config_binding(db_session, conversation_update.writer_config)
    try:
        writer_config = None
        if conversation_update.writer_config is not None:
            writer_config = _writer_config_with_group_context(
                conversation_update.writer_config,
                conversation_update.group_context or {},
            )
        session = ConversationService(db_session).update_session(
            context.world_id,
            conversation_id,
            ConversationSessionUpdate(
                title=conversation_update.title,
                objective=conversation_update.objective,
                opening_prompt=conversation_update.opening_prompt,
                max_turns=conversation_update.max_turns,
                policy=None
                if conversation_update.policy is None
                else _policy_contract(conversation_update.policy),
                writer_config=writer_config,
                memory_config=None
                if conversation_update.memory_config is None
                else _memory_config_contract(conversation_update.memory_config),
            ),
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
    except ConversationStateError as exc:
        raise _conflict(str(exc)) from exc
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
    can_manage = context.is_platform_admin or context.role == AuthRole.WORLD_ADMIN.value
    return [_turn_response(turn, include_admin_fields=can_manage) for turn in turns]


@router.get(
    "/{conversation_id}/speaker-preview",
    response_model=ConversationSpeakerPreviewResponse,
)
def preview_conversation_speaker(
    conversation_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ConversationSpeakerPreviewResponse:
    try:
        preview = ConversationService(db_session).preview_next_speaker(
            context.world_id,
            conversation_id,
        )
    except LookupError as exc:
        raise _not_found() from exc
    return _speaker_preview_response(preview)


@router.get(
    "/{conversation_id}/diagnostics",
    response_model=list[ConversationDiagnosticResponse],
)
def list_conversation_diagnostics(
    conversation_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[ConversationDiagnosticResponse]:
    try:
        records = ConversationService(db_session).list_diagnostics(
            context.world_id,
            conversation_id,
            limit=limit,
        )
    except LookupError as exc:
        raise _not_found() from exc
    return [_diagnostic_response(record) for record in records]


@router.get(
    "/{conversation_id}/diagnostics/summary",
    response_model=ConversationDiagnosticsSummaryResponse,
)
def get_conversation_diagnostics_summary(
    conversation_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ConversationDiagnosticsSummaryResponse:
    service = ConversationService(db_session)
    try:
        session = service.get_session(context.world_id, conversation_id)
        turns = service.list_turns(context.world_id, conversation_id)
        diagnostics = service.list_diagnostics(context.world_id, conversation_id, limit=20)
    except LookupError as exc:
        raise _not_found() from exc
    last_turn = turns[-1] if turns else None
    provider_count = sum(
        1
        for diagnostic in diagnostics
        if diagnostic.component.value == "provider" or "provider" in diagnostic.event_type
    )
    memory_count = sum(
        1
        for diagnostic in diagnostics
        if diagnostic.component.value == "memory" or "memory" in diagnostic.event_type
    )
    return ConversationDiagnosticsSummaryResponse(
        session_status=session.status.value,
        terminal_reason=None if session.terminal_reason is None else session.terminal_reason.value,
        last_turn_status=None if last_turn is None else last_turn.status.value,
        last_turn_error=None if last_turn is None else last_turn.error_text,
        provider_diagnostic_count=provider_count,
        memory_diagnostic_count=memory_count,
        recent_diagnostics=[_diagnostic_response(record) for record in diagnostics[:5]],
        operator_message=_conversation_operator_message(
            session,
            last_turn,
            diagnostics,
            provider_count,
            memory_count,
        ),
    )


@router.get(
    "/{conversation_id}/memory/summary",
    response_model=ConversationMemorySummaryResponse,
)
def get_conversation_memory_summary(
    conversation_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ConversationMemorySummaryResponse:
    service = ConversationService(db_session)
    try:
        session = service.get_session(context.world_id, conversation_id)
        turns = service.list_turns(context.world_id, conversation_id)
        diagnostics = service.list_diagnostics(context.world_id, conversation_id, limit=20)
    except LookupError as exc:
        raise _not_found() from exc
    run_ids = {turn.run_id for turn in turns if turn.run_id is not None}
    runtime_records = (
        [
            _runtime_diagnostic_record(record)
            for record in db_session.scalars(
                select(RuntimeDiagnosticEvent)
                .where(
                    RuntimeDiagnosticEvent.world_id == context.world_id,
                    RuntimeDiagnosticEvent.run_id.in_(run_ids),
                )
                .order_by(RuntimeDiagnosticEvent.occurred_at.desc())
                .limit(50),
            ).all()
        ]
        if run_ids
        else []
    )
    run_diagnostics = [
        record
        for record in [*runtime_records, *diagnostics]
        if record.run_id in run_ids
        and (
            "memory" in record.event_type
            or "memory_backend" in record.details
            or "memory_hit_count" in record.details
        )
    ]
    latest = run_diagnostics[0] if run_diagnostics else None
    latest_details = latest.details if latest is not None else {}
    return ConversationMemorySummaryResponse(
        retrieve_memory=session.memory_config.retrieve_memory,
        write_turn_memory=session.memory_config.write_turn_memory,
        max_context_items=session.memory_config.max_context_items,
        query_window=session.memory_config.query_window,
        include_recent_turns=session.memory_config.include_recent_turns,
        include_agent_observations=session.memory_config.include_agent_observations,
        memory_query_strategy=session.memory_config.memory_query_strategy,
        latest_backend=_string_or_none(latest_details.get("memory_backend")),
        latest_hit_count=_int_or_zero(latest_details.get("memory_hit_count")),
        latest_retrieval_enabled=bool(latest_details.get("memory_retrieval_enabled", False)),
        latest_write_enabled=session.memory_config.write_turn_memory,
        recent_memory_diagnostics=[
            _diagnostic_response(record) for record in run_diagnostics[:5]
        ],
    )


@router.get(
    "/{conversation_id}/narrative",
    response_model=list[ConversationNarrativeArtifactResponse],
)
def list_conversation_narrative_artifacts(
    conversation_id: uuid.UUID,
    context: Annotated[WorldAccessContext, Depends(get_world_member_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[ConversationNarrativeArtifactResponse]:
    can_manage = context.is_platform_admin or context.role == AuthRole.WORLD_ADMIN.value
    try:
        if can_manage:
            artifacts: Sequence[NarrativeArtifactRecord | NarrativeArtifactWithPublication] = (
                ConversationNarrativeWriterService(
                    db_session,
                    ProviderProfileService(db_session, load_settings()),
                ).list_conversation_artifacts(context.world_id, conversation_id)
            )
        else:
            ConversationService(db_session).get_session(context.world_id, conversation_id)
            artifacts = NarrativeArtifactService(db_session).list_artifacts_with_publications(
                context.world_id,
                source_conversation_id=conversation_id,
                limit=50,
                published_only=True,
            )
    except LookupError as exc:
        raise _not_found() from exc
    return [
        _narrative_artifact_response(artifact, include_admin_fields=can_manage)
        for artifact in artifacts
    ]


@router.post(
    "/{conversation_id}/narrative/generate",
    response_model=list[ConversationNarrativeArtifactResponse],
)
def generate_conversation_narrative_artifacts(
    conversation_id: uuid.UUID,
    generate_request: ConversationNarrativeGenerateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[ConversationNarrativeArtifactResponse]:
    require_csrf(request)
    try:
        artifacts = ConversationNarrativeWriterService(
            db_session,
            ProviderProfileService(db_session, load_settings()),
        ).generate_for_conversation(
            ConversationNarrativeGenerate(
                world_id=context.world_id,
                conversation_id=conversation_id,
                artifact_set=ConversationNarrativeArtifactSet(generate_request.artifact_set),
                provider_profile_id=generate_request.provider_profile_id,
                generation_mode=NarrativeGenerationMode.MANUAL,
            ),
        )
    except LookupError as exc:
        raise _not_found() from exc
    except (ConversationValidationError, ConversationStateError, ValueError) as exc:
        raise _http_error_for_conversation_error(str(exc)) from exc
    return [_narrative_artifact_response(artifact) for artifact in artifacts]


@router.post(
    "/{conversation_id}/narrative/preview",
    response_model=ConversationNarrativePromptPreviewResponse,
)
def preview_conversation_narrative_prompt(
    conversation_id: uuid.UUID,
    generate_request: ConversationNarrativeGenerateRequest,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ConversationNarrativePromptPreviewResponse:
    require_csrf(request)
    try:
        preview = ConversationNarrativeWriterService(
            db_session,
            ProviderProfileService(db_session, load_settings()),
        ).preview_for_conversation(
            ConversationNarrativeGenerate(
                world_id=context.world_id,
                conversation_id=conversation_id,
                artifact_set=ConversationNarrativeArtifactSet(generate_request.artifact_set),
                provider_profile_id=generate_request.provider_profile_id,
                generation_mode=NarrativeGenerationMode.MANUAL,
            ),
        )
    except LookupError as exc:
        raise _not_found() from exc
    except (ConversationValidationError, ConversationStateError, ValueError) as exc:
        raise _http_error_for_conversation_error(str(exc)) from exc
    return _narrative_prompt_preview_response(preview)


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
        settings = load_settings()
        result = ConversationRuntimeOrchestrator(
            db_session,
            ProviderProfileService(db_session, settings),
            settings,
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


@router.post("/{conversation_id}/stop", response_model=ConversationSessionResponse)
def stop_conversation(
    conversation_id: uuid.UUID,
    request: Request,
    context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ConversationSessionResponse:
    require_csrf(request)
    try:
        session = ConversationService(db_session).stop_session(context.world_id, conversation_id)
    except LookupError as exc:
        raise _not_found() from exc
    except (ConversationValidationError, ConversationStateError) as exc:
        raise _http_error_for_conversation_error(str(exc)) from exc
    return _session_response(session)


def _policy_contract(policy: ConversationPolicyRequest) -> ConversationPolicyConfig:
    return ConversationPolicyConfig(
        error_policy=ConversationErrorPolicy(policy.error_policy),
        max_consecutive_failed_turns=policy.max_consecutive_failed_turns,
        loop_guard_window=policy.loop_guard_window,
        repeat_output_threshold=policy.repeat_output_threshold,
        speaker_policy=ConversationSpeakerPolicyMode(policy.speaker_policy),
        manual_next_agent_id=policy.manual_next_agent_id,
        participant_repeat_cooldown=policy.participant_repeat_cooldown,
        min_enabled_participants=policy.min_enabled_participants,
        max_turn_budget=policy.max_turn_budget,
    )


def _writer_config_contract(
    writer_config: ConversationWriterConfigRequest,
) -> ConversationWriterConfig:
    return ConversationWriterConfig(
        provider_profile_id=writer_config.provider_profile_id,
        writer_plugin_identifier=writer_config.writer_plugin_identifier,
        writer_plugin_config=writer_config.writer_plugin_config,
        auto_generate_on_complete=writer_config.auto_generate_on_complete,
        generate_summary=writer_config.generate_summary,
        generate_chapter=writer_config.generate_chapter,
        style_guide=writer_config.style_guide,
        target_length=writer_config.target_length,
        source_constraints=writer_config.source_constraints,
        include_prompt_preview=writer_config.include_prompt_preview,
    )


def _writer_config_with_group_context(
    writer_config: ConversationWriterConfigRequest,
    group_context: dict[str, Any],
) -> ConversationWriterConfig:
    contract = _writer_config_contract(writer_config)
    config = contract.model_dump(mode="json")
    if group_context:
        plugin_config = dict(config.get("writer_plugin_config") or {})
        plugin_config["group_context"] = group_context
        config["writer_plugin_config"] = plugin_config
    return ConversationWriterConfig(**config)


def _memory_config_contract(
    memory_config: ConversationMemoryConfigRequest,
) -> ConversationMemoryConfig:
    return ConversationMemoryConfig(
        write_turn_memory=memory_config.write_turn_memory,
        retrieve_memory=memory_config.retrieve_memory,
        max_context_items=memory_config.max_context_items,
        query_window=memory_config.query_window,
        include_recent_turns=memory_config.include_recent_turns,
        include_agent_observations=memory_config.include_agent_observations,
        memory_query_strategy=memory_config.memory_query_strategy,
    )


def _session_response(
    session: ConversationSessionRecord,
    *,
    include_admin_fields: bool = True,
) -> ConversationSessionResponse:
    return ConversationSessionResponse(
        id=session.id,
        world_id=session.world_id,
        worldline_id=session.worldline_id,
        scene_id=session.scene_id,
        session_key=session.session_key,
        title=session.title,
        scope_type=session.scope_type.value,
        mode=session.mode.value,
        status=session.status.value,
        objective=session.objective if include_admin_fields else "",
        opening_prompt=session.opening_prompt if include_admin_fields else "",
        max_turns=session.max_turns,
        next_turn_index=session.next_turn_index,
        policy=_session_policy_response(session, include_admin_fields=include_admin_fields),
        writer_config=_session_writer_config_response(
            session,
            include_admin_fields=include_admin_fields,
        ),
        memory_config=_session_memory_config_response(
            session,
            include_admin_fields=include_admin_fields,
        ),
        group_context=(
            _group_context_from_writer_config(session.writer_config)
            if include_admin_fields
            else {}
        ),
        terminal_reason=None if session.terminal_reason is None else session.terminal_reason.value,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
    )


def _session_policy_response(
    session: ConversationSessionRecord,
    *,
    include_admin_fields: bool,
) -> ConversationPolicyResponse:
    if not include_admin_fields:
        return ConversationPolicyResponse(
            error_policy="fail_session",
            max_consecutive_failed_turns=1,
            loop_guard_window=2,
            repeat_output_threshold=2,
            speaker_policy="round_robin",
            manual_next_agent_id=None,
            participant_repeat_cooldown=0,
            min_enabled_participants=1,
            max_turn_budget=None,
        )
    return ConversationPolicyResponse(
        error_policy=session.policy.error_policy.value,
        max_consecutive_failed_turns=session.policy.max_consecutive_failed_turns,
        loop_guard_window=session.policy.loop_guard_window,
        repeat_output_threshold=session.policy.repeat_output_threshold,
        speaker_policy=session.policy.speaker_policy.value,
        manual_next_agent_id=session.policy.manual_next_agent_id,
        participant_repeat_cooldown=session.policy.participant_repeat_cooldown,
        min_enabled_participants=session.policy.min_enabled_participants,
        max_turn_budget=session.policy.max_turn_budget,
    )


def _session_writer_config_response(
    session: ConversationSessionRecord,
    *,
    include_admin_fields: bool,
) -> ConversationWriterConfigResponse:
    if not include_admin_fields:
        return ConversationWriterConfigResponse(
            provider_profile_id=None,
            writer_plugin_identifier="",
            writer_plugin_config={},
            auto_generate_on_complete=False,
            generate_summary=False,
            generate_chapter=False,
            style_guide="",
            target_length="standard",
            source_constraints="",
            include_prompt_preview=False,
        )
    return ConversationWriterConfigResponse(
        provider_profile_id=session.writer_config.provider_profile_id,
        writer_plugin_identifier=session.writer_config.writer_plugin_identifier,
        writer_plugin_config=session.writer_config.writer_plugin_config,
        auto_generate_on_complete=session.writer_config.auto_generate_on_complete,
        generate_summary=session.writer_config.generate_summary,
        generate_chapter=session.writer_config.generate_chapter,
        style_guide=session.writer_config.style_guide,
        target_length=session.writer_config.target_length,
        source_constraints=session.writer_config.source_constraints,
        include_prompt_preview=session.writer_config.include_prompt_preview,
    )


def _session_memory_config_response(
    session: ConversationSessionRecord,
    *,
    include_admin_fields: bool,
) -> ConversationMemoryConfigResponse:
    if not include_admin_fields:
        return ConversationMemoryConfigResponse(
            write_turn_memory=False,
            retrieve_memory=False,
            max_context_items=0,
            query_window=0,
            include_recent_turns=False,
            include_agent_observations=False,
            memory_query_strategy="",
        )
    return ConversationMemoryConfigResponse(
        write_turn_memory=session.memory_config.write_turn_memory,
        retrieve_memory=session.memory_config.retrieve_memory,
        max_context_items=session.memory_config.max_context_items,
        query_window=session.memory_config.query_window,
        include_recent_turns=session.memory_config.include_recent_turns,
        include_agent_observations=session.memory_config.include_agent_observations,
        memory_query_strategy=session.memory_config.memory_query_strategy,
    )


def _group_context_from_writer_config(writer_config: ConversationWriterConfig) -> dict[str, Any]:
    raw = writer_config.writer_plugin_config.get("group_context")
    return raw if isinstance(raw, dict) else {}


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


def _speaker_preview_response(
    preview: ConversationSpeakerPreview,
) -> ConversationSpeakerPreviewResponse:
    return ConversationSpeakerPreviewResponse(
        session_id=preview.session_id,
        policy_mode=preview.policy_mode.value,
        selected_agent_id=preview.selected_agent_id,
        selected_reason=preview.selected_reason,
        candidates=[
            ConversationSpeakerCandidateResponse(
                agent_id=candidate.agent_id,
                display_name=candidate.display_name,
                turn_order=candidate.turn_order,
                is_enabled=candidate.is_enabled,
                score=candidate.score,
                reasons=candidate.reasons,
                last_spoke_turn_index=candidate.last_spoke_turn_index,
            )
            for candidate in preview.candidates
        ],
    )


def _turn_response(
    turn: ConversationTurnRecord,
    *,
    include_admin_fields: bool = True,
) -> ConversationTurnResponse:
    return ConversationTurnResponse(
        id=turn.id,
        session_id=turn.session_id,
        turn_index=turn.turn_index,
        speaker_kind=turn.speaker_kind.value,
        speaker_agent_id=turn.speaker_agent_id,
        input_text=turn.input_text,
        output_text=turn.output_text,
        status=turn.status.value,
        run_id=turn.run_id if include_admin_fields else None,
        error_text=turn.error_text if include_admin_fields else None,
        created_at=turn.created_at.isoformat(),
        updated_at=turn.updated_at.isoformat(),
    )


def _diagnostic_response(record: RuntimeDiagnosticRecord) -> ConversationDiagnosticResponse:
    return ConversationDiagnosticResponse(
        id=record.id,
        severity=record.severity.value,
        component=record.component.value,
        event_type=record.event_type,
        message=record.message,
        details=record.details,
        occurred_at=record.occurred_at.isoformat(),
        world_id=record.world_id,
        agent_id=record.agent_id,
        run_id=record.run_id,
        provider_profile_id=record.provider_profile_id,
        created_at=record.created_at.isoformat(),
    )


def _runtime_diagnostic_record(model: RuntimeDiagnosticEvent) -> RuntimeDiagnosticRecord:
    return RuntimeDiagnosticRecord(
        id=model.id,
        severity=DiagnosticSeverity(model.severity),
        component=DiagnosticComponent(model.component),
        event_type=model.event_type,
        message=model.message,
        details=model.details,
        occurred_at=model.occurred_at,
        world_id=model.world_id,
        agent_id=model.agent_id,
        run_id=model.run_id,
        provider_profile_id=model.provider_profile_id,
        created_at=model.created_at,
    )


def _conversation_operator_message(
    session: ConversationSessionRecord,
    last_turn: ConversationTurnRecord | None,
    diagnostics: list[RuntimeDiagnosticRecord],
    provider_count: int,
    memory_count: int,
) -> str:
    if session.terminal_reason is not None:
        return f"Conversation ended because {session.terminal_reason.value}."
    if last_turn is not None and last_turn.status.value == "failed":
        return last_turn.error_text or "Last conversation turn failed."
    if provider_count > 0:
        return "Recent provider diagnostics may explain degraded conversation behavior."
    if memory_count > 0:
        return "Recent memory diagnostics may explain missing or failed memory context."
    if diagnostics:
        return diagnostics[0].message
    return "No blocking conversation diagnostics are currently recorded."


def _string_or_none(value: object) -> str | None:
    return None if value is None else str(value)


def _int_or_zero(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return 0


def _narrative_artifact_response(
    artifact: NarrativeArtifactRecord | NarrativeArtifactWithPublication,
    *,
    include_admin_fields: bool = True,
) -> ConversationNarrativeArtifactResponse:
    if isinstance(artifact, NarrativeArtifactWithPublication):
        artifact_record = artifact.artifact
    else:
        artifact_record = artifact
    return ConversationNarrativeArtifactResponse(
        id=artifact_record.id,
        world_id=artifact_record.world_id,
        agent_id=artifact_record.agent_id,
        source_run_id=artifact_record.source_run_id if include_admin_fields else None,
        source_conversation_id=artifact_record.source_conversation_id,
        title=artifact_record.title,
        content=artifact_record.content,
        artifact_kind=artifact_record.artifact_kind.value,
        metadata=artifact_record.metadata if include_admin_fields else {},
        created_at=artifact_record.created_at.isoformat(),
    )


def _narrative_prompt_preview_response(
    preview: ConversationNarrativePromptPreview,
) -> ConversationNarrativePromptPreviewResponse:
    return ConversationNarrativePromptPreviewResponse(
        world_id=preview.world_id,
        conversation_id=preview.conversation_id,
        artifact_set=preview.artifact_set.value,
        provider_profile_id=preview.provider_profile_id,
        provider_profile_key=preview.provider_profile_key,
        writer_plugin_identifier=preview.writer_plugin_identifier,
        prompt_text=preview.prompt_text,
        source_turn_count=preview.source_turn_count,
        existing_artifact_count=preview.existing_artifact_count,
        warnings=preview.warnings,
        living_world_context=preview.living_world_context,
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
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    if (
        "already exists" in detail
        or "cannot" in detail
        or "no longer" in detail
        or "already" in detail
        or "paused" in detail
        or "running" in detail
        or "active" in detail
    ):
        status_code = status.HTTP_409_CONFLICT
    return HTTPException(status_code=status_code, detail=detail)


def _validate_writer_config_binding(
    db_session: Session,
    writer_config: ConversationWriterConfigRequest,
) -> None:
    if writer_config.provider_profile_id is not None:
        profile = db_session.get(ProviderProfile, writer_config.provider_profile_id)
        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Provider profile not found",
            )
    registry = get_builtin_plugin_registry()
    try:
        definition = registry.get(writer_config.writer_plugin_identifier)
    except PluginNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if definition.manifest.category is not PluginCategory.NARRATIVE_WRITER:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Writer binding must use a narrative_writer plugin",
        )
    try:
        registry.validate_config(
            writer_config.writer_plugin_identifier,
            writer_config.writer_plugin_config,
        )
    except PluginConfigValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
