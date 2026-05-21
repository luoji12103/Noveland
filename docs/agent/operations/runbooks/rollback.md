# Rollback Runbook

## Purpose

Return a local/single-host environment to a known good application, database, and media state after a failed normal-use change.

## Scope

Use this after failed migrations, unsafe release-candidate gates, severe provider reliability regressions, import/export corruption, or failed backup/restore drill verification.

## Immediate Actions

1. Stop API, Web, runtime, and worker processes.
2. Confirm the rollback target commit and migration head from release notes, active handoff, or backup metadata.
3. Verify backup artifacts before changing code or data:
   ```sh
   cd backend
   uv run noveland-backup-verify
   ```
4. Restore database and object storage using the backup restore runbook.
5. Switch code only to the approved rollback commit:
   ```sh
   git status --short --branch
   git switch main
   git log --oneline -5
   ```
6. Reinstall dependencies only if the rollback commit requires it, then run migrations to the expected head.

## Evidence To Collect

- Rollback reason, source commit, target commit, migration head, backup artifact timestamp, and restore verifier result.
- Impacted worlds, worldlines, sessions, media jobs, provider profiles, and feedback reports.
- Readiness reports before and after rollback.

## Redaction Rules

Do not record resolved secrets, storage paths, raw prompts, raw outputs, bytes, base64, invite tokens, provider credentials, prompt snapshot internals, or local model paths.

## Escalation

- Do not edit database rows directly as the default recovery path.
- If rollback requires destructive commands, get an explicit operator decision first.
- If schema downgrade is not supported, prefer restore from a verified backup over manual data edits.
- If rollback would lose tester reports or safety incidents, export safe summaries before restore.

## Closeout

Run targeted smoke checks, OpenSpec validation if docs changed, storage audit, and private beta or RC readiness checks. Record what data was restored and what remains deferred.
