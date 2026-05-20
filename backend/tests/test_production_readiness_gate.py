from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import cast

from fastapi.testclient import TestClient
from noveland.agents.models import Agent, AgentPersona
from noveland.auth import AuthRole
from noveland.auth.contracts import AuthSessionStatus
from noveland.auth.models import AuthSession, PlatformRoleAssignment, User
from noveland.auth.services import hash_session_token
from noveland.authoring.models import (
    AuthoringImportProposal,
    AuthoringImportRun,
    AuthoringSourceAsset,
    AuthoringSourceBatch,
    AuthoringSourceFragment,
    AuthoringSourceTraceability,
)
from noveland.conversations.models import (
    ConversationParticipant,
    ConversationSession,
    ConversationTurn,
    ConversationTurnPresentation,
)
from noveland.events.models import WorldEventModel, WorldSnapshotModel
from noveland.invocations.models import ModelInvocation, PromptSnapshot
from noveland.media.models import MediaAsset, MediaJob, MediaObject, MediaReference
from noveland.memory.models import AgentMemoryItem, MemoryWriteJob
from noveland.moderation.models import ModerationAction, ModerationIncident, ModerationReport
from noveland.narrative.models import NarrativeArtifact, NarrativePublication
from noveland.observability import (
    DiagnosticComponent,
    DiagnosticSeverity,
    ProductionReadinessGateService,
    RuntimeDiagnosticCreate,
    RuntimeDiagnosticsService,
)
from noveland.observability.models import RuntimeDiagnosticEvent
from noveland.player_privacy.models import PlayerPrivacyRequest
from noveland.player_sessions.models import PlayerSession
from noveland.private_beta.models import PrivateBetaInvite
from noveland.providers.models import (
    ProviderBudgetPolicy,
    ProviderHealthCheck,
    ProviderIntegration,
)
from noveland.services.api.app import create_app
from noveland.services.api.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from noveland.services.api.dependencies import get_db_session
from noveland.speech.models import (
    AgentVoiceProfileBinding,
    SpeechStyleMapping,
    SpeechTranscript,
    VoiceProfile,
)
from noveland.visual.models import (
    CharacterSpriteSet,
    CharacterSpriteVariant,
    SceneBackgroundProfile,
)
from noveland.visual_generation.models import (
    CharacterVisualGenerationProfile,
    VisualGenerationPlan,
    VisualGenerationPlanReference,
    VisualModelAsset,
    VisualWorkflowTemplate,
    VisualWorkflowTemplateVersion,
)
from noveland.worlds.models import (
    BetaChecklistItem,
    BetaChecklistRun,
    LivingWorldReleaseProfile,
    LongRunEvalRun,
    PlayerActorProfile,
    World,
    Worldline,
    WorldMembership,
)
from sqlalchemy import Table, create_engine, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

FORBIDDEN_RESPONSE_TOKENS = (
    "sk-live-secret",
    "Bearer",
    "storage_uri",
    "media://private-object",
    "/tmp/private-file",
    "raw prompt",
    "raw output",
    "base64",
)


@dataclass(frozen=True, slots=True)
class _StorageAuditStub:
    status: str = "ok"
    finding_count: int = 0


def test_production_readiness_report_aggregates_existing_safe_evidence() -> None:
    engine = _engine()
    world_id, worldline_id = _seed_world(engine)
    _seed_ready_evidence(engine, world_id, worldline_id)

    with Session(engine) as session:
        report = ProductionReadinessGateService(session).report(
            world_id=world_id,
            storage_audit=_StorageAuditStub(),
        )

    sections = {section.section_key: section for section in report.sections}
    assert report.status == "ok"
    assert report.readiness_kind == "internal_production_readiness"
    assert report.blocker_count == 0
    assert sections["release_profile"].status == "ok"
    assert sections["beta_checklist"].status == "ok"
    assert sections["long_run_eval"].status == "ok"
    assert sections["provider_governance"].summary.startswith("1 active providers")
    assert sections["budget_controls"].status == "ok"
    assert sections["storage_integrity"].status == "ok"
    assert sections["security_regression"].evidence_refs[0].id == (
        "v0.7-security-regression-suite"
    )
    assert "public_launch_gate" in report.non_goals


def test_production_readiness_report_blocks_missing_or_failed_evidence_safely() -> None:
    engine = _engine()
    world_id, worldline_id = _seed_world(engine)
    _seed_blocking_evidence(engine, world_id, worldline_id)

    with Session(engine) as session:
        before_counts = _framework_counts(session)
        report = ProductionReadinessGateService(session).report(
            world_id=world_id,
            storage_audit=_StorageAuditStub(status="error", finding_count=2),
        )
        after_counts = _framework_counts(session)

    sections = {section.section_key: section for section in report.sections}
    assert report.status == "blocked"
    assert report.blocker_count >= 1
    assert sections["storage_integrity"].status == "blocked"
    assert sections["incident_diagnostics"].status == "blocked"
    assert before_counts == after_counts

    response_text = report.model_dump_json()
    for token in FORBIDDEN_RESPONSE_TOKENS:
        assert token not in response_text


def test_production_readiness_endpoint_is_platform_admin_only_and_safe() -> None:
    client, engine = _client_with_database()
    platform_user_id, platform_token = _seed_user(
        engine,
        "platform-readiness@example.test",
        platform_admin=True,
    )
    world_id, worldline_id = _seed_world(engine, owner_user_id=platform_user_id)
    _seed_blocking_evidence(engine, world_id, worldline_id)
    _authenticate(client, platform_token)

    response = client.get(f"/observability/readiness/production?world_id={world_id}")

    assert response.status_code == 200
    assert response.json()["readiness_kind"] == "internal_production_readiness"
    assert response.json()["world_id"] == str(world_id)
    assert response.json()["status"] == "blocked"
    for token in FORBIDDEN_RESPONSE_TOKENS:
        assert token not in response.text

    _member_id, member_token = _seed_user(engine, "member-readiness@example.test", False)
    _authenticate(client, member_token)
    forbidden = client.get("/observability/readiness/production")
    assert forbidden.status_code == 403
    for token in FORBIDDEN_RESPONSE_TOKENS:
        assert token not in forbidden.text


def test_production_readiness_does_not_create_duplicate_framework_tables() -> None:
    table_names = {
        "beta_checklist_runs",
        "beta_checklist_items",
        "long_run_eval_runs",
        "living_world_release_profiles",
    }
    assert "production_readiness_runs" not in table_names
    assert "production_readiness_reports" not in table_names


def test_public_launch_readiness_blocks_internal_readiness_blockers_safely() -> None:
    engine = _engine()
    world_id, worldline_id = _seed_world(engine)
    _seed_blocking_evidence(engine, world_id, worldline_id)
    _seed_public_launch_evidence(engine, world_id, worldline_id)

    with Session(engine) as session:
        report = ProductionReadinessGateService(session).public_launch_report(
            world_id=world_id,
            storage_audit=_StorageAuditStub(status="error", finding_count=2),
            security_signoff=True,
            privacy_signoff=True,
            moderation_signoff=True,
            sample_world_signoff=True,
            operator_signoff=True,
        )

    sections = {section.section_key: section for section in report.sections}
    assert report.status == "blocked"
    assert report.readiness_kind == "public_launch_readiness"
    assert report.internal_readiness.status == "blocked"
    assert report.auto_launch_enabled is False
    assert sections["internal_production_readiness"].status == "blocked"
    assert "Internal production readiness has blocking sections." in (
        sections["internal_production_readiness"].blockers
    )
    for token in FORBIDDEN_RESPONSE_TOKENS:
        assert token not in report.model_dump_json()


