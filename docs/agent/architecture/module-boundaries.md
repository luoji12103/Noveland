# Module Boundaries

## `worlds`
Owns:
- world model
- scene/location model
- world clock state
- world-scoped orchestration
- visibility rules at the world layer

Must not own:
- provider-specific model logic
- object storage implementation details
- frontend formatting concerns

## `agents`
Owns:
- agent identity
- agent runtime configuration
- observation shaping
- allowed tool binding

Must not own:
- cross-agent direct data reads
- world rule authority
- narrative publishing

## `calendar`
Owns:
- per-agent calendar data
- schedule resolution against world time

Must not own:
- global world time authority
- other agents' calendar access

## `conversations`
Owns:
- conversation session metadata
- participant ordering
- transcript turn persistence
- deterministic round-robin turn advancement
- per-session policy, writer, and memory configuration

Must not own:
- LLM provider transport details
- narrative chapter publication
- global runtime scheduling policy
- arbitrary cross-agent private memory reads

## `memory`
Owns:
- long-term memory backend profile CRUD
- async write queueing and processing
- retrieval and context assembly contracts
- local write/retrieval audit logs
- agent profile snapshots
- forget/delete-scope orchestration across local and backend boundaries

Must not own:
- runtime loop ownership
- canonical raw event storage
- direct UI policy decisions
- cross-agent visibility expansion outside explicit auth rules

## `narrative`
Owns:
- conversation-first summarizer workflow
- summary/chapter artifacts
- reader-facing narrative units
- provider-backed generation ordering for conversation summary then chapter draft

Must not own:
- raw unrestricted access to all private scratch context
- world state authority

## `events`
Owns:
- append-only event definitions
- event persistence contracts
- snapshot contracts
- replay semantics

Must not own:
- UI behavior
- provider model prompts

## `plugins`
Owns:
- plugin contracts
- registration rules
- manifest/config schema
- loading policy

Must not own:
- ad hoc runtime shortcuts around registry
