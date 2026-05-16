# Proposal — v0.8 Public Experience & Ecosystem

## Why

v0.7 completed the internal production-hardening baseline: ACL regression, secret/provider governance, cost/rate controls, storage integrity, deployment profile docs, incident diagnostics, security regression, and internal production readiness. Noveland can now plan reader/player-facing experiences and ecosystem packaging, but those surfaces need a stricter public/read-only contract than the admin/member APIs built so far.

## What Changes

- Align the v0.8 roadmap with the completed v0.7 baseline and current repository capabilities.
- Keep v0.8 as an OpenSpec roadmap change with 11 independently implementable phases.
- Require a feasibility and public/read-only contract checkpoint before the first implementation phase.
- Make Reader Media Delivery the dependency for conversation playback and galgame scene view.
- Explicitly reuse existing player records, media/provider/invocation/eval frameworks, plugin catalog/bindings, multimodal presentation records, and v0.7 production readiness.
- Preserve Phase 13 and v0.7 architecture guardrails while planning future implementation.

This proposal does not change current runtime behavior.

## Capabilities

### New Capabilities

- `reader-media-delivery`: Provide reader-safe media descriptors and delivery without leaking `storage_uri`, filesystem paths, bytes, base64, prompts, outputs, or secrets.
- `conversation-playback-ui`: Render published conversation/presentation playback using reader-safe media and turn presentation DTOs.
- `player-interaction-ui`: Expose player choices, interventions, journals, notifications, and route feedback by reusing existing player records.
- `worldline-browser`: Support authorized branch viewing and read-only comparison without unsafe rollback.
- `scene-view-galgame-view`: Provide a basic galgame reading surface over safe presentation and media records.
- `player-privacy-data-controls`: Support export/delete-request workflows with shared-world safeguards.
- `world-packaging`: Define safe world/media manifests, import preview, and import apply.
- `plugin-provider-package-contract`: Define package metadata, capability declaration, config export, and safety review without secrets.
- `sample-world-release-package`: Package a demonstrable sample world linked to the Phase 13 regression fixture.
- `moderation-incident-workflow`: Support report review, disable actions, rollback review, and incident evidence without automatic moderation.
- `public-launch-gate`: Aggregate v0.7 internal production readiness with public, privacy, moderation, and sample-world readiness.

### Modified Capabilities

- None.

## Impact

- Future backend, Web, docs, and test work will be driven by this change's `phase-plan.md`, `tasks.md`, and capability specs.
- Implementation phases must start from a docs-only planning checkpoint, run targeted tests and the full local gate, and fast-forward merge to clean local `main`.
- Current implementation behavior is unchanged by this plan update.
