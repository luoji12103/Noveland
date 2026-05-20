from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from noveland.auth import AuthenticatedSubject
from noveland.core.settings import load_settings
from noveland.media.storage import LocalMediaObjectStorage
from noveland.observability import (
    IncidentDiagnosticsService,
    IncidentSummary,
    PrivateBetaGateReport,
    PrivateBetaSetupReadinessReport,
    ProductionReadinessGateService,
    ProductionReadinessReport,
    PublicLaunchReadinessReport,
    SelfUseMvpGateReport,
)
from noveland.services.api.dependencies import get_db_session, get_platform_admin_subject
from noveland.storage import LocalObjectStorage
from noveland.storage.integrity import StorageIntegrityAuditService
from sqlalchemy.orm import Session

router = APIRouter(prefix="/observability", tags=["observability"])


@router.get("/incidents/summary", response_model=IncidentSummary)
def get_incident_summary(
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
    world_id: Annotated[uuid.UUID | None, Query()] = None,
    retention_days: Annotated[int, Query(ge=1, le=3650)] = 30,
    evidence_limit_per_component: Annotated[int, Query(ge=1, le=20)] = 5,
) -> IncidentSummary:
    del subject
    return IncidentDiagnosticsService(db_session).summary(
        world_id=world_id,
        retention_days=retention_days,
        evidence_limit_per_component=evidence_limit_per_component,
    )


@router.get("/readiness/production", response_model=ProductionReadinessReport)
def get_production_readiness(
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
    world_id: Annotated[uuid.UUID | None, Query()] = None,
    evidence_limit_per_section: Annotated[int, Query(ge=1, le=20)] = 5,
    storage_audit_limit: Annotated[int, Query(ge=1, le=10_000)] = 1000,
    storage_finding_limit: Annotated[int, Query(ge=1, le=1000)] = 100,
) -> ProductionReadinessReport:
    del subject
    settings = load_settings()
    storage_audit = StorageIntegrityAuditService(
        db_session,
        media_storage=LocalMediaObjectStorage(settings.object_storage_root / "media"),
        object_storage=LocalObjectStorage(settings.object_storage_root),
    ).audit(limit=storage_audit_limit, finding_limit=storage_finding_limit)
    return ProductionReadinessGateService(db_session).report(
        world_id=world_id,
        evidence_limit_per_section=evidence_limit_per_section,
        storage_audit=storage_audit,
    )


@router.get("/readiness/public-launch", response_model=PublicLaunchReadinessReport)
def get_public_launch_readiness(
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
    world_id: Annotated[uuid.UUID | None, Query()] = None,
    evidence_limit_per_section: Annotated[int, Query(ge=1, le=20)] = 5,
    storage_audit_limit: Annotated[int, Query(ge=1, le=10_000)] = 1000,
    storage_finding_limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    security_signoff: Annotated[bool, Query()] = False,
    privacy_signoff: Annotated[bool, Query()] = False,
    moderation_signoff: Annotated[bool, Query()] = False,
    sample_world_signoff: Annotated[bool, Query()] = False,
    operator_signoff: Annotated[bool, Query()] = False,
) -> PublicLaunchReadinessReport:
    del subject
    settings = load_settings()
    storage_audit = StorageIntegrityAuditService(
        db_session,
        media_storage=LocalMediaObjectStorage(settings.object_storage_root / "media"),
        object_storage=LocalObjectStorage(settings.object_storage_root),
    ).audit(limit=storage_audit_limit, finding_limit=storage_finding_limit)
    return ProductionReadinessGateService(db_session).public_launch_report(
        world_id=world_id,
        evidence_limit_per_section=evidence_limit_per_section,
        storage_audit=storage_audit,
        security_signoff=security_signoff,
        privacy_signoff=privacy_signoff,
        moderation_signoff=moderation_signoff,
        sample_world_signoff=sample_world_signoff,
        operator_signoff=operator_signoff,
    )


