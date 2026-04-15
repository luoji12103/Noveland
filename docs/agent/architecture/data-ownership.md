# Data Ownership

## Platform-owned data

- users
- admin accounts
- global settings
- provider defaults
- global plugin configuration

## World-owned data

- world config
- world rules configuration
- scenes/locations
- world event stream
- world snapshots
- world-level runtime state

## Agent-owned data

- agent profile
- persona binding
- private memory namespace
- private calendar
- runtime state scoped to that agent

## Narrative-owned data

- summaries
- chapter drafts
- published narrative artifacts
- artifact metadata

## Ownership rules

- A world may read its own events and state.
- An agent may read only its own private resources plus allowed observations.
- The narrative pipeline reads from authorized summaries/events, not arbitrary private internals.
- Cross-world access is forbidden by default.
