from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from noveland.auth import AuthenticatedSubject
from noveland.authoring.contracts import (
    AuthoringApplyRequest,
    AuthoringApplyResult,
    AuthoringAssetMatchRequest,
    AuthoringAssetMatchResult,
    AuthoringCharacterExtractRequest,
    AuthoringCharacterExtractResult,
    AuthoringCharacterMemoryDistillRequest,
    AuthoringCharacterMemoryDistillResult,
    AuthoringConflictReviewRequest,
    AuthoringConflictReviewResult,
    AuthoringImportRunCreate,
    AuthoringImportRunKind,
    AuthoringImportRunRead,
    AuthoringLoreExtractRequest,
    AuthoringLoreExtractResult,
    AuthoringMemoryMigrateRequest,
    AuthoringMemoryMigrateResult,
    AuthoringPreviewRequest,
    AuthoringPreviewResult,
    AuthoringProposalCreate,
    AuthoringProposalDraft,
    AuthoringProposalRead,
    AuthoringReviewDecisionCreate,
    AuthoringReviewDecisionRead,
    AuthoringScriptParseRequest,
    AuthoringScriptParseResult,
    AuthoringSourceAssetCreate,
    AuthoringSourceAssetKind,
    AuthoringSourceAssetRead,
    AuthoringSourceBatchCreate,
    AuthoringSourceBatchRead,
    AuthoringSourceBatchStatus,
    AuthoringSourceFragmentCreate,
    AuthoringSourceFragmentKind,
    AuthoringSourceFragmentRead,
    AuthoringSourceVisibility,
    BetaContentRepairRequest,
    BetaContentRepairResult,
    DemoWorldAssemblyRequest,
    DemoWorldAssemblyResult,
    GalgameSourceIntakeApplyRequest,
    GalgameSourceIntakeApplyResult,
    GalgameSourceIntakePreviewRequest,
    GalgameSourceIntakePreviewResult,
)
from noveland.authoring.galgame_intake import GalgameSourceIntakeService
from noveland.authoring.service import (
    AuthoringNotFoundError,
    AuthoringService,
    AuthoringValidationError,
)
from noveland.beta_feedback import (
    BetaFeedbackNotFoundError,
    BetaFeedbackRepairProposalRef,
    BetaFeedbackService,
    BetaFeedbackValidationError,
)
from noveland.core.settings import load_settings
from noveland.media.storage import LocalMediaObjectStorage
from noveland.services.api.csrf import require_csrf
from noveland.services.api.dependencies import (
    WorldAccessContext,
    get_current_subject,
    get_db_session,
    get_world_admin_context,
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

router = APIRouter(prefix="/worlds/{world_id}/authoring", tags=["authoring"])


def _authoring_media_storage() -> LocalMediaObjectStorage:
    return LocalMediaObjectStorage(load_settings().object_storage_root / "media")


class AuthoringSourceBatchCreateRequest(BaseModel):
    worldline_id: uuid.UUID
    batch_key: str = Field(min_length=1, max_length=120)
    display_name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    source_kind: AuthoringSourceAssetKind = AuthoringSourceAssetKind.OTHER
    status: AuthoringSourceBatchStatus = AuthoringSourceBatchStatus.ACTIVE
    visibility: AuthoringSourceVisibility = AuthoringSourceVisibility.PRIVATE
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class AuthoringSourceAssetCreateRequest(BaseModel):
    worldline_id: uuid.UUID
    media_asset_id: uuid.UUID | None = None
    source_asset_kind: AuthoringSourceAssetKind = AuthoringSourceAssetKind.OTHER
    source_label: str = Field(min_length=1, max_length=160)
    source_ref: str | None = Field(default=None, max_length=240)
    status: AuthoringSourceBatchStatus = AuthoringSourceBatchStatus.ACTIVE
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class AuthoringSourceFragmentCreateRequest(BaseModel):
    worldline_id: uuid.UUID
    fragment_key: str = Field(min_length=1, max_length=120)
    fragment_kind: AuthoringSourceFragmentKind = AuthoringSourceFragmentKind.OTHER
    sequence: int = Field(ge=0)
    excerpt_text: str | None = Field(default=None, max_length=4000)
    locator_json: dict[str, Any] = Field(default_factory=dict)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class AuthoringImportRunCreateRequest(BaseModel):
    worldline_id: uuid.UUID
    source_batch_id: uuid.UUID | None = None
    run_kind: AuthoringImportRunKind = AuthoringImportRunKind.PREVIEW
    summary_json: dict[str, Any] = Field(default_factory=dict)


class GalgameSourceIntakePreviewBody(BaseModel):
    worldline_id: uuid.UUID
    source_directory: str = Field(min_length=1, max_length=1000)
    batch_key: str = Field(min_length=1, max_length=120)
    display_name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    max_text_fragment_chars: int = Field(default=2000, ge=200, le=4000)
    max_files: int = Field(default=500, ge=1, le=5000)


class GalgameSourceIntakeApplyBody(GalgameSourceIntakePreviewBody):
    confirm_already_unpacked_user_provided: bool = False


class DemoWorldAssemblyBody(BaseModel):
    worldline_id: uuid.UUID
    agent_ids: list[uuid.UUID] = Field(min_length=2, max_length=3)
    dialogue_proposal_ids: list[uuid.UUID] = Field(min_length=1)
    persona_proposal_ids: list[uuid.UUID] = Field(default_factory=list)
    memory_proposal_ids: list[uuid.UUID] = Field(default_factory=list)
    visual_proposal_ids: list[uuid.UUID] = Field(default_factory=list)
    voice_proposal_ids: list[uuid.UUID] = Field(default_factory=list)
    visual_profile_proposal_ids: list[uuid.UUID] = Field(default_factory=list)
    visual_generation_profile_ids: list[uuid.UUID] = Field(default_factory=list)
    title: str = Field(default="Self-use MVP Demo World", min_length=1, max_length=160)
    session_key: str | None = Field(default=None, min_length=3, max_length=80)
    opening_prompt: str = Field(default="Begin the demo world conversation.", max_length=4000)
    objective: str = Field(default="Play a source-grounded self-use demo world.", max_length=4000)
    max_turns: int = Field(default=48, ge=2, le=200)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


@router.post(
    "/galgame-source-intake/preview",
    response_model=GalgameSourceIntakePreviewResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def preview_galgame_source_intake(
    world_id: uuid.UUID,
    request: GalgameSourceIntakePreviewBody,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> GalgameSourceIntakePreviewResult:
    try:
        return GalgameSourceIntakeService(db_session).preview(
            GalgameSourceIntakePreviewRequest(world_id=world_id, **request.model_dump())
        )
    except (AuthoringValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/galgame-source-intake/apply",
    response_model=GalgameSourceIntakeApplyResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def apply_galgame_source_intake(
    world_id: uuid.UUID,
    request: GalgameSourceIntakeApplyBody,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
    storage: Annotated[LocalMediaObjectStorage, Depends(_authoring_media_storage)],
) -> GalgameSourceIntakeApplyResult:
    try:
        return GalgameSourceIntakeService(db_session, storage).apply(
            GalgameSourceIntakeApplyRequest(world_id=world_id, **request.model_dump()),
            actor_ref=f"user:{subject.user_id}",
        )
    except (AuthoringValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.get("/source-batches", response_model=list[AuthoringSourceBatchRead])
def list_authoring_source_batches(
    world_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: Annotated[uuid.UUID, Query()],
) -> list[AuthoringSourceBatchRead]:
    try:
        return AuthoringService(db_session).list_source_batches(
            world_id,
            worldline_id=worldline_id,
        )
    except AuthoringValidationError as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/source-batches",
    response_model=AuthoringSourceBatchRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_authoring_source_batch(
    world_id: uuid.UUID,
    request: AuthoringSourceBatchCreateRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AuthoringSourceBatchRead:
    try:
        return AuthoringService(db_session).create_source_batch(
            AuthoringSourceBatchCreate(world_id=world_id, **request.model_dump()),
            actor_ref=f"user:{subject.user_id}",
        )
    except (AuthoringValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.get("/source-batches/{batch_id}", response_model=AuthoringSourceBatchRead)
def get_authoring_source_batch(
    world_id: uuid.UUID,
    batch_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AuthoringSourceBatchRead:
    try:
        return AuthoringService(db_session).get_source_batch(world_id, batch_id)
    except AuthoringNotFoundError as exc:
        raise _not_found() from exc


@router.post(
    "/source-batches/{batch_id}/assets",
    response_model=AuthoringSourceAssetRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def add_authoring_source_asset(
    world_id: uuid.UUID,
    batch_id: uuid.UUID,
    request: AuthoringSourceAssetCreateRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AuthoringSourceAssetRead:
    try:
        return AuthoringService(db_session).add_source_asset(
            AuthoringSourceAssetCreate(
                world_id=world_id,
                batch_id=batch_id,
                **request.model_dump(),
            )
        )
    except AuthoringNotFoundError as exc:
        raise _not_found() from exc
    except (AuthoringValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/source-assets/{source_asset_id}/fragments",
    response_model=AuthoringSourceFragmentRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def add_authoring_source_fragment(
    world_id: uuid.UUID,
    source_asset_id: uuid.UUID,
    request: AuthoringSourceFragmentCreateRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AuthoringSourceFragmentRead:
    try:
        return AuthoringService(db_session).add_source_fragment(
            AuthoringSourceFragmentCreate(
                world_id=world_id,
                source_asset_id=source_asset_id,
                **request.model_dump(),
            )
        )
    except AuthoringNotFoundError as exc:
        raise _not_found() from exc
    except (AuthoringValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.get("/import-runs", response_model=list[AuthoringImportRunRead])
def list_authoring_import_runs(
    world_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
    worldline_id: Annotated[uuid.UUID, Query()],
) -> list[AuthoringImportRunRead]:
    try:
        return AuthoringService(db_session).list_import_runs(world_id, worldline_id=worldline_id)
    except AuthoringValidationError as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/import-runs",
    response_model=AuthoringImportRunRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_authoring_import_run(
    world_id: uuid.UUID,
    request: AuthoringImportRunCreateRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AuthoringImportRunRead:
    try:
        return AuthoringService(db_session).create_import_run(
            AuthoringImportRunCreate(world_id=world_id, **request.model_dump()),
            actor_ref=f"user:{subject.user_id}",
        )
    except AuthoringNotFoundError as exc:
        raise _not_found() from exc
    except (AuthoringValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.get("/import-runs/{run_id}", response_model=AuthoringImportRunRead)
def get_authoring_import_run(
    world_id: uuid.UUID,
    run_id: uuid.UUID,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AuthoringImportRunRead:
    try:
        return AuthoringService(db_session).get_import_run(world_id, run_id)
    except AuthoringNotFoundError as exc:
        raise _not_found() from exc


@router.post(
    "/import-runs/{run_id}/proposals",
    response_model=AuthoringProposalRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_authoring_import_proposal(
    world_id: uuid.UUID,
    run_id: uuid.UUID,
    request: AuthoringProposalDraft,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AuthoringProposalRead:
    try:
        run = AuthoringService(db_session).get_import_run(world_id, run_id)
        return AuthoringService(db_session).create_proposal(
            AuthoringProposalCreate.from_draft(
                world_id=world_id,
                worldline_id=run.worldline_id,
                run_id=run_id,
                draft=request,
            )
        )
    except AuthoringNotFoundError as exc:
        raise _not_found() from exc
    except (AuthoringValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/import-runs/{run_id}/preview",
    response_model=AuthoringPreviewResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def preview_authoring_import_run(
    world_id: uuid.UUID,
    run_id: uuid.UUID,
    request: AuthoringPreviewRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AuthoringPreviewResult:
    try:
        return AuthoringService(db_session).preview(world_id, run_id, request)
    except AuthoringNotFoundError as exc:
        raise _not_found() from exc
    except (AuthoringValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/import-runs/{run_id}/parse-script",
    response_model=AuthoringScriptParseResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def parse_authoring_script(
    world_id: uuid.UUID,
    run_id: uuid.UUID,
    request: AuthoringScriptParseRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AuthoringScriptParseResult:
    try:
        return AuthoringService(db_session).parse_script(world_id, run_id, request)
    except AuthoringNotFoundError as exc:
        raise _not_found() from exc
    except (AuthoringValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/import-runs/{run_id}/extract-characters",
    response_model=AuthoringCharacterExtractResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def extract_authoring_characters(
    world_id: uuid.UUID,
    run_id: uuid.UUID,
    request: AuthoringCharacterExtractRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AuthoringCharacterExtractResult:
    try:
        return AuthoringService(db_session).extract_characters(world_id, run_id, request)
    except AuthoringNotFoundError as exc:
        raise _not_found() from exc
    except (AuthoringValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/import-runs/{run_id}/extract-lore",
    response_model=AuthoringLoreExtractResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def extract_authoring_lore(
    world_id: uuid.UUID,
    run_id: uuid.UUID,
    request: AuthoringLoreExtractRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AuthoringLoreExtractResult:
    try:
        return AuthoringService(db_session).extract_lore(world_id, run_id, request)
    except AuthoringNotFoundError as exc:
        raise _not_found() from exc
    except (AuthoringValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/import-runs/{run_id}/review-conflicts",
    response_model=AuthoringConflictReviewResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def review_authoring_conflicts(
    world_id: uuid.UUID,
    run_id: uuid.UUID,
    request: AuthoringConflictReviewRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AuthoringConflictReviewResult:
    try:
        return AuthoringService(db_session).review_conflicts(world_id, run_id, request)
    except AuthoringNotFoundError as exc:
        raise _not_found() from exc
    except (AuthoringValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/import-runs/{run_id}/migrate-memory",
    response_model=AuthoringMemoryMigrateResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def migrate_authoring_memory(
    world_id: uuid.UUID,
    run_id: uuid.UUID,
    request: AuthoringMemoryMigrateRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AuthoringMemoryMigrateResult:
    try:
        return AuthoringService(db_session).migrate_memory(world_id, run_id, request)
    except AuthoringNotFoundError as exc:
        raise _not_found() from exc
    except (AuthoringValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/import-runs/{run_id}/distill-character-memory",
    response_model=AuthoringCharacterMemoryDistillResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def distill_authoring_character_memory(
    world_id: uuid.UUID,
    run_id: uuid.UUID,
    request: AuthoringCharacterMemoryDistillRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AuthoringCharacterMemoryDistillResult:
    try:
        return AuthoringService(db_session).distill_character_memory(
            world_id,
            run_id,
            request,
            actor_ref=f"user:{subject.user_id}",
        )
    except AuthoringNotFoundError as exc:
        raise _not_found() from exc
    except (AuthoringValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/import-runs/{run_id}/match-assets",
    response_model=AuthoringAssetMatchResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def match_authoring_assets(
    world_id: uuid.UUID,
    run_id: uuid.UUID,
    request: AuthoringAssetMatchRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AuthoringAssetMatchResult:
    try:
        return AuthoringService(db_session).match_assets(world_id, run_id, request)
    except AuthoringNotFoundError as exc:
        raise _not_found() from exc
    except (AuthoringValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/import-runs/{run_id}/assemble-demo-world",
    response_model=DemoWorldAssemblyResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def assemble_authoring_demo_world(
    world_id: uuid.UUID,
    run_id: uuid.UUID,
    request: DemoWorldAssemblyBody,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> DemoWorldAssemblyResult:
    try:
        return AuthoringService(db_session).assemble_demo_world(
            world_id,
            run_id,
            DemoWorldAssemblyRequest(
                worldline_id=request.worldline_id,
                agent_ids=tuple(request.agent_ids),
                dialogue_proposal_ids=tuple(request.dialogue_proposal_ids),
                persona_proposal_ids=tuple(request.persona_proposal_ids),
                memory_proposal_ids=tuple(request.memory_proposal_ids),
                visual_proposal_ids=tuple(request.visual_proposal_ids),
                voice_proposal_ids=tuple(request.voice_proposal_ids),
                visual_profile_proposal_ids=tuple(request.visual_profile_proposal_ids),
                visual_generation_profile_ids=tuple(request.visual_generation_profile_ids),
                title=request.title,
                session_key=request.session_key,
                opening_prompt=request.opening_prompt,
                objective=request.objective,
                max_turns=request.max_turns,
                metadata_json=request.metadata_json,
            ),
        )
    except AuthoringNotFoundError as exc:
        raise _not_found() from exc
    except (AuthoringValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/beta-content-repairs",
    response_model=BetaContentRepairResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def create_beta_content_repairs(
    world_id: uuid.UUID,
    request: BetaContentRepairRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> BetaContentRepairResult:
    try:
        result = AuthoringService(db_session).create_beta_content_repairs(
            world_id,
            request,
            actor_ref=f"user:{subject.user_id}",
        )
        report_refs: dict[uuid.UUID, list[BetaFeedbackRepairProposalRef]] = {}
        for candidate, proposal in zip(request.candidates, result.proposals, strict=True):
            repair_ref = BetaFeedbackRepairProposalRef(
                proposal_id=proposal.id,
                proposal_kind=candidate.repair_kind.value,
                status=proposal.status.value,
                metadata={
                    "run_id": str(result.run.id),
                    "target_ref_kind": proposal.target_ref_kind,
                    "repair_kind": candidate.repair_kind.value,
                },
            )
            for report_id in candidate.feedback_report_ids:
                report_refs.setdefault(report_id, []).append(repair_ref)
        if report_refs:
            BetaFeedbackService(db_session).link_repair_proposals(
                world_id,
                request.worldline_id,
                {report_id: tuple(refs) for report_id, refs in report_refs.items()},
                actor_ref=f"user:{subject.user_id}",
            )
        return result
    except (AuthoringNotFoundError, BetaFeedbackNotFoundError) as exc:
        raise _not_found() from exc
    except (AuthoringValidationError, BetaFeedbackValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/import-runs/{run_id}/apply",
    response_model=AuthoringApplyResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def apply_authoring_import_run(
    world_id: uuid.UUID,
    run_id: uuid.UUID,
    request: AuthoringApplyRequest,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AuthoringApplyResult:
    try:
        return AuthoringService(db_session).apply(world_id, run_id, request)
    except AuthoringNotFoundError as exc:
        raise _not_found() from exc
    except (AuthoringValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


@router.post(
    "/proposals/{proposal_id}/review",
    response_model=AuthoringReviewDecisionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
def review_authoring_import_proposal(
    world_id: uuid.UUID,
    proposal_id: uuid.UUID,
    request: AuthoringReviewDecisionCreate,
    _context: Annotated[WorldAccessContext, Depends(get_world_admin_context)],
    subject: Annotated[AuthenticatedSubject, Depends(get_current_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> AuthoringReviewDecisionRead:
    try:
        return AuthoringService(db_session).review_proposal(
            world_id,
            proposal_id,
            request,
            actor_ref=f"user:{subject.user_id}",
        )
    except AuthoringNotFoundError as exc:
        raise _not_found() from exc
    except (AuthoringValidationError, ValueError) as exc:
        raise _unprocessable(str(exc)) from exc


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


def _unprocessable(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)
