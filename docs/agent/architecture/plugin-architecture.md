# Plugin Architecture

## Why plugins exist

To allow stable extension points without rewriting the kernel.

## v1 plugin categories

- model provider
- memory backend
- world rules / schedule rules
- persona / behavior policy
- narrative writer / summarizer

## Loading policy

- code-registered plugins only
- enabled by configuration
- no hot loading or remote marketplace in v1

## Current registry skeleton

- plugin definitions are registered in code through `PluginRegistry`
- identifiers are globally unique lowercase slug or dotted strings
- enabled plugin resolution accepts configured identifiers but does not persist registry state
- category-specific runtime method contracts are intentionally deferred
- plugin failures currently surface through typed exceptions; admin diagnostics and logging integration are later work

## Current runtime wiring

- `model_provider` bindings are resolved from provider profiles and validated through `PluginRegistry` before provider invocation.
- `memory_backend` bindings are resolved behind `MemoryService`; business code uses the service facade, not backend SDK or adapter types directly.
- `world_rules` bindings govern schedule-resolution wiring for world-owned rules.
- `persona_policy` bindings shape agent prompt construction, including memory context integration.
- `narrative_writer` bindings drive conversation-first summary and chapter generation.
- Built-in implementations remain code-registered first-party plugins; there is still no marketplace, hot loading, or dynamic code upload path.

## Required plugin shape

Each plugin should define:
- identifier
- category
- version
- config schema
- capability declaration
- implementation binding

## Registry rules

- all plugins must be registered through the central registry
- no direct ad hoc plugin discovery in business logic
- plugin config validation is mandatory
- plugin failures must be visible in logs and admin diagnostics
- no remote plugin discovery or filesystem scanning is allowed in v1

## Contract testing

Every plugin category must have contract tests.
