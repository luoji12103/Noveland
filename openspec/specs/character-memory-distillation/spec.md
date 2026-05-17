# Character Memory Distillation Specification

## Purpose
This spec captures the current v0.9 character memory distillation path on `main`. It covers traceable source-driven persona cards, memory candidates, provider-backed distillation evidence, and explicit review/apply before agent persona or memory records are changed.

## Requirements
### Requirement: Distillation produces persona cards and memory candidates
The system SHALL use traceable source fragments to create reviewable persona cards, speech style summaries, relationship summaries, key memories, emotional baselines, taboo/secret knowledge, route-specific facts, sample dialogue style, and uncertainty notes.

#### Scenario: Persona candidate generation
- **Given** a character has reviewed source dialogue fragments
- **When** the distillation agent runs
- **Then** it SHALL create persona and memory proposals linked to the source fragments
- **And** the character SHALL NOT be modified until an authorized review/apply step succeeds.

### Requirement: Distillation uses provider execution safely
The system SHALL run provider-backed distillation through the provider kernel and SHALL write invocation ledger evidence.

#### Scenario: Provider-backed distillation
- **Given** provider-backed distillation is enabled
- **When** a model call is made
- **Then** it SHALL record `model_invocations` and `prompt_snapshots`
- **And** responses, event payloads, and reader/member APIs SHALL NOT expose resolved secrets, storage paths, raw prompts, raw outputs, bytes, or base64.

### Requirement: Memory apply is explicit and traceable
The system SHALL write initial persona and memory only after explicit review/apply and SHALL preserve traceability back to source fragments.

#### Scenario: Apply memory candidates
- **Given** memory proposals have been reviewed and selected
- **When** an authorized operator applies them
- **Then** the target agent SHALL receive non-empty persona or memory entries
- **And** each applied entry SHALL retain source evidence references.
