from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from noveland.agents.models import Agent
from noveland.auth.models import User
from noveland.authoring.models import AuthoringImportProposal, AuthoringImportRun
from noveland.beta_feedback.models import BetaFeedbackReport
from noveland.conversations.models import ConversationSession, ConversationTurn
from noveland.invocations.models import ModelInvocation
from noveland.media.models import MediaJob
from noveland.memory.models import MemoryBackendProfile, MemoryWriteJob
from noveland.observability import NormalUseStressService
from noveland.player_sessions.models import PlayerSession
from noveland.providers.models import ProviderBudgetPolicy, ProviderIntegration
from noveland.worlds.models import (
    LongRunEvalRun,
    PlayerActorProfile,
    Scene,
    World,
    Worldline,
)
from sqlalchemy import Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

FORBIDDEN_STRESS_MARKERS = (
    "storage_uri",
    "file://",
    "local://",
    "object://",
    "raw_prompt",
    "raw output",
    "prompt_snapshot",
    "resolved_secret",
    "sk-live",
    "authorization",
    "bearer ",
    "invite_token",
    "local_model_path",
    "base64",
)


def test_normal_use_stress_passes_deterministic_fake_provider_baseline() -> None:
    engine = _engine()
    _seed_stress_fixture(engine)

    with Session(engine) as session:
        report = NormalUseStressService(session).report()

    checks = {check.check_key: check for check in report.checks}
    assert report.status == "ok"
    assert report.observed_world_count == 3
    assert report.observed_worldline_count == 6
    assert report.observed_player_session_count == 6
    assert report.observed_fake_provider_count == 6
    assert report.observed_turn_equivalent >= 120
    assert report.real_provider_profile_enabled is False
    assert report.latency_summary["invocation_count"] == 18
    assert report.cost_summary["estimated_cost_total"] == "0.18000000"
    assert report.failure_summary["failed_invocations"] == 0
    assert report.quota_summary["active_policy_count"] == 3
    assert checks["baseline_coverage"].status == "ok"
    assert checks["worldline_player_isolation"].status == "ok"
    assert checks["provider_quota_controls"].status == "ok"
    assert checks["runtime_path_coverage"].status == "ok"
    assert checks["long_session_coverage"].status == "ok"
    assert checks["default_fake_provider_profile"].status == "ok"
    _assert_no_forbidden_markers(report.model_dump(mode="json"))


def test_normal_use_stress_detects_cross_worldline_session_leak() -> None:
    engine = _engine()
    seeded = _seed_stress_fixture(engine)
    source = seeded[0]
    target = seeded[1]
    with Session(engine) as session:
        player_session = session.scalars(
            select(PlayerSession).where(PlayerSession.world_id == source["world_id"]),
        ).first()
        assert player_session is not None
        player_session.worldline_id = target["worldline_ids"][0]
        session.commit()

    with Session(engine) as session:
        report = NormalUseStressService(session).report()

    isolation = {check.check_key: check for check in report.checks}["worldline_player_isolation"]
    assert report.status == "blocked"
    assert isolation.status == "blocked"
    assert any("cross-worldline actor" in blocker for blocker in isolation.blockers)
    assert any("cross-worldline conversation" in blocker for blocker in isolation.blockers)
    _assert_no_forbidden_markers(report.model_dump(mode="json"))


def test_normal_use_stress_blocks_missing_quota_policy() -> None:
    engine = _engine()
    seeded = _seed_stress_fixture(engine)
    with Session(engine) as session:
        session.query(ProviderBudgetPolicy).filter(
            ProviderBudgetPolicy.world_id == seeded[0]["world_id"],
        ).delete()
        session.commit()

    with Session(engine) as session:
        report = NormalUseStressService(session).report()

    quota = {check.check_key: check for check in report.checks}["provider_quota_controls"]
    assert report.status == "blocked"
    assert quota.status == "blocked"
    assert any("no active provider budget policy" in blocker for blocker in quota.blockers)
    _assert_no_forbidden_markers(report.model_dump(mode="json"))


def test_normal_use_stress_blocks_insufficient_turn_equivalent() -> None:
    engine = _engine()
    _seed_stress_fixture(engine, turns_per_conversation=6, eval_turn_equivalent=0)

    with Session(engine) as session:
        report = NormalUseStressService(session).report()

    long_session = {check.check_key: check for check in report.checks}["long_session_coverage"]
    assert report.status == "blocked"
    assert report.observed_turn_equivalent == 36
    assert long_session.status == "blocked"
    assert any("turn-equivalent evidence" in blocker for blocker in long_session.blockers)
    _assert_no_forbidden_markers(report.model_dump(mode="json"))


