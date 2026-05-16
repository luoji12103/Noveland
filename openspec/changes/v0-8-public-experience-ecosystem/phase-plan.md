# Phase Plan — v0.8 Public Experience & Ecosystem

## Version Goal

Expose safe reader/player experiences, worldline navigation, media playback, world packaging, plugin/provider package contracts, moderation workflow, and public launch readiness without weakening the completed Phase 13 and v0.7 production boundaries.

## Baseline

- v0.7 Production Hardening is complete locally and provides the internal readiness baseline.
- Reader narrative publication already exists, but reader-safe media delivery does not.
- Admin/member media object download exists, but it must not be reused as a public delivery contract without a safe DTO and visibility layer.
- Player choice, journal, notification, and intervention records already exist and must be reused.
- Plugin catalog, plugin binding validation, provider registry, provider capabilities, and provider secret governance already exist and must be reused.

## Version Non-Goals

- Bypassing v0.7 production readiness.
- Public CDN or unauthenticated media delivery without explicit approval.
- Provider marketplace or user-managed secret UI.
- Streaming image/audio/runtime updates beyond existing event streams.
- Runtime daemon auto-generation or automatic provider spend.
- Broad route growth in `worlds.py`.
- Exposing hidden media, developer-only data, raw prompts/outputs, storage paths, bytes, base64, or resolved secrets.

## Phase Discipline

- Implement phases strictly in order unless OpenSpec is updated first.
- Each phase starts from clean local `main`.
- Each phase begins with a docs-only planning checkpoint and harness update.
- Each implementation phase is independently testable, mergeable, and reversible.
- Each phase runs targeted tests, the full local gate, OpenSpec validation when relevant, and `git diff --check`.
- Do not continue to the next phase after a failing gate, unresolved migration issue, or unresolved architecture decision.
- Do not push unless the user explicitly requests it.

## Pre-Implementation Review

The v0.8 feasibility review adapts this phase plan to the current repository and records open architecture decisions for Phase 1. It is not a product implementation phase.

## Phase 1 — Reader Media Delivery

### Goal

Provide reader-safe media descriptors and delivery for visible image/audio assets without leaking storage internals.

### Scope

- Public/read-only media contract inventory.
- Reader-safe media descriptor DTOs.
- Delivery policy for application streaming and/or opaque short-lived tokens.
- Visibility enforcement across media assets, objects, references, narrative publications, and presentation records.
- Backend/API-first implementation; no player UI beyond what is required to test delivery.

### Non-Goals

- Public CDN integration unless explicitly accepted in the phase checkpoint.
- Admin-only media browsing.
- Provider calls or media generation.
- Exposing `MediaObjectRecord.storage_uri`.

### Reused Systems

- `MediaService`, `media_assets`, `media_objects`, `media_references`
- narrative publication visibility
- conversation turn presentations
- authorization dependencies
- v0.7 security regression patterns

### Acceptance Criteria

- Authorized readers can access only visible media needed by published reader surfaces.
- Hidden and developer-only media is blocked.
- Responses do not expose storage paths, base64, bytes, raw prompts/outputs, or secrets.
- Reader-safe descriptors are usable by later playback and galgame UI phases.

### Stop Conditions

- Public authentication model is unclear.
- Delivery design requires exposing storage paths or raw object metadata.
- Visibility policy conflicts across media assets, references, and narrative publications.
- Any broad `worlds.py` route growth is required.

## Phase 2 — Conversation Playback UI

### Goal

Render conversation turn playback using safe presentation DTOs, subtitles, images, and audio.

### Scope

- Reader/member-safe playback UI.
- Turn list and active turn playback state.
- Audio playback through Phase 1 delivery.
- Graceful missing-asset states.

### Non-Goals

- Editing presentation state in reader UI.
- Admin prompt/invocation evidence display.
- Streaming playback.

### Reused Systems

- conversation turn presentations
- reader media delivery
- speech assets and media references
- existing conversation reader/server helpers

### Acceptance Criteria

- Playback uses reader-safe media descriptors only.
- Audio and image access honor visibility and worldline scope.
- UI tests and e2e smoke cover safe playback.

## Phase 3 — Player Interaction UI

### Goal

Expose choices, interventions, journal, notifications, and route feedback to players using existing player records.

### Scope

- Choice and intervention affordances.
- Player journal and unread notification surfaces.
- Route feedback that hides spoilers and admin evidence.

### Non-Goals

- New player record framework.
- Admin diagnostics in player UI.
- Direct provider-backed player action execution.

### Reused Systems

- `PlayerChoiceRecord`
- `PlayerJournalEntry`
- `InWorldNotification`
- `PlayerInterventionRecord`
- existing world/player guardrail services

### Acceptance Criteria

- Player actions create or display structured existing records.
- Journal and route feedback respect player knowledge visibility.
- No admin diagnostics, storage paths, prompts, or hidden future route data leak.

## Phase 4 — Worldline Browser

### Goal

Support authorized branch viewing and read-only comparison of worldlines.

### Scope

- Worldline list/tree view.
- Read-only branch summaries.
- Comparison of timeline, events, narrative publications, and media/presentation presence.

### Non-Goals

- Unsafe destructive rollback.
- Switch execution without explicit review.
- Merging worldlines.

### Reused Systems

- worldline records and services
- event snapshots/replay
- strict-worldline visual and presentation records
- v0.7 ACL regression matrix

### Acceptance Criteria

- Authorized users can browse worldline state without mutation.
- Comparison keeps branch-specific media and presentation state isolated.
- Reader/player users see only allowed branches and safe summaries.

