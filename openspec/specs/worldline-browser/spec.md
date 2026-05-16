# Worldline Browser Specification

## Purpose

This spec captures the current v0.8 read-only worldline browser on `main`. It covers safe branch listing, read-only comparison summaries, visibility enforcement, and strict preservation of branch-scoped media, presentation, and player state.

## Requirements
### Requirement: Worldline browser is read-only first
The system SHALL provide worldline list/tree and comparison views without executing rollback, merge, or branch switching in the first implementation scope.

#### Scenario: Authorized branch comparison
- **Given** an authorized actor can access two worldlines in the same world
- **When** they compare the branches
- **Then** the system SHALL return safe summaries of state differences
- **And** it SHALL NOT mutate either worldline.

### Requirement: Browser enforces worldline visibility
The system SHALL enforce ACL and worldline visibility for reader/member/player views.

#### Scenario: Reader lacks branch access
- **Given** a reader is not allowed to view a private branch
- **When** they request the worldline tree
- **Then** the private branch SHALL be omitted or denied
- **And** no branch-specific hidden media or presentation data SHALL leak.

### Requirement: Browser preserves strict-worldline media and presentation state
The system SHALL keep visual bindings, presentation records, player records, and publications scoped to their original worldline in comparison output.

#### Scenario: Branch-specific sprite state
- **Given** two worldlines have different sprite variants for a character
- **When** comparison output is generated
- **Then** each variant SHALL remain attributed to its own worldline.

### Requirement: Worldline browser has explicit acceptance evidence
The implementation SHALL include read-only, ACL, comparison, and isolation tests.

#### Scenario: Phase acceptance
- **Given** Worldline Browser implementation is complete
- **When** targeted tests and the full local gate run
- **Then** all checks SHALL pass before fast-forward merge.

## Non-goals

- Unsafe destructive rollback.
- Branch merge.
- Switch execution without explicit later approval.
