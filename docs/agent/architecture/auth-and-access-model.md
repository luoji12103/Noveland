# Auth and Access Model

## Roles

- `platform_admin`
- `world_admin`
- `human_user`
- `agent_runtime`

## Model

RBAC with world-scoped ownership checks.

## Access principles

- platform admins manage global settings and platform defaults
- world admins manage worlds they own or are assigned to
- human users only access worlds and roles explicitly granted
- agent runtime identities only access their own runtime resources and allowed world observations

## Hard boundaries

- an agent must not read another agent's private calendar or private memory
- world data is isolated per world
- UI routes must be validated server-side, not trusted client-side
- narrative access is authorized, not implicit

## Session policy

- backend-owned authenticated sessions
- no client-side trust for role enforcement
