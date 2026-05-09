# V2 Living World Roadmap

## Purpose

This document is the V2 long-term planning guide for Noveland after the original
50-phase V1 roadmap.

The product target is a galgame sequel-style living world system: an ended story
world continues to run with many characters, groups, organizations, relationships,
player choices, branches, memories, and daily narrative events. The system should
feel like an evolving continuation of an existing setting, not a generic chatbot.

This roadmap is not the active task board. Use `task-board.md` for current work.
Use this file to choose future mainlines, keep the product direction coherent,
and avoid drifting into unrelated simulation or generic agent-platform features.

## Current Baseline

Noveland already has:

- Multiple worlds with world-scoped access control.
- Scenes/locations, role agents, persona policy, observations, calendars, and schedules.
- World clock, event log, snapshots, replay, integrity checks, and event audit.
- Runtime daemon loops for clocks, agents, conversations, memory jobs, and narrative artifacts.
- Conversation workspace, narrative writer, publication workflow, reader search, and timeline views.
- Long-term memory profiles, async write jobs, evals, backfill, and operator surfaces behind `MemoryService`.
- Provider profiles, plugin contracts, diagnostics, metrics, recovery docs, and scale-readiness reporting.

At roadmap creation, the main V2 gaps were:

- No first-class organizations/factions.
- No durable relationship graph.
- No GM/world engine for macro situation, offscreen events, and daily episode generation.
- No branchable worldlines or independent branch memory.
- No structured player choice/consequence model.
- No promise, foreshadowing, route, secret, or information-flow systems.
- No galgame-oriented world-state dashboard or player-facing story journal.

Implementation and remediation status now lives in `change-journal.md`,
`debug-journal.md`, `task-board.md`, and the active handoff. Treat the list
above as the historical baseline that motivated the V2 roadmap, not as the
current implementation state.

## Planning Rules

- Foundations and ADRs remain higher authority than this roadmap.
- V2 phases are feature mainlines, not commits.
- Debugging, fixes, tests, docs, and regression checks are part of every phase acceptance criteria and are not separate roadmap phases.
- Extend existing world, event, runtime, memory, narrative, and Web surfaces before adding new parallel layers.
- `world_events` remains the canonical append-only event stream; new V2 systems should append typed, attributable events rather than reconstruct state from chat logs.
- Memory behavior remains behind `MemoryService`; runtime/conversation/GM code must not import memory backend SDKs directly.
- Branch/worldline work must preserve world-scoped and future worldline-scoped isolation.

## Phase Acceptance Baseline

Every phase below must satisfy all of these before it is considered complete:

- Phase-specific behavior is implemented and manually reviewable.
- Targeted backend unit/API tests and relevant Web component/client tests pass.
- Relevant regression checks pass based on blast radius.
- Public contracts, mocks, docs, task board, and active handoff are updated.
- No unrelated scope expansion, schema churn, secret exposure, or architectural bypass is introduced.

## Long-Term Roadmap

