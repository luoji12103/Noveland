# Implementation Brief: Pluggable Long-Term Memory v1 (Mem0-first)
**Attention: This is a general design architecture, you need to revise the designing scheme to adapt to the specific implementation of the current project.**

## Project adaptation note: Noveland

This document is adapted into Noveland with the following concrete boundaries:

- `world_id` is the primary application scope for long-term memory.
- `agent_id` is the private owner scope; long-term memory remains agent-private by default.
- `conversation_id`, `turn_id`, `run_id`, and `source_event_id` are attribution metadata, not replacement scopes.
- Noveland does not introduce a separate raw `conversation_event_log`; first-party raw source-of-truth already exists in `world_events`, `conversation_turns`, and `agent_runtime_runs`.
- Backend selection is platform-owned through `memory_backend_profiles`; worlds bind to a profile through `worlds.memory_backend_profile_id`.
- Runtime and conversation flows write long-term memory asynchronously through database-backed jobs processed behind `MemoryService`.
- Application code, runtime, conversation services, and persona policy code use `MemoryService` and internal contracts only; they do not import Mem0 SDK types directly.
- The v1 Web memory surface is read-only for operators: inspect, search, profile snapshot refresh, forget, health, logs, and eval smoke.
- The current baseline is Mem0 OSS-first with a local pgvector fallback backend retained for tests and fallback coverage.
## 1. Objective

Build a **production-usable v1 long-term memory subsystem** for an AI application using **Mem0 as the initial backend**, while keeping the business/application layer insulated behind our own abstractions so that we can later replace the backend with a more advanced custom long-term memory architecture.

The goal of this phase is **not** to invent a new memory algorithm. The goal is to:

1. ship a usable persistent memory capability quickly;
2. preserve clean seams for backend replacement;
3. log enough ground truth to support future migration and evaluation;
4. avoid coupling agent/business logic directly to Mem0 APIs.

## 2. High-level decision

Use **Mem0 as the first-generation memory engine** behind an internal `MemoryBackend` interface.

All application code must depend only on our interfaces and contracts, never on Mem0 SDK types directly.

We will keep:

- our own event log for raw conversation/application events;
- our own retrieval/context assembly layer;
- our own profile snapshot layer;
- our own evaluation harness;
- our own audit/logging around memory reads/writes.

This allows a future `NextGenMemoryBackend` to be implemented without rewriting the application layer.

## 3. Why this architecture

Mem0’s current architecture is already closer to the direction we want than older memory systems:

- extraction is **single-pass ADD-only**;
- retrieval is **multi-signal hybrid**;
- **entity linking** is built in;
- current ranking behavior handles historical facts at retrieval time rather than destructive UPDATE/DELETE.

This makes it a good v1 engine, but **not** the final system boundary.

## 4. Scope for v1

### In scope

- Internal memory abstraction and Mem0-backed implementation
- Memory write pipeline from application events / chat turns
- Memory search and context assembly
- Lightweight profile snapshot store
- Retrieval/write/audit logging
- Contract tests and evaluation harness
- Feature flags / configuration for backend selection
- Basic observability and metrics

### Out of scope

- Building a new graph-native temporal memory system
- Multi-agent retrieval planners
- Advanced contradiction resolution beyond simple ranking/filters
- Full historical backfill migration of all legacy data unless already available in clean event logs
- UI/dashboard beyond minimal internal inspection utilities

## 5. Implementation principles

1. **Application layer must not import Mem0 directly.**
2. **Raw events are first-party data and must be stored by us.**
3. **Every memory read/write must be auditable.**
4. **Context assembly belongs to our code, not to the backend SDK.**
5. **Backend swap must require only wiring changes plus passing the same contract tests.**
6. **Async write path by default.** Memory persistence should not block primary user response unless explicitly configured.
7. **Deletion/privacy must be controlled from our boundary**, even if the backend provides its own delete semantics.

## 6. Recommended stack

### Language and framework

- Python 3.12
- FastAPI for service/API surface
- Pydantic v2 for schema/contracts
- httpx for service clients

### Storage

- PostgreSQL for:
  - raw event log
  - profile snapshots
  - audit logs
  - retrieval/write observations
  - configuration and feature flags if needed
- Redis for short-lived caching and queue coordination

### Memory backend

- Mem0 Platform preferred for fastest v1 if managed service is acceptable
- Mem0 OSS if self-hosting / data residency / infra control is required

