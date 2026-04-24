from __future__ import annotations

import time
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from noveland.core.settings import AppSettings
from noveland.memory.contracts import (
    MemoryBackendHealth,
    MemoryBackendHealthStatus,
    MemoryBackendProfileRecord,
    MemoryDeleteResult,
    MemoryDeleteScope,
    MemoryEvent,
    MemoryItemRecord,
    MemorySearchRequest,
    MemorySearchResult,
    MemoryTurn,
    MemoryWriteResult,
)
from noveland.memory.errors import (
    MemoryBackendUnavailableError,
    MemoryContractViolationError,
    MemoryPrivacyDeletionError,
    MemorySearchFailedError,
    MemoryWriteFailedError,
)

BACKEND_NAME = "mem0_oss"


class Mem0OssMemoryBackend:
    def __init__(
        self,
        profile: MemoryBackendProfileRecord,
        settings: AppSettings,
    ) -> None:
        if profile.backend_kind.value != BACKEND_NAME:
            raise MemoryBackendUnavailableError(
                f"memory profile {profile.profile_key} does not use the mem0_oss backend",
            )
        self._profile = profile
        self._settings = settings
        self._client: Any | None = None

    def record_turn(self, turn: MemoryTurn) -> MemoryWriteResult:
        started_at = time.perf_counter()
        try:
            result = self._client_instance().add(
                messages=[message.model_dump(mode="json") for message in turn.messages],
                user_id=str(turn.agent_id),
                agent_id=str(turn.agent_id),
                app_id=str(turn.world_id),
                run_id=_run_scope(turn.run_id, turn.turn_id, turn.source_event_id),
                metadata={
                    **turn.metadata,
                    "world_id": str(turn.world_id),
                    "agent_id": str(turn.agent_id),
                    "conversation_id": _string(turn.conversation_id),
                    "turn_id": _string(turn.turn_id),
                    "run_id": _string(turn.run_id),
                    "source_event_id": _string(turn.source_event_id),
                    "trigger_source": turn.trigger_source,
                },
            )
        except Exception as exc:  # pragma: no cover - exercised through service tests
            raise MemoryWriteFailedError(str(exc)) from exc
        return MemoryWriteResult(
            backend=BACKEND_NAME,
            source_dedupe_key=turn.dedupe_key,
            recorded_count=len(_memory_ids(result)),
            backend_ids=_memory_ids(result),
            latency_ms=_elapsed_ms(started_at),
        )

    def record_events(self, events: Sequence[MemoryEvent]) -> MemoryWriteResult:
        started_at = time.perf_counter()
        backend_ids: list[str] = []
        try:
            client = self._client_instance()
            for event in events:
                result = client.add(
                    messages=[{"role": "system", "content": event.content}],
                    user_id=str(event.agent_id),
                    agent_id=str(event.agent_id),
                    app_id=str(event.world_id),
                    run_id=_run_scope(event.run_id, event.event_id, event.event_id),
                    metadata={
                        **event.metadata,
                        "world_id": str(event.world_id),
                        "agent_id": str(event.agent_id),
                        "event_id": str(event.event_id),
                        "run_id": _string(event.run_id),
                    },
                    infer=False,
                )
                backend_ids.extend(_memory_ids(result))
        except Exception as exc:  # pragma: no cover - exercised through service tests
            raise MemoryWriteFailedError(str(exc)) from exc
        dedupe_key = events[0].dedupe_key if events else "no-events"
        return MemoryWriteResult(
            backend=BACKEND_NAME,
            source_dedupe_key=dedupe_key,
            recorded_count=len(backend_ids),
            backend_ids=backend_ids,
            latency_ms=_elapsed_ms(started_at),
        )

    def list_memories(self, world_id: uuid.UUID, agent_id: uuid.UUID) -> Sequence[MemoryItemRecord]:
        try:
            payload = self._client_instance().get_all(
                filters=_scope_filters(world_id, agent_id),
            )
        except Exception as exc:  # pragma: no cover - exercised through service tests
            raise MemorySearchFailedError(str(exc)) from exc
        return _coerce_items(payload, world_id, agent_id)

    def search(self, request: MemorySearchRequest) -> MemorySearchResult:
        started_at = time.perf_counter()
        try:
            payload = self._client_instance().search(
                request.query_text,
                filters=_scope_filters(request.world_id, request.agent_id),
                top_k=request.limit,
            )
        except Exception as exc:  # pragma: no cover - exercised through service tests
            raise MemorySearchFailedError(str(exc)) from exc
        return MemorySearchResult(
            backend=BACKEND_NAME,
            items=_coerce_items(payload, request.world_id, request.agent_id),
            latency_ms=_elapsed_ms(started_at),
        )

    def delete_scope(self, scope: MemoryDeleteScope) -> MemoryDeleteResult:
        try:
            if scope.run_id is None:
                result = self._client_instance().delete_all(
                    user_id=str(scope.agent_id),
                    agent_id=str(scope.agent_id),
                    app_id=str(scope.world_id),
                )
            else:
                result = self._client_instance().delete_all(
                    user_id=str(scope.agent_id),
                    agent_id=str(scope.agent_id),
                    app_id=str(scope.world_id),
                    run_id=str(scope.run_id),
                )
        except Exception as exc:  # pragma: no cover - exercised through service tests
            raise MemoryPrivacyDeletionError(str(exc)) from exc
        deleted_count = None
        if isinstance(result, dict):
            raw_count = result.get("deleted_count")
            if isinstance(raw_count, int):
                deleted_count = raw_count
        return MemoryDeleteResult(backend=BACKEND_NAME, deleted_count=deleted_count)

    def healthcheck(self) -> MemoryBackendHealth:
        try:
            self._client_instance().get_all(filters={"app_id": "__noveland_healthcheck__"})
        except Exception as exc:
            return MemoryBackendHealth(
                backend=BACKEND_NAME,
                status=MemoryBackendHealthStatus.UNAVAILABLE,
                details={"error": str(exc), "profile_key": self._profile.profile_key},
            )
        return MemoryBackendHealth(
            backend=BACKEND_NAME,
            status=MemoryBackendHealthStatus.OK,
            details={"profile_key": self._profile.profile_key},
        )

    def _client_instance(self) -> Any:
        if self._client is None:
            try:
                from mem0 import Memory  # type: ignore[import-untyped]
            except Exception as exc:  # pragma: no cover - import behavior depends on env
                raise MemoryBackendUnavailableError(
                    "mem0ai is not installed for the configured mem0_oss backend",
                ) from exc
            self._client = Memory.from_config(_resolved_config(self._profile, self._settings))
        return self._client


