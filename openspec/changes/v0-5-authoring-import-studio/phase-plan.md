# Phase Plan — v0.5 Authoring & Import Studio

## Version Goal

World admins can ingest source materials, preview extracted canon, characters, relationships, memories, and assets, resolve conflicts, and selectively apply reviewed imports into a target worldline.

## Version Architecture Boundary

v0.5 authoring/import work SHALL use a dedicated subsystem:

- `backend/packages/authoring/`
- `backend/services/api/src/noveland/services/api/authoring.py`

The authoring router SHALL be registered at app level. v0.5 SHALL NOT continue expanding `worlds.py` for new authoring/import logic except for a narrow compatibility hook if unavoidable. Existing `authoring_templates`, `authoring_import_jobs`, and world composition import may be referenced as legacy-compatible inputs, but they are not the primary v0.5 foundation.

## Version Non-goals

- Unreviewed automatic writes to canonical world state
- One-pass perfect parsing
- Bypassing preview/apply
- Automatic memory writes without migration proposal/apply
- Long-term runtime prompts containing full raw copyrighted sources
- Provider outputs directly mutating world state
- New media/provider/memory subsystems
- Public reader import visibility

## Phase Discipline

- Implement phases strictly in order unless OpenSpec is updated first.
- Each phase starts from clean local `main`.
- Each phase is independently testable, mergeable, and reversible.
- Do not continue to the next phase after a failing gate or unresolved architecture decision.
- Do not push unless the user explicitly requests it.

## Phase 1 — Authoring Import Core

### Goal

Create the dedicated authoring package/router and shared import foundation for source registry, import runs, proposals, review decisions, source traceability, preview, and selective apply.

### Scope

- `backend/packages/authoring/` contracts, models, services, and package registration
- `backend/services/api/src/noveland/services/api/authoring.py` router and app-level include
- Source batch/source asset/source fragment registry
- Import run lifecycle
- Proposal records for extracted dialogue, characters, relationships, lore, assets, and memory candidates
- Review decision records
- Source traceability records from proposals/applied refs back to source fragments
- Preview creates proposals only
- Apply is selective, admin-controlled, and proposal-kind gated
- Compatibility references to legacy authoring templates/jobs where useful

### Non-goals

- Parsing source content beyond minimal fixture/manual proposal creation
- Provider-backed extraction
- Asset matching automation
- Direct lore/world-bible apply
- Automatic memory writes
- Web UI beyond the minimum needed if implementation chooses API-only first

### Reused Systems

- MediaService for source documents/images/audio
- Worldline validation helpers
- auth/ACL services
- asset generation preview/apply patterns
- world events for safe audit references only
- diagnostics patterns

### Acceptance Criteria

- Admins can register source batches/assets/fragments in a target worldline.
- Preview creates import runs and proposals without provider execution.
- Apply requires explicit reviewed proposal selection.
- Apply cannot mutate unsupported proposal kinds.
- All source/proposal/review records preserve world and worldline scope.
- No storage URI, raw path, bytes, base64, raw prompt, or raw output is written to `world_events.payload`.

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- authoring core service/API tests
- source registry tests
- preview/apply proposal tests
- ACL and worldline isolation tests
- schema metadata and Alembic config tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 2 — Script Parser & Dialogue Extractor

### Goal

Parse dialogue, speaker, scene, choice, route, and event candidates into Phase 1 proposal records.

### Scope

- Script parse jobs
- Deterministic parser fixture path
- Dialogue extraction
- Speaker uncertainty and resolution hints
- Scene/choice/route/event candidate proposals
- Optional provider-backed parsing only if safe and explicitly scoped

### Non-goals

- Direct apply to world state
- Runtime prompt injection of full raw source

### Reused Systems

- Phase 1 authoring source fragments and proposals
- provider execution for optional parsing
- invocation ledger for provider-backed parsing

### Acceptance Criteria

- Parser creates reviewable preview candidates.
- Speaker uncertainty is represented.
- Provider parsing writes invocation evidence when used.
- Raw source is not copied into world events or reader/member routes.

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- parser fixture tests
- proposal creation tests
- ledger/redaction tests for provider-backed parsing
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 3 — Character & Relationship Extractor

### Goal

Extract characters, relationships, names, factions, identities, and emotional baselines into reviewable proposals.

### Scope

- Character candidate proposals
- Relationship candidate proposals
- Faction/identity/emotional baseline metadata
- Source traceability
- Confidence and uncertainty fields

### Non-goals

- Automatic relationship graph mutation
- Direct agent creation outside explicit apply

### Reused Systems

- agents package
- existing agent relationship records on explicit apply
- Phase 1 proposal/review/apply workflow

### Acceptance Criteria

