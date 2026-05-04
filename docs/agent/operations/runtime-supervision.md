# Runtime Supervision

## Purpose

Runtime supervision explains how to tell whether the API and runtime daemon are independently healthy.

## Operator Surface

- `GET /health` checks only API process availability.
- `GET /runtime/supervision` checks API status, database status, desired runtime state, heartbeat freshness, and last runtime error.
- `GET /runtime/status` includes detailed runtime control, health, and memory queue counts.
- `GET /metrics` exposes local Prometheus-style text metrics for runtime, memory queue, and provider health counts.

## Expected States

- `desired_state=stopped`: daemon may be idle; no runtime process is required.
- `desired_state=running` and fresh heartbeat: daemon is observed.
- `desired_state=running` and stale/missing heartbeat: daemon is expected but not observed.
- `last_error` populated: inspect runtime diagnostics before restarting.

## Recovery Flow

1. Check `GET /runtime/supervision`.
2. Check `GET /runtime/diagnostics?component=runtime`.
3. If desired state is running and heartbeat is stale, restart `noveland-runtime --daemon`.
4. Recheck `GET /runtime/supervision` and `GET /metrics`.

This document complements `docs/agent/operations/runtime-recovery.md`.
