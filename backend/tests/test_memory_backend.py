from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
from noveland.agents.models import Agent, AgentRuntimeRun
from noveland.auth.models import User
from noveland.conversations.models import ConversationSession, ConversationTurn
from noveland.core.settings import AppSettings
from noveland.events.models import WorldEventModel
from noveland.memory import (
    FakeMemoryBackend,
    LocalPgvectorMemoryBackend,
    Mem0OssMemoryBackend,
    MemoryBackendKind,
    MemoryBackendProfileCreate,
    MemoryBackendProfileService,
    MemoryDeleteScope,
    MemoryEvalCase,
    MemoryEvent,
    MemoryMessage,
    MemoryProfileSnapshotRecord,
    MemorySearchRequest,
    MemoryService,
    MemoryTurn,
    MemoryWriteJobStatus,
    run_memory_eval_cases,
)
from noveland.memory.errors import MemoryValidationError
from noveland.memory.models import (
    AgentMemoryItem,
    AgentProfileSnapshotModel,
    MemoryBackendProfile,
    MemoryRetrievalLog,
    MemoryWriteJob,
    MemoryWriteLog,
)
from noveland.plugins.constants import BUILTIN_MEM0_OSS_MEMORY
from noveland.worlds.models import World, Worldline
from pydantic import ValidationError
from sqlalchemy import Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_memory_turn_requires_at_least_one_message() -> None:
    with pytest.raises(ValidationError):
        MemoryTurn(
            world_id=uuid.uuid4(),
            agent_id=uuid.uuid4(),
            messages=[],
            dedupe_key="turn-1",
        )


def test_local_pgvector_memory_backend_records_lists_searches_and_deletes_scope() -> None:
    engine = _engine()
    user_id = _seed_user(engine)
    world_id = _seed_world(engine, user_id)
    agent_id = _seed_agent(engine, world_id)

    with Session(engine) as session:
        backend = LocalPgvectorMemoryBackend(session)
        first = backend.record_turn(
            MemoryTurn(
                world_id=world_id,
                agent_id=agent_id,
                messages=[MemoryMessage(role="assistant", content="likes green tea")],
                dedupe_key="turn-1",
            ),
        )
        second = backend.record_turn(
            MemoryTurn(
                world_id=world_id,
                agent_id=agent_id,
                messages=[MemoryMessage(role="assistant", content="likes red apples")],
                dedupe_key="turn-2",
            ),
        )
        listed = backend.list_memories(world_id, agent_id)
        searched = backend.search(
            MemorySearchRequest(
                world_id=world_id,
                agent_id=agent_id,
                query_text="green tea",
            ),
        )
        delete_result = backend.delete_scope(
            MemoryDeleteScope(
                world_id=world_id,
                agent_id=agent_id,
                run_id=None,
            ),
        )
        after_delete = backend.list_memories(world_id, agent_id)
        session.commit()

    assert set(first.backend_ids) | set(second.backend_ids) == {item.id for item in listed}
    assert searched.items[0].content == "likes green tea"
    assert searched.items[0].score is not None
    assert delete_result.deleted_count == 2
    assert after_delete == []


def test_fake_memory_backend_matches_long_term_memory_contract() -> None:
    world_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    backend = FakeMemoryBackend()

    turn_result = backend.record_turn(
        MemoryTurn(
            world_id=world_id,
            agent_id=agent_id,
            messages=[MemoryMessage(role="assistant", content="remembers the blue gate")],
            dedupe_key="turn-1",
        )
    )
    event_result = backend.record_events(
        [
            MemoryEvent(
                world_id=world_id,
                agent_id=agent_id,
                event_id=uuid.uuid4(),
                content="saw the blue gate again",
                dedupe_key="event-1",
            )
        ]
    )
    search_result = backend.search(
        MemorySearchRequest(world_id=world_id, agent_id=agent_id, query_text="blue gate")
    )
    delete_result = backend.delete_scope(
        MemoryDeleteScope(world_id=world_id, agent_id=agent_id),
    )

    assert turn_result.recorded_count == 1
    assert event_result.recorded_count == 1
    assert len(search_result.items) == 2
    assert delete_result.deleted_count == 2
    assert backend.healthcheck().status.value == "ok"


