# Tasks — v0.8 Public Experience & Ecosystem

Use these tasks when implementation is explicitly requested. Planning tasks may be marked complete during roadmap alignment; implementation tasks must only be marked complete after code, tests, local gate, fast-forward merge, and harness updates are done.

## Planning / Preflight

- [x] Confirm v0.7 Production Hardening local acceptance state.
- [x] Review current repository capabilities against the original v0.8 roadmap.
- [x] Add v0.8 feasibility/adaptation review to harness docs.
- [x] Update v0.8 OpenSpec proposal/design/phase-plan/specs for the current baseline.

## Phase 1 — Reader Media Delivery

- [x] Write docs-only phase planning checkpoint.
- [x] Decide first-cut reader media auth model and delivery mechanism.
- [x] Inventory current admin/member media download and narrative reader routes.
- [x] Implement reader-safe media descriptors and delivery policy only.
- [x] Add focused API, ACL, visibility, and leak tests.
- [x] Run targeted tests.
- [x] Run full local gate.
- [x] Fast-forward merge to local main.
- [x] Update OpenSpec tasks and harness docs.

## Phase 2 — Conversation Playback UI

- [x] Write docs-only phase planning checkpoint.
- [x] Confirm Phase 1 reader media descriptors are stable.
- [x] Implement playback UI over safe presentation DTOs only.
- [x] Add component and e2e playback smoke tests.
- [x] Run targeted tests.
- [x] Run full local gate.
- [x] Fast-forward merge to local main.
- [x] Update OpenSpec tasks and harness docs.

## Phase 3 — Player Interaction UI

- [x] Write docs-only phase planning checkpoint.
- [x] Map UI workflows to existing player choice, journal, notification, and intervention records.
- [x] Implement player interaction UI without a new player record framework.
- [x] Add UI, API, ACL, and spoiler/leak tests.
- [x] Run targeted tests.
- [x] Run full local gate.
- [x] Fast-forward merge to local main.
- [x] Update OpenSpec tasks and harness docs.

## Phase 4 — Worldline Browser

- [x] Write docs-only phase planning checkpoint.
- [x] Define read-only worldline browser DTOs and ACL expectations.
- [x] Implement browsing/comparison without rollback execution.
- [x] Add worldline isolation, ACL, and UI tests.
- [x] Run targeted tests.
- [x] Run full local gate.
- [x] Fast-forward merge to local main.
- [x] Update OpenSpec tasks and harness docs.

## Phase 5 — Scene View / Galgame View

- [x] Write docs-only phase planning checkpoint.
- [x] Confirm Phase 1 and Phase 2 safe media/playback contracts are sufficient.
- [x] Implement scene view over presentation records and reader media descriptors.
- [x] Add responsive, accessibility, component, and e2e tests.
- [x] Run targeted tests.
- [x] Run full local gate.
- [x] Fast-forward merge to local main.
- [x] Update OpenSpec tasks and harness docs.

## Phase 6 — Player Privacy & Data Controls

- [x] Write docs-only phase planning checkpoint.
- [x] Decide export/delete request schema and shared-world safeguards.
- [x] Implement player data export/delete-request workflow only.
- [x] Add privacy, ACL, export-redaction, and request-review tests.
- [x] Run targeted tests.
- [x] Run full local gate.
- [x] Fast-forward merge to local main.
- [x] Update OpenSpec tasks and harness docs.

## Phase 7 — World Packaging

- [x] Write docs-only phase planning checkpoint.
- [x] Define safe bundle and media manifest schemas.
- [x] Implement export, import preview, and reviewed apply.
- [x] Add manifest, import/export, compatibility, and leak tests.
- [x] Run targeted tests.
- [x] Run full local gate.
- [x] Fast-forward merge to local main.
- [x] Update OpenSpec tasks and harness docs.

## Phase 8 — Plugin/Provider Package Contract

- [ ] Write docs-only phase planning checkpoint.
- [ ] Define package metadata, capability, config export, and safety review contracts.
- [ ] Implement contract validation without marketplace or untrusted-code installation.
- [ ] Add plugin/provider governance and secret-redaction tests.
- [ ] Run targeted tests.
- [ ] Run full local gate.
- [ ] Fast-forward merge to local main.
- [ ] Update OpenSpec tasks and harness docs.

## Phase 9 — Sample World Release Package

- [ ] Write docs-only phase planning checkpoint.
- [ ] Define sample content/media manifest and fixture linkage.
- [ ] Implement deterministic sample package import/export support only.
- [ ] Add sample package, fixture, rights/visibility, and leak tests.
- [ ] Run targeted tests.
- [ ] Run full local gate.
- [ ] Fast-forward merge to local main.
- [ ] Update OpenSpec tasks and harness docs.

## Phase 10 — Moderation & Incident Workflow

- [ ] Write docs-only phase planning checkpoint.
- [ ] Resolve schema/router ownership before implementation.
- [ ] Implement report/review/disable workflow without automatic moderation.
- [ ] Add moderation ACL, evidence-redaction, audit, and rollback-review tests.
- [ ] Run targeted tests.
- [ ] Run full local gate.
- [ ] Fast-forward merge to local main.
- [ ] Update OpenSpec tasks and harness docs.

## Phase 11 — Public Launch Gate

- [ ] Write docs-only phase planning checkpoint.
- [ ] Define public readiness evidence inputs from v0.7 and v0.8 phases.
- [ ] Implement public launch readiness aggregation without duplicate release framework.
- [ ] Add readiness, blocker, ACL, signoff, and evidence-redaction tests.
- [ ] Run targeted tests.
- [ ] Run full local gate.
- [ ] Fast-forward merge to local main.
- [ ] Update OpenSpec tasks and harness docs.
