from __future__ import annotations

import re
import uuid
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from noveland.agents.models import Agent
from noveland.events.models import WorldEventModel
from noveland.invocations.models import ModelInvocation, PromptSnapshot
from noveland.media.models import MediaAsset, MediaJob, MediaObject
from noveland.media.storage import MediaObjectStorage
from noveland.memory.models import MemoryWriteJob
from noveland.providers.models import ProviderHealthCheck, ProviderIntegration
from noveland.providers.secrets import REDACTED, is_sensitive_key
from noveland.speech.models import AgentVoiceProfileBinding, SpeechTranscript, VoiceProfile
from noveland.visual.models import (
    CharacterSpriteSet,
    CharacterSpriteVariant,
    SceneBackgroundProfile,
)
from noveland.worlds.models import LongRunEvalRun
from noveland.worlds.worldlines import worldline_or_404
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .contracts import (
    DEFAULT_MULTIMODAL_EVAL_KEY,
    MultimodalDiagnosticFinding,
    MultimodalDiagnosticsResult,
    MultimodalEvalRunRead,
    MultimodalEvalRunRequest,
    MultimodalEvalStatus,
    MultimodalEvidenceRef,
    MultimodalFindingSeverity,
)


class MultimodalEvalNotFoundError(LookupError):
    pass


