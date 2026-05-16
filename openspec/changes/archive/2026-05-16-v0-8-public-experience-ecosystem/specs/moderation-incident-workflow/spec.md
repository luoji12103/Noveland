# Moderation & Incident Workflow

## Capability

Support report review, rollback review, disable actions, and public-surface incident records without automatic public moderation. This capability belongs to v0.8 Public Experience & Ecosystem and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Moderation implementation requires schema/router decision
The system SHALL resolve moderation record ownership, router boundary, and audit semantics before implementation begins.

#### Scenario: Phase checkpoint
- **Given** Phase 10 is selected for implementation
- **When** the docs-only checkpoint is written
- **Then** it SHALL decide whether moderation lives in a dedicated package/router or extends observability
- **And** implementation SHALL stop if ownership remains unclear.

### Requirement: Reports become reviewable records
The system SHALL convert reader/player/admin reports into reviewable records with safe status, actor refs, target refs, and redacted evidence refs.

#### Scenario: Reader reports content
- **Given** a reader reports a scene or publication
- **When** the report is recorded
- **Then** moderators SHALL see a reviewable record
- **And** raw prompts, storage paths, resolved secrets, and private hidden content SHALL not be embedded in the report payload.

### Requirement: Moderator actions are audited and bounded
The system SHALL support reviewed disable or rollback-review actions with ACL protection and safe audit summaries.

#### Scenario: Moderator disables a provider
- **Given** a platform admin disables a risky provider integration
- **When** the action is recorded
- **Then** the audit SHALL reference the provider and reason safely
- **And** it SHALL not expose provider secrets.

### Requirement: Moderation workflow has explicit acceptance evidence
The implementation SHALL include ACL, evidence-redaction, audit, disable, and rollback-review tests.

#### Scenario: Phase acceptance
- **Given** Moderation & Incident Workflow implementation is complete
- **When** targeted tests and the full local gate run
- **Then** all checks SHALL pass before fast-forward merge.

## Non-goals

- Automated public moderation without human review.
- Public exposure of internal incident evidence.
- Replacing v0.7 incident diagnostics.