| Phase | Goal | Expected Outcome | Specific Acceptance Signal |
| --- | --- | --- | --- |
| 1. Story World Bible | Establish a structured world bible. | Worlds can record source work context, canon timeline, locations, character rules, forbidden changes, and sequel boundaries. | World admins can edit and inspect the world bible; runtime and narrative paths can read its constraints. |
| 2. Canon Continuity Rules | Define continuation semantics for existing story worlds. | Content can be marked as canon, post-canon, alternate, or original expansion. | New world events and narrative artifacts carry continuity metadata. |
| 3. Character Roster Expansion | Expand the agent roster model for galgame roles. | Main characters, side characters, ordinary members, organization members, and original characters are distinguishable. | Agents support narrative role, importance, canon status, and affiliation metadata. |
| 4. Character Profile Sheets | Move beyond free-form persona text. | Characters have structured speech style, goals, secrets, daily preferences, story function, and emotional baseline. | Agent builder can manage structured profile fields alongside persona text. |
| 5. Relationship Graph v1 | Add first-class character relationship edges. | Relationships can record affection, trust, hostility, intimacy, obligation, rivalry, and debt. | API and UI can list and update agent-to-agent relationship edges. |
| 6. Relationship Memory Integration | Make relationship changes durable in memory. | Conversations, events, and player choices can affect relationships and later retrieval. | `MemoryService` records relationship change summaries and runtime prompts can retrieve relationship context. |
| 7. Organization Model | Add organizations and factions. | Worlds can model schools, clubs, families, companies, enemy factions, and secret groups. | World admins can CRUD organizations/factions under a world. |
| 8. Organization Membership | Track character membership in organizations. | Characters can belong to multiple organizations with roles, loyalty, influence, and hidden/public status. | Agent detail surfaces organization identity and responsibility. |
| 9. Faction Progress Tracks | Track organization plans and pressure. | Organizations can progress goals, conflicts, resources, reputation, and risk. | Runtime can update faction progress and world overview can show it. |
| 10. Location Graph v1 | Upgrade scenes into a location graph. | Locations support regions, adjacency, availability, opening rules, and narrative tags. | World map/location list can express relationships between places and active state. |
| 11. Character Presence | Track where characters are and whether they are visible. | Characters have current location, scheduled movement, offscreen state, and encounter eligibility. | Runtime ticks can update character location/presence state. |
| 12. Daily Life Scheduler | Make character routines run without player prompts. | Characters naturally attend school, work, rest, travel, and socialize. | Calendar/schedule resolution can create daily-life events. |
| 13. Offscreen Event Queue | Let the world continue away from the player. | Characters and organizations can create pending offscreen events. | Runtime can resolve queued offscreen events into `world_events`. |
| 14. Event Importance Ranking | Classify event narrative weight. | The system distinguishes daily, relationship, organization, route, and main-plot events. | Event audit and narrative pipeline can filter by importance. |
| 15. GM World Engine v1 | Add a GM/world engine runtime component. | A runtime component handles macro situation, daily inserts, and plot pressure. | GM engine uses existing runtime, event, memory, and diagnostics boundaries. |
| 16. GM Agenda Planner | Persist near-term GM agenda. | GM can track upcoming story goals, character hooks, organization plans, and world pressure. | World admins can inspect active GM agenda. |
| 17. GM Event Proposal | Propose events before they are committed. | GM produces candidate events with reasons, source context, risk, and affected actors. | Event proposals are reviewable and testable before resolution. |
| 18. Event Resolution Rules | Resolve offscreen events deterministically. | Offscreen outcomes can depend on character state, relationships, faction progress, and player history. | Same input state produces testable, replay-compatible outcomes. |
| 19. Player Actor Model | Represent the player as an in-world actor. | The player has identity, relationships, location, history, and visibility inside the world. | World membership can bind to a player actor profile. |
| 20. Player Choice Records | Store structured player choices. | Player decisions affect relationships, events, and worldline conditions. | Choice records append to event log and are retrievable by memory/narrative systems. |
| 21. Choice Consequence Engine | Apply player consequences explicitly. | Choices can affect relationships, organization action, future events, and branch eligibility. | Consequence preview/diagnostics can explain impact paths. |
| 22. Branchable Worldlines | Add branch saves/worldlines. | A world can fork into independent histories and states. | Creating a branch preserves the original and gives reader/replay worldline scope. |
| 23. Worldline Snapshot Fork | Fork from snapshots or event sequence points. | Branches record lineage and fork position. | Fork metadata includes parent worldline, snapshot/event sequence, and created actor. |
| 24. Worldline Memory Isolation | Isolate branch memory. | Different branches do not contaminate character memory, relationship state, or event history. | Memory write/search/dedupe keys include worldline scope. |
| 25. Timeline Comparison View | Compare branches. | Admins can inspect divergent choices, events, relationships, and faction state. | UI shows fork point, divergent events, and state deltas. |
| 26. Promise And Foreshadowing Tracker | Track promises, hooks, and flags. | The system records promises, unresolved mysteries, foreshadowing, agreements, and flags. | GM and narrative paths can query unresolved hooks. |
| 27. Plot Thread Model | Model personal, organization, daily, main, and hidden plot lines. | Plot threads have status, participants, stakes, next beats, and related events. | World admins can inspect active and dormant plot threads. |
| 28. Route Affinity System | Add galgame route progression. | Character routes advance by player behavior, relationship state, and events. | Route status is distinct from simple affection and is testable. |
| 29. Event Flag Conditions | Gate events with explicit conditions. | Event triggers can require time, place, relationship, faction state, hook state, and player choices. | Trigger dry-run explains satisfied and unsatisfied conditions. |
| 30. Scene Beat Composer | Convert events into galgame-style scene beats. | Events can become structured scenes with setup, dialogue, choice, and aftermath. | Narrative writer can generate scene beat drafts from event inputs. |
| 31. Daily Episode Generator | Generate low-risk daily episodes. | Characters naturally produce short daily scenes, encounters, misunderstandings, and relationship moments. | Runtime can create daily narrative drafts from low-risk event proposals. |
| 32. Group Interaction Engine | Support group scenes and multi-party interaction. | Clubs, classes, organizations, meetings, and conflicts can involve many characters. | Conversation system supports group context plus organization/location constraints. |
| 33. Relationship Event Suggestions | Suggest events from relationship tension. | The system recommends scenes based on affection, conflict, debt, rivalry, or missed promises. | Admin UI shows candidate participants and recommendation reasons. |
| 34. Organization Conflict Engine | Let factions compete. | Organizations can contest resources, secrets, reputation, and goals. | Faction progress can emit conflict events. |
| 35. Rumor And Information Flow | Model how information spreads. | Knowledge moves through characters, locations, organizations, and rumors instead of global omniscience. | Agent observations are filtered by known information. |
| 36. Character Knowledge State | Track what each character knows or misunderstands. | Characters can hold facts, secrets, guesses, and mistaken beliefs. | Runtime prompts do not expose information a character has not learned. |
| 37. Secret And Revelation System | Add secrets and reveal conditions. | Secrets track holders, discoverability, reveal events, and consequences. | Secret reveal appends events and triggers relationship/organization effects. |
| 38. Emotional State Model | Add short-term character emotional state. | Characters have stress, fatigue, anticipation, jealousy, anger, and mood state. | Emotion state affects dialogue, event participation, and schedules. |
| 39. Relationship Decay And Repair | Let relationships change over time. | Neglect, conflict, apology, kept promises, and shared events can decay or repair relationships. | Runtime tick can emit relationship decay/repair diagnostics and events. |
| 40. World State Dashboard v2 | Build a living-world admin overview. | Admin can see characters, locations, organizations, queued events, worldlines, hooks, and pressure. | Dashboard is oriented around story operations, not only technical status. |
| 41. Player-Facing Story Journal | Give the player a story journal. | Players can read choices, relationship changes, recent events, and pending invitations. | Reader separates public narrative, player-private journal, and admin drafts. |
| 42. In-World Notification Feed | Notify players of world activity. | Players receive messages, invitations, rumors, promises, and sudden incidents. | Notifications trace back to world events. |
| 43. Intervention Controls | Let players intervene in living events. | Players can observe, reply, travel, contact characters, or push events forward. | Each intervention creates a structured choice/event. |
| 44. GM Safety And Style Guardrails | Preserve galgame style and setting continuity. | GM output stays daily/narrative/setting-aware instead of drifting into generic chatbot behavior. | GM output has style diagnostics and continuity warnings. |
| 45. Narrative Continuity Review | Review drafts for continuity issues. | Drafts can be checked for OOC behavior, canon conflicts, time contradictions, and relationship jumps. | Publishing workflow surfaces continuity issues before reader visibility. |
| 46. Route And Ending Planning | Plan routes and endings. | The system supports character routes, hidden routes, normal endings, bad endings, and epilogues. | Plot threads can define route milestones and ending candidates. |
| 47. Long-Run Simulation Evaluation | Evaluate multi-day simulation quality. | Test worlds can run days/weeks to measure activity, event density, consistency, and narrative drift. | Eval output recommends concrete improvements, not only pass/fail. |
| 48. Authoring Toolchain v2 | Improve author tools for sequel worlds. | Admins can import source-work notes, character templates, event templates, and route templates. | A structured template can create a sequel-ready world. |
| 49. Living World Release Profile | Define a release/deployment profile for living worlds. | Operators have guidance for branch management, backups, content review, and player permissions. | README/ops docs can guide deployment of a sustainable living world. |
| 50. Galgame Living World Beta | Validate with a complete sample world. | One sample world proves multi-character, multi-organization, worldline, GM, choice, and narrative loops. | Beta checklist covers 7-day simulation, branch saves, relationship changes, faction progress, and narrative output. |

