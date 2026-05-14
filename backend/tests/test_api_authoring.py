from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import cast

from fastapi.testclient import TestClient
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
from noveland.events.models import WorldEventModel
from noveland.media.models import MediaJob
from noveland.services.api.app import create_app
from noveland.services.api.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, SESSION_COOKIE_NAME
from noveland.services.api.dependencies import get_db_session
from noveland.worlds.models import World, Worldline, WorldMembership
from noveland.worlds.worldlines import ensure_primary_worldline
from sqlalchemy import Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


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
    assert parsed.json()["created_proposal_count"] == 7
    assert parsed.json()["dialogue_count"] == 2
    assert parsed.json()["scene_count"] == 1
    assert parsed.json()["choice_count"] == 2
    assert parsed.json()["route_count"] == 1
    assert parsed.json()["event_count"] == 1
    assert parsed.json()["unresolved_speaker_count"] == 1
    assert parsed.json()["run"]["summary_json"]["provider_execution"] is False
    assert all(
        proposal["source_fragment_id"] == fragment.json()["id"]
        for proposal in parsed.json()["run"]["proposals"]
    )
    assert "storage_uri" not in _json_text(parsed.json())

    with Session(engine) as session:
        assert len(session.scalars(select(AuthoringSourceTraceability)).all()) == 7
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
        cast(Table, Worldline.__table__),
        cast(Table, WorldMembership.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, MediaJob.__table__),
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


def _authenticate(client: TestClient, token: str) -> None:
    client.cookies.set(SESSION_COOKIE_NAME, token)
    client.cookies.set(CSRF_COOKIE_NAME, "csrf")
    client.headers.update({CSRF_HEADER_NAME: "csrf"})


def _json_text(value: object) -> str:
    return str(value).lower()
