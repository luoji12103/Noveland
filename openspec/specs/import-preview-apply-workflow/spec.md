# Import Preview/Apply Workflow Specification

## Purpose

This spec captures current v0.5 import run, proposal, review decision, source traceability, preview, and guarded trace-only apply behavior.

## Requirements

### Requirement: Import runs group reviewable authoring work
The system SHALL store authoring import runs with non-null `world_id`, `worldline_id`, optional source batch linkage, run kind, status, summary JSON, and actor reference.

#### Scenario: Import run is created
- **GIVEN** a world admin creates an import run for a source batch
- **WHEN** the batch and worldline belong to the same worldline
- **THEN** the run SHALL be persisted
- **AND** subsequent proposals SHALL be linked to that run.

### Requirement: Preview creates traceable proposals without provider execution
The system SHALL allow preview requests to create authoring proposals linked to an import run and optional source fragment.

#### Scenario: Preview creates proposals
- **GIVEN** a world admin submits proposal drafts to an import run preview endpoint
- **WHEN** the preview succeeds
- **THEN** the run status SHALL become `previewed`
- **AND** summary JSON SHALL record `provider_execution` as `false`
- **AND** source traceability SHALL be written for fragment-backed proposals.

### Requirement: Proposal review records explicit admin decisions
The system SHALL store review decisions for proposals and update proposal status based on the decision.

#### Scenario: Proposal is approved
- **GIVEN** a proposed authoring import proposal exists
- **WHEN** a world admin reviews it with an approve decision
- **THEN** a review decision record SHALL be created
- **AND** the proposal status SHALL become `approved`.

### Requirement: Apply is selective and trace-only
The system SHALL apply only selected, approved proposals and SHALL only perform trace-only apply for supported proposal kinds.

#### Scenario: Unsupported proposal is applied
- **GIVEN** an approved proposal has a proposal kind that is not supported for trace-only apply
- **WHEN** an admin includes it in apply
- **THEN** the proposal SHALL become `blocked`
- **AND** the blocked reason SHALL be recorded safely in `applied_ref_json`
- **AND** no canonical world, media, visual, speech, memory, provider, or event mutation SHALL occur.

### Requirement: Apply records safe traceability
The system SHALL write source traceability when proposals are created, reviewed, applied, or blocked.

#### Scenario: Trace-only proposal is applied
- **GIVEN** an approved trace-only proposal is selected for apply
- **WHEN** apply succeeds
- **THEN** the proposal SHALL become `applied`
- **AND** the applied reference SHALL point to the authoring proposal itself
- **AND** `canonical_mutation` SHALL be `false`.

## Non-goals

- This spec does not define automatic canonical mutation for dialogue, character, lore, asset, or memory proposals.
- This spec does not define rollback execution.
- This spec does not define provider-backed apply.
- This spec does not define unbounded batch mutation.