class MultimodalEvalService:
    def __init__(
        self,
        session: Session,
        storage: MediaObjectStorage | None = None,
    ) -> None:
        self._session = session
        self._storage = storage

    def diagnostics(
        self,
        world_id: uuid.UUID,
        *,
        worldline_id: uuid.UUID | None = None,
    ) -> MultimodalDiagnosticsResult:
        resolved_worldline_id = worldline_or_404(self._session, world_id, worldline_id).id
        now = datetime.now(UTC)
        blockers: list[MultimodalDiagnosticFinding] = []
        warnings: list[MultimodalDiagnosticFinding] = []
        evidence_refs: list[MultimodalEvidenceRef] = []

        metrics: dict[str, Any] = {}
        metrics["providers"] = self._provider_metrics(world_id, warnings, evidence_refs)
        metrics["invocations"] = self._invocation_metrics(
            world_id,
            resolved_worldline_id,
            blockers,
            warnings,
        )
        metrics["media_jobs"] = self._media_job_metrics(world_id, resolved_worldline_id, blockers)
        metrics["media_assets"] = self._media_asset_metrics(
            world_id,
            resolved_worldline_id,
            blockers,
            warnings,
        )
        metrics["visual"] = self._visual_metrics(world_id, resolved_worldline_id, blockers)
        metrics["speech"] = self._speech_metrics(world_id, resolved_worldline_id, blockers)
        metrics["events"] = self._event_payload_metrics(world_id, resolved_worldline_id, blockers)

        recommendations = _recommendations(blockers=blockers, warnings=warnings)
        status = _status(blockers=blockers, warnings=warnings)
        return MultimodalDiagnosticsResult(
            world_id=world_id,
            worldline_id=resolved_worldline_id,
            status=status,
            metrics=metrics,
            blockers=blockers,
            warnings=warnings,
            recommendations=recommendations,
            evidence_refs=evidence_refs,
            generated_at=now,
        )

    def run_eval(
        self,
        world_id: uuid.UUID,
        request: MultimodalEvalRunRequest,
    ) -> MultimodalEvalRunRead:
        started_at = datetime.now(UTC)
        diagnostics = self.diagnostics(world_id, worldline_id=request.worldline_id)
        finished_at = datetime.now(UTC)
        run = LongRunEvalRun(
            id=uuid.uuid4(),
            world_id=world_id,
            worldline_id=diagnostics.worldline_id,
            eval_key=request.eval_key,
            horizon_days=request.horizon_days,
            status=diagnostics.status.value,
            started_at=started_at,
            finished_at=finished_at,
            metrics=diagnostics.metrics,
            recommendations=[
                {"message": recommendation} for recommendation in diagnostics.recommendations
            ],
            blockers=[
                _finding_to_json(finding)
                for finding in (*diagnostics.blockers, *diagnostics.warnings)
            ],
            metadata_json={
                **request.metadata,
                "diagnostic_eval_key": DEFAULT_MULTIMODAL_EVAL_KEY,
                "warning_count": len(diagnostics.warnings),
                "blocker_count": len(diagnostics.blockers),
                "evidence_refs": [_evidence_ref_to_json(ref) for ref in diagnostics.evidence_refs],
            },
        )
        self._session.add(run)
        self._session.flush()
        self._session.refresh(run)
        return _run_record(run)

    def list_runs(
        self,
        world_id: uuid.UUID,
        *,
        worldline_id: uuid.UUID | None = None,
        limit: int = 20,
    ) -> list[MultimodalEvalRunRead]:
        resolved_worldline_id = worldline_or_404(self._session, world_id, worldline_id).id
        runs = self._session.scalars(
            select(LongRunEvalRun)
            .where(
                LongRunEvalRun.world_id == world_id,
                LongRunEvalRun.worldline_id == resolved_worldline_id,
                LongRunEvalRun.eval_key.like("multimodal-%"),
            )
            .order_by(LongRunEvalRun.created_at.desc())
            .limit(limit),
        ).all()
        return [_run_record(run) for run in runs]

    def get_run(self, world_id: uuid.UUID, run_id: uuid.UUID) -> MultimodalEvalRunRead:
        run = self._session.get(LongRunEvalRun, run_id)
        if run is None or run.world_id != world_id or not run.eval_key.startswith("multimodal-"):
            raise MultimodalEvalNotFoundError("multimodal eval run not found")
        return _run_record(run)

    def _provider_metrics(
        self,
        world_id: uuid.UUID,
        warnings: list[MultimodalDiagnosticFinding],
        evidence_refs: list[MultimodalEvidenceRef],
    ) -> dict[str, Any]:
        providers = self._session.scalars(
            select(ProviderIntegration).where(
                (ProviderIntegration.world_id == world_id)
                | (ProviderIntegration.scope_kind == "global")
            )
        ).all()
        health_checks = self._session.scalars(select(ProviderHealthCheck)).all()
        health_by_provider: dict[uuid.UUID, ProviderHealthCheck] = {}
        for check in sorted(health_checks, key=lambda item: item.checked_at):
            health_by_provider[check.provider_integration_id] = check

        unsafe_provider_ids: list[str] = []
        providers_without_health: list[str] = []
        configured_auth_count = 0
        for provider in providers:
            if provider.auth_ref:
                configured_auth_count += 1
            if _contains_secret_value(provider.config_json) or _contains_secret_value(
                provider.default_params_json
            ):
                unsafe_provider_ids.append(str(provider.id))
            if provider.id not in health_by_provider:
                providers_without_health.append(str(provider.id))

        if unsafe_provider_ids:
            warnings.append(
                _finding(
                    code="provider_secret_boundary",
                    severity=MultimodalFindingSeverity.WARNING,
                    message="Provider configuration contains unredacted secret-like values.",
                    refs=[("provider_integration", item) for item in unsafe_provider_ids],
                )
            )
        if providers_without_health:
            warnings.append(
                _finding(
                    code="provider_health_missing",
                    severity=MultimodalFindingSeverity.WARNING,
                    message="Some provider integrations do not have health or smoke evidence.",
                    refs=[("provider_integration", item) for item in providers_without_health],
                )
            )
        evidence_refs.extend(
            MultimodalEvidenceRef(kind="provider_integration", id=str(provider.id))
            for provider in providers
        )
        status_counts = Counter(check.status for check in health_checks)
        return {
            "configured_count": len(providers),
            "auth_ref_configured_count": configured_auth_count,
            "health_status_counts": dict(status_counts),
            "providers_without_health_count": len(providers_without_health),
            "unsafe_provider_config_count": len(unsafe_provider_ids),
        }

    def _invocation_metrics(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        blockers: list[MultimodalDiagnosticFinding],
        warnings: list[MultimodalDiagnosticFinding],
    ) -> dict[str, Any]:
        invocations = self._session.scalars(
            select(ModelInvocation).where(
                ModelInvocation.world_id == world_id,
                ModelInvocation.worldline_id == worldline_id,
            )
        ).all()
        snapshots = self._session.scalars(
            select(PromptSnapshot).join(
                ModelInvocation,
                PromptSnapshot.invocation_id == ModelInvocation.id,
            )
            .where(
                ModelInvocation.world_id == world_id,
                ModelInvocation.worldline_id == worldline_id,
            )
        ).all()
        snapshot_invocation_ids = {snapshot.invocation_id for snapshot in snapshots}
        provider_invocations = [
            invocation
            for invocation in invocations
            if invocation.invocation_kind
            in {
                "image_generation",
                "image_edit",
                "image_analysis",
                "speech_to_text",
                "text_to_speech",
                "voice_clone",
            }
        ]
        missing_snapshot_ids = [
            str(invocation.id)
            for invocation in provider_invocations
            if invocation.id not in snapshot_invocation_ids
        ]
        prompt_leak_ids = [
            str(snapshot.id)
            for snapshot in snapshots
            if snapshot.redaction_status == "raw" or _snapshot_contains_leak(snapshot)
        ]
        secret_leak_ids = [
            str(snapshot.id)
            for snapshot in snapshots
            if _snapshot_contains_secret(snapshot)
        ]
        if missing_snapshot_ids:
            blockers.append(
                _finding(
                    code="invocation_missing_prompt_snapshot",
                    severity=MultimodalFindingSeverity.BLOCKER,
                    message="Provider invocations are missing prompt snapshots.",
                    refs=[("model_invocation", item) for item in missing_snapshot_ids],
                )
            )
        if prompt_leak_ids:
            blockers.append(
                _finding(
                    code="prompt_snapshot_raw_or_leaky",
                    severity=MultimodalFindingSeverity.BLOCKER,
                    message="Prompt snapshots contain raw or leaky request/output fields.",
                    refs=[("prompt_snapshot", item) for item in prompt_leak_ids],
                )
            )
        if secret_leak_ids:
            blockers.append(
                _finding(
                    code="prompt_snapshot_secret_leak",
                    severity=MultimodalFindingSeverity.BLOCKER,
                    message="Prompt snapshots contain unredacted secret-like values.",
                    refs=[("prompt_snapshot", item) for item in secret_leak_ids],
                )
            )

        latency_values = [
            invocation.latency_ms for invocation in invocations if invocation.latency_ms is not None
        ]
        total_cost = sum(
            (invocation.estimated_cost or Decimal("0")) for invocation in invocations
        )
        status_counts = Counter(invocation.status for invocation in invocations)
        kind_counts = Counter(invocation.invocation_kind for invocation in invocations)
        if any(invocation.status == "failed" for invocation in provider_invocations):
            warnings.append(
                _finding(
                    code="provider_invocation_failures",
                    severity=MultimodalFindingSeverity.WARNING,
                    message="Some provider invocations failed.",
                    refs=[
                        ("model_invocation", str(invocation.id))
                        for invocation in provider_invocations
                        if invocation.status == "failed"
                    ][:10],
                )
            )
        return {
            "count": len(invocations),
            "provider_invocation_count": len(provider_invocations),
            "status_counts": dict(status_counts),
            "kind_counts": dict(kind_counts),
            "missing_prompt_snapshot_count": len(missing_snapshot_ids),
            "prompt_snapshot_leak_count": len(prompt_leak_ids) + len(secret_leak_ids),
            "average_latency_ms": _average_int(latency_values),
            "estimated_cost_total": float(total_cost),
        }

    def _media_job_metrics(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        blockers: list[MultimodalDiagnosticFinding],
    ) -> dict[str, Any]:
        jobs = self._session.scalars(
            select(MediaJob).where(
                MediaJob.world_id == world_id,
                MediaJob.worldline_id == worldline_id,
            )
        ).all()
        linked_asset_job_ids = {
            asset.source_job_id
            for asset in self._session.scalars(
                select(MediaAsset).where(
                    MediaAsset.world_id == world_id,
                    MediaAsset.worldline_id == worldline_id,
                    MediaAsset.source_job_id.is_not(None),
                )
            )
            if asset.source_job_id is not None
        }
        missing_output_job_ids = [
            str(job.id)
            for job in jobs
            if job.status == "succeeded"
            and job.job_kind
            in {
                "image_generation",
                "image_edit",
                "speech_generation",
                "speech_transcription",
                "composition",
            }
            and job.id not in linked_asset_job_ids
            and job.job_kind != "speech_transcription"
        ]
        if missing_output_job_ids:
            blockers.append(
                _finding(
                    code="media_job_missing_output_asset",
                    severity=MultimodalFindingSeverity.BLOCKER,
                    message="Succeeded media jobs are missing output assets.",
                    refs=[("media_job", item) for item in missing_output_job_ids],
                )
            )
        return {
            "count": len(jobs),
            "status_counts": dict(Counter(job.status for job in jobs)),
            "kind_counts": dict(Counter(job.job_kind for job in jobs)),
            "succeeded_without_output_asset_count": len(missing_output_job_ids),
        }

    def _media_asset_metrics(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        blockers: list[MultimodalDiagnosticFinding],
        warnings: list[MultimodalDiagnosticFinding],
    ) -> dict[str, Any]:
        assets = self._session.scalars(
            select(MediaAsset).where(
                MediaAsset.world_id == world_id,
                MediaAsset.worldline_id == worldline_id,
                MediaAsset.status != "deleted",
            )
        ).all()
        objects = self._session.scalars(
            select(MediaObject).where(
                MediaObject.world_id == world_id,
                MediaObject.worldline_id == worldline_id,
            )
        ).all()
        object_asset_ids = {model.asset_id for model in objects}
        missing_object_ids = [
            str(asset.id)
            for asset in assets
            if asset.status == "available" and asset.id not in object_asset_ids
        ]
        invalid_checksum_ids = [
            str(model.id)
            for model in objects
            if not _looks_like_sha256(model.checksum_sha256) or model.size_bytes < 0
        ]
        missing_storage_ids = [
            str(model.id)
            for model in objects
            if self._storage is not None and not self._storage.exists(model.storage_uri)
        ]
        tts_unlinked_asset_ids = [
            str(asset.id)
            for asset in assets
            if asset.asset_role == "speech_audio"
            and asset.source_kind == "provider_generated"
            and asset.source_invocation_id is None
        ]
        if missing_object_ids:
            blockers.append(
                _finding(
                    code="media_asset_missing_object",
                    severity=MultimodalFindingSeverity.BLOCKER,
                    message="Available media assets are missing media objects.",
                    refs=[("media_asset", item) for item in missing_object_ids],
                )
            )
        if invalid_checksum_ids:
            blockers.append(
                _finding(
                    code="media_object_invalid_checksum",
                    severity=MultimodalFindingSeverity.BLOCKER,
                    message="Media objects have invalid checksum or size metadata.",
                    refs=[("media_object", item) for item in invalid_checksum_ids],
                )
            )
        if missing_storage_ids:
            blockers.append(
                _finding(
                    code="media_object_storage_missing",
                    severity=MultimodalFindingSeverity.BLOCKER,
                    message="Media object records point at missing local storage objects.",
                    refs=[("media_object", item) for item in missing_storage_ids],
                )
            )
        if tts_unlinked_asset_ids:
            warnings.append(
                _finding(
                    code="tts_asset_missing_invocation_link",
                    severity=MultimodalFindingSeverity.WARNING,
                    message="Provider-generated TTS assets are missing invocation links.",
                    refs=[("media_asset", item) for item in tts_unlinked_asset_ids],
                )
            )
        return {
            "asset_count": len(assets),
            "object_count": len(objects),
            "asset_role_counts": dict(Counter(asset.asset_role for asset in assets)),
            "missing_object_count": len(missing_object_ids),
            "missing_storage_count": len(missing_storage_ids),
            "invalid_checksum_count": len(invalid_checksum_ids),
            "tts_missing_invocation_link_count": len(tts_unlinked_asset_ids),
        }

    def _visual_metrics(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        blockers: list[MultimodalDiagnosticFinding],
    ) -> dict[str, Any]:
        sprite_sets = self._session.scalars(
            select(CharacterSpriteSet).where(
                CharacterSpriteSet.world_id == world_id,
                CharacterSpriteSet.worldline_id == worldline_id,
                CharacterSpriteSet.status == "active",
            )
        ).all()
        variants = self._session.scalars(
            select(CharacterSpriteVariant).where(
                CharacterSpriteVariant.world_id == world_id,
                CharacterSpriteVariant.worldline_id == worldline_id,
                CharacterSpriteVariant.status == "active",
            )
        ).all()
        variants_by_set: dict[uuid.UUID, list[CharacterSpriteVariant]] = {}
        for variant in variants:
            variants_by_set.setdefault(variant.sprite_set_id, []).append(variant)
        missing_default_ids: list[str] = []
        missing_neutral_ids: list[str] = []
        for sprite_set in sprite_sets:
            set_variants = variants_by_set.get(sprite_set.id, [])
            if sprite_set.default_variant_id is None and not any(
                variant.is_default for variant in set_variants
            ):
                missing_default_ids.append(str(sprite_set.id))
            if not any(variant.expression_key == "neutral" for variant in set_variants):
                missing_neutral_ids.append(str(sprite_set.id))
        backgrounds = self._session.scalars(
            select(SceneBackgroundProfile).where(
                SceneBackgroundProfile.world_id == world_id,
                SceneBackgroundProfile.worldline_id == worldline_id,
                SceneBackgroundProfile.status == "active",
            )
        ).all()
        if missing_default_ids:
            blockers.append(
                _finding(
                    code="sprite_set_missing_default",
                    severity=MultimodalFindingSeverity.BLOCKER,
                    message="Active sprite sets are missing a default variant.",
                    refs=[("character_sprite_set", item) for item in missing_default_ids],
                )
            )
        if missing_neutral_ids:
            blockers.append(
                _finding(
                    code="sprite_set_missing_neutral",
                    severity=MultimodalFindingSeverity.BLOCKER,
                    message="Active sprite sets are missing a neutral expression variant.",
                    refs=[("character_sprite_set", item) for item in missing_neutral_ids],
                )
            )
        if not backgrounds and (sprite_sets or variants):
            blockers.append(
                _finding(
                    code="scene_background_missing",
                    severity=MultimodalFindingSeverity.BLOCKER,
                    message="Visual setup exists but no active scene backgrounds are configured.",
                )
            )
        return {
            "sprite_set_count": len(sprite_sets),
            "sprite_variant_count": len(variants),
            "sprite_sets_missing_default_count": len(missing_default_ids),
            "sprite_sets_missing_neutral_count": len(missing_neutral_ids),
            "scene_background_count": len(backgrounds),
        }

    def _speech_metrics(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        blockers: list[MultimodalDiagnosticFinding],
    ) -> dict[str, Any]:
        agents = self._session.scalars(
            select(Agent).where(Agent.world_id == world_id, Agent.kind == "role_agent")
        ).all()
        bindings = self._session.scalars(
            select(AgentVoiceProfileBinding).where(
                AgentVoiceProfileBinding.world_id == world_id,
                AgentVoiceProfileBinding.worldline_id == worldline_id,
            )
        ).all()
        profiles = self._session.scalars(
            select(VoiceProfile).where(VoiceProfile.world_id == world_id)
        ).all()
        default_binding_agent_ids = {
            binding.agent_id for binding in bindings if binding.is_default
        }
        missing_binding_ids = [
            str(agent.id) for agent in agents if agent.id not in default_binding_agent_ids
        ]
        transcripts = self._session.scalars(
            select(SpeechTranscript).where(
                SpeechTranscript.world_id == world_id,
                SpeechTranscript.worldline_id == worldline_id,
            )
        ).all()
        transcript_ids = {transcript.id for transcript in transcripts}
        memory_write_count = 0
        if transcript_ids:
            memory_write_count = self._session.scalar(
                select(func.count())
                .select_from(MemoryWriteJob)
                .where(
                    MemoryWriteJob.world_id == world_id,
                    MemoryWriteJob.worldline_id == worldline_id,
                    MemoryWriteJob.source_id.in_(transcript_ids),
                )
            ) or 0
        if missing_binding_ids and (profiles or bindings):
            blockers.append(
                _finding(
                    code="agent_missing_default_voice",
                    severity=MultimodalFindingSeverity.BLOCKER,
                    message="Agents with voice setup are missing default voice bindings.",
                    refs=[("agent", item) for item in missing_binding_ids],
                )
            )
        if memory_write_count:
            blockers.append(
                _finding(
                    code="stt_transcript_memory_written",
                    severity=MultimodalFindingSeverity.BLOCKER,
                    message="STT transcript records appear to have been auto-enqueued for memory.",
                )
            )
        return {
            "voice_profile_count": len(profiles),
            "voice_binding_count": len(bindings),
            "agents_missing_default_voice_count": len(missing_binding_ids),
            "speech_transcript_count": len(transcripts),
            "transcript_memory_write_count": memory_write_count,
        }

    def _event_payload_metrics(
        self,
        world_id: uuid.UUID,
        worldline_id: uuid.UUID,
        blockers: list[MultimodalDiagnosticFinding],
    ) -> dict[str, Any]:
        events = self._session.scalars(
            select(WorldEventModel).where(
                WorldEventModel.world_id == world_id,
                (WorldEventModel.worldline_id == worldline_id)
                | (WorldEventModel.worldline_id.is_(None)),
            )
        ).all()
        leaky_ids = [
            str(event.id)
            for event in events
            if _json_contains_forbidden_event_payload(event.payload)
        ]
        if leaky_ids:
            blockers.append(
                _finding(
                    code="world_event_payload_leak",
                    severity=MultimodalFindingSeverity.BLOCKER,
                    message=(
                        "World event payload contains media paths, raw prompt/output, "
                        "bytes, or base64."
                    ),
                    refs=[("world_event", item) for item in leaky_ids],
                )
            )
        return {
            "count": len(events),
            "payload_leak_count": len(leaky_ids),
        }


