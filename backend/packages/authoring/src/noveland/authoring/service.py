from __future__ import annotations

import re
import uuid
from typing import Any

from noveland.agents.contracts import AgentPersonaUpsert
from noveland.agents.models import Agent
from noveland.agents.services import AgentPersonaService
from noveland.authoring.asset_matching import (
    AssetMatchCandidate,
    AssetMatchInput,
    match_asset,
)
from noveland.authoring.asset_matching import (
    dedupe_candidates as dedupe_asset_match_candidates,
)
from noveland.authoring.character_extractor import (
    ExtractedCharacterCandidate,
    dedupe_candidates,
    extract_dialogue_speaker_candidate,
)
from noveland.authoring.character_extractor import (
    extract_fragment as extract_character_fragment,
)
from noveland.authoring.conflict_review import (
    ConflictReviewProposal,
    review_proposals,
)
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
    AuthoringImportRunStatus,
    AuthoringLoreExtractRequest,
    AuthoringLoreExtractResult,
    AuthoringMemoryMigrateRequest,
    AuthoringMemoryMigrateResult,
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
from noveland.authoring.lore_extractor import (
    ExtractedLoreCandidate,
)
from noveland.authoring.lore_extractor import (
    dedupe_candidates as dedupe_lore_candidates,
)
from noveland.authoring.lore_extractor import (
    extract_fragment as extract_lore_fragment,
)
from noveland.authoring.memory_migration import (
    MemoryMigrationCandidate,
    migrate_fragment,
    migrate_proposal,
)
from noveland.authoring.memory_migration import (
    dedupe_candidates as dedupe_memory_candidates,
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
from noveland.memory.models import AgentMemoryItem
from noveland.memory.utils import deterministic_embedding
from noveland.providers.contracts import ProviderExecutionRequest, ProviderKind
from noveland.providers.service import ProviderExecutionService
from noveland.speech.contracts import (
    AgentVoiceProfileBindingCreate,
    VoiceBindingRole,
    VoiceConsentStatus,
    VoiceKind,
    VoiceProfileCreate,
    VoiceProfileOwnerKind,
    VoiceProfileVisibility,
)
from noveland.speech.models import AgentVoiceProfileBinding, VoiceProfile
from noveland.speech.voice_profiles import SpeechValidationError, VoiceProfileService
from noveland.visual.contracts import (
    BackgroundVisibility,
    SceneBackgroundCreate,
    SpriteBindingVisibility,
    SpriteSetCreate,
    SpriteVariantCreate,
)
from noveland.visual.models import (
    CharacterSpriteSet,
    CharacterSpriteVariant,
    SceneBackgroundProfile,
)
from noveland.visual.service import VisualAssetService, VisualValidationError
from noveland.worlds.worldlines import worldline_or_404
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class AuthoringValidationError(ValueError):
    pass


class AuthoringNotFoundError(LookupError):
    pass


SUPPORTED_TRACE_ONLY_APPLY_KINDS = {AuthoringProposalKind.OTHER.value}
RESTRICTED_MEDIA_VISIBILITIES = {"developer_only", "hidden"}
PERSONA_PROPOSAL_TARGET = "agent_persona_candidate"
MEMORY_PROPOSAL_TARGET = "memory_candidate"
VISUAL_PROFILE_RECOMMENDATION_TARGET = "visual_generation_profile_recommendation"
SPRITE_ASSET_MATCH_TARGET = "sprite_asset_match"
BACKGROUND_ASSET_MATCH_TARGET = "background_asset_match"
CG_ASSET_MATCH_TARGET = "cg_asset_match"
VOICE_ASSET_MATCH_TARGET = "voice_asset_match"


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
            "emotion_hint_count": sum(
                1 for candidate in candidates if candidate.candidate_kind == "emotion_hint"
            ),
            "relationship_hint_count": sum(
                1
                for candidate in candidates
                if candidate.candidate_kind == "relationship_hint"
            ),
            "manual_label_count": sum(
                1 for candidate in candidates if candidate.candidate_kind == "manual_label"
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
            emotion_hint_count=int(run.summary_json["emotion_hint_count"]),
            relationship_hint_count=int(run.summary_json["relationship_hint_count"]),
            manual_label_count=int(run.summary_json["manual_label_count"]),
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

    def extract_lore(
        self,
        world_id: uuid.UUID,
        run_id: uuid.UUID,
        request: AuthoringLoreExtractRequest,
    ) -> AuthoringLoreExtractResult:
        worldline_id = self._worldline_id(world_id, request.worldline_id)
        run = self._run_required(world_id, run_id)
        if run.worldline_id != worldline_id:
            raise AuthoringValidationError(
                "lore extraction run must belong to request worldline"
            )

        candidates: list[ExtractedLoreCandidate] = []
        for fragment_id in request.source_fragment_ids:
            fragment = self._fragment_required(world_id, fragment_id)
            if fragment.worldline_id != worldline_id:
                raise AuthoringValidationError(
                    "source fragment must belong to extraction worldline"
                )
            candidates.extend(
                extract_lore_fragment(
                    source_fragment_id=fragment.id,
                    excerpt_text=fragment.excerpt_text,
                    extractor_mode=request.extractor_mode.value,
                )
            )

        candidates = dedupe_lore_candidates(candidates)
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
            "lore_count": sum(
                1 for candidate in candidates if candidate.candidate_kind == "lore"
            ),
            "location_count": sum(
                1 for candidate in candidates if candidate.candidate_kind == "location"
            ),
            "organization_count": sum(
                1
                for candidate in candidates
                if candidate.candidate_kind == "organization"
            ),
            "world_rule_count": sum(
                1 for candidate in candidates if candidate.candidate_kind == "world_rule"
            ),
            "secret_count": sum(
                1 for candidate in candidates if candidate.candidate_kind == "secret"
            ),
            "knowledge_boundary_count": sum(
                1
                for candidate in candidates
                if candidate.candidate_kind == "knowledge_boundary"
            ),
            "uncertain_count": sum(
                1 for candidate in candidates if candidate.classification == "uncertain"
            ),
        }
        run.status = AuthoringImportRunStatus.PREVIEWED.value
        run.summary_json = {
            **run.summary_json,
            "lore_extractor_mode": request.extractor_mode.value,
            "provider_execution": False,
            **summary_counts,
        }
        self._session.flush()
        return AuthoringLoreExtractResult(
            run=self.get_import_run(world_id, run.id),
            created_proposal_count=summary_counts["created_proposal_count"],
            lore_count=summary_counts["lore_count"],
            location_count=summary_counts["location_count"],
            organization_count=summary_counts["organization_count"],
            world_rule_count=summary_counts["world_rule_count"],
            secret_count=summary_counts["secret_count"],
            knowledge_boundary_count=summary_counts["knowledge_boundary_count"],
            uncertain_count=summary_counts["uncertain_count"],
        )

    def review_conflicts(
        self,
        world_id: uuid.UUID,
        run_id: uuid.UUID,
        request: AuthoringConflictReviewRequest,
    ) -> AuthoringConflictReviewResult:
        worldline_id = self._worldline_id(world_id, request.worldline_id)
        run = self._run_required(world_id, run_id)
        if run.worldline_id != worldline_id:
            raise AuthoringValidationError(
                "conflict review run must belong to request worldline"
            )

        include_statuses = tuple(status.value for status in request.include_statuses)
        proposal_models = self._session.scalars(
            select(AuthoringImportProposal)
            .where(
                AuthoringImportProposal.run_id == run.id,
                AuthoringImportProposal.world_id == world_id,
                AuthoringImportProposal.worldline_id == worldline_id,
                AuthoringImportProposal.status.in_(include_statuses),
                AuthoringImportProposal.target_ref_kind != "canon_conflict_report",
            )
            .order_by(AuthoringImportProposal.priority, AuthoringImportProposal.created_at)
        ).all()
        review_inputs = [
            ConflictReviewProposal(
                id=proposal.id,
                source_fragment_id=proposal.source_fragment_id,
                target_ref_kind=proposal.target_ref_kind,
                proposed_payload_json=proposal.proposed_payload_json,
                evidence_json=proposal.evidence_json,
            )
            for proposal in proposal_models
        ]
        candidates = review_proposals(
            review_inputs,
            review_mode=request.review_mode.value,
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

        summary_counts = {
            "created_proposal_count": len(created),
            "duplicate_count": sum(
                1 for candidate in candidates if candidate.conflict_kind == "duplicate"
            ),
            "contradiction_count": sum(
                1
                for candidate in candidates
                if candidate.conflict_kind == "contradiction"
            ),
            "uncertain_count": sum(
                1 for candidate in candidates if candidate.conflict_kind == "uncertain"
            ),
            "ooc_risk_count": sum(
                1 for candidate in candidates if candidate.conflict_kind == "ooc_risk"
            ),
        }
        run.status = AuthoringImportRunStatus.PREVIEWED.value
        run.summary_json = {
            **run.summary_json,
            "conflict_review_mode": request.review_mode.value,
            "provider_execution": False,
            **summary_counts,
        }
        self._session.flush()
        return AuthoringConflictReviewResult(
            run=self.get_import_run(world_id, run.id),
            created_proposal_count=summary_counts["created_proposal_count"],
            duplicate_count=summary_counts["duplicate_count"],
            contradiction_count=summary_counts["contradiction_count"],
            uncertain_count=summary_counts["uncertain_count"],
            ooc_risk_count=summary_counts["ooc_risk_count"],
        )

    def migrate_memory(
        self,
        world_id: uuid.UUID,
        run_id: uuid.UUID,
        request: AuthoringMemoryMigrateRequest,
    ) -> AuthoringMemoryMigrateResult:
        worldline_id = self._worldline_id(world_id, request.worldline_id)
        run = self._run_required(world_id, run_id)
        if run.worldline_id != worldline_id:
            raise AuthoringValidationError(
                "memory migration run must belong to request worldline"
            )

        candidates: list[MemoryMigrationCandidate] = []
        for fragment_id in request.source_fragment_ids:
            fragment = self._fragment_required(world_id, fragment_id)
            if fragment.worldline_id != worldline_id:
                raise AuthoringValidationError(
                    "source fragment must belong to memory migration worldline"
                )
            candidates.extend(
                migrate_fragment(
                    source_fragment_id=fragment.id,
                    excerpt_text=fragment.excerpt_text,
                    migration_mode=request.migration_mode.value,
                )
            )

        if request.include_proposals:
            candidates.extend(
                self._memory_candidates_from_proposals(
                    run.id,
                    migration_mode=request.migration_mode.value,
                    priority_offset=len(candidates) + 1,
                )
            )

        candidates = dedupe_memory_candidates(candidates)
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
            "fact_count": sum(
                1 for candidate in candidates if candidate.memory_kind == "fact"
            ),
            "episodic_count": sum(
                1 for candidate in candidates if candidate.memory_kind == "episodic"
            ),
            "relationship_count": sum(
                1 for candidate in candidates if candidate.memory_kind == "relationship"
            ),
            "preference_count": sum(
                1 for candidate in candidates if candidate.memory_kind == "preference"
            ),
            "style_count": sum(
                1 for candidate in candidates if candidate.memory_kind == "style"
            ),
        }
        run.status = AuthoringImportRunStatus.PREVIEWED.value
        run.summary_json = {
            **run.summary_json,
            "memory_migration_mode": request.migration_mode.value,
            "include_proposals": request.include_proposals,
            "provider_execution": False,
            **summary_counts,
        }
        self._session.flush()
        return AuthoringMemoryMigrateResult(
            run=self.get_import_run(world_id, run.id),
            created_proposal_count=summary_counts["created_proposal_count"],
            fact_count=summary_counts["fact_count"],
            episodic_count=summary_counts["episodic_count"],
            relationship_count=summary_counts["relationship_count"],
            preference_count=summary_counts["preference_count"],
            style_count=summary_counts["style_count"],
        )

    def distill_character_memory(
        self,
        world_id: uuid.UUID,
        run_id: uuid.UUID,
        request: AuthoringCharacterMemoryDistillRequest,
        *,
        actor_ref: str,
    ) -> AuthoringCharacterMemoryDistillResult:
        worldline_id = self._worldline_id(world_id, request.worldline_id)
        run = self._run_required(world_id, run_id)
        if run.worldline_id != worldline_id:
            raise AuthoringValidationError(
                "character memory distillation run must belong to request worldline"
            )
        agent = self._agent_required(world_id, request.agent_id)
        fragments = self._distillation_fragments(
            world_id,
            worldline_id,
            request.source_fragment_ids,
        )
        source_refs = [str(fragment.id) for fragment in fragments]
        prompt_text = _distillation_prompt(agent, fragments)
        provider_result = ProviderExecutionService(self._session).execute(
            ProviderExecutionRequest(
                world_id=world_id,
                worldline_id=worldline_id,
                provider_id=request.provider_id,
                provider_kind=ProviderKind.TEXT_GENERATION,
                input_text=prompt_text,
                input_json={
                    "task": "character_memory_distillation",
                    "agent_id": str(agent.id),
                    "source_fragment_ids": source_refs,
                },
                request_json={
                    "distillation_mode": request.distillation_mode.value,
                    "output_contract": "persona_and_initial_memory_candidates",
                },
                model_name=request.model_name,
                actor_ref=actor_ref,
            )
        )
        persona_payload = _persona_payload(
            agent=agent,
            fragments=fragments,
            model_invocation_id=provider_result.invocation.id,
        )
        memory_payloads = _memory_payloads(
            agent=agent,
            fragments=fragments,
            model_invocation_id=provider_result.invocation.id,
        )
        visual_payload = _visual_profile_payload(
            agent=agent,
            fragments=fragments,
            model_invocation_id=provider_result.invocation.id,
        )

        created: list[AuthoringProposalRead] = []
        first_fragment_id = fragments[0].id
        created.append(
            self.create_proposal(
                AuthoringProposalCreate(
                    world_id=world_id,
                    worldline_id=worldline_id,
                    run_id=run.id,
                    source_fragment_id=first_fragment_id,
                    proposal_kind=AuthoringProposalKind.CHARACTER,
                    target_ref_kind=PERSONA_PROPOSAL_TARGET,
                    target_ref_id=agent.id,
                    title=f"Persona card for {agent.display_name}",
                    summary=(
                        f"Provider-backed persona card candidate for {agent.display_name}."
                    ),
                    proposed_payload_json=persona_payload,
                    evidence_json=_distillation_evidence(
                        source_refs=source_refs,
                        model_invocation_id=provider_result.invocation.id,
                        evidence_kind="persona_card",
                    ),
                    confidence=0.72,
                    priority=10,
                )
            )
        )
        for index, memory_payload in enumerate(memory_payloads, start=1):
            source_fragment_id = _uuid_from_payload(
                memory_payload.get("source_fragment_id"),
            ) or first_fragment_id
            created.append(
                self.create_proposal(
                    AuthoringProposalCreate(
                        world_id=world_id,
                        worldline_id=worldline_id,
                        run_id=run.id,
                        source_fragment_id=source_fragment_id,
                        proposal_kind=AuthoringProposalKind.MEMORY,
                        target_ref_kind=MEMORY_PROPOSAL_TARGET,
                        target_ref_id=agent.id,
                        title=f"Initial memory {index} for {agent.display_name}",
                        summary=str(memory_payload["content"])[:200],
                        proposed_payload_json=memory_payload,
                        evidence_json=_distillation_evidence(
                            source_refs=[str(source_fragment_id)],
                            model_invocation_id=provider_result.invocation.id,
                            evidence_kind="memory_candidate",
                        ),
                        confidence=0.68,
                        priority=20 + index,
                    )
                )
            )
        visual_count = 0
        if request.include_visual_profile_recommendation:
            created.append(
                self.create_proposal(
                    AuthoringProposalCreate(
                        world_id=world_id,
                        worldline_id=worldline_id,
                        run_id=run.id,
                        source_fragment_id=first_fragment_id,
                        proposal_kind=AuthoringProposalKind.ASSET_MATCH,
                        target_ref_kind=VISUAL_PROFILE_RECOMMENDATION_TARGET,
                        target_ref_id=agent.id,
                        title=f"Visual generation profile recommendation for {agent.display_name}",
                        summary=(
                            "Review-only visual generation profile recommendations derived "
                            "from character source fragments."
                        ),
                        proposed_payload_json=visual_payload,
                        evidence_json=_distillation_evidence(
                            source_refs=source_refs,
                            model_invocation_id=provider_result.invocation.id,
                            evidence_kind="visual_generation_profile_recommendation",
                        ),
                        confidence=0.55,
                        priority=90,
                    )
                )
            )
            visual_count = 1

        summary_counts = {
            "created_proposal_count": len(created),
            "persona_proposal_count": 1,
            "memory_candidate_count": len(memory_payloads),
            "visual_profile_recommendation_count": visual_count,
        }
        run.status = AuthoringImportRunStatus.PREVIEWED.value
        run.summary_json = {
            **run.summary_json,
            "character_memory_distillation_mode": request.distillation_mode.value,
            "agent_id": str(agent.id),
            "provider_execution": True,
            "model_invocation_id": str(provider_result.invocation.id),
            "source_fragment_count": len(fragments),
            **summary_counts,
        }
        self._session.flush()
        return AuthoringCharacterMemoryDistillResult(
            run=self.get_import_run(world_id, run.id),
            model_invocation_id=provider_result.invocation.id,
            provider_execution=True,
            **summary_counts,
        )

    def match_assets(
        self,
        world_id: uuid.UUID,
        run_id: uuid.UUID,
        request: AuthoringAssetMatchRequest,
    ) -> AuthoringAssetMatchResult:
        worldline_id = self._worldline_id(world_id, request.worldline_id)
        run = self._run_required(world_id, run_id)
        if run.worldline_id != worldline_id:
            raise AuthoringValidationError("asset match run must belong to request worldline")

        match_inputs, blocked_count = self._asset_match_inputs(
            world_id,
            worldline_id,
            request,
        )
        candidates: list[AssetMatchCandidate] = []
        for match_input in match_inputs:
            candidates.extend(
                match_asset(
                    match_input,
                    matching_mode=request.matching_mode.value,
                    include_visual_matches=request.include_visual_matches,
                    include_voice_matches=request.include_voice_matches,
                    include_cg_matches=request.include_cg_matches,
                )
            )

        candidates = dedupe_asset_match_candidates(candidates)
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
            "sprite_match_count": sum(
                1 for candidate in candidates if candidate.match_kind == "sprite"
            ),
            "background_match_count": sum(
                1 for candidate in candidates if candidate.match_kind == "background"
            ),
            "cg_match_count": sum(
                1 for candidate in candidates if candidate.match_kind == "cg"
            ),
            "voice_match_count": sum(
                1 for candidate in candidates if candidate.match_kind == "voice"
            ),
            "blocked_count": blocked_count,
        }
        run.status = AuthoringImportRunStatus.PREVIEWED.value
        run.summary_json = {
            **run.summary_json,
            "asset_matching_mode": request.matching_mode.value,
            "include_visual_matches": request.include_visual_matches,
            "include_voice_matches": request.include_voice_matches,
            "include_cg_matches": request.include_cg_matches,
            "provider_execution": False,
            **summary_counts,
        }
        self._session.flush()
        return AuthoringAssetMatchResult(
            run=self.get_import_run(world_id, run.id),
            created_proposal_count=summary_counts["created_proposal_count"],
            sprite_match_count=summary_counts["sprite_match_count"],
            background_match_count=summary_counts["background_match_count"],
            cg_match_count=summary_counts["cg_match_count"],
            voice_match_count=summary_counts["voice_match_count"],
            blocked_count=summary_counts["blocked_count"],
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
            applied_ref_json = self._apply_supported_proposal(
                proposal,
                world_id=world_id,
                worldline_id=worldline_id,
            )
            if applied_ref_json is None:
                proposal.status = AuthoringProposalStatus.BLOCKED.value
                proposal.applied_ref_json = {
                    "blocked_reason": "unsupported_proposal_kind",
                    "proposal_kind": proposal.proposal_kind,
                    "target_ref_kind": proposal.target_ref_kind,
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
            proposal.applied_ref_json = applied_ref_json
            if proposal.source_fragment_id is not None:
                self._add_trace(
                    world_id=world_id,
                    worldline_id=worldline_id,
                    source_fragment_id=proposal.source_fragment_id,
                    proposal_id=proposal.id,
                    trace_kind=AuthoringTraceKind.PROPOSAL_APPLIED,
                    applied_ref_kind=str(applied_ref_json["applied_ref_kind"]),
                    applied_ref_id=_uuid_from_payload(applied_ref_json["applied_ref_id"]),
                    metadata={
                        "canonical_mutation": bool(
                            applied_ref_json.get("canonical_mutation", False)
                        ),
                        "target_ref_kind": proposal.target_ref_kind,
                    },
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

    def _agent_required(self, world_id: uuid.UUID, agent_id: uuid.UUID) -> Agent:
        agent = self._session.get(Agent, agent_id)
        if agent is None or agent.world_id != world_id:
            raise AuthoringValidationError("target agent not found")
        return agent

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

    def _media_asset_required(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        media_asset_id: uuid.UUID,
    ) -> MediaAsset:
        asset = self._session.get(MediaAsset, media_asset_id)
        if (
            asset is None
            or asset.world_id != world_id
            or asset.worldline_id != worldline_id
            or asset.status != "available"
        ):
            raise AuthoringValidationError("media asset must belong to apply worldline")
        if asset.visibility in RESTRICTED_MEDIA_VISIBILITIES:
            raise AuthoringValidationError("restricted media asset cannot be applied")
        return asset

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

    def _memory_candidates_from_proposals(
        self,
        run_id: uuid.UUID,
        *,
        migration_mode: str,
        priority_offset: int,
    ) -> list[MemoryMigrationCandidate]:
        proposals = self._session.scalars(
            select(AuthoringImportProposal)
            .where(
                AuthoringImportProposal.run_id == run_id,
                AuthoringImportProposal.proposal_kind.in_(
                    (
                        AuthoringProposalKind.DIALOGUE.value,
                        AuthoringProposalKind.RELATIONSHIP.value,
                        AuthoringProposalKind.LORE.value,
                    )
                ),
                AuthoringImportProposal.target_ref_kind != "memory_candidate",
            )
            .order_by(AuthoringImportProposal.priority, AuthoringImportProposal.created_at)
        ).all()
        candidates: list[MemoryMigrationCandidate] = []
        for index, proposal in enumerate(proposals):
            candidate = migrate_proposal(
                source_fragment_id=proposal.source_fragment_id,
                target_ref_kind=proposal.target_ref_kind,
                proposed_payload_json=proposal.proposed_payload_json,
                migration_mode=migration_mode,
                priority=priority_offset + index,
            )
            if candidate is not None:
                candidates.append(candidate)
        return candidates

    def _asset_match_inputs(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        request: AuthoringAssetMatchRequest,
    ) -> tuple[list[AssetMatchInput], int]:
        match_inputs: list[AssetMatchInput] = []
        blocked_count = 0

        def append_asset(
            source_asset: AuthoringSourceAsset,
            source_fragment: AuthoringSourceFragment | None,
        ) -> None:
            nonlocal blocked_count
            if source_asset.worldline_id != worldline_id:
                raise AuthoringValidationError(
                    "source asset must belong to asset matching worldline"
                )
            if source_asset.status != AuthoringSourceBatchStatus.ACTIVE.value:
                blocked_count += 1
                return
            media_asset = self._media_asset_for_match(
                world_id,
                worldline_id,
                source_asset.media_asset_id,
            )
            if media_asset is None:
                blocked_count += 1
                return
            if (
                media_asset.status != "available"
                or media_asset.visibility in RESTRICTED_MEDIA_VISIBILITIES
                or media_asset.asset_kind not in {"image", "audio"}
            ):
                blocked_count += 1
                return
            match_inputs.append(
                AssetMatchInput(
                    source_asset_id=source_asset.id,
                    source_fragment_id=None if source_fragment is None else source_fragment.id,
                    media_asset_id=media_asset.id,
                    source_asset_kind=source_asset.source_asset_kind,
                    source_label=source_asset.source_label,
                    source_metadata_json=source_asset.metadata_json,
                    fragment_kind=None
                    if source_fragment is None
                    else source_fragment.fragment_kind,
                    fragment_metadata_json={}
                    if source_fragment is None
                    else source_fragment.metadata_json,
                    media_asset_kind=media_asset.asset_kind,
                    media_asset_role=media_asset.asset_role,
                    media_visibility=media_asset.visibility,
                    priority=len(match_inputs) + 1,
                )
            )

        for source_asset_id in request.source_asset_ids:
            append_asset(self._asset_required(world_id, source_asset_id), None)
        for source_fragment_id in request.source_fragment_ids:
            source_fragment = self._fragment_required(world_id, source_fragment_id)
            if source_fragment.worldline_id != worldline_id:
                raise AuthoringValidationError(
                    "source fragment must belong to asset matching worldline"
                )
            source_asset = self._asset_required(world_id, source_fragment.source_asset_id)
            append_asset(source_asset, source_fragment)
        return match_inputs, blocked_count

    def _media_asset_for_match(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        media_asset_id: uuid.UUID | None,
    ) -> MediaAsset | None:
        if media_asset_id is None:
            return None
        media_asset = self._session.get(MediaAsset, media_asset_id)
        if media_asset is None:
            return None
        if media_asset.world_id != world_id:
            raise AuthoringValidationError("source media asset must belong to world")
        if media_asset.worldline_id != worldline_id:
            raise AuthoringValidationError(
                "source media asset must belong to asset matching worldline"
            )
        return media_asset

    def _asset_match_media_asset_id(self, payload: dict[str, Any]) -> uuid.UUID:
        media_asset_id = _uuid_from_payload(payload.get("media_asset_id"))
        if media_asset_id is None:
            raise AuthoringValidationError("asset match proposal requires media_asset_id")
        return media_asset_id

    def _agent_for_sprite_payload(self, world_id: uuid.UUID, payload: dict[str, Any]) -> Agent:
        agent_id = _uuid_from_payload(payload.get("agent_id"))
        if agent_id is not None:
            return self._agent_required(world_id, agent_id)
        character_label = str(
            payload.get("character_label") or payload.get("speaker_label") or ""
        ).strip()
        if not character_label:
            raise AuthoringValidationError(
                "sprite asset match requires agent_id or character_label"
            )
        normalized = _label_key(character_label)
        agent = self._session.scalars(
            select(Agent).where(
                Agent.world_id == world_id,
                (Agent.agent_key == normalized) | (Agent.display_name == character_label),
            )
        ).first()
        if agent is not None:
            return agent
        agents = self._session.scalars(select(Agent).where(Agent.world_id == world_id)).all()
        for candidate in agents:
            if _label_key(candidate.display_name) == normalized:
                return candidate
        raise AuthoringValidationError("sprite asset match target agent not found")

    def _agent_for_voice_payload(self, world_id: uuid.UUID, payload: dict[str, Any]) -> Agent:
        agent_id = _uuid_from_payload(payload.get("agent_id"))
        if agent_id is not None:
            return self._agent_required(world_id, agent_id)
        speaker_label = str(
            payload.get("speaker_label")
            or payload.get("character_label")
            or payload.get("voice_label")
            or ""
        ).strip()
        if not speaker_label:
            raise AuthoringValidationError("voice asset match requires agent_id or speaker_label")
        normalized = _label_key(speaker_label)
        agent = self._session.scalars(
            select(Agent).where(
                Agent.world_id == world_id,
                (Agent.agent_key == normalized) | (Agent.display_name == speaker_label),
            )
        ).first()
        if agent is not None:
            return agent
        agents = self._session.scalars(select(Agent).where(Agent.world_id == world_id)).all()
        for candidate in agents:
            if _label_key(candidate.display_name) == normalized:
                return candidate
        raise AuthoringValidationError("voice asset match target agent not found")

    def _find_sprite_set(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        agent_id: uuid.UUID,
        style_key: str,
    ) -> CharacterSpriteSet | None:
        return self._session.scalars(
            select(CharacterSpriteSet).where(
                CharacterSpriteSet.world_id == world_id,
                CharacterSpriteSet.worldline_id == worldline_id,
                CharacterSpriteSet.agent_id == agent_id,
                CharacterSpriteSet.style_key == style_key,
                CharacterSpriteSet.status != "deleted",
            )
        ).first()

    def _find_sprite_variant(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        sprite_set_id: uuid.UUID,
        media_asset_id: uuid.UUID,
        expression_key: str,
        pose_key: str | None,
        outfit_key: str | None,
    ) -> CharacterSpriteVariant | None:
        return self._session.scalars(
            select(CharacterSpriteVariant).where(
                CharacterSpriteVariant.world_id == world_id,
                CharacterSpriteVariant.worldline_id == worldline_id,
                CharacterSpriteVariant.sprite_set_id == sprite_set_id,
                CharacterSpriteVariant.asset_id == media_asset_id,
                CharacterSpriteVariant.expression_key == expression_key,
                CharacterSpriteVariant.pose_key.is_(None)
                if pose_key is None
                else CharacterSpriteVariant.pose_key == pose_key,
                CharacterSpriteVariant.outfit_key.is_(None)
                if outfit_key is None
                else CharacterSpriteVariant.outfit_key == outfit_key,
                CharacterSpriteVariant.status != "deleted",
            )
        ).first()

    def _find_background(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        media_asset_id: uuid.UUID,
        scene_id: uuid.UUID | None,
        location_key: str,
        time_of_day: str | None,
        weather_key: str | None,
    ) -> SceneBackgroundProfile | None:
        return self._session.scalars(
            select(SceneBackgroundProfile).where(
                SceneBackgroundProfile.world_id == world_id,
                SceneBackgroundProfile.worldline_id == worldline_id,
                SceneBackgroundProfile.asset_id == media_asset_id,
                SceneBackgroundProfile.scene_id.is_(None)
                if scene_id is None
                else SceneBackgroundProfile.scene_id == scene_id,
                SceneBackgroundProfile.location_key == location_key,
                SceneBackgroundProfile.time_of_day.is_(None)
                if time_of_day is None
                else SceneBackgroundProfile.time_of_day == time_of_day,
                SceneBackgroundProfile.weather_key.is_(None)
                if weather_key is None
                else SceneBackgroundProfile.weather_key == weather_key,
                SceneBackgroundProfile.status != "deleted",
            )
        ).first()

    def _should_default_sprite_variant(
        self,
        world_id: uuid.UUID,
        sprite_set_id: uuid.UUID,
        expression_key: str,
    ) -> bool:
        existing_default = self._session.scalars(
            select(CharacterSpriteVariant).where(
                CharacterSpriteVariant.world_id == world_id,
                CharacterSpriteVariant.sprite_set_id == sprite_set_id,
                CharacterSpriteVariant.status != "deleted",
                CharacterSpriteVariant.is_default.is_(True),
            )
        ).first()
        if existing_default is not None:
            return False
        existing_variant = self._session.scalars(
            select(CharacterSpriteVariant).where(
                CharacterSpriteVariant.world_id == world_id,
                CharacterSpriteVariant.sprite_set_id == sprite_set_id,
                CharacterSpriteVariant.status != "deleted",
            )
        ).first()
        return existing_variant is None or expression_key == "neutral"

    def _should_default_background(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        scene_id: uuid.UUID | None,
        location_key: str,
    ) -> bool:
        existing_default = self._session.scalars(
            select(SceneBackgroundProfile).where(
                SceneBackgroundProfile.world_id == world_id,
                SceneBackgroundProfile.worldline_id == worldline_id,
                SceneBackgroundProfile.scene_id.is_(None)
                if scene_id is None
                else SceneBackgroundProfile.scene_id == scene_id,
                SceneBackgroundProfile.location_key == location_key,
                SceneBackgroundProfile.status != "deleted",
                SceneBackgroundProfile.is_default.is_(True),
            )
        ).first()
        return existing_default is None

    def _mark_media_generation_reference_candidate(
        self,
        media_asset_id: uuid.UUID,
        proposal: AuthoringImportProposal,
        *,
        reference_role: str,
    ) -> None:
        media_asset = self._session.get(MediaAsset, media_asset_id)
        if media_asset is None:
            raise AuthoringValidationError("media asset not found")
        metadata = dict(media_asset.metadata_json)
        metadata["generation_reference_candidate"] = True
        roles = set(_string_list(metadata.get("generation_reference_roles")))
        roles.add(reference_role)
        metadata["generation_reference_roles"] = sorted(roles)
        applied = list(metadata.get("authoring_visual_mapping_proposals", []))
        entry = {"proposal_id": str(proposal.id), "run_id": str(proposal.run_id)}
        if entry not in applied:
            applied.append(entry)
        metadata["authoring_visual_mapping_proposals"] = applied
        media_asset.metadata_json = metadata

    def _find_voice_profile(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        profile_key: str,
    ) -> VoiceProfile | None:
        return self._session.scalars(
            select(VoiceProfile).where(
                VoiceProfile.world_id == world_id,
                VoiceProfile.worldline_id == worldline_id,
                VoiceProfile.profile_key == profile_key,
                VoiceProfile.status != "deleted",
            )
        ).first()

    def _find_voice_binding(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        agent_id: uuid.UUID,
        voice_profile_id: uuid.UUID,
        binding_role: str,
    ) -> AgentVoiceProfileBinding | None:
        return self._session.scalars(
            select(AgentVoiceProfileBinding).where(
                AgentVoiceProfileBinding.world_id == world_id,
                AgentVoiceProfileBinding.worldline_id == worldline_id,
                AgentVoiceProfileBinding.agent_id == agent_id,
                AgentVoiceProfileBinding.voice_profile_id == voice_profile_id,
                AgentVoiceProfileBinding.binding_role == binding_role,
            )
        ).first()

    def _should_default_voice_binding(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        agent_id: uuid.UUID,
    ) -> bool:
        existing_default = self._session.scalars(
            select(AgentVoiceProfileBinding).where(
                AgentVoiceProfileBinding.world_id == world_id,
                AgentVoiceProfileBinding.worldline_id == worldline_id,
                AgentVoiceProfileBinding.agent_id == agent_id,
                AgentVoiceProfileBinding.is_default.is_(True),
            )
        ).first()
        return existing_default is None

    def _mark_media_voice_reference(
        self,
        media_asset_id: uuid.UUID,
        proposal: AuthoringImportProposal,
        *,
        agent_id: uuid.UUID,
        voice_profile_id: uuid.UUID,
    ) -> None:
        media_asset = self._session.get(MediaAsset, media_asset_id)
        if media_asset is None:
            raise AuthoringValidationError("media asset not found")
        metadata = dict(media_asset.metadata_json)
        metadata["voice_reference_candidate"] = True
        mappings = list(metadata.get("authoring_voice_mapping_proposals", []))
        entry = {
            "proposal_id": str(proposal.id),
            "run_id": str(proposal.run_id),
            "agent_id": str(agent_id),
            "voice_profile_id": str(voice_profile_id),
        }
        if entry not in mappings:
            mappings.append(entry)
        metadata["authoring_voice_mapping_proposals"] = mappings
        media_asset.metadata_json = metadata

    def _distillation_fragments(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        source_fragment_ids: tuple[uuid.UUID, ...],
    ) -> list[AuthoringSourceFragment]:
        fragments: list[AuthoringSourceFragment] = []
        for fragment_id in source_fragment_ids:
            fragment = self._fragment_required(world_id, fragment_id)
            if fragment.worldline_id != worldline_id:
                raise AuthoringValidationError(
                    "source fragment must belong to character distillation worldline"
                )
            if not (fragment.excerpt_text or "").strip():
                raise AuthoringValidationError(
                    "character distillation source fragments require excerpt text"
                )
            fragments.append(fragment)
        return fragments

    def _apply_supported_proposal(
        self,
        proposal: AuthoringImportProposal,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
    ) -> dict[str, Any] | None:
        if (
            proposal.proposal_kind == AuthoringProposalKind.CHARACTER.value
            and proposal.target_ref_kind == PERSONA_PROPOSAL_TARGET
        ):
            return self._apply_persona_candidate(proposal, world_id=world_id)
        if (
            proposal.proposal_kind == AuthoringProposalKind.MEMORY.value
            and proposal.target_ref_kind == MEMORY_PROPOSAL_TARGET
            and proposal.target_ref_id is not None
            and proposal.proposed_payload_json.get("source_kind") == "authoring_distillation"
        ):
            return self._apply_memory_candidate(
                proposal,
                world_id=world_id,
                worldline_id=worldline_id,
            )
        if (
            proposal.proposal_kind == AuthoringProposalKind.ASSET_MATCH.value
            and proposal.target_ref_kind == VISUAL_PROFILE_RECOMMENDATION_TARGET
        ):
            return {
                "applied_ref_kind": "visual_generation_profile_recommendation",
                "applied_ref_id": str(proposal.id),
                "canonical_mutation": False,
                "profile_mutation": False,
            }
        if (
            proposal.proposal_kind == AuthoringProposalKind.ASSET_MATCH.value
            and proposal.target_ref_kind == SPRITE_ASSET_MATCH_TARGET
        ):
            return self._apply_sprite_asset_match(
                proposal,
                world_id=world_id,
                worldline_id=worldline_id,
            )
        if (
            proposal.proposal_kind == AuthoringProposalKind.ASSET_MATCH.value
            and proposal.target_ref_kind == BACKGROUND_ASSET_MATCH_TARGET
        ):
            return self._apply_background_asset_match(
                proposal,
                world_id=world_id,
                worldline_id=worldline_id,
            )
        if (
            proposal.proposal_kind == AuthoringProposalKind.ASSET_MATCH.value
            and proposal.target_ref_kind == CG_ASSET_MATCH_TARGET
        ):
            return self._apply_cg_asset_match(
                proposal,
                world_id=world_id,
                worldline_id=worldline_id,
            )
        if (
            proposal.proposal_kind == AuthoringProposalKind.ASSET_MATCH.value
            and proposal.target_ref_kind == VOICE_ASSET_MATCH_TARGET
        ):
            return self._apply_voice_asset_match(
                proposal,
                world_id=world_id,
                worldline_id=worldline_id,
            )
        if proposal.proposal_kind in SUPPORTED_TRACE_ONLY_APPLY_KINDS:
            return {
                "applied_ref_kind": "authoring_import_proposal",
                "applied_ref_id": str(proposal.id),
                "canonical_mutation": False,
            }
        return None

    def _apply_persona_candidate(
        self,
        proposal: AuthoringImportProposal,
        *,
        world_id: uuid.UUID,
    ) -> dict[str, Any]:
        agent_id = proposal.target_ref_id or _uuid_from_payload(
            proposal.proposed_payload_json.get("agent_id")
        )
        if agent_id is None:
            raise AuthoringValidationError("persona proposal requires target agent")
        agent = self._agent_required(world_id, agent_id)
        payload = proposal.proposed_payload_json
        persona_text = str(payload.get("persona_text") or "").strip()
        if not persona_text:
            raise AuthoringValidationError("persona proposal requires persona_text")
        behavior_policy = _dict_or_empty(payload.get("behavior_policy"))
        policy_config = {
            "authoring": {
                "source_kind": "character_memory_distillation",
                "proposal_id": str(proposal.id),
                "run_id": str(proposal.run_id),
                "source_fragment_id": None
                if proposal.source_fragment_id is None
                else str(proposal.source_fragment_id),
                "model_invocation_id": payload.get("model_invocation_id"),
            }
        }
        persona = AgentPersonaService(self._session).upsert(
            AgentPersonaUpsert(
                world_id=world_id,
                agent_id=agent.id,
                persona_text=persona_text,
                behavior_policy=behavior_policy,
                policy_plugin_config=policy_config,
                is_enabled=True,
            )
        )
        structured_profile = _dict_or_empty(payload.get("character_profile"))
        agent.character_profile = {
            **agent.character_profile,
            "distilled_persona": structured_profile,
            "distilled_persona_source": {
                "proposal_id": str(proposal.id),
                "run_id": str(proposal.run_id),
                "model_invocation_id": payload.get("model_invocation_id"),
            },
        }
        self._session.flush()
        return {
            "applied_ref_kind": "agent_persona",
            "applied_ref_id": str(persona.id),
            "agent_id": str(agent.id),
            "canonical_mutation": False,
            "persona_mutation": True,
        }

    def _apply_memory_candidate(
        self,
        proposal: AuthoringImportProposal,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
    ) -> dict[str, Any]:
        if proposal.target_ref_id is None:
            raise AuthoringValidationError("memory proposal requires target agent")
        agent = self._agent_required(world_id, proposal.target_ref_id)
        payload = proposal.proposed_payload_json
        content = str(payload.get("content") or "").strip()
        if not content:
            raise AuthoringValidationError("memory proposal requires content")
        memory = AgentMemoryItem(
            id=uuid.uuid4(),
            world_id=world_id,
            worldline_id=worldline_id,
            agent_id=agent.id,
            source_event_id=None,
            content=content,
            metadata_json={
                "source_kind": "authoring_distillation",
                "proposal_id": str(proposal.id),
                "run_id": str(proposal.run_id),
                "source_fragment_id": None
                if proposal.source_fragment_id is None
                else str(proposal.source_fragment_id),
                "memory_kind": payload.get("memory_kind", "fact"),
                "route_key": payload.get("route_key"),
                "confidence": proposal.confidence,
                "model_invocation_id": payload.get("model_invocation_id"),
                "source_evidence": _dict_or_empty(payload.get("source_evidence")),
            },
            embedding=deterministic_embedding(content),
            visibility="private",
            is_active=True,
        )
        self._session.add(memory)
        self._session.flush()
        return {
            "applied_ref_kind": "agent_memory_item",
            "applied_ref_id": str(memory.id),
            "agent_id": str(agent.id),
            "canonical_mutation": False,
            "memory_mutation": True,
        }

    def _apply_sprite_asset_match(
        self,
        proposal: AuthoringImportProposal,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
    ) -> dict[str, Any]:
        payload = proposal.proposed_payload_json
        media_asset_id = self._asset_match_media_asset_id(payload)
        source_asset_id = _uuid_from_payload(payload.get("source_asset_id"))
        agent = self._agent_for_sprite_payload(world_id, payload)
        style_key = _safe_key(str(payload.get("style_key") or "galgame-import"), "galgame-import")
        expression_key = _safe_key(str(payload.get("expression_key") or "neutral"), "neutral")
        pose_key = _optional_safe_key(payload.get("pose_key"))
        outfit_key = _optional_safe_key(payload.get("outfit_key"))
        mood_tags = tuple(_string_list(payload.get("mood_tags")))
        visual = VisualAssetService(self._session)
        sprite_set = self._find_sprite_set(world_id, worldline_id, agent.id, style_key)
        created_sprite_set = False
        if sprite_set is None:
            try:
                created = visual.create_sprite_set(
                    SpriteSetCreate(
                        world_id=world_id,
                        worldline_id=worldline_id,
                        agent_id=agent.id,
                        style_key=style_key,
                        display_name=f"{agent.display_name} imported sprites",
                        visibility=SpriteBindingVisibility.WORLD_ADMIN,
                        metadata_json=_visual_mapping_metadata(
                            proposal,
                            source_asset_id=source_asset_id,
                            media_asset_id=media_asset_id,
                            mapping_kind="sprite_set",
                        ),
                    )
                )
            except VisualValidationError as exc:
                raise AuthoringValidationError(str(exc)) from exc
            sprite_set = self._find_sprite_set(world_id, worldline_id, agent.id, created.style_key)
            created_sprite_set = True
        if sprite_set is None:
            raise AuthoringValidationError("sprite set apply failed")
        existing_variant = self._find_sprite_variant(
            world_id,
            worldline_id,
            sprite_set.id,
            media_asset_id,
            expression_key,
            pose_key,
            outfit_key,
        )
        if existing_variant is not None:
            variant_id = existing_variant.id
            reused_variant = True
        else:
            try:
                variant = visual.create_sprite_variant(
                    SpriteVariantCreate(
                        world_id=world_id,
                        worldline_id=worldline_id,
                        sprite_set_id=sprite_set.id,
                        asset_id=media_asset_id,
                        expression_key=expression_key,
                        pose_key=pose_key,
                        outfit_key=outfit_key,
                        mood_tags=mood_tags,
                        is_default=self._should_default_sprite_variant(
                            world_id,
                            sprite_set.id,
                            expression_key,
                        ),
                        visibility=SpriteBindingVisibility.WORLD_ADMIN,
                        metadata_json=_visual_mapping_metadata(
                            proposal,
                            source_asset_id=source_asset_id,
                            media_asset_id=media_asset_id,
                            mapping_kind="sprite_variant",
                        ),
                    )
                )
            except VisualValidationError as exc:
                raise AuthoringValidationError(str(exc)) from exc
            variant_id = variant.id
            reused_variant = False
        self._mark_media_generation_reference_candidate(
            media_asset_id,
            proposal,
            reference_role="character_reference",
        )
        return {
            "applied_ref_kind": "character_sprite_variant",
            "applied_ref_id": str(variant_id),
            "sprite_set_id": str(sprite_set.id),
            "agent_id": str(agent.id),
            "media_asset_id": str(media_asset_id),
            "source_asset_id": None if source_asset_id is None else str(source_asset_id),
            "created_sprite_set": created_sprite_set,
            "reused_variant": reused_variant,
            "canonical_mutation": False,
            "visual_binding_mutation": True,
            "generation_reference_candidate": True,
        }

    def _apply_background_asset_match(
        self,
        proposal: AuthoringImportProposal,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
    ) -> dict[str, Any]:
        payload = proposal.proposed_payload_json
        media_asset_id = self._asset_match_media_asset_id(payload)
        source_asset_id = _uuid_from_payload(payload.get("source_asset_id"))
        scene_id = _uuid_from_payload(payload.get("scene_id"))
        location_key = _safe_key(
            str(payload.get("location_key") or payload.get("cg_key") or "imported"),
            "imported",
        )
        time_of_day = _optional_safe_key(payload.get("time_of_day"))
        weather_key = _optional_safe_key(payload.get("weather_key"))
        existing = self._find_background(
            world_id,
            worldline_id,
            media_asset_id,
            scene_id,
            location_key,
            time_of_day,
            weather_key,
        )
        if existing is not None:
            background_id = existing.id
            reused_background = True
        else:
            visual = VisualAssetService(self._session)
            try:
                background = visual.create_background(
                    SceneBackgroundCreate(
                        world_id=world_id,
                        worldline_id=worldline_id,
                        scene_id=scene_id,
                        location_key=location_key,
                        time_of_day=time_of_day,
                        weather_key=weather_key,
                        asset_id=media_asset_id,
                        is_default=self._should_default_background(
                            world_id,
                            worldline_id,
                            scene_id,
                            location_key,
                        ),
                        visibility=BackgroundVisibility.WORLD_ADMIN,
                        metadata_json=_visual_mapping_metadata(
                            proposal,
                            source_asset_id=source_asset_id,
                            media_asset_id=media_asset_id,
                            mapping_kind="scene_background",
                        ),
                    )
                )
            except VisualValidationError as exc:
                raise AuthoringValidationError(str(exc)) from exc
            background_id = background.id
            reused_background = False
        self._mark_media_generation_reference_candidate(
            media_asset_id,
            proposal,
            reference_role="style_reference",
        )
        return {
            "applied_ref_kind": "scene_background_profile",
            "applied_ref_id": str(background_id),
            "media_asset_id": str(media_asset_id),
            "source_asset_id": None if source_asset_id is None else str(source_asset_id),
            "reused_background": reused_background,
            "canonical_mutation": False,
            "visual_binding_mutation": True,
            "generation_reference_candidate": True,
        }

    def _apply_cg_asset_match(
        self,
        proposal: AuthoringImportProposal,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
    ) -> dict[str, Any]:
        payload = proposal.proposed_payload_json
        media_asset_id = self._asset_match_media_asset_id(payload)
        source_asset_id = _uuid_from_payload(payload.get("source_asset_id"))
        media_asset = self._media_asset_required(world_id, worldline_id, media_asset_id)
        if media_asset.asset_kind != "image":
            raise AuthoringValidationError("CG asset match requires image media")
        metadata = dict(media_asset.metadata_json)
        bindings = list(metadata.get("galgame_cg_bindings", []))
        binding = {
            "proposal_id": str(proposal.id),
            "run_id": str(proposal.run_id),
            "source_asset_id": None if source_asset_id is None else str(source_asset_id),
            "cg_key": _safe_key(str(payload.get("cg_key") or "imported-cg"), "imported-cg"),
            "route_key": _optional_safe_key(payload.get("route_key")),
            "scene_id": str(_uuid_from_payload(payload.get("scene_id")))
            if _uuid_from_payload(payload.get("scene_id")) is not None
            else None,
            "reference_role": "style_reference",
        }
        if binding not in bindings:
            bindings.append(binding)
        metadata["galgame_cg_bindings"] = bindings
        metadata["generation_reference_candidate"] = True
        metadata["generation_reference_roles"] = sorted(
            set(_string_list(metadata.get("generation_reference_roles")) + ["style_reference"])
        )
        media_asset.metadata_json = metadata
        self._session.flush()
        return {
            "applied_ref_kind": "media_asset",
            "applied_ref_id": str(media_asset.id),
            "media_asset_id": str(media_asset.id),
            "source_asset_id": None if source_asset_id is None else str(source_asset_id),
            "cg_binding": binding,
            "canonical_mutation": False,
            "visual_binding_mutation": False,
            "generation_reference_candidate": True,
        }

    def _apply_voice_asset_match(
        self,
        proposal: AuthoringImportProposal,
        *,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
    ) -> dict[str, Any]:
        payload = proposal.proposed_payload_json
        media_asset_id = self._asset_match_media_asset_id(payload)
        source_asset_id = _uuid_from_payload(payload.get("source_asset_id"))
        media_asset = self._media_asset_required(world_id, worldline_id, media_asset_id)
        if media_asset.asset_kind != "audio":
            raise AuthoringValidationError("voice asset match requires audio media")
        agent = self._agent_for_voice_payload(world_id, payload)
        voice_label = _safe_key(
            str(payload.get("voice_label") or payload.get("speaker_label") or agent.agent_key),
            agent.agent_key,
        )
        profile_key = _safe_key(f"{agent.agent_key}-{voice_label}", agent.agent_key)
        provider_id = _uuid_from_payload(payload.get("provider_id"))
        provider_voice_id = _optional_text(payload.get("provider_voice_id")) or _optional_text(
            payload.get("voice_id")
        )
        style_key = _optional_safe_key(payload.get("style_key"))
        emotion_key = _optional_safe_key(payload.get("emotion_key"))
        speech = VoiceProfileService(self._session)
        profile = self._find_voice_profile(world_id, worldline_id, profile_key)
        created_profile = False
        if profile is None:
            try:
                created = speech.create_profile(
                    VoiceProfileCreate(
                        world_id=world_id,
                        worldline_id=worldline_id,
                        profile_key=profile_key,
                        display_name=f"{agent.display_name} imported voice",
                        description="Reviewed galgame voice reference mapping.",
                        visibility=VoiceProfileVisibility.WORLD_ADMIN,
                        owner_kind=VoiceProfileOwnerKind.AGENT,
                        owner_agent_id=agent.id,
                        provider_integration_id=provider_id,
                        provider_voice_id=provider_voice_id,
                        default_language=_optional_text(payload.get("language")),
                        supported_languages=_string_list(payload.get("supported_languages")),
                        voice_kind=VoiceKind.IMPORTED
                        if provider_voice_id is None
                        else VoiceKind.EXTERNAL_PROVIDER,
                        reference_asset_id=media_asset.id,
                        consent_status=VoiceConsentStatus.ADMIN_AUTHORIZED,
                        usage_policy_json={
                            "source": "reviewed_galgame_import",
                            "review_apply_required": True,
                            "allow_tts_reference": True,
                        },
                        metadata_json=_voice_mapping_metadata(
                            proposal,
                            source_asset_id=source_asset_id,
                            media_asset_id=media_asset.id,
                            style_key=style_key,
                            emotion_key=emotion_key,
                        ),
                    )
                )
            except SpeechValidationError as exc:
                raise AuthoringValidationError(str(exc)) from exc
            profile = self._session.get(VoiceProfile, created.id)
            created_profile = True
        if profile is None:
            raise AuthoringValidationError("voice profile apply failed")
        binding = self._find_voice_binding(
            world_id,
            worldline_id,
            agent.id,
            profile.id,
            VoiceBindingRole.DEFAULT.value,
        )
        created_binding = False
        if binding is None:
            try:
                created_binding_record = speech.bind_agent_voice(
                    AgentVoiceProfileBindingCreate(
                        world_id=world_id,
                        worldline_id=worldline_id,
                        agent_id=agent.id,
                        voice_profile_id=profile.id,
                        binding_role=VoiceBindingRole.DEFAULT,
                        is_default=self._should_default_voice_binding(
                            world_id,
                            worldline_id,
                            agent.id,
                        ),
                        style_overrides_json=_voice_style_overrides(
                            style_key=style_key,
                            emotion_key=emotion_key,
                        ),
                    )
                )
            except SpeechValidationError as exc:
                raise AuthoringValidationError(str(exc)) from exc
            binding_id = created_binding_record.id
            created_binding = True
        else:
            binding_id = binding.id
        self._mark_media_voice_reference(
            media_asset.id,
            proposal,
            agent_id=agent.id,
            voice_profile_id=profile.id,
        )
        return {
            "applied_ref_kind": "agent_voice_profile_binding",
            "applied_ref_id": str(binding_id),
            "voice_profile_id": str(profile.id),
            "agent_id": str(agent.id),
            "media_asset_id": str(media_asset.id),
            "source_asset_id": None if source_asset_id is None else str(source_asset_id),
            "provider_id": None if provider_id is None else str(provider_id),
            "provider_voice_id": provider_voice_id,
            "created_voice_profile": created_profile,
            "created_binding": created_binding,
            "canonical_mutation": False,
            "voice_binding_mutation": True,
        }

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


def _distillation_prompt(
    agent: Agent,
    fragments: list[AuthoringSourceFragment],
) -> str:
    excerpts = "\n".join(
        f"- fragment {index}: {fragment.excerpt_text.strip()[:700]}"
        for index, fragment in enumerate(fragments, start=1)
        if fragment.excerpt_text is not None
    )
    return (
        "Summarize the following traceable character source excerpts into a persona card, "
        "speech style, relationship summary, key initial memories, emotional baseline, "
        "taboo or secret knowledge, route-specific facts, sample dialogue style, and "
        "uncertainty notes. Return concise structured JSON only; do not mutate runtime state.\n"
        f"Character: {agent.display_name}\n"
        f"Source excerpts:\n{excerpts}"
    )


def _persona_payload(
    *,
    agent: Agent,
    fragments: list[AuthoringSourceFragment],
    model_invocation_id: uuid.UUID,
) -> dict[str, Any]:
    text = _combined_excerpt(fragments)
    speech_style = _infer_speech_style(text)
    emotional_baseline = _infer_emotional_baseline(text)
    key_memories = _initial_memory_texts(fragments)[:5]
    persona_text = (
        f"{agent.display_name} is initialized from reviewed source fragments. "
        f"Speech style: {speech_style}. Emotional baseline: {emotional_baseline}. "
        f"Key evidence: {'; '.join(key_memories[:3]) or 'source evidence pending review'}."
    )
    return {
        "source_kind": "authoring_distillation",
        "agent_id": str(agent.id),
        "model_invocation_id": str(model_invocation_id),
        "persona_text": persona_text[:4000],
        "speech_style": speech_style,
        "relationship_summary": _relationship_summary(text),
        "key_memories": key_memories,
        "emotional_baseline": emotional_baseline,
        "taboo_secret_knowledge": _secret_notes(text),
        "route_specific_facts": _route_facts(text),
        "sample_dialogue_style": _sample_dialogue_style(text),
        "uncertainty_conflict_notes": _uncertainty_notes(text),
        "behavior_policy": {
            "source": "authoring_distillation",
            "review_required": True,
            "preserve_character_voice": True,
        },
        "character_profile": {
            "speech_style": speech_style,
            "relationship_summary": _relationship_summary(text),
            "emotional_baseline": emotional_baseline,
            "route_specific_facts": _route_facts(text),
            "uncertainty_conflict_notes": _uncertainty_notes(text),
        },
        "source_evidence": _source_evidence(fragments),
    }


def _memory_payloads(
    *,
    agent: Agent,
    fragments: list[AuthoringSourceFragment],
    model_invocation_id: uuid.UUID,
) -> list[dict[str, Any]]:
    memory_texts = _initial_memory_texts(fragments)
    if not memory_texts:
        memory_texts = [f"{agent.display_name} has reviewed source evidence for initial play."]
    payloads: list[dict[str, Any]] = []
    for index, content in enumerate(memory_texts[:8], start=1):
        fragment = fragments[min(index - 1, len(fragments) - 1)]
        payloads.append(
            {
                "source_kind": "authoring_distillation",
                "agent_id": str(agent.id),
                "source_fragment_id": str(fragment.id),
                "model_invocation_id": str(model_invocation_id),
                "memory_kind": _memory_kind(content),
                "content": content[:1000],
                "route_key": _first_marker_value(content, ("route:", "[route:")),
                "source_evidence": {
                    "fragment_id": str(fragment.id),
                    "fragment_key": fragment.fragment_key,
                    "sequence": fragment.sequence,
                },
            }
        )
    return payloads


def _visual_profile_payload(
    *,
    agent: Agent,
    fragments: list[AuthoringSourceFragment],
    model_invocation_id: uuid.UUID,
) -> dict[str, Any]:
    text = _combined_excerpt(fragments)
    return {
        "source_kind": "authoring_distillation",
        "agent_id": str(agent.id),
        "model_invocation_id": str(model_invocation_id),
        "review_only": True,
        "recommended_prompt_fragments": [
            agent.display_name,
            _infer_emotional_baseline(text),
            _infer_speech_style(text),
        ],
        "negative_prompt_fragments": [],
        "reference_asset_ids": [],
        "workflow_binding_recommendation": {
            "default_workflow_template": None,
            "expression_workflow_template": None,
            "cg_workflow_template": None,
        },
        "source_evidence": _source_evidence(fragments),
    }


def _distillation_evidence(
    *,
    source_refs: list[str],
    model_invocation_id: uuid.UUID,
    evidence_kind: str,
) -> dict[str, Any]:
    return {
        "evidence_kind": evidence_kind,
        "source_fragment_ids": source_refs,
        "model_invocation_id": str(model_invocation_id),
        "provider_execution": True,
    }


def _combined_excerpt(fragments: list[AuthoringSourceFragment]) -> str:
    return "\n".join(
        (fragment.excerpt_text or "").strip()
        for fragment in fragments
        if (fragment.excerpt_text or "").strip()
    )


def _source_evidence(fragments: list[AuthoringSourceFragment]) -> list[dict[str, Any]]:
    return [
        {
            "fragment_id": str(fragment.id),
            "fragment_key": fragment.fragment_key,
            "fragment_kind": fragment.fragment_kind,
            "sequence": fragment.sequence,
        }
        for fragment in fragments
    ]


def _initial_memory_texts(fragments: list[AuthoringSourceFragment]) -> list[str]:
    memories: list[str] = []
    for fragment in fragments:
        for line in (fragment.excerpt_text or "").splitlines():
            normalized = line.strip()
            if not normalized:
                continue
            lower = normalized.lower()
            if lower.startswith(("fact:", "episode:", "episodic:", "memory:", "preference:")):
                memories.append(normalized.split(":", 1)[1].strip())
            elif ":" in normalized and len(normalized) <= 220:
                memories.append(normalized)
            elif len(normalized) <= 160:
                memories.append(normalized)
    deduped: list[str] = []
    seen: set[str] = set()
    for memory in memories:
        key = memory.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(memory)
    return deduped


def _infer_speech_style(text: str) -> str:
    lowered = text.lower()
    if "whisper" in lowered or "quiet" in lowered:
        return "quiet and restrained"
    if "!" in text:
        return "expressive and energetic"
    if "formal" in lowered or "council" in lowered:
        return "polite and formal"
    return "grounded and conversational"


def _infer_emotional_baseline(text: str) -> str:
    lowered = text.lower()
    if "guarded" in lowered or "secret" in lowered:
        return "guarded"
    if "happy" in lowered or "curious" in lowered:
        return "curious"
    if "sad" in lowered or "lonely" in lowered:
        return "melancholic"
    return "neutral"


def _relationship_summary(text: str) -> str:
    for line in text.splitlines():
        lowered = line.lower()
        if "relationship" in lowered or "trust" in lowered or "friend" in lowered:
            return line.strip()[:500]
    return "No explicit relationship summary; keep interactions source-grounded."


def _secret_notes(text: str) -> list[str]:
    return [
        line.strip()[:500]
        for line in text.splitlines()
        if "secret" in line.lower() or "taboo" in line.lower()
    ][:5]


def _route_facts(text: str) -> list[str]:
    return [
        line.strip()[:500]
        for line in text.splitlines()
        if "route" in line.lower() or "choice" in line.lower()
    ][:5]


def _sample_dialogue_style(text: str) -> str:
    for line in text.splitlines():
        if ":" in line and len(line.strip()) <= 240:
            return line.strip()
    return "Use short, source-grounded dialogue."


def _uncertainty_notes(text: str) -> list[str]:
    return [
        line.strip()[:500]
        for line in text.splitlines()
        if "uncertain" in line.lower() or "maybe" in line.lower() or "conflict" in line.lower()
    ][:5]


def _memory_kind(content: str) -> str:
    lowered = content.lower()
    if "trust" in lowered or "friend" in lowered or "relationship" in lowered:
        return "relationship"
    if "like" in lowered or "prefer" in lowered:
        return "preference"
    if "met " in lowered or "episode" in lowered:
        return "episodic"
    return "fact"


def _first_marker_value(text: str, markers: tuple[str, ...]) -> str | None:
    lowered = text.lower()
    for marker in markers:
        index = lowered.find(marker)
        if index >= 0:
            return text[index + len(marker) :].strip(" ]")[:80] or None
    return None


def _uuid_from_payload(value: object) -> uuid.UUID | None:
    if isinstance(value, uuid.UUID):
        return value
    if not isinstance(value, str):
        return None
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


def _dict_or_empty(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _visual_mapping_metadata(
    proposal: AuthoringImportProposal,
    *,
    source_asset_id: uuid.UUID | None,
    media_asset_id: uuid.UUID,
    mapping_kind: str,
) -> dict[str, Any]:
    return {
        "source_kind": "galgame_visual_asset_mapping",
        "proposal_id": str(proposal.id),
        "run_id": str(proposal.run_id),
        "source_fragment_id": None
        if proposal.source_fragment_id is None
        else str(proposal.source_fragment_id),
        "source_asset_id": None if source_asset_id is None else str(source_asset_id),
        "media_asset_id": str(media_asset_id),
        "mapping_kind": mapping_kind,
        "review_apply": True,
    }


def _voice_mapping_metadata(
    proposal: AuthoringImportProposal,
    *,
    source_asset_id: uuid.UUID | None,
    media_asset_id: uuid.UUID,
    style_key: str | None,
    emotion_key: str | None,
) -> dict[str, Any]:
    return {
        "source_kind": "galgame_voice_profile_mapping",
        "proposal_id": str(proposal.id),
        "run_id": str(proposal.run_id),
        "source_fragment_id": None
        if proposal.source_fragment_id is None
        else str(proposal.source_fragment_id),
        "source_asset_id": None if source_asset_id is None else str(source_asset_id),
        "media_asset_id": str(media_asset_id),
        "style_key": style_key,
        "emotion_key": emotion_key,
        "review_apply": True,
    }


def _voice_style_overrides(
    *,
    style_key: str | None,
    emotion_key: str | None,
) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    if style_key is not None:
        overrides["style_key"] = style_key
    if emotion_key is not None:
        overrides["emotion"] = emotion_key
    return overrides


def _label_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")


def _safe_key(value: str, fallback: str) -> str:
    normalized = _label_key(value)
    return normalized or fallback


def _optional_safe_key(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = _label_key(value)
    return normalized or None


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list | tuple | set):
        return []
    return sorted(
        {
            item.strip().lower()
            for item in value
            if isinstance(item, str) and item.strip()
        }
    )


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
