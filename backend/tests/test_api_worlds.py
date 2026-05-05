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
    AgentPreset,
    AgentRelationshipEdge,
    AgentRuntimeRun,
)
from noveland.auth import AuthRole
from noveland.auth.contracts import AuthSessionStatus
from noveland.auth.models import AuthSession, PlatformRoleAssignment, User
from noveland.auth.services import hash_session_token
from noveland.calendar.models import AgentCalendarEntry, WorldScheduleRule
from noveland.conversations.models import ConversationSession, ConversationTurn
from noveland.events import CLOCK_ADVANCED_EVENT_NAME, WorldEventAppend, WorldEventStore
from noveland.events.models import WorldEventModel, WorldSnapshotModel
from noveland.memory.models import (
    AgentMemoryItem,
    AgentProfileSnapshotModel,
    MemoryBackendProfile,
    MemoryRetrievalLog,
    MemoryWriteJob,
    MemoryWriteLog,
)
from noveland.narrative.models import NarrativeArtifact, NarrativePublication
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
    WorldBible,
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
    member_transitions = client.get(f"/worlds/{world_id}/clock/transitions")
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
    transitions = client.get(f"/worlds/{world_id}/clock/transitions", params={"limit": 3})

    assert read_clock.status_code == 200
    assert read_clock.json()["status"] == "paused"
    assert member_transitions.status_code == 403
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
    assert transitions.status_code == 200
    assert [item["transition_type"] for item in transitions.json()] == [
        "skip",
        "pause",
        "advance",
    ]
    assert transitions.json()[0]["new_revision"] == 4
    assert transitions.json()[0]["actor_ref"] == f"user:{owner_id}"
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


def test_world_bible_api_preserves_continuity_contract_and_access() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id = _seed_world(engine, owner_id, "bible-world")
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)

    _authenticate(client, member_token)
    empty_read = client.get(f"/worlds/{world_id}/bible")
    forbidden_write = client.put(
        f"/worlds/{world_id}/bible",
        json={"source_material": "blocked"},
    )

    _authenticate(client, owner_token)
    invalid_continuity = client.put(
        f"/worlds/{world_id}/bible",
        json={"continuity_config": {"status": "fanon"}},
    )
    created = client.put(
        f"/worlds/{world_id}/bible",
        json={
            "source_material": "Original ending and sequel notes.",
            "canon_timeline": [{"label": "Finale", "world_time": "2030-01-01"}],
            "setting_rules": {"school": "closed on Sunday"},
            "forbidden_changes": [{"rule": "Do not revive resolved antagonist"}],
            "sequel_boundaries": {"starts_after": "original finale"},
            "continuity_config": {"status": "post_canon", "tone": "daily"},
            "metadata": {"source": "operator"},
        },
    )
    updated = client.put(
        f"/worlds/{world_id}/bible",
        json={
            "source_material": "Updated sequel notes.",
            "continuity_config": {"continuity_status": "alternate"},
        },
    )

    assert empty_read.status_code == 200
    assert empty_read.json() is None
    assert forbidden_write.status_code == 403
    assert invalid_continuity.status_code == 422
    assert created.status_code == 200
    assert created.json()["source_material"] == "Original ending and sequel notes."
    assert created.json()["continuity_status"] == "post_canon"
    assert created.json()["metadata"] == {"source": "operator"}
    assert updated.status_code == 200
    assert updated.json()["source_material"] == "Updated sequel notes."
    assert updated.json()["continuity_status"] == "alternate"


def test_agent_character_metadata_and_continuity_surfaces_are_compatible() -> None:
    client, engine = _client_with_database()
    owner_id, token = _seed_user(engine, "owner@example.test")
    world_id = _seed_world(engine, owner_id, "character-world")
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _authenticate(client, token)

    legacy_agent = client.post(
        f"/worlds/{world_id}/agents",
        json={"agent_key": "legacy", "display_name": "Legacy", "kind": "role_agent"},
    )
    create_agent = client.post(
        f"/worlds/{world_id}/agents",
        json={
            "agent_key": "heroine",
            "display_name": "Heroine",
            "kind": "role_agent",
            "narrative_role": "main_character",
            "importance": "lead",
            "canon_status": "post_canon",
            "character_category": "main_character",
            "character_profile": {
                "speech_style_notes": "Soft Kansai inflection",
                "goals": ["reopen the club room"],
                "secrets": ["keeps the old letter"],
                "daily_preferences": {"morning": "library"},
                "emotional_baseline": "guarded but warm",
                "story_function": "route heroine",
            },
        },
    )
    update_agent = client.patch(
        f"/worlds/{world_id}/agents/{create_agent.json()['id']}",
        json={
            "importance": "major",
            "character_profile": {"goals": ["repair the club sign"]},
        },
    )
    invalid_agent = client.post(
        f"/worlds/{world_id}/agents",
        json={
            "agent_key": "bad-role",
            "display_name": "Bad Role",
            "kind": "role_agent",
            "narrative_role": "mascot",
        },
    )
    with Session(engine) as session:
        WorldEventStore(session).append_event(
            WorldEventAppend(
                world_id=world_id,
                event_name="story.post_canon_note",
                payload={
                    "summary": "The club room lights are on again.",
                    "continuity": {"status": "post_canon", "source": "bible"},
                },
                wall_time=datetime(2026, 5, 5, 12, 0, tzinfo=UTC),
                world_time=datetime(2030, 1, 2, 18, 0, tzinfo=UTC),
                actor_ref="user:test",
            ),
        )
        session.commit()
    events = client.get(f"/worlds/{world_id}/events")
    artifact = client.post(
        f"/worlds/{world_id}/narrative-artifacts",
        json={
            "title": "After Story Draft",
            "content": "The heroine returns to the club room.",
            "artifact_kind": "world_summary",
            "continuity_metadata": {"status": "post_canon", "source": "writer"},
        },
    )

    assert legacy_agent.status_code == 201
    assert legacy_agent.json()["narrative_role"] is None
    assert legacy_agent.json()["character_profile"] == {}
    assert create_agent.status_code == 201
    assert create_agent.json()["narrative_role"] == "main_character"
    assert create_agent.json()["canon_status"] == "post_canon"
    assert create_agent.json()["character_profile"]["story_function"] == "route heroine"
    assert update_agent.status_code == 200
    assert update_agent.json()["importance"] == "major"
    assert update_agent.json()["character_profile"] == {"goals": ["repair the club sign"]}
    assert invalid_agent.status_code == 422
    assert events.status_code == 200
    assert events.json()[0]["continuity_status"] == "post_canon"
    assert events.json()[0]["continuity_metadata"]["source"] == "bible"
    assert artifact.status_code == 201
    assert artifact.json()["continuity_status"] == "post_canon"
    assert artifact.json()["continuity_metadata"]["source"] == "writer"


