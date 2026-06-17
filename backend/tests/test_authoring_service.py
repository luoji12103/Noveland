from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, cast

import pytest
from noveland.agents.models import Agent, AgentPersona
from noveland.auth.models import User
from noveland.authoring import AuthoringService
from noveland.authoring.contracts import (
    AuthoringApplyRequest,
    AuthoringApplyResult,
    AuthoringAssetMatchRequest,
    AuthoringCharacterExtractRequest,
    AuthoringCharacterMemoryDistillRequest,
    AuthoringConflictReviewRequest,
    AuthoringImportRunCreate,
    AuthoringLoreExtractRequest,
    AuthoringMemoryMigrateRequest,
    AuthoringPreviewRequest,
    AuthoringProposalCreate,
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
    BetaContentRepairCandidate,
    BetaContentRepairKind,
    BetaContentRepairRequest,
    DemoWorldAssemblyRequest,
    GalgameSourceIntakeApplyRequest,
    GalgameSourceIntakePreviewRequest,
)
from noveland.authoring.galgame_intake import GalgameSourceIntakeService
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
    ProviderCapabilityCreate,
    ProviderIntegrationCreate,
    ProviderKind,
    ProviderScopeKind,
)
from noveland.providers.models import ProviderBudgetPolicy, ProviderCapability, ProviderIntegration
from noveland.providers.registry import ProviderRegistryService
from noveland.speech.contracts import TTSRequest
from noveland.speech.models import (
    AgentVoiceProfileBinding,
    SpeechStyleMapping,
    SpeechTranscript,
    VoiceProfile,
)
from noveland.speech.service import SpeechService
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


def test_galgame_source_intake_preview_and_apply_imports_safe_sources(
    tmp_path: Path,
) -> None:
    engine = _engine()
    graph = _seed_graph(engine)
    source_dir = _galgame_source_dir(tmp_path)

    with Session(engine) as session:
        service = GalgameSourceIntakeService(session, LocalMediaObjectStorage(tmp_path / "media"))
        request = GalgameSourceIntakeApplyRequest(
            world_id=graph.world_id,
            worldline_id=graph.worldline_id,
            source_directory=str(source_dir),
            batch_key="demo-galgame",
            display_name="Demo Galgame",
            max_text_fragment_chars=200,
            confirm_already_unpacked_user_provided=True,
        )
        preview = service.preview(request)
        result = service.apply(request, actor_ref="test")
        session.commit()

    assert preview.accepted_count == 9
    assert preview.rejected_count == 2
    assert preview.media_file_count == 6
    assert preview.text_file_count == 3
    assert preview.root_label == source_dir.name
    assert all(str(source_dir) not in item.model_dump_json() for item in preview.files)
    assert any(item.asset_role == "character_sprite" for item in preview.files)
    assert any(item.asset_role == "expression_variant" for item in preview.files)
    assert any(item.asset_role == "background" for item in preview.files)
    assert any(item.asset_role == "cg" for item in preview.files)
    assert any(item.asset_role == "voice_reference" for item in preview.files)
    assert any(
        item.reason == "archive, executable, or packed container is not accepted"
        for item in preview.files
    )
    assert result.batch.metadata_json["source_type"] == "already_unpacked_galgame"
    assert result.run.summary_json["provider_execution"] is False
    assert result.run.summary_json["canon_mutation"] is False
    assert len(result.media_asset_ids) == 6
    assert len(result.source_fragments) >= 3
    assert "storage_uri" not in result.model_dump_json().lower()
    assert str(source_dir) not in result.model_dump_json()

    with Session(engine) as session:
        media_assets = session.scalars(select(MediaAsset)).all()
        imported = [asset for asset in media_assets if asset.source_kind == "imported_original"]
        assert len(imported) == 6
        assert all(asset.visibility == "private" for asset in imported)
        assert any(
            asset.metadata_json.get("generation_reference_candidate") is True
            for asset in imported
            if asset.asset_kind == "image"
        )
        assert len(session.scalars(select(MediaObject)).all()) == 6
        assert session.scalars(select(WorldEventModel)).all() == []


def test_galgame_source_intake_requires_confirmation_and_existing_directory(
    tmp_path: Path,
) -> None:
    engine = _engine()
    graph = _seed_graph(engine)
    source_dir = _galgame_source_dir(tmp_path)

    with Session(engine) as session:
        service = GalgameSourceIntakeService(session, LocalMediaObjectStorage(tmp_path / "media"))
        with pytest.raises(ValueError, match="confirmation"):
            GalgameSourceIntakeApplyRequest(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                source_directory=str(source_dir),
                batch_key="demo-galgame",
                display_name="Demo Galgame",
            )
        with pytest.raises(AuthoringValidationError, match="existing directory"):
            service.preview(
                GalgameSourceIntakePreviewRequest(
                    world_id=graph.world_id,
                    worldline_id=graph.worldline_id,
                    source_directory=str(source_dir / "missing"),
                    batch_key="demo-galgame",
                    display_name="Demo Galgame",
                )
            )


def test_galgame_source_intake_does_not_extract_packed_sources(tmp_path: Path) -> None:
    engine = _engine()
    graph = _seed_graph(engine)
    source_dir = tmp_path / "packed"
    source_dir.mkdir()
    (source_dir / "game.xp3").write_bytes(b"packed")
    (source_dir / "archive.zip").write_bytes(b"packed")

    with Session(engine) as session:
        service = GalgameSourceIntakeService(session, LocalMediaObjectStorage(tmp_path / "media"))
        request = GalgameSourceIntakeApplyRequest(
            world_id=graph.world_id,
            worldline_id=graph.worldline_id,
            source_directory=str(source_dir),
            batch_key="packed",
            display_name="Packed",
            confirm_already_unpacked_user_provided=True,
        )
        preview = service.preview(request)
        with pytest.raises(AuthoringValidationError, match="no accepted files"):
            service.apply(request, actor_ref="test")

    assert preview.accepted_count == 0
    assert preview.rejected_count == 2
    assert all(
        item.reason == "archive, executable, or packed container is not accepted"
        for item in preview.files
    )


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
                "[emotion: happy]\n"
                "[relationship: Hero -> Alice: trust]\n"
                "@unknown_macro heroine pose=smile\n"
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

    assert result.created_proposal_count == 10
    assert result.dialogue_count == 2
    assert result.scene_count == 1
    assert result.choice_count == 2
    assert result.route_count == 1
    assert result.event_count == 1
    assert result.emotion_hint_count == 1
    assert result.relationship_hint_count == 1
    assert result.manual_label_count == 1
    assert result.unresolved_speaker_count == 2
    assert result.run.summary_json["parser_mode"] == "deterministic"
    assert result.run.summary_json["provider_execution"] is False
    assert all(
        proposal.source_fragment_id == fragment.id for proposal in result.run.proposals
    )
    proposals_by_kind = {
        proposal.target_ref_kind: proposal for proposal in result.run.proposals
    }
    dialogue = next(
        proposal
        for proposal in result.run.proposals
        if proposal.target_ref_kind == "dialogue_candidate"
        and proposal.proposed_payload_json.get("speaker_label") == "hero"
    )
    assert dialogue.proposed_payload_json["line_text"] == "hello"
    assert (
        proposals_by_kind["emotion_hint_candidate"].proposed_payload_json["emotion_key"]
        == "happy"
    )
    assert (
        proposals_by_kind["relationship_hint_candidate"].proposed_payload_json[
            "relationship_hint"
        ]
        == "Hero -> Alice: trust"
    )
    assert (
        proposals_by_kind["manual_label_candidate"].proposed_payload_json[
            "label_status"
        ]
        == "needs_review"
    )
    assert "@unknown_macro" in proposals_by_kind[
        "manual_label_candidate"
    ].proposed_payload_json["line_excerpt"]
    assert all(proposal.status == "proposed" for proposal in result.run.proposals)
    assert trace_count == 10


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


