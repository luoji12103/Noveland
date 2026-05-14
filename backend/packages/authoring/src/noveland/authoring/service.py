from __future__ import annotations

import uuid
from typing import Any

from noveland.authoring.character_extractor import (
    ExtractedCharacterCandidate,
    dedupe_candidates,
    extract_dialogue_speaker_candidate,
)
from noveland.authoring.character_extractor import (
    extract_fragment as extract_character_fragment,
)
from noveland.authoring.contracts import (
    AuthoringApplyRequest,
    AuthoringApplyResult,
    AuthoringCharacterExtractRequest,
    AuthoringCharacterExtractResult,
    AuthoringImportRunCreate,
    AuthoringImportRunKind,
    AuthoringImportRunRead,
    AuthoringImportRunStatus,
    AuthoringPreviewRequest,
    AuthoringPreviewResult,
    AuthoringProposalCreate,
    AuthoringProposalKind,
    AuthoringProposalRead,
    AuthoringProposalStatus,
    AuthoringReviewDecisionCreate,
    AuthoringReviewDecisionKind,
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
    AuthoringTraceKind,
)
from noveland.authoring.models import (
    AuthoringImportProposal,
    AuthoringImportRun,
    AuthoringReviewDecision,
    AuthoringSourceAsset,
    AuthoringSourceBatch,
    AuthoringSourceFragment,
    AuthoringSourceTraceability,
)
from noveland.authoring.parser import ParsedScriptCandidate, parse_fragment
from noveland.media.models import MediaAsset
from noveland.worlds.worldlines import worldline_or_404
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class AuthoringValidationError(ValueError):
    pass


class AuthoringNotFoundError(LookupError):
    pass


SUPPORTED_TRACE_ONLY_APPLY_KINDS = {AuthoringProposalKind.OTHER.value}


