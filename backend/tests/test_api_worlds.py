from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
from fastapi.testclient import TestClient
from noveland.adapters import ProviderCompletion, ProviderProfileService
from noveland.adapters.models import ProviderProfile
from noveland.agents.models import Agent, AgentObservation, AgentPersona, AgentRuntimeRun
from noveland.auth import AuthRole
from noveland.auth.contracts import AuthSessionStatus
from noveland.auth.models import AuthSession, PlatformRoleAssignment, User
from noveland.auth.services import hash_session_token
from noveland.calendar.models import AgentCalendarEntry, WorldScheduleRule
from noveland.events import CLOCK_ADVANCED_EVENT_NAME, WorldEventAppend, WorldEventStore
from noveland.events.models import WorldEventModel, WorldSnapshotModel
from noveland.memory.models import AgentMemoryItem
from noveland.narrative.models import NarrativeArtifact
from noveland.observability import (
    DiagnosticComponent,
    DiagnosticSeverity,
    RuntimeDiagnosticCreate,
    RuntimeDiagnosticsService,
)
from noveland.observability.models import RuntimeDiagnosticEvent
from noveland.services.api.app import create_app
from noveland.services.api.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from noveland.services.api.dependencies import get_db_session
from noveland.worlds.models import (
    Scene,
    World,
    WorldClockStateModel,
    WorldClockTransitionModel,
    WorldMembership,
)
from sqlalchemy import Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_platform_admin_can_create_list_and_update_worlds() -> None:
    client, engine = _client_with_database()
    platform_user_id, token = _seed_user(engine, "platform@example.test", platform_admin=True)
    _authenticate(client, token)

    create_response = client.post(
        "/worlds",
        json={
            "slug": "first-world",
            "name": "First World",
            "description": "Initial test world",
            "rules_config": {"mode": "local"},
        },
    )
    world = create_response.json()
    list_response = client.get("/worlds")
    update_response = client.patch(
        f"/worlds/{world['id']}",
        json={"name": "Renamed World", "is_active": False},
    )
    deactivate_response = client.delete(f"/worlds/{world['id']}")
    inactive_world = _world_is_active(engine, uuid.UUID(world["id"]))

    assert create_response.status_code == 201
    assert world["owner_user_id"] == str(platform_user_id)
    assert list_response.status_code == 200
    assert [item["slug"] for item in list_response.json()] == ["first-world"]
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Renamed World"
    assert update_response.json()["is_active"] is False
    assert deactivate_response.status_code == 204
    assert inactive_world is False
    assert _membership_role(engine, uuid.UUID(world["id"]), platform_user_id) == "world_admin"
    assert _clock_revision(engine, uuid.UUID(world["id"])) == 0


def test_world_member_can_read_but_not_mutate_and_non_member_is_hidden() -> None:
    client, engine = _client_with_database()
    owner_id, _owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    _stranger_id, stranger_token = _seed_user(engine, "stranger@example.test")
    world_id = _seed_world(engine, owner_id, "shared-world")
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)

    _authenticate(client, member_token)
    member_list = client.get("/worlds")
    member_get = client.get(f"/worlds/{world_id}")
    member_patch = client.patch(f"/worlds/{world_id}", json={"name": "Blocked"})
    member_candidates = client.get(f"/worlds/{world_id}/member-candidates")

    _authenticate(client, stranger_token)
    stranger_list = client.get("/worlds")
    stranger_get = client.get(f"/worlds/{world_id}")

    assert [item["id"] for item in member_list.json()] == [str(world_id)]
    assert member_get.status_code == 200
    assert member_patch.status_code == 403
    assert member_candidates.status_code == 403
    assert stranger_list.json() == []
    assert stranger_get.status_code == 404


