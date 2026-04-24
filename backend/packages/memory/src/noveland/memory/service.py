from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol, cast

from noveland.core.settings import AppSettings
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
    MemoryContext,
    MemoryContextItem,
    MemoryDeleteResult,
    MemoryDeleteScope,
    MemoryEvalCase,
    MemoryEvalResult,
    MemoryEvent,
    MemoryItemRecord,
    MemoryProfileSnapshotRecord,
    MemoryRetrievalLogRecord,
    MemorySearchRequest,
    MemorySearchResult,
    MemoryTurn,
    MemoryWriteJobStatus,
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
from sqlalchemy import Select, join, select
from sqlalchemy.orm import Session


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
            .where(
                MemoryWriteJob.status.in_(
                    [MemoryWriteJobStatus.PENDING.value, MemoryWriteJobStatus.FAILED.value],
                ),
                MemoryWriteJob.next_attempt_at <= datetime.now(UTC),
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
