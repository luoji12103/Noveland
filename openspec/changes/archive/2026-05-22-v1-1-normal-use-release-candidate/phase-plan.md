# Phase Plan — v1.1 Normal Use / Release Candidate

## Version Goal

Make Noveland maintainable for longer-running normal use and release-candidate evaluation by proving operations, recovery, stress, safety, import/export, provider reliability, UI polish, and readiness evidence.

## Version Non-Goals

- Automatic public launch.
- Marketplace.
- Full external observability platform.
- Streaming runtime architecture.
- Public unauthenticated media access.
- Duplicate readiness, provider, media, packaging, moderation, or eval frameworks.
- Broad `worlds.py` route growth.

## Phase Discipline

- Implement phases strictly in order unless OpenSpec is updated first.
- Each phase starts from clean local `main`.
- Each phase begins with a docs-only phase checkpoint and harness update.
- Each implementation phase is independently testable, mergeable, and reversible.
- Each phase runs targeted tests, full local gate, OpenSpec validation, and `git diff --check`.
- Use fake/mocked providers by default; real-provider stress is opt-in only.
- Use `impeccable` before Web implementation.
- Do not push unless explicitly requested.

## Feasibility Decision

The accepted feasibility recommendation is **B. v1.1 can start after minor OpenSpec adjustments**.

The phase order remains unchanged. Phase 1 may start after the feasibility review is accepted. Phases 2-8 must each start with a docs-only checkpoint that confirms any unresolved environment, schema, API, package/router, or Web-scope decisions before implementation.

## Phase 1 — Operational Runbooks

### Goal

Write and validate operator procedures for common normal-use incidents.

### Scope

- Provider failure handling.
- Quota exhaustion handling.
- Media/job stuck handling.
- Migration failure handling.
- Worldline rollback review.
- Worldline restore operation.
- Backup/restore operation.
- Secret rotation operation.
- Invite/session/feedback incident handling.
- Import/export recovery.

### Non-Goals

- New runtime behavior unless required by a runbook gap and accepted in a later phase.
- External SRE platform.

### Reused Systems

- v0.7 operations docs.
- Observability diagnostics.
- Provider/media/readiness reports.

### Targeted Tests

- Docs consistency tests where lightweight.
- Runbook references existing commands/routes.
- No secret or storage path examples in unsafe form.

### Stop Conditions

- Runbook requires unimplemented behavior to be considered complete.
- Secret rotation guidance would expose secrets.
- Rollback or restore guidance encourages unsafe direct database mutation as the default path.

## Phase 2 — Real Backup/Restore Drill

### Goal

Perform a real backup and restore to a fresh environment/profile and verify state.

### Scope

- Fresh local/single-host restore target with empty database and object storage root.
- Database dump/restore.
- Media/object payload archive restore.
- Checksum validation.
- Worldline/conversation/presentation/memory verification.
- Provider config without secrets.
- OpenSpec/docs provenance verification.

### Non-Goals

- Cloud-specific managed backup product.
- Restoring resolved secrets.

### Reused Systems

- Storage backup docs.
- Media object checksums.
- Worldline/conversation/memory diagnostics.

### Targeted Tests

- Backup manifest validates.
- Restored media checksums match.
- Restored worldline/conversation/memory references resolve.
- Provider secrets absent.
- Restore report avoids storage paths, raw prompts, raw outputs, bytes, base64, and secrets.

### Stop Conditions

- Restore requires leaking storage paths or secrets.
- Media/object restore cannot be verified.
- Drill target cannot be isolated from the active developer database/object store.

## Phase 3 — Multi-world / Multi-user Stress Test

### Goal

Exercise multiple worlds, players, providers, and long sessions under controlled conditions.

### Scope

- Deterministic fixture with at least 3 worlds.
- At least 2 worldlines per world.
- At least 2 player sessions per world.
- At least 2 fake provider profiles.
- Deterministic 120-turn or equivalent long-session eval/report.

### Non-Goals

- Unbounded load testing.
- Default real-provider stress.

### Reused Systems

- Long-run eval.
- Production readiness and diagnostics.
- Provider lab opt-in for real-provider runs.

### Targeted Tests

- Multiple worlds remain isolated.
- Multiple players remain scoped.
- Provider quotas hold.
- Long-session report is safe.

### Stop Conditions

- Stress test mutates across worldlines.
- Default gate would consume provider quota.
- Stress fixture requires proprietary or user-provided galgame assets.

## Phase 4 — Content Safety & Moderation Hardening

### Goal

Harden player-visible content safety, report/takedown, visibility, and character output boundaries.

