# Noveland

Noveland is a persistent virtual-world operating system for AI agents. The repository is in its early implementation phase: the architecture and governance package is in place, and the implementation now includes a backend API, auth/session baseline, world-first Web workspace, multi-agent conversation substrate, conversation-first narrative writer pipeline, a dedicated reader surface, runtime host, and local infrastructure.

## Current Status

- Product and architecture source of truth: `docs/agent/`
- Backend stack: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, uv
- Frontend stack: Next.js, TypeScript, React, Tailwind CSS, Vitest, Playwright
- Local services: PostgreSQL 16 with pgvector, NATS with JetStream
- Long-term memory: Mem0 OSS-first backend profiles, async write jobs, read-only agent memory search, profile snapshots, forget/eval operators, job retry observability, and backfill dry-run planning
- License: TBD

## Local Setup

Install `uv` before working on the backend:

```sh
python3 -m pip install --user uv
uv python install 3.12
```

Copy local configuration:

```sh
cp .env.example .env
```

Start local infrastructure:

```sh
docker compose -f infra/compose.yaml up -d
```

Apply database migrations from `backend/`:

```sh
uv run alembic upgrade head
```

Seed a local platform admin from `backend/` after migrations:

```sh
uv run noveland-seed-admin \
  --email admin@example.test \
  --password "change-me-local-only" \
  --display-name "Admin"
```

If local ports are already taken, override them before starting Compose:

```sh
NOVELAND_POSTGRES_PORT=55432 NOVELAND_NATS_PORT=44222 NOVELAND_NATS_MONITOR_PORT=48222 \
  docker compose -f infra/compose.yaml up -d
```

Use a matching database URL when running backend commands against the overridden port:

```sh
NOVELAND_DATABASE_URL=postgresql+psycopg://noveland:noveland@localhost:55432/noveland \
  uv run alembic upgrade head
```

Run backend checks from `backend/`:

```sh
uv run ruff check .
uv run mypy .
uv run pytest
```

Run the API from `backend/`:

```sh
uv run uvicorn noveland.services.api.app:app --reload
```

Run one finite runtime tick from `backend/`:

```sh
uv run noveland-runtime
```

Run the long-lived runtime loop from `backend/`:

```sh
uv run noveland-runtime --daemon
```

Runtime recovery reference: `docs/agent/operations/runtime-recovery.md`.

Run frontend checks from `web/`:

```sh
npm install
npm run lint
npm run typecheck
npm run test
npm run test:e2e
```

Run the web app from `web/`:

```sh
npm run dev
```

Open `http://127.0.0.1:3000/login` and sign in with the seeded admin account. Successful sign-in lands on `/worlds`.

For live workspace updates, set the web-facing API WebSocket base URL in local configuration:

```sh
NEXT_PUBLIC_NOVELAND_API_WS_BASE_URL=ws://127.0.0.1:8000
```

For long-term memory backends, keep provider secrets out of the database and provide them through local configuration:

```sh
NOVELAND_MEMORY_BACKEND_SECRETS_JSON={}
```

## 人工确认步骤

按下面顺序做一轮人工验收，可以覆盖当前主干上最重要的能力：

1. 启动基础设施：
   ```sh
   docker compose -f infra/compose.yaml up -d
   ```
2. 在 `backend/` 执行数据库迁移并 seed 管理员：
   ```sh
   uv run alembic upgrade head
   uv run noveland-seed-admin \
     --email admin@example.test \
     --password "change-me-local-only" \
     --display-name "Admin"
   ```
3. 分别启动 API、Web、runtime daemon：
   ```sh
   # backend/
   uv run uvicorn noveland.services.api.app:app --reload
   ```
   ```sh
   # web/
   npm run dev
   ```
   ```sh
   # backend/
   uv run noveland-runtime --daemon
   ```
4. 打开 `http://127.0.0.1:3000/login`，用刚刚 seed 的管理员账号登录。
5. 在 Web workspace 中确认以下操作可用：
   - 创建 world，确认 world clock 已初始化
   - 创建 scene 和 agent
   - 在 agent builder 中设置 default provider、persona、observation、calendar 和 memory
   - 创建 conversation，添加 participants，seed transcript，手动 advance 一轮
   - 创建 auto dialogue conversation，Start 后由 `noveland-runtime --daemon` 逐轮推进
   - 创建 provider profile，并执行 `Test provider`，确认 provider health 状态可读
   - 手动运行 agent，确认 run、memory、narrative artifact、diagnostics 有更新
   - 启动 runtime，确认 runtime status、memory write job counts 和 diagnostics 有变化
