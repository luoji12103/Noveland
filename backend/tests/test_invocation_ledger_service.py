from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import cast

import pytest
from noveland.adapters.models import ProviderProfile
from noveland.agents.models import Agent, AgentRuntimeRun
from noveland.auth.models import User
from noveland.conversations.models import ConversationSession, ConversationTurn
from noveland.events import WorldEventAppend, WorldEventStore
from noveland.events.models import WorldEventModel
from noveland.invocations.contracts import (
    AgentRuntimeRunInvocationLinkCreate,
    InvocationActorKind,
    InvocationKind,
    InvocationProviderKind,
    InvocationRecordCreate,
    InvocationRedactionStatus,
    InvocationRedactRequest,
    InvocationRole,
    InvocationSearchFilters,
    InvocationStatus,
    InvocationStatusUpdate,
    InvocationTagCreate,
    InvocationTagFilter,
    PromptSnapshotCreate,
    PromptSnapshotUpdate,
    PromptTemplateCreate,
    PromptTemplateScopeKind,
    PromptTemplateStatus,
    RedactionMode,
)
from noveland.invocations.models import (
    AgentRuntimeRunModelInvocation,
    ModelInvocation,
    ModelInvocationTag,
    PromptSnapshot,
    PromptTemplate,
)
from noveland.invocations.service import (
    InvocationLedgerService,
    InvocationValidationError,
    PromptSnapshotService,
)
from noveland.media.models import MediaAsset, MediaJob
from noveland.memory.models import MemoryBackendProfile, MemoryWriteJob
from noveland.worlds.models import World, Worldline
from noveland.worlds.worldlines import ensure_primary_worldline
from sqlalchemy import Table, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_invocation_ledger_records_searches_tags_and_redacts() -> None:
    engine = _engine()
    graph = _seed_graph(engine)

    with Session(engine) as session:
        service = InvocationLedgerService(session)
        created = service.record(
            InvocationRecordCreate(
                world_id=graph.world_id,
                worldline_id=graph.primary_id,
                invocation_kind=InvocationKind.AGENT_RUNTIME,
                actor_kind=InvocationActorKind.RUNTIME,
                actor_ref="system:runtime",
                agent_id=graph.agent_id,
                conversation_id=graph.conversation_id,
                turn_id=graph.turn_id,
                world_event_id=graph.event_id,
                media_job_id=graph.media_job_id,
                media_asset_id=graph.media_asset_id,
                memory_write_job_id=graph.memory_job_id,
                provider_kind=InvocationProviderKind.OPENAI_COMPATIBLE,
                provider_profile_id=graph.provider_profile_id,
                model_name="test-model",
                input_text="visible input summary",
                status=InvocationStatus.RUNNING,
                prompt_snapshot=PromptSnapshotCreate(
                    raw_prompt_text="raw prompt with searchable phrase",
                    raw_request_json={"prompt": "raw prompt"},
                    prompt_context_snapshot_json={"worldline_id": str(graph.primary_id)},
                ),
            )
        )
        service.update_status(
            graph.world_id,
            created.id,
            InvocationStatusUpdate(
                status=InvocationStatus.SUCCEEDED,
                output_text="model output",
                response_metadata_json={"ok": True},
                latency_ms=12,
            ),
        )
        PromptSnapshotService(session).update_snapshot_for_invocation(
            created.id,
            PromptSnapshotUpdate(raw_response_json={"ok": True}, raw_output_text="raw output"),
        )
        tag = service.attach_tag(
            InvocationTagCreate(
                world_id=graph.world_id,
                worldline_id=graph.primary_id,
                invocation_id=created.id,
                tag_type="Provider",
                tag_key="Model",
                tag_value="test:model",
            )
        )
        link = service.link_runtime_run(
            AgentRuntimeRunInvocationLinkCreate(
                world_id=graph.world_id,
                worldline_id=graph.primary_id,
                agent_runtime_run_id=graph.run_id,
                model_invocation_id=created.id,
                invocation_role=InvocationRole.PRIMARY,
                sequence_index=0,
            )
        )
        session.commit()

    with Session(engine) as session:
        service = InvocationLedgerService(session)
        result = service.list(
            graph.world_id,
            InvocationSearchFilters(
                worldline_id=graph.primary_id,
                contains_text="searchable",
                tags=(InvocationTagFilter.parse("provider:model:test:model"),),
            ),
        )
        snapshot = PromptSnapshotService(session).get_snapshot(graph.world_id, created.id)
        redacted = service.redact(
            graph.world_id,
            created.id,
            InvocationRedactRequest(
                redaction_status=InvocationRedactionStatus.REDACTED,
                reason="test",
                mode=RedactionMode.CLEAR_RAW_PAYLOADS,
            ),
        )
        redacted_snapshot = PromptSnapshotService(session).get_snapshot(graph.world_id, created.id)
        session.commit()

    assert [record.id for record in result.invocations] == [created.id]
    assert tag.tag_type == "provider"
    assert tag.tag_value == "test:model"
    assert link.sequence_index == 0
    assert snapshot is not None
    assert snapshot.raw_prompt_text == "raw prompt with searchable phrase"
    assert snapshot.raw_output_text == "raw output"
    assert redacted.status == InvocationStatus.REDACTED
    assert redacted.input_text is None
    assert redacted_snapshot is None


