# System Context

## System summary

The system hosts multiple persistent worlds. Each world contains scenes, agents, schedules, rules, events, and narrative artifacts.

Admins manage the worlds through the web app. The runtime process advances world time, supervises agents, and records events. The narrative pipeline transforms authorized events into readable chapters or summaries.

## Context diagram (conceptual)

- Web app
  - admin UI
  - dashboard
  - narrative reader
- API service
  - auth
  - admin operations
  - websocket bridge
- Runtime service
  - world clock
  - world orchestration
  - agent supervisor
  - narrative scheduler
- PostgreSQL
  - business data
  - event log metadata
  - snapshot metadata
  - memory indexes
- Object storage
  - snapshots
  - narrative artifacts
  - exports
- NATS
  - runtime messaging
  - event fanout
  - UI update bridge

## Trust boundaries

- user/browser boundary
- admin API boundary
- runtime boundary
- world isolation boundary
- plugin implementation boundary
