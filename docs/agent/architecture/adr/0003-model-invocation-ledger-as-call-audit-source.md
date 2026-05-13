# Model Invocation Ledger As Call Audit Source

## Status

Accepted

## Context

Text, image, speech, and provider workflow calls need a single audit source for cost, latency, prompt evidence, status, and media links.

## Decision

All model/provider calls must write `model_invocations` and `prompt_snapshots` through the invocation ledger boundary.

## Consequences

Diagnostics can audit call coverage and media linkage uniformly. Raw prompt/output evidence stays admin-scoped and must not leak into event payloads.

## Non-goals

- Public prompt browsing.
- Reader/member access to prompt snapshots.
- Replacing provider-specific adapters.

## Related files/tests

- `backend/packages/invocations/src/noveland/invocations/models.py`
- `backend/packages/providers/src/noveland/providers/service.py`
- `backend/tests/test_invocation_ledger_service.py`
- `backend/tests/test_provider_execution_service.py`
