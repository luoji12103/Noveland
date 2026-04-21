import { headers } from "next/headers";

import { getAuthApiBaseUrl } from "@/lib/auth/server-config";
import type {
  Agent,
  AgentObservation,
  AgentPersona,
  AgentRun,
  CalendarEntry,
  ConversationParticipant,
  ConversationSession,
  ConversationTurn,
  MemoryItem,
  Membership,
  NarrativeArtifact,
  ProviderProfile,
  RuntimeDiagnostic,
  RuntimeControl,
  RuntimeStatus,
  Scene,
  ScheduleRule,
  World,
  WorldClock,
  WorldDashboardData,
  WorldReplayState,
  WorldSnapshot,
} from "@/lib/worlds/types";

export type WorldWorkspaceData = {
  worlds: World[];
  selectedWorld: World | null;
  scenes: Scene[];
  agents: Agent[];
  memberships: Membership[];
  clock: WorldClock | null;
  replayState: WorldReplayState | null;
  latestSnapshot: WorldSnapshot | null;
  scheduleRules: ScheduleRule[];
  worldDiagnostics: RuntimeDiagnostic[];
  canManageSelectedWorld: boolean;
  loadError: string | null;
};

export type AgentWorkspaceData = {
  worlds: World[];
  selectedWorld: World | null;
  scenes: Scene[];
  agents: Agent[];
  providerProfiles: ProviderProfile[];
  loadError: string | null;
};

export type AgentDetailData = AgentWorkspaceData & {
  selectedAgent: Agent | null;
  calendarEntries: CalendarEntry[];
  memoryItems: MemoryItem[];
  agentRuns: AgentRun[];
  agentPersona: AgentPersona | null;
  agentObservations: AgentObservation[];
};

export type ConversationListData = {
  worlds: World[];
  selectedWorld: World | null;
  scenes: Scene[];
  agents: Agent[];
  conversations: ConversationSession[];
  canManageSelectedWorld: boolean;
  loadError: string | null;
};

export type ConversationDetailData = ConversationListData & {
  conversation: ConversationSession | null;
  participants: ConversationParticipant[];
  turns: ConversationTurn[];
  diagnostics: RuntimeDiagnostic[];
  narrativeArtifacts: NarrativeArtifact[];
};

export type NarrativeWorkspaceData = {
  worlds: World[];
  selectedWorld: World | null;
  agents: Agent[];
  narrativeArtifacts: NarrativeArtifact[];
  canManageSelectedWorld: boolean;
  loadError: string | null;
};

export type NarrativeReaderListData = {
  worlds: World[];
  selectedWorld: World | null;
  conversations: ConversationSession[];
  narrativeArtifacts: NarrativeArtifact[];
  selectedArtifactKind: string;
  selectedConversationId: string;
  loadError: string | null;
};

export type NarrativeReaderDetailData = {
  worlds: World[];
  selectedWorld: World | null;
  conversations: ConversationSession[];
  artifact: NarrativeArtifact | null;
  loadError: string | null;
};

export type RuntimeAdminData = {
  runtimeControl: RuntimeControl | null;
  runtimeStatus: RuntimeStatus | null;
  runtimeDiagnostics: RuntimeDiagnostic[];
  loadError: string | null;
};