def test_world_mutations_require_csrf() -> None:
    client, engine = _client_with_database()
    platform_user_id, token = _seed_user(engine, "platform@example.test", platform_admin=True)
    _authenticate_session_only(client, token)

    missing_csrf = client.post("/worlds", json={"slug": "missing-csrf", "name": "Blocked"})
    client.cookies.set(CSRF_COOKIE_NAME, "csrf-token")
    wrong_csrf = client.post(
        "/worlds",
        headers={CSRF_HEADER_NAME: "wrong-token"},
        json={"slug": "wrong-csrf", "name": "Blocked"},
    )
    allowed = client.post(
        "/worlds",
        headers={CSRF_HEADER_NAME: "csrf-token"},
        json={"slug": "allowed-world", "name": "Allowed"},
    )

    assert platform_user_id
    assert missing_csrf.status_code == 403
    assert wrong_csrf.status_code == 403
    assert allowed.status_code == 201


def test_clock_api_allows_members_to_read_and_admins_to_control_clock() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id = _seed_world(engine, owner_id, "clock-world")
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)

    _authenticate(client, member_token)
    read_clock = client.get(f"/worlds/{world_id}/clock")
    blocked_resume = client.post(
        f"/worlds/{world_id}/clock/resume",
        json={"speed_multiplier": "2"},
    )

    _authenticate_session_only(client, owner_token)
    missing_csrf = client.post(f"/worlds/{world_id}/clock/resume", json={})
    _authenticate(client, owner_token)
    resume = client.post(
        f"/worlds/{world_id}/clock/resume",
        json={"speed_multiplier": "2.5", "reason": "test resume"},
    )
    advance = client.post(f"/worlds/{world_id}/clock/advance", json={"reason": "checkpoint"})
    pause = client.post(f"/worlds/{world_id}/clock/pause", json={"reason": "operator pause"})
    skip = client.post(
        f"/worlds/{world_id}/clock/skip",
        json={"target_world_time": "2030-01-01T00:00:00Z"},
    )

    assert read_clock.status_code == 200
    assert read_clock.json()["status"] == "paused"
    assert blocked_resume.status_code == 403
    assert missing_csrf.status_code == 403
    assert resume.status_code == 200
    assert resume.json()["status"] == "running"
    assert resume.json()["speed_multiplier"] == "2.5"
    assert advance.status_code == 200
    assert advance.json()["revision"] == 2
    assert pause.status_code == 200
    assert pause.json()["status"] == "paused"
    assert skip.status_code == 200
    assert skip.json()["current_world_time"].startswith("2030-01-01T00:00:00")
    assert _clock_revision(engine, world_id) == 4


def test_clock_api_rejects_invalid_transitions_and_inputs() -> None:
    client, engine = _client_with_database()
    owner_id, token = _seed_user(engine, "owner@example.test")
    world_id = _seed_world(engine, owner_id, "clock-errors")
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _authenticate(client, token)

    pause_paused = client.post(f"/worlds/{world_id}/clock/pause", json={})
    bad_multiplier = client.post(
        f"/worlds/{world_id}/clock/resume",
        json={"speed_multiplier": 0},
    )
    bad_skip = client.post(
        f"/worlds/{world_id}/clock/skip",
        json={"target_world_time": "not-a-date"},
    )

    assert pause_paused.status_code == 409
    assert bad_multiplier.status_code == 422
    assert bad_skip.status_code == 422