def test_agent_relationship_graph_enforces_world_scope_and_updates_edges() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    other_owner_id, _other_token = _seed_user(engine, "other@example.test")
    world_id = _seed_world(engine, owner_id, "relationship-world")
    other_world_id = _seed_world(engine, other_owner_id, "other-relationship-world")
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    source_agent_id = _seed_agent(engine, world_id, "source")
    target_agent_id = _seed_agent(engine, world_id, "target")
    other_agent_id = _seed_agent(engine, other_world_id, "outside")

    _authenticate(client, member_token)
    member_empty = client.get(f"/worlds/{world_id}/agents/{source_agent_id}/relationships")
    member_create = client.post(
        f"/worlds/{world_id}/agents/{source_agent_id}/relationships",
        json={
            "source_agent_id": str(source_agent_id),
            "target_agent_id": str(target_agent_id),
            "relationship_type": "friendship",
        },
    )

    _authenticate(client, owner_token)
    self_edge = client.post(
        f"/worlds/{world_id}/agents/{source_agent_id}/relationships",
        json={
            "source_agent_id": str(source_agent_id),
            "target_agent_id": str(source_agent_id),
            "relationship_type": "friendship",
        },
    )
    cross_world = client.post(
        f"/worlds/{world_id}/agents/{source_agent_id}/relationships",
        json={
            "source_agent_id": str(source_agent_id),
            "target_agent_id": str(other_agent_id),
            "relationship_type": "friendship",
        },
    )
    created = client.post(
        f"/worlds/{world_id}/agents/{source_agent_id}/relationships",
        json={
            "source_agent_id": str(source_agent_id),
            "target_agent_id": str(target_agent_id),
            "relationship_type": "friendship",
            "affection": 42,
            "trust": 35,
            "metadata": {"reason": "shared promise"},
        },
    )
    duplicate = client.post(
        f"/worlds/{world_id}/agents/{source_agent_id}/relationships",
        json={
            "source_agent_id": str(source_agent_id),
            "target_agent_id": str(target_agent_id),
            "relationship_type": "friendship",
        },
    )
    updated = client.patch(
        f"/worlds/{world_id}/agents/{source_agent_id}/relationships/{created.json()['id']}",
        json={"trust": 55, "metadata": {"reason": "kept promise"}},
    )
    listed = client.get(f"/worlds/{world_id}/agents/{source_agent_id}/relationships")

    assert member_empty.status_code == 200
    assert member_empty.json() == []
    assert member_create.status_code == 403
    assert self_edge.status_code == 422
    assert cross_world.status_code == 404
    assert created.status_code == 201
    assert created.json()["source_agent_key"] == "source"
    assert created.json()["target_agent_key"] == "target"
    assert created.json()["relationship_type"] == "friendship"
    assert created.json()["affection"] == 42
    assert duplicate.status_code == 409
    assert updated.status_code == 200
    assert updated.json()["trust"] == 55
    assert updated.json()["metadata"] == {"reason": "kept promise"}
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == created.json()["id"]


def test_membership_management_and_final_admin_guard() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    user_id, _user_token = _seed_user(engine, "user@example.test")
    second_admin_id, second_token = _seed_user(engine, "second@example.test")
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
    _authenticate(client, second_token)
    access_review = client.get(f"/worlds/{world_id}/access-review")
    diagnostics = client.get(f"/worlds/{world_id}/diagnostics")

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
    assert access_review.status_code == 200
    assert access_review.json()["member_count"] == 1
    assert access_review.json()["world_admin_count"] == 1
    assert access_review.json()["final_admin_risk"] is True
    assert access_review.json()["members"][0]["user_id"] == str(second_admin_id)
    assert {
        item["event_type"] for item in diagnostics.json()
    } >= {"world.membership_upserted", "world.membership_deleted"}


def test_platform_admin_manages_agent_presets_and_world_admin_lists_active_presets() -> None:
    client, engine = _client_with_database()
    _platform_user_id, platform_token = _seed_user(
        engine,
        "platform@example.test",
        platform_admin=True,
    )
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id = _seed_world(engine, owner_id, "preset-world")
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _seed_provider_profile(engine, profile_key="preset-provider")

    _authenticate(client, platform_token)
    create_preset = client.post(
        "/agent-presets",
        json={
            "preset_key": "storyteller",
            "name": "Storyteller",
            "default_kind": "narrative_agent",
            "default_provider_profile_key": "preset-provider",
            "persona_text": "Writes as a storyteller.",
            "behavior_policy": {"tone": "gentle"},
            "calendar_blueprint": [
                {
                    "title": "Morning check-in",
                    "starts_at": "2030-01-01T08:00:00Z",
                    "metadata": {"source": "preset"},
                }
            ],
            "advanced_config": {"style": "baseline"},
        },
    )
    preset_id = create_preset.json()["id"]
    active_list_for_admin = client.get("/agent-presets")
    deactivate_preset = client.patch(
        f"/agent-presets/{preset_id}",
        json={"is_active": False, "name": "Storyteller Disabled"},
    )
    inactive_list_for_admin = client.get("/agent-presets")

    _authenticate(client, owner_token)
    active_list_for_world_admin = client.get("/agent-presets")

    assert create_preset.status_code == 201
    assert create_preset.json()["version"] == 1
    assert active_list_for_admin.status_code == 200
    assert active_list_for_admin.json()[0]["preset_key"] == "storyteller"
    assert deactivate_preset.status_code == 200
    assert deactivate_preset.json()["is_active"] is False
    assert deactivate_preset.json()["version"] == 2
    assert inactive_list_for_admin.status_code == 200
    assert inactive_list_for_admin.json()[0]["name"] == "Storyteller Disabled"
    assert active_list_for_world_admin.status_code == 200
    assert active_list_for_world_admin.json() == []


