# Provider System Specification

## Purpose

This spec captures the current provider execution kernel, secret boundary, provider registry, health/smoke validation, invocation ledger integration, and adapter families.

## Requirements

### Requirement: Provider registry stores integrations and capabilities
The system SHALL store provider integrations, provider capabilities, and provider health checks in the provider registry.

#### Scenario: Provider capability routing
- **GIVEN** a provider integration declares a capability and an adapter kind
- **WHEN** a provider-backed request is routed
- **THEN** routing SHALL use the configured `adapter_kind`
- **AND** it SHALL validate the requested capability before execution.

### Requirement: Provider execution writes invocation evidence
The system SHALL create `model_invocations` and `prompt_snapshots` for provider-backed calls, including failed calls.

#### Scenario: Failed provider call
- **GIVEN** a provider request fails because of missing auth, unsupported capability, timeout, malformed response, or upstream error
- **WHEN** the provider execution service handles the failure
- **THEN** a failed invocation record SHALL exist
- **AND** prompt snapshot evidence SHALL be safe and redacted.

### Requirement: Provider secrets are resolved at execution time
The system SHALL resolve supported `auth_ref` formats such as environment references and known aliases only in memory.

#### Scenario: Missing environment secret
- **GIVEN** a real provider integration references an unset environment variable
- **WHEN** health check or smoke test execution runs
- **THEN** the result SHALL report safe auth-missing status
- **AND** it SHALL NOT persist a stack trace containing secret material.

### Requirement: Provider config rejects secret-like fields
The system SHALL reject or sanitize secret-like keys in provider config, default params, health metadata, smoke request payloads, prompt snapshots, and API responses.

#### Scenario: Secret-like config value
- **GIVEN** a provider create or update request contains `api_key`, `token`, `authorization`, `secret`, `client_secret`, `access_key`, `password`, or `private_key` in nested config
- **WHEN** the registry validates the request
- **THEN** it SHALL reject the request or prevent the value from being persisted.

### Requirement: Fake and real adapter families share the execution layer
The system SHALL support fake provider flows plus OpenAI image, OpenAI-compatible image, ComfyUI, OpenAI speech, MiMo TTS/ASR, OmniVoice, GPT-SoVITS, and custom HTTP-style speech adapters through provider execution contracts.

#### Scenario: Fake media output
- **GIVEN** a fake provider produces image or audio output
- **WHEN** the execution completes
- **THEN** it SHALL write invocation evidence
- **AND** it SHALL create appropriate media job, asset, object, and reference records.

### Requirement: Provider APIs enforce admin-scoped access
The system SHALL restrict provider management, health, smoke test, and test invocation routes to appropriate world or platform admin actors.

#### Scenario: Member attempts provider management
- **GIVEN** a world member without provider management authority
- **WHEN** they call provider management routes
- **THEN** the API SHALL deny the request
- **AND** no provider secrets or config metadata SHALL be disclosed.

## Non-goals

- This spec does not define provider marketplace behavior.
- This spec does not define provider fallback, load balancing, or streaming.
- This spec does not define encrypted DB secret storage.
- This spec does not require live provider tests unless explicitly enabled by environment.