export async function getWorldDashboardData(
  requestedWorldId: string | null,
  isPlatformAdmin: boolean,
): Promise<WorldDashboardData> {
  const cookieHeader = (await headers()).get("cookie");
  try {
    const [providerProfiles, runtimeControl, runtimeStatus, runtimeDiagnostics] = isPlatformAdmin
      ? await Promise.all([
          apiFetch<ProviderProfile[]>("/provider-profiles", cookieHeader),
          apiFetch<RuntimeControl>("/runtime/control", cookieHeader),
          apiFetch<RuntimeStatus>("/runtime/status", cookieHeader),
          apiFetch<RuntimeDiagnostic[]>("/runtime/diagnostics", cookieHeader),
        ])
      : [[], null, null, []];
    const worlds = await apiFetch<World[]>("/worlds", cookieHeader);
    const selectedWorld = selectedWorldForRequest(worlds, requestedWorldId);
    if (selectedWorld === null) {
      return emptyDashboardData(
        worlds,
        null,
        null,
        providerProfiles,
        runtimeControl,
        runtimeStatus,
        runtimeDiagnostics,
      );
    }

    const [
      scenes,
      agents,
      memberships,
      clock,
      replayState,
      latestSnapshot,
      scheduleRules,
      narrativeArtifacts,
      worldDiagnostics,
    ] =
      await Promise.all([
        apiFetch<Scene[]>(`/worlds/${selectedWorld.id}/scenes`, cookieHeader),
        apiFetch<Agent[]>(`/worlds/${selectedWorld.id}/agents`, cookieHeader),
        apiFetchOptional<Membership[]>(`/worlds/${selectedWorld.id}/memberships`, cookieHeader),
        apiFetch<WorldClock>(`/worlds/${selectedWorld.id}/clock`, cookieHeader),
        apiFetch<WorldReplayState>(`/worlds/${selectedWorld.id}/replay/state`, cookieHeader),
        apiFetch<WorldSnapshot | null>(`/worlds/${selectedWorld.id}/snapshots/latest`, cookieHeader),
        apiFetch<ScheduleRule[]>(`/worlds/${selectedWorld.id}/schedule-rules`, cookieHeader),
        apiFetch<NarrativeArtifact[]>(`/worlds/${selectedWorld.id}/narrative-artifacts`, cookieHeader),
        apiFetchOptional<RuntimeDiagnostic[]>(`/worlds/${selectedWorld.id}/diagnostics`, cookieHeader),
      ]);
    const selectedAgent = agents[0] ?? null;
    const [calendarEntries, memoryItems, agentRuns, agentPersona, agentObservations] =
      selectedAgent === null
        ? [[], [], [], null, []]
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
            apiFetch<AgentRun[]>(
              `/worlds/${selectedWorld.id}/agents/${selectedAgent.id}/runs`,
              cookieHeader,
            ),
            memberships === null
              ? Promise.resolve<AgentPersona | null>(null)
              : apiFetch<AgentPersona | null>(
                  `/worlds/${selectedWorld.id}/agents/${selectedAgent.id}/persona`,
                  cookieHeader,
                ),
            memberships === null
              ? Promise.resolve<AgentObservation[]>([])
              : apiFetch<AgentObservation[]>(
                  `/worlds/${selectedWorld.id}/agents/${selectedAgent.id}/observations`,
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
      agentRuns,
      agentPersona,
      agentObservations,
      narrativeArtifacts,
      providerProfiles,
      runtimeControl,
      runtimeStatus,
      runtimeDiagnostics,
      worldDiagnostics: worldDiagnostics ?? [],
      canManageSelectedWorld: memberships !== null,
      loadError: null,
    };
  } catch (error) {
    if (error instanceof WorldServerError && error.status === 401) {
      throw error;
    }
    return emptyDashboardData([], null, "Unable to load world data.", [], null, null, []);
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

export async function getWorldsIndexData(): Promise<World[]> {
  return apiFetch<World[]>("/worlds", await cookieHeader());
}

export async function getWorldWorkspaceData(
  worldId: string,
): Promise<WorldWorkspaceData> {
  const cookies = await cookieHeader();
  try {
    const worlds = await apiFetch<World[]>("/worlds", cookies);
    const selectedWorld = worlds.find((world) => world.id === worldId) ?? null;
    if (selectedWorld === null) {
      return emptyWorldWorkspaceData(worlds, "Unable to load selected world.");
    }
    const [
      scenes,
      agents,
      memberships,
      clock,
      replayState,
      latestSnapshot,
      scheduleRules,
      worldDiagnostics,
    ] = await Promise.all([
      apiFetch<Scene[]>(`/worlds/${worldId}/scenes`, cookies),
      apiFetch<Agent[]>(`/worlds/${worldId}/agents`, cookies),
      apiFetchOptional<Membership[]>(`/worlds/${worldId}/memberships`, cookies),
      apiFetch<WorldClock>(`/worlds/${worldId}/clock`, cookies),
      apiFetch<WorldReplayState>(`/worlds/${worldId}/replay/state`, cookies),
      apiFetch<WorldSnapshot | null>(`/worlds/${worldId}/snapshots/latest`, cookies),
      apiFetch<ScheduleRule[]>(`/worlds/${worldId}/schedule-rules`, cookies),
      apiFetchOptional<RuntimeDiagnostic[]>(`/worlds/${worldId}/diagnostics`, cookies),
    ]);
    return {
      worlds,
      selectedWorld,
      scenes,
      agents,
      memberships: memberships ?? [],
      clock,
      replayState,
      latestSnapshot,
      scheduleRules,
      worldDiagnostics: worldDiagnostics ?? [],
      canManageSelectedWorld: memberships !== null,
      loadError: null,
    };
  } catch (error) {
    if (error instanceof WorldServerError && error.status === 401) {
      throw error;
    }
    return emptyWorldWorkspaceData([], "Unable to load world workspace.");
  }
}

export async function getAgentWorkspaceData(
  worldId: string,
  isPlatformAdmin: boolean,
): Promise<AgentWorkspaceData> {
  const cookies = await cookieHeader();
  try {
    const [worlds, scenes, agents, providerProfiles] = await Promise.all([
      apiFetch<World[]>("/worlds", cookies),
      apiFetch<Scene[]>(`/worlds/${worldId}/scenes`, cookies),
      apiFetch<Agent[]>(`/worlds/${worldId}/agents`, cookies),
      isPlatformAdmin ? apiFetch<ProviderProfile[]>("/provider-profiles", cookies) : [],
    ]);
    return {
      worlds,
      selectedWorld: worlds.find((world) => world.id === worldId) ?? null,
      scenes,
      agents,
      providerProfiles,
      loadError: null,
    };
  } catch (error) {
    if (error instanceof WorldServerError && error.status === 401) {
      throw error;
    }
    return {
      worlds: [],
      selectedWorld: null,
      scenes: [],
      agents: [],
      providerProfiles: [],
      loadError: "Unable to load agents.",
    };
  }
}

export async function getAgentDetailData(
  worldId: string,
  agentId: string,
  isPlatformAdmin: boolean,
): Promise<AgentDetailData> {
  const data = await getAgentWorkspaceData(worldId, isPlatformAdmin);
  const selectedAgent = data.agents.find((agent) => agent.id === agentId) ?? null;
  if (selectedAgent === null || data.selectedWorld === null) {
    return {
      ...data,
      selectedAgent: null,
      calendarEntries: [],
      memoryItems: [],
      agentRuns: [],
      agentPersona: null,
      agentObservations: [],
    };
  }
  const cookies = await cookieHeader();
  const [calendarEntries, memoryItems, agentRuns, agentPersona, agentObservations] =
    await Promise.all([
      apiFetch<CalendarEntry[]>(`/worlds/${worldId}/agents/${agentId}/calendar`, cookies),
      apiFetchOptional<MemoryItem[]>(`/worlds/${worldId}/agents/${agentId}/memory`, cookies),
      apiFetch<AgentRun[]>(`/worlds/${worldId}/agents/${agentId}/runs`, cookies),
      apiFetchOptional<AgentPersona | null>(
        `/worlds/${worldId}/agents/${agentId}/persona`,
        cookies,
      ),
      apiFetchOptional<AgentObservation[]>(
        `/worlds/${worldId}/agents/${agentId}/observations`,
        cookies,
      ),
    ]);
  return {
    ...data,
    selectedAgent,
    calendarEntries,
    memoryItems: memoryItems ?? [],
    agentRuns,
    agentPersona,
    agentObservations: agentObservations ?? [],
  };
}

export async function getConversationListData(worldId: string): Promise<ConversationListData> {
  const cookies = await cookieHeader();
  try {
    const [worlds, scenes, agents, conversations, memberships] = await Promise.all([
      apiFetch<World[]>("/worlds", cookies),
      apiFetch<Scene[]>(`/worlds/${worldId}/scenes`, cookies),
      apiFetch<Agent[]>(`/worlds/${worldId}/agents`, cookies),
      apiFetch<ConversationSession[]>(`/worlds/${worldId}/conversations`, cookies),
      apiFetchOptional<Membership[]>(`/worlds/${worldId}/memberships`, cookies),
    ]);
    return {
      worlds,
      selectedWorld: worlds.find((world) => world.id === worldId) ?? null,
      scenes,
      agents,
      conversations,
      canManageSelectedWorld: memberships !== null,
      loadError: null,
    };
  } catch (error) {
    if (error instanceof WorldServerError && error.status === 401) {
      throw error;
    }
    return emptyConversationListData("Unable to load conversations.");
  }
}

export async function getConversationDetailData(
  worldId: string,
  conversationId: string,
): Promise<ConversationDetailData> {
  const listData = await getConversationListData(worldId);
  const cookies = await cookieHeader();
  const conversation =
    listData.conversations.find((item) => item.id === conversationId) ?? null;
  if (conversation === null) {
    return {
      ...listData,
      conversation: null,
      participants: [],
      turns: [],
      diagnostics: [],
      narrativeArtifacts: [],
    };
  }
  const [participants, turns, diagnostics, narrativeArtifacts] = await Promise.all([
    apiFetch<ConversationParticipant[]>(
      `/worlds/${worldId}/conversations/${conversationId}/participants`,
      cookies,
    ),
    apiFetch<ConversationTurn[]>(
      `/worlds/${worldId}/conversations/${conversationId}/turns`,
      cookies,
    ),
    apiFetchOptional<RuntimeDiagnostic[]>(
      `/worlds/${worldId}/conversations/${conversationId}/diagnostics`,
      cookies,
    ),
    apiFetch<NarrativeArtifact[]>(
      `/worlds/${worldId}/conversations/${conversationId}/narrative`,
      cookies,
    ),
  ]);
  return {
    ...listData,
    conversation,
    participants,
    turns,
    diagnostics: diagnostics ?? [],
    narrativeArtifacts,
  };
}

export async function getNarrativeWorkspaceData(
  worldId: string,
): Promise<NarrativeWorkspaceData> {
  const cookies = await cookieHeader();
  try {
    const [worlds, agents, narrativeArtifacts, memberships] = await Promise.all([
      apiFetch<World[]>("/worlds", cookies),
      apiFetch<Agent[]>(`/worlds/${worldId}/agents`, cookies),
      apiFetch<NarrativeArtifact[]>(`/worlds/${worldId}/narrative-artifacts`, cookies),
      apiFetchOptional<Membership[]>(`/worlds/${worldId}/memberships`, cookies),
    ]);
    return {
      worlds,
      selectedWorld: worlds.find((world) => world.id === worldId) ?? null,
      agents,
      narrativeArtifacts,
      canManageSelectedWorld: memberships !== null,
      loadError: null,
    };
  } catch (error) {
    if (error instanceof WorldServerError && error.status === 401) {
      throw error;
    }
    return {
      worlds: [],
      selectedWorld: null,
      agents: [],
      narrativeArtifacts: [],
      canManageSelectedWorld: false,
      loadError: "Unable to load narrative artifacts.",
    };
  }
}

export async function getNarrativeReaderListData(
  worldId: string,
  filters: {
    artifactKind?: string | null;
    sourceConversationId?: string | null;
    limit?: number;
  } = {},
): Promise<NarrativeReaderListData> {
  const cookies = await cookieHeader();
  try {
    const worlds = await apiFetch<World[]>("/worlds", cookies);
    const selectedWorld = worlds.find((world) => world.id === worldId) ?? null;
    if (selectedWorld === null) {
      return emptyNarrativeReaderListData(
        worlds,
        "Unable to load narrative reader.",
        filters.artifactKind ?? "",
        filters.sourceConversationId ?? "",
      );
    }

    const [conversations, narrativeArtifacts] = await Promise.all([
      apiFetch<ConversationSession[]>(`/worlds/${worldId}/conversations`, cookies),
      apiFetch<NarrativeArtifact[]>(
        `/worlds/${worldId}/narrative-artifacts${narrativeArtifactQuery(filters)}`,
        cookies,
      ),
    ]);

    return {
      worlds,
      selectedWorld,
      conversations,
      narrativeArtifacts,
      selectedArtifactKind: filters.artifactKind ?? "",
      selectedConversationId: filters.sourceConversationId ?? "",
      loadError: null,
    };
  } catch (error) {
    if (error instanceof WorldServerError && error.status === 401) {
      throw error;
    }
    return emptyNarrativeReaderListData(
      [],
      "Unable to load narrative reader.",
      filters.artifactKind ?? "",
      filters.sourceConversationId ?? "",
    );
  }
}

export async function getNarrativeReaderDetailData(
  worldId: string,
  artifactId: string,
): Promise<NarrativeReaderDetailData> {
  const cookies = await cookieHeader();
  try {
    const worlds = await apiFetch<World[]>("/worlds", cookies);
    const selectedWorld = worlds.find((world) => world.id === worldId) ?? null;
    if (selectedWorld === null) {
      return emptyNarrativeReaderDetailData(worlds, "Unable to load narrative artifact.");
    }

    const [conversations, artifact] = await Promise.all([
      apiFetch<ConversationSession[]>(`/worlds/${worldId}/conversations`, cookies),
      apiFetch<NarrativeArtifact>(`/worlds/${worldId}/narrative-artifacts/${artifactId}`, cookies),
    ]);

    return {
      worlds,
      selectedWorld,
      conversations,
      artifact,
      loadError: null,
    };
  } catch (error) {
    if (error instanceof WorldServerError && error.status === 401) {
      throw error;
    }
    return emptyNarrativeReaderDetailData([], "Unable to load narrative artifact.");
  }
}

export async function getProviderAdminData(): Promise<ProviderProfile[]> {
  return apiFetch<ProviderProfile[]>("/provider-profiles", await cookieHeader());
}

export async function getRuntimeAdminData(): Promise<RuntimeAdminData> {
  const cookies = await cookieHeader();
  try {
    const [runtimeControl, runtimeStatus, runtimeDiagnostics] = await Promise.all([
      apiFetch<RuntimeControl>("/runtime/control", cookies),
      apiFetch<RuntimeStatus>("/runtime/status", cookies),
      apiFetch<RuntimeDiagnostic[]>("/runtime/diagnostics", cookies),
    ]);
    return { runtimeControl, runtimeStatus, runtimeDiagnostics, loadError: null };
  } catch (error) {
    if (error instanceof WorldServerError && error.status === 401) {
      throw error;
    }
    return {
      runtimeControl: null,
      runtimeStatus: null,
      runtimeDiagnostics: [],
      loadError: "Unable to load runtime state.",
    };
  }
}

async function cookieHeader(): Promise<string | null> {
  return (await headers()).get("cookie");
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

function emptyWorldWorkspaceData(worlds: World[], loadError: string): WorldWorkspaceData {
  return {
    worlds,
    selectedWorld: null,
    scenes: [],
    agents: [],
    memberships: [],
    clock: null,
    replayState: null,
    latestSnapshot: null,
    scheduleRules: [],
    worldDiagnostics: [],
    canManageSelectedWorld: false,
    loadError,
  };
}

function emptyNarrativeReaderListData(
  worlds: World[],
  loadError: string,
  selectedArtifactKind: string,
  selectedConversationId: string,
): NarrativeReaderListData {
  return {
    worlds,
    selectedWorld: null,
    conversations: [],
    narrativeArtifacts: [],
    selectedArtifactKind,
    selectedConversationId,
    loadError,
  };
}

function emptyNarrativeReaderDetailData(
  worlds: World[],
  loadError: string,
): NarrativeReaderDetailData {
  return {
    worlds,
    selectedWorld: null,
    conversations: [],
    artifact: null,
    loadError,
  };
}

function emptyConversationListData(loadError: string): ConversationListData {
  return {
    worlds: [],
    selectedWorld: null,
    scenes: [],
    agents: [],
    conversations: [],
    canManageSelectedWorld: false,
    loadError,
  };
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
  providerProfiles: ProviderProfile[],
  runtimeControl: RuntimeControl | null,
  runtimeStatus: RuntimeStatus | null,
  runtimeDiagnostics: RuntimeDiagnostic[],
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
    agentRuns: [],
    agentPersona: null,
    agentObservations: [],
    narrativeArtifacts: [],
    providerProfiles,
    runtimeControl,
    runtimeStatus,
    runtimeDiagnostics,
    worldDiagnostics: [],
    canManageSelectedWorld: false,
    loadError,
  };
}

function narrativeArtifactQuery(filters: {
  artifactKind?: string | null;
  sourceConversationId?: string | null;
  limit?: number;
}): string {
  const search = new URLSearchParams();
  if (filters.artifactKind) {
    search.set("artifact_kind", filters.artifactKind);
  }
  if (filters.sourceConversationId) {
    search.set("source_conversation_id", filters.sourceConversationId);
  }
  if (filters.limit !== undefined) {
    search.set("limit", String(filters.limit));
  }
  return search.size === 0 ? "" : `?${search.toString()}`;
}

async function errorDetail(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    return typeof body.detail === "string" ? body.detail : "World request failed.";
  } catch {
    return "World request failed.";
  }
}
