# Phase Plan — v0.7 Production Hardening

## Version Goal

Noveland should support stable long-running local/single-host production-like operation with stronger permissions, secret/provider governance, cost/rate controls, backup/integrity checks, observability, and repeatable readiness evidence.

## Version Non-goals

- Large new gameplay features
- Player-facing public launch
- Provider marketplace
- Streaming
- Expanded automatic content generation
- Broad new `worlds.py` routes
- Full vault/KMS or encrypted DB secret storage unless separately accepted
- External observability exporter

## Current Baseline

- v0.4 admin UX surfaces exist for providers, media, visual assets, speech, invocation ledger, and multimodal diagnostics.
- v0.5 authoring/import exists as proposal/review/apply-first under a dedicated authoring package/router.
- v0.6 runtime narrative quality is locally complete with API-first admin diagnostics and no Web dashboard expansion.
- Phase 13 architecture freeze remains active: no unsafe world event payloads, no resolved secret exposure, no media path leaks, no raw prompt/output leaks, and no worldline isolation regression.

## Phase Discipline

- Implement phases strictly in order unless OpenSpec is updated first.
- Each phase starts from clean local `main`.
- Each phase begins with a docs-only planning checkpoint.
- Each phase is independently testable, mergeable, and reversible.
- Do not continue to the next phase after a failing gate or unresolved architecture decision.
- Do not push unless the user explicitly requests it.
- Keep implementation API/test/docs-first. Web work must be explicitly accepted before any Web route/component/e2e scope is added.

## Phase 1 — Permission Matrix & ACL Regression Baseline

### Goal

Establish and enforce a concrete owner/admin/member/reader/player permission matrix for the current v0.4-v0.6 route surface.

### Scope

- Route inventory for platform-admin, world-admin, world-member, reader, and player-visible APIs.
- Permission matrix document and service-level expectations.
- Focused regression tests for admin evidence boundaries, reader/member suppression, and player-private data.
- Targeted enforcement fixes only where current behavior conflicts with the matrix.

### Non-goals

- New public launch routes
- New role hierarchy UI
- Large auth schema redesign unless the matrix proves existing models cannot express required behavior

### Reused Systems

- `noveland.auth`
- `world_memberships`
- API authorization dependencies
- existing router tests and Web route guards
- v0.4-v0.6 admin/API surfaces

### Acceptance Criteria

- Permission matrix is documented and reflected in tests.
- Reader/player/member routes cannot access admin evidence, prompt snapshots, resolved provider refs, hidden media, or diagnostics internals.
- Admin-only v0.5/v0.6 routes remain admin-scoped.
- No unsafe data is added to `world_events.payload`.

### Stop Conditions

- A new role/membership schema is required and not covered by the phase plan.
- ACL enforcement would require broad `worlds.py` rewrites.
- Reader/player/member access would expose storage paths, raw prompts/outputs, prompt snapshots, resolved secrets, or admin-only evidence.
- Targeted tests or full local gate fail.

### Expected Validation

- authorization tests
- route permission matrix tests
- regression tests for prompt/storage/secret leakage through lower-privilege routes
- full local gate
- `git diff --check`

## Phase 2 — Secret & Provider Governance

### Goal

Harden provider lifecycle controls: provider disable, safe auth_ref rotation, provider-scoped permissions, safe provider health/smoke status, and audit evidence.

### Scope

- Provider disable semantics at provider registry and execution boundaries.
- Auth reference rotation using opaque `auth_ref` only.
- Safe provider audit evidence using health checks, invocation metadata, or a narrowly accepted audit record if reuse is insufficient.
- Provider-scoped ACL checks for global vs world providers and hidden/developer-only provider records.

### Non-goals

- Provider marketplace
- Resolved secret exposure
- Full vault/KMS/encrypted DB secret storage
- Client-side secret management UI

### Reused Systems

- `ProviderSecretResolver`
- `ProviderRegistryService`
- `ProviderHealthService`
- `ProviderExecutionService`
- `model_invocations`
- `prompt_snapshots`
- provider API tests

### Acceptance Criteria

- Disabled providers cannot execute through image, speech, narrative quality, or provider smoke/test paths.
- Auth rotation changes only the reference, never the resolved secret value.
- Health/smoke/audit metadata records safe status only.
- No resolved secret appears in API responses, logs, prompt snapshots, model invocations, media jobs, diagnostics, or world events.

### Stop Conditions

