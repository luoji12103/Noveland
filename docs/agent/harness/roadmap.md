# Long-Term Roadmap

## Purpose

This document is the long-term planning guide for Noveland.

It is not the active task board. Use `task-board.md` for current work, and use this roadmap to choose future mainlines, preserve product direction, and prevent isolated feature work from drifting outside the project architecture.

## Current Baseline

Noveland currently has a self-hosted modular-monolith baseline with world/auth management, runtime control, provider profiles, event and snapshot storage, replay, calendar rules, agent runs, conversations, narrative writer and reader surfaces, realtime updates, plugin runtime wiring, Mem0 OSS-first long-term memory profiles, async memory write jobs, memory eval/forget/operator flows, and runtime memory ops visibility.

The expected v1 experience is:

- A platform admin can create worlds, configure providers, manage memory backends, manage presets, and operate runtime state.
- World admins can compose agents, scenes, schedules, conversations, persona policy, observations, and narrative outputs.
- Runtime loops can advance clocks, run agents, process conversations, emit events, generate narrative artifacts, and enqueue/process memory jobs.
- Memory behavior stays behind `MemoryService`; runtime and conversation code must not import backend SDKs directly.
- Reader, replay, diagnostics, and admin surfaces are sufficient for local operator use, but production operations, recovery, scaling, and richer authoring workflows remain future work.

## Planning Rules

- Foundations and ADRs remain higher authority than this roadmap.
- Each roadmap phase is a mainline-sized planning unit, not a single commit.
- Debugging, checks, tests, and docs are part of every phase acceptance criteria and must not be promoted into separate roadmap phases.
- Do not add parallel API, runtime, plugin, memory, auth, or storage layers when an existing surface can be extended.
- Public contract changes require backend schema/API updates, web proxy/client updates, mock backend updates, and docs/handoff updates in the same phase.
- Sensitive areas require extra care: `MemoryService`, plugin registry/bindings, event/snapshot semantics, auth/world access, world clock state, migrations, and runtime daemon behavior.

## Phase Acceptance Baseline

Every phase below must satisfy all of these before it is considered complete:

- Phase-specific behavior is implemented and manually reviewable.
- Targeted unit/API/component tests pass for the changed area.
- Relevant backend, web, infra, or E2E regression checks pass based on blast radius.
- New or changed public contracts are reflected in docs, mocks, and handoff notes.
- No unrelated scope expansion, schema churn, or architectural bypass is introduced.

## Long-Term Roadmap