def test_mem0_oss_backend_translates_sdk_payloads() -> None:
    with Session(_engine()) as session:
        profile = MemoryBackendProfileService(session).create_profile(
            MemoryBackendProfileCreate(
                profile_key="mem0",
                name="Mem0",
                backend_kind=MemoryBackendKind.MEM0_OSS,
            )
        )
        session.commit()
    backend = Mem0OssMemoryBackend(profile, AppSettings())
    backend._client = _FakeMem0Client()
    world_id = uuid.uuid4()
    agent_id = uuid.uuid4()

    turn_result = backend.record_turn(
        MemoryTurn(
            world_id=world_id,
            agent_id=agent_id,
            conversation_id=uuid.uuid4(),
            turn_id=uuid.uuid4(),
            messages=[MemoryMessage(role="assistant", content="remembers the green tea")],
            dedupe_key="turn-1",
        )
    )
    search_result = backend.search(
        MemorySearchRequest(world_id=world_id, agent_id=agent_id, query_text="green tea")
    )

    assert turn_result.backend == "mem0_oss"
    assert turn_result.recorded_count == 1
    assert search_result.items[0].content == "remembers the green tea"
    assert search_result.items[0].metadata["tag"] == "mem0"


def test_run_memory_eval_cases_reports_hits_and_context_sizes() -> None:
    world_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    backend = FakeMemoryBackend()
    backend.record_turn(
        MemoryTurn(
            world_id=world_id,
            agent_id=agent_id,
            messages=[MemoryMessage(role="assistant", content="prefers green tea")],
            dedupe_key="turn-1",
        )
    )

    result = run_memory_eval_cases(
        backend="fake_memory",
        cases=[
            MemoryEvalCase(
                label="green-tea",
                world_id=world_id,
                agent_id=agent_id,
                query_text="green tea",
                limit=3,
            )
        ],
        search_fn=backend.search,
    )

    assert result.case_count == 1
    assert result.hit_case_count == 1
    assert result.average_context_items == 1
    assert result.cases[0].query_text == "green tea"


def test_memory_service_delete_scope_scrubs_logs_and_snapshots() -> None:
    engine = _engine()
    user_id = _seed_user(engine)
    world_id = _seed_world(engine, user_id)
    agent_id = _seed_agent(engine, world_id)

    with Session(engine) as session:
        profile = MemoryBackendProfileService(session).create_profile(
            MemoryBackendProfileCreate(
                profile_key="local-memory",
                name="Local memory",
                backend_kind=MemoryBackendKind.LOCAL_PGVECTOR,
            )
        )
        world = session.get(World, world_id)
        assert world is not None
        world.memory_backend_profile_id = profile.id
        session.add(
            AgentMemoryItem(
                world_id=world_id,
                agent_id=agent_id,
                content="Guide likes green tea",
                metadata_json={"source": "runtime"},
                embedding=[0.25] * 1536,
                visibility="private",
                is_active=True,
            )
        )
        session.add(
            AgentProfileSnapshotModel(
                world_id=world_id,
                agent_id=agent_id,
                aliases=["guide"],
                identity_notes=["identity"],
                durable_preferences=["tea"],
                long_lived_goals=["help"],
                language_style_preferences=["direct"],
            )
        )
        job = MemoryWriteJob(
            world_id=world_id,
            agent_id=agent_id,
            backend_profile_id=profile.id,
            source_kind="agent_run",
            source_id=uuid.uuid4(),
            payload_json={"content": "Guide likes green tea"},
            dedupe_key="job-1",
            status="succeeded",
            attempt_count=1,
            next_attempt_at=datetime.now(UTC),
        )
        session.add(job)
        session.flush()
        session.add(
            MemoryWriteLog(
                job_id=job.id,
                backend="local_pgvector",
                success=True,
                latency_ms=4,
                request_summary={"prompt": "secret"},
                response_summary={"stored": True},
                correlation_ids={"run_id": "secret"},
            )
        )
        session.add(
            MemoryRetrievalLog(
                world_id=world_id,
                agent_id=agent_id,
                backend_profile_id=profile.id,
                backend="local_pgvector",
                query_text="green tea",
                hit_count=1,
                selected_item_ids=["memory-1"],
                latency_ms=5,
                context_item_count=1,
            )
        )
        session.flush()

        service = MemoryService(session, AppSettings())
        result = service.delete_scope(
            MemoryDeleteScope(world_id=world_id, agent_id=agent_id),
        )
        snapshot = service.refresh_profile_snapshot(world_id, agent_id)
        write_log = session.scalars(select(MemoryWriteLog)).one()
        retrieval_log = session.scalars(select(MemoryRetrievalLog)).one()
        write_log_request_summary = dict(write_log.request_summary)
        retrieval_log_query_text = retrieval_log.query_text
        session.commit()

    assert result.deleted_count == 1
    assert write_log_request_summary == {"redacted": True}
    assert retrieval_log_query_text == "[redacted]"
    assert snapshot == MemoryProfileSnapshotRecord(
        id=snapshot.id,
        world_id=world_id,
        agent_id=agent_id,
        aliases=[],
        identity_notes=[],
        durable_preferences=[],
        long_lived_goals=[],
        language_style_preferences=[],
        refreshed_at=snapshot.refreshed_at,
        created_at=snapshot.created_at,
        updated_at=snapshot.updated_at,
    )


