import { afterEach, describe, expect, it, vi } from "vitest";

import {
  cancelAgentCalendarEntry,
  createAgentCalendarEntry,
  createAgentMemoryItem,
  createNarrativeArtifact,
  createProviderProfile,
  createScheduleRule,
  createSnapshot,
  createWorld,
  disableAgentMemoryItem,
  disableProviderProfile,
  deactivateScene,
  getRuntimeControl,
  getRuntimeStatus,
  getLatestSnapshot,
  getReplayState,
  listAgentRuns,
  pauseWorldClock,
  resumeWorldClock,
  listAgentMemory,
  listNarrativeArtifacts,
  listProviderProfiles,
  runAgent,
  skipWorldClock,
  listMemberCandidates,
  listScheduleRules,
  searchAgentMemory,
  updateAgent,
  updateProviderProfile,
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

  it("sends clock control requests", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ status: "paused" }))
      .mockResolvedValueOnce(jsonResponse({ status: "running" }))
      .mockResolvedValueOnce(jsonResponse({ status: "running" }));
    vi.stubGlobal("fetch", fetchMock);

    await pauseWorldClock("world-1", "rest");
    await resumeWorldClock("world-1", "2", "go");
    await skipWorldClock("world-1", "2030-01-01T00:00:00Z");

    expect(fetchMock.mock.calls[0][0]).toBe("/api/worlds/world-1/clock/pause");
    expect(fetchMock.mock.calls[1][0]).toBe("/api/worlds/world-1/clock/resume");
    expect(fetchMock.mock.calls[1][1].body).toBe(
      JSON.stringify({ speed_multiplier: "2", reason: "go" }),
    );
    expect(fetchMock.mock.calls[2][0]).toBe("/api/worlds/world-1/clock/skip");
  });

  it("maps replay and snapshot requests", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ source_sequence: 3 }))
      .mockResolvedValueOnce(jsonResponse(null))
      .mockResolvedValueOnce(jsonResponse({ id: "snapshot-1" }, 201));
    vi.stubGlobal("fetch", fetchMock);

    await getReplayState("world-1");
    await getLatestSnapshot("world-1");
    await createSnapshot("world-1");

    expect(fetchMock.mock.calls[0][0]).toBe("/api/worlds/world-1/replay/state");
    expect(fetchMock.mock.calls[1][0]).toBe("/api/worlds/world-1/snapshots/latest");
    expect(fetchMock.mock.calls[2][0]).toBe("/api/worlds/world-1/snapshots");
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
      .mockResolvedValueOnce(jsonResponse({ id: "rule-1" }))
      .mockResolvedValueOnce(jsonResponse({ id: "entry-1" }, 201))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    await listScheduleRules("world-1");
    await createScheduleRule("world-1", { rule_key: "weekday", name: "Weekday", kind: "weekday" });
    await updateScheduleRule("world-1", "rule-1", { is_enabled: false });
    await createAgentCalendarEntry("world-1", "agent-1", {
      title: "Morning scene",
      starts_at: "2030-01-01T08:00:00Z",
    });
    await cancelAgentCalendarEntry("world-1", "agent-1", "entry-1");

    expect(fetchMock.mock.calls[0][0]).toBe("/api/worlds/world-1/schedule-rules");
    expect(fetchMock.mock.calls[1][0]).toBe("/api/worlds/world-1/schedule-rules");
    expect(fetchMock.mock.calls[2][0]).toBe("/api/worlds/world-1/schedule-rules/rule-1");
    expect(fetchMock.mock.calls[3][0]).toBe("/api/worlds/world-1/agents/agent-1/calendar");
    expect(fetchMock.mock.calls[4][0]).toBe(
      "/api/worlds/world-1/agents/agent-1/calendar/entry-1",
    );
  });

  it("maps memory requests", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([{ id: "memory-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "memory-1" }, 201))
      .mockResolvedValueOnce(jsonResponse([{ id: "memory-1", score: 0.9 }]))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    await listAgentMemory("world-1", "agent-1");
    await createAgentMemoryItem("world-1", "agent-1", {
      content: "Memory",
      embedding: [1, 0, 0],
    });
    await searchAgentMemory("world-1", "agent-1", { embedding: [1, 0, 0], limit: 5 });
    await disableAgentMemoryItem("world-1", "agent-1", "memory-1");

    expect(fetchMock.mock.calls[0][0]).toBe("/api/worlds/world-1/agents/agent-1/memory");
    expect(fetchMock.mock.calls[1][0]).toBe("/api/worlds/world-1/agents/agent-1/memory");
    expect(fetchMock.mock.calls[2][0]).toBe("/api/worlds/world-1/agents/agent-1/memory/search");
    expect(fetchMock.mock.calls[3][0]).toBe(
      "/api/worlds/world-1/agents/agent-1/memory/memory-1",
    );
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
      .mockResolvedValueOnce(jsonResponse([{ id: "profile-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "profile-1" }, 201))
      .mockResolvedValueOnce(jsonResponse({ id: "profile-1" }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    await getRuntimeControl();
    await updateRuntimeControl({ desired_state: "running" });
    await getRuntimeStatus();
    await listProviderProfiles();
    await createProviderProfile({
      profile_key: "openai-local",
      name: "OpenAI Local",
      provider_type: "openai_compatible",
      base_url: "https://api.example.test/v1",
      model_name: "gpt-test",
      api_key_ref: "openai-local",
    });
    await updateProviderProfile("profile-1", { name: "Updated" });
    await disableProviderProfile("profile-1");

    expect(fetchMock.mock.calls[0][0]).toBe("/api/runtime/control");
    expect(fetchMock.mock.calls[1][0]).toBe("/api/runtime/control");
    expect(fetchMock.mock.calls[2][0]).toBe("/api/runtime/status");
    expect(fetchMock.mock.calls[3][0]).toBe("/api/provider-profiles");
    expect(fetchMock.mock.calls[4][0]).toBe("/api/provider-profiles");
    expect(fetchMock.mock.calls[5][0]).toBe("/api/provider-profiles/profile-1");
    expect(fetchMock.mock.calls[6][0]).toBe("/api/provider-profiles/profile-1");
  });

  it("maps runs and narrative requests", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse([{ run_id: "run-1" }]))
      .mockResolvedValueOnce(jsonResponse({ run_id: "run-2" }, 201))
      .mockResolvedValueOnce(jsonResponse([{ id: "artifact-1" }]))
      .mockResolvedValueOnce(jsonResponse({ id: "artifact-2" }, 201));
    vi.stubGlobal("fetch", fetchMock);

    await listAgentRuns("world-1", "agent-1");
    await runAgent("world-1", "agent-1", { prompt: "hello" });
    await listNarrativeArtifacts("world-1");
    await createNarrativeArtifact("world-1", { title: "Artifact", content: "Body" });

    expect(fetchMock.mock.calls[0][0]).toBe("/api/worlds/world-1/agents/agent-1/runs");
    expect(fetchMock.mock.calls[1][0]).toBe("/api/worlds/world-1/agents/agent-1/run");
    expect(fetchMock.mock.calls[2][0]).toBe("/api/worlds/world-1/narrative-artifacts");
    expect(fetchMock.mock.calls[3][0]).toBe("/api/worlds/world-1/narrative-artifacts");
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
