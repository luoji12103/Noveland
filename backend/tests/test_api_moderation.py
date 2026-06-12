from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, cast

from fastapi.testclient import TestClient
from noveland.auth import AuthRole
from noveland.auth.contracts import AuthSessionStatus
from noveland.auth.models import AuthSession, PlatformRoleAssignment, User
from noveland.auth.services import hash_session_token
from noveland.beta_feedback.models import BetaFeedbackReport
from noveland.conversations.models import ConversationSession
from noveland.events.models import WorldEventModel
from noveland.media.models import MediaAsset, MediaObject, MediaReference
from noveland.media.storage import LocalMediaObjectStorage
from noveland.moderation.models import ModerationAction, ModerationIncident, ModerationReport
from noveland.narrative.models import NarrativeArtifact, NarrativePublication
from noveland.providers.models import ProviderIntegration
from noveland.services.api.app import create_app
from noveland.services.api.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from noveland.services.api.dependencies import get_db_session
from noveland.services.api.media import _media_storage
from noveland.services.api.reader_media import _reader_media_storage
from noveland.worlds.models import PlayerActorProfile, Scene, World, Worldline, WorldMembership
from sqlalchemy import Table, create_engine, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

FORBIDDEN_MARKERS = (
    "storage_uri",
    "media://",
    "file://",
    "s3://",
    "gs://",
    "base64",
    "raw_prompt",
    "raw_output",
    "prompt_snapshot",
    "promptsnapshot",
    "rawprompt",
    "rawoutput",
    "storageuri",
    "api_key",
    "bearer_token",
    "authorization",
    "secret-value",
    "/tmp/",
    "/root/",
)


def test_reader_can_create_report_and_admin_can_review_without_leaks() -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test", platform_admin=True)
    member_id, member_token = _seed_user(engine, "member@example.test")
    other_id, other_token = _seed_user(engine, "other@example.test")
    world_id, worldline_id = _seed_world_graph(engine, admin_id)
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    _add_membership(engine, world_id, other_id, AuthRole.HUMAN_USER)
    target_id = _seed_conversation(engine, world_id, worldline_id)

    client.cookies.set(CSRF_COOKIE_NAME, "csrf-token")
    unauthenticated = client.post(
        f"/worlds/{world_id}/moderation/reports",
        json=_report_payload(worldline_id, target_id),
        headers={CSRF_HEADER_NAME: "csrf-token"},
    )
    _authenticate_without_csrf(client, member_token)
    missing_csrf_report = client.post(
        f"/worlds/{world_id}/moderation/reports",
        json=_report_payload(worldline_id, target_id),
    )

    _authenticate(client, member_token)
    created = client.post(
        f"/worlds/{world_id}/moderation/reports",
        json=_report_payload(worldline_id, target_id),
    )
    unsafe = client.post(
        f"/worlds/{world_id}/moderation/reports",
        json={
            **_report_payload(worldline_id, target_id),
            "reason": "leak storage_uri media://private",
        },
    )
    member_list = client.get(f"/worlds/{world_id}/moderation/reports")

    _authenticate(client, other_token)
    other_list = client.get(f"/worlds/{world_id}/moderation/reports")

    _authenticate_without_csrf(client, admin_token)
    missing_csrf_review = client.patch(
        f"/worlds/{world_id}/moderation/reports/{created.json()['id']}",
        json={"status": "under_review", "review_note": "missing csrf"},
    )

    _authenticate(client, admin_token)
    admin_list = client.get(f"/worlds/{world_id}/moderation/reports")
    reviewed = client.patch(
        f"/worlds/{world_id}/moderation/reports/{created.json()['id']}",
        json={"status": "under_review", "review_note": "Triaged for review."},
    )

    assert unauthenticated.status_code == 401
    assert missing_csrf_report.status_code == 403
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "submitted"
    assert body["reporter_user_id"] == str(member_id)
    assert body["worldline_id"] == str(worldline_id)
    assert body["evidence_refs"][0]["kind"] == "conversation_session"
    assert body["metadata"] == {"client_note": "safe", "nested": {"safe": "kept"}}
    assert unsafe.status_code == 400
    assert member_list.status_code == 403
    assert other_list.status_code == 403
    assert admin_list.status_code == 200
    assert missing_csrf_review.status_code == 403
    assert [item["id"] for item in admin_list.json()] == [body["id"]]
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "under_review"
    _assert_no_forbidden_markers(body)
    _assert_no_forbidden_markers(admin_list.json())
    _assert_no_forbidden_markers(reviewed.json())


