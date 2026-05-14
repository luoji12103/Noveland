from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import cast

from noveland.agents.models import Agent
from noveland.auth import AuthRole
from noveland.auth.models import User
from noveland.authoring import AuthoringService
from noveland.authoring.contracts import (
    AuthoringApplyRequest,
    AuthoringAssetMatchRequest,
    AuthoringCharacterExtractRequest,
    AuthoringConflictReviewRequest,
    AuthoringImportRunCreate,
    AuthoringLoreExtractRequest,
    AuthoringMemoryMigrateRequest,
    AuthoringProposalRead,
    AuthoringReviewDecisionCreate,
    AuthoringReviewDecisionKind,
    AuthoringScriptParseRequest,
    AuthoringSourceAssetCreate,
    AuthoringSourceAssetKind,
    AuthoringSourceBatchCreate,
    AuthoringSourceFragmentCreate,
    AuthoringSourceFragmentKind,
)
from noveland.authoring.models import (
    AuthoringImportProposal,
    AuthoringImportRun,
    AuthoringReviewDecision,
    AuthoringSourceAsset,
    AuthoringSourceBatch,
    AuthoringSourceFragment,
    AuthoringSourceTraceability,
)
from noveland.conversations.models import ConversationSession, ConversationTurn
from noveland.events.models import WorldEventModel
from noveland.media.models import MediaAsset, MediaJob
from noveland.memory.models import MemoryBackendProfile, MemoryWriteJob
from noveland.speech.models import AgentVoiceProfileBinding, VoiceProfile
from noveland.visual.models import CharacterSpriteSet, CharacterSpriteVariant
from noveland.worlds.models import Scene, World, Worldline, WorldMembership
from sqlalchemy import Table, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

_NAMESPACE = uuid.UUID("c6930ebc-5272-48c3-a799-626d32cf8c46")


@dataclass(frozen=True, slots=True)
class AuthoringSampleImport:
    engine: Engine
    world_id: uuid.UUID
    worldline_id: uuid.UUID
    admin_user_id: uuid.UUID
    source_batch_id: uuid.UUID
    source_asset_ids: dict[str, uuid.UUID]
    source_fragment_ids: dict[str, uuid.UUID]
    media_asset_ids: dict[str, uuid.UUID]
    import_run_id: uuid.UUID
    proposal_counts: dict[str, int]
    target_ref_counts: dict[str, int]
    applied_other_proposal_id: uuid.UUID
    blocked_proposal_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class _AssetSpec:
    kind: AuthoringSourceAssetKind
    label: str
    metadata_json: dict[str, object]
    media_asset_id: uuid.UUID | None


@dataclass(frozen=True, slots=True)
class _FragmentSpec:
    source_asset_key: str
    kind: AuthoringSourceFragmentKind
    text: str


def create_authoring_sample_import() -> AuthoringSampleImport:
    engine = _engine()
    graph = _ids()
    with Session(engine) as session:
        _seed_world_graph(session, graph)
        _seed_media_assets(session, graph)
        sample = _run_authoring_pipeline(session, graph)
        session.commit()
    return sample


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
        cast(Table, World.__table__),
        cast(Table, Worldline.__table__),
        cast(Table, WorldMembership.__table__),
        cast(Table, Scene.__table__),
        cast(Table, Agent.__table__),
        cast(Table, ConversationSession.__table__),
        cast(Table, ConversationTurn.__table__),
        cast(Table, WorldEventModel.__table__),
        cast(Table, MemoryBackendProfile.__table__),
        cast(Table, MemoryWriteJob.__table__),
        cast(Table, MediaJob.__table__),
        cast(Table, MediaAsset.__table__),
        cast(Table, VoiceProfile.__table__),
        cast(Table, AgentVoiceProfileBinding.__table__),
        cast(Table, CharacterSpriteSet.__table__),
        cast(Table, CharacterSpriteVariant.__table__),
        cast(Table, AuthoringSourceBatch.__table__),
        cast(Table, AuthoringSourceAsset.__table__),
        cast(Table, AuthoringSourceFragment.__table__),
        cast(Table, AuthoringImportRun.__table__),
        cast(Table, AuthoringImportProposal.__table__),
        cast(Table, AuthoringReviewDecision.__table__),
        cast(Table, AuthoringSourceTraceability.__table__),
    ):
        table.create(engine)


