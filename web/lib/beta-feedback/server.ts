import { headers } from "next/headers";

import { getAuthApiBaseUrl } from "@/lib/auth/server-config";
import type { BetaFeedbackReport } from "@/lib/beta-feedback/types";
import type { Membership, World, Worldline } from "@/lib/worlds/types";

export type BetaFeedbackData = {
  worlds: World[];
  selectedWorld: World | null;
  worldlines: Worldline[];
  reports: BetaFeedbackReport[];
  canManageSelectedWorld: boolean;
  loadError: string | null;
};

class BetaFeedbackServerError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "BetaFeedbackServerError";
  }
}

export async function getBetaFeedbackData(
  worldId: string,
  isPlatformAdmin: boolean,
): Promise<BetaFeedbackData> {
  const cookies = await cookieHeader();
  try {
    const worlds = await apiFetch<World[]>("/worlds", cookies);
    const selectedWorld = worlds.find((world) => world.id === worldId) ?? null;
    if (selectedWorld === null) {
      return emptyBetaFeedbackData(worlds, "Unable to load selected world.");
    }
    const worldPath = `/worlds/${pathSegment(worldId)}`;
    const [worldlines, reports, memberships] = await Promise.all([
      apiFetch<Worldline[]>(`${worldPath}/worldlines`, cookies),
      apiFetch<BetaFeedbackReport[]>(`${worldPath}/beta-feedback/reports`, cookies),
      apiFetchOptional<Membership[]>(`${worldPath}/memberships`, cookies),
    ]);
    return {
      worlds,
      selectedWorld,
      worldlines,
      reports,
      canManageSelectedWorld: isPlatformAdmin || memberships !== null,
      loadError: null,
    };
  } catch (error) {
    if (error instanceof BetaFeedbackServerError && error.status === 401) {
      throw error;
    }
    return emptyBetaFeedbackData([], "Unable to load beta feedback.");
  }
}

async function cookieHeader(): Promise<string | null> {
  return (await headers()).get("cookie");
}

function pathSegment(value: string): string {
  return encodeURIComponent(value);
}

async function apiFetch<T>(path: string, cookieHeaderValue: string | null): Promise<T> {
  const response = await fetch(`${getAuthApiBaseUrl()}${path}`, {
    headers: cookieHeaderValue === null ? undefined : { cookie: cookieHeaderValue },
    cache: "no-store",
  });
  if (response.ok) {
    return (await response.json()) as T;
  }
  throw new BetaFeedbackServerError(await errorDetail(response), response.status);
}

async function apiFetchOptional<T>(path: string, cookieHeaderValue: string | null): Promise<T | null> {
  try {
    return await apiFetch<T>(path, cookieHeaderValue);
  } catch (error) {
    if (
      error instanceof BetaFeedbackServerError
      && (error.status === 403 || error.status === 404)
    ) {
      return null;
    }
    throw error;
  }
}

async function errorDetail(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    return typeof body.detail === "string" ? body.detail : "Beta feedback request failed.";
  } catch {
    return "Beta feedback request failed.";
  }
}

function emptyBetaFeedbackData(worlds: World[], loadError: string): BetaFeedbackData {
  return {
    worlds,
    selectedWorld: null,
    worldlines: [],
    reports: [],
    canManageSelectedWorld: false,
    loadError,
  };
}
