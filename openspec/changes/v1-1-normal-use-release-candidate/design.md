# Design — v1.1 Normal Use / Release Candidate

## Context

v1.0 private beta should prove limited tester usage. v1.1 asks a different question: can Noveland be operated, recovered, maintained, and explained for longer-running normal use?

```text
private beta evidence
  -> runbooks
  -> backup/restore drill
  -> stress evidence
  -> safety hardening
  -> import/export stability
  -> provider reliability
  -> user-facing polish
  -> release-candidate gate
```

## Goals / Non-Goals

**Goals:**

- Make operational procedures explicit and repeatable.
- Prove real backup and restore, not just documentation.
- Test multiple worlds, players, providers, and long sessions.
- Harden content safety and moderation for player-visible content.
- Stabilize portable import/export without secrets or storage leaks.
- Add provider reliability behavior without corrupting world state.
- Polish user-facing flows enough for normal-use evaluation.
- Produce a release-candidate report with actionable blockers and evidence.

**Non-Goals:**

- Automatic public launch.
- Marketplace.
- Full enterprise SRE platform.
- Streaming runtime architecture.
- Public unauthenticated media access without a separate accepted change.
- Duplicate readiness, provider, media, packaging, moderation, or eval frameworks.
- Broad route growth in `worlds.py`.

## Decisions

### Operations are evidence-backed

Runbooks are necessary but not sufficient. Backup/restore, stress, provider failover, and readiness gates must produce testable evidence.

### Backup restore includes media and state

A successful restore must verify media objects/checksums, worldlines, conversations, presentations, memory, and provider config without secrets. Restoring only the database is not enough.

### Provider reliability cannot corrupt worlds

Fallback, degraded mode, model switch, manual retry, and requeue must be explicit and auditable. They must not cause duplicate provider spend, cross-worldline writes, or hidden model changes that alter world state without evidence.

### Import/export stability extends packaging, not marketplace

World packaging should become repeatable and safe for normal use, but v1.1 must not become a marketplace or public distribution channel.

### Polish follows product context

User-facing polish should remove friction, improve clarity, and support accessibility/responsiveness. It should not introduce decorative marketing surfaces or hide operational status.

## Risks / Trade-offs

- Backup drills can become environment-specific → Keep a local/single-host baseline and document optional extensions.
- Stress testing can be expensive → Use fake/mocked providers by default and opt-in real-provider stress only under explicit lab env.
- Provider fallback can mask quality problems → Surface degraded mode clearly to admins and player-safe UI.
- Polish can expand scope → Focus only on key onboarding, playback, scene, feedback, loading/error, mobile, and copy flows.
- RC gate can duplicate readiness systems → Aggregate existing readiness/eval evidence and add only missing RC-specific checks.

## Migration Plan

This roadmap does not add migrations. Expected migration pressure:

- Provider reliability may need retry/requeue records if current media/job/provider health records are insufficient.
- Stress evidence should reuse long-run eval and readiness records first.
- Import/export stability should reuse world packaging manifests first.
- Content safety should reuse v0.8 moderation/incident workflow first.

## Open Questions

- What is the minimum acceptable backup/restore target environment for RC: fresh local stack, staging, or both?
- How many concurrent worlds and players define the first normal-use stress baseline?
- Should provider fallback be automatic within strict policies or manual/admin-triggered first?
- Which user-facing polish issues are blocking RC versus deferred quality improvements?
