# Phase Plan — v0.5 Authoring & Import Studio

## Version Goal

World admins can ingest source materials, preview extracted canon, characters, relationships, memories, and assets, resolve conflicts, and selectively apply reviewed imports into a target worldline.

## Version Non-goals

- Unreviewed automatic writes to canonical world state
- One-pass perfect parsing
- Bypassing preview/apply
- Automatic memory writes without migration proposal/apply
- Long-term runtime prompts containing full raw copyrighted sources
- Provider outputs directly mutating world state

## Phase Discipline

- Implement phases strictly in order unless OpenSpec is updated first.
- Each phase starts from clean local `main`.
- Each phase is independently testable, mergeable, and reversible.
- Do not continue to the next phase after a failing gate or unresolved architecture decision.
- Do not push unless the user explicitly requests it.

## Phase 1 — Authoring Source Registry

### Goal

Manage script, lore, character sheet, location sheet, image, and audio source assets.

### Scope

- Source asset registry
- Source metadata
- Import batch
- Target worldline
- Ownership/visibility

### Non-goals

- Parsing or applying source content

### Reused Systems

- MediaService
- worldline records
- auth/ACL services

### Acceptance Criteria

- Admins can register source batches
- Target worldline is explicit
- Source visibility is enforced

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- source registry service/API tests
- ACL tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 2 — Script Parser & Dialogue Extractor

### Goal

Parse dialogue, speaker, scene, choice, route, and event candidates.

### Scope

- Script parse jobs
- Dialogue extraction
- Speaker resolution
- Scene/choice candidate extraction
- Preview records

### Non-goals

- Direct apply to world state

### Reused Systems

- provider execution for optional parsing
- invocation ledger
- import preview records

### Acceptance Criteria

- Parser creates preview candidates
- Speaker uncertainty is represented
- Provider parsing writes invocation evidence when used

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- parser fixture tests
- ledger tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 3 — Character & Relationship Extractor

### Goal

Extract characters, relationships, names, factions, identities, and emotional baselines.

### Scope

- Character candidates
- Relationship candidates
- Faction/identity tags
- Review records

### Non-goals

- Automatic relationship graph mutation

### Reused Systems

- agents package
- future relationship records
- import preview/apply workflow

### Acceptance Criteria

- Candidates are reviewable
- Relationship confidence/uncertainty is explicit
- Worldline scope is preserved

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- extractor fixture tests
- worldline isolation tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 4 — World Bible & Lore Extractor

### Goal

Extract locations, organizations, world rules, secrets, and knowledge boundaries.

### Scope

- World bible fragments
- Lore candidates
- Secret/knowledge boundary candidates
- canon/inference/uncertain classification

### Non-goals

- Runtime context injection of full raw source

### Reused Systems

- worlds/events docs
- future world bible records
- provider ledger if model-backed

### Acceptance Criteria

- Lore candidates preserve source traceability
- Secret/knowledge boundaries are not reader-exposed
- Uncertain claims require review

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- lore extractor fixture tests
- visibility tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 5 — Canon Conflict Review

### Goal

Identify conflicting facts, duplicate characters, relationship contradictions, timeline conflicts, and OOC risk.

### Scope

- Conflict reports
- Duplicate detection
- Admin resolution
- Apply decisions

### Non-goals

- Automatic conflict resolution

### Reused Systems

- import candidates
- world events
- agent/profile records
- diagnostics patterns

### Acceptance Criteria

- Conflicts are grouped with evidence
- Admin decisions are persisted
- Unresolved blockers prevent unsafe apply

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- conflict fixture tests
- apply blocker tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 6 — Memory Migration Pipeline

### Goal

Convert source content into fact, episodic, relationship, preference, and style memory proposals.

### Scope

- Memory migration proposals
- Preview/apply
- Source traceability
- Worldline scoping

### Non-goals

- Direct memory backend SDK access
- Automatic memory writes outside apply

### Reused Systems

- MemoryService
- memory write jobs
- import proposal workflow

### Acceptance Criteria

- Memory proposals are reviewable
- Apply uses MemoryService boundaries
- Worldline scope and source traceability are retained

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- memory migration tests
- MemoryService boundary tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 7 — Asset Import & Matching

### Goal

Import sprites, variants, backgrounds, CGs, and voice references and match them to characters or scenes.

### Scope

- Asset matching candidates
- Character/scene binding proposals
- Manual confirmation

### Non-goals

- Public media delivery
- Automatic visual binding apply without review

### Reused Systems

- MediaService
- VisualAssetService
- Speech voice references

### Acceptance Criteria

- Imported assets become media records
- Matching proposals are reviewable
- Apply validates same worldline

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- asset matching fixture tests
- media/visual validation tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 8 — Import Preview/Apply Workflow

### Goal

Unify import run lifecycle, proposal review, selective apply, rollback hints, and audit records.

### Scope

- Import run lifecycle
- Proposal review
- Selective apply
- Audit trail

### Non-goals

- Unbounded batch mutation
- Provider outputs directly applying state

### Reused Systems

- asset generation preview/apply patterns
- world events
- diagnostics

### Acceptance Criteria

- Preview creates proposals only
- Apply is selective and admin-controlled
- Audit records explain changes

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- preview/apply tests
- rollback hint tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 9 — Authoring Regression Fixture

### Goal

Create a small galgame import fixture for regression of scripts, characters, relationships, assets, and memory migration.

### Scope

- Script fixture
- Character fixture
- Relationship fixture
- Asset fixture
- Memory migration fixture

### Non-goals

- Production seed framework
- Quality benchmark for all content

### Reused Systems

- test fixture patterns
- multimodal sample-world regression

### Acceptance Criteria

- Fixture can be created deterministically
- Import pipeline can pass expected scenarios
- No raw source leaks into runtime/event payloads

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- authoring regression tests
- leak tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.
