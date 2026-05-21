# Provider Outage Runbook

## Purpose

Recover from degraded or unavailable LLM, image, TTS, ASR, ComfyUI, or custom gateway providers without exposing credentials or creating hidden spend.

## Scope

Use this when provider health checks, model discovery, model lab smoke tests, runtime diagnostics, media jobs, or player-facing degraded states indicate provider failure.

## Immediate Actions

1. Confirm the failure is provider-scoped, not a local runtime or network outage:
   ```sh
   curl -sS http://127.0.0.1:8000/runtime/status \
     -H "Cookie: noveland_session=<admin-session>"
   ```
2. Check provider health and recent safe diagnostics:
   ```sh
   curl -sS http://127.0.0.1:8000/provider-profiles/health \
     -H "Cookie: noveland_session=<admin-session>"
   ```
3. For world-scoped providers, inspect provider health and quota status:
   ```sh
   curl -sS http://127.0.0.1:8000/worlds/<world-id>/providers/<provider-id>/health-checks \
     -H "Cookie: noveland_session=<admin-session>"
   curl -sS http://127.0.0.1:8000/worlds/<world-id>/providers/quota-status \
     -H "Cookie: noveland_session=<admin-session>"
   ```
4. If player sessions are affected, confirm the player-safe resume state shows degraded or provider failure rather than admin diagnostics:
   ```sh
   curl -sS http://127.0.0.1:8000/worlds/<world-id>/player-sessions/resume \
     -H "Cookie: noveland_session=<tester-session>"
   ```
5. Disable or pause risky real-provider paths through existing provider configuration if failures are causing repeated spend attempts.

## Evidence To Collect

- Provider profile id, provider integration id, provider kind, capability key, model name, and safe health state.
- Quota status, emergency stop state, and whether the failure happened before or after provider execution.
- Related media job ids, invocation ids, or readiness evidence refs.
- Runtime diagnostic event type, severity, and safe error class.

## Redaction Rules

Do not record resolved secrets, storage paths, raw prompts, raw outputs, bytes, base64, invite tokens, provider credentials, prompt snapshot internals, or local model paths.

## Escalation

- If local configuration changed, restart only the affected local API/runtime process and re-check health.
- If a provider is consistently unavailable, use degraded mode and defer opt-in fallback until Phase 6 provider reliability policy permits it.
- Real provider experiments must happen in the provider lab worktree described in `docs/agent/operations/provider-lab.md`.

## Closeout

Confirm runtime status, provider health, quota status, and affected player session recovery states are safe. Record final evidence refs in the active handoff.
