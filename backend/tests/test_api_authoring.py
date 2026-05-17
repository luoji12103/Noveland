from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
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
    AuthoringReviewDecision,
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
from noveland.events.models import WorldEventModel
from noveland.invocations.models import ModelInvocation, PromptSnapshot
from noveland.media.models import MediaAsset, MediaJob, MediaObject
from noveland.media.storage import LocalMediaObjectStorage
from noveland.memory.models import AgentMemoryItem
from noveland.providers.contracts import (
    ProviderAdapterKind,
    ProviderIntegrationCreate,
    ProviderKind,
    ProviderScopeKind,
)
from noveland.providers.models import ProviderBudgetPolicy, ProviderCapability, ProviderIntegration
from noveland.providers.registry import ProviderRegistryService
from noveland.services.api.app import create_app
from noveland.services.api.authoring import _authoring_media_storage
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
from noveland.worlds.models import World, Worldline, WorldMembership
from noveland.worlds.worldlines import ensure_primary_worldline
from sqlalchemy import Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


class _AuthoringApiClient(TestClient):
    authoring_storage: LocalMediaObjectStorage


def test_authoring_api_source_preview_review_and_apply() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id = _seed_world(engine, owner_id)
    worldline_id = _seed_worldline(engine, world_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)

    _authenticate(client, member_token)
    forbidden = client.post(
        f"/worlds/{world_id}/authoring/source-batches",
        json={
            "worldline_id": str(worldline_id),
            "batch_key": "script-1",
            "display_name": "Script 1",
        },
    )

    _authenticate(client, owner_token)
    batch = client.post(
        f"/worlds/{world_id}/authoring/source-batches",
        json={
            "worldline_id": str(worldline_id),
            "batch_key": "script-1",
            "display_name": "Script 1",
            "source_kind": "script",
        },
    )
    listed_batches = client.get(
        f"/worlds/{world_id}/authoring/source-batches",
        params={"worldline_id": str(worldline_id)},
    )
    asset = client.post(
        f"/worlds/{world_id}/authoring/source-batches/{batch.json()['id']}/assets",
        json={
            "worldline_id": str(worldline_id),
            "source_asset_kind": "script",
            "source_label": "script.ks",
        },
    )
    fragment = client.post(
        f"/worlds/{world_id}/authoring/source-assets/{asset.json()['id']}/fragments",
        json={
            "worldline_id": str(worldline_id),
            "fragment_key": "line-1",
            "fragment_kind": "dialogue",
            "sequence": 1,
            "excerpt_text": "Alice: hello",
        },
    )
    run = client.post(
        f"/worlds/{world_id}/authoring/import-runs",
        json={
            "worldline_id": str(worldline_id),
            "source_batch_id": batch.json()["id"],
        },
    )
    preview = client.post(
        f"/worlds/{world_id}/authoring/import-runs/{run.json()['id']}/preview",
        json={
            "worldline_id": str(worldline_id),
            "proposals": [
                {
                    "source_fragment_id": fragment.json()["id"],
                    "proposal_kind": "other",
                    "title": "Trace note",
                    "summary": "Trace only.",
                    "proposed_payload_json": {"note": "safe"},
                }
            ],
        },
    )
    proposal_id = preview.json()["run"]["proposals"][0]["id"]
    review = client.post(
        f"/worlds/{world_id}/authoring/proposals/{proposal_id}/review",
        json={"decision": "approve", "reason": "safe trace-only apply"},
    )
    apply = client.post(
        f"/worlds/{world_id}/authoring/import-runs/{run.json()['id']}/apply",
        json={"worldline_id": str(worldline_id), "proposal_ids": [proposal_id]},
    )
    leaky = client.post(
        f"/worlds/{world_id}/authoring/source-batches",
        json={
            "worldline_id": str(worldline_id),
            "batch_key": "bad",
            "display_name": "Bad",
            "metadata_json": {"storage_uri": "local://leak"},
        },
    )

    assert forbidden.status_code == 403
    assert batch.status_code == 201
    assert listed_batches.status_code == 200
    assert len(listed_batches.json()) == 1
    assert asset.status_code == 201
    assert fragment.status_code == 201
    assert run.status_code == 201
    assert preview.status_code == 201
    assert preview.json()["run"]["summary_json"]["provider_execution"] is False
    assert review.status_code == 201
    assert apply.status_code == 201
    assert apply.json()["applied_proposals"][0]["status"] == "applied"
    assert leaky.status_code == 422
    assert "storage_uri" not in str(preview.json()).lower()
    assert "storage_uri" not in str(apply.json()).lower()

    with Session(engine) as session:
        assert session.scalars(select(WorldEventModel)).all() == []


