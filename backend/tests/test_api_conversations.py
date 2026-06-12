from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
from fastapi.testclient import TestClient
from noveland.adapters import ProviderCompletion, ProviderProfileService
from noveland.adapters.models import ProviderProfile
from noveland.agents.models import (
    Agent,
    AgentObservation,
    AgentPersona,
    AgentRelationshipEdge,
    AgentRuntimeRun,
)
from noveland.auth import AuthRole
from noveland.auth.contracts import AuthSessionStatus
from noveland.auth.models import AuthSession, PlatformRoleAssignment, User
from noveland.auth.services import hash_session_token
from noveland.calendar.models import AgentCalendarEntry, WorldScheduleRule
from noveland.conversations.models import (
    ConversationParticipant,
    ConversationSession,
    ConversationTurn,
)
from noveland.events.models import WorldEventModel
from noveland.invocations.models import (
    AgentRuntimeRunModelInvocation,
    ModelInvocation,
    ModelInvocationTag,
    PromptSnapshot,
    PromptTemplate,
)
from noveland.memory.models import (
    AgentMemoryItem,
    AgentProfileSnapshotModel,
    MemoryBackendProfile,
    MemoryRetrievalLog,
    MemoryWriteJob,
    MemoryWriteLog,
)
from noveland.narrative.models import NarrativeArtifact, NarrativePublication
from noveland.observability.models import RuntimeDiagnosticEvent
from noveland.services.api.app import create_app
from noveland.services.api.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from noveland.services.api.dependencies import get_db_session
from noveland.worlds.models import (
    CharacterEmotionalState,
    CharacterKnowledgeFact,
    NarrativeContinuityReview,
    PlotThread,
    RouteAffinity,
    Scene,
    SecretRecord,
    StoryHook,
    World,
    WorldBible,
    Worldline,
    WorldMembership,
)
from noveland.worlds.worldlines import ensure_primary_worldline
from sqlalchemy import Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_conversation_api_enforces_access_and_manual_advance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    _stranger_id, stranger_token = _seed_user(engine, "stranger@example.test")
    world_id = _seed_world(engine, owner_id, "dialogue-world")
    scene_id = _seed_scene(engine, world_id, "square")
    first_agent_id = _seed_agent(engine, world_id, "guide", scene_id)
    second_agent_id = _seed_agent(engine, world_id, "scribe", scene_id)
    fork_id = _seed_fork_worldline(engine, world_id)
    provider_profile_id = _seed_provider_profile(engine)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)

    def fake_invoke_profile(
        self: ProviderProfileService,
        profile: object,
        prompt: str,
    ) -> ProviderCompletion:
        del self, profile, prompt
        return ProviderCompletion(
            text="Agent response with raw_output media://private/turn",
            raw_response={"ok": True},
        )

    monkeypatch.setattr(ProviderProfileService, "invoke_profile", fake_invoke_profile)

    _authenticate(client, owner_token)
    create_response = client.post(
        f"/worlds/{world_id}/conversations",
        json={
            "session_key": "manual-chain",
            "title": "Manual chain",
            "scope_type": "scene",
            "mode": "manual_chain",
            "worldline_id": str(fork_id),
            "scene_id": str(scene_id),
            "objective": "operator-only objective with raw_prompt marker",
            "opening_prompt": "operator-only opening prompt",
            "max_turns": 3,
            "policy": {
                **_policy_json(),
                "max_turn_budget": 3,
            },
            "writer_config": {
                **_writer_config_json(),
                "provider_profile_id": str(provider_profile_id),
                "style_guide": "operator-only style guide",
                "source_constraints": "operator-only source constraints",
                "include_prompt_preview": True,
            },
            "memory_config": {
                "write_turn_memory": True,
                "retrieve_memory": True,
                "max_context_items": 7,
                "query_window": 9,
                "include_recent_turns": True,
                "include_agent_observations": True,
                "memory_query_strategy": "transcript",
            },
            "group_context": {"raw_output": "operator-only group context"},
        },
    )
    conversation_id = create_response.json()["id"]
    replace_participants = client.put(
        f"/worlds/{world_id}/conversations/{conversation_id}/participants",
        json=[
            {"agent_id": str(first_agent_id), "turn_order": 0, "is_enabled": True},
            {"agent_id": str(second_agent_id), "turn_order": 1, "is_enabled": True},
        ],
    )
    seed_response = client.post(
        f"/worlds/{world_id}/conversations/{conversation_id}/seed",
        json={"input_text": "Operator seed with raw_prompt /root/private/seed.txt"},
    )
    advance_response = client.post(f"/worlds/{world_id}/conversations/{conversation_id}/advance")
    speaker_preview = client.get(
        f"/worlds/{world_id}/conversations/{conversation_id}/speaker-preview",
    )

    _authenticate(client, member_token)
    member_list = client.get(f"/worlds/{world_id}/conversations")
    member_detail = client.get(f"/worlds/{world_id}/conversations/{conversation_id}")
    member_turns = client.get(f"/worlds/{world_id}/conversations/{conversation_id}/turns")
    member_speaker_preview = client.get(
        f"/worlds/{world_id}/conversations/{conversation_id}/speaker-preview",
    )
    member_diagnostics = client.get(
        f"/worlds/{world_id}/conversations/{conversation_id}/diagnostics",
    )
    memory_summary = client.get(
        f"/worlds/{world_id}/conversations/{conversation_id}/memory/summary",
    )
    member_advance = client.post(f"/worlds/{world_id}/conversations/{conversation_id}/advance")

    _authenticate(client, stranger_token)
    stranger_list = client.get(f"/worlds/{world_id}/conversations")
    with Session(engine) as session:
        event_worldline_ids = {
            event.worldline_id
            for event in session.scalars(
                select(WorldEventModel).order_by(WorldEventModel.sequence.asc()),
            )
        }

    assert create_response.status_code == 201
    assert create_response.json()["worldline_id"] == str(fork_id)
    assert create_response.json()["objective"] == "operator-only objective with raw_prompt marker"
    assert create_response.json()["opening_prompt"] == "operator-only opening prompt"
    assert create_response.json()["policy"]["max_turn_budget"] == 3
    assert create_response.json()["writer_config"]["provider_profile_id"] == str(
        provider_profile_id,
    )
    assert create_response.json()["writer_config"]["writer_plugin_config"]["group_context"] == {
        "raw_output": "operator-only group context",
    }
    assert create_response.json()["memory_config"]["memory_query_strategy"] == "transcript"
    assert create_response.json()["group_context"]["raw_output"] == (
        "operator-only group context"
    )
    assert replace_participants.status_code == 200
    assert seed_response.status_code == 200
    assert seed_response.json()["input_text"] == (
        "Operator seed with raw_prompt /root/private/seed.txt"
    )
    assert advance_response.status_code == 200
    assert advance_response.json()["turn"]["speaker_agent_id"] == str(first_agent_id)
    assert advance_response.json()["turn"]["output_text"] == (
        "Agent response with raw_output media://private/turn"
    )
    assert advance_response.json()["turn"]["run_id"] is not None
    assert advance_response.json()["turn"]["error_text"] is None
    assert speaker_preview.status_code == 200
    assert speaker_preview.json()["policy_mode"] == "round_robin"
    assert speaker_preview.json()["selected_agent_id"] == str(second_agent_id)
    assert member_list.status_code == 200
    assert member_detail.status_code == 200
    member_session = member_list.json()[0]
    assert member_session["id"] == str(conversation_id)
    assert member_session["title"] == "Manual chain"
    assert member_session["objective"] == ""
    assert member_session["opening_prompt"] == ""
    assert member_session["policy"]["manual_next_agent_id"] is None
    assert member_session["writer_config"]["provider_profile_id"] is None
    assert member_session["writer_config"]["writer_plugin_identifier"] == ""
    assert member_session["writer_config"]["writer_plugin_config"] == {}
    assert member_session["writer_config"]["style_guide"] == ""
    assert member_session["writer_config"]["source_constraints"] == ""
    assert member_session["writer_config"]["include_prompt_preview"] is False
    assert member_session["memory_config"]["retrieve_memory"] is False
    assert member_session["memory_config"]["memory_query_strategy"] == ""
    assert member_session["group_context"] == {}
    assert member_detail.json()["objective"] == ""
    assert member_detail.json()["writer_config"]["writer_plugin_config"] == {}
    assert member_turns.status_code == 200
    assert member_speaker_preview.status_code == 403
    assert member_diagnostics.status_code == 403
    assert memory_summary.status_code == 403
    assert [turn["speaker_kind"] for turn in member_turns.json()] == ["operator", "agent"]
    assert member_turns.json()[0]["input_text"] == ""
    assert member_turns.json()[1]["output_text"] == ""
    assert member_turns.json()[1]["run_id"] is None
    assert member_turns.json()[1]["error_text"] is None
    assert member_advance.status_code == 403
    assert stranger_list.status_code == 404
    assert event_worldline_ids == {fork_id}


