import { readCookie, requestCsrf } from "@/lib/auth/client";
import { CSRF_COOKIE_NAME, CSRF_HEADER_NAME } from "@/lib/auth/types";
import type {
  Agent,
  AgentCreateInput,
  AgentUpdateInput,
  CalendarEntry,
  CalendarEntryCreateInput,
  CalendarEntryUpdateInput,
  MemberCandidate,
  MemoryItem,
  MemoryItemCreateInput,
  MemorySearchInput,
  Membership,
  Scene,
  SceneCreateInput,
  SceneUpdateInput,
  ScheduleRule,
  ScheduleRuleCreateInput,
  ScheduleRuleUpdateInput,
  World,
  WorldCreateInput,
  WorldClock,
  WorldRole,
  WorldReplayState,
  WorldSnapshot,
  WorldUpdateInput,
} from "@/lib/worlds/types";

export class WorldClientError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "WorldClientError";
  }
}

export function listWorlds(): Promise<World[]> {
  return worldRequest<World[]>("/api/worlds", { method: "GET" });
}

export function createWorld(input: WorldCreateInput): Promise<World> {
  return worldRequest<World>("/api/worlds", { method: "POST", body: input, csrf: true });
}

export function updateWorld(worldId: string, input: WorldUpdateInput): Promise<World> {
  return worldRequest<World>(`/api/worlds/${worldId}`, {
    method: "PATCH",
    body: input,
    csrf: true,
  });
}

export function deactivateWorld(worldId: string): Promise<void> {
  return worldRequest<void>(`/api/worlds/${worldId}`, { method: "DELETE", csrf: true });
}

export function getWorldClock(worldId: string): Promise<WorldClock> {
  return worldRequest<WorldClock>(`/api/worlds/${worldId}/clock`, { method: "GET" });
}

export function pauseWorldClock(worldId: string, reason?: string): Promise<WorldClock> {
  return worldRequest<WorldClock>(`/api/worlds/${worldId}/clock/pause`, {
    method: "POST",
    body: reason === undefined ? {} : { reason },
    csrf: true,
  });
}

export function resumeWorldClock(
  worldId: string,
  speed_multiplier?: string,
  reason?: string,
): Promise<WorldClock> {
  return worldRequest<WorldClock>(`/api/worlds/${worldId}/clock/resume`, {
    method: "POST",
    body: {
      ...(speed_multiplier === undefined || speed_multiplier === "" ? {} : { speed_multiplier }),
      ...(reason === undefined ? {} : { reason }),
    },
    csrf: true,
  });
}

export function advanceWorldClock(worldId: string, reason?: string): Promise<WorldClock> {
  return worldRequest<WorldClock>(`/api/worlds/${worldId}/clock/advance`, {
    method: "POST",
    body: reason === undefined ? {} : { reason },
    csrf: true,
  });
}

export function skipWorldClock(
  worldId: string,
  target_world_time: string,
  reason?: string,
): Promise<WorldClock> {
  return worldRequest<WorldClock>(`/api/worlds/${worldId}/clock/skip`, {
    method: "POST",
    body: { target_world_time, ...(reason === undefined ? {} : { reason }) },
    csrf: true,
  });
}

export function getReplayState(worldId: string): Promise<WorldReplayState> {
  return worldRequest<WorldReplayState>(`/api/worlds/${worldId}/replay/state`, {
    method: "GET",
  });
}

export function getLatestSnapshot(worldId: string): Promise<WorldSnapshot | null> {
  return worldRequest<WorldSnapshot | null>(`/api/worlds/${worldId}/snapshots/latest`, {
    method: "GET",
  });
}

export function createSnapshot(worldId: string): Promise<WorldSnapshot> {
  return worldRequest<WorldSnapshot>(`/api/worlds/${worldId}/snapshots`, {
    method: "POST",
    csrf: true,
  });
}

export function listScenes(worldId: string): Promise<Scene[]> {
  return worldRequest<Scene[]>(`/api/worlds/${worldId}/scenes`, { method: "GET" });
}

