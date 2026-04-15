You are the coding agent for this repository.

Before changing code, read in order:
1. `/docs/agent/README.md`
2. `/docs/agent/foundations/product-restatement.md`
3. `/docs/agent/foundations/mvp-definition.md`
4. `/docs/agent/architecture/architecture-map.md`
5. `/docs/agent/architecture/repository-layout.md`
6. `/docs/agent/engineering/file-creation-rules.md`
7. `/docs/agent/git/workflow.md`
8. `/docs/agent/harness/project-index.md`
9. `/docs/agent/harness/handoffs/active-session.md`

Rules:
- Stay inside the MVP unless explicitly instructed otherwise.
- Do not invent new top-level directories.
- Do not create parallel architectures.
- Do not bypass plugin interfaces, event boundaries, or auth boundaries.
- Do not leave stray temp or debug files.
- If architecture assumptions break, stop and ask instead of improvising.

Before implementation, output:
- task interpretation
- impacted modules
- files expected to change
- tests to add/update
- docs/agent files to update

After implementation, update:
- change or debug journal
- task board
- active handoff
- any affected docs
