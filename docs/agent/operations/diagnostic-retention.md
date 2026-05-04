# Diagnostic Retention

## Purpose

Runtime diagnostics are operational evidence, but they should not grow without policy.

## Operator API

- `GET /runtime/diagnostics/retention?retention_days=30` reports how many diagnostic rows are older than the cutoff.
- `POST /runtime/diagnostics/prune?retention_days=30&limit=1000` prunes at most `limit` old rows.

Both endpoints require platform-admin access. The prune endpoint requires CSRF.

## Policy

- Keep recent diagnostics during active incident work.
- Prefer a dry-run before prune.
- Use small prune limits for local/manual operations.
- Diagnostics are redacted on write, but they may still contain operational context; do not export them casually.

## Verification

After pruning, check:

```sh
GET /runtime/diagnostics/retention?retention_days=30
GET /runtime/status
```