## Suggested Mainline Bundles

- World Model Deepening: phases 1-10.
- Autonomous Life Runtime: phases 11-18.
- Player Choice + Worldlines: phases 19-25.
- Plot/Route/Narrative Systems: phases 26-33.
- Organizations + Information Flow: phases 34-39.
- Player/Admin Experience: phases 40-45.
- Beta/Authoring/Release: phases 46-50.

## Public Interfaces And Data Areas

- Add or extend backend contracts for world bible, character profile sheets, relationships, organizations, worldlines, plot threads, event proposals, player choices, secrets, route states, and GM agenda.
- Extend event semantics rather than replacing `world_events`; V2 systems should produce typed world events with actor, causation, correlation, worldline, and continuity metadata.
- Extend `MemoryService` scope with worldline and relationship/plot context; runtime, conversation, and GM code must still not import memory backend SDKs directly.
- Extend Web surfaces under existing world, admin, and reader routes instead of creating a parallel app.

## Test Plan

- Every phase includes backend unit/API tests, Web component/client tests where UI changes exist, docs/handoff updates, and targeted regression checks.
- High-risk phase groups require additional simulation/eval tests for worldline isolation, relationship updates, GM event proposals, choice consequences, memory isolation, and long-run simulation.
- No phase is complete if it creates untested schema migrations, untracked API contracts, stale mocks, or cross-world/worldline data leakage.

## Maintenance Rules

- Keep this file at roadmap granularity; detailed phase execution plans belong in task-board or active-session handoff updates.
- Do not mark all 50 phases as active work.
- When a V2 phase starts, select one mainline bundle in `task-board.md`.
- When a V2 phase completes, record the implementation in `change-journal.md` and update the active handoff.