def test_memory_service_lists_summarizes_and_retries_write_jobs() -> None:
    engine = _engine()
    user_id = _seed_user(engine)
    world_id = _seed_world(engine, user_id)
    agent_id = _seed_agent(engine, world_id)

    with Session(engine) as session:
        profile = MemoryBackendProfileService(session).create_profile(
            MemoryBackendProfileCreate(
                profile_key="local-memory",
                name="Local memory",
                backend_kind=MemoryBackendKind.LOCAL_PGVECTOR,
            )
        )
        failed_job = MemoryWriteJob(
            world_id=world_id,
            agent_id=agent_id,
            backend_profile_id=profile.id,
            source_kind="agent_run",
            source_id=uuid.uuid4(),
            payload_json={"content": "failed memory"},
            dedupe_key="failed-job",
            status="failed",
            attempt_count=2,
            next_attempt_at=datetime.now(UTC),
            last_error="backend timeout",
        )
        succeeded_job = MemoryWriteJob(
            world_id=world_id,
            agent_id=agent_id,
            backend_profile_id=profile.id,
            source_kind="conversation_turn",
            source_id=uuid.uuid4(),
            payload_json={"content": "stored memory"},
            dedupe_key="succeeded-job",
            status="succeeded",
            attempt_count=1,
            next_attempt_at=datetime.now(UTC),
            processed_at=datetime.now(UTC),
        )
        session.add_all([failed_job, succeeded_job])
        session.flush()
        failed_job_id = failed_job.id
        session.add(
            MemoryWriteLog(
                job_id=failed_job.id,
                backend="local_pgvector",
                success=False,
                latency_ms=None,
                request_summary={"source_kind": "agent_run"},
                response_summary={"error": "backend timeout"},
                correlation_ids={"world_id": str(world_id), "agent_id": str(agent_id)},
            )
        )

        service = MemoryService(session, AppSettings())
        failed_jobs = service.list_write_jobs(
            profile_id=profile.id,
            status=MemoryWriteJobStatus.FAILED,
        )
        summary_before_retry = service.write_job_status_summary()
        retried = service.retry_write_job(failed_job_id)
        summary_after_retry = service.write_job_status_summary()
        session.commit()

    assert [job.id for job in failed_jobs] == [failed_job_id]
    assert failed_jobs[0].backend_profile_key == "local-memory"
    assert failed_jobs[0].is_retryable is True
    assert failed_jobs[0].terminal_reason is None
    assert failed_jobs[0].last_log_success is False
    assert failed_jobs[0].age_seconds >= 0
    assert summary_before_retry.failed_count == 1
    assert summary_before_retry.succeeded_count == 1
    assert summary_before_retry.due_count == 1
    assert summary_before_retry.retryable_failed_count == 1
    assert summary_before_retry.terminal_failed_count == 0
    assert summary_before_retry.stalled_processing_count == 0
    assert retried.status == MemoryWriteJobStatus.PENDING
    assert retried.last_error is None
    assert summary_after_retry.pending_count == 1
    assert summary_after_retry.failed_count == 0
    assert summary_after_retry.succeeded_count == 1


