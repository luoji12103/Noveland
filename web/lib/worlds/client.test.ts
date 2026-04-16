import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createWorld,
  deactivateScene,
  listMemberCandidates,
  updateAgent,
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
