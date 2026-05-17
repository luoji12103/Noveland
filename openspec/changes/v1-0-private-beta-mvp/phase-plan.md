# Phase Plan — v1.0 Private Beta MVP

## Version Goal

Allow 1-3 invited testers to use a limited world for 1-2 hours without constant developer
intervention, while preserving Noveland's safety, cost, traceability, provider, media, memory,
and worldline boundaries.

## Version Non-Goals

- Public registration.
- Marketplace, public launch, or public unauthenticated delivery.
- Automatic destructive repair.
- Hidden provider spend.
- Duplicate readiness, provider, media, memory, or feedback frameworks.
- Broad `worlds.py` route growth.

## Feasibility Review Decision

The v1.0 feasibility review concluded: **C. v1.0 phase order must be revised before
implementation.**

v0.9 provides the content and provider foundation, but private beta introduces external tester
access, recoverability, quota, and feedback obligations. Therefore the v1.0 order front-loads
invite/access, player session stability, and quota enforcement before the setup wizard and final
gate.

## Revised Phase Order

1. Private Beta Onboarding & Access Model
2. Player Session Stability
3. Cost & Quota Real Enforcement
4. World Setup Wizard
5. Memory & Persona QA
6. Beta Feedback System
7. Beta Content Iteration Loop
8. Private Beta Gate

## Phase Discipline

- Implement phases strictly in order unless OpenSpec is updated first.
- Each phase starts from clean local `main`.
- Each phase begins with a docs-only phase checkpoint and harness update.
- Each implementation phase is independently testable, mergeable, and reversible.
- Each phase runs targeted tests, full local gate, OpenSpec validation, and `git diff --check`.
- Do not continue after failing tests, unresolved migration issues, unclear provider boundaries,
  unclear worldline isolation, unclear tester access semantics, or leak risk.
- Use `impeccable` before Web implementation.
- Do not push unless explicitly requested.

## Phase 1 — Private Beta Onboarding & Access Model

### Goal

Invite testers, create player profiles, choose a world, choose/create a player identity, and show
first-run guidance while preserving deny-by-default access.

### Scope

- Docs-only checkpoint deciding invite/access schema and router ownership.
- Dedicated private beta invite/access model; do not use membership-only access.
- Invite-only eligibility, including pending, waitlisted, accepted, redeemed, expired, revoked,
  expiration, revocation, redemption, and audit.
- Planned `backend/packages/private_beta/` package and app-level
  `backend/services/api/src/noveland/services/api/private_beta.py` router.
- `WorldMembership` remains the least-privilege enforcement layer after valid redemption.
- Player profile setup.
- World selection for eligible testers.
- Player identity setup through existing player boundaries.
- Minimal first-run tutorial.

### Non-Goals

- Public registration.
- Marketplace.
- Social graph.
- Admin/provider diagnostics in tester responses.

### Reused Systems

- Auth/session.
- World memberships.
- Existing player records.
- Reader/player UI shells.
- Permission matrix and access review patterns.

### Targeted Tests

- Invite or eligibility required.
- Expired/revoked/uninvited tester rejected.
- Player profile and identity created in authorized world/worldline scope.
- Unauthorized user rejected by default.
- No admin diagnostics, provider config, storage path, raw prompt/output, or secret leaks.

### Stop Conditions

- Public signup is required.
- Existing auth/membership model cannot represent private beta safely and no migration checkpoint
  is approved.
- Invite tokens would be stored or logged in plaintext.
- Implementation requires broad onboarding route growth in `worlds.py`.
- Tester onboarding requires admin/provider privileges.

## Phase 2 — Player Session Stability

### Goal

Restore player session, current conversation state, scene/presentation state, and fallback UI after
browser close/reopen or provider/media interruption.

### Scope