def test_conversation_memory_summary_reports_config_and_runtime_diagnostics() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id = _seed_world(engine, owner_id, "memory-world")
    agent_id = _seed_agent(engine, world_id, "speaker")
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _authenticate(client, owner_token)

    create_response = client.post(
        f"/worlds/{world_id}/conversations",
        json={
            "session_key": "memory-session",
            "title": "Memory session",
            "scope_type": "world",
            "mode": "manual_chain",
            "policy": _policy_json(),
            "writer_config": _writer_config_json(),
            "memory_config": {
                "write_turn_memory": False,
                "retrieve_memory": True,
                "max_context_items": 3,
                "query_window": 6,
                "include_recent_turns": False,
                "include_agent_observations": True,
                "memory_query_strategy": "objective",
            },
        },
    )
    conversation_id = uuid.UUID(create_response.json()["id"])
    run_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            ConversationTurn(
                id=uuid.uuid4(),
                session_id=conversation_id,
                turn_index=0,
                speaker_kind="agent",
                speaker_agent_id=agent_id,
                input_text="Prompt",
                output_text="Output",
                status="succeeded",
                run_id=run_id,
            ),
        )
        session.add(
            RuntimeDiagnosticEvent(
                id=uuid.uuid4(),
                severity="info",
                component="agent",
                event_type="agent.run_succeeded",
                message="Agent runtime run succeeded.",
                details={
                    "conversation_id": str(conversation_id),
                    "memory_backend": "local_pgvector",
                    "memory_hit_count": 2,
                    "memory_retrieval_enabled": True,
                },
                world_id=world_id,
                agent_id=agent_id,
                run_id=run_id,
                occurred_at=datetime.now(UTC),
            ),
        )
        session.commit()

    response = client.get(f"/worlds/{world_id}/conversations/{conversation_id}/memory/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["write_turn_memory"] is False
    assert body["retrieve_memory"] is True
    assert body["memory_query_strategy"] == "objective"
    assert body["latest_backend"] == "local_pgvector"
    assert body["latest_hit_count"] == 2


def test_conversation_api_validates_scene_scope_auto_lifecycle_and_agent_provider_profile() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id = _seed_world(engine, owner_id, "scene-world")
    first_scene_id = _seed_scene(engine, world_id, "hall")
    second_scene_id = _seed_scene(engine, world_id, "garden")
    in_scene_agent_id = _seed_agent(engine, world_id, "guide", first_scene_id)
    out_of_scene_agent_id = _seed_agent(engine, world_id, "outsider", second_scene_id)
    profile_id = _seed_provider_profile(engine)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _authenticate(client, owner_token)

    create_agent = client.post(
        f"/worlds/{world_id}/agents",
        json={
            "agent_key": "planner",
            "display_name": "Planner",
            "kind": "role_agent",
            "provider_profile_id": str(profile_id),
            "config": {"tone": "direct"},
        },
    )
    created_agent_id = create_agent.json()["id"]
    clear_provider = client.patch(
        f"/worlds/{world_id}/agents/{created_agent_id}",
        json={"provider_profile_id": None},
    )

    create_conversation = client.post(
        f"/worlds/{world_id}/conversations",
        json={
            "session_key": "auto-room",
            "title": "Auto room",
            "scope_type": "scene",
            "mode": "auto_dialogue",
            "scene_id": str(first_scene_id),
            "policy": _policy_json(),
            "writer_config": _writer_config_json(),
        },
    )
    invalid_world_scope = client.post(
        f"/worlds/{world_id}/conversations",
        json={
            "session_key": "invalid-world-scene",
            "title": "Invalid world scene",
            "scope_type": "world",
            "mode": "manual_chain",
            "scene_id": str(first_scene_id),
            "policy": _policy_json(),
            "writer_config": _writer_config_json(),
        },
    )
    invalid_scene_scope = client.post(
        f"/worlds/{world_id}/conversations",
        json={
            "session_key": "invalid-scene-missing",
            "title": "Invalid scene missing",
            "scope_type": "scene",
            "mode": "manual_chain",
            "policy": _policy_json(),
            "writer_config": _writer_config_json(),
        },
    )
    conversation_id = create_conversation.json()["id"]
    mismatched_participant = client.put(
        f"/worlds/{world_id}/conversations/{conversation_id}/participants",
        json=[{"agent_id": str(out_of_scene_agent_id), "turn_order": 0, "is_enabled": True}],
    )
    valid_participant = client.put(
        f"/worlds/{world_id}/conversations/{conversation_id}/participants",
        json=[{"agent_id": str(in_scene_agent_id), "turn_order": 0, "is_enabled": True}],
    )
    start_response = client.post(f"/worlds/{world_id}/conversations/{conversation_id}/start")
    advance_while_running = client.post(
        f"/worlds/{world_id}/conversations/{conversation_id}/advance",
    )
    pause_response = client.post(f"/worlds/{world_id}/conversations/{conversation_id}/pause")
    resume_response = client.post(f"/worlds/{world_id}/conversations/{conversation_id}/resume")

    assert create_agent.status_code == 201
    assert create_agent.json()["provider_profile_id"] is not None
    assert (
        create_agent.json()["config"]["provider_profile_id"]
        == create_agent.json()["provider_profile_id"]
    )
    assert clear_provider.status_code == 200
    assert clear_provider.json()["provider_profile_id"] is None
    assert "provider_profile_id" not in clear_provider.json()["config"]
    assert create_conversation.status_code == 201
    assert invalid_world_scope.status_code == 422
    assert invalid_scene_scope.status_code == 422
    assert mismatched_participant.status_code == 404
    assert valid_participant.status_code == 200
    assert start_response.status_code == 200
    assert start_response.json()["status"] == "running"
    assert advance_while_running.status_code == 409
    assert pause_response.status_code == 200
    assert pause_response.json()["status"] == "paused"
    assert resume_response.status_code == 200
    assert resume_response.json()["status"] == "running"


def test_conversation_api_stop_and_diagnostics() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id = _seed_world(engine, owner_id, "stop-world")
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _authenticate(client, owner_token)

    create_conversation = client.post(
        f"/worlds/{world_id}/conversations",
        json={
            "session_key": "stoppable",
            "title": "Stoppable",
            "scope_type": "world",
            "mode": "manual_chain",
            "policy": _policy_json(),
            "writer_config": _writer_config_json(),
        },
    )
    conversation_id = create_conversation.json()["id"]
    stop_response = client.post(f"/worlds/{world_id}/conversations/{conversation_id}/stop")
    diagnostics_response = client.get(
        f"/worlds/{world_id}/conversations/{conversation_id}/diagnostics",
    )
    diagnostics_summary = client.get(
        f"/worlds/{world_id}/conversations/{conversation_id}/diagnostics/summary",
    )

    assert stop_response.status_code == 200
    assert stop_response.json()["status"] == "stopped"
    assert stop_response.json()["terminal_reason"] == "operator_stopped"
    assert diagnostics_response.status_code == 200
    assert diagnostics_response.json()[0]["component"] == "conversation"
    assert diagnostics_response.json()[0]["details"]["conversation_id"] == str(conversation_id)
    assert diagnostics_summary.status_code == 200
    assert diagnostics_summary.json()["terminal_reason"] == "operator_stopped"
    assert diagnostics_summary.json()["operator_message"] == (
        "Conversation ended because operator_stopped."
    )


def test_conversation_narrative_listing_redacts_member_evidence() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id = _seed_world(engine, owner_id, "conversation-narrative-world")
    scene_id = _seed_scene(engine, world_id, "story-room")
    agent_id = _seed_agent(engine, world_id, "scribe", scene_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)

    _authenticate(client, owner_token)
    create_response = client.post(
        f"/worlds/{world_id}/conversations",
        json={
            "session_key": "member-narrative-session",
            "title": "Member narrative session",
            "scope_type": "scene",
            "mode": "manual_chain",
            "scene_id": str(scene_id),
            "policy": _policy_json(),
            "writer_config": _writer_config_json(),
        },
    )
    conversation_id = uuid.UUID(create_response.json()["id"])
    published_summary_id = _seed_conversation_narrative_artifact(
        engine,
        world_id,
        conversation_id,
        "Published summary",
        "Published summary body",
        agent_id=agent_id,
        source_run_id=uuid.uuid4(),
        metadata={
            "raw_prompt": "operator-only prompt",
            "storage_uri": "media://private/artifact",
        },
        publish=True,
        reader_visible=True,
    )
    sensitive_summary_id = _seed_conversation_narrative_artifact(
        engine,
        world_id,
        conversation_id,
        "Published raw_prompt summary",
        "storage_uri media://private/artifact body",
        agent_id=agent_id,
        source_run_id=uuid.uuid4(),
        metadata={"raw_output": "operator-only generated text"},
        publish=True,
        reader_visible=True,
    )
    draft_chapter_id = _seed_conversation_narrative_artifact(
        engine,
        world_id,
        conversation_id,
        "Draft chapter",
        "Draft chapter body",
        artifact_kind="chapter_draft",
        metadata={"raw_output": "operator-only draft"},
    )
    hidden_summary_id = _seed_conversation_narrative_artifact(
        engine,
        world_id,
        conversation_id,
        "Hidden summary",
        "Hidden summary body",
        metadata={"storage_uri": "media://hidden/artifact"},
        publish=True,
        reader_visible=False,
    )

    _authenticate(client, member_token)
    member_response = client.get(
        f"/worlds/{world_id}/conversations/{conversation_id}/narrative",
    )

    _authenticate(client, owner_token)
    admin_response = client.get(
        f"/worlds/{world_id}/conversations/{conversation_id}/narrative",
    )

    assert create_response.status_code == 201
    assert member_response.status_code == 200
    member_artifacts = {artifact["id"]: artifact for artifact in member_response.json()}
    assert set(member_artifacts) == {str(published_summary_id), str(sensitive_summary_id)}
    assert member_artifacts[str(published_summary_id)]["source_run_id"] is None
    assert member_artifacts[str(published_summary_id)]["source_conversation_id"] == str(
        conversation_id,
    )
    assert member_artifacts[str(published_summary_id)]["metadata"] == {}
    assert member_artifacts[str(published_summary_id)]["title"] == "Published summary"
    assert member_artifacts[str(published_summary_id)]["content"] == "Published summary body"
    assert member_artifacts[str(sensitive_summary_id)]["source_run_id"] is None
    assert member_artifacts[str(sensitive_summary_id)]["metadata"] == {}
    assert member_artifacts[str(sensitive_summary_id)]["title"] == ""
    assert member_artifacts[str(sensitive_summary_id)]["content"] == ""
    assert admin_response.status_code == 200
    assert {artifact["id"] for artifact in admin_response.json()} == {
        str(hidden_summary_id),
        str(draft_chapter_id),
        str(published_summary_id),
        str(sensitive_summary_id),
    }
    admin_published = next(
        artifact
        for artifact in admin_response.json()
        if artifact["id"] == str(published_summary_id)
    )
    assert admin_published["source_run_id"] is not None
    assert admin_published["metadata"]["raw_prompt"] == "operator-only prompt"
    admin_sensitive = next(
        artifact
        for artifact in admin_response.json()
        if artifact["id"] == str(sensitive_summary_id)
    )
    assert admin_sensitive["title"] == "Published raw_prompt summary"
    assert admin_sensitive["content"] == "storage_uri media://private/artifact body"


def test_conversation_narrative_generation_and_listing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id = _seed_world(engine, owner_id, "writer-world")
    scene_id = _seed_scene(engine, world_id, "story-room")
    agent_id = _seed_agent(engine, world_id, "scribe", scene_id)
    profile_id = _seed_provider_profile(engine)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)

    prompts: list[str] = []

    def fake_invoke_profile(
        self: ProviderProfileService,
        profile: object,
        prompt: str,
    ) -> ProviderCompletion:
        del self, profile
        prompts.append(prompt)
        if len(prompts) == 1:
            return ProviderCompletion(text="Conversation summary output", raw_response={"ok": True})
        return ProviderCompletion(text="Chapter draft output", raw_response={"ok": True})

    monkeypatch.setattr(ProviderProfileService, "invoke_profile", fake_invoke_profile)

    _authenticate(client, owner_token)
    create_response = client.post(
        f"/worlds/{world_id}/conversations",
        json={
            "session_key": "writer-session",
            "title": "Writer session",
            "scope_type": "scene",
            "mode": "manual_chain",
            "scene_id": str(scene_id),
            "max_turns": 1,
            "policy": _policy_json(),
            "writer_config": {
                **_writer_config_json(),
                "provider_profile_id": str(profile_id),
                "auto_generate_on_complete": True,
            },
        },
    )
    conversation_id = create_response.json()["id"]
    replace_response = client.put(
        f"/worlds/{world_id}/conversations/{conversation_id}/participants",
        json=[{"agent_id": str(agent_id), "turn_order": 0, "is_enabled": True}],
    )
    seed_response = client.post(
        f"/worlds/{world_id}/conversations/{conversation_id}/seed",
        json={"input_text": "Operator seed"},
    )
    advance_response = client.post(f"/worlds/{world_id}/conversations/{conversation_id}/advance")
    list_response = client.get(
        f"/worlds/{world_id}/conversations/{conversation_id}/narrative",
    )
    preview_response = client.post(
        f"/worlds/{world_id}/conversations/{conversation_id}/narrative/preview",
        json={"artifact_set": "summary_only"},
    )
    regenerate_response = client.post(
        f"/worlds/{world_id}/conversations/{conversation_id}/narrative/generate",
        json={"artifact_set": "summary_and_chapter"},
    )

    with Session(engine) as session:
        artifacts = session.scalars(select(NarrativeArtifact)).all()

    assert create_response.status_code == 201
    assert replace_response.status_code == 200
    assert seed_response.status_code == 200
    assert advance_response.status_code == 200
    assert advance_response.json()["session"]["status"] == "completed"
    assert list_response.status_code == 200
    assert preview_response.status_code == 200
    assert preview_response.json()["prompt_text"].startswith("Writer controls:")
    assert preview_response.json()["source_turn_count"] == 2
    assert regenerate_response.status_code == 200
    assert [artifact["artifact_kind"] for artifact in list_response.json()] == [
        "chapter_draft",
        "conversation_summary",
    ]
    assert len(prompts) == 3
    assert prompts[1].startswith("Writer controls:")
    assert "Write a concise but complete conversation summary." in prompts[1]
    assert "Write a chapter draft based on this Noveland conversation." in prompts[2]
    assert len(artifacts) == 2
    assert {artifact.artifact_kind for artifact in artifacts} == {
        "conversation_summary",
        "chapter_draft",
    }


