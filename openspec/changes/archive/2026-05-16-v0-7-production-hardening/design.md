# Design — v0.7 Production Hardening

## Context

Noveland now has a broad local beta surface: provider execution and smoke tests, media/image/speech pipelines, strict-worldline visual state, conversation turn presentations, admin asset generation proposals, multimodal eval diagnostics, v0.4 admin consoles, v0.5 authoring/import proposal workflows, and v0.6 narrative quality APIs.

v0.7 should not add new gameplay or authoring features. It should harden the operational boundaries that already exist so the system can run longer with clearer permissions, safer provider governance, bounded spend, verifiable storage, repeatable deployment, and regression evidence.

Current `openspec/specs/` files describe implemented behavior through the archived v0.4/v0.5 specs and the current Phase 3-13 baseline. The v0.6 change is locally complete and ready to archive, but this v0.7 planning update does not archive it.

## Goals / Non-Goals

Goals:

- Define a concrete v0.7 hardening architecture after v0.6 completion.
- Keep v0.7 in 8 independently implementable, testable, mergeable phases.
- Prefer API/test/docs-first hardening. Web dashboard work is optional later work, not required for the first backend hardening phases.
- Preserve the Phase 13 architecture freeze and the v0.4-v0.6 package/router boundaries.
- Make every phase produce targeted regression evidence before it can merge.

Non-goals:

- Large new gameplay features
- Player-facing public launch
- Provider marketplace
- Streaming
- Expanded automatic content generation
- Full external observability exporter
- Full vault/KMS or encrypted DB secret storage unless a later explicit decision accepts it
- Broad new routes in `worlds.py`

## Decisions

- Harden existing boundaries before broad public exposure.
- Keep v0.7 internal-readiness focused. It is not a public launch gate.
- Start implementation with permission matrix and route ACL regression coverage because v0.4-v0.6 added many admin-only APIs.
- Keep provider governance tied to `ProviderSecretResolver`, provider status, provider health checks, and invocation ledger evidence. Do not store resolved secrets.
- Apply cost/rate controls at provider execution, media job, asset generation, and narrative quality provider-backed generation boundaries.
- Reuse `model_invocations`, `prompt_snapshots`, `media_jobs`, `asset_generation_policies`, provider health checks, multimodal evals, and runtime diagnostics rather than creating parallel audit systems.
- Reuse existing package boundaries where they are already clear: `auth`, `providers`, `media`, `storage`, `observability`, `multimodal_eval`, `narrative_quality`, and API authorization dependencies.
- Avoid expanding `worlds.py` and avoid turning `runtime.py` into a general production-hardening router. If a cross-cutting readiness API cannot fit existing bounded routers, stop for an explicit architecture decision on a dedicated production-hardening package/router.
- Prefer backup/restore drills and regression tests over unchecked operational assumptions.

## Architecture Guardrails

- no storage_uri/path/base64/bytes in `world_events.payload`
- no raw prompt/output in `world_events.payload`
- no resolved provider secret exposure
- strict worldline visual state
- provider output does not directly mutate world state
- media assets are not narrative artifacts
- ComfyUI remains optional provider, not a core dependency
- asset generation remains admin apply only unless a future accepted OpenSpec change changes it
- conversation presentation remains API-only until a specific UI phase implements it
- no runtime daemon auto-generation unless a future accepted OpenSpec change changes it
- reader/player-facing routes do not expose admin/developer-only data
- admin diagnostics may expose safe evidence refs and aggregate counts, not raw prompts, resolved secrets, storage paths, bytes, base64, or unsafe payload snapshots

## Boundary Strategy

Use existing ownership boundaries first:

- Permission hardening: `noveland.auth`, API authorization dependencies, router tests, and Web route guards.
- Provider governance: `noveland.providers`, `ProviderSecretResolver`, provider router, health checks, and invocation ledger metadata.
- Cost/rate control: provider execution service, media jobs, asset generation policies, narrative quality provider-backed generation, and model invocation cost metadata.
- Object storage/backup: `noveland.storage`, `noveland.media.storage`, media objects, snapshot object storage, and existing backup/restore docs.
- Observability: `noveland.observability`, runtime diagnostics, provider/media/eval diagnostics, and safe evidence refs.
- Production readiness: existing beta/release/eval records where suitable.

## Risks / Trade-offs

- Hardening can block feature work: scope each phase to one operational risk class and merge only after local gate evidence.
- Permission hardening can break existing operator workflows: start with an explicit matrix and route tests before changing behavior.
- Secret governance can become a vault project: keep vault/KMS as a future decision unless implementation proves existing env/auth_ref boundaries are insufficient.
- Cost controls can create hidden execution failures: blocked execution must return actionable safe errors and safe audit evidence.
- Remote object storage can become cloud lock-in: first version should abstract the interface and prove backup/integrity behavior without requiring one cloud provider.
- Production gates can be mistaken for public launch: keep v0.7 internal readiness only.

## Migration Plan

This planning revision does not add migrations. Future implementation phases must explicitly propose migrations when schema changes are required and must stop if phase plans and migration needs conflict.

Expected migration pressure:

- Permission model hardening: likely no migration if existing platform roles and world memberships are sufficient; stop if new role tables are needed.
- Provider governance: may need audit records; first attempt should reuse provider health checks/model invocation metadata if sufficient.
- Cost/rate control: likely needs persisted policy records unless existing asset generation policies can cover the first scope.
- Object storage/backup: prefer no migration for storage adapter abstraction; stop if object schema changes are required.
- Production readiness gate: prefer reuse of `BetaChecklistRun`, `LongRunEvalRun`, release profiles, and diagnostics.

## Open Questions Before Implementation

- Should cross-cutting v0.7 readiness APIs get a dedicated `production_hardening` package/router, or should each phase stay inside existing bounded routers only?
- Should provider governance introduce a new audit table, or can provider health checks plus model invocation metadata cover the first accepted scope?
- Should cost/rate control be persisted as a new policy table, or should the first phase reuse `asset_generation_policies` plus provider/default config?
- Should Web admin status surfaces be deferred entirely until after backend hardening APIs stabilize?
