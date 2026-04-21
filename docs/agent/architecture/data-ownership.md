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
- world/scene-scoped conversation transcripts

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
- `user_credentials` stores local user password hashes.
- `auth_sessions` stores backend-owned opaque session records and token hashes.
- `platform_role_assignments` stores platform-level role grants.
- `platform_settings` stores non-secret platform configuration values.
- `worlds`, `world_memberships`, and `scenes` establish world ownership, membership, and location boundaries.
- `agents` stores world-scoped agent identity basics only, not runtime state, memory, or private calendars.
- `agent_personas` stores one world-scoped persona/policy record per agent.
- `agent_observations` stores filtered, agent-scoped derived observations from stable world events and operator notes.
- `conversation_sessions` stores world/scene-scoped conversation objectives, mode, status, and turn cursor state.
- `conversation_participants` stores enabled agent participant ordering for each conversation session.
- `conversation_turns` stores append-only operator and agent transcript turns, including optional run linkage and failure text.
- `world_clock_states` stores world-owned operational clock state, with one current state row per world.
- `world_clock_transitions` stores world-owned operational audit records for clock state changes.
- `world_events` stores the append-only world event stream.
- `world_snapshots` stores world-owned snapshot metadata, inline diagnostic payloads, and future object-storage payload references.
- `agent_calendar_entries` stores private, world-scoped agent calendar items.
- `world_schedule_rules` stores world-owned weekday/weekend/timetable rule configuration.
- `agent_memory_items` stores private, world-scoped agent memory records, embeddings, and optional source-event linkage.
- `provider_profiles` stores non-secret provider configuration records, reliability controls, test-call health metadata, and API key references.
- `runtime_control_states` stores platform-owned runtime desired state and daemon heartbeat metadata.
- `agent_runtime_runs` stores world-scoped operational run history, prompt/response content, and diagnostics for agent executions.
- `narrative_artifacts` stores world-scoped narrative outputs linked to optional agents and runtime runs.
- `runtime_diagnostic_events` stores operational diagnostic events for runtime, provider, agent, event publisher, and API surfaces; diagnostic details must be redacted and are not canonical world events.
- Plugin registry persistence remains deferred to a separate task.

## Ownership rules

- A world may read its own events and state.
- An agent may read only its own private resources plus allowed observations.
- The narrative pipeline reads from authorized summaries/events, not arbitrary private internals.
- Cross-world access is forbidden by default.
