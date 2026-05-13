# Multimodal Evals Reuse Release Framework

## Status

Accepted

## Context

The system already has long-run eval and release evidence records. Multimodal diagnostics need repeatable evidence without creating a parallel release framework.

## Decision

Multimodal evals reuse `long_run_eval_runs` with multimodal eval keys and safe metrics/blockers/recommendations metadata.

## Consequences

Diagnostics integrate with existing evidence patterns. A new eval table is deferred unless existing records become insufficient.

## Non-goals

- New release framework.
- Public launch gate changes.
- Human scoring platform.
- External observability exporter.

## Related files/tests

- `backend/packages/multimodal_eval/src/noveland/multimodal_eval/service.py`
- `backend/packages/worlds/src/noveland/worlds/models.py`
- `backend/tests/test_multimodal_eval_service.py`
- `backend/tests/test_api_multimodal_evals.py`