def _resolved_config(
    profile: MemoryBackendProfileRecord,
    settings: AppSettings,
) -> dict[str, Any]:
    config = {
        "vector_store": dict(profile.vector_store_config),
        "llm": dict(profile.llm_config),
        "embedder": dict(profile.embedder_config),
    }
    if profile.reranker_config:
        config["reranker"] = dict(profile.reranker_config)

    secret_values = settings.memory_backend_secrets_json
    _inject_secret(config.get("vector_store"), "vector_store_api_key", secret_values, profile)
    _inject_secret(config.get("llm"), "llm_api_key", secret_values, profile)
    _inject_secret(config.get("embedder"), "embedder_api_key", secret_values, profile)
    _inject_secret(config.get("reranker"), "reranker_api_key", secret_values, profile)
    return config


def _inject_secret(
    config_section: dict[str, Any] | None,
    secret_slot: str,
    secret_values: dict[str, str],
    profile: MemoryBackendProfileRecord,
) -> None:
    if config_section is None:
        return
    section_config = config_section.setdefault("config", {})
    if not isinstance(section_config, dict):
        raise MemoryBackendUnavailableError(
            f"memory backend profile {profile.profile_key} has invalid {secret_slot} config",
        )
    secret_ref = profile.secret_refs.get(secret_slot)
    if secret_ref is None:
        return
    secret_value = secret_values.get(secret_ref)
    if secret_value is None:
        raise MemoryBackendUnavailableError(
            "memory backend secret ref "
            f"{secret_ref} is missing from NOVELAND_MEMORY_BACKEND_SECRETS_JSON",
        )
    section_config.setdefault("api_key", secret_value)


def _scope_filters(world_id: uuid.UUID, agent_id: uuid.UUID) -> dict[str, str]:
    scope_id = str(agent_id)
    return {"app_id": str(world_id), "agent_id": scope_id, "user_id": scope_id}


def _coerce_items(payload: Any, world_id: uuid.UUID, agent_id: uuid.UUID) -> list[MemoryItemRecord]:
    raw_items: Any
    if isinstance(payload, dict):
        raw_items = payload.get("results", payload.get("memories", payload))
    else:
        raw_items = payload
    if not isinstance(raw_items, list):
        raise MemoryContractViolationError("memory backend returned a non-list payload")

    records: list[MemoryItemRecord] = []
    for item in raw_items:
        if not isinstance(item, dict):
            raise MemoryContractViolationError("memory backend returned a malformed item")
        content = item.get("memory") or item.get("text") or item.get("content")
        if not isinstance(content, str):
            raise MemoryContractViolationError("memory backend item is missing text content")
        metadata = item.get("metadata")
        records.append(
            MemoryItemRecord(
                id=str(item.get("id", uuid.uuid4())),
                world_id=world_id,
                agent_id=agent_id,
                content=content,
                metadata=metadata if isinstance(metadata, dict) else {},
                backend=BACKEND_NAME,
                created_at=_parse_datetime(item.get("created_at")),
                score=_parse_score(item.get("score")),
            ),
        )
    return records


def _memory_ids(payload: Any) -> list[str]:
    if isinstance(payload, list):
        ids = []
        for entry in payload:
            if isinstance(entry, dict) and "id" in entry:
                ids.append(str(entry["id"]))
        return ids
    if isinstance(payload, dict) and "id" in payload:
        return [str(payload["id"])]
    return []


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
        except ValueError:
            return None
    return None


def _parse_score(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _run_scope(
    run_id: uuid.UUID | None,
    turn_id: uuid.UUID | None,
    source_event_id: uuid.UUID | None,
) -> str:
    return str(run_id or turn_id or source_event_id or uuid.uuid4())


def _elapsed_ms(started_at: float) -> int:
    return int((time.perf_counter() - started_at) * 1000)


def _string(value: uuid.UUID | None) -> str | None:
    return None if value is None else str(value)