def test_conflict_review_creates_trace_only_conflict_reports() -> None:
    engine = _engine()
    graph = _seed_graph(engine)
    with Session(engine) as session:
        service = AuthoringService(session)
        batch = service.create_source_batch(
            AuthoringSourceBatchCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                batch_key="conflicts",
                display_name="Conflicts",
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
                source_label="conflicts.md",
            )
        )
        fragment = service.add_source_fragment(
            AuthoringSourceFragmentCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                source_asset_id=source_asset.id,
                fragment_key="conflicts",
                fragment_kind=AuthoringSourceFragmentKind.CHARACTER,
                sequence=1,
                excerpt_text="conflict fixture",
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
        service.preview(
            graph.world_id,
            run.id,
            AuthoringPreviewRequest(
                worldline_id=graph.worldline_id,
                proposals=(
                    _draft(
                        fragment.id,
                        "character_candidate",
                        {"candidate_kind": "character", "character_label": "Alice"},
                    ),
                    _draft(
                        fragment.id,
                        "character_candidate",
                        {"candidate_kind": "character", "character_label": "Alice"},
                    ),
                    _draft(
                        fragment.id,
                        "relationship_candidate",
                        {
                            "candidate_kind": "relationship",
                            "source_character_label": "Alice",
                            "target_character_label": "Bob",
                            "relationship_label": "trusts",
                        },
                        proposal_kind=AuthoringProposalKind.RELATIONSHIP,
                    ),
                    _draft(
                        fragment.id,
                        "relationship_candidate",
                        {
                            "candidate_kind": "relationship",
                            "source_character_label": "Alice",
                            "target_character_label": "Bob",
                            "relationship_label": "hates",
                        },
                        proposal_kind=AuthoringProposalKind.RELATIONSHIP,
                    ),
                    _draft(
                        fragment.id,
                        "identity_candidate",
                        {
                            "candidate_kind": "identity",
                            "character_label": "Alice",
                            "identity_value": "prefect",
                        },
                    ),
                    _draft(
                        fragment.id,
                        "identity_candidate",
                        {
                            "candidate_kind": "identity",
                            "character_label": "Alice",
                            "identity_value": "spy",
                        },
                    ),
                    _draft(
                        fragment.id,
                        "lore_candidate",
                        {
                            "candidate_kind": "lore",
                            "classification": "uncertain",
                            "lore_text": "maybe",
                        },
                    ),
                    _draft(
                        fragment.id,
                        "dialogue_candidate",
                        {"candidate_kind": "dialogue", "ooc_risk": True},
                    ),
                ),
            ),
        )
        result = service.review_conflicts(
            graph.world_id,
            run.id,
            AuthoringConflictReviewRequest(worldline_id=graph.worldline_id),
        )
        assert session.scalars(select(MediaJob)).all() == []
        assert session.scalars(select(WorldEventModel)).all() == []
        session.commit()

    assert result.created_proposal_count == 5
    assert result.duplicate_count == 1
    assert result.contradiction_count == 2
    assert result.uncertain_count == 1
    assert result.ooc_risk_count == 1
    assert result.run.summary_json["conflict_review_mode"] == "deterministic"
    assert result.run.summary_json["provider_execution"] is False
    reports = [
        proposal
        for proposal in result.run.proposals
        if proposal.target_ref_kind == "canon_conflict_report"
    ]
    assert len(reports) == 5
    assert all(proposal.proposal_kind == AuthoringProposalKind.OTHER for proposal in reports)
    assert "storage_uri" not in str(result.run.model_dump()).lower()


def test_memory_migration_creates_proposal_only_memory_candidates() -> None:
    engine = _engine()
    graph = _seed_graph(engine)
    with Session(engine) as session:
        service = AuthoringService(session)
        batch = service.create_source_batch(
            AuthoringSourceBatchCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                batch_key="memory",
                display_name="Memory",
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
                source_label="memory.md",
            )
        )
        fragment = service.add_source_fragment(
            AuthoringSourceFragmentCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                source_asset_id=source_asset.id,
                fragment_key="memory",
                fragment_kind=AuthoringSourceFragmentKind.MEMORY,
                sequence=1,
                excerpt_text=(
                    "fact: Magic exists\n"
                    "episode: Alice met Bob at the gate\n"
                    "relationship memory: Alice -> Bob: trusts him\n"
                    "preference: Alice = tea\n"
                    "style: Alice = terse\n"
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
        service.preview(
            graph.world_id,
            run.id,
            AuthoringPreviewRequest(
                worldline_id=graph.worldline_id,
                proposals=(
                    _draft(
                        fragment.id,
                        "lore_candidate",
                        {"candidate_kind": "lore", "lore_text": "The bell rings"},
                        proposal_kind=AuthoringProposalKind.LORE,
                    ),
                    _draft(
                        fragment.id,
                        "relationship_candidate",
                        {
                            "candidate_kind": "relationship",
                            "source_character_label": "Alice",
                            "target_character_label": "Bob",
                            "relationship_label": "trusts",
                        },
                        proposal_kind=AuthoringProposalKind.RELATIONSHIP,
                    ),
                    _draft(
                        fragment.id,
                        "dialogue_candidate",
                        {"candidate_kind": "dialogue", "speaker_label": "Alice"},
                        proposal_kind=AuthoringProposalKind.DIALOGUE,
                    ),
                ),
            ),
        )
        result = service.migrate_memory(
            graph.world_id,
            run.id,
            AuthoringMemoryMigrateRequest(
                worldline_id=graph.worldline_id,
                source_fragment_ids=(fragment.id,),
            ),
        )
        first_memory = [
            proposal
            for proposal in result.run.proposals
            if proposal.target_ref_kind == "memory_candidate"
        ][0]
        service.review_proposal(
            graph.world_id,
            first_memory.id,
            AuthoringReviewDecisionCreate(decision=AuthoringReviewDecisionKind.APPROVE),
            actor_ref="test",
        )
        apply_result = service.apply(
            graph.world_id,
            run.id,
            AuthoringApplyRequest(
                worldline_id=graph.worldline_id,
                proposal_ids=(first_memory.id,),
            ),
        )
        assert session.scalars(select(MediaJob)).all() == []
        assert session.scalars(select(WorldEventModel)).all() == []
        session.commit()

    assert result.created_proposal_count == 8
    assert result.fact_count == 2
    assert result.episodic_count == 1
    assert result.relationship_count == 2
    assert result.preference_count == 1
    assert result.style_count == 2
    assert result.run.summary_json["memory_migration_mode"] == "deterministic"
    assert result.run.summary_json["provider_execution"] is False
    assert apply_result.applied_proposals == []
    assert apply_result.blocked_proposals[0].applied_ref_json["blocked_reason"] == (
        "unsupported_proposal_kind"
    )
    assert "storage_uri" not in str(result.run.model_dump()).lower()


def test_character_memory_distillation_creates_reviewable_proposals() -> None:
    engine = _engine()
    graph = _seed_graph(engine)
    agent_id = _seed_agent(engine, graph.world_id, "alice", "Alice")
    with Session(engine) as session:
        provider_id = _seed_text_provider(session, graph.world_id)
        service = AuthoringService(session)
        batch = service.create_source_batch(
            AuthoringSourceBatchCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                batch_key="alice-source",
                display_name="Alice Source",
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
                source_label="alice.md",
            )
        )
        fragment = service.add_source_fragment(
            AuthoringSourceFragmentCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                source_asset_id=source_asset.id,
                fragment_key="alice",
                fragment_kind=AuthoringSourceFragmentKind.CHARACTER,
                sequence=1,
                excerpt_text=(
                    "Alice: I trust Bob.\n"
                    "emotion: Alice = guarded\n"
                    "secret: Alice hides the old key\n"
                    "route: alice\n"
                    "preference: Alice likes tea\n"
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
        result = service.distill_character_memory(
            graph.world_id,
            run.id,
            AuthoringCharacterMemoryDistillRequest(
                worldline_id=graph.worldline_id,
                agent_id=agent_id,
                source_fragment_ids=(fragment.id,),
                provider_id=provider_id,
            ),
            actor_ref="test",
        )
        proposals = result.run.proposals
        persona = next(
            proposal
            for proposal in proposals
            if proposal.target_ref_kind == "agent_persona_candidate"
        )
        memory = next(
            proposal for proposal in proposals if proposal.target_ref_kind == "memory_candidate"
        )
        visual = next(
            proposal
            for proposal in proposals
            if proposal.target_ref_kind == "visual_generation_profile_recommendation"
        )
        assert result.created_proposal_count >= 3
        assert result.persona_proposal_count == 1
        assert result.memory_candidate_count >= 1
        assert result.visual_profile_recommendation_count == 1
        assert result.provider_execution is True
        assert result.run.summary_json["provider_execution"] is True
        assert persona.proposed_payload_json["agent_id"] == str(agent_id)
        assert memory.proposed_payload_json["source_kind"] == "authoring_distillation"
        assert visual.proposed_payload_json["review_only"] is True
        assert session.scalars(select(AgentPersona)).all() == []
        assert session.scalars(select(AgentMemoryItem)).all() == []
        assert len(session.scalars(select(ModelInvocation)).all()) == 1
        assert len(session.scalars(select(PromptSnapshot)).all()) == 1
        assert session.scalars(select(WorldEventModel)).all() == []
        assert "raw_output" not in str(result.run.model_dump()).lower()
        assert "storage_uri" not in str(result.run.model_dump()).lower()
        assert "base64" not in str(result.run.model_dump()).lower()
        session.commit()


def test_character_memory_distillation_apply_writes_traceable_state() -> None:
    engine = _engine()
    graph = _seed_graph(engine)
    agent_id = _seed_agent(engine, graph.world_id, "alice", "Alice")
    with Session(engine) as session:
        provider_id = _seed_text_provider(session, graph.world_id)
        service = AuthoringService(session)
        batch = service.create_source_batch(
            AuthoringSourceBatchCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                batch_key="alice-source",
                display_name="Alice Source",
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
                source_label="alice.md",
            )
        )
        fragment = service.add_source_fragment(
            AuthoringSourceFragmentCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                source_asset_id=source_asset.id,
                fragment_key="alice",
                fragment_kind=AuthoringSourceFragmentKind.CHARACTER,
                sequence=1,
                excerpt_text="Alice: I trust Bob.\npreference: Alice likes tea",
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
        result = service.distill_character_memory(
            graph.world_id,
            run.id,
            AuthoringCharacterMemoryDistillRequest(
                worldline_id=graph.worldline_id,
                agent_id=agent_id,
                source_fragment_ids=(fragment.id,),
                provider_id=provider_id,
                include_visual_profile_recommendation=False,
            ),
            actor_ref="test",
        )
        proposal_ids = tuple(proposal.id for proposal in result.run.proposals)
        with pytest.raises(AuthoringValidationError, match="approved"):
            service.apply(
                graph.world_id,
                run.id,
                AuthoringApplyRequest(
                    worldline_id=graph.worldline_id,
                    proposal_ids=proposal_ids,
                ),
            )
        for proposal in result.run.proposals:
            service.review_proposal(
                graph.world_id,
                proposal.id,
                AuthoringReviewDecisionCreate(decision=AuthoringReviewDecisionKind.APPROVE),
                actor_ref="test",
            )
        applied = service.apply(
            graph.world_id,
            run.id,
            AuthoringApplyRequest(
                worldline_id=graph.worldline_id,
                proposal_ids=proposal_ids,
            ),
        )
        assert len(applied.applied_proposals) == len(proposal_ids)
        assert applied.blocked_proposals == []
        session.commit()

    with Session(engine) as session:
        persona = session.scalars(select(AgentPersona)).one()
        memory = session.scalars(select(AgentMemoryItem)).first()
        agent = session.get(Agent, agent_id)
        traces = session.scalars(select(AuthoringSourceTraceability)).all()
        assert agent is not None
        assert persona.persona_text
        assert persona.policy_plugin_config["authoring"]["source_kind"] == (
            "character_memory_distillation"
        )
        assert memory is not None
        assert memory.metadata_json["source_kind"] == "authoring_distillation"
        assert memory.metadata_json["proposal_id"]
        assert agent.character_profile["distilled_persona_source"]["model_invocation_id"]
        assert len([trace for trace in traces if trace.trace_kind == "proposal_applied"]) >= 2
        assert session.scalars(select(WorldEventModel)).all() == []


def test_asset_matching_applies_reviewed_visual_candidates() -> None:
    engine = _engine()
    graph = _seed_graph(engine)
    agent_id = _seed_agent(engine, graph.world_id, "alice", "Alice")
    sprite_media_id = graph.media_asset_id
    background_media_id = _seed_media_asset(
        engine,
        graph.world_id,
        graph.worldline_id,
        asset_kind="image",
        asset_role="scene_background",
    )
    cg_media_id = _seed_media_asset(
        engine,
        graph.world_id,
        graph.worldline_id,
        asset_kind="image",
        asset_role="event_cg",
    )
    voice_media_id = _seed_media_asset(
        engine,
        graph.world_id,
        graph.worldline_id,
        asset_kind="audio",
        asset_role="voice_sample",
    )
    hidden_media_id = _seed_media_asset(
        engine,
        graph.world_id,
        graph.worldline_id,
        asset_kind="image",
        asset_role="character_sprite",
        visibility="hidden",
    )
    with Session(engine) as session:
        service = AuthoringService(session)
        batch = service.create_source_batch(
            AuthoringSourceBatchCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                batch_key="assets",
                display_name="Assets",
                source_kind=AuthoringSourceAssetKind.IMAGE,
            ),
            actor_ref="test",
        )
        sprite_asset = service.add_source_asset(
            AuthoringSourceAssetCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                batch_id=batch.id,
                media_asset_id=sprite_media_id,
                source_asset_kind=AuthoringSourceAssetKind.IMAGE,
                source_label="alice-happy",
                metadata_json={
                    "character_label": "Alice",
                    "expression_key": "happy",
                    "pose_key": "standing",
                    "outfit_key": "uniform",
                },
            )
        )
        background_asset = service.add_source_asset(
            AuthoringSourceAssetCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                batch_id=batch.id,
                media_asset_id=background_media_id,
                source_asset_kind=AuthoringSourceAssetKind.IMAGE,
                source_label="schoolyard-day",
                metadata_json={
                    "location_key": "schoolyard",
                    "time_of_day": "day",
                    "weather_key": "clear",
                },
            )
        )
        cg_asset = service.add_source_asset(
            AuthoringSourceAssetCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                batch_id=batch.id,
                media_asset_id=cg_media_id,
                source_asset_kind=AuthoringSourceAssetKind.IMAGE,
                source_label="opening-cg",
                metadata_json={"cg_key": "opening", "route_key": "common"},
            )
        )
        voice_asset = service.add_source_asset(
            AuthoringSourceAssetCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                batch_id=batch.id,
                media_asset_id=voice_media_id,
                source_asset_kind=AuthoringSourceAssetKind.AUDIO,
                source_label="alice-voice",
                metadata_json={
                    "speaker_label": "Alice",
                    "voice_label": "alice-default",
                    "style_key": "soft",
                },
            )
        )
        hidden_asset = service.add_source_asset(
            AuthoringSourceAssetCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                batch_id=batch.id,
                media_asset_id=hidden_media_id,
                source_asset_kind=AuthoringSourceAssetKind.IMAGE,
                source_label="hidden",
                metadata_json={"character_label": "Hidden"},
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
        result = service.match_assets(
            graph.world_id,
            run.id,
            AuthoringAssetMatchRequest(
                worldline_id=graph.worldline_id,
                source_asset_ids=(
                    sprite_asset.id,
                    background_asset.id,
                    cg_asset.id,
                    voice_asset.id,
                    hidden_asset.id,
                ),
            ),
        )
        visual_matches = [
            proposal
            for proposal in result.run.proposals
            if proposal.target_ref_kind
            in {"sprite_asset_match", "background_asset_match", "cg_asset_match"}
        ]
        for proposal in visual_matches:
            service.review_proposal(
                graph.world_id,
                proposal.id,
                AuthoringReviewDecisionCreate(decision=AuthoringReviewDecisionKind.APPROVE),
                actor_ref="test",
            )
        apply_result = service.apply(
            graph.world_id,
            run.id,
            AuthoringApplyRequest(
                worldline_id=graph.worldline_id,
                proposal_ids=tuple(proposal.id for proposal in visual_matches),
            ),
        )
        assert session.scalars(select(MediaJob)).all() == []
        assert session.scalars(select(WorldEventModel)).all() == []
        session.commit()

    assert result.created_proposal_count == 4
    assert result.sprite_match_count == 1
    assert result.background_match_count == 1
    assert result.cg_match_count == 1
    assert result.voice_match_count == 1
    assert result.blocked_count == 1
    assert result.run.summary_json["asset_matching_mode"] == "deterministic"
    assert result.run.summary_json["provider_execution"] is False
    target_ref_kinds = {proposal.target_ref_kind for proposal in result.run.proposals}
    assert {
        "sprite_asset_match",
        "background_asset_match",
        "cg_asset_match",
        "voice_asset_match",
    }.issubset(target_ref_kinds)
    assert len(apply_result.applied_proposals) == 3
    assert apply_result.blocked_proposals == []
    assert "storage_uri" not in str(result.run.model_dump()).lower()

    with Session(engine) as session:
        sprite_set = session.scalars(select(CharacterSpriteSet)).one()
        variant = session.scalars(select(CharacterSpriteVariant)).one()
        background = session.scalars(select(SceneBackgroundProfile)).one()
        sprite_media = session.get(MediaAsset, sprite_media_id)
        background_media = session.get(MediaAsset, background_media_id)
        cg_media = session.get(MediaAsset, cg_media_id)
        assert sprite_set.agent_id == agent_id
        assert sprite_set.worldline_id == graph.worldline_id
        assert variant.expression_key == "happy"
        assert variant.pose_key == "standing"
        assert variant.outfit_key == "uniform"
        assert variant.asset_id == sprite_media_id
        assert background.location_key == "schoolyard"
        assert background.asset_id == background_media_id
        assert sprite_media is not None
        assert background_media is not None
        assert cg_media is not None
        assert sprite_media.metadata_json["generation_reference_candidate"] is True
        assert background_media.metadata_json["generation_reference_candidate"] is True
        assert cg_media.metadata_json["generation_reference_candidate"] is True
        assert cg_media.metadata_json["galgame_cg_bindings"][0]["cg_key"] == "opening"
        assert "storage_uri" not in str(sprite_set.metadata_json).lower()
        assert "storage_uri" not in str(variant.metadata_json).lower()
        assert "storage_uri" not in str(background.metadata_json).lower()
        assert session.scalars(select(WorldEventModel)).all() == []


def test_asset_matching_rejects_cross_worldline_source_asset() -> None:
    engine = _engine()
    graph = _seed_graph(engine)
    fork_id = _seed_fork(engine, graph.world_id, graph.worldline_id)
    fork_media_id = _seed_media_asset(
        engine,
        graph.world_id,
        fork_id,
        asset_kind="image",
        asset_role="character_sprite",
    )
    with Session(engine) as session:
        service = AuthoringService(session)
        main_batch = service.create_source_batch(
            AuthoringSourceBatchCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                batch_key="main-assets",
                display_name="Main Assets",
            ),
            actor_ref="test",
        )
        fork_batch = service.create_source_batch(
            AuthoringSourceBatchCreate(
                world_id=graph.world_id,
                worldline_id=fork_id,
                batch_key="fork-assets",
                display_name="Fork Assets",
            ),
            actor_ref="test",
        )
        fork_asset = service.add_source_asset(
            AuthoringSourceAssetCreate(
                world_id=graph.world_id,
                worldline_id=fork_id,
                batch_id=fork_batch.id,
                media_asset_id=fork_media_id,
                source_asset_kind=AuthoringSourceAssetKind.IMAGE,
                source_label="fork-sprite",
                metadata_json={"character_label": "Fork"},
            )
        )
        run = service.create_import_run(
            AuthoringImportRunCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                source_batch_id=main_batch.id,
            ),
            actor_ref="test",
        )
        with pytest.raises(AuthoringValidationError, match="worldline"):
            service.match_assets(
                graph.world_id,
                run.id,
                AuthoringAssetMatchRequest(
                    worldline_id=graph.worldline_id,
                    source_asset_ids=(fork_asset.id,),
                ),
            )


