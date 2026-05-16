# Proposal — v1.1 Normal Use / Release Candidate

## Why

After v1.0 private beta proves that a few invited testers can use Noveland with limited intervention, the next milestone is maintainable normal use. v1.1 should focus on operations, recovery, stress, reliability, safety, import/export stability, and user-facing polish needed for a release-candidate evaluation.

## What Changes

- Plan a v1.1 roadmap focused on long-running normal use and release-candidate readiness.
- Add operational runbooks for provider failures, stuck media/jobs, worldline rollback, backup/restore, and secret rotation.
- Require a real backup/restore drill that verifies database, media, checksums, worldlines, conversations, and memory in a new environment.
- Add multi-world/multi-user stress testing and long-session evidence.
- Harden content safety, moderation, public/private visibility, and player-visible output boundaries.
- Stabilize import/export for world packages, media manifests, persona/memory manifests, provider config without secrets, and repeatable sample package import.
- Add provider reliability controls for fallback, degraded mode, health trends, model switching, retry, and requeue.
- Add user-facing polish for key UI flows, loading/error states, mobile basics, audio/scene playback, and onboarding copy.
- Add a release-candidate gate that aggregates operational, recovery, safety, stress, packaging, provider, UX, and readiness evidence.

## Capabilities

### New Capabilities

- `operational-runbooks`: Operator playbooks for provider failure, media/job recovery, worldline rollback, backup/restore, and secret rotation.
- `backup-restore-drill`: Actual backup and restore drill with media, checksum, worldline, conversation, memory, and provider-config-without-secrets verification.
- `multiworld-multiuser-stress`: Multi-world, multi-player, multi-provider, long-session stress evidence and regression reporting.
- `content-safety-moderation-hardening`: Hardening of player-visible content review, report/takedown, role visibility, and character output safety.
- `import-export-stability`: Stable world package import/export with media, persona, memory, and provider config manifests that exclude secrets and unsafe storage paths.
- `provider-reliability-layer`: Provider fallback, degraded mode, health trend, model switching, manual retry, and requeue controls.
- `user-facing-polish`: Focused polish for onboarding, playback, scene, feedback, loading, error, responsive, accessibility, and copy quality.
- `release-candidate-gate`: Normal-use release-candidate report that validates long-term operability, recovery, cost, safety, packaging, provider reliability, and user experience.

### Modified Capabilities

- None. v1.1 introduces planned release-candidate capability contracts that will later extend current specs when implemented and archived.

## Impact

- Future backend work will likely touch operations docs, backup/restore tooling, storage/media integrity, stress/eval diagnostics, moderation, world packaging, provider execution, provider health, quota controls, readiness gates, and observability.
- Future Web work will likely touch operational dashboards, player-facing polish, onboarding, playback/scene UX, and admin readiness reports; implementation must use `impeccable` first.
- Future implementation must not bypass v0.7/v0.8/v1.0 readiness, expose secrets/storage paths, or introduce automatic public launch.
