# Quota Exhaustion Runbook

## Purpose

Recover from world, provider, player, or capability quota exhaustion while preventing hidden provider spend.

## Scope

Use this when provider execution, image generation, TTS, ASR, visual generation, asset generation, model lab smoke tests, or player sessions report quota-exceeded or emergency-stop states.

## Immediate Actions

1. Check world/provider quota state:
   ```sh
   curl -sS http://127.0.0.1:8000/worlds/<world-id>/providers/quota-status \
     -H "Cookie: noveland_session=<admin-session>"
   ```
2. Confirm player-safe behavior for impacted testers:
   ```sh
   curl -sS http://127.0.0.1:8000/worlds/<world-id>/player-sessions/resume \
     -H "Cookie: noveland_session=<tester-session>"
   ```
3. Inspect provider budget policies without changing them:
   ```sh
   curl -sS http://127.0.0.1:8000/worlds/<world-id>/providers/budget-policies \
     -H "Cookie: noveland_session=<admin-session>"
   ```
4. Pause optional generation jobs if quota failures are blocking normal play:
   ```sh
   curl -sS "http://127.0.0.1:8000/worlds/<world-id>/media/jobs?status=queued" \
     -H "Cookie: noveland_session=<admin-session>"
   ```
5. Do not raise quotas until the failure source and impacted player scope are known.

## Evidence To Collect

- World id, provider id, capability key, player actor id if known, quota policy id, and safe quota counts.
- Whether an emergency stop is active.
- Whether provider execution was blocked before secret resolution and adapter execution.
- Related media job ids, model invocation ids, and player session ids.

## Redaction Rules

Do not record resolved secrets, storage paths, raw prompts, raw outputs, bytes, base64, invite tokens, provider credentials, prompt snapshot internals, or local model paths.

## Escalation

- If quota was exhausted by a tester workflow, keep the tester in degraded mode and triage feedback before changing policy.
- If quota was exhausted by a background job, cancel or retry only through existing media/job controls.
- If quota enforcement appears advisory rather than pre-call, stop normal-use testing and file a blocker.

## Closeout

Confirm quota status is understood, no hidden retries are active, player UI shows a safe degraded/quota state, and any policy change is recorded in the change journal.