def test_visual_asset_mapping_apply_rejects_cross_worldline_media_payload() -> None:
    engine = _engine()
    graph = _seed_graph(engine)
    _seed_agent(engine, graph.world_id, "alice", "Alice")
    fork_id = _seed_fork(engine, graph.world_id, graph.worldline_id)
    fork_media_id = _seed_media_asset(
        engine,
        graph.world_id,
        fork_id,
        asset_kind="image",
        asset_role="character_sprite",
    )
    with Session(engine) as session:
        service = AuthoringService(session)
        batch = service.create_source_batch(
            AuthoringSourceBatchCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                batch_key="visual-cross",
                display_name="Visual Cross",
            ),
            actor_ref="test",
        )
        run = service.create_import_run(
            AuthoringImportRunCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                source_batch_id=batch.id,
            ),
            actor_ref="test",
        )
        proposal = service.create_proposal(
            AuthoringProposalCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                run_id=run.id,
                proposal_kind=AuthoringProposalKind.ASSET_MATCH,
                target_ref_kind="sprite_asset_match",
                title="Cross-worldline sprite",
                summary="Should not apply.",
                proposed_payload_json={
                    "candidate_kind": "asset_match",
                    "match_kind": "sprite",
                    "media_asset_id": str(fork_media_id),
                    "character_label": "Alice",
                    "expression_key": "neutral",
                },
            )
        )
        service.review_proposal(
            graph.world_id,
            proposal.id,
            AuthoringReviewDecisionCreate(decision=AuthoringReviewDecisionKind.APPROVE),
            actor_ref="test",
        )
        with pytest.raises(AuthoringValidationError, match="worldline"):
            service.apply(
                graph.world_id,
                run.id,
                AuthoringApplyRequest(
                    worldline_id=graph.worldline_id,
                    proposal_ids=(proposal.id,),
                ),
            )


