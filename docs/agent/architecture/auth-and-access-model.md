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

## Implemented baseline

- `user_credentials` stores one local password credential per user using Argon2id PHC hashes.
- `auth_sessions` stores backend-owned opaque sessions; plaintext session tokens are returned only once and only SHA-256 token hashes are persisted.
- `platform_role_assignments` stores platform-level `platform_admin` grants.
- `noveland.auth.PasswordCredentialService` sets and verifies local passwords.
- `noveland.auth.AuthSessionService` creates, authenticates, revokes, and expires opaque sessions.
- `GET /auth/csrf` issues a readable CSRF token cookie for browser clients.
- `POST /auth/login` accepts email/password credentials, creates an opaque backend session, and sets auth cookies.
- `GET /auth/me` returns the authenticated subject for a valid session cookie.
- `POST /auth/logout` requires a valid session plus matching `X-CSRF-Token` header and CSRF cookie, then revokes the session.
- `noveland-seed-admin` seeds or updates a local platform admin without exposing public registration.

## Current limits

- No frontend login UI, OAuth/OIDC, email verification, password reset, MFA, or public registration endpoint.
- No auth middleware or world access enforcement yet.
- `world_admin` and `human_user` continue to be represented by `world_memberships`.
- `agent_runtime` credential modeling remains deferred.
