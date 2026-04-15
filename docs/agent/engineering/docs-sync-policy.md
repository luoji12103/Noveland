# Documentation Sync Policy

## When docs must be updated

Update docs when changing:
- repository structure
- plugin interfaces
- event or snapshot semantics
- auth or ownership model
- environment variables
- key API contracts
- test strategy
- handoff policy

## Minimum sync rule

If a future coding agent would make a wrong decision because docs are outdated, the change is not complete.

## Canonical sources

- architecture docs are canonical for structure and boundaries
- harness docs are canonical for working state and workflow
- ADRs are canonical for major decisions
