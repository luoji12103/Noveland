from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol, cast

from noveland.agents.models import AgentRuntimeRun
from noveland.conversations.models import ConversationSession, ConversationTurn
from noveland.core.settings import AppSettings
from noveland.events.models import WorldEventModel
from noveland.memory.backends.mem0_oss import BACKEND_NAME as MEM0_OSS_BACKEND_NAME
from noveland.memory.contracts import (
    AgentProfileSnapshot,
    MemoryBackend,
    MemoryBackendHealth,
    MemoryBackendHealthStatus,
    MemoryBackendKind,
    MemoryBackendProfileCreate,
    MemoryBackendProfileRecord,
    MemoryBackendProfileUpdate,
    MemoryBackfillDryRunResult,
    MemoryBackfillExecutionResult,
    MemoryBackfillSourceSummary,
    MemoryBackfillWorldSummary,
    MemoryContext,
    MemoryContextItem,
    MemoryDeleteResult,
    MemoryDeleteScope,
    MemoryEvalCase,
    MemoryEvalResult,
    MemoryEvent,
    MemoryItemRecord,
    MemoryMessage,
    MemoryProfileSnapshotRecord,
    MemoryQueueReadinessReport,
    MemoryRetrievalLogRecord,
    MemorySearchRequest,
    MemorySearchResult,
    MemoryTurn,
    MemoryWriteJobRecord,
    MemoryWriteJobStatus,
    MemoryWriteJobStatusSummary,
    MemoryWriteLogRecord,
    MemoryWriteSourceKind,
)
from noveland.memory.errors import (
    MemoryBackendUnavailableError,
    MemoryPrivacyDeletionError,
    MemoryValidationError,
)
from noveland.memory.evals import run_memory_eval_cases
from noveland.memory.models import (
    AgentProfileSnapshotModel,
    MemoryBackendProfile,
    MemoryRetrievalLog,
    MemoryWriteJob,
    MemoryWriteLog,
)
from noveland.plugins.builtins import get_builtin_plugin_registry
from noveland.plugins.constants import BUILTIN_LOCAL_PGVECTOR_MEMORY, BUILTIN_MEM0_OSS_MEMORY
from noveland.plugins.errors import (
    PluginConfigValidationError,
    PluginFactoryError,
    PluginNotFoundError,
)
from noveland.worlds.models import World
from sqlalchemy import Select, and_, func, join, or_, select
from sqlalchemy.orm import Session

MEMORY_BACKFILL_EVENT_NAMES = frozenset(
    {
        "agent.run_completed",
        "calendar.entry_due",
        "narrative.artifact_created",
        "memory.item_created",
    },
)


class _BackfillCandidate:
    def __init__(
        self,
        *,
        source_kind: MemoryWriteSourceKind,
        world_id: uuid.UUID,
        agent_id: uuid.UUID,
        source_id: uuid.UUID,
        dedupe_key: str,
        content: str,
        metadata: dict[str, Any],
        conversation_id: uuid.UUID | None = None,
    ) -> None:
        self.source_kind = source_kind
        self.world_id = world_id
        self.agent_id = agent_id
        self.source_id = source_id
        self.dedupe_key = dedupe_key
        self.content = content
        self.metadata = metadata
        self.conversation_id = conversation_id


class _MemoryBackendPlugin(Protocol):
    def create_backend(
        self,
        *,
        profile: MemoryBackendProfileRecord,
        settings: AppSettings,
        session: Session,
    ) -> MemoryBackend: ...


class MemoryBackendProfileService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_profiles(self) -> list[MemoryBackendProfileRecord]:
        return [
            _profile_record(model)
            for model in self._session.scalars(
                select(MemoryBackendProfile).order_by(MemoryBackendProfile.profile_key),
            ).all()
        ]

    def get_profile(self, profile_id: uuid.UUID) -> MemoryBackendProfileRecord | None:
        model = self._session.get(MemoryBackendProfile, profile_id)
        return None if model is None else _profile_record(model)

    def first_enabled_profile(self) -> MemoryBackendProfileRecord | None:
        model = self._session.scalars(
            select(MemoryBackendProfile)
            .where(MemoryBackendProfile.is_enabled.is_(True))
            .order_by(MemoryBackendProfile.profile_key),
        ).first()
        return None if model is None else _profile_record(model)

    def create_profile(
        self,
        profile_create: MemoryBackendProfileCreate,
    ) -> MemoryBackendProfileRecord:
        if self._profile_key_exists(profile_create.profile_key):
            raise MemoryValidationError("Memory backend profile key already exists")
        model = MemoryBackendProfile(
            profile_key=profile_create.profile_key,
            name=profile_create.name,
            backend_kind=profile_create.backend_kind.value,
            vector_store_config=profile_create.vector_store_config,
            llm_config=profile_create.llm_config,
            embedder_config=profile_create.embedder_config,
            reranker_config=profile_create.reranker_config,
            secret_refs=profile_create.secret_refs,
            is_enabled=profile_create.is_enabled,
        )
        self._session.add(model)
        self._session.flush()
        return _profile_record(model)

    def update_profile(
        self,
        model: MemoryBackendProfile,
        profile_update: MemoryBackendProfileUpdate,
    ) -> MemoryBackendProfileRecord:
        if "name" in profile_update.model_fields_set and profile_update.name is not None:
            model.name = profile_update.name
        if "vector_store_config" in profile_update.model_fields_set:
            model.vector_store_config = profile_update.vector_store_config or {}
        if "llm_config" in profile_update.model_fields_set:
            model.llm_config = profile_update.llm_config or {}
        if "embedder_config" in profile_update.model_fields_set:
            model.embedder_config = profile_update.embedder_config or {}
        if "reranker_config" in profile_update.model_fields_set:
            model.reranker_config = profile_update.reranker_config or {}
        if "secret_refs" in profile_update.model_fields_set:
            model.secret_refs = profile_update.secret_refs or {}
        if "is_enabled" in profile_update.model_fields_set:
            model.is_enabled = bool(profile_update.is_enabled)
        self._session.flush()
        return _profile_record(model)

    def delete_profile(self, model: MemoryBackendProfile) -> None:
        self._session.delete(model)
        self._session.flush()

    def _profile_key_exists(self, profile_key: str) -> bool:
        return (
            self._session.scalars(
                select(MemoryBackendProfile.id).where(
                    MemoryBackendProfile.profile_key == profile_key,
                ),
            ).first()
            is not None
        )


