## Context

The current Web app has admin and reader surfaces, and the backend has long-run eval and multimodal diagnostics. Future beta work should make these usable for living-world operations without duplicating release evidence systems.

## Goals / Non-Goals

Goals:

- Provide world state dashboard and player story journal requirements.
- Define in-world notifications and intervention controls.
- Add GM safety/style and narrative continuity review.
- Plan route endings and long-run simulation evaluations.
- Improve authoring imports/templates and release profile evidence.

Non-goals:

- Public launch gate changes in this planning stage.
- External observability exporter.
- Human scoring platform.
- Provider marketplace.

## Decisions

- Reuse existing release/eval evidence tables and diagnostics patterns.
- Extend existing Web routes rather than creating a separate app.
- Keep player-facing data filtered by ACL and knowledge visibility.
- Use sample worlds as regression fixtures, not production seed systems.

## Risks / Trade-offs

- Web scope can sprawl. Mitigation: route each surface to concrete backend contracts.
- Release evidence can duplicate diagnostics. Mitigation: reuse long-run eval and checklist patterns.
- Beta content quality can become subjective. Mitigation: separate contract regression from qualitative review.

## Migration Plan

This proposal is planning-only. Future implementation should start with diagnostics and author/admin review surfaces before player-facing beta flows.

## Open Questions

- Which beta checklist fields should become hard local gate checks.
- Whether authoring imports should support only structured templates first.