@router.get("/readiness/self-use-mvp", response_model=SelfUseMvpGateReport)
def get_self_use_mvp_readiness(
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
    world_id: Annotated[uuid.UUID, Query()],
    worldline_id: Annotated[uuid.UUID | None, Query()] = None,
    conversation_id: Annotated[uuid.UUID | None, Query()] = None,
    evidence_limit_per_section: Annotated[int, Query(ge=1, le=20)] = 5,
    manual_play_minutes: Annotated[int, Query(ge=0, le=1440)] = 0,
    resume_verified: Annotated[bool, Query()] = False,
    failure_notes_recorded: Annotated[bool, Query()] = False,
) -> SelfUseMvpGateReport:
    del subject
    return ProductionReadinessGateService(db_session).self_use_mvp_report(
        world_id=world_id,
        worldline_id=worldline_id,
        conversation_id=conversation_id,
        evidence_limit_per_section=evidence_limit_per_section,
        manual_play_minutes=manual_play_minutes,
        resume_verified=resume_verified,
        failure_notes_recorded=failure_notes_recorded,
    )


@router.get("/readiness/private-beta-setup", response_model=PrivateBetaSetupReadinessReport)
def get_private_beta_setup_readiness(
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
    world_id: Annotated[uuid.UUID, Query()],
    worldline_id: Annotated[uuid.UUID | None, Query()] = None,
    conversation_id: Annotated[uuid.UUID | None, Query()] = None,
    evidence_limit_per_section: Annotated[int, Query(ge=1, le=20)] = 5,
    manual_play_minutes: Annotated[int, Query(ge=0, le=1440)] = 0,
    resume_verified: Annotated[bool, Query()] = False,
    failure_notes_recorded: Annotated[bool, Query()] = False,
) -> PrivateBetaSetupReadinessReport:
    del subject
    report = ProductionReadinessGateService(db_session).private_beta_setup_report(
        world_id=world_id,
        worldline_id=worldline_id,
        conversation_id=conversation_id,
        evidence_limit_per_section=evidence_limit_per_section,
        manual_play_minutes=manual_play_minutes,
        resume_verified=resume_verified,
        failure_notes_recorded=failure_notes_recorded,
    )
    return PrivateBetaSetupReadinessReport.model_validate(report.model_dump())


@router.get("/readiness/private-beta", response_model=PrivateBetaGateReport)
def get_private_beta_readiness(
    subject: Annotated[AuthenticatedSubject, Depends(get_platform_admin_subject)],
    db_session: Annotated[Session, Depends(get_db_session)],
    world_id: Annotated[uuid.UUID, Query()],
    worldline_id: Annotated[uuid.UUID | None, Query()] = None,
    conversation_id: Annotated[uuid.UUID | None, Query()] = None,
    evidence_limit_per_section: Annotated[int, Query(ge=1, le=20)] = 5,
    manual_play_minutes: Annotated[int, Query(ge=0, le=240)] = 0,
    resume_verified: Annotated[bool, Query()] = False,
    failure_notes_recorded: Annotated[bool, Query()] = False,
    manual_tester_count: Annotated[int, Query(ge=0, le=3)] = 0,
    tester_session_completed: Annotated[bool, Query()] = False,
    no_developer_intervention_verified: Annotated[bool, Query()] = False,
    quota_reviewed: Annotated[bool, Query()] = False,
    feedback_triage_verified: Annotated[bool, Query()] = False,
    memory_persona_qa_reviewed: Annotated[bool, Query()] = False,
    repair_loop_reviewed: Annotated[bool, Query()] = False,
) -> PrivateBetaGateReport:
    del subject
    return ProductionReadinessGateService(db_session).private_beta_gate_report(
        world_id=world_id,
        worldline_id=worldline_id,
        conversation_id=conversation_id,
        evidence_limit_per_section=evidence_limit_per_section,
        manual_play_minutes=manual_play_minutes,
        resume_verified=resume_verified,
        failure_notes_recorded=failure_notes_recorded,
        manual_tester_count=manual_tester_count,
        tester_session_completed=tester_session_completed,
        no_developer_intervention_verified=no_developer_intervention_verified,
        quota_reviewed=quota_reviewed,
        feedback_triage_verified=feedback_triage_verified,
        memory_persona_qa_reviewed=memory_persona_qa_reviewed,
        repair_loop_reviewed=repair_loop_reviewed,
    )
