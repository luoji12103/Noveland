# Beta Content Iteration Loop

## ADDED Requirements

### Requirement: Feedback and diagnostics create repair proposals
The system SHALL convert beta feedback and diagnostics into reviewable repair proposals for persona, memory, dialogue style, visual mapping, voice mapping, or route issues.

#### Scenario: OOC feedback becomes proposal
- **Given** feedback reports an out-of-character response
- **When** an admin creates a repair candidate
- **Then** the system SHALL create a reviewable persona or memory repair proposal
- **And** it SHALL preserve links to the original feedback and safe evidence refs.

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

## Non-goals

- Automatic repair apply.
- Historical rewrite.
- Replacement authoring proposal system.