def test_moderation_rejects_cross_worldline_report_targets() -> None:
    client, engine = _client_with_database()
    admin_id, _admin_token = _seed_user(engine, "admin@example.test", platform_admin=True)
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id, _worldline_id = _seed_world_graph(engine, admin_id)
    other_world_id, other_worldline_id = _seed_world_graph(engine, admin_id, slug="other-world")
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    _add_membership(engine, other_world_id, member_id, AuthRole.HUMAN_USER)

    _authenticate(client, member_token)
    response = client.post(
        f"/worlds/{world_id}/moderation/reports",
        json=_report_payload(other_worldline_id, uuid.uuid4()),
    )

    assert response.status_code == 404


def test_moderation_rejects_unresolved_concrete_target_refs() -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test", platform_admin=True)
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id, worldline_id = _seed_world_graph(engine, admin_id)
    other_worldline_id = _seed_worldline(engine, world_id, "secondary")
    other_world_id, _other_worldline_id = _seed_world_graph(
        engine, admin_id, slug="other-target-scope"
    )
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    publication_id = _seed_publication(engine, world_id, worldline_id)
    other_publication_id = _seed_publication(engine, world_id, other_worldline_id)
    player_profile_id = _seed_player_profile(engine, world_id, worldline_id, member_id)
    other_player_profile_id = _seed_player_profile(engine, world_id, other_worldline_id, member_id)
    scene_id = _seed_scene(engine, world_id)
    other_scene_id = _seed_scene(engine, other_world_id)
    random_target_id = uuid.uuid4()

    _authenticate(client, member_token)
    missing_publication_report = client.post(
        f"/worlds/{world_id}/moderation/reports",
        json={
            **_report_payload(worldline_id, random_target_id),
            "target_ref_kind": "narrative_publication",
            "target_ref_id": str(random_target_id),
        },
    )
    cross_worldline_publication_report = client.post(
        f"/worlds/{world_id}/moderation/reports",
        json={
            **_report_payload(worldline_id, other_publication_id),
            "target_ref_kind": "narrative_publication",
            "target_ref_id": str(other_publication_id),
        },
    )
    valid_publication_report = client.post(
        f"/worlds/{world_id}/moderation/reports",
        json={
            **_report_payload(worldline_id, publication_id),
            "target_ref_kind": "narrative_publication",
            "target_ref_id": str(publication_id),
        },
    )

    _authenticate(client, admin_token)
    missing_scene_action = client.post(
        f"/worlds/{world_id}/moderation/actions",
        json={
            "action_kind": "note_only",
            "target_ref_kind": "scene",
            "target_ref_id": str(random_target_id),
            "reason": "Scene report should target a real scene.",
        },
    )
    cross_world_scene_action = client.post(
        f"/worlds/{world_id}/moderation/actions",
        json={
            "action_kind": "note_only",
            "target_ref_kind": "scene",
            "target_ref_id": str(other_scene_id),
            "reason": "Scene report should stay in world scope.",
        },
    )
    valid_scene_action = client.post(
        f"/worlds/{world_id}/moderation/actions",
        json={
            "action_kind": "note_only",
            "target_ref_kind": "scene",
            "target_ref_id": str(scene_id),
            "reason": "Scene report targets an existing scene.",
        },
    )
    missing_profile_action = client.post(
        f"/worlds/{world_id}/moderation/actions",
        json={
            "worldline_id": str(worldline_id),
            "action_kind": "note_only",
            "target_ref_kind": "player_profile",
            "target_ref_id": str(random_target_id),
            "reason": "Player report should target a real profile.",
        },
    )
    cross_worldline_profile_action = client.post(
        f"/worlds/{world_id}/moderation/actions",
        json={
            "worldline_id": str(worldline_id),
            "action_kind": "note_only",
            "target_ref_kind": "player_profile",
            "target_ref_id": str(other_player_profile_id),
            "reason": "Player report should stay in worldline scope.",
        },
    )
    valid_profile_action = client.post(
        f"/worlds/{world_id}/moderation/actions",
        json={
            "worldline_id": str(worldline_id),
            "action_kind": "note_only",
            "target_ref_kind": "player_profile",
            "target_ref_id": str(player_profile_id),
            "reason": "Player report targets an existing profile.",
        },
    )

    assert missing_publication_report.status_code == 404
    assert cross_worldline_publication_report.status_code == 404
    assert valid_publication_report.status_code == 201
    assert missing_scene_action.status_code == 404
    assert cross_world_scene_action.status_code == 404
    assert valid_scene_action.status_code == 201
    assert missing_profile_action.status_code == 404
    assert cross_worldline_profile_action.status_code == 404
    assert valid_profile_action.status_code == 201