### Scope

- Player-visible content review checks.
- Report/takedown hardening.
- Beta feedback safety escalation.
- Player privacy integration.
- Character output safety boundaries.
- Public/private visibility regression.

### Non-Goals

- Automatic punitive action without explicit policy.
- Public moderator UI unless separately approved.

### Reused Systems

- Moderation/incident workflow.
- Narrative quality diagnostics.
- Reader media delivery.
- Permission model hardening.

### Targeted Tests

- Takedown hides content/media.
- Reporter privacy protected.
- Unsafe output is flagged.
- Reader/player routes respect visibility.

### Stop Conditions

- Moderation leaks reporter private data.
- Safety action mutates world state without audit.
- Safety evidence requires raw prompt snapshots in player/member responses.

## Phase 5 — Import/Export Stability

### Goal

Stabilize world package import/export for normal use.

### Scope

- World package export/import.
- Media manifest.
- Persona/memory manifest.
- Provider config without secrets.
- Visual/voice mapping manifests.
- Source traceability manifests.
- Proprietary/user-provided asset export policy.
- Repeatable sample package import.

### Non-Goals

- Marketplace.
- Raw prompt snapshot export by default.
- Resolved secret export.

### Reused Systems

- v0.8 world packaging.
- Sample world release package.
- Authoring preview/apply.
- Media manifests.

### Targeted Tests

- Export/import roundtrip.
- No secret/storage path/raw prompt leak.
- Persona/memory manifest validates.
- Sample world package imports repeatedly.

### Stop Conditions

- Import bypasses preview/apply.
- Package requires resolved secrets.
- User-provided galgame assets would be committed to repository fixtures or public sample exports.

## Phase 6 — Provider Reliability Layer

### Goal

Add controlled provider fallback, degraded mode, health trends, model switch, manual retry, and requeue.

### Scope

- Per-provider health trend.
- Manual retry/requeue.
- Degraded mode.
- Manual-first configured fallback/model switch with audit.
- Constrained automatic fallback only when explicitly configured and capability/quota checked.

### Non-Goals

- Marketplace.
- Hidden model switch.
- Provider execution outside provider kernel.

### Reused Systems

- Provider execution service.
- Provider health checks.
- Invocation ledger.
- Cost/quota controls.
- Media jobs.

### Targeted Tests

- Failed provider enters degraded state.
- Manual retry/requeue is audited.
- Fallback respects capability and quota.
- No duplicate hidden spend.

### Stop Conditions

- Fallback can corrupt world state.
- Model switch is not auditable.
- Retry/requeue can duplicate hidden spend.

## Phase 7 — User-facing Polish

### Goal

Polish key user-facing flows for normal use.

### Scope

- Loading and error states.
- Mobile/basic responsive behavior.
- Audio and scene playback clarity.
- Onboarding copy.
- Feedback affordances.
- Quota exceeded and provider degraded states.
- Setup/readiness, import/export, and provider status clarity where scoped.
- Accessibility improvements.

### Non-Goals

- Brand/marketing redesign.
- Full game engine.
- Decorative hero pages.

### Reused Systems

- v0.8 playback/scene/player UI.
- v1.0 onboarding/feedback/session stability.
- Existing Web design primitives.

### Targeted Tests

- Web lint/typecheck/unit/e2e.
- Accessibility/responsive smoke where feasible.
- Error/loading state tests.

### Stop Conditions

- UI work starts without `impeccable`.
- Polish requires unstable backend contract changes.
- Polish expands into marketing redesign or decorative hero pages.

## Phase 8 — Release Candidate Gate

### Goal

Produce a normal-use release-candidate report.

### Scope

- Operational runbook evidence.
- Backup/restore drill evidence.
- Stress evidence.
- Safety/moderation evidence.
- Import/export evidence.
- Provider reliability evidence.
- User-facing polish evidence.
- v0.7/v0.8/v1.0 readiness evidence.
- Distinction between self-use MVP, private beta, normal use, release candidate, and public launch readiness.

### Non-Goals

- Automatic public launch.
- Duplicate release framework.

### Reused Systems

- Production readiness gate.
- Public launch gate.
- Private beta gate.
- Long-run eval records.
- Observability diagnostics.

### Targeted Tests

- RC gate passes with complete evidence.
- RC gate fails on missing backup restore.
- RC gate fails on leak fixture.
- Report is safe for admin review.

### Stop Conditions

- Gate bypasses prior readiness.
- Gate enables public launch automatically.
- Gate duplicates observability/readiness framework.
