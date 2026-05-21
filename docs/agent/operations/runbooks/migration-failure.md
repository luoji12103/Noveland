# Migration Failure Runbook

## Purpose

Handle failed database migrations during normal-use or release-candidate validation without destructive default actions.

## Scope

Use this when `alembic upgrade head`, app startup, schema metadata tests, or backup/restore drill verification reports migration errors.

## Immediate Actions

1. Stop API and runtime writes before retrying migration:
   ```sh
   cd backend
   uv run noveland-runtime --once
   ```
2. Record the current migration head:
   ```sh
   cd backend
   uv run alembic current
   ```
3. Check the configured target head:
   ```sh
   cd backend
   uv run alembic heads
   ```
4. Verify the backup exists before any remediation:
   ```sh
   cd backend
   uv run noveland-backup-verify
   ```
5. Retry only after identifying whether the failure is an ordering, constraint, data, or environment issue:
   ```sh
   cd backend
   uv run alembic upgrade head
   ```

## Evidence To Collect

- Current revision, target revision, failed revision, database profile, command, and safe error class.
- Whether API/runtime were stopped.
- Backup verification status and object checksum status.
- Any related schema metadata or alembic test failure.

## Redaction Rules

Do not record resolved secrets, storage paths, raw prompts, raw outputs, bytes, base64, invite tokens, provider credentials, prompt snapshot internals, or local model paths.

## Escalation

- Do not edit database rows directly as the default recovery path.
- If migration partly applied, do not hand-edit rows as the default recovery path.
- If rollback is needed, follow the rollback runbook and restore from verified backup artifacts.
- If data migration semantics are unclear, stop implementation and write a checkpoint decision before changing schema or data.

## Closeout

Confirm `uv run alembic current`, schema metadata tests, OpenSpec validation, and the targeted phase tests pass before restarting normal runtime.