def test_moderation_action_is_audited_without_automatic_execution_or_provider_secret_leak() -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test", platform_admin=True)
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id, worldline_id = _seed_world_graph(engine, admin_id)
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    provider_id = _seed_provider(engine, world_id)
    global_provider_id = _seed_provider(engine, None, key="global-provider")
    before_events = _count_rows(engine, WorldEventModel)

    _authenticate(client, member_token)
    member_action = client.post(
        f"/worlds/{world_id}/moderation/actions",
        json={
            "action_kind": "disable_provider",
            "target_ref_kind": "provider_integration",
            "target_ref_id": str(provider_id),
            "reason": "Provider behavior needs review.",
        },
    )

    _authenticate(client, admin_token)
    created = client.post(
        f"/worlds/{world_id}/moderation/actions",
        json={
            "worldline_id": str(worldline_id),
            "action_kind": "disable_provider",
            "status": "applied",
            "target_ref_kind": "provider_integration",
            "target_ref_id": str(provider_id),
            "reason": "Disable after review.",
            "review_note": "Reviewed by admin.",
            "evidence_refs": [
                {
                    "kind": "provider_integration",
                    "id": str(provider_id),
                    "component": "provider",
                    "status": "watch",
                    "reason_code": "reader_report",
                    "world_id": str(world_id),
                    "worldline_id": str(worldline_id),
                }
            ],
            "metadata": {"auth_ref": "env:OPENAI_API_KEY", "api_key": "secret-value"},
        },
    )
    global_provider_action = client.post(
        f"/worlds/{world_id}/moderation/actions",
        json={
            "action_kind": "disable_provider",
            "target_ref_kind": "provider_integration",
            "target_ref_id": str(global_provider_id),
            "reason": "Global provider needs platform review.",
        },
    )
    listed = client.get(f"/worlds/{world_id}/moderation/actions")

    assert member_action.status_code == 403
    assert created.status_code == 201
    body = created.json()
    assert body["audit_summary"]["automatic_execution"] is False
    assert body["audit_summary"]["provider_execution"] is False
    assert body["audit_summary"]["daemon_execution"] is False
    assert body["audit_summary"]["world_event_writes"] is False
    assert "auth_ref" not in body["metadata"]
    assert "api_key" not in body["metadata"]
    assert global_provider_action.status_code == 201
    assert listed.status_code == 200
    assert _count_rows(engine, WorldEventModel) == before_events
    _assert_provider_status(engine, provider_id, "active")
    _assert_no_forbidden_markers(body)
    _assert_no_forbidden_markers(listed.json())