def test_create_agent_from_preset_materializes_persona_calendar_and_provider_mapping() -> None:
    client, engine = _client_with_database()
    _platform_user_id, platform_token = _seed_user(
        engine,
        "platform@example.test",
        platform_admin=True,
    )
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id = _seed_world(engine, owner_id, "agent-preset-world")
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _seed_provider_profile(engine, profile_key="preset-provider")

    _authenticate(client, platform_token)
    preset_response = client.post(
        "/agent-presets",
        json={
            "preset_key": "narrator",
            "name": "Narrator",
            "default_kind": "narrative_agent",
            "default_provider_profile_key": "preset-provider",
            "persona_text": "Always narrates in scene.",
            "behavior_policy": {"voice": "omniscient"},
            "calendar_blueprint": [
                {
                    "title": "Narrative pulse",
                    "starts_at": "2030-01-01T09:00:00Z",
                    "metadata": {"kind": "pulse"},
                }
            ],
            "advanced_config": {"style": "baseline", "length": "short"},
        },
    )
    preset_id = preset_response.json()["id"]

    _authenticate(client, owner_token)
    create_agent = client.post(
        f"/worlds/{world_id}/agents",
        json={
            "agent_key": "narrator",
            "display_name": "Narrator",
            "preset_id": preset_id,
            "config": {"style": "override", "temperature": 0.2},
        },
    )
    agent_id = create_agent.json()["id"]
    persona = client.get(f"/worlds/{world_id}/agents/{agent_id}/persona")
    calendar = client.get(f"/worlds/{world_id}/agents/{agent_id}/calendar")

    assert create_agent.status_code == 201
    assert create_agent.json()["kind"] == "narrative_agent"
    assert create_agent.json()["source_preset_id"] == preset_id
    assert create_agent.json()["source_preset_version"] == 1
    assert create_agent.json()["provider_profile_id"] == str(
        _provider_profile_id_by_key(engine, "preset-provider"),
    )
    assert create_agent.json()["config"]["style"] == "override"
    assert create_agent.json()["config"]["length"] == "short"
    assert create_agent.json()["config"]["temperature"] == 0.2
    assert persona.status_code == 200
    assert persona.json()["persona_text"] == "Always narrates in scene."
    assert calendar.status_code == 200
    assert [entry["title"] for entry in calendar.json()] == ["Narrative pulse"]

    _authenticate(client, platform_token)
    updated_preset = client.patch(
        f"/agent-presets/{preset_id}",
        json={"persona_text": "Updated persona.", "name": "Narrator v2"},
    )

    _authenticate(client, owner_token)
    agents = client.get(f"/worlds/{world_id}/agents")

    assert updated_preset.status_code == 200
    assert updated_preset.json()["version"] == 2
    assert agents.status_code == 200
    assert agents.json()[0]["source_preset_version"] == 1


def test_agent_preset_update_preview_reports_stale_and_current_agents() -> None:
    client, engine = _client_with_database()
    _platform_user_id, platform_token = _seed_user(
        engine,
        "platform@example.test",
        platform_admin=True,
    )
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id = _seed_world(engine, owner_id, "preset-preview-world")
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    preset_id = _seed_agent_preset(
        engine,
        preset_key="preview-preset",
        default_provider_profile_key=None,
    )
    _seed_agent(
        engine,
        world_id,
        "current-agent",
        source_preset_id=preset_id,
        source_preset_version=1,
    )
    stale_agent_id = _seed_agent(
        engine,
        world_id,
        "stale-agent",
        source_preset_id=preset_id,
        source_preset_version=1,
    )
    _seed_agent(
        engine,
        world_id,
        "unversioned-agent",
        source_preset_id=preset_id,
        source_preset_version=None,
    )

    _authenticate(client, platform_token)
    updated_preset = client.patch(
        f"/agent-presets/{preset_id}",
        json={"advanced_config": {"style": "updated", "temperature": 0.2}},
    )
    preview = client.get(f"/agent-presets/{preset_id}/update-preview")

    _authenticate(client, owner_token)
    forbidden = client.get(f"/agent-presets/{preset_id}/update-preview")

    preview_by_agent = {item["agent_key"]: item for item in preview.json()["agents"]}
    assert updated_preset.status_code == 200
    assert updated_preset.json()["version"] == 2
    assert preview.status_code == 200
    assert preview.json()["stale_agent_count"] == 2
    assert preview.json()["current_agent_count"] == 0
    assert preview.json()["unversioned_agent_count"] == 1
    assert preview_by_agent["stale-agent"]["agent_id"] == str(stale_agent_id)
    assert preview_by_agent["stale-agent"]["status"] == "stale"
    assert "config.style" in preview_by_agent["stale-agent"]["changed_fields"]
    assert preview_by_agent["unversioned-agent"]["status"] == "unversioned"
    assert forbidden.status_code == 403


