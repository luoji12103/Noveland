import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { proxyPrivateBetaRequest } from "@/lib/private-beta/proxy";

describe("private beta proxy", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it("strips backend set-cookie headers from non-auth private beta responses", async () => {
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
    const request = new NextRequest("http://web.example.test/api/private-beta/onboarding");

    const response = await proxyPrivateBetaRequest(request, ["onboarding"], "GET");

    expect(response.status).toBe(200);
    expect(response.headers.get("set-cookie")).toBeNull();
    await expect(response.json()).resolves.toEqual({ ok: true });
  });
});
