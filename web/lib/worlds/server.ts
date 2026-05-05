import { headers } from "next/headers";

import { getAuthApiBaseUrl } from "@/lib/auth/server-config";
import type {
  Agent,
  AgentObservation,
  AgentPresence,
  AgentPreset,
  AgentPersona,
  AgentRelationship,
  AgentRun,
  CalendarConflictReport,
  CalendarEntry,
  ConversationParticipant,
  ConversationDiagnosticsSummary,
  ConversationSession,
  ConversationTurn,
  DailyLifeEventCandidate,
  DailyLifePreview,
  ExternalToolPolicy,
  FactionProgressTrack,
  MemoryBackendProfile,
  MemoryBackendHealth,
  MemoryBackendLogs,
  MemoryBackfillDryRun,
  MemoryWriteJobList,
  MemoryItem,
  MemoryProfileSnapshot,
  Membership,
  NarrativeArtifact,
  NarrativeArtifactFilters,
  OffscreenEventQueueItem,
  OrganizationMembership,
  PluginBinding,
  PluginCatalogEntry,
  ProviderHealth,
  ProviderProfile,
  RuntimeDiagnostic,
  RuntimeControl,
  RuntimeStatus,
  ScaleReadiness,
  Scene,
  SceneLocationEdge,
  ScheduleRule,
  World,
  WorldBible,
  WorldClock,
  WorldClockTransition,
  WorldDashboardData,
  WorldEventAuditEntry,
  WorldReplayState,
  WorldSnapshot,
  WorldSnapshotIntegrity,
  WorldOrganization,
} from "@/lib/worlds/types";

export type WorldWorkspaceData = {
  worlds: World[];
  selectedWorld: World | null;
  scenes: Scene[];
  locationEdges: SceneLocationEdge[];
  agents: Agent[];
  organizations: WorldOrganization[];
  organizationMemberships: OrganizationMembership[];
  factionTracks: FactionProgressTrack[];
  agentPresenceStates: AgentPresence[];
  dailyLifePreview: DailyLifePreview | null;
  dailyLifeCandidates: DailyLifeEventCandidate[];
  offscreenEvents: OffscreenEventQueueItem[];
  memberships: Membership[];
  worldBible: WorldBible | null;
  memoryBackendProfiles: MemoryBackendProfile[];
  memoryPlugins: PluginCatalogEntry[];
  worldRulesPlugins: PluginCatalogEntry[];
  clock: WorldClock | null;
  clockTransitions: WorldClockTransition[];
  replayState: WorldReplayState | null;
  latestSnapshot: WorldSnapshot | null;
  snapshotIntegrity: WorldSnapshotIntegrity | null;
  worldEventAudit: WorldEventAuditEntry[];
  calendarConflicts: CalendarConflictReport | null;
  scheduleRules: ScheduleRule[];
  worldDiagnostics: RuntimeDiagnostic[];
  canManageSelectedWorld: boolean;
  isPlatformAdmin: boolean;
  loadError: string | null;
};

export type AgentWorkspaceData = {
  worlds: World[];
  selectedWorld: World | null;
  scenes: Scene[];
  agents: Agent[];
  providerProfiles: ProviderProfile[];
  agentPresets: AgentPreset[];
  personaPolicyPlugins: PluginCatalogEntry[];
  canManageSelectedWorld: boolean;
  isPlatformAdmin: boolean;
  loadError: string | null;
};

export type AgentDetailData = AgentWorkspaceData & {
  selectedAgent: Agent | null;
  presence: AgentPresence | null;
  organizationMemberships: OrganizationMembership[];
  relationships: AgentRelationship[];
  calendarEntries: CalendarEntry[];
  memoryItems: MemoryItem[];
  memoryProfileSnapshot: MemoryProfileSnapshot | null;
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
  diagnosticsSummary: ConversationDiagnosticsSummary | null;
  narrativeArtifacts: NarrativeArtifact[];
  narrativeWriterPlugins: PluginCatalogEntry[];
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
  selectedSearch: string;
  selectedSourceKind: string;
  selectedOrderBy: string;
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
  externalToolPolicy: ExternalToolPolicy | null;
  scaleReadiness: ScaleReadiness | null;
  runtimeDiagnostics: RuntimeDiagnostic[];
  modelProviderPlugins: PluginCatalogEntry[];
  loadError: string | null;
};

