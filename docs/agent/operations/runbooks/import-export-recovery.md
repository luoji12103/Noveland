# Import Export Recovery Runbook

## Purpose

Recover failed world package, authoring, media manifest, provider config, or source traceability import/export flows without bypassing preview/review/apply.

## Scope

Use this when package validation fails, imported data is incomplete, media manifest checks fail, provider config export includes unsafe fields, or sample package repeatability regresses.

## Immediate Actions

1. Validate package contracts:
   ```sh
   curl -sS -X POST http://127.0.0.1:8000/worlds/<world-id>/package-contracts/validate \
     -H "Cookie: noveland_session=<admin-session>; noveland_csrf=<csrf-token>" \
     -H "X-CSRF-Token: <csrf-token>" \
     -H "Content-Type: application/json" \
     --data '{"worldline_id":"<worldline-id>"}'
   ```
2. Export provider config metadata and confirm it contains safe references only:
   ```sh
   curl -sS http://127.0.0.1:8000/worlds/<world-id>/package-contracts/provider-config-export \
     -H "Cookie: noveland_session=<admin-session>"
   ```
3. For authoring imports, use preview first:
   ```sh
   curl -sS -X POST http://127.0.0.1:8000/worlds/<world-id>/authoring/import-runs/<run-id>/preview \
     -H "Cookie: noveland_session=<admin-session>; noveland_csrf=<csrf-token>" \
     -H "X-CSRF-Token: <csrf-token>"
   ```
4. Apply only approved proposals. Do not import directly into canon, persona, memory, media bindings, provider profiles, or worldline state.
5. Keep proprietary or user-provided galgame assets out of repository fixtures and public sample packages.

## Evidence To Collect

- Package id or run id, world id, worldline id, manifest version, media counts, checksum status, provider config export status, and source traceability refs.
- Preview blockers, proposals created, proposals approved, and explicit apply result.
- Asset exclusion summary for proprietary or user-provided sources.

## Redaction Rules

Do not record resolved secrets, storage paths, raw prompts, raw outputs, bytes, base64, invite tokens, provider credentials, prompt snapshot internals, or local model paths.

## Escalation

- If import/export requires resolved secrets, stop and file a blocker.
- If import bypasses preview/review/apply, stop and revert the workflow before normal-use testing continues.
- If public sample export would include proprietary or user-provided galgame assets, exclude them or replace them with safe placeholder metadata.

## Closeout

Confirm package validation, preview, reviewed apply, media manifest integrity, provider config safety, and sample repeatability evidence are complete.
