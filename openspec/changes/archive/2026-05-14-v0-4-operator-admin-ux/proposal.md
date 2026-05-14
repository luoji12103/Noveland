# Proposal — v0.4 Operator/Admin UX

## Why

Turn the Phase 3-13 backend substrate into controlled admin/operator surfaces for configuration, inspection, troubleshooting, and acceptance.

## What Changes

- Save v0.4 as an OpenSpec roadmap change with 7 independently implementable phases.
- Define phase goals, scope, non-goals, reused systems, acceptance criteria, stop conditions, validation, and deliverables.
- Add capability delta specs for each planned capability.
- Preserve Phase 13 architecture freeze boundaries while planning future implementation.

## Capabilities

### New Capabilities
- `admin-ux-foundation`: Unify admin layout, route guards, shared states, API client conventions, and table/detail/action patterns.
- `provider-admin-console`: Manage provider integrations, adapter_kind, capabilities, health checks, and smoke tests.
- `media-admin-console`: Manage media assets, objects, jobs, and references with upload, download, verification, and status inspection.
- `visual-admin-console`: Manage character sprites, expression variants, backgrounds, and scene compose preview.
- `speech-admin-console`: Manage voice profiles, agent bindings, style mappings, transcripts, and TTS/STT test actions.
- `invocation-ledger-browser`: Allow admins to inspect model invocation records, prompt snapshots, tags, redaction, visibility, and retention state.
- `multimodal-diagnostics-dashboard`: Visualize Phase 12 multimodal diagnostic results.

### Modified Capabilities
- None.

## Impact

- Future backend, Web, docs, and test work will be driven by this change's `phase-plan.md`, `tasks.md`, and capability specs.
- Current implementation behavior is unchanged by this roadmap skeleton.
- Future implementation phases must run targeted tests and the full local gate before merge.