def test_moderation_incident_groups_reports_and_actions_safely() -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test", platform_admin=True)
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id, worldline_id = _seed_world_graph(engine, admin_id)
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    target_id = _seed_conversation(engine, world_id, worldline_id)

    _authenticate(client, member_token)
    report = client.post(
        f"/worlds/{world_id}/moderation/reports",
        json=_report_payload(worldline_id, target_id),
    )

    _authenticate(client, admin_token)
    action = client.post(
        f"/worlds/{world_id}/moderation/actions",
        json={
            "worldline_id": str(worldline_id),
            "report_id": report.json()["id"],
            "action_kind": "rollback_review",
            "target_ref_kind": "conversation_session",
            "target_ref_id": str(target_id),
            "reason": "Needs rollback review only.",
        },
    )
    incident = client.post(
        f"/worlds/{world_id}/moderation/incidents",
        json={
            "worldline_id": str(worldline_id),
            "severity": "high",
            "title": "Playback report cluster",
            "summary": "Grouped public-surface reports.",
            "report_ids": [report.json()["id"]],
            "action_ids": [action.json()["id"]],
        },
    )
    reviewed = client.patch(
        f"/worlds/{world_id}/moderation/incidents/{incident.json()['id']}",
        json={"status": "mitigated", "review_note": "Reviewed and mitigated."},
    )

    assert report.status_code == 201
    assert action.status_code == 201
    assert action.json()["audit_summary"]["destructive_rollback"] is False
    assert incident.status_code == 201
    assert incident.json()["report_ids"] == [report.json()["id"]]
    assert incident.json()["action_ids"] == [action.json()["id"]]
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "mitigated"
    _assert_no_forbidden_markers(incident.json())
    _assert_no_forbidden_markers(reviewed.json())


def test_applied_moderation_takedown_hides_reader_media_without_admin_route_change() -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test", platform_admin=True)
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id, worldline_id = _seed_world_graph(engine, admin_id)
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    artifact_id = _seed_published_artifact(engine, world_id, worldline_id)
    asset_id, object_id = _seed_available_asset_with_object(
        engine,
        client.reader_media_storage,
        world_id,
        worldline_id,
    )
    _seed_reference(engine, world_id, worldline_id, asset_id, artifact_id)

    _authenticate(client, member_token)
    before_list = client.get(f"/worlds/{world_id}/reader/media")
    before_download = client.get(_reader_media_download_path(world_id, worldline_id, object_id))

    _authenticate(client, admin_token)
    action = client.post(
        f"/worlds/{world_id}/moderation/actions",
        json={
            "worldline_id": str(worldline_id),
            "action_kind": "disable_media",
            "status": "applied",
            "target_ref_kind": "media_asset",
            "target_ref_id": str(asset_id),
            "reason": "Reviewed takedown.",
        },
    )

    _authenticate(client, member_token)
    after_list = client.get(f"/worlds/{world_id}/reader/media")
    after_detail = client.get(f"/worlds/{world_id}/reader/media/{asset_id}")
    after_download = client.get(_reader_media_download_path(world_id, worldline_id, object_id))

    _authenticate(client, admin_token)
    admin_download = client.get(f"/worlds/{world_id}/media/objects/{object_id}/download")

    assert before_list.status_code == 200
    assert [item["asset_id"] for item in before_list.json()] == [str(asset_id)]
    assert before_download.status_code == 200
    assert action.status_code == 201
    assert action.json()["audit_summary"]["reader_delivery_suppression"] is True
    assert after_list.status_code == 200
    assert after_list.json() == []
    assert after_detail.status_code == 404
    assert after_download.status_code == 404
    assert admin_download.status_code == 200
    assert admin_download.content == b"reader-image"


def test_admin_flags_player_visible_output_with_safe_safety_review() -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test", platform_admin=True)
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id, worldline_id = _seed_world_graph(engine, admin_id)
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    conversation_id = _seed_conversation(engine, world_id, worldline_id)
    before_events = _count_rows(engine, WorldEventModel)
    payload = {
        "worldline_id": str(worldline_id),
        "target_ref_kind": "conversation_session",
        "target_ref_id": str(conversation_id),
        "category": "safety",
        "severity": "high",
        "policy_key": "player_visible_harm",
        "finding": "Character output needs a player-visible safety review.",
        "evidence_refs": [
            {
                "kind": "conversation_session",
                "id": str(conversation_id),
                "component": "reader_playback",
                "status": "flagged",
                "reason_code": "player_visible_harm",
                "world_id": str(world_id),
                "worldline_id": str(worldline_id),
            }
        ],
        "metadata": {
            "safe_note": "review transcript summary",
            "storage_uri": "media://hidden",
            "nested": {"raw_prompt": "hidden"},
        },
    }

    _authenticate(client, member_token)
    member_review = client.post(f"/worlds/{world_id}/moderation/safety-reviews", json=payload)

    _authenticate(client, admin_token)
    created = client.post(f"/worlds/{world_id}/moderation/safety-reviews", json=payload)

    assert member_review.status_code == 403
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "under_review"
    assert body["reporter_user_id"] == str(admin_id)
    assert body["created_by_actor_ref"] == f"user:{admin_id}"
    assert body["target_ref_kind"] == "conversation_session"
    assert body["metadata"] == {
        "source": "safety_review",
        "policy_key": "player_visible_harm",
        "safe_note": "review transcript summary",
        "nested": {},
    }
    assert body["evidence_refs"][0]["component"] == "moderation_safety_review"
    assert body["evidence_refs"][0]["kind"] == "conversation_session"
    assert _count_rows(engine, WorldEventModel) == before_events
    _assert_no_forbidden_markers(body)


