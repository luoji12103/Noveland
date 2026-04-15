# ADR-0002: World-Kernel-First Architecture

## Status
Accepted

## Context
The product is a persistent world system, not a generic agent workflow product.

## Decision
The world kernel is the primary authority for time, scenes, rules, and state transitions. Agents consume filtered observations and propose actions.

## Consequences
This prevents world logic from leaking into prompts. It requires more kernel design upfront.