def test_world_admin_manages_scenes_agents_and_conflicts() -> None:
    client, engine = _client_with_database()
    owner_id, token = _seed_user(engine, "owner@example.test")
    other_owner_id, _other_token = _seed_user(engine, "other@example.test")
    world_id = _seed_world(engine, owner_id, "agent-world")
    other_world_id = _seed_world(engine, other_owner_id, "other-world")
    other_scene_id = _seed_scene(engine, other_world_id, "outside")
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _authenticate(client, token)

    scene_response = client.post(
        f"/worlds/{world_id}/scenes",
        json={"scene_key": "home", "name": "Home"},
    )
    scene_id = scene_response.json()["id"]
    duplicate_scene = client.post(
        f"/worlds/{world_id}/scenes",
        json={"scene_key": "home", "name": "Home Again"},
    )
    update_scene = client.patch(
        f"/worlds/{world_id}/scenes/{scene_id}",
        json={"name": "New Home", "is_active": False},
    )
    deactivate_scene = client.delete(f"/worlds/{world_id}/scenes/{scene_id}")
    agent_response = client.post(
        f"/worlds/{world_id}/agents",
        json={
            "agent_key": "guide",
            "display_name": "Guide",
            "kind": "role_agent",
            "home_scene_id": scene_id,
            "config": {"tone": "direct"},
        },
    )
    duplicate_agent = client.post(
        f"/worlds/{world_id}/agents",
        json={"agent_key": "guide", "display_name": "Guide", "kind": "role_agent"},
    )
    cross_world_agent = client.post(
        f"/worlds/{world_id}/agents",
        json={
            "agent_key": "outsider",
            "display_name": "Outsider",
            "kind": "role_agent",
            "home_scene_id": str(other_scene_id),
        },
    )
    update_agent = client.patch(
        f"/worlds/{world_id}/agents/{agent_response.json()['id']}",
        json={"display_name": "Guide Updated", "is_enabled": False},
    )
    deactivate_agent = client.delete(f"/worlds/{world_id}/agents/{agent_response.json()['id']}")
    list_agents = client.get(f"/worlds/{world_id}/agents")

    assert scene_response.status_code == 201
    assert duplicate_scene.status_code == 409
    assert update_scene.status_code == 200
    assert update_scene.json()["is_active"] is False
    assert deactivate_scene.status_code == 204
    assert _scene_is_active(engine, uuid.UUID(scene_id)) is False
    assert agent_response.status_code == 201
    assert duplicate_agent.status_code == 409
    assert cross_world_agent.status_code == 404
    assert update_agent.status_code == 200
    assert update_agent.json()["display_name"] == "Guide Updated"
    assert deactivate_agent.status_code == 204
    assert _agent_is_enabled(engine, uuid.UUID(agent_response.json()["id"])) is False
    assert list_agents.json()[0]["agent_key"] == "guide"


def test_membership_management_and_final_admin_guard() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    user_id, _user_token = _seed_user(engine, "user@example.test")
    second_admin_id, _second_token = _seed_user(engine, "second@example.test")
    world_id = _seed_world(engine, owner_id, "membership-world")
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _authenticate(client, owner_token)

    invalid_role = client.put(
        f"/worlds/{world_id}/memberships/{user_id}",
        json={"user_id": str(user_id), "role": "platform_admin"},
    )
    create_member = client.put(
        f"/worlds/{world_id}/memberships/{user_id}",
        json={"user_id": str(user_id), "role": "human_user"},
    )
    list_members = client.get(f"/worlds/{world_id}/memberships")
    member_candidates = client.get(
        f"/worlds/{world_id}/member-candidates",
        params={"query": "user", "limit": 5},
    )
    invalid_limit = client.get(f"/worlds/{world_id}/member-candidates", params={"limit": 51})
    delete_member = client.delete(f"/worlds/{world_id}/memberships/{user_id}")
    downgrade_final_admin = client.put(
        f"/worlds/{world_id}/memberships/{owner_id}",
        json={"user_id": str(owner_id), "role": "human_user"},
    )
    delete_final_admin = client.delete(f"/worlds/{world_id}/memberships/{owner_id}")
    add_second_admin = client.put(
        f"/worlds/{world_id}/memberships/{second_admin_id}",
        json={"user_id": str(second_admin_id), "role": "world_admin"},
    )
    delete_original_admin = client.delete(f"/worlds/{world_id}/memberships/{owner_id}")

    assert invalid_role.status_code == 422
    assert create_member.status_code == 200
    assert create_member.json()["role"] == "human_user"
    assert create_member.json()["user"]["email"] == "user@example.test"
    assert sorted(item["role"] for item in list_members.json()) == ["human_user", "world_admin"]
    assert list_members.json()[0]["user"]["email"]
    assert member_candidates.status_code == 200
    assert invalid_limit.status_code == 422
    assert member_candidates.json() == [
        {
            "id": str(user_id),
            "email": "user@example.test",
            "display_name": "user@example.test",
            "is_active": True,
            "role": "human_user",
        },
    ]
    assert delete_member.status_code == 204
    assert downgrade_final_admin.status_code == 409
    assert delete_final_admin.status_code == 409
    assert add_second_admin.status_code == 200
    assert delete_original_admin.status_code == 204


