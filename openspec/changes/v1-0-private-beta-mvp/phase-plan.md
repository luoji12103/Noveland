# Phase Plan — v1.0 Private Beta MVP

## Version Goal

Allow 1-3 invited testers to use a limited world for 1-2 hours without constant developer intervention, while preserving Noveland's safety, cost, traceability, provider, media, memory, and worldline boundaries.

## Version Non-Goals

- Public registration.
- Marketplace, public launch, or public unauthenticated delivery.
- Automatic destructive repair.
- Hidden provider spend.
- Duplicate readiness, provider, media, memory, or feedback frameworks.
- Broad `worlds.py` route growth.

## Phase Discipline

- Implement phases strictly in order unless OpenSpec is updated first.
- Each phase starts from clean local `main`.
- Each phase begins with a docs-only phase checkpoint and harness update.
- Each implementation phase is independently testable, mergeable, and reversible.
- Each phase runs targeted tests, full local gate, OpenSpec validation, and `git diff --check`.
- Do not continue after failing tests, unresolved migration issues, unclear provider boundaries, unclear worldline isolation, or leak risk.
- Use `impeccable` before Web implementation.
- Do not push unless explicitly requested.

## Phase 1 — Private Beta Onboarding

### Goal

Invite testers, create player profiles, choose a world, choose/create a player identity, and show first-run guidance.

### Scope

- Invite-only eligibility.
- Player profile setup.
- World selection for eligible testers.
- Player identity setup.
- Minimal first-run tutorial.

### Non-Goals

- Public registration.
- Marketplace.
- Social graph.

### Reused Systems

- Auth/session.
- World memberships.
- Existing player records.
- Reader/player UI shells.

### Targeted Tests

- Invite required.
- Player profile created.
- Unauthorized user rejected.
- No admin diagnostics or secrets leak.

### Stop Conditions

- Public signup is required.
- Existing auth/membership model cannot represent private beta safely.

## Phase 2 — World Setup Wizard

### Goal

Let admins prepare a beta world and validate provider, media, voice, persona, memory, visual, and readiness completeness.

### Scope

- Setup checklist.
- Provider/model readiness.
- Media/visual/speech completeness.
- Persona/memory readiness.
- v0.9 gate evidence.
- Private beta readiness report.

### Non-Goals

- Auto-fixing missing content.
- Public launch gate.

### Reused Systems

- v0.8 public launch/readiness patterns.
- v0.9 self-use gate evidence.
- Multimodal diagnostics.
- Provider, media, visual, speech, memory, authoring systems.

### Targeted Tests

- Ready world passes.
- Missing voice/persona/provider blocks.
- Report is safe and admin-scoped.

### Stop Conditions

- Wizard duplicates readiness framework.
- Report requires raw prompt/output or storage paths.

## Phase 3 — Player Session Stability

### Goal

Restore player session, current conversation state, scene/presentation state, and fallback UI after interruption.

### Scope

- Resume current conversation.
- Restore scene/presentation/audio/image fallback state.
- Player-safe errors.
- No manual DB repair for normal resume.

### Non-Goals

- Offline mode.
- Real-time multiplayer synchronization.

### Reused Systems

- Conversation sessions/turns.
- Conversation presentations.
- Reader media delivery.
- Player state records.

### Targeted Tests

- Close/reopen restores session.
- Missing media fallback is safe.
- Cross-worldline resume rejected.
- No leak in player responses.

### Stop Conditions

- Resume requires unsafe raw event payload exposure.
- Player state model conflicts with worldline isolation.

## Phase 4 — Memory & Persona QA

### Goal

Help admins detect memory contamination, persona drift, style drift, and worldline contamination.

### Scope

- Admin diagnostics.
- Suggested repair proposals.
- Evidence refs to source, memory, turns, and invocations.
- No automatic destructive fix.

### Non-Goals

- Direct memory rewrite.
- Reader/player diagnostic access.

### Reused Systems

- Narrative quality diagnostics.
- Memory service/evals.
- Invocation ledger.
- Authoring proposals.

### Targeted Tests

- Detect contaminated memory.
- Detect persona/style drift.
- Reject cross-worldline evidence.
- Response redaction.

### Stop Conditions

- Diagnostics require exposing raw prompts/outputs to non-admin users.
- Repair path bypasses review/apply.

## Phase 5 — Beta Feedback System

### Goal

Let testers report scene, dialogue, character, voice, image, and playback issues and let admins triage them.

### Scope

- Player feedback submission.
- Admin triage.
- Links to turn, presentation, media, invocation, route, and worldline safe refs.
- Status lifecycle.

### Non-Goals

- Public forum.
- Automatic moderation punishment.

### Reused Systems

- Moderation/incident workflow where suitable.
- Conversation presentations.
- Media references.
- Invocation ledger safe refs.

### Targeted Tests

- Feedback creation.
- Admin triage.
- Reporter privacy.
- Safe evidence refs only.

### Stop Conditions

- Feedback needs public social scope.
- Evidence model leaks raw prompt/output or storage paths.

## Phase 6 — Cost & Quota Real Enforcement

### Goal

Enforce bounded spend per world, player, provider, and capability.

### Scope

- LLM, image, TTS, ASR quota checks.
- World/player/provider limits.
- Fallback when over limit.
- Admin controls.

### Non-Goals

- Billing system.
- Marketplace pricing.

### Reused Systems

- v0.7 cost/rate controls.
- Provider execution service.
- Media jobs.
- Asset generation policies.
- Invocation cost metadata.

### Targeted Tests

- Limit blocks excessive calls.
- Safe fallback returned.
- Admin override is explicit and audited.
- No hidden spend.

### Stop Conditions

- Enforcement cannot cover runtime provider calls.
- Limit failures are silent or unsafe.

## Phase 7 — Beta Content Iteration Loop

### Goal

Generate reviewable fixes from feedback and diagnostics without rewriting history.

### Scope

- Persona repair proposals.
- Memory repair proposals.
- Asset mapping repair proposals.
- Voice/style repair proposals.
- Audited apply.

### Non-Goals

- Direct historical mutation.
- Automatic repair apply.

### Reused Systems

- Authoring proposal/review/apply.
- Narrative quality diagnostics.
- Memory/persona services.
- Visual and speech bindings.

### Targeted Tests

- Fix OOC issue through proposal/apply.
- Fix wrong sprite/voice binding through proposal/apply.
- Audit trail preserved.
- Worldline isolation enforced.

### Stop Conditions

- Repair needs direct mutation outside review/apply.
- Historical continuity is corrupted.

## Phase 8 — Private Beta Gate

### Goal

Validate 1-3 testers can experience a world for 1-2 hours with bounded failures and minimal developer intervention.

### Scope

- Gate report over onboarding, setup, session stability, memory/persona QA, feedback, quota, and repair evidence.
- Failure summary for crash, provider failure, character drift, cost, and content quality.

### Non-Goals

- Public launch gate.
- Normal-use RC gate.

### Reused Systems

- v0.9 self-use gate.
- v0.8 public launch/readiness patterns.
- v0.7 production readiness.
- Long-run eval records where suitable.

### Targeted Tests

- Gate passes with complete evidence.
- Gate fails without quota or feedback path.
- Gate fails on leak fixture.
- Report remains admin-safe.

### Stop Conditions

- Gate duplicates release framework.
- Gate implies public launch readiness.
