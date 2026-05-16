# Design — v0.8 Public Experience & Ecosystem

## Context

Noveland has completed the backend multimodal foundation, operator/admin UX, authoring/import studio, runtime narrative quality APIs, and production hardening locally. v0.6 and v0.7 remain active OpenSpec changes until archived, so their implemented behavior is represented by their active change docs, harness records, and current repository code.

v0.8 is the first roadmap section that intentionally exposes reader/player and ecosystem-facing surfaces. The main risk is not implementation difficulty; it is accidentally reusing admin/member DTOs in public contexts and leaking storage paths, secrets, raw prompts, raw outputs, hidden media, or worldline-private state.

## Goals

- Define a current-repo-aligned v0.8 implementation sequence.
- Keep all reader/player/public surfaces behind explicit safe DTOs, visibility checks, and ACL rules.
- Reuse existing media, provider, invocation, multimodal, player, plugin, diagnostic, and readiness systems.
- Make the first implementation phase API/backend-first so UI phases depend on stable reader-safe contracts.
- Preserve the completed Phase 13 and v0.7 architecture guardrails.

## Non-Goals

- Bypassing v0.7 internal production readiness.
- Exposing hidden or `developer_only` media to readers.
- Exposing resolved provider secrets.
- Exposing `storage_uri`, filesystem paths, bytes, base64, raw prompts, or raw outputs.
- Adding provider marketplace, streaming, runtime daemon execution, or automatic provider spend.
- Adding broad new routes to `worlds.py`.
- Replacing existing media/provider/eval/readiness frameworks.

## Accepted Planning Decisions

- v0.8 implementation must start with a feasibility and public/read-only contract checkpoint.
- Reader Media Delivery is backend/API-first and must precede playback and galgame UI work.
- The first reader media implementation should prefer application-controlled delivery or opaque short-lived tokens over external public storage URLs unless a later design explicitly accepts external delivery.
- Conversation Playback UI and Scene View / Galgame View must consume reader-safe media descriptors and presentation DTOs; they must not read `MediaObjectRecord.storage_uri` or admin media DTOs.
- Player Interaction UI must reuse existing `PlayerChoiceRecord`, `PlayerJournalEntry`, `InWorldNotification`, and `PlayerInterventionRecord` semantics.
- Worldline Browser starts as read-only browse/compare. Destructive rollback or switch execution requires explicit phase-level approval.
- World Packaging uses preview/apply discipline and excludes secrets, internal paths, raw prompt/output evidence, and resolved provider config.
- Plugin/Provider Package Contract builds on the plugin catalog, plugin binding validation, provider registry, provider capabilities, and `ProviderSecretResolver`.
- Moderation & Incident Workflow uses a dedicated `moderation` package and `moderation.py` router for persisted reports, actions, and incident workflow records. It reuses v0.7 observability evidence concepts but does not extend observability into workflow ownership.
- Public Launch Gate builds on v0.7 `ProductionReadinessGateService` and must not replace internal production readiness.

## Architecture Guardrails

- No `storage_uri`, filesystem path, bytes, base64, raw prompt, or raw output in `world_events.payload`.
- No resolved provider secret in API responses, diagnostics, prompt snapshots, health metadata, logs, package manifests, or public exports.
- Strict worldline isolation for visual bindings, conversation presentations, player records, narrative publications, package contents, and reader DTOs.
- Provider outputs do not directly mutate public world state.
- Media assets are not narrative artifacts.
- ComfyUI remains optional provider, not a core dependency.
- Asset generation remains admin apply only unless a later accepted OpenSpec change changes it.
- Reader/player-facing routes do not expose admin/developer-only evidence.

## Risks / Trade-Offs

- Public media delivery can leak internal object paths if it reuses admin download responses. Mitigation: define reader-safe media descriptors and delivery policy first.
- UI work can accidentally couple to unstable backend contracts. Mitigation: place Reader Media Delivery before playback and galgame UI.
- Plugin packaging can blur into marketplace behavior. Mitigation: keep v0.8 to package metadata, validation, and safety review.
- Moderation can become a large governance subsystem. Mitigation: require an architecture decision before adding schema or routes.
- Public launch can outpace readiness evidence. Mitigation: aggregate v0.7 internal readiness and add public-specific blockers.

## Migration Plan

This roadmap update adds no migrations. Future implementation phases must declare migration needs in their phase checkpoint. If a phase discovers a schema need not anticipated by the checkpoint, stop and update OpenSpec/harness docs before implementation continues.

## Open Questions Before Implementation

- Is first-cut reader media delivery authenticated-reader/member-only, public unauthenticated, or mixed by visibility policy?
- Should delivery use application streaming, opaque short-lived media tokens, or both?
- Which existing media/publication visibility fields are authoritative for reader media access?
- Resolved for Phase 10: moderation records live in a dedicated package/router; observability remains derived diagnostics/readiness.