def test_world_admin_manages_calendar_entries_and_schedule_rules() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id = _seed_world(engine, owner_id, "calendar-world")
    agent_id = _seed_agent(engine, world_id, "guide")
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)

    _authenticate(client, member_token)
    member_rules = client.get(f"/worlds/{world_id}/schedule-rules")
    member_create_rule = client.post(
        f"/worlds/{world_id}/schedule-rules",
        json={"rule_key": "weekday", "name": "Weekday", "kind": "weekday"},
    )

    _authenticate(client, owner_token)
    create_rule = client.post(
        f"/worlds/{world_id}/schedule-rules",
        json={"rule_key": "weekday", "name": "Weekday", "kind": "weekday"},
    )
    duplicate_rule = client.post(
        f"/worlds/{world_id}/schedule-rules",
        json={"rule_key": "weekday", "name": "Again", "kind": "weekday"},
    )
    update_rule = client.patch(
        f"/worlds/{world_id}/schedule-rules/{create_rule.json()['id']}",
        json={"name": "Weekday Updated", "is_enabled": False},
    )
    create_entry = client.post(
        f"/worlds/{world_id}/agents/{agent_id}/calendar",
        json={
            "title": "Morning scene",
            "starts_at": "2030-01-01T08:00:00Z",
            "ends_at": "2030-01-01T09:00:00Z",
            "metadata": {"source": "api-test"},
        },
    )
    list_entries = client.get(f"/worlds/{world_id}/agents/{agent_id}/calendar")
    update_entry = client.patch(
        f"/worlds/{world_id}/agents/{agent_id}/calendar/{create_entry.json()['id']}",
        json={"title": "Morning scene updated"},
    )
    cancel_entry = client.delete(
        f"/worlds/{world_id}/agents/{agent_id}/calendar/{create_entry.json()['id']}",
    )

    assert member_rules.status_code == 200
    assert member_create_rule.status_code == 403
    assert create_rule.status_code == 201
    assert duplicate_rule.status_code == 409
    assert update_rule.status_code == 200
    assert update_rule.json()["name"] == "Weekday Updated"
    assert update_rule.json()["is_enabled"] is False
    assert create_entry.status_code == 201
    assert create_entry.json()["status"] == "active"
    assert list_entries.status_code == 200
    assert list_entries.json()[0]["title"] == "Morning scene"
    assert update_entry.status_code == 200
    assert update_entry.json()["title"] == "Morning scene updated"
    assert cancel_entry.status_code == 204


def test_world_admin_manages_agent_memory() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id = _seed_world(engine, owner_id, "memory-world")
    agent_id = _seed_agent(engine, world_id, "guide")
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)

    _authenticate(client, member_token)
    member_list = client.get(f"/worlds/{world_id}/agents/{agent_id}/memory")
    member_create = client.post(
        f"/worlds/{world_id}/agents/{agent_id}/memory",
        json={"content": "blocked", "embedding": _embedding()},
    )

    _authenticate(client, owner_token)
    create_memory = client.post(
        f"/worlds/{world_id}/agents/{agent_id}/memory",
        json={
            "content": "Stored memory",
            "embedding": _embedding(),
            "metadata": {"source": "api-test"},
        },
    )
    list_memory = client.get(f"/worlds/{world_id}/agents/{agent_id}/memory")
    search_memory = client.post(
        f"/worlds/{world_id}/agents/{agent_id}/memory/search",
        json={"embedding": _embedding(), "limit": 5},
    )
    bad_embedding = client.post(
        f"/worlds/{world_id}/agents/{agent_id}/memory/search",
        json={"embedding": [1, 2, 3]},
    )
    disable_memory = client.delete(
        f"/worlds/{world_id}/agents/{agent_id}/memory/{create_memory.json()['id']}",
    )
    list_after_disable = client.get(f"/worlds/{world_id}/agents/{agent_id}/memory")

    assert member_list.status_code == 403
    assert member_create.status_code == 403
    assert create_memory.status_code == 201
    assert create_memory.json()["content"] == "Stored memory"
    assert create_memory.json()["visibility"] == "private"
    assert create_memory.json()["metadata"] == {"source": "api-test"}
    assert list_memory.status_code == 200
    assert len(list_memory.json()) == 1
    assert search_memory.status_code == 200
    assert search_memory.json()[0]["content"] == "Stored memory"
    assert isinstance(search_memory.json()[0]["score"], float)
    assert bad_embedding.status_code == 422
    assert disable_memory.status_code == 204
    assert list_after_disable.json() == []