6. 如需验证 API 面，额外确认：
   - `GET /health` 返回固定 contract
   - `/auth/*` 登录、当前用户、登出正常
   - `/worlds/*`、`/runtime/*`、`/provider-profiles/*` 在登录态下按权限正常工作

## 正常使用教程

日常本地使用可以按这个最短路径：

1. 首次环境准备：
   - 安装 `uv`
   - 复制 `.env.example` 为 `.env`
   - 在 `web/` 执行一次 `npm install`
2. 每次开始工作前：
   ```sh
   docker compose -f infra/compose.yaml up -d
   ```
3. 后端如有新 migration，先在 `backend/` 执行：
   ```sh
   uv run alembic upgrade head
   ```
4. 如需重新建立管理员账号，在 `backend/` 执行：
   ```sh
   uv run noveland-seed-admin \
     --email admin@example.test \
     --password "change-me-local-only" \
     --display-name "Admin"
   ```
5. 开发时通常需要三个进程：
   - `backend/`: `uv run uvicorn noveland.services.api.app:app --reload`
   - `web/`: `npm run dev`
   - `backend/`: `uv run noveland-runtime --daemon`
6. 登录后的一般操作顺序：
   - 先在 `/worlds` 创建或选择 world
   - 在 `/worlds/{worldId}` 配置 scenes、memberships、clock、schedule rules、replay/snapshots
   - 如需复用 agent 组合，在 `/admin/presets` 创建平台级 preset
   - 在 `/worlds/{worldId}/agents` 创建 agent，可直接套用 preset
   - 在 `/worlds/{worldId}/agents/{agentId}` 设置 scene、default provider、persona、observations、calendar，查看只读 memory/search/profile snapshot，并可手动 run
   - 在 `/worlds/{worldId}/conversations` 创建 manual chain 或 auto dialogue session，并配置 writer 行为
   - 在 `/worlds/{worldId}/conversations/{conversationId}` 添加 participants，seed transcript，advance/start/pause/resume，并可生成 summary / chapter
   - 在 `/worlds/{worldId}/narrative` 查看 narrative artifacts
   - 在 `/worlds/{worldId}/reader` 以只读方式阅读 summary / chapter，并跳回 source conversation
   - 如需复制世界骨架，在 `/worlds/{worldId}` 的 `World composition` 面板导出 JSON，并由平台管理员导入为新 world
   - 在 `/admin/providers` 配置 provider profile，并先做 `Test provider`
   - 在 `/admin/memory-backends` 配置 memory backend profile，查看 health / logs / jobs / backfill dry-run，必要时 retry failed memory write job，并执行 eval smoke
   - 在 `/admin/runtime` 启停 runtime desired state
7. 常用回归命令：
   ```sh
   # backend/
   uv run ruff check .
   uv run mypy .
   uv run pytest
   ```
   ```sh
   # web/
   npm run lint
   npm run typecheck
   npm run test
   npm run test:e2e
   npm run build
   npm run check:next-env
   ```
8. 停止本地依赖：
   ```sh
   docker compose -f infra/compose.yaml down
   ```

## Stable Interfaces

The first stable backend endpoint is:

```http
GET /health
```

Expected response:

```json
{"service":"api","status":"ok","version":"0.1.0"}
```

Realtime transport endpoints currently exposed by the API:

```http
GET /runtime/stream
GET /worlds/{world_id}/stream
GET /worlds/{world_id}/conversations/{conversation_id}/stream
WS  /worlds/{world_id}/conversations/{conversation_id}/live
```

Preset and world composition endpoints currently exposed by the API:

```http
GET /agent-presets
POST /agent-presets
PATCH /agent-presets/{preset_id}
DELETE /agent-presets/{preset_id}
GET /worlds/{world_id}/composition-export
POST /world-compositions/import
```

Memory backend and long-term memory endpoints currently exposed by the API:

