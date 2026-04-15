# Release Policy

## Early phase

Use tags on `main` for notable milestones.

## Later phase

If release stabilization becomes necessary:
- branch `release/<version>`
- allow only release fixes
- merge hotfixes back to `main`

## Hotfix rule

Hotfixes target released behavior only and must also be merged back to `main`.

## Versioning

Semantic versioning is recommended once public releases begin.
