from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from noveland.asset_generation.contracts import (
    AssetGenerationApplyRequest,
    AssetGenerationApplyResult,
    AssetGenerationPolicyCreate,
    AssetGenerationPolicyRead,
    AssetGenerationPolicyStatus,
    AssetGenerationPolicyUpdate,
    AssetGenerationPreviewRequest,
    AssetGenerationPreviewResult,
    AssetGenerationProposalKind,
    AssetGenerationProposalRead,
    AssetGenerationProposalStatus,
    AssetGenerationRunKind,
    AssetGenerationRunRead,
    AssetGenerationRunStatus,
    MediaJobCancelSupersededRequest,
    MediaJobCancelSupersededResult,
    MediaJobReprioritizeRequest,
    MediaJobReprioritizeResult,
    _assert_safe_json,
)
from noveland.asset_generation.models import (
    AssetGenerationPolicy,
    AssetGenerationProposal,
    AssetGenerationRun,
)
from noveland.conversations.models import (
    ConversationSession,
    ConversationTurn,
    ConversationTurnPresentation,
)
from noveland.media.contracts import (
    MediaJobCreate,
    MediaJobKind,
    MediaJobRecord,
    MediaJobStatus,
    MediaJobUpdate,
)
from noveland.media.errors import MediaConflictError, MediaValidationError
from noveland.media.models import MediaJob
from noveland.media.service import MediaJobService
from noveland.providers.contracts import ProviderIntegrationRead, ProviderKind
from noveland.providers.registry import ProviderNotFoundError, ProviderRegistryService
from noveland.speech.models import AgentVoiceProfileBinding, VoiceProfile
from noveland.visual.models import (
    CharacterSpriteSet,
    CharacterSpriteVariant,
    SceneBackgroundProfile,
)
from noveland.worlds.worldlines import worldline_or_404
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class AssetGenerationValidationError(ValueError):
    pass


class AssetGenerationNotFoundError(LookupError):
    pass


TERMINAL_JOB_STATUSES = {
    MediaJobStatus.SUCCEEDED.value,
    MediaJobStatus.FAILED.value,
    MediaJobStatus.CANCELLED.value,
}
RESTRICTED_VISIBILITIES = {"developer_only", "hidden"}


@dataclass(frozen=True)
class _ProposalCandidate:
    proposal_kind: AssetGenerationProposalKind
    target_ref_kind: str
    target_ref_id: uuid.UUID
    reason: str
    evidence_json: dict[str, Any]
    priority: int
    estimated_cost: float | None
    provider_kind: str | None
    provider_id: uuid.UUID | None
    request_json: dict[str, Any]
    status: AssetGenerationProposalStatus = AssetGenerationProposalStatus.PROPOSED


