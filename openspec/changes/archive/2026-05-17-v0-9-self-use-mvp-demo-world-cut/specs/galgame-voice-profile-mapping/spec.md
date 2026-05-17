# Galgame Voice Profile Mapping

## ADDED Requirements

### Requirement: Imported voice references map to voice profiles
The system SHALL map imported voice references or configured speech provider voice IDs to voice profiles, agent voice bindings, and emotion/style mappings through review/apply.

#### Scenario: Voice profile is bound
- **Given** a character has imported voice references or a configured provider voice ID
- **When** an authorized operator applies a voice mapping proposal
- **Then** the character's agent SHALL have a voice profile binding
- **And** the binding SHALL preserve world and worldline scope.

### Requirement: MiMo and generic speech settings remain configurable
The system SHALL support MiMo V2.5 TTS/ASR and generic TTS/STT provider configuration without hardcoded base URLs.

#### Scenario: MiMo provider through custom gateway
- **Given** an operator configures a MiMo-compatible provider through a custom `base_url`
- **When** they run a TTS smoke test
- **Then** the call SHALL use the configured provider settings and `auth_ref`
- **And** no API key SHALL appear in API responses, logs, prompt snapshots, or event payloads.

### Requirement: Voice output attaches through media references
The system SHALL store generated speech output through the speech and media systems.

#### Scenario: TTS output is generated
- **Given** a character has a valid voice profile
- **When** TTS generation succeeds
- **Then** the resulting audio SHALL be represented as media asset/object records with safe references
- **And** conversation playback SHALL use reader-safe media delivery.

## Non-goals

- Hardcoded MiMo endpoint.
- Client-side speech provider secrets.
- Replacement speech pipeline.