### Async jobs

One of:

- Temporal
- Celery
- Dramatiq

Choose the one already aligned with the existing project.

### Testing and quality

- pytest
- pytest-asyncio
- respx or equivalent for external API mocking
- mypy or pyright
- ruff

### Optional orchestration layer

- LangGraph may be used by the application/agent runtime
- Memory subsystem should remain independently testable and not require LangGraph-specific runtime coupling

## 7. Required repository structure

```text
memory/
  backend/
    base.py
    mem0_backend.py
    nextgen_backend.py
    factory.py
  contracts/
    memory_models.py
    requests.py
    responses.py
  pipeline/
    write_pipeline.py
    retrieval_pipeline.py
    context_builder.py
    profile_updater.py
  storage/
    event_log_repo.py
    profile_repo.py
    audit_repo.py
    observations_repo.py
  service/
    memory_service.py
    profile_service.py
  evals/
    datasets/
    runners/
    reports/
    contract_tests/
  config/
    settings.py
    feature_flags.py
  api/
    routes.py
    admin_routes.py
```

Keep the rest of the application dependent on `memory.service.memory_service` or equivalent façade, not on backend internals.

## 8. Core abstractions

### 8.1 `MemoryBackend`

Create a backend protocol / abstract base class:

```python
class MemoryBackend(Protocol):
    async def add_turn(self, turn: MemoryTurn) -> WriteResult: ...
    async def add_events(self, events: list[MemoryEvent]) -> BatchWriteResult: ...
    async def search(self, req: MemorySearchRequest) -> MemorySearchResult: ...
    async def get_profile_candidates(self, req: ProfileCandidateRequest) -> list[ProfileCandidate]: ...
    async def delete_scope(self, req: DeleteScopeRequest) -> DeleteResult: ...
    async def healthcheck(self) -> BackendHealth: ...
```

### 8.2 `MemoryService`

Application-facing façade:

```python
class MemoryService:
    async def record_turn(...): ...
    async def record_events(...): ...
    async def build_context(...): ...
    async def get_profile_snapshot(...): ...
    async def forget_user(...): ...
```

This service is the only entry point the application should use.

### 8.3 `ContextBuilder`

Own the final prompt/context assembly here. The builder should:

- call backend retrieval;
- merge with profile snapshot;
- deduplicate items;
- cap tokens/items by policy;
- return a stable `MemoryContext` object for downstream prompting.

### 8.4 `ProfileSnapshot`

Maintain our own lightweight structured profile independent of Mem0. This should hold only stable, high-value fields such as:

- user name / aliases
- language preference
- timezone
- durable preferences
- role/account metadata
- long-lived goals if product-relevant

Do **not** store everything here. This is a stable structured overlay, not the primary memory engine.

## 9. Data contracts

Codex should define Pydantic models for at least the following.

### 9.1 Input/event models

- `MemoryTurn`
- `MemoryMessage`
- `MemoryEvent`
- `MemoryEventMetadata`

Minimum fields:

- `app_id`
- `tenant_id`
- `user_id`
- `thread_id`
- `session_id`
- `turn_id` / `event_id`
- `timestamp`
- `actor` (`user`, `assistant`, `system`, `tool`, `external_event`)
- `content`
- `metadata`
- `trace_id`

### 9.2 Retrieval models

- `MemorySearchRequest`
- `MemoryHit`
- `MemorySearchResult`
- `MemoryContext`

Minimum fields for `MemoryHit`:

- `id`
- `text`
- `score`
- `source_type`
- `backend`
- `created_at`
- `user_id`
- `thread_id` or namespace
- `metadata`
- `explanations` or score breakdown if available

### 9.3 Audit/log models

- `MemoryWriteLog`
- `MemoryRetrievalObservation`
- `MemoryContextAssemblyLog`
- `BackendErrorLog`

These should capture request/response summaries, not only exceptions.

## 10. Write path

### Required flow

1. Application receives a user turn or external event.
2. Persist raw event/turn to our own `event_log` table first.
3. Enqueue async memory write job.
4. Worker loads event payload and calls `Mem0Backend.add_turn()` or `add_events()`.
5. Persist write observation log:
   - success/failure
   - latency
   - backend request id if available
   - trace_id correlation
6. Optionally trigger profile snapshot refresh.

### Important constraints

