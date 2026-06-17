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

  it("normalizes sensitive json error details before relaying proxy responses", async () => {
    const backendResponse = new Response(
      JSON.stringify({
        detail: {
          message: "Provider failed with rawPrompt, Bearer proxy-token, and storageUri media://proxy/object",
          review_status: "fail",
          storageUri: "media://proxy/hidden-object",
        },
      }),
      {
        status: 500,
        headers: {
          "content-type": "application/json",
          "set-cookie": "noveland_session=attacker; Path=/",
        },
      },
    );

    const response = await buildProxyResponse(backendResponse);

    expect(response.status).toBe(500);
    expect(response.headers.get("set-cookie")).toBeNull();
    const body = await response.json();
    expect(JSON.stringify(body)).not.toMatch(/rawPrompt|Bearer proxy-token|media:\/\//i);
    expect(body.detail.message).toBe("Request failed.");
    expect(body.detail.review_status).toBe("fail");
    expect(body.detail.storageUri).toBeUndefined();
  });

  it("normalizes sensitive structured json error content types", async () => {
    const backendResponse = new Response(
      JSON.stringify({
        detail: {
          message: "Problem detail leaked rawOutput, Bearer problem-token, and media://problem/object",
          storageUri: "media://problem/hidden-object",
        },
      }),
      {
        status: 502,
        headers: {
          "content-type": "application/problem+json",
          "content-length": "200",
        },
      },
    );

    const response = await buildProxyResponse(backendResponse);

    expect(response.status).toBe(502);
    expect(response.headers.get("content-length")).toBeNull();
    const body = await response.json();
    expect(JSON.stringify(body)).not.toMatch(/rawOutput|Bearer problem-token|media:\/\//i);
    expect(body.detail.message).toBe("Request failed.");
    expect(body.detail.storageUri).toBeUndefined();
  });

  it("normalizes filesystem and object-storage path variants in json error details", async () => {
    const backendResponse = new Response(
      JSON.stringify({
        detail: {
          message: "Upload failed at file:///root/code/Noveland/.env and s3://noveland/private/object",
          debugPath: "/root/code/Noveland/private/provider-output.json",
          safeCode: "upload_failed",
        },
      }),
      {
        status: 500,
        headers: {
          "content-type": "application/json",
        },
      },
    );

    const response = await buildProxyResponse(backendResponse);

    expect(response.status).toBe(500);
    const body = await response.json();
    expect(JSON.stringify(body)).not.toMatch(/file:\/\/|s3:\/\/|\/root\/code/i);
    expect(body.detail.message).toBe("Request failed.");
    expect(body.detail.debugPath).toBe("[redacted]");
    expect(body.detail.safeCode).toBe("upload_failed");
  });

  it("leaves safe json error bodies unchanged", async () => {
    const safeBody = JSON.stringify(
      { detail: { message: "Invalid credentials", review_status: "fail" } },
      null,
      2,
    );
    const contentLength = String(new TextEncoder().encode(safeBody).byteLength);
    const backendResponse = new Response(safeBody, {
      status: 400,
      headers: {
        "content-type": "application/json",
        "content-length": contentLength,
      },
    });

    const response = await buildProxyResponse(backendResponse);

    expect(response.headers.get("content-length")).toBe(contentLength);
    await expect(response.text()).resolves.toBe(safeBody);
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