class AssetGenerationService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_policy(self, create: AssetGenerationPolicyCreate) -> AssetGenerationPolicyRead:
        worldline_id = self._worldline_id(create.world_id, create.worldline_id)
        model = AssetGenerationPolicy(
            id=uuid.uuid4(),
            world_id=create.world_id,
            worldline_id=worldline_id,
            policy_key=create.policy_key,
            status=create.status.value,
            budget_json=create.budget_json,
            lookahead_json=create.lookahead_json,
            provider_preferences_json=create.provider_preferences_json,
            rules_json=create.rules_json,
        )
        self._session.add(model)
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise AssetGenerationValidationError("asset generation policy already exists") from exc
        self._session.refresh(model)
        return _policy_record(model)

    def list_policies(
        self,
        world_id: uuid.UUID,
        *,
        worldline_id: uuid.UUID,
        include_deleted: bool = False,
    ) -> list[AssetGenerationPolicyRead]:
        resolved_worldline_id = self._worldline_id(world_id, worldline_id)
        statement = select(AssetGenerationPolicy).where(
            AssetGenerationPolicy.world_id == world_id,
            AssetGenerationPolicy.worldline_id == resolved_worldline_id,
        )
        if not include_deleted:
            statement = statement.where(
                AssetGenerationPolicy.status != AssetGenerationPolicyStatus.DELETED.value
            )
        statement = statement.order_by(AssetGenerationPolicy.policy_key)
        return [_policy_record(model) for model in self._session.scalars(statement).all()]

    def update_policy(
        self,
        world_id: uuid.UUID,
        policy_id: uuid.UUID,
        update: AssetGenerationPolicyUpdate,
    ) -> AssetGenerationPolicyRead:
        model = self._policy_required(world_id, policy_id)
        if update.status is not None:
            model.status = update.status.value
        if update.budget_json is not None:
            model.budget_json = update.budget_json
        if update.lookahead_json is not None:
            model.lookahead_json = update.lookahead_json
        if update.provider_preferences_json is not None:
            model.provider_preferences_json = update.provider_preferences_json
        if update.rules_json is not None:
            model.rules_json = update.rules_json
        self._session.flush()
        self._session.refresh(model)
        return _policy_record(model)

    def preview(
        self,
        world_id: uuid.UUID,
        request: AssetGenerationPreviewRequest,
        *,
        actor_ref: str,
    ) -> AssetGenerationPreviewResult:
        worldline_id = self._worldline_id(world_id, request.worldline_id)
        policy = (
            None
            if request.policy_id is None
            else self._policy_required(world_id, request.policy_id)
        )
        if policy is not None and policy.worldline_id != worldline_id:
            raise AssetGenerationValidationError("policy must belong to preview worldline")
        self._validate_conversation(world_id, worldline_id, request.conversation_id)
        self._validate_turn(world_id, worldline_id, request.current_turn_id)

        run = AssetGenerationRun(
            id=uuid.uuid4(),
            world_id=world_id,
            worldline_id=worldline_id,
            policy_id=None if policy is None else policy.id,
            run_kind=AssetGenerationRunKind.PREVIEW.value,
            status=AssetGenerationRunStatus.SUCCEEDED.value,
            summary_json={},
            created_by_actor_ref=actor_ref,
        )
        self._session.add(run)
        self._session.flush()

        candidates = self._build_candidates(world_id, worldline_id, request)
        candidates = self._apply_budget_and_limit(candidates, request, policy)
        for candidate in candidates:
            self._add_proposal(run.id, world_id, worldline_id, candidate)
        run.summary_json = _run_summary(candidates, media_job_count=0)
        self._session.flush()
        return AssetGenerationPreviewResult(run=self.get_run(world_id, run.id))

    def apply(
        self,
        world_id: uuid.UUID,
        request: AssetGenerationApplyRequest,
        *,
        actor_ref: str,
    ) -> AssetGenerationApplyResult:
        worldline_id = self._worldline_id(world_id, request.worldline_id)
        source_run = self._run_required(world_id, request.run_id)
        if source_run.worldline_id != worldline_id:
            raise AssetGenerationValidationError("run must belong to apply worldline")
        proposals = self._proposals_for_apply(source_run.id, request.proposal_ids)
        apply_run = AssetGenerationRun(
            id=uuid.uuid4(),
            world_id=world_id,
            worldline_id=worldline_id,
            policy_id=source_run.policy_id,
            run_kind=AssetGenerationRunKind.APPLY.value,
            status=AssetGenerationRunStatus.SUCCEEDED.value,
            summary_json={},
            created_by_actor_ref=actor_ref,
        )
        self._session.add(apply_run)
        self._session.flush()

        jobs: list[MediaJobRecord] = []
        for proposal in proposals:
            job = self._create_media_job_from_proposal(proposal, actor_ref=actor_ref)
            proposal.status = AssetGenerationProposalStatus.APPLIED.value
            proposal.resulting_media_job_id = job.id
            jobs.append(job)
        apply_run.summary_json = {
            "source_run_id": str(source_run.id),
            "applied_count": len(jobs),
            "media_job_count": len(jobs),
        }
        self._session.flush()
        return AssetGenerationApplyResult(
            source_run_id=source_run.id,
            apply_run=self.get_run(world_id, apply_run.id),
            applied_proposals=[_proposal_record(model) for model in proposals],
            media_jobs=jobs,
        )

    def get_run(self, world_id: uuid.UUID, run_id: uuid.UUID) -> AssetGenerationRunRead:
        run = self._run_required(world_id, run_id)
        proposals = self._session.scalars(
            select(AssetGenerationProposal)
            .where(AssetGenerationProposal.run_id == run.id)
            .order_by(AssetGenerationProposal.priority, AssetGenerationProposal.created_at),
        ).all()
        return _run_record(run, [_proposal_record(model) for model in proposals])

    def reprioritize_jobs(
        self,
        world_id: uuid.UUID,
        request: MediaJobReprioritizeRequest,
    ) -> MediaJobReprioritizeResult:
        worldline_id = self._worldline_id(world_id, request.worldline_id)
        jobs = self._target_jobs(world_id, worldline_id, request.job_ids, request.invalidation_key)
        updated: list[MediaJobRecord] = []
        media_jobs = MediaJobService(self._session)
        for job in jobs:
            updated.append(
                media_jobs.update_job(
                    world_id,
                    job.id,
                    MediaJobUpdate(priority=request.priority),
                )
            )
        return MediaJobReprioritizeResult(jobs=updated)

    def cancel_superseded_jobs(
        self,
        world_id: uuid.UUID,
        request: MediaJobCancelSupersededRequest,
    ) -> MediaJobCancelSupersededResult:
        worldline_id = self._worldline_id(world_id, request.worldline_id)
        jobs = self._target_jobs(world_id, worldline_id, request.job_ids, request.invalidation_key)
        media_jobs = MediaJobService(self._session)
        cancelled: list[uuid.UUID] = []
        skipped: list[uuid.UUID] = []
        for job in jobs:
            if job.status in TERMINAL_JOB_STATUSES:
                skipped.append(job.id)
                continue
            try:
                media_jobs.cancel_job(world_id, job.id)
                cancelled.append(job.id)
            except MediaConflictError:
                skipped.append(job.id)
        return MediaJobCancelSupersededResult(
            cancelled_job_ids=cancelled,
            skipped_job_ids=skipped,
        )

    def _build_candidates(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        request: AssetGenerationPreviewRequest,
    ) -> list[_ProposalCandidate]:
        candidates: list[_ProposalCandidate] = []
        turns = self._turns_for_preview(world_id, worldline_id, request)
        image_provider = self._resolve_provider(
            world_id,
            provider_kind=ProviderKind.IMAGE_GENERATION,
            capability_key="supports_image_generation",
        )
        speech_provider = self._resolve_provider(
            world_id,
            provider_kind=ProviderKind.TEXT_TO_SPEECH,
            capability_key="supports_tts",
        )
        for turn, session_model, presentation in turns:
            priority = _priority_for_turn(turn, session_model, request.current_turn_id)
            if request.include_visual:
                candidates.extend(
                    self._visual_candidates(
                        world_id,
                        worldline_id,
                        turn,
                        session_model,
                        presentation,
                        priority,
                        image_provider,
                    )
                )
            if request.include_speech:
                speech = self._speech_candidate(
                    world_id,
                    worldline_id,
                    turn,
                    session_model,
                    presentation,
                    priority,
                    speech_provider,
                )
                if speech is not None:
                    candidates.append(speech)
        return sorted(candidates, key=lambda item: (item.priority, item.proposal_kind.value))

    def _visual_candidates(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        turn: ConversationTurn,
        session_model: ConversationSession,
        presentation: ConversationTurnPresentation | None,
        priority: int,
        image_provider: ProviderIntegrationRead | None,
    ) -> list[_ProposalCandidate]:
        if turn.speaker_agent_id is None:
            return []
        sprite_ready = _presentation_has_sprite(presentation) or self._has_sprite_variant(
            world_id,
            worldline_id,
            turn.speaker_agent_id,
        )
        background_ready = _presentation_has_background(presentation) or self._has_background(
            world_id,
            worldline_id,
            session_model.scene_id,
        )
        candidates: list[_ProposalCandidate] = []
        if not sprite_ready:
            candidates.append(
                self._provider_backed_candidate(
                    AssetGenerationProposalKind.CHARACTER_SPRITE,
                    turn,
                    session_model,
                    priority + 1,
                    image_provider,
                    "missing character sprite variant",
                    estimated_cost=0.03,
                    action="generate_character_sprite",
                )
            )
        if not background_ready:
            candidates.append(
                self._provider_backed_candidate(
                    AssetGenerationProposalKind.SCENE_BACKGROUND,
                    turn,
                    session_model,
                    priority + 2,
                    image_provider,
                    "missing scene background asset",
                    estimated_cost=0.03,
                    action="generate_scene_background",
                )
            )
        composite_missing = presentation is None or presentation.composite_scene_asset_id is None
        if composite_missing and sprite_ready and background_ready:
            candidates.append(
                _ProposalCandidate(
                    proposal_kind=AssetGenerationProposalKind.COMPOSITE_SCENE,
                    target_ref_kind="conversation_turn",
                    target_ref_id=turn.id,
                    reason="turn is missing a composite scene asset",
                    evidence_json=_turn_evidence(turn, session_model, missing="composite_scene"),
                    priority=priority,
                    estimated_cost=0.0,
                    provider_kind=None,
                    provider_id=None,
                    request_json=_job_request(
                        "compose_scene",
                        worldline_id,
                        turn,
                        session_model,
                    ),
                )
            )
        return candidates

    def _speech_candidate(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        turn: ConversationTurn,
        session_model: ConversationSession,
        presentation: ConversationTurnPresentation | None,
        priority: int,
        speech_provider: ProviderIntegrationRead | None,
    ) -> _ProposalCandidate | None:
        if turn.speaker_agent_id is None:
            return None
        if presentation is not None and presentation.tts_media_asset_id is not None:
            return None
        voice_profile_id = self._default_voice_profile_id(
            world_id,
            worldline_id,
            turn.speaker_agent_id,
        )
        if voice_profile_id is None:
            return _ProposalCandidate(
                proposal_kind=AssetGenerationProposalKind.SPEECH_AUDIO,
                target_ref_kind="conversation_turn",
                target_ref_id=turn.id,
                reason="missing default voice profile binding",
                evidence_json=_turn_evidence(turn, session_model, missing="voice_profile"),
                priority=priority + 3,
                estimated_cost=0.01,
                provider_kind=None,
                provider_id=None,
                request_json=_job_request(
                    "generate_speech_audio",
                    worldline_id,
                    turn,
                    session_model,
                ),
                status=AssetGenerationProposalStatus.BLOCKED,
            )
        candidate = self._provider_backed_candidate(
            AssetGenerationProposalKind.SPEECH_AUDIO,
            turn,
            session_model,
            priority + 3,
            speech_provider,
            "turn is missing generated speech audio",
            estimated_cost=0.01,
            action="generate_speech_audio",
        )
        candidate.request_json["voice_profile_id"] = str(voice_profile_id)
        return candidate

    def _provider_backed_candidate(
        self,
        kind: AssetGenerationProposalKind,
        turn: ConversationTurn,
        session_model: ConversationSession,
        priority: int,
        provider: ProviderIntegrationRead | None,
        reason: str,
        *,
        estimated_cost: float,
        action: str,
    ) -> _ProposalCandidate:
        if provider is None:
            return _ProposalCandidate(
                proposal_kind=kind,
                target_ref_kind="conversation_turn",
                target_ref_id=turn.id,
                reason=f"{reason}; missing provider capability",
                evidence_json=_turn_evidence(turn, session_model, missing=kind.value),
                priority=priority,
                estimated_cost=estimated_cost,
                provider_kind=None,
                provider_id=None,
                request_json=_job_request(action, session_model.worldline_id, turn, session_model),
                status=AssetGenerationProposalStatus.BLOCKED,
            )
        return _ProposalCandidate(
            proposal_kind=kind,
            target_ref_kind="conversation_turn",
            target_ref_id=turn.id,
            reason=reason,
            evidence_json=_turn_evidence(turn, session_model, missing=kind.value),
            priority=priority,
            estimated_cost=estimated_cost,
            provider_kind=provider.provider_kind.value,
            provider_id=provider.id,
            request_json=_job_request(action, session_model.worldline_id, turn, session_model),
        )

    def _apply_budget_and_limit(
        self,
        candidates: list[_ProposalCandidate],
        request: AssetGenerationPreviewRequest,
        policy: AssetGenerationPolicy | None,
    ) -> list[_ProposalCandidate]:
        budget = request.max_total_estimated_cost
        if budget is None and policy is not None:
            budget = _float_from_json(policy.budget_json.get("max_total_estimated_cost"))
        max_proposals = request.max_proposals
        if max_proposals is None and policy is not None:
            max_proposals = _int_from_json(policy.lookahead_json.get("max_proposals"))
        accepted_count = 0
        running_cost = 0.0
        output: list[_ProposalCandidate] = []
        for candidate in candidates:
            if candidate.status == AssetGenerationProposalStatus.PROPOSED:
                cost = 0.0 if candidate.estimated_cost is None else candidate.estimated_cost
                if budget is not None and running_cost + cost > budget:
                    output.append(_blocked(candidate, "cost budget exceeded"))
                    continue
                if max_proposals is not None and accepted_count >= max_proposals:
                    output.append(_blocked(candidate, "proposal limit exceeded"))
                    continue
                running_cost += cost
                accepted_count += 1
            output.append(candidate)
        return output

    def _add_proposal(
        self,
        run_id: uuid.UUID,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        candidate: _ProposalCandidate,
    ) -> None:
        _assert_safe_json(candidate.evidence_json, "proposal evidence")
        _assert_safe_json(candidate.request_json, "proposal request")
        self._session.add(
            AssetGenerationProposal(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                run_id=run_id,
                proposal_kind=candidate.proposal_kind.value,
                target_ref_kind=candidate.target_ref_kind,
                target_ref_id=candidate.target_ref_id,
                reason=candidate.reason,
                evidence_json=candidate.evidence_json,
                priority=candidate.priority,
                estimated_cost=candidate.estimated_cost,
                provider_kind=candidate.provider_kind,
                provider_id=candidate.provider_id,
                request_json=candidate.request_json,
                status=candidate.status.value,
            )
        )

    def _create_media_job_from_proposal(
        self,
        proposal: AssetGenerationProposal,
        *,
        actor_ref: str,
    ) -> MediaJobRecord:
        request_json = {
            **proposal.request_json,
            "asset_generation_proposal_id": str(proposal.id),
            "asset_generation_run_id": str(proposal.run_id),
        }
        _assert_safe_json(request_json, "media job request")
        provider_config_json = (
            {} if proposal.provider_id is None else {"provider_id": str(proposal.provider_id)}
        )
        try:
            return MediaJobService(self._session).create_job(
                MediaJobCreate(
                    world_id=proposal.world_id,
                    worldline_id=proposal.worldline_id,
                    conversation_id=_uuid_from_json(proposal.request_json.get("conversation_id")),
                    turn_id=(
                        proposal.target_ref_id
                        if proposal.target_ref_kind == "conversation_turn"
                        else _uuid_from_json(proposal.request_json.get("turn_id"))
                    ),
                    agent_id=_uuid_from_json(proposal.request_json.get("agent_id")),
                    job_kind=_job_kind_for_proposal(
                        AssetGenerationProposalKind(proposal.proposal_kind)
                    ),
                    provider_kind=proposal.provider_kind,
                    priority=proposal.priority,
                    cancel_policy="cancel_superseded",
                    dedupe_key=_invalidation_key(proposal),
                    invalidation_key=_invalidation_key(proposal),
                    provider_config_json=provider_config_json,
                    request_json=request_json,
                ),
                actor_ref=actor_ref,
            )
        except MediaValidationError as exc:
            raise AssetGenerationValidationError(str(exc)) from exc

    def _turns_for_preview(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        request: AssetGenerationPreviewRequest,
    ) -> list[tuple[ConversationTurn, ConversationSession, ConversationTurnPresentation | None]]:
        statement = (
            select(ConversationTurn, ConversationSession)
            .join(ConversationSession, ConversationTurn.session_id == ConversationSession.id)
            .where(
                ConversationSession.world_id == world_id,
                ConversationSession.worldline_id == worldline_id,
            )
        )
        if request.conversation_id is not None:
            statement = statement.where(ConversationSession.id == request.conversation_id)
        statement = statement.order_by(
            ConversationSession.created_at.desc(),
            ConversationTurn.turn_index,
        )
        rows = self._session.execute(statement).all()
        if not rows:
            return []
        current_index: int | None = None
        if request.current_turn_id is not None:
            current_turn = next(
                (
                    turn
                    for turn, _session_model in rows
                    if turn.id == request.current_turn_id
                ),
                None,
            )
            if current_turn is None:
                raise AssetGenerationValidationError(
                    "current turn must belong to preview worldline"
                )
            current_index = current_turn.turn_index
        output: list[
            tuple[ConversationTurn, ConversationSession, ConversationTurnPresentation | None]
        ] = []
        for turn, session_model in rows:
            if (
                current_index is not None
                and turn.turn_index > current_index + request.lookahead_turns
            ):
                continue
            presentation = self._session.scalars(
                select(ConversationTurnPresentation).where(
                    ConversationTurnPresentation.turn_id == turn.id
                )
            ).one_or_none()
            output.append((turn, session_model, presentation))
        return output

    def _has_sprite_variant(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        agent_id: uuid.UUID,
    ) -> bool:
        return (
            self._session.scalars(
                select(CharacterSpriteVariant.id)
                .join(
                    CharacterSpriteSet,
                    CharacterSpriteVariant.sprite_set_id == CharacterSpriteSet.id,
                )
                .where(
                    CharacterSpriteSet.world_id == world_id,
                    CharacterSpriteSet.worldline_id == worldline_id,
                    CharacterSpriteSet.agent_id == agent_id,
                    CharacterSpriteSet.status == "active",
                    CharacterSpriteSet.visibility.not_in(RESTRICTED_VISIBILITIES),
                    CharacterSpriteVariant.world_id == world_id,
                    CharacterSpriteVariant.worldline_id == worldline_id,
                    CharacterSpriteVariant.status == "active",
                    CharacterSpriteVariant.visibility.not_in(RESTRICTED_VISIBILITIES),
                )
                .limit(1)
            ).first()
            is not None
        )

    def _has_background(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        scene_id: uuid.UUID | None,
    ) -> bool:
        statement = select(SceneBackgroundProfile.id).where(
            SceneBackgroundProfile.world_id == world_id,
            SceneBackgroundProfile.worldline_id == worldline_id,
            SceneBackgroundProfile.status == "active",
            SceneBackgroundProfile.visibility.not_in(RESTRICTED_VISIBILITIES),
        )
        if scene_id is not None:
            statement = statement.where(
                (SceneBackgroundProfile.scene_id == scene_id)
                | (SceneBackgroundProfile.is_default.is_(True))
            )
        return self._session.scalars(statement.limit(1)).first() is not None

    def _default_voice_profile_id(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        agent_id: uuid.UUID,
    ) -> uuid.UUID | None:
        model = self._session.scalars(
            select(AgentVoiceProfileBinding)
            .join(VoiceProfile, AgentVoiceProfileBinding.voice_profile_id == VoiceProfile.id)
            .where(
                AgentVoiceProfileBinding.world_id == world_id,
                AgentVoiceProfileBinding.agent_id == agent_id,
                (
                    (AgentVoiceProfileBinding.worldline_id == worldline_id)
                    | (AgentVoiceProfileBinding.worldline_id.is_(None))
                ),
                VoiceProfile.world_id == world_id,
                VoiceProfile.status == "active",
                VoiceProfile.visibility.not_in(RESTRICTED_VISIBILITIES),
            )
            .order_by(
                AgentVoiceProfileBinding.is_default.desc(),
                AgentVoiceProfileBinding.priority,
                AgentVoiceProfileBinding.created_at,
            )
            .limit(1)
        ).first()
        return None if model is None else model.voice_profile_id

    def _resolve_provider(
        self,
        world_id: uuid.UUID,
        *,
        provider_kind: ProviderKind,
        capability_key: str,
    ) -> ProviderIntegrationRead | None:
        try:
            return ProviderRegistryService(self._session).resolve_provider_for_capability(
                world_id,
                provider_kind=provider_kind,
                capability_key=capability_key,
            )
        except ProviderNotFoundError:
            return None

    def _target_jobs(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        job_ids: tuple[uuid.UUID, ...],
        invalidation_key: str | None,
    ) -> list[MediaJob]:
        statement = select(MediaJob).where(
            MediaJob.world_id == world_id,
            MediaJob.worldline_id == worldline_id,
        )
        if job_ids:
            statement = statement.where(MediaJob.id.in_(job_ids))
        if invalidation_key is not None:
            statement = statement.where(MediaJob.invalidation_key == invalidation_key)
        models = list(self._session.scalars(statement).all())
        if job_ids and len({model.id for model in models}) != len(set(job_ids)):
            raise AssetGenerationNotFoundError("media job not found in worldline")
        return models

    def _proposals_for_apply(
        self,
        run_id: uuid.UUID,
        proposal_ids: tuple[uuid.UUID, ...],
    ) -> list[AssetGenerationProposal]:
        statement = select(AssetGenerationProposal).where(
            AssetGenerationProposal.run_id == run_id,
            AssetGenerationProposal.status == AssetGenerationProposalStatus.PROPOSED.value,
        )
        if proposal_ids:
            statement = statement.where(AssetGenerationProposal.id.in_(proposal_ids))
        statement = statement.order_by(
            AssetGenerationProposal.priority,
            AssetGenerationProposal.created_at,
        )
        proposals = list(self._session.scalars(statement).all())
        if proposal_ids and len({proposal.id for proposal in proposals}) != len(set(proposal_ids)):
            raise AssetGenerationValidationError("selected proposals must be proposed in the run")
        return proposals

    def _policy_required(self, world_id: uuid.UUID, policy_id: uuid.UUID) -> AssetGenerationPolicy:
        model = self._session.get(AssetGenerationPolicy, policy_id)
        if (
            model is None
            or model.world_id != world_id
            or model.status == AssetGenerationPolicyStatus.DELETED.value
        ):
            raise AssetGenerationNotFoundError("asset generation policy not found")
        return model

    def _run_required(self, world_id: uuid.UUID, run_id: uuid.UUID) -> AssetGenerationRun:
        model = self._session.get(AssetGenerationRun, run_id)
        if model is None or model.world_id != world_id:
            raise AssetGenerationNotFoundError("asset generation run not found")
        return model

    def _validate_conversation(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        conversation_id: uuid.UUID | None,
    ) -> None:
        if conversation_id is None:
            return
        model = self._session.get(ConversationSession, conversation_id)
        if model is None or model.world_id != world_id or model.worldline_id != worldline_id:
            raise AssetGenerationValidationError("conversation must belong to worldline")

    def _validate_turn(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        turn_id: uuid.UUID | None,
    ) -> None:
        if turn_id is None:
            return
        row = self._session.execute(
            select(ConversationTurn, ConversationSession)
            .join(ConversationSession, ConversationTurn.session_id == ConversationSession.id)
            .where(ConversationTurn.id == turn_id)
        ).one_or_none()
        if row is None:
            raise AssetGenerationValidationError("turn must belong to worldline")
        _turn, session_model = row
        if session_model.world_id != world_id or session_model.worldline_id != worldline_id:
            raise AssetGenerationValidationError("turn must belong to worldline")

    def _worldline_id(self, world_id: uuid.UUID, worldline_id: uuid.UUID) -> uuid.UUID:
        try:
            return worldline_or_404(self._session, world_id, worldline_id).id
        except ValueError as exc:
            raise AssetGenerationValidationError("worldline not found") from exc


