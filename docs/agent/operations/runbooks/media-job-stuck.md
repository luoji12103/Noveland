# Media Job Stuck Runbook

## Purpose

Recover queued, running, failed, or superseded media jobs without exposing media storage internals or duplicating provider spend.

## Scope

Use this when image, TTS, ASR, presentation, visual generation, or asset generation jobs are stale, failed, or blocking playback/readiness.

## Immediate Actions

1. List affected jobs:
   ```sh
   curl -sS "http://127.0.0.1:8000/worlds/<world-id>/media/jobs?worldline_id=<worldline-id>" \
     -H "Cookie: noveland_session=<admin-session>"
   ```
2. Read the specific job:
   ```sh
   curl -sS http://127.0.0.1:8000/worlds/<world-id>/media/jobs/<job-id> \
     -H "Cookie: noveland_session=<admin-session>"
   ```
3. If a queued or running job is superseded, cancel it through the media API:
   ```sh
   curl -sS -X POST http://127.0.0.1:8000/worlds/<world-id>/media/jobs/<job-id>/cancel \
     -H "Cookie: noveland_session=<admin-session>; noveland_csrf=<csrf-token>" \
     -H "X-CSRF-Token: <csrf-token>"
   ```
4. If a failed or cancelled job is eligible and quota allows, retry it explicitly:
   ```sh
   curl -sS -X POST http://127.0.0.1:8000/worlds/<world-id>/media/jobs/<job-id>/retry \
     -H "Cookie: noveland_session=<admin-session>; noveland_csrf=<csrf-token>" \
     -H "X-CSRF-Token: <csrf-token>"
   ```
5. Re-check private beta or RC readiness reports only after job state changes settle.

## Evidence To Collect

- Job id, world id, worldline id, job kind, status, provider id, source invocation id, and safe failure class.
- Associated conversation, turn, presentation, or media asset ids.
- Quota status before any retry.
- Whether player resume shows missing media fallback rather than admin evidence.

## Redaction Rules

Do not record resolved secrets, storage paths, raw prompts, raw outputs, bytes, base64, invite tokens, provider credentials, prompt snapshot internals, or local model paths.

## Escalation

- If a retry would call a real provider, verify quota and operator approval first.
- If jobs repeatedly fail for one provider, follow the provider outage runbook.
- If media payload integrity is suspect, follow the backup/restore or restore drill runbook before retrying generation.

## Closeout

Confirm the job state is terminal or recovered, impacted player surfaces show safe fallback or restored media, and readiness reports no longer list the job as a blocker.
