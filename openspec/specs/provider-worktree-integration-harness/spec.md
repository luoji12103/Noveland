# Provider Worktree Integration Harness Specification

## Purpose
This spec captures the current v0.9 provider lab testing discipline on `main`. It covers default-skipped real-provider tests, opt-in provider lab worktree usage, fake/mocked default contract tests, and safe real-provider evidence handling.

## Requirements
### Requirement: Real provider tests are opt-in
The system SHALL keep real external provider tests disabled by default and SHALL require explicit opt-in environment variables or test profile configuration.

#### Scenario: Default local gate
- **Given** the default local gate runs without `NOVELAND_RUN_REAL_PROVIDER_TESTS=1`
- **When** provider integration tests execute
- **Then** real OpenAI-compatible, Anthropic-compatible, MiMo, Z-Image, GPT Image, and ComfyUI provider calls SHALL be skipped or mocked
- **And** no external quota SHALL be consumed.

### Requirement: Provider lab worktree is documented
The system SHALL document a separate provider lab workflow for real provider development, such as `git worktree add ../Noveland-provider-lab <branch>`.

#### Scenario: Operator follows provider lab setup
- **Given** an operator configures a provider lab worktree and required env vars
- **When** they run the provider lab tests
- **Then** smoke, model list, sample text, sample TTS, sample ASR, and sample image checks SHALL run through existing provider services
- **And** secrets SHALL NOT be printed, committed, or persisted in unsafe records.

### Requirement: Provider lab evidence is safe
The system SHALL record only safe real-provider evidence suitable for debugging.

#### Scenario: Real provider call fails
- **Given** an opt-in real provider test fails
- **When** failure evidence is reported
- **Then** the report SHALL include provider kind, model name, capability, status, and safe error class
- **And** it SHALL NOT include resolved secrets, raw credentials, raw prompts, or storage paths.
