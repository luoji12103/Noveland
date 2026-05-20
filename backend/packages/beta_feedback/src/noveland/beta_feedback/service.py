from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any, TypeVar

from noveland.agents.models import AgentPersona
from noveland.beta_feedback.contracts import (
    BetaFeedbackEvidenceKind,
    BetaFeedbackEvidenceRef,
    BetaFeedbackIssueType,
    BetaFeedbackRepairProposalRef,
    BetaFeedbackReportCreate,
    BetaFeedbackReportRead,
    BetaFeedbackReportStatus,
    BetaFeedbackReportTriage,
    BetaFeedbackSeverity,
)
from noveland.beta_feedback.models import BetaFeedbackReport
from noveland.conversations.models import (
    ConversationSession,
    ConversationTurn,
    ConversationTurnPresentation,
)
from noveland.invocations.models import ModelInvocation
from noveland.media.models import MediaAsset, MediaJob
from noveland.memory.models import AgentMemoryItem
from noveland.providers.models import ProviderIntegration
from noveland.speech.models import VoiceProfile
from noveland.visual.models import (
    CharacterSpriteSet,
    CharacterSpriteVariant,
    SceneBackgroundProfile,
)
from noveland.worlds.models import PlayerActorProfile, Scene, World, Worldline, WorldMembership
from noveland.worlds.worldlines import worldline_or_404
from sqlalchemy import select
from sqlalchemy.orm import Session

_SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "base64",
    "bearer_token",
    "bytes",
    "client_secret",
    "event_payload",
    "file_path",
    "filesystem_path",
    "invite_token",
    "object_path",
    "password",
    "path",
    "private_key",
    "prompt_snapshot",
    "raw_event_payload",
    "raw_output",
    "raw_prompt",
    "secret",
    "storage_uri",
    "token",
}
_LEAK_PATTERN = re.compile(
    r"(storage_uri|media://|file://|s3://|gs://|/root/|/tmp/|base64,|BEGIN PRIVATE KEY|"
    r"raw_prompt|raw_output|prompt_snapshot|sk-[A-Za-z0-9]|bearer\s+)",
    re.IGNORECASE,
)
_SAFE_TEXT_LIMIT = 1_500
_SAFE_JSON_LIMIT = 12_000
_RESTRICTED_VISIBILITY = {"developer_only", "hidden"}
_WORLDLINELESS_EVIDENCE = {
    BetaFeedbackEvidenceKind.PROVIDER,
    BetaFeedbackEvidenceKind.PERSONA,
    BetaFeedbackEvidenceKind.QUOTA,
    BetaFeedbackEvidenceKind.UX,
    BetaFeedbackEvidenceKind.OTHER,
}
_ModelT = TypeVar("_ModelT")


class BetaFeedbackError(ValueError):
    pass


class BetaFeedbackNotFoundError(BetaFeedbackError):
    pass


class BetaFeedbackValidationError(BetaFeedbackError):
    pass