def test_beta_feedback_escalates_to_moderation_without_reporter_leak_to_testers() -> None:
    client, engine = _client_with_database()
    admin_id, admin_token = _seed_user(engine, "admin@example.test", platform_admin=True)
    reporter_id, reporter_token = _seed_user(engine, "reporter@example.test")
    other_id, other_token = _seed_user(engine, "other@example.test")
    world_id, worldline_id = _seed_world_graph(engine, admin_id)
    _add_membership(engine, world_id, admin_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, reporter_id, AuthRole.HUMAN_USER)
    _add_membership(engine, world_id, other_id, AuthRole.HUMAN_USER)
    feedback_id = _seed_beta_feedback(engine, world_id, worldline_id, reporter_id)
    before_events = _count_rows(engine, WorldEventModel)

    _authenticate(client, other_token)
    other_feedback_list = client.get(f"/worlds/{world_id}/beta-feedback/reports")
    other_feedback_detail = client.get(f"/worlds/{world_id}/beta-feedback/reports/{feedback_id}")
    other_moderation_list = client.get(f"/worlds/{world_id}/moderation/reports")

    _authenticate(client, reporter_token)
    reporter_feedback_detail = client.get(f"/worlds/{world_id}/beta-feedback/reports/{feedback_id}")

    _authenticate(client, admin_token)
    escalated = client.post(
        f"/worlds/{world_id}/moderation/feedback-escalations",
        json={
            "feedback_report_id": str(feedback_id),
            "category": "safety",
            "severity": "critical",
            "reason": "Escalate player-visible harm report.",
            "evidence_refs": [
                {
                    "kind": "beta_feedback_report",
                    "id": str(feedback_id),
                    "component": "beta_feedback",
                    "status": "submitted",
                    "reason_code": "player_visible_harm",
                    "world_id": str(world_id),
                    "worldline_id": str(worldline_id),
                }
            ],
            "metadata": {
                "safe_note": "triage with moderation",
                "api_key": "secret-value",
                "storage_uri": "media://hidden",
            },
        },
    )
    admin_reports = client.get(f"/worlds/{world_id}/moderation/reports")

    assert other_feedback_list.status_code == 200
    assert other_feedback_list.json() == []
    assert other_feedback_detail.status_code == 404
    assert other_moderation_list.status_code == 403
    assert reporter_feedback_detail.status_code == 200
    assert reporter_feedback_detail.json()["reporter_user_id"] == str(reporter_id)
    assert escalated.status_code == 201
    body = escalated.json()
    assert body["status"] == "escalated"
    assert body["reporter_user_id"] == str(reporter_id)
    assert body["created_by_actor_ref"] == f"user:{admin_id}"
    assert body["metadata"] == {
        "source": "beta_feedback_escalation",
        "feedback_report_id": str(feedback_id),
        "feedback_issue_type": "playback",
        "safe_note": "triage with moderation",
    }
    assert body["evidence_refs"][-1]["component"] == "beta_feedback"
    assert admin_reports.status_code == 200
    assert [item["id"] for item in admin_reports.json()] == [body["id"]]
    _assert_feedback_linked_to_moderation(engine, feedback_id, uuid.UUID(body["id"]))
    assert _count_rows(engine, WorldEventModel) == before_events
    _assert_no_forbidden_markers(body)
    _assert_no_forbidden_markers(admin_reports.json())


