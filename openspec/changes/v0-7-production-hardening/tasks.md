# Tasks — v0.7 Production Hardening

Use these tasks when implementation is explicitly requested. Do not mark items complete during roadmap-only work.

## Phase 1 — Permission Matrix & ACL Regression Baseline

- [x] Write phase planning checkpoint.
- [x] Implement `permission-model-hardening` scope only.
- [x] Document the current platform-admin/world-admin/world-member/reader/player route matrix.
- [x] Add or update route ACL and lower-privilege leak regression coverage.
- [x] Preserve Phase 13 architecture guardrails.
- [x] Add or update focused tests.
- [x] Run targeted tests.
- [x] Run full local gate.
- [x] Fast-forward merge to local main.
- [x] Update OpenSpec tasks and harness docs.

## Phase 2 — Secret & Provider Governance

- [x] Write phase planning checkpoint.
- [x] Implement `secret-provider-governance` scope only.
- [x] Confirm disabled providers are blocked across provider, image, speech, narrative quality, and smoke-test execution paths.
- [x] Confirm auth_ref rotation never stores or returns resolved secret values.
- [x] Preserve Phase 13 architecture guardrails.
- [x] Add or update focused tests.
- [x] Run targeted tests.
- [x] Run full local gate.
- [x] Fast-forward merge to local main.
- [x] Update OpenSpec tasks and harness docs.

## Phase 3 — Cost & Rate Control

- [x] Write phase planning checkpoint.
- [x] Implement `cost-rate-control` scope only.
- [x] Define budget/quotas for provider execution, media jobs, asset generation, and provider-backed narrative quality generation.
- [x] Ensure budget blocks happen before external provider calls and produce safe evidence.
- [x] Preserve Phase 13 architecture guardrails.
- [x] Add or update focused tests.
- [x] Run targeted tests.
- [x] Run full local gate.
- [x] Fast-forward merge to local main.
- [x] Update OpenSpec tasks and harness docs.

## Phase 4 — Object Storage & Backup v2

- [x] Write phase planning checkpoint.
- [x] Implement `object-storage-backup-v2` scope only.
- [x] Audit media object and snapshot storage integrity without exposing filesystem paths.
- [x] Update backup/restore drill docs and local verification entrypoint if needed.
- [x] Preserve Phase 13 architecture guardrails.
- [x] Add or update focused tests.
- [x] Run targeted tests.
- [x] Run full local gate.
- [x] Fast-forward merge to local main.
- [x] Update OpenSpec tasks and harness docs.

## Phase 5 — Deployment Profile

- [x] Write phase planning checkpoint.
- [x] Implement `deployment-profile` scope only.
- [x] Document production-like local/single-host profile, health checks, migration procedure, and rollback prerequisites.
- [x] Validate deployment profile commands without introducing managed-cloud lock-in.
- [x] Preserve Phase 13 architecture guardrails.
- [x] Add or update focused tests.
- [x] Run targeted tests.
- [x] Run full local gate.
- [x] Fast-forward merge to local main.
- [x] Update OpenSpec tasks and harness docs.

## Phase 6 — Observability & Incident Diagnostics

- [x] Write phase planning checkpoint.
- [ ] Implement `observability-incident-diagnostics` scope only.
- [ ] Reuse runtime diagnostics, provider health, model invocation, media job, multimodal eval, and narrative quality evidence.
- [ ] Ensure incident reports expose safe evidence refs only.
- [ ] Preserve Phase 13 architecture guardrails.
- [ ] Add or update focused tests.
- [ ] Run targeted tests.
- [ ] Run full local gate.
- [ ] Fast-forward merge to local main.
- [ ] Update OpenSpec tasks and harness docs.

## Phase 7 — Security Regression Suite

- [ ] Write phase planning checkpoint.
- [ ] Implement `security-regression-suite` scope only.
- [ ] Consolidate secret, prompt/output, storage/path, ACL, and worldline isolation regression fixtures.
- [ ] Extend Phase 13 and v0.5/v0.6 regression coverage where useful.
- [ ] Preserve Phase 13 architecture guardrails.
- [ ] Add or update focused tests.
- [ ] Run targeted tests.
- [ ] Run full local gate.
- [ ] Fast-forward merge to local main.
- [ ] Update OpenSpec tasks and harness docs.

## Phase 8 — Production Readiness Gate

- [ ] Write phase planning checkpoint.
- [ ] Implement `production-readiness-gate` scope only.
- [ ] Reuse beta checklist, long-run eval, release profile, multimodal eval, narrative quality, diagnostics, and v0.7 hardening evidence.
- [ ] Keep readiness gate internal and distinct from public launch readiness.
- [ ] Preserve Phase 13 architecture guardrails.
- [ ] Add or update focused tests.
- [ ] Run targeted tests.
- [ ] Run full local gate.
- [ ] Fast-forward merge to local main.
- [ ] Update OpenSpec tasks and harness docs.