def test_public_launch_readiness_requires_explicit_signoffs() -> None:
    engine = _engine()
    world_id, worldline_id = _seed_world(engine)
    _seed_ready_evidence(engine, world_id, worldline_id)
    _seed_public_launch_evidence(engine, world_id, worldline_id)

    with Session(engine) as session:
        report = ProductionReadinessGateService(session).public_launch_report(
            world_id=world_id,
            storage_audit=_StorageAuditStub(),
            security_signoff=True,
            privacy_signoff=True,
            moderation_signoff=False,
            sample_world_signoff=True,
            operator_signoff=False,
        )

    sections = {section.section_key: section for section in report.sections}
    assert report.status == "blocked"
    assert report.required_signoffs["moderation_signoff"] is False
    assert report.required_signoffs["operator_signoff"] is False
    assert sections["moderation_workflow"].status == "blocked"
    assert "Moderation signoff is missing." in sections["moderation_workflow"].blockers
    assert sections["explicit_public_signoff"].status == "blocked"
    assert "operator_signoff is missing." in sections["explicit_public_signoff"].blockers


def test_public_launch_readiness_passes_with_required_evidence_and_signoffs() -> None:
    engine = _engine()
    world_id, worldline_id = _seed_world(engine)
    _seed_ready_evidence(engine, world_id, worldline_id)
    _seed_public_launch_evidence(engine, world_id, worldline_id)

    with Session(engine) as session:
        before_counts = _framework_counts(session)
        report = ProductionReadinessGateService(session).public_launch_report(
            world_id=world_id,
            storage_audit=_StorageAuditStub(),
            security_signoff=True,
            privacy_signoff=True,
            moderation_signoff=True,
            sample_world_signoff=True,
            operator_signoff=True,
        )
        after_counts = _framework_counts(session)

    sections = {section.section_key: section for section in report.sections}
    assert report.status == "ok"
    assert report.auto_launch_enabled is False
    assert report.blocker_count == 0
    assert report.internal_readiness.status == "ok"
    assert sections["reader_media_delivery"].status == "ok"
    assert sections["conversation_playback_scene"].status == "ok"
    assert sections["player_privacy_controls"].status == "ok"
    assert sections["moderation_workflow"].status == "ok"
    assert sections["sample_world_package"].status == "ok"
    assert sections["plugin_provider_safety"].status == "ok"
    assert sections["public_surface_security"].status == "ok"
    assert sections["explicit_public_signoff"].status == "ok"
    assert before_counts == after_counts


def test_public_launch_readiness_endpoint_is_platform_admin_only_and_safe() -> None:
    client, engine = _client_with_database()
    platform_user_id, platform_token = _seed_user(
        engine,
        "platform-launch@example.test",
        platform_admin=True,
    )
    world_id, worldline_id = _seed_world(engine, owner_user_id=platform_user_id)
    _seed_ready_evidence(engine, world_id, worldline_id)
    _seed_public_launch_evidence(engine, world_id, worldline_id)
    _authenticate(client, platform_token)

    response = client.get(
        "/observability/readiness/public-launch",
        params={
            "world_id": str(world_id),
            "security_signoff": "true",
            "privacy_signoff": "true",
            "moderation_signoff": "true",
            "sample_world_signoff": "true",
            "operator_signoff": "true",
        },
    )

    assert response.status_code == 200
    assert response.json()["readiness_kind"] == "public_launch_readiness"
    assert response.json()["world_id"] == str(world_id)
    assert response.json()["auto_launch_enabled"] is False
    assert response.json()["status"] == "blocked"
    assert (
        response.json()["sections"][0]["section_key"]
        == "internal_production_readiness"
    )
    for token in FORBIDDEN_RESPONSE_TOKENS:
        assert token not in response.text

    _member_id, member_token = _seed_user(engine, "member-launch@example.test", False)
    _authenticate(client, member_token)
    forbidden = client.get("/observability/readiness/public-launch")
    assert forbidden.status_code == 403


def test_public_launch_readiness_does_not_create_duplicate_framework_tables() -> None:
    table_names = {
        "beta_checklist_runs",
        "long_run_eval_runs",
        "living_world_release_profiles",
    }
    assert "public_launch_readiness_runs" not in table_names
    assert "public_launch_readiness_reports" not in table_names


def test_self_use_mvp_gate_passes_with_demo_evidence_and_manual_checklist() -> None:
    engine = _engine()
    world_id, worldline_id = _seed_world(engine)
    conversation_id = _seed_self_use_demo_evidence(engine, world_id, worldline_id)

    with Session(engine) as session:
        before_counts = _framework_counts(session)
        report = ProductionReadinessGateService(session).self_use_mvp_report(
            world_id=world_id,
            worldline_id=worldline_id,
            conversation_id=conversation_id,
            manual_play_minutes=30,
            resume_verified=True,
            failure_notes_recorded=True,
        )
        after_counts = _framework_counts(session)

    sections = {section.section_key: section for section in report.sections}
    checklist = {item.item_key: item for item in report.manual_checklist}
    assert report.status == "ok"
    assert report.readiness_kind == "self_use_mvp_gate"
    assert report.conversation_id == conversation_id
    assert report.blocker_count == 0
    assert sections["demo_entry"].status == "ok"
    assert sections["conversation_continuity"].status == "ok"
    assert sections["persona_memory"].status == "ok"
    assert sections["visual_playback_generation"].status == "ok"
    assert sections["voice_playback"].status == "ok"
    assert sections["provider_model_lab"].status == "ok"
    assert sections["source_traceability"].status == "ok"
    assert checklist["manual_30_minute_play_session"].status == "ok"
    assert checklist["resume_behavior_verified"].status == "ok"
    assert "private_beta_readiness" in report.non_goals
    assert "public_launch_readiness" in report.non_goals
    assert before_counts == after_counts


