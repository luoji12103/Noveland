# Worldline Restore Runbook

## Purpose

Recover a worldline from snapshot, replay, backup, or reviewable repair evidence without cross-worldline contamination.

## Scope

Use this when a worldline has inconsistent state, failed session resume, broken presentations, unsafe content repair, or suspected cross-world/worldline leakage.

## Immediate Actions

1. Inspect snapshot integrity:
   ```sh
   curl -sS http://127.0.0.1:8000/worlds/<world-id>/snapshots/integrity \
     -H "Cookie: noveland_session=<admin-session>"
   ```
2. Inspect recent safe event audit rows:
   ```sh
   curl -sS "http://127.0.0.1:8000/worlds/<world-id>/events?limit=20" \
     -H "Cookie: noveland_session=<admin-session>"
   ```
3. Check affected player session resume state:
   ```sh
   curl -sS http://127.0.0.1:8000/worlds/<world-id>/player-sessions/resume \
     -H "Cookie: noveland_session=<tester-session>"
   ```
4. If content repair is needed, create or review an authoring proposal. Do not mutate persona, memory, visual, voice, provider, or dialogue state directly.
5. If full restore is needed, use the backup restore runbook and preserve safe evidence refs before restore.

## Evidence To Collect

- World id, worldline id, snapshot id, covered event sequence, conversation id, player session id, presentation id, and safe failure status.
- Whether affected memory, persona, media, feedback, and repair proposals are scoped to the same worldline.
- Readiness blocker or QA finding ids.

## Redaction Rules

Do not record resolved secrets, storage paths, raw prompts, raw outputs, bytes, base64, invite tokens, provider credentials, prompt snapshot internals, or local model paths.

## Escalation

- If replay integrity fails, stop player access for the affected worldline until the cause is known.
- If a repair proposal would bypass review/apply, stop and add an OpenSpec checkpoint.
- If contamination crosses worlds, treat it as a release-candidate blocker.

## Closeout

Confirm snapshot integrity, player session resume, media/presentation readiness, and QA findings are clear for the restored worldline.
