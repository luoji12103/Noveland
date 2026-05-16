# Tasks — v1.1 Normal Use / Release Candidate

Use these tasks when implementation is explicitly requested. Planning tasks may be marked complete during roadmap alignment; implementation tasks must only be marked complete after code, tests, full local gate, fast-forward merge, and harness updates are done.

## 1. Planning / Preflight

- [ ] 1.1 Confirm v1.0 is complete, archived, and represented in current specs.
- [ ] 1.2 Write v1.1 feasibility review before implementation begins.
- [ ] 1.3 Confirm backup/restore drill target environment.
- [ ] 1.4 Confirm stress baseline for worlds, players, providers, and session duration.
- [ ] 1.5 Confirm provider reliability policy: manual-first or constrained automatic fallback.
- [ ] 1.6 Confirm frontend phases will use `impeccable` before Web implementation.

## 2. Phase 1 — Operational Runbooks

- [ ] 2.1 Write docs-only phase planning checkpoint.
- [ ] 2.2 Add provider failure, media/job recovery, worldline rollback, backup/restore, and secret rotation runbooks.
- [ ] 2.3 Add lightweight docs consistency tests if useful.
- [ ] 2.4 Run targeted docs checks, OpenSpec validation, full applicable gate, and `git diff --check`.
- [ ] 2.5 Fast-forward merge to local main and update harness docs.

## 3. Phase 2 — Real Backup/Restore Drill

- [ ] 3.1 Write docs-only phase planning checkpoint.
- [ ] 3.2 Implement or document executable backup/restore drill steps for the accepted environment.
- [ ] 3.3 Verify database, media, checksums, worldlines, conversations, presentations, memory, and provider config without secrets.
- [ ] 3.4 Add backup/restore drill, checksum, reference, and no-secret tests.
- [ ] 3.5 Run targeted tests, full local gate, OpenSpec validation, and `git diff --check`.
- [ ] 3.6 Fast-forward merge to local main and update harness docs.

## 4. Phase 3 — Multi-world / Multi-user Stress Test

- [ ] 4.1 Write docs-only phase planning checkpoint.
- [ ] 4.2 Implement stress fixture/report with fake providers by default.
- [ ] 4.3 Add opt-in real-provider stress profile only if safe.
- [ ] 4.4 Add isolation, quota, long-session, and safe-report tests.
- [ ] 4.5 Run targeted tests, full local gate, OpenSpec validation, and `git diff --check`.
- [ ] 4.6 Fast-forward merge to local main and update harness docs.

## 5. Phase 4 — Content Safety & Moderation Hardening

- [ ] 5.1 Write docs-only phase planning checkpoint.
- [ ] 5.2 Harden report/takedown, visibility, and character output safety checks.
- [ ] 5.3 Add admin moderation UI improvements only after using `impeccable` if Web scope is approved.
- [ ] 5.4 Add takedown, reporter privacy, visibility, safety, ACL, and no-leak tests.
- [ ] 5.5 Run targeted tests, full local gate, OpenSpec validation, and `git diff --check`.
- [ ] 5.6 Fast-forward merge to local main and update harness docs.

## 6. Phase 5 — Import/Export Stability

- [ ] 6.1 Write docs-only phase planning checkpoint.
- [ ] 6.2 Implement package export/import roundtrip stability and manifest validation.
- [ ] 6.3 Add import/export UI improvements only after using `impeccable` if Web scope is approved.
- [ ] 6.4 Add roundtrip, sample package repeatability, no-secret, no-storage-path, and preview/apply tests.
- [ ] 6.5 Run targeted tests, full local gate, OpenSpec validation, and `git diff --check`.
- [ ] 6.6 Fast-forward merge to local main and update harness docs.

## 7. Phase 6 — Provider Reliability Layer

- [ ] 7.1 Write docs-only phase planning checkpoint.
- [ ] 7.2 Implement health trend, degraded mode, manual retry/requeue, and fallback/model switch policy.
- [ ] 7.3 Add provider reliability UI only after using `impeccable` if Web scope is approved.
- [ ] 7.4 Add degraded mode, retry, fallback, quota, audit, and no-hidden-spend tests.
- [ ] 7.5 Run targeted tests, full local gate, OpenSpec validation, and `git diff --check`.
- [ ] 7.6 Fast-forward merge to local main and update harness docs.

## 8. Phase 7 — User-facing Polish

- [ ] 8.1 Write docs-only phase planning checkpoint.
- [ ] 8.2 Use `impeccable` to shape the approved polish scope before UI edits.
- [ ] 8.3 Improve loading, error, mobile, playback, onboarding copy, feedback affordances, and accessibility.
- [ ] 8.4 Add Web unit/e2e/a11y/responsive checks as appropriate.
- [ ] 8.5 Run targeted tests, full local gate, OpenSpec validation, and `git diff --check`.
- [ ] 8.6 Fast-forward merge to local main and update harness docs.

## 9. Phase 8 — Release Candidate Gate

- [ ] 9.1 Write docs-only phase planning checkpoint.
- [ ] 9.2 Implement release-candidate evidence aggregation using existing readiness/eval frameworks.
- [ ] 9.3 Add RC report UI only after using `impeccable` if Web scope is approved.
- [ ] 9.4 Add pass/fail, backup, stress, moderation, packaging, provider reliability, UX evidence, and no-leak tests.
- [ ] 9.5 Run targeted tests, full local gate, OpenSpec validation, and `git diff --check`.
- [ ] 9.6 Fast-forward merge to local main and update harness docs.

## 10. Closeout

- [ ] 10.1 Archive the completed OpenSpec change only after all phases are accepted.
- [ ] 10.2 Generate v1.1 release notes.
- [ ] 10.3 Confirm main is clean and report ahead/behind origin.