def test_world_composition_export_and_import_round_trip() -> None:
    client, engine = _client_with_database()
    _platform_user_id, platform_token = _seed_user(
        engine,
        "platform@example.test",
        platform_admin=True,
    )
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    import_owner_id, import_owner_token = _seed_user(engine, "import-owner@example.test")
    world_id = _seed_world(engine, owner_id, "composition-source")
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    profile_id = _seed_provider_profile(engine, profile_key="composition-provider")
    preset_id = _seed_agent_preset(
        engine,
        preset_key="story-preset",
        default_provider_profile_key="composition-provider",
    )
    scene_id = _seed_scene(engine, world_id, "hall")
    _seed_schedule_rule(engine, world_id)
    _seed_agent(
        engine,
        world_id,
        "story-agent",
        scene_id=scene_id,
        source_preset_id=preset_id,
        provider_profile_id=profile_id,
    )

    _authenticate(client, owner_token)
    export_response = client.get(f"/worlds/{world_id}/composition-export")
    forbidden_import = client.post(
        "/world-compositions/import",
        json={
            "slug": "forbidden-import",
            "name": "Forbidden Import",
            "owner_user_id": str(import_owner_id),
            "composition": export_response.json(),
        },
    )
    forbidden_validate = client.post(
        "/world-compositions/validate",
        json={
            "slug": "forbidden-import",
            "name": "Forbidden Import",
            "owner_user_id": str(import_owner_id),
            "composition": export_response.json(),
        },
    )

    _authenticate(client, platform_token)
    validation_response = client.post(
        "/world-compositions/validate",
        json={
            "slug": "composition-imported",
            "name": "Composition Imported",
            "owner_user_id": str(import_owner_id),
            "composition": export_response.json(),
        },
    )
    import_response = client.post(
        "/world-compositions/import",
        json={
            "slug": "composition-imported",
            "name": "Composition Imported",
            "owner_user_id": str(import_owner_id),
            "composition": export_response.json(),
        },
    )
    imported_world_id = uuid.UUID(import_response.json()["id"])

    _authenticate(client, import_owner_token)
    imported_scenes = client.get(f"/worlds/{imported_world_id}/scenes")
    imported_agents = client.get(f"/worlds/{imported_world_id}/agents")
    imported_rules = client.get(f"/worlds/{imported_world_id}/schedule-rules")
    imported_persona = client.get(
        f"/worlds/{imported_world_id}/agents/{imported_agents.json()[0]['id']}/persona"
    )
    imported_calendar = client.get(
        f"/worlds/{imported_world_id}/agents/{imported_agents.json()[0]['id']}/calendar"
    )

    assert export_response.status_code == 200
    assert "memberships" not in export_response.json()
    assert (
        export_response.json()["world"]["memory_plugin_identifier"]
        == "builtin.local_pgvector_memory"
    )
    assert (
        export_response.json()["world"]["world_rules_plugin_identifier"]
        == "builtin.default_world_rules"
    )
    assert export_response.json()["agents"][0]["source_preset_key"] == "story-preset"
    assert export_response.json()["agents"][0]["source_preset_version"] is None
    assert export_response.json()["agents"][0]["provider_profile_key"] == "composition-provider"
    assert export_response.json()["preset_references"][0]["version"] == 1
    assert forbidden_import.status_code == 403
    assert forbidden_validate.status_code == 403
    assert validation_response.status_code == 200
    assert validation_response.json()["valid"] is True
    assert validation_response.json()["issues"] == []
    assert import_response.status_code == 201
    assert import_response.json()["slug"] == "composition-imported"
    assert imported_scenes.status_code == 200
    assert imported_scenes.json()[0]["scene_key"] == "hall"
    assert imported_agents.status_code == 200
    assert imported_agents.json()[0]["source_preset_id"] == str(preset_id)
    assert imported_agents.json()[0]["source_preset_version"] == 1
    assert imported_agents.json()[0]["provider_profile_id"] == str(profile_id)
    assert imported_rules.status_code == 200
    assert imported_rules.json()[0]["rule_key"] == "weekday"
    assert imported_persona.status_code == 200
    assert imported_persona.json()["persona_text"] == "Preset persona"
    assert imported_calendar.status_code == 200
    assert imported_calendar.json()[0]["title"] == "Preset briefing"


