from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any

from noveland.beta_feedback.models import BetaFeedbackReport
from noveland.conversations.models import ConversationSession, ConversationTurn
from noveland.media.models import MediaAsset
from noveland.moderation.contracts import (
    ModerationActionCreate,
    ModerationActionKind,
    ModerationActionRead,
    ModerationActionStatus,
    ModerationCategory,
    ModerationFeedbackEscalationCreate,
    ModerationIncidentCreate,
    ModerationIncidentRead,
    ModerationIncidentReview,
    ModerationIncidentStatus,
    ModerationReportCreate,
    ModerationReportRead,
    ModerationReportReview,
    ModerationReportStatus,
    ModerationSafetyReviewCreate,
    ModerationSeverity,
    ModerationTargetKind,
)
from noveland.moderation.models import ModerationAction, ModerationIncident, ModerationReport
from noveland.observability.contracts import IncidentEvidenceRef
from noveland.providers.models import ProviderIntegration
from noveland.worlds.models import Worldline
from sqlalchemy import select
from sqlalchemy.orm import Session

_SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "token",
    "bearer_token",
    "authorization",
    "secret",
    "client_secret",
    "access_key",
    "password",
    "private_key",
    "auth_ref",
    "storage_uri",
    "preview_uri",
    "thumbnail_uri",
    "base64",
    "bytes",
    "path",
    "file_path",
    "filesystem_path",
    "raw_prompt",
    "raw_output",
    "prompt_snapshot",
}
_SENSITIVE_KEY_MARKERS = {
    re.sub(r"[^a-z0-9]+", "", marker.lower()) for marker in _SENSITIVE_KEYS
}
_LEAK_PATTERN = re.compile(
    r"(storage[-_ ]?uri|media://|file://|s3://|gs://|/root/|/tmp/|base64,|"
    r"BEGIN PRIVATE KEY|sk-[A-Za-z0-9]|raw[-_ ]?prompt|raw[-_ ]?output|"
    r"prompt[-_ ]?snapshot|file[-_ ]?path|filesystem[-_ ]?path|bearer\s+)",
    re.IGNORECASE,
)
_WORLDLINE_SCOPED_TARGETS = {
    ModerationTargetKind.WORLDLINE,
    ModerationTargetKind.NARRATIVE_PUBLICATION,
    ModerationTargetKind.CONVERSATION_SESSION,
    ModerationTargetKind.CONVERSATION_TURN,
    ModerationTargetKind.MEDIA_ASSET,
    ModerationTargetKind.PLAYER_PROFILE,
}
_APPLIED_SUPPRESSION_ACTIONS = {
    ModerationActionKind.DISABLE_MEDIA.value,
    ModerationActionKind.DISABLE_WORLD.value,
    ModerationActionKind.TAKEDOWN_CONTENT.value,
}
class ModerationError(ValueError):
    pass


class ModerationNotFoundError(ModerationError):
    pass


class ModerationValidationError(ModerationError):
    pass


