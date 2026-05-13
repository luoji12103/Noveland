# Phase Plan — v0.6 Runtime Narrative Quality

## Version Goal

Noveland runtime should produce more consistent, character-faithful, emotionally coherent, and causally continuous world evolution while preserving review gates and worldline isolation.

## Version Non-goals

- Provider output directly modifying world state
- Bypassing invocation ledger
- Bypassing context visibility
- Automatic GM apply for high-impact events
- Public launch
- Making quality evaluation block every runtime path initially

## Phase Discipline

- Implement phases strictly in order unless OpenSpec is updated first.
- Each phase starts from clean local `main`.
- Each phase is independently testable, mergeable, and reversible.
- Do not continue to the next phase after a failing gate or unresolved architecture decision.
- Do not push unless the user explicitly requests it.

## Phase 1 — Runtime Context Contract v2

### Goal

Distinguish agent, conversation, GM, narrative, and eval context contracts.

### Scope

- Context schemas
- Visibility boundaries
- Worldline scope
- Prompt snapshot traceability

### Non-goals

- One generic prompt context for all call sites

### Reused Systems

- Invocation ledger
- observations
- conversation services
- memory services

### Acceptance Criteria

- Each context type has explicit visibility rules
- Prompt snapshots identify context kind
- Hidden data is filtered

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- context contract tests
- prompt snapshot tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 2 — Provider-backed GM Proposal

### Goal

Use providers to generate GM proposals without directly mutating world state.

### Scope

- GM proposal generation
- Review/apply boundary
- Impact classification

### Non-goals

- Automatic high-impact event apply

### Reused Systems

- ProviderExecutionService
- InvocationLedgerService
- world events

### Acceptance Criteria

- Provider calls write ledger evidence
- GM outputs become proposals
- Apply remains explicit

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- GM proposal tests
- provider boundary tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 3 — Dialogue Style & OOC Review

### Goal

Check character speech style, relationship consistency, and out-of-character risk.

### Scope

- Dialogue review service
- OOC signal
- Style consistency score

### Non-goals

- Blocking all dialogue generation by default

### Reused Systems

- conversation turns
- agent profiles
- invocation ledger

### Acceptance Criteria

- Reviews attach evidence to dialogue
- OOC warnings are explainable
- Reader output is not polluted with diagnostics

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- dialogue review tests
- ACL tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 4 — Emotion/Sprite/Voice Alignment

### Goal

Check and suggest fixes for emotion tag, sprite variant, and voice style alignment.

### Scope

- Alignment diagnostics
- Suggested fixes
- Admin review

### Non-goals

- Automatic unreviewed visual/speech changes

### Reused Systems

- VisualResolver
- SpeechStyleMappingService
- conversation presentations

### Acceptance Criteria

- Misalignment is detected
- Fix suggestions preserve worldline scope
- No media path leaks occur

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- alignment diagnostic tests
- worldline tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 5 — Narrative Writer v2

### Goal

Generate chapters from world events and conversation turns with worldline, visibility, and reader-safe filtering.

### Scope

- Narrative generation v2
- Visibility filter
- Reader-safe output

### Non-goals

- Narrative artifacts as media storage
- Raw prompt/output in world_events.payload

### Reused Systems

- narrative services
- events
- invocation ledger
- media references

### Acceptance Criteria

- Generated drafts are reader-safe
- Provider calls are audited
- Hidden/developer-only content is filtered

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- narrative writer tests
- leak tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 6 — Continuity Review v2

### Goal

Check causality, secret leakage, timeline conflicts, relationship jumps, and route conflicts.

### Scope

- Continuity diagnostics
- Conflict reports
- Repair suggestions

### Non-goals

- Automatic repair apply

### Reused Systems

- world events
- relationship/route records
- multimodal diagnostics

### Acceptance Criteria

- Continuity blockers have evidence
- Repair suggestions are reviewable
- Secret leakage is detected

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- continuity fixture tests
- secret leak tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 7 — Runtime Pacing Controller

### Goal

Control world evolution speed, reading speed, lookahead, offscreen compression, and asset generation budget.

### Scope

- Pacing policy
- Lookahead limits
- Offscreen compression

### Non-goals

- Unbounded pre-generation
- Daemon auto-generation without accepted spec

### Reused Systems

- runtime services
- asset generation policies
- media jobs

### Acceptance Criteria

- Pacing policy caps background work
- Offscreen compression is explainable
- Budgets block excess proposals

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- pacing policy tests
- budget tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 8 — Route & Relationship Progression Quality

### Goal

Review route progression, affection/conflict/repair, and relationship state changes.

### Scope

- Relationship progression review
- Route progression review
- Drift detection

### Non-goals

- Replacing relationship model semantics

### Reused Systems

- relationship records
- route records
- world events
- diagnostics

### Acceptance Criteria

- Progression changes are explainable
- Drift warnings reference evidence
- No hidden state is exposed to players

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- progression fixture tests
- ACL tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 9 — Long-run Living World Simulation Eval

### Goal

Run multi-day/multi-turn simulations to detect character drift, narrative breaks, and world state pollution.

### Scope

- Long-run eval scenario
- Drift metrics
- Failure reports

### Non-goals

- External observability platform
- Human scoring system

### Reused Systems

- LongRunEvalRun
- multimodal eval service
- runtime diagnostics

### Acceptance Criteria

- Eval produces metrics and blockers
- Failures point to evidence
- Sample scenario is deterministic

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- long-run eval tests
- sample fixture tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 10 — Narrative Quality Dashboard/API

### Goal

Expose quality metrics, blockers, and repair recommendations to admins.

### Scope

- Quality API
- Dashboard-ready DTOs
- Diagnostic summaries

### Non-goals

- Public quality dashboard
- Changing diagnostics semantics without tests

### Reused Systems

- multimodal evals
- runtime diagnostics
- admin API patterns

### Acceptance Criteria

- Admin APIs summarize quality results
- Reader/member routes cannot access admin evidence
- DTOs avoid raw prompts and storage paths

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- quality API tests
- permission tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.
