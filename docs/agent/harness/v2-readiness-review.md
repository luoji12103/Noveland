# v2 Readiness Review

## Purpose

This review closes the current 50-phase roadmap with evidence, not a binding v2
product direction. It compares the MVP definition, implemented operational
surfaces, deferred scope, and likely expansion paths.

## Evidence

- Runtime has platform-admin control, supervision, metrics, diagnostics,
  recovery docs, and daemon processing visibility.
- Memory has backend profiles, secret refs, async job processing, retry, eval
  recommendations, backfill dry-run/execution, and queue readiness reporting.
- Provider operations include profile health, secret-ref validation, diagnostics,
  rate-limit fields, and test-call behavior.
- Replay and snapshot flows include event audit, object-storage-backed new
  snapshots, integrity reporting, and backup verification docs.
- Conversation and narrative workflows include diagnostics, memory controls,
  speaker policy, guardrails, writer preview, publishing, reader search,
  timeline, and publication-aware visibility.
- Plugin and preset work remains code-registered, schema-validated, and
  diagnostic-aware without marketplace or hot reload.
- External tool policy is defined but execution is intentionally disabled.

## Not v2-Ready Yet

- Scale readiness should be reviewed against real operator data, not synthetic
  local counts alone.
- External tool execution needs a separate sandbox proof, approval model,
  secret-ref handling, and output-attribution rules.
- Distributed memory queue migration needs sustained evidence that DB-backed
  queue limits are the bottleneck.
- Multi-user/multi-world growth needs explicit realtime fanout and database
  query-plan validation.

## Candidate v2 Directions

- **Operator-grade runtime**: process supervision, incident workflows, richer
  metrics, and deployment automation.
- **Narrative product depth**: richer reader, editing workflow, publication
  review, and world timeline features.
- **Agent autonomy**: tool policy execution, sandboxing, runtime identity, and
  controlled external actions.
- **Scale platform**: distributed queue, managed storage, provider quota
  management, and multi-world fanout hardening.

## Recommendation

Do not select a binding v2 direction from the roadmap alone. Use the scale
readiness report, real operator feedback, and the external tool policy boundary
to choose the next product direction.
