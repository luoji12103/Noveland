# Code Change Policy

## Small change

Examples:
- local bug fix
- non-structural refactor
- test update

Required:
- change or debug journal
- tests
- handoff update

## Structural change

Examples:
- new module
- new plugin category
- event schema change
- auth boundary change

Required:
- architecture doc update
- file inventory update
- project index update
- ADR or decision log entry
- tests
- handoff update

## Stop condition

If the requested work requires breaking a documented architecture boundary, stop and ask before improvising.