def _client_with_database() -> tuple[TestClient, Engine]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in (
        cast(Table, User.__table__),
        cast(Table, AuthSession.__table__),
        cast(Table, PlatformRoleAssignment.__table__),
        cast(Table, MemoryBackendProfile.__table__),
        cast(Table, World.__table__),
        cast(Table, Worldline.__table__),
        cast(Table, WorldMembership.__table__),
        cast(Table, Scene.__table__),
        cast(Table, ProviderProfile.__table__),
        cast(Table, Agent.__table__),
        cast(Table, WorldBible.__table__),
        cast(Table, AgentRelationshipEdge.__table__),
        cast(Table, AgentPersona.__table__),
        cast(Table, AgentObservation.__table__),
        cast(Table, AgentCalendarEntry.__table__),
        cast(Table, WorldScheduleRule.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, AgentMemoryItem.__table__),
        cast(Table, MemoryWriteJob.__table__),
        cast(Table, MemoryWriteLog.__table__),
        cast(Table, MemoryRetrievalLog.__table__),
        cast(Table, AgentProfileSnapshotModel.__table__),
        cast(Table, AgentRuntimeRun.__table__),
        cast(Table, ModelInvocation.__table__),
        cast(Table, PromptTemplate.__table__),
        cast(Table, PromptSnapshot.__table__),
        cast(Table, AgentRuntimeRunModelInvocation.__table__),
        cast(Table, ModelInvocationTag.__table__),
        cast(Table, RuntimeDiagnosticEvent.__table__),
        cast(Table, ConversationSession.__table__),
        cast(Table, ConversationParticipant.__table__),
        cast(Table, ConversationTurn.__table__),
        cast(Table, NarrativeArtifact.__table__),
        cast(Table, NarrativePublication.__table__),
        cast(Table, SecretRecord.__table__),
        cast(Table, CharacterKnowledgeFact.__table__),
        cast(Table, CharacterEmotionalState.__table__),
        cast(Table, StoryHook.__table__),
        cast(Table, PlotThread.__table__),
        cast(Table, RouteAffinity.__table__),
        cast(Table, NarrativeContinuityReview.__table__),
    ):
        table.create(engine)
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