def test_self_use_mvp_gate_blocks_missing_evidence_safely() -> None:
    engine = _engine()
    world_id, worldline_id = _seed_world(engine)
    conversation_id = _seed_self_use_demo_evidence(
        engine,
        world_id,
        worldline_id,
        include_memory=False,
        include_visual_plan=False,
        include_voice=False,
        include_required_providers=False,
        include_invocation=False,
        include_traceability=False,
        include_agent_turn=False,
    )
    _seed_leaky_world_event(engine, world_id, worldline_id)

    with Session(engine) as session:
        report = ProductionReadinessGateService(session).self_use_mvp_report(
            world_id=world_id,
            worldline_id=worldline_id,
            conversation_id=conversation_id,
            manual_play_minutes=12,
            resume_verified=False,
            failure_notes_recorded=False,
        )

    sections = {section.section_key: section for section in report.sections}
    checklist = {item.item_key: item for item in report.manual_checklist}
    assert report.status == "blocked"
    assert report.blocker_count >= 1
    assert sections["persona_memory"].status == "blocked"
    assert sections["visual_playback_generation"].status == "blocked"
    assert sections["voice_playback"].status == "blocked"
    assert sections["provider_model_lab"].status == "blocked"
    assert sections["invocation_ledger"].status == "watch"
    assert sections["source_traceability"].status == "blocked"
    assert sections["world_event_leak_check"].status == "blocked"
    assert checklist["manual_30_minute_play_session"].status == "blocked"
    assert checklist["resume_behavior_verified"].status == "blocked"
    for token in FORBIDDEN_RESPONSE_TOKENS:
        assert token not in report.model_dump_json()


def test_self_use_mvp_endpoint_is_platform_admin_only_and_safe() -> None:
    client, engine = _client_with_database()
    platform_user_id, platform_token = _seed_user(
        engine,
        "platform-self-use@example.test",
        platform_admin=True,
    )
    world_id, worldline_id = _seed_world(engine, owner_user_id=platform_user_id)
    conversation_id = _seed_self_use_demo_evidence(engine, world_id, worldline_id)
    _authenticate(client, platform_token)

    response = client.get(
        "/observability/readiness/self-use-mvp",
        params={
            "world_id": str(world_id),
            "worldline_id": str(worldline_id),
            "conversation_id": str(conversation_id),
            "manual_play_minutes": "30",
            "resume_verified": "true",
            "failure_notes_recorded": "true",
        },
    )

    assert response.status_code == 200
    assert response.json()["readiness_kind"] == "self_use_mvp_gate"
    assert response.json()["status"] == "ok"
    assert response.json()["world_id"] == str(world_id)
    assert response.json()["conversation_id"] == str(conversation_id)
    for token in FORBIDDEN_RESPONSE_TOKENS:
        assert token not in response.text

    _member_id, member_token = _seed_user(engine, "member-self-use@example.test", False)
    _authenticate(client, member_token)
    forbidden = client.get(
        "/observability/readiness/self-use-mvp",
        params={"world_id": str(world_id), "worldline_id": str(worldline_id)},
    )
    assert forbidden.status_code == 403


def test_self_use_mvp_gate_does_not_create_duplicate_framework_tables() -> None:
    table_names = {
        "beta_checklist_runs",
        "long_run_eval_runs",
        "living_world_release_profiles",
    }
    assert "self_use_mvp_gate_runs" not in table_names
    assert "self_use_mvp_gate_reports" not in table_names


def test_private_beta_setup_readiness_passes_with_safe_beta_evidence() -> None:
    engine = _engine()
    world_id, worldline_id = _seed_world(engine)
    conversation_id = _seed_self_use_demo_evidence(engine, world_id, worldline_id)
    _seed_private_beta_setup_evidence(engine, world_id, worldline_id, conversation_id)

    with Session(engine) as session:
        before_counts = _framework_counts(session)
        report = ProductionReadinessGateService(session).private_beta_setup_report(
            world_id=world_id,
            worldline_id=worldline_id,
            conversation_id=conversation_id,
            manual_play_minutes=30,
            resume_verified=True,
            failure_notes_recorded=True,
        )
        after_counts = _framework_counts(session)

    sections = {section.section_key: section for section in report.sections}
    assert report.status == "ok"
    assert report.readiness_kind == "private_beta_world_setup"
    assert report.blocker_count == 0
    assert sections["private_beta_access"].status == "ok"
    assert sections["player_session_restore"].status == "ok"
    assert sections["private_beta_quota_controls"].status == "ok"
    assert sections["provider_model_lab"].status == "ok"
    assert sections["persona_memory"].status == "ok"
    assert sections["visual_playback_generation"].status == "ok"
    assert sections["voice_playback"].status == "ok"
    assert sections["self_use_mvp_evidence"].status == "ok"
    assert "duplicate_readiness_framework" in report.non_goals
    assert before_counts == after_counts
    for token in FORBIDDEN_RESPONSE_TOKENS:
        assert token not in report.model_dump_json()


def test_private_beta_setup_readiness_blocks_missing_access_session_quota_content_safely() -> None:
    engine = _engine()
    world_id, worldline_id = _seed_world(engine)
    conversation_id = _seed_self_use_demo_evidence(
        engine,
        world_id,
        worldline_id,
        include_memory=False,
        include_visual_plan=False,
        include_voice=False,
        include_required_providers=False,
        include_traceability=False,
    )
    _seed_leaky_world_event(engine, world_id, worldline_id)

    with Session(engine) as session:
        report = ProductionReadinessGateService(session).private_beta_setup_report(
            world_id=world_id,
            worldline_id=worldline_id,
            conversation_id=conversation_id,
            manual_play_minutes=0,
            resume_verified=False,
            failure_notes_recorded=False,
        )

    sections = {section.section_key: section for section in report.sections}
    assert report.status == "blocked"
    assert sections["private_beta_access"].status == "blocked"
    assert sections["player_session_restore"].status == "blocked"
    assert sections["private_beta_quota_controls"].status == "blocked"
    assert sections["provider_model_lab"].status == "blocked"
    assert sections["persona_memory"].status == "blocked"
    assert sections["visual_playback_generation"].status == "blocked"
    assert sections["voice_playback"].status == "blocked"
    assert sections["world_event_leak_check"].status == "blocked"
    for token in FORBIDDEN_RESPONSE_TOKENS:
        assert token not in report.model_dump_json()


def test_private_beta_setup_endpoint_is_platform_admin_only_and_safe() -> None:
    client, engine = _client_with_database()
    platform_user_id, platform_token = _seed_user(
        engine,
        "platform-beta-setup@example.test",
        platform_admin=True,
    )
    world_id, worldline_id = _seed_world(engine, owner_user_id=platform_user_id)
    conversation_id = _seed_self_use_demo_evidence(engine, world_id, worldline_id)
    _seed_private_beta_setup_evidence(engine, world_id, worldline_id, conversation_id)
    _authenticate(client, platform_token)

    response = client.get(
        "/observability/readiness/private-beta-setup",
        params={
            "world_id": str(world_id),
            "worldline_id": str(worldline_id),
            "conversation_id": str(conversation_id),
            "manual_play_minutes": "30",
            "resume_verified": "true",
            "failure_notes_recorded": "true",
        },
    )

    assert response.status_code == 200
    assert response.json()["readiness_kind"] == "private_beta_world_setup"
    assert response.json()["status"] == "ok"
    assert response.json()["world_id"] == str(world_id)
    for token in FORBIDDEN_RESPONSE_TOKENS:
        assert token not in response.text

    _member_id, member_token = _seed_user(engine, "member-beta-setup@example.test", False)
    _authenticate(client, member_token)
    forbidden = client.get(
        "/observability/readiness/private-beta-setup",
        params={"world_id": str(world_id), "worldline_id": str(worldline_id)},
    )
    assert forbidden.status_code == 403


