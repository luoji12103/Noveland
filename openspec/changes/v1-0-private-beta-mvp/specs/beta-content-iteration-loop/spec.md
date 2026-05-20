# Beta Content Iteration Loop

## ADDED Requirements

### Requirement: Repair proposal ownership is decided before implementation
The system SHALL complete a docs-only checkpoint before implementing the beta content iteration loop.
The checkpoint SHALL confirm that content repair reuses authoring proposal/review/apply unless an
explicit OpenSpec revision approves a narrower repair boundary.

#### Scenario: Repair checkpoint runs
- **Given** v1.0 Phase 7 is selected for implementation
- **When** the checkpoint is written
- **Then** it SHALL define how beta feedback and QA diagnostics link to repair proposals
- **And** it SHALL stop implementation if repairs would bypass preview/review/apply.

### Requirement: Feedback and diagnostics create repair proposals
The system SHALL convert beta feedback and diagnostics into reviewable repair proposals for persona, memory, dialogue style, visual mapping, voice mapping, or route issues.

#### Scenario: OOC feedback becomes proposal
- **Given** feedback reports an out-of-character response
- **When** an admin creates a repair candidate
- **Then** the system SHALL create a reviewable persona or memory repair proposal
- **And** it SHALL preserve links to the original feedback and safe evidence refs.

#### Scenario: Provider or visual profile repair is proposed
- **Given** feedback identifies a provider prompt, visual generation profile, or voice/style issue
- **When** an admin creates a repair candidate
- **Then** the system SHALL create a reviewable proposal using the existing owning package boundary
- **And** it SHALL NOT let provider output directly mutate world state.

### Requirement: Repair apply is audited and non-destructive
The system SHALL apply repair proposals only after explicit review and SHALL NOT rewrite history destructively.

#### Scenario: Repair is applied
- **Given** an admin approves a memory repair proposal
- **When** apply runs
- **Then** the system SHALL create or update allowed target records through existing services
- **And** it SHALL keep an audit trail and source/feedback traceability.

### Requirement: Repair respects worldline isolation
The system SHALL reject repair proposals that mix worldlines or worlds.

#### Scenario: Repair references another worldline
- **Given** a repair proposal references a memory from another worldline
- **When** apply is requested
- **Then** the system SHALL reject the apply action with a safe error.

### Requirement: Repair bridge reuses authoring
The system SHALL reuse authoring import runs, proposals, review decisions, and apply records for
beta content repair instead of adding a duplicate repair framework.

#### Scenario: Repair bridge creates an authoring run
- **Given** an admin creates repair candidates from beta feedback
- **When** the bridge persists the repair work
- **Then** it SHALL create an authoring preview import run
- **And** it SHALL create proposed authoring import proposals
- **And** it SHALL link feedback reports to safe repair proposal refs
- **And** it SHALL NOT mutate persona, memory, visual, speech, provider, or world state.

## Non-goals

- Automatic repair apply.
- Historical rewrite.
- Replacement authoring proposal system.
