# Commit Convention

Use Conventional Commit style.

## Examples

- `feat(worlds): add world clock state model`
- `fix(events): preserve snapshot recovery metadata`
- `docs(agent): tighten file creation rules`
- `test(auth): add cross-world access regression case`
- `refactor(memory): isolate backend adapter wiring`

## Commit granularity

Commit after:
- a meaningful implementation step
- a debug resolution
- a completed test-backed fix
- a doc/governance update that changes agent behavior

Do not lump unrelated work into one commit.
