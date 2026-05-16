# Plugin/Provider Package Contract

## Capability

Define plugin/provider package metadata, capability schema, safe config export, and safety review without exposing secrets. This capability belongs to v0.8 Public Experience & Ecosystem and is planned future work until implemented and archived.

## ADDED Requirements

### Requirement: Packages declare capabilities and boundaries
The system SHALL represent package metadata with identifier, version, capability declarations, config schema, supported provider/media modes, and safety notes.

#### Scenario: Package metadata validation
- **Given** a provider adapter package declares image and speech capabilities
- **When** the package contract is validated
- **Then** the validator SHALL check capability names and adapter boundaries
- **And** it SHALL reject unknown secret-bearing config fields.

### Requirement: Package config export excludes secrets
The system SHALL export only safe config templates and `auth_ref` references, never resolved provider credentials.

#### Scenario: Export provider package config
- **Given** a provider integration has `auth_ref=env:OPENAI_API_KEY`
- **When** config is exported for a package
- **Then** the export MAY include the opaque auth reference
- **And** it SHALL NOT include the resolved environment value.

### Requirement: Package contracts reuse plugin and provider systems
The system SHALL reuse plugin catalog/binding validation, provider registry/capabilities, and `ProviderSecretResolver` rather than adding a provider marketplace or secret resolver.

#### Scenario: Plugin binding compatibility check
- **Given** a package declares a model-provider capability
- **When** it is checked against existing plugin/provider registries
- **Then** compatibility SHALL be reported through existing validation concepts where possible.

### Requirement: Package contract has explicit acceptance evidence
The implementation SHALL include package validation, provider governance, and secret-redaction tests.

#### Scenario: Phase acceptance
- **Given** Plugin/Provider Package Contract implementation is complete
- **When** targeted tests and the full local gate run
- **Then** all checks SHALL pass before fast-forward merge.

## Non-goals

- Provider marketplace.
- Runtime installation of untrusted code.
- Plugins resolving secrets directly.
