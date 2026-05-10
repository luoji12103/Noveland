# Noveland Current System Architecture Review

Date: 2026-05-10

Purpose: give architects a compact but complete view of the current Noveland
codebase before choosing the next framework design and implementation path.

## Executive Summary

Noveland is currently a local-first persistent virtual-world operating system for
AI agents. The implemented product direction is no longer a generic chatbot or a
generic office-agent workflow tool. The active product shape is a galgame
sequel-style living world: an already-finished story world can continue running
with characters, relationships, organizations, branches, player choices, memory,
daily events, narrative artifacts, and release-readiness evidence.

The V1 50-phase roadmap and the V2 living-world phases 1-50 are implemented
locally. The later V2 remediation and hardening work also landed locally:
worldline memory isolation, prompt/publish leak guardrails, runtime GM/narrative
execution depth, beta gate hardening, release evidence gates, beta GM loop
evidence, Web mock parity, and Mem0 worldline isolation contracts.

The current system is strong as a deterministic local development and beta
evidence platform. It is not yet a public production launch system. Provider
profiles and provider-backed agent runs exist, but GM planning, beta evaluation,
release evidence, authoring imports, and most living-world control loops are
deterministic and local by design. External tool execution remains policy-only.

## Current Source Of Record

Use these files to verify current state:

- `docs/agent/harness/task-board.md`: current execution state. It currently has
  no Open, In Progress, or Blocked items.
- `docs/agent/harness/debug-journal.md`: acceptance and remediation reports.
  The 2026-05-10 closure report supersedes the 2026-05-09 remaining-risk bullets.
- `docs/agent/harness/change-journal.md`: implementation history and branch
  summaries.
- `docs/agent/harness/roadmap-v2-living-world.md`: long-term V2 direction and
  historical phase plan, not the active task board.
- `docs/agent/harness/project-index.md`: stable entrypoint map.
- `docs/agent/harness/file-inventory.md`: registered structural files.

## Stack

Backend:

- Python 3.12
- FastAPI
- Pydantic v2
- SQLAlchemy 2.x
- Alembic
- uv workspace
- PostgreSQL 16 with pgvector
- NATS JetStream for event publication surfaces

Frontend:

- Next.js 16
- React 19
- TypeScript 6
- Tailwind CSS 4
- Vitest
- Playwright

Local infrastructure:

- `infra/compose.yaml`: PostgreSQL/pgvector and NATS JetStream.
- Local object storage under `NOVELAND_OBJECT_STORAGE_ROOT`, defaulting to a
  local filesystem root.

## Architectural Shape

The project is organized as a backend workspace plus a Next.js Web app.

```text
Web app
  Next app routes
  same-origin API proxies
  feature components
  typed client/server helpers

Backend API
  FastAPI routers
  auth and authorization dependencies
  DTO mapping and request validation

Domain packages
  worlds, agents, conversations, narrative, memory, events, calendar,
  auth, adapters, plugins, observability, storage

Runtime services
  clock tick
  agent loop
  conversation loop
  living-world autonomy/GM loop
  memory write job processing

Persistence and integration
  PostgreSQL + pgvector
  Alembic migrations
  NATS event publisher
  local object storage
```

The strongest architectural boundaries are:

- `world_id` is the primary multi-world boundary.
- `worldline_id` is the branch/history boundary for V2 living-world state.
- `world_events` is the canonical append-only event stream.
- Runtime, conversation, narrative, and GM paths must go through service
  boundaries rather than importing memory backend SDKs directly.
- `MemoryService` is the long-term memory facade.
- `LivingWorldContextSelector` is the prompt/review visibility boundary for
  knowledge, secrets, emotional state, relationship summaries, and world context.
- Web routes should extend existing world/admin/reader surfaces instead of
  creating parallel apps.

## Backend Modules

### API Service

Location: `backend/services/api/src/noveland/services/api/`

Main routers:

