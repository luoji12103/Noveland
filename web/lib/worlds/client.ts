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
  AuthoringImportJob,
  AuthoringTemplate,
  AuthoringTemplateApplyInput,
  AuthoringTemplateCreateInput,
  BetaChecklistItem,
  BetaChecklistRun,
  BetaChecklistRunCreateInput,
  CalendarEntry,
  CalendarEntryCreateInput,
  CalendarConflictFilters,
  CalendarConflictReport,
  CalendarEntryUpdateInput,
  CharacterEmotionalState,
  CharacterKnowledgeFact,
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
  EndingCandidate,
  EndingCandidateCreateInput,
  EndingDryRun,
  ExternalToolPolicy,
  EmotionalStateUpsertInput,
  AgentPresence,
  AgentPresenceInput,
  DailyLifeCandidateFilters,
  DailyEpisodeDraft,
  DailyEpisodeDraftCreateInput,
  DailyLifeEventCandidate,
  DailyLifeGenerateInput,
  DailyLifePreview,
  DailyLifePreviewFilters,
  ChoiceConsequencePreview,
  EventResolutionRule,
  EventResolutionRuleCreateInput,
  EventResolutionRuleUpdateInput,
  EventTriggerCondition,
  EventTriggerConditionCreateInput,
  EventTriggerConditionUpdateInput,
  FactionProgressTrack,
  FactionProgressTrackCreateInput,
  FactionProgressTrackUpdateInput,
  GMAgenda,
  GMAgendaCreateInput,
  GMAgendaUpdateInput,
  GMStyleReview,
  GMStyleReviewCreateInput,
  GMEventProposal,
  GMProposalCreateInput,
  GMProposalReviewInput,
  GroupInteractionContext,
  GroupInteractionCreateInput,
  InWorldNotification,
  InterventionCreateInput,
  JournalEntryCreateInput,
  KnowledgeFactUpsertInput,
  LivingWorldReleaseProfile,
  LivingWorldDashboard,
  LongRunEvalCreateInput,
  LongRunEvalRun,
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
  NarrativeContinuityReview,
  NarrativeContinuityReviewCreateInput,
  NarrativePublication,
  NarrativePublicationInput,
  NotificationCreateInput,
  OffscreenEventCreateInput,
  OffscreenEventFilters,
  OffscreenEventQueueItem,
  OffscreenResolution,
  OrganizationConflict,
  OrganizationConflictCreateInput,
  OrganizationCreateInput,
  OrganizationMembership,
  OrganizationMembershipCreateInput,
  OrganizationMembershipUpdateInput,
  OrganizationUpdateInput,
  PersonaPolicyValidation,
  PlayerActor,
  PlayerActorBindInput,
  PlayerChoice,
  PlayerChoiceCreateInput,
  PlayerInterventionRecord,
  PlayerJournalEntry,
  PluginBinding,
  PluginCatalogEntry,
  PluginCategory,
  PlotThread,
  PlotThreadCreateInput,
  Scene,
  SceneBeatDraft,
  SceneBeatDraftCreateInput,
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
  ResolutionRuleDryRun,
  RelationshipEventSuggestion,
  RelationshipRepairCreateInput,
  RelationshipRepairRecord,
  RelationshipSuggestionUpdateInput,
  RouteAffinity,
  RouteAffinityUpsertInput,
  RouteMilestone,
  RouteMilestoneCreateInput,
  Rumor,
  RumorCreateInput,
  RumorPropagation,
  RumorPropagationCreateInput,
  SecretCreateInput,
  SecretRecord,
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
  Worldline,
  WorldlineComparison,
  WorldlineForkInput,
  WorldlineScopedFilters,
  StoryHook,
  StoryHookCreateInput,
  TriggerConditionDryRun,
  ReleaseProfileUpsertInput,
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

export function listWorldlines(worldId: string): Promise<Worldline[]> {
  return worldRequest<Worldline[]>(`/api/worlds/${worldId}/worldlines`, { method: "GET" });
}