export function createScene(worldId: string, input: SceneCreateInput): Promise<Scene> {
  return worldRequest<Scene>(`/api/worlds/${worldId}/scenes`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function updateScene(
  worldId: string,
  sceneId: string,
  input: SceneUpdateInput,
): Promise<Scene> {
  return worldRequest<Scene>(`/api/worlds/${worldId}/scenes/${sceneId}`, {
    method: "PATCH",
    body: input,
    csrf: true,
  });
}

export function deactivateScene(worldId: string, sceneId: string): Promise<void> {
  return worldRequest<void>(`/api/worlds/${worldId}/scenes/${sceneId}`, {
    method: "DELETE",
    csrf: true,
  });
}

export function listAgents(worldId: string): Promise<Agent[]> {
  return worldRequest<Agent[]>(`/api/worlds/${worldId}/agents`, { method: "GET" });
}

export function listAgentCalendar(worldId: string, agentId: string): Promise<CalendarEntry[]> {
  return worldRequest<CalendarEntry[]>(`/api/worlds/${worldId}/agents/${agentId}/calendar`, {
    method: "GET",
  });
}

export function createAgentCalendarEntry(
  worldId: string,
  agentId: string,
  input: CalendarEntryCreateInput,
): Promise<CalendarEntry> {
  return worldRequest<CalendarEntry>(`/api/worlds/${worldId}/agents/${agentId}/calendar`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function updateAgentCalendarEntry(
  worldId: string,
  agentId: string,
  entryId: string,
  input: CalendarEntryUpdateInput,
): Promise<CalendarEntry> {
  return worldRequest<CalendarEntry>(
    `/api/worlds/${worldId}/agents/${agentId}/calendar/${entryId}`,
    {
      method: "PATCH",
      body: input,
      csrf: true,
    },
  );
}

export function cancelAgentCalendarEntry(
  worldId: string,
  agentId: string,
  entryId: string,
): Promise<void> {
  return worldRequest<void>(`/api/worlds/${worldId}/agents/${agentId}/calendar/${entryId}`, {
    method: "DELETE",
    csrf: true,
  });
}

export function listScheduleRules(worldId: string): Promise<ScheduleRule[]> {
  return worldRequest<ScheduleRule[]>(`/api/worlds/${worldId}/schedule-rules`, { method: "GET" });
}

export function createScheduleRule(
  worldId: string,
  input: ScheduleRuleCreateInput,
): Promise<ScheduleRule> {
  return worldRequest<ScheduleRule>(`/api/worlds/${worldId}/schedule-rules`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function updateScheduleRule(
  worldId: string,
  ruleId: string,
  input: ScheduleRuleUpdateInput,
): Promise<ScheduleRule> {
  return worldRequest<ScheduleRule>(`/api/worlds/${worldId}/schedule-rules/${ruleId}`, {
    method: "PATCH",
    body: input,
    csrf: true,
  });
}

export function disableScheduleRule(worldId: string, ruleId: string): Promise<void> {
  return worldRequest<void>(`/api/worlds/${worldId}/schedule-rules/${ruleId}`, {
    method: "DELETE",
    csrf: true,
  });
}

export function listAgentMemory(worldId: string, agentId: string): Promise<MemoryItem[]> {
  return worldRequest<MemoryItem[]>(`/api/worlds/${worldId}/agents/${agentId}/memory`, {
    method: "GET",
  });
}

export function createAgentMemoryItem(
  worldId: string,
  agentId: string,
  input: MemoryItemCreateInput,
): Promise<MemoryItem> {
  return worldRequest<MemoryItem>(`/api/worlds/${worldId}/agents/${agentId}/memory`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function searchAgentMemory(
  worldId: string,
  agentId: string,
  input: MemorySearchInput,
): Promise<MemoryItem[]> {
  return worldRequest<MemoryItem[]>(`/api/worlds/${worldId}/agents/${agentId}/memory/search`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function disableAgentMemoryItem(
  worldId: string,
  agentId: string,
  memoryId: string,
): Promise<void> {
  return worldRequest<void>(`/api/worlds/${worldId}/agents/${agentId}/memory/${memoryId}`, {
    method: "DELETE",
    csrf: true,
  });
}

export function createAgent(worldId: string, input: AgentCreateInput): Promise<Agent> {
  return worldRequest<Agent>(`/api/worlds/${worldId}/agents`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function updateAgent(
  worldId: string,
  agentId: string,
  input: AgentUpdateInput,
): Promise<Agent> {
  return worldRequest<Agent>(`/api/worlds/${worldId}/agents/${agentId}`, {
    method: "PATCH",
    body: input,
    csrf: true,
  });
}

export function deactivateAgent(worldId: string, agentId: string): Promise<void> {
  return worldRequest<void>(`/api/worlds/${worldId}/agents/${agentId}`, {
    method: "DELETE",
    csrf: true,
  });
}

export function listMemberships(worldId: string): Promise<Membership[]> {
  return worldRequest<Membership[]>(`/api/worlds/${worldId}/memberships`, { method: "GET" });
}

export function upsertMembership(
  worldId: string,
  userId: string,
  role: WorldRole,
): Promise<Membership> {
  return worldRequest<Membership>(`/api/worlds/${worldId}/memberships/${userId}`, {
    method: "PUT",
    body: { user_id: userId, role },
    csrf: true,
  });
}

export function deleteMembership(worldId: string, userId: string): Promise<void> {
  return worldRequest<void>(`/api/worlds/${worldId}/memberships/${userId}`, {
    method: "DELETE",
    csrf: true,
  });
}

export function listMemberCandidates(
  worldId: string,
  query: string,
  limit = 20,
): Promise<MemberCandidate[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (query.trim() !== "") {
    params.set("query", query.trim());
  }
  return worldRequest<MemberCandidate[]>(
    `/api/worlds/${worldId}/member-candidates?${params.toString()}`,
    { method: "GET" },
  );
}

type WorldRequestOptions = {
  method: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  csrf?: boolean;
};

async function worldRequest<T>(path: string, options: WorldRequestOptions): Promise<T> {
  const headers = new Headers();
  if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }
  if (options.csrf === true) {
    headers.set(CSRF_HEADER_NAME, await csrfToken());
  }

  const response = await fetch(path, {
    method: options.method,
    headers,
    credentials: "include",
    cache: "no-store",
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });

  if (response.status === 204) {
    return undefined as T;
  }
  if (response.ok) {
    return (await response.json()) as T;
  }

  const detail = await errorDetail(response);
  throw new WorldClientError(detail ?? "World request failed.", response.status);
}

async function csrfToken(): Promise<string> {
  const existingToken = readCookie(CSRF_COOKIE_NAME);
  if (existingToken !== null) {
    return existingToken;
  }
  const response = await requestCsrf();
  return response.csrf_token;
}

async function errorDetail(response: Response): Promise<string | null> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    return typeof body.detail === "string" ? body.detail : null;
  } catch {
    return null;
  }
}