- `auth.py`: CSRF, login, current subject, logout.
- `worlds.py`: the largest API surface. It covers worlds, scenes, memberships,
  agents, clocks, events, snapshots, replay, schedules, living-world V2 state,
  release readiness, narrative artifacts, and most admin operations.
- `conversations.py`: conversation sessions, participants, turns, start/pause,
  manual advance, memory/writer configs, and narrative generation actions.
- `runtime.py`: runtime control/status/supervision, diagnostics, metrics,
  provider profiles, plugin bindings, memory backend profiles, memory jobs,
  backfill, queue readiness, tool policy, and scale readiness.
- `realtime.py`: runtime/world/conversation SSE and conversation live WebSocket.
- `authorization.py`, `dependencies.py`, `csrf.py`: request-level access and
  safety plumbing.

Current design issue: `worlds.py` is now a very large orchestration router. It is
functional and covered by tests, but future framework work should consider
extracting route groups or service adapters around stable subdomains before
adding another large feature wave.

### Runtime Service

Location: `backend/services/runtime/src/noveland/services/runtime/`

Runtime components:

- `daemon.py`: database-backed runtime loop. A running iteration advances clocks,
  runs due agents, advances running conversations, executes living-world autonomy
  work, processes memory jobs, records diagnostics, and commits as one loop.
- `clock_tick.py`: advances world clocks and emits clock/world events.
- `agent_loop.py`: provider-backed agent execution. It builds prompt context from
  persona, observations, memory, living-world visibility selection, and world
  context packs. It records runtime runs, world events, memory jobs, diagnostics,
  and optional narrative artifacts.
- `conversation_loop.py`: deterministic conversation advancement for running
  sessions.
- `identity.py`: shared runtime actor reference.

Runtime is intentionally deterministic except for configured provider calls in
agent execution. GM macro planning and beta evaluation do not call providers.

### Domain Packages

Important packages:

- `noveland.worlds`: world model, world bible, worldlines, organizations,
  presence, daily/offscreen events, GM, conditions, plot/route/rumor flow,
  knowledge/secrets, guardrails, beta readiness, release profiles.
- `noveland.agents`: agent identity, structured character metadata,
  relationship graph, presets, runtime runs, persona, observations.
- `noveland.conversations`: conversation sessions, participants, turns, policies,
  stop conditions, writer config, memory config, group context metadata.
- `noveland.narrative`: narrative artifacts, publications, writer pipeline, and
  publication metadata.
- `noveland.memory`: memory backend profiles, fake/local/Mem0 adapters, async
  write jobs, retrieval logs, profile snapshots, forget, backfill, evals, queue
  readiness.
- `noveland.events`: world events, snapshots, replay reconstruction, event
  publication envelopes.
- `noveland.calendar`: calendar entries and schedule rules.
- `noveland.adapters`: provider profiles, reliability settings, provider
  test-call support.
- `noveland.plugins`: built-in plugin registry, manifests, binding validation.
- `noveland.observability`: runtime diagnostics, retention dry-run/prune,
  severity/component contracts.
- `noveland.storage`: local object storage and backup verification.
- `noveland.auth`: users, credentials, sessions, platform roles, admin seeding.

## Data Model Overview

The current schema is large and V2-heavy. Key model families:

World core:

- `World`
- `WorldBible`
- `Worldline`
- `WorldMembership`
- `Scene`
- `WorldClockStateModel`
- `WorldClockTransitionModel`

Agent and conversation:

- `Agent`
- `AgentRelationshipEdge`
- `AgentPreset`
- `AgentRuntimeRun`
- `AgentPersona`
- `AgentObservation`
- `ConversationSession`
- `ConversationParticipant`
- `ConversationTurn`

Events, snapshots, narrative:

- `WorldEventModel`
- `WorldSnapshotModel`
- `NarrativeArtifact`
- `NarrativePublication`

Memory:

- `MemoryBackendProfile`
- `AgentMemoryItem`
- `MemoryWriteJob`
- `MemoryWriteLog`
- `MemoryRetrievalLog`
- `AgentProfileSnapshotModel`

