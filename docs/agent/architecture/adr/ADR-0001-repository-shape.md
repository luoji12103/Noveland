# ADR-0001: Repository Shape

## Status
Accepted

## Context
The project needs strong governance for AI-assisted development and must prevent top-level sprawl and parallel architectures.

## Decision
Use a small fixed top-level layout with separate `web/`, `backend/`, `contracts/`, `infra/`, and `docs/agent/` directories.

## Consequences
This keeps file growth controlled and makes handoff simpler. It requires developers to be deliberate before introducing new structural areas.