class MemoryService:
    def __init__(
        self,
        session: Session,
        settings: AppSettings,
    ) -> None:
        self._session = session
        self._settings = settings
        self._profile_service = MemoryBackendProfileService(session)

    def record_turn(self, turn: MemoryTurn) -> MemoryWriteJob:
        world = self._world_or_404(turn.world_id)
        profile = self._backend_profile_for_world(world)
        existing = self._session.scalars(
            select(MemoryWriteJob).where(MemoryWriteJob.dedupe_key == turn.dedupe_key),
        ).one_or_none()
        if existing is not None:
            return existing
        source_id = turn.turn_id or turn.run_id or turn.source_event_id
        if source_id is None:
            raise MemoryValidationError("memory turn requires one stable source id")
        job = MemoryWriteJob(
            world_id=turn.world_id,
            agent_id=turn.agent_id,
            backend_profile_id=profile.id,
            source_kind=MemoryWriteSourceKind.CONVERSATION_TURN.value
            if turn.turn_id is not None
            else MemoryWriteSourceKind.AGENT_RUN.value,
            source_id=source_id,
            payload_json=turn.model_dump(mode="json"),
            dedupe_key=turn.dedupe_key,
            status=MemoryWriteJobStatus.PENDING.value,
            next_attempt_at=datetime.now(UTC),
        )
        self._session.add(job)
        self._session.flush()
        return job

    def record_events(self, events: list[MemoryEvent]) -> list[MemoryWriteJob]:
        if not events:
            return []
        jobs: list[MemoryWriteJob] = []
        for event in events:
            world = self._world_or_404(event.world_id)
            profile = self._backend_profile_for_world(world)
            existing = self._session.scalars(
                select(MemoryWriteJob).where(MemoryWriteJob.dedupe_key == event.dedupe_key),
            ).one_or_none()
            if existing is not None:
                jobs.append(existing)
                continue
            job = MemoryWriteJob(
                world_id=event.world_id,
                agent_id=event.agent_id,
                backend_profile_id=profile.id,
                source_kind=MemoryWriteSourceKind.WORLD_EVENT.value,
                source_id=event.event_id,
                payload_json=event.model_dump(mode="json"),
                dedupe_key=event.dedupe_key,
                status=MemoryWriteJobStatus.PENDING.value,
                next_attempt_at=datetime.now(UTC),
            )
            self._session.add(job)
            self._session.flush()
            jobs.append(job)
        return jobs

    def process_due_jobs(self, limit: int) -> int:
        processed = 0
        for job in self._due_jobs(limit):
            job.status = MemoryWriteJobStatus.PROCESSING.value
            job.attempt_count += 1
            self._session.flush()
            try:
                backend = self._backend_for_job(job)
                if job.source_kind == MemoryWriteSourceKind.WORLD_EVENT.value:
                    result = backend.record_events([MemoryEvent.model_validate(job.payload_json)])
                else:
                    result = backend.record_turn(MemoryTurn.model_validate(job.payload_json))
                job.status = MemoryWriteJobStatus.SUCCEEDED.value
                job.last_error = None
                job.processed_at = datetime.now(UTC)
                self._session.add(
                    MemoryWriteLog(
                        job_id=job.id,
                        backend=result.backend,
                        success=True,
                        latency_ms=result.latency_ms,
                        request_summary={
                            "source_kind": job.source_kind,
                            "source_id": str(job.source_id),
                        },
                        response_summary={
                            "recorded_count": result.recorded_count,
                            "backend_ids": result.backend_ids,
                        },
                        correlation_ids={
                            "dedupe_key": job.dedupe_key,
                            "world_id": str(job.world_id),
                            "agent_id": str(job.agent_id),
                        },
                    ),
                )
            except Exception as exc:
                job.status = MemoryWriteJobStatus.FAILED.value
                job.last_error = str(exc)
                job.next_attempt_at = datetime.now(UTC) + timedelta(
                    seconds=min(2 ** min(job.attempt_count, 8), 300),
                )
                self._session.add(
                    MemoryWriteLog(
                        job_id=job.id,
                        backend=self._job_backend_name(job),
                        success=False,
                        latency_ms=None,
                        request_summary={
                            "source_kind": job.source_kind,
                            "source_id": str(job.source_id),
                        },
                        response_summary={"error": str(exc), "error_type": type(exc).__name__},
                        correlation_ids={
                            "dedupe_key": job.dedupe_key,
                            "world_id": str(job.world_id),
                            "agent_id": str(job.agent_id),
                        },
                    ),
                )
            processed += 1
        self._session.flush()
        return processed

    def list_memories(self, world_id: uuid.UUID, agent_id: uuid.UUID) -> list[MemoryItemRecord]:
        try:
            return list(self._backend_for_scope(world_id).list_memories(world_id, agent_id))
        except Exception:
            return []

    def search(self, request: MemorySearchRequest) -> MemorySearchResult:
        try:
            result = self._backend_for_scope(request.world_id).search(request)
        except Exception:
            result = MemorySearchResult(
                backend=self._scope_backend_name(request.world_id), items=[], latency_ms=None
            )
        self._session.add(
            MemoryRetrievalLog(
                world_id=request.world_id,
                agent_id=request.agent_id,
                backend_profile_id=self._world_or_404(request.world_id).memory_backend_profile_id,
                backend=result.backend,
                query_text=request.query_text,
                hit_count=len(result.items),
                selected_item_ids=[item.id for item in result.items],
                latency_ms=result.latency_ms,
                context_item_count=len(result.items),
            ),
        )
        self._session.flush()
        return result

    def build_context(
        self,
        *,
        world_id: uuid.UUID,
        agent_id: uuid.UUID,
        query_text: str,
        max_context_items: int,
    ) -> MemoryContext:
        search_result = self.search(
            MemorySearchRequest(
                world_id=world_id,
                agent_id=agent_id,
                query_text=query_text,
                limit=max_context_items,
            ),
        )
        snapshot = self.get_profile_snapshot(world_id, agent_id)
        return MemoryContext(
            backend=search_result.backend,
            items=[
                MemoryContextItem(
                    id=item.id,
                    content=item.content,
                    score=item.score,
                    metadata=item.metadata,
                )
                for item in search_result.items[:max_context_items]
            ],
            profile_snapshot=None if snapshot is None else _snapshot_contract(snapshot),
            query_text=query_text,
        )

    def get_profile_snapshot(
        self,
        world_id: uuid.UUID,
        agent_id: uuid.UUID,
    ) -> MemoryProfileSnapshotRecord | None:
        model = self._session.scalars(
            select(AgentProfileSnapshotModel).where(
                AgentProfileSnapshotModel.world_id == world_id,
                AgentProfileSnapshotModel.agent_id == agent_id,
            ),
        ).one_or_none()
        return None if model is None else _snapshot_record(model)

    def refresh_profile_snapshot(
        self,
        world_id: uuid.UUID,
        agent_id: uuid.UUID,
    ) -> MemoryProfileSnapshotRecord:
        items = self.list_memories(world_id, agent_id)
        snapshot = _build_snapshot(items)
        model = self._session.scalars(
            select(AgentProfileSnapshotModel).where(
                AgentProfileSnapshotModel.world_id == world_id,
                AgentProfileSnapshotModel.agent_id == agent_id,
            ),
        ).one_or_none()
        if model is None:
            model = AgentProfileSnapshotModel(world_id=world_id, agent_id=agent_id)
            self._session.add(model)
        model.aliases = snapshot.aliases
        model.identity_notes = snapshot.identity_notes
        model.durable_preferences = snapshot.durable_preferences
        model.long_lived_goals = snapshot.long_lived_goals
        model.language_style_preferences = snapshot.language_style_preferences
        model.refreshed_at = datetime.now(UTC)
        self._session.flush()
        return _snapshot_record(model)

    def delete_scope(self, scope: MemoryDeleteScope) -> MemoryDeleteResult:
        try:
            result = self._backend_for_scope(scope.world_id).delete_scope(scope)
        except Exception as exc:
            raise MemoryPrivacyDeletionError(str(exc)) from exc
        if scope.run_id is None:
            self._scrub_local_scope_data(scope.world_id, scope.agent_id)
        self._session.flush()
        return result

    def backend_health(self, world_id: uuid.UUID) -> MemoryBackendHealth:
        try:
            return self._backend_for_scope(world_id).healthcheck()
        except Exception as exc:
            return MemoryBackendHealth(
                backend=self._scope_backend_name(world_id),
                status=MemoryBackendHealthStatus.UNAVAILABLE,
                details={"error": str(exc)},
            )

    def profile_health(self, profile_id: uuid.UUID) -> MemoryBackendHealth:
        profile = self._profile_service.get_profile(profile_id)
        if profile is None:
            raise LookupError("Memory backend profile not found")
        try:
            return self._create_backend(
                _plugin_identifier_for_backend_kind(profile.backend_kind.value),
                {},
                profile,
            ).healthcheck()
        except Exception as exc:
            return MemoryBackendHealth(
                backend=profile.backend_kind.value,
                status=MemoryBackendHealthStatus.UNAVAILABLE,
                details={"error": str(exc), "profile_key": profile.profile_key},
            )

    def list_write_logs(
        self,
        *,
        profile_id: uuid.UUID | None = None,
        limit: int = 20,
    ) -> list[MemoryWriteLogRecord]:
        safe_limit = max(1, min(limit, 100))
        statement: Select[tuple[MemoryWriteLog]] = (
            select(MemoryWriteLog)
            .order_by(MemoryWriteLog.occurred_at.desc())
            .limit(safe_limit)
        )
        if profile_id is not None:
            statement = (
                select(MemoryWriteLog)
                .select_from(
                    join(
                        MemoryWriteLog,
                        MemoryWriteJob,
                        MemoryWriteLog.job_id == MemoryWriteJob.id,
                    )
                )
                .where(MemoryWriteJob.backend_profile_id == profile_id)
                .order_by(MemoryWriteLog.occurred_at.desc())
                .limit(safe_limit)
            )
        return [_write_log_record(model) for model in self._session.scalars(statement).all()]

    def list_write_jobs(
        self,
        *,
        profile_id: uuid.UUID | None = None,
        status: MemoryWriteJobStatus | None = None,
        limit: int = 20,
    ) -> list[MemoryWriteJobRecord]:
        safe_limit = max(1, min(limit, 100))
        statement = (
            select(MemoryWriteJob, MemoryBackendProfile)
            .join(
                MemoryBackendProfile,
                MemoryWriteJob.backend_profile_id == MemoryBackendProfile.id,
            )
            .order_by(MemoryWriteJob.created_at.desc())
            .limit(safe_limit)
        )
        if profile_id is not None:
            statement = statement.where(MemoryWriteJob.backend_profile_id == profile_id)
        if status is not None:
            statement = statement.where(MemoryWriteJob.status == status.value)
        return [
            _write_job_record(job, profile, self._settings, self._session)
            for job, profile in self._session.execute(statement).all()
        ]

    def write_job_status_summary(self) -> MemoryWriteJobStatusSummary:
        now = datetime.now(UTC)
        rows = self._session.execute(
            select(MemoryWriteJob.status, func.count(MemoryWriteJob.id)).group_by(
                MemoryWriteJob.status,
            ),
        ).all()
        counts = {str(status): int(count) for status, count in rows}
        failed_rows = self._session.execute(
            select(MemoryWriteJob, MemoryBackendProfile)
            .join(
                MemoryBackendProfile,
                MemoryWriteJob.backend_profile_id == MemoryBackendProfile.id,
            )
            .where(MemoryWriteJob.status == MemoryWriteJobStatus.FAILED.value),
        ).all()
        retryable_failed_count = sum(
            1 for job, profile in failed_rows if _is_retryable(job, profile, self._settings)
        )
        terminal_failed_count = len(failed_rows) - retryable_failed_count
        due_pending_count = self._session.scalar(
            select(func.count(MemoryWriteJob.id)).where(
                MemoryWriteJob.status == MemoryWriteJobStatus.PENDING.value,
                MemoryWriteJob.next_attempt_at <= now,
            ),
        )
        stalled_threshold = now - timedelta(seconds=self._settings.memory_job_stalled_after_seconds)
        stalled_processing_count = self._session.scalar(
            select(func.count(MemoryWriteJob.id)).where(
                MemoryWriteJob.status == MemoryWriteJobStatus.PROCESSING.value,
                MemoryWriteJob.updated_at <= stalled_threshold,
            ),
        )
        return MemoryWriteJobStatusSummary(
            pending_count=counts.get(MemoryWriteJobStatus.PENDING.value, 0),
            processing_count=counts.get(MemoryWriteJobStatus.PROCESSING.value, 0),
            succeeded_count=counts.get(MemoryWriteJobStatus.SUCCEEDED.value, 0),
            failed_count=counts.get(MemoryWriteJobStatus.FAILED.value, 0),
            due_count=(0 if due_pending_count is None else int(due_pending_count))
            + retryable_failed_count,
            retryable_failed_count=retryable_failed_count,
            terminal_failed_count=terminal_failed_count,
            stalled_processing_count=0
            if stalled_processing_count is None
            else int(stalled_processing_count),
        )

    def retry_write_job(self, job_id: uuid.UUID) -> MemoryWriteJobRecord:
        row = self._session.execute(
            select(MemoryWriteJob, MemoryBackendProfile)
            .join(
                MemoryBackendProfile,
                MemoryWriteJob.backend_profile_id == MemoryBackendProfile.id,
            )
            .where(MemoryWriteJob.id == job_id),
        ).one_or_none()
        if row is None:
            raise LookupError("Memory write job not found")
        job, profile = row
        if job.status != MemoryWriteJobStatus.FAILED.value:
            raise MemoryValidationError("Only failed memory write jobs can be retried")
        if not _is_retryable(job, profile, self._settings):
            reason = _terminal_reason(job, profile, self._settings) or "job is not retryable"
            raise MemoryValidationError(f"Memory write job cannot be retried: {reason}")
        job.status = MemoryWriteJobStatus.PENDING.value
        job.next_attempt_at = datetime.now(UTC)
        job.last_error = None
        job.processed_at = None
        self._session.flush()
        return _write_job_record(job, profile, self._settings, self._session)

    def dry_run_backfill(self, limit: int = 500) -> MemoryBackfillDryRunResult:
        safe_limit = max(1, min(limit, 2000))
        source_stats: dict[str, dict[str, int]] = defaultdict(_empty_backfill_stats)
        world_stats: dict[uuid.UUID, dict[str, Any]] = {}

        def record(
            *,
            source_kind: MemoryWriteSourceKind,
            world: World | None,
            dedupe_key: str,
            skip_reason: str | None,
        ) -> None:
            source_bucket = source_stats[source_kind.value]
            world_model = world
            if world_model is not None:
                world_key = world_model.id
                if world_key in world_stats:
                    target = world_stats[world_key]
                else:
                    profile = (
                        None
                        if world_model.memory_backend_profile_id is None
                        else self._profile_service.get_profile(
                            world_model.memory_backend_profile_id,
                        )
                    )
                    world_stats[world_key] = {
                        "world_id": world_key,
                        "backend_profile_id": None if profile is None else profile.id,
                        "backend_profile_key": None if profile is None else profile.profile_key,
                        **_empty_backfill_stats(),
                    }
                    target = world_stats[world_key]
            else:
                target = None
            if self._dedupe_exists(dedupe_key):
                source_bucket["skipped_existing_count"] += 1
                if target is not None:
                    target["skipped_existing_count"] += 1
                return
            if skip_reason is None:
                source_bucket["candidate_count"] += 1
                if target is not None:
                    target["candidate_count"] += 1
                return
            source_bucket[skip_reason] += 1
            if target is not None:
                target[skip_reason] += 1

        for run in self._session.scalars(
            select(AgentRuntimeRun)
            .where(
                AgentRuntimeRun.status == "succeeded",
                AgentRuntimeRun.response_text.is_not(None),
            )
            .order_by(AgentRuntimeRun.started_at.desc())
            .limit(safe_limit),
        ).all():
            world = self._session.get(World, run.world_id)
            record(
                source_kind=MemoryWriteSourceKind.AGENT_RUN,
                world=world,
                dedupe_key=f"agent-run:{run.id}",
                skip_reason=None if world is None else self._backfill_skip_reason(world),
            )

        for turn in self._session.scalars(
            select(ConversationTurn)
            .where(
                ConversationTurn.status == "succeeded",
                ConversationTurn.output_text.is_not(None),
            )
            .order_by(ConversationTurn.created_at.desc())
            .limit(safe_limit),
        ).all():
            session_model = self._session.get(ConversationSession, turn.session_id)
            world = (
                None
                if session_model is None
                else self._session.get(World, session_model.world_id)
            )
            record(
                source_kind=MemoryWriteSourceKind.CONVERSATION_TURN,
                world=world,
                dedupe_key=f"conversation-turn:{turn.id}",
                skip_reason=None if world is None else self._backfill_skip_reason(world),
            )

        for event in self._session.scalars(
            select(WorldEventModel)
            .where(WorldEventModel.event_name.in_(MEMORY_BACKFILL_EVENT_NAMES))
            .order_by(WorldEventModel.wall_time.desc())
            .limit(safe_limit),
        ).all():
            world = self._session.get(World, event.world_id)
            record(
                source_kind=MemoryWriteSourceKind.WORLD_EVENT,
                world=world,
                dedupe_key=f"world-event:{event.id}",
                skip_reason=None if world is None else self._backfill_skip_reason(world),
            )

        totals = _empty_backfill_stats()
        for source_kind in MemoryWriteSourceKind:
            source_stats[source_kind.value]
        for bucket in source_stats.values():
            for key in totals:
                totals[key] += bucket[key]
        return MemoryBackfillDryRunResult(
            candidate_count=totals["candidate_count"],
            skipped_existing_count=totals["skipped_existing_count"],
            skipped_no_profile_count=totals["skipped_no_profile_count"],
            skipped_disabled_profile_count=totals["skipped_disabled_profile_count"],
            source_summaries=[
                MemoryBackfillSourceSummary(
                    source_kind=MemoryWriteSourceKind(source_kind),
                    candidate_count=stats["candidate_count"],
                    skipped_existing_count=stats["skipped_existing_count"],
                    skipped_no_profile_count=stats["skipped_no_profile_count"],
                    skipped_disabled_profile_count=stats["skipped_disabled_profile_count"],
                )
                for source_kind, stats in sorted(source_stats.items())
            ],
            world_summaries=[
                MemoryBackfillWorldSummary(
                    world_id=stats["world_id"],
                    backend_profile_id=stats["backend_profile_id"],
                    backend_profile_key=stats["backend_profile_key"],
                    candidate_count=stats["candidate_count"],
                    skipped_existing_count=stats["skipped_existing_count"],
                    skipped_no_profile_count=stats["skipped_no_profile_count"],
                    skipped_disabled_profile_count=stats["skipped_disabled_profile_count"],
                )
                for stats in sorted(world_stats.values(), key=lambda item: str(item["world_id"]))
            ],
        )

    def execute_backfill(self, limit: int = 100) -> MemoryBackfillExecutionResult:
        safe_limit = max(1, min(limit, 500))
        dry_run_before = self.dry_run_backfill(limit=safe_limit)
        counters = _empty_backfill_stats()
        enqueued_count = 0
        for candidate in self._backfill_candidates(safe_limit):
            if enqueued_count >= safe_limit:
                break
            if self._dedupe_exists(candidate.dedupe_key):
                counters["skipped_existing_count"] += 1
                continue
            world = self._session.get(World, candidate.world_id)
            if world is None:
                counters["skipped_no_profile_count"] += 1
                continue
            skip_reason = self._backfill_skip_reason(world)
            if skip_reason is not None:
                counters[skip_reason] += 1
                continue
            if candidate.source_kind == MemoryWriteSourceKind.WORLD_EVENT:
                self.record_events(
                    [
                        MemoryEvent(
                            world_id=candidate.world_id,
                            agent_id=candidate.agent_id,
                            event_id=candidate.source_id,
                            content=candidate.content,
                            metadata=candidate.metadata,
                            dedupe_key=candidate.dedupe_key,
                        ),
                    ],
                )
            else:
                self.record_turn(
                    MemoryTurn(
                        world_id=candidate.world_id,
                        agent_id=candidate.agent_id,
                        conversation_id=candidate.conversation_id,
                        turn_id=candidate.source_id
                        if candidate.source_kind == MemoryWriteSourceKind.CONVERSATION_TURN
                        else None,
                        run_id=candidate.source_id
                        if candidate.source_kind == MemoryWriteSourceKind.AGENT_RUN
                        else None,
                        trigger_source="memory_backfill",
                        messages=[MemoryMessage(role="assistant", content=candidate.content)],
                        metadata=candidate.metadata,
                        dedupe_key=candidate.dedupe_key,
                    ),
                )
            enqueued_count += 1
        return MemoryBackfillExecutionResult(
            enqueued_count=enqueued_count,
            skipped_existing_count=counters["skipped_existing_count"],
            skipped_no_profile_count=counters["skipped_no_profile_count"],
            skipped_disabled_profile_count=counters["skipped_disabled_profile_count"],
            batch_limit=safe_limit,
            dry_run_before=dry_run_before,
        )

    def queue_readiness_report(self) -> MemoryQueueReadinessReport:
        summary = self.write_job_status_summary()
        issues: list[str] = []
        if summary.terminal_failed_count > 0:
            issues.append("Terminal failed memory jobs require operator review before migration.")
        if summary.stalled_processing_count > 0:
            issues.append("Stalled processing jobs should be resolved before external workers.")
        if summary.retryable_failed_count > 0:
            issues.append("Retryable failures exist; retry or inspect backend health first.")
        if summary.pending_count + summary.processing_count > 1000:
            issues.append("Large queue backlog should be drained before changing worker topology.")
        readiness_status = "ready" if not issues else "blocked"
        return MemoryQueueReadinessReport(
            status=readiness_status,
            pending_count=summary.pending_count,
            processing_count=summary.processing_count,
            failed_count=summary.failed_count,
            retryable_failed_count=summary.retryable_failed_count,
            terminal_failed_count=summary.terminal_failed_count,
            stalled_processing_count=summary.stalled_processing_count,
            due_count=summary.due_count,
            max_attempts=self._settings.memory_job_max_attempts,
            stalled_after_seconds=self._settings.memory_job_stalled_after_seconds,
            external_queue_ready=readiness_status == "ready",
            issues=issues,
        )

    def list_retrieval_logs(
        self,
        *,
        profile_id: uuid.UUID | None = None,
        limit: int = 20,
    ) -> list[MemoryRetrievalLogRecord]:
        safe_limit = max(1, min(limit, 100))
        statement: Select[tuple[MemoryRetrievalLog]] = (
            select(MemoryRetrievalLog)
            .order_by(MemoryRetrievalLog.occurred_at.desc())
            .limit(safe_limit)
        )
        if profile_id is not None:
            statement = (
                select(MemoryRetrievalLog)
                .where(MemoryRetrievalLog.backend_profile_id == profile_id)
                .order_by(MemoryRetrievalLog.occurred_at.desc())
                .limit(safe_limit)
            )
        return [_retrieval_log_record(model) for model in self._session.scalars(statement).all()]

    def run_eval_smoke(
        self,
        *,
        profile_id: uuid.UUID,
        limit: int = 5,
    ) -> MemoryEvalResult:
        profile = self._profile_service.get_profile(profile_id)
        if profile is None:
            raise LookupError("Memory backend profile not found")
        retrieval_logs = self.list_retrieval_logs(profile_id=profile_id, limit=limit)
        cases = [
            MemoryEvalCase(
                label=str(log.id),
                world_id=log.world_id,
                agent_id=log.agent_id,
                query_text=log.query_text,
                limit=max(1, min(log.context_item_count or 5, 10)),
            )
            for log in retrieval_logs
            if log.query_text.strip() != ""
        ]
        return run_memory_eval_cases(
            backend=profile.backend_kind.value,
            cases=cases,
            search_fn=self._eval_search,
        )

    def _due_jobs(self, limit: int) -> list[MemoryWriteJob]:
        safe_limit = max(0, min(limit, 200))
        if safe_limit == 0:
            return []
        statement: Select[tuple[MemoryWriteJob]] = (
            select(MemoryWriteJob)
            .join(World, MemoryWriteJob.world_id == World.id)
            .outerjoin(
                MemoryBackendProfile,
                MemoryWriteJob.backend_profile_id == MemoryBackendProfile.id,
            )
            .where(
                MemoryWriteJob.next_attempt_at <= datetime.now(UTC),
                or_(
                    MemoryBackendProfile.is_enabled.is_(True),
                    and_(
                        MemoryBackendProfile.id.is_(None),
                        World.memory_backend_profile_id.is_(None),
                        World.memory_plugin_identifier == BUILTIN_LOCAL_PGVECTOR_MEMORY,
                    ),
                ),
                (
                    (MemoryWriteJob.status == MemoryWriteJobStatus.PENDING.value)
                    | (
                        (MemoryWriteJob.status == MemoryWriteJobStatus.FAILED.value)
                        & (MemoryWriteJob.attempt_count < self._settings.memory_job_max_attempts)
                    )
                ),
            )
            .order_by(MemoryWriteJob.created_at.asc())
            .limit(safe_limit)
        )
        return list(self._session.scalars(statement).all())

    def _backend_for_scope(self, world_id: uuid.UUID) -> MemoryBackend:
        world = self._world_or_404(world_id)
        profile = self._backend_profile_for_world(world)
        return self._create_backend(
            world.memory_plugin_identifier, world.memory_plugin_config, profile
        )

    def _backend_for_job(self, job: MemoryWriteJob) -> MemoryBackend:
        world = self._world_or_404(job.world_id)
        profile = self._profile_service.get_profile(job.backend_profile_id)
        if profile is None:
            if world.memory_plugin_identifier == BUILTIN_LOCAL_PGVECTOR_MEMORY:
                profile = _local_fallback_profile(world.id)
            else:
                raise MemoryBackendUnavailableError("Memory backend profile not found")
        return self._create_backend(
            world.memory_plugin_identifier, world.memory_plugin_config, profile
        )

    def _create_backend(
        self,
        plugin_identifier: str,
        plugin_config: dict[str, Any],
        profile: MemoryBackendProfileRecord,
    ) -> MemoryBackend:
        try:
            plugin = cast(
                _MemoryBackendPlugin,
                get_builtin_plugin_registry().create(plugin_identifier, plugin_config),
            )
        except (PluginNotFoundError, PluginConfigValidationError, PluginFactoryError) as exc:
            raise MemoryBackendUnavailableError(str(exc)) from exc
        return plugin.create_backend(
            profile=profile, settings=self._settings, session=self._session
        )

    def _backend_profile_for_world(self, world: World) -> MemoryBackendProfileRecord:
        profile_id = world.memory_backend_profile_id
        if profile_id is None:
            if world.memory_plugin_identifier == BUILTIN_LOCAL_PGVECTOR_MEMORY:
                return _local_fallback_profile(world.id)
            raise MemoryBackendUnavailableError("World does not have a memory backend profile")
        profile = self._profile_service.get_profile(profile_id)
        if profile is None:
            raise MemoryBackendUnavailableError("Memory backend profile not found")
        if not profile.is_enabled:
            raise MemoryBackendUnavailableError("Memory backend profile is disabled")
        return profile

    def _scope_backend_name(self, world_id: uuid.UUID) -> str:
        world = self._world_or_404(world_id)
        profile_id = world.memory_backend_profile_id
        if profile_id is None:
            return world.memory_plugin_identifier
        profile = self._profile_service.get_profile(profile_id)
        if profile is None:
            return world.memory_plugin_identifier
        return profile.backend_kind.value

    def _job_backend_name(self, job: MemoryWriteJob) -> str:
        profile = self._profile_service.get_profile(job.backend_profile_id)
        if profile is None:
            return MEM0_OSS_BACKEND_NAME
        return profile.backend_kind.value

    def _eval_search(self, request: MemorySearchRequest) -> MemorySearchResult:
        return self._backend_for_scope(request.world_id).search(request)

    def _backfill_candidates(self, limit: int) -> list[_BackfillCandidate]:
        safe_limit = max(1, min(limit, 500))
        candidates: list[_BackfillCandidate] = []
        for run in self._session.scalars(
            select(AgentRuntimeRun)
            .where(
                AgentRuntimeRun.status == "succeeded",
                AgentRuntimeRun.response_text.is_not(None),
            )
            .order_by(AgentRuntimeRun.started_at.desc())
            .limit(safe_limit),
        ).all():
            if run.response_text is None:
                continue
            candidates.append(
                _BackfillCandidate(
                    source_kind=MemoryWriteSourceKind.AGENT_RUN,
                    world_id=run.world_id,
                    agent_id=run.agent_id,
                    source_id=run.id,
                    dedupe_key=f"agent-run:{run.id}",
                    content=run.response_text,
                    metadata={
                        "source_kind": "agent_run",
                        "run_id": str(run.id),
                        "trigger_source": run.trigger_source,
                    },
                ),
            )
        for turn in self._session.scalars(
            select(ConversationTurn)
            .where(
                ConversationTurn.status == "succeeded",
                ConversationTurn.output_text.is_not(None),
                ConversationTurn.speaker_agent_id.is_not(None),
            )
            .order_by(ConversationTurn.created_at.desc())
            .limit(safe_limit),
        ).all():
            session_model = self._session.get(ConversationSession, turn.session_id)
            if session_model is None or turn.speaker_agent_id is None or turn.output_text is None:
                continue
            candidates.append(
                _BackfillCandidate(
                    source_kind=MemoryWriteSourceKind.CONVERSATION_TURN,
                    world_id=session_model.world_id,
                    agent_id=turn.speaker_agent_id,
                    source_id=turn.id,
                    conversation_id=session_model.id,
                    dedupe_key=f"conversation-turn:{turn.id}",
                    content=turn.output_text,
                    metadata={
                        "source_kind": "conversation_turn",
                        "conversation_id": str(session_model.id),
                        "turn_index": turn.turn_index,
                    },
                ),
            )
        for event in self._session.scalars(
            select(WorldEventModel)
            .where(WorldEventModel.event_name.in_(MEMORY_BACKFILL_EVENT_NAMES))
            .order_by(WorldEventModel.wall_time.desc())
            .limit(safe_limit),
        ).all():
            agent_id = _event_agent_id(event)
            content = _event_content(event)
            if agent_id is None or content is None:
                continue
            candidates.append(
                _BackfillCandidate(
                    source_kind=MemoryWriteSourceKind.WORLD_EVENT,
                    world_id=event.world_id,
                    agent_id=agent_id,
                    source_id=event.id,
                    dedupe_key=f"world-event:{event.id}",
                    content=content,
                    metadata={
                        "source_kind": "world_event",
                        "event_name": event.event_name,
                        "event_id": str(event.id),
                    },
                ),
            )
        return candidates[:safe_limit]

    def _dedupe_exists(self, dedupe_key: str) -> bool:
        return (
            self._session.scalars(
                select(MemoryWriteJob.id).where(MemoryWriteJob.dedupe_key == dedupe_key),
            ).first()
            is not None
        )

    def _backfill_skip_reason(self, world: World) -> str | None:
        profile_id = world.memory_backend_profile_id
        if profile_id is None:
            if world.memory_plugin_identifier == BUILTIN_LOCAL_PGVECTOR_MEMORY:
                return None
            return "skipped_no_profile_count"
        profile = self._profile_service.get_profile(profile_id)
        if profile is None:
            return "skipped_no_profile_count"
        if not profile.is_enabled:
            return "skipped_disabled_profile_count"
        return None

    def _scrub_local_scope_data(self, world_id: uuid.UUID, agent_id: uuid.UUID) -> None:
        for job in self._session.scalars(
            select(MemoryWriteJob).where(
                MemoryWriteJob.world_id == world_id,
                MemoryWriteJob.agent_id == agent_id,
            ),
        ).all():
            job.last_error = "deleted_by_forget_scope"
            for write_log in self._session.scalars(
                select(MemoryWriteLog).where(MemoryWriteLog.job_id == job.id),
            ).all():
                write_log.request_summary = {"redacted": True}
                write_log.response_summary = {"redacted": True}
                write_log.correlation_ids = {
                    "world_id": str(world_id),
                    "agent_id": str(agent_id),
                    "redacted": True,
                }
        for retrieval_log in self._session.scalars(
            select(MemoryRetrievalLog).where(
                MemoryRetrievalLog.world_id == world_id,
                MemoryRetrievalLog.agent_id == agent_id,
            ),
        ).all():
            retrieval_log.query_text = "[redacted]"
            retrieval_log.hit_count = 0
            retrieval_log.selected_item_ids = []
            retrieval_log.context_item_count = 0
        snapshot = self._session.scalars(
            select(AgentProfileSnapshotModel).where(
                AgentProfileSnapshotModel.world_id == world_id,
                AgentProfileSnapshotModel.agent_id == agent_id,
            ),
        ).one_or_none()
        if snapshot is not None:
            snapshot.aliases = []
            snapshot.identity_notes = []
            snapshot.durable_preferences = []
            snapshot.long_lived_goals = []
            snapshot.language_style_preferences = []
            snapshot.refreshed_at = datetime.now(UTC)

    def _world_or_404(self, world_id: uuid.UUID) -> World:
        world = self._session.get(World, world_id)
        if world is None:
            raise LookupError("World not found")
        return world