Living-world autonomous systems:

- `WorldOrganization`
- `OrganizationMembership`
- `FactionProgressTrack`
- `SceneLocationEdge`
- `AgentPresenceState`
- `DailyLifeEventCandidate`
- `OffscreenEventQueueItem`

GM, choices, and worldlines:

- `GMAgenda`
- `GMEventProposal`
- `EventResolutionRule`
- `PlayerActorProfile`
- `PlayerChoiceRecord`

Plot, route, daily narrative, groups, information flow:

- `StoryHook`
- `PlotThread`
- `RouteAffinity`
- `EventTriggerCondition`
- `SceneBeatDraft`
- `DailyEpisodeDraft`
- `GroupInteractionContext`
- `RelationshipEventSuggestion`
- `OrganizationConflictEvent`
- `RumorRecord`
- `RumorPropagation`

Knowledge/player/guardrails:

- `CharacterKnowledgeFact`
- `SecretRecord`
- `CharacterEmotionalState`
- `RelationshipRepairRecord`
- `PlayerJournalEntry`
- `InWorldNotification`
- `PlayerInterventionRecord`
- `GMStyleReview`
- `NarrativeContinuityReview`

Beta readiness:

- `RouteMilestone`
- `EndingCandidate`
- `LongRunEvalRun`
- `AuthoringTemplate`
- `AuthoringImportJob`
- `LivingWorldReleaseProfile`
- `BetaChecklistRun`
- `BetaChecklistItem`

Architectural implication: the schema now expresses most V2 concepts directly.
Future work should avoid adding another parallel representation of the same
concepts. New framework work should either reuse these tables or introduce a
clear compatibility/migration strategy.

## V2 Living-World Capabilities

### World Model And Characters

Implemented:

- Structured world bible.
- Continuity metadata.
- Expanded agent roster fields for galgame character roles.
- Structured character profile sheets.
- First-class relationship graph.

The agent model preserves compatibility with `Agent.config`, but queryable V2
fields exist for important behavior.

### Autonomous Life

Implemented:

- Organizations and organization memberships.
- Faction progress tracks.
- Location graph over scenes.
- Agent presence state.
- Daily-life scheduler previews/generation.
- Offscreen event queue.
- Event importance ranking.
- Deterministic GM world engine baseline.

The runtime can resolve offscreen events and produce world events and diagnostics.

### GM, Choices, And Worldlines

Implemented:

- GM agendas and event proposals.
- Deterministic resolution rules.
- Player actor profiles.
- Player choice records and consequence previews/apply flows.
- Branchable worldlines.
- Snapshot/event fork metadata with unsupported historical forks rejected rather
  than silently misrepresented.
- Worldline-scoped runtime runs, conversation sessions, memory jobs/retrieval,
  profile snapshots, replay/snapshot APIs, and event filtering.
- Timeline comparison data.

Important invariant: omitted `worldline_id` resolves to the world's primary
worldline for backward compatibility.

### Plot, Route, Rumor, And Daily Narrative

Implemented:

- Promise/foreshadowing hooks.
- Plot threads.
- Route affinity.
- Trigger conditions with dry-run reasons.
- Scene beat drafts.
- Daily episode drafts.
- Group interaction contexts.
- Relationship event suggestions.
- Organization conflict events.
- Rumor records and propagation.

The condition evaluator can inspect time, world clock, locations/presence,
relationships, faction tracks, hook/plot state, route state, choices, knowledge,
and secrets.

### Knowledge, Player Surfaces, And Guardrails

Implemented:

- Character knowledge state.
- Secrets and reveal flows.
- Emotional state.
- Relationship decay/repair records.
- Living-world dashboard data.
- Player journal.
- In-world notifications.
- Player interventions.
- GM style diagnostics.
- Narrative continuity reviews.
- Prompt context selector and publication leak gate.

