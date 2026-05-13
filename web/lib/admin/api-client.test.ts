import { afterEach, describe, expect, it, vi } from "vitest";

import { adminRequest, AdminClientError } from "@/lib/admin/api-client";

describe("admin API client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    document.cookie = "noveland_csrf=; Max-Age=0; Path=/";
  });

  it("adds csrf headers to mutating admin requests", async () => {
    document.cookie = "noveland_csrf=csrf-token; Path=/";
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    await adminRequest<{ ok: boolean }>("/api/provider-profiles", {
      method: "POST",
      body: { profile_key: "fake" },
      csrf: true,
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/provider-profiles",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
        cache: "no-store",
        body: JSON.stringify({ profile_key: "fake" }),
        headers: expect.any(Headers),
      }),
    );
    const headers = fetchMock.mock.calls[0][1].headers as Headers;
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(headers.get("X-CSRF-Token")).toBe("csrf-token");
  });

  it("requests csrf when the cookie is absent", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ csrf_token: "new-csrf" }))
      .mockResolvedValueOnce(jsonResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    await adminRequest<{ ok: boolean }>("/api/runtime/control", {
      method: "PATCH",
      body: { desired_state: "running" },
      csrf: true,
    });

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/auth/csrf",
      expect.objectContaining({ cache: "no-store", credentials: "include" }),
    );
    const headers = fetchMock.mock.calls[1][1].headers as Headers;
    expect(headers.get("X-CSRF-Token")).toBe("new-csrf");
  });

  it("preserves safe backend error detail", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ detail: "Forbidden" }, { status: 403 })),
    );

    await expect(adminRequest("/api/provider-profiles", { method: "GET" })).rejects.toEqual(
      new AdminClientError("Forbidden", 403),
    );
  });

  it("handles no-content responses", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204 })));

    await expect(adminRequest<void>("/api/provider-profiles/profile-1", { method: "DELETE" }))
      .resolves.toBeUndefined();
  });
});

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: { "Content-Type": "application/json" },
  });
}