- Implementation requires storing resolved secrets in DB.
- Secret governance expands into vault/KMS without an accepted design.
- Provider governance requires broad `worlds.py` or `runtime.py` route growth.
- Targeted tests or full local gate fail.

### Expected Validation

- provider governance tests
- secret leak tests
- provider execution disable tests
- OpenSpec validation
- full local gate
- `git diff --check`

## Phase 3 — Cost & Rate Control

### Goal

Add internal cost/rate guardrails for provider execution, media jobs, asset generation proposals, and provider-backed narrative quality generation.

### Scope

- Per-world and per-provider budget policy.
- Emergency stop and quota status.
- Guard checks at provider execution and proposal/apply boundaries.
- Safe blocked-execution evidence and actionable errors.

### Non-goals

- Billing marketplace
- User-facing subscription plans
- Complex multi-tenant quota service
- Automatic provider fallback/load balancing

### Reused Systems

- `model_invocations.estimated_cost`
- `media_jobs`
- provider integrations
- `asset_generation_policies`
- narrative quality provider-backed generation
- multimodal eval cost summaries

### Acceptance Criteria

- Budget checks can block provider execution before an external call.
- Quota status is visible to admins through safe API evidence.
- Emergency stop is auditable and reversible by authorized admins.
- Blocked execution cannot leak prompts, storage paths, resolved secrets, bytes, base64, or raw provider output.

### Stop Conditions

- Existing policy records are insufficient and a new schema is needed without an accepted migration plan.
- Cost controls would silently drop jobs or mutate canonical world state.
- Targeted tests or full local gate fail.

### Expected Validation

- budget policy tests
- provider execution guard tests
- asset generation budget tests
- narrative quality generation block tests
- full local gate
- `git diff --check`

## Phase 4 — Object Storage & Backup v2

### Goal

Define and test object storage integrity, backup/restore drills, checksum audit, and optional S3/GCS-compatible abstraction without exposing storage paths.

### Scope

- Storage backend interface review and minimal adapter boundary.
- Media object checksum/size/existence audit.
- Snapshot object storage integrity checks.
- Backup/restore drill docs and lightweight verification entrypoint.
- Lifecycle policy documentation.

### Non-goals

- Public media CDN delivery
- Destructive restore Web UI
- Cloud provider lock-in
- Migration/backfill of existing local objects unless separately accepted

### Reused Systems

- `noveland.storage`
- `LocalObjectStorage`
- `LocalMediaObjectStorage`
- `MediaService`
- `media_objects`
- event snapshot object storage
- existing backup/restore docs

### Acceptance Criteria

- Storage integrity can be audited without exposing raw paths to reader/member APIs.
- Backup/restore drill is documented and testable locally.
- Object lifecycle policy distinguishes local, backup, and future remote storage.
- Media object and snapshot checksums remain verifiable.

### Stop Conditions

- Object schema changes are required without a migration plan.
- Backup/restore implementation requires destructive runtime behavior.
- API responses would expose filesystem paths or storage URIs outside admin-safe evidence.
- Targeted tests or full local gate fail.

### Expected Validation

- storage integrity tests
- backup docs checks
- media object checksum tests
- docker compose config
- full local gate
- `git diff --check`

## Phase 5 — Deployment Profile

### Goal

Define a repeatable internal production-like deployment profile with health checks, migration procedure, operator docs, and rollback guidance using the existing operational surfaces.

### Scope

- Production-like compose/profile documentation.
- Environment variable inventory and startup validation.
- Health endpoint coverage for core dependencies.
- Migration and rollback procedure.
- Operator checklist for local/single-host deployment.
- Docs/test validation only for the first pass; no new deployment router is expected because the current health and validation commands already exist.

### Non-goals

- Managed cloud platform lock-in
- Kubernetes orchestration
- Autoscaling
- Public launch checklist
- New runtime or deployment endpoint
- New persisted deployment state

### Reused Systems

- `infra/compose.yaml`
- `/health`
- runtime diagnostics
- migration config
- backup/restore docs
- provider health checks

### Acceptance Criteria

- Deployment profile is documented and validated by local commands.
- Health checks cover API, database, NATS, storage readiness, provider governance status, and migration status where available.
- Migration procedure has rollback guidance and backup prerequisites.

### Stop Conditions

- Deployment work requires new external services not already accepted.
- Health checks expose secrets, storage paths, raw prompts, or admin evidence to unauthenticated/public callers.
- Targeted tests or full local gate fail.

### Expected Validation

- compose config
- health tests
- docs checks where available
- full local gate
- `git diff --check`

## Phase 6 — Observability & Incident Diagnostics