class ModerationService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_report(
        self,
        world_id: uuid.UUID,
        reporter_user_id: uuid.UUID,
        request: ModerationReportCreate,
        *,
        actor_ref: str,
    ) -> ModerationReportRead:
        _validate_safe_text(request.reason, "reason")
        _validate_safe_text(request.reporter_note, "reporter_note")
        metadata = _sanitize_json(request.metadata)
        evidence_refs = _safe_evidence_refs(request.evidence_refs)
        self._validate_target(
            world_id,
            request.target_ref_kind,
            request.target_ref_id,
            request.worldline_id,
            actor_is_platform_admin=False,
            action_kind=None,
        )
        model = ModerationReport(
            world_id=world_id,
            worldline_id=request.worldline_id,
            reporter_user_id=reporter_user_id,
            target_ref_kind=request.target_ref_kind.value,
            target_ref_id=request.target_ref_id,
            category=request.category.value,
            severity=request.severity.value,
            status="submitted",
            reason=request.reason,
            reporter_note=request.reporter_note,
            evidence_refs_json=evidence_refs,
            created_by_actor_ref=actor_ref,
            metadata_json=metadata,
        )
        self._session.add(model)
        self._session.flush()
        return _report_read(model)

    def list_reports(
        self,
        world_id: uuid.UUID,
        *,
        worldline_id: uuid.UUID | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[ModerationReportRead]:
        statement = (
            select(ModerationReport)
            .where(ModerationReport.world_id == world_id)
            .order_by(ModerationReport.created_at.desc())
            .limit(max(1, min(limit, 200)))
        )
        if worldline_id is not None:
            statement = statement.where(ModerationReport.worldline_id == worldline_id)
        if status is not None:
            statement = statement.where(ModerationReport.status == status)
        return [_report_read(report) for report in self._session.scalars(statement).all()]

    def review_report(
        self,
        world_id: uuid.UUID,
        report_id: uuid.UUID,
        review: ModerationReportReview,
        *,
        actor_ref: str,
    ) -> ModerationReportRead:
        _validate_safe_text(review.review_note, "review_note")
        report = self._session.get(ModerationReport, report_id)
        if report is None or report.world_id != world_id:
            raise ModerationNotFoundError("moderation report not found")
        report.status = review.status.value
        report.review_note = review.review_note
        report.reviewed_by_actor_ref = actor_ref
        report.reviewed_at = datetime.now(UTC)
        self._session.flush()
        return _report_read(report)

    def create_safety_review_report(
        self,
        world_id: uuid.UUID,
        reporter_user_id: uuid.UUID,
        request: ModerationSafetyReviewCreate,
        *,
        actor_ref: str,
    ) -> ModerationReportRead:
        _validate_safe_text(request.policy_key, "policy_key")
        _validate_safe_text(request.finding, "finding")
        self._validate_target(
            world_id,
            request.target_ref_kind,
            request.target_ref_id,
            request.worldline_id,
            actor_is_platform_admin=False,
            action_kind=None,
        )
        evidence_refs = list(_safe_evidence_refs(request.evidence_refs))
        evidence_refs.insert(
            0,
            IncidentEvidenceRef(
                kind=request.target_ref_kind.value,
                id=str(request.target_ref_id),
                component="moderation_safety_review",
                status="flagged",
                reason_code=request.policy_key,
                world_id=world_id,
                worldline_id=request.worldline_id,
            ).model_dump(mode="json", exclude_none=True),
        )
        model = ModerationReport(
            world_id=world_id,
            worldline_id=request.worldline_id,
            reporter_user_id=reporter_user_id,
            target_ref_kind=request.target_ref_kind.value,
            target_ref_id=request.target_ref_id,
            category=request.category.value,
            severity=request.severity.value,
            status=ModerationReportStatus.UNDER_REVIEW.value,
            reason=request.finding,
            reporter_note=None,
            evidence_refs_json=evidence_refs,
            created_by_actor_ref=actor_ref,
            metadata_json={
                "source": "safety_review",
                "policy_key": _safe_text(request.policy_key),
                **_sanitize_json(request.metadata),
            },
        )
        self._session.add(model)
        self._session.flush()
        return _report_read(model)

    def escalate_beta_feedback(
        self,
        world_id: uuid.UUID,
        request: ModerationFeedbackEscalationCreate,
        *,
        actor_ref: str,
    ) -> ModerationReportRead:
        _validate_safe_text(request.reason, "reason")
        feedback = self._session.get(BetaFeedbackReport, request.feedback_report_id)
        if feedback is None or feedback.world_id != world_id:
            raise ModerationNotFoundError("beta feedback report not found")
        severity = request.severity.value if request.severity is not None else feedback.severity
        evidence_refs = list(_safe_evidence_refs(request.evidence_refs))
        evidence_refs.append(
            IncidentEvidenceRef(
                kind="beta_feedback_report",
                id=str(feedback.id),
                component="beta_feedback",
                status=feedback.status,
                reason_code=f"beta_feedback_{feedback.issue_type}",
                world_id=feedback.world_id,
                worldline_id=feedback.worldline_id,
            ).model_dump(mode="json", exclude_none=True),
        )
        model = ModerationReport(
            world_id=world_id,
            worldline_id=feedback.worldline_id,
            reporter_user_id=feedback.reporter_user_id,
            target_ref_kind=ModerationTargetKind.OTHER.value,
            target_ref_id=None,
            category=request.category.value,
            severity=severity,
            status=ModerationReportStatus.ESCALATED.value,
            reason=request.reason,
            reporter_note=None,
            evidence_refs_json=evidence_refs,
            created_by_actor_ref=actor_ref,
            metadata_json={
                "source": "beta_feedback_escalation",
                "feedback_report_id": str(feedback.id),
                "feedback_issue_type": feedback.issue_type,
                **_sanitize_json(request.metadata),
            },
        )
        self._session.add(model)
        self._session.flush()
        feedback.moderation_report_id = model.id
        feedback.status = "investigating"
        feedback.triaged_by_actor_ref = actor_ref
        feedback.triaged_at = datetime.now(UTC)
        self._session.flush()
        return _report_read(model)

    def create_action(
        self,
        world_id: uuid.UUID,
        request: ModerationActionCreate,
        *,
        actor_ref: str,
        actor_is_platform_admin: bool,
    ) -> ModerationActionRead:
        _validate_safe_text(request.reason, "reason")
        _validate_safe_text(request.review_note, "review_note")
        metadata = _sanitize_json(request.metadata)
        evidence_refs = _safe_evidence_refs(request.evidence_refs)
        self._validate_target(
            world_id,
            request.target_ref_kind,
            request.target_ref_id,
            request.worldline_id,
            actor_is_platform_admin=actor_is_platform_admin,
            action_kind=request.action_kind,
        )
        self._validate_report_link(world_id, request.report_id)
        self._validate_incident_link(world_id, request.incident_id)
        audit_summary = {
            "automatic_execution": False,
            "provider_execution": False,
            "daemon_execution": False,
            "world_event_writes": False,
            "destructive_rollback": False,
            "reader_delivery_suppression": (
                request.status == ModerationActionStatus.APPLIED
                and request.action_kind.value in _APPLIED_SUPPRESSION_ACTIONS
            ),
            "target": {
                "kind": request.target_ref_kind.value,
                "id": None if request.target_ref_id is None else str(request.target_ref_id),
            },
        }
        model = ModerationAction(
            world_id=world_id,
            worldline_id=request.worldline_id,
            report_id=request.report_id,
            incident_id=request.incident_id,
            action_kind=request.action_kind.value,
            status=request.status.value,
            target_ref_kind=request.target_ref_kind.value,
            target_ref_id=request.target_ref_id,
            reason=request.reason,
            audit_summary_json=audit_summary,
            evidence_refs_json=evidence_refs,
            created_by_actor_ref=actor_ref,
            reviewed_by_actor_ref=(
                actor_ref if request.status != ModerationActionStatus.PROPOSED else None
            ),
            reviewed_at=(
                datetime.now(UTC) if request.status != ModerationActionStatus.PROPOSED else None
            ),
            review_note=request.review_note,
            metadata_json=metadata,
        )
        self._session.add(model)
        self._session.flush()
        return _action_read(model)

    def list_actions(
        self,
        world_id: uuid.UUID,
        *,
        worldline_id: uuid.UUID | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[ModerationActionRead]:
        statement = (
            select(ModerationAction)
            .where(ModerationAction.world_id == world_id)
            .order_by(ModerationAction.created_at.desc())
            .limit(max(1, min(limit, 200)))
        )
        if worldline_id is not None:
            statement = statement.where(ModerationAction.worldline_id == worldline_id)
        if status is not None:
            statement = statement.where(ModerationAction.status == status)
        return [_action_read(action) for action in self._session.scalars(statement).all()]

    def create_incident(
        self,
        world_id: uuid.UUID,
        request: ModerationIncidentCreate,
        *,
        actor_ref: str,
    ) -> ModerationIncidentRead:
        _validate_safe_text(request.title, "title")
        _validate_safe_text(request.summary, "summary")
        metadata = _sanitize_json(request.metadata)
        evidence_refs = _safe_evidence_refs(request.evidence_refs)
        self._validate_worldline(world_id, request.worldline_id)
        report_ids = self._validate_report_ids(world_id, request.report_ids)
        action_ids = self._validate_action_ids(world_id, request.action_ids)
        model = ModerationIncident(
            world_id=world_id,
            worldline_id=request.worldline_id,
            status=request.status.value,
            severity=request.severity.value,
            title=request.title,
            summary=request.summary,
            report_ids_json=[str(report_id) for report_id in report_ids],
            action_ids_json=[str(action_id) for action_id in action_ids],
            evidence_refs_json=evidence_refs,
            created_by_actor_ref=actor_ref,
            metadata_json=metadata,
        )
        self._session.add(model)
        self._session.flush()
        return _incident_read(model)

    def list_incidents(
        self,
        world_id: uuid.UUID,
        *,
        worldline_id: uuid.UUID | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[ModerationIncidentRead]:
        statement = (
            select(ModerationIncident)
            .where(ModerationIncident.world_id == world_id)
            .order_by(ModerationIncident.created_at.desc())
            .limit(max(1, min(limit, 200)))
        )
        if worldline_id is not None:
            statement = statement.where(ModerationIncident.worldline_id == worldline_id)
        if status is not None:
            statement = statement.where(ModerationIncident.status == status)
        return [_incident_read(incident) for incident in self._session.scalars(statement).all()]

    def review_incident(
        self,
        world_id: uuid.UUID,
        incident_id: uuid.UUID,
        review: ModerationIncidentReview,
        *,
        actor_ref: str,
    ) -> ModerationIncidentRead:
        _validate_safe_text(review.review_note, "review_note")
        incident = self._session.get(ModerationIncident, incident_id)
        if incident is None or incident.world_id != world_id:
            raise ModerationNotFoundError("moderation incident not found")
        incident.status = review.status.value
        incident.review_note = review.review_note
        incident.reviewed_by_actor_ref = actor_ref
        incident.reviewed_at = datetime.now(UTC)
        if review.report_ids is not None:
            incident.report_ids_json = [
                str(report_id)
                for report_id in self._validate_report_ids(world_id, review.report_ids)
            ]
        if review.action_ids is not None:
            incident.action_ids_json = [
                str(action_id)
                for action_id in self._validate_action_ids(world_id, review.action_ids)
            ]
        self._session.flush()
        return _incident_read(incident)

    def target_is_suppressed(
        self,
        world_id: uuid.UUID,
        target_ref_kind: ModerationTargetKind,
        target_ref_id: uuid.UUID | None,
        *,
        worldline_id: uuid.UUID | None = None,
    ) -> bool:
        world_action = self._session.scalars(
            select(ModerationAction.id).where(
                ModerationAction.world_id == world_id,
                ModerationAction.status == ModerationActionStatus.APPLIED.value,
                ModerationAction.action_kind == ModerationActionKind.DISABLE_WORLD.value,
                ModerationAction.target_ref_kind == ModerationTargetKind.WORLD.value,
            )
        ).first()
        if world_action is not None:
            return True
        statement = select(ModerationAction.id).where(
            ModerationAction.world_id == world_id,
            ModerationAction.status == ModerationActionStatus.APPLIED.value,
            ModerationAction.action_kind.in_(_APPLIED_SUPPRESSION_ACTIONS),
            ModerationAction.target_ref_kind == target_ref_kind.value,
            ModerationAction.target_ref_id == target_ref_id,
        )
        if worldline_id is not None:
            statement = statement.where(
                (ModerationAction.worldline_id.is_(None))
                | (ModerationAction.worldline_id == worldline_id)
            )
        return self._session.scalars(statement).first() is not None

    def _validate_target(
        self,
        world_id: uuid.UUID,
        target_kind: ModerationTargetKind,
        target_id: uuid.UUID | None,
        worldline_id: uuid.UUID | None,
        *,
        actor_is_platform_admin: bool,
        action_kind: ModerationActionKind | None,
    ) -> None:
        if target_kind in _WORLDLINE_SCOPED_TARGETS and worldline_id is None:
            raise ModerationValidationError("worldline_id is required for worldline-scoped targets")
        self._validate_worldline(world_id, worldline_id)
        if target_kind == ModerationTargetKind.WORLD and target_id not in (None, world_id):
            raise ModerationValidationError("world target_ref_id must match world_id")
        if target_kind == ModerationTargetKind.WORLDLINE:
            if target_id is None:
                raise ModerationValidationError("worldline target_ref_id is required")
            worldline = self._session.get(Worldline, target_id)
            if worldline is None or worldline.world_id != world_id:
                raise ModerationNotFoundError("target worldline not found")
            if worldline_id is not None and target_id != worldline_id:
                raise ModerationValidationError("worldline target_ref_id must match worldline_id")
        if target_kind == ModerationTargetKind.PROVIDER_INTEGRATION:
            if target_id is None:
                raise ModerationValidationError("provider target_ref_id is required")
            provider = self._session.get(ProviderIntegration, target_id)
            if (
                provider is None
                or (provider.world_id is not None and provider.world_id != world_id)
            ):
                raise ModerationNotFoundError("provider integration not found")
            if (
                action_kind == ModerationActionKind.DISABLE_PROVIDER
                and provider.world_id is None
                and not actor_is_platform_admin
            ):
                raise ModerationValidationError(
                    "platform admin is required for global provider moderation actions"
                )
        if target_kind == ModerationTargetKind.CONVERSATION_SESSION:
            conversation = self._session.get(ConversationSession, target_id)
            if (
                target_id is None
                or conversation is None
                or conversation.world_id != world_id
                or conversation.worldline_id != worldline_id
            ):
                raise ModerationNotFoundError("conversation not found")
        if target_kind == ModerationTargetKind.CONVERSATION_TURN:
            turn = self._session.get(ConversationTurn, target_id)
            if target_id is None or turn is None:
                raise ModerationNotFoundError("conversation turn not found")
            conversation = self._session.get(ConversationSession, turn.session_id)
            if (
                conversation is None
                or conversation.world_id != world_id
                or conversation.worldline_id != worldline_id
            ):
                raise ModerationNotFoundError("conversation turn not found")
        if target_kind == ModerationTargetKind.MEDIA_ASSET:
            asset = self._session.get(MediaAsset, target_id)
            if (
                target_id is None
                or asset is None
                or asset.world_id != world_id
                or asset.worldline_id != worldline_id
            ):
                raise ModerationNotFoundError("media asset not found")

    def _validate_worldline(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID | None,
    ) -> None:
        if worldline_id is None:
            return
        worldline = self._session.get(Worldline, worldline_id)
        if worldline is None or worldline.world_id != world_id:
            raise ModerationNotFoundError("worldline not found")

    def _validate_report_link(self, world_id: uuid.UUID, report_id: uuid.UUID | None) -> None:
        if report_id is None:
            return
        report = self._session.get(ModerationReport, report_id)
        if report is None or report.world_id != world_id:
            raise ModerationNotFoundError("moderation report not found")

    def _validate_incident_link(self, world_id: uuid.UUID, incident_id: uuid.UUID | None) -> None:
        if incident_id is None:
            return
        incident = self._session.get(ModerationIncident, incident_id)
        if incident is None or incident.world_id != world_id:
            raise ModerationNotFoundError("moderation incident not found")

    def _validate_report_ids(
        self,
        world_id: uuid.UUID,
        report_ids: tuple[uuid.UUID, ...],
    ) -> tuple[uuid.UUID, ...]:
        for report_id in report_ids:
            self._validate_report_link(world_id, report_id)
        return report_ids

    def _validate_action_ids(
        self,
        world_id: uuid.UUID,
        action_ids: tuple[uuid.UUID, ...],
    ) -> tuple[uuid.UUID, ...]:
        for action_id in action_ids:
            action = self._session.get(ModerationAction, action_id)
            if action is None or action.world_id != world_id:
                raise ModerationNotFoundError("moderation action not found")
        return action_ids


def _report_read(report: ModerationReport) -> ModerationReportRead:
    return ModerationReportRead(
        id=report.id,
        world_id=report.world_id,
        worldline_id=report.worldline_id,
        reporter_user_id=report.reporter_user_id,
        target_ref_kind=ModerationTargetKind(report.target_ref_kind),
        target_ref_id=report.target_ref_id,
        category=ModerationCategory(report.category),
        severity=ModerationSeverity(report.severity),
        status=ModerationReportStatus(report.status),
        reason=report.reason,
        reporter_note=report.reporter_note,
        evidence_refs=_evidence_ref_tuple(report.evidence_refs_json),
        created_by_actor_ref=report.created_by_actor_ref,
        reviewed_by_actor_ref=report.reviewed_by_actor_ref,
        reviewed_at=report.reviewed_at,
        review_note=report.review_note,
        metadata=_sanitize_json(report.metadata_json),
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


def _action_read(action: ModerationAction) -> ModerationActionRead:
    return ModerationActionRead(
        id=action.id,
        world_id=action.world_id,
        worldline_id=action.worldline_id,
        report_id=action.report_id,
        incident_id=action.incident_id,
        action_kind=ModerationActionKind(action.action_kind),
        status=ModerationActionStatus(action.status),
        target_ref_kind=ModerationTargetKind(action.target_ref_kind),
        target_ref_id=action.target_ref_id,
        reason=action.reason,
        audit_summary=_sanitize_json(action.audit_summary_json),
        evidence_refs=_evidence_ref_tuple(action.evidence_refs_json),
        created_by_actor_ref=action.created_by_actor_ref,
        reviewed_by_actor_ref=action.reviewed_by_actor_ref,
        reviewed_at=action.reviewed_at,
        review_note=action.review_note,
        metadata=_sanitize_json(action.metadata_json),
        created_at=action.created_at,
        updated_at=action.updated_at,
    )


def _incident_read(incident: ModerationIncident) -> ModerationIncidentRead:
    return ModerationIncidentRead(
        id=incident.id,
        world_id=incident.world_id,
        worldline_id=incident.worldline_id,
        status=ModerationIncidentStatus(incident.status),
        severity=ModerationSeverity(incident.severity),
        title=incident.title,
        summary=incident.summary,
        report_ids=tuple(uuid.UUID(value) for value in incident.report_ids_json),
        action_ids=tuple(uuid.UUID(value) for value in incident.action_ids_json),
        evidence_refs=_evidence_ref_tuple(incident.evidence_refs_json),
        created_by_actor_ref=incident.created_by_actor_ref,
        reviewed_by_actor_ref=incident.reviewed_by_actor_ref,
        reviewed_at=incident.reviewed_at,
        review_note=incident.review_note,
        metadata=_sanitize_json(incident.metadata_json),
        created_at=incident.created_at,
        updated_at=incident.updated_at,
    )


def _evidence_ref_tuple(value: list[dict[str, Any]]) -> tuple[IncidentEvidenceRef, ...]:
    return tuple(IncidentEvidenceRef.model_validate(item) for item in value)


def _safe_evidence_refs(
    evidence_refs: tuple[IncidentEvidenceRef, ...],
) -> list[dict[str, Any]]:
    return [
        _sanitize_json(ref.model_dump(mode="json", exclude_none=True)) for ref in evidence_refs
    ]


def _sanitize_json(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            if not _is_sensitive_key(str(key)):
                sanitized[str(key)] = _sanitize_json(item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_json(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_json(item) for item in value]
    if isinstance(value, str):
        return _safe_text(value)
    return value


def _validate_safe_text(value: str | None, field_name: str) -> None:
    if value is not None and _LEAK_PATTERN.search(value):
        raise ModerationValidationError(f"{field_name} contains unsafe internal data")


def _safe_text(value: str) -> str:
    return _LEAK_PATTERN.sub("[REDACTED]", value)


def _is_sensitive_key(key: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "", key.lower())
    return any(marker and marker in normalized for marker in _SENSITIVE_KEY_MARKERS)