def test_agent_runs_and_narrative_artifacts_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id = _seed_world(engine, owner_id, "runtime-world")
    agent_id = _seed_agent(engine, world_id, "guide")
    _seed_provider_profile(engine)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)

    def fake_invoke_profile(
        self: ProviderProfileService,
        profile: object,
        prompt: str,
    ) -> ProviderCompletion:
        del self, profile
        return ProviderCompletion(
            text=f"Run completed for: {prompt}",
            raw_response={"ok": True},
        )

    monkeypatch.setattr(ProviderProfileService, "invoke_profile", fake_invoke_profile)

    _authenticate(client, member_token)
    member_list_runs = client.get(f"/worlds/{world_id}/agents/{agent_id}/runs")
    member_list_artifacts = client.get(f"/worlds/{world_id}/narrative-artifacts")
    member_run = client.post(
        f"/worlds/{world_id}/agents/{agent_id}/run",
        json={"prompt": "blocked"},
    )
    member_create_artifact = client.post(
        f"/worlds/{world_id}/narrative-artifacts",
        json={"title": "Blocked", "content": "Blocked"},
    )

    _authenticate(client, owner_token)
    run_response = client.post(
        f"/worlds/{world_id}/agents/{agent_id}/run",
        json={"prompt": "Operator run"},
    )
    list_runs = client.get(f"/worlds/{world_id}/agents/{agent_id}/runs")
    create_artifact = client.post(
        f"/worlds/{world_id}/narrative-artifacts",
        json={
            "title": "Manual summary",
            "content": "Current world summary",
            "artifact_kind": "world_summary",
            "agent_id": str(agent_id),
        },
    )
    list_artifacts = client.get(f"/worlds/{world_id}/narrative-artifacts")

    assert member_list_runs.status_code == 200
    assert member_list_runs.json() == []
    assert member_list_artifacts.status_code == 200
    assert member_list_artifacts.json() == []
    assert member_run.status_code == 403
    assert member_create_artifact.status_code == 403
    assert run_response.status_code == 201
    assert run_response.json()["status"] == "succeeded"
    assert run_response.json()["response_text"].startswith("Run completed for: Operator run")
    assert run_response.json()["diagnostics"]["profile_key"] == "runtime-profile"
    assert list_runs.status_code == 200
    assert list_runs.json()[0]["run_id"] == run_response.json()["run_id"]
    assert create_artifact.status_code == 201
    assert create_artifact.json()["artifact_kind"] == "world_summary"
    assert [item["title"] for item in list_artifacts.json()] == [
        "Manual summary",
        "guide runtime note",
    ]


def test_replay_and_snapshot_api_reads_state_and_creates_snapshot() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    _stranger_id, stranger_token = _seed_user(engine, "stranger@example.test")
    world_id = _seed_world(engine, owner_id, "replay-world")
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    _seed_clock_event(engine, world_id, revision=1)

    _authenticate(client, member_token)
    replay = client.get(f"/worlds/{world_id}/replay/state")
    latest_before = client.get(f"/worlds/{world_id}/snapshots/latest")
    member_create = client.post(f"/worlds/{world_id}/snapshots")

    _authenticate_session_only(client, owner_token)
    missing_csrf = client.post(f"/worlds/{world_id}/snapshots")
    _authenticate(client, owner_token)
    created = client.post(f"/worlds/{world_id}/snapshots")
    latest_after = client.get(f"/worlds/{world_id}/snapshots/latest")
    replay_after = client.get(f"/worlds/{world_id}/replay/state")

    _authenticate(client, stranger_token)
    hidden_replay = client.get(f"/worlds/{world_id}/replay/state")

    assert replay.status_code == 200
    assert replay.json()["clock"]["revision"] == 1
    assert replay.json()["applied_event_count"] == 1
    assert latest_before.status_code == 200
    assert latest_before.json() is None
    assert member_create.status_code == 403
    assert missing_csrf.status_code == 403
    assert created.status_code == 201
    assert created.json()["covers_event_sequence"] == 1
    assert created.json()["schema_version"] == "world_state.v1"
    assert latest_after.status_code == 200
    assert latest_after.json()["id"] == created.json()["id"]
    assert replay_after.json()["source_sequence"] == 2
    assert hidden_replay.status_code == 404