def test_private_beta_setup_does_not_create_duplicate_framework_tables() -> None:
    table_names = {
        "beta_checklist_runs",
        "long_run_eval_runs",
        "living_world_release_profiles",
    }
    assert "private_beta_setup_runs" not in table_names
    assert "private_beta_setup_reports" not in table_names
    assert "world_setup_wizard_reports" not in table_names


def _engine() -> Engine:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in (
        User.__table__,
        AuthSession.__table__,
        PlatformRoleAssignment.__table__,
        World.__table__,
        Worldline.__table__,
        WorldMembership.__table__,
        PlayerActorProfile.__table__,
        Agent.__table__,
        AgentPersona.__table__,
        WorldEventModel.__table__,
        WorldSnapshotModel.__table__,
        ConversationSession.__table__,
        ConversationParticipant.__table__,
        ConversationTurn.__table__,
        AuthoringSourceBatch.__table__,
        AuthoringSourceAsset.__table__,
        AuthoringSourceFragment.__table__,
        AuthoringImportRun.__table__,
        AuthoringImportProposal.__table__,
        AuthoringSourceTraceability.__table__,
        MediaAsset.__table__,
        MediaObject.__table__,
        MediaReference.__table__,
        NarrativeArtifact.__table__,
        NarrativePublication.__table__,
        ConversationTurnPresentation.__table__,
        PlayerPrivacyRequest.__table__,
        ModerationReport.__table__,
        ModerationIncident.__table__,
        ModerationAction.__table__,
        MediaJob.__table__,
        ModelInvocation.__table__,
        PromptSnapshot.__table__,
        AgentMemoryItem.__table__,
        MemoryWriteJob.__table__,
        RuntimeDiagnosticEvent.__table__,
        ProviderIntegration.__table__,
        ProviderHealthCheck.__table__,
        ProviderBudgetPolicy.__table__,
        PrivateBetaInvite.__table__,
        PlayerSession.__table__,
        CharacterSpriteSet.__table__,
        CharacterSpriteVariant.__table__,
        SceneBackgroundProfile.__table__,
        VoiceProfile.__table__,
        AgentVoiceProfileBinding.__table__,
        SpeechTranscript.__table__,
        SpeechStyleMapping.__table__,
        VisualWorkflowTemplate.__table__,
        VisualWorkflowTemplateVersion.__table__,
        VisualModelAsset.__table__,
        CharacterVisualGenerationProfile.__table__,
        VisualGenerationPlan.__table__,
        VisualGenerationPlanReference.__table__,
        LongRunEvalRun.__table__,
        LivingWorldReleaseProfile.__table__,
        BetaChecklistRun.__table__,
        BetaChecklistItem.__table__,
    ):
        cast(Table, table).create(engine)
    return engine


def _client_with_database() -> tuple[TestClient, Engine]:
    engine = _engine()
    app = create_app()

    def override_get_db_session() -> Iterator[Session]:
        with Session(engine) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    app.dependency_overrides[get_db_session] = override_get_db_session
    return TestClient(app), engine


def _seed_user(engine: Engine, email: str, platform_admin: bool) -> tuple[uuid.UUID, str]:
    user_id = uuid.uuid4()
    token = f"token-{user_id}"
    now = datetime.now(UTC)
    with Session(engine) as session:
        session.add(User(id=user_id, email=email, display_name=email, is_active=True))
        session.add(
            AuthSession(
                id=uuid.uuid4(),
                user_id=user_id,
                token_hash=hash_session_token(token),
                status=AuthSessionStatus.ACTIVE.value,
                expires_at=now + timedelta(hours=1),
            ),
        )
        if platform_admin:
            session.add(
                PlatformRoleAssignment(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    role=AuthRole.PLATFORM_ADMIN.value,
                    assigned_at=now,
                ),
            )
        session.commit()
    return user_id, token


def _authenticate(client: TestClient, token: str) -> None:
    client.cookies.clear()
    client.headers.clear()
    client.cookies.set(SESSION_COOKIE_NAME, token)
    client.cookies.set(CSRF_COOKIE_NAME, "csrf-token")
    client.headers.update({CSRF_HEADER_NAME: "csrf-token"})


def _seed_world(
    engine: Engine,
    *,
    owner_user_id: uuid.UUID | None = None,
) -> tuple[uuid.UUID, uuid.UUID]:
    user_id = owner_user_id or uuid.uuid4()
    world_id = uuid.uuid4()
    worldline_id = uuid.uuid4()
    with Session(engine) as session:
        if owner_user_id is None:
            session.add(
                User(
                    id=user_id,
                    email=f"readiness-{world_id.hex[:8]}@example.test",
                    display_name="Readiness Owner",
                ),
            )
        session.add(
            World(
                id=world_id,
                owner_user_id=user_id,
                slug=f"readiness-{world_id.hex[:8]}",
                name="Readiness World",
                rules_config={},
            ),
        )
        session.add(
            Worldline(
                id=worldline_id,
                world_id=world_id,
                worldline_key="primary",
                name="Primary",
                description=None,
                parent_worldline_id=None,
                forked_from_snapshot_id=None,
                fork_event_sequence=None,
                status="active",
                created_by_actor_ref="system:test",
                metadata={},
            ),
        )
        session.commit()
    return world_id, worldline_id


def _seed_ready_evidence(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
) -> None:
    now = datetime.now(UTC)
    provider_id = uuid.uuid4()
    checklist_id = uuid.uuid4()
    with Session(engine) as session:
        _seed_release_eval_and_checklist(
            session,
            world_id,
            worldline_id,
            checklist_id=checklist_id,
            checklist_status="passed",
            long_run_status="completed",
            multimodal_status="completed",
            narrative_status="completed",
            release_status="ready",
            now=now,
        )
        session.add(
            ProviderIntegration(
                id=provider_id,
                world_id=world_id,
                scope_kind="world",
                scope_key=str(world_id),
                provider_kind="text_generation",
                adapter_kind="fake",
                provider_key="readiness-provider",
                display_name="Readiness Provider",
                base_url=None,
                auth_ref="env:OPENAI_API_KEY",
                config_json={},
                default_params_json={},
                status="active",
                visibility="world_admin",
            ),
        )
        session.add(
            ProviderBudgetPolicy(
                id=uuid.uuid4(),
                world_id=world_id,
                provider_id=provider_id,
                policy_key="readiness-budget",
                status="active",
                emergency_stop_enabled=False,
                limits_json={"max_daily_estimated_cost": 10},
                metadata_json={},
            ),
        )
        session.commit()


