# Proposal — v1.0 Private Beta MVP

## Why

After v0.9 proves a self-use demo world, Noveland needs to support 1-3 invited testers without constant developer intervention. v1.0 turns the self-use path into a small private beta workflow with onboarding, setup checks, session stability, feedback, quota enforcement, and reviewable content iteration.

## What Changes

- Plan a v1.0 roadmap focused on invited private beta users rather than public launch.
- Add private beta onboarding for invited testers, player profiles, world selection, player identity, and first-run guidance.
- Harden player session resume, presentation restore, fallback states, and understandable error messaging.
- Enforce cost/quota limits before invited testers can generate provider spend.
- Add a world setup wizard that checks provider, media, voice, persona, memory, visual, onboarding, session, quota, and readiness evidence before testers enter.
- Add memory/persona QA, feedback collection, cost/quota enforcement, and reviewable beta content iteration loops.
- Preserve source traceability, preview/review/apply, provider boundaries, media boundaries, ACLs, and worldline isolation.

## Capabilities

### New Capabilities

- `private-beta-onboarding`: Invite-only tester onboarding, player profile creation, world selection, player identity setup, and first-run guidance.
- `player-session-stability`: Session resume, current conversation state, scene/presentation restore, fallback behavior, and player-safe error handling.
- `cost-quota-enforcement`: Real enforcement of world, player, provider, LLM, image, and TTS quotas with explicit fallback behavior.
- `world-setup-wizard`: Admin setup workflow that validates provider, media, voice, persona, memory, visual, onboarding, session, quota, and readiness completeness for private beta worlds.
- `memory-persona-qa`: Admin diagnostics for character memory contamination, persona drift, dialogue style drift, and worldline contamination.
- `beta-feedback-system`: Tester feedback, issue reporting, and admin triage linked to turns, presentations, media, invocations, and worldlines.
- `beta-content-iteration-loop`: Reviewable repair proposals for persona, memory, asset mapping, dialogue style, and binding issues based on feedback and diagnostics.
- `private-beta-gate`: Gate that validates 1-3 testers can experience a limited world for 1-2 hours with bounded cost, recoverable failures, and minimal developer intervention.

### Modified Capabilities

- None. v1.0 introduces planned private beta capability contracts that will later extend current specs when implemented and archived.

## Impact

- Future backend work will likely touch auth/invitations, player records, sessions, readiness/eval, memory/narrative quality, feedback/moderation-adjacent records, quota/cost controls, and authoring proposals.
- Future Web work will likely touch invite/onboarding, player resume, beta feedback, admin setup wizard, and beta QA screens; these must follow the Noveland product UI context and use `impeccable` before implementation.
- Future implementation must not open public registration, marketplace, public unauthenticated access, or automatic destructive repair.

## Feasibility Review Result

The v1.0 feasibility review concluded that implementation should not start from the original
roadmap order. v0.9 provides the content and provider foundation, but private beta requires
front-loaded decisions for invite/access ownership, player session restore, per-player/capability
quota enforcement, feedback ownership, and readiness/gate ownership. The revised phase order puts
access, session recovery, and quota before the world setup wizard.