- The user-facing response path should not depend on successful memory write completion by default.
- Writes must be idempotent by our own event IDs or trace IDs where possible.
- Failures must be retryable without duplicating raw event storage.

## 11. Read path

### Required flow

1. Application asks for memory context for a new turn/task.
2. `MemoryService.build_context()` creates a normalized `MemorySearchRequest`.
3. `Mem0Backend.search()` performs backend retrieval.
4. `ContextBuilder` merges:
   - backend retrieval results
   - profile snapshot
   - optional recent thread state supplied by caller
5. Builder applies:
   - deduplication
   - stale/noisy item filtering
   - max item count
   - max token budget
   - stable formatting contract
6. Return `MemoryContext` to downstream prompt/agent logic.
7. Log retrieval observation and context assembly metrics.

### Important constraint

The application must never depend on raw Mem0 response shape. Only our normalized `MemorySearchResult` and `MemoryContext` should leave the memory module.

## 12. Mem0-specific implementation guidance

### 12.1 Backend wrapper

The Mem0 backend implementation should translate our contracts to Mem0 SDK/API calls and back.

Do not leak:

- Mem0 request parameter names
- Mem0 response schemas
- Mem0-specific exceptions
- Mem0-specific filtering structure

Wrap them into our own models/exceptions.

### 12.2 OSS vs Platform

Support both through configuration if practical, but optimize for one active mode in v1.

Suggested config:

```python
MEMORY_BACKEND=mem0
MEM0_MODE=platform | oss
MEM0_API_KEY=...
MEM0_API_URL=...
MEM0_PROJECT_ID=...
```

### 12.3 Feature flags

Implement feature flags for:

- enable/disable memory writes
- enable/disable retrieval
- backend selection
- async vs sync writes
- profile snapshot updates
- request/response debug logging

## 13. Local data we must own even in v1

Create our own tables or equivalents for:

### `conversation_event_log`
Stores raw source events/turns.

### `memory_write_log`
Stores backend write attempts and outcomes.

### `retrieval_observation_log`
Stores retrieval request, hit counts, selected items, latency, token budget usage.

### `profile_snapshot`
Stores our structured overlay profile.

### `memory_backend_config`
Optional: stores backend settings per tenant/environment if needed.

This is non-negotiable if we want a clean future migration path.

## 14. Public/internal API surface

Implement a small internal service API only if needed by the existing system.

Recommended internal endpoints:

- `POST /memory/turns`
- `POST /memory/events`
- `POST /memory/context`
- `GET /memory/profile/{user_id}`
- `DELETE /memory/users/{user_id}`
- `GET /memory/health`

If the application is monolithic, these can be service methods instead of HTTP endpoints.

## 15. Error handling rules

Codex should implement explicit typed exceptions:

- `MemoryBackendUnavailableError`
- `MemoryWriteFailedError`
- `MemorySearchFailedError`
- `MemoryPrivacyDeletionError`
- `MemoryContractViolationError`

Rules:

- backend failures must not crash unrelated application flows unless memory is explicitly mandatory for that route;
- reads should degrade gracefully to empty memory context;
- writes should retry via queue policy;
- all failures must be logged with trace correlation.

## 16. Observability and metrics

Emit at minimum:

- write success rate
- write latency p50/p95
- retrieval latency p50/p95
- retrieval hit count
- context token count
- context item count
- empty retrieval rate
- backend error rate
- queue retry count

If the project already uses OpenTelemetry, add spans around:

- event log write
- backend write
- backend search
- context assembly
- profile snapshot update

## 17. Security and privacy requirements

- Namespace/scoping must prevent cross-user or cross-tenant leakage.
- Forget/delete requests must delete from our local stores and invoke backend deletion for the relevant scope.
- Avoid storing secrets or access tokens in memory payloads.
- Support PII minimization hooks before writes if the product requires it.
- Audit all deletion requests.

## 18. Acceptance criteria for v1

Codex should treat the following as hard acceptance criteria.

### Functional

1. Application code uses only `MemoryService` / our contracts.
2. Mem0 can be fully disabled via config without breaking core app flows.
3. Raw events are stored locally before async memory write.
4. Retrieval returns normalized `MemoryContext`, not backend-native payloads.
5. Profile snapshots can be retrieved independently of Mem0.
6. Deletion/forget flow works across local data and backend scope.

### Replaceability