```http
GET /memory-backend-profiles
POST /memory-backend-profiles
PATCH /memory-backend-profiles/{profile_id}
DELETE /memory-backend-profiles/{profile_id}
GET /memory-backend-profiles/{profile_id}/health
GET /memory-backend-profiles/{profile_id}/logs
GET /memory-backend-profiles/{profile_id}/jobs
POST /memory-backend-profiles/{profile_id}/eval-smoke
POST /memory-write-jobs/{job_id}/retry
GET /memory-backfill/dry-run
GET /worlds/{world_id}/agents/{agent_id}/memory
POST /worlds/{world_id}/agents/{agent_id}/memory/search
GET /worlds/{world_id}/agents/{agent_id}/memory/profile-snapshot
POST /worlds/{world_id}/agents/{agent_id}/memory/profile-snapshot/refresh
POST /worlds/{world_id}/agents/{agent_id}/memory/forget
```

This health endpoint does not imply database, messaging, world-clock, replay, auth, or plugin readiness.

The initial auth HTTP surface is:

```http
GET /auth/csrf
POST /auth/login
GET /auth/me
POST /auth/logout
```

Auth uses an HttpOnly opaque session cookie named `noveland_session`, a readable CSRF cookie named `noveland_csrf`, and `X-CSRF-Token` for mutating authenticated requests. The web app reaches FastAPI through same-origin Next route handlers under `/api/auth/*`; `NOVELAND_API_BASE_URL` points those handlers at the backend API.

The initial world management API is available under:

```http
GET /worlds
POST /worlds
GET /worlds/{world_id}
PATCH /worlds/{world_id}
DELETE /worlds/{world_id}
GET /worlds/{world_id}/scenes
POST /worlds/{world_id}/scenes
PATCH /worlds/{world_id}/scenes/{scene_id}
DELETE /worlds/{world_id}/scenes/{scene_id}
GET /worlds/{world_id}/memberships
PUT /worlds/{world_id}/memberships/{user_id}
DELETE /worlds/{world_id}/memberships/{user_id}
GET /worlds/{world_id}/member-candidates
GET /worlds/{world_id}/agents
POST /worlds/{world_id}/agents
PATCH /worlds/{world_id}/agents/{agent_id}
DELETE /worlds/{world_id}/agents/{agent_id}
GET /worlds/{world_id}/agents/{agent_id}/calendar
POST /worlds/{world_id}/agents/{agent_id}/calendar
PATCH /worlds/{world_id}/agents/{agent_id}/calendar/{entry_id}
DELETE /worlds/{world_id}/agents/{agent_id}/calendar/{entry_id}
GET /worlds/{world_id}/agents/{agent_id}/memory
POST /worlds/{world_id}/agents/{agent_id}/memory
POST /worlds/{world_id}/agents/{agent_id}/memory/search
DELETE /worlds/{world_id}/agents/{agent_id}/memory/{memory_id}
GET /worlds/{world_id}/agents/{agent_id}/runs
GET /worlds/{world_id}/agents/{agent_id}/runs/{run_id}
POST /worlds/{world_id}/agents/{agent_id}/run
GET /worlds/{world_id}/agents/{agent_id}/persona
POST /worlds/{world_id}/agents/{agent_id}/persona/validate
PATCH /worlds/{world_id}/agents/{agent_id}/persona
GET /worlds/{world_id}/agents/{agent_id}/observations
POST /worlds/{world_id}/agents/{agent_id}/observations
POST /worlds/{world_id}/agents/{agent_id}/observations/refresh
GET /worlds/{world_id}/schedule-rules
GET /worlds/{world_id}/calendar/conflicts
POST /worlds/{world_id}/schedule-rules
POST /worlds/{world_id}/schedule-rules/preview
PATCH /worlds/{world_id}/schedule-rules/{rule_id}
DELETE /worlds/{world_id}/schedule-rules/{rule_id}
GET /worlds/{world_id}/narrative-artifacts
GET /worlds/{world_id}/narrative-artifacts/{artifact_id}
POST /worlds/{world_id}/narrative-artifacts
POST /worlds/{world_id}/narrative-artifacts/{artifact_id}/publish
POST /worlds/{world_id}/narrative-artifacts/{artifact_id}/unpublish
GET /worlds/{world_id}/clock
GET /worlds/{world_id}/clock/transitions
POST /worlds/{world_id}/clock/pause
POST /worlds/{world_id}/clock/resume
POST /worlds/{world_id}/clock/advance
POST /worlds/{world_id}/clock/skip
GET /worlds/{world_id}/replay/state
GET /worlds/{world_id}/snapshots/latest
GET /worlds/{world_id}/snapshots/integrity
POST /worlds/{world_id}/snapshots
GET /worlds/{world_id}/events
GET /worlds/{world_id}/diagnostics
GET /worlds/{world_id}/conversations
POST /worlds/{world_id}/conversations
GET /worlds/{world_id}/conversations/{conversation_id}
PATCH /worlds/{world_id}/conversations/{conversation_id}
GET /worlds/{world_id}/conversations/{conversation_id}/participants
PUT /worlds/{world_id}/conversations/{conversation_id}/participants
GET /worlds/{world_id}/conversations/{conversation_id}/turns
GET /worlds/{world_id}/conversations/{conversation_id}/diagnostics/summary
POST /worlds/{world_id}/conversations/{conversation_id}/seed
POST /worlds/{world_id}/conversations/{conversation_id}/advance
POST /worlds/{world_id}/conversations/{conversation_id}/start
POST /worlds/{world_id}/conversations/{conversation_id}/pause
POST /worlds/{world_id}/conversations/{conversation_id}/resume
GET /worlds/{world_id}/conversations/{conversation_id}/narrative
POST /worlds/{world_id}/conversations/{conversation_id}/narrative/preview
POST /worlds/{world_id}/conversations/{conversation_id}/narrative/generate
```

