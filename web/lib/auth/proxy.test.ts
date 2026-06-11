import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { buildProxyResponse, extractSetCookieHeaders, proxyAuthRequest } from "@/lib/auth/proxy";

describe("auth proxy helpers", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it("extracts multiple set-cookie headers when runtime exposes getSetCookie", () => {
    const headers = new Headers() as Headers & { getSetCookie: () => string[] };
    headers.getSetCookie = () => ["noveland_session=token; Path=/", "noveland_csrf=csrf; Path=/"];

    expect(extractSetCookieHeaders(headers)).toEqual([
      "noveland_session=token; Path=/",
      "noveland_csrf=csrf; Path=/",
    ]);
  });

  it("relays response status, content type, cache policy, and cookies", async () => {
    const backendResponse = new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: {
        "content-type": "application/json",
        "set-cookie": "noveland_csrf=csrf; Path=/",
      },
    });

    const response = await buildProxyResponse(backendResponse, { relaySetCookie: true });

    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toBe("application/json");
    expect(response.headers.get("cache-control")).toBe("no-store");
    expect(response.headers.get("set-cookie")).toContain("noveland_csrf=csrf");
    await expect(response.json()).resolves.toEqual({ ok: true });
  });

  it("strips set-cookie headers unless cookie relay is explicitly enabled", async () => {
    const backendResponse = new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: {
        "content-type": "application/json",
        "set-cookie": "noveland_session=attacker; Path=/",
      },
    });

    const response = await buildProxyResponse(backendResponse);

    expect(response.headers.get("set-cookie")).toBeNull();
    await expect(response.json()).resolves.toEqual({ ok: true });
  });

  it("auth proxy requests explicitly relay backend cookie mutations", async () => {
    vi.stubEnv("NOVELAND_API_BASE_URL", "http://api.example.test");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ csrf_token: "csrf" }), {
          status: 200,
          headers: {
            "content-type": "application/json",
            "set-cookie": "noveland_csrf=csrf; Path=/",
          },
        }),
      ),
    );
    const request = new NextRequest("http://web.example.test/api/auth/csrf");

    const response = await proxyAuthRequest(request, "/auth/csrf", "GET");

    expect(response.headers.get("set-cookie")).toContain("noveland_csrf=csrf");
  });
});