Important safety boundary: prompts and review context use selected, bounded,
agent-visible living-world context. Hidden secrets should not enter runtime or
conversation prompts unless the acting character is a holder or the secret is
revealed.

### Beta Release Readiness

Implemented:

- Route milestones.
- Ending candidates and deterministic dry-runs.
- Long-run eval runs with blockers, metrics, and recommendations.
- Authoring templates and import preview/apply jobs.
- Release profile records.
- Beta checklist runs/items and structured evidence refs.
- Server-side release gate hardening.

Important product boundary: `ready` has strict evidence gates; `released` remains
blocked behind a future launch gate.

## Major Runtime Flows

### Runtime Iteration

One daemon iteration:

1. Reads runtime desired state.
2. Records heartbeat and diagnostics.
3. Advances running world clocks.
4. Runs due agents using provider profiles and prompt context.
5. Advances running conversation sessions.
6. Runs living-world autonomy/GM work.
7. Processes due memory write jobs.
8. Records iteration diagnostics and commits.

### Agent Run

An agent run:

1. Resolves worldline.
2. Refreshes observations from events.
3. Loads persona, observations, and memory context.
4. Uses `LivingWorldContextSelector` for visible knowledge/secrets/emotion/
   relationship context.
5. Adds world bible/hook/plot/route context pack.
6. Builds provider prompt.
7. Calls configured provider profile where appropriate.
8. Records `AgentRuntimeRun`, `world_events`, memory writes, diagnostics, and
   optional narrative artifacts.

### Conversation

Conversation sessions support manual chains and running auto dialogue. They are
worldline-scoped and can carry group interaction metadata, participant roles,
organization refs, scene constraints, writer config, and memory config.

Manual and runtime turns preserve worldline scope when invoking agent runs and
memory behavior.

### Narrative Publication

Narrative artifacts can be drafts or published reader-visible records. Publication
passes through a gate that checks review status, hidden secret leaks, publication
visibility, warning override decisions, and worldline evidence where release
gates need it. Reader surfaces filter by visibility and support source/search/
status/order filters.

### Worldline Forking

Worldlines track parent lineage, fork metadata, creator actor, status, and copied
queryable state needed for branch operation. Runtime, memory, conversation,
snapshot, event, and release/beta evidence surfaces now carry worldline scope.

### Release Gate

Release readiness requires evidence from the target worldline:

- latest checklist,
- zero blockers,
- latest acceptable long-run eval,
- required snapshot/worldline/publication/review/checklist/eval refs,
- published reader-visible narrative output,
- explicit warning decisions.

Public `released` status remains blocked until a future launch gate is designed.

## Web App

Primary routes:

- `/login`
- `/worlds`
- `/worlds/{worldId}`
- `/worlds/{worldId}/agents`
- `/worlds/{worldId}/agents/{agentId}`
- `/worlds/{worldId}/conversations`
- `/worlds/{worldId}/conversations/{conversationId}`
- `/worlds/{worldId}/narrative`
- `/worlds/{worldId}/reader`
- `/worlds/{worldId}/reader/{artifactId}`
- `/admin/presets`
- `/admin/providers`
- `/admin/runtime`
- `/admin/memory-backends`

Web architecture:

- Next app routes load server data through `web/lib/worlds/server.ts`.
- Browser actions go through `web/lib/worlds/client.ts`.
- Same-origin API routes proxy to the backend using configured API base URL.
- `web/lib/realtime.ts` handles EventSource and live conversation WebSocket
  helpers.
- Feature components are grouped under `web/features`.

Important current Web considerations:

- `world-overview.tsx` is a dense operational surface with many V2 panels.
- `narrative-reader.tsx` now filters streamed SSE artifacts by the active reader
  filters before merging them into visible state.
- Playwright e2e uses a mock backend with mutable process memory and is configured
  for a single worker. Future e2e files should preserve isolation deliberately.
- `web/next-env.d.ts` can churn after build/e2e; the project has
  `npm run check:next-env` to catch and restore it.

## Tests And Verification

