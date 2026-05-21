# Normal-use Runbooks

These runbooks are operator procedures for v1.1 normal-use and release-candidate preparation. They are command-oriented, local/single-host first, and evidence-backed.

## Shared Rules

- Prefer existing Web admin surfaces, safe API diagnostics, and readiness reports before manual intervention.
- Keep provider calls fake or mocked unless a runbook explicitly points to the opt-in provider lab workflow.
- Do not bypass authoring preview/review/apply for import/export recovery or content repair.
- Do not edit database rows directly unless a later incident-specific handoff explicitly approves it.
- Do not record resolved secrets, storage paths, raw prompts, raw outputs, bytes, base64, invite tokens, provider credentials, prompt snapshot internals, or local model paths.

## Runbooks

- [Provider Outage](provider-outage.md)
- [Quota Exhaustion](quota-exhaustion.md)
- [Media Job Stuck](media-job-stuck.md)
- [Migration Failure](migration-failure.md)
- [Backup Restore](backup-restore.md)
- [Rollback](rollback.md)
- [Worldline Restore](worldline-restore.md)
- [Secret Rotation](secret-rotation.md)
- [Private Beta Incident](private-beta-incident.md)
- [Import Export Recovery](import-export-recovery.md)
- [Provider Fallback](provider-fallback.md)