def _engine() -> Engine:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in (
        User.__table__,
        World.__table__,
        Worldline.__table__,
        Scene.__table__,
        Agent.__table__,
        MemoryBackendProfile.__table__,
        ConversationSession.__table__,
        ConversationTurn.__table__,
        ProviderIntegration.__table__,
        ProviderBudgetPolicy.__table__,
        ModelInvocation.__table__,
        MediaJob.__table__,
        MemoryWriteJob.__table__,
        PlayerActorProfile.__table__,
        PlayerSession.__table__,
        BetaFeedbackReport.__table__,
        AuthoringImportRun.__table__,
        AuthoringImportProposal.__table__,
        LongRunEvalRun.__table__,
    ):
        assert isinstance(table, Table)
        table.create(engine)
    return engine


def _seed_stress_fixture(
    engine: Engine,
    *,
    turns_per_conversation: int = 20,
    eval_turn_equivalent: int = 20,
) -> list[dict[str, Any]]:
    now = datetime.now(UTC)
    seeded: list[dict[str, Any]] = []
    with Session(engine) as session:
        memory_backend = MemoryBackendProfile(
            id=uuid.uuid4(),
            profile_key="stress-local-memory",
            name="Stress Local Memory",
            backend_kind="local_pgvector",
            vector_store_config={"provider": "fake"},
            llm_config={"provider": "fake"},
            embedder_config={"provider": "fake"},
            reranker_config={},
            secret_refs={},
            is_enabled=True,
        )
        session.add(memory_backend)
        for world_index in range(3):
            owner_id = uuid.uuid4()
            world_id = uuid.uuid4()
            session.add(
                User(
                    id=owner_id,
                    email=f"stress-owner-{world_index}@example.test",
                    display_name=f"Stress Owner {world_index}",
                    is_active=True,
                ),
            )
            session.add(
                World(
                    id=world_id,
                    owner_user_id=owner_id,
                    slug=f"stress-world-{world_index}",
                    name=f"Stress World {world_index}",
                    description="Normal-use stress fixture.",
                    rules_config={},
                    is_active=True,
                ),
            )
            scene_id = uuid.uuid4()
            session.add(
                Scene(
                    id=scene_id,
                    world_id=world_id,
                    scene_key="stress-room",
                    name="Stress Room",
                    description="Safe deterministic test scene.",
                    region_key="stress",
                    location_tags=["stress"],
                    opening_rules={},
                    is_active=True,
                ),
            )
            agent_id = uuid.uuid4()
            session.add(
                Agent(
                    id=agent_id,
                    world_id=world_id,
                    home_scene_id=scene_id,
                    agent_key=f"stress-guide-{world_index}",
                    display_name=f"Stress Guide {world_index}",
                    kind="role_agent",
                    narrative_role="supporting_cast",
                    importance="minor",
                    canon_status="original_expansion",
                    character_category="side_character",
                    character_profile={"summary": "Safe deterministic stress guide."},
                    config={},
                    is_enabled=True,
                ),
            )
            session.add(
                ProviderIntegration(
                    id=uuid.uuid4(),
                    world_id=world_id,
                    scope_kind="world",
                    scope_key=str(world_id),
                    provider_kind="text_generation",
                    adapter_kind="fake",
                    provider_key=f"stress-fake-text-{world_index}",
                    display_name=f"Stress Fake Text {world_index}",
                    base_url=None,
                    auth_ref="env:STRESS_FAKE_PROVIDER",
                    config_json={"fixture": "normal_use_stress"},
                    default_params_json={"model": "fake-text"},
                    status="active",
                    visibility="world_admin",
                ),
            )
            session.add(
                ProviderIntegration(
                    id=uuid.uuid4(),
                    world_id=world_id,
                    scope_kind="world",
                    scope_key=f"{world_id}:image",
                    provider_kind="image_generation",
                    adapter_kind="fake",
                    provider_key=f"stress-fake-image-{world_index}",
                    display_name=f"Stress Fake Image {world_index}",
                    base_url=None,
                    auth_ref="env:STRESS_FAKE_PROVIDER",
                    config_json={"fixture": "normal_use_stress"},
                    default_params_json={"model": "fake-image"},
                    status="active",
                    visibility="world_admin",
                ),
            )
            session.add(
                ProviderBudgetPolicy(
                    id=uuid.uuid4(),
                    world_id=world_id,
                    provider_id=None,
                    policy_key=f"stress-budget-{world_index}",
                    status="active",
                    emergency_stop_enabled=False,
                    limits_json={
                        "daily_invocation_limit": 1000,
                        "daily_cost_limit": "1.00",
                        "capabilities": {"text_generation": 500, "image_generation": 100},
                    },
                    metadata_json={"fixture": "normal_use_stress"},
                ),
            )
            worldline_ids: list[uuid.UUID] = []
            for worldline_index in range(2):
                worldline_id = uuid.uuid4()
                worldline_ids.append(worldline_id)
                session.add(
                    Worldline(
                        id=worldline_id,
                        world_id=world_id,
                        worldline_key=f"stress-line-{worldline_index}",
                        name=f"Stress Line {worldline_index}",
                        description="Deterministic stress worldline.",
                        parent_worldline_id=None,
                        forked_from_snapshot_id=None,
                        fork_event_sequence=None,
                        status="active",
                        created_by_actor_ref="system:normal-use-stress",
                        metadata_json={"fixture": "normal_use_stress"},
                    ),
                )
                conversation_id = uuid.uuid4()
                session.add(
                    ConversationSession(
                        id=conversation_id,
                        world_id=world_id,
                        worldline_id=worldline_id,
                        scene_id=None,
                        session_key=f"stress-{world_index}-{worldline_index}",
                        title=f"Stress Conversation {world_index}-{worldline_index}",
                        scope_type="world",
                        mode="manual_chain",
                        status="completed",
                        objective="normal-use stress baseline",
                        opening_prompt="",
                        max_turns=turns_per_conversation,
                        next_turn_index=turns_per_conversation,
                        policy_config={},
                        writer_config={},
                        memory_config={},
                    ),
                )
                last_turn_id: uuid.UUID | None = None
                for turn_index in range(turns_per_conversation):
                    turn_id = uuid.uuid4()
                    last_turn_id = turn_id
                    session.add(
                        ConversationTurn(
                            id=turn_id,
                            session_id=conversation_id,
                            turn_index=turn_index,
                            speaker_kind="agent",
                            speaker_agent_id=agent_id,
                            input_text=f"stress input {turn_index}",
                            output_text=f"stress output {turn_index}",
                            status="succeeded",
                        ),
                    )
                    if turn_index < 3:
                        invocation_id = uuid.uuid4()
                        session.add(
                            ModelInvocation(
                                id=invocation_id,
                                world_id=world_id,
                                worldline_id=worldline_id,
                                trace_id=uuid.uuid4(),
                                parent_invocation_id=None,
                                invocation_kind="conversation_turn",
                                actor_kind="service",
                                actor_ref="system:normal-use-stress",
                                agent_id=agent_id,
                                conversation_id=conversation_id,
                                turn_id=turn_id,
                                world_event_id=None,
                                media_job_id=None,
                                media_asset_id=None,
                                memory_write_job_id=None,
                                provider_kind="local_stub",
                                provider_profile_id=None,
                                model_name="fake-stress-model",
                                model_version=None,
                                prompt_template_key=None,
                                prompt_template_version=None,
                                input_text=None,
                                output_text=None,
                                input_json={"summary": "redacted"},
                                output_json={"summary": "redacted"},
                                request_params_json={"temperature": 0},
                                response_metadata_json={"adapter": "fake"},
                                usage_json={"total_tokens": 12},
                                latency_ms=25 + turn_index,
                                estimated_cost=Decimal("0.01000000"),
                                status="succeeded",
                                error_text=None,
                                visibility="world_admin",
                                redaction_status="redacted",
                                retention_policy="eval_only",
                                contains_sensitive_context=False,
                                purge_after=None,
                            ),
                        )
                session.add(
                    MediaJob(
                        id=uuid.uuid4(),
                        world_id=world_id,
                        worldline_id=worldline_id,
                        conversation_id=conversation_id,
                        turn_id=last_turn_id,
                        agent_id=agent_id,
                        job_kind="image_generation",
                        provider_kind="fake",
                        status="succeeded",
                        priority=0,
                        cancel_policy=None,
                        deadline_hint=None,
                        dedupe_key=f"stress-media-{world_index}-{worldline_index}",
                        invalidation_key=None,
                        source_event_id=None,
                        source_invocation_id=None,
                        provider_config_json={"adapter": "fake"},
                        request_json={"safe_ref": "stress_scene"},
                        result_json={"safe_ref": "stress_media"},
                        error_text=None,
                        created_by_actor_ref="system:normal-use-stress",
                        started_at=now,
                        finished_at=now + timedelta(seconds=1),
                    ),
                )
                memory_job_id = uuid.uuid4()
                session.add(
                    MemoryWriteJob(
                        id=memory_job_id,
                        world_id=world_id,
                        worldline_id=worldline_id,
                        agent_id=agent_id,
                        backend_profile_id=memory_backend.id,
                        source_kind="conversation_turn",
                        source_id=last_turn_id or uuid.uuid4(),
                        payload_json={"summary": "stress memory"},
                        dedupe_key=f"stress-memory-{world_index}-{worldline_index}",
                        status="succeeded",
                        attempt_count=1,
                        next_attempt_at=now,
                        last_error=None,
                        processed_at=now,
                    ),
                )
                feedback_user_id = uuid.uuid4()
                session.add(
                    User(
                        id=feedback_user_id,
                        email=f"stress-player-{world_index}-{worldline_index}@example.test",
                        display_name=f"Stress Player {world_index}-{worldline_index}",
                        is_active=True,
                    ),
                )
                player_actor_id = uuid.uuid4()
                session.add(
                    PlayerActorProfile(
                        id=player_actor_id,
                        world_id=world_id,
                        worldline_id=worldline_id,
                        user_id=feedback_user_id,
                        actor_ref=f"player:stress:{world_index}:{worldline_index}",
                        display_name=f"Stress Player {world_index}-{worldline_index}",
                        current_scene_id=scene_id,
                        profile_json={"fixture": "normal_use_stress"},
                        is_active=True,
                    ),
                )
                session.add(
                    PlayerSession(
                        id=uuid.uuid4(),
                        world_id=world_id,
                        worldline_id=worldline_id,
                        user_id=feedback_user_id,
                        player_actor_id=player_actor_id,
                        conversation_session_id=conversation_id,
                        scene_id=scene_id,
                        last_turn_id=last_turn_id,
                        last_presentation_id=None,
                        route_state_json={"route": "stress"},
                        resume_state_json={"status": "ready"},
                        recovery_status="ready",
                        status="active",
                        last_seen_at=now,
                    ),
                )
                session.add(
                    BetaFeedbackReport(
                        id=uuid.uuid4(),
                        world_id=world_id,
                        worldline_id=worldline_id,
                        reporter_user_id=feedback_user_id,
                        player_actor_id=player_actor_id,
                        issue_type="ux",
                        severity="low",
                        status="triaged",
                        title="Stress feedback",
                        description="Safe deterministic feedback.",
                        reporter_note=None,
                        evidence_refs_json=[
                            {"kind": "conversation", "id": str(conversation_id)},
                        ],
                        repair_proposal_refs_json=[],
                        triage_note="Reviewed for stress baseline.",
                        triaged_by_actor_ref="system:normal-use-stress",
                        triaged_at=now,
                        moderation_report_id=None,
                        metadata_json={"fixture": "normal_use_stress"},
                    ),
                )
                import_run_id = uuid.uuid4()
                session.add(
                    AuthoringImportRun(
                        id=import_run_id,
                        world_id=world_id,
                        worldline_id=worldline_id,
                        source_batch_id=None,
                        run_kind="preview",
                        status="previewed",
                        summary_json={"fixture": "normal_use_stress"},
                        created_by_actor_ref="system:normal-use-stress",
                    ),
                )
                session.add(
                    AuthoringImportProposal(
                        id=uuid.uuid4(),
                        world_id=world_id,
                        worldline_id=worldline_id,
                        run_id=import_run_id,
                        source_fragment_id=None,
                        proposal_kind="dialogue",
                        target_ref_kind="conversation",
                        target_ref_id=conversation_id,
                        title="Stress dialogue repair proposal",
                        summary="Proposal-only stress repair evidence.",
                        proposed_payload_json={"action": "review_only"},
                        evidence_json={"feedback": "stress"},
                        confidence=0.9,
                        priority=10,
                        status="proposed",
                        applied_ref_json={},
                    ),
                )
                session.add(
                    LongRunEvalRun(
                        id=uuid.uuid4(),
                        world_id=world_id,
                        worldline_id=worldline_id,
                        eval_key=f"stress-long-run-{world_index}-{worldline_index}",
                        horizon_days=7,
                        status="completed",
                        started_at=now,
                        finished_at=now + timedelta(minutes=1),
                        metrics={"turn_equivalent": eval_turn_equivalent},
                        recommendations=[],
                        blockers=[],
                        metadata_json={"fixture": "normal_use_stress"},
                    ),
                )
            seeded.append({"world_id": world_id, "worldline_ids": worldline_ids})
        session.commit()
    return seeded


def _assert_no_forbidden_markers(payload: object) -> None:
    if isinstance(payload, dict):
        payload = {
            key: value
            for key, value in payload.items()
            if key not in {"suppressed_fields", "non_goals"}
        }
    text = str(payload).lower()
    for marker in FORBIDDEN_STRESS_MARKERS:
        assert marker not in text