def _report_payload(worldline_id: uuid.UUID, target_id: uuid.UUID) -> dict[str, Any]:
    return {
        "worldline_id": str(worldline_id),
        "target_ref_kind": "conversation_session",
        "target_ref_id": str(target_id),
        "category": "safety",
        "severity": "medium",
        "reason": "Reader-visible content needs moderation review.",
        "reporter_note": "This should be checked.",
        "evidence_refs": [
            {
                "kind": "conversation_session",
                "id": str(target_id),
                "component": "reader_playback",
                "status": "watch",
                "reason_code": "reader_report",
                "worldline_id": str(worldline_id),
            }
        ],
        "metadata": {
            "client_note": "safe",
            "rawPrompt": "hidden moderation prompt",
            "promptSnapshotId": str(uuid.uuid4()),
            "nested": {
                "rawOutput": "hidden moderation output",
                "storageUri": "opaque-moderation-storage",
                "safe": "kept",
            },
        },
    }


class _ModerationApiClient(TestClient):
    reader_media_storage: LocalMediaObjectStorage


def _client_with_database() -> tuple[_ModerationApiClient, Engine]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    _create_required_tables(engine)

    def override_session() -> Iterator[Session]:
        session = Session(engine)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[get_db_session] = override_session
    storage_tmp = TemporaryDirectory()
    storage = LocalMediaObjectStorage(Path(storage_tmp.name))
    app.dependency_overrides[_reader_media_storage] = lambda: storage
    app.dependency_overrides[_media_storage] = lambda: storage
    app.state._moderation_storage_tmp = storage_tmp
    client = _ModerationApiClient(app)
    client.reader_media_storage = storage
    return client, engine


def _create_required_tables(engine: Engine) -> None:
    for table in (
        cast(Table, User.__table__),
        cast(Table, AuthSession.__table__),
        cast(Table, PlatformRoleAssignment.__table__),
        cast(Table, World.__table__),
        cast(Table, Worldline.__table__),
        cast(Table, WorldMembership.__table__),
        cast(Table, Scene.__table__),
        cast(Table, ConversationSession.__table__),
        cast(Table, PlayerActorProfile.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, ProviderIntegration.__table__),
        cast(Table, NarrativeArtifact.__table__),
        cast(Table, NarrativePublication.__table__),
        cast(Table, MediaAsset.__table__),
        cast(Table, MediaObject.__table__),
        cast(Table, MediaReference.__table__),
        cast(Table, BetaFeedbackReport.__table__),
        cast(Table, ModerationReport.__table__),
        cast(Table, ModerationIncident.__table__),
        cast(Table, ModerationAction.__table__),
    ):
        table.create(engine)


def _seed_user(
    engine: Engine,
    email: str,
    *,
    platform_admin: bool = False,
) -> tuple[uuid.UUID, str]:
    user_id = uuid.uuid4()
    token = f"token-{user_id}"
    now = datetime.now(UTC)
    with Session(engine) as session:
        session.add(User(id=user_id, email=email, display_name=email.split("@")[0], is_active=True))
        session.add(
            AuthSession(
                id=uuid.uuid4(),
                user_id=user_id,
                token_hash=hash_session_token(token),
                status=AuthSessionStatus.ACTIVE.value,
                expires_at=now + timedelta(hours=1),
            )
        )
        if platform_admin:
            session.add(
                PlatformRoleAssignment(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    role=AuthRole.PLATFORM_ADMIN.value,
                    assigned_at=now,
                )
            )
        session.commit()
    return user_id, token


def _seed_world_graph(
    engine: Engine,
    owner_id: uuid.UUID,
    *,
    slug: str = "moderation-world",
) -> tuple[uuid.UUID, uuid.UUID]:
    world_id = uuid.uuid4()
    worldline_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            World(
                id=world_id,
                owner_user_id=owner_id,
                slug=slug,
                name=slug,
                rules_config={},
                is_active=True,
            )
        )
        session.add(
            Worldline(
                id=worldline_id,
                world_id=world_id,
                worldline_key="primary",
                name="Primary",
                status="active",
                created_by_actor_ref="system:test",
                metadata_json={},
            )
        )
        session.commit()
    return world_id, worldline_id