def _seed_blocking_evidence(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
) -> None:
    now = datetime.now(UTC)
    provider_id = uuid.uuid4()
    checklist_id = uuid.uuid4()
    with Session(engine) as session:
        _seed_release_eval_and_checklist(
            session,
            world_id,
            worldline_id,
            checklist_id=checklist_id,
            checklist_status="blocked",
            long_run_status="failed",
            multimodal_status="failed",
            narrative_status="warning",
            release_status="blocked",
            now=now,
        )
        RuntimeDiagnosticsService(session).record(
            RuntimeDiagnosticCreate(
                severity=DiagnosticSeverity.ERROR,
                component=DiagnosticComponent.RUNTIME,
                event_type="readiness.failed",
                message="runtime failed with sk-live-secret and /tmp/private-file",
                details={"authorization": "Bearer sk-live-secret"},
                occurred_at=now,
                world_id=world_id,
            ),
        )
        session.add(
            ProviderIntegration(
                id=provider_id,
                world_id=world_id,
                scope_kind="world",
                scope_key=str(world_id),
                provider_kind="text_generation",
                adapter_kind="fake",
                provider_key="blocked-provider",
                display_name="Blocked Provider",
                base_url=None,
                auth_ref="env:OPENAI_API_KEY",
                config_json={},
                default_params_json={},
                status="active",
                visibility="world_admin",
            ),
        )
        session.add(
            ProviderHealthCheck(
                id=uuid.uuid4(),
                provider_integration_id=provider_id,
                status="unhealthy",
                latency_ms=None,
                checked_at=now,
                error_text="auth failed for sk-live-secret",
                metadata_json={"authorization": "Bearer sk-live-secret"},
            ),
        )
        session.add(
            ProviderBudgetPolicy(
                id=uuid.uuid4(),
                world_id=world_id,
                provider_id=provider_id,
                policy_key="blocked-budget",
                status="active",
                emergency_stop_enabled=True,
                limits_json={"max_daily_estimated_cost": 1},
                metadata_json={},
            ),
        )
        session.commit()


def _seed_public_launch_evidence(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
) -> None:
    now = datetime.now(UTC)
    with Session(engine) as session:
        world = session.get(World, world_id)
        if world is None:
            raise RuntimeError("seeded world is missing")
        owner_id = world.owner_user_id
        artifact_id = uuid.uuid4()
        publication_id = uuid.uuid4()
        conversation_id = uuid.uuid4()
        turn_id = uuid.uuid4()
        background_asset_id = uuid.uuid4()
        audio_asset_id = uuid.uuid4()
        composite_asset_id = uuid.uuid4()
        for asset_id, role, kind in (
            (background_asset_id, "scene_background", "image"),
            (audio_asset_id, "speech_audio", "audio"),
            (composite_asset_id, "composite_image", "image"),
        ):
            session.add(
                MediaAsset(
                    id=asset_id,
                    world_id=world_id,
                    worldline_id=worldline_id,
                    asset_kind=kind,
                    asset_role=role,
                    source_kind="test_fixture",
                    status="available",
                    visibility="reader_visible",
                    storage_uri=f"media://private-object/{asset_id}",
                    mime_type="audio/wav" if kind == "audio" else "image/png",
                    size_bytes=16,
                    checksum_sha256="a" * 64,
                    created_by_actor_ref="system:test",
                    metadata_json={"secret": "must not leak"},
                ),
            )
            session.add(
                MediaObject(
                    id=uuid.uuid4(),
                    asset_id=asset_id,
                    world_id=world_id,
                    worldline_id=worldline_id,
                    object_role="original",
                    storage_uri=f"media://private-object/{asset_id}/object",
                    filename="private-file.png" if kind == "image" else "private-file.wav",
                    mime_type="audio/wav" if kind == "audio" else "image/png",
                    size_bytes=16,
                    checksum_sha256="a" * 64,
                    metadata_json={"storage_uri": "must not leak"},
                ),
            )
        session.add(
            NarrativeArtifact(
                id=artifact_id,
                world_id=world_id,
                worldline_id=worldline_id,
                title="Public Launch Chapter",
                content="Reader-safe content.",
                artifact_kind="chapter_draft",
                artifact_metadata={},
            ),
        )
        session.add(
            NarrativePublication(
                id=publication_id,
                world_id=world_id,
                worldline_id=worldline_id,
                artifact_id=artifact_id,
                status="published",
                reader_visible=True,
                published_metadata={"public_launch_fixture": True},
                published_at=now,
                published_by_user_id=owner_id,
            ),
        )
        session.add(
            ConversationSession(
                id=conversation_id,
                world_id=world_id,
                worldline_id=worldline_id,
                scene_id=None,
                session_key=f"launch-{conversation_id.hex[:8]}",
                title="Public Launch Playback",
                scope_type="world",
                mode="manual_chain",
                status="completed",
                objective="Readiness playback",
                opening_prompt="",
                max_turns=1,
                next_turn_index=1,
                policy_config={},
                writer_config={},
                memory_config={},
            ),
        )
        session.add(
            ConversationTurn(
                id=turn_id,
                session_id=conversation_id,
                turn_index=0,
                speaker_kind="operator",
                speaker_agent_id=None,
                input_text="Reader-safe input",
                output_text="Reader-safe output",
                status="succeeded",
            ),
        )
        session.add(
            ConversationTurnPresentation(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                conversation_id=conversation_id,
                turn_id=turn_id,
                speaker_agent_id=None,
                emotion_key="neutral",
                emotion_intensity=0.5,
                tts_media_asset_id=audio_asset_id,
                background_asset_id=background_asset_id,
                composite_scene_asset_id=composite_asset_id,
                presentation_json={"safe": True},
                render_state="speech_rendered",
            ),
        )
        for asset_id, role in (
            (background_asset_id, "background"),
            (audio_asset_id, "output"),
            (composite_asset_id, "output"),
        ):
            session.add(
                MediaReference(
                    id=uuid.uuid4(),
                    world_id=world_id,
                    worldline_id=worldline_id,
                    asset_id=asset_id,
                    ref_kind="conversation_turn",
                    ref_id=turn_id,
                    ref_role=role,
                    display_order=0,
                    metadata_json={"path": "must not leak"},
                ),
            )
        session.add(
            PlayerPrivacyRequest(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                user_id=owner_id,
                request_kind="export",
                status="completed",
                target_ref_kind=None,
                target_ref_id=None,
                reason="public launch fixture",
                summary_json={"safe": True},
                redaction_plan_json={"shared_world_records_protected": True},
                created_by_actor_ref=f"user:{owner_id}",
                reviewed_by_actor_ref="system:test",
                reviewed_at=now,
                review_note="completed",
                metadata_json={},
            ),
        )
        report_id = uuid.uuid4()
        incident_id = uuid.uuid4()
        action_id = uuid.uuid4()
        session.add(
            ModerationReport(
                id=report_id,
                world_id=world_id,
                worldline_id=worldline_id,
                reporter_user_id=owner_id,
                target_ref_kind="media_asset",
                target_ref_id=background_asset_id,
                category="quality",
                severity="low",
                status="resolved",
                reason="public launch fixture",
                reporter_note="private reporter note with /tmp/private-file",
                evidence_refs_json=[{"kind": "media_asset", "id": str(background_asset_id)}],
                created_by_actor_ref=f"user:{owner_id}",
                reviewed_by_actor_ref="system:test",
                reviewed_at=now,
                review_note="resolved",
                metadata_json={"secret": "must not leak"},
            ),
        )
        session.add(
            ModerationIncident(
                id=incident_id,
                world_id=world_id,
                worldline_id=worldline_id,
                status="closed",
                severity="low",
                title="Public launch fixture incident",
                summary="Resolved public surface review.",
                report_ids_json=[str(report_id)],
                action_ids_json=[str(action_id)],
                evidence_refs_json=[],
                created_by_actor_ref="system:test",
                reviewed_by_actor_ref="system:test",
                reviewed_at=now,
                review_note="closed",
                metadata_json={},
            ),
        )
        session.add(
            ModerationAction(
                id=action_id,
                world_id=world_id,
                worldline_id=worldline_id,
                report_id=report_id,
                incident_id=incident_id,
                action_kind="note_only",
                status="applied",
                target_ref_kind="media_asset",
                target_ref_id=background_asset_id,
                reason="public launch fixture action",
                audit_summary_json={"safe": True},
                evidence_refs_json=[],
                created_by_actor_ref="system:test",
                reviewed_by_actor_ref="system:test",
                reviewed_at=now,
                review_note="applied",
                metadata_json={},
            ),
        )
        session.commit()