def _profile_record(model: MemoryBackendProfile) -> MemoryBackendProfileRecord:
    return MemoryBackendProfileRecord(
        id=model.id,
        profile_key=model.profile_key,
        name=model.name,
        backend_kind=MemoryBackendKind(model.backend_kind),
        vector_store_config=model.vector_store_config,
        llm_config=model.llm_config,
        embedder_config=model.embedder_config,
        reranker_config=model.reranker_config,
        secret_refs=model.secret_refs,
        is_enabled=model.is_enabled,
        created_at=_aware_datetime(model.created_at),
        updated_at=_aware_datetime(model.updated_at),
    )


def _snapshot_record(model: AgentProfileSnapshotModel) -> MemoryProfileSnapshotRecord:
    return MemoryProfileSnapshotRecord(
        id=model.id,
        world_id=model.world_id,
        agent_id=model.agent_id,
        aliases=model.aliases,
        identity_notes=model.identity_notes,
        durable_preferences=model.durable_preferences,
        long_lived_goals=model.long_lived_goals,
        language_style_preferences=model.language_style_preferences,
        refreshed_at=_aware_datetime(model.refreshed_at),
        created_at=_aware_datetime(model.created_at),
        updated_at=_aware_datetime(model.updated_at),
    )


def _write_log_record(model: MemoryWriteLog) -> MemoryWriteLogRecord:
    return MemoryWriteLogRecord(
        id=model.id,
        job_id=model.job_id,
        backend=model.backend,
        success=model.success,
        latency_ms=model.latency_ms,
        request_summary=model.request_summary,
        response_summary=model.response_summary,
        correlation_ids=model.correlation_ids,
        occurred_at=_aware_datetime(model.occurred_at),
    )


