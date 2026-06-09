import { afterEach, describe, expect, it, vi } from "vitest";

import {
  getMultimodalDiagnostics,
  getMultimodalEvalRun,
  listMultimodalEvalRuns,
  runMultimodalEval,
} from "@/lib/worlds/diagnostics";

describe("multimodal diagnostics admin client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    document.cookie = "noveland_csrf=; Max-Age=0; Path=/";
  });

  it("reads diagnostics and eval runs through world proxy paths", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(diagnostics))
      .mockResolvedValueOnce(jsonResponse([evalRun]))
      .mockResolvedValueOnce(jsonResponse(evalRun));
    vi.stubGlobal("fetch", fetchMock);

    await getMultimodalDiagnostics("world-1", { worldline_id: "worldline-1" });
    await listMultimodalEvalRuns("world-1", { worldline_id: "worldline-1", limit: 10 });
    await getMultimodalEvalRun("world-1", "run-1");

    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      "/api/worlds/world-1/diagnostics/multimodal?worldline_id=worldline-1",
      "/api/worlds/world-1/multimodal-evals?worldline_id=worldline-1&limit=10",
      "/api/worlds/world-1/multimodal-evals/run-1",
    ]);
  });

  it("uses csrf and safe defaults when running a multimodal eval", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi.fn().mockResolvedValueOnce(jsonResponse(evalRun));
    vi.stubGlobal("fetch", fetchMock);

    await runMultimodalEval("world-1", { worldline_id: "worldline-1" });

    expect(fetchMock.mock.calls[0][0]).toBe("/api/worlds/world-1/multimodal-evals/run");
    expect((fetchMock.mock.calls[0][1].headers as Headers).get("X-CSRF-Token")).toBe(
      "csrf-token",
    );
    expect(JSON.parse(fetchMock.mock.calls[0][1].body as string)).toEqual({
      eval_key: "multimodal-smoke",
      horizon_days: 7,
      metadata: { source: "web_admin" },
      worldline_id: "worldline-1",
    });
  });

  it("encodes reserved characters in diagnostics route segments", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(diagnostics))
      .mockResolvedValueOnce(jsonResponse([evalRun]))
      .mockResolvedValueOnce(jsonResponse(evalRun))
      .mockResolvedValueOnce(jsonResponse(evalRun));
    vi.stubGlobal("fetch", fetchMock);

    const worldId = "world/diagnostics?admin=true#frag";
    const runId = "run/eval?detail=true#frag";

    await getMultimodalDiagnostics(worldId, { worldline_id: "line/main?x=1#frag" });
    await listMultimodalEvalRuns(worldId, { worldline_id: "line/main?x=1#frag", limit: 25 });
    await getMultimodalEvalRun(worldId, runId);
    await runMultimodalEval(worldId, { worldline_id: "line/main?x=1#frag" });

    const encodedWorld = encodeURIComponent(worldId);
    const encodedRun = encodeURIComponent(runId);

    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      `/api/worlds/${encodedWorld}/diagnostics/multimodal?worldline_id=line%2Fmain%3Fx%3D1%23frag`,
      `/api/worlds/${encodedWorld}/multimodal-evals?worldline_id=line%2Fmain%3Fx%3D1%23frag&limit=25`,
      `/api/worlds/${encodedWorld}/multimodal-evals/${encodedRun}`,
      `/api/worlds/${encodedWorld}/multimodal-evals/run`,
    ]);
    expect((fetchMock.mock.calls[3][1].headers as Headers).get("X-CSRF-Token")).toBe(
      "csrf-token",
    );
  });

});

const diagnostics = {
  world_id: "world-1",
  worldline_id: "worldline-1",
  status: "completed",
  metrics: {},
  blockers: [],
  warnings: [],
  recommendations: [],
  evidence_refs: [],
  generated_at: "2026-05-14T00:00:00.000Z",
};

const evalRun = {
  id: "run-1",
  world_id: "world-1",
  worldline_id: "worldline-1",
  eval_key: "multimodal-smoke",
  horizon_days: 7,
  status: "completed",
  started_at: "2026-05-14T00:00:00.000Z",
  finished_at: "2026-05-14T00:00:01.000Z",
  metrics: {},
  recommendations: [],
  blockers: [],
  metadata: {},
  created_at: "2026-05-14T00:00:00.000Z",
  updated_at: "2026-05-14T00:00:01.000Z",
};

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: { "Content-Type": "application/json" },
  });
}
