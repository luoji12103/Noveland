import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createBetaFeedbackReport,
  listBetaFeedbackReports,
  triageBetaFeedbackReport,
} from "@/lib/beta-feedback/client";

describe("beta feedback client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    document.cookie = "noveland_csrf=; Max-Age=0; Path=/";
  });

  it("encodes world path segments and preserves filters as query parameters", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse([feedbackReport]));
    vi.stubGlobal("fetch", fetchMock);

    await listBetaFeedbackReports(worldId, {
      worldline_id: worldlineId,
      status: "submitted",
      issue_type: "provider",
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [path, request] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(path).toBe(
      "/api/worlds/world%2Fprivate%3Fbeta%3Dtrue%23frag/beta-feedback/reports" +
        "?worldline_id=worldline%2Fprivate%3Fphase%3D1%23frag&status=submitted&issue_type=provider",
    );
    expect(request.method).toBe("GET");
    expect(request.credentials).toBe("include");
    expect(request.cache).toBe("no-store");
    expect((request.headers as Headers).get("X-CSRF-Token")).toBeNull();
  });

  it("encodes world path segments when creating feedback reports", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(feedbackReport));
    vi.stubGlobal("fetch", fetchMock);

    const input = {
      worldline_id: worldlineId,
      issue_type: "provider" as const,
      severity: "high" as const,
      title: "Provider failed",
      description: "The provider degraded during onboarding.",
      reporter_note: null,
      evidence_refs: [{ kind: "provider" as const, id: "provider-1" }],
      metadata: { request_id: "req-1" },
    };

    await createBetaFeedbackReport(worldId, input);

    const [path, request] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(path).toBe("/api/worlds/world%2Fprivate%3Fbeta%3Dtrue%23frag/beta-feedback/reports");
    expect(request.method).toBe("POST");
    expect((request.headers as Headers).get("Content-Type")).toBe("application/json");
    expect((request.headers as Headers).get("X-CSRF-Token")).toBe("csrf-token");
    expect(request.body).toBe(JSON.stringify(input));
  });

  it("encodes world and report path segments when triaging feedback reports", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ...feedbackReport, status: "triaged" }));
    vi.stubGlobal("fetch", fetchMock);

    const input = {
      status: "triaged" as const,
      severity: "medium" as const,
      triage_note: "Linked to provider reliability review.",
      repair_proposal_refs: [],
    };

    await triageBetaFeedbackReport(worldId, reportId, input);

    const [path, request] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(path).toBe(
      "/api/worlds/world%2Fprivate%3Fbeta%3Dtrue%23frag/beta-feedback/reports/" +
        "feedback%2Freport%3Ftriage%3Dtrue%23frag/triage",
    );
    expect(request.method).toBe("PATCH");
    expect((request.headers as Headers).get("Content-Type")).toBe("application/json");
    expect((request.headers as Headers).get("X-CSRF-Token")).toBe("csrf-token");
    expect(request.body).toBe(JSON.stringify(input));
  });
});

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

const worldId = "world/private?beta=true#frag";
const worldlineId = "worldline/private?phase=1#frag";
const reportId = "feedback/report?triage=true#frag";

const feedbackReport = {
  id: "feedback-1",
  world_id: "world-1",
  worldline_id: "worldline-1",
  reporter_user_id: "user-1",
  player_actor_id: null,
  issue_type: "provider",
  severity: "high",
  status: "submitted",
  title: "Provider failed",
  description: "The provider degraded during onboarding.",
  reporter_note: null,
  evidence_refs: [],
  repair_proposal_refs: [],
  triage_note: null,
  triaged_by_actor_ref: null,
  triaged_at: null,
  moderation_report_id: null,
  metadata: {},
  created_at: "2026-05-17T00:00:00.000Z",
  updated_at: "2026-05-17T00:00:00.000Z",
};
