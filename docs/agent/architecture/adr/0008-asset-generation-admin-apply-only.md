# Asset Generation Admin Apply Only

## Status

Accepted

## Context

Background asset generation can create unbounded provider cost if preview/planning automatically executes work.

## Decision

Asset generation preview creates proposals only. Admin apply creates queued media jobs only. Provider execution and daemon automation remain explicit and deferred.

## Consequences

Operators can inspect proposals before spend. Runtime daemon cannot silently execute proposal jobs in Phase 11-13.

## Non-goals

- Background auto-generation daemon.
- Real-time pre-generation.
- Provider calls during preview/apply.
- Web review UI.

## Related files/tests

- `backend/packages/asset_generation/src/noveland/asset_generation/service.py`
- `backend/services/api/src/noveland/services/api/asset_generation.py`
- `backend/tests/test_asset_generation_service.py`
- `backend/tests/test_api_asset_generation.py`
