# Proposal — v1.1 Normal Use / Release Candidate

## Why

After v1.0 private beta proves that a few invited testers can use Noveland with limited intervention, the next milestone is maintainable normal use. v1.1 should focus on operations, recovery, stress, reliability, safety, import/export stability, and user-facing polish needed for a release-candidate evaluation.

## What Changes

- Complete a feasibility review before implementation and keep the existing v1.1 phase order.
- Plan a v1.1 roadmap focused on long-running normal use and release-candidate readiness.
- Add operational runbooks for provider outage, quota exhaustion, stuck media/jobs, migration failure, backup/restore, rollback, worldline restore, secret rotation, invite/session/feedback incidents, and import/export recovery.
- Require a real backup/restore drill against a fresh local/single-host target that verifies database, media, checksums, worldlines, conversations, presentations, memory, provider config without secrets, and OpenSpec/docs provenance.
- Add multi-world/multi-user stress testing and long-session evidence with fake/mocked providers by default.
- Harden content safety, moderation, beta feedback escalation, player privacy, public/private visibility, and player-visible output boundaries.
- Stabilize import/export for world packages, media manifests, persona/memory manifests, provider config without secrets, and repeatable sample package import.
- Add provider reliability controls for manual-first retry/requeue, degraded mode, health trends, and opt-in policy-driven fallback/model switching.
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

## Feasibility Review Result

Recommendation: **B. v1.1 can start after minor OpenSpec adjustments.**

The phase order remains valid. Phase 1 may start after review acceptance. Phases 2-8 must begin with docs-only checkpoints that confirm restore target, stress baseline, moderation ownership, import/export manifest policy, provider reliability policy, Web polish scope, and release-candidate gate evidence ownership.
