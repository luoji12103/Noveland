# ADR-0003: Event Log Plus Snapshot

## Status
Accepted

## Context
The product requires pause/resume/recovery/replay semantics that cannot be reliably implemented with current-state only persistence.

## Decision
Use append-only event logging plus periodic snapshots as the durable truth and recovery model.

## Consequences
This supports replay and disaster recovery. It makes event schema governance more important.
