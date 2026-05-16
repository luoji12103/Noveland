# Self-use MVP Gate

## ADDED Requirements

### Requirement: Self-use gate validates a 30-minute play loop
The system SHALL provide a self-use MVP gate that validates the developer can play a demo world for about 30 minutes with sustained conversation, state persistence, memory retention, visual presentation, speech support, and inspectable failures.

#### Scenario: Gate passes
- **Given** the demo world has at least two interactive characters, initial memory, visual mappings, voice mappings, and provider settings
- **When** the self-use gate runs after a play session
- **Then** it SHALL report pass evidence for entry, conversation continuity, memory persistence, visual/speech follow-through, provider health, and resume state.

### Requirement: Gate failures are actionable and safe
The system SHALL block the self-use gate when required provider, memory, visual, speech, conversation, or resume evidence is missing and SHALL return actionable safe reasons.

#### Scenario: Provider failure
- **Given** a provider fails during the demo session
- **When** the gate evaluates the session
- **Then** it SHALL report the failure with safe provider, model, capability, status, and ledger references
- **And** it SHALL NOT expose resolved secrets, raw prompts, raw outputs, storage paths, bytes, or base64.

### Requirement: Gate evidence does not imply beta readiness
The system SHALL distinguish the self-use MVP gate from private beta and public launch readiness.

#### Scenario: Self-use passes
- **Given** the self-use MVP gate passes
- **When** the operator requests beta readiness
- **Then** the system SHALL require later v1.0 private beta checks rather than treating self-use evidence as beta acceptance.

## Non-goals

- Public launch gate replacement.
- Private beta acceptance.
- Automatic provider fallback or load balancing.
