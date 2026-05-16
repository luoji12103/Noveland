# Design — v1.0 Private Beta MVP

## Context

v0.9 is expected to prove that the developer can play a real demo world for about 30 minutes. v1.0 raises the bar from self-use to a small invited tester group. The design objective is controlled reliability, not scale or public growth.

```text
self-use demo evidence
  -> admin setup wizard
  -> invite-only onboarding
  -> stable player sessions
  -> feedback and diagnostics
  -> bounded cost/quota
  -> reviewable repairs
  -> private beta gate
```

## Goals / Non-Goals

**Goals:**

- Let 1-3 invited testers enter a prepared world without developer DB edits.
- Restore player sessions, conversation state, scene state, and fallback UI after browser close/reopen.
- Give admins setup and QA evidence before inviting testers.
- Collect feedback tied to concrete turn, media, presentation, provider, invocation, and worldline evidence.
- Enforce real quotas so one tester cannot cause unbounded provider spend.
- Generate repair proposals from feedback/diagnostics while preserving review/apply and auditability.

**Non-Goals:**

- Public registration.
- Marketplace or public world directory.
- Automatic destructive repair.
- Automatic provider spend outside explicit gameplay or admin-reviewed actions.
- Public launch readiness.
- Broad route growth in `worlds.py`.

## Decisions

### Private beta remains invite-only

v1.0 should reuse existing auth/session/world membership/player records where possible and add only the minimum invitation or eligibility model needed. Public signup belongs later.

### Setup wizard aggregates existing evidence

The world setup wizard should not duplicate readiness systems. It must aggregate provider health, media/visual/speech completeness, persona/memory evidence, diagnostics, v0.9 self-use gate evidence, and v0.8/v0.7 readiness where useful.

### Session stability is a product requirement

Private beta testers should be able to close the browser and return to a stable conversation, scene/presentation state, and fallback status. The design should prefer explicit recoverable states over hidden retries or silent reset.

### Feedback is linked evidence, not a forum

Feedback records should point to turn, conversation, presentation, media, invocation, route, worldline, and player context through safe refs. v1.0 should not build public forums or social features.

### Repair uses proposal/review/apply

Diagnostics and feedback may generate repair proposals for memory, persona, dialogue style, visual mapping, voice mapping, or route issues. They must not directly rewrite history or mutate canonical state without review.

### Frontend surfaces must be operational

Onboarding and admin setup UI should be calm, explicit, and task-focused. They must avoid decorative hero flows, hidden cost/spend, and vague AI demo language.

## Risks / Trade-offs

- Invitation scope can drift into public auth → Keep invite-only and stop if public signup becomes necessary.
- Session restore can conflict with worldline isolation → Require world/worldline/player scope on resume records and tests.
- Feedback can leak internals → Store safe evidence refs, not raw prompts, raw outputs, storage paths, or secrets.
- Quota enforcement can break user flow → Provide explicit fallback states and admin override review paths.
- Repair proposals can become automatic mutation → Keep review/apply as the only mutation path.

## Migration Plan

This roadmap does not add migrations. Expected migration pressure:

- Onboarding may need invitation/beta eligibility records unless existing memberships can represent invites.
- Feedback likely needs persistent report/feedback records unless v0.8 moderation records are sufficient.
- Cost/quota enforcement may extend v0.7 cost/rate controls.
- Session stability should reuse existing conversation/player/session state first and stop if a new canonical state model is required.

## Open Questions

- Can existing world memberships represent private beta invites, or is a dedicated invite table needed?
- Should beta feedback extend moderation incident records or use a dedicated beta feedback package?
- What is the minimum quota model for private beta: per world, per player, per provider, or all three?
- Should the private beta gate be implemented under existing readiness/eval systems or a dedicated beta readiness route?
