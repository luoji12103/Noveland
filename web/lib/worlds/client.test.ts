import { afterEach, describe, expect, it, vi } from "vitest";

import {
  applyAuthoringTemplate,
  applyRelationshipRepair,
  cancelAgentCalendarEntry,
  bindPlayerActor,
  compareWorldlines,
  createAgentCalendarEntry,
  createAgentObservation,
  createAgentRelationship,
  createAuthoringTemplate,
  createBetaChecklist,
  createDailyEpisode,
  createEndingCandidate,
  createFactionTrack,
  createGMAgenda,
  createGMProposal,
  createGMStyleReview,
  createGroupInteraction,
  createIntervention,
  createLongRunEval,
  createNarrativeContinuityReview,
  createNotification,
  createLocationEdge,
  createMemoryBackendProfile,
  createNarrativeArtifact,
  createOffscreenEvent,
  createOrganization,
  createOrganizationConflict,
  createOrganizationMembership,
  createAgentPreset,
  createPlayerJournalEntry,
  createPlotThread,
  createProviderProfile,
  createRelationshipRepair,
  createResolutionRule,
  createRouteMilestone,
  createScheduleRule,
  createSnapshot,
  createRumor,
  createRumorPropagation,
  createSceneBeat,
  createSecret,
  createStoryHook,
  createEventTriggerCondition,
  generateConversationNarrativeArtifacts,
  generateRelationshipSuggestions,
  getConversationDiagnosticsSummary,
  getConversationMemorySummary,
  getConversationSpeakerPreview,
  getExternalToolPolicy,
  getReleaseProfile,
  getLivingWorldDashboard,
  previewConversationNarrativePrompt,
  getCalendarConflicts,
  getDailyLifePreview,
  getAgentRunDetail,
  getAgentPresence,
  getNarrativeArtifact,
  createWorld,
  deactivateAgentPreset,
  deleteMemoryBackendProfile,
  disableProviderProfile,
  dryRunEndingCandidate,
  dryRunMemoryBackfill,
  dryRunResolutionRule,
  dryRunEventTriggerCondition,
  deactivateScene,
  deliverRumorPropagation,
  exportWorldComposition,
  forkWorldline,
  getRuntimeControl,
  getRuntimeStatus,
  getScaleReadiness,
  getLatestSnapshot,
  getAgentPersona,
  getAgentPresetUpdatePreview,
  getReplayState,
  getSnapshotIntegrity,
  getWorldBible,
  generateDailyLifeCandidates,
  listAuthoringTemplates,
  listBetaChecklistItems,
  listBetaChecklists,
  listEndingCandidates,
  listEmotionalStates,
  listDailyLifeCandidates,
  listFactionTracks,
  listGMAgendas,
  listGMStyleReviews,
  listGMProposals,
  listGroupInteractions,
  listInterventions,
  listKnowledgeFacts,
  listDailyEpisodes,
  listEventTriggerConditions,
  listLocationEdges,
  listOffscreenEvents,
  listOrganizationMemberships,
  listOrganizationConflicts,
  listOrganizations,
  listPluginBindings,
  listPlayerActors,
  listPlayerChoices,
  listPlayerJournal,
  listPlotThreads,
  listResolutionRules,
  listRelationshipSuggestions,
  listRelationshipRepairs,
  listRouteAffinities,
  listRouteMilestones,
  listLongRunEvals,
  listRumors,
  listRumorPropagations,
  listNarrativeContinuityReviews,
  listNotifications,
  listSecrets,
  listSceneBeats,
  listStoryHooks,
  listWorldEvents,
  listFilteredNarrativeArtifacts,
  listClockTransitions,
  listRuntimeDiagnostics,
  listAgentRuns,
  listAgentObservations,
  listMemoryBackendProfiles,
  listMemoryBackendProfileJobs,
  pauseWorldClock,
  previewAuthoringTemplate,
  previewPlayerChoiceConsequences,
  previewScheduleRule,
  publishNarrativeArtifact,
  resolveOffscreenEvents,
  recordPlayerChoice,
  revealSecret,
  reviewGMProposal,
  resumeWorldClock,
  listAgentMemory,
  listAgentRelationships,
  listNarrativeArtifacts,
  listConversationNarrativeArtifacts,
  listAgentPresets,
  listProviderProfiles,
  listProviderHealth,
  listPluginCatalog,
  runAgent,
  refreshAgentObservations,
  retryMemoryWriteJob,
  resolveOrganizationConflict,
  skipWorldClock,
  listMemberCandidates,
  listScheduleRules,
  listWorldDiagnostics,
  searchAgentMemory,
  testProviderProfile,
  importWorldComposition,
  validateWorldComposition,
  updateMemoryBackendProfile,
  updateAgent,
  updateEventTriggerCondition,
  updateFactionTrack,
  updateGMAgenda,
  updateLocationEdge,
  updateOrganization,
  updateOrganizationMembership,
  updateAgentRelationship,
  updateAgentPreset,
  updateProviderProfile,
  updateResolutionRule,
  updateRelationshipSuggestion,
  unpublishNarrativeArtifact,
  updateAgentPersona,
  validateAgentPersona,
  updateRuntimeControl,
  updateScheduleRule,
  upsertAgentPresence,
  upsertEmotionalState,
  upsertKnowledgeFact,
  upsertReleaseProfile,
  upsertRouteAffinity,
  upsertWorldBible,
  listWorldlines,
} from "@/lib/worlds/client";

