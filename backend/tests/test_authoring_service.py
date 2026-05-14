from __future__ import annotations

import uuid
from typing import cast

import pytest
from noveland.auth.models import User
from noveland.authoring import AuthoringService
from noveland.authoring.contracts import (
    AuthoringApplyRequest,
    AuthoringCharacterExtractRequest,
    AuthoringImportRunCreate,
    AuthoringLoreExtractRequest,
    AuthoringPreviewRequest,
    AuthoringProposalDraft,
    AuthoringProposalKind,
    AuthoringProposalStatus,
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
from noveland.authoring.service import AuthoringValidationError
from noveland.events.models import WorldEventModel
from noveland.media.models import MediaAsset, MediaJob
from noveland.worlds.models import World, Worldline
from noveland.worlds.worldlines import ensure_primary_worldline
from sqlalchemy import Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def test_source_registry_preview_review_and_apply_are_trace_only() -> None:
    engine = _engine()
    graph = _seed_graph(engine)
    with Session(engine) as session:
        service = AuthoringService(session)
        batch = service.create_source_batch(
            AuthoringSourceBatchCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                batch_key="script-1",
                display_name="Script 1",
                source_kind=AuthoringSourceAssetKind.SCRIPT,
            ),
            actor_ref="test",
        )
        source_asset = service.add_source_asset(
            AuthoringSourceAssetCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                batch_id=batch.id,
                media_asset_id=graph.media_asset_id,
                source_asset_kind=AuthoringSourceAssetKind.SCRIPT,
                source_label="script.ks",
            )
        )
        fragment = service.add_source_fragment(
            AuthoringSourceFragmentCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                source_asset_id=source_asset.id,
                fragment_key="line-1",
                fragment_kind=AuthoringSourceFragmentKind.DIALOGUE,
                sequence=1,
                excerpt_text="Alice: hello",
            )
        )
        run = service.create_import_run(
            AuthoringImportRunCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                source_batch_id=batch.id,
            ),
            actor_ref="test",
        )
        preview = service.preview(
            graph.world_id,
            run.id,
            AuthoringPreviewRequest(
                worldline_id=graph.worldline_id,
                proposals=(
                    AuthoringProposalDraft(
                        source_fragment_id=fragment.id,
                        proposal_kind=AuthoringProposalKind.OTHER,
                        title="Traceable note",
                        summary="Keep source trace only.",
                        proposed_payload_json={"note": "trace only"},
                    ),
                    AuthoringProposalDraft(
                        source_fragment_id=fragment.id,
                        proposal_kind=AuthoringProposalKind.LORE,
                        title="Lore candidate",
                        summary="Blocked in phase 1.",
                    ),
                ),
            ),
        )
        for proposal in preview.run.proposals:
            service.review_proposal(
                graph.world_id,
                proposal.id,
                AuthoringReviewDecisionCreate(
                    decision=AuthoringReviewDecisionKind.APPROVE,
                    reason="accepted for apply test",
                ),
                actor_ref="test",
            )
        result = service.apply(
            graph.world_id,
            run.id,
            AuthoringApplyRequest(
                worldline_id=graph.worldline_id,
                proposal_ids=tuple(proposal.id for proposal in preview.run.proposals),
            ),
        )
        session.commit()

    with Session(engine) as session:
        proposals = session.scalars(select(AuthoringImportProposal)).all()
        assert len(proposals) == 2
        assert [proposal.status for proposal in proposals] == ["applied", "blocked"]
        assert len(result.applied_proposals) == 1
        assert len(result.blocked_proposals) == 1
        assert result.applied_proposals[0].status == AuthoringProposalStatus.APPLIED
        assert result.blocked_proposals[0].applied_ref_json["blocked_reason"]
        assert len(session.scalars(select(AuthoringSourceTraceability)).all()) >= 4
        assert session.scalars(select(MediaJob)).all() == []
        assert session.scalars(select(WorldEventModel)).all() == []


