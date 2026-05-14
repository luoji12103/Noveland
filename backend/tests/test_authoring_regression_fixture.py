from __future__ import annotations

from noveland.authoring.models import (
    AuthoringImportProposal,
    AuthoringImportRun,
    AuthoringSourceAsset,
    AuthoringSourceBatch,
    AuthoringSourceFragment,
    AuthoringSourceTraceability,
)
from noveland.events.models import WorldEventModel
from noveland.media.models import MediaJob
from noveland.memory.models import MemoryWriteJob
from noveland.speech.models import AgentVoiceProfileBinding, VoiceProfile
from noveland.visual.models import CharacterSpriteSet, CharacterSpriteVariant
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.fixtures.authoring_sample_import import create_authoring_sample_import


def test_authoring_sample_fixture_has_deterministic_signature() -> None:
    first = create_authoring_sample_import()
    second = create_authoring_sample_import()

    assert first.world_id == second.world_id
    assert first.worldline_id == second.worldline_id
    assert first.admin_user_id == second.admin_user_id
    assert first.media_asset_ids == second.media_asset_ids
    assert first.proposal_counts == second.proposal_counts
    assert first.target_ref_counts == second.target_ref_counts


def test_authoring_sample_fixture_is_worldline_scoped() -> None:
    sample = create_authoring_sample_import()

    with Session(sample.engine) as session:
        batches = session.scalars(select(AuthoringSourceBatch)).all()
        assets = session.scalars(select(AuthoringSourceAsset)).all()
        fragments = session.scalars(select(AuthoringSourceFragment)).all()
        runs = session.scalars(select(AuthoringImportRun)).all()
        proposals = session.scalars(select(AuthoringImportProposal)).all()
        traces = session.scalars(select(AuthoringSourceTraceability)).all()

    assert batches
    assert assets
    assert fragments
    assert runs
    assert proposals
    assert {batch.world_id for batch in batches} == {sample.world_id}
    assert {asset.world_id for asset in assets} == {sample.world_id}
    assert {fragment.world_id for fragment in fragments} == {sample.world_id}
    assert {run.world_id for run in runs} == {sample.world_id}
    assert {proposal.world_id for proposal in proposals} == {sample.world_id}
    assert {trace.world_id for trace in traces} == {sample.world_id}
    assert {batch.worldline_id for batch in batches} == {sample.worldline_id}
    assert {asset.worldline_id for asset in assets} == {sample.worldline_id}
    assert {fragment.worldline_id for fragment in fragments} == {sample.worldline_id}
    assert {run.worldline_id for run in runs} == {sample.worldline_id}
    assert {proposal.worldline_id for proposal in proposals} == {sample.worldline_id}
    assert {trace.worldline_id for trace in traces} == {sample.worldline_id}


def test_authoring_sample_fixture_covers_pipeline_and_guarded_apply() -> None:
    sample = create_authoring_sample_import()

    assert sample.proposal_counts["dialogue"] >= 2
    assert sample.proposal_counts["character"] >= 2
    assert sample.proposal_counts["relationship"] >= 1
    assert sample.proposal_counts["lore"] >= 7
    assert sample.proposal_counts["memory"] >= 5
    assert sample.proposal_counts["asset_match"] == 4
    assert sample.proposal_counts["other"] >= 1
    assert sample.target_ref_counts["canon_conflict_report"] >= 1
    assert sample.target_ref_counts["memory_candidate"] >= 5
    assert sample.target_ref_counts["sprite_asset_match"] == 1
    assert sample.target_ref_counts["background_asset_match"] == 1
    assert sample.target_ref_counts["cg_asset_match"] == 1
    assert sample.target_ref_counts["voice_asset_match"] == 1

    with Session(sample.engine) as session:
        applied = session.get(AuthoringImportProposal, sample.applied_other_proposal_id)
        blocked = session.get(AuthoringImportProposal, sample.blocked_proposal_id)

    assert applied is not None
    assert blocked is not None
    assert applied.status == "applied"
    assert applied.applied_ref_json["canonical_mutation"] is False
    assert blocked.status == "blocked"
    assert blocked.applied_ref_json["blocked_reason"] == "unsupported_proposal_kind"


def test_authoring_sample_fixture_has_no_runtime_or_media_side_effects() -> None:
    sample = create_authoring_sample_import()

    with Session(sample.engine) as session:
        assert session.scalars(select(WorldEventModel)).all() == []
        assert session.scalars(select(MediaJob)).all() == []
        assert session.scalars(select(MemoryWriteJob)).all() == []
        assert session.scalars(select(CharacterSpriteSet)).all() == []
        assert session.scalars(select(CharacterSpriteVariant)).all() == []
        assert session.scalars(select(VoiceProfile)).all() == []
        assert session.scalars(select(AgentVoiceProfileBinding)).all() == []
        proposals = session.scalars(select(AuthoringImportProposal)).all()

    serialized = str(
        [
            {
                "payload": proposal.proposed_payload_json,
                "evidence": proposal.evidence_json,
                "applied_ref": proposal.applied_ref_json,
            }
            for proposal in proposals
        ]
    ).lower()
    for forbidden in (
        "storage_uri",
        "file://",
        "local://",
        "base64",
        "raw_prompt",
        "raw_output",
        "full_raw_source",
    ):
        assert forbidden not in serialized
