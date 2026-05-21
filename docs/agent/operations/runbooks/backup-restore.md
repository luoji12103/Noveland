# Backup Restore Runbook

## Purpose

Run and verify normal-use backup and restore operations for the supported local/single-host profile.

## Scope

Use this before migrations, release-candidate gates, rollback, or destructive local environment changes. This runbook extends `docs/agent/operations/backup-restore.md`; the v1.1 Phase 2 drill makes it executable and evidence-backed.

## Immediate Actions

1. Stop write-heavy local processes where possible.
2. Verify current backup readiness:
   ```sh
   cd backend
   uv run noveland-backup-verify
   ```
3. Capture safe storage audit evidence:
   ```sh
   curl -sS http://127.0.0.1:8000/runtime/storage-audit \
     -H "Cookie: noveland_session=<admin-session>"
   ```
4. Create database and object storage backups using the existing backup playbook.
5. Restore only into a fresh local/single-host target with an empty database and empty object storage root.
6. After restore, verify database, media objects, checksums, worldlines, conversations, presentations, memory, provider config without secrets, and OpenSpec/docs provenance.

## Evidence To Collect

- Backup timestamp, git commit, migration head, object count, checksum summary, and restore target profile.
- World ids, worldline ids, conversation ids, presentation ids, memory counts, and safe provider config refs.
- Restore verifier status and failure type if any item is missing.

## Redaction Rules

Do not record resolved secrets, storage paths, raw prompts, raw outputs, bytes, base64, invite tokens, provider credentials, prompt snapshot internals, or local model paths.

## Escalation

- If provider config restore requires resolved secrets, stop and treat it as a blocker.
- If media verification requires user-facing storage path exposure, stop and treat it as a blocker.
- If checksums fail, do not restart normal use until missing or mismatched objects are understood.

## Closeout

Record the backup/restore drill report evidence, rerun readiness checks, and note whether restore is safe enough for release-candidate evaluation.