class AuthoringService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_source_batch(
        self,
        create: AuthoringSourceBatchCreate,
        *,
        actor_ref: str,
    ) -> AuthoringSourceBatchRead:
        worldline_id = self._worldline_id(create.world_id, create.worldline_id)
        model = AuthoringSourceBatch(
            id=uuid.uuid4(),
            world_id=create.world_id,
            worldline_id=worldline_id,
            batch_key=create.batch_key,
            display_name=create.display_name,
            description=create.description,
            source_kind=create.source_kind.value,
            status=create.status.value,
            visibility=create.visibility.value,
            metadata_json=create.metadata_json,
            created_by_actor_ref=actor_ref,
        )
        self._session.add(model)
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise AuthoringValidationError("authoring source batch already exists") from exc
        self._session.refresh(model)
        return _batch_record(model)

    def list_source_batches(
        self,
        world_id: uuid.UUID,
        *,
        worldline_id: uuid.UUID,
        include_deleted: bool = False,
    ) -> list[AuthoringSourceBatchRead]:
        resolved_worldline_id = self._worldline_id(world_id, worldline_id)
        statement = select(AuthoringSourceBatch).where(
            AuthoringSourceBatch.world_id == world_id,
            AuthoringSourceBatch.worldline_id == resolved_worldline_id,
        )
        if not include_deleted:
            statement = statement.where(AuthoringSourceBatch.status != "deleted")
        statement = statement.order_by(
            AuthoringSourceBatch.created_at,
            AuthoringSourceBatch.batch_key,
        )
        return [_batch_record(model) for model in self._session.scalars(statement).all()]

    def get_source_batch(
        self,
        world_id: uuid.UUID,
        batch_id: uuid.UUID,
    ) -> AuthoringSourceBatchRead:
        return _batch_record(self._batch_required(world_id, batch_id))

    def add_source_asset(
        self,
        create: AuthoringSourceAssetCreate,
    ) -> AuthoringSourceAssetRead:
        worldline_id = self._worldline_id(create.world_id, create.worldline_id)
        batch = self._batch_required(create.world_id, create.batch_id)
        if batch.worldline_id != worldline_id:
            raise AuthoringValidationError("source asset must belong to batch worldline")
        self._validate_media_asset(create.world_id, worldline_id, create.media_asset_id)
        model = AuthoringSourceAsset(
            id=uuid.uuid4(),
            world_id=create.world_id,
            worldline_id=worldline_id,
            batch_id=batch.id,
            media_asset_id=create.media_asset_id,
            source_asset_kind=create.source_asset_kind.value,
            source_label=create.source_label,
            source_ref=create.source_ref,
            status=create.status.value,
            metadata_json=create.metadata_json,
        )
        self._session.add(model)
        self._session.flush()
        self._session.refresh(model)
        return _asset_record(model)

    def add_source_fragment(
        self,
        create: AuthoringSourceFragmentCreate,
    ) -> AuthoringSourceFragmentRead:
        worldline_id = self._worldline_id(create.world_id, create.worldline_id)
        source_asset = self._asset_required(create.world_id, create.source_asset_id)
        if source_asset.worldline_id != worldline_id:
            raise AuthoringValidationError("source fragment must belong to asset worldline")
        model = AuthoringSourceFragment(
            id=uuid.uuid4(),
            world_id=create.world_id,
            worldline_id=worldline_id,
            source_asset_id=source_asset.id,
            fragment_key=create.fragment_key,
            fragment_kind=create.fragment_kind.value,
            sequence=create.sequence,
            excerpt_text=create.excerpt_text,
            locator_json=create.locator_json,
            metadata_json=create.metadata_json,
        )
        self._session.add(model)
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise AuthoringValidationError("authoring source fragment already exists") from exc
        self._session.refresh(model)
        return _fragment_record(model)

    def create_import_run(
        self,
        create: AuthoringImportRunCreate,
        *,
        actor_ref: str,
    ) -> AuthoringImportRunRead:
        worldline_id = self._worldline_id(create.world_id, create.worldline_id)
        if create.source_batch_id is not None:
            batch = self._batch_required(create.world_id, create.source_batch_id)
            if batch.worldline_id != worldline_id:
                raise AuthoringValidationError("import run source batch must belong to worldline")
        run = AuthoringImportRun(
            id=uuid.uuid4(),
            world_id=create.world_id,
            worldline_id=worldline_id,
            source_batch_id=create.source_batch_id,
            run_kind=create.run_kind.value,
            status=AuthoringImportRunStatus.DRAFT.value,
            summary_json=create.summary_json,
            created_by_actor_ref=actor_ref,
        )
        self._session.add(run)
        self._session.flush()
        self._session.refresh(run)
        return self.get_import_run(create.world_id, run.id)

    def list_import_runs(
        self,
        world_id: uuid.UUID,
        *,
        worldline_id: uuid.UUID,
    ) -> list[AuthoringImportRunRead]:
        resolved_worldline_id = self._worldline_id(world_id, worldline_id)
        runs = self._session.scalars(
            select(AuthoringImportRun)
            .where(
                AuthoringImportRun.world_id == world_id,
                AuthoringImportRun.worldline_id == resolved_worldline_id,
            )
            .order_by(AuthoringImportRun.created_at),
        ).all()
        return [self.get_import_run(world_id, run.id) for run in runs]

    def get_import_run(
        self,
        world_id: uuid.UUID,
        run_id: uuid.UUID,
    ) -> AuthoringImportRunRead:
        run = self._run_required(world_id, run_id)
        proposals = self._session.scalars(
            select(AuthoringImportProposal)
            .where(AuthoringImportProposal.run_id == run.id)
            .order_by(AuthoringImportProposal.priority, AuthoringImportProposal.created_at),
        ).all()
        return _run_record(run, [_proposal_record(proposal) for proposal in proposals])

    def create_proposal(
        self,
        create: AuthoringProposalCreate,
    ) -> AuthoringProposalRead:
        run = self._run_required(create.world_id, create.run_id)
        worldline_id = self._worldline_id(create.world_id, create.worldline_id)
        if run.worldline_id != worldline_id:
            raise AuthoringValidationError("proposal must belong to run worldline")
        source_fragment = self._fragment_or_none(create.world_id, create.source_fragment_id)
        if source_fragment is not None and source_fragment.worldline_id != worldline_id:
            raise AuthoringValidationError("proposal source fragment must belong to worldline")
        proposal = AuthoringImportProposal(
            id=uuid.uuid4(),
            world_id=create.world_id,
            worldline_id=worldline_id,
            run_id=run.id,
            source_fragment_id=None if source_fragment is None else source_fragment.id,
            proposal_kind=create.proposal_kind.value,
            target_ref_kind=create.target_ref_kind,
            target_ref_id=create.target_ref_id,
            title=create.title,
            summary=create.summary,
            proposed_payload_json=create.proposed_payload_json,
            evidence_json=create.evidence_json,
            confidence=create.confidence,
            priority=create.priority,
            status=create.status.value,
            applied_ref_json={},
        )
        self._session.add(proposal)
        self._session.flush()
        if source_fragment is not None:
            self._add_trace(
                world_id=create.world_id,
                worldline_id=worldline_id,
                source_fragment_id=source_fragment.id,
                proposal_id=proposal.id,
                trace_kind=AuthoringTraceKind.PROPOSAL_CREATED,
                metadata={"run_id": str(run.id), "proposal_kind": proposal.proposal_kind},
            )
        self._session.flush()
        self._session.refresh(proposal)
        return _proposal_record(proposal)

    def preview(
        self,
        world_id: uuid.UUID,
        run_id: uuid.UUID,
        request: AuthoringPreviewRequest,
    ) -> AuthoringPreviewResult:
        worldline_id = self._worldline_id(world_id, request.worldline_id)
        run = self._run_required(world_id, run_id)
        if run.worldline_id != worldline_id:
            raise AuthoringValidationError("preview run must belong to request worldline")
        created: list[AuthoringProposalRead] = []
        for draft in request.proposals:
            created.append(
                self.create_proposal(
                    AuthoringProposalCreate.from_draft(
                        world_id=world_id,
                        worldline_id=worldline_id,
                        run_id=run.id,
                        draft=draft,
                    )
                )
            )
        run.status = AuthoringImportRunStatus.PREVIEWED.value
        run.summary_json = {
            **run.summary_json,
            "preview_created_proposal_count": len(created),
            "provider_execution": False,
        }
        self._session.flush()
        return AuthoringPreviewResult(run=self.get_import_run(world_id, run.id))

    def parse_script(
        self,
        world_id: uuid.UUID,
        run_id: uuid.UUID,
        request: AuthoringScriptParseRequest,
    ) -> AuthoringScriptParseResult:
        worldline_id = self._worldline_id(world_id, request.worldline_id)
        run = self._run_required(world_id, run_id)
        if run.worldline_id != worldline_id:
            raise AuthoringValidationError("parse run must belong to request worldline")

        candidates: list[ParsedScriptCandidate] = []
        for fragment_id in request.source_fragment_ids:
            fragment = self._fragment_required(world_id, fragment_id)
            if fragment.worldline_id != worldline_id:
                raise AuthoringValidationError("source fragment must belong to parse worldline")
            candidates.extend(
                parse_fragment(
                    source_fragment_id=fragment.id,
                    excerpt_text=fragment.excerpt_text,
                    parser_mode=request.parser_mode.value,
                )
            )

        created: list[AuthoringProposalRead] = []
        for candidate in candidates:
            created.append(
                self.create_proposal(
                    AuthoringProposalCreate(
                        world_id=world_id,
                        worldline_id=worldline_id,
                        run_id=run.id,
                        source_fragment_id=candidate.source_fragment_id,
                        proposal_kind=candidate.proposal_kind,
                        target_ref_kind=candidate.target_ref_kind,
                        target_ref_id=None,
                        title=candidate.title,
                        summary=candidate.summary,
                        proposed_payload_json=candidate.proposed_payload_json,
                        evidence_json=candidate.evidence_json,
                        confidence=candidate.confidence,
                        priority=candidate.priority,
                    )
                )
            )

        run.status = AuthoringImportRunStatus.PREVIEWED.value
        run.summary_json = {
            **run.summary_json,
            "parser_mode": request.parser_mode.value,
            "provider_execution": False,
            "created_proposal_count": len(created),
            "dialogue_count": sum(
                1 for candidate in candidates if candidate.candidate_kind == "dialogue"
            ),
            "scene_count": sum(
                1 for candidate in candidates if candidate.candidate_kind == "scene"
            ),
            "choice_count": sum(
                1 for candidate in candidates if candidate.candidate_kind == "choice"
            ),
            "route_count": sum(
                1 for candidate in candidates if candidate.candidate_kind == "route"
            ),
            "event_count": sum(
                1 for candidate in candidates if candidate.candidate_kind == "event"
            ),
            "unresolved_speaker_count": sum(
                1 for candidate in candidates if candidate.unresolved_speaker
            ),
        }
        self._session.flush()
        return AuthoringScriptParseResult(
            run=self.get_import_run(world_id, run.id),
            created_proposal_count=len(created),
            dialogue_count=int(run.summary_json["dialogue_count"]),
            scene_count=int(run.summary_json["scene_count"]),
            choice_count=int(run.summary_json["choice_count"]),
            route_count=int(run.summary_json["route_count"]),
            event_count=int(run.summary_json["event_count"]),
            unresolved_speaker_count=int(run.summary_json["unresolved_speaker_count"]),
        )

    def extract_characters(
        self,
        world_id: uuid.UUID,
        run_id: uuid.UUID,
        request: AuthoringCharacterExtractRequest,
    ) -> AuthoringCharacterExtractResult:
        worldline_id = self._worldline_id(world_id, request.worldline_id)
        run = self._run_required(world_id, run_id)
        if run.worldline_id != worldline_id:
            raise AuthoringValidationError(
                "character extraction run must belong to request worldline"
            )

        candidates: list[ExtractedCharacterCandidate] = []
        for fragment_id in request.source_fragment_ids:
            fragment = self._fragment_required(world_id, fragment_id)
            if fragment.worldline_id != worldline_id:
                raise AuthoringValidationError(
                    "source fragment must belong to extraction worldline"
                )
            candidates.extend(
                extract_character_fragment(
                    source_fragment_id=fragment.id,
                    excerpt_text=fragment.excerpt_text,
                    extractor_mode=request.extractor_mode.value,
                )
            )

        if request.include_dialogue_proposals:
            candidates.extend(
                self._dialogue_speaker_candidates(
                    run.id,
                    extractor_mode=request.extractor_mode.value,
                    priority_offset=len(candidates) + 1,
                )
            )

        candidates = dedupe_candidates(candidates)
        created: list[AuthoringProposalRead] = []
        for candidate in candidates:
            created.append(
                self.create_proposal(
                    AuthoringProposalCreate(
                        world_id=world_id,
                        worldline_id=worldline_id,
                        run_id=run.id,
                        source_fragment_id=candidate.source_fragment_id,
                        proposal_kind=candidate.proposal_kind,
                        target_ref_kind=candidate.target_ref_kind,
                        target_ref_id=None,
                        title=candidate.title,
                        summary=candidate.summary,
                        proposed_payload_json=candidate.proposed_payload_json,
                        evidence_json=candidate.evidence_json,
                        confidence=candidate.confidence,
                        priority=candidate.priority,
                    )
                )
            )

        summary_counts = {
            "created_proposal_count": len(created),
            "character_count": sum(
                1 for candidate in candidates if candidate.candidate_kind == "character"
            ),
            "relationship_count": sum(
                1 for candidate in candidates if candidate.candidate_kind == "relationship"
            ),
            "alias_count": sum(
                1 for candidate in candidates if candidate.candidate_kind == "alias"
            ),
            "faction_count": sum(
                1 for candidate in candidates if candidate.candidate_kind == "faction"
            ),
            "identity_count": sum(
                1 for candidate in candidates if candidate.candidate_kind == "identity"
            ),
            "emotional_baseline_count": sum(
                1
                for candidate in candidates
                if candidate.candidate_kind == "emotional_baseline"
            ),
        }
        run.status = AuthoringImportRunStatus.PREVIEWED.value
        run.summary_json = {
            **run.summary_json,
            "character_extractor_mode": request.extractor_mode.value,
            "include_dialogue_proposals": request.include_dialogue_proposals,
            "provider_execution": False,
            **summary_counts,
        }
        self._session.flush()
        return AuthoringCharacterExtractResult(
            run=self.get_import_run(world_id, run.id),
            created_proposal_count=summary_counts["created_proposal_count"],
            character_count=summary_counts["character_count"],
            relationship_count=summary_counts["relationship_count"],
            alias_count=summary_counts["alias_count"],
            faction_count=summary_counts["faction_count"],
            identity_count=summary_counts["identity_count"],
            emotional_baseline_count=summary_counts["emotional_baseline_count"],
        )

    def review_proposal(
        self,
        world_id: uuid.UUID,
        proposal_id: uuid.UUID,
        review: AuthoringReviewDecisionCreate,
        *,
        actor_ref: str,
    ) -> AuthoringReviewDecisionRead:
        proposal = self._proposal_required(world_id, proposal_id)
        decision = AuthoringReviewDecision(
            id=uuid.uuid4(),
            world_id=proposal.world_id,
            worldline_id=proposal.worldline_id,
            proposal_id=proposal.id,
            decision=review.decision.value,
            reason=review.reason,
            decision_json=review.decision_json,
            decided_by_actor_ref=actor_ref,
        )
        self._session.add(decision)
        proposal.status = _status_for_review_decision(review.decision).value
        if proposal.source_fragment_id is not None:
            self._add_trace(
                world_id=proposal.world_id,
                worldline_id=proposal.worldline_id,
                source_fragment_id=proposal.source_fragment_id,
                proposal_id=proposal.id,
                trace_kind=AuthoringTraceKind.PROPOSAL_REVIEWED,
                metadata={"decision": review.decision.value},
            )
        self._session.flush()
        self._session.refresh(decision)
        return _review_record(decision)

    def apply(
        self,
        world_id: uuid.UUID,
        run_id: uuid.UUID,
        request: AuthoringApplyRequest,
    ) -> AuthoringApplyResult:
        worldline_id = self._worldline_id(world_id, request.worldline_id)
        run = self._run_required(world_id, run_id)
        if run.worldline_id != worldline_id:
            raise AuthoringValidationError("apply run must belong to request worldline")
        proposals = self._proposals_for_apply(run.id, request.proposal_ids)
        applied: list[AuthoringImportProposal] = []
        blocked: list[AuthoringImportProposal] = []
        for proposal in proposals:
            if proposal.world_id != world_id or proposal.worldline_id != worldline_id:
                raise AuthoringValidationError("proposal must belong to apply worldline")
            if proposal.status != AuthoringProposalStatus.APPROVED.value:
                raise AuthoringValidationError("proposal must be approved before apply")
            if proposal.proposal_kind not in SUPPORTED_TRACE_ONLY_APPLY_KINDS:
                proposal.status = AuthoringProposalStatus.BLOCKED.value
                proposal.applied_ref_json = {
                    "blocked_reason": "unsupported_proposal_kind",
                    "proposal_kind": proposal.proposal_kind,
                }
                if proposal.source_fragment_id is not None:
                    self._add_trace(
                        world_id=world_id,
                        worldline_id=worldline_id,
                        source_fragment_id=proposal.source_fragment_id,
                        proposal_id=proposal.id,
                        trace_kind=AuthoringTraceKind.APPLY_BLOCKED,
                        metadata=proposal.applied_ref_json,
                    )
                blocked.append(proposal)
                continue
            proposal.status = AuthoringProposalStatus.APPLIED.value
            proposal.applied_ref_json = {
                "applied_ref_kind": "authoring_import_proposal",
                "applied_ref_id": str(proposal.id),
                "canonical_mutation": False,
            }
            if proposal.source_fragment_id is not None:
                self._add_trace(
                    world_id=world_id,
                    worldline_id=worldline_id,
                    source_fragment_id=proposal.source_fragment_id,
                    proposal_id=proposal.id,
                    trace_kind=AuthoringTraceKind.PROPOSAL_APPLIED,
                    applied_ref_kind="authoring_import_proposal",
                    applied_ref_id=proposal.id,
                    metadata={"canonical_mutation": False},
                )
            applied.append(proposal)
        run.status = AuthoringImportRunStatus.APPLIED.value
        run.summary_json = {
            **run.summary_json,
            "apply_selected_count": len(proposals),
            "applied_count": len(applied),
            "blocked_count": len(blocked),
        }
        self._session.flush()
        return AuthoringApplyResult(
            run=self.get_import_run(world_id, run.id),
            applied_proposals=[_proposal_record(model) for model in applied],
            blocked_proposals=[_proposal_record(model) for model in blocked],
        )

    def _worldline_id(self, world_id: uuid.UUID, worldline_id: uuid.UUID) -> uuid.UUID:
        return worldline_or_404(self._session, world_id, worldline_id).id

    def _batch_required(self, world_id: uuid.UUID, batch_id: uuid.UUID) -> AuthoringSourceBatch:
        batch = self._session.get(AuthoringSourceBatch, batch_id)
        if batch is None or batch.world_id != world_id:
            raise AuthoringNotFoundError("authoring source batch not found")
        return batch

    def _asset_required(self, world_id: uuid.UUID, asset_id: uuid.UUID) -> AuthoringSourceAsset:
        asset = self._session.get(AuthoringSourceAsset, asset_id)
        if asset is None or asset.world_id != world_id:
            raise AuthoringNotFoundError("authoring source asset not found")
        return asset

    def _fragment_required(
        self,
        world_id: uuid.UUID,
        fragment_id: uuid.UUID,
    ) -> AuthoringSourceFragment:
        fragment = self._session.get(AuthoringSourceFragment, fragment_id)
        if fragment is None or fragment.world_id != world_id:
            raise AuthoringNotFoundError("authoring source fragment not found")
        return fragment

    def _fragment_or_none(
        self,
        world_id: uuid.UUID,
        fragment_id: uuid.UUID | None,
    ) -> AuthoringSourceFragment | None:
        if fragment_id is None:
            return None
        return self._fragment_required(world_id, fragment_id)

    def _run_required(self, world_id: uuid.UUID, run_id: uuid.UUID) -> AuthoringImportRun:
        run = self._session.get(AuthoringImportRun, run_id)
        if run is None or run.world_id != world_id:
            raise AuthoringNotFoundError("authoring import run not found")
        return run

    def _proposal_required(
        self,
        world_id: uuid.UUID,
        proposal_id: uuid.UUID,
    ) -> AuthoringImportProposal:
        proposal = self._session.get(AuthoringImportProposal, proposal_id)
        if proposal is None or proposal.world_id != world_id:
            raise AuthoringNotFoundError("authoring import proposal not found")
        return proposal

    def _validate_media_asset(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        media_asset_id: uuid.UUID | None,
    ) -> None:
        if media_asset_id is None:
            return
        asset = self._session.get(MediaAsset, media_asset_id)
        if asset is None or asset.world_id != world_id:
            raise AuthoringValidationError("source media asset not found")
        if asset.worldline_id != worldline_id:
            raise AuthoringValidationError("source media asset must belong to source worldline")

    def _proposals_for_apply(
        self,
        run_id: uuid.UUID,
        proposal_ids: tuple[uuid.UUID, ...],
    ) -> list[AuthoringImportProposal]:
        proposals = self._session.scalars(
            select(AuthoringImportProposal).where(
                AuthoringImportProposal.run_id == run_id,
                AuthoringImportProposal.id.in_(proposal_ids),
            )
        ).all()
        if len(proposals) != len(set(proposal_ids)):
            raise AuthoringValidationError("one or more proposals were not found")
        order = {proposal_id: index for index, proposal_id in enumerate(proposal_ids)}
        return sorted(proposals, key=lambda proposal: order[proposal.id])

    def _dialogue_speaker_candidates(
        self,
        run_id: uuid.UUID,
        *,
        extractor_mode: str,
        priority_offset: int,
    ) -> list[ExtractedCharacterCandidate]:
        proposals = self._session.scalars(
            select(AuthoringImportProposal)
            .where(
                AuthoringImportProposal.run_id == run_id,
                AuthoringImportProposal.proposal_kind == AuthoringProposalKind.DIALOGUE.value,
                AuthoringImportProposal.target_ref_kind == "dialogue_candidate",
            )
            .order_by(AuthoringImportProposal.priority, AuthoringImportProposal.created_at)
        ).all()
        candidates: list[ExtractedCharacterCandidate] = []
        for index, proposal in enumerate(proposals):
            speaker_label = proposal.proposed_payload_json.get("speaker_label")
            if not isinstance(speaker_label, str) or not speaker_label.strip():
                continue
            candidates.append(
                extract_dialogue_speaker_candidate(
                    source_fragment_id=proposal.source_fragment_id,
                    speaker_label=speaker_label,
                    extractor_mode=extractor_mode,
                    priority=priority_offset + index,
                )
            )
        return candidates

    def _add_trace(
        self,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        source_fragment_id: uuid.UUID,
        proposal_id: uuid.UUID | None,
        trace_kind: AuthoringTraceKind,
        metadata: dict[str, Any],
        applied_ref_kind: str | None = None,
        applied_ref_id: uuid.UUID | None = None,
    ) -> None:
        self._session.add(
            AuthoringSourceTraceability(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                source_fragment_id=source_fragment_id,
                proposal_id=proposal_id,
                applied_ref_kind=applied_ref_kind,
                applied_ref_id=applied_ref_id,
                trace_kind=trace_kind.value,
                metadata_json=metadata,
            )
        )


