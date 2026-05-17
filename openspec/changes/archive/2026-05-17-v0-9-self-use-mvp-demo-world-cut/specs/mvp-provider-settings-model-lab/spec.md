# MVP Provider Settings & Model Lab

## ADDED Requirements

### Requirement: Provider settings expose configurable model templates
The system SHALL provide settings/admin-facing provider templates for OpenAI-compatible LLM, Anthropic-compatible LLM, MiMo V2.5 TTS, MiMo V2.5 ASR, generic TTS/STT, Z-Image, GPT Image, ComfyUI, and generic image API providers.

#### Scenario: Configure compatible provider
- **Given** an authorized operator opens provider settings
- **When** they create a provider from a compatible template with custom `base_url`, `auth_ref`, `model_name`, capability flags, and adapter kind
- **Then** the provider SHALL be saved through the existing provider integration boundary
- **And** the response SHALL include only safe references, never resolved secrets.

### Requirement: Provider settings support model discovery and manual fallback
The system SHALL allow operators to pull model lists when a provider exposes a compatible discovery endpoint and manually enter model names when discovery fails or is unavailable.

#### Scenario: Model discovery fails
- **Given** a provider template has a configured model discovery strategy
- **When** the model list request fails
- **Then** the operator SHALL be able to enter a model name manually
- **And** the failed discovery SHALL produce safe health or smoke evidence without leaking credentials.

### Requirement: Image provider settings expose generation-control capability metadata
The system SHALL let image provider templates declare supported visual generation controls such as text-to-image, image-to-image, edit, inpaint, reference images, mask images, workflow templates, LoRA slots, checkpoint slots, seed, size, sampler, and output format.

#### Scenario: Configure image provider capabilities
- **Given** an authorized operator configures a ComfyUI, Z-Image, GPT Image, OpenAI-compatible image, or generic image provider
- **When** they save capability metadata
- **Then** the provider SHALL expose safe capability flags to the visual generation planner
- **And** unsupported controls SHALL be rejected or omitted before adapter execution.

### Requirement: Provider test actions preserve secret and ledger boundaries
The system SHALL run explicit provider tests and smoke checks through the provider kernel and SHALL record safe invocation or health evidence.

#### Scenario: Smoke test runs
- **Given** an authorized operator runs a provider smoke check
- **When** the provider adapter receives a resolved secret
- **Then** the secret SHALL remain in memory only
- **And** API responses, logs, prompt snapshots, and `world_events.payload` SHALL NOT include API keys, authorization headers, storage paths, raw prompts, raw outputs, bytes, or base64.

## Non-goals

- Hardcoded official vendor base URLs.
- Client-side API keys.
- Provider marketplace.
- New provider execution framework.
- Image workflow editor.
