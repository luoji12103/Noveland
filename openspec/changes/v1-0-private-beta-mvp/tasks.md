# Tasks — v1.0 Private Beta MVP

Use these tasks when implementation is explicitly requested. Planning tasks may be marked complete
during roadmap alignment; implementation tasks must only be marked complete after code, tests, full
local gate, fast-forward merge, and harness updates are done.

## 1. Planning / Preflight

- [x] 1.1 Confirm v0.9 is complete, archived, and represented in current specs.
- [x] 1.2 Write v1.0 feasibility review before implementation begins.
- [x] 1.3 Revise v1.0 phase order based on feasibility review.
- [x] 1.4 Confirm private beta invitation model and whether existing world memberships are sufficient.
- [x] 1.5 Confirm player session/resume schema and package/router ownership.
- [ ] 1.6 Confirm quota enforcement coverage across runtime/provider/media/speech/image paths.
- [ ] 1.7 Confirm feedback ownership and whether moderation records can be reused.
- [ ] 1.8 Confirm setup wizard and private beta gate reuse existing observability/readiness.
- [x] 1.9 Confirm frontend phases will use `impeccable` before Web implementation.

## 2. Phase 1 — Private Beta Onboarding & Access Model

- [x] 2.1 Write docs-only phase planning checkpoint for invite/access ownership.
- [x] 2.2 Decide dedicated invite/access records vs membership-only model.
- [x] 2.3 Implement invite-only beta eligibility and player profile setup.
- [x] 2.4 Implement onboarding UI only after using `impeccable`.
- [x] 2.5 Add invite, profile, authorization, expiration/revocation, and no-leak tests.
- [x] 2.6 Run targeted tests, full local gate, OpenSpec validation, and `git diff --check`.
- [x] 2.7 Fast-forward merge to local main and update harness docs.

## 3. Phase 2 — Player Session Stability

- [x] 3.1 Write docs-only phase planning checkpoint for player session/resume ownership.
- [x] 3.2 Implement session resume and presentation restore.
- [x] 3.3 Implement player-safe loading/error/fallback UI only after using `impeccable`.
- [x] 3.4 Add resume, fallback, cross-player, worldline, ACL, and no-leak tests.
- [x] 3.5 Run targeted tests, full local gate, OpenSpec validation, and `git diff --check`.
- [ ] 3.6 Fast-forward merge to local main and update harness docs.

## 4. Phase 3 — Cost & Quota Real Enforcement

- [ ] 4.1 Write docs-only phase planning checkpoint for player/capability quota ownership.
- [ ] 4.2 Audit all runtime/provider/media/speech/image spend paths for pre-call quota coverage.
- [ ] 4.3 Implement world/player/provider/capability quota enforcement.
- [ ] 4.4 Implement admin quota controls and tester quota fallback UI only after using `impeccable` if Web scope is approved.
- [ ] 4.5 Add limit, fallback, per-player isolation, override, audit, and no-hidden-spend tests.
- [ ] 4.6 Run targeted tests, full local gate, OpenSpec validation, and `git diff --check`.
- [ ] 4.7 Fast-forward merge to local main and update harness docs.

## 5. Phase 4 — World Setup Wizard

- [ ] 5.1 Write docs-only phase planning checkpoint for readiness aggregation ownership.
- [ ] 5.2 Implement setup wizard evidence aggregation and readiness report.
- [ ] 5.3 Implement setup wizard UI only after using `impeccable`.
- [ ] 5.4 Add provider/media/visual/speech/persona/memory/onboarding/session/quota completeness tests.
- [ ] 5.5 Run targeted tests, full local gate, OpenSpec validation, and `git diff --check`.
- [ ] 5.6 Fast-forward merge to local main and update harness docs.

## 6. Phase 5 — Memory & Persona QA

- [ ] 6.1 Write docs-only phase planning checkpoint for QA diagnostics ownership.
- [ ] 6.2 Implement admin diagnostics for memory contamination and persona drift.
- [ ] 6.3 Add QA UI only after using `impeccable` if Web scope is approved.
- [ ] 6.4 Add contamination, drift, worldline, redaction, and repair-proposal tests.
- [ ] 6.5 Run targeted tests, full local gate, OpenSpec validation, and `git diff --check`.
- [ ] 6.6 Fast-forward merge to local main and update harness docs.

## 7. Phase 6 — Beta Feedback System

- [ ] 7.1 Write docs-only phase planning checkpoint for feedback ownership.
- [ ] 7.2 Decide dedicated beta feedback package/router vs moderation extension.
- [ ] 7.3 Implement feedback submission and admin triage over safe refs.
- [ ] 7.4 Implement tester feedback UI and admin triage UI only after using `impeccable`.
- [ ] 7.5 Add feedback, triage, reporter privacy, ACL, repair-link, and no-leak tests.
- [ ] 7.6 Run targeted tests, full local gate, OpenSpec validation, and `git diff --check`.
- [ ] 7.7 Fast-forward merge to local main and update harness docs.

## 8. Phase 7 — Beta Content Iteration Loop

- [ ] 8.1 Write docs-only phase planning checkpoint for repair proposal ownership.
- [ ] 8.2 Implement feedback/diagnostic repair proposals and reviewed apply.
- [ ] 8.3 Implement repair review UI only after using `impeccable` if Web scope is approved.
- [ ] 8.4 Add persona/memory/asset/voice/provider-profile repair, audit, worldline, and no-leak tests.
- [ ] 8.5 Run targeted tests, full local gate, OpenSpec validation, and `git diff --check`.
- [ ] 8.6 Fast-forward merge to local main and update harness docs.

## 9. Phase 8 — Private Beta Gate

- [ ] 9.1 Write docs-only phase planning checkpoint for private beta readiness ownership.
- [ ] 9.2 Implement private beta gate evidence aggregation.
- [ ] 9.3 Add readiness UI only after using `impeccable` if Web scope is approved.
- [ ] 9.4 Add gate pass/fail, onboarding/session/quota/feedback, leak fixture, and report-redaction tests.
- [ ] 9.5 Run targeted tests, full local gate, OpenSpec validation, and `git diff --check`.
- [ ] 9.6 Fast-forward merge to local main and update harness docs.

## 10. Closeout

- [ ] 10.1 Archive the completed OpenSpec change only after all phases are accepted.
- [ ] 10.2 Generate v1.0 release notes.
- [ ] 10.3 Confirm main is clean and report ahead/behind origin.