Backend tests:

- Auth/API authorization.
- World API and integration behavior.
- Conversations.
- Runtime daemon.
- Realtime.
- Event store, replay, snapshots.
- Memory backend and Mem0/fake isolation contracts.
- Narrative writer.
- Calendar, clock, schema metadata, Alembic.
- Provider, plugin, observability.

Web tests:

- Component tests for admin, agents, conversations, dashboard, narrative,
  world overview, reader.
- Client route mapping tests.
- Playwright e2e for auth, workspace, conversations, reader filters, publication
  blockers, release gate blockers, and read-only member views.

Recommended full gate:

```sh
cd backend && uv run ruff check .
cd backend && uv run mypy .
cd backend && uv run pytest
cd web && npm run lint
cd web && npm run typecheck
cd web && npm run test
cd web && npm run build
cd web && npm run check:next-env
cd web && npm run test:e2e
docker compose -f infra/compose.yaml config
git diff --check
```

## Operations

Current operator docs cover:

- runtime recovery,
- backup/restore,
- deployment profile,
- runtime supervision,
- diagnostic retention,
- memory queue readiness,
- performance budget,
- sandbox options,
- external tool policy,
- scale readiness,
- living-world release profile.

The supported posture is local/single-host oriented. Production multi-tenant SaaS,
public marketplace plugins, unrestricted sandbox execution, and public launch
operations are out of scope unless a future roadmap promotes them explicitly.

## Known Constraints And Design Pressure

### Large API And Model Files

`backend/services/api/worlds.py` and `backend/packages/worlds/models.py` carry a
large portion of V2. They are test-covered, but they are becoming framework
pressure points. New framework work should consider a planned decomposition by
subdomain:

- world core,
- autonomy/GM,
- worldlines/player choices,
- plot/route/rumor,
- knowledge/secrets/guardrails,
- beta/release/authoring.

The decomposition should preserve existing routes or provide compatibility
wrappers.

### Deterministic Baseline Versus Generated Narrative

The current living-world logic is mostly deterministic. This is good for
acceptance, tests, and replay compatibility. It does not yet prove high-quality
AI-authored galgame prose. A future design needs to decide where provider-backed
generation belongs:

- GM planning,
- scene beat expansion,
- daily episode prose,
- character dialogue,
- continuity/style review,
- authoring import normalization.

Any provider-backed expansion should keep deterministic dry-runs and evidence
available.

### Release Gate Is Not Launch Gate

Release readiness now has strong server-side evidence checks. Public launch still
needs separate decisions for:

- content moderation,
- backup retention and restore drills,
- player permission model,
- worldline policy,
- incident response,
- provider cost/rate limiting,
- moderation review,
- production observability.

### Worldline Scope Is A Core Contract

Worldline scope now appears across runtime, memory, events, snapshots,
conversations, player choices, release evidence, and beta checklists. Future
features should treat `worldline_id` as a first-class argument, not as metadata
to be added later.

### Prompt/Knowledge Safety Is A Core Contract

The selector/review/publish gate is the current defense against hidden knowledge
leaks. Future prompt builders should consume context packs/selectors rather than
re-reading raw knowledge, secret, or relationship tables.

### E2E Mock State Is Serial

The Playwright mock backend is useful and broad, but it stores mutable state in a
single process. New e2e tests should either keep serial execution, add explicit
reset/seed support, or isolate state per worker.

## Recommended Next Framework Work

The next update should probably not be another roadmap phase. The system already
has the V2 feature breadth. The next useful layer is framework consolidation:
make the current behavior easier to reason about, extend, and verify.

Recommended sequence:

1. Extract living-world service boundaries.
   - Move API orchestration out of `worlds.py` into subdomain service modules
     while preserving route contracts.
   - Keep DTOs stable and add compatibility tests before refactoring behavior.

