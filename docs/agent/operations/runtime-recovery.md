# Runtime Recovery Playbook

## Purpose

This playbook gives local operators repeatable recovery steps for runtime stalls, provider configuration failures, memory queue failures, and replay/snapshot checks.

It is intentionally conservative:

- Do not run destructive restore actions from this playbook.
- Do not edit database rows directly unless a later incident-specific handoff explicitly approves it.
- Do not copy secret values into logs, tickets, docs, screenshots, or API responses.
- Prefer Web admin surfaces first, then read-only API checks, then process restart.

## Preconditions

- Local infrastructure is running:

  ```sh
  docker compose -f infra/compose.yaml up -d
  ```

- Database migrations are current:

  ```sh
  cd backend
  uv run alembic upgrade head
  ```

- API, Web, and runtime are normally started in separate shells:

  ```sh
  cd backend
  uv run uvicorn noveland.services.api.app:app --reload
  ```

  ```sh
  cd web
  npm run dev
  ```

  ```sh
  cd backend
  uv run noveland-runtime --daemon
  ```

## Runtime Status Check

Use the Web admin page first:

- Open `/admin/runtime`.
- Confirm the desired state, derived health, heartbeat freshness, last iteration, memory job counts, and recent error count.
- A stopped desired state is not an incident unless runtime should be running.
- A degraded or failed health state should be paired with diagnostics before taking action.

Use the API when a browser is not practical. The endpoint requires a platform-admin session cookie:

```sh
curl -sS http://127.0.0.1:8000/runtime/status \
  -H "Cookie: noveland_session=<session-token>"
```

Expected verification points:

- `desired_state` matches the intended operator setting.
- `runtime_health.status` is `healthy` or a known intentional state such as `stopped`.
- `runtime_health.heartbeat_age_seconds` is recent when the daemon is expected to run.
- `memory_write_jobs.failed_count` and `memory_write_jobs.stalled_processing_count` are understood.
- `runtime_health.recent_error_count` is zero or explained by recent diagnostics.

## Runtime Restart

Use this when the daemon process is down, stale, or wedged, and the database desired state is already correct.

1. Stop the existing local daemon process from its shell with `Ctrl-C`.
2. Start it again:

   ```sh
   cd backend
   uv run noveland-runtime --daemon
   ```

3. Re-check `/admin/runtime` or `/runtime/status`.
4. Confirm a fresh heartbeat and a recent finished iteration.
5. Review `/runtime/diagnostics` for new `runtime.iteration_failed`, provider, memory, or event publisher errors.

If the daemon restarts but health immediately becomes degraded again, treat the failure as provider, memory queue, or event/snapshot related instead of repeatedly restarting.

## Provider Degradation

Use this when provider test calls fail, agent runs fail, or runtime health points to provider diagnostics.

1. Open `/admin/providers`.
2. Check the health card for each enabled profile:
   - `ok`: recent provider state has no known issue.
   - `untested`: run `Test provider` before relying on the profile.
   - `configuration_error`: check `api_key_ref`, `secret_ref_status`, plugin binding, base URL, and model name.
   - `degraded`: inspect recent diagnostics and last test error.
   - `disabled`: profile is intentionally unavailable.
3. Confirm `NOVELAND_PROVIDER_API_KEYS_JSON` contains the referenced key and that the configured value is not empty.

Example local configuration shape:

```sh
NOVELAND_PROVIDER_API_KEYS_JSON='{"openai-local":"set-a-local-secret-value"}'
```

4. Restart the API if local environment variables changed.
5. Run `Test provider` again.
6. Re-check runtime health and relevant agent/conversation diagnostics.

Never paste the secret value itself into diagnostics or docs. Only the secret reference, such as `openai-local`, should appear in operator output.

## Memory Queue Failures

Use this when `/admin/runtime` shows failed or stalled memory write jobs.

1. Open `/admin/memory-backends`.
2. Check profile health and failed job rows.
3. Confirm failed jobs are retryable before retrying:
   - retryable jobs have attempts remaining and an enabled backend profile.
   - terminal jobs need configuration or data correction before a future enqueue path can succeed.
4. Retry a failed job from the Web row action, or through the API with a platform-admin session and CSRF token:

   ```sh
   curl -sS -X POST http://127.0.0.1:8000/memory-write-jobs/<job-id>/retry \
     -H "Cookie: noveland_session=<session-token>; noveland_csrf=<csrf-token>" \
     -H "X-CSRF-Token: <csrf-token>"
   ```

5. Confirm the job returns to `pending`.
6. Let `noveland-runtime --daemon` process the queue.
7. Re-check `/admin/runtime` memory counts and `/admin/memory-backends` job rows.

For stalled `processing` jobs, do not reset rows directly. Record the job id, profile, age, and last error in the active handoff or debug journal, then decide on a targeted fix.

## Event Audit Checks

Use this when world state appears inconsistent, replay behaves unexpectedly, or a runtime action needs causal review.

1. Open the selected world overview.
2. Use the event audit panel to filter by event name, actor ref, sequence bounds, and wall-time bounds.
3. Prefer narrow filters before inspecting payloads.
4. Verify:
   - event sequence ordering is monotonic.
   - causation and correlation ids match the action being investigated.
   - event payloads contain expected fields without secret values.

Read-only API check:

```sh
curl -sS "http://127.0.0.1:8000/worlds/<world-id>/events?limit=20" \
  -H "Cookie: noveland_session=<session-token>"
```

The event audit endpoint is world-admin only because payloads may contain operational or narrative details.

## Snapshot Integrity Checks

Use this before relying on replay output for recovery or before investigating a suspected replay gap.

1. Open the selected world overview.
2. Check the replay and snapshots panel.
3. Confirm the live clock state is visually separate from reconstructed replay state.
4. Check snapshot integrity:
   - `ok`: latest snapshot is compatible and covers the latest event sequence.
   - `warning`: no snapshot exists or a valid snapshot is stale.
   - `error`: schema mismatch, missing payload, invalid payload, or a snapshot covering a future event sequence.
5. If status is `warning`, create an inline snapshot from the Web control when appropriate.
6. If status is `error`, do not restore or overwrite data. Record the world id, latest event sequence, snapshot id, cover sequence, schema version, and issues.

Read-only API check:

```sh
curl -sS http://127.0.0.1:8000/worlds/<world-id>/snapshots/integrity \
  -H "Cookie: noveland_session=<session-token>"
```

## Closeout

After recovery:

- Re-check `/admin/runtime`.
- Re-run the specific action that previously failed.
- Record any code fix in `docs/agent/harness/change-journal.md`.
- Record incident details, failed commands, and unresolved risks in `docs/agent/harness/debug-journal.md` or the active handoff.
- Keep the final handoff specific about what was verified and what remains uncertain.
