# MVP Definition

## In scope for v1

- Web-only product entry
- Single Linux server deployment
- Multiple worlds in one program
- World-scoped data isolation
- World-scoped scheduling isolation
- Agent worker partitioning by world
- 5–10 always-on role agents
- Same-scene multi-agent conversation
- Private per-agent calendar read/write
- World rules for weekday, weekend, holiday, and timetable behavior
- World overview dashboard
- Narrative reader
- Narrative agent with scheduled and manual trigger
- Real-time continuous operation
- Snapshot + incremental event log
- Plugin interfaces for:
  - model providers
  - memory backends
  - world rules / schedule rules
  - persona / behavior policies
  - narrative writers / summarizers

## Explicitly out of scope for v1

- official multi-tenant product support
- mobile app
- public third-party API
- real cross-world migration flow
- hot-pluggable plugin marketplace
- unrestricted external tools and network access by default
- advanced enterprise policy engine
- production-grade hard sandbox as a required default

## Deferred but expected later

- more advanced replay controls
- stronger sandbox options
- broader plugin ecosystem
- optional external storage backends
- higher agent counts

## Scope discipline

Anything not listed as in-scope must be treated as out-of-scope until explicitly promoted.
