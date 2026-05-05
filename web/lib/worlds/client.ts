import { readCookie, requestCsrf } from "@/lib/auth/client";
import { CSRF_COOKIE_NAME, CSRF_HEADER_NAME } from "@/lib/auth/types";
import type {
  Agent,
  AgentCreateInput,
  AgentObservation,
  AgentObservationCreateInput,
  AgentPreset,
  AgentPresetCreateInput,
  AgentPresetUpdatePreview,
  AgentPresetUpdateInput,
  AgentPersona,
  AgentPersonaUpdateInput,
  AgentRelationship,
  AgentRelationshipCreateInput,
  AgentRelationshipUpdateInput,
  AgentRun,
  AgentRunCreateInput,
  AgentRunDetail,
  AgentUpdateInput,
  CalendarEntry,
  CalendarEntryCreateInput,
  CalendarConflictFilters,
  CalendarConflictReport,
  CalendarEntryUpdateInput,
  ConversationAdvanceResult,
  ConversationNarrativeArtifactSet,
  ConversationNarrativePromptPreview,
  ConversationCreateInput,
  ConversationDiagnosticsSummary,
  ConversationMemorySummary,
  ConversationParticipant,
  ConversationParticipantInput,
  ConversationSeedInput,
  ConversationSession,
  ConversationSpeakerPreview,
  ConversationTurn,
  ConversationUpdateInput,
  ExternalToolPolicy,
  AgentPresence,
  AgentPresenceInput,
  DailyLifeCandidateFilters,
  DailyLifeEventCandidate,
  DailyLifeGenerateInput,
  DailyLifePreview,
  DailyLifePreviewFilters,
  FactionProgressTrack,
  FactionProgressTrackCreateInput,
  FactionProgressTrackUpdateInput,
  MemberCandidate,
  MemoryBackendProfile,
  MemoryBackendProfileCreateInput,
  MemoryBackendProfileUpdateInput,
  MemoryBackfillDryRun,
  MemoryBackendHealth,
  MemoryBackendLogs,
  MemoryWriteJob,
  MemoryWriteJobList,
  MemoryWriteJobStatus,
  MemoryEvalResult,
  MemoryItem,
  MemoryProfileSnapshot,
  MemorySearchInput,
  Membership,
  NarrativeArtifact,
  NarrativeArtifactCreateInput,
  NarrativeArtifactFilters,
  NarrativePublication,
  NarrativePublicationInput,
  OffscreenEventCreateInput,
  OffscreenEventFilters,
  OffscreenEventQueueItem,
  OffscreenResolution,
  OrganizationCreateInput,
  OrganizationMembership,
  OrganizationMembershipCreateInput,
  OrganizationMembershipUpdateInput,
  OrganizationUpdateInput,
  PersonaPolicyValidation,
  PluginBinding,
  PluginCatalogEntry,
  PluginCategory,
  Scene,
  SceneCreateInput,
  SceneUpdateInput,
  ProviderHealth,
  ProviderProfile,
  ProviderProfileCreateInput,
  ProviderTestCallResult,
  ProviderProfileUpdateInput,
  RuntimeDiagnostic,
  RuntimeControl,
  RuntimeControlUpdateInput,
  RuntimeStatus,
  ScaleReadiness,
  ScheduleRule,
  SceneLocationEdge,
  SceneLocationEdgeCreateInput,
  SceneLocationEdgeUpdateInput,
  ScheduleRuleCreateInput,
  ScheduleRulePreview,
  ScheduleRulePreviewInput,
  ScheduleRuleUpdateInput,
  World,
  WorldBible,
  WorldBibleInput,
  WorldCreateInput,
  WorldClock,
  WorldClockTransition,
  WorldEventAuditEntry,
  WorldEventAuditFilters,
  WorldRole,
  WorldReplayState,
  WorldSnapshot,
  WorldSnapshotIntegrity,
  WorldUpdateInput,
  WorldCompositionExport,
  WorldCompositionImportInput,
  WorldCompositionValidation,
  WorldOrganization,
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

export function exportWorldComposition(worldId: string): Promise<WorldCompositionExport> {
  return worldRequest<WorldCompositionExport>(`/api/worlds/${worldId}/composition-export`, {
    method: "GET",
  });
}

export function getWorldBible(worldId: string): Promise<WorldBible | null> {
  return worldRequest<WorldBible | null>(`/api/worlds/${worldId}/bible`, { method: "GET" });
}

export function upsertWorldBible(
  worldId: string,
  input: WorldBibleInput,
): Promise<WorldBible> {
  return worldRequest<WorldBible>(`/api/worlds/${worldId}/bible`, {
    method: "PUT",
    body: input,
    csrf: true,
  });
}

export function importWorldComposition(
  input: WorldCompositionImportInput,
): Promise<World> {
  return apiRequest<World>("/api/world-compositions/import", {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function validateWorldComposition(
  input: WorldCompositionImportInput,
): Promise<WorldCompositionValidation> {
  return apiRequest<WorldCompositionValidation>("/api/world-compositions/validate", {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function listAgentPresets(): Promise<AgentPreset[]> {
  return apiRequest<AgentPreset[]>("/api/agent-presets", { method: "GET" });
}

export function createAgentPreset(
  input: AgentPresetCreateInput,
): Promise<AgentPreset> {
  return apiRequest<AgentPreset>("/api/agent-presets", {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function updateAgentPreset(
  presetId: string,
  input: AgentPresetUpdateInput,
): Promise<AgentPreset> {
  return apiRequest<AgentPreset>(`/api/agent-presets/${presetId}`, {
    method: "PATCH",
    body: input,
    csrf: true,
  });
}

export function getAgentPresetUpdatePreview(
  presetId: string,
): Promise<AgentPresetUpdatePreview> {
  return apiRequest<AgentPresetUpdatePreview>(
    `/api/agent-presets/${presetId}/update-preview`,
    { method: "GET" },
  );
}

export function deactivateAgentPreset(presetId: string): Promise<void> {
  return apiRequest<void>(`/api/agent-presets/${presetId}`, {
    method: "DELETE",
    csrf: true,
  });
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

export function listClockTransitions(worldId: string, limit = 20): Promise<WorldClockTransition[]> {
  return worldRequest<WorldClockTransition[]>(
    `/api/worlds/${worldId}/clock/transitions?limit=${encodeURIComponent(String(limit))}`,
    { method: "GET" },
  );
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

export function getSnapshotIntegrity(worldId: string): Promise<WorldSnapshotIntegrity> {
  return worldRequest<WorldSnapshotIntegrity>(`/api/worlds/${worldId}/snapshots/integrity`, {
    method: "GET",
  });
}

export function listWorldEvents(
  worldId: string,
  filters: WorldEventAuditFilters = {},
): Promise<WorldEventAuditEntry[]> {
  const search = new URLSearchParams();
  if (filters.event_name) {
    search.set("event_name", filters.event_name);
  }
  if (filters.actor_ref) {
    search.set("actor_ref", filters.actor_ref);
  }
  if (filters.importance) {
    search.set("importance", filters.importance);
  }
  if (filters.sequence_after !== undefined && filters.sequence_after !== null) {
    search.set("sequence_after", String(filters.sequence_after));
  }
  if (filters.sequence_before !== undefined && filters.sequence_before !== null) {
    search.set("sequence_before", String(filters.sequence_before));
  }
  if (filters.wall_time_from) {
    search.set("wall_time_from", filters.wall_time_from);
  }
  if (filters.wall_time_to) {
    search.set("wall_time_to", filters.wall_time_to);
  }
  if (filters.limit !== undefined) {
    search.set("limit", String(filters.limit));
  }
  const suffix = search.size === 0 ? "" : `?${search.toString()}`;
  return worldRequest<WorldEventAuditEntry[]>(`/api/worlds/${worldId}/events${suffix}`, {
    method: "GET",
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

export function listLocationEdges(worldId: string): Promise<SceneLocationEdge[]> {
  return worldRequest<SceneLocationEdge[]>(`/api/worlds/${worldId}/location-edges`, {
    method: "GET",
  });
}

export function createLocationEdge(
  worldId: string,
  input: SceneLocationEdgeCreateInput,
): Promise<SceneLocationEdge> {
  return worldRequest<SceneLocationEdge>(`/api/worlds/${worldId}/location-edges`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function updateLocationEdge(
  worldId: string,
  edgeId: string,
  input: SceneLocationEdgeUpdateInput,
): Promise<SceneLocationEdge> {
  return worldRequest<SceneLocationEdge>(`/api/worlds/${worldId}/location-edges/${edgeId}`, {
    method: "PATCH",
    body: input,
    csrf: true,
  });
}

export function listOrganizations(worldId: string): Promise<WorldOrganization[]> {
  return worldRequest<WorldOrganization[]>(`/api/worlds/${worldId}/organizations`, {
    method: "GET",
  });
}

export function createOrganization(
  worldId: string,
  input: OrganizationCreateInput,
): Promise<WorldOrganization> {
  return worldRequest<WorldOrganization>(`/api/worlds/${worldId}/organizations`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function updateOrganization(
  worldId: string,
  organizationId: string,
  input: OrganizationUpdateInput,
): Promise<WorldOrganization> {
  return worldRequest<WorldOrganization>(
    `/api/worlds/${worldId}/organizations/${organizationId}`,
    {
      method: "PATCH",
      body: input,
      csrf: true,
    },
  );
}

export function listOrganizationMemberships(
  worldId: string,
  organizationId: string,
): Promise<OrganizationMembership[]> {
  return worldRequest<OrganizationMembership[]>(
    `/api/worlds/${worldId}/organizations/${organizationId}/memberships`,
    { method: "GET" },
  );
}

export function createOrganizationMembership(
  worldId: string,
  organizationId: string,
  input: OrganizationMembershipCreateInput,
): Promise<OrganizationMembership> {
  return worldRequest<OrganizationMembership>(
    `/api/worlds/${worldId}/organizations/${organizationId}/memberships`,
    {
      method: "POST",
      body: input,
      csrf: true,
    },
  );
}

export function updateOrganizationMembership(
  worldId: string,
  organizationId: string,
  membershipId: string,
  input: OrganizationMembershipUpdateInput,
): Promise<OrganizationMembership> {
  return worldRequest<OrganizationMembership>(
    `/api/worlds/${worldId}/organizations/${organizationId}/memberships/${membershipId}`,
    {
      method: "PATCH",
      body: input,
      csrf: true,
    },
  );
}

export function listFactionTracks(
  worldId: string,
  organizationId: string,
): Promise<FactionProgressTrack[]> {
  return worldRequest<FactionProgressTrack[]>(
    `/api/worlds/${worldId}/organizations/${organizationId}/faction-tracks`,
    { method: "GET" },
  );
}

export function createFactionTrack(
  worldId: string,
  organizationId: string,
  input: FactionProgressTrackCreateInput,
): Promise<FactionProgressTrack> {
  return worldRequest<FactionProgressTrack>(
    `/api/worlds/${worldId}/organizations/${organizationId}/faction-tracks`,
    {
      method: "POST",
      body: input,
      csrf: true,
    },
  );
}

export function updateFactionTrack(
  worldId: string,
  organizationId: string,
  trackId: string,
  input: FactionProgressTrackUpdateInput,
): Promise<FactionProgressTrack> {
  return worldRequest<FactionProgressTrack>(
    `/api/worlds/${worldId}/organizations/${organizationId}/faction-tracks/${trackId}`,
    {
      method: "PATCH",
      body: input,
      csrf: true,
    },
  );
}

export function listAgents(worldId: string): Promise<Agent[]> {
  return worldRequest<Agent[]>(`/api/worlds/${worldId}/agents`, { method: "GET" });
}

export function listAgentRelationships(
  worldId: string,
  agentId: string,
): Promise<AgentRelationship[]> {
  return worldRequest<AgentRelationship[]>(
    `/api/worlds/${worldId}/agents/${agentId}/relationships`,
    { method: "GET" },
  );
}

export function createAgentRelationship(
  worldId: string,
  agentId: string,
  input: AgentRelationshipCreateInput,
): Promise<AgentRelationship> {
  return worldRequest<AgentRelationship>(
    `/api/worlds/${worldId}/agents/${agentId}/relationships`,
    {
      method: "POST",
      body: input,
      csrf: true,
    },
  );
}

export function updateAgentRelationship(
  worldId: string,
  agentId: string,
  relationshipId: string,
  input: AgentRelationshipUpdateInput,
): Promise<AgentRelationship> {
  return worldRequest<AgentRelationship>(
    `/api/worlds/${worldId}/agents/${agentId}/relationships/${relationshipId}`,
    {
      method: "PATCH",
      body: input,
      csrf: true,
    },
  );
}

export function getAgentPresence(
  worldId: string,
  agentId: string,
): Promise<AgentPresence | null> {
  return worldRequest<AgentPresence | null>(
    `/api/worlds/${worldId}/agents/${agentId}/presence`,
    { method: "GET" },
  );
}

export function upsertAgentPresence(
  worldId: string,
  agentId: string,
  input: AgentPresenceInput,
): Promise<AgentPresence> {
  return worldRequest<AgentPresence>(`/api/worlds/${worldId}/agents/${agentId}/presence`, {
    method: "PUT",
    body: input,
    csrf: true,
  });
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

export function getCalendarConflicts(
  worldId: string,
  filters: CalendarConflictFilters = {},
): Promise<CalendarConflictReport> {
  const search = new URLSearchParams();
  if (filters.start_world_time) {
    search.set("start_world_time", filters.start_world_time);
  }
  if (filters.horizon_hours !== undefined) {
    search.set("horizon_hours", String(filters.horizon_hours));
  }
  if (filters.limit !== undefined) {
    search.set("limit", String(filters.limit));
  }
  const query = search.toString();
  return worldRequest<CalendarConflictReport>(
    `/api/worlds/${worldId}/calendar/conflicts${query === "" ? "" : `?${query}`}`,
    { method: "GET" },
  );
}

export function getDailyLifePreview(
  worldId: string,
  filters: DailyLifePreviewFilters = {},
): Promise<DailyLifePreview> {
  const search = new URLSearchParams();
  if (filters.start_world_time) {
    search.set("start_world_time", filters.start_world_time);
  }
  if (filters.horizon_hours !== undefined) {
    search.set("horizon_hours", String(filters.horizon_hours));
  }
  if (filters.limit !== undefined) {
    search.set("limit", String(filters.limit));
  }
  const suffix = search.size === 0 ? "" : `?${search.toString()}`;
  return worldRequest<DailyLifePreview>(`/api/worlds/${worldId}/daily-life/preview${suffix}`, {
    method: "GET",
  });
}

export function generateDailyLifeCandidates(
  worldId: string,
  input: DailyLifeGenerateInput = {},
): Promise<DailyLifeEventCandidate[]> {
  return worldRequest<DailyLifeEventCandidate[]>(`/api/worlds/${worldId}/daily-life/generate`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function listDailyLifeCandidates(
  worldId: string,
  filters: DailyLifeCandidateFilters = {},
): Promise<DailyLifeEventCandidate[]> {
  const search = new URLSearchParams();
  if (filters.status) {
    search.set("status", filters.status);
  }
  if (filters.limit !== undefined) {
    search.set("limit", String(filters.limit));
  }
  const suffix = search.size === 0 ? "" : `?${search.toString()}`;
  return worldRequest<DailyLifeEventCandidate[]>(
    `/api/worlds/${worldId}/daily-life/candidates${suffix}`,
    { method: "GET" },
  );
}

export function createOffscreenEvent(
  worldId: string,
  input: OffscreenEventCreateInput,
): Promise<OffscreenEventQueueItem> {
  return worldRequest<OffscreenEventQueueItem>(`/api/worlds/${worldId}/offscreen-events`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function listOffscreenEvents(
  worldId: string,
  filters: OffscreenEventFilters = {},
): Promise<OffscreenEventQueueItem[]> {
  const search = new URLSearchParams();
  if (filters.status) {
    search.set("status", filters.status);
  }
  if (filters.limit !== undefined) {
    search.set("limit", String(filters.limit));
  }
  const suffix = search.size === 0 ? "" : `?${search.toString()}`;
  return worldRequest<OffscreenEventQueueItem[]>(
    `/api/worlds/${worldId}/offscreen-events${suffix}`,
    { method: "GET" },
  );
}

export function resolveOffscreenEvents(
  worldId: string,
  limit = 20,
): Promise<OffscreenResolution> {
  return worldRequest<OffscreenResolution>(
    `/api/worlds/${worldId}/offscreen-events/resolve?limit=${encodeURIComponent(String(limit))}`,
    {
      method: "POST",
      csrf: true,
    },
  );
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

export function previewScheduleRule(
  worldId: string,
  input: ScheduleRulePreviewInput,
): Promise<ScheduleRulePreview> {
  return worldRequest<ScheduleRulePreview>(`/api/worlds/${worldId}/schedule-rules/preview`, {
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

export function searchAgentMemory(
  worldId: string,
  agentId: string,
  input: MemorySearchInput,
): Promise<MemoryItem[]> {
  return worldRequest<MemoryItem[]>(`/api/worlds/${worldId}/agents/${agentId}/memory/search`, {
    method: "POST",
    body: input,
  });
}

export function getAgentMemoryProfileSnapshot(
  worldId: string,
  agentId: string,
): Promise<MemoryProfileSnapshot | null> {
  return worldRequest<MemoryProfileSnapshot | null>(
    `/api/worlds/${worldId}/agents/${agentId}/memory/profile-snapshot`,
    { method: "GET" },
  );
}

export function refreshAgentMemoryProfileSnapshot(
  worldId: string,
  agentId: string,
): Promise<MemoryProfileSnapshot> {
  return worldRequest<MemoryProfileSnapshot>(
    `/api/worlds/${worldId}/agents/${agentId}/memory/profile-snapshot/refresh`,
    {
      method: "POST",
      csrf: true,
    },
  );
}

export function forgetAgentMemory(
  worldId: string,
  agentId: string,
): Promise<{ backend: string; deleted_count: number | null }> {
  return worldRequest<{ backend: string; deleted_count: number | null }>(
    `/api/worlds/${worldId}/agents/${agentId}/memory/forget`,
    {
      method: "POST",
      csrf: true,
    },
  );
}

export function listAgentRuns(worldId: string, agentId: string): Promise<AgentRun[]> {
  return worldRequest<AgentRun[]>(`/api/worlds/${worldId}/agents/${agentId}/runs`, {
    method: "GET",
  });
}

export function getAgentRunDetail(
  worldId: string,
  agentId: string,
  runId: string,
): Promise<AgentRunDetail> {
  return worldRequest<AgentRunDetail>(
    `/api/worlds/${worldId}/agents/${agentId}/runs/${runId}`,
    { method: "GET" },
  );
}

export function getAgentPersona(worldId: string, agentId: string): Promise<AgentPersona | null> {
  return worldRequest<AgentPersona | null>(`/api/worlds/${worldId}/agents/${agentId}/persona`, {
    method: "GET",
  });
}

export function updateAgentPersona(
  worldId: string,
  agentId: string,
  input: AgentPersonaUpdateInput,
): Promise<AgentPersona> {
  return worldRequest<AgentPersona>(`/api/worlds/${worldId}/agents/${agentId}/persona`, {
    method: "PATCH",
    body: input,
    csrf: true,
  });
}

export function validateAgentPersona(
  worldId: string,
  agentId: string,
  input: AgentPersonaUpdateInput,
): Promise<PersonaPolicyValidation> {
  return worldRequest<PersonaPolicyValidation>(
    `/api/worlds/${worldId}/agents/${agentId}/persona/validate`,
    {
      method: "POST",
      body: input,
      csrf: true,
    },
  );
}

export function listPluginCatalog(
  category?: PluginCategory,
): Promise<PluginCatalogEntry[]> {
  const query = category === undefined ? "" : `?category=${encodeURIComponent(category)}`;
  return apiRequest<PluginCatalogEntry[]>(`/api/plugins/catalog${query}`, { method: "GET" });
}

export function listPluginBindings(category?: PluginCategory): Promise<PluginBinding[]> {
  const query = category === undefined ? "" : `?category=${encodeURIComponent(category)}`;
  return apiRequest<PluginBinding[]>(`/api/plugins/bindings${query}`, { method: "GET" });
}

export function listAgentObservations(
  worldId: string,
  agentId: string,
): Promise<AgentObservation[]> {
  return worldRequest<AgentObservation[]>(`/api/worlds/${worldId}/agents/${agentId}/observations`, {
    method: "GET",
  });
}

export function createAgentObservation(
  worldId: string,
  agentId: string,
  input: AgentObservationCreateInput,
): Promise<AgentObservation> {
  return worldRequest<AgentObservation>(`/api/worlds/${worldId}/agents/${agentId}/observations`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function refreshAgentObservations(
  worldId: string,
  agentId: string,
): Promise<AgentObservation[]> {
  return worldRequest<AgentObservation[]>(
    `/api/worlds/${worldId}/agents/${agentId}/observations/refresh`,
    {
      method: "POST",
      csrf: true,
    },
  );
}

export function runAgent(worldId: string, agentId: string, input: AgentRunCreateInput): Promise<AgentRun> {
  return worldRequest<AgentRun>(`/api/worlds/${worldId}/agents/${agentId}/run`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function listNarrativeArtifacts(worldId: string): Promise<NarrativeArtifact[]> {
  return worldRequest<NarrativeArtifact[]>(`/api/worlds/${worldId}/narrative-artifacts`, {
    method: "GET",
  });
}

export function listFilteredNarrativeArtifacts(
  worldId: string,
  options: NarrativeArtifactFilters = {},
): Promise<NarrativeArtifact[]> {
  const search = new URLSearchParams();
  if (options.artifact_kind) {
    search.set("artifact_kind", options.artifact_kind);
  }
  if (options.source_conversation_id) {
    search.set("source_conversation_id", options.source_conversation_id);
  }
  if (options.q) {
    search.set("q", options.q);
  }
  if (options.source_kind) {
    search.set("source_kind", options.source_kind);
  }
  if (options.publication_status) {
    search.set("publication_status", options.publication_status);
  }
  if (options.order_by) {
    search.set("order_by", options.order_by);
  }
  if (options.limit !== undefined) {
    search.set("limit", String(options.limit));
  }
  const suffix = search.size === 0 ? "" : `?${search.toString()}`;
  return worldRequest<NarrativeArtifact[]>(
    `/api/worlds/${worldId}/narrative-artifacts${suffix}`,
    {
      method: "GET",
    },
  );
}

export function getNarrativeArtifact(
  worldId: string,
  artifactId: string,
): Promise<NarrativeArtifact> {
  return worldRequest<NarrativeArtifact>(`/api/worlds/${worldId}/narrative-artifacts/${artifactId}`, {
    method: "GET",
  });
}

export function createNarrativeArtifact(
  worldId: string,
  input: NarrativeArtifactCreateInput,
): Promise<NarrativeArtifact> {
  return worldRequest<NarrativeArtifact>(`/api/worlds/${worldId}/narrative-artifacts`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function publishNarrativeArtifact(
  worldId: string,
  artifactId: string,
  input: NarrativePublicationInput = {},
): Promise<NarrativePublication> {
  return worldRequest<NarrativePublication>(
    `/api/worlds/${worldId}/narrative-artifacts/${artifactId}/publish`,
    {
      method: "POST",
      body: input,
      csrf: true,
    },
  );
}

export function unpublishNarrativeArtifact(
  worldId: string,
  artifactId: string,
  input: NarrativePublicationInput = {},
): Promise<NarrativePublication> {
  return worldRequest<NarrativePublication>(
    `/api/worlds/${worldId}/narrative-artifacts/${artifactId}/unpublish`,
    {
      method: "POST",
      body: input,
      csrf: true,
    },
  );
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

export function listConversations(worldId: string): Promise<ConversationSession[]> {
  return worldRequest<ConversationSession[]>(`/api/worlds/${worldId}/conversations`, {
    method: "GET",
  });
}

export function createConversation(
  worldId: string,
  input: ConversationCreateInput,
): Promise<ConversationSession> {
  return worldRequest<ConversationSession>(`/api/worlds/${worldId}/conversations`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function updateConversation(
  worldId: string,
  conversationId: string,
  input: ConversationUpdateInput,
): Promise<ConversationSession> {
  return worldRequest<ConversationSession>(
    `/api/worlds/${worldId}/conversations/${conversationId}`,
    {
      method: "PATCH",
      body: input,
      csrf: true,
    },
  );
}

export function listConversationParticipants(
  worldId: string,
  conversationId: string,
): Promise<ConversationParticipant[]> {
  return worldRequest<ConversationParticipant[]>(
    `/api/worlds/${worldId}/conversations/${conversationId}/participants`,
    { method: "GET" },
  );
}

export function replaceConversationParticipants(
  worldId: string,
  conversationId: string,
  input: ConversationParticipantInput[],
): Promise<ConversationParticipant[]> {
  return worldRequest<ConversationParticipant[]>(
    `/api/worlds/${worldId}/conversations/${conversationId}/participants`,
    {
      method: "PUT",
      body: input,
      csrf: true,
    },
  );
}

export function listConversationTurns(
  worldId: string,
  conversationId: string,
): Promise<ConversationTurn[]> {
  return worldRequest<ConversationTurn[]>(
    `/api/worlds/${worldId}/conversations/${conversationId}/turns`,
    { method: "GET" },
  );
}

export function getConversationSpeakerPreview(
  worldId: string,
  conversationId: string,
): Promise<ConversationSpeakerPreview> {
  return worldRequest<ConversationSpeakerPreview>(
    `/api/worlds/${worldId}/conversations/${conversationId}/speaker-preview`,
    { method: "GET" },
  );
}

export function getConversationMemorySummary(
  worldId: string,
  conversationId: string,
): Promise<ConversationMemorySummary> {
  return worldRequest<ConversationMemorySummary>(
    `/api/worlds/${worldId}/conversations/${conversationId}/memory/summary`,
    { method: "GET" },
  );
}

export function getConversationDiagnosticsSummary(
  worldId: string,
  conversationId: string,
): Promise<ConversationDiagnosticsSummary> {
  return worldRequest<ConversationDiagnosticsSummary>(
    `/api/worlds/${worldId}/conversations/${conversationId}/diagnostics/summary`,
    { method: "GET" },
  );
}

export function listConversationNarrativeArtifacts(
  worldId: string,
  conversationId: string,
): Promise<NarrativeArtifact[]> {
  return worldRequest<NarrativeArtifact[]>(
    `/api/worlds/${worldId}/conversations/${conversationId}/narrative`,
    { method: "GET" },
  );
}

export function generateConversationNarrativeArtifacts(
  worldId: string,
  conversationId: string,
  artifact_set: ConversationNarrativeArtifactSet,
  provider_profile_id?: string | null,
): Promise<NarrativeArtifact[]> {
  return worldRequest<NarrativeArtifact[]>(
    `/api/worlds/${worldId}/conversations/${conversationId}/narrative/generate`,
    {
      method: "POST",
      body: {
        artifact_set,
        ...(provider_profile_id ? { provider_profile_id } : {}),
      },
      csrf: true,
    },
  );
}

export function previewConversationNarrativePrompt(
  worldId: string,
  conversationId: string,
  artifact_set: ConversationNarrativeArtifactSet,
  provider_profile_id?: string | null,
): Promise<ConversationNarrativePromptPreview> {
  return worldRequest<ConversationNarrativePromptPreview>(
    `/api/worlds/${worldId}/conversations/${conversationId}/narrative/preview`,
    {
      method: "POST",
      body: {
        artifact_set,
        ...(provider_profile_id ? { provider_profile_id } : {}),
      },
      csrf: true,
    },
  );
}

export function seedConversation(
  worldId: string,
  conversationId: string,
  input: ConversationSeedInput,
): Promise<ConversationTurn> {
  return worldRequest<ConversationTurn>(
    `/api/worlds/${worldId}/conversations/${conversationId}/seed`,
    {
      method: "POST",
      body: input,
      csrf: true,
    },
  );
}

export function advanceConversation(
  worldId: string,
  conversationId: string,
): Promise<ConversationAdvanceResult> {
  return worldRequest<ConversationAdvanceResult>(
    `/api/worlds/${worldId}/conversations/${conversationId}/advance`,
    {
      method: "POST",
      csrf: true,
    },
  );
}

export function startConversation(
  worldId: string,
  conversationId: string,
): Promise<ConversationSession> {
  return worldRequest<ConversationSession>(
    `/api/worlds/${worldId}/conversations/${conversationId}/start`,
    {
      method: "POST",
      csrf: true,
    },
  );
}

export function pauseConversation(
  worldId: string,
  conversationId: string,
): Promise<ConversationSession> {
  return worldRequest<ConversationSession>(
    `/api/worlds/${worldId}/conversations/${conversationId}/pause`,
    {
      method: "POST",
      csrf: true,
    },
  );
}

export function resumeConversation(
  worldId: string,
  conversationId: string,
): Promise<ConversationSession> {
  return worldRequest<ConversationSession>(
    `/api/worlds/${worldId}/conversations/${conversationId}/resume`,
    {
      method: "POST",
      csrf: true,
    },
  );
}

export function stopConversation(
  worldId: string,
  conversationId: string,
): Promise<ConversationSession> {
  return worldRequest<ConversationSession>(
    `/api/worlds/${worldId}/conversations/${conversationId}/stop`,
    {
      method: "POST",
      csrf: true,
    },
  );
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

export function getRuntimeControl(): Promise<RuntimeControl> {
  return apiRequest<RuntimeControl>("/api/runtime/control", { method: "GET" });
}

export function updateRuntimeControl(input: RuntimeControlUpdateInput): Promise<RuntimeControl> {
  return apiRequest<RuntimeControl>("/api/runtime/control", {
    method: "PATCH",
    body: input,
    csrf: true,
  });
}

export function getRuntimeStatus(): Promise<RuntimeStatus> {
  return apiRequest<RuntimeStatus>("/api/runtime/status", { method: "GET" });
}

export function getExternalToolPolicy(): Promise<ExternalToolPolicy> {
  return apiRequest<ExternalToolPolicy>("/api/runtime/tool-policy", { method: "GET" });
}

export function getScaleReadiness(): Promise<ScaleReadiness> {
  return apiRequest<ScaleReadiness>("/api/runtime/scale-readiness", { method: "GET" });
}

export function listRuntimeDiagnostics(): Promise<RuntimeDiagnostic[]> {
  return apiRequest<RuntimeDiagnostic[]>("/api/runtime/diagnostics", { method: "GET" });
}

export function listWorldDiagnostics(worldId: string): Promise<RuntimeDiagnostic[]> {
  return worldRequest<RuntimeDiagnostic[]>(`/api/worlds/${worldId}/diagnostics`, {
    method: "GET",
  });
}

export function listProviderProfiles(): Promise<ProviderProfile[]> {
  return apiRequest<ProviderProfile[]>("/api/provider-profiles", { method: "GET" });
}

export function listProviderHealth(): Promise<ProviderHealth[]> {
  return apiRequest<ProviderHealth[]>("/api/provider-profiles/health", { method: "GET" });
}

export function listMemoryBackendProfiles(): Promise<MemoryBackendProfile[]> {
  return apiRequest<MemoryBackendProfile[]>("/api/memory-backend-profiles", { method: "GET" });
}

export function createMemoryBackendProfile(
  input: MemoryBackendProfileCreateInput,
): Promise<MemoryBackendProfile> {
  return apiRequest<MemoryBackendProfile>("/api/memory-backend-profiles", {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function updateMemoryBackendProfile(
  profileId: string,
  input: MemoryBackendProfileUpdateInput,
): Promise<MemoryBackendProfile> {
  return apiRequest<MemoryBackendProfile>(`/api/memory-backend-profiles/${profileId}`, {
    method: "PATCH",
    body: input,
    csrf: true,
  });
}

export function deleteMemoryBackendProfile(profileId: string): Promise<void> {
  return apiRequest<void>(`/api/memory-backend-profiles/${profileId}`, {
    method: "DELETE",
    csrf: true,
  });
}

export function getMemoryBackendProfileHealth(
  profileId: string,
): Promise<MemoryBackendHealth> {
  return apiRequest<MemoryBackendHealth>(
    `/api/memory-backend-profiles/${profileId}/health`,
    { method: "GET" },
  );
}

export function getMemoryBackendProfileLogs(
  profileId: string,
  limit = 20,
): Promise<MemoryBackendLogs> {
  return apiRequest<MemoryBackendLogs>(
    `/api/memory-backend-profiles/${profileId}/logs?limit=${encodeURIComponent(String(limit))}`,
    { method: "GET" },
  );
}

export function dryRunMemoryBackfill(limit = 500): Promise<MemoryBackfillDryRun> {
  return apiRequest<MemoryBackfillDryRun>(
    `/api/memory-backfill/dry-run?limit=${encodeURIComponent(String(limit))}`,
    { method: "GET" },
  );
}

export function listMemoryBackendProfileJobs(
  profileId: string,
  options: { status?: MemoryWriteJobStatus; limit?: number } = {},
): Promise<MemoryWriteJobList> {
  const search = new URLSearchParams();
  if (options.status !== undefined) {
    search.set("status", options.status);
  }
  if (options.limit !== undefined) {
    search.set("limit", String(options.limit));
  }
  const suffix = search.size === 0 ? "" : `?${search.toString()}`;
  return apiRequest<MemoryWriteJobList>(
    `/api/memory-backend-profiles/${profileId}/jobs${suffix}`,
    { method: "GET" },
  );
}

export function retryMemoryWriteJob(jobId: string): Promise<MemoryWriteJob> {
  return apiRequest<MemoryWriteJob>(`/api/memory-write-jobs/${jobId}/retry`, {
    method: "POST",
    csrf: true,
  });
}

export function runMemoryBackendProfileEvalSmoke(
  profileId: string,
): Promise<MemoryEvalResult> {
  return apiRequest<MemoryEvalResult>(
    `/api/memory-backend-profiles/${profileId}/eval-smoke`,
    {
      method: "POST",
      csrf: true,
    },
  );
}

export function createProviderProfile(input: ProviderProfileCreateInput): Promise<ProviderProfile> {
  return apiRequest<ProviderProfile>("/api/provider-profiles", {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function updateProviderProfile(
  profileId: string,
  input: ProviderProfileUpdateInput,
): Promise<ProviderProfile> {
  return apiRequest<ProviderProfile>(`/api/provider-profiles/${profileId}`, {
    method: "PATCH",
    body: input,
    csrf: true,
  });
}

export function disableProviderProfile(profileId: string): Promise<void> {
  return apiRequest<void>(`/api/provider-profiles/${profileId}`, {
    method: "DELETE",
    csrf: true,
  });
}

export function testProviderProfile(
  profileId: string,
  prompt?: string,
): Promise<ProviderTestCallResult> {
  return apiRequest<ProviderTestCallResult>(`/api/provider-profiles/${profileId}/test-call`, {
    method: "POST",
    body: prompt === undefined || prompt.trim() === "" ? {} : { prompt },
    csrf: true,
  });
}

type WorldRequestOptions = {
  method: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  csrf?: boolean;
};

async function worldRequest<T>(path: string, options: WorldRequestOptions): Promise<T> {
  return apiRequest<T>(path, options);
}

async function apiRequest<T>(path: string, options: WorldRequestOptions): Promise<T> {
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
