# Secret Rotation Runbook

## Purpose

Rotate provider, memory backend, or local service secrets while preserving safe `auth_ref` references and avoiding secret leakage.

## Scope

Use this when credentials are expired, suspected compromised, or changing providers during normal-use validation.

## Immediate Actions

1. Identify affected references only by safe key names, such as `auth_ref`, `api_key_ref`, or profile id.
2. Disable or pause affected provider profiles before rotating secrets if active execution is possible.
3. Update local secret storage outside the repository, for example environment variables or local secret JSON.
4. Restart local API/runtime processes that read the changed environment.
5. Run safe health checks:
   ```sh
   curl -sS http://127.0.0.1:8000/provider-profiles/health \
     -H "Cookie: noveland_session=<admin-session>"
   ```
6. For world-scoped provider integrations, verify provider health and quota status before re-enabling spend paths.

## Evidence To Collect

- Secret reference key, provider profile id, affected world/provider integration ids, rotation timestamp, and safe health status.
- Confirmation that provider config exports preserve `auth_ref` only and exclude resolved secret values.
- Any failed jobs or invocations caused by the old credential.

## Redaction Rules

Do not record resolved secrets, storage paths, raw prompts, raw outputs, bytes, base64, invite tokens, provider credentials, prompt snapshot internals, or local model paths.

## Escalation

- If a resolved secret appears in logs, docs, tickets, event payloads, prompt snapshots, or API responses, treat it as a security incident.
- If provider config export includes resolved secret values, stop import/export work and file a blocker.
- If rotation breaks model discovery or smoke tests, follow provider outage after confirming the new reference is present.

## Closeout

Confirm the old credential is revoked outside Noveland, health checks pass or are intentionally disabled, quota remains enforced, and no committed file contains the secret.