- Docs-only checkpoint deciding player session schema and package/router ownership.
- Current worldline/current conversation/current scene/current presentation tracking.
- Player-safe resume endpoint.
- Scene/presentation/audio/image fallback state.
- Player-safe errors.
- No manual DB repair for normal resume.
- Multi-tester isolation.

### Non-Goals

- Offline mode.
- Real-time multiplayer synchronization.
- Raw event payload display.

### Reused Systems

- Conversation sessions/turns.
- Conversation presentations.
- Reader media delivery.
- Player actor/profile records.
- Player choices, journal, notifications, and interventions.

### Targeted Tests

- Close/reopen restores current session.
- Cross-player session access rejected.
- Missing media fallback is safe.
- Provider failure fallback is safe.
- Cross-worldline resume rejected.
- No leak in player responses.

### Stop Conditions

- Resume requires unsafe raw event payload exposure.
- Player state model conflicts with worldline isolation.
- Multiple testers share mutable session state unintentionally.

## Phase 3 — Cost & Quota Real Enforcement

### Goal

Enforce bounded spend per world, player, provider, and capability before external provider calls.

### Scope

- Docs-only checkpoint deciding quota schema/policy extension.
- LLM, image, TTS, and ASR quota checks.
- World/player/provider/capability limits.
- Explicit fallback when over limit.
- Admin controls and audited overrides.
- Runtime spend path coverage audit.

### Non-Goals

- Billing system.
- Marketplace pricing.
- Silent quota bypass.

### Reused Systems

- v0.7 cost/rate controls.
- Provider execution service.
- Media jobs.
- Asset generation policies.
- Invocation cost metadata.
- Provider model lab smoke evidence.

### Targeted Tests

- Limit blocks excessive calls before provider execution.
- Per-player limit is isolated from another tester.
- Capability limit blocks the correct text/image/TTS/ASR path.
- Safe fallback returned.
- Admin override is explicit and audited.
- No hidden spend and no real provider calls by default.

### Stop Conditions

- Enforcement cannot cover runtime provider calls.
- Per-player enforcement cannot identify the current tester.
- Limit failures are silent, retry into hidden spend, or expose provider internals.

## Phase 4 — World Setup Wizard

### Goal

Let admins prepare a beta world and validate provider, media, voice, persona, memory, visual,
onboarding, session, quota, feedback, and readiness completeness.

### Scope

- Setup checklist.
- Provider/model readiness.
- Media/visual/speech completeness.
- Persona/memory readiness.
- v0.9 self-use gate evidence.
- Onboarding/access readiness.
- Session restore readiness.
- Quota readiness.
- Private beta readiness report.

### Non-Goals

- Auto-fixing missing content.
- Public launch gate.
- Duplicate readiness framework.

### Reused Systems

- v0.7 production readiness patterns.
- v0.8 public launch/readiness patterns.
- v0.9 self-use gate evidence.
- Multimodal diagnostics.
- Provider, media, visual, speech, memory, authoring, private beta access, player session, and
  quota systems.

### Targeted Tests

- Ready world passes.
- Missing voice/persona/provider/session/quota blocks.
- Report is safe and admin-scoped.
- Player requests are denied or redacted.

### Stop Conditions

- Wizard duplicates readiness framework.
- Report requires raw prompt/output, prompt snapshot internals, resolved secrets, or storage paths.
- Wizard is implemented before access/session/quota evidence can be represented.

## Phase 5 — Memory & Persona QA

### Goal

Help admins detect memory contamination, persona drift, dialogue style drift, relationship drift,
and worldline contamination.

### Scope

- Docs-only checkpoint deciding whether QA is read-only diagnostics over existing eval/authoring
  records or needs persisted QA runs.
- Admin diagnostics.
- Suggested repair proposals.
- Evidence refs to source, memory, turns, and invocations.
- No automatic destructive fix.

### Non-Goals

- Direct memory rewrite.
- Reader/player diagnostic access.
- Replacement memory framework.

### Reused Systems