def _seed_self_use_demo_evidence(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    *,
    include_memory: bool = True,
    include_visual_plan: bool = True,
    include_voice: bool = True,
    include_required_providers: bool = True,
    include_invocation: bool = True,
    include_traceability: bool = True,
    include_agent_turn: bool = True,
) -> uuid.UUID:
    now = datetime.now(UTC)
    alice_id = uuid.uuid4()
    bob_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    operator_turn_id = uuid.uuid4()
    agent_turn_id = uuid.uuid4()
    background_asset_id = uuid.uuid4()
    sprite_asset_id = uuid.uuid4()
    bob_sprite_asset_id = uuid.uuid4()
    voice_asset_id = uuid.uuid4()
    sprite_set_id = uuid.uuid4()
    sprite_variant_id = uuid.uuid4()
    bob_sprite_set_id = uuid.uuid4()
    bob_sprite_variant_id = uuid.uuid4()
    voice_profile_id = uuid.uuid4()
    provider_ids = {
        "text_generation": uuid.uuid4(),
        "image_generation": uuid.uuid4(),
        "text_to_speech": uuid.uuid4(),
        "speech_to_text": uuid.uuid4(),
    }
    with Session(engine) as session:
        session.add_all(
            [
                Agent(
                    id=alice_id,
                    world_id=world_id,
                    agent_key="alice",
                    display_name="Alice",
                    kind="role_agent",
                    character_profile={},
                    config={},
                    is_enabled=True,
                ),
                Agent(
                    id=bob_id,
                    world_id=world_id,
                    agent_key="bob",
                    display_name="Bob",
                    kind="role_agent",
                    character_profile={},
                    config={},
                    is_enabled=True,
                ),
                AgentPersona(
                    id=uuid.uuid4(),
                    world_id=world_id,
                    agent_id=alice_id,
                    persona_text="Alice is prepared for the self-use demo.",
                    behavior_policy={},
                    policy_plugin_identifier="builtin.default_persona_policy",
                    policy_plugin_config={},
                    is_enabled=True,
                ),
                AgentPersona(
                    id=uuid.uuid4(),
                    world_id=world_id,
                    agent_id=bob_id,
                    persona_text="Bob is prepared for the self-use demo.",
                    behavior_policy={},
                    policy_plugin_identifier="builtin.default_persona_policy",
                    policy_plugin_config={},
                    is_enabled=True,
                ),
            ]
        )
        if include_memory:
            for agent_id, content in (
                (alice_id, "Alice remembers the opening classroom."),
                (bob_id, "Bob remembers Alice at the gate."),
            ):
                session.add(
                    AgentMemoryItem(
                        id=uuid.uuid4(),
                        world_id=world_id,
                        worldline_id=worldline_id,
                        agent_id=agent_id,
                        source_event_id=None,
                        content=content,
                        metadata_json={"source": "authoring_distillation"},
                        embedding=[0.1] * 1536,
                        visibility="private",
                        is_active=True,
                    )
                )
        session.add(
            ConversationSession(
                id=conversation_id,
                world_id=world_id,
                worldline_id=worldline_id,
                scene_id=None,
                session_key=f"demo-{conversation_id.hex[:8]}",
                title="Self-use MVP Demo",
                scope_type="world",
                mode="manual_chain",
                status="running",
                objective="Self-use MVP gate fixture",
                opening_prompt="Begin the safe demo.",
                max_turns=48,
                next_turn_index=2 if include_agent_turn else 1,
                policy_config={},
                writer_config={"include_prompt_preview": False},
                memory_config={"retrieve_memory": True, "write_turn_memory": True},
            )
        )
        session.add_all(
            [
                ConversationParticipant(
                    id=uuid.uuid4(),
                    session_id=conversation_id,
                    agent_id=alice_id,
                    turn_order=0,
                    is_enabled=True,
                ),
                ConversationParticipant(
                    id=uuid.uuid4(),
                    session_id=conversation_id,
                    agent_id=bob_id,
                    turn_order=1,
                    is_enabled=True,
                ),
                ConversationTurn(
                    id=operator_turn_id,
                    session_id=conversation_id,
                    turn_index=0,
                    speaker_kind="operator",
                    speaker_agent_id=None,
                    input_text="Safe operator prompt",
                    output_text="Alice: ready",
                    status="succeeded",
                ),
            ]
        )
        if include_agent_turn:
            session.add(
                ConversationTurn(
                    id=agent_turn_id,
                    session_id=conversation_id,
                    turn_index=1,
                    speaker_kind="agent",
                    speaker_agent_id=alice_id,
                    input_text="Safe agent input",
                    output_text="Alice continues safely.",
                    status="succeeded",
                )
            )
        for asset_id, role, kind in (
            (background_asset_id, "scene_background", "image"),
            (sprite_asset_id, "character_sprite", "image"),
            (bob_sprite_asset_id, "character_sprite", "image"),
            (voice_asset_id, "voice_sample", "audio"),
        ):
            session.add(
                MediaAsset(
                    id=asset_id,
                    world_id=world_id,
                    worldline_id=worldline_id,
                    asset_kind=kind,
                    asset_role=role,
                    source_kind="test_fixture",
                    status="available",
                    visibility="world_admin",
                    mime_type="audio/wav" if kind == "audio" else "image/png",
                    size_bytes=16,
                    checksum_sha256="b" * 64,
                    created_by_actor_ref="system:test",
                    metadata_json={"safe": True},
                )
            )
        session.add(
            CharacterSpriteSet(
                id=sprite_set_id,
                world_id=world_id,
                worldline_id=worldline_id,
                agent_id=alice_id,
                style_key="default",
                display_name="Alice Default",
                default_variant_id=sprite_variant_id,
                status="active",
                visibility="world_admin",
                metadata_json={},
            )
        )
        session.add(
            CharacterSpriteSet(
                id=bob_sprite_set_id,
                world_id=world_id,
                worldline_id=worldline_id,
                agent_id=bob_id,
                style_key="default",
                display_name="Bob Default",
                default_variant_id=bob_sprite_variant_id,
                status="active",
                visibility="world_admin",
                metadata_json={},
            )
        )
        session.add(
            CharacterSpriteVariant(
                id=sprite_variant_id,
                world_id=world_id,
                worldline_id=worldline_id,
                sprite_set_id=sprite_set_id,
                asset_id=sprite_asset_id,
                expression_key="neutral",
                mood_tags_json=["neutral"],
                priority=100,
                is_default=True,
                status="active",
                visibility="world_admin",
                metadata_json={},
            )
        )
        session.add(
            CharacterSpriteVariant(
                id=bob_sprite_variant_id,
                world_id=world_id,
                worldline_id=worldline_id,
                sprite_set_id=bob_sprite_set_id,
                asset_id=bob_sprite_asset_id,
                expression_key="neutral",
                mood_tags_json=["neutral"],
                priority=100,
                is_default=True,
                status="active",
                visibility="world_admin",
                metadata_json={},
            )
        )
        session.add(
            SceneBackgroundProfile(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                scene_id=None,
                location_key="opening",
                asset_id=background_asset_id,
                priority=100,
                is_default=True,
                status="active",
                visibility="world_admin",
                metadata_json={},
            )
        )
        if include_voice:
            session.add(
                VoiceProfile(
                    id=voice_profile_id,
                    world_id=world_id,
                    worldline_id=worldline_id,
                    profile_key="alice-default",
                    display_name="Alice Default Voice",
                    status="active",
                    visibility="world_admin",
                    owner_kind="agent",
                    owner_agent_id=alice_id,
                    provider_integration_id=None,
                    provider_voice_id="alice-voice",
                    voice_kind="imported",
                    reference_asset_id=voice_asset_id,
                    consent_status="admin_authorized",
                    usage_policy_json={},
                    metadata_json={},
                )
            )
            for agent_id in (alice_id, bob_id):
                session.add(
                    AgentVoiceProfileBinding(
                        id=uuid.uuid4(),
                        world_id=world_id,
                        worldline_id=worldline_id,
                        agent_id=agent_id,
                        voice_profile_id=voice_profile_id,
                        binding_role="default",
                        priority=100,
                        is_default=True,
                        style_overrides_json={"emotion": "neutral"},
                    )
                )
        session.add(
            ConversationTurnPresentation(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                conversation_id=conversation_id,
                turn_id=operator_turn_id,
                speaker_agent_id=alice_id,
                emotion_key="neutral",
                emotion_intensity=1.0,
                sprite_set_id=sprite_set_id,
                sprite_variant_id=sprite_variant_id,
                voice_profile_id=voice_profile_id if include_voice else None,
                background_asset_id=background_asset_id,
                presentation_json={"source": "demo_world_assembly"},
                render_state="speech_rendered" if include_voice else "visual_rendered",
            )
        )
        if include_required_providers:
            for kind, provider_id in provider_ids.items():
                session.add(
                    ProviderIntegration(
                        id=provider_id,
                        world_id=world_id,
                        scope_kind="world",
                        scope_key=str(world_id),
                        provider_kind=kind,
                        adapter_kind="fake",
                        provider_key=f"self-use-{kind}",
                        display_name=f"Self-use {kind}",
                        base_url=None,
                        auth_ref="env:SAFE_PROVIDER_KEY",
                        config_json={"available_models": ["safe-model"]},
                        default_params_json={"model": "safe-model"},
                        status="active",
                        visibility="world_admin",
                    )
                )
                session.add(
                    ProviderHealthCheck(
                        id=uuid.uuid4(),
                        provider_integration_id=provider_id,
                        status="healthy",
                        latency_ms=10,
                        checked_at=now,
                        metadata_json={"smoke_test": True},
                    )
                )
        if include_visual_plan:
            session.add(
                CharacterVisualGenerationProfile(
                    id=uuid.uuid4(),
                    world_id=world_id,
                    worldline_id=worldline_id,
                    agent_id=alice_id,
                    preferred_checkpoint_id=None,
                    allowed_lora_ids_json=[],
                    default_lora_ids_json=[],
                    banned_lora_ids_json=[],
                    prompt_fragments_json={"subject": ["Alice"]},
                    negative_prompt_fragments_json={},
                    reference_asset_ids_json=[str(sprite_asset_id)],
                    default_workflow_template_id=None,
                    expression_workflow_template_id=None,
                    cg_workflow_template_id=None,
                    outfit_policy_json={},
                    pose_policy_json={},
                    review_status="approved",
                    visibility="world_admin",
                )
            )
            session.add(
                CharacterVisualGenerationProfile(
                    id=uuid.uuid4(),
                    world_id=world_id,
                    worldline_id=worldline_id,
                    agent_id=bob_id,
                    preferred_checkpoint_id=None,
                    allowed_lora_ids_json=[],
                    default_lora_ids_json=[],
                    banned_lora_ids_json=[],
                    prompt_fragments_json={"subject": ["Bob"]},
                    negative_prompt_fragments_json={},
                    reference_asset_ids_json=[],
                    default_workflow_template_id=None,
                    expression_workflow_template_id=None,
                    cg_workflow_template_id=None,
                    outfit_policy_json={},
                    pose_policy_json={},
                    review_status="approved",
                    visibility="world_admin",
                )
            )
            session.add(
                VisualGenerationPlan(
                    id=uuid.uuid4(),
                    world_id=world_id,
                    worldline_id=worldline_id,
                    intent="expression_variant",
                    provider_id=provider_ids["image_generation"],
                    workflow_template_id=None,
                    workflow_template_version_id=None,
                    status="validated",
                    character_ids_json=[str(alice_id)],
                    prompt_plan_json={"subject": "Alice"},
                    model_plan_json={},
                    output_plan_json={"asset_kind": "character_expression"},
                    validation_results_json={"valid": True},
                    source_context_json={"safe": True},
                )
            )
        session.add(
            MediaJob(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                conversation_id=conversation_id,
                turn_id=operator_turn_id,
                agent_id=alice_id,
                job_kind="composition",
                provider_kind="fake",
                status="succeeded",
                priority=100,
                provider_config_json={},
                request_json={"safe": True},
                result_json={"safe": True},
                created_by_actor_ref="system:test",
                finished_at=now,
            )
        )
        if include_invocation:
            invocation_id = uuid.uuid4()
            session.add(
                ModelInvocation(
                    id=invocation_id,
                    world_id=world_id,
                    worldline_id=worldline_id,
                    trace_id=uuid.uuid4(),
                    invocation_kind="conversation_turn",
                    actor_kind="agent",
                    actor_ref="agent:alice",
                    agent_id=alice_id,
                    conversation_id=conversation_id,
                    turn_id=agent_turn_id if include_agent_turn else operator_turn_id,
                    provider_kind="local_stub",
                    model_name="safe-model",
                    input_json={"redacted": True},
                    output_json={"redacted": True},
                    usage_json={},
                    latency_ms=20,
                    estimated_cost=0,
                    status="succeeded",
                    visibility="world_admin",
                    redaction_status="redacted",
                    retention_policy="local_debug",
                    contains_sensitive_context=False,
                )
            )
        if include_traceability:
            batch_id = uuid.uuid4()
            source_asset_id = uuid.uuid4()
            fragment_id = uuid.uuid4()
            run_id = uuid.uuid4()
            assembly_proposal_id = uuid.uuid4()
            session.add(
                AuthoringSourceBatch(
                    id=batch_id,
                    world_id=world_id,
                    worldline_id=worldline_id,
                    batch_key="self-use-demo",
                    display_name="Self-use Demo Source",
                    source_kind="script",
                    status="active",
                    visibility="private",
                    metadata_json={},
                    created_by_actor_ref="system:test",
                )
            )
            session.add(
                AuthoringSourceAsset(
                    id=source_asset_id,
                    world_id=world_id,
                    worldline_id=worldline_id,
                    batch_id=batch_id,
                    media_asset_id=None,
                    source_asset_kind="script",
                    source_label="opening.ks",
                    status="active",
                    metadata_json={},
                )
            )
            session.add(
                AuthoringSourceFragment(
                    id=fragment_id,
                    world_id=world_id,
                    worldline_id=worldline_id,
                    source_asset_id=source_asset_id,
                    fragment_key="opening",
                    fragment_kind="dialogue",
                    sequence=1,
                    excerpt_text="Alice: ready",
                    locator_json={"line": 1},
                    metadata_json={},
                )
            )
            session.add(
                AuthoringImportRun(
                    id=run_id,
                    world_id=world_id,
                    worldline_id=worldline_id,
                    source_batch_id=batch_id,
                    run_kind="manual",
                    status="applied",
                    summary_json={"assembly_ready": True},
                    created_by_actor_ref="system:test",
                )
            )
            session.add(
                AuthoringImportProposal(
                    id=assembly_proposal_id,
                    world_id=world_id,
                    worldline_id=worldline_id,
                    run_id=run_id,
                    source_fragment_id=fragment_id,
                    proposal_kind="other",
                    target_ref_kind="demo_world_assembly",
                    title="Self-use MVP Demo Assembly",
                    summary="Safe demo assembly evidence.",
                    proposed_payload_json={"review_apply_required": True},
                    evidence_json={"source_fragment_ids": [str(fragment_id)]},
                    confidence=0.9,
                    priority=100,
                    status="applied",
                    applied_ref_json={
                        "applied_ref_kind": "conversation_session",
                        "applied_ref_id": str(conversation_id),
                    },
                )
            )
        session.commit()
    return conversation_id