def test_memory_service_marks_terminal_and_stalled_write_jobs() -> None:
    engine = _engine()
    user_id = _seed_user(engine)
    world_id = _seed_world(engine, user_id)
    agent_id = _seed_agent(engine, world_id)
    now = datetime.now(UTC)

    with Session(engine) as session:
        enabled_profile = MemoryBackendProfileService(session).create_profile(
            MemoryBackendProfileCreate(
                profile_key="enabled-memory",
                name="Enabled memory",
                backend_kind=MemoryBackendKind.LOCAL_PGVECTOR,
            )
        )
        disabled_profile = MemoryBackendProfileService(session).create_profile(
            MemoryBackendProfileCreate(
                profile_key="disabled-memory",
                name="Disabled memory",
                backend_kind=MemoryBackendKind.LOCAL_PGVECTOR,
                is_enabled=False,
            )
        )
        max_attempt_job = MemoryWriteJob(
            world_id=world_id,
            agent_id=agent_id,
            backend_profile_id=enabled_profile.id,
            source_kind="agent_run",
            source_id=uuid.uuid4(),
            payload_json={"content": "maxed out memory"},
            dedupe_key="maxed-job",
            status="failed",
            attempt_count=3,
            next_attempt_at=now,
            last_error="repeated timeout",
        )
        disabled_profile_job = MemoryWriteJob(
            world_id=world_id,
            agent_id=agent_id,
            backend_profile_id=disabled_profile.id,
            source_kind="conversation_turn",
            source_id=uuid.uuid4(),
            payload_json={"content": "disabled backend memory"},
            dedupe_key="disabled-job",
            status="failed",
            attempt_count=1,
            next_attempt_at=now,
            last_error="backend disabled",
        )
        stalled_job = MemoryWriteJob(
            world_id=world_id,
            agent_id=agent_id,
            backend_profile_id=enabled_profile.id,
            source_kind="world_event",
            source_id=uuid.uuid4(),
            payload_json={"content": "stalled memory"},
            dedupe_key="stalled-job",
            status="processing",
            attempt_count=1,
            next_attempt_at=now,
            created_at=now - timedelta(minutes=10),
            updated_at=now - timedelta(minutes=10),
        )
        session.add_all([max_attempt_job, disabled_profile_job, stalled_job])
        session.flush()
        max_attempt_job_id = max_attempt_job.id
        disabled_profile_job_id = disabled_profile_job.id

        settings = AppSettings(
            memory_job_max_attempts=3,
            memory_job_stalled_after_seconds=60,
        )
        service = MemoryService(session, settings)
        summary = service.write_job_status_summary()
        failed_jobs = {
            job.dedupe_key: job
            for job in service.list_write_jobs(status=MemoryWriteJobStatus.FAILED)
        }

        with pytest.raises(MemoryValidationError, match="max attempts reached"):
            service.retry_write_job(max_attempt_job_id)
        with pytest.raises(MemoryValidationError, match="backend profile disabled"):
            service.retry_write_job(disabled_profile_job_id)
        session.commit()

    assert summary.failed_count == 2
    assert summary.retryable_failed_count == 0
    assert summary.terminal_failed_count == 2
    assert summary.stalled_processing_count == 1
    assert failed_jobs["maxed-job"].is_retryable is False
    assert failed_jobs["maxed-job"].terminal_reason == "max attempts reached"
    assert failed_jobs["disabled-job"].is_retryable is False
    assert failed_jobs["disabled-job"].terminal_reason == "backend profile disabled"