export function forkWorldline(worldId: string, input: WorldlineForkInput): Promise<Worldline> {
  return worldRequest<Worldline>(`/api/worlds/${worldId}/worldlines/fork`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function compareWorldlines(
  worldId: string,
  baseWorldlineId: string,
  compareWorldlineId: string,
): Promise<WorldlineComparison> {
  return worldRequest<WorldlineComparison>(
    `/api/worlds/${worldId}/worldlines/${baseWorldlineId}/compare/${compareWorldlineId}`,
    { method: "GET" },
  );
}

export function listGMAgendas(
  worldId: string,
  filters: WorldlineScopedFilters = {},
): Promise<GMAgenda[]> {
  return worldRequest<GMAgenda[]>(`/api/worlds/${worldId}/gm/agendas${worldlineSuffix(filters)}`, {
    method: "GET",
  });
}

export function createGMAgenda(worldId: string, input: GMAgendaCreateInput): Promise<GMAgenda> {
  return worldRequest<GMAgenda>(`/api/worlds/${worldId}/gm/agendas`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function updateGMAgenda(
  worldId: string,
  agendaId: string,
  input: GMAgendaUpdateInput,
): Promise<GMAgenda> {
  return worldRequest<GMAgenda>(`/api/worlds/${worldId}/gm/agendas/${agendaId}`, {
    method: "PATCH",
    body: input,
    csrf: true,
  });
}

export function listGMProposals(
  worldId: string,
  filters: WorldlineScopedFilters & { status?: string | null; limit?: number } = {},
): Promise<GMEventProposal[]> {
  const search = new URLSearchParams();
  appendOptional(search, "worldline_id", filters.worldline_id);
  appendOptional(search, "status", filters.status);
  if (filters.limit !== undefined) {
    search.set("limit", String(filters.limit));
  }
  return worldRequest<GMEventProposal[]>(
    `/api/worlds/${worldId}/gm/proposals${searchSuffix(search)}`,
    { method: "GET" },
  );
}

export function createGMProposal(
  worldId: string,
  input: GMProposalCreateInput,
): Promise<GMEventProposal> {
  return worldRequest<GMEventProposal>(`/api/worlds/${worldId}/gm/proposals`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function reviewGMProposal(
  worldId: string,
  proposalId: string,
  input: GMProposalReviewInput,
): Promise<GMEventProposal> {
  return worldRequest<GMEventProposal>(
    `/api/worlds/${worldId}/gm/proposals/${proposalId}/review`,
    {
      method: "POST",
      body: input,
      csrf: true,
    },
  );
}

export function listResolutionRules(worldId: string): Promise<EventResolutionRule[]> {
  return worldRequest<EventResolutionRule[]>(`/api/worlds/${worldId}/resolution-rules`, {
    method: "GET",
  });
}

export function createResolutionRule(
  worldId: string,
  input: EventResolutionRuleCreateInput,
): Promise<EventResolutionRule> {
  return worldRequest<EventResolutionRule>(`/api/worlds/${worldId}/resolution-rules`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function updateResolutionRule(
  worldId: string,
  ruleId: string,
  input: EventResolutionRuleUpdateInput,
): Promise<EventResolutionRule> {
  return worldRequest<EventResolutionRule>(
    `/api/worlds/${worldId}/resolution-rules/${ruleId}`,
    {
      method: "PATCH",
      body: input,
      csrf: true,
    },
  );
}

export function dryRunResolutionRule(
  worldId: string,
  ruleId: string,
  filters: WorldlineScopedFilters = {},
): Promise<ResolutionRuleDryRun> {
  return worldRequest<ResolutionRuleDryRun>(
    `/api/worlds/${worldId}/resolution-rules/${ruleId}/dry-run${worldlineSuffix(filters)}`,
    {
      method: "POST",
      csrf: true,
    },
  );
}

export function listPlayerActors(
  worldId: string,
  filters: WorldlineScopedFilters = {},
): Promise<PlayerActor[]> {
  return worldRequest<PlayerActor[]>(
    `/api/worlds/${worldId}/player-actors${worldlineSuffix(filters)}`,
    { method: "GET" },
  );
}

export function bindPlayerActor(
  worldId: string,
  input: PlayerActorBindInput,
): Promise<PlayerActor> {
  return worldRequest<PlayerActor>(`/api/worlds/${worldId}/player-actors`, {
    method: "PUT",
    body: input,
    csrf: true,
  });
}

export function listPlayerChoices(
  worldId: string,
  filters: WorldlineScopedFilters & { user_id?: string | null; limit?: number } = {},
): Promise<PlayerChoice[]> {
  const search = new URLSearchParams();
  appendOptional(search, "worldline_id", filters.worldline_id);
  appendOptional(search, "user_id", filters.user_id);
  if (filters.limit !== undefined) {
    search.set("limit", String(filters.limit));
  }
  return worldRequest<PlayerChoice[]>(
    `/api/worlds/${worldId}/player-choices${searchSuffix(search)}`,
    { method: "GET" },
  );
}

export function recordPlayerChoice(
  worldId: string,
  input: PlayerChoiceCreateInput,
): Promise<PlayerChoice> {
  return worldRequest<PlayerChoice>(`/api/worlds/${worldId}/player-choices`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function previewPlayerChoiceConsequences(
  worldId: string,
  input: PlayerChoiceCreateInput,
): Promise<ChoiceConsequencePreview> {
  return worldRequest<ChoiceConsequencePreview>(
    `/api/worlds/${worldId}/player-choices/preview`,
    {
      method: "POST",
      body: input,
      csrf: true,
    },
  );
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

export function getReplayState(
  worldId: string,
  filters: WorldlineScopedFilters = {},
): Promise<WorldReplayState> {
  return worldRequest<WorldReplayState>(`/api/worlds/${worldId}/replay/state${worldlineSuffix(filters)}`, {
    method: "GET",
  });
}

export function getLatestSnapshot(
  worldId: string,
  filters: WorldlineScopedFilters = {},
): Promise<WorldSnapshot | null> {
  return worldRequest<WorldSnapshot | null>(
    `/api/worlds/${worldId}/snapshots/latest${worldlineSuffix(filters)}`,
    {
      method: "GET",
    },
  );
}

export function createSnapshot(
  worldId: string,
  filters: WorldlineScopedFilters = {},
): Promise<WorldSnapshot> {
  return worldRequest<WorldSnapshot>(`/api/worlds/${worldId}/snapshots${worldlineSuffix(filters)}`, {
    method: "POST",
    csrf: true,
  });
}

export function getSnapshotIntegrity(
  worldId: string,
  filters: WorldlineScopedFilters = {},
): Promise<WorldSnapshotIntegrity> {
  return worldRequest<WorldSnapshotIntegrity>(
    `/api/worlds/${worldId}/snapshots/integrity${worldlineSuffix(filters)}`,
    {
      method: "GET",
    },
  );
}

export function listWorldEvents(
  worldId: string,
  filters: WorldEventAuditFilters = {},
): Promise<WorldEventAuditEntry[]> {
  const search = new URLSearchParams();
  appendOptional(search, "worldline_id", filters.worldline_id);
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
  filters: WorldlineScopedFilters = {},
): Promise<FactionProgressTrack[]> {
  return worldRequest<FactionProgressTrack[]>(
    `/api/worlds/${worldId}/organizations/${organizationId}/faction-tracks${worldlineSuffix(filters)}`,
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
  filters: WorldlineScopedFilters = {},
): Promise<AgentRelationship[]> {
  return worldRequest<AgentRelationship[]>(
    `/api/worlds/${worldId}/agents/${agentId}/relationships${worldlineSuffix(filters)}`,
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
  filters: WorldlineScopedFilters = {},
): Promise<AgentPresence | null> {
  return worldRequest<AgentPresence | null>(
    `/api/worlds/${worldId}/agents/${agentId}/presence${worldlineSuffix(filters)}`,
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
  appendOptional(search, "worldline_id", filters.worldline_id);
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
  appendOptional(search, "worldline_id", filters.worldline_id);
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
  appendOptional(search, "worldline_id", filters.worldline_id);
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
  worldlineId?: string | null,
): Promise<OffscreenResolution> {
  const search = new URLSearchParams();
  search.set("limit", String(limit));
  appendOptional(search, "worldline_id", worldlineId);
  return worldRequest<OffscreenResolution>(
    `/api/worlds/${worldId}/offscreen-events/resolve?${search.toString()}`,
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

export function listStoryHooks(
  worldId: string,
  filters: WorldlineScopedFilters = {},
): Promise<StoryHook[]> {
  return worldRequest<StoryHook[]>(
    `/api/worlds/${worldId}/story-hooks${worldlineSuffix(filters)}`,
    { method: "GET" },
  );
}

export function createStoryHook(
  worldId: string,
  input: StoryHookCreateInput,
): Promise<StoryHook> {
  return worldRequest<StoryHook>(`/api/worlds/${worldId}/story-hooks`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function listPlotThreads(
  worldId: string,
  filters: WorldlineScopedFilters = {},
): Promise<PlotThread[]> {
  return worldRequest<PlotThread[]>(
    `/api/worlds/${worldId}/plot-threads${worldlineSuffix(filters)}`,
    { method: "GET" },
  );
}

export function createPlotThread(
  worldId: string,
  input: PlotThreadCreateInput,
): Promise<PlotThread> {
  return worldRequest<PlotThread>(`/api/worlds/${worldId}/plot-threads`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function listRouteAffinities(
  worldId: string,
  filters: WorldlineScopedFilters & { agent_id?: string | null; status?: string | null } = {},
): Promise<RouteAffinity[]> {
  const search = new URLSearchParams();
  appendOptional(search, "worldline_id", filters.worldline_id);
  appendOptional(search, "agent_id", filters.agent_id);
  appendOptional(search, "status", filters.status);
  return worldRequest<RouteAffinity[]>(
    `/api/worlds/${worldId}/route-affinities${searchSuffix(search)}`,
    { method: "GET" },
  );
}

export function upsertRouteAffinity(
  worldId: string,
  input: RouteAffinityUpsertInput,
): Promise<RouteAffinity> {
  return worldRequest<RouteAffinity>(`/api/worlds/${worldId}/route-affinities`, {
    method: "PUT",
    body: input,
    csrf: true,
  });
}

export function listRouteMilestones(
  worldId: string,
  filters: WorldlineScopedFilters = {},
): Promise<RouteMilestone[]> {
  return worldRequest<RouteMilestone[]>(
    `/api/worlds/${worldId}/route-milestones${worldlineSuffix(filters)}`,
    { method: "GET" },
  );
}

export function createRouteMilestone(
  worldId: string,
  input: RouteMilestoneCreateInput,
): Promise<RouteMilestone> {
  return worldRequest<RouteMilestone>(`/api/worlds/${worldId}/route-milestones`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function listEndingCandidates(
  worldId: string,
  filters: WorldlineScopedFilters & { status?: string | null; ending_type?: string | null } = {},
): Promise<EndingCandidate[]> {
  const search = new URLSearchParams();
  appendOptional(search, "worldline_id", filters.worldline_id);
  appendOptional(search, "status", filters.status);
  appendOptional(search, "ending_type", filters.ending_type);
  return worldRequest<EndingCandidate[]>(
    `/api/worlds/${worldId}/ending-candidates${searchSuffix(search)}`,
    { method: "GET" },
  );
}

export function createEndingCandidate(
  worldId: string,
  input: EndingCandidateCreateInput,
): Promise<EndingCandidate> {
  return worldRequest<EndingCandidate>(`/api/worlds/${worldId}/ending-candidates`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function dryRunEndingCandidate(
  worldId: string,
  endingId: string,
  filters: WorldlineScopedFilters = {},
): Promise<EndingDryRun> {
  return worldRequest<EndingDryRun>(
    `/api/worlds/${worldId}/ending-candidates/${endingId}/dry-run${worldlineSuffix(filters)}`,
    { method: "POST", csrf: true },
  );
}

export function listLongRunEvals(
  worldId: string,
  filters: WorldlineScopedFilters = {},
): Promise<LongRunEvalRun[]> {
  return worldRequest<LongRunEvalRun[]>(
    `/api/worlds/${worldId}/long-run-evals${worldlineSuffix(filters)}`,
    { method: "GET" },
  );
}

export function createLongRunEval(
  worldId: string,
  input: LongRunEvalCreateInput,
): Promise<LongRunEvalRun> {
  return worldRequest<LongRunEvalRun>(`/api/worlds/${worldId}/long-run-evals`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function listAuthoringTemplates(
  worldId: string,
  filters: { template_kind?: string | null } = {},
): Promise<AuthoringTemplate[]> {
  const search = new URLSearchParams();
  appendOptional(search, "template_kind", filters.template_kind);
  return worldRequest<AuthoringTemplate[]>(
    `/api/worlds/${worldId}/authoring-templates${searchSuffix(search)}`,
    { method: "GET" },
  );
}

export function createAuthoringTemplate(
  worldId: string,
  input: AuthoringTemplateCreateInput,
): Promise<AuthoringTemplate> {
  return worldRequest<AuthoringTemplate>(`/api/worlds/${worldId}/authoring-templates`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function previewAuthoringTemplate(
  worldId: string,
  templateId: string,
  input: AuthoringTemplateApplyInput = {},
): Promise<AuthoringImportJob> {
  return worldRequest<AuthoringImportJob>(
    `/api/worlds/${worldId}/authoring-templates/${templateId}/preview`,
    {
      method: "POST",
      body: input,
      csrf: true,
    },
  );
}

export function applyAuthoringTemplate(
  worldId: string,
  templateId: string,
  input: AuthoringTemplateApplyInput = {},
): Promise<AuthoringImportJob> {
  return worldRequest<AuthoringImportJob>(
    `/api/worlds/${worldId}/authoring-templates/${templateId}/apply`,
    {
      method: "POST",
      body: input,
      csrf: true,
    },
  );
}

export function getReleaseProfile(worldId: string): Promise<LivingWorldReleaseProfile | null> {
  return worldRequest<LivingWorldReleaseProfile | null>(`/api/worlds/${worldId}/release-profile`, {
    method: "GET",
  });
}

export function upsertReleaseProfile(
  worldId: string,
  input: ReleaseProfileUpsertInput,
): Promise<LivingWorldReleaseProfile> {
  return worldRequest<LivingWorldReleaseProfile>(`/api/worlds/${worldId}/release-profile`, {
    method: "PUT",
    body: input,
    csrf: true,
  });
}

export function listBetaChecklists(
  worldId: string,
  filters: WorldlineScopedFilters = {},
): Promise<BetaChecklistRun[]> {
  return worldRequest<BetaChecklistRun[]>(
    `/api/worlds/${worldId}/beta-checklists${worldlineSuffix(filters)}`,
    { method: "GET" },
  );
}

export function createBetaChecklist(
  worldId: string,
  input: BetaChecklistRunCreateInput,
): Promise<BetaChecklistRun> {
  return worldRequest<BetaChecklistRun>(`/api/worlds/${worldId}/beta-checklists`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function listBetaChecklistItems(
  worldId: string,
  runId: string,
): Promise<BetaChecklistItem[]> {
  return worldRequest<BetaChecklistItem[]>(
    `/api/worlds/${worldId}/beta-checklists/${runId}/items`,
    { method: "GET" },
  );
}

export function listEventTriggerConditions(worldId: string): Promise<EventTriggerCondition[]> {
  return worldRequest<EventTriggerCondition[]>(
    `/api/worlds/${worldId}/event-trigger-conditions`,
    { method: "GET" },
  );
}

export function createEventTriggerCondition(
  worldId: string,
  input: EventTriggerConditionCreateInput,
): Promise<EventTriggerCondition> {
  return worldRequest<EventTriggerCondition>(
    `/api/worlds/${worldId}/event-trigger-conditions`,
    {
      method: "POST",
      body: input,
      csrf: true,
    },
  );
}

export function updateEventTriggerCondition(
  worldId: string,
  conditionId: string,
  input: EventTriggerConditionUpdateInput,
): Promise<EventTriggerCondition> {
  return worldRequest<EventTriggerCondition>(
    `/api/worlds/${worldId}/event-trigger-conditions/${conditionId}`,
    {
      method: "PATCH",
      body: input,
      csrf: true,
    },
  );
}

export function dryRunEventTriggerCondition(
  worldId: string,
  conditionId: string,
  filters: WorldlineScopedFilters = {},
): Promise<TriggerConditionDryRun> {
  return worldRequest<TriggerConditionDryRun>(
    `/api/worlds/${worldId}/event-trigger-conditions/${conditionId}/dry-run${worldlineSuffix(
      filters,
    )}`,
    { method: "POST", csrf: true },
  );
}

export function listSceneBeats(
  worldId: string,
  filters: WorldlineScopedFilters = {},
): Promise<SceneBeatDraft[]> {
  return worldRequest<SceneBeatDraft[]>(
    `/api/worlds/${worldId}/scene-beats${worldlineSuffix(filters)}`,
    { method: "GET" },
  );
}

export function createSceneBeat(
  worldId: string,
  input: SceneBeatDraftCreateInput,
): Promise<SceneBeatDraft> {
  return worldRequest<SceneBeatDraft>(`/api/worlds/${worldId}/scene-beats`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function listDailyEpisodes(
  worldId: string,
  filters: WorldlineScopedFilters = {},
): Promise<DailyEpisodeDraft[]> {
  return worldRequest<DailyEpisodeDraft[]>(
    `/api/worlds/${worldId}/daily-episodes${worldlineSuffix(filters)}`,
    { method: "GET" },
  );
}

export function createDailyEpisode(
  worldId: string,
  input: DailyEpisodeDraftCreateInput,
): Promise<DailyEpisodeDraft> {
  return worldRequest<DailyEpisodeDraft>(`/api/worlds/${worldId}/daily-episodes`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function listGroupInteractions(
  worldId: string,
  filters: WorldlineScopedFilters = {},
): Promise<GroupInteractionContext[]> {
  return worldRequest<GroupInteractionContext[]>(
    `/api/worlds/${worldId}/group-interactions${worldlineSuffix(filters)}`,
    { method: "GET" },
  );
}

export function createGroupInteraction(
  worldId: string,
  input: GroupInteractionCreateInput,
): Promise<GroupInteractionContext> {
  return worldRequest<GroupInteractionContext>(`/api/worlds/${worldId}/group-interactions`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function listRelationshipSuggestions(
  worldId: string,
  filters: WorldlineScopedFilters = {},
): Promise<RelationshipEventSuggestion[]> {
  return worldRequest<RelationshipEventSuggestion[]>(
    `/api/worlds/${worldId}/relationship-suggestions${worldlineSuffix(filters)}`,
    { method: "GET" },
  );
}

export function generateRelationshipSuggestions(
  worldId: string,
  filters: WorldlineScopedFilters & { limit?: number } = {},
): Promise<RelationshipEventSuggestion[]> {
  const search = new URLSearchParams();
  appendOptional(search, "worldline_id", filters.worldline_id);
  if (filters.limit !== undefined) {
    search.set("limit", String(filters.limit));
  }
  return worldRequest<RelationshipEventSuggestion[]>(
    `/api/worlds/${worldId}/relationship-suggestions/generate${searchSuffix(search)}`,
    { method: "POST", csrf: true },
  );
}

export function updateRelationshipSuggestion(
  worldId: string,
  suggestionId: string,
  input: RelationshipSuggestionUpdateInput,
): Promise<RelationshipEventSuggestion> {
  return worldRequest<RelationshipEventSuggestion>(
    `/api/worlds/${worldId}/relationship-suggestions/${suggestionId}`,
    {
      method: "PATCH",
      body: input,
      csrf: true,
    },
  );
}

export function listOrganizationConflicts(
  worldId: string,
  filters: WorldlineScopedFilters = {},
): Promise<OrganizationConflict[]> {
  return worldRequest<OrganizationConflict[]>(
    `/api/worlds/${worldId}/organization-conflicts${worldlineSuffix(filters)}`,
    { method: "GET" },
  );
}

export function createOrganizationConflict(
  worldId: string,
  input: OrganizationConflictCreateInput,
): Promise<OrganizationConflict> {
  return worldRequest<OrganizationConflict>(`/api/worlds/${worldId}/organization-conflicts`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function resolveOrganizationConflict(
  worldId: string,
  conflictId: string,
): Promise<OrganizationConflict> {
  return worldRequest<OrganizationConflict>(
    `/api/worlds/${worldId}/organization-conflicts/${conflictId}/resolve`,
    { method: "POST", csrf: true },
  );
}

export function listRumors(
  worldId: string,
  filters: WorldlineScopedFilters = {},
): Promise<Rumor[]> {
  return worldRequest<Rumor[]>(
    `/api/worlds/${worldId}/rumors${worldlineSuffix(filters)}`,
    { method: "GET" },
  );
}

export function createRumor(worldId: string, input: RumorCreateInput): Promise<Rumor> {
  return worldRequest<Rumor>(`/api/worlds/${worldId}/rumors`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function listRumorPropagations(
  worldId: string,
  filters: WorldlineScopedFilters = {},
): Promise<RumorPropagation[]> {
  return worldRequest<RumorPropagation[]>(
    `/api/worlds/${worldId}/rumor-propagations${worldlineSuffix(filters)}`,
    { method: "GET" },
  );
}

export function createRumorPropagation(
  worldId: string,
  input: RumorPropagationCreateInput,
): Promise<RumorPropagation> {
  return worldRequest<RumorPropagation>(`/api/worlds/${worldId}/rumor-propagations`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function deliverRumorPropagation(
  worldId: string,
  propagationId: string,
): Promise<RumorPropagation> {
  return worldRequest<RumorPropagation>(
    `/api/worlds/${worldId}/rumor-propagations/${propagationId}/deliver`,
    { method: "POST", csrf: true },
  );
}

export function getLivingWorldDashboard(
  worldId: string,
  filters: WorldlineScopedFilters = {},
): Promise<LivingWorldDashboard> {
  return worldRequest<LivingWorldDashboard>(
    `/api/worlds/${worldId}/living-world-dashboard${worldlineSuffix(filters)}`,
    { method: "GET" },
  );
}

export function listKnowledgeFacts(
  worldId: string,
  filters: WorldlineScopedFilters & { agent_id?: string | null; limit?: number } = {},
): Promise<CharacterKnowledgeFact[]> {
  const search = new URLSearchParams();
  appendOptional(search, "worldline_id", filters.worldline_id);
  appendOptional(search, "agent_id", filters.agent_id);
  if (filters.limit !== undefined) {
    search.set("limit", String(filters.limit));
  }
  return worldRequest<CharacterKnowledgeFact[]>(
    `/api/worlds/${worldId}/knowledge${searchSuffix(search)}`,
    { method: "GET" },
  );
}

export function upsertKnowledgeFact(
  worldId: string,
  input: KnowledgeFactUpsertInput,
): Promise<CharacterKnowledgeFact> {
  return worldRequest<CharacterKnowledgeFact>(`/api/worlds/${worldId}/knowledge`, {
    method: "PUT",
    body: input,
    csrf: true,
  });
}

export function listSecrets(
  worldId: string,
  filters: WorldlineScopedFilters & { status?: string | null; limit?: number } = {},
): Promise<SecretRecord[]> {
  const search = new URLSearchParams();
  appendOptional(search, "worldline_id", filters.worldline_id);
  appendOptional(search, "status", filters.status);
  if (filters.limit !== undefined) {
    search.set("limit", String(filters.limit));
  }
  return worldRequest<SecretRecord[]>(`/api/worlds/${worldId}/secrets${searchSuffix(search)}`, {
    method: "GET",
  });
}

export function createSecret(worldId: string, input: SecretCreateInput): Promise<SecretRecord> {
  return worldRequest<SecretRecord>(`/api/worlds/${worldId}/secrets`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function revealSecret(worldId: string, secretId: string): Promise<SecretRecord> {
  return worldRequest<SecretRecord>(`/api/worlds/${worldId}/secrets/${secretId}/reveal`, {
    method: "POST",
    csrf: true,
  });
}

export function listEmotionalStates(
  worldId: string,
  filters: WorldlineScopedFilters & { agent_id?: string | null } = {},
): Promise<CharacterEmotionalState[]> {
  const search = new URLSearchParams();
  appendOptional(search, "worldline_id", filters.worldline_id);
  appendOptional(search, "agent_id", filters.agent_id);
  return worldRequest<CharacterEmotionalState[]>(
    `/api/worlds/${worldId}/emotional-states${searchSuffix(search)}`,
    { method: "GET" },
  );
}

export function upsertEmotionalState(
  worldId: string,
  input: EmotionalStateUpsertInput,
): Promise<CharacterEmotionalState> {
  return worldRequest<CharacterEmotionalState>(`/api/worlds/${worldId}/emotional-states`, {
    method: "PUT",
    body: input,
    csrf: true,
  });
}

export function listRelationshipRepairs(
  worldId: string,
  filters: WorldlineScopedFilters & { status?: string | null; limit?: number } = {},
): Promise<RelationshipRepairRecord[]> {
  const search = new URLSearchParams();
  appendOptional(search, "worldline_id", filters.worldline_id);
  appendOptional(search, "status", filters.status);
  if (filters.limit !== undefined) {
    search.set("limit", String(filters.limit));
  }
  return worldRequest<RelationshipRepairRecord[]>(
    `/api/worlds/${worldId}/relationship-repairs${searchSuffix(search)}`,
    { method: "GET" },
  );
}

export function createRelationshipRepair(
  worldId: string,
  input: RelationshipRepairCreateInput,
): Promise<RelationshipRepairRecord> {
  return worldRequest<RelationshipRepairRecord>(`/api/worlds/${worldId}/relationship-repairs`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function applyRelationshipRepair(
  worldId: string,
  repairId: string,
): Promise<RelationshipRepairRecord> {
  return worldRequest<RelationshipRepairRecord>(
    `/api/worlds/${worldId}/relationship-repairs/${repairId}/apply`,
    { method: "POST", csrf: true },
  );
}

export function listPlayerJournal(
  worldId: string,
  filters: WorldlineScopedFilters & { user_id?: string | null; limit?: number } = {},
): Promise<PlayerJournalEntry[]> {
  const search = new URLSearchParams();
  appendOptional(search, "worldline_id", filters.worldline_id);
  appendOptional(search, "user_id", filters.user_id);
  if (filters.limit !== undefined) {
    search.set("limit", String(filters.limit));
  }
  return worldRequest<PlayerJournalEntry[]>(
    `/api/worlds/${worldId}/player-journal${searchSuffix(search)}`,
    { method: "GET" },
  );
}

export function createPlayerJournalEntry(
  worldId: string,
  input: JournalEntryCreateInput,
): Promise<PlayerJournalEntry> {
  return worldRequest<PlayerJournalEntry>(`/api/worlds/${worldId}/player-journal`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function listNotifications(
  worldId: string,
  filters: WorldlineScopedFilters & { status?: string | null; limit?: number } = {},
): Promise<InWorldNotification[]> {
  const search = new URLSearchParams();
  appendOptional(search, "worldline_id", filters.worldline_id);
  appendOptional(search, "status", filters.status);
  if (filters.limit !== undefined) {
    search.set("limit", String(filters.limit));
  }
  return worldRequest<InWorldNotification[]>(
    `/api/worlds/${worldId}/notifications${searchSuffix(search)}`,
    { method: "GET" },
  );
}

export function createNotification(
  worldId: string,
  input: NotificationCreateInput,
): Promise<InWorldNotification> {
  return worldRequest<InWorldNotification>(`/api/worlds/${worldId}/notifications`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function listInterventions(
  worldId: string,
  filters: WorldlineScopedFilters & {
    user_id?: string | null;
    status?: string | null;
    limit?: number;
  } = {},
): Promise<PlayerInterventionRecord[]> {
  const search = new URLSearchParams();
  appendOptional(search, "worldline_id", filters.worldline_id);
  appendOptional(search, "user_id", filters.user_id);
  appendOptional(search, "status", filters.status);
  if (filters.limit !== undefined) {
    search.set("limit", String(filters.limit));
  }
  return worldRequest<PlayerInterventionRecord[]>(
    `/api/worlds/${worldId}/interventions${searchSuffix(search)}`,
    { method: "GET" },
  );
}

export function createIntervention(
  worldId: string,
  input: InterventionCreateInput,
): Promise<PlayerInterventionRecord> {
  return worldRequest<PlayerInterventionRecord>(`/api/worlds/${worldId}/interventions`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function listGMStyleReviews(
  worldId: string,
  filters: WorldlineScopedFilters & { status?: string | null; limit?: number } = {},
): Promise<GMStyleReview[]> {
  const search = new URLSearchParams();
  appendOptional(search, "worldline_id", filters.worldline_id);
  appendOptional(search, "status", filters.status);
  if (filters.limit !== undefined) {
    search.set("limit", String(filters.limit));
  }
  return worldRequest<GMStyleReview[]>(
    `/api/worlds/${worldId}/gm-style-reviews${searchSuffix(search)}`,
    { method: "GET" },
  );
}

export function createGMStyleReview(
  worldId: string,
  input: GMStyleReviewCreateInput,
): Promise<GMStyleReview> {
  return worldRequest<GMStyleReview>(`/api/worlds/${worldId}/gm-style-reviews`, {
    method: "POST",
    body: input,
    csrf: true,
  });
}

export function listNarrativeContinuityReviews(
  worldId: string,
  filters: WorldlineScopedFilters & { status?: string | null; limit?: number } = {},
): Promise<NarrativeContinuityReview[]> {
  const search = new URLSearchParams();
  appendOptional(search, "worldline_id", filters.worldline_id);
  appendOptional(search, "status", filters.status);
  if (filters.limit !== undefined) {
    search.set("limit", String(filters.limit));
  }
  return worldRequest<NarrativeContinuityReview[]>(
    `/api/worlds/${worldId}/narrative-continuity-reviews${searchSuffix(search)}`,
    { method: "GET" },
  );
}

export function createNarrativeContinuityReview(
  worldId: string,
  input: NarrativeContinuityReviewCreateInput,
): Promise<NarrativeContinuityReview> {
  return worldRequest<NarrativeContinuityReview>(
    `/api/worlds/${worldId}/narrative-continuity-reviews`,
    {
      method: "POST",
      body: input,
      csrf: true,
    },
  );
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

function appendOptional(search: URLSearchParams, key: string, value: string | null | undefined) {
  if (value !== undefined && value !== null && value !== "") {
    search.set(key, value);
  }
}

function searchSuffix(search: URLSearchParams): string {
  return search.size === 0 ? "" : `?${search.toString()}`;
}

function worldlineSuffix(filters: WorldlineScopedFilters): string {
  const search = new URLSearchParams();
  appendOptional(search, "worldline_id", filters.worldline_id);
  return searchSuffix(search);
}

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
    if (typeof body.detail === "string") {
      return body.detail;
    }
    if (body.detail !== null && typeof body.detail === "object" && !Array.isArray(body.detail)) {
      const detail = body.detail as Record<string, unknown>;
      const message = typeof detail.message === "string" ? detail.message : null;
      const reviewStatus =
        typeof detail.review_status === "string" ? detail.review_status : null;
      if (message !== null && reviewStatus !== null) {
        return `${message} (${reviewStatus})`;
      }
      return message;
    }
    return null;
  } catch {
    return null;
  }
}
