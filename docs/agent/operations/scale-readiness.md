# Scale Readiness

Scale readiness is a derived operator report, not a load test.

## Operator Surface

- `GET /runtime/scale-readiness` reports current v1 readiness signals.
- The response is platform-admin only.
- The endpoint is read-only and must not enqueue jobs, mutate runtime state, or
  trigger migrations.

## Reviewed Areas

- database/index pressure from world, event, and agent run counts
- realtime fanout based on active world counts
- memory queue throughput, failed jobs, retryability, and stalled jobs
- provider health and missing rate-limit configuration
- diagnostic growth and retention readiness
- snapshot storage mode and legacy inline snapshot presence

## Interpretation

- `ok`: no immediate blocker was detected from current local data.
- `watch`: growth work can continue, but an operator should review the listed
  recommendations first.
- `blocked`: fix listed blockers before treating the deployment as v2-ready.

This report does not introduce autoscaling, distributed queues, or remote object
storage. It helps decide which blocker should be handled before v2 expansion.
