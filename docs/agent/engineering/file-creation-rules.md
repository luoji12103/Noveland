# File Creation Rules

## Allowed

- Add files inside existing domain directories when the role is clear.
- Add tests beside the relevant test area.
- Add migrations under `backend/migrations/`.
- Add templates and governance docs under `docs/agent/`.
- Add plugin implementations under the approved adapter/plugin locations.

## Forbidden

- Creating new top-level directories without architecture updates first
- Leaving debug exports or one-off scripts in production directories
- Creating a second utility layer because the first one is inconvenient
- Writing files named `tmp`, `temp`, `new`, `final`, `v2`, `copy`
- Adding business logic to experimental directories and then depending on it from production code

## Structural changes

Any structural file or directory addition requires:
- architecture doc review
- file inventory update
- project index update
- change journal update