def _seed_user(engine: Engine, email: str) -> tuple[uuid.UUID, str]:
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
        session.commit()
    return user_id, token


def _seed_world(engine: Engine, owner_user_id: uuid.UUID, slug: str) -> uuid.UUID:
    world_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            World(
                id=world_id,
                owner_user_id=owner_user_id,
                slug=slug,
                name=slug,
                rules_config={},
                is_active=True,
            ),
        )
        session.commit()
    return world_id


def _seed_scene(engine: Engine, world_id: uuid.UUID, scene_key: str) -> uuid.UUID:
    scene_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            Scene(
                id=scene_id,
                world_id=world_id,
                scene_key=scene_key,
                name=scene_key,
                is_active=True,
            ),
        )
        session.commit()
    return scene_id


def _seed_agent(
    engine: Engine,
    world_id: uuid.UUID,
    agent_key: str,
    scene_id: uuid.UUID | None = None,
) -> uuid.UUID:
    agent_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            Agent(
                id=agent_id,
                world_id=world_id,
                home_scene_id=scene_id,
                agent_key=agent_key,
                display_name=agent_key,
                kind="role_agent",
                config={},
                is_enabled=True,
            ),
        )
        session.commit()
    return agent_id


def _seed_conversation_narrative_artifact(
    engine: Engine,
    world_id: uuid.UUID,
    conversation_id: uuid.UUID,
    title: str,
    content: str,
    *,
    agent_id: uuid.UUID | None = None,
    source_run_id: uuid.UUID | None = None,
    artifact_kind: str = "conversation_summary",
    metadata: dict[str, object] | None = None,
    publish: bool = False,
    reader_visible: bool = True,
) -> uuid.UUID:
    artifact_id = uuid.uuid4()
    now = datetime.now(UTC)
    with Session(engine) as session:
        session.add(
            NarrativeArtifact(
                id=artifact_id,
                world_id=world_id,
                agent_id=agent_id,
                source_run_id=source_run_id,
                source_conversation_id=conversation_id,
                title=title,
                content=content,
                artifact_kind=artifact_kind,
                artifact_metadata=metadata or {},
            ),
        )
        if publish:
            session.add(
                NarrativePublication(
                    id=uuid.uuid4(),
                    world_id=world_id,
                    artifact_id=artifact_id,
                    source_draft_id=artifact_id,
                    status="published",
                    reader_visible=reader_visible,
                    published_metadata={"publication_gate": {"status": "pass"}},
                    published_at=now,
                    published_by_user_id=None,
                ),
            )
        session.commit()
    return artifact_id