def _presentation_has_sprite(presentation: ConversationTurnPresentation | None) -> bool:
    return presentation is not None and presentation.sprite_variant_id is not None


def _presentation_has_background(presentation: ConversationTurnPresentation | None) -> bool:
    return presentation is not None and presentation.background_asset_id is not None


def _turn_evidence(
    turn: ConversationTurn,
    session_model: ConversationSession,
    *,
    missing: str,
) -> dict[str, Any]:
    evidence: dict[str, Any] = {
        "conversation_id": str(session_model.id),
        "turn_id": str(turn.id),
        "turn_index": turn.turn_index,
        "missing": missing,
        "conversation_status": session_model.status,
    }
    if turn.speaker_agent_id is not None:
        evidence["agent_id"] = str(turn.speaker_agent_id)
    if session_model.scene_id is not None:
        evidence["scene_id"] = str(session_model.scene_id)
    return evidence


def _job_request(
    action: str,
    worldline_id: uuid.UUID | None,
    turn: ConversationTurn,
    session_model: ConversationSession,
) -> dict[str, Any]:
    if worldline_id is None:
        raise AssetGenerationValidationError("asset generation requires a worldline")
    request: dict[str, Any] = {
        "action": action,
        "worldline_id": str(worldline_id),
        "conversation_id": str(session_model.id),
        "turn_id": str(turn.id),
        "text_source_ref": f"conversation_turn:{turn.id}",
        "invalidation_key": f"turn:{turn.id}:{action}",
    }
    if turn.speaker_agent_id is not None:
        request["agent_id"] = str(turn.speaker_agent_id)
    if session_model.scene_id is not None:
        request["scene_id"] = str(session_model.scene_id)
    return request


