# Provider Fallback Runbook

## Purpose

Operate degraded mode, manual retry/requeue, and future provider fallback safely without hidden spend or world corruption.

## Scope

Use this when a provider is degraded and an operator considers retrying, requeueing, switching models, or using an alternative provider.

## Immediate Actions

1. Confirm fallback is not automatic by default. If no explicit opt-in policy exists, stay in degraded mode.
2. Check provider health and quota before any manual retry:
   ```sh
   curl -sS http://127.0.0.1:8000/provider-profiles/health \
     -H "Cookie: noveland_session=<admin-session>"
   curl -sS http://127.0.0.1:8000/worlds/<world-id>/providers/quota-status \
     -H "Cookie: noveland_session=<admin-session>"
   ```
3. For media jobs, retry only eligible failed or cancelled jobs through media job controls.
4. For provider smoke/model lab checks, use fake/mocked paths by default. Use the provider lab worktree only for explicit real-provider validation.
5. If fallback is approved in a later phase, verify capability compatibility, quota budget, auth reference availability, and audit recording before execution.

## Evidence To Collect

- Primary provider id, fallback provider id if approved, capability key, model name, quota state, health state, invocation id, and media job id.
- Opt-in policy evidence and audit refs.
- Whether degraded mode was shown to admins and player-safe UI.

## Redaction Rules

Do not record resolved secrets, storage paths, raw prompts, raw outputs, bytes, base64, invite tokens, provider credentials, prompt snapshot internals, or local model paths.

## Escalation

- If fallback would bypass quota, stop and file a blocker.
- If fallback would change world state without reviewable evidence, stop and file a blocker.
- If retries can create duplicate hidden spend, keep provider workflows degraded and defer to Phase 6 provider reliability work.

## Closeout

Confirm the final status is degraded, recovered, or explicitly deferred; record safe audit refs and any remaining manual steps.
