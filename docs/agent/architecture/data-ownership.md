# Data Ownership

## Platform-owned data

- users
- admin accounts
- global settings
- provider defaults
- global plugin configuration
- memory backend profiles
- memory backend write/retrieval audit logs

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
- agent profile snapshots
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
- `conversation_sessions` stores world/scene-scoped conversation objectives, mode, status, turn cursor state, policy config, writer config, and memory config.
- `conversation_participants` stores enabled agent participant ordering for each conversation session.
- `conversation_turns` stores append-only operator and agent transcript turns, including optional run linkage and failure text.
- `world_clock_states` stores world-owned operational clock state, with one current state row per world.
- `world_clock_transitions` stores world-owned operational audit records for clock state changes.
- `world_events` stores the append-only world event stream.
- `world_snapshots` stores world-owned snapshot metadata, inline diagnostic payloads, and future object-storage payload references.
- `agent_calendar_entries` stores private, world-scoped agent calendar items.
- `world_schedule_rules` stores world-owned weekday/weekend/timetable rule configuration.
- `memory_backend_profiles` stores platform-owned non-secret long-term memory backend configuration plus secret refs and enablement state.
- `memory_write_jobs` stores asynchronous long-term memory write work items, dedupe keys, retry state, and source attribution.
- `memory_write_logs` stores local audit summaries for backend write attempts, correlation ids, latency, and failure information.
- `memory_retrieval_logs` stores local audit summaries for long-term memory searches, selected item ids, context size, and latency.
- `agent_profile_snapshots` stores structured agent-owned profile overlays derived from long-term memory and local summarization logic.
- `agent_memory_items` remains a private, world-scoped local pgvector fallback namespace for tests and fallback behavior; it is not the canonical long-term memory store in the Mem0-first baseline.
- `provider_profiles` stores non-secret provider configuration records, reliability controls, test-call health metadata, and API key references.
- `runtime_control_states` stores platform-owned runtime desired state and daemon heartbeat metadata.
- `agent_runtime_runs` stores world-scoped operational run history, prompt/response content, and diagnostics for agent executions.
- `narrative_artifacts` stores world-scoped narrative outputs linked to optional agents, runtime runs, and source conversations.
- `runtime_diagnostic_events` stores operational diagnostic events for runtime, provider, agent, event publisher, and API surfaces; diagnostic details must be redacted and are not canonical world events.
- Plugin registry persistence remains deferred to a separate task.

## Ownership rules

- A world may read its own events and state.
- An agent may read only its own private resources plus allowed observations and its own long-term memory retrieval results.
- The narrative pipeline reads from authorized conversation transcripts, summaries, and events, not arbitrary private internals.
- Cross-world access is forbidden by default.