export type PresetAdminData = {
  presets: AgentPreset[];
  loadError: string | null;
};

export type ProviderAdminData = {
  profiles: ProviderProfile[];
  providerHealth: ProviderHealth[];
  modelProviderPlugins: PluginCatalogEntry[];
  pluginBindings: PluginBinding[];
  pluginDiagnostics: RuntimeDiagnostic[];
  loadError: string | null;
};

export type MemoryBackendAdminData = {
  profiles: MemoryBackendProfile[];
  profileHealth: Record<string, MemoryBackendHealth>;
  profileLogs: Record<string, MemoryBackendLogs>;
  profileJobs: Record<string, MemoryWriteJobList>;
  backfillDryRun: MemoryBackfillDryRun | null;
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
      locationEdges: [],
      agents,
      organizations: [],
      organizationMemberships: [],
      factionTracks: [],
      agentPresenceStates: [],
      dailyLifePreview: null,
      dailyLifeCandidates: [],
      offscreenEvents: [],
      memberships: memberships ?? [],
      clock,
      replayState,
      latestSnapshot,
      worldEventAudit: [],
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
  isPlatformAdmin: boolean,
): Promise<WorldWorkspaceData> {
  const cookies = await cookieHeader();
  try {
    const [worlds, memoryPlugins, worldRulesPlugins, memoryBackendProfiles] = await Promise.all([
      apiFetch<World[]>("/worlds", cookies),
      listPluginCatalogForServer("memory_backend", cookies),
      listPluginCatalogForServer("world_rules", cookies),
      isPlatformAdmin
        ? apiFetch<MemoryBackendProfile[]>("/memory-backend-profiles", cookies)
        : Promise.resolve<MemoryBackendProfile[]>([]),
    ]);
    const selectedWorld = worlds.find((world) => world.id === worldId) ?? null;
    if (selectedWorld === null) {
      return emptyWorldWorkspaceData(worlds, "Unable to load selected world.", isPlatformAdmin);
    }
    const [
      scenes,
      locationEdges,
      agents,
      organizations,
      memberships,
      worldBible,
      clock,
      clockTransitions,
      replayState,
      latestSnapshot,
      snapshotIntegrity,
      worldEventAudit,
      calendarConflicts,
      scheduleRules,
      dailyLifePreview,
      dailyLifeCandidates,
      offscreenEvents,
      worldDiagnostics,
    ] = await Promise.all([
      apiFetch<Scene[]>(`/worlds/${worldId}/scenes`, cookies),
      apiFetch<SceneLocationEdge[]>(`/worlds/${worldId}/location-edges`, cookies),
      apiFetch<Agent[]>(`/worlds/${worldId}/agents`, cookies),
      apiFetch<WorldOrganization[]>(`/worlds/${worldId}/organizations`, cookies),
      apiFetchOptional<Membership[]>(`/worlds/${worldId}/memberships`, cookies),
      apiFetch<WorldBible | null>(`/worlds/${worldId}/bible`, cookies),
      apiFetch<WorldClock>(`/worlds/${worldId}/clock`, cookies),
      apiFetchOptional<WorldClockTransition[]>(
        `/worlds/${worldId}/clock/transitions?limit=5`,
        cookies,
      ),
      apiFetch<WorldReplayState>(`/worlds/${worldId}/replay/state`, cookies),
      apiFetch<WorldSnapshot | null>(`/worlds/${worldId}/snapshots/latest`, cookies),
      apiFetchOptional<WorldSnapshotIntegrity>(`/worlds/${worldId}/snapshots/integrity`, cookies),
      apiFetchOptional<WorldEventAuditEntry[]>(`/worlds/${worldId}/events?limit=10`, cookies),
      apiFetchOptional<CalendarConflictReport>(`/worlds/${worldId}/calendar/conflicts`, cookies),
      apiFetch<ScheduleRule[]>(`/worlds/${worldId}/schedule-rules`, cookies),
      apiFetchOptional<DailyLifePreview>(`/worlds/${worldId}/daily-life/preview`, cookies),
      apiFetchOptional<DailyLifeEventCandidate[]>(
        `/worlds/${worldId}/daily-life/candidates?limit=10`,
        cookies,
      ),
      apiFetchOptional<OffscreenEventQueueItem[]>(
        `/worlds/${worldId}/offscreen-events?limit=10`,
        cookies,
      ),
      apiFetchOptional<RuntimeDiagnostic[]>(`/worlds/${worldId}/diagnostics`, cookies),
    ]);
    const [organizationMembershipGroups, factionTrackGroups, agentPresenceStates] =
      await Promise.all([
        Promise.all(
          organizations.map((organization) =>
            apiFetch<OrganizationMembership[]>(
              `/worlds/${worldId}/organizations/${organization.id}/memberships`,
              cookies,
            ),
          ),
        ),
        Promise.all(
          organizations.map((organization) =>
            apiFetch<FactionProgressTrack[]>(
              `/worlds/${worldId}/organizations/${organization.id}/faction-tracks`,
              cookies,
            ),
          ),
        ),
        Promise.all(
          agents.map((agent) =>
            apiFetch<AgentPresence | null>(
              `/worlds/${worldId}/agents/${agent.id}/presence`,
              cookies,
            ),
          ),
        ),
      ]);
    return {
      worlds,
      selectedWorld,
      scenes,
      locationEdges,
      agents,
      organizations,
      organizationMemberships: organizationMembershipGroups.flat(),
      factionTracks: factionTrackGroups.flat(),
      agentPresenceStates: agentPresenceStates.filter(
        (presence): presence is AgentPresence => presence !== null,
      ),
      dailyLifePreview,
      dailyLifeCandidates: dailyLifeCandidates ?? [],
      offscreenEvents: offscreenEvents ?? [],
      memberships: memberships ?? [],
      worldBible,
      memoryBackendProfiles,
      memoryPlugins,
      worldRulesPlugins,
      clock,
      clockTransitions: clockTransitions ?? [],
      replayState,
      latestSnapshot,
      snapshotIntegrity,
      worldEventAudit: worldEventAudit ?? [],
      calendarConflicts,
      scheduleRules,
      worldDiagnostics: worldDiagnostics ?? [],
      canManageSelectedWorld: memberships !== null,
      isPlatformAdmin,
      loadError: null,
    };
  } catch (error) {
    if (error instanceof WorldServerError && error.status === 401) {
      throw error;
    }
    return emptyWorldWorkspaceData([], "Unable to load world workspace.", isPlatformAdmin);
  }
}