def _ids() -> dict[str, uuid.UUID]:
    names = (
        "admin_user",
        "world",
        "worldline",
        "membership",
        "scene",
        "agent_alice",
        "agent_bob",
        "media_sprite",
        "media_background",
        "media_cg",
        "media_voice",
    )
    return {name: uuid.uuid5(_NAMESPACE, name) for name in names}


def _id(name: str) -> uuid.UUID:
    return uuid.uuid5(_NAMESPACE, name)


def _seed_world_graph(session: Session, graph: dict[str, uuid.UUID]) -> None:
    session.add(
        User(
            id=graph["admin_user"],
            email="authoring-admin@example.test",
            display_name="Authoring Admin",
            is_active=True,
        )
    )
    session.add(
        World(
            id=graph["world"],
            owner_user_id=graph["admin_user"],
            slug="v0-5-authoring-sample",
            name="v0.5 Authoring Sample",
            is_active=True,
        )
    )
    session.add(
        Worldline(
            id=graph["worldline"],
            world_id=graph["world"],
            worldline_key="primary",
            name="Primary Worldline",
            parent_worldline_id=None,
            status="active",
            created_by_actor_ref="test:v0.5",
            metadata_json={"primary": True},
        )
    )
    session.add(
        WorldMembership(
            id=graph["membership"],
            world_id=graph["world"],
            user_id=graph["admin_user"],
            role=AuthRole.WORLD_ADMIN.value,
        )
    )
    session.add(
        Scene(
            id=graph["scene"],
            world_id=graph["world"],
            scene_key="schoolyard",
            name="Schoolyard",
            location_tags=["school", "day"],
        )
    )
    session.add_all(
        [
            Agent(
                id=graph["agent_alice"],
                world_id=graph["world"],
                home_scene_id=graph["scene"],
                agent_key="alice",
                display_name="Alice",
                kind="role_agent",
                importance="lead",
                is_enabled=True,
            ),
            Agent(
                id=graph["agent_bob"],
                world_id=graph["world"],
                home_scene_id=graph["scene"],
                agent_key="bob",
                display_name="Bob",
                kind="role_agent",
                importance="major",
                is_enabled=True,
            ),
        ]
    )
    session.flush()


def _seed_media_assets(session: Session, graph: dict[str, uuid.UUID]) -> None:
    for key, asset_kind, asset_role, title in (
        ("media_sprite", "image", "character_sprite", "Alice happy sprite"),
        ("media_background", "image", "scene_background", "Schoolyard background"),
        ("media_cg", "image", "event_cg", "Opening CG"),
        ("media_voice", "audio", "voice_sample", "Alice voice sample"),
    ):
        session.add(
            MediaAsset(
                id=graph[key],
                world_id=graph["world"],
                worldline_id=graph["worldline"],
                asset_kind=asset_kind,
                asset_role=asset_role,
                source_kind="test_fixture",
                status="available",
                visibility="world_admin",
                mime_type="image/png" if asset_kind == "image" else "audio/wav",
                checksum_sha256="a" * 64,
                title=title,
                created_by_actor_ref="test:v0.5",
                metadata_json={},
            )
        )
    session.flush()