def _priority_for_turn(
    turn: ConversationTurn,
    session_model: ConversationSession,
    current_turn_id: uuid.UUID | None,
) -> int:
    if current_turn_id is not None and turn.id == current_turn_id:
        return 0
    if session_model.status in {"running", "paused"}:
        return 10
    if current_turn_id is not None:
        return 20
    return 30


def _blocked(candidate: _ProposalCandidate, reason: str) -> _ProposalCandidate:
    return _ProposalCandidate(
        proposal_kind=candidate.proposal_kind,
        target_ref_kind=candidate.target_ref_kind,
        target_ref_id=candidate.target_ref_id,
        reason=f"{candidate.reason}; {reason}",
        evidence_json={**candidate.evidence_json, "blocked_reason": reason},
        priority=candidate.priority,
        estimated_cost=candidate.estimated_cost,
        provider_kind=candidate.provider_kind,
        provider_id=candidate.provider_id,
        request_json=candidate.request_json,
        status=AssetGenerationProposalStatus.BLOCKED,
    )


def _run_summary(candidates: list[_ProposalCandidate], *, media_job_count: int) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    for candidate in candidates:
        status_counts[candidate.status.value] = status_counts.get(candidate.status.value, 0) + 1
    return {
        "proposal_count": len(candidates),
        "media_job_count": media_job_count,
        "status_counts": status_counts,
    }