def _run_record(run: LongRunEvalRun) -> MultimodalEvalRunRead:
    return MultimodalEvalRunRead(
        id=run.id,
        world_id=run.world_id,
        worldline_id=run.worldline_id,
        eval_key=run.eval_key,
        horizon_days=run.horizon_days,
        status=MultimodalEvalStatus(run.status),
        started_at=run.started_at,
        finished_at=run.finished_at,
        metrics=run.metrics,
        recommendations=run.recommendations,
        blockers=run.blockers,
        metadata=run.metadata_json,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


def _status(
    *,
    blockers: list[MultimodalDiagnosticFinding],
    warnings: list[MultimodalDiagnosticFinding],
) -> MultimodalEvalStatus:
    if blockers:
        return MultimodalEvalStatus.FAILED
    if warnings:
        return MultimodalEvalStatus.WARNING
    return MultimodalEvalStatus.COMPLETED


def _recommendations(
    *,
    blockers: list[MultimodalDiagnosticFinding],
    warnings: list[MultimodalDiagnosticFinding],
) -> list[str]:
    if not blockers and not warnings:
        return ["Multimodal diagnostics passed for the sampled worldline."]
    recommendations: list[str] = []
    if any(finding.code.startswith("provider_") for finding in (*blockers, *warnings)):
        recommendations.append("Run provider health or smoke checks and review secret references.")
    if any(
        finding.code.startswith("media_") or finding.code.startswith("tts_")
        for finding in blockers
    ):
        recommendations.append(
            "Repair media job outputs and verify media object storage integrity."
        )
    if any(
        finding.code.startswith("sprite_") or finding.code.startswith("scene_")
        for finding in blockers
    ):
        recommendations.append("Add default sprite variants and scene background bindings.")
    if any(finding.code.startswith("agent_missing") for finding in blockers):
        recommendations.append("Bind default voice profiles for speaking agents.")
    if any("leak" in finding.code for finding in blockers):
        recommendations.append(
            "Remove leaked raw prompt/output or storage data from event payloads."
        )
    return recommendations or ["Review warning findings before release."]


def _finding(
    *,
    code: str,
    severity: MultimodalFindingSeverity,
    message: str,
    refs: list[tuple[str, str]] | None = None,
) -> MultimodalDiagnosticFinding:
    return MultimodalDiagnosticFinding(
        code=code,
        severity=severity,
        message=message,
        evidence_refs=[
            MultimodalEvidenceRef(kind=kind, id=identifier) for kind, identifier in (refs or [])
        ],
    )


def _finding_to_json(finding: MultimodalDiagnosticFinding) -> dict[str, Any]:
    return {
        "code": finding.code,
        "severity": finding.severity.value,
        "message": finding.message,
        "evidence_refs": [_evidence_ref_to_json(ref) for ref in finding.evidence_refs],
    }


def _evidence_ref_to_json(ref: MultimodalEvidenceRef) -> dict[str, str]:
    return {"kind": ref.kind, "id": ref.id}


def _average_int(values: list[int]) -> int | None:
    if not values:
        return None
    return sum(values) // len(values)


def _looks_like_sha256(value: str) -> bool:
    return bool(re.fullmatch(r"[a-fA-F0-9]{64}", value))


def _snapshot_contains_leak(snapshot: PromptSnapshot) -> bool:
    if snapshot.raw_prompt_text or snapshot.raw_output_text:
        return True
    return any(
        _json_contains_leaky_value(value)
        for value in (
            snapshot.raw_messages_json,
            snapshot.raw_request_json,
            snapshot.raw_response_json,
            snapshot.normalized_output_json,
            snapshot.prompt_context_snapshot_json,
            snapshot.tool_definitions_json,
            snapshot.context_pack_refs_json,
            snapshot.input_asset_refs_json,
        )
    )


def _snapshot_contains_secret(snapshot: PromptSnapshot) -> bool:
    return any(
        _contains_secret_value(value)
        for value in (
            snapshot.raw_messages_json,
            snapshot.raw_request_json,
            snapshot.raw_response_json,
            snapshot.normalized_output_json,
            snapshot.prompt_context_snapshot_json,
            snapshot.tool_definitions_json,
            snapshot.context_pack_refs_json,
            snapshot.input_asset_refs_json,
        )
    )


def _contains_secret_value(value: object) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            if is_sensitive_key(key_text) and item not in {None, "", REDACTED}:
                return True
            if _contains_secret_value(item):
                return True
    elif isinstance(value, list | tuple):
        return any(_contains_secret_value(item) for item in value)
    return False


def _json_contains_leaky_value(value: object) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).strip().lower() in _LEAKY_JSON_KEYS:
                return True
            if _json_contains_leaky_value(item):
                return True
    elif isinstance(value, list | tuple):
        return any(_json_contains_leaky_value(item) for item in value)
    elif isinstance(value, str):
        lowered = value.lower()
        return (
            lowered.startswith(("media://", "local://", "file://", "/", "./", "../"))
            or "base64," in lowered
        )
    return False


def _json_contains_forbidden_event_payload(value: object) -> bool:
    if _json_contains_leaky_value(value):
        return True
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).strip().lower() in _EVENT_RAW_KEYS:
                return True
            if _json_contains_forbidden_event_payload(item):
                return True
    elif isinstance(value, list | tuple):
        return any(_json_contains_forbidden_event_payload(item) for item in value)
    return False


_LEAKY_JSON_KEYS = {
    "storage_uri",
    "preview_uri",
    "thumbnail_uri",
    "base64",
    "bytes",
    "path",
    "file_path",
    "raw_bytes",
}
_EVENT_RAW_KEYS = {"raw_prompt", "raw_prompt_text", "raw_output", "raw_output_text"}