### Goal

Expose safe incident diagnostics and retention controls over provider, media, runtime, eval, cost, and narrative quality evidence.

### Scope

- Incident summary APIs or service entrypoints.
- Safe evidence refs for provider failures, media job failures, budget blocks, eval failures, and runtime diagnostics.
- Diagnostic retention dry-run/prune behavior where already supported.
- Failure replay metadata without raw prompt/output or resolved secret exposure.
- Dedicated observability service and, if needed, a bounded platform-admin observability router; avoid broad runtime route growth.

### Non-goals

- External observability exporter
- Real-time incident Web dashboard
- Raw prompt/output replay
- Public/member incident routes

### Reused Systems

- `noveland.observability`
- runtime diagnostics
- provider health checks
- model invocation ledger
- media jobs
- multimodal eval service
- narrative quality dashboard summary
- platform-admin authorization dependencies

### Acceptance Criteria

- Incident reports link to safe evidence refs.
- Retention rules are explicit and tested.
- Failure replay avoids secrets, raw prompts, raw outputs, storage paths, bytes, and base64.
- Admin-only diagnostics stay unavailable to reader/member/player routes.

### Stop Conditions

- Diagnostics require raw prompt/output exposure.
- Implementation duplicates v0.6 narrative quality or multimodal diagnostics instead of reusing them.
- Targeted tests or full local gate fail.

### Expected Validation

- diagnostics tests
- redaction tests
- retention tests
- ACL tests
- full local gate
- `git diff --check`

## Phase 7 — Security Regression Suite

### Goal

Consolidate security regression coverage for secret leaks, prompt/output leaks, storage/path leaks, ACL leaks, and worldline isolation after the earlier hardening phases.

### Scope

- Regression fixtures for forbidden payload content.
- ACL matrix coverage across v0.4-v0.7 API surfaces.
- Worldline isolation checks for media, visual, conversations, authoring proposals, narrative quality, and evals.
- Sample-world regression extension where useful.

### Non-goals

- Full external penetration test program
- SAST/DAST platform rollout
- Public bug bounty process

### Reused Systems

- Phase 13 multimodal fixture
- authorization tests
- provider secret tests
- multimodal diagnostics
- v0.5 authoring regression fixture
- v0.6 narrative quality tests

### Acceptance Criteria

- Regression fixtures catch forbidden leaks.
- ACL matrix is tested across admin/member/reader/player expectations.
- Worldline isolation failures are detected in cross-module workflows.
- No new runtime behavior is required unless a regression test exposes a real bug.

### Stop Conditions

- Regression suite needs broad route refactors before the failing behavior is understood.
- Security fixtures require storing real secrets, raw prompts, raw media bytes, or filesystem paths.
- Targeted tests or full local gate fail.

### Expected Validation

- security regression suite
- route ACL tests
- sample-world regression tests
- full local gate
- `git diff --check`

## Phase 8 — Production Readiness Gate

### Goal

Create an internal readiness gate that aggregates v0.7 hardening evidence without becoming a public launch gate.

### Scope

- Readiness checklist and gate report.
- Read-only production-readiness aggregation under `noveland.observability`.
- Platform-admin-only readiness API under the existing `/observability` router.
- Operator signoff record or safe evidence reference.
- Aggregation of provider governance, budget status, storage integrity, deployment profile, diagnostics, security regression, beta checklist, long-run eval, and multimodal/narrative quality evidence.
- Actionable blocker/recommendation output.

### Non-goals

- Public launch gate
- Marketing/release workflow
- External compliance certification
- Blocking every runtime path

### Reused Systems

- `BetaChecklistRun`
- `LongRunEvalRun`
- `LivingWorldReleaseProfile`
- multimodal evals
- narrative quality dashboard summary
- runtime diagnostics
- provider health checks
- security regression evidence

### Acceptance Criteria

- Gate report aggregates existing evidence without duplicating release/eval systems.
- Operator signoff remains deferred unless an existing safe write path is explicitly accepted.
- Failed checks have actionable blockers and remediation hints.
- Gate output does not expose raw prompts, raw outputs, resolved secrets, storage paths, bytes, base64, or unsafe event payloads.

### Stop Conditions

- Existing eval/release records cannot carry readiness evidence and a new schema is required without a migration plan.
- Gate semantics drift into public launch readiness.
- Targeted tests or full local gate fail.

### Expected Validation

- readiness gate tests
- diagnostics aggregation tests
- ACL and redaction tests
- full local gate
- `git diff --check`