def _status_for_review_decision(
    decision: AuthoringReviewDecisionKind,
) -> AuthoringProposalStatus:
    if decision == AuthoringReviewDecisionKind.APPROVE:
        return AuthoringProposalStatus.APPROVED
    if decision in {AuthoringReviewDecisionKind.REJECT, AuthoringReviewDecisionKind.DISMISS}:
        return AuthoringProposalStatus.REJECTED
    return AuthoringProposalStatus.REVIEWED


def _batch_record(model: AuthoringSourceBatch) -> AuthoringSourceBatchRead:
    return AuthoringSourceBatchRead(
        id=model.id,
        world_id=model.world_id,
        worldline_id=model.worldline_id,
        batch_key=model.batch_key,
        display_name=model.display_name,
        description=model.description,
        source_kind=AuthoringSourceAssetKind(model.source_kind),
        status=AuthoringSourceBatchStatus(model.status),
        visibility=AuthoringSourceVisibility(model.visibility),
        metadata_json=model.metadata_json,
        created_by_actor_ref=model.created_by_actor_ref,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _asset_record(model: AuthoringSourceAsset) -> AuthoringSourceAssetRead:
    return AuthoringSourceAssetRead(
        id=model.id,
        world_id=model.world_id,
        worldline_id=model.worldline_id,
        batch_id=model.batch_id,
        media_asset_id=model.media_asset_id,
        source_asset_kind=AuthoringSourceAssetKind(model.source_asset_kind),
        source_label=model.source_label,
        source_ref=model.source_ref,
        status=AuthoringSourceBatchStatus(model.status),
        metadata_json=model.metadata_json,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _fragment_record(model: AuthoringSourceFragment) -> AuthoringSourceFragmentRead:
    return AuthoringSourceFragmentRead(
        id=model.id,
        world_id=model.world_id,
        worldline_id=model.worldline_id,
        source_asset_id=model.source_asset_id,
        fragment_key=model.fragment_key,
        fragment_kind=AuthoringSourceFragmentKind(model.fragment_kind),
        sequence=model.sequence,
        excerpt_text=model.excerpt_text,
        locator_json=model.locator_json,
        metadata_json=model.metadata_json,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _proposal_record(model: AuthoringImportProposal) -> AuthoringProposalRead:
    return AuthoringProposalRead(
        id=model.id,
        world_id=model.world_id,
        worldline_id=model.worldline_id,
        run_id=model.run_id,
        source_fragment_id=model.source_fragment_id,
        proposal_kind=AuthoringProposalKind(model.proposal_kind),
        target_ref_kind=model.target_ref_kind,
        target_ref_id=model.target_ref_id,
        title=model.title,
        summary=model.summary,
        proposed_payload_json=model.proposed_payload_json,
        evidence_json=model.evidence_json,
        confidence=model.confidence,
        priority=model.priority,
        status=AuthoringProposalStatus(model.status),
        applied_ref_json=model.applied_ref_json,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _run_record(
    model: AuthoringImportRun,
    proposals: list[AuthoringProposalRead],
) -> AuthoringImportRunRead:
    return AuthoringImportRunRead(
        id=model.id,
        world_id=model.world_id,
        worldline_id=model.worldline_id,
        source_batch_id=model.source_batch_id,
        run_kind=AuthoringImportRunKind(model.run_kind),
        status=AuthoringImportRunStatus(model.status),
        summary_json=model.summary_json,
        created_by_actor_ref=model.created_by_actor_ref,
        created_at=model.created_at,
        updated_at=model.updated_at,
        proposals=proposals,
    )


def _review_record(model: AuthoringReviewDecision) -> AuthoringReviewDecisionRead:
    return AuthoringReviewDecisionRead(
        id=model.id,
        world_id=model.world_id,
        worldline_id=model.worldline_id,
        proposal_id=model.proposal_id,
        decision=AuthoringReviewDecisionKind(model.decision),
        reason=model.reason,
        decision_json=model.decision_json,
        decided_by_actor_ref=model.decided_by_actor_ref,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