def test_world_composition_validation_reports_import_blockers() -> None:
    client, engine = _client_with_database()
    platform_user_id, platform_token = _seed_user(
        engine,
        "platform@example.test",
        platform_admin=True,
    )
    _seed_world(engine, platform_user_id, "existing-slug")
    payload = {
        "slug": "existing-slug",
        "name": "Invalid Import",
        "owner_user_id": str(platform_user_id),
        "composition": {
            "world": {
                "slug": "source",
                "name": "Source",
                "description": None,
                "rules_config": {},
                "memory_backend_profile_key": "missing-memory",
                "memory_plugin_identifier": "missing.memory_plugin",
                "memory_plugin_config": {},
                "world_rules_plugin_identifier": "missing.world_rules_plugin",
                "world_rules_plugin_config": {},
                "is_active": True,
            },
            "scenes": [
                {
                    "scene_key": "hall",
                    "name": "Hall",
                    "description": None,
                    "is_active": True,
                }
            ],
            "agents": [
                {
                    "agent_key": "guide",
                    "display_name": "Guide",
                    "kind": "role_agent",
                    "home_scene_key": "missing-scene",
                    "source_preset_key": "missing-preset",
                    "provider_profile_key": "missing-provider",
                    "config": {},
                    "is_enabled": True,
                }
            ],
            "schedule_rules": [
                {
                    "rule_key": "weekday",
                    "name": "Weekday",
                    "kind": "weekday",
                    "config": {},
                    "is_enabled": True,
                },
                {
                    "rule_key": "weekday",
                    "name": "Duplicate Weekday",
                    "kind": "weekday",
                    "config": {},
                    "is_enabled": True,
                },
            ],
            "preset_references": [
                {
                    "preset_key": "missing-preset",
                    "name": "Missing Preset",
                    "default_kind": "role_agent",
                    "default_provider_profile_key": "missing-provider",
                    "is_active": True,
                }
            ],
        },
    }

    _authenticate(client, platform_token)
    validation = client.post(
        "/world-compositions/validate",
        json=payload,
    )
    import_response = client.post("/world-compositions/import", json=payload)

    codes = {issue["code"] for issue in validation.json()["issues"]}
    assert validation.status_code == 200
    assert validation.json()["valid"] is False
    assert "slug_collision" in codes
    assert "unknown_memory_backend_profile" in codes
    assert "memory_plugin_missing" in codes
    assert "world_rules_plugin_missing" in codes
    assert "missing_preset" in codes
    assert "unknown_provider_profile" in codes
    assert "unknown_scene_key" in codes
    assert "duplicate_schedule_rule_key" in codes
    assert import_response.status_code == 422


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
    member_preview = client.post(
        f"/worlds/{world_id}/schedule-rules/preview",
        json={"kind": "weekday"},
    )
    member_conflicts = client.get(f"/worlds/{world_id}/calendar/conflicts")

    _authenticate(client, owner_token)
    preview_rule = client.post(
        f"/worlds/{world_id}/schedule-rules/preview",
        json={
            "kind": "timetable",
            "config": {"hours": [8]},
            "start_world_time": "2030-01-01T07:00:00Z",
            "horizon_hours": 2,
            "limit": 5,
        },
    )
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
    create_overlapping_entry = client.post(
        f"/worlds/{world_id}/agents/{agent_id}/calendar",
        json={
            "title": "Overlap scene",
            "starts_at": "2030-01-01T08:30:00Z",
            "ends_at": "2030-01-01T09:30:00Z",
        },
    )
    conflicts = client.get(
        f"/worlds/{world_id}/calendar/conflicts",
        params={
            "start_world_time": "2030-01-01T07:00:00Z",
            "horizon_hours": 4,
            "limit": 10,
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
    assert member_preview.status_code == 403
    assert member_conflicts.status_code == 403
    assert preview_rule.status_code == 200
    assert preview_rule.json()["kind"] == "timetable"
    assert preview_rule.json()["match_count"] == 1
    assert preview_rule.json()["affected_agent_count"] == 1
    assert preview_rule.json()["matches"][0]["world_time"].startswith("2030-01-01T08:00:00")
    assert create_rule.status_code == 201
    assert duplicate_rule.status_code == 409
    assert update_rule.status_code == 200
    assert update_rule.json()["name"] == "Weekday Updated"
    assert update_rule.json()["is_enabled"] is False
    assert create_entry.status_code == 201
    assert create_overlapping_entry.status_code == 201
    assert conflicts.status_code == 200
    assert conflicts.json()["conflict_count"] >= 1
    assert conflicts.json()["conflicts"][0]["conflict_type"] == "calendar_entry_overlap"
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
    with Session(engine) as session:
        session.add(
            AgentMemoryItem(
                world_id=world_id,
                agent_id=agent_id,
                content="Guide likes green tea",
                metadata_json={"source": "api-test"},
                embedding=_embedding(),
                visibility="private",
                is_active=True,
            ),
        )
        session.commit()

    _authenticate(client, member_token)
    member_list = client.get(f"/worlds/{world_id}/agents/{agent_id}/memory")
    member_search = client.post(
        f"/worlds/{world_id}/agents/{agent_id}/memory/search",
        json={"query_text": "blocked"},
    )
    member_snapshot = client.get(
        f"/worlds/{world_id}/agents/{agent_id}/memory/profile-snapshot",
    )
    member_forget = client.post(f"/worlds/{world_id}/agents/{agent_id}/memory/forget")

    _authenticate(client, owner_token)
    initial_snapshot = client.get(
        f"/worlds/{world_id}/agents/{agent_id}/memory/profile-snapshot",
    )
    refresh_snapshot = client.post(
        f"/worlds/{world_id}/agents/{agent_id}/memory/profile-snapshot/refresh",
    )
    list_memory = client.get(f"/worlds/{world_id}/agents/{agent_id}/memory")
    search_memory = client.post(
        f"/worlds/{world_id}/agents/{agent_id}/memory/search",
        json={"query_text": "green tea", "limit": 5},
    )
    bad_query = client.post(
        f"/worlds/{world_id}/agents/{agent_id}/memory/search",
        json={"query_text": ""},
    )
    forget_memory = client.post(f"/worlds/{world_id}/agents/{agent_id}/memory/forget")
    after_forget = client.get(f"/worlds/{world_id}/agents/{agent_id}/memory")

    assert member_list.status_code == 403
    assert member_search.status_code == 403
    assert member_snapshot.status_code == 403
    assert member_forget.status_code == 403
    assert initial_snapshot.status_code == 200
    assert initial_snapshot.json() is None
    assert refresh_snapshot.status_code == 200
    assert refresh_snapshot.json()["durable_preferences"] == ["Guide likes green tea"]
    assert list_memory.status_code == 200
    assert len(list_memory.json()) == 1
    assert list_memory.json()[0]["content"] == "Guide likes green tea"
    assert list_memory.json()[0]["metadata"] == {"source": "api-test"}
    assert search_memory.status_code == 200
    assert search_memory.json()[0]["content"] == "Guide likes green tea"
    assert isinstance(search_memory.json()[0]["score"], float)
    assert bad_query.status_code == 422
    assert forget_memory.status_code == 200
    assert forget_memory.json()["deleted_count"] == 1
    assert after_forget.json() == []


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
    run_detail = client.get(
        f"/worlds/{world_id}/agents/{agent_id}/runs/{run_response.json()['run_id']}",
    )
    _authenticate(client, member_token)
    member_run_detail = client.get(
        f"/worlds/{world_id}/agents/{agent_id}/runs/{run_response.json()['run_id']}",
    )
    _authenticate(client, owner_token)
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
    assert member_run_detail.status_code == 403
    assert member_create_artifact.status_code == 403
    assert run_response.status_code == 201
    assert run_response.json()["status"] == "succeeded"
    assert run_response.json()["response_text"].startswith("Run completed for: Operator run")
    assert run_response.json()["diagnostics"]["profile_key"] == "runtime-profile"
    assert list_runs.status_code == 200
    assert list_runs.json()[0]["run_id"] == run_response.json()["run_id"]
    assert run_detail.status_code == 200
    assert run_detail.json()["run"]["trigger_source"] == "manual"
    assert run_detail.json()["provider_profile"]["profile_key"] == "runtime-profile"
    assert run_detail.json()["conversation_turns"] == []
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
    member_integrity = client.get(f"/worlds/{world_id}/snapshots/integrity")
    member_create = client.post(f"/worlds/{world_id}/snapshots")

    _authenticate_session_only(client, owner_token)
    missing_csrf = client.post(f"/worlds/{world_id}/snapshots")
    _authenticate(client, owner_token)
    created = client.post(f"/worlds/{world_id}/snapshots")
    latest_after = client.get(f"/worlds/{world_id}/snapshots/latest")
    integrity_after = client.get(f"/worlds/{world_id}/snapshots/integrity")
    replay_after = client.get(f"/worlds/{world_id}/replay/state")

    _authenticate(client, stranger_token)
    hidden_replay = client.get(f"/worlds/{world_id}/replay/state")
    hidden_integrity = client.get(f"/worlds/{world_id}/snapshots/integrity")

    assert replay.status_code == 200
    assert replay.json()["clock"]["revision"] == 1
    assert replay.json()["applied_event_count"] == 1
    assert latest_before.status_code == 200
    assert latest_before.json() is None
    assert member_integrity.status_code == 403
    assert member_create.status_code == 403
    assert missing_csrf.status_code == 403
    assert created.status_code == 201
    assert created.json()["covers_event_sequence"] == 1
    assert created.json()["schema_version"] == "world_state.v1"
    assert latest_after.status_code == 200
    assert latest_after.json()["id"] == created.json()["id"]
    assert integrity_after.status_code == 200
    assert integrity_after.json()["status"] == "ok"
    assert integrity_after.json()["latest_snapshot_id"] == created.json()["id"]
    assert integrity_after.json()["event_gap"] == 0
    assert replay_after.json()["source_sequence"] == 2
    assert hidden_replay.status_code == 404
    assert hidden_integrity.status_code == 404


def test_world_event_audit_requires_admin_and_filters_events() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    _stranger_id, stranger_token = _seed_user(engine, "stranger@example.test")
    world_id = _seed_world(engine, owner_id, "event-audit-world")
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    correlation_id = uuid.uuid4()
    _seed_world_event(
        engine,
        world_id,
        event_name="agent.run_succeeded",
        actor_ref="agent:guide",
        minute=1,
        payload={"source": "agent", "output": "ok"},
        correlation_id=correlation_id,
    )
    _seed_world_event(
        engine,
        world_id,
        event_name="conversation.turn_completed",
        actor_ref="conversation:seed",
        minute=2,
        payload={"turn": 1},
    )
    _seed_world_event(
        engine,
        world_id,
        event_name="agent.run_failed",
        actor_ref="agent:guide",
        minute=3,
        payload={"error": "provider timeout"},
    )

    _authenticate(client, member_token)
    member_events = client.get(f"/worlds/{world_id}/events")

    _authenticate(client, owner_token)
    all_events = client.get(f"/worlds/{world_id}/events")
    by_event_name = client.get(
        f"/worlds/{world_id}/events",
        params={"event_name": "agent.run_succeeded"},
    )
    by_actor = client.get(f"/worlds/{world_id}/events", params={"actor_ref": "agent:guide"})
    by_sequence = client.get(
        f"/worlds/{world_id}/events",
        params={"sequence_after": 1, "sequence_before": 3},
    )
    by_wall_time = client.get(
        f"/worlds/{world_id}/events",
        params={
            "wall_time_from": "2026-04-17T12:02:00Z",
            "wall_time_to": "2026-04-17T12:03:00Z",
        },
    )
    limited = client.get(f"/worlds/{world_id}/events", params={"limit": 1})
    limit_too_high = client.get(f"/worlds/{world_id}/events", params={"limit": 101})

    _authenticate(client, stranger_token)
    hidden_events = client.get(f"/worlds/{world_id}/events")

    assert member_events.status_code == 403
    assert all_events.status_code == 200
    assert [event["sequence"] for event in all_events.json()] == [3, 2, 1]
    assert all_events.json()[2]["payload"]["output"] == "ok"
    assert all_events.json()[2]["correlation_id"] == str(correlation_id)
    assert by_event_name.status_code == 200
    assert [event["event_name"] for event in by_event_name.json()] == ["agent.run_succeeded"]
    assert by_actor.status_code == 200
    assert [event["sequence"] for event in by_actor.json()] == [3, 1]
    assert by_sequence.status_code == 200
    assert [event["event_name"] for event in by_sequence.json()] == [
        "conversation.turn_completed",
    ]
    assert by_wall_time.status_code == 200
    assert [event["sequence"] for event in by_wall_time.json()] == [3, 2]
    assert limited.status_code == 200
    assert [event["sequence"] for event in limited.json()] == [3]
    assert limit_too_high.status_code == 422
    assert hidden_events.status_code == 404


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
    member_validate_persona = client.post(
        f"/worlds/{world_id}/agents/{agent_id}/persona/validate",
        json={"persona_text": "Blocked"},
    )
    member_observations = client.get(f"/worlds/{world_id}/agents/{agent_id}/observations")

    _authenticate(client, owner_token)
    empty_persona = client.get(f"/worlds/{world_id}/agents/{agent_id}/persona")
    valid_persona = client.post(
        f"/worlds/{world_id}/agents/{agent_id}/persona/validate",
        json={
            "persona_text": "Careful guide.",
            "behavior_policy": {"tone": "direct"},
            "is_enabled": True,
        },
    )
    invalid_persona = client.post(
        f"/worlds/{world_id}/agents/{agent_id}/persona/validate",
        json={
            "persona_text": "",
            "behavior_policy": {"required": ["direct"], "disabled": ["direct"]},
            "policy_plugin_config": {"unexpected": True},
            "is_enabled": True,
        },
    )
    invalid_save = client.patch(
        f"/worlds/{world_id}/agents/{agent_id}/persona",
        json={
            "persona_text": "",
            "behavior_policy": {"required": ["direct"], "disabled": ["direct"]},
            "is_enabled": True,
        },
    )
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
        json={
            "content": "Operator observation",
            "observation_type": "manual",
            "confidence_score": 0.75,
            "review_status": "approved",
        },
    )
    refreshed = client.post(f"/worlds/{world_id}/agents/{agent_id}/observations/refresh")
    listed = client.get(f"/worlds/{world_id}/agents/{agent_id}/observations")

    assert member_persona.status_code == 403
    assert member_validate_persona.status_code == 403
    assert member_observations.status_code == 403
    assert empty_persona.status_code == 200
    assert empty_persona.json() is None
    assert valid_persona.status_code == 200
    assert valid_persona.json()["valid"] is True
    assert invalid_persona.status_code == 200
    assert invalid_persona.json()["valid"] is False
    assert invalid_save.status_code == 422
    assert upsert_persona.status_code == 200
    assert upsert_persona.json()["persona_text"] == "Careful guide."
    assert upsert_persona.json()["behavior_policy"] == {"tone": "direct"}
    assert manual_observation.status_code == 201
    assert manual_observation.json()["content"] == "Operator observation"
    assert manual_observation.json()["confidence_score"] == 0.75
    assert manual_observation.json()["review_status"] == "approved"
    assert manual_observation.json()["runtime_use_count"] == 0
    assert manual_observation.json()["last_used_run_id"] is None
    assert refreshed.status_code == 200
    assert any(item["observation_type"] == "world.clock_advanced" for item in refreshed.json())
    assert listed.status_code == 200
    assert {item["observation_type"] for item in listed.json()} >= {
        "manual",
        "world.clock_advanced",
    }


def test_narrative_reader_api_supports_filters_and_detail_for_world_members() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    _stranger_id, stranger_token = _seed_user(engine, "stranger@example.test")
    world_id = _seed_world(engine, owner_id, "reader-world")
    conversation_id = _seed_conversation(engine, world_id, "reader-conversation")
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    summary_id = _seed_narrative_artifact(
        engine,
        world_id,
        "Conversation summary",
        "Summary body",
        artifact_kind="conversation_summary",
        source_conversation_id=conversation_id,
    )
    _publish_narrative_artifact(engine, world_id, summary_id, owner_id)
    draft_chapter_id = _seed_narrative_artifact(
        engine,
        world_id,
        "Chapter draft",
        "Chapter body",
        artifact_kind="chapter_draft",
        source_conversation_id=conversation_id,
    )
    _seed_narrative_artifact(
        engine,
        world_id,
        "World summary",
        "World body",
        artifact_kind="world_summary",
    )

    _authenticate(client, member_token)
    filtered = client.get(
        f"/worlds/{world_id}/narrative-artifacts",
        params={
            "artifact_kind": "conversation_summary",
            "source_conversation_id": str(conversation_id),
            "q": "summary body",
            "source_kind": "conversation",
            "order_by": "published_at",
            "limit": 1,
        },
    )
    hidden_draft_search = client.get(
        f"/worlds/{world_id}/narrative-artifacts",
        params={"q": "chapter", "source_kind": "conversation"},
    )
    detail = client.get(f"/worlds/{world_id}/narrative-artifacts/{summary_id}")

    _authenticate(client, owner_token)
    owner_list = client.get(
        f"/worlds/{world_id}/narrative-artifacts",
        params={"source_conversation_id": str(conversation_id), "publication_status": "draft"},
    )

    _authenticate(client, stranger_token)
    hidden = client.get(f"/worlds/{world_id}/narrative-artifacts/{summary_id}")

    assert filtered.status_code == 200
    assert len(filtered.json()) == 1
    assert filtered.json()[0]["artifact_kind"] == "conversation_summary"
    assert filtered.json()[0]["source_conversation_id"] == str(conversation_id)
    assert hidden_draft_search.status_code == 200
    assert hidden_draft_search.json() == []
    assert detail.status_code == 200
    assert detail.json()["id"] == str(summary_id)
    assert detail.json()["source_conversation_id"] == str(conversation_id)
    assert owner_list.status_code == 200
    assert [item["artifact_kind"] for item in owner_list.json()] == [
        "chapter_draft",
    ]
    assert owner_list.json()[0]["id"] == str(draft_chapter_id)
    assert owner_list.json()[0]["publication"] is None
    assert hidden.status_code == 404


def test_narrative_publication_workflow_filters_reader_visibility() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id = _seed_world(engine, owner_id, "publication-world")
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    draft_id = _seed_narrative_artifact(
        engine,
        world_id,
        "Draft chapter",
        "Draft body",
        artifact_kind="chapter_draft",
    )

    _authenticate(client, member_token)
    member_before_publish = client.get(f"/worlds/{world_id}/narrative-artifacts")
    member_draft_detail = client.get(f"/worlds/{world_id}/narrative-artifacts/{draft_id}")
    member_publish = client.post(f"/worlds/{world_id}/narrative-artifacts/{draft_id}/publish")

    _authenticate(client, owner_token)
    publish = client.post(
        f"/worlds/{world_id}/narrative-artifacts/{draft_id}/publish",
        json={"reader_visible": True, "metadata": {"channel": "reader"}},
    )

    _authenticate(client, member_token)
    member_after_publish = client.get(f"/worlds/{world_id}/narrative-artifacts")
    member_published_detail = client.get(f"/worlds/{world_id}/narrative-artifacts/{draft_id}")

    _authenticate(client, owner_token)
    unpublish = client.post(
        f"/worlds/{world_id}/narrative-artifacts/{draft_id}/unpublish",
        json={"metadata": {"reason": "revision"}},
    )

    _authenticate(client, member_token)
    member_after_unpublish = client.get(f"/worlds/{world_id}/narrative-artifacts")
    member_unpublished_detail = client.get(f"/worlds/{world_id}/narrative-artifacts/{draft_id}")

    assert member_before_publish.status_code == 200
    assert member_before_publish.json() == []
    assert member_draft_detail.status_code == 404
    assert member_publish.status_code == 403
    assert publish.status_code == 200
    assert publish.json()["status"] == "published"
    assert publish.json()["reader_visible"] is True
    assert publish.json()["metadata"] == {"channel": "reader"}
    assert publish.json()["published_by_user_id"] == str(owner_id)
    assert member_after_publish.status_code == 200
    assert member_after_publish.json()[0]["id"] == str(draft_id)
    assert member_after_publish.json()[0]["publication"]["status"] == "published"
    assert member_published_detail.status_code == 200
    assert member_published_detail.json()["content"] == "Draft body"
    assert unpublish.status_code == 200
    assert unpublish.json()["status"] == "unpublished"
    assert unpublish.json()["reader_visible"] is False
    assert unpublish.json()["metadata"] == {"channel": "reader", "reason": "revision"}
    assert member_after_unpublish.status_code == 200
    assert member_after_unpublish.json() == []
    assert member_unpublished_detail.status_code == 404


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
        cast(Table, MemoryBackendProfile.__table__),
        cast(Table, World.__table__),
        cast(Table, WorldMembership.__table__),
        cast(Table, Scene.__table__),
        cast(Table, WorldClockStateModel.__table__),
        cast(Table, WorldClockTransitionModel.__table__),
        cast(Table, AgentPreset.__table__),
        cast(Table, Agent.__table__),
        cast(Table, WorldBible.__table__),
        cast(Table, AgentRelationshipEdge.__table__),
        cast(Table, AgentPersona.__table__),
        cast(Table, AgentObservation.__table__),
        cast(Table, AgentCalendarEntry.__table__),
        cast(Table, WorldScheduleRule.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, WorldSnapshotModel.__table__),
        cast(Table, AgentMemoryItem.__table__),
        cast(Table, MemoryWriteJob.__table__),
        cast(Table, MemoryWriteLog.__table__),
        cast(Table, MemoryRetrievalLog.__table__),
        cast(Table, AgentProfileSnapshotModel.__table__),
        cast(Table, ProviderProfile.__table__),
        cast(Table, AgentRuntimeRun.__table__),
        cast(Table, ConversationSession.__table__),
        cast(Table, ConversationTurn.__table__),
        cast(Table, NarrativeArtifact.__table__),
        cast(Table, NarrativePublication.__table__),
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


def _seed_agent(
    engine: Engine,
    world_id: uuid.UUID,
    agent_key: str,
    *,
    scene_id: uuid.UUID | None = None,
    source_preset_id: uuid.UUID | None = None,
    source_preset_version: int | None = None,
    provider_profile_id: uuid.UUID | None = None,
) -> uuid.UUID:
    agent_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            Agent(
                id=agent_id,
                world_id=world_id,
                home_scene_id=scene_id,
                source_preset_id=source_preset_id,
                source_preset_version=source_preset_version,
                agent_key=agent_key,
                display_name=agent_key,
                kind="role_agent",
                config=(
                    {}
                    if provider_profile_id is None
                    else {"provider_profile_id": str(provider_profile_id)}
                ),
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


def _seed_provider_profile(
    engine: Engine,
    *,
    profile_key: str = "runtime-profile",
) -> uuid.UUID:
    profile_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            ProviderProfile(
                id=profile_id,
                profile_key=profile_key,
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


def _provider_profile_id_by_key(engine: Engine, profile_key: str) -> uuid.UUID:
    with Session(engine) as session:
        return session.scalars(
            select(ProviderProfile.id).where(ProviderProfile.profile_key == profile_key),
        ).one()


def _seed_agent_preset(
    engine: Engine,
    *,
    preset_key: str,
    default_provider_profile_key: str | None,
) -> uuid.UUID:
    preset_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            AgentPreset(
                id=preset_id,
                preset_key=preset_key,
                name=preset_key,
                default_kind="role_agent",
                default_provider_profile_key=default_provider_profile_key,
                persona_text="Preset persona",
                behavior_policy={"tone": "direct"},
                calendar_blueprint_json=[
                    {
                        "title": "Preset briefing",
                        "description": None,
                        "starts_at": "2030-01-01T07:00:00Z",
                        "ends_at": None,
                        "recurrence_rule": None,
                        "metadata": {"source": "preset"},
                    }
                ],
                advanced_config={"style": "preset"},
                is_active=True,
            ),
        )
        session.commit()
    return preset_id


def _seed_schedule_rule(engine: Engine, world_id: uuid.UUID) -> uuid.UUID:
    rule_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            WorldScheduleRule(
                id=rule_id,
                world_id=world_id,
                rule_key="weekday",
                name="Weekday",
                kind="weekday",
                config={"window": "day"},
                is_enabled=True,
            )
        )
        session.commit()
    return rule_id


def _seed_conversation(engine: Engine, world_id: uuid.UUID, session_key: str) -> uuid.UUID:
    conversation_id = uuid.uuid4()
    now = datetime.now(UTC)
    with Session(engine) as session:
        session.add(
            ConversationSession(
                id=conversation_id,
                world_id=world_id,
                scene_id=None,
                session_key=session_key,
                title=session_key,
                scope_type="world",
                mode="manual_chain",
                status="completed",
                objective="Reader seed",
                opening_prompt="Reader seed",
                max_turns=4,
                next_turn_index=1,
                policy_config={
                    "error_policy": "fail_session",
                    "max_consecutive_failed_turns": 1,
                    "loop_guard_window": 4,
                    "repeat_output_threshold": 2,
                },
                writer_config={
                    "provider_profile_id": None,
                    "auto_generate_on_complete": False,
                    "generate_summary": True,
                    "generate_chapter": True,
                },
                terminal_reason="max_turns_reached",
                created_at=now,
                updated_at=now,
            ),
        )
        session.commit()
    return conversation_id


def _seed_narrative_artifact(
    engine: Engine,
    world_id: uuid.UUID,
    title: str,
    content: str,
    *,
    artifact_kind: str,
    source_conversation_id: uuid.UUID | None = None,
) -> uuid.UUID:
    artifact_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            NarrativeArtifact(
                id=artifact_id,
                world_id=world_id,
                agent_id=None,
                source_run_id=None,
                source_conversation_id=source_conversation_id,
                title=title,
                content=content,
                artifact_kind=artifact_kind,
                artifact_metadata={},
            ),
        )
        session.commit()
    return artifact_id