def test_voice_asset_mapping_applies_reviewed_voice_reference_and_tts_smoke(
    tmp_path: Path,
) -> None:
    engine = _engine()
    graph = _seed_graph(engine)
    agent_id = _seed_agent(engine, graph.world_id, "alice", "Alice")
    voice_media_id = _seed_media_asset(
        engine,
        graph.world_id,
        graph.worldline_id,
        asset_kind="audio",
        asset_role="voice_sample",
    )
    with Session(engine) as session:
        tts_provider_id = _seed_speech_provider(session, graph.world_id)
        service = AuthoringService(session)
        batch = service.create_source_batch(
            AuthoringSourceBatchCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                batch_key="voices",
                display_name="Voices",
                source_kind=AuthoringSourceAssetKind.AUDIO,
            ),
            actor_ref="test",
        )
        voice_asset = service.add_source_asset(
            AuthoringSourceAssetCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                batch_id=batch.id,
                media_asset_id=voice_media_id,
                source_asset_kind=AuthoringSourceAssetKind.AUDIO,
                source_label="alice-soft",
                metadata_json={
                    "speaker_label": "Alice",
                    "voice_label": "soft",
                    "style_key": "gentle",
                    "emotion_key": "happy",
                    "provider_id": str(tts_provider_id),
                    "provider_voice_id": "alice_gateway_voice",
                    "supported_languages": ["ja", "zh"],
                },
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
        result = service.match_assets(
            graph.world_id,
            run.id,
            AuthoringAssetMatchRequest(
                worldline_id=graph.worldline_id,
                source_asset_ids=(voice_asset.id,),
            ),
        )
        voice_match = result.run.proposals[0]
        service.review_proposal(
            graph.world_id,
            voice_match.id,
            AuthoringReviewDecisionCreate(decision=AuthoringReviewDecisionKind.APPROVE),
            actor_ref="test",
        )
        applied = service.apply(
            graph.world_id,
            run.id,
            AuthoringApplyRequest(
                worldline_id=graph.worldline_id,
                proposal_ids=(voice_match.id,),
            ),
        )
        tts = SpeechService(session, LocalMediaObjectStorage(tmp_path / "speech")).text_to_speech(
            graph.world_id,
            TTSRequest(
                worldline_id=graph.worldline_id,
                provider_id=tts_provider_id,
                agent_id=agent_id,
                text="voice smoke",
                emotion="happy",
            ),
            actor_ref="test",
        )
        assert session.scalars(select(WorldEventModel)).all() == []
        session.commit()

    assert result.created_proposal_count == 1
    assert result.voice_match_count == 1
    assert len(applied.applied_proposals) == 1
    assert applied.blocked_proposals == []
    assert "storage_uri" not in str(applied.model_dump()).lower()
    assert "mimo-secret" not in str(applied.model_dump()).lower()

    with Session(engine) as session:
        profile = session.scalars(select(VoiceProfile)).one()
        binding = session.scalars(select(AgentVoiceProfileBinding)).one()
        voice_media = session.get(MediaAsset, voice_media_id)
        invocation = session.get(ModelInvocation, tts.model_invocation_id)
        assert profile.worldline_id == graph.worldline_id
        assert profile.owner_agent_id == agent_id
        assert profile.reference_asset_id == voice_media_id
        assert profile.provider_integration_id == tts_provider_id
        assert profile.provider_voice_id == "alice_gateway_voice"
        assert profile.supported_languages_json == ["ja", "zh"]
        assert profile.metadata_json["style_key"] == "gentle"
        assert profile.metadata_json["emotion_key"] == "happy"
        assert binding.agent_id == agent_id
        assert binding.voice_profile_id == profile.id
        assert binding.is_default is True
        assert binding.style_overrides_json == {"style_key": "gentle", "emotion": "happy"}
        assert voice_media is not None
        assert voice_media.metadata_json["voice_reference_candidate"] is True
        assert invocation is not None
        assert invocation.invocation_kind == "text_to_speech"
        assert invocation.request_params_json is not None
        assert invocation.request_params_json["request"]["provider_voice_id"] == (
            "alice_gateway_voice"
        )
        assert "mimo-secret" not in str(invocation.request_params_json).lower()
        assert session.scalars(select(WorldEventModel)).all() == []


def test_voice_asset_mapping_rejects_non_audio_payload() -> None:
    engine = _engine()
    graph = _seed_graph(engine)
    _seed_agent(engine, graph.world_id, "alice", "Alice")
    with Session(engine) as session:
        service = AuthoringService(session)
        batch = service.create_source_batch(
            AuthoringSourceBatchCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                batch_key="bad-voice",
                display_name="Bad Voice",
            ),
            actor_ref="test",
        )
        run = service.create_import_run(
            AuthoringImportRunCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                source_batch_id=batch.id,
            ),
            actor_ref="test",
        )
        proposal = service.create_proposal(
            AuthoringProposalCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                run_id=run.id,
                proposal_kind=AuthoringProposalKind.ASSET_MATCH,
                target_ref_kind="voice_asset_match",
                title="Bad voice",
                summary="Should not apply.",
                proposed_payload_json={
                    "candidate_kind": "asset_match",
                    "match_kind": "voice",
                    "media_asset_id": str(graph.media_asset_id),
                    "speaker_label": "Alice",
                },
            )
        )
        service.review_proposal(
            graph.world_id,
            proposal.id,
            AuthoringReviewDecisionCreate(decision=AuthoringReviewDecisionKind.APPROVE),
            actor_ref="test",
        )
        with pytest.raises(AuthoringValidationError, match="audio"):
            service.apply(
                graph.world_id,
                run.id,
                AuthoringApplyRequest(
                    worldline_id=graph.worldline_id,
                    proposal_ids=(proposal.id,),
                ),
            )


