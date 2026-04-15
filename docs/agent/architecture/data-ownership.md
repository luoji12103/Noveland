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

## Initial persistence baseline

- `users` stores platform user identity basics only, not passwords or sessions.
- `platform_settings` stores non-secret platform configuration values.
- `worlds`, `world_memberships`, and `scenes` establish world ownership, membership, and location boundaries.
- `agents` stores world-scoped agent identity basics only, not runtime state, memory, or private calendars.
- `world_clock_states` stores world-owned operational clock state, with one current state row per world.
- `world_clock_transitions` stores world-owned operational audit records for clock state changes.
- Event streams, snapshots, plugin registry data, sessions, calendars, memory vectors, and narrative artifacts are intentionally deferred to separate migrations.

## Ownership rules

- A world may read its own events and state.
- An agent may read only its own private resources plus allowed observations.
- The narrative pipeline reads from authorized summaries/events, not arbitrary private internals.
- Cross-world access is forbidden by default.
