# Demo World Assembly

## ADDED Requirements

### Requirement: Demo assembly creates a minimal playable world
The system SHALL assemble a minimal demo world from reviewed source, dialogue, persona, memory, visual, voice, visual generation profile, and conversation proposals.

#### Scenario: Assemble demo world
- **Given** reviewed proposals exist for at least two characters, one initial conversation path, backgrounds, sprites, voices, visual generation profiles, and initial memories
- **When** an authorized operator applies demo assembly
- **Then** the system SHALL create or update the demo world/worldline with traceable agents, conversation state, presentation assets, and initial memories
- **And** no unsupported proposal SHALL be applied.

### Requirement: Demo assembly preserves source traceability
The system SHALL maintain source evidence references for applied persona, memory, dialogue, visual, visual generation profile, and voice outputs.

#### Scenario: Inspect applied character memory
- **Given** a demo character has applied memory entries
- **When** an admin inspects the memory evidence
- **Then** each entry SHALL link back to safe source evidence references
- **And** reader/player APIs SHALL NOT expose raw source fragments or storage paths.

### Requirement: Demo world can be entered without manual database edits
The system SHALL provide an approved path to enter the assembled demo world without developer-only database changes.

#### Scenario: Enter demo world
- **Given** demo assembly has completed
- **When** the developer enters the world through the supported surface
- **Then** the initial conversation SHALL be available
- **And** presentation, visual, visual generation plan, speech, memory, and provider state SHALL have inspectable safe status.

## Non-goals

- Private beta onboarding.
- Public launch readiness.
- Perfect content quality.
