# Player Interaction UI

## Capability

Expose choices, interventions, journal, notifications, and route feedback to players. This capability belongs to v0.8 Public Experience & Ecosystem and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Player Interaction UI provides the planned workflow
The system SHALL provide Player Interaction UI capability for Choice UI, Intervention UI, Player journal, Notifications while preserving worldline, ACL, provider, media, secret, and invocation boundaries.

#### Scenario: Authorized workflow
- **Given** an authorized actor is using Player Interaction UI
- **When** they perform the primary workflow for this capability
- **Then** the system SHALL support the planned scope
- **And** the workflow SHALL reuse future player choice records, world events, notifications rather than creating a parallel subsystem.

### Requirement: Player Interaction UI preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for Player Interaction UI, including safe event payloads, secret redaction, media boundary reuse, and reader/member visibility filtering.

#### Scenario: Boundary enforcement
- **Given** Player Interaction UI reads or writes provider, media, invocation, visual, speech, event, or presentation data
- **When** the capability returns API/UI data or persists records
- **Then** it SHALL NOT expose resolved secrets, storage_uri, filesystem paths, bytes, base64, raw prompts, or raw outputs
- **And** it SHALL validate world and worldline scope where applicable.

### Requirement: Player Interaction UI has explicit acceptance evidence
The system SHALL provide focused validation for Player Interaction UI and SHALL stop implementation if targeted tests, full local gate, or architecture checks fail.

#### Scenario: Phase acceptance
- **Given** implementation for Player Interaction UI is complete
- **When** targeted validation and the full local gate run
- **Then** all expected validation checks SHALL pass
- **And** the phase SHALL be merged only by fast-forward to clean local main.

## Non-goals

- Admin diagnostics in player UI