def test_memory_backfill_dry_run_reports_candidates_and_skips_without_enqueuing() -> None:
    engine = _engine()
    user_id = _seed_user(engine)
    enabled_world_id = _seed_world(engine, user_id)
    disabled_world_id = _seed_world(engine, user_id)
    no_profile_world_id = _seed_world(engine, user_id)
    enabled_agent_id = _seed_agent(engine, enabled_world_id)
    disabled_agent_id = _seed_agent(engine, disabled_world_id)
    no_profile_agent_id = _seed_agent(engine, no_profile_world_id)
    now = datetime.now(UTC)

    with Session(engine) as session:
        enabled_profile = MemoryBackendProfileService(session).create_profile(
            MemoryBackendProfileCreate(
                profile_key="enabled-backfill",
                name="Enabled backfill",
                backend_kind=MemoryBackendKind.LOCAL_PGVECTOR,
            )
        )
        disabled_profile = MemoryBackendProfileService(session).create_profile(
            MemoryBackendProfileCreate(
                profile_key="disabled-backfill",
                name="Disabled backfill",
                backend_kind=MemoryBackendKind.LOCAL_PGVECTOR,
                is_enabled=False,
            )
        )
        enabled_world = session.get(World, enabled_world_id)
        disabled_world = session.get(World, disabled_world_id)
        no_profile_world = session.get(World, no_profile_world_id)
        assert enabled_world is not None
        assert disabled_world is not None
        assert no_profile_world is not None
        enabled_world.memory_backend_profile_id = enabled_profile.id
        disabled_world.memory_backend_profile_id = disabled_profile.id
        no_profile_world.memory_plugin_identifier = BUILTIN_MEM0_OSS_MEMORY

        enabled_run = AgentRuntimeRun(
            world_id=enabled_world_id,
            agent_id=enabled_agent_id,
            status="succeeded",
            trigger_source="runtime_tick",
            prompt_text="Remember this",
            response_text="Backfill agent memory",
            diagnostics={},
            started_at=now,
            finished_at=now,
        )
        disabled_run = AgentRuntimeRun(
            world_id=disabled_world_id,
            agent_id=disabled_agent_id,
            status="succeeded",
            trigger_source="runtime_tick",
            prompt_text="Remember this",
            response_text="Disabled profile memory",
            diagnostics={},
            started_at=now,
            finished_at=now,
        )
        no_profile_run = AgentRuntimeRun(
            world_id=no_profile_world_id,
            agent_id=no_profile_agent_id,
            status="succeeded",
            trigger_source="runtime_tick",
            prompt_text="Remember this",
            response_text="No profile memory",
            diagnostics={},
            started_at=now,
            finished_at=now,
        )
        conversation = ConversationSession(
            world_id=enabled_world_id,
            session_key="backfill-conversation",
            title="Backfill conversation",
            scope_type="world",
            mode="auto_dialogue",
            status="running",
            objective="test",
            opening_prompt="test",
            max_turns=3,
            next_turn_index=1,
            policy_config={},
            writer_config={},
            memory_config={},
        )
        session.add_all([enabled_run, disabled_run, no_profile_run, conversation])
        session.flush()
        turn = ConversationTurn(
            session_id=conversation.id,
            turn_index=0,
            speaker_kind="agent",
            speaker_agent_id=enabled_agent_id,
            input_text="input",
            output_text="Backfill conversation memory",
            status="succeeded",
        )
        event = WorldEventModel(
            world_id=enabled_world_id,
            sequence=1,
            event_name="agent.run_completed",
            payload={"content": "Backfill event memory"},
            wall_time=now,
            actor_ref="agent:guide",
        )
        session.add_all([turn, event])
        session.flush()
        existing_job = MemoryWriteJob(
            world_id=enabled_world_id,
            agent_id=enabled_agent_id,
            backend_profile_id=enabled_profile.id,
            source_kind="world_event",
            source_id=event.id,
            payload_json={"content": "Backfill event memory"},
            dedupe_key=f"world-event:{event.id}",
            status="succeeded",
            attempt_count=1,
            next_attempt_at=now,
        )
        session.add(existing_job)
        session.flush()

        result = MemoryService(session, AppSettings()).dry_run_backfill()
        job_count = session.query(MemoryWriteJob).count()
        session.commit()

    source_summaries = {summary.source_kind.value: summary for summary in result.source_summaries}
    assert result.candidate_count == 2
    assert result.skipped_existing_count == 1
    assert result.skipped_disabled_profile_count == 1
    assert result.skipped_no_profile_count == 1
    assert source_summaries["agent_run"].candidate_count == 1
    assert source_summaries["agent_run"].skipped_disabled_profile_count == 1
    assert source_summaries["agent_run"].skipped_no_profile_count == 1
    assert source_summaries["conversation_turn"].candidate_count == 1
    assert source_summaries["world_event"].skipped_existing_count == 1
    assert job_count == 1


