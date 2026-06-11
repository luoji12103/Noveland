import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { proxyWorldRequest } from "@/lib/worlds/proxy";

describe("world proxy", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it("forwards path, query, cookies, csrf header, and json body", async () => {
    vi.stubEnv("NOVELAND_API_BASE_URL", "http://api.example.test");
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);
    const request = new NextRequest("http://web.example.test/api/worlds/world-1/scenes?limit=2", {
      method: "POST",
      headers: {
        cookie: "noveland_session=session",
        "content-type": "application/json",
        "x-csrf-token": "csrf",
      },
      body: JSON.stringify({ scene_key: "home", name: "Home" }),
    });

    const response = await proxyWorldRequest(request, ["world-1", "scenes"], "POST");

    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.example.test/worlds/world-1/scenes?limit=2",
      expect.objectContaining({
        method: "POST",
      }),
    );
    const body = fetchMock.mock.calls[0][1].body as ArrayBuffer;
    expect(new TextDecoder().decode(body)).toBe(
      JSON.stringify({ scene_key: "home", name: "Home" }),
    );
    const headers = fetchMock.mock.calls[0][1].headers as Headers;
    expect(headers.get("cookie")).toBe("noveland_session=session");
    expect(headers.get("x-csrf-token")).toBe("csrf");
  });

  it("forwards upload request bodies as original bytes", async () => {
    vi.stubEnv("NOVELAND_API_BASE_URL", "http://api.example.test");
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);
    const uploadBytes = new Uint8Array([0, 255, 128, 65]);
    const request = new NextRequest("http://web.example.test/api/worlds/world-1/media/assets/upload", {
      method: "POST",
      headers: {
        "content-type": "application/octet-stream",
        "x-csrf-token": "csrf",
      },
      body: uploadBytes,
    });

    const response = await proxyWorldRequest(request, ["world-1", "media", "assets", "upload"], "POST");

    expect(response.status).toBe(200);
    const forwardedBody = new Uint8Array(fetchMock.mock.calls[0][1].body as ArrayBuffer);
    expect(Array.from(forwardedBody)).toEqual(Array.from(uploadBytes));
  });

  it("strips backend set-cookie headers from non-auth world responses", async () => {
    vi.stubEnv("NOVELAND_API_BASE_URL", "http://api.example.test");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ ok: true }), {
          status: 200,
          headers: {
            "content-type": "application/json",
            "set-cookie": "noveland_session=attacker; Path=/",
          },
        }),
      ),
    );
    const request = new NextRequest("http://web.example.test/api/worlds/world-1");

    const response = await proxyWorldRequest(request, ["world-1"], "GET");

    expect(response.status).toBe(200);
    expect(response.headers.get("set-cookie")).toBeNull();
    await expect(response.json()).resolves.toEqual({ ok: true });
  });

  it("preserves media safety headers while stripping backend cookies", async () => {
    vi.stubEnv("NOVELAND_API_BASE_URL", "http://api.example.test");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(new Uint8Array([1, 2, 3]), {
          status: 200,
          headers: {
            "content-type": "image/png",
            "content-disposition": "attachment; filename=scene.png",
            "content-length": "3",
            "x-content-type-options": "nosniff",
            "set-cookie": "noveland_session=attacker; Path=/",
          },
        }),
      ),
    );
    const request = new NextRequest("http://web.example.test/api/worlds/world-1/reader/media/objects/object-1/download");

    const response = await proxyWorldRequest(
      request,
      ["world-1", "reader", "media", "objects", "object-1", "download"],
      "GET",
    );

    expect(response.headers.get("content-type")).toBe("image/png");
    expect(response.headers.get("content-disposition")).toBe("attachment; filename=scene.png");
    expect(response.headers.get("content-length")).toBe("3");
    expect(response.headers.get("x-content-type-options")).toBe("nosniff");
    expect(response.headers.get("set-cookie")).toBeNull();
  });

  it("relays backend delete status", async () => {
    vi.stubEnv("NOVELAND_API_BASE_URL", "http://api.example.test");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204 })));
    const request = new NextRequest("http://web.example.test/api/worlds/world-1");

    const response = await proxyWorldRequest(request, ["world-1"], "DELETE");

    expect(response.status).toBe(204);
  });
});

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}
