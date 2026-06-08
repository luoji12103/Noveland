import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { GET as memoryProfileJobsGET } from "@/app/api/memory-backend-profiles/[profileId]/jobs/route";
import { GET as memoryProfileLogsGET } from "@/app/api/memory-backend-profiles/[profileId]/logs/route";

describe("runtime proxy route handlers", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it("forwards memory backend job query parameters exactly once", async () => {
    vi.stubEnv("NOVELAND_API_BASE_URL", "http://api.example.test");
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ jobs: [] }));
    vi.stubGlobal("fetch", fetchMock);
    const request = new NextRequest("http://web.example.test/api/memory-backend-profiles/memory%2Fprofile/jobs?status=failed&limit=5");

    const response = await memoryProfileJobsGET(request, {
      params: Promise.resolve({ profileId: "memory/profile" }),
    });

    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.example.test/memory-backend-profiles/memory%2Fprofile/jobs?status=failed&limit=5",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("forwards memory backend log query parameters exactly once", async () => {
    vi.stubEnv("NOVELAND_API_BASE_URL", "http://api.example.test");
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ write_logs: [], retrieval_logs: [] }));
    vi.stubGlobal("fetch", fetchMock);
    const request = new NextRequest("http://web.example.test/api/memory-backend-profiles/memory%2Fprofile/logs?limit=10");

    const response = await memoryProfileLogsGET(request, {
      params: Promise.resolve({ profileId: "memory/profile" }),
    });

    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.example.test/memory-backend-profiles/memory%2Fprofile/logs?limit=10",
      expect.objectContaining({ method: "GET" }),
    );
  });
});

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}