def test_authoring_api_galgame_source_intake_preview_and_apply(
    tmp_path: Path,
) -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id = _seed_world(engine, owner_id)
    worldline_id = _seed_worldline(engine, world_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    source_dir = _galgame_source_dir(tmp_path)

    body = {
        "worldline_id": str(worldline_id),
        "source_directory": str(source_dir),
        "batch_key": "demo-galgame",
        "display_name": "Demo Galgame",
        "max_text_fragment_chars": 200,
    }
    _authenticate(client, member_token)
    forbidden = client.post(
        f"/worlds/{world_id}/authoring/galgame-source-intake/preview",
        json=body,
    )
    _authenticate(client, owner_token)
    preview = client.post(
        f"/worlds/{world_id}/authoring/galgame-source-intake/preview",
        json=body,
    )
    missing_confirmation = client.post(
        f"/worlds/{world_id}/authoring/galgame-source-intake/apply",
        json=body,
    )
    apply = client.post(
        f"/worlds/{world_id}/authoring/galgame-source-intake/apply",
        json={**body, "confirm_already_unpacked_user_provided": True},
    )

    assert forbidden.status_code == 403
    assert preview.status_code == 201
    assert preview.json()["accepted_count"] == 9
    assert preview.json()["rejected_count"] == 2
    assert preview.json()["media_file_count"] == 6
    assert preview.json()["text_file_count"] == 3
    assert preview.json()["provider_execution"] is False
    assert preview.json()["canon_mutation"] is False
    assert missing_confirmation.status_code == 422
    assert apply.status_code == 201
    assert len(apply.json()["media_asset_ids"]) == 6
    assert len(apply.json()["source_assets"]) == 9
    assert apply.json()["batch"]["metadata_json"]["source_type"] == "already_unpacked_galgame"
    assert apply.json()["run"]["summary_json"]["canon_mutation"] is False
    assert str(source_dir) not in _json_text(preview.json())
    assert str(source_dir) not in _json_text(apply.json())
    for forbidden_marker in ("storage_uri", "file://", "local://", "base64", "raw_prompt"):
        assert forbidden_marker not in _json_text(preview.json())
        assert forbidden_marker not in _json_text(apply.json())

    with Session(engine) as session:
        imported = session.scalars(
            select(MediaAsset).where(MediaAsset.source_kind == "imported_original")
        ).all()
        assert len(imported) == 6
        assert len(session.scalars(select(MediaObject)).all()) == 6
        assert len(session.scalars(select(AuthoringSourceBatch)).all()) == 1
        assert len(session.scalars(select(AuthoringSourceAsset)).all()) == 9
        assert len(session.scalars(select(AuthoringSourceFragment)).all()) >= 3
        assert session.scalars(select(WorldEventModel)).all() == []


def test_authoring_api_script_parse_endpoint() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id = _seed_world(engine, owner_id)
    worldline_id = _seed_worldline(engine, world_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)

    _authenticate(client, owner_token)
    batch = client.post(
        f"/worlds/{world_id}/authoring/source-batches",
        json={
            "worldline_id": str(worldline_id),
            "batch_key": "script-parse",
            "display_name": "Script Parse",
            "source_kind": "script",
        },
    )
    asset = client.post(
        f"/worlds/{world_id}/authoring/source-batches/{batch.json()['id']}/assets",
        json={
            "worldline_id": str(worldline_id),
            "source_asset_kind": "script",
            "source_label": "script.ks",
        },
    )
    fragment = client.post(
        f"/worlds/{world_id}/authoring/source-assets/{asset.json()['id']}/fragments",
        json={
            "worldline_id": str(worldline_id),
            "fragment_key": "scene-1",
            "fragment_kind": "scene",
            "sequence": 1,
            "excerpt_text": (
                "Hero: hello\n"
                "「whispered line」\n"
                "[scene: schoolyard]\n"
                "choice: leave with him\n"
                "-> stay\n"
                "[route: branch_a]\n"
                "[event: encounter]\n"
                "[emotion: happy]\n"
                "[relationship: Hero -> Alice: trust]\n"
                "@unknown_macro heroine pose=smile\n"
            ),
        },
    )
    run = client.post(
        f"/worlds/{world_id}/authoring/import-runs",
        json={
            "worldline_id": str(worldline_id),
            "source_batch_id": batch.json()["id"],
        },
    )
    parsed = client.post(
        f"/worlds/{world_id}/authoring/import-runs/{run.json()['id']}/parse-script",
        json={
            "worldline_id": str(worldline_id),
            "source_fragment_ids": [fragment.json()["id"]],
        },
    )

    assert parsed.status_code == 201
    assert parsed.json()["created_proposal_count"] == 10
    assert parsed.json()["dialogue_count"] == 2
    assert parsed.json()["scene_count"] == 1
    assert parsed.json()["choice_count"] == 2
    assert parsed.json()["route_count"] == 1
    assert parsed.json()["event_count"] == 1
    assert parsed.json()["emotion_hint_count"] == 1
    assert parsed.json()["relationship_hint_count"] == 1
    assert parsed.json()["manual_label_count"] == 1
    assert parsed.json()["unresolved_speaker_count"] == 2
    assert parsed.json()["run"]["summary_json"]["provider_execution"] is False
    assert all(
        proposal["source_fragment_id"] == fragment.json()["id"]
        for proposal in parsed.json()["run"]["proposals"]
    )
    proposals_by_kind = {
        proposal["target_ref_kind"]: proposal
        for proposal in parsed.json()["run"]["proposals"]
    }
    dialogue = next(
        proposal
        for proposal in parsed.json()["run"]["proposals"]
        if proposal["target_ref_kind"] == "dialogue_candidate"
        and proposal["proposed_payload_json"].get("speaker_label") == "hero"
    )
    assert dialogue["proposed_payload_json"]["line_text"] == "hello"
    assert (
        proposals_by_kind["manual_label_candidate"]["proposed_payload_json"][
            "label_status"
        ]
        == "needs_review"
    )
    assert "storage_uri" not in _json_text(parsed.json())

    with Session(engine) as session:
        assert len(session.scalars(select(AuthoringSourceTraceability)).all()) == 10
        assert session.scalars(select(WorldEventModel)).all() == []


def test_authoring_api_character_extract_endpoint() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id = _seed_world(engine, owner_id)
    worldline_id = _seed_worldline(engine, world_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)

    _authenticate(client, owner_token)
    batch = client.post(
        f"/worlds/{world_id}/authoring/source-batches",
        json={
            "worldline_id": str(worldline_id),
            "batch_key": "characters",
            "display_name": "Characters",
            "source_kind": "character_sheet",
        },
    )
    asset = client.post(
        f"/worlds/{world_id}/authoring/source-batches/{batch.json()['id']}/assets",
        json={
            "worldline_id": str(worldline_id),
            "source_asset_kind": "character_sheet",
            "source_label": "characters.md",
        },
    )
    fragment = client.post(
        f"/worlds/{world_id}/authoring/source-assets/{asset.json()['id']}/fragments",
        json={
            "worldline_id": str(worldline_id),
            "fragment_key": "characters",
            "fragment_kind": "character",
            "sequence": 1,
            "excerpt_text": (
                "character: Alice\n"
                "alias: Alice -> Al\n"
                "Alice trusts Bob\n"
                "faction: Student Council\n"
                "identity: Alice = prefect\n"
                "emotion: Alice = guarded\n"
            ),
        },
    )
    run = client.post(
        f"/worlds/{world_id}/authoring/import-runs",
        json={
            "worldline_id": str(worldline_id),
            "source_batch_id": batch.json()["id"],
        },
    )
    extracted = client.post(
        f"/worlds/{world_id}/authoring/import-runs/{run.json()['id']}/extract-characters",
        json={
            "worldline_id": str(worldline_id),
            "source_fragment_ids": [fragment.json()["id"]],
        },
    )

    assert extracted.status_code == 201
    assert extracted.json()["created_proposal_count"] == 6
    assert extracted.json()["character_count"] == 1
    assert extracted.json()["relationship_count"] == 1
    assert extracted.json()["alias_count"] == 1
    assert extracted.json()["faction_count"] == 1
    assert extracted.json()["identity_count"] == 1
    assert extracted.json()["emotional_baseline_count"] == 1
    assert extracted.json()["run"]["summary_json"]["provider_execution"] is False
    assert all(
        proposal["source_fragment_id"] == fragment.json()["id"]
        for proposal in extracted.json()["run"]["proposals"]
    )
    assert "storage_uri" not in _json_text(extracted.json())

    with Session(engine) as session:
        assert len(session.scalars(select(AuthoringSourceTraceability)).all()) == 6
        assert session.scalars(select(WorldEventModel)).all() == []


def test_authoring_api_lore_extract_endpoint() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id = _seed_world(engine, owner_id)
    worldline_id = _seed_worldline(engine, world_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)

    _authenticate(client, owner_token)
    batch = client.post(
        f"/worlds/{world_id}/authoring/source-batches",
        json={
            "worldline_id": str(worldline_id),
            "batch_key": "lore",
            "display_name": "Lore",
            "source_kind": "lore",
        },
    )
    asset = client.post(
        f"/worlds/{world_id}/authoring/source-batches/{batch.json()['id']}/assets",
        json={
            "worldline_id": str(worldline_id),
            "source_asset_kind": "lore",
            "source_label": "lore.md",
        },
    )
    fragment = client.post(
        f"/worlds/{world_id}/authoring/source-assets/{asset.json()['id']}/fragments",
        json={
            "worldline_id": str(worldline_id),
            "fragment_key": "lore",
            "fragment_kind": "lore",
            "sequence": 1,
            "excerpt_text": (
                "canon: The city sleeps at noon\n"
                "uncertain: The gate may be alive\n"
                "location: Old Gate\n"
                "organization: Student Council\n"
                "rule: Wishes require payment\n"
                "secret: Alice is heir\n"
                "knowledge: Alice -> Alice is heir\n"
            ),
        },
    )
    run = client.post(
        f"/worlds/{world_id}/authoring/import-runs",
        json={
            "worldline_id": str(worldline_id),
            "source_batch_id": batch.json()["id"],
        },
    )
    extracted = client.post(
        f"/worlds/{world_id}/authoring/import-runs/{run.json()['id']}/extract-lore",
        json={
            "worldline_id": str(worldline_id),
            "source_fragment_ids": [fragment.json()["id"]],
        },
    )

    assert extracted.status_code == 201
    assert extracted.json()["created_proposal_count"] == 7
    assert extracted.json()["lore_count"] == 2
    assert extracted.json()["location_count"] == 1
    assert extracted.json()["organization_count"] == 1
    assert extracted.json()["world_rule_count"] == 1
    assert extracted.json()["secret_count"] == 1
    assert extracted.json()["knowledge_boundary_count"] == 1
    assert extracted.json()["uncertain_count"] == 1
    assert extracted.json()["run"]["summary_json"]["provider_execution"] is False
    assert all(
        proposal["source_fragment_id"] == fragment.json()["id"]
        for proposal in extracted.json()["run"]["proposals"]
    )
    assert "storage_uri" not in _json_text(extracted.json())

    with Session(engine) as session:
        assert len(session.scalars(select(AuthoringSourceTraceability)).all()) == 7
        assert session.scalars(select(WorldEventModel)).all() == []


def test_authoring_api_conflict_review_endpoint() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id = _seed_world(engine, owner_id)
    worldline_id = _seed_worldline(engine, world_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)

    _authenticate(client, owner_token)
    batch = client.post(
        f"/worlds/{world_id}/authoring/source-batches",
        json={
            "worldline_id": str(worldline_id),
            "batch_key": "conflicts",
            "display_name": "Conflicts",
            "source_kind": "character_sheet",
        },
    )
    asset = client.post(
        f"/worlds/{world_id}/authoring/source-batches/{batch.json()['id']}/assets",
        json={
            "worldline_id": str(worldline_id),
            "source_asset_kind": "character_sheet",
            "source_label": "conflicts.md",
        },
    )
    fragment = client.post(
        f"/worlds/{world_id}/authoring/source-assets/{asset.json()['id']}/fragments",
        json={
            "worldline_id": str(worldline_id),
            "fragment_key": "conflicts",
            "fragment_kind": "character",
            "sequence": 1,
            "excerpt_text": "conflict fixture",
        },
    )
    run = client.post(
        f"/worlds/{world_id}/authoring/import-runs",
        json={
            "worldline_id": str(worldline_id),
            "source_batch_id": batch.json()["id"],
        },
    )
    preview = client.post(
        f"/worlds/{world_id}/authoring/import-runs/{run.json()['id']}/preview",
        json={
            "worldline_id": str(worldline_id),
            "proposals": [
                {
                    "source_fragment_id": fragment.json()["id"],
                    "proposal_kind": "character",
                    "target_ref_kind": "character_candidate",
                    "title": "Alice",
                    "summary": "Alice candidate.",
                    "proposed_payload_json": {
                        "candidate_kind": "character",
                        "character_label": "Alice",
                    },
                },
                {
                    "source_fragment_id": fragment.json()["id"],
                    "proposal_kind": "character",
                    "target_ref_kind": "character_candidate",
                    "title": "Alice duplicate",
                    "summary": "Alice duplicate candidate.",
                    "proposed_payload_json": {
                        "candidate_kind": "character",
                        "character_label": "Alice",
                    },
                },
            ],
        },
    )
    reviewed = client.post(
        f"/worlds/{world_id}/authoring/import-runs/{run.json()['id']}/review-conflicts",
        json={"worldline_id": str(worldline_id)},
    )

    assert preview.status_code == 201
    assert reviewed.status_code == 201
    assert reviewed.json()["created_proposal_count"] == 1
    assert reviewed.json()["duplicate_count"] == 1
    assert reviewed.json()["contradiction_count"] == 0
    assert reviewed.json()["run"]["summary_json"]["provider_execution"] is False
    reports = [
        proposal
        for proposal in reviewed.json()["run"]["proposals"]
        if proposal["target_ref_kind"] == "canon_conflict_report"
    ]
    assert len(reports) == 1
    assert reports[0]["proposal_kind"] == "other"
    assert "storage_uri" not in _json_text(reviewed.json())

    with Session(engine) as session:
        assert len(session.scalars(select(AuthoringSourceTraceability)).all()) == 3
        assert session.scalars(select(WorldEventModel)).all() == []


def test_authoring_api_memory_migration_endpoint() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id = _seed_world(engine, owner_id)
    worldline_id = _seed_worldline(engine, world_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)

    _authenticate(client, owner_token)
    batch = client.post(
        f"/worlds/{world_id}/authoring/source-batches",
        json={
            "worldline_id": str(worldline_id),
            "batch_key": "memory",
            "display_name": "Memory",
            "source_kind": "lore",
        },
    )
    asset = client.post(
        f"/worlds/{world_id}/authoring/source-batches/{batch.json()['id']}/assets",
        json={
            "worldline_id": str(worldline_id),
            "source_asset_kind": "lore",
            "source_label": "memory.md",
        },
    )
    fragment = client.post(
        f"/worlds/{world_id}/authoring/source-assets/{asset.json()['id']}/fragments",
        json={
            "worldline_id": str(worldline_id),
            "fragment_key": "memory",
            "fragment_kind": "memory",
            "sequence": 1,
            "excerpt_text": (
                "fact: Magic exists\n"
                "episodic: Alice met Bob\n"
                "Alice likes tea\n"
            ),
        },
    )
    run = client.post(
        f"/worlds/{world_id}/authoring/import-runs",
        json={
            "worldline_id": str(worldline_id),
            "source_batch_id": batch.json()["id"],
        },
    )
    migrated = client.post(
        f"/worlds/{world_id}/authoring/import-runs/{run.json()['id']}/migrate-memory",
        json={
            "worldline_id": str(worldline_id),
            "source_fragment_ids": [fragment.json()["id"]],
        },
    )

    assert migrated.status_code == 201
    assert migrated.json()["created_proposal_count"] == 3
    assert migrated.json()["fact_count"] == 1
    assert migrated.json()["episodic_count"] == 1
    assert migrated.json()["relationship_count"] == 0
    assert migrated.json()["preference_count"] == 1
    assert migrated.json()["style_count"] == 0
    assert migrated.json()["run"]["summary_json"]["provider_execution"] is False
    assert all(
        proposal["source_fragment_id"] == fragment.json()["id"]
        for proposal in migrated.json()["run"]["proposals"]
    )
    assert "storage_uri" not in _json_text(migrated.json())

    with Session(engine) as session:
        assert len(session.scalars(select(AuthoringSourceTraceability)).all()) == 3
        assert session.scalars(select(WorldEventModel)).all() == []


def test_authoring_api_character_memory_distillation_endpoint() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id = _seed_world(engine, owner_id)
    worldline_id = _seed_worldline(engine, world_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    agent_id = _seed_agent(engine, world_id, "alice", "Alice")
    provider_id = _seed_text_provider(engine, world_id)

    _authenticate(client, owner_token)
    batch = client.post(
        f"/worlds/{world_id}/authoring/source-batches",
        json={
            "worldline_id": str(worldline_id),
            "batch_key": "alice",
            "display_name": "Alice",
            "source_kind": "character_sheet",
        },
    )
    asset = client.post(
        f"/worlds/{world_id}/authoring/source-batches/{batch.json()['id']}/assets",
        json={
            "worldline_id": str(worldline_id),
            "source_asset_kind": "character_sheet",
            "source_label": "alice.md",
        },
    )
    fragment = client.post(
        f"/worlds/{world_id}/authoring/source-assets/{asset.json()['id']}/fragments",
        json={
            "worldline_id": str(worldline_id),
            "fragment_key": "alice",
            "fragment_kind": "character",
            "sequence": 1,
            "excerpt_text": "Alice: I trust Bob.\npreference: Alice likes tea",
        },
    )
    run = client.post(
        f"/worlds/{world_id}/authoring/import-runs",
        json={
            "worldline_id": str(worldline_id),
            "source_batch_id": batch.json()["id"],
        },
    )
    _authenticate(client, member_token)
    forbidden = client.post(
        f"/worlds/{world_id}/authoring/import-runs/{run.json()['id']}/distill-character-memory",
        json={
            "worldline_id": str(worldline_id),
            "agent_id": str(agent_id),
            "source_fragment_ids": [fragment.json()["id"]],
            "provider_id": str(provider_id),
        },
    )
    _authenticate(client, owner_token)
    distilled = client.post(
        f"/worlds/{world_id}/authoring/import-runs/{run.json()['id']}/distill-character-memory",
        json={
            "worldline_id": str(worldline_id),
            "agent_id": str(agent_id),
            "source_fragment_ids": [fragment.json()["id"]],
            "provider_id": str(provider_id),
            "include_visual_profile_recommendation": True,
        },
    )

    assert forbidden.status_code == 403
    assert distilled.status_code == 201
    assert distilled.json()["provider_execution"] is True
    assert distilled.json()["persona_proposal_count"] == 1
    assert distilled.json()["memory_candidate_count"] >= 1
    assert distilled.json()["visual_profile_recommendation_count"] == 1
    response_text = _json_text(distilled.json())
    for forbidden_marker in (
        "storage_uri",
        "file://",
        "local://",
        "base64",
        "raw_prompt",
        "raw_output",
        "prompt_snapshot",
    ):
        assert forbidden_marker not in response_text

    proposals = distilled.json()["run"]["proposals"]
    proposal_ids = [
        proposal["id"]
        for proposal in proposals
        if proposal["target_ref_kind"]
        in {"agent_persona_candidate", "memory_candidate"}
    ]
    for proposal_id in proposal_ids:
        reviewed = client.post(
            f"/worlds/{world_id}/authoring/proposals/{proposal_id}/review",
            json={"decision": "approve", "reason": "phase 6 apply"},
        )
        assert reviewed.status_code == 201
    applied = client.post(
        f"/worlds/{world_id}/authoring/import-runs/{run.json()['id']}/apply",
        json={"worldline_id": str(worldline_id), "proposal_ids": proposal_ids},
    )
    assert applied.status_code == 201
    assert len(applied.json()["applied_proposals"]) == len(proposal_ids)
    assert applied.json()["blocked_proposals"] == []
    assert "storage_uri" not in _json_text(applied.json())

    with Session(engine) as session:
        assert len(session.scalars(select(ModelInvocation)).all()) == 1
        assert len(session.scalars(select(PromptSnapshot)).all()) == 1
        assert session.scalars(select(AgentPersona)).one().persona_text
        assert session.scalars(select(AgentMemoryItem)).first() is not None
        assert session.scalars(select(WorldEventModel)).all() == []


def test_authoring_api_asset_matching_endpoint() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    world_id = _seed_world(engine, owner_id)
    worldline_id = _seed_worldline(engine, world_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    sprite_media_id = _add_media_asset(
        engine,
        world_id,
        worldline_id,
        asset_kind="image",
        asset_role="character_sprite",
    )
    voice_media_id = _add_media_asset(
        engine,
        world_id,
        worldline_id,
        asset_kind="audio",
        asset_role="voice_sample",
    )

    _authenticate(client, owner_token)
    batch = client.post(
        f"/worlds/{world_id}/authoring/source-batches",
        json={
            "worldline_id": str(worldline_id),
            "batch_key": "assets",
            "display_name": "Assets",
            "source_kind": "image",
        },
    )
    sprite_asset = client.post(
        f"/worlds/{world_id}/authoring/source-batches/{batch.json()['id']}/assets",
        json={
            "worldline_id": str(worldline_id),
            "media_asset_id": str(sprite_media_id),
            "source_asset_kind": "image",
            "source_label": "alice-happy",
            "metadata_json": {
                "character_label": "Alice",
                "expression_key": "happy",
                "pose_key": "standing",
            },
        },
    )
    voice_asset = client.post(
        f"/worlds/{world_id}/authoring/source-batches/{batch.json()['id']}/assets",
        json={
            "worldline_id": str(worldline_id),
            "media_asset_id": str(voice_media_id),
            "source_asset_kind": "audio",
            "source_label": "alice-voice",
            "metadata_json": {"speaker_label": "Alice", "voice_label": "alice"},
        },
    )
    run = client.post(
        f"/worlds/{world_id}/authoring/import-runs",
        json={
            "worldline_id": str(worldline_id),
            "source_batch_id": batch.json()["id"],
        },
    )
    matched = client.post(
        f"/worlds/{world_id}/authoring/import-runs/{run.json()['id']}/match-assets",
        json={
            "worldline_id": str(worldline_id),
            "source_asset_ids": [sprite_asset.json()["id"], voice_asset.json()["id"]],
        },
    )

    assert matched.status_code == 201
    assert matched.json()["created_proposal_count"] == 2
    assert matched.json()["sprite_match_count"] == 1
    assert matched.json()["voice_match_count"] == 1
    assert matched.json()["blocked_count"] == 0
    assert matched.json()["run"]["summary_json"]["provider_execution"] is False
    target_ref_kinds = {
        proposal["target_ref_kind"] for proposal in matched.json()["run"]["proposals"]
    }
    assert {"sprite_asset_match", "voice_asset_match"}.issubset(target_ref_kinds)
    assert "storage_uri" not in _json_text(matched.json())

    with Session(engine) as session:
        assert len(session.scalars(select(AuthoringSourceTraceability)).all()) == 0
        assert session.scalars(select(WorldEventModel)).all() == []


def test_authoring_api_demo_world_assembly_endpoint() -> None:
    client, engine = _client_with_database()
    owner_id, owner_token = _seed_user(engine, "owner@example.test")
    member_id, member_token = _seed_user(engine, "member@example.test")
    world_id = _seed_world(engine, owner_id)
    worldline_id = _seed_worldline(engine, world_id)
    _add_membership(engine, world_id, owner_id, AuthRole.WORLD_ADMIN)
    _add_membership(engine, world_id, member_id, AuthRole.HUMAN_USER)
    alice_id = _seed_agent(engine, world_id, "alice", "Alice")
    bob_id = _seed_agent(engine, world_id, "bob", "Bob")
    alice_sprite_id = _add_media_asset(
        engine,
        world_id,
        worldline_id,
        asset_kind="image",
        asset_role="character_sprite",
    )
    bob_sprite_id = _add_media_asset(
        engine,
        world_id,
        worldline_id,
        asset_kind="image",
        asset_role="character_sprite",
    )
    background_id = _add_media_asset(
        engine,
        world_id,
        worldline_id,
        asset_kind="image",
        asset_role="scene_background",
    )
    alice_voice_id = _add_media_asset(
        engine,
        world_id,
        worldline_id,
        asset_kind="audio",
        asset_role="voice_sample",
    )
    bob_voice_id = _add_media_asset(
        engine,
        world_id,
        worldline_id,
        asset_kind="audio",
        asset_role="voice_sample",
    )

    _authenticate(client, owner_token)
    batch = client.post(
        f"/worlds/{world_id}/authoring/source-batches",
        json={
            "worldline_id": str(worldline_id),
            "batch_key": "demo-assembly",
            "display_name": "Demo Assembly",
        },
    )
    asset = client.post(
        f"/worlds/{world_id}/authoring/source-batches/{batch.json()['id']}/assets",
        json={
            "worldline_id": str(worldline_id),
            "source_label": "demo.ks",
        },
    )
    fragment = client.post(
        f"/worlds/{world_id}/authoring/source-assets/{asset.json()['id']}/fragments",
        json={
            "worldline_id": str(worldline_id),
            "fragment_key": "opening",
            "fragment_kind": "dialogue",
            "sequence": 1,
            "excerpt_text": "Alice: start\nBob: continue",
        },
    )
    run = client.post(
        f"/worlds/{world_id}/authoring/import-runs",
        json={
            "worldline_id": str(worldline_id),
            "source_batch_id": batch.json()["id"],
        },
    )
    parsed = client.post(
        f"/worlds/{world_id}/authoring/import-runs/{run.json()['id']}/parse-script",
        json={
            "worldline_id": str(worldline_id),
            "source_fragment_ids": [fragment.json()["id"]],
        },
    )
    dialogue_ids = [
        proposal["id"]
        for proposal in parsed.json()["run"]["proposals"]
        if proposal["target_ref_kind"] == "dialogue_candidate"
    ]
    for proposal_id in dialogue_ids:
        reviewed = client.post(
            f"/worlds/{world_id}/authoring/proposals/{proposal_id}/review",
            json={"decision": "approve"},
        )
        assert reviewed.status_code == 201
    apply_ids = _create_demo_api_evidence(
        client,
        world_id,
        run.json()["id"],
        fragment.json()["id"],
        {
            str(alice_id): {
                "name": "Alice",
                "sprite_media_id": str(alice_sprite_id),
                "voice_media_id": str(alice_voice_id),
            },
            str(bob_id): {
                "name": "Bob",
                "sprite_media_id": str(bob_sprite_id),
                "voice_media_id": str(bob_voice_id),
            },
        },
        background_media_id=str(background_id),
    )
    for proposal_id in apply_ids:
        reviewed = client.post(
            f"/worlds/{world_id}/authoring/proposals/{proposal_id}/review",
            json={"decision": "approve"},
        )
        assert reviewed.status_code == 201
    applied = client.post(
        f"/worlds/{world_id}/authoring/import-runs/{run.json()['id']}/apply",
        json={"worldline_id": str(worldline_id), "proposal_ids": apply_ids},
    )
    with Session(engine) as session:
        profile_id = uuid.uuid4()
        session.add(
            CharacterVisualGenerationProfile(
                id=profile_id,
                world_id=world_id,
                worldline_id=worldline_id,
                agent_id=alice_id,
                preferred_checkpoint_id=None,
                allowed_lora_ids_json=[],
                default_lora_ids_json=[],
                banned_lora_ids_json=[],
                prompt_fragments_json={},
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
        session.commit()

    persona_ids = _applied_json_ids(applied.json(), "agent_persona")
    memory_ids = _applied_json_ids(applied.json(), "agent_memory_item")
    visual_ids = _target_json_ids(
        applied.json(),
        {"sprite_asset_match", "background_asset_match"},
    )
    voice_ids = _target_json_ids(applied.json(), {"voice_asset_match"})
    visual_profile_ids = _target_json_ids(
        applied.json(),
        {"visual_generation_profile_recommendation"},
    )
    assembly_body = {
        "worldline_id": str(worldline_id),
        "agent_ids": [str(alice_id), str(bob_id)],
        "dialogue_proposal_ids": dialogue_ids,
        "persona_proposal_ids": persona_ids,
        "memory_proposal_ids": memory_ids,
        "visual_proposal_ids": visual_ids,
        "voice_proposal_ids": voice_ids,
        "visual_profile_proposal_ids": visual_profile_ids,
        "visual_generation_profile_ids": [str(profile_id)],
    }
    _authenticate(client, member_token)
    forbidden = client.post(
        f"/worlds/{world_id}/authoring/import-runs/{run.json()['id']}/assemble-demo-world",
        json=assembly_body,
    )
    _authenticate(client, owner_token)
    assembly = client.post(
        f"/worlds/{world_id}/authoring/import-runs/{run.json()['id']}/assemble-demo-world",
        json=assembly_body,
    )
    proposal_id = assembly.json()["proposal"]["id"]
    reviewed = client.post(
        f"/worlds/{world_id}/authoring/proposals/{proposal_id}/review",
        json={"decision": "approve"},
    )
    assembly_apply = client.post(
        f"/worlds/{world_id}/authoring/import-runs/{run.json()['id']}/apply",
        json={"worldline_id": str(worldline_id), "proposal_ids": [proposal_id]},
    )

    assert forbidden.status_code == 403
    assert assembly.status_code == 201
    assert reviewed.status_code == 201
    assert assembly.json()["proposal"]["target_ref_kind"] == "demo_world_assembly"
    assert assembly.json()["report_json"]["entry_supported"] is True
    assert assembly_apply.status_code == 201
    assert assembly_apply.json()["applied_proposals"][0]["applied_ref_json"][
        "applied_ref_kind"
    ] == "conversation_session"
    for marker in ("storage_uri", "file://", "local://", "base64", "raw_prompt", "raw_output"):
        assert marker not in _json_text(assembly.json())
        assert marker not in _json_text(assembly_apply.json())

    with Session(engine) as session:
        assert session.scalars(select(ConversationSession)).one()
        assert len(session.scalars(select(ConversationParticipant)).all()) == 2
        assert session.scalars(select(ConversationTurn)).one()
        assert session.scalars(select(ConversationTurnPresentation)).one()
        assert session.scalars(select(WorldEventModel)).all() == []


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
    storage_tmp = TemporaryDirectory()
    storage = LocalMediaObjectStorage(Path(storage_tmp.name) / "media")
    app.dependency_overrides[_authoring_media_storage] = lambda: storage
    app.state._authoring_storage_tmp = storage_tmp
    client = _AuthoringApiClient(app)
    client.authoring_storage = storage
    return client, engine


def _create_tables(engine: Engine) -> None:
    for table in (
        cast(Table, User.__table__),
        cast(Table, AuthSession.__table__),
        cast(Table, PlatformRoleAssignment.__table__),
        cast(Table, World.__table__),
        cast(Table, Worldline.__table__),
        cast(Table, WorldMembership.__table__),
        cast(Table, Agent.__table__),
        cast(Table, AgentPersona.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, MediaJob.__table__),
        cast(Table, MediaAsset.__table__),
        cast(Table, MediaObject.__table__),
        cast(Table, ConversationSession.__table__),
        cast(Table, ConversationParticipant.__table__),
        cast(Table, ConversationTurn.__table__),
        cast(Table, ConversationTurnPresentation.__table__),
        cast(Table, CharacterSpriteSet.__table__),
        cast(Table, CharacterSpriteVariant.__table__),
        cast(Table, SceneBackgroundProfile.__table__),
        cast(Table, VoiceProfile.__table__),
        cast(Table, AgentVoiceProfileBinding.__table__),
        cast(Table, SpeechTranscript.__table__),
        cast(Table, SpeechStyleMapping.__table__),
        cast(Table, AgentMemoryItem.__table__),
        cast(Table, ProviderIntegration.__table__),
        cast(Table, ProviderCapability.__table__),
        cast(Table, ProviderBudgetPolicy.__table__),
        cast(Table, ModelInvocation.__table__),
        cast(Table, PromptSnapshot.__table__),
        cast(Table, VisualWorkflowTemplate.__table__),
        cast(Table, VisualWorkflowTemplateVersion.__table__),
        cast(Table, VisualModelAsset.__table__),
        cast(Table, CharacterVisualGenerationProfile.__table__),
        cast(Table, VisualGenerationPlan.__table__),
        cast(Table, VisualGenerationPlanReference.__table__),
        cast(Table, AuthoringSourceBatch.__table__),
        cast(Table, AuthoringSourceAsset.__table__),
        cast(Table, AuthoringSourceFragment.__table__),
        cast(Table, AuthoringImportRun.__table__),
        cast(Table, AuthoringImportProposal.__table__),
        cast(Table, AuthoringReviewDecision.__table__),
        cast(Table, AuthoringSourceTraceability.__table__),
    ):
        table.create(engine)


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
            )
        )
        session.commit()
    return user_id, token


def _seed_world(engine: Engine, owner_user_id: uuid.UUID) -> uuid.UUID:
    world_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            World(
                id=world_id,
                owner_user_id=owner_user_id,
                slug=f"world-{world_id.hex[:8]}",
                name="World",
            )
        )
        session.commit()
    return world_id


def _seed_worldline(engine: Engine, world_id: uuid.UUID) -> uuid.UUID:
    with Session(engine) as session:
        primary = ensure_primary_worldline(session, world_id)
        session.commit()
        return primary.id


def _seed_agent(
    engine: Engine,
    world_id: uuid.UUID,
    agent_key: str,
    display_name: str,
) -> uuid.UUID:
    agent_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            Agent(
                id=agent_id,
                world_id=world_id,
                agent_key=agent_key,
                display_name=display_name,
                kind="role_agent",
                character_profile={},
                config={},
            )
        )
        session.commit()
    return agent_id


def _seed_text_provider(engine: Engine, world_id: uuid.UUID) -> uuid.UUID:
    with Session(engine) as session:
        provider = ProviderRegistryService(session).create_provider(
            ProviderIntegrationCreate(
                world_id=world_id,
                scope_kind=ProviderScopeKind.WORLD,
                provider_kind=ProviderKind.TEXT_GENERATION,
                adapter_kind=ProviderAdapterKind.FAKE,
                provider_key=f"fake-text-{uuid.uuid4().hex[:8]}",
                display_name="Fake Text",
            )
        )
        session.commit()
        return provider.id


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


def _add_media_asset(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    *,
    asset_kind: str,
    asset_role: str,
) -> uuid.UUID:
    media_asset_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            MediaAsset(
                id=media_asset_id,
                world_id=world_id,
                worldline_id=worldline_id,
                asset_kind=asset_kind,
                asset_role=asset_role,
                source_kind="manual_upload",
                status="available",
                visibility="world_admin",
                mime_type="image/png" if asset_kind == "image" else "audio/wav",
                checksum_sha256="a" * 64,
                created_by_actor_ref="test",
                metadata_json={},
            )
        )
        session.commit()
    return media_asset_id