def test_world_diagnostics_require_world_admin() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    _stranger_id, stranger_token = _seed_user(engine, "stranger@example.test")
    world_id = _seed_world(engine, owner_id, "diagnostics-world")
    agent_id = _seed_agent(engine, world_id, "guide")
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    _seed_world_diagnostic(engine, world_id, agent_id)

    _authenticate(client, member_token)
    member_response = client.get(f"/worlds/{world_id}/diagnostics")

    _authenticate(client, owner_token)
    owner_response = client.get(
        f"/worlds/{world_id}/diagnostics",
        params={"agent_id": str(agent_id)},
    )

    _authenticate(client, stranger_token)
    hidden_response = client.get(f"/worlds/{world_id}/diagnostics")

    assert member_response.status_code == 403
    assert owner_response.status_code == 200
    assert owner_response.json()[0]["event_type"] == "agent.run_failed"
    assert owner_response.json()[0]["agent_id"] == str(agent_id)
    assert hidden_response.status_code == 404


def test_agent_persona_and_observation_api_requires_world_admin() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id = _seed_world(engine, owner_id, "persona-world")
    agent_id = _seed_agent(engine, world_id, "guide")
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    _seed_clock_event(engine, world_id, revision=1)

    _authenticate(client, member_token)
    member_persona = client.get(f"/worlds/{world_id}/agents/{agent_id}/persona")
    member_observations = client.get(f"/worlds/{world_id}/agents/{agent_id}/observations")

    _authenticate(client, owner_token)
    empty_persona = client.get(f"/worlds/{world_id}/agents/{agent_id}/persona")
    upsert_persona = client.patch(
        f"/worlds/{world_id}/agents/{agent_id}/persona",
        json={
            "persona_text": "Careful guide.",
            "behavior_policy": {"tone": "direct"},
            "is_enabled": True,
        },
    )
    manual_observation = client.post(
        f"/worlds/{world_id}/agents/{agent_id}/observations",
        json={"content": "Operator observation", "observation_type": "manual"},
    )
    refreshed = client.post(f"/worlds/{world_id}/agents/{agent_id}/observations/refresh")
    listed = client.get(f"/worlds/{world_id}/agents/{agent_id}/observations")

    assert member_persona.status_code == 403
    assert member_observations.status_code == 403
    assert empty_persona.status_code == 200
    assert empty_persona.json() is None
    assert upsert_persona.status_code == 200
    assert upsert_persona.json()["persona_text"] == "Careful guide."
    assert upsert_persona.json()["behavior_policy"] == {"tone": "direct"}
    assert manual_observation.status_code == 201
    assert manual_observation.json()["content"] == "Operator observation"
    assert refreshed.status_code == 200
    assert any(item["observation_type"] == "world.clock_advanced" for item in refreshed.json())
    assert listed.status_code == 200
    assert {item["observation_type"] for item in listed.json()} >= {
        "manual",
        "world.clock_advanced",
    }


def _client_with_database() -> tuple[TestClient, Engine]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    _create_tables(engine)
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


def _create_tables(engine: Engine) -> None:
    for table in (
        cast(Table, User.__table__),
        cast(Table, AuthSession.__table__),
        cast(Table, PlatformRoleAssignment.__table__),
        cast(Table, World.__table__),
        cast(Table, WorldMembership.__table__),
        cast(Table, Scene.__table__),
        cast(Table, WorldClockStateModel.__table__),
        cast(Table, WorldClockTransitionModel.__table__),
        cast(Table, Agent.__table__),
        cast(Table, AgentPersona.__table__),
        cast(Table, AgentObservation.__table__),
        cast(Table, AgentCalendarEntry.__table__),
        cast(Table, WorldScheduleRule.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, WorldSnapshotModel.__table__),
        cast(Table, AgentMemoryItem.__table__),
        cast(Table, ProviderProfile.__table__),
        cast(Table, AgentRuntimeRun.__table__),
        cast(Table, NarrativeArtifact.__table__),
        cast(Table, RuntimeDiagnosticEvent.__table__),
    ):
        table.create(engine)


