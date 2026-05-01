# Locked Technical Stack

## Backend

- Python 3.12
- FastAPI
- Pydantic v2
- SQLAlchemy 2.x
- Alembic
- uv
- ruff
- mypy
- pytest

## Frontend

- Next.js
- TypeScript
- React
- Tailwind CSS
- Vitest
- Playwright

## Data and storage

- PostgreSQL 16+
- Mem0 OSS-first long-term memory backend profiles
- local pgvector fallback backend for tests and local fallback paths
- Local object storage implementation by default
- Optional S3-compatible adapter

## Messaging and realtime

- NATS + JetStream
- SSE for read-side realtime updates
- WebSocket for conversation control

## Architecture stance

- modular monolith
- separate long-running runtime process
- plugin-first interfaces
- event log + snapshots

## Why this stack

It reduces early architectural fragmentation while leaving room for future scaling and backend substitution.

## Rejected for v1

- microservices-first split
- public API platform design
- separate dedicated vector DB as the default
- workflow engine as the source of truth for world time