def _seed_worldline(engine: Engine, world_id: uuid.UUID, key: str) -> uuid.UUID:
    worldline_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            Worldline(
                id=worldline_id,
                world_id=world_id,
                worldline_key=key,
                name=key.title(),
                status="active",
                created_by_actor_ref="system:test",
                metadata_json={},
            )
        )
        session.commit()
    return worldline_id


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
            )
        )
        session.commit()


def _seed_conversation(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
) -> uuid.UUID:
    conversation_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            ConversationSession(
                id=conversation_id,
                world_id=world_id,
                worldline_id=worldline_id,
                scene_id=None,
                session_key=f"conversation-{conversation_id.hex[:8]}",
                title="Reader-visible conversation",
                scope_type="world",
                mode="manual_chain",
                status="completed",
                objective="internal objective",
                opening_prompt="raw prompt should not leak",
                max_turns=4,
                next_turn_index=0,
                policy_config={},
                writer_config={},
                memory_config={},
            )
        )
        session.commit()
    return conversation_id


def _seed_provider(
    engine: Engine,
    world_id: uuid.UUID | None,
    *,
    key: str = "world-provider",
) -> uuid.UUID:
    provider_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            ProviderIntegration(
                id=provider_id,
                world_id=world_id,
                scope_kind="global" if world_id is None else "world",
                scope_key="global" if world_id is None else str(world_id),
                provider_kind="text_generation",
                adapter_kind="fake",
                provider_key=key,
                display_name=key,
                base_url=None,
                auth_ref="env:OPENAI_API_KEY",
                config_json={"safe": True, "api_key": "secret-value"},
                default_params_json={},
                status="active",
                visibility="world_admin",
            )
        )
        session.commit()
    return provider_id


def _seed_scene(engine: Engine, world_id: uuid.UUID) -> uuid.UUID:
    scene_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            Scene(
                id=scene_id,
                world_id=world_id,
                scene_key=f"scene-{scene_id.hex[:8]}",
                name="Moderation scene",
                is_active=True,
            )
        )
        session.commit()
    return scene_id


def _seed_player_profile(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    user_id: uuid.UUID,
) -> uuid.UUID:
    profile_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            PlayerActorProfile(
                id=profile_id,
                world_id=world_id,
                worldline_id=worldline_id,
                user_id=user_id,
                actor_ref=f"player:{user_id}",
                display_name="Moderation Player",
                profile_json={},
                is_active=True,
            )
        )
        session.commit()
    return profile_id


def _seed_publication(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
) -> uuid.UUID:
    publication_id = uuid.uuid4()
    artifact_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            NarrativeArtifact(
                id=artifact_id,
                world_id=world_id,
                worldline_id=worldline_id,
                title="Moderation chapter",
                content="Reader-safe content",
                artifact_kind="chapter_draft",
                artifact_metadata={},
            )
        )
        session.add(
            NarrativePublication(
                id=publication_id,
                world_id=world_id,
                worldline_id=worldline_id,
                artifact_id=artifact_id,
                status="published",
                reader_visible=True,
                published_metadata={},
                published_at=datetime.now(UTC),
            )
        )
        session.commit()
    return publication_id


def _seed_published_artifact(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
) -> uuid.UUID:
    artifact_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            NarrativeArtifact(
                id=artifact_id,
                world_id=world_id,
                worldline_id=worldline_id,
                title="Chapter",
                content="Reader-safe content",
                artifact_kind="chapter_draft",
                artifact_metadata={},
            )
        )
        session.add(
            NarrativePublication(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                artifact_id=artifact_id,
                status="published",
                reader_visible=True,
                published_metadata={},
                published_at=datetime.now(UTC),
            )
        )
        session.commit()
    return artifact_id


