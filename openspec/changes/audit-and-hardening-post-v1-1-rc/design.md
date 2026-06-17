## Context

Current `main` has archived v0.9 self-use MVP, v1.0 private beta MVP, and v1.1 normal-use release-candidate work. The implemented system has strong documented boundaries around provider execution, secret resolution, invocation ledger evidence, media storage, world-event payloads, reader/member/player DTOs, worldline isolation, moderation, packaging, and readiness. The remaining risk is drift: implementation, Web proxies, e2e flows, release notes, and specs may no longer fully agree with those boundaries after many phases.

## Goals / Non-Goals

**Goals:**

- Audit backend security first: FastAPI auth/authz, session handling, role boundaries, worldline isolation, provider spend, secret handling, prompt/output redaction, storage/media path exposure, and admin/player/reader/member API separation.
- Audit Web and e2e second: Next route handlers, same-origin proxies, CSRF handling, XSS/client leaks, admin/player boundary, and existing Playwright paths without using browser/computer-use plugins.
- Audit product normal-use flows: onboarding, resume, feedback, quota/degraded provider states, import/export, provider reliability, and v1.1 RC evidence usability.
- Audit spec/history compliance: OpenSpec specs vs implementation, archived v0.9/v1.0/v1.1 changes, release notes, and harness records.
- Fix confirmed issues in small, test-backed batches and keep the feature branch clean between batches where possible.

**Non-Goals:**

- No push unless explicitly requested.
- No direct work on `main` after branch creation.
- No real-provider tests, external provider calls, or quota consumption by default.
- No new provider, media, readiness, moderation, authoring, or packaging framework when an existing owner can be extended.
- No UI implementation before using `impeccable`; no browser/computer-use plugin usage for UI/e2e.
- No broad route growth in `worlds.py`.

## Decisions

### Audit findings drive implementation order

The first implementation batches must be based on concrete findings. High-risk security issues can move directly into remediation once captured in `tasks.md` and supported by an OpenSpec requirement or an existing spec contract. Lower-risk product/spec drift can wait behind security and isolation work.

### Existing owners remain authoritative

Provider spend and fallback stay in `noveland.providers`; media storage and descriptors stay in `noveland.media`/`reader_delivery`; safety actions stay in `noveland.moderation`; repair proposals stay in `noveland.authoring`; readiness evidence stays in `noveland.observability`; world state stays in `noveland.worlds` without turning `worlds.py` into a catch-all router.

### No-leak checks must be explicit

Any remediation that touches API DTOs, Web proxies, readiness reports, package manifests, provider execution, prompt snapshots, events, media, player sessions, or feedback must include tests or targeted inspection for forbidden markers: resolved secrets, auth refs where not allowed, storage URI/path, filesystem path, local model path, raw prompt, raw output, prompt snapshot internals, invite tokens, bytes, and base64.

### Default tests remain fake-provider only

The audit may inspect real-provider lab docs, but it must not set `NOVELAND_RUN_REAL_PROVIDER_TESTS=1` or trigger external provider execution unless the user explicitly authorizes it later.

### Harness records are part of completion

Each fix batch must update the necessary harness files, usually `project-index.md`, `file-inventory.md`, `change-journal.md`, and `handoffs/active-session.md`, so the next agent can reconstruct findings, tests, branch state, and residual risks.

## Risks / Trade-offs

- Audit scope is broad -> Split into backend security, Web/e2e security, product normal-use, and spec/history batches with explicit stop points.
- Fixes can accidentally widen public/player/member data -> Add no-leak and ACL regression tests around every exposed route or DTO touched.
- Full gates can be slow -> Run targeted tests for each batch and attempt full gates when the batch size justifies the cost; record any skipped full gate with reason.
- Spec updates can drift from implementation -> Add or modify spec deltas before behavior changes, then validate OpenSpec strictly.

## Migration Plan

No migration is planned for the audit scaffolding. Any remediation that needs a migration must include a finding-specific design note, migration tests, rollback considerations, and OpenSpec spec delta before implementation.

## Open Questions

- Which backend security finding should be fixed first after the initial audit pass?
- Should later Web/product batches add a dedicated Playwright regression, or are existing e2e paths sufficient after targeted unit coverage?
- Which full-gate subset is practical for each batch on the current server environment?
