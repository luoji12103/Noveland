## MODIFIED Requirements

### Requirement: Observability & Incident Diagnostics preserves architecture freeze boundaries
The system SHALL enforce Phase 13 architecture guardrails for observability work.

#### Scenario: Runtime diagnostic text and details redact sensitive values
- **Given** runtime diagnostics are recorded with message, event type, or detail values containing resolved secret-looking values, storage locators, filesystem paths, raw prompt/output markers, bytes, or base64
- **When** diagnostics are persisted or returned through admin runtime, world, conversation, or realtime diagnostics
- **Then** those sensitive values SHALL be redacted before storage and response shaping
- **And** existing stored diagnostics SHALL be redacted again on read before API/UI output.