def _seed_leaky_world_event(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
) -> None:
    with Session(engine) as session:
        session.add(
            WorldEventModel(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                sequence=1,
                event_name="self_use.leak_check",
                importance="system",
                payload={
                    "storage_uri": "media://private-object/hidden",
                    "authorization": "Bearer sk-live-secret",
                },
                wall_time=datetime.now(UTC),
                actor_ref="system:test",
            )
        )
        session.commit()


def _seed_private_beta_setup_evidence(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    conversation_id: uuid.UUID,
) -> None:
    tester_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    now = datetime.now(UTC)
    with Session(engine) as session:
        session.add(
            User(
                id=tester_id,
                email=f"tester-{tester_id.hex[:8]}@example.test",
                display_name="Private Beta Tester",
            )
        )
        session.add(
            WorldMembership(
                id=uuid.uuid4(),
                world_id=world_id,
                user_id=tester_id,
                role="human_user",
            )
        )
        session.add(
            PlayerActorProfile(
                id=actor_id,
                world_id=world_id,
                worldline_id=worldline_id,
                user_id=tester_id,
                actor_ref=f"player:{tester_id}",
                display_name="Tester",
                current_scene_id=None,
                profile_json={"safe": True},
                is_active=True,
            )
        )
        session.add(
            PrivateBetaInvite(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                invited_email="tester@example.test",
                invited_user_id=None,
                token_hash="a" * 64,
                status="redeemed",
                intended_world_role="human_user",
                beta_role="tester",
                expires_at=now + timedelta(days=7),
                accepted_at=None,
                redeemed_at=now,
                redeemed_by_user_id=tester_id,
                revoked_at=None,
                revoked_by_actor_ref=None,
                revocation_reason=None,
                created_by_actor_ref="user:admin",
                metadata_json={"safe": True},
            )
        )
        session.add(
            PlayerSession(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                user_id=tester_id,
                player_actor_id=actor_id,
                conversation_session_id=conversation_id,
                scene_id=None,
                last_turn_id=None,
                last_presentation_id=None,
                route_state_json={"route": "opening"},
                resume_state_json={"safe": True},
                recovery_status="ready",
                status="active",
                last_seen_at=now,
            )
        )
        session.add(
            ProviderBudgetPolicy(
                id=uuid.uuid4(),
                world_id=world_id,
                provider_id=None,
                policy_key="private-beta-player-capability-quota",
                status="active",
                emergency_stop_enabled=False,
                limits_json={
                    "max_daily_invocations": 100,
                    "default_player": {"max_daily_invocations": 20},
                    "capabilities": {
                        "text_generation": {"max_daily_invocations": 20},
                        "image_generation": {"max_daily_invocations": 4},
                        "text_to_speech": {"max_daily_media_jobs": 20},
                    },
                },
                metadata_json={"safe": True},
            )
        )
        session.commit()