def _write_job_record(
    model: MemoryWriteJob,
    profile: MemoryBackendProfile,
    settings: AppSettings,
    session: Session,
) -> MemoryWriteJobRecord:
    last_log_success = _last_write_log_success(session, model)
    now = datetime.now(UTC)
    return MemoryWriteJobRecord(
        id=model.id,
        world_id=model.world_id,
        agent_id=model.agent_id,
        backend_profile_id=model.backend_profile_id,
        backend_profile_key=profile.profile_key,
        backend_profile_name=profile.name,
        backend_kind=MemoryBackendKind(profile.backend_kind),
        source_kind=MemoryWriteSourceKind(model.source_kind),
        source_id=model.source_id,
        dedupe_key=model.dedupe_key,
        status=MemoryWriteJobStatus(model.status),
        attempt_count=model.attempt_count,
        next_attempt_at=_aware_datetime(model.next_attempt_at),
        last_error=model.last_error,
        processed_at=None if model.processed_at is None else _aware_datetime(model.processed_at),
        is_retryable=_is_retryable(model, profile, settings),
        terminal_reason=_terminal_reason(model, profile, settings),
        last_log_success=last_log_success,
        age_seconds=max(0, int((now - _aware_datetime(model.created_at)).total_seconds())),
        created_at=_aware_datetime(model.created_at),
        updated_at=_aware_datetime(model.updated_at),
    )


