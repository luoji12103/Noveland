# Git Workflow

## Mainline policy

`main` is the only long-lived primary branch and should remain releasable.

## Working branches

- `feat/<scope>-<topic>`
- `fix/<scope>-<topic>`
- `docs/<scope>-<topic>`
- `refactor/<scope>-<topic>`
- `hotfix/<scope>-<topic>`
- `release/<version>` when release freezing becomes necessary

Branch names should describe the feature, outcome, or subsystem being changed. Do not name future branches after roadmap phase numbers.

## Strategy

- keep branches short-lived
- merge back to `main` quickly
- do not create long-term parallel product lines
- prefer readable history over maximal rebasing cleverness

## AI-agent rule

If a task crosses multiple modules or changes structure, use a branch.
If it is a small contained fix, a short branch is still preferred over direct `main` edits.