def _seed_provider_profile(engine: Engine) -> uuid.UUID:
    profile_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            ProviderProfile(
                id=profile_id,
                profile_key="runtime-profile",
                name="Runtime Profile",
                provider_type="openai_compatible",
                base_url="https://api.example.test/v1",
                model_name="test-model",
                capabilities={},
                api_key_ref="runtime-ref",
                is_enabled=True,
            ),
        )
        session.commit()
    return profile_id


def _seed_fork_worldline(engine: Engine, world_id: uuid.UUID) -> uuid.UUID:
    with Session(engine) as session:
        primary = ensure_primary_worldline(session, world_id)
        fork = Worldline(
            world_id=world_id,
            worldline_key=f"fork-{uuid.uuid4().hex[:8]}",
            name="Fork",
            description="Forked test worldline",
            parent_worldline_id=primary.id,
            status="active",
            created_by_actor_ref="test:conversation-api",
            metadata_json={},
        )
        session.add(fork)
        session.commit()
        return fork.id


def _add_membership(
    engine: Engine,
    world_id: uuid.UUID,
    user_id: uuid.UUID,
    role: AuthRole,
) -> None:
    with Session(engine) as session:
        session.add(
            WorldMembership(
                id=uuid.uuid4(),
                world_id=world_id,
                user_id=user_id,
                role=role.value,
            ),
        )
        session.commit()


def _authenticate(client: TestClient, token: str) -> None:
    client.cookies.clear()
    client.headers.clear()
    client.cookies.set(SESSION_COOKIE_NAME, token)
    client.cookies.set(CSRF_COOKIE_NAME, "csrf-token")
    client.headers.update({CSRF_HEADER_NAME: "csrf-token"})


def _policy_json() -> dict[str, object]:
    return {
        "error_policy": "retry_once_then_fail",
        "max_consecutive_failed_turns": 2,
        "loop_guard_window": 4,
        "repeat_output_threshold": 3,
    }


def _writer_config_json() -> dict[str, object]:
    return {
        "provider_profile_id": None,
        "auto_generate_on_complete": False,
        "generate_summary": True,
        "generate_chapter": True,
    }