def test_script_parser_creates_traceable_proposals_from_excerpt_text() -> None:
    engine = _engine()
    graph = _seed_graph(engine)
    with Session(engine) as session:
        service = AuthoringService(session)
        batch = service.create_source_batch(
            AuthoringSourceBatchCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                batch_key="script-1",
                display_name="Script 1",
                source_kind=AuthoringSourceAssetKind.SCRIPT,
            ),
            actor_ref="test",
        )
        source_asset = service.add_source_asset(
            AuthoringSourceAssetCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                batch_id=batch.id,
                source_asset_kind=AuthoringSourceAssetKind.SCRIPT,
                source_label="script.ks",
            )
        )
        fragment = service.add_source_fragment(
            AuthoringSourceFragmentCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                source_asset_id=source_asset.id,
                fragment_key="scene-1",
                fragment_kind=AuthoringSourceFragmentKind.SCENE,
                sequence=1,
                excerpt_text=(
                    "Hero: hello\n"
                    "「whispered line」\n"
                    "[scene: schoolyard]\n"
                    "choice: leave with him\n"
                    "-> stay\n"
                    "[route: branch_a]\n"
                    "[event: encounter]\n"
                ),
            )
        )
        run = service.create_import_run(
            AuthoringImportRunCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                source_batch_id=batch.id,
            ),
            actor_ref="test",
        )
        result = service.parse_script(
            graph.world_id,
            run.id,
            AuthoringScriptParseRequest(
                worldline_id=graph.worldline_id,
                source_fragment_ids=(fragment.id,),
            ),
        )
        trace_count = len(session.scalars(select(AuthoringSourceTraceability)).all())
        assert session.scalars(select(WorldEventModel)).all() == []
        session.commit()

    assert result.created_proposal_count == 7
    assert result.dialogue_count == 2
    assert result.scene_count == 1
    assert result.choice_count == 2
    assert result.route_count == 1
    assert result.event_count == 1
    assert result.unresolved_speaker_count == 1
    assert result.run.summary_json["parser_mode"] == "deterministic"
    assert result.run.summary_json["provider_execution"] is False
    assert all(
        proposal.source_fragment_id == fragment.id for proposal in result.run.proposals
    )
    assert all(proposal.status == "proposed" for proposal in result.run.proposals)
    assert trace_count == 7


def test_character_extractor_creates_traceable_character_relationship_proposals() -> None:
    engine = _engine()
    graph = _seed_graph(engine)
    with Session(engine) as session:
        service = AuthoringService(session)
        batch = service.create_source_batch(
            AuthoringSourceBatchCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                batch_key="character-sheet",
                display_name="Character Sheet",
                source_kind=AuthoringSourceAssetKind.CHARACTER_SHEET,
            ),
            actor_ref="test",
        )
        source_asset = service.add_source_asset(
            AuthoringSourceAssetCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                batch_id=batch.id,
                source_asset_kind=AuthoringSourceAssetKind.CHARACTER_SHEET,
                source_label="characters.md",
            )
        )
        character_fragment = service.add_source_fragment(
            AuthoringSourceFragmentCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                source_asset_id=source_asset.id,
                fragment_key="characters",
                fragment_kind=AuthoringSourceFragmentKind.CHARACTER,
                sequence=1,
                excerpt_text=(
                    "character: Alice\n"
                    "character: Alice\n"
                    "alias: Alice -> Al\n"
                    "Alice trusts Bob\n"
                    "faction: Student Council\n"
                    "identity: Alice = prefect\n"
                    "emotion: Alice = guarded\n"
                ),
            )
        )
        dialogue_fragment = service.add_source_fragment(
            AuthoringSourceFragmentCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                source_asset_id=source_asset.id,
                fragment_key="dialogue",
                fragment_kind=AuthoringSourceFragmentKind.DIALOGUE,
                sequence=2,
                excerpt_text="Hero: hello",
            )
        )
        run = service.create_import_run(
            AuthoringImportRunCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                source_batch_id=batch.id,
            ),
            actor_ref="test",
        )
        service.parse_script(
            graph.world_id,
            run.id,
            AuthoringScriptParseRequest(
                worldline_id=graph.worldline_id,
                source_fragment_ids=(dialogue_fragment.id,),
            ),
        )
        result = service.extract_characters(
            graph.world_id,
            run.id,
            AuthoringCharacterExtractRequest(
                worldline_id=graph.worldline_id,
                source_fragment_ids=(character_fragment.id,),
                include_dialogue_proposals=True,
            ),
        )
        assert session.scalars(select(MediaJob)).all() == []
        assert session.scalars(select(WorldEventModel)).all() == []
        session.commit()

    assert result.created_proposal_count == 7
    assert result.character_count == 2
    assert result.relationship_count == 1
    assert result.alias_count == 1
    assert result.faction_count == 1
    assert result.identity_count == 1
    assert result.emotional_baseline_count == 1
    assert result.run.summary_json["character_extractor_mode"] == "deterministic"
    assert result.run.summary_json["provider_execution"] is False
    character_proposals = [
        proposal
        for proposal in result.run.proposals
        if proposal.target_ref_kind == "character_candidate"
    ]
    character_labels = {
        proposal.proposed_payload_json["character_label"] for proposal in character_proposals
    }
    assert character_labels == {
        "Alice",
        "hero",
    }
    assert all(proposal.status == "proposed" for proposal in result.run.proposals)
    assert "storage_uri" not in str(result.run.model_dump()).lower()