def _job_kind_for_proposal(kind: AssetGenerationProposalKind) -> MediaJobKind:
    if kind == AssetGenerationProposalKind.SPEECH_AUDIO:
        return MediaJobKind.SPEECH_GENERATION
    if kind == AssetGenerationProposalKind.COMPOSITE_SCENE:
        return MediaJobKind.COMPOSITION
    return MediaJobKind.IMAGE_GENERATION


def _invalidation_key(proposal: AssetGenerationProposal) -> str:
    value = proposal.request_json.get("invalidation_key")
    if isinstance(value, str) and value:
        return value[:160]
    return f"asset-generation:{proposal.proposal_kind}:{proposal.target_ref_id}"[:160]


def _uuid_from_json(value: object) -> uuid.UUID | None:
    if isinstance(value, str):
        return uuid.UUID(value)
    return None


def _float_from_json(value: object) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None


def _int_from_json(value: object) -> int | None:
    if isinstance(value, int):
        return value
    return None


def _policy_record(model: AssetGenerationPolicy) -> AssetGenerationPolicyRead:
    return AssetGenerationPolicyRead(
        id=model.id,
        world_id=model.world_id,
        worldline_id=model.worldline_id,
        policy_key=model.policy_key,
        status=AssetGenerationPolicyStatus(model.status),
        budget_json=model.budget_json,
        lookahead_json=model.lookahead_json,
        provider_preferences_json=model.provider_preferences_json,
        rules_json=model.rules_json,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _proposal_record(model: AssetGenerationProposal) -> AssetGenerationProposalRead:
    return AssetGenerationProposalRead(
        id=model.id,
        world_id=model.world_id,
        worldline_id=model.worldline_id,
        run_id=model.run_id,
        proposal_kind=AssetGenerationProposalKind(model.proposal_kind),
        target_ref_kind=model.target_ref_kind,
        target_ref_id=model.target_ref_id,
        reason=model.reason,
        evidence_json=model.evidence_json,
        priority=model.priority,
        estimated_cost=model.estimated_cost,
        provider_kind=model.provider_kind,
        provider_id=model.provider_id,
        request_json=model.request_json,
        status=AssetGenerationProposalStatus(model.status),
        resulting_media_job_id=model.resulting_media_job_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _run_record(
    model: AssetGenerationRun,
    proposals: list[AssetGenerationProposalRead],
) -> AssetGenerationRunRead:
    return AssetGenerationRunRead(
        id=model.id,
        world_id=model.world_id,
        worldline_id=model.worldline_id,
        policy_id=model.policy_id,
        run_kind=AssetGenerationRunKind(model.run_kind),
        status=AssetGenerationRunStatus(model.status),
        summary_json=model.summary_json,
        created_by_actor_ref=model.created_by_actor_ref,
        created_at=model.created_at,
        updated_at=model.updated_at,
        proposals=proposals,
    )