class BetaFeedbackService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_report(
        self,
        world_id: uuid.UUID,
        reporter_user_id: uuid.UUID,
        request: BetaFeedbackReportCreate,
        *,
        actor_ref: str,
        actor_is_admin: bool = False,
    ) -> BetaFeedbackReportRead:
        self._world_or_404(world_id)
        worldline = self._worldline_or_404(world_id, request.worldline_id)
        self._membership_or_404(world_id, reporter_user_id)
        self._validate_safe_text(request.title, "title")
        self._validate_safe_text(request.description, "description")
        self._validate_safe_text(request.reporter_note, "reporter_note")
        player_actor_id = self._validate_player_actor(
            world_id,
            worldline.id,
            request.player_actor_id,
            reporter_user_id=reporter_user_id,
        )
        evidence_refs = self._safe_evidence_refs(
            world_id,
            worldline.id,
            request.evidence_refs,
            actor_is_admin=actor_is_admin,
        )
        metadata = self._sanitize_json_object(request.metadata, "metadata")
        report = BetaFeedbackReport(
            world_id=world_id,
            worldline_id=worldline.id,
            reporter_user_id=reporter_user_id,
            player_actor_id=player_actor_id,
            issue_type=request.issue_type.value,
            severity=request.severity.value,
            status=BetaFeedbackReportStatus.SUBMITTED.value,
            title=request.title,
            description=request.description,
            reporter_note=request.reporter_note,
            evidence_refs_json=evidence_refs,
            repair_proposal_refs_json=[],
            metadata_json=metadata,
        )
        self._session.add(report)
        self._session.flush()
        return self._read(report)

    def list_reports(
        self,
        world_id: uuid.UUID,
        *,
        actor_user_id: uuid.UUID,
        actor_is_admin: bool,
        worldline_id: uuid.UUID | None = None,
        status: BetaFeedbackReportStatus | None = None,
        issue_type: str | None = None,
        limit: int = 100,
    ) -> list[BetaFeedbackReportRead]:
        self._world_or_404(world_id)
        self._membership_or_404(world_id, actor_user_id)
        if worldline_id is not None:
            self._worldline_or_404(world_id, worldline_id)
        statement = (
            select(BetaFeedbackReport)
            .where(BetaFeedbackReport.world_id == world_id)
            .order_by(BetaFeedbackReport.created_at.desc())
            .limit(max(1, min(limit, 200)))
        )
        if not actor_is_admin:
            statement = statement.where(BetaFeedbackReport.reporter_user_id == actor_user_id)
        if worldline_id is not None:
            statement = statement.where(BetaFeedbackReport.worldline_id == worldline_id)
        if status is not None:
            statement = statement.where(BetaFeedbackReport.status == status.value)
        if issue_type is not None:
            statement = statement.where(BetaFeedbackReport.issue_type == issue_type)
        return [self._read(report) for report in self._session.scalars(statement).all()]

    def get_report(
        self,
        world_id: uuid.UUID,
        report_id: uuid.UUID,
        *,
        actor_user_id: uuid.UUID,
        actor_is_admin: bool,
    ) -> BetaFeedbackReportRead:
        self._membership_or_404(world_id, actor_user_id)
        report = self._report_or_404(world_id, report_id)
        if not actor_is_admin and report.reporter_user_id != actor_user_id:
            raise BetaFeedbackNotFoundError("beta feedback report not found")
        return self._read(report)

    def triage_report(
        self,
        world_id: uuid.UUID,
        report_id: uuid.UUID,
        request: BetaFeedbackReportTriage,
        *,
        actor_ref: str,
    ) -> BetaFeedbackReportRead:
        report = self._report_or_404(world_id, report_id)
        self._validate_safe_text(request.triage_note, "triage_note")
        report.status = request.status.value
        if request.severity is not None:
            report.severity = request.severity.value
        if request.evidence_refs is not None:
            report.evidence_refs_json = self._safe_evidence_refs(
                world_id,
                report.worldline_id,
                request.evidence_refs,
                actor_is_admin=True,
            )
        if request.repair_proposal_refs is not None:
            report.repair_proposal_refs_json = [
                self._safe_repair_ref(ref) for ref in request.repair_proposal_refs
            ]
            if (
                request.status == BetaFeedbackReportStatus.TRIAGED
                and report.repair_proposal_refs_json
            ):
                report.status = BetaFeedbackReportStatus.LINKED_TO_REPAIR.value
        if request.metadata is not None:
            report.metadata_json = self._sanitize_json_object(request.metadata, "metadata")
        report.triage_note = request.triage_note
        report.triaged_by_actor_ref = actor_ref
        report.triaged_at = datetime.now(UTC)
        self._session.flush()
        return self._read(report)

    def link_repair_proposals(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        report_refs: dict[uuid.UUID, tuple[BetaFeedbackRepairProposalRef, ...]],
        *,
        actor_ref: str,
    ) -> list[BetaFeedbackReportRead]:
        self._world_or_404(world_id)
        self._worldline_or_404(world_id, worldline_id)
        updated: list[BetaFeedbackReportRead] = []
        for report_id, refs in report_refs.items():
            report = self._report_or_404(world_id, report_id)
            if report.worldline_id != worldline_id:
                raise BetaFeedbackValidationError(
                    "repair feedback report belongs to another worldline"
                )
            existing = list(
                self._sanitize_json_array(
                    report.repair_proposal_refs_json,
                    "repair_proposal_refs",
                )
            )
            seen = {str(item.get("proposal_id")) for item in existing}
            for ref in refs:
                safe_ref = self._safe_repair_ref(ref)
                if str(safe_ref["proposal_id"]) not in seen:
                    existing.append(safe_ref)
                    seen.add(str(safe_ref["proposal_id"]))
            report.repair_proposal_refs_json = existing
            if existing:
                report.status = BetaFeedbackReportStatus.LINKED_TO_REPAIR.value
                report.triaged_by_actor_ref = actor_ref
                report.triaged_at = datetime.now(UTC)
            updated.append(self._read(report))
        self._session.flush()
        return updated

    def _safe_evidence_refs(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        evidence_refs: tuple[BetaFeedbackEvidenceRef, ...],
        *,
        actor_is_admin: bool,
    ) -> list[dict[str, Any]]:
        return [
            self._safe_evidence_ref(
                world_id,
                worldline_id,
                ref,
                actor_is_admin=actor_is_admin,
            )
            for ref in evidence_refs
        ]

    def _safe_evidence_ref(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        ref: BetaFeedbackEvidenceRef,
        *,
        actor_is_admin: bool,
    ) -> dict[str, Any]:
        self._validate_safe_text(ref.label, "evidence label")
        self._validate_safe_text(ref.role, "evidence role")
        if ref.worldline_id is not None and ref.worldline_id != worldline_id:
            raise BetaFeedbackValidationError("evidence ref belongs to another worldline")
        if ref.kind not in _WORLDLINELESS_EVIDENCE and ref.id is None:
            raise BetaFeedbackValidationError(f"{ref.kind.value} evidence requires an id")
        resolved_worldline_id = self._validate_evidence_target(
            world_id,
            worldline_id,
            ref.kind,
            ref.id,
            actor_is_admin=actor_is_admin,
        )
        if resolved_worldline_id is not None and resolved_worldline_id != worldline_id:
            raise BetaFeedbackValidationError("evidence ref belongs to another worldline")
        payload = ref.model_dump(mode="json", exclude_none=True)
        if resolved_worldline_id is not None:
            payload["worldline_id"] = str(resolved_worldline_id)
        payload["metadata"] = self._sanitize_json_object(ref.metadata, "evidence metadata")
        return payload

    def _validate_evidence_target(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        kind: BetaFeedbackEvidenceKind,
        target_id: uuid.UUID | None,
        *,
        actor_is_admin: bool,
    ) -> uuid.UUID | None:
        if kind == BetaFeedbackEvidenceKind.WORLDLINE:
            if target_id != worldline_id:
                raise BetaFeedbackValidationError("worldline evidence must match report worldline")
            self._worldline_or_404(world_id, worldline_id)
            return worldline_id
        if kind == BetaFeedbackEvidenceKind.SCENE:
            scene = self._get_required(Scene, target_id, "scene not found")
            if scene.world_id != world_id:
                raise BetaFeedbackNotFoundError("scene not found")
            return worldline_id
        if kind == BetaFeedbackEvidenceKind.CONVERSATION:
            conversation = self._get_required(
                ConversationSession,
                target_id,
                "conversation not found",
            )
            self._validate_worldline_scope(
                conversation.world_id,
                conversation.worldline_id,
                world_id,
                worldline_id,
                "conversation",
            )
            return conversation.worldline_id
        if kind == BetaFeedbackEvidenceKind.TURN:
            turn = self._get_required(ConversationTurn, target_id, "turn not found")
            conversation = self._get_required(
                ConversationSession,
                turn.session_id,
                "conversation not found",
            )
            self._validate_worldline_scope(
                conversation.world_id,
                conversation.worldline_id,
                world_id,
                worldline_id,
                "turn",
            )
            return conversation.worldline_id
        if kind == BetaFeedbackEvidenceKind.PRESENTATION:
            presentation = self._get_required(
                ConversationTurnPresentation,
                target_id,
                "presentation not found",
            )
            self._validate_worldline_scope(
                presentation.world_id,
                presentation.worldline_id,
                world_id,
                worldline_id,
                "presentation",
            )
            return presentation.worldline_id
        if kind == BetaFeedbackEvidenceKind.MEDIA_ASSET:
            asset = self._get_required(MediaAsset, target_id, "media asset not found")
            self._validate_worldline_scope(
                asset.world_id,
                asset.worldline_id,
                world_id,
                worldline_id,
                "media asset",
            )
            self._reject_restricted_visibility(asset.visibility, actor_is_admin, "media asset")
            return asset.worldline_id
        if kind == BetaFeedbackEvidenceKind.MEDIA_JOB:
            job = self._get_required(MediaJob, target_id, "media job not found")
            self._validate_worldline_scope(
                job.world_id,
                job.worldline_id,
                world_id,
                worldline_id,
                "media job",
            )
            return job.worldline_id
        if kind == BetaFeedbackEvidenceKind.INVOCATION:
            invocation = self._get_required(
                ModelInvocation,
                target_id,
                "model invocation not found",
            )
            self._validate_worldline_scope(
                invocation.world_id,
                invocation.worldline_id,
                world_id,
                worldline_id,
                "model invocation",
            )
            return invocation.worldline_id
        if kind == BetaFeedbackEvidenceKind.PERSONA:
            persona = self._get_required(AgentPersona, target_id, "persona not found")
            if persona.world_id != world_id:
                raise BetaFeedbackNotFoundError("persona not found")
            return None
        if kind == BetaFeedbackEvidenceKind.MEMORY:
            memory = self._get_required(AgentMemoryItem, target_id, "memory not found")
            self._validate_worldline_scope(
                memory.world_id,
                memory.worldline_id,
                world_id,
                worldline_id,
                "memory",
            )
            return memory.worldline_id
        if kind == BetaFeedbackEvidenceKind.VOICE_PROFILE:
            voice = self._get_required(VoiceProfile, target_id, "voice profile not found")
            self._validate_worldline_scope(
                voice.world_id,
                voice.worldline_id,
                world_id,
                worldline_id,
                "voice profile",
            )
            self._reject_restricted_visibility(voice.visibility, actor_is_admin, "voice profile")
            return voice.worldline_id
        if kind == BetaFeedbackEvidenceKind.SPRITE_SET:
            sprite_set = self._get_required(CharacterSpriteSet, target_id, "sprite set not found")
            self._validate_worldline_scope(
                sprite_set.world_id,
                sprite_set.worldline_id,
                world_id,
                worldline_id,
                "sprite set",
            )
            self._reject_restricted_visibility(
                sprite_set.visibility,
                actor_is_admin,
                "sprite set",
            )
            return sprite_set.worldline_id
        if kind == BetaFeedbackEvidenceKind.SPRITE_VARIANT:
            variant = self._get_required(
                CharacterSpriteVariant,
                target_id,
                "sprite variant not found",
            )
            self._validate_worldline_scope(
                variant.world_id,
                variant.worldline_id,
                world_id,
                worldline_id,
                "sprite variant",
            )
            self._reject_restricted_visibility(
                variant.visibility,
                actor_is_admin,
                "sprite variant",
            )
            return variant.worldline_id
        if kind == BetaFeedbackEvidenceKind.BACKGROUND_PROFILE:
            background = self._get_required(
                SceneBackgroundProfile,
                target_id,
                "background profile not found",
            )
            self._validate_worldline_scope(
                background.world_id,
                background.worldline_id,
                world_id,
                worldline_id,
                "background profile",
            )
            self._reject_restricted_visibility(
                background.visibility,
                actor_is_admin,
                "background profile",
            )
            return background.worldline_id
        if kind == BetaFeedbackEvidenceKind.PROVIDER:
            provider = self._get_required(
                ProviderIntegration,
                target_id,
                "provider integration not found",
            )
            if provider.world_id is not None and provider.world_id != world_id:
                raise BetaFeedbackNotFoundError("provider integration not found")
            self._reject_restricted_visibility(
                provider.visibility,
                actor_is_admin,
                "provider integration",
            )
            return None
        if kind == BetaFeedbackEvidenceKind.PLAYER_ACTOR:
            actor = self._get_required(PlayerActorProfile, target_id, "player actor not found")
            self._validate_worldline_scope(
                actor.world_id,
                actor.worldline_id,
                world_id,
                worldline_id,
                "player actor",
            )
            return actor.worldline_id
        return None

    def _validate_player_actor(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        player_actor_id: uuid.UUID | None,
        *,
        reporter_user_id: uuid.UUID,
    ) -> uuid.UUID | None:
        if player_actor_id is None:
            return None
        actor = self._session.get(PlayerActorProfile, player_actor_id)
        if (
            actor is None
            or actor.world_id != world_id
            or actor.worldline_id != worldline_id
            or actor.user_id != reporter_user_id
            or not actor.is_active
        ):
            raise BetaFeedbackNotFoundError("player actor not found")
        return actor.id

    def _validate_worldline_scope(
        self,
        target_world_id: uuid.UUID | None,
        target_worldline_id: uuid.UUID | None,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        label: str,
    ) -> None:
        if target_world_id != world_id:
            raise BetaFeedbackNotFoundError(f"{label} not found")
        if target_worldline_id is not None and target_worldline_id != worldline_id:
            raise BetaFeedbackValidationError(f"{label} belongs to another worldline")

    def _reject_restricted_visibility(
        self,
        visibility: str,
        actor_is_admin: bool,
        label: str,
    ) -> None:
        if not actor_is_admin and visibility in _RESTRICTED_VISIBILITY:
            raise BetaFeedbackNotFoundError(f"{label} not found")

    def _safe_repair_ref(self, ref: BetaFeedbackRepairProposalRef) -> dict[str, Any]:
        self._validate_safe_text(ref.proposal_kind, "proposal_kind")
        self._validate_safe_text(ref.status, "proposal status")
        return {
            **ref.model_dump(mode="json", exclude_none=True),
            "metadata": self._sanitize_json_object(ref.metadata, "repair metadata"),
        }

    def _report_or_404(self, world_id: uuid.UUID, report_id: uuid.UUID) -> BetaFeedbackReport:
        report = self._session.get(BetaFeedbackReport, report_id)
        if report is None or report.world_id != world_id:
            raise BetaFeedbackNotFoundError("beta feedback report not found")
        return report

    def _world_or_404(self, world_id: uuid.UUID) -> World:
        world = self._session.get(World, world_id)
        if world is None:
            raise BetaFeedbackNotFoundError("world not found")
        return world

    def _worldline_or_404(self, world_id: uuid.UUID, worldline_id: uuid.UUID) -> Worldline:
        try:
            return worldline_or_404(self._session, world_id, worldline_id)
        except ValueError as exc:
            raise BetaFeedbackNotFoundError("worldline not found") from exc

    def _membership_or_404(self, world_id: uuid.UUID, user_id: uuid.UUID) -> WorldMembership:
        membership = self._session.scalars(
            select(WorldMembership).where(
                WorldMembership.world_id == world_id,
                WorldMembership.user_id == user_id,
            )
        ).one_or_none()
        if membership is None:
            raise BetaFeedbackNotFoundError("world membership not found")
        return membership

    def _get_required(
        self,
        model_type: type[_ModelT],
        target_id: uuid.UUID | None,
        message: str,
    ) -> _ModelT:
        if target_id is None:
            raise BetaFeedbackValidationError(message)
        model = self._session.get(model_type, target_id)
        if model is None:
            raise BetaFeedbackNotFoundError(message)
        return model

    def _read(self, report: BetaFeedbackReport) -> BetaFeedbackReportRead:
        return BetaFeedbackReportRead(
            id=report.id,
            world_id=report.world_id,
            worldline_id=report.worldline_id,
            reporter_user_id=report.reporter_user_id,
            player_actor_id=report.player_actor_id,
            issue_type=BetaFeedbackIssueType(report.issue_type),
            severity=BetaFeedbackSeverity(report.severity),
            status=BetaFeedbackReportStatus(report.status),
            title=self._safe_text(report.title),
            description=self._safe_text(report.description),
            reporter_note=(
                None if report.reporter_note is None else self._safe_text(report.reporter_note)
            ),
            evidence_refs=tuple(
                BetaFeedbackEvidenceRef.model_validate(item)
                for item in self._sanitize_json_array(report.evidence_refs_json, "evidence_refs")
            ),
            repair_proposal_refs=tuple(
                BetaFeedbackRepairProposalRef.model_validate(item)
                for item in self._sanitize_json_array(
                    report.repair_proposal_refs_json,
                    "repair_proposal_refs",
                )
            ),
            triage_note=None if report.triage_note is None else self._safe_text(report.triage_note),
            triaged_by_actor_ref=report.triaged_by_actor_ref,
            triaged_at=report.triaged_at,
            moderation_report_id=report.moderation_report_id,
            metadata=self._sanitize_json_object(report.metadata_json, "metadata"),
            created_at=report.created_at,
            updated_at=report.updated_at,
        )

    def _validate_safe_text(self, value: str | None, field_name: str) -> None:
        if value is not None and _LEAK_PATTERN.search(value):
            raise BetaFeedbackValidationError(f"{field_name} contains unsafe internal data")

    def _safe_text(self, value: str) -> str:
        return _LEAK_PATTERN.sub("[REDACTED]", value)[:_SAFE_TEXT_LIMIT]

    def _sanitize_json_object(self, value: object, field_name: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise BetaFeedbackValidationError(f"{field_name} must be an object")
        sanitized = self._sanitize_json_value(value)
        if not isinstance(sanitized, dict):
            raise BetaFeedbackValidationError(f"{field_name} must be an object")
        if len(str(sanitized)) > _SAFE_JSON_LIMIT:
            raise BetaFeedbackValidationError(f"{field_name} is too large")
        return sanitized

    def _sanitize_json_array(self, value: object, field_name: str) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            raise BetaFeedbackValidationError(f"{field_name} must be an array")
        sanitized = self._sanitize_json_value(value)
        if not isinstance(sanitized, list):
            raise BetaFeedbackValidationError(f"{field_name} must be an array")
        return [item for item in sanitized if isinstance(item, dict)]

    def _sanitize_json_value(self, value: object) -> Any:
        if isinstance(value, dict):
            sanitized: dict[str, Any] = {}
            for key, item in value.items():
                key_text = str(key)
                if key_text.lower() in _SENSITIVE_KEYS:
                    continue
                clean_item = self._sanitize_json_value(item)
                if clean_item is not None:
                    sanitized[key_text] = clean_item
            return sanitized
        if isinstance(value, list | tuple | set):
            return [
                item
                for item in (self._sanitize_json_value(item) for item in list(value)[:50])
                if item is not None
            ]
        if isinstance(value, str):
            return None if _LEAK_PATTERN.search(value) else value[:500]
        if value is None or isinstance(value, bool | int | float):
            return value
        return str(value)[:200]