def test_lore_extractor_creates_proposal_only_lore_candidates() -> None:
    engine = _engine()
    graph = _seed_graph(engine)
    with Session(engine) as session:
        service = AuthoringService(session)
        batch = service.create_source_batch(
            AuthoringSourceBatchCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                batch_key="lore",
                display_name="Lore",
                source_kind=AuthoringSourceAssetKind.LORE,
            ),
            actor_ref="test",
        )
        source_asset = service.add_source_asset(
            AuthoringSourceAssetCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                batch_id=batch.id,
                source_asset_kind=AuthoringSourceAssetKind.LORE,
                source_label="lore.md",
            )
        )
        fragment = service.add_source_fragment(
            AuthoringSourceFragmentCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                source_asset_id=source_asset.id,
                fragment_key="lore",
                fragment_kind=AuthoringSourceFragmentKind.LORE,
                sequence=1,
                excerpt_text=(
                    "lore: Magic exists\n"
                    "canon: The city sleeps at noon\n"
                    "inferred: Alice distrusts the council\n"
                    "uncertain: The old gate may be alive\n"
                    "location: Old Gate\n"
                    "organization: Student Council\n"
                    "world rule: Wishes require payment\n"
                    "secret: Alice is heir\n"
                    "knowledge: Alice -> Alice is heir\n"
                    "hidden from: Bob -> Alice is heir\n"
                ),
            )
        )
        run = service.create_import_run(
            AuthoringImportRunCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                source_batch_id=batch.id,
            ),
            actor_ref="test",
        )
        result = service.extract_lore(
            graph.world_id,
            run.id,
            AuthoringLoreExtractRequest(
                worldline_id=graph.worldline_id,
                source_fragment_ids=(fragment.id,),
            ),
        )
        first_lore = result.run.proposals[0]
        service.review_proposal(
            graph.world_id,
            first_lore.id,
            AuthoringReviewDecisionCreate(decision=AuthoringReviewDecisionKind.APPROVE),
            actor_ref="test",
        )
        apply_result = service.apply(
            graph.world_id,
            run.id,
            AuthoringApplyRequest(
                worldline_id=graph.worldline_id,
                proposal_ids=(first_lore.id,),
            ),
        )
        assert session.scalars(select(MediaJob)).all() == []
        assert session.scalars(select(WorldEventModel)).all() == []
        session.commit()

    assert result.created_proposal_count == 10
    assert result.lore_count == 4
    assert result.location_count == 1
    assert result.organization_count == 1
    assert result.world_rule_count == 1
    assert result.secret_count == 1
    assert result.knowledge_boundary_count == 2
    assert result.uncertain_count == 1
    assert result.run.summary_json["lore_extractor_mode"] == "deterministic"
    assert result.run.summary_json["provider_execution"] is False
    assert apply_result.applied_proposals == []
    assert apply_result.blocked_proposals[0].applied_ref_json["blocked_reason"] == (
        "unsupported_proposal_kind"
    )
    assert "storage_uri" not in str(result.run.model_dump()).lower()


