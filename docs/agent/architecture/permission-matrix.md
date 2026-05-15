# Permission Matrix

Status: v0.7 Phase 1 baseline

## Roles

- `unauthenticated`: no valid session.
- `platform_admin`: platform operator with global administration privileges.
- `world_admin`: world member with `world_admin` membership.
- `world_member`: world member with non-admin membership.
- `reader`: reader-facing projection only. Current backend reader surfaces are filtered world routes, not a separate public delivery system.
- `player`: player-facing projection only. Current player state is worldline-scoped and must not imply admin evidence access.

## Route Matrix

| Surface | Examples | platform_admin | world_admin | world_member | reader/player | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Health | `GET /health` | allow | allow | allow | allow | No operational evidence beyond service status. |
| Auth | `/auth/*` | own session | own session | own session | own session | Session and CSRF only. |
| World membership reads | selected `/worlds/*` reads | allow | allow scoped | allow scoped | filtered only | Member reads must stay projection-safe. |
| World admin operations | world CRUD/admin mutations | allow | allow scoped | deny | deny | No admin evidence for lower roles. |
| Providers | `/worlds/{world_id}/providers*` | allow | allow scoped except global/developer-only restrictions | deny | deny | `auth_ref` is an opaque reference only; resolved values are never exposed. |
| Model invocations | `/worlds/{world_id}/model-invocations*`, prompt snapshots/templates | allow | allow scoped | deny | deny | Prompt snapshots and raw prompts/outputs are admin evidence. |
| Media admin catalog | `/worlds/{world_id}/media/*` | allow | allow scoped | read visible assets only | no public delivery | Members may read visible assets; private, hidden, objects, jobs, lineage internals stay restricted. |
| Images | `/worlds/{world_id}/images/*` | allow | allow scoped | deny | deny | Provider-backed generation is admin-controlled. |
| Speech admin | `/worlds/{world_id}/speech/*`, `/agents/{agent_id}/voice-binding` | allow | allow scoped | deny | deny | Voice profiles, bindings, TTS/STT, transcripts, and mappings are admin-controlled unless a later public projection is accepted. |
| Visual admin | `/worlds/{world_id}/visual/*` | allow | allow scoped | deny | deny | Strict-worldline visual bindings and compose operations are admin-controlled. |
| Conversation presentations | `/worlds/{world_id}/conversations/{conversation_id}/turns/{turn_id}/presentation*` | allow | allow scoped | deny | deny | Presentation CRUD/render orchestration is backend/API-only admin scope. |
| Asset generation | `/worlds/{world_id}/asset-generation/*`, media job reprioritize/cancel | allow | allow scoped | deny | deny | Proposal/apply and spend-affecting job controls are admin-only. |
| Authoring/import | `/worlds/{world_id}/authoring/*` | allow | allow scoped | deny | deny | Source registry, proposals, review, preview, and apply are admin-only. |
| Multimodal evals | `/worlds/{world_id}/multimodal-evals*`, `/diagnostics/multimodal` | allow | allow scoped | deny | deny | Eval metrics expose admin diagnostics and safe evidence refs only. |
| Narrative quality | `/worlds/{world_id}/narrative-quality/*` | allow | allow scoped | deny | deny | v0.6 quality context, generation, diagnostics, and dashboard APIs are admin-only. |
| Runtime/platform ops | `/runtime/*`, platform admin pages/proxies | allow | deny unless explicitly world-scoped elsewhere | deny | deny | Platform operations require platform admin. |
| Realtime streams | runtime/world/conversation stream routes | role-specific | role-specific | role-specific | filtered only | Streams must follow the same projection rules as the backing routes. |

## Forbidden Lower-Privilege Data

`world_member`, `reader`, and `player` surfaces must not expose:

- resolved provider secrets or request authorization headers;
- prompt snapshots, raw prompts, raw messages, raw requests, raw responses, or raw outputs;
- storage URIs, filesystem paths, public object paths, bytes, or base64 payloads;
- hidden/developer-only provider, media, visual, speech, authoring, eval, or diagnostic evidence;
- admin-only cost, provider, invocation, diagnostics, readiness, or regression evidence unless returned as an accepted safe projection.

## Implementation Rules

- Prefer `get_world_admin_context` for admin-only world routes.
- Prefer `get_world_member_context` only for routes with explicit member-safe projections.
- Platform-only routes must use `require_platform_admin` or equivalent dependency.
- New cross-cutting production-hardening APIs must not be added broadly to `worlds.py`; use existing bounded routers or stop for a dedicated package/router decision.
- ACL fixes should be narrow and backed by route tests.

## Regression Coverage

The v0.7 Phase 1 regression baseline verifies that lower-privilege actors cannot reach high-risk admin surfaces and that denial responses do not leak forbidden data. Later v0.7 phases should extend this matrix instead of redefining it.