export async function getAgentWorkspaceData(
  worldId: string,
  isPlatformAdmin: boolean,
): Promise<AgentWorkspaceData> {
  const cookies = await cookieHeader();
  try {
    const [
      worlds,
      scenes,
      agents,
      memberships,
      providerProfiles,
      agentPresets,
      personaPolicyPlugins,
    ] = await Promise.all([
      apiFetch<World[]>("/worlds", cookies),
      apiFetch<Scene[]>(`/worlds/${worldId}/scenes`, cookies),
      apiFetch<Agent[]>(`/worlds/${worldId}/agents`, cookies),
      apiFetchOptional<Membership[]>(`/worlds/${worldId}/memberships`, cookies),
      isPlatformAdmin ? apiFetch<ProviderProfile[]>("/provider-profiles", cookies) : [],
      apiFetch<AgentPreset[]>("/agent-presets", cookies),
      listPluginCatalogForServer("persona_policy", cookies),
    ]);
    return {
      worlds,
      selectedWorld: worlds.find((world) => world.id === worldId) ?? null,
      scenes,
      agents,
      providerProfiles,
      agentPresets,
      personaPolicyPlugins,
      canManageSelectedWorld: memberships !== null,
      isPlatformAdmin,
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
      agentPresets: [],
      personaPolicyPlugins: [],
      canManageSelectedWorld: false,
      isPlatformAdmin,
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
      presence: null,
      organizationMemberships: [],
      relationships: [],
      calendarEntries: [],
      memoryItems: [],
      memoryProfileSnapshot: null,
      agentRuns: [],
      agentPersona: null,
      agentObservations: [],
    };
  }
  const cookies = await cookieHeader();
  const [
    presence,
    organizations,
    relationships,
    calendarEntries,
    memoryItems,
    memoryProfileSnapshot,
    agentRuns,
    agentPersona,
    agentObservations,
  ] =
    await Promise.all([
      apiFetch<AgentPresence | null>(`/worlds/${worldId}/agents/${agentId}/presence`, cookies),
      apiFetch<WorldOrganization[]>(`/worlds/${worldId}/organizations`, cookies),
      apiFetch<AgentRelationship[]>(`/worlds/${worldId}/agents/${agentId}/relationships`, cookies),
      apiFetch<CalendarEntry[]>(`/worlds/${worldId}/agents/${agentId}/calendar`, cookies),
      apiFetchOptional<MemoryItem[]>(`/worlds/${worldId}/agents/${agentId}/memory`, cookies),
      data.canManageSelectedWorld
        ? apiFetchOptional<MemoryProfileSnapshot | null>(
            `/worlds/${worldId}/agents/${agentId}/memory/profile-snapshot`,
            cookies,
          )
        : Promise.resolve<MemoryProfileSnapshot | null>(null),
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
  const organizationMembershipGroups = await Promise.all(
    organizations.map((organization) =>
      apiFetch<OrganizationMembership[]>(
        `/worlds/${worldId}/organizations/${organization.id}/memberships`,
        cookies,
      ),
    ),
  );
  return {
    ...data,
    selectedAgent,
    presence,
    organizationMemberships: organizationMembershipGroups
      .flat()
      .filter((membership) => membership.agent_id === agentId),
    relationships,
    calendarEntries,
    memoryItems: memoryItems ?? [],
    memoryProfileSnapshot,
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
  const narrativeWriterPlugins = await listPluginCatalogForServer("narrative_writer", cookies);
  const conversation =
    listData.conversations.find((item) => item.id === conversationId) ?? null;
  if (conversation === null) {
    return {
      ...listData,
      conversation: null,
      participants: [],
      turns: [],
      diagnostics: [],
      diagnosticsSummary: null,
      narrativeArtifacts: [],
      narrativeWriterPlugins,
    };
  }
  const [
    participants,
    turns,
    diagnostics,
    diagnosticsSummary,
    narrativeArtifacts,
  ] = await Promise.all([
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
    apiFetchOptional<ConversationDiagnosticsSummary>(
      `/worlds/${worldId}/conversations/${conversationId}/diagnostics/summary`,
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
    diagnosticsSummary,
    narrativeArtifacts,
    narrativeWriterPlugins,
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
  filters: NarrativeArtifactFilters = {},
): Promise<NarrativeReaderListData> {
  const cookies = await cookieHeader();
  try {
    const worlds = await apiFetch<World[]>("/worlds", cookies);
    const selectedWorld = worlds.find((world) => world.id === worldId) ?? null;
    if (selectedWorld === null) {
      return emptyNarrativeReaderListData(
        worlds,
        "Unable to load narrative reader.",
        filters.artifact_kind ?? "",
        filters.source_conversation_id ?? "",
        filters.q ?? "",
        filters.source_kind ?? "",
        filters.order_by ?? "published_at",
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
      selectedArtifactKind: filters.artifact_kind ?? "",
      selectedConversationId: filters.source_conversation_id ?? "",
      selectedSearch: filters.q ?? "",
      selectedSourceKind: filters.source_kind ?? "",
      selectedOrderBy: filters.order_by ?? "published_at",
      loadError: null,
    };
  } catch (error) {
    if (error instanceof WorldServerError && error.status === 401) {
      throw error;
    }
    return emptyNarrativeReaderListData(
      [],
      "Unable to load narrative reader.",
      filters.artifact_kind ?? "",
      filters.source_conversation_id ?? "",
      filters.q ?? "",
      filters.source_kind ?? "",
      filters.order_by ?? "published_at",
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

export async function getProviderAdminData(): Promise<ProviderAdminData> {
  const cookies = await cookieHeader();
  try {
    const [
      profiles,
      providerHealth,
      modelProviderPlugins,
      pluginBindings,
      pluginDiagnostics,
    ] = await Promise.all([
      apiFetch<ProviderProfile[]>("/provider-profiles", cookies),
      apiFetch<ProviderHealth[]>("/provider-profiles/health", cookies),
      listPluginCatalogForServer("model_provider", cookies),
      apiFetch<PluginBinding[]>("/plugins/bindings", cookies),
      apiFetch<RuntimeDiagnostic[]>("/runtime/diagnostics?component=plugin&limit=5", cookies),
    ]);
    return {
      profiles,
      providerHealth,
      modelProviderPlugins,
      pluginBindings,
      pluginDiagnostics,
      loadError: null,
    };
  } catch (error) {
    if (error instanceof WorldServerError && error.status === 401) {
      throw error;
    }
    return {
      profiles: [],
      providerHealth: [],
      modelProviderPlugins: [],
      pluginBindings: [],
      pluginDiagnostics: [],
      loadError: "Unable to load provider profiles.",
    };
  }
}

export async function getRuntimeAdminData(): Promise<RuntimeAdminData> {
  const cookies = await cookieHeader();
  try {
    const [
      runtimeControl,
      runtimeStatus,
      externalToolPolicy,
      scaleReadiness,
      runtimeDiagnostics,
      modelProviderPlugins,
    ] = await Promise.all([
      apiFetch<RuntimeControl>("/runtime/control", cookies),
      apiFetch<RuntimeStatus>("/runtime/status", cookies),
      apiFetch<ExternalToolPolicy>("/runtime/tool-policy", cookies),
      apiFetch<ScaleReadiness>("/runtime/scale-readiness", cookies),
      apiFetch<RuntimeDiagnostic[]>("/runtime/diagnostics", cookies),
      listPluginCatalogForServer("model_provider", cookies),
    ]);
    return {
      runtimeControl,
      runtimeStatus,
      externalToolPolicy,
      scaleReadiness,
      runtimeDiagnostics,
      modelProviderPlugins,
      loadError: null,
    };
  } catch (error) {
    if (error instanceof WorldServerError && error.status === 401) {
      throw error;
    }
    return {
      runtimeControl: null,
      runtimeStatus: null,
      externalToolPolicy: null,
      scaleReadiness: null,
      runtimeDiagnostics: [],
      modelProviderPlugins: [],
      loadError: "Unable to load runtime state.",
    };
  }
}

export async function getPresetAdminData(): Promise<PresetAdminData> {
  const cookies = await cookieHeader();
  try {
    return {
      presets: await apiFetch<AgentPreset[]>("/agent-presets", cookies),
      loadError: null,
    };
  } catch (error) {
    if (error instanceof WorldServerError && error.status === 401) {
      throw error;
    }
    return {
      presets: [],
      loadError: "Unable to load presets.",
    };
  }
}

export async function getMemoryBackendAdminData(): Promise<MemoryBackendAdminData> {
  const cookies = await cookieHeader();
  try {
    const profiles = await apiFetch<MemoryBackendProfile[]>("/memory-backend-profiles", cookies);
    const profilePairs = await Promise.all(
      profiles.map(async (profile) => [
        profile.id,
        {
          health: await apiFetch<MemoryBackendHealth>(
            `/memory-backend-profiles/${profile.id}/health`,
            cookies,
          ),
          logs: await apiFetch<MemoryBackendLogs>(
            `/memory-backend-profiles/${profile.id}/logs`,
            cookies,
          ),
          jobs: await apiFetch<MemoryWriteJobList>(
            `/memory-backend-profiles/${profile.id}/jobs?limit=20`,
            cookies,
          ),
        },
      ] as const),
    );
    return {
      profiles,
      profileHealth: Object.fromEntries(
        profilePairs.map(([profileId, data]) => [profileId, data.health]),
      ),
      profileLogs: Object.fromEntries(
        profilePairs.map(([profileId, data]) => [profileId, data.logs]),
      ),
      profileJobs: Object.fromEntries(
        profilePairs.map(([profileId, data]) => [profileId, data.jobs]),
      ),
      backfillDryRun: await apiFetch<MemoryBackfillDryRun>(
        "/memory-backfill/dry-run?limit=500",
        cookies,
      ),
      loadError: null,
    };
  } catch (error) {
    if (error instanceof WorldServerError && error.status === 401) {
      throw error;
    }
    return {
      profiles: [],
      profileHealth: {},
      profileLogs: {},
      profileJobs: {},
      backfillDryRun: null,
      loadError: "Unable to load memory backend profiles.",
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

function emptyWorldWorkspaceData(
  worlds: World[],
  loadError: string,
  isPlatformAdmin: boolean,
): WorldWorkspaceData {
  return {
    worlds,
    selectedWorld: null,
    scenes: [],
    locationEdges: [],
    agents: [],
    organizations: [],
    organizationMemberships: [],
    factionTracks: [],
    agentPresenceStates: [],
    dailyLifePreview: null,
    dailyLifeCandidates: [],
    offscreenEvents: [],
    memberships: [],
    worldBible: null,
    memoryBackendProfiles: [],
    memoryPlugins: [],
    worldRulesPlugins: [],
    clock: null,
    clockTransitions: [],
    replayState: null,
    latestSnapshot: null,
    snapshotIntegrity: null,
    worldEventAudit: [],
    calendarConflicts: null,
    scheduleRules: [],
    worldDiagnostics: [],
    canManageSelectedWorld: false,
    isPlatformAdmin,
    loadError,
  };
}

function emptyNarrativeReaderListData(
  worlds: World[],
  loadError: string,
  selectedArtifactKind: string,
  selectedConversationId: string,
  selectedSearch: string,
  selectedSourceKind: string,
  selectedOrderBy: string,
): NarrativeReaderListData {
  return {
    worlds,
    selectedWorld: null,
    conversations: [],
    narrativeArtifacts: [],
    selectedArtifactKind,
    selectedConversationId,
    selectedSearch,
    selectedSourceKind,
    selectedOrderBy,
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

async function listPluginCatalogForServer(
  category: PluginCatalogEntry["category"],
  cookieHeader: string | null,
): Promise<PluginCatalogEntry[]> {
  return apiFetch<PluginCatalogEntry[]>(`/plugins/catalog?category=${encodeURIComponent(category)}`, cookieHeader);
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
    locationEdges: [],
    agents: [],
    organizations: [],
    organizationMemberships: [],
    factionTracks: [],
    agentPresenceStates: [],
    dailyLifePreview: null,
    dailyLifeCandidates: [],
    offscreenEvents: [],
    memberships: [],
    clock: null,
    replayState: null,
    latestSnapshot: null,
    worldEventAudit: [],
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

function narrativeArtifactQuery(filters: NarrativeArtifactFilters): string {
  const search = new URLSearchParams();
  if (filters.artifact_kind) {
    search.set("artifact_kind", filters.artifact_kind);
  }
  if (filters.source_conversation_id) {
    search.set("source_conversation_id", filters.source_conversation_id);
  }
  if (filters.q) {
    search.set("q", filters.q);
  }
  if (filters.source_kind) {
    search.set("source_kind", filters.source_kind);
  }
  if (filters.publication_status) {
    search.set("publication_status", filters.publication_status);
  }
  if (filters.order_by) {
    search.set("order_by", filters.order_by);
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
