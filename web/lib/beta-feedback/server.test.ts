import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { headersMock } = vi.hoisted(() => ({
  headersMock: vi.fn(),
}));

vi.mock("next/headers", () => ({
  headers: headersMock,
}));

import { getBetaFeedbackData } from "@/lib/beta-feedback/server";

describe("beta feedback server loader", () => {
  beforeEach(() => {
    headersMock.mockResolvedValue({
      get: (name: string) => (name === "cookie" ? "noveland_session=session" : null),
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
    vi.clearAllMocks();
  });

  it("normalizes sensitive backend error details before rethrowing auth failures", async () => {
    vi.stubEnv("NOVELAND_API_BASE_URL", apiBase);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(
          {
            detail:
              "Beta feedback auth failed with rawPrompt, Bearer beta-token, and /var/noveland/feedback",
          },
          401,
        ),
      ),
    );

    await expect(getBetaFeedbackData(worldId, false)).rejects.toMatchObject({
      message: "Beta feedback request failed.",
      status: 401,
    });
  });

  it("encodes reserved characters in backend world path segments", async () => {
    vi.stubEnv("NOVELAND_API_BASE_URL", apiBase);
    const fetchMock = vi.fn(async (requestUrl: string) => responseFor(requestUrl));
    vi.stubGlobal("fetch", fetchMock);

    await getBetaFeedbackData(worldId, false);

    const urls = fetchMock.mock.calls.map((call) => String(call[0]));
    const encodedWorld = encodeURIComponent(worldId);

    expect(urls).toContain(`${apiBase}/worlds/${encodedWorld}/worldlines`);
    expect(urls).toContain(`${apiBase}/worlds/${encodedWorld}/beta-feedback/reports`);
    expect(urls).toContain(`${apiBase}/worlds/${encodedWorld}/memberships`);
    expect(urls.join("\n")).not.toContain("/worlds/world/feedback?");
  });
});

const apiBase = "http://api.example.test";
const worldId = "world/feedback?mode=triage#frag";

function responseFor(requestUrl: string): Response {
  const url = new URL(requestUrl);
  const encodedWorld = encodeURIComponent(worldId);
  const worldPrefix = `/worlds/${encodedWorld}`;

  if (url.pathname === "/worlds") {
    return jsonResponse([{ id: worldId, name: "World" }]);
  }
  if (!url.pathname.startsWith(worldPrefix)) {
    throw new Error(`Unexpected backend URL: ${requestUrl}`);
  }
  if (url.pathname.endsWith("/worldlines")) {
    return jsonResponse([]);
  }
  if (url.pathname.endsWith("/beta-feedback/reports")) {
    return jsonResponse([]);
  }
  if (url.pathname.endsWith("/memberships")) {
    return jsonResponse([]);
  }
  throw new Error(`Unexpected backend URL: ${requestUrl}`);
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}