def test_memory_backfill_execution_enqueues_candidates_idempotently() -> None:
    engine = _engine()
    user_id = _seed_user(engine)
    world_id = _seed_world(engine, user_id)
    agent_id = _seed_agent(engine, world_id)
    now = datetime.now(UTC)

    with Session(engine) as session:
        profile = MemoryBackendProfileService(session).create_profile(
            MemoryBackendProfileCreate(
                profile_key="execute-backfill",
                name="Execute backfill",
                backend_kind=MemoryBackendKind.LOCAL_PGVECTOR,
            )
        )
        world = session.get(World, world_id)
        assert world is not None
        world.memory_backend_profile_id = profile.id
        run = AgentRuntimeRun(
            world_id=world_id,
            agent_id=agent_id,
            status="succeeded",
            trigger_source="runtime_tick",
            prompt_text="Remember this",
            response_text="Backfill agent memory",
            diagnostics={},
            started_at=now,
            finished_at=now,
        )
        session.add(run)
        session.flush()
        expected_dedupe_key = f"agent-run:{run.id}"

        first = MemoryService(session, AppSettings()).execute_backfill(limit=10)
        second = MemoryService(session, AppSettings()).execute_backfill(limit=10)
        job_dedupe_keys = [job.dedupe_key for job in session.query(MemoryWriteJob).all()]
        readiness = MemoryService(session, AppSettings()).queue_readiness_report()
        session.commit()

    assert first.enqueued_count == 1
    assert first.dry_run_before.candidate_count == 1
    assert second.enqueued_count == 0
    assert second.dry_run_before.skipped_existing_count == 1
    assert job_dedupe_keys == [expected_dedupe_key]
    assert readiness.external_queue_ready is True
    assert readiness.issues == []


def _engine() -> Engine:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in (
        cast(Table, User.__table__),
        cast(Table, World.__table__),
        cast(Table, Worldline.__table__),
        cast(Table, Agent.__table__),
        cast(Table, AgentRuntimeRun.__table__),
        cast(Table, ConversationSession.__table__),
        cast(Table, ConversationTurn.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, MemoryBackendProfile.__table__),
        cast(Table, AgentMemoryItem.__table__),
        cast(Table, MemoryWriteJob.__table__),
        cast(Table, MemoryWriteLog.__table__),
        cast(Table, MemoryRetrievalLog.__table__),
        cast(Table, AgentProfileSnapshotModel.__table__),
    ):
        table.create(engine)
    return engine


def _seed_user(engine: Engine) -> uuid.UUID:
    user_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(User(id=user_id, email=f"{user_id}@example.test", display_name="User"))
        session.commit()
    return user_id


def _seed_world(engine: Engine, user_id: uuid.UUID) -> uuid.UUID:
    world_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            World(
                id=world_id,
                owner_user_id=user_id,
                slug=f"world-{world_id.hex[:8]}",
                name="World",
                rules_config={},
            ),
        )
        session.commit()
    return world_id


def _seed_agent(engine: Engine, world_id: uuid.UUID) -> uuid.UUID:
    agent_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            Agent(
                id=agent_id,
                world_id=world_id,
                agent_key=f"agent-{agent_id.hex[:8]}",
                display_name="Agent",
                kind="role_agent",
                config={},
            ),
        )
        session.commit()
    return agent_id


class _FakeMem0Client:
    def __init__(self) -> None:
        self._items: list[dict[str, object]] = []

    def add(
        self,
        *,
        messages: list[dict[str, str]],
        metadata: dict[str, object],
        **_: object,
    ) -> dict[str, object]:
        item_id = str(uuid.uuid4())
        content = messages[0]["content"]
        self._items.insert(
            0,
            {
                "id": item_id,
                "memory": content,
                "metadata": {**metadata, "tag": "mem0"},
                "created_at": datetime.now(UTC).isoformat(),
            },
        )
        return {"id": item_id}

    def search(self, query: str, **_: object) -> list[dict[str, object]]:
        return [
            {**item, "score": 0.9}
            for item in self._items
            if query.lower() in str(item["memory"]).lower()
        ]

    def get_all(self, **_: object) -> list[dict[str, object]]:
        return list(self._items)

    def delete_all(self, **_: object) -> dict[str, int]:
        deleted_count = len(self._items)
        self._items = []
        return {"deleted_count": deleted_count}