def test_source_asset_rejects_cross_worldline_media_asset() -> None:
    engine = _engine()
    graph = _seed_graph(engine)
    fork_id = _seed_fork(engine, graph.world_id, graph.worldline_id)
    media_asset_id = _seed_media_asset(engine, graph.world_id, fork_id)
    with Session(engine) as session:
        service = AuthoringService(session)
        batch = service.create_source_batch(
            AuthoringSourceBatchCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                batch_key="script-1",
                display_name="Script 1",
            ),
            actor_ref="test",
        )
        with pytest.raises(AuthoringValidationError, match="worldline"):
            service.add_source_asset(
                AuthoringSourceAssetCreate(
                    world_id=graph.world_id,
                    worldline_id=graph.worldline_id,
                    batch_id=batch.id,
                    media_asset_id=media_asset_id,
                    source_label="cross-worldline.txt",
                )
            )


def test_authoring_json_rejects_leaky_values() -> None:
    graph_id = uuid.uuid4()
    with pytest.raises(ValueError, match="storage_uri"):
        AuthoringSourceBatchCreate(
            world_id=graph_id,
            worldline_id=uuid.uuid4(),
            batch_key="bad",
            display_name="Bad",
            metadata_json={"nested": {"storage_uri": "local://leak"}},
        )
    with pytest.raises(ValueError, match="base64"):
        AuthoringProposalDraft(
            title="Bad",
            summary="Bad",
            evidence_json={"image": "data:image/png;base64,abc"},
        )


class _Graph:
    def __init__(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        media_asset_id: uuid.UUID,
    ) -> None:
        self.world_id = world_id
        self.worldline_id = worldline_id
        self.media_asset_id = media_asset_id


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
        cast(Table, WorldEventModel.__table__),
        cast(Table, MediaJob.__table__),
        cast(Table, MediaAsset.__table__),
        cast(Table, AuthoringSourceBatch.__table__),
        cast(Table, AuthoringSourceAsset.__table__),
        cast(Table, AuthoringSourceFragment.__table__),
        cast(Table, AuthoringImportRun.__table__),
        cast(Table, AuthoringImportProposal.__table__),
        cast(Table, AuthoringReviewDecision.__table__),
        cast(Table, AuthoringSourceTraceability.__table__),
    ):
        table.create(engine)


def _seed_graph(engine: Engine) -> _Graph:
    user_id = uuid.uuid4()
    world_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            User(
                id=user_id,
                email="user@example.test",
                display_name="User",
                is_active=True,
            )
        )
        session.add(
            World(
                id=world_id,
                owner_user_id=user_id,
                slug=f"world-{world_id.hex[:8]}",
                name="World",
            )
        )
        session.flush()
        worldline_id = ensure_primary_worldline(session, world_id).id
        media_asset_id = _add_media_asset(session, world_id, worldline_id)
        session.commit()
    return _Graph(world_id=world_id, worldline_id=worldline_id, media_asset_id=media_asset_id)


def _seed_fork(engine: Engine, world_id: uuid.UUID, parent_worldline_id: uuid.UUID) -> uuid.UUID:
    fork_id = uuid.uuid4()
    with Session(engine) as session:
        session.add(
            Worldline(
                id=fork_id,
                world_id=world_id,
                worldline_key=f"fork-{fork_id.hex[:8]}",
                name="Fork",
                parent_worldline_id=parent_worldline_id,
                status="active",
                created_by_actor_ref="test",
                metadata_json={},
            )
        )
        session.commit()
    return fork_id


def _seed_media_asset(engine: Engine, world_id: uuid.UUID, worldline_id: uuid.UUID) -> uuid.UUID:
    with Session(engine) as session:
        media_asset_id = _add_media_asset(session, world_id, worldline_id)
        session.commit()
        return media_asset_id


def _add_media_asset(session: Session, world_id: uuid.UUID, worldline_id: uuid.UUID) -> uuid.UUID:
    media_asset_id = uuid.uuid4()
    session.add(
        MediaAsset(
            id=media_asset_id,
            world_id=world_id,
            worldline_id=worldline_id,
            asset_kind="document",
            asset_role="document",
            source_kind="manual_upload",
            status="available",
            visibility="world_admin",
            mime_type="text/plain",
            checksum_sha256="a" * 64,
            created_by_actor_ref="test",
            metadata_json={},
        )
    )
    return media_asset_id
