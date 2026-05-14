# Phase Plan — v0.4 Operator/Admin UX

## Version Goal

Admin/operator users can inspect, configure, validate, and troubleshoot providers, media assets, visual assets, speech assets, invocation ledger records, and multimodal diagnostics through controlled admin UI without exposing secrets, storage paths, raw prompt data, or hidden/developer-only records.

## Version Non-goals

- Public reader/player UI.
- Public media delivery.
- New provider capabilities or adapters.
- Runtime daemon automation or streaming.
- Core schema changes unless a later phase proposal explicitly approves a small field addition.
- Exposure of resolved secrets, storage_uri, filesystem paths, raw prompts, or raw outputs.

## Phase Discipline

- Implement phases strictly in order unless OpenSpec is updated first.
- Each phase starts from clean local `main`.
- Each phase is independently testable, mergeable, and reversible.
- Do not continue to the next phase after a failing gate or unresolved architecture decision.
- Do not push unless the user explicitly requests it.

## Phase 1 — Admin UX Foundation

### Goal

Unify admin layout, route guards, shared states, API client conventions, and table/detail/action patterns.

### Scope

- Admin shell conventions
- Shared loading, error, and empty states
- Admin route guard pattern
- Admin API client conventions
- Shared table, detail, and action patterns

### Non-goals

- Concrete provider/media/speech/visual business UI
- Backend business logic changes

### Reused Systems

- Next.js app routes
- existing auth proxy/client patterns
- workspace shell components

### Acceptance Criteria

- Admin pages share consistent loading/error/empty states
- Admin route guard pattern is documented and tested
- No backend behavior changes are required

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- Web lint/typecheck/tests for touched components
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 2 — Provider Admin Console

### Goal

Manage provider integrations, adapter_kind, capabilities, health checks, and smoke tests.

### Scope

- Provider list/detail
- Capability view
- Health-check history
- Smoke-test action
- auth_ref status display
- Restricted visibility handling

### Non-goals

- Resolved secret display
- New provider adapters
- Provider execution kernel changes

### Reused Systems

- ProviderRegistryService
- ProviderHealthService
- ProviderExecutionService
- providers API

### Acceptance Criteria

- World admins can inspect allowed providers
- Smoke-test actions show safe status
- Secrets are never displayed

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- Provider admin UI tests
- API proxy tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 3 — Media Asset Admin Console

### Goal

Manage media assets, objects, jobs, and references with upload, download, verification, and status inspection.

### Scope

- Asset list/detail
- Object list/download
- Job list/status
- Reference browser
- Upload flow
- Visibility/status filters

### Non-goals

- Public reader media delivery
- New storage backend

### Reused Systems

- MediaService
- MediaJobService
- MediaCatalogService
- media API

### Acceptance Criteria

- Admins can inspect media lifecycle
- Downloads use safe API paths
- No storage_uri/path leak appears in UI payloads

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- Media admin UI/API proxy tests
- leak fixture check
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 4 — Visual Asset Admin Console

### Goal

Manage character sprites, expression variants, backgrounds, and scene compose preview.

### Scope

- Sprite sets
- Sprite variants
- Scene backgrounds
- Resolve sprite preview
- Resolve background preview
- Compose scene preview

### Non-goals

- Automatic sprite generation
- Background generation orchestration
- Worldline-null visual defaults

### Reused Systems

- VisualAssetService
- VisualResolver
- VisualCompositionService
- ImageService

### Acceptance Criteria

- Admins can manage strict-worldline visual bindings
- Resolve previews are deterministic
- Compose preview reuses existing composer

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- Visual admin UI/API proxy tests
- worldline isolation tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 5 — Speech Admin Console

### Goal

Manage voice profiles, agent bindings, style mappings, transcripts, and TTS/STT test actions.

### Scope

- Voice profile list/detail
- Agent voice binding editor
- Style mapping editor
- Transcript browser
- TTS/STT test action

### Non-goals

- Realtime voice
- Streaming
- Local voice server deployment

### Reused Systems

- SpeechService
- VoiceProfileService
- SpeechTranscriptService
- SpeechStyleMappingService

### Acceptance Criteria

- Admins can test speech flows safely
- Audio assets remain media records
- Transcripts do not imply memory writes

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- Speech admin UI/API proxy tests
- no secret/audio path leak checks
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 6 — Invocation Ledger Browser

### Goal

Allow admins to inspect model invocation records, prompt snapshots, tags, redaction, visibility, and retention state.

### Scope

- Invocation list/detail
- Prompt snapshot detail with permission guard
- Tag management
- Redaction action
- Visibility/retention display

### Non-goals

- Reader/member raw prompt exposure
- External tracing exporter

### Reused Systems

- InvocationLedgerService
- PromptSnapshotService
- invocations API

### Acceptance Criteria

- Admins can inspect ledger evidence
- Raw evidence is gated
- Redaction state is visible and actionable

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- Invocation browser UI/API proxy tests
- member route exposure tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 7 — Multimodal Diagnostics Dashboard

### Goal

Visualize Phase 12 multimodal diagnostic results.

### Scope

- Diagnostics overview
- Missing asset checks
- Secret/storage/prompt leak checks
- Provider health summary
- Sample fixture status
- Cost/latency summaries

### Non-goals

- Diagnostics backend rule changes
- Public launch gate

### Reused Systems

- MultimodalEvalService
- long_run_eval_runs
- provider/media/invocation diagnostics

### Acceptance Criteria

- Admins can review blockers and warnings
- Sample fixture status is visible
- No hidden evidence is exposed to reader/member users

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- Diagnostics dashboard UI/API proxy tests
- multimodal eval tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.
