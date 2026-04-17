import { headers } from "next/headers";

import { getAuthApiBaseUrl } from "@/lib/auth/server-config";
import type {
  Agent,
  CalendarEntry,
  MemoryItem,
  Membership,
  Scene,
  ScheduleRule,
  World,
  WorldClock,
  WorldDashboardData,
  WorldReplayState,
  WorldSnapshot,
} from "@/lib/worlds/types";

export async function getWorldDashboardData(
  requestedWorldId: string | null,
): Promise<WorldDashboardData> {
  const cookieHeader = (await headers()).get("cookie");
  try {
    const worlds = await apiFetch<World[]>("/worlds", cookieHeader);
    const selectedWorld = selectedWorldForRequest(worlds, requestedWorldId);
    if (selectedWorld === null) {
      return emptyDashboardData(worlds, null, null);
    }

    const [scenes, agents, memberships, clock, replayState, latestSnapshot, scheduleRules] =
      await Promise.all([
        apiFetch<Scene[]>(`/worlds/${selectedWorld.id}/scenes`, cookieHeader),
        apiFetch<Agent[]>(`/worlds/${selectedWorld.id}/agents`, cookieHeader),
        apiFetchOptional<Membership[]>(`/worlds/${selectedWorld.id}/memberships`, cookieHeader),
        apiFetch<WorldClock>(`/worlds/${selectedWorld.id}/clock`, cookieHeader),
        apiFetch<WorldReplayState>(`/worlds/${selectedWorld.id}/replay/state`, cookieHeader),
        apiFetch<WorldSnapshot | null>(`/worlds/${selectedWorld.id}/snapshots/latest`, cookieHeader),
        apiFetch<ScheduleRule[]>(`/worlds/${selectedWorld.id}/schedule-rules`, cookieHeader),
      ]);
    const selectedAgent = agents[0] ?? null;
    const [calendarEntries, memoryItems] =
      selectedAgent === null
        ? [[], []]
        : await Promise.all([
            apiFetch<CalendarEntry[]>(
              `/worlds/${selectedWorld.id}/agents/${selectedAgent.id}/calendar`,
              cookieHeader,
            ),
            memberships === null
              ? Promise.resolve<MemoryItem[]>([])
              : apiFetch<MemoryItem[]>(
                  `/worlds/${selectedWorld.id}/agents/${selectedAgent.id}/memory`,
                  cookieHeader,
                ),
          ]);

    return {
      worlds,
      selectedWorldId: selectedWorld.id,
      scenes,
      agents,
      memberships: memberships ?? [],
      clock,
      replayState,
      latestSnapshot,
      selectedAgentId: selectedAgent?.id ?? null,
      calendarEntries,
      scheduleRules,
      memoryItems,
      canManageSelectedWorld: memberships !== null,
      loadError: null,
    };
  } catch (error) {
    if (error instanceof WorldServerError && error.status === 401) {
      throw error;
    }
    return emptyDashboardData([], null, "Unable to load world data.");
  }
}

class WorldServerError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "WorldServerError";
  }
}

async function apiFetch<T>(path: string, cookieHeader: string | null): Promise<T> {
  const response = await fetch(`${getAuthApiBaseUrl()}${path}`, {
    headers: cookieHeader === null ? undefined : { cookie: cookieHeader },
    cache: "no-store",
  });
  if (response.ok) {
    return (await response.json()) as T;
  }
  throw new WorldServerError(await errorDetail(response), response.status);
}

async function apiFetchOptional<T>(path: string, cookieHeader: string | null): Promise<T | null> {
  try {
    return await apiFetch<T>(path, cookieHeader);
  } catch (error) {
    if (
      error instanceof WorldServerError
      && (error.status === 403 || error.status === 404)
    ) {
      return null;
    }
    throw error;
  }
}

function selectedWorldForRequest(worlds: World[], requestedWorldId: string | null): World | null {
  if (worlds.length === 0) {
    return null;
  }
  if (requestedWorldId !== null) {
    const requestedWorld = worlds.find((world) => world.id === requestedWorldId);
    if (requestedWorld !== undefined) {
      return requestedWorld;
    }
  }
  return worlds[0];
}

function emptyDashboardData(
  worlds: World[],
  selectedWorldId: string | null,
  loadError: string | null,
): WorldDashboardData {
  return {
    worlds,
    selectedWorldId,
    scenes: [],
    agents: [],
    memberships: [],
    clock: null,
    replayState: null,
    latestSnapshot: null,
    selectedAgentId: null,
    calendarEntries: [],
    scheduleRules: [],
    memoryItems: [],
    canManageSelectedWorld: false,
    loadError,
  };
}

async function errorDetail(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    return typeof body.detail === "string" ? body.detail : "World request failed.";
  } catch {
    return "World request failed.";
  }
}