- Narrative quality diagnostics.
- Memory service/evals.
- Invocation ledger.
- Authoring proposals.
- v0.9 persona/memory distillation evidence.

### Targeted Tests

- Detect contaminated memory.
- Detect persona/style drift.
- Reject cross-worldline evidence.
- Response redaction.
- Repair suggestions are proposal-only.

### Stop Conditions

- Diagnostics require exposing raw prompts/outputs to non-admin users.
- Repair path bypasses review/apply.
- Persona or memory apply cannot preserve source traceability.

## Phase 6 — Beta Feedback System

### Goal

Let testers report scene, dialogue, character, voice, image, playback, provider, memory/persona,
and UX issues and let admins triage them.

### Scope

- Docs-only checkpoint deciding whether to extend moderation or add a dedicated beta feedback
  package/router.
- Player feedback submission.
- Admin triage.
- Links to turn, presentation, media, invocation, route, persona, memory, and worldline safe refs.
- Status lifecycle.

### Non-Goals

- Public forum.
- Automatic moderation punishment.
- Unreviewed repair apply.

### Reused Systems

- Moderation/incident workflow where suitable.
- Conversation presentations.
- Media references.
- Invocation ledger safe refs.
- Incident evidence refs.
- Authoring proposals for repair linkage.

### Targeted Tests

- Feedback creation.
- Admin triage.
- Reporter privacy.
- Safe evidence refs only.
- Cross-world/cross-worldline evidence rejection.

### Stop Conditions

- Feedback needs public social scope.
- Evidence model leaks raw prompt/output, prompt snapshot internals, storage paths, bytes, base64,
  or secrets.
- Reporter private data is visible to other testers.

## Phase 7 — Beta Content Iteration Loop

### Goal

Generate reviewable fixes from feedback and diagnostics without rewriting history.

### Scope

- Persona repair proposals.
- Memory repair proposals.
- Asset mapping repair proposals.
- Voice/style repair proposals.
- Provider prompt/profile or visual generation profile repair proposals where review/apply supports
  them safely.
- Audited apply.

### Non-Goals

- Direct historical mutation.
- Automatic repair apply.
- Replacement authoring proposal system.

### Reused Systems

- Authoring proposal/review/apply.
- Narrative quality diagnostics.
- Beta feedback evidence.
- Memory/persona services.
- Visual generation, visual, and speech bindings.

### Targeted Tests

- Fix OOC issue through proposal/apply.
- Fix wrong sprite/voice binding through proposal/apply.
- Feedback-to-repair traceability preserved.
- Audit trail preserved.
- Worldline isolation enforced.

### Stop Conditions

- Repair needs direct mutation outside review/apply.
- Historical continuity is corrupted.
- Feedback or source traceability is lost.

## Phase 8 — Private Beta Gate

### Goal

Validate 1-3 testers can experience a world for 1-2 hours with bounded failures, recoverable
session state, feedback, quota enforcement, and minimal developer intervention.

### Scope

- Gate report over onboarding, setup wizard, session stability, memory/persona QA, feedback, quota,
  and repair evidence.
- Failure summary for crash, provider failure, character drift, cost, session recovery, feedback,
  and content quality.
- Manual 1-2 hour tester-session checklist.

### Non-Goals

- Public launch gate.
- Normal-use RC gate.
- Duplicate readiness framework.

### Reused Systems

- v0.9 self-use gate.
- v0.8 public launch/readiness patterns.
- v0.7 production readiness.
- Long-run eval records where suitable.
- Private beta access/session/quota/feedback evidence.

### Targeted Tests

- Gate passes with complete evidence.
- Gate fails without onboarding/session/quota/feedback path.
- Gate fails on leak fixture.
- Report remains admin-safe.
- Gate remains distinct from public launch readiness.

### Stop Conditions

- Gate duplicates release framework.
- Gate implies public launch readiness.
- Gate needs raw prompt/output, prompt snapshot internals, resolved secrets, bytes/base64, or
  storage paths.