- Candidates are reviewable.
- Relationship confidence/uncertainty is explicit.
- Worldline scope is preserved.
- Apply is blocked unless proposal kind and review state allow it.

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- extractor fixture tests
- proposal/apply blocker tests
- worldline isolation tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 4 — World Bible & Lore Extractor

### Goal

Extract locations, organizations, world rules, secrets, and knowledge boundaries into proposal-only lore records.

### Scope

- World bible/lore candidate proposals
- Location/organization/rule/secret/knowledge-boundary candidate metadata
- canon/inference/uncertain classification
- Source traceability and visibility flags

### Non-goals

- Direct apply to `WorldBible` or global canon tables
- Runtime context injection of full raw source
- Reader/member exposure of secret or developer-only lore candidates

### Reused Systems

- Phase 1 source/proposal/review workflow
- worlds/events records as referenced context only
- provider ledger if model-backed

### Acceptance Criteria

- Lore candidates preserve source traceability.
- Secret/knowledge boundaries are not reader-exposed.
- Uncertain claims require review.
- Apply remains blocked/proposal-only until a later accepted architecture decision defines global-vs-worldline canon semantics.

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- lore extractor fixture tests
- visibility tests
- proposal-only apply blocker tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 5 — Canon Conflict Review

### Goal

Identify conflicting facts, duplicate characters, relationship contradictions, timeline conflicts, and OOC risk across import proposals.

### Scope

- Conflict reports
- Duplicate detection
- Admin resolution decisions
- Apply blockers and warnings

### Non-goals

- Automatic conflict resolution
- Provider outputs directly applying state

### Reused Systems

- Phase 1 proposals/reviews/source traceability
- world events as safe audit references
- agent/profile records
- diagnostics patterns

### Acceptance Criteria

- Conflicts are grouped with evidence.
- Admin decisions are persisted.
- Unresolved blockers prevent unsafe apply.
- Evidence refs do not expose raw source, raw prompt/output, media paths, or secrets.

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- conflict fixture tests
- apply blocker tests
- safe evidence tests
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
- Preview/apply through Phase 1 workflow
- Source traceability
- Worldline scoping
- Explicit apply path through MemoryService boundaries

### Non-goals

- Direct memory backend SDK access
- Automatic memory writes outside reviewed apply
- STT transcript auto-memory writes

### Reused Systems

- Phase 1 proposal/review/apply workflow
- MemoryService
- memory write jobs

### Acceptance Criteria

- Memory proposals are reviewable.
- Apply uses MemoryService boundaries.
- Worldline scope and source traceability are retained.
- Memory apply writes safe audit references only.

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- memory migration tests
- MemoryService boundary tests
- apply audit leak tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 7 — Asset Import & Matching

### Goal

Import sprites, variants, backgrounds, CGs, and voice references and match them to characters or scenes through reviewable proposals.

### Scope

- Source image/audio registration through MediaService
- Asset matching candidates
- Character/scene/voice binding proposals
- Manual confirmation before apply

### Non-goals

- Public media delivery
- Automatic visual binding apply without review
- New media storage framework

### Reused Systems

- Phase 1 proposal/review/apply workflow
- MediaService
- VisualAssetService
- Speech voice profiles/references

### Acceptance Criteria

- Imported assets become media records.
- Matching proposals are reviewable.
- Apply validates same worldline.
- Visual/speech bindings reuse existing visual and speech services.

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- asset matching fixture tests
- media/visual/speech validation tests
- no storage URI/path leak tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.

## Phase 8 — Authoring Regression Fixture

### Goal

Create a small galgame import fixture for regression of scripts, characters, relationships, assets, memory migration, proposal review, and apply behavior.

### Scope

- Script fixture
- Character fixture
- Relationship fixture
- Lore proposal fixture
- Asset fixture
- Memory migration fixture
- Review/apply fixture

### Non-goals

- Production seed framework
- Quality benchmark for all content

### Reused Systems

- test fixture patterns
- multimodal sample-world regression
- Phase 1 authoring core

### Acceptance Criteria

- Fixture can be created deterministically.
- Import pipeline can pass expected scenarios.
- No raw source leaks into runtime/event payloads.
- Proposal-only lore behavior is covered.

### Stop Conditions

- Architecture conflict with current OpenSpec specs or Phase 13 ADRs.
- Migration conflict or unexpected schema requirement not covered by this phase.
- Provider boundary, secret boundary, storage path, raw prompt/output, or worldline isolation risk.
- Scope creep into a listed non-goal.
- Targeted tests or full local gate fail during implementation.

### Expected Validation

- authoring regression tests
- leak tests
- no duplicate media/provider/memory framework tests
- git diff --check

### Expected Deliverables

- Phase planning checkpoint document if implementation begins.
- Focused implementation commit or commits for this phase only.
- Updated OpenSpec tasks and harness docs after implementation.
- Targeted tests and full local gate evidence.