7. A `NextGenMemoryBackend` stub exists and passes import/type checks.
8. Contract tests can run against both `Mem0Backend` and a fake/in-memory backend.
9. No business module imports Mem0 directly.

### Reliability

10. Write retries are idempotent or bounded by dedupe keys.
11. Retrieval failures degrade to empty context, not hard crashes.
12. Logs/metrics exist for both reads and writes.

## 19. Test plan

### Unit tests

- contract model validation
- backend adapter translation
- context builder behavior
- profile merge behavior
- feature flag behavior
- deletion logic

### Integration tests

- record turn -> event log persisted -> backend write invoked
- build context -> retrieval normalized -> prompt context produced
- backend down -> graceful degradation
- duplicate write event -> no duplicate local event record / bounded backend retries

### Contract tests

Create a shared contract test suite that any backend implementation must pass:

- add turn
- add events
- search
- delete scope
- healthcheck
- empty response handling
- malformed backend response handling

### Eval harness

Provide a minimal evaluation runner that can replay a small representative dataset and record:

- answer accuracy proxy or retrieval hit proxy
- average retrieved items
- estimated token count
- latency

This does not need to be benchmark-perfect in v1. It must exist so that future backend replacement can be compared objectively.

## 20. Migration path to next-generation memory

Design v1 so we can later build a custom backend with:

- raw event ingestion from the same event log
- atomic memory layer
- structured profile layer
- temporal/entity graph
- custom hybrid retrieval/reranking

This future backend should implement the same `MemoryBackend` interface. The application layer should not need major changes.

## 21. Explicit non-goals for Codex in this phase

Codex should **not**:

- redesign the product’s overall agent architecture;
- invent a new memory algorithm;
- hardwire Mem0-specific data types into prompts/business logic;
- build speculative graph-memory features beyond stubs/interfaces;
- add unnecessary infrastructure not justified by the current codebase.

## 22. Preferred execution order for Codex

1. Define contracts and interfaces.
2. Create local persistence models/repos for event log, profile snapshot, audit logs.
3. Implement `Mem0Backend` adapter.
4. Implement `MemoryService` façade.
5. Implement write pipeline and queue worker.
6. Implement retrieval pipeline and `ContextBuilder`.
7. Add feature flags/config.
8. Add tests.
9. Add eval harness.
10. Add `NextGenMemoryBackend` stub and backend factory wiring.

## 23. Definition of done

This phase is done when:

- a user turn can be recorded through our service boundary;
- it is persisted to our event log;
- it is asynchronously written to Mem0;
- a later request can retrieve a normalized memory context through our own abstraction;
- the system can run with memory disabled;
- the codebase is structurally ready for a future backend replacement.

## 24. Notes for future branch

When the dedicated next-generation memory branch starts, it should reuse:

- `MemoryBackend`
- `MemoryService`
- local event log
- retrieval observation log
- eval harness
- contract tests

The new branch should replace only the backend implementation and related retrieval/indexing internals.

## 25. Reference constraints informing this brief

This brief is based on current public documentation indicating that modern Mem0 architecture uses:

- single-pass ADD-only extraction;
- multi-signal hybrid retrieval;
- entity linking;
- retrieval-time handling of historical/current fact ranking;
- managed Platform and self-hosted OSS deployment options.

Also relevant is LangGraph’s separation of short-term thread memory from long-term namespaced memory, which supports keeping memory infrastructure behind a clean application boundary rather than coupling it to a single runtime.

## 26. Optional appendix: minimal fake backend for tests

Codex should consider adding an in-memory fake backend that stores normalized `MemoryHit` records in Python structures so contract tests can run without external services.

This fake backend should be intentionally simple and deterministic.


## 27. References

- Mem0 Platform Overview: https://docs.mem0.ai/platform/overview
- Mem0 Platform Migration to New Memory Algorithm: https://docs.mem0.ai/migration/platform-v2-to-v3
- Mem0 OSS Migration to New Memory Algorithm: https://docs.mem0.ai/migration/oss-v2-to-v3
- Mem0 Memory Evaluation: https://docs.mem0.ai/core-concepts/memory-evaluation
- Mem0 Changelog Highlights: https://docs.mem0.ai/changelog/highlights
- LangGraph Memory Overview: https://docs.langchain.com/oss/python/concepts/memory
- LangGraph Long-Term Memory: https://docs.langchain.com/oss/python/langchain/long-term-memory
