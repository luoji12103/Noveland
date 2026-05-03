import { afterEach, describe, expect, it, vi } from "vitest";

import {
  cancelAgentCalendarEntry,
  createAgentCalendarEntry,
  createAgentObservation,
  createMemoryBackendProfile,
  createNarrativeArtifact,
  createProviderProfile,
  createAgentPreset,
  createScheduleRule,
  createSnapshot,
  generateConversationNarrativeArtifacts,
  getCalendarConflicts,
  getAgentRunDetail,
  getNarrativeArtifact,
  createWorld,
  deactivateAgentPreset,
  deleteMemoryBackendProfile,
  disableProviderProfile,
  dryRunMemoryBackfill,
  deactivateScene,
  exportWorldComposition,
  getRuntimeControl,
  getRuntimeStatus,
  getLatestSnapshot,
  getAgentPersona,
  getReplayState,
  getSnapshotIntegrity,
  listWorldEvents,
  listFilteredNarrativeArtifacts,
  listClockTransitions,
  listRuntimeDiagnostics,
  listAgentRuns,
  listAgentObservations,
  listMemoryBackendProfiles,
  listMemoryBackendProfileJobs,
  pauseWorldClock,
  previewScheduleRule,
  resumeWorldClock,
  listAgentMemory,
  listNarrativeArtifacts,
  listConversationNarrativeArtifacts,
  listAgentPresets,
  listProviderProfiles,
  listProviderHealth,
  runAgent,
  refreshAgentObservations,
  retryMemoryWriteJob,
  skipWorldClock,
  listMemberCandidates,
  listScheduleRules,
  listWorldDiagnostics,
  searchAgentMemory,
  testProviderProfile,
  importWorldComposition,
  updateMemoryBackendProfile,
  updateAgent,
  updateAgentPreset,
  updateProviderProfile,
  updateAgentPersona,
  updateRuntimeControl,
  updateScheduleRule,
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
      .mockResolvedValueOnce(jsonResponse({ world: { slug: "first-world" } }))
      .mockResolvedValueOnce(jsonResponse({ id: "world-2" }, 201));
    vi.stubGlobal("fetch", fetchMock);

    await listAgentPresets();
    await createAgentPreset({
      preset_key: "storyteller",
      name: "Storyteller",
      default_kind: "narrative_agent",
    });
    await updateAgentPreset("preset-1", { name: "Updated preset" });
    await deactivateAgentPreset("preset-1");
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

    expect(fetchMock.mock.calls[0][0]).toBe("/api/agent-presets");
    expect(fetchMock.mock.calls[1][0]).toBe("/api/agent-presets");
    expect(fetchMock.mock.calls[2][0]).toBe("/api/agent-presets/preset-1");
    expect(fetchMock.mock.calls[3][0]).toBe("/api/agent-presets/preset-1");
    expect(fetchMock.mock.calls[4][0]).toBe("/api/worlds/world-1/composition-export");
    expect(fetchMock.mock.calls[5][0]).toBe("/api/world-compositions/import");
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
      .mockResolvedValueOnce(jsonResponse([{ event_type: "runtime.iteration_failed" }]))
      .mockResolvedValueOnce(jsonResponse([{ event_type: "agent.run_succeeded" }]))
      .mockResolvedValueOnce(jsonResponse([{ id: "profile-1" }]))
      .mockResolvedValueOnce(jsonResponse([{ id: "profile-1", health: "ok" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "profile-1" }, 201))
      .mockResolvedValueOnce(jsonResponse({ id: "profile-1" }))
      .mockResolvedValueOnce(jsonResponse({ status: "success", latency_ms: 10 }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    await getRuntimeControl();
    await updateRuntimeControl({ desired_state: "running" });
    await getRuntimeStatus();
    await listRuntimeDiagnostics();
    await listWorldDiagnostics("world-1");
    await listProviderProfiles();
    await listProviderHealth();
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
    expect(fetchMock.mock.calls[3][0]).toBe("/api/runtime/diagnostics");
    expect(fetchMock.mock.calls[4][0]).toBe("/api/worlds/world-1/diagnostics");
    expect(fetchMock.mock.calls[5][0]).toBe("/api/provider-profiles");
    expect(fetchMock.mock.calls[6][0]).toBe("/api/provider-profiles/health");
    expect(fetchMock.mock.calls[7][0]).toBe("/api/provider-profiles");
    expect(fetchMock.mock.calls[8][0]).toBe("/api/provider-profiles/profile-1");
    expect(fetchMock.mock.calls[9][0]).toBe("/api/provider-profiles/profile-1/test-call");
    expect(fetchMock.mock.calls[10][0]).toBe("/api/provider-profiles/profile-1");
  });

  it("maps runs and narrative requests", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([{ run_id: "run-1" }]))
      .mockResolvedValueOnce(jsonResponse({ run_id: "run-2" }, 201))
      .mockResolvedValueOnce(jsonResponse([{ id: "artifact-1" }]))
      .mockResolvedValueOnce(jsonResponse([{ id: "artifact-2" }]))
      .mockResolvedValueOnce(jsonResponse([{ id: "artifact-3" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "artifact-4" }, 201));
    vi.stubGlobal("fetch", fetchMock);

    await listAgentRuns("world-1", "agent-1");
    await runAgent("world-1", "agent-1", { prompt: "hello" });
    await listNarrativeArtifacts("world-1");
    await listConversationNarrativeArtifacts("world-1", "conversation-1");
    await generateConversationNarrativeArtifacts("world-1", "conversation-1", "summary_only");
    await createNarrativeArtifact("world-1", { title: "Artifact", content: "Body" });

    expect(fetchMock.mock.calls[0][0]).toBe("/api/worlds/world-1/agents/agent-1/runs");
    expect(fetchMock.mock.calls[1][0]).toBe("/api/worlds/world-1/agents/agent-1/run");
    expect(fetchMock.mock.calls[2][0]).toBe("/api/worlds/world-1/narrative-artifacts");
    expect(fetchMock.mock.calls[3][0]).toBe("/api/worlds/world-1/conversations/conversation-1/narrative");
    expect(fetchMock.mock.calls[4][0]).toBe(
      "/api/worlds/world-1/conversations/conversation-1/narrative/generate",
    );
    expect(fetchMock.mock.calls[5][0]).toBe("/api/worlds/world-1/narrative-artifacts");
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

  it("maps narrative reader filter and detail requests", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([{ id: "artifact-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "artifact-1" }));
    vi.stubGlobal("fetch", fetchMock);

    await listFilteredNarrativeArtifacts("world-1", {
      artifact_kind: "chapter_draft",
      source_conversation_id: "conversation-1",
      limit: 10,
    });
    await getNarrativeArtifact("world-1", "artifact-1");

    expect(fetchMock.mock.calls[0][0]).toBe(
      "/api/worlds/world-1/narrative-artifacts?artifact_kind=chapter_draft&source_conversation_id=conversation-1&limit=10",
    );
    expect(fetchMock.mock.calls[1][0]).toBe("/api/worlds/world-1/narrative-artifacts/artifact-1");
  });

  it("maps persona and observation requests", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(null))
      .mockResolvedValueOnce(jsonResponse({ id: "persona-1" }))
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
    await listAgentObservations("world-1", "agent-1");
    await createAgentObservation("world-1", "agent-1", { content: "Manual note" });
    await refreshAgentObservations("world-1", "agent-1");

    expect(fetchMock.mock.calls[0][0]).toBe("/api/worlds/world-1/agents/agent-1/persona");
    expect(fetchMock.mock.calls[1][0]).toBe("/api/worlds/world-1/agents/agent-1/persona");
    expect(fetchMock.mock.calls[2][0]).toBe("/api/worlds/world-1/agents/agent-1/observations");
    expect(fetchMock.mock.calls[3][0]).toBe("/api/worlds/world-1/agents/agent-1/observations");
    expect(fetchMock.mock.calls[4][0]).toBe(
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
});

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}