2. Define a command/event/evidence kernel.
   - Standardize how player interventions, GM proposals, offscreen events,
     relationship repairs, authoring imports, publications, evals, and release
     gates produce events and evidence refs.
   - Make actor, causation, correlation, worldline, and continuity metadata
     mandatory for new event-producing paths.

3. Promote the condition evaluator into a stable rule framework.
   - Use one condition language for triggers, GM rules, ending dry-runs, beta
     checklist evidence, and authoring validation.
   - Keep dry-run reasons human-readable and testable.

4. Modularize prompt/context assembly.
   - Keep `LivingWorldContextSelector` as the visibility boundary.
   - Split prompt consumers into agent, conversation, GM, narrative preview,
     publication review, and eval contexts.
   - Add explicit tests for every context type.

5. Formalize worldline-aware repository helpers.
   - Reduce repeated same-world/worldline validation in routers.
   - Make cross-world and cross-worldline failures uniform.

6. Improve Web surface composition.
   - Break the very dense world overview into subpanels with typed data loaders.
   - Keep existing routes, but create smaller internal components and tests.

7. Add beta sample-world fixtures.
   - Turn the beta checklist from infrastructure into repeatable sample-world
     evidence.
   - Use fixed data seeds to compare multi-day simulation quality over time.

8. Decide provider-backed generation boundaries.
   - Add provider calls only where there is a deterministic preview, review, and
     rollback path.
   - Keep GM macro decisions and release gates explainable even if prose
     generation becomes provider-backed.

## Architecture Questions For The Next Discussion

1. Should `worlds.py` be decomposed first, before new product features?
2. Should the next framework define a formal command bus, or keep direct service
   method calls with stricter conventions?
3. What is the canonical event/evidence schema for all future living-world state
   transitions?
4. Which systems are allowed to call providers, and which must stay deterministic?
5. Should prompt context packs become versioned contracts stored with run/review
   records?
6. How strict should publication gates become for style warnings versus hard
   leak/canon errors?
7. What is the minimum launch gate beyond current `ready` evidence?
8. How should e2e mock state be reset or isolated before adding more browser
   scenarios?
9. Should authoring imports become a separate package, or remain under
   `noveland.worlds.beta` until production launch design starts?
10. What sample world should serve as the canonical regression fixture for living
    world quality?

## Practical Entry Points For Review

Backend:

- `backend/services/api/src/noveland/services/api/worlds.py`
- `backend/services/runtime/src/noveland/services/runtime/daemon.py`
- `backend/services/runtime/src/noveland/services/runtime/agent_loop.py`
- `backend/packages/worlds/src/noveland/worlds/models.py`
- `backend/packages/worlds/src/noveland/worlds/living_context.py`
- `backend/packages/worlds/src/noveland/worlds/conditions.py`
- `backend/packages/worlds/src/noveland/worlds/gm.py`
- `backend/packages/worlds/src/noveland/worlds/beta.py`
- `backend/packages/memory/src/noveland/memory/service.py`
- `backend/packages/narrative/src/noveland/narrative/services.py`

Web:

- `web/features/worlds/world-overview.tsx`
- `web/features/worlds/narrative-reader.tsx`
- `web/features/agents/agent-builder.tsx`
- `web/features/conversations/conversation-detail.tsx`
- `web/lib/worlds/types.ts`
- `web/lib/worlds/client.ts`
- `web/lib/worlds/server.ts`
- `web/tests/e2e/start-with-mock-auth.mjs`
- `web/tests/e2e/auth.spec.ts`

Docs:

- `docs/agent/harness/roadmap-v2-living-world.md`
- `docs/agent/harness/debug-journal.md`
- `docs/agent/harness/change-journal.md`
- `docs/agent/operations/living-world-release-profile.md`

## Bottom Line

The project has broad V2 feature coverage and strong local acceptance scaffolding.
The next architectural win is not adding more concepts. It is consolidating the
current living-world concepts into clearer service boundaries, a stricter
event/evidence framework, versioned context contracts, and repeatable beta sample
world evaluation. That will make later provider-backed generation and public
launch design safer to implement.
