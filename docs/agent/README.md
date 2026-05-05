# `/docs/agent` README

This directory is the canonical pre-build architecture and governance package for the coding agent.

It exists to keep the project stable while the implementation is still evolving. Read this before changing code, structure, or workflow.

## Read order for a new session

1. `foundations/product-restatement.md`
2. `foundations/mvp-definition.md`
3. `architecture/architecture-map.md`
4. `architecture/repository-layout.md`
5. `engineering/file-creation-rules.md`
6. `git/workflow.md`
7. `harness/project-index.md`
8. `harness/roadmap.md`
9. `harness/roadmap-v2-living-world.md`
10. `operations/runtime-recovery.md`
11. `harness/handoffs/active-session.md`

## Project stance

- World-kernel first, not chatbot-first
- Modular monolith first, not microservices-first
- Plugin-first interfaces, but not a plugin marketplace
- Stable directories, stable contracts, stable handoff discipline
- English is canonical for this package

## Non-negotiable rules

- Do not invent new top-level directories without updating the architecture docs.
- Do not implement outside the documented MVP unless explicitly instructed.
- Do not create parallel utility layers.
- Do not leave temporary files inside production directories.
- Do not change core event, snapshot, auth, world-clock, or plugin registry behavior without updating docs and decision records.
- Do not end a session without updating handoff and logs.

## Canonical working files

- `harness/project-index.md`
- `harness/file-inventory.md`
- `harness/ownership-map.md`
- `harness/roadmap.md`
- `harness/roadmap-v2-living-world.md`
- `harness/task-board.md`
- `harness/change-journal.md`
- `harness/debug-journal.md`
- `harness/handoffs/active-session.md`
- `operations/runtime-recovery.md`

## Definitions

- **Canonical**: source of truth unless replaced by a later ADR or explicit decision log entry.
- **Derived**: generated or archival content; do not edit first.
- **Sensitive area**: high-risk area that requires doc review before changes.

## Completion checklist for the coding agent

Before considering work complete:

- code updated
- tests added or updated
- relevant docs updated
- change or debug journal updated
- task board updated
- active handoff updated