def _publish_narrative_artifact(
    engine: Engine,
    world_id: uuid.UUID,
    artifact_id: uuid.UUID,
    published_by_user_id: uuid.UUID,
) -> uuid.UUID:
    publication_id = uuid.uuid4()
    now = datetime.now(UTC)
    with Session(engine) as session:
        session.add(
            NarrativePublication(
                id=publication_id,
                world_id=world_id,
                artifact_id=artifact_id,
                source_draft_id=artifact_id,
                status="published",
                reader_visible=True,
                published_metadata={},
                published_at=now,
                unpublished_at=None,
                published_by_user_id=published_by_user_id,
            ),
        )
        session.commit()
    return publication_id


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


def _seed_world_event(
    engine: Engine,
    world_id: uuid.UUID,
    *,
    event_name: str,
    actor_ref: str,
    minute: int,
    payload: dict[str, object],
    correlation_id: uuid.UUID | None = None,
) -> None:
    with Session(engine) as session:
        WorldEventStore(session).append_event(
            WorldEventAppend(
                world_id=world_id,
                event_name=event_name,
                payload=payload,
                wall_time=datetime(2026, 4, 17, 12, minute, tzinfo=UTC),
                world_time=datetime(2030, 1, 1, 0, minute, tzinfo=UTC),
                actor_ref=actor_ref,
                correlation_id=correlation_id,
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
