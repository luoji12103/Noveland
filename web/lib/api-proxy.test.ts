import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { proxyApiRequest } from "@/lib/api-proxy";

describe("api proxy", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it("strips backend set-cookie headers from non-auth API responses", async () => {
    vi.stubEnv("NOVELAND_API_BASE_URL", "http://api.example.test");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ ok: true }), {
          status: 200,
          headers: {
            "content-type": "application/json",
            "set-cookie": "noveland_csrf=attacker; Path=/",
          },
        }),
      ),
    );
    const request = new NextRequest("http://web.example.test/api/plugins/catalog");

    const response = await proxyApiRequest(request, "/plugins/catalog", "GET");

    expect(response.status).toBe(200);
    expect(response.headers.get("set-cookie")).toBeNull();
    await expect(response.json()).resolves.toEqual({ ok: true });
  });
});