def _create_demo_api_evidence(
    client: TestClient,
    world_id: uuid.UUID,
    run_id: str,
    fragment_id: str,
    agents: dict[str, dict[str, str]],
    *,
    background_media_id: str,
) -> list[str]:
    proposal_ids: list[str] = []
    for agent_id, data in agents.items():
        name = data["name"]
        drafts = [
            {
                "source_fragment_id": fragment_id,
                "proposal_kind": "character",
                "target_ref_kind": "agent_persona_candidate",
                "target_ref_id": agent_id,
                "title": f"{name} persona",
                "summary": "Traceable persona.",
                "proposed_payload_json": {
                    "agent_id": agent_id,
                    "persona_text": f"{name} is ready.",
                    "behavior_policy": {"source": "api-test"},
                    "character_profile": {"speech_style": "calm"},
                },
            },
            {
                "source_fragment_id": fragment_id,
                "proposal_kind": "memory",
                "target_ref_kind": "memory_candidate",
                "target_ref_id": agent_id,
                "title": f"{name} memory",
                "summary": "Traceable memory.",
                "proposed_payload_json": {
                    "source_kind": "authoring_distillation",
                    "agent_id": agent_id,
                    "content": f"{name} remembers the opening.",
                    "memory_kind": "fact",
                },
            },
            {
                "source_fragment_id": fragment_id,
                "proposal_kind": "asset_match",
                "target_ref_kind": "sprite_asset_match",
                "title": f"{name} sprite",
                "summary": "Traceable sprite.",
                "proposed_payload_json": {
                    "media_asset_id": data["sprite_media_id"],
                    "agent_id": agent_id,
                    "character_label": name,
                    "expression_key": "neutral",
                },
            },
            {
                "source_fragment_id": fragment_id,
                "proposal_kind": "asset_match",
                "target_ref_kind": "voice_asset_match",
                "title": f"{name} voice",
                "summary": "Traceable voice.",
                "proposed_payload_json": {
                    "media_asset_id": data["voice_media_id"],
                    "agent_id": agent_id,
                    "speaker_label": name,
                    "voice_label": "default",
                },
            },
            {
                "source_fragment_id": fragment_id,
                "proposal_kind": "asset_match",
                "target_ref_kind": "visual_generation_profile_recommendation",
                "target_ref_id": agent_id,
                "title": f"{name} visual profile",
                "summary": "Traceable visual profile.",
                "proposed_payload_json": {
                    "agent_id": agent_id,
                    "review_only": True,
                    "recommended_prompt_fragments": [name],
                },
            },
        ]
        for draft in drafts:
            created = client.post(
                f"/worlds/{world_id}/authoring/import-runs/{run_id}/proposals",
                json=draft,
            )
            assert created.status_code == 201
            proposal_ids.append(created.json()["id"])
    background = client.post(
        f"/worlds/{world_id}/authoring/import-runs/{run_id}/proposals",
        json={
            "source_fragment_id": fragment_id,
            "proposal_kind": "asset_match",
            "target_ref_kind": "background_asset_match",
            "title": "Opening background",
            "summary": "Traceable background.",
            "proposed_payload_json": {
                "media_asset_id": background_media_id,
                "location_key": "opening",
            },
        },
    )
    assert background.status_code == 201
    proposal_ids.append(background.json()["id"])
    return proposal_ids