def _seed_available_asset_with_object(
    engine: Engine,
    storage: LocalMediaObjectStorage,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
) -> tuple[uuid.UUID, uuid.UUID]:
    asset_id = uuid.uuid4()
    object_id = uuid.uuid4()
    stored = storage.write_bytes(
        f"worlds/{world_id}/worldlines/{worldline_id}/assets/{asset_id}/reader.png",
        b"reader-image",
        content_type="image/png",
    )
    with Session(engine) as session:
        session.add(
            MediaAsset(
                id=asset_id,
                world_id=world_id,
                worldline_id=worldline_id,
                asset_kind="image",
                asset_role="reference_image",
                source_kind="manual_upload",
                status="available",
                visibility="reader_visible",
                storage_uri=stored.uri,
                mime_type="image/png",
                size_bytes=stored.size_bytes,
                checksum_sha256=stored.checksum_sha256,
                created_by_actor_ref="test",
                title="Reader image",
                metadata_json={},
            )
        )
        session.add(
            MediaObject(
                id=object_id,
                asset_id=asset_id,
                world_id=world_id,
                worldline_id=worldline_id,
                object_role="original",
                storage_uri=stored.uri,
                filename="reader.png",
                mime_type="image/png",
                size_bytes=stored.size_bytes,
                checksum_sha256=stored.checksum_sha256,
                width=100,
                height=100,
                metadata_json={},
            )
        )
        session.commit()
    return asset_id, object_id


def _seed_reference(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    asset_id: uuid.UUID,
    artifact_id: uuid.UUID,
) -> None:
    with Session(engine) as session:
        session.add(
            MediaReference(
                id=uuid.uuid4(),
                world_id=world_id,
                worldline_id=worldline_id,
                asset_id=asset_id,
                ref_kind="narrative_artifact",
                ref_id=artifact_id,
                ref_role="attachment",
                display_order=0,
                metadata_json={},
            )
        )
        session.commit()


def _seed_beta_feedback(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    reporter_id: uuid.UUID,
) -> uuid.UUID:
    feedback_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            BetaFeedbackReport(
                id=feedback_id,
                world_id=world_id,
                worldline_id=worldline_id,
                reporter_user_id=reporter_id,
                player_actor_id=None,
                issue_type="playback",
                severity="high",
                status="submitted",
                title="Unsafe playback moment",
                description="Player-visible playback needs moderation review.",
                reporter_note="Reporter private note.",
                evidence_refs_json=[
                    {
                        "kind": "worldline",
                        "id": str(worldline_id),
                        "worldline_id": str(worldline_id),
                        "label": "safe feedback ref",
                    }
                ],
                repair_proposal_refs_json=[],
                metadata_json={"safe": True},
            )
        )
        session.commit()
    return feedback_id


def _reader_media_download_path(
    world_id: uuid.UUID, worldline_id: uuid.UUID, object_id: uuid.UUID
) -> str:
    return (
        f"/worlds/{world_id}/reader/media/worldlines/"
        f"{worldline_id}/objects/{object_id}/download"
    )


def _authenticate(client: TestClient, token: str) -> None:
    client.cookies.clear()
    client.headers.clear()
    client.cookies.set(SESSION_COOKIE_NAME, token)
    client.cookies.set(CSRF_COOKIE_NAME, "csrf-token")
    client.headers.update({CSRF_HEADER_NAME: "csrf-token"})


def _authenticate_without_csrf(client: TestClient, token: str) -> None:
    client.cookies.clear()
    client.headers.clear()
    client.cookies.set(SESSION_COOKIE_NAME, token)


def _count_rows(engine: Engine, model: type[Any]) -> int:
    with Session(engine) as session:
        return session.scalar(select(func.count(model.id))) or 0


def _assert_provider_status(engine: Engine, provider_id: uuid.UUID, status: str) -> None:
    with Session(engine) as session:
        provider = session.get(ProviderIntegration, provider_id)
        assert provider is not None
        assert provider.status == status


def _assert_feedback_linked_to_moderation(
    engine: Engine,
    feedback_id: uuid.UUID,
    report_id: uuid.UUID,
) -> None:
    with Session(engine) as session:
        feedback = session.get(BetaFeedbackReport, feedback_id)
        assert feedback is not None
        assert feedback.moderation_report_id == report_id
        assert feedback.status == "investigating"
        assert feedback.triaged_by_actor_ref is not None
        assert feedback.triaged_at is not None


def _assert_no_forbidden_markers(value: object) -> None:
    serialized = json.dumps(value, sort_keys=True).lower()
    for marker in FORBIDDEN_MARKERS:
        assert marker.lower() not in serialized