def test_invocation_ledger_validates_worldline_and_parent_scope() -> None:
    engine = _engine()
    graph = _seed_graph(engine)

    with Session(engine) as session:
        service = InvocationLedgerService(session)
        parent = service.record(
            InvocationRecordCreate(
                world_id=graph.world_id,
                worldline_id=graph.primary_id,
                invocation_kind=InvocationKind.AGENT_RUNTIME,
                actor_kind=InvocationActorKind.RUNTIME,
                provider_kind=InvocationProviderKind.OPENAI_COMPATIBLE,
                provider_profile_id=graph.provider_profile_id,
                status=InvocationStatus.SUCCEEDED,
            )
        )
        with pytest.raises(InvocationValidationError, match="parent invocation"):
            service.record(
                InvocationRecordCreate(
                    world_id=graph.world_id,
                    worldline_id=graph.fork_id,
                    parent_invocation_id=parent.id,
                    invocation_kind=InvocationKind.AGENT_RUNTIME,
                    actor_kind=InvocationActorKind.RUNTIME,
                    provider_kind=InvocationProviderKind.OPENAI_COMPATIBLE,
                    provider_profile_id=graph.provider_profile_id,
                )
            )
        with pytest.raises(InvocationValidationError, match="conversation"):
            service.record(
                InvocationRecordCreate(
                    world_id=graph.world_id,
                    worldline_id=graph.fork_id,
                    conversation_id=graph.conversation_id,
                    invocation_kind=InvocationKind.AGENT_RUNTIME,
                    actor_kind=InvocationActorKind.RUNTIME,
                    provider_kind=InvocationProviderKind.OPENAI_COMPATIBLE,
                    provider_profile_id=graph.provider_profile_id,
                )
            )
        with pytest.raises(InvocationValidationError, match="media asset"):
            service.record(
                InvocationRecordCreate(
                    world_id=graph.world_id,
                    worldline_id=graph.fork_id,
                    media_asset_id=graph.media_asset_id,
                    invocation_kind=InvocationKind.AGENT_RUNTIME,
                    actor_kind=InvocationActorKind.RUNTIME,
                    provider_kind=InvocationProviderKind.OPENAI_COMPATIBLE,
                    provider_profile_id=graph.provider_profile_id,
                )
            )


def test_prompt_templates_resolve_world_override_before_global() -> None:
    engine = _engine()
    graph = _seed_graph(engine)

    with Session(engine) as session:
        service = PromptSnapshotService(session)
        global_template = service.create_template(
            PromptTemplateCreate(
                scope_kind=PromptTemplateScopeKind.GLOBAL,
                template_key="agent.run",
                version=1,
                invocation_kind=InvocationKind.AGENT_RUNTIME,
                title="Global",
                content="global content",
                status=PromptTemplateStatus.ACTIVE,
            )
        )
        world_template = service.create_template(
            PromptTemplateCreate(
                scope_kind=PromptTemplateScopeKind.WORLD,
                world_id=graph.world_id,
                template_key="agent.run",
                version=2,
                invocation_kind=InvocationKind.AGENT_RUNTIME,
                title="World",
                content="world content",
                status=PromptTemplateStatus.ACTIVE,
            )
        )
        resolved = service.resolve_template(graph.world_id, "agent.run")
        global_read = service.get_template(graph.world_id, global_template.id)
        session.commit()

    assert resolved.id == world_template.id
    assert global_read is not None
    assert global_read.id == global_template.id


class _Graph:
    def __init__(
        self,
        *,
        world_id: uuid.UUID,
        primary_id: uuid.UUID,
        fork_id: uuid.UUID,
        agent_id: uuid.UUID,
        conversation_id: uuid.UUID,
        turn_id: uuid.UUID,
        event_id: uuid.UUID,
        provider_profile_id: uuid.UUID,
        media_job_id: uuid.UUID,
        media_asset_id: uuid.UUID,
        memory_job_id: uuid.UUID,
        run_id: uuid.UUID,
    ) -> None:
        self.world_id = world_id
        self.primary_id = primary_id
        self.fork_id = fork_id
        self.agent_id = agent_id
        self.conversation_id = conversation_id
        self.turn_id = turn_id
        self.event_id = event_id
        self.provider_profile_id = provider_profile_id
        self.media_job_id = media_job_id
        self.media_asset_id = media_asset_id
        self.memory_job_id = memory_job_id
        self.run_id = run_id


def _engine() -> Engine:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    _create_tables(engine)
    return engine