def _applied_json_ids(body: dict[str, object], applied_ref_kind: str) -> list[str]:
    proposals = body.get("applied_proposals")
    if not isinstance(proposals, list):
        return []
    return [
        str(proposal["id"])
        for proposal in proposals
        if isinstance(proposal, dict)
        and isinstance(proposal.get("applied_ref_json"), dict)
        and proposal["applied_ref_json"].get("applied_ref_kind") == applied_ref_kind
    ]


def _target_json_ids(body: dict[str, object], target_ref_kinds: set[str]) -> list[str]:
    proposals = body.get("applied_proposals")
    if not isinstance(proposals, list):
        return []
    return [
        str(proposal["id"])
        for proposal in proposals
        if isinstance(proposal, dict) and proposal.get("target_ref_kind") in target_ref_kinds
    ]


def _authenticate(client: TestClient, token: str) -> None:
    client.cookies.set(SESSION_COOKIE_NAME, token)
    client.cookies.set(CSRF_COOKIE_NAME, "csrf")
    client.headers.update({CSRF_HEADER_NAME: "csrf"})


def _json_text(value: object) -> str:
    return str(value).lower()


def _galgame_source_dir(tmp_path: Path) -> Path:
    root = tmp_path / "already-unpacked-demo"
    (root / "sprites" / "alice").mkdir(parents=True)
    (root / "backgrounds").mkdir(parents=True)
    (root / "cg").mkdir(parents=True)
    (root / "voice" / "alice").mkdir(parents=True)
    (root / "scripts").mkdir(parents=True)
    (root / "profiles").mkdir(parents=True)
    (root / "routes").mkdir(parents=True)
    (root / ".hidden").mkdir()
    (root / "sprites" / "alice" / "alice_neutral.png").write_bytes(b"sprite")
    (root / "sprites" / "alice" / "alice_happy_face.png").write_bytes(b"expression")
    (root / "backgrounds" / "school_bg.jpg").write_bytes(b"background")
    (root / "cg" / "event_cg.webp").write_bytes(b"cg")
    (root / "voice" / "alice" / "alice_line.wav").write_bytes(b"voice")
    (root / "voice" / "bgm_theme.ogg").write_bytes(b"bgm")
    (root / "scripts" / "scene1.ks").write_text(
        "\n".join(f"Alice: line {index}" for index in range(120)),
        encoding="utf-8",
    )
    (root / "profiles" / "alice_profile.md").write_text(
        "character: Alice\nkind and curious",
        encoding="utf-8",
    )
    (root / "routes" / "alice_route_choice.txt").write_text(
        "choice: walk home with Alice\nroute: alice",
        encoding="utf-8",
    )
    (root / "archive.zip").write_bytes(b"packed")
    (root / ".hidden" / "secret.txt").write_text("hidden", encoding="utf-8")
    return root