| Phase | Goal | Expected Outcome | Specific Acceptance Signal |
| --- | --- | --- | --- |
| 1. Merge Hygiene Baseline | Keep `main` merge-ready after the current memory/runtime work. | Clean branch state, accurate handoff, and no stale feature-branch instructions. | Handoff states `main`, task board has no stale upcoming mainline, and full merge-gate commands are recorded when run. |
| 2. Runtime Ops Dashboard Hardening | Make runtime status more useful to a platform operator. | Runtime admin shows daemon state, recent failures, memory queue counts, provider health, and actionable controls. | Admin runtime view can explain whether runtime is running, stalled, degraded, or blocked. |
| 3. Memory Queue Reliability v1 | Improve the database-backed memory job queue without adding external workers. | Failed, retryable, delayed, and completed memory jobs are easier to inspect and recover. | Operators can distinguish transient retry from terminal failure and retry only valid jobs. |
| 4. Memory Backfill Planning | Design safe memory backfill for existing events, turns, and agent runs. | Backfill scope, idempotency, attribution, and throttling rules are documented and testable. | Dry-run backfill reports candidates without writing memory jobs. |
| 5. Provider Health Dashboard | Expand provider operations beyond single test calls. | Provider health history, failure classes, and last successful checks are visible. | Platform admin can identify which provider/profile is causing runtime degradation. |
| 6. Provider Secrets Validation | Make secret-ref configuration failures obvious before runtime use. | Missing or malformed secret refs surface through health checks and diagnostics. | Secret values remain hidden while secret refs and validation errors are visible. |
| 7. Runtime Recovery Playbook | Establish repeatable recovery steps for local operators. | Runtime restart, stuck job recovery, provider degradation, and memory failure procedures are documented. | README or ops docs include commands and expected verification output. |
| 8. Event Stream Audit Views | Add operator-facing event stream inspection. | World admins can review filtered event history without direct database access. | Event filters support type, time range, actor, and source area. |
| 9. Snapshot Integrity Checks | Validate snapshots against event replay expectations. | Snapshot metadata exposes integrity status and replay compatibility. | Corrupt or incompatible snapshots are detected before restore use. |
| 10. Replay UI v1 | Make replay state more usable from the web workspace. | World admins can inspect reconstructed state, snapshot source, and replay boundaries. | Replay panel clearly distinguishes live state from reconstructed state. |
| 11. World Clock Ops | Improve clock operation and visibility. | Clock state, pause/run changes, and drift-sensitive behavior are inspectable. | Clock controls show audit history and current effective tick settings. |
| 12. Schedule Rule Preview | Let admins preview schedule effects before saving rules. | Rule changes can be evaluated against upcoming world time. | Preview shows affected agents/events without persisting changes. |
| 13. Calendar Conflict Detection | Detect conflicting calendar entries and schedule rules. | World admins receive actionable conflict warnings. | Conflicts identify agent, time range, source rule, and recommended resolution area. |
| 14. Agent Run Inspector | Add detailed run-level runtime inspection. | Agent runs expose prompt inputs, provider profile, memory context summary, outputs, and diagnostics. | Sensitive values are redacted while enough context remains for debugging. |
| 15. Persona Policy Controls | Strengthen persona policy authoring and review. | World admins can edit, compare, and validate persona constraints. | Invalid or contradictory persona policy is rejected before runtime use. |
| 16. Observation Pipeline v2 | Improve filtered observation quality and traceability. | Observations include source attribution, confidence, review status, and runtime use visibility. | Runtime prompts can cite which observations were used. |
| 17. Conversation Diagnostics v2 | Make conversation failures easier to understand. | Conversation detail surfaces retry, skip, provider, memory, and stop-condition diagnostics. | A failed conversation session includes a concise operator-facing explanation. |
| 18. Conversation Speaker Policy | Move beyond deterministic round-robin where appropriate. | Configurable speaker selection supports deterministic and policy-guided modes. | Existing round-robin behavior remains the default and fully tested. |
| 19. Conversation Guardrails v2 | Add richer conversation safety and quality constraints. | Sessions can enforce turn budgets, repetition controls, participant constraints, and failure thresholds. | Guardrail-triggered stops are explicit in terminal reasons and diagnostics. |
| 20. Conversation Memory Controls | Improve memory context selection for conversation sessions. | Session-level memory settings are understandable, testable, and visible during runtime. | Conversation detail shows memory profile, retrieval summary, and write behavior. |
| 21. Narrative Writer Prompt Controls | Give admins safer control over writer behavior. | Writer configuration supports style, length, source constraints, and prompt previews. | Writer output is traceable to source conversation or world event inputs. |
| 22. Narrative Publishing Workflow | Separate drafts, published artifacts, and reader-visible content. | Authors can review generated narrative before publishing it to readers. | Reader surfaces only show published artifacts unless the user has edit access. |
| 23. Narrative Reader Search | Add reader search and filtering. | Members can find narrative artifacts by title, source, tags, time, or content. | Search results preserve access control and stable artifact links. |
| 24. Narrative Timeline View | Present narrative artifacts chronologically. | Reader and admin views can navigate story progression by world time and publication time. | Timeline distinguishes generated, edited, and published dates. |
| 25. Narrative Realtime Updates | Make narrative changes visible without full reloads. | Reader and workspace surfaces receive relevant narrative updates through existing realtime channels. | SSE/WebSocket updates reuse current proxy infrastructure. |
| 26. World Composition Validation | Harden composition import/export. | Invalid presets, missing plugin bindings, and incompatible settings are caught early. | Import dry-run reports all blocking and warning-level issues. |
| 27. Preset Versioning | Track preset revisions without breaking existing agents. | Agents retain materialized provenance while admins can evolve presets. | Preset edits do not silently mutate existing agents. |
| 28. Preset Update Strategy | Provide explicit workflows for applying preset changes. | Admins can compare and selectively apply preset updates to agents or worlds. | Update preview shows affected fields before persistence. |
| 29. Plugin Binding Persistence | Broaden durable plugin binding configuration. | Plugin bindings are explicit, inspectable, and tied to supported runtime extension points. | Runtime never falls back to implicit plugin behavior when a binding is required. |
| 30. Plugin Contract Test Harness | Make built-in plugin contracts easier to verify. | Plugin categories have repeatable contract tests and fixtures. | New built-in plugins cannot merge without category contract coverage. |
| 31. Plugin Config UI Schema | Generate safer plugin configuration forms from schemas. | Admin UI can render supported plugin config fields consistently. | Invalid config is caught in web and backend validation. |
| 32. Plugin Runtime Diagnostics | Improve visibility into plugin execution and config failures. | Diagnostics identify plugin id, category, binding, config issue, and runtime impact. | Plugin diagnostics avoid exposing secret values. |
| 33. Storage Backend Baseline | Define durable storage behavior for payloads that should not remain inline forever. | Snapshot payloads, artifacts, and large diagnostics have a planned storage abstraction. | Local filesystem/object-storage choice is documented before implementation. |
| 34. Backup And Restore v1 | Provide local operator backup and restore workflow. | Database, config, and storage payload backup steps are documented and testable. | Restore can be validated in a fresh local environment. |
| 35. Migration Safety Gate | Reduce migration risk as schema grows. | Alembic history, downgrade policy, and data migration checks are clearer. | Migration checks catch missing model metadata and unsafe assumptions. |
| 36. Auth Hardening | Improve local-auth production readiness. | Session lifetime, cookie policy, password handling, and admin bootstrap are hardened. | Security-sensitive defaults are documented and tested. |
| 37. Agent Runtime Identity | Clarify non-human runtime identity and permissions. | Runtime writes can be attributed separately from human users. | Events, diagnostics, and memory jobs identify runtime actor context consistently. |
| 38. World Access Review | Make world membership and role review easier. | Admins can inspect access across worlds and remove stale members safely. | Access changes are audited and do not bypass world-admin rules. |
| 39. Diagnostic Retention Policy | Prevent diagnostics from growing without policy. | Retention, pruning, redaction, and export expectations are defined. | Operators can prune old diagnostics without losing active incident context. |
| 40. Metrics Export Baseline | Add machine-readable operational metrics. | Runtime, provider, memory, and API health metrics can be scraped or exported locally. | Metrics do not expose secrets or private narrative content. |
| 41. Deployment Profile v1 | Formalize local and single-host deployment expectations. | Compose, env, ports, migrations, and startup order are documented as a supported profile. | A new operator can bring up the stack from README steps. |
| 42. Runtime Process Supervision | Improve daemon lifecycle management. | Runtime process start/stop/restart, crash visibility, and liveness checks are reliable. | Operator can tell whether API and runtime daemon are independently healthy. |
| 43. Performance Budget v1 | Establish performance expectations for key workflows. | API, runtime loop, memory retrieval, reader, and admin pages have baseline budgets. | Regressions are detectable with repeatable local checks. |
| 44. Memory Evaluation v2 | Make memory eval output more actionable. | Evals cover retrieval quality, profile health, attribution, privacy isolation, and write behavior. | Eval results recommend concrete operator actions. |
| 45. Memory Backfill Execution | Implement the planned memory backfill safely. | Existing worlds can enqueue historical memory writes with throttling and attribution. | Backfill is idempotent and can resume after interruption. |
| 46. Distributed Queue Readiness | Prepare for external queue workers without adopting them prematurely. | Current job contracts can map cleanly to future Celery/Temporal/Redis-style workers. | V1 database queue remains supported and documented. |
| 47. Sandbox Options Design | Evaluate runtime/tool sandbox choices. | Security, cost, local deployment, and plugin constraints are documented. | No sandbox implementation starts without a selected design. |
| 48. External Tool Policy v1 | Define how agents may use external tools. | Tool permissions, audit, failure handling, and data exposure rules are explicit. | Runtime/tool integration has clear allow/deny policy inputs. |
| 49. Scale Readiness | Identify bottlenecks before multi-world or multi-user growth. | Database indexes, realtime fanout, memory queue throughput, and provider limits are reviewed. | Scale plan lists concrete blockers and non-blockers for v2. |
| 50. v2 Product Expansion Review | Reassess scope after v1 operations are stable. | Team can choose the next product direction from evidence rather than drift. | Review compares MVP goals, user workflows, operational readiness, and out-of-scope candidates. |

## Suggested Mainline Bundles

- Runtime/Deployment Hardening: phases 1-7, 41-43.
- Replay + Narrative Reader: phases 8-10, 21-25.
- Conversation/Agent Quality: phases 14-20, 44.
- Plugin Persistence + Contract Harness: phases 26-32.
- Backup/Storage/Auth Ops: phases 33-40.

The first selected mainline should be chosen in `task-board.md` only when implementation is ready to begin.

## Maintenance Rules

- Update this file when a completed mainline changes the realistic long-term order.
- Keep entries at roadmap granularity; detailed implementation plans belong in task entries, feature plans, or handoffs.
- When a phase starts, create or update active task-board entries instead of editing the roadmap into an execution checklist.
- When a phase completes, record the implementation in `change-journal.md` and update the handoff with the next candidate phase or mainline.
