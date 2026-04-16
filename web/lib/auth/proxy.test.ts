import { describe, expect, it } from "vitest";

import { buildProxyResponse, extractSetCookieHeaders } from "@/lib/auth/proxy";

describe("auth proxy helpers", () => {
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

    const response = await buildProxyResponse(backendResponse);

    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toBe("application/json");
    expect(response.headers.get("cache-control")).toBe("no-store");
    expect(response.headers.get("set-cookie")).toContain("noveland_csrf=csrf");
    await expect(response.json()).resolves.toEqual({ ok: true });
  });
});
