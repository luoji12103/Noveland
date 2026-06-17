import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { proxyEventStream } from "@/lib/realtime/proxy";
import { GET as conversationStreamGET } from "@/app/api/worlds/[worldId]/conversations/[conversationId]/stream/route";
import { GET as worldStreamGET } from "@/app/api/worlds/[worldId]/stream/route";

describe("realtime proxy", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it("forwards cookie and last-event-id headers to the backend stream", async () => {
    vi.stubEnv("NOVELAND_API_BASE_URL", "http://api.example.test");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response("id: cursor\ndata: {}\n\n", {
        status: 200,
        headers: { "content-type": "text/event-stream" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const request = new NextRequest("http://web.example.test/api/runtime/stream", {
      headers: {
        cookie: "noveland_session=session",
        "last-event-id": "cursor-123",
        accept: "text/event-stream",
      },
    });

    const response = await proxyEventStream(request, "/runtime/stream");

    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.example.test/runtime/stream",
      expect.objectContaining({ method: "GET" }),
    );
    const headers = fetchMock.mock.calls[0][1].headers as Headers;
    expect(headers.get("cookie")).toBe("noveland_session=session");
    expect(headers.get("last-event-id")).toBe("cursor-123");
  });

  it("normalizes sensitive json setup errors before returning stream proxy responses", async () => {
    vi.stubEnv("NOVELAND_API_BASE_URL", "http://api.example.test");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            detail: {
              message: "Stream setup leaked rawPrompt, Bearer stream-token, and media://stream/object",
              storageUri: "media://stream/hidden-object",
            },
          }),
          {
            status: 500,
            headers: {
              "content-type": "application/problem+json",
              "set-cookie": "noveland_session=attacker; Path=/",
            },
          },
        ),
      ),
    );
    const request = new NextRequest("http://web.example.test/api/runtime/stream");

    const response = await proxyEventStream(request, "/runtime/stream");

    expect(response.status).toBe(500);
    expect(response.headers.get("set-cookie")).toBeNull();
    expect(response.headers.get("connection")).toBeNull();
    const body = await response.json();
    expect(JSON.stringify(body)).not.toMatch(/rawPrompt|Bearer stream-token|media:\/\//i);
    expect(body.detail.message).toBe("Request failed.");
    expect(body.detail.storageUri).toBeUndefined();
  });

  it("encodes dynamic world stream path segments before proxying", async () => {
    vi.stubEnv("NOVELAND_API_BASE_URL", "http://api.example.test");
    const fetchMock = vi.fn().mockResolvedValue(streamResponse());
    vi.stubGlobal("fetch", fetchMock);
    const request = new NextRequest(
      "http://web.example.test/api/worlds/world%2Fadmin/stream?cursor=next",
      {
        headers: {
          cookie: "noveland_session=session",
        },
      },
    );

    const response = await worldStreamGET(request, {
      params: Promise.resolve({ worldId: "world/admin" }),
    });

    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.example.test/worlds/world%2Fadmin/stream?cursor=next",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("encodes dynamic conversation stream path segments before proxying", async () => {
    vi.stubEnv("NOVELAND_API_BASE_URL", "http://api.example.test");
    const fetchMock = vi.fn().mockResolvedValue(streamResponse());
    vi.stubGlobal("fetch", fetchMock);
    const request = new NextRequest(
      "http://web.example.test/api/worlds/world%2Fadmin/conversations/conversation%2Fdebug/stream",
      {
        headers: {
          cookie: "noveland_session=session",
        },
      },
    );

    const response = await conversationStreamGET(request, {
      params: Promise.resolve({
        worldId: "world/admin",
        conversationId: "conversation/debug",
      }),
    });

    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.example.test/worlds/world%2Fadmin/conversations/conversation%2Fdebug/stream",
      expect.objectContaining({ method: "GET" }),
    );
  });
});

function streamResponse(): Response {
  return new Response("id: cursor\ndata: {}\n\n", {
    status: 200,
    headers: { "content-type": "text/event-stream" },
  });
}