def _seed_release_eval_and_checklist(
    session: Session,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    *,
    checklist_id: uuid.UUID,
    checklist_status: str,
    long_run_status: str,
    multimodal_status: str,
    narrative_status: str,
    release_status: str,
    now: datetime,
) -> None:
    session.add(
        LivingWorldReleaseProfile(
            id=uuid.uuid4(),
            world_id=world_id,
            profile_key="default",
            status=release_status,
            branch_policy={},
            backup_policy={},
            content_review_policy={},
            player_permission_policy={},
            worldline_policy={},
            checklist={},
            metadata_json={},
        ),
    )
    session.add(
        BetaChecklistRun(
            id=checklist_id,
            world_id=world_id,
            worldline_id=worldline_id,
            run_key="beta-readiness",
            status=checklist_status,
            summary="safe summary",
            evidence={"refs": []},
            blocker_count=0 if checklist_status == "passed" else 1,
            created_by_actor_ref="system:test",
            metadata_json={},
        ),
    )
    session.add(
        BetaChecklistItem(
            id=uuid.uuid4(),
            run_id=checklist_id,
            item_key="safe-check",
            title="Safe check",
            status=checklist_status,
            evidence={},
            recommendation=None,
        ),
    )
    for eval_key, status in (
        ("long-run-seven-day", long_run_status),
        ("multimodal-smoke", multimodal_status),
        ("narrative-quality-seven-day", narrative_status),
    ):
        session.add(
            LongRunEvalRun(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                eval_key=eval_key,
                horizon_days=7,
                status=status,
                started_at=now,
                finished_at=now,
                metrics={},
                recommendations=[],
                blockers=[],
                metadata_json={},
            ),
        )


def _framework_counts(session: Session) -> tuple[int, int, int]:
    return (
        int(session.scalar(select(func.count(BetaChecklistRun.id))) or 0),
        int(session.scalar(select(func.count(LongRunEvalRun.id))) or 0),
        int(session.scalar(select(func.count(LivingWorldReleaseProfile.id))) or 0),
    )