def _is_retryable(
    model: MemoryWriteJob,
    profile: MemoryBackendProfile,
    settings: AppSettings,
) -> bool:
    return (
        model.status == MemoryWriteJobStatus.FAILED.value
        and _terminal_reason(model, profile, settings) is None
    )


def _terminal_reason(
    model: MemoryWriteJob,
    profile: MemoryBackendProfile,
    settings: AppSettings,
) -> str | None:
    if model.status != MemoryWriteJobStatus.FAILED.value:
        return None
    if not profile.is_enabled:
        return "backend profile disabled"
    if model.attempt_count >= settings.memory_job_max_attempts:
        return "max attempts reached"
    return None


def _last_write_log_success(session: Session, model: MemoryWriteJob) -> bool | None:
    latest = session.scalars(
        select(MemoryWriteLog)
        .where(MemoryWriteLog.job_id == model.id)
        .order_by(MemoryWriteLog.occurred_at.desc())
        .limit(1),
    ).first()
    return None if latest is None else latest.success


def _empty_backfill_stats() -> dict[str, int]:
    return {
        "candidate_count": 0,
        "skipped_existing_count": 0,
        "skipped_no_profile_count": 0,
        "skipped_disabled_profile_count": 0,
    }


def _retrieval_log_record(model: MemoryRetrievalLog) -> MemoryRetrievalLogRecord:
    return MemoryRetrievalLogRecord(
        id=model.id,
        world_id=model.world_id,
        agent_id=model.agent_id,
        backend_profile_id=model.backend_profile_id,
        backend=model.backend,
        query_text=model.query_text,
        hit_count=model.hit_count,
        selected_item_ids=model.selected_item_ids,
        latency_ms=model.latency_ms,
        context_item_count=model.context_item_count,
        occurred_at=_aware_datetime(model.occurred_at),
    )


