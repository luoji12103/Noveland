# Phase Plan — v0.8 Public Experience & Ecosystem

## Version Goal

Noveland should expose safe reader/player experiences, worldline navigation, media playback, world packaging, and plugin/provider packaging while preserving production/security boundaries.

## Version Non-goals

- Bypassing production readiness
- Exposing developer_only/hidden media
- Exposing raw invocation prompts/outputs
- Exposing storage_uri/path
- Plugins bypassing provider secret boundary
- Unreviewed public world launch

## Phase Discipline

- Implement phases strictly in order unless OpenSpec is updated first.
- Each phase starts from clean local `main`.
- Each phase is independently testable, mergeable, and reversible.
- Do not continue to the next phase after a failing gate or unresolved architecture decision.
- Do not push unless the user explicitly requests it.

## Phase 1 — Reader Media Delivery

### Goal

Provide reader-visible media delivery without leaking storage_uri or filesystem paths.

### Scope

- Reader media endpoint
- Image/audio delivery
- Visibility enforcement

### Non-goals

- Admin-only media exposure
- Raw storage path delivery

### Reused Systems

- MediaService
- media references
- authorization

### Acceptance Criteria

- Reader can access visible media
- Hidden/developer-only media is blocked
- Storage paths are never exposed

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- reader media API tests
- ACL/leak tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 2 — Conversation Playback UI

### Goal

Render image, sprite, background, voice, subtitles, and turn presentation playback.

### Scope

- Playback UI
- Turn presentation rendering
- Audio playback

### Non-goals

- Editing presentation state in reader UI

### Reused Systems

- conversation presentations
- media delivery
- speech assets

### Acceptance Criteria

- Playback uses safe reader DTOs
- Audio/image assets honor visibility
- No raw prompt or storage path appears

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- playback component tests
- e2e smoke
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 3 — Player Interaction UI

### Goal

Expose choices, interventions, journal, notifications, and route feedback to players.

### Scope

- Choice UI
- Intervention UI
- Player journal
- Notifications

### Non-goals

- Admin diagnostics in player UI

### Reused Systems

- future player choice records
- world events
- notifications

### Acceptance Criteria

- Player actions create structured records
- Journal respects knowledge visibility
- Route feedback hides spoilers

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- player UI tests
- visibility tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 4 — Worldline Browser

### Goal

Support branch viewing, rollback/switch review, and worldline comparison.

### Scope

- Worldline tree/list
- Branch compare
- Switch/review UI

### Non-goals

- Unsafe destructive rollback without confirmation

### Reused Systems

- worldline services
- event snapshots
- comparison APIs

### Acceptance Criteria

- Worldline tree is visible to authorized users
- Comparison does not mutate state
- Branch-specific media/presentation state remains isolated

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- worldline browser tests
- isolation tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 5 — Scene View / Galgame View

### Goal

Provide a basic galgame reading surface with scene background, sprites, dialogue, audio, and basic transitions.

### Scope

- Scene background
- Sprites
- Dialogue
- Audio
- Basic transitions

### Non-goals

- Full game engine
- Streaming rendering

### Reused Systems

- visual resolver outputs
- conversation presentations
- reader media delivery

### Acceptance Criteria

- Scene view renders safe presentation records
- Fallback states are graceful
- No admin evidence leaks

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- scene view component tests
- responsive/e2e tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 6 — Player Privacy & Data Controls

### Goal

Support export/delete requests, player profile visibility, and conversation data controls.

### Scope

- Data export
- Data deletion request
- Privacy controls

### Non-goals

- Deleting shared world history without governance

### Reused Systems

- auth/member records
- conversation records
- world events

### Acceptance Criteria

- Players can request/export allowed data
- Deletion has review and shared-state safeguards
- Private data visibility is enforceable

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- privacy API/UI tests
- ACL tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 7 — World Packaging

### Goal

Define world bundle manifest, media bundle manifest, import, and export.

### Scope

- World export
- World import
- Media manifest

### Non-goals

- Including secrets or internal storage URIs in bundles

### Reused Systems

- media assets/objects
- world records
- OpenSpec/current contracts

### Acceptance Criteria

- Export manifest excludes secrets/internal paths
- Import validates compatibility
- Media references are portable

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- package manifest tests
- secret/path leak tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 8 — Plugin/Provider Package Contract

### Goal

Define adapter packaging, capability schema, safety review, and config export without secrets.

### Scope

- Plugin package metadata
- Provider adapter package contract
- Safety review checklist

### Non-goals

- Provider marketplace
- Plugins resolving secrets directly

### Reused Systems

- plugins package
- provider registry
- ProviderSecretResolver

### Acceptance Criteria

- Package metadata declares capabilities
- Config export excludes secrets
- Safety review blocks boundary violations

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- plugin contract tests
- provider governance tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 9 — Sample World Release Package

### Goal

Package a complete demonstrable sample world with content, media bundle, and regression fixture linkage.

### Scope

- Sample world content
- Media bundle
- Regression fixture linkage

### Non-goals

- Production seed framework
- Unlicensed third-party content

### Reused Systems

- Phase 13 fixture
- world packaging
- media manifests

### Acceptance Criteria

- Sample package imports deterministically
- Regression fixture linkage is documented
- Content rights and visibility are explicit

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- sample package tests
- fixture regression tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 10 — Moderation & Incident Workflow

### Goal

Support reports, rollback, disable world/provider, and incident records.

### Scope

- Reports
- Incident records
- Admin moderation flow

### Non-goals

- Automated public moderation without review

### Reused Systems

- incident diagnostics
- provider disable
- worldline snapshots

### Acceptance Criteria

- Reports become reviewable records
- Moderators can disable risky worlds/providers
- Actions are audited

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- moderation workflow tests
- ACL tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 11 — Public Launch Gate

### Goal

Define public launch readiness checklist separate from internal production readiness.

### Scope

- Public launch checklist
- Security/privacy signoff
- Moderation signoff

### Non-goals

- Skipping v0.7 production readiness
- Automatic launch on passing tests

### Reused Systems

- production readiness gate
- BetaChecklistRun
- LongRunEvalRun
- diagnostics

### Acceptance Criteria

- Launch gate aggregates production, privacy, moderation, and sample-world evidence
- Failures produce blockers
- Signoff is explicit

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- public launch gate tests
- evidence aggregation tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.
