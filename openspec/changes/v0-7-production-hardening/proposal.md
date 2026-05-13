# Proposal — v0.7 Production Hardening

## Why

Move local beta capabilities toward long-running production-like operation with stronger permissions, secret governance, budgets, backups, observability, and security regression.

## What Changes

- Save v0.7 as an OpenSpec roadmap change with 8 independently implementable phases.
- Define phase goals, scope, non-goals, reused systems, acceptance criteria, stop conditions, validation, and deliverables.
- Add capability delta specs for each planned capability.
- Preserve Phase 13 architecture freeze boundaries while planning future implementation.

## Capabilities

### New Capabilities
- `permission-model-hardening`: Establish owner/admin/member/reader/player permission matrix.
- `secret-provider-governance`: Support secret rotation, provider disable, provider audit, and provider-scoped permissions.
- `cost-rate-control`: Add per-world budgets, per-provider budgets, media generation budgets, emergency stop, and quota status.
- `object-storage-backup-v2`: Define S3/GCS-compatible abstraction, backup/restore drill, checksum audit, and object lifecycle policy.
- `deployment-profile`: Define production compose/profile, health endpoints, migration procedure, and operator docs.
- `observability-incident-diagnostics`: Expose provider/media/runtime/eval dashboards, failure replay, and diagnostic retention.
- `security-regression-suite`: Add regression coverage for secret leak, prompt leak, storage_uri/path leak, ACL leak, and worldline isolation.
- `production-readiness-gate`: Create an internal readiness gate distinct from public launch readiness.

### Modified Capabilities
- None.

## Impact

- Future backend, Web, docs, and test work will be driven by this change's `phase-plan.md`, `tasks.md`, and capability specs.
- Current implementation behavior is unchanged by this roadmap skeleton.
- Future implementation phases must run targeted tests and the full local gate before merge.