def _seed_user(engine: Engine, email: str, platform_admin: bool = False) -> tuple[uuid.UUID, str]:
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


def _seed_agent(engine: Engine, world_id: uuid.UUID, agent_key: str) -> uuid.UUID:
    agent_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            Agent(
                id=agent_id,
                world_id=world_id,
                agent_key=agent_key,
                display_name=agent_key,
                kind="role_agent",
                config={},
            ),
        )
        session.commit()
    return agent_id


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


def _seed_provider_profile(engine: Engine) -> None:
    with Session(engine) as session:
        session.add(
            ProviderProfile(
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


def _membership_role(engine: Engine, world_id: uuid.UUID, user_id: uuid.UUID) -> str | None:
    with Session(engine) as session:
        return session.scalars(
            select(WorldMembership.role).where(
                WorldMembership.world_id == world_id,
                WorldMembership.user_id == user_id,
            ),
        ).one_or_none()


def _world_is_active(engine: Engine, world_id: uuid.UUID) -> bool:
    with Session(engine) as session:
        return bool(session.scalars(select(World.is_active).where(World.id == world_id)).one())


def _scene_is_active(engine: Engine, scene_id: uuid.UUID) -> bool:
    with Session(engine) as session:
        return bool(session.scalars(select(Scene.is_active).where(Scene.id == scene_id)).one())


def _agent_is_enabled(engine: Engine, agent_id: uuid.UUID) -> bool:
    with Session(engine) as session:
        return bool(session.scalars(select(Agent.is_enabled).where(Agent.id == agent_id)).one())


def _clock_revision(engine: Engine, world_id: uuid.UUID) -> int:
    with Session(engine) as session:
        return session.scalars(
            select(WorldClockStateModel.revision).where(WorldClockStateModel.world_id == world_id),
        ).one()


def _seed_clock_event(engine: Engine, world_id: uuid.UUID, revision: int) -> None:
    with Session(engine) as session:
        WorldEventStore(session).append_event(
            WorldEventAppend(
                world_id=world_id,
                event_name=CLOCK_ADVANCED_EVENT_NAME,
                payload={
                    "status": "running",
                    "current_world_time": "2030-01-01T00:00:00+00:00",
                    "effective_world_time": "2030-01-01T00:00:00+00:00",
                    "wall_time_anchor": "2026-04-17T12:00:00+00:00",
                    "speed_multiplier": "1",
                    "revision": revision,
                },
                wall_time=datetime(2026, 4, 17, 12, revision, tzinfo=UTC),
                world_time=datetime(2030, 1, 1, 0, revision - 1, tzinfo=UTC),
                actor_ref="system:test",
            ),
        )
        session.commit()


def _seed_world_diagnostic(engine: Engine, world_id: uuid.UUID, agent_id: uuid.UUID) -> None:
    with Session(engine) as session:
        RuntimeDiagnosticsService(session).record(
            RuntimeDiagnosticCreate(
                severity=DiagnosticSeverity.ERROR,
                component=DiagnosticComponent.AGENT,
                event_type="agent.run_failed",
                message="Agent run failed.",
                details={"error": "Provider failed"},
                world_id=world_id,
                agent_id=agent_id,
            ),
        )
        session.commit()


def _authenticate(client: TestClient, token: str) -> None:
    _authenticate_session_only(client, token)
    client.cookies.set(CSRF_COOKIE_NAME, "csrf-token")
    client.headers.update({CSRF_HEADER_NAME: "csrf-token"})


def _authenticate_session_only(client: TestClient, token: str) -> None:
    client.cookies.clear()
    client.headers.clear()
    client.cookies.set(SESSION_COOKIE_NAME, token)


def _embedding() -> list[float]:
    return [1.0] + [0.0] * 1535