def _run_authoring_pipeline(
    session: Session,
    graph: dict[str, uuid.UUID],
) -> AuthoringSampleImport:
    service = AuthoringService(session)
    batch = service.create_source_batch(
        AuthoringSourceBatchCreate(
            world_id=graph["world"],
            worldline_id=graph["worldline"],
            batch_key="v0-5-sample",
            display_name="v0.5 Sample Import",
            source_kind=AuthoringSourceAssetKind.SCRIPT,
        ),
        actor_ref="test:v0.5",
    )
    source_assets = _create_source_assets(service, graph, batch.id)
    source_fragments = _create_source_fragments(service, graph, source_assets)
    run = service.create_import_run(
        AuthoringImportRunCreate(
            world_id=graph["world"],
            worldline_id=graph["worldline"],
            source_batch_id=batch.id,
        ),
        actor_ref="test:v0.5",
    )

    service.parse_script(
        graph["world"],
        run.id,
        AuthoringScriptParseRequest(
            worldline_id=graph["worldline"],
            source_fragment_ids=(source_fragments["script"],),
        ),
    )
    service.extract_characters(
        graph["world"],
        run.id,
        AuthoringCharacterExtractRequest(
            worldline_id=graph["worldline"],
            source_fragment_ids=(source_fragments["character"],),
        ),
    )
    service.extract_lore(
        graph["world"],
        run.id,
        AuthoringLoreExtractRequest(
            worldline_id=graph["worldline"],
            source_fragment_ids=(source_fragments["lore"],),
        ),
    )
    service.review_conflicts(
        graph["world"],
        run.id,
        AuthoringConflictReviewRequest(worldline_id=graph["worldline"]),
    )
    service.migrate_memory(
        graph["world"],
        run.id,
        AuthoringMemoryMigrateRequest(
            worldline_id=graph["worldline"],
            source_fragment_ids=(source_fragments["memory"],),
        ),
    )
    service.match_assets(
        graph["world"],
        run.id,
        AuthoringAssetMatchRequest(
            worldline_id=graph["worldline"],
            source_asset_ids=(
                source_assets["sprite"],
                source_assets["background"],
                source_assets["cg"],
                source_assets["voice"],
            ),
        ),
    )

    run_read = service.get_import_run(graph["world"], run.id)
    conflict_report = next(
        proposal
        for proposal in run_read.proposals
        if proposal.target_ref_kind == "canon_conflict_report"
    )
    blocked_candidate = next(
        proposal
        for proposal in run_read.proposals
        if proposal.target_ref_kind == "memory_candidate"
    )
    for proposal_id in (conflict_report.id, blocked_candidate.id):
        service.review_proposal(
            graph["world"],
            proposal_id,
            AuthoringReviewDecisionCreate(decision=AuthoringReviewDecisionKind.APPROVE),
            actor_ref="test:v0.5",
        )
    service.apply(
        graph["world"],
        run.id,
        AuthoringApplyRequest(
            worldline_id=graph["worldline"],
            proposal_ids=(conflict_report.id, blocked_candidate.id),
        ),
    )
    final_run = service.get_import_run(graph["world"], run.id)
    proposal_counts = _proposal_counts(final_run.proposals)
    target_ref_counts = _target_ref_counts(final_run.proposals)
    return AuthoringSampleImport(
        engine=cast(Engine, session.get_bind()),
        world_id=graph["world"],
        worldline_id=graph["worldline"],
        admin_user_id=graph["admin_user"],
        source_batch_id=batch.id,
        source_asset_ids=source_assets,
        source_fragment_ids=source_fragments,
        media_asset_ids={
            "sprite": graph["media_sprite"],
            "background": graph["media_background"],
            "cg": graph["media_cg"],
            "voice": graph["media_voice"],
        },
        import_run_id=run.id,
        proposal_counts=proposal_counts,
        target_ref_counts=target_ref_counts,
        applied_other_proposal_id=conflict_report.id,
        blocked_proposal_id=blocked_candidate.id,
    )


