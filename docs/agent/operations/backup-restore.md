# Backup And Restore

## Purpose

This playbook covers the supported local/single-host backup workflow for the database and local object storage payloads.

## Backup

1. Stop write-heavy local processes if possible:
   - API server
   - `noveland-runtime --daemon`
2. Verify backup readiness:
   ```sh
   cd backend
   uv run noveland-backup-verify
   ```
3. Run the platform-admin storage audit before taking the backup:
   ```sh
   curl -sS -H "cookie: noveland_session=<admin-session>" \
     http://127.0.0.1:8000/runtime/storage-audit
   ```
   The audit reports media object and snapshot payload counts plus safe mismatch
   reasons. It must not return raw storage URIs, filesystem paths, object bytes,
   base64, raw prompts, or raw outputs.
4. Dump the database:
   ```sh
   pg_dump "$NOVELAND_DATABASE_URL" > .local/backups/noveland-db.sql
   ```
5. Archive object storage:
   ```sh
   tar -C "${NOVELAND_OBJECT_STORAGE_ROOT:-.local/object-storage}" \
     -czf .local/backups/noveland-object-storage.tgz .
   ```
6. Record the current migration head:
   ```sh
   cd backend
   uv run alembic current
   ```

## Restore

1. Start PostgreSQL and keep API/runtime stopped.
2. Restore the database into an empty target database:
   ```sh
   psql "$NOVELAND_DATABASE_URL" < .local/backups/noveland-db.sql
   ```
3. Restore object storage:
   ```sh
   mkdir -p "${NOVELAND_OBJECT_STORAGE_ROOT:-.local/object-storage}"
   tar -C "${NOVELAND_OBJECT_STORAGE_ROOT:-.local/object-storage}" \
     -xzf .local/backups/noveland-object-storage.tgz
   ```
4. Apply migrations if the code is newer than the backup:
   ```sh
   cd backend
   uv run alembic upgrade head
   ```
5. Verify restored payloads:
   ```sh
   cd backend
   uv run noveland-backup-verify
   ```
6. Re-run the platform-admin storage audit and confirm it returns `status=ok`.

## Notes

- New world snapshots store replay payloads in local object storage and keep a safe `object://...` URI in the database.
- Older inline snapshots remain readable and do not require an object storage payload.
- Media object payloads are verified through the storage abstraction by object
  IDs, sizes, checksums, and safe reason codes rather than by exposing local
  filesystem paths.
- Human actions should be attributable to user/session refs in API paths. Runtime-created events use `system:runtime`; this is an operational actor ref, not a login-capable user.
- This playbook intentionally does not expose destructive restore actions through the Web UI.