def test_demo_world_assembly_creates_reviewable_entry_session() -> None:
    engine = _engine()
    graph = _seed_graph(engine)
    alice_id = _seed_agent(engine, graph.world_id, "alice", "Alice")
    bob_id = _seed_agent(engine, graph.world_id, "bob", "Bob")
    alice_sprite_media_id = graph.media_asset_id
    bob_sprite_media_id = _seed_media_asset(
        engine,
        graph.world_id,
        graph.worldline_id,
        asset_kind="image",
        asset_role="character_sprite",
    )
    background_media_id = _seed_media_asset(
        engine,
        graph.world_id,
        graph.worldline_id,
        asset_kind="image",
        asset_role="scene_background",
    )
    alice_voice_media_id = _seed_media_asset(
        engine,
        graph.world_id,
        graph.worldline_id,
        asset_kind="audio",
        asset_role="voice_sample",
    )
    bob_voice_media_id = _seed_media_asset(
        engine,
        graph.world_id,
        graph.worldline_id,
        asset_kind="audio",
        asset_role="voice_sample",
    )
    with Session(engine) as session:
        service = AuthoringService(session)
        batch = service.create_source_batch(
            AuthoringSourceBatchCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                batch_key="demo-assembly",
                display_name="Demo Assembly",
            ),
            actor_ref="test",
        )
        source_asset = service.add_source_asset(
            AuthoringSourceAssetCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                batch_id=batch.id,
                source_asset_kind=AuthoringSourceAssetKind.SCRIPT,
                source_label="demo.ks",
            )
        )
        fragment = service.add_source_fragment(
            AuthoringSourceFragmentCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                source_asset_id=source_asset.id,
                fragment_key="opening",
                fragment_kind=AuthoringSourceFragmentKind.DIALOGUE,
                sequence=1,
                excerpt_text="Alice: We can start here.\nBob: I remember the gate.",
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
        dialogue = service.parse_script(
            graph.world_id,
            run.id,
            AuthoringScriptParseRequest(
                worldline_id=graph.worldline_id,
                source_fragment_ids=(fragment.id,),
            ),
        )
        dialogue_ids = tuple(
            proposal.id
            for proposal in dialogue.run.proposals
            if proposal.target_ref_kind == "dialogue_candidate"
        )
        for proposal_id in dialogue_ids:
            service.review_proposal(
                graph.world_id,
                proposal_id,
                AuthoringReviewDecisionCreate(decision=AuthoringReviewDecisionKind.APPROVE),
                actor_ref="test",
            )
        apply_ids = _create_demo_applied_evidence(
            service,
            graph.world_id,
            graph.worldline_id,
            run.id,
            fragment.id,
            {
                alice_id: {
                    "name": "Alice",
                    "sprite_media_id": alice_sprite_media_id,
                    "voice_media_id": alice_voice_media_id,
                },
                bob_id: {
                    "name": "Bob",
                    "sprite_media_id": bob_sprite_media_id,
                    "voice_media_id": bob_voice_media_id,
                },
            },
            background_media_id=background_media_id,
        )
        for proposal_id in apply_ids:
            service.review_proposal(
                graph.world_id,
                proposal_id,
                AuthoringReviewDecisionCreate(decision=AuthoringReviewDecisionKind.APPROVE),
                actor_ref="test",
            )
        applied = service.apply(
            graph.world_id,
            run.id,
            AuthoringApplyRequest(worldline_id=graph.worldline_id, proposal_ids=apply_ids),
        )
        profile = CharacterVisualGenerationProfile(
            id=uuid.uuid4(),
            world_id=graph.world_id,
            worldline_id=graph.worldline_id,
            agent_id=alice_id,
            preferred_checkpoint_id=None,
            allowed_lora_ids_json=[],
            default_lora_ids_json=[],
            banned_lora_ids_json=[],
            prompt_fragments_json={"subject": ["Alice"]},
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
        session.add(profile)
        session.flush()
        assembly = service.assemble_demo_world(
            graph.world_id,
            run.id,
            DemoWorldAssemblyRequest(
                worldline_id=graph.worldline_id,
                agent_ids=(alice_id, bob_id),
                dialogue_proposal_ids=dialogue_ids,
                persona_proposal_ids=_applied_ids_for_kind(
                    applied,
                    "agent_persona",
                ),
                memory_proposal_ids=_applied_ids_for_kind(
                    applied,
                    "agent_memory_item",
                ),
                visual_proposal_ids=_target_ids_for_kind(
                    applied,
                    {
                        "sprite_asset_match",
                        "background_asset_match",
                    },
                ),
                voice_proposal_ids=_target_ids_for_kind(applied, {"voice_asset_match"}),
                visual_profile_proposal_ids=_target_ids_for_kind(
                    applied,
                    {"visual_generation_profile_recommendation"},
                ),
                visual_generation_profile_ids=(profile.id,),
            ),
        )
        with pytest.raises(AuthoringValidationError, match="approved"):
            service.apply(
                graph.world_id,
                run.id,
                AuthoringApplyRequest(
                    worldline_id=graph.worldline_id,
                    proposal_ids=(assembly.proposal.id,),
                ),
            )
        service.review_proposal(
            graph.world_id,
            assembly.proposal.id,
            AuthoringReviewDecisionCreate(decision=AuthoringReviewDecisionKind.APPROVE),
            actor_ref="test",
        )
        assembly_apply = service.apply(
            graph.world_id,
            run.id,
            AuthoringApplyRequest(
                worldline_id=graph.worldline_id,
                proposal_ids=(assembly.proposal.id,),
            ),
        )
        session.commit()

    assert assembly.proposal.target_ref_kind == "demo_world_assembly"
    assert assembly.report_json["entry_supported"] is True
    assert assembly.report_json["provider_execution"] is False
    assert "storage_uri" not in assembly.model_dump_json().lower()
    assert "base64" not in assembly.model_dump_json().lower()
    assert len(assembly_apply.applied_proposals) == 1
    assert assembly_apply.blocked_proposals == []

    with Session(engine) as session:
        conversation = session.scalars(select(ConversationSession)).one()
        participants = session.scalars(select(ConversationParticipant)).all()
        turn = session.scalars(select(ConversationTurn)).one()
        presentation = session.scalars(select(ConversationTurnPresentation)).one()
        assert conversation.worldline_id == graph.worldline_id
        assert conversation.mode == "manual_chain"
        assert conversation.status == "draft"
        assert len(participants) == 2
        assert turn.output_text is not None
        assert turn.output_text.startswith("alice:")
        assert presentation.sprite_variant_id is not None
        assert presentation.background_asset_id == background_media_id
        assert presentation.voice_profile_id is not None
        assert "storage_uri" not in str(presentation.presentation_json).lower()
        assert session.scalars(select(WorldEventModel)).all() == []


def test_demo_world_assembly_blocks_missing_memory_evidence() -> None:
    engine = _engine()
    graph = _seed_graph(engine)
    alice_id = _seed_agent(engine, graph.world_id, "alice", "Alice")
    bob_id = _seed_agent(engine, graph.world_id, "bob", "Bob")
    with Session(engine) as session:
        service = AuthoringService(session)
        batch = service.create_source_batch(
            AuthoringSourceBatchCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                batch_key="demo-missing",
                display_name="Demo Missing",
            ),
            actor_ref="test",
        )
        source_asset = service.add_source_asset(
            AuthoringSourceAssetCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                batch_id=batch.id,
                source_label="demo.ks",
            )
        )
        fragment = service.add_source_fragment(
            AuthoringSourceFragmentCreate(
                world_id=graph.world_id,
                worldline_id=graph.worldline_id,
                source_asset_id=source_asset.id,
                fragment_key="opening",
                fragment_kind=AuthoringSourceFragmentKind.DIALOGUE,
                sequence=1,
                excerpt_text="Alice: ready",
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
        dialogue = service.parse_script(
            graph.world_id,
            run.id,
            AuthoringScriptParseRequest(
                worldline_id=graph.worldline_id,
                source_fragment_ids=(fragment.id,),
            ),
        )
        dialogue_ids = tuple(
            proposal.id
            for proposal in dialogue.run.proposals
            if proposal.target_ref_kind == "dialogue_candidate"
        )
        for proposal_id in dialogue_ids:
            service.review_proposal(
                graph.world_id,
                proposal_id,
                AuthoringReviewDecisionCreate(decision=AuthoringReviewDecisionKind.APPROVE),
                actor_ref="test",
            )
        persona_ids = tuple(
            service.create_proposal(
                AuthoringProposalCreate(
                    world_id=graph.world_id,
                    worldline_id=graph.worldline_id,
                    run_id=run.id,
                    source_fragment_id=fragment.id,
                    proposal_kind=AuthoringProposalKind.CHARACTER,
                    target_ref_kind="agent_persona_candidate",
                    target_ref_id=agent_id,
                    title=f"{name} persona",
                    summary="Traceable persona.",
                    proposed_payload_json={
                        "agent_id": str(agent_id),
                        "persona_text": f"{name} is ready.",
                    },
                )
            ).id
            for agent_id, name in ((alice_id, "Alice"), (bob_id, "Bob"))
        )
        for proposal_id in persona_ids:
            service.review_proposal(
                graph.world_id,
                proposal_id,
                AuthoringReviewDecisionCreate(decision=AuthoringReviewDecisionKind.APPROVE),
                actor_ref="test",
            )
        applied_persona = service.apply(
            graph.world_id,
            run.id,
            AuthoringApplyRequest(
                worldline_id=graph.worldline_id,
                proposal_ids=persona_ids,
            ),
        )
        with pytest.raises(AuthoringValidationError, match="memory"):
            service.assemble_demo_world(
                graph.world_id,
                run.id,
                DemoWorldAssemblyRequest(
                    worldline_id=graph.worldline_id,
                    agent_ids=(alice_id, bob_id),
                    dialogue_proposal_ids=dialogue_ids,
                    persona_proposal_ids=_applied_ids_for_kind(
                        applied_persona,
                        "agent_persona",
                    ),
                ),
            )


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
    with pytest.raises(ValueError, match="storage"):
        AuthoringSourceBatchCreate(
            world_id=graph_id,
            worldline_id=uuid.uuid4(),
            batch_key="bad",
            display_name="Bad",
            metadata_json={"nested": {"storageUri": "opaque-storage-ref"}},
        )
    with pytest.raises(ValueError, match="base64"):
        AuthoringProposalDraft(
            title="Bad",
            summary="Bad",
            evidence_json={"image": "data:image/png;base64,abc"},
        )


def test_beta_content_repairs_create_reviewable_proposals_without_mutation() -> None:
    engine = _engine()
    graph = _seed_graph(engine)
    agent_id = _seed_agent(engine, graph.world_id, "alice", "Alice")
    feedback_id = uuid.uuid4()
    diagnostic_id = uuid.uuid4()

    with Session(engine) as session:
        service = AuthoringService(session)
        result = service.create_beta_content_repairs(
            graph.world_id,
            BetaContentRepairRequest(
                worldline_id=graph.worldline_id,
                candidates=(
                    BetaContentRepairCandidate(
                        repair_kind=BetaContentRepairKind.PERSONA,
                        target_ref_id=agent_id,
                        feedback_report_ids=(feedback_id,),
                        diagnostic_refs=(
                            {
                                "kind": "memory_persona_qa",
                                "id": str(diagnostic_id),
                                "label": "OOC drift",
                            },
                        ),
                        title="Repair Alice persona",
                        summary="Tune Alice back to source persona.",
                        proposed_payload_json={
                            "persona_text": "Alice is careful and source-grounded.",
                        },
                        evidence_json={"issue": "ooc"},
                    ),
                    BetaContentRepairCandidate(
                        repair_kind=BetaContentRepairKind.PROVIDER_PROFILE,
                        feedback_report_ids=(feedback_id,),
                        title="Review provider prompt profile",
                        summary="Provider profile needs admin review.",
                        proposed_payload_json={"recommendation": "tighten style preset"},
                    ),
                ),
            ),
            actor_ref="test",
        )

        assert result.run.status.value == "previewed"
        assert result.impact.proposal_count == 2
        assert result.impact.feedback_report_count == 1
        assert result.impact.repair_counts == {"persona": 1, "provider_profile": 1}
        assert [proposal.status.value for proposal in result.proposals] == [
            "proposed",
            "proposed",
        ]
        assert result.proposals[0].target_ref_kind == "agent_persona_candidate"
        assert result.proposals[0].evidence_json["feedback_report_ids"] == [str(feedback_id)]
        assert result.proposals[1].target_ref_kind == "provider_profile_repair_candidate"
        assert result.proposals[1].proposed_payload_json["review_only"] is True
        assert session.scalars(select(AgentPersona)).all() == []
        assert session.scalars(select(AgentMemoryItem)).all() == []
        assert session.scalars(select(WorldEventModel)).all() == []


def test_beta_content_repair_apply_uses_existing_review_apply_path() -> None:
    engine = _engine()
    graph = _seed_graph(engine)
    agent_id = _seed_agent(engine, graph.world_id, "alice", "Alice")

    with Session(engine) as session:
        service = AuthoringService(session)
        result = service.create_beta_content_repairs(
            graph.world_id,
            BetaContentRepairRequest(
                worldline_id=graph.worldline_id,
                candidates=(
                    BetaContentRepairCandidate(
                        repair_kind=BetaContentRepairKind.PERSONA,
                        target_ref_id=agent_id,
                        title="Repair Alice persona",
                        summary="Update persona through review/apply.",
                        proposed_payload_json={
                            "persona_text": "Alice is calm under pressure.",
                        },
                    ),
                    BetaContentRepairCandidate(
                        repair_kind=BetaContentRepairKind.MEMORY,
                        target_ref_id=agent_id,
                        title="Repair Alice memory",
                        summary="Add source-grounded beta repair memory.",
                        proposed_payload_json={
                            "content": "Alice remembers the beta opening scene.",
                            "memory_kind": "fact",
                        },
                    ),
                ),
            ),
            actor_ref="test",
        )
        proposal_ids = tuple(proposal.id for proposal in result.proposals)
        for proposal_id in proposal_ids:
            service.review_proposal(
                graph.world_id,
                proposal_id,
                AuthoringReviewDecisionCreate(decision=AuthoringReviewDecisionKind.APPROVE),
                actor_ref="reviewer",
            )

        applied = service.apply(
            graph.world_id,
            result.run.id,
            AuthoringApplyRequest(
                worldline_id=graph.worldline_id,
                proposal_ids=proposal_ids,
            ),
        )

        applied_ref_kinds = {
            proposal.applied_ref_json["applied_ref_kind"]
            for proposal in applied.applied_proposals
        }
        assert applied_ref_kinds == {
            "agent_persona",
            "agent_memory_item",
        }
        persona = session.scalars(select(AgentPersona)).one()
        memory = session.scalars(select(AgentMemoryItem)).one()
        assert "calm under pressure" in persona.persona_text
        assert memory.worldline_id == graph.worldline_id
        assert memory.metadata_json["source_kind"] == "authoring_distillation"


def _draft(
    source_fragment_id: uuid.UUID,
    target_ref_kind: str,
    payload: dict[str, Any],
    *,
    proposal_kind: AuthoringProposalKind = AuthoringProposalKind.CHARACTER,
) -> AuthoringProposalDraft:
    return AuthoringProposalDraft(
        source_fragment_id=source_fragment_id,
        proposal_kind=proposal_kind,
        target_ref_kind=target_ref_kind,
        title=f"{target_ref_kind} draft",
        summary="Draft for conflict review.",
        proposed_payload_json=payload,
    )


def _create_demo_applied_evidence(
    service: AuthoringService,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    run_id: uuid.UUID,
    fragment_id: uuid.UUID,
    agents: dict[uuid.UUID, dict[str, object]],
    *,
    background_media_id: uuid.UUID,
) -> tuple[uuid.UUID, ...]:
    proposal_ids: list[uuid.UUID] = []
    for agent_id, data in agents.items():
        name = str(data["name"])
        sprite_media_id = cast(uuid.UUID, data["sprite_media_id"])
        voice_media_id = cast(uuid.UUID, data["voice_media_id"])
        proposal_ids.extend(
            [
                service.create_proposal(
                    AuthoringProposalCreate(
                        world_id=world_id,
                        worldline_id=worldline_id,
                        run_id=run_id,
                        source_fragment_id=fragment_id,
                        proposal_kind=AuthoringProposalKind.CHARACTER,
                        target_ref_kind="agent_persona_candidate",
                        target_ref_id=agent_id,
                        title=f"{name} persona",
                        summary="Traceable persona.",
                        proposed_payload_json={
                            "agent_id": str(agent_id),
                            "persona_text": f"{name} is ready for demo play.",
                            "behavior_policy": {"source": "test"},
                            "character_profile": {"speech_style": "calm"},
                        },
                    )
                ).id,
                service.create_proposal(
                    AuthoringProposalCreate(
                        world_id=world_id,
                        worldline_id=worldline_id,
                        run_id=run_id,
                        source_fragment_id=fragment_id,
                        proposal_kind=AuthoringProposalKind.MEMORY,
                        target_ref_kind="memory_candidate",
                        target_ref_id=agent_id,
                        title=f"{name} memory",
                        summary="Traceable memory.",
                        proposed_payload_json={
                            "source_kind": "authoring_distillation",
                            "agent_id": str(agent_id),
                            "content": f"{name} remembers the opening scene.",
                            "memory_kind": "fact",
                        },
                    )
                ).id,
                service.create_proposal(
                    AuthoringProposalCreate(
                        world_id=world_id,
                        worldline_id=worldline_id,
                        run_id=run_id,
                        source_fragment_id=fragment_id,
                        proposal_kind=AuthoringProposalKind.ASSET_MATCH,
                        target_ref_kind="sprite_asset_match",
                        title=f"{name} sprite",
                        summary="Traceable sprite.",
                        proposed_payload_json={
                            "media_asset_id": str(sprite_media_id),
                            "agent_id": str(agent_id),
                            "character_label": name,
                            "expression_key": "neutral",
                        },
                    )
                ).id,
                service.create_proposal(
                    AuthoringProposalCreate(
                        world_id=world_id,
                        worldline_id=worldline_id,
                        run_id=run_id,
                        source_fragment_id=fragment_id,
                        proposal_kind=AuthoringProposalKind.ASSET_MATCH,
                        target_ref_kind="voice_asset_match",
                        title=f"{name} voice",
                        summary="Traceable voice.",
                        proposed_payload_json={
                            "media_asset_id": str(voice_media_id),
                            "agent_id": str(agent_id),
                            "speaker_label": name,
                            "voice_label": "default",
                        },
                    )
                ).id,
                service.create_proposal(
                    AuthoringProposalCreate(
                        world_id=world_id,
                        worldline_id=worldline_id,
                        run_id=run_id,
                        source_fragment_id=fragment_id,
                        proposal_kind=AuthoringProposalKind.ASSET_MATCH,
                        target_ref_kind="visual_generation_profile_recommendation",
                        target_ref_id=agent_id,
                        title=f"{name} visual generation profile",
                        summary="Traceable visual generation profile recommendation.",
                        proposed_payload_json={
                            "agent_id": str(agent_id),
                            "review_only": True,
                            "recommended_prompt_fragments": [name],
                        },
                    )
                ).id,
            ]
        )
    proposal_ids.append(
        service.create_proposal(
            AuthoringProposalCreate(
                world_id=world_id,
                worldline_id=worldline_id,
                run_id=run_id,
                source_fragment_id=fragment_id,
                proposal_kind=AuthoringProposalKind.ASSET_MATCH,
                target_ref_kind="background_asset_match",
                title="Opening background",
                summary="Traceable background.",
                proposed_payload_json={
                    "media_asset_id": str(background_media_id),
                    "location_key": "opening",
                },
            )
        ).id
    )
    return tuple(proposal_ids)


def _applied_ids_for_kind(
    result: AuthoringApplyResult,
    applied_ref_kind: str,
) -> tuple[uuid.UUID, ...]:
    return tuple(
        proposal.id
        for proposal in result.applied_proposals
        if proposal.applied_ref_json.get("applied_ref_kind") == applied_ref_kind
    )


def _target_ids_for_kind(
    result: AuthoringApplyResult,
    target_ref_kinds: set[str],
) -> tuple[uuid.UUID, ...]:
    return tuple(
        proposal.id
        for proposal in result.applied_proposals
        if proposal.target_ref_kind in target_ref_kinds
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


def _seed_text_provider(session: Session, world_id: uuid.UUID) -> uuid.UUID:
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
    return provider.id


def _seed_speech_provider(session: Session, world_id: uuid.UUID) -> uuid.UUID:
    provider = ProviderRegistryService(session).create_provider(
        ProviderIntegrationCreate(
            world_id=world_id,
            scope_kind=ProviderScopeKind.WORLD,
            provider_kind=ProviderKind.TEXT_TO_SPEECH,
            adapter_kind=ProviderAdapterKind.FAKE,
            provider_key=f"fake-tts-{uuid.uuid4().hex[:8]}",
            display_name="Fake TTS",
            base_url="https://gateway.example",
            auth_ref="env:MIMO_SECRET",
            config_json={"dry_run": True},
            default_params_json={"model_name": "mimo-voice-model"},
            capabilities=(
                ProviderCapabilityCreate(
                    capability_key="supports_tts",
                    capability_json={"value": True},
                ),
            ),
        )
    )
    return provider.id


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


def _seed_media_asset(
    engine: Engine,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    *,
    asset_kind: str = "document",
    asset_role: str = "document",
    visibility: str = "world_admin",
) -> uuid.UUID:
    with Session(engine) as session:
        media_asset_id = _add_media_asset(
            session,
            world_id,
            worldline_id,
            asset_kind=asset_kind,
            asset_role=asset_role,
            visibility=visibility,
        )
        session.commit()
        return media_asset_id


def _add_media_asset(
    session: Session,
    world_id: uuid.UUID,
    worldline_id: uuid.UUID,
    *,
    asset_kind: str = "image",
    asset_role: str = "character_sprite",
    visibility: str = "world_admin",
) -> uuid.UUID:
    media_asset_id = uuid.uuid4()
    session.add(
        MediaAsset(
            id=media_asset_id,
            world_id=world_id,
            worldline_id=worldline_id,
            asset_kind=asset_kind,
            asset_role=asset_role,
            source_kind="manual_upload",
            status="available",
            visibility=visibility,
            mime_type="image/png" if asset_kind == "image" else "audio/wav",
            checksum_sha256="a" * 64,
            created_by_actor_ref="test",
            metadata_json={},
        )
    )
    return media_asset_id


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
