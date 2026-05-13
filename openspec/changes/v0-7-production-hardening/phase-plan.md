# Phase Plan — v0.7 Production Hardening

## Version Goal

Noveland should support stable long-running deployment with stronger permissions, secret governance, budgets, backups, observability, and security regression coverage.

## Version Non-goals

- Large new gameplay features
- Player-facing public launch
- Provider marketplace
- Streaming
- Expanded automatic content generation

## Phase Discipline

- Implement phases strictly in order unless OpenSpec is updated first.
- Each phase starts from clean local `main`.
- Each phase is independently testable, mergeable, and reversible.
- Do not continue to the next phase after a failing gate or unresolved architecture decision.
- Do not push unless the user explicitly requests it.

## Phase 1 — Permission Model Hardening

### Goal

Establish owner/admin/member/reader/player permission matrix.

### Scope

- ACL matrix
- Route-level permissions
- Admin vs reader/player separation

### Non-goals

- New public launch routes

### Reused Systems

- auth services
- API authorization dependencies
- current route tests

### Acceptance Criteria

- Permission matrix is documented and enforced
- Reader/player routes cannot access admin evidence
- ACL tests cover key routes

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- authorization tests
- route permission tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 2 — Secret & Provider Governance

### Goal

Support secret rotation, provider disable, provider audit, and provider-scoped permissions.

### Scope

- Secret lifecycle
- Provider governance
- Audit records

### Non-goals

- Provider marketplace
- Resolved secret exposure

### Reused Systems

- ProviderSecretResolver
- provider registry
- health checks

### Acceptance Criteria

- Provider disable prevents execution
- Secret references remain opaque
- Audit records are safe

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- provider governance tests
- secret leak tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 3 — Cost & Rate Control

### Goal

Add per-world budgets, per-provider budgets, media generation budgets, emergency stop, and quota status.

### Scope

- Budget model
- Rate limits
- Emergency disable switches

### Non-goals

- Complex billing marketplace

### Reused Systems

- model_invocations
- media_jobs
- provider integrations
- asset generation policies

### Acceptance Criteria

- Budget checks can block provider execution
- Quota status is visible to admins
- Emergency stop is auditable

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- budget tests
- provider execution guard tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 4 — Object Storage & Backup v2

### Goal

Define S3/GCS-compatible abstraction, backup/restore drill, checksum audit, and object lifecycle policy.

### Scope

- Storage backend abstraction
- Backup/restore procedure
- Integrity checks

### Non-goals

- Public media CDN delivery

### Reused Systems

- MediaService
- media_objects
- storage local/backup modules

### Acceptance Criteria

- Storage integrity can be audited
- Backup/restore drill is documented/tested
- Object lifecycle does not leak storage paths

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- storage integrity tests
- backup docs checks
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 5 — Deployment Profile

### Goal

Define production compose/profile, health endpoints, migration procedure, and operator docs.

### Scope

- Production deployment docs
- Compose profile
- Health checks

### Non-goals

- Managed cloud platform lock-in

### Reused Systems

- infra compose
- health API
- migration config

### Acceptance Criteria

- Deployment profile is documented
- Health checks cover core dependencies
- Migration procedure has rollback guidance

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- compose config
- health tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 6 — Observability & Incident Diagnostics

### Goal

Expose provider/media/runtime/eval dashboards, failure replay, and diagnostic retention.

### Scope

- Observability APIs
- Failure replay data
- Incident diagnostics

### Non-goals

- External observability exporter

### Reused Systems

- observability package
- runtime diagnostics
- multimodal eval service

### Acceptance Criteria

- Incident reports link to safe evidence
- Retention rules are clear
- Failure replay avoids secrets/raw prompts

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- diagnostics tests
- redaction tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 7 — Security Regression Suite

### Goal

Add regression coverage for secret leak, prompt leak, storage_uri/path leak, ACL leak, and worldline isolation.

### Scope

- Security regression tests
- Leak fixtures
- ACL test matrix

### Non-goals

- Full external penetration test program

### Reused Systems

- Phase 13 fixture
- authorization tests
- multimodal diagnostics

### Acceptance Criteria

- Regression fixtures catch forbidden leaks
- ACL matrix is tested
- Worldline isolation failures are detected

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- security regression suite
- full local gate for implementation phases
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 8 — Production Readiness Gate

### Goal

Create an internal readiness gate distinct from public launch readiness.

### Scope

- Readiness checklist
- Gate report
- Operator signoff

### Non-goals

- Public launch gate
- Marketing/release workflow

### Reused Systems

- BetaChecklistRun
- LongRunEvalRun
- diagnostics services

### Acceptance Criteria

- Gate report aggregates existing evidence
- Operator signoff is recorded
- Failed checks have actionable blockers

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- readiness gate tests
- diagnostics aggregation tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.