## Phase 5 — Scene View / Galgame View

### Goal

Provide a basic galgame reading surface with background, sprites, dialogue, audio, and restrained transitions.

### Scope

- Scene background and sprite layout using presentation data.
- Dialogue/subtitle display.
- Audio controls using reader media delivery.
- Responsive desktop/mobile view.

### Non-Goals

- Full game engine.
- Custom rendering pipeline.
- Streaming or real-time animation engine.

### Reused Systems

- Phase 9 visual resolver outputs
- conversation turn presentations
- reader media delivery
- speech/media assets

### Acceptance Criteria

- Scene view renders safe presentation records.
- Missing assets have deterministic fallback states.
- UI is accessible, responsive, and does not expose admin evidence.

## Phase 6 — Player Privacy & Data Controls

### Goal

Support player data export and delete-request workflows without corrupting shared world history.

### Scope

- Player profile visibility controls.
- Export of allowed player-owned records.
- Deletion request/review flow.
- Shared-world safeguards.

### Non-Goals

- Immediate deletion of shared canonical world history.
- Legal compliance automation beyond local product controls.
- Secret/prompt/export of internal diagnostics.

### Reused Systems

- auth/session/user records
- world memberships
- player records
- conversation and narrative reader records

### Acceptance Criteria

- Players can request/export allowed data.
- Deletion is reviewable and protects shared records.
- Exports exclude storage paths, secrets, raw prompts, and hidden admin evidence.

## Phase 7 — World Packaging

### Goal

Define safe world bundle and media bundle manifests with preview/apply import discipline.

### Scope

- Export manifest schema.
- Media manifest schema.
- Import preview and compatibility validation.
- Import apply after explicit review.

### Non-Goals

- Including secrets or internal storage URIs.
- Bulk historical backfill.
- Marketplace distribution.

### Reused Systems

- media assets/objects/references
- world records and scenes
- authoring preview/apply discipline
- Phase 13 architecture inventories

### Acceptance Criteria

- Export manifests are portable and exclude secrets/internal paths.
- Import validates compatibility before mutation.
- Media references remain portable and worldline-aware.

## Phase 8 — Plugin/Provider Package Contract

### Goal

Define plugin/provider package metadata, capability schema, config export, and safety review.

### Scope

- Package metadata schema.
- Capability declaration.
- Safe config export without secrets.
- Safety review checklist/API if needed.

### Non-Goals

- Provider marketplace.
- Plugins resolving secrets directly.
- Runtime installation of untrusted code.

### Reused Systems

- plugin catalog and binding validation
- provider registry/capabilities
- `ProviderSecretResolver`
- v0.7 provider governance checks

### Acceptance Criteria

- Package metadata declares capabilities and boundaries.
- Config export excludes secrets and resolved auth.
- Safety review blocks media, prompt, storage, and provider-boundary violations.

## Phase 9 — Sample World Release Package

### Goal

Package a demonstrable sample world with content, media bundle, and regression fixture linkage.

### Scope

- Sample world content manifest.
- Media bundle manifest.
- Fixture linkage to Phase 13 sample-world regression.
- Rights/visibility documentation.

### Non-Goals

- Production seed framework.
- Unlicensed third-party content.
- Real provider calls during fixture import.

### Reused Systems

- Phase 13 multimodal sample-world fixture
- world packaging
- media manifests
- multimodal diagnostics

### Acceptance Criteria

- Sample package imports deterministically.
- Fixture linkage is documented and testable.
- Content rights and visibility are explicit.

## Phase 10 — Moderation & Incident Workflow

### Goal

Support report review, rollback review, disable actions, and public-surface incident records.

### Scope

- Architecture decision for package/router/schema before implementation.
- Reader/player report records.
- Moderator review and status transitions.
- Safe disable-world/provider action flow.
- Incident evidence refs without raw evidence exposure.
- Dedicated `backend/packages/moderation/` package and `moderation.py` router for persisted workflow records.

### Non-Goals

- Automated public moderation without human review.
- Public exposure of internal incident evidence.
- Replacing v0.7 incident diagnostics.

### Reused Systems

- v0.7 incident diagnostics
- provider governance/disable state
- worldline snapshots/replay
- observability evidence refs

### Acceptance Criteria

- Reports become reviewable records.
- Moderator actions are audited and ACL-protected.
- Evidence is safe, redacted, and linked by reference only.

### Stop Conditions

- Schema/router ownership is unclear.
- Disable/rollback semantics conflict with worldline isolation.

## Phase 11 — Public Launch Gate

### Goal

Define public launch readiness separate from, and dependent on, v0.7 internal production readiness.

### Scope

- Public launch checklist.
- Security/privacy/moderation/sample-world signoff.
- Evidence aggregation from prior v0.8 phases.
- Blocker/warning output.
- Platform-admin-only public readiness endpoint under the existing observability boundary.

### Non-Goals

- Skipping v0.7 production readiness.
- Automatic public launch on passing tests.
- Duplicate release/readiness framework.

### Reused Systems

- `ProductionReadinessGateService`
- `BetaChecklistRun`
- `LongRunEvalRun`
- multimodal/narrative diagnostics
- moderation evidence
- sample-world release package
- reader media, conversation presentation, player privacy, and package contract evidence

### Acceptance Criteria

- Launch gate aggregates production, privacy, moderation, media, and sample-world evidence.
- Failures produce actionable blockers.
- Public signoff is explicit and audit-friendly.
