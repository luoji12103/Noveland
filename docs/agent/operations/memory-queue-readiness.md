# Memory Queue Readiness

## Purpose

The current memory queue is intentionally database-backed. This report defines what must be true before a later external worker queue is considered.

## Operator API

- `GET /memory-queue/readiness`
- `GET /memory-backfill/dry-run`
- `POST /memory-backfill/execute?limit=100`

All endpoints are platform-admin only. Backfill execution requires CSRF.

## Readiness Rules

The queue is blocked for external-worker migration when:

- terminal failed jobs exist
- stalled processing jobs exist
- retryable failures have not been retried or inspected
- the pending/processing backlog is too large for a safe topology change

## Backfill Rules

- Execution is bounded by `limit`.
- Dedupe keys match the dry-run format: `agent-run:{id}`, `conversation-turn:{id}`, and `world-event:{id}`.
- Jobs are enqueued through `MemoryService`; runtime/conversation code still does not import backend SDKs directly.
- Existing jobs are skipped by dedupe key.

This phase does not introduce Celery, Temporal, Redis, or another external queue.