def _create_tables(engine: Engine) -> None:
    for table in (
        cast(Table, User.__table__),
        cast(Table, MemoryBackendProfile.__table__),
        cast(Table, World.__table__),
        cast(Table, Worldline.__table__),
        cast(Table, ProviderProfile.__table__),
        cast(Table, Agent.__table__),
        cast(Table, ConversationSession.__table__),
        cast(Table, ConversationTurn.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, MediaJob.__table__),
        cast(Table, MediaAsset.__table__),
        cast(Table, MemoryWriteJob.__table__),
        cast(Table, AgentRuntimeRun.__table__),
        cast(Table, ModelInvocation.__table__),
        cast(Table, PromptTemplate.__table__),
        cast(Table, PromptSnapshot.__table__),
        cast(Table, AgentRuntimeRunModelInvocation.__table__),
        cast(Table, ModelInvocationTag.__table__),
    ):
        table.create(engine)


def _seed_graph(engine: Engine) -> _Graph:
    user_id = uuid.uuid4()
    world_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    turn_id = uuid.uuid4()
    provider_profile_id = uuid.uuid4()
    media_job_id = uuid.uuid4()
    media_asset_id = uuid.uuid4()
    memory_profile_id = uuid.uuid4()
    memory_job_id = uuid.uuid4()
    run_id = uuid.uuid4()
    now = datetime.now(UTC)
    with Session(engine) as session:
        session.add(User(id=user_id, email=f"{user_id}@example.test", display_name="Test"))
        session.add(
            MemoryBackendProfile(
                id=memory_profile_id,
                profile_key=f"memory-{memory_profile_id.hex[:8]}",
                name="Memory",
                backend_kind="local_pgvector",
                vector_store_config={},
                llm_config={},
                embedder_config={},
                reranker_config={},
                secret_refs={},
            )
        )
        session.add(
            World(
                id=world_id,
                owner_user_id=user_id,
                slug=f"world-{world_id.hex[:8]}",
                name="World",
                memory_backend_profile_id=memory_profile_id,
            )
        )
        session.flush()
        primary = ensure_primary_worldline(session, world_id)
        fork = Worldline(
            world_id=world_id,
            worldline_key=f"fork-{uuid.uuid4().hex[:8]}",
            name="Fork",
            parent_worldline_id=primary.id,
            status="active",
            created_by_actor_ref="test",
            metadata_json={},
        )
        session.add(fork)
        session.add(
            ProviderProfile(
                id=provider_profile_id,
                profile_key=f"profile-{provider_profile_id.hex[:8]}",
                name="Provider",
                provider_type="openai_compatible",
                base_url="https://api.example.test/v1",
                model_name="test-model",
                capabilities={},
                api_key_ref="provider-key",
            )
        )
        session.add(
            Agent(
                id=agent_id,
                world_id=world_id,
                agent_key="agent",
                display_name="Agent",
                kind="role_agent",
            )
        )
        session.add(
            ConversationSession(
                id=conversation_id,
                world_id=world_id,
                worldline_id=primary.id,
                session_key="session",
                title="Session",
                scope_type="world",
                mode="manual_chain",
                status="draft",
                objective="",
                opening_prompt="",
                max_turns=3,
                next_turn_index=1,
                policy_config={},
                writer_config={},
                memory_config={},
            )
        )
        session.add(
            ConversationTurn(
                id=turn_id,
                session_id=conversation_id,
                turn_index=0,
                speaker_kind="operator",
                input_text="hi",
                status="succeeded",
            )
        )
        event = WorldEventStore(session).append_event(
            WorldEventAppend(
                world_id=world_id,
                worldline_id=primary.id,
                event_name="invocation.seed_event",
                payload={"kind": "seed"},
                wall_time=now,
                actor_ref="test",
            )
        )
        session.add(
            MediaJob(
                id=media_job_id,
                world_id=world_id,
                worldline_id=primary.id,
                job_kind="image_generation",
                status="queued",
                request_json={},
                result_json={},
                created_by_actor_ref="test",
            )
        )
        session.add(
            MediaAsset(
                id=media_asset_id,
                world_id=world_id,
                worldline_id=primary.id,
                asset_kind="image",
                asset_role="reference_image",
                source_kind="manual_upload",
                status="registered",
                visibility="private",
                created_by_actor_ref="test",
                metadata_json={},
            )
        )
        session.add(
            MemoryWriteJob(
                id=memory_job_id,
                world_id=world_id,
                worldline_id=primary.id,
                agent_id=agent_id,
                backend_profile_id=memory_profile_id,
                source_kind="agent_run",
                source_id=run_id,
                payload_json={},
                dedupe_key=f"memory-{memory_job_id}",
                status="pending",
                next_attempt_at=now,
            )
        )
        session.add(
            AgentRuntimeRun(
                id=run_id,
                world_id=world_id,
                worldline_id=primary.id,
                agent_id=agent_id,
                provider_profile_id=provider_profile_id,
                status="running",
                trigger_source="manual",
                prompt_text="summary",
                diagnostics={},
                started_at=now,
            )
        )
        session.commit()
        return _Graph(
            world_id=world_id,
            primary_id=primary.id,
            fork_id=fork.id,
            agent_id=agent_id,
            conversation_id=conversation_id,
            turn_id=turn_id,
            event_id=event.id,
            provider_profile_id=provider_profile_id,
            media_job_id=media_job_id,
            media_asset_id=media_asset_id,
            memory_job_id=memory_job_id,
            run_id=run_id,
        )