def _create_source_assets(
    service: AuthoringService,
    graph: dict[str, uuid.UUID],
    batch_id: uuid.UUID,
) -> dict[str, uuid.UUID]:
    asset_specs = {
        "script": _AssetSpec(
            kind=AuthoringSourceAssetKind.SCRIPT,
            label="chapter-1.ks",
            metadata_json={},
            media_asset_id=None,
        ),
        "character": _AssetSpec(
            kind=AuthoringSourceAssetKind.CHARACTER_SHEET,
            label="characters.md",
            metadata_json={},
            media_asset_id=None,
        ),
        "lore": _AssetSpec(
            kind=AuthoringSourceAssetKind.LORE,
            label="lore.md",
            metadata_json={},
            media_asset_id=None,
        ),
        "memory": _AssetSpec(
            kind=AuthoringSourceAssetKind.LORE,
            label="memory.md",
            metadata_json={},
            media_asset_id=None,
        ),
        "sprite": _AssetSpec(
            kind=AuthoringSourceAssetKind.IMAGE,
            label="alice-happy",
            metadata_json={
                "character_label": "Alice",
                "expression_key": "happy",
                "pose_key": "standing",
            },
            media_asset_id=graph["media_sprite"],
        ),
        "background": _AssetSpec(
            kind=AuthoringSourceAssetKind.IMAGE,
            label="schoolyard-day",
            metadata_json={"location_key": "schoolyard", "time_of_day": "day"},
            media_asset_id=graph["media_background"],
        ),
        "cg": _AssetSpec(
            kind=AuthoringSourceAssetKind.IMAGE,
            label="opening-cg",
            metadata_json={"cg_key": "opening", "route_key": "common"},
            media_asset_id=graph["media_cg"],
        ),
        "voice": _AssetSpec(
            kind=AuthoringSourceAssetKind.AUDIO,
            label="alice-voice",
            metadata_json={"speaker_label": "Alice", "voice_label": "alice-default"},
            media_asset_id=graph["media_voice"],
        ),
    }
    created: dict[str, uuid.UUID] = {}
    for key, spec in asset_specs.items():
        asset = service.add_source_asset(
            AuthoringSourceAssetCreate(
                world_id=graph["world"],
                worldline_id=graph["worldline"],
                batch_id=batch_id,
                media_asset_id=spec.media_asset_id,
                source_asset_kind=spec.kind,
                source_label=spec.label,
                metadata_json=spec.metadata_json,
            )
        )
        created[key] = asset.id
    return created


def _create_source_fragments(
    service: AuthoringService,
    graph: dict[str, uuid.UUID],
    source_assets: dict[str, uuid.UUID],
) -> dict[str, uuid.UUID]:
    fragment_specs = {
        "script": _FragmentSpec(
            source_asset_key="script",
            kind=AuthoringSourceFragmentKind.SCENE,
            text=(
                "Alice: hello Bob\n"
                "「unassigned whisper」\n"
                "[scene: schoolyard]\n"
                "choice: follow Alice\n"
                "-> wait for Bob\n"
                "[route: common]\n"
                "[event: bell_rings]\n"
            ),
        ),
        "character": _FragmentSpec(
            source_asset_key="character",
            kind=AuthoringSourceFragmentKind.CHARACTER,
            text=(
                "character: Alice\n"
                "alias: Alice -> Al\n"
                "Alice trusts Bob\n"
                "faction: Student Council\n"
                "identity: Alice = prefect\n"
                "emotion: Alice = guarded\n"
            ),
        ),
        "lore": _FragmentSpec(
            source_asset_key="lore",
            kind=AuthoringSourceFragmentKind.LORE,
            text=(
                "canon: The city sleeps at noon\n"
                "uncertain: The gate may be alive\n"
                "location: Old Gate\n"
                "organization: Student Council\n"
                "rule: Wishes require payment\n"
                "secret: Alice is heir\n"
                "knowledge: Alice -> Alice is heir\n"
            ),
        ),
        "memory": _FragmentSpec(
            source_asset_key="memory",
            kind=AuthoringSourceFragmentKind.MEMORY,
            text=(
                "fact: Magic exists\n"
                "episodic: Alice met Bob\n"
                "relationship memory: Alice -> Bob: trusts him\n"
                "Alice likes tea\n"
                "style: Alice = terse\n"
            ),
        ),
    }
    created: dict[str, uuid.UUID] = {}
    for sequence, (key, spec) in enumerate(fragment_specs.items(), start=1):
        fragment = service.add_source_fragment(
            AuthoringSourceFragmentCreate(
                world_id=graph["world"],
                worldline_id=graph["worldline"],
                source_asset_id=source_assets[spec.source_asset_key],
                fragment_key=key,
                fragment_kind=spec.kind,
                sequence=sequence,
                excerpt_text=spec.text,
            )
        )
        created[key] = fragment.id
    return created


def _proposal_counts(proposals: list[AuthoringProposalRead]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for proposal in proposals:
        key = proposal.proposal_kind.value
        counts[key] = counts.get(key, 0) + 1
    return counts


def _target_ref_counts(proposals: list[AuthoringProposalRead]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for proposal in proposals:
        target_ref_kind = proposal.target_ref_kind
        if target_ref_kind is None:
            continue
        counts[target_ref_kind] = counts.get(target_ref_kind, 0) + 1
    return counts