describe("world client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    document.cookie = "noveland_csrf=; Max-Age=0; Path=/";
  });

  it("adds csrf headers to mutating world requests", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ id: "world-1" }));
    vi.stubGlobal("fetch", fetchMock);

    await createWorld({ slug: "first-world", name: "First World" });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/worlds",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
        body: JSON.stringify({ slug: "first-world", name: "First World" }),
        headers: expect.any(Headers),
      }),
    );
    const headers = fetchMock.mock.calls[0][1].headers as Headers;
    expect(headers.get("X-CSRF-Token")).toBe("csrf-token");
  });

  it("requests csrf when no csrf cookie exists", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ csrf_token: "new-csrf" }))
      .mockResolvedValueOnce(jsonResponse({ id: "agent-1" }));
    vi.stubGlobal("fetch", fetchMock);

    await updateAgent("world-1", "agent-1", { display_name: "Guide" });

    const headers = fetchMock.mock.calls[1][1].headers as Headers;
    expect(fetchMock.mock.calls[0][0]).toBe("/api/auth/csrf");
    expect(headers.get("X-CSRF-Token")).toBe("new-csrf");
  });

  it("maps query params and empty delete responses", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([{ email: "user@example.test" }]))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    vi.stubGlobal("fetch", fetchMock);

    await expect(listMemberCandidates("world-1", "user")).resolves.toHaveLength(1);
    await expect(deactivateScene("world-1", "scene-1")).resolves.toBeUndefined();

    expect(fetchMock.mock.calls[0][0]).toBe(
      "/api/worlds/world-1/member-candidates?limit=20&query=user",
    );
    expect(fetchMock.mock.calls[1][0]).toBe("/api/worlds/world-1/scenes/scene-1");
  });

  it("maps preset and composition requests", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([{ id: "preset-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "preset-1" }, 201))
      .mockResolvedValueOnce(jsonResponse({ id: "preset-1" }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(jsonResponse({ preset_id: "preset-1", agents: [] }))
      .mockResolvedValueOnce(jsonResponse({ world: { slug: "first-world" } }))
      .mockResolvedValueOnce(jsonResponse({ id: "world-2" }, 201))
      .mockResolvedValueOnce(jsonResponse({ valid: true, issues: [] }));
    vi.stubGlobal("fetch", fetchMock);

    await listAgentPresets();
    await createAgentPreset({
      preset_key: "storyteller",
      name: "Storyteller",
      default_kind: "narrative_agent",
    });
    await updateAgentPreset("preset-1", { name: "Updated preset" });
    await deactivateAgentPreset("preset-1");
    await getAgentPresetUpdatePreview("preset-1");
    await exportWorldComposition("world-1");
    await importWorldComposition({
      slug: "imported-world",
      name: "Imported World",
      owner_user_id: "user-1",
      composition: {
        world: {
          slug: "first-world",
          name: "First World",
          description: null,
          rules_config: {},
          is_active: true,
        },
        scenes: [],
        agents: [],
        schedule_rules: [],
        preset_references: [],
      },
    });
    await validateWorldComposition({
      slug: "validated-world",
      name: "Validated World",
      owner_user_id: "user-1",
      composition: {
        world: {
          slug: "first-world",
          name: "First World",
          description: null,
          rules_config: {},
          is_active: true,
        },
        scenes: [],
        agents: [],
        schedule_rules: [],
        preset_references: [],
      },
    });

    expect(fetchMock.mock.calls[0][0]).toBe("/api/agent-presets");
    expect(fetchMock.mock.calls[1][0]).toBe("/api/agent-presets");
    expect(fetchMock.mock.calls[2][0]).toBe("/api/agent-presets/preset-1");
    expect(fetchMock.mock.calls[3][0]).toBe("/api/agent-presets/preset-1");
    expect(fetchMock.mock.calls[4][0]).toBe("/api/agent-presets/preset-1/update-preview");
    expect(fetchMock.mock.calls[5][0]).toBe("/api/worlds/world-1/composition-export");
    expect(fetchMock.mock.calls[6][0]).toBe("/api/world-compositions/import");
    expect(fetchMock.mock.calls[7][0]).toBe("/api/world-compositions/validate");
  });

  it("maps world bible and relationship requests", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(null))
      .mockResolvedValueOnce(jsonResponse({ continuity_status: "post_canon" }))
      .mockResolvedValueOnce(jsonResponse([{ id: "relationship-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "relationship-1" }, 201))
      .mockResolvedValueOnce(jsonResponse({ id: "relationship-1", trust: 55 }));
    vi.stubGlobal("fetch", fetchMock);

    await getWorldBible("world-1");
    await upsertWorldBible("world-1", {
      source_material: "After story",
      continuity_config: { status: "post_canon" },
    });
    await listAgentRelationships("world-1", "agent-1");
    await createAgentRelationship("world-1", "agent-1", {
      source_agent_id: "agent-1",
      target_agent_id: "agent-2",
      relationship_type: "friendship",
      trust: 40,
    });
    await updateAgentRelationship("world-1", "agent-1", "relationship-1", { trust: 55 });

    expect(fetchMock.mock.calls[0][0]).toBe("/api/worlds/world-1/bible");
    expect(fetchMock.mock.calls[1][0]).toBe("/api/worlds/world-1/bible");
    expect(fetchMock.mock.calls[1][1].method).toBe("PUT");
    expect(fetchMock.mock.calls[2][0]).toBe(
      "/api/worlds/world-1/agents/agent-1/relationships",
    );
    expect(fetchMock.mock.calls[3][0]).toBe(
      "/api/worlds/world-1/agents/agent-1/relationships",
    );
    expect(fetchMock.mock.calls[4][0]).toBe(
      "/api/worlds/world-1/agents/agent-1/relationships/relationship-1",
    );
  });

  it("maps autonomous living world requests", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([{ id: "edge-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "edge-1" }, 201))
      .mockResolvedValueOnce(jsonResponse({ id: "edge-1", travel_label: "walkway" }))
      .mockResolvedValueOnce(jsonResponse([{ id: "org-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "org-1" }, 201))
      .mockResolvedValueOnce(jsonResponse({ id: "org-1", is_active: false }))
      .mockResolvedValueOnce(jsonResponse([{ id: "membership-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "membership-1" }, 201))
      .mockResolvedValueOnce(jsonResponse({ id: "membership-1", loyalty: 80 }))
      .mockResolvedValueOnce(jsonResponse([{ id: "track-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "track-1" }, 201))
      .mockResolvedValueOnce(jsonResponse({ id: "track-1", progress: 40 }))
      .mockResolvedValueOnce(jsonResponse({ id: "presence-1" }))
      .mockResolvedValueOnce(jsonResponse({ id: "presence-1", visibility_status: "offscreen" }))
      .mockResolvedValueOnce(jsonResponse({ candidate_count: 1, candidates: [] }))
      .mockResolvedValueOnce(jsonResponse([{ id: "candidate-1" }]))
      .mockResolvedValueOnce(jsonResponse([{ id: "candidate-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "queue-1" }, 201))
      .mockResolvedValueOnce(jsonResponse([{ id: "queue-1" }]))
      .mockResolvedValueOnce(jsonResponse({ processed_count: 1, resolved_count: 1 }));
    vi.stubGlobal("fetch", fetchMock);

    await listLocationEdges("world-1");
    await createLocationEdge("world-1", {
      source_scene_id: "scene-1",
      target_scene_id: "scene-2",
      travel_label: "walkway",
    });
    await updateLocationEdge("world-1", "edge-1", { travel_label: "covered walkway" });
    await listOrganizations("world-1");
    await createOrganization("world-1", {
      organization_key: "student-council",
      name: "Student Council",
      organization_type: "club",
    });
    await updateOrganization("world-1", "org-1", { is_active: false });
    await listOrganizationMemberships("world-1", "org-1");
    await createOrganizationMembership("world-1", "org-1", {
      agent_id: "agent-1",
      role_title: "President",
    });
    await updateOrganizationMembership("world-1", "org-1", "membership-1", { loyalty: 80 });
    await listFactionTracks("world-1", "org-1");
    await createFactionTrack("world-1", "org-1", {
      track_key: "festival-plan",
      name: "Festival Plan",
      track_type: "goal",
    });
    await updateFactionTrack("world-1", "org-1", "track-1", { progress: 40 });
    await getAgentPresence("world-1", "agent-1");
    await upsertAgentPresence("world-1", "agent-1", {
      current_scene_id: "scene-1",
      visibility_status: "offscreen",
    });
    await getDailyLifePreview("world-1", { horizon_hours: 12, limit: 5 });
    await generateDailyLifeCandidates("world-1", { horizon_hours: 12, limit: 5 });
    await listDailyLifeCandidates("world-1", { status: "candidate", limit: 5 });
    await createOffscreenEvent("world-1", {
      candidate_id: "candidate-1",
      title: "Daily beat",
      due_at: "2030-01-01T08:00:00Z",
    });
    await listOffscreenEvents("world-1", { status: "pending", limit: 5 });
    await resolveOffscreenEvents("world-1", 5);

    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      "/api/worlds/world-1/location-edges",
      "/api/worlds/world-1/location-edges",
      "/api/worlds/world-1/location-edges/edge-1",
      "/api/worlds/world-1/organizations",
      "/api/worlds/world-1/organizations",
      "/api/worlds/world-1/organizations/org-1",
      "/api/worlds/world-1/organizations/org-1/memberships",
      "/api/worlds/world-1/organizations/org-1/memberships",
      "/api/worlds/world-1/organizations/org-1/memberships/membership-1",
      "/api/worlds/world-1/organizations/org-1/faction-tracks",
      "/api/worlds/world-1/organizations/org-1/faction-tracks",
      "/api/worlds/world-1/organizations/org-1/faction-tracks/track-1",
      "/api/worlds/world-1/agents/agent-1/presence",
      "/api/worlds/world-1/agents/agent-1/presence",
      "/api/worlds/world-1/daily-life/preview?horizon_hours=12&limit=5",
      "/api/worlds/world-1/daily-life/generate",
      "/api/worlds/world-1/daily-life/candidates?status=candidate&limit=5",
      "/api/worlds/world-1/offscreen-events",
      "/api/worlds/world-1/offscreen-events?status=pending&limit=5",
      "/api/worlds/world-1/offscreen-events/resolve?limit=5",
    ]);
    expect((fetchMock.mock.calls[1][1].headers as Headers).get("X-CSRF-Token")).toBe(
      "csrf-token",
    );
  });

  it("maps gm choice and worldline requests", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([{ id: "worldline-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "worldline-2" }, 201))
      .mockResolvedValueOnce(jsonResponse({ divergent_event_count: 1 }))
      .mockResolvedValueOnce(jsonResponse([{ id: "agenda-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "agenda-1" }, 201))
      .mockResolvedValueOnce(jsonResponse({ id: "agenda-1", status: "paused" }))
      .mockResolvedValueOnce(jsonResponse([{ id: "proposal-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "proposal-1" }, 201))
      .mockResolvedValueOnce(jsonResponse({ id: "proposal-1", status: "resolved" }))
      .mockResolvedValueOnce(jsonResponse([{ id: "rule-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "rule-1" }, 201))
      .mockResolvedValueOnce(jsonResponse({ id: "rule-1", status: "inactive" }))
      .mockResolvedValueOnce(jsonResponse({ matched: true }))
      .mockResolvedValueOnce(jsonResponse([{ id: "actor-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "actor-1" }))
      .mockResolvedValueOnce(jsonResponse([{ id: "choice-1" }]))
      .mockResolvedValueOnce(jsonResponse({ diagnostics: [] }))
      .mockResolvedValueOnce(jsonResponse({ id: "choice-2" }, 201));
    vi.stubGlobal("fetch", fetchMock);

    await listWorldlines("world-1");
    await forkWorldline("world-1", {
      source_worldline_id: "worldline-1",
      worldline_key: "alt-route",
      name: "Alt Route",
    });
    await compareWorldlines("world-1", "worldline-1", "worldline-2");
    await listGMAgendas("world-1", { worldline_id: "worldline-1" });
    await createGMAgenda("world-1", { title: "Agenda", summary: "Summary" });
    await updateGMAgenda("world-1", "agenda-1", { status: "paused" });
    await listGMProposals("world-1", { status: "proposed", limit: 5 });
    await createGMProposal("world-1", {
      title: "Proposal",
      reason: "Reason",
      event_name: "gm.route_beat",
    });
    await reviewGMProposal("world-1", "proposal-1", { status: "resolved" });
    await listResolutionRules("world-1");
    await createResolutionRule("world-1", { rule_key: "trust-gate", name: "Trust Gate" });
    await updateResolutionRule("world-1", "rule-1", { status: "inactive" });
    await dryRunResolutionRule("world-1", "rule-1", { worldline_id: "worldline-1" });
    await listPlayerActors("world-1", { worldline_id: "worldline-1" });
    await bindPlayerActor("world-1", { display_name: "Player" });
    await listPlayerChoices("world-1", { worldline_id: "worldline-1", limit: 5 });
    await previewPlayerChoiceConsequences("world-1", {
      player_actor_id: "actor-1",
      choice_key: "help",
      choice_kind: "intervention",
      prompt: "Help?",
      selected_option: "Yes",
    });
    await recordPlayerChoice("world-1", {
      player_actor_id: "actor-1",
      choice_key: "help",
      choice_kind: "intervention",
      prompt: "Help?",
      selected_option: "Yes",
    });

    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      "/api/worlds/world-1/worldlines",
      "/api/worlds/world-1/worldlines/fork",
      "/api/worlds/world-1/worldlines/worldline-1/compare/worldline-2",
      "/api/worlds/world-1/gm/agendas?worldline_id=worldline-1",
      "/api/worlds/world-1/gm/agendas",
      "/api/worlds/world-1/gm/agendas/agenda-1",
      "/api/worlds/world-1/gm/proposals?status=proposed&limit=5",
      "/api/worlds/world-1/gm/proposals",
      "/api/worlds/world-1/gm/proposals/proposal-1/review",
      "/api/worlds/world-1/resolution-rules",
      "/api/worlds/world-1/resolution-rules",
      "/api/worlds/world-1/resolution-rules/rule-1",
      "/api/worlds/world-1/resolution-rules/rule-1/dry-run?worldline_id=worldline-1",
      "/api/worlds/world-1/player-actors?worldline_id=worldline-1",
      "/api/worlds/world-1/player-actors",
      "/api/worlds/world-1/player-choices?worldline_id=worldline-1&limit=5",
      "/api/worlds/world-1/player-choices/preview",
      "/api/worlds/world-1/player-choices",
    ]);
  });

  it("maps plot, route, and rumor flow requests", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([{ id: "hook-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "hook-2" }, 201))
      .mockResolvedValueOnce(jsonResponse([{ id: "thread-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "thread-2" }, 201))
      .mockResolvedValueOnce(jsonResponse([{ id: "route-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "route-1", affinity: 45 }))
      .mockResolvedValueOnce(jsonResponse([{ id: "condition-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "condition-2" }, 201))
      .mockResolvedValueOnce(jsonResponse({ id: "condition-2", status: "inactive" }))
      .mockResolvedValueOnce(jsonResponse({ matched: true, satisfied: [], unsatisfied: [] }))
      .mockResolvedValueOnce(jsonResponse([{ id: "beat-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "beat-2" }, 201))
      .mockResolvedValueOnce(jsonResponse([{ id: "episode-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "episode-2" }, 201))
      .mockResolvedValueOnce(jsonResponse([{ id: "group-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "group-2" }, 201))
      .mockResolvedValueOnce(jsonResponse([{ id: "suggestion-1" }]))
      .mockResolvedValueOnce(jsonResponse([{ id: "suggestion-2" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "suggestion-2", status: "accepted" }))
      .mockResolvedValueOnce(jsonResponse([{ id: "conflict-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "conflict-2" }, 201))
      .mockResolvedValueOnce(jsonResponse({ id: "conflict-2", status: "resolved" }))
      .mockResolvedValueOnce(jsonResponse([{ id: "rumor-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "rumor-2" }, 201))
      .mockResolvedValueOnce(jsonResponse([{ id: "propagation-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "propagation-2" }, 201))
      .mockResolvedValueOnce(jsonResponse({ id: "propagation-2", status: "delivered" }));
    vi.stubGlobal("fetch", fetchMock);

    await listStoryHooks("world-1", { worldline_id: "worldline-1" });
    await createStoryHook("world-1", {
      hook_key: "festival-promise",
      title: "Festival promise",
      hook_type: "promise",
      summary: "Promise to attend the festival.",
    });
    await listPlotThreads("world-1", { worldline_id: "worldline-1" });
    await createPlotThread("world-1", {
      thread_key: "festival-route",
      title: "Festival route",
      thread_type: "personal",
      summary: "Guide route pressure.",
    });
    await listRouteAffinities("world-1", { agent_id: "agent-1", status: "active" });
    await upsertRouteAffinity("world-1", {
      agent_id: "agent-1",
      route_key: "guide-route",
      affinity: 45,
    });
    await listEventTriggerConditions("world-1");
    await createEventTriggerCondition("world-1", {
      condition_key: "festival-flag",
      name: "Festival flag",
    });
    await updateEventTriggerCondition("world-1", "condition-2", { status: "inactive" });
    await dryRunEventTriggerCondition("world-1", "condition-2", {
      worldline_id: "worldline-1",
    });
    await listSceneBeats("world-1", { worldline_id: "worldline-1" });
    await createSceneBeat("world-1", { title: "Festival scene" });
    await listDailyEpisodes("world-1", { worldline_id: "worldline-1" });
    await createDailyEpisode("world-1", { title: "Festival morning" });
    await listGroupInteractions("world-1", { worldline_id: "worldline-1" });
    await createGroupInteraction("world-1", {
      context_key: "club-meeting",
      title: "Club meeting",
      interaction_type: "club",
    });
    await listRelationshipSuggestions("world-1", { worldline_id: "worldline-1" });
    await generateRelationshipSuggestions("world-1", { worldline_id: "worldline-1", limit: 5 });
    await updateRelationshipSuggestion("world-1", "suggestion-2", { status: "accepted" });
    await listOrganizationConflicts("world-1", { worldline_id: "worldline-1" });
    await createOrganizationConflict("world-1", {
      organization_id: "org-1",
      title: "Budget pressure",
      summary: "Festival budget pressure rises.",
    });
    await resolveOrganizationConflict("world-1", "conflict-2");
    await listRumors("world-1", { worldline_id: "worldline-1" });
    await createRumor("world-1", {
      rumor_key: "late-rehearsal",
      title: "Late rehearsal rumor",
      content: "Someone saw the club room lights after closing.",
    });
    await listRumorPropagations("world-1", { worldline_id: "worldline-1" });
    await createRumorPropagation("world-1", {
      rumor_id: "rumor-2",
      propagation_reason: "Shared after class",
    });
    await deliverRumorPropagation("world-1", "propagation-2");

    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      "/api/worlds/world-1/story-hooks?worldline_id=worldline-1",
      "/api/worlds/world-1/story-hooks",
      "/api/worlds/world-1/plot-threads?worldline_id=worldline-1",
      "/api/worlds/world-1/plot-threads",
      "/api/worlds/world-1/route-affinities?agent_id=agent-1&status=active",
      "/api/worlds/world-1/route-affinities",
      "/api/worlds/world-1/event-trigger-conditions",
      "/api/worlds/world-1/event-trigger-conditions",
      "/api/worlds/world-1/event-trigger-conditions/condition-2",
      "/api/worlds/world-1/event-trigger-conditions/condition-2/dry-run?worldline_id=worldline-1",
      "/api/worlds/world-1/scene-beats?worldline_id=worldline-1",
      "/api/worlds/world-1/scene-beats",
      "/api/worlds/world-1/daily-episodes?worldline_id=worldline-1",
      "/api/worlds/world-1/daily-episodes",
      "/api/worlds/world-1/group-interactions?worldline_id=worldline-1",
      "/api/worlds/world-1/group-interactions",
      "/api/worlds/world-1/relationship-suggestions?worldline_id=worldline-1",
      "/api/worlds/world-1/relationship-suggestions/generate?worldline_id=worldline-1&limit=5",
      "/api/worlds/world-1/relationship-suggestions/suggestion-2",
      "/api/worlds/world-1/organization-conflicts?worldline_id=worldline-1",
      "/api/worlds/world-1/organization-conflicts",
      "/api/worlds/world-1/organization-conflicts/conflict-2/resolve",
      "/api/worlds/world-1/rumors?worldline_id=worldline-1",
      "/api/worlds/world-1/rumors",
      "/api/worlds/world-1/rumor-propagations?worldline_id=worldline-1",
      "/api/worlds/world-1/rumor-propagations",
      "/api/worlds/world-1/rumor-propagations/propagation-2/deliver",
    ]);
  });

  it("maps knowledge, player, and guardrail requests", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ worldline_id: "worldline-1" }))
      .mockResolvedValueOnce(jsonResponse([{ id: "knowledge-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "knowledge-1" }))
      .mockResolvedValueOnce(jsonResponse([{ id: "secret-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "secret-2" }, 201))
      .mockResolvedValueOnce(jsonResponse({ id: "secret-2", status: "revealed" }))
      .mockResolvedValueOnce(jsonResponse([{ id: "emotion-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "emotion-1" }))
      .mockResolvedValueOnce(jsonResponse([{ id: "repair-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "repair-2" }, 201))
      .mockResolvedValueOnce(jsonResponse({ id: "repair-2", status: "applied" }))
      .mockResolvedValueOnce(jsonResponse([{ id: "journal-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "journal-2" }, 201))
      .mockResolvedValueOnce(jsonResponse([{ id: "notification-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "notification-2" }, 201))
      .mockResolvedValueOnce(jsonResponse([{ id: "intervention-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "intervention-2" }, 201))
      .mockResolvedValueOnce(jsonResponse([{ id: "style-review-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "style-review-2" }, 201))
      .mockResolvedValueOnce(jsonResponse([{ id: "continuity-review-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "continuity-review-2" }, 201));
    vi.stubGlobal("fetch", fetchMock);

    await getLivingWorldDashboard("world-1", { worldline_id: "worldline-1" });
    await listKnowledgeFacts("world-1", {
      worldline_id: "worldline-1",
      agent_id: "agent-1",
      limit: 5,
    });
    await upsertKnowledgeFact("world-1", {
      agent_id: "agent-1",
      fact_key: "club-note",
      content: "Guide noticed the club room.",
    });
    await listSecrets("world-1", { status: "hidden", limit: 5 });
    await createSecret("world-1", {
      secret_key: "hidden-letter",
      title: "Hidden letter",
      content: "Letter.",
    });
    await revealSecret("world-1", "secret-2");
    await listEmotionalStates("world-1", { agent_id: "agent-1" });
    await upsertEmotionalState("world-1", { agent_id: "agent-1", mood: "restless" });
    await listRelationshipRepairs("world-1", { status: "proposed", limit: 5 });
    await createRelationshipRepair("world-1", {
      relationship_id: "relationship-1",
      repair_kind: "apology",
      reason: "Missed practice.",
    });
    await applyRelationshipRepair("world-1", "repair-2");
    await listPlayerJournal("world-1", { user_id: "user-1", limit: 5 });
    await createPlayerJournalEntry("world-1", {
      entry_kind: "event",
      title: "Journal",
      body: "Body",
    });
    await listNotifications("world-1", { status: "unread", limit: 5 });
    await createNotification("world-1", {
      notification_kind: "rumor",
      title: "Notice",
      body: "Body",
    });
    await listInterventions("world-1", { status: "recorded", limit: 5 });
    await createIntervention("world-1", {
      player_actor_id: "actor-1",
      intervention_kind: "contact",
      prompt: "Message.",
    });
    await listGMStyleReviews("world-1", { status: "warning", limit: 5 });
    await createGMStyleReview("world-1", {
      source_kind: "manual",
      reviewed_text: "As an AI chatbot.",
    });
    await listNarrativeContinuityReviews("world-1", { status: "warning", limit: 5 });
    await createNarrativeContinuityReview("world-1", {
      source_kind: "manual",
      reviewed_text: "Everyone knows.",
    });

    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      "/api/worlds/world-1/living-world-dashboard?worldline_id=worldline-1",
      "/api/worlds/world-1/knowledge?worldline_id=worldline-1&agent_id=agent-1&limit=5",
      "/api/worlds/world-1/knowledge",
      "/api/worlds/world-1/secrets?status=hidden&limit=5",
      "/api/worlds/world-1/secrets",
      "/api/worlds/world-1/secrets/secret-2/reveal",
      "/api/worlds/world-1/emotional-states?agent_id=agent-1",
      "/api/worlds/world-1/emotional-states",
      "/api/worlds/world-1/relationship-repairs?status=proposed&limit=5",
      "/api/worlds/world-1/relationship-repairs",
      "/api/worlds/world-1/relationship-repairs/repair-2/apply",
      "/api/worlds/world-1/player-journal?user_id=user-1&limit=5",
      "/api/worlds/world-1/player-journal",
      "/api/worlds/world-1/notifications?status=unread&limit=5",
      "/api/worlds/world-1/notifications",
      "/api/worlds/world-1/interventions?status=recorded&limit=5",
      "/api/worlds/world-1/interventions",
      "/api/worlds/world-1/gm-style-reviews?status=warning&limit=5",
      "/api/worlds/world-1/gm-style-reviews",
      "/api/worlds/world-1/narrative-continuity-reviews?status=warning&limit=5",
      "/api/worlds/world-1/narrative-continuity-reviews",
    ]);
  });

  it("sends clock control requests", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ status: "paused" }))
      .mockResolvedValueOnce(jsonResponse({ status: "running" }))
      .mockResolvedValueOnce(jsonResponse({ status: "running" }))
      .mockResolvedValueOnce(jsonResponse([{ transition_type: "resume" }]));
    vi.stubGlobal("fetch", fetchMock);

    await pauseWorldClock("world-1", "rest");
    await resumeWorldClock("world-1", "2", "go");
    await skipWorldClock("world-1", "2030-01-01T00:00:00Z");
    await listClockTransitions("world-1", 5);

    expect(fetchMock.mock.calls[0][0]).toBe("/api/worlds/world-1/clock/pause");
    expect(fetchMock.mock.calls[1][0]).toBe("/api/worlds/world-1/clock/resume");
    expect(fetchMock.mock.calls[1][1].body).toBe(
      JSON.stringify({ speed_multiplier: "2", reason: "go" }),
    );
    expect(fetchMock.mock.calls[2][0]).toBe("/api/worlds/world-1/clock/skip");
    expect(fetchMock.mock.calls[3][0]).toBe(
      "/api/worlds/world-1/clock/transitions?limit=5",
    );
  });

  it("maps beta release readiness requests", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([{ id: "milestone-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "milestone-2" }, 201))
      .mockResolvedValueOnce(jsonResponse([{ id: "ending-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "ending-2" }, 201))
      .mockResolvedValueOnce(jsonResponse({ matched: true }))
      .mockResolvedValueOnce(jsonResponse([{ id: "eval-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "eval-2" }, 201))
      .mockResolvedValueOnce(jsonResponse([{ id: "template-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "template-2" }, 201))
      .mockResolvedValueOnce(jsonResponse({ id: "job-1", status: "preview" }))
      .mockResolvedValueOnce(jsonResponse({ id: "job-2", status: "applied" }))
      .mockResolvedValueOnce(jsonResponse(null))
      .mockResolvedValueOnce(jsonResponse({ id: "profile-1", status: "ready" }))
      .mockResolvedValueOnce(jsonResponse([{ id: "checklist-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "checklist-2" }, 201))
      .mockResolvedValueOnce(jsonResponse([{ id: "item-1" }]));
    vi.stubGlobal("fetch", fetchMock);

    await listRouteMilestones("world-1", { worldline_id: "worldline-1" });
    await createRouteMilestone("world-1", {
      milestone_key: "festival-promise",
      title: "Festival promise",
    });
    await listEndingCandidates("world-1", { status: "available", ending_type: "normal" });
    await createEndingCandidate("world-1", {
      ending_key: "hero-normal",
      title: "Hero normal",
      ending_type: "normal",
    });
    await dryRunEndingCandidate("world-1", "ending-2", { worldline_id: "worldline-1" });
    await listLongRunEvals("world-1", { worldline_id: "worldline-1" });
    await createLongRunEval("world-1", { eval_key: "seven-day", horizon_days: 7 });
    await listAuthoringTemplates("world-1", { template_kind: "world_bundle" });
    await createAuthoringTemplate("world-1", {
      template_key: "hero-source",
      template_kind: "world_bundle",
      name: "Hero source",
    });
    await previewAuthoringTemplate("world-1", "template-2");
    await applyAuthoringTemplate("world-1", "template-2", { metadata: { operator: "test" } });
    await getReleaseProfile("world-1");
    await upsertReleaseProfile("world-1", { profile_key: "beta", status: "ready" });
    await listBetaChecklists("world-1", { worldline_id: "worldline-1" });
    await createBetaChecklist("world-1", { run_key: "beta-readiness" });
    await listBetaChecklistItems("world-1", "checklist-2");

    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      "/api/worlds/world-1/route-milestones?worldline_id=worldline-1",
      "/api/worlds/world-1/route-milestones",
      "/api/worlds/world-1/ending-candidates?status=available&ending_type=normal",
      "/api/worlds/world-1/ending-candidates",
      "/api/worlds/world-1/ending-candidates/ending-2/dry-run?worldline_id=worldline-1",
      "/api/worlds/world-1/long-run-evals?worldline_id=worldline-1",
      "/api/worlds/world-1/long-run-evals",
      "/api/worlds/world-1/authoring-templates?template_kind=world_bundle",
      "/api/worlds/world-1/authoring-templates",
      "/api/worlds/world-1/authoring-templates/template-2/preview",
      "/api/worlds/world-1/authoring-templates/template-2/apply",
      "/api/worlds/world-1/release-profile",
      "/api/worlds/world-1/release-profile",
      "/api/worlds/world-1/beta-checklists?worldline_id=worldline-1",
      "/api/worlds/world-1/beta-checklists",
      "/api/worlds/world-1/beta-checklists/checklist-2/items",
    ]);
  });

  it("maps replay and snapshot requests", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ source_sequence: 3 }))
      .mockResolvedValueOnce(jsonResponse(null))
      .mockResolvedValueOnce(jsonResponse({ id: "snapshot-1" }, 201))
      .mockResolvedValueOnce(jsonResponse({ status: "ok" }))
      .mockResolvedValueOnce(jsonResponse([{ sequence: 3 }]));
    vi.stubGlobal("fetch", fetchMock);

    await getReplayState("world-1");
    await getLatestSnapshot("world-1");
    await createSnapshot("world-1");
    await getSnapshotIntegrity("world-1");
    await listWorldEvents("world-1", {
      event_name: "agent.run_succeeded",
      actor_ref: "agent:guide",
      sequence_after: 1,
      wall_time_from: "2026-04-17T00:00:00Z",
      limit: 10,
    });

    expect(fetchMock.mock.calls[0][0]).toBe("/api/worlds/world-1/replay/state");
    expect(fetchMock.mock.calls[1][0]).toBe("/api/worlds/world-1/snapshots/latest");
    expect(fetchMock.mock.calls[2][0]).toBe("/api/worlds/world-1/snapshots");
    expect(fetchMock.mock.calls[3][0]).toBe("/api/worlds/world-1/snapshots/integrity");
    expect(fetchMock.mock.calls[4][0]).toBe(
      "/api/worlds/world-1/events?event_name=agent.run_succeeded&actor_ref=agent%3Aguide&sequence_after=1&wall_time_from=2026-04-17T00%3A00%3A00Z&limit=10",
    );
    expect((fetchMock.mock.calls[2][1].headers as Headers).get("X-CSRF-Token")).toBe(
      "csrf-token",
    );
  });

  it("maps calendar and schedule requests", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([{ rule_key: "weekday" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "rule-1" }, 201))
      .mockResolvedValueOnce(jsonResponse({ match_count: 1 }))
      .mockResolvedValueOnce(jsonResponse({ id: "rule-1" }))
      .mockResolvedValueOnce(jsonResponse({ id: "entry-1" }, 201))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    await listScheduleRules("world-1");
    await createScheduleRule("world-1", { rule_key: "weekday", name: "Weekday", kind: "weekday" });
    await previewScheduleRule("world-1", {
      kind: "timetable",
      config: { hours: [8] },
      start_world_time: "2030-01-01T07:00:00Z",
      horizon_hours: 4,
    });
    await updateScheduleRule("world-1", "rule-1", { is_enabled: false });
    await createAgentCalendarEntry("world-1", "agent-1", {
      title: "Morning scene",
      starts_at: "2030-01-01T08:00:00Z",
    });
    await cancelAgentCalendarEntry("world-1", "agent-1", "entry-1");

    expect(fetchMock.mock.calls[0][0]).toBe("/api/worlds/world-1/schedule-rules");
    expect(fetchMock.mock.calls[1][0]).toBe("/api/worlds/world-1/schedule-rules");
    expect(fetchMock.mock.calls[2][0]).toBe("/api/worlds/world-1/schedule-rules/preview");
    expect(fetchMock.mock.calls[3][0]).toBe("/api/worlds/world-1/schedule-rules/rule-1");
    expect(fetchMock.mock.calls[4][0]).toBe("/api/worlds/world-1/agents/agent-1/calendar");
    expect(fetchMock.mock.calls[5][0]).toBe(
      "/api/worlds/world-1/agents/agent-1/calendar/entry-1",
    );
  });

  it("maps memory requests", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([{ id: "memory-1" }]))
      .mockResolvedValueOnce(jsonResponse([{ id: "memory-1", score: 0.9 }]))
    vi.stubGlobal("fetch", fetchMock);

    await listAgentMemory("world-1", "agent-1");
    await searchAgentMemory("world-1", "agent-1", { query_text: "green tea", limit: 5 });

    expect(fetchMock.mock.calls[0][0]).toBe("/api/worlds/world-1/agents/agent-1/memory");
    expect(fetchMock.mock.calls[1][0]).toBe("/api/worlds/world-1/agents/agent-1/memory/search");
    expect(fetchMock.mock.calls[1][1].body).toBe(
      JSON.stringify({ query_text: "green tea", limit: 5 }),
    );
  });

  it("maps memory backend profile requests", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([{ id: "memory-profile-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "memory-profile-1" }, 201))
      .mockResolvedValueOnce(jsonResponse({ id: "memory-profile-1" }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(jsonResponse({ jobs: [{ id: "job-1", status: "failed" }] }))
      .mockResolvedValueOnce(jsonResponse({ id: "job-1", status: "pending" }))
      .mockResolvedValueOnce(jsonResponse({ candidate_count: 1 }));
    vi.stubGlobal("fetch", fetchMock);

    await listMemoryBackendProfiles();
    await createMemoryBackendProfile({
      profile_key: "mem0-default",
      name: "Mem0 default",
      backend_kind: "mem0_oss",
    });
    await updateMemoryBackendProfile("memory-profile-1", { name: "Updated" });
    await deleteMemoryBackendProfile("memory-profile-1");
    await listMemoryBackendProfileJobs("memory-profile-1", { status: "failed", limit: 5 });
    await retryMemoryWriteJob("job-1");
    await dryRunMemoryBackfill(25);

    expect(fetchMock.mock.calls[0][0]).toBe("/api/memory-backend-profiles");
    expect(fetchMock.mock.calls[1][0]).toBe("/api/memory-backend-profiles");
    expect(fetchMock.mock.calls[2][0]).toBe("/api/memory-backend-profiles/memory-profile-1");
    expect(fetchMock.mock.calls[3][0]).toBe("/api/memory-backend-profiles/memory-profile-1");
    expect(fetchMock.mock.calls[4][0]).toBe(
      "/api/memory-backend-profiles/memory-profile-1/jobs?status=failed&limit=5",
    );
    expect(fetchMock.mock.calls[5][0]).toBe("/api/memory-write-jobs/job-1/retry");
    expect(fetchMock.mock.calls[6][0]).toBe("/api/memory-backfill/dry-run?limit=25");
  });

  it("maps runtime and provider requests", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ desired_state: "stopped" }))
      .mockResolvedValueOnce(jsonResponse({ desired_state: "running" }))
      .mockResolvedValueOnce(
        jsonResponse({
          desired_state: "running",
          runtime_loop_interval_seconds: 5,
          runtime_batch_limit: 20,
        }),
      )
      .mockResolvedValueOnce(jsonResponse({ policy_mode: "policy_only" }))
      .mockResolvedValueOnce(jsonResponse({ status: "ok", sections: [] }))
      .mockResolvedValueOnce(jsonResponse([{ event_type: "runtime.iteration_failed" }]))
      .mockResolvedValueOnce(jsonResponse([{ event_type: "agent.run_succeeded" }]))
      .mockResolvedValueOnce(jsonResponse([{ id: "profile-1" }]))
      .mockResolvedValueOnce(jsonResponse([{ id: "profile-1", health: "ok" }]))
      .mockResolvedValueOnce(jsonResponse([{ identifier: "builtin.openai_compatible" }]))
      .mockResolvedValueOnce(jsonResponse([{ owner_kind: "provider_profile" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "profile-1" }, 201))
      .mockResolvedValueOnce(jsonResponse({ id: "profile-1" }))
      .mockResolvedValueOnce(jsonResponse({ status: "success", latency_ms: 10 }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    await getRuntimeControl();
    await updateRuntimeControl({ desired_state: "running" });
    await getRuntimeStatus();
    await getExternalToolPolicy();
    await getScaleReadiness();
    await listRuntimeDiagnostics();
    await listWorldDiagnostics("world-1");
    await listProviderProfiles();
    await listProviderHealth();
    await listPluginCatalog("model_provider");
    await listPluginBindings("model_provider");
    await createProviderProfile({
      profile_key: "openai-local",
      name: "OpenAI Local",
      provider_type: "openai_compatible",
      base_url: "https://api.example.test/v1",
      model_name: "gpt-test",
      api_key_ref: "openai-local",
      timeout_seconds: 20,
      retry_attempts: 1,
    });
    await updateProviderProfile("profile-1", { name: "Updated" });
    await testProviderProfile("profile-1", "Reply with OK.");
    await disableProviderProfile("profile-1");

    expect(fetchMock.mock.calls[0][0]).toBe("/api/runtime/control");
    expect(fetchMock.mock.calls[1][0]).toBe("/api/runtime/control");
    expect(fetchMock.mock.calls[2][0]).toBe("/api/runtime/status");
    expect(fetchMock.mock.calls[3][0]).toBe("/api/runtime/tool-policy");
    expect(fetchMock.mock.calls[4][0]).toBe("/api/runtime/scale-readiness");
    expect(fetchMock.mock.calls[5][0]).toBe("/api/runtime/diagnostics");
    expect(fetchMock.mock.calls[6][0]).toBe("/api/worlds/world-1/diagnostics");
    expect(fetchMock.mock.calls[7][0]).toBe("/api/provider-profiles");
    expect(fetchMock.mock.calls[8][0]).toBe("/api/provider-profiles/health");
    expect(fetchMock.mock.calls[9][0]).toBe("/api/plugins/catalog?category=model_provider");
    expect(fetchMock.mock.calls[10][0]).toBe("/api/plugins/bindings?category=model_provider");
    expect(fetchMock.mock.calls[11][0]).toBe("/api/provider-profiles");
    expect(fetchMock.mock.calls[12][0]).toBe("/api/provider-profiles/profile-1");
    expect(fetchMock.mock.calls[13][0]).toBe("/api/provider-profiles/profile-1/test-call");
    expect(fetchMock.mock.calls[14][0]).toBe("/api/provider-profiles/profile-1");
  });

  it("maps runs and narrative requests", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([{ run_id: "run-1" }]))
      .mockResolvedValueOnce(jsonResponse({ run_id: "run-2" }, 201))
      .mockResolvedValueOnce(jsonResponse([{ id: "artifact-1" }]))
      .mockResolvedValueOnce(jsonResponse({ selected_agent_id: "agent-1" }))
      .mockResolvedValueOnce(jsonResponse({ latest_hit_count: 2 }))
      .mockResolvedValueOnce(jsonResponse([{ id: "artifact-2" }]))
      .mockResolvedValueOnce(jsonResponse({ prompt_text: "Prompt" }))
      .mockResolvedValueOnce(jsonResponse([{ id: "artifact-3" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "artifact-4" }, 201))
      .mockResolvedValueOnce(jsonResponse({ id: "publication-1" }))
      .mockResolvedValueOnce(jsonResponse({ id: "publication-1", status: "unpublished" }));
    vi.stubGlobal("fetch", fetchMock);

    await listAgentRuns("world-1", "agent-1");
    await runAgent("world-1", "agent-1", { prompt: "hello" });
    await listNarrativeArtifacts("world-1");
    await getConversationSpeakerPreview("world-1", "conversation-1");
    await getConversationMemorySummary("world-1", "conversation-1");
    await listConversationNarrativeArtifacts("world-1", "conversation-1");
    await previewConversationNarrativePrompt("world-1", "conversation-1", "summary_only");
    await generateConversationNarrativeArtifacts("world-1", "conversation-1", "summary_only");
    await createNarrativeArtifact("world-1", { title: "Artifact", content: "Body" });
    await publishNarrativeArtifact("world-1", "artifact-4", {
      reader_visible: true,
      override_style_warning: true,
    });
    await unpublishNarrativeArtifact("world-1", "artifact-4");

    expect(fetchMock.mock.calls[0][0]).toBe("/api/worlds/world-1/agents/agent-1/runs");
    expect(fetchMock.mock.calls[1][0]).toBe("/api/worlds/world-1/agents/agent-1/run");
    expect(fetchMock.mock.calls[2][0]).toBe("/api/worlds/world-1/narrative-artifacts");
    expect(fetchMock.mock.calls[3][0]).toBe(
      "/api/worlds/world-1/conversations/conversation-1/speaker-preview",
    );
    expect(fetchMock.mock.calls[4][0]).toBe(
      "/api/worlds/world-1/conversations/conversation-1/memory/summary",
    );
    expect(fetchMock.mock.calls[5][0]).toBe(
      "/api/worlds/world-1/conversations/conversation-1/narrative",
    );
    expect(fetchMock.mock.calls[6][0]).toBe(
      "/api/worlds/world-1/conversations/conversation-1/narrative/preview",
    );
    expect(fetchMock.mock.calls[7][0]).toBe(
      "/api/worlds/world-1/conversations/conversation-1/narrative/generate",
    );
    expect(fetchMock.mock.calls[8][0]).toBe("/api/worlds/world-1/narrative-artifacts");
    expect(fetchMock.mock.calls[9][0]).toBe(
      "/api/worlds/world-1/narrative-artifacts/artifact-4/publish",
    );
    expect(fetchMock.mock.calls[10][0]).toBe(
      "/api/worlds/world-1/narrative-artifacts/artifact-4/unpublish",
    );
  });

  it("maps calendar conflict requests", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(jsonResponse({ conflict_count: 0 }));
    vi.stubGlobal("fetch", fetchMock);

    await getCalendarConflicts("world-1", {
      start_world_time: "2030-01-01T00:00:00Z",
      horizon_hours: 24,
      limit: 10,
    });

    expect(fetchMock.mock.calls[0][0]).toBe(
      "/api/worlds/world-1/calendar/conflicts?start_world_time=2030-01-01T00%3A00%3A00Z&horizon_hours=24&limit=10",
    );
  });

  it("maps agent run detail requests", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(jsonResponse({ run: { run_id: "run-1" } }));
    vi.stubGlobal("fetch", fetchMock);

    await getAgentRunDetail("world-1", "agent-1", "run-1");

    expect(fetchMock.mock.calls[0][0]).toBe(
      "/api/worlds/world-1/agents/agent-1/runs/run-1",
    );
  });

  it("maps conversation diagnostics summary requests", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(jsonResponse({ operator_message: "ok" }));
    vi.stubGlobal("fetch", fetchMock);

    await getConversationDiagnosticsSummary("world-1", "conversation-1");

    expect(fetchMock.mock.calls[0][0]).toBe(
      "/api/worlds/world-1/conversations/conversation-1/diagnostics/summary",
    );
  });

  it("maps narrative reader filter and detail requests", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([{ id: "artifact-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "artifact-1" }));
    vi.stubGlobal("fetch", fetchMock);

    await listFilteredNarrativeArtifacts("world-1", {
      artifact_kind: "chapter_draft",
      source_conversation_id: "conversation-1",
      q: "summary",
      source_kind: "conversation",
      publication_status: "published",
      order_by: "published_at",
      limit: 10,
    });
    await getNarrativeArtifact("world-1", "artifact-1");

    expect(fetchMock.mock.calls[0][0]).toBe(
      "/api/worlds/world-1/narrative-artifacts?artifact_kind=chapter_draft&source_conversation_id=conversation-1&q=summary&source_kind=conversation&publication_status=published&order_by=published_at&limit=10",
    );
    expect(fetchMock.mock.calls[1][0]).toBe("/api/worlds/world-1/narrative-artifacts/artifact-1");
  });

  it("maps persona and observation requests", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(null))
      .mockResolvedValueOnce(jsonResponse({ id: "persona-1" }))
      .mockResolvedValueOnce(jsonResponse({ valid: true, issues: [] }))
      .mockResolvedValueOnce(jsonResponse([{ id: "observation-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "observation-2" }, 201))
      .mockResolvedValueOnce(jsonResponse([{ id: "observation-1" }, { id: "observation-2" }]));
    vi.stubGlobal("fetch", fetchMock);

    await getAgentPersona("world-1", "agent-1");
    await updateAgentPersona("world-1", "agent-1", {
      persona_text: "Careful guide.",
      behavior_policy: { tone: "direct" },
      is_enabled: true,
    });
    await validateAgentPersona("world-1", "agent-1", {
      persona_text: "Careful guide.",
      behavior_policy: { tone: "direct" },
      is_enabled: true,
    });
    await listAgentObservations("world-1", "agent-1");
    await createAgentObservation("world-1", "agent-1", { content: "Manual note" });
    await refreshAgentObservations("world-1", "agent-1");

    expect(fetchMock.mock.calls[0][0]).toBe("/api/worlds/world-1/agents/agent-1/persona");
    expect(fetchMock.mock.calls[1][0]).toBe("/api/worlds/world-1/agents/agent-1/persona");
    expect(fetchMock.mock.calls[2][0]).toBe("/api/worlds/world-1/agents/agent-1/persona/validate");
    expect(fetchMock.mock.calls[3][0]).toBe("/api/worlds/world-1/agents/agent-1/observations");
    expect(fetchMock.mock.calls[4][0]).toBe("/api/worlds/world-1/agents/agent-1/observations");
    expect(fetchMock.mock.calls[5][0]).toBe(
      "/api/worlds/world-1/agents/agent-1/observations/refresh",
    );
  });

  it("raises typed world client errors", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ detail: "World slug already exists" }, 409)),
    );

    await expect(createWorld({ slug: "first-world", name: "First World" })).rejects.toMatchObject({
      name: "WorldClientError",
      status: 409,
    });
  });

  it("summarizes structured publication gate errors", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(
          {
            detail: {
              message: "Narrative publication blocked by continuity review",
              review_id: "review-1",
              review_status: "fail",
              issues: [{ code: "hidden_secret_leak" }],
            },
          },
          422,
        ),
      ),
    );

    await expect(
      publishNarrativeArtifact("world-1", "artifact-1", { reader_visible: true }),
    ).rejects.toMatchObject({
      message: "Narrative publication blocked by continuity review (fail)",
      status: 422,
    });
  });
});

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}