def _event_agent_id(event: WorldEventModel) -> uuid.UUID | None:
    raw_agent_id = event.payload.get("agent_id")
    if not isinstance(raw_agent_id, str):
        return None
    try:
        return uuid.UUID(raw_agent_id)
    except ValueError:
        return None


def _event_content(event: WorldEventModel) -> str | None:
    for key in ("content", "response_text", "text", "summary"):
        value = event.payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _snapshot_contract(record: MemoryProfileSnapshotRecord) -> AgentProfileSnapshot:
    return AgentProfileSnapshot(
        aliases=record.aliases,
        identity_notes=record.identity_notes,
        durable_preferences=record.durable_preferences,
        long_lived_goals=record.long_lived_goals,
        language_style_preferences=record.language_style_preferences,
    )


def _build_snapshot(items: list[MemoryItemRecord]) -> AgentProfileSnapshot:
    aliases: list[str] = []
    identity_notes: list[str] = []
    durable_preferences: list[str] = []
    long_lived_goals: list[str] = []
    language_style_preferences: list[str] = []
    for item in items[:50]:
        content = item.content.strip()
        lowered = content.lower()
        if (
            "alias" in lowered or "name is" in lowered or "i am" in lowered
        ) and content not in aliases:
            aliases.append(content)
        if (
            "style" in lowered or "tone" in lowered or "language" in lowered
        ) and content not in language_style_preferences:
            language_style_preferences.append(content)
        elif (
            "goal" in lowered or "plan" in lowered or "want to" in lowered
        ) and content not in long_lived_goals:
            long_lived_goals.append(content)
        elif (
            "prefer" in lowered or "likes" in lowered or "favorite" in lowered
        ) and content not in durable_preferences:
            durable_preferences.append(content)
        elif content not in identity_notes:
            identity_notes.append(content)
    return AgentProfileSnapshot(
        aliases=aliases[:8],
        identity_notes=identity_notes[:12],
        durable_preferences=durable_preferences[:12],
        long_lived_goals=long_lived_goals[:12],
        language_style_preferences=language_style_preferences[:8],
    )


def _aware_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _plugin_identifier_for_backend_kind(backend_kind: str) -> str:
    if backend_kind == "local_pgvector":
        return BUILTIN_LOCAL_PGVECTOR_MEMORY
    return BUILTIN_MEM0_OSS_MEMORY


def _local_fallback_profile(world_id: uuid.UUID) -> MemoryBackendProfileRecord:
    now = datetime.now(UTC)
    return MemoryBackendProfileRecord(
        id=uuid.uuid5(uuid.NAMESPACE_URL, f"noveland:local-pgvector:{world_id}"),
        profile_key="local-pgvector-fallback",
        name="Local pgvector fallback",
        backend_kind=MemoryBackendKind.LOCAL_PGVECTOR,
        vector_store_config={},
        llm_config={},
        embedder_config={},
        reranker_config={},
        secret_refs={},
        is_enabled=True,
        created_at=now,
        updated_at=now,
    )
