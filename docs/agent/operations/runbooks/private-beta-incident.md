# Private Beta Incident Runbook

## Purpose

Handle incidents involving invites, tester sessions, beta feedback, reporter privacy, or private beta readiness evidence.

## Scope

Use this when a tester cannot redeem an invite, a revoked or expired invite appears usable, a player session resumes the wrong state, feedback visibility is wrong, or beta evidence leaks admin-only data.

## Immediate Actions

1. Inspect the invite lifecycle with a world-admin or platform-admin session:
   ```sh
   curl -sS http://127.0.0.1:8000/worlds/<world-id>/private-beta/invites \
     -H "Cookie: noveland_session=<admin-session>"
   ```
2. Revoke unsafe invites through the private beta API if needed:
   ```sh
   curl -sS -X POST http://127.0.0.1:8000/worlds/<world-id>/private-beta/invites/<invite-id>/revoke \
     -H "Cookie: noveland_session=<admin-session>; noveland_csrf=<csrf-token>" \
     -H "X-CSRF-Token: <csrf-token>" \
     -H "Content-Type: application/json" \
     --data '{"reason":"incident_response"}'
   ```
3. Check the affected player session resume state with the tester session.
4. Inspect beta feedback only through reporter-owned or admin-triage APIs:
   ```sh
   curl -sS http://127.0.0.1:8000/worlds/<world-id>/beta-feedback/reports \
     -H "Cookie: noveland_session=<admin-session>"
   ```
5. Re-run private beta readiness reports after containment:
   ```sh
   curl -sS http://127.0.0.1:8000/observability/readiness/private-beta \
     -H "Cookie: noveland_session=<admin-session>"
   ```

## Evidence To Collect

- Invite id, invite state, world id, optional worldline id, user id, player actor id, player session id, and feedback report id.
- Whether membership remains least-privilege.
- Whether reporter privacy and admin-only evidence boundaries held.

## Redaction Rules

Do not record resolved secrets, storage paths, raw prompts, raw outputs, bytes, base64, invite tokens, provider credentials, prompt snapshot internals, or local model paths.

## Escalation

- If invite token plaintext was logged or exposed, treat it as a security incident and revoke affected invites.
- If testers can see other testers' feedback or sessions, stop beta access for the affected world.
- If a tester can access admin/provider/media/invocation diagnostics, stop normal-use testing and file a release-candidate blocker.

## Closeout

Confirm revoked/expired invites cannot be redeemed, player sessions are isolated, feedback privacy is intact, and private beta readiness evidence is safe.