Mutating world endpoints require the same `noveland_csrf` cookie and `X-CSRF-Token` header used by auth logout. DELETE routes are soft-disable operations; they do not hard-delete world, scene, or agent rows. Narrative reader routes only expose artifacts with a published, reader-visible publication record to non-editor world members; world admins can still manage draft artifacts in `/worlds/{worldId}/narrative`.

The platform-admin runtime surface is available under:

```http
GET /runtime/control
PATCH /runtime/control
GET /runtime/status
GET /runtime/diagnostics
GET /provider-profiles
GET /provider-profiles/health
POST /provider-profiles
PATCH /provider-profiles/{profile_id}
POST /provider-profiles/{profile_id}/test-call
DELETE /provider-profiles/{profile_id}
```

Provider profiles are non-secret records. API keys stay in `NOVELAND_PROVIDER_API_KEYS_JSON`, keyed by each profile's `api_key_ref`. Profiles include timeout, retry, optional per-process rate-limit, and last test-call status fields; test-call responses and diagnostics never expose API key material.

The protected Web workspace reads this API through server-side helpers and same-origin `/api/worlds/*` proxy routes. It can create and update worlds, scenes, agents, memberships, agent calendar entries, private agent memory items, world schedule rules, world clock state, inline snapshots, and conversation sessions according to the current user's backend permissions, while exposing a separate read-only reader for narrative consumption.

The Web workspace is split into `/worlds`, `/worlds/{worldId}`, `/worlds/{worldId}/agents`, `/worlds/{worldId}/agents/{agentId}`, `/worlds/{worldId}/conversations`, `/worlds/{worldId}/conversations/{conversationId}`, `/worlds/{worldId}/narrative`, `/worlds/{worldId}/reader`, `/worlds/{worldId}/reader/{artifactId}`, `/admin/providers`, and `/admin/runtime`.

The protected Web workspace also exposes runtime controls, recent runtime/world diagnostics, provider profiles, agent personas, filtered observations, manual agent runs, conversation transcript controls, per-session writer configuration, and narrative artifacts through same-origin `/api/runtime/*`, `/api/provider-profiles/*`, and `/api/worlds/*` proxy routes.

The runtime host now supports both finite and daemon modes. `noveland-runtime --once` advances active running clocks, appends `world.clock_advanced` events, and broadcasts event envelopes to NATS on `noveland.world.{world_id}.events`. `noveland-runtime --daemon` obeys the database-backed runtime control state, resolves due calendar entries and schedule rules, runs enabled agents through provider profiles, advances running auto-dialogue conversations one turn per loop, appends agent/runtime/conversation events, optionally writes memory items, and optionally creates narrative artifacts.

## Development Rules

Read `docs/agent/README.md` before changing structure or implementing domain behavior. New structural files must be reflected in the agent harness docs.
