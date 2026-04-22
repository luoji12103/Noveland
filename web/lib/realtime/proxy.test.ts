import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { proxyEventStream } from "@/lib/realtime/proxy";

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
});
